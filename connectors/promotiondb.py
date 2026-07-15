"""
Promotion Event Log — SQLite-backed store for manually recorded environment promotions.

Phase 1: manual log. Phase 2: auto-detection from PSPROJECTDEFN.LASTUPDDTTM —
snapshots each environment in a configured promotion chain and, when a
downstream environment's timestamp for a project changes to match its
upstream neighbor's current timestamp, records the promotion automatically.
"""

import json
import sqlite3
import time
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH  = DATA_DIR / "promotions.db"

# Canonical environment ordering — used for display and validation hints.
# Not enforced; from_env/to_env are free-form text to support lab/aux envs.
ENV_ORDER = ["DV", "TST", "UAT", "PRD"]
ENV_SUGGESTIONS = ["DV", "TST", "UAT", "CRP", "PAR", "PER", "PRD"]


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS promotions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pillar       TEXT NOT NULL,
                project      TEXT NOT NULL,
                from_env     TEXT NOT NULL,
                to_env       TEXT NOT NULL,
                promoted_at  TEXT NOT NULL,
                promoted_by  TEXT,
                notes        TEXT,
                ticket_ref   TEXT,
                created_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_promo_pillar
                ON promotions(pillar, promoted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_promo_project
                ON promotions(project, promoted_at DESC);

            CREATE TABLE IF NOT EXISTS project_state (
                pillar         TEXT NOT NULL,
                env            TEXT NOT NULL,
                project        TEXT NOT NULL,
                last_upd_dttm  TEXT NOT NULL,
                checked_at     TEXT NOT NULL,
                PRIMARY KEY (pillar, env, project)
            );
        """)


def record_promotion(
    pillar: str,
    project: str,
    from_env: str,
    to_env: str,
    promoted_at: str,
    promoted_by: str = None,
    notes: str = None,
    ticket_ref: str = None,
) -> dict:
    """
    Insert a promotion event. Returns the created record.
    promoted_at must be an ISO 8601 date/datetime string (e.g. '2026-07-01' or '2026-07-01T14:30:00Z').
    """
    init_db()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO promotions
                (pillar, project, from_env, to_env, promoted_at,
                 promoted_by, notes, ticket_ref, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                pillar.upper().strip(),
                project.upper().strip(),
                from_env.upper().strip(),
                to_env.upper().strip(),
                promoted_at.strip(),
                (promoted_by or "").strip() or None,
                (notes or "").strip() or None,
                (ticket_ref or "").strip() or None,
                now,
            ),
        )
        new_id = cur.lastrowid
    # Fetch after the with-block exits so the commit is visible to the new connection
    return get_promotion(new_id)


def get_promotion(id: int) -> dict | None:
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM promotions WHERE id=?", (id,)
        ).fetchone()
    return dict(row) if row else None


def list_promotions(
    pillar: str = None,
    project: str = None,
    env: str = None,
    limit: int = 200,
) -> list:
    """
    Return promotion events, newest first.
    `env` matches either from_env or to_env.
    """
    init_db()
    clauses, params = [], []
    if pillar:
        clauses.append("UPPER(pillar)=UPPER(?)")
        params.append(pillar)
    if project:
        clauses.append("UPPER(project) LIKE UPPER(?)")
        params.append(f"%{project}%")
    if env:
        clauses.append("(UPPER(from_env)=UPPER(?) OR UPPER(to_env)=UPPER(?))")
        params += [env, env]

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    with _conn() as con:
        rows = con.execute(
            f"SELECT * FROM promotions {where} ORDER BY promoted_at DESC, id DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def delete_promotion(id: int) -> bool:
    """Hard-delete a promotion record. Returns True if a row was deleted."""
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM promotions WHERE id=?", (id,))
    return cur.rowcount > 0


def project_timeline(pillar: str, project: str) -> list:
    """
    Return all promotion events for a project in chronological order,
    shaped as a timeline for UI rendering.
    """
    init_db()
    with _conn() as con:
        rows = con.execute(
            """
            SELECT * FROM promotions
             WHERE UPPER(pillar)=UPPER(?) AND UPPER(project)=UPPER(?)
             ORDER BY promoted_at ASC, id ASC
            """,
            (pillar, project),
        ).fetchall()
    return [dict(r) for r in rows]


def _load_project_state(pillar: str, env: str) -> dict:
    """Return {project: last_upd_dttm} previously recorded for this pillar/env."""
    with _conn() as con:
        rows = con.execute(
            "SELECT project, last_upd_dttm FROM project_state WHERE UPPER(pillar)=UPPER(?) AND UPPER(env)=UPPER(?)",
            (pillar, env),
        ).fetchall()
    return {r["project"]: r["last_upd_dttm"] for r in rows}


def _save_project_state(pillar: str, env: str, current: dict):
    """Upsert {project: last_upd_dttm} for this pillar/env."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _conn() as con:
        con.executemany(
            """
            INSERT INTO project_state (pillar, env, project, last_upd_dttm, checked_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(pillar, env, project) DO UPDATE SET
                last_upd_dttm = excluded.last_upd_dttm,
                checked_at    = excluded.checked_at
            """,
            [
                (pillar.upper().strip(), env.upper().strip(), project, last_upd, now)
                for project, last_upd in current.items()
            ],
        )


def detect_promotions(pillar: str, chain: list[str]) -> dict:
    """
    Snapshot PSPROJECTDEFN.LASTUPDDTTM for every environment in `chain`
    (ordered upstream -> downstream, e.g. ["DV", "TST", "UAT", "PRD"]) and
    auto-record a promotion whenever a downstream environment's timestamp
    for a project changes since the last check AND the new value matches
    its immediate upstream neighbor's current timestamp.

    First run for a given pillar/chain only establishes a baseline (no prior
    state to diff against) — nothing is auto-recorded until a second run
    observes a real change.
    """
    from connectors import psdb

    init_db()
    envs_cfg = {e["name"]: e for e in psdb.load_envs()}
    current: dict[str, dict[str, str]] = {}
    project_counts: dict[str, int] = {}

    for env in chain:
        if env not in envs_cfg:
            raise KeyError(f"Environment '{env}' not found in config.json peoplesoft.environments")
        rows = psdb.query_env(
            envs_cfg[env],
            "SELECT PROJECTNAME, LASTUPDDTTM FROM SYSADM.PSPROJECTDEFN",
        )
        current[env] = {r["projectname"]: str(r["lastupddttm"]) for r in rows}
        project_counts[env] = len(current[env])

    detected = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for i in range(1, len(chain)):
        upstream_env, this_env = chain[i - 1], chain[i]
        prev_state = _load_project_state(pillar, this_env)
        for project, cur_val in current[this_env].items():
            prev_val = prev_state.get(project)
            if prev_val is None or prev_val == cur_val:
                continue   # no prior baseline, or unchanged — nothing to detect
            upstream_val = current[upstream_env].get(project)
            if upstream_val is not None and upstream_val == cur_val:
                promo = record_promotion(
                    pillar=pillar,
                    project=project,
                    from_env=upstream_env,
                    to_env=this_env,
                    promoted_at=now,
                    promoted_by="auto-detected",
                    notes=(f"Auto-detected: PSPROJECTDEFN.LASTUPDDTTM in {this_env} advanced "
                           f"from {prev_val} to {cur_val}, matching {upstream_env}'s current value."),
                )
                detected.append(promo)

    for env in chain:
        _save_project_state(pillar, env, current[env])

    return {
        "pillar": pillar.upper(),
        "chain": chain,
        "project_counts": project_counts,
        "detected": detected,
        "checked_at": now,
    }


def pillar_summary(pillar: str) -> list:
    """
    Return distinct projects that have promotion events for a pillar,
    with their latest promotion date and furthest-along environment.
    """
    init_db()
    with _conn() as con:
        rows = con.execute(
            """
            SELECT project,
                   COUNT(*) AS event_count,
                   MAX(promoted_at) AS latest_promotion,
                   MAX(to_env) AS latest_to_env
              FROM promotions
             WHERE UPPER(pillar)=UPPER(?)
             GROUP BY project
             ORDER BY latest_promotion DESC
            """,
            (pillar,),
        ).fetchall()
    return [dict(r) for r in rows]
