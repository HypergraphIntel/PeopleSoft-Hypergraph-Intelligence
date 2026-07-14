"""
Promotion Event Log — SQLite-backed store for manually recorded environment promotions.

Phase 1: manual log only. Phase 2 (future): auto-detection from PSPROJECTDEFN
LASTUPDDTTM comparison when DV/TST/UAT/PRD DB connections are available.
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
