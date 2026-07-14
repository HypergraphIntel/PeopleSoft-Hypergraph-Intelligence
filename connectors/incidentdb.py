"""
SQLite store for incident records and runtime state snapshots.
Persisted at data/incidents.db.

Schema
------
incidents
  id           INTEGER PK
  title        TEXT
  env          TEXT
  severity     TEXT    (P1/P2/P3/P4)
  state        TEXT    (open/resolved)
  created_at   TEXT    ISO-8601
  resolved_at  TEXT    ISO-8601 or NULL
  window_start TEXT    ISO-8601 (RCA window start)
  window_end   TEXT    ISO-8601 (RCA window end)
  notes        TEXT

incident_snapshots
  id           INTEGER PK
  incident_id  INTEGER FK → incidents.id
  source       TEXT    (rca/process/log/ash/ib/kg)
  data         TEXT    JSON blob
  snapshot_at  TEXT    ISO-8601
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH  = DATA_DIR / "incidents.db"


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                env          TEXT    NOT NULL DEFAULT 'HCM',
                severity     TEXT    NOT NULL DEFAULT 'P3',
                state        TEXT    NOT NULL DEFAULT 'open',
                created_at   TEXT    NOT NULL,
                resolved_at  TEXT,
                window_start TEXT,
                window_end   TEXT,
                notes        TEXT    DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_inc_state ON incidents(state);
            CREATE INDEX IF NOT EXISTS idx_inc_env   ON incidents(env);
            CREATE INDEX IF NOT EXISTS idx_inc_created ON incidents(created_at);

            CREATE TABLE IF NOT EXISTS incident_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
                source      TEXT    NOT NULL,
                data        TEXT    NOT NULL DEFAULT '{}',
                snapshot_at TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snap_inc ON incident_snapshots(incident_id);
        """)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ── Incident CRUD ─────────────────────────────────────────────────────────────

def create_incident(title: str, env: str, severity: str = "P3",
                    window_start: str = None, window_end: str = None,
                    notes: str = "") -> int:
    """Create a new incident record; returns the new incident id."""
    now = _now_iso()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO incidents (title, env, severity, state,
                   created_at, window_start, window_end, notes)
               VALUES (?,?,?,'open',?,?,?,?)""",
            (title, env, severity, now, window_start, window_end, notes),
        )
        return cur.lastrowid


def list_incidents(state: str = None, env: str = None, limit: int = 200) -> list:
    """Return incidents, newest first, with optional state/env filter."""
    sql  = "SELECT * FROM incidents WHERE 1=1"
    args = []
    if state:
        sql += " AND state=?"; args.append(state)
    if env:
        sql += " AND env=?"; args.append(env)
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with _conn() as con:
        return [dict(r) for r in con.execute(sql, args).fetchall()]


def get_incident(incident_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM incidents WHERE id=?", (incident_id,)
        ).fetchone()
        return dict(row) if row else None


def update_incident(incident_id: int, **kwargs) -> bool:
    """Update mutable fields: title, severity, state, notes, resolved_at."""
    allowed = {"title", "severity", "state", "notes", "resolved_at"}
    fields  = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    # auto-set resolved_at when transitioning to resolved
    if fields.get("state") == "resolved" and "resolved_at" not in fields:
        fields["resolved_at"] = _now_iso()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values     = list(fields.values()) + [incident_id]
    with _conn() as con:
        rowcount = con.execute(
            f"UPDATE incidents SET {set_clause} WHERE id=?", values
        ).rowcount
    return rowcount > 0


def delete_incident(incident_id: int) -> bool:
    with _conn() as con:
        rowcount = con.execute(
            "DELETE FROM incidents WHERE id=?", (incident_id,)
        ).rowcount
    return rowcount > 0


# ── Snapshots ─────────────────────────────────────────────────────────────────

def add_snapshot(incident_id: int, source: str, data: dict) -> int:
    """Attach a JSON data blob to an incident under a named source."""
    now = _now_iso()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO incident_snapshots (incident_id, source, data, snapshot_at) VALUES (?,?,?,?)",
            (incident_id, source, json.dumps(data, default=str), now),
        )
        return cur.lastrowid


def get_snapshots(incident_id: int) -> list:
    """Return all snapshots for an incident, ordered by snapshot_at."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM incident_snapshots WHERE incident_id=? ORDER BY snapshot_at",
            (incident_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["data"] = json.loads(d["data"])
        except Exception:
            pass
        result.append(d)
    return result


def get_snapshot_series(incident_id: int, source: str) -> list:
    """Return all snapshots for a given source, chronological — a per-source timeline."""
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM incident_snapshots
               WHERE incident_id=? AND source=?
               ORDER BY snapshot_at""",
            (incident_id, source),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["data"] = json.loads(d["data"])
        except Exception:
            pass
        result.append(d)
    return result


def replay_timeline(incident_id: int) -> list:
    """
    Merge every snapshot across all sources into one chronologically-sorted
    list, for a single "what happened, in order" replay view spanning the
    incident's investigation. get_snapshots() already returns everything
    ordered by snapshot_at — this just documents that as the replay contract
    and keeps the shape stable if snapshot storage ever changes.
    """
    return get_snapshots(incident_id)


def get_snapshot(incident_id: int, source: str) -> dict | None:
    """Return the most recent snapshot for a given source."""
    with _conn() as con:
        row = con.execute(
            """SELECT * FROM incident_snapshots
               WHERE incident_id=? AND source=?
               ORDER BY snapshot_at DESC LIMIT 1""",
            (incident_id, source),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["data"] = json.loads(d["data"])
    except Exception:
        pass
    return d


# ── Stats ─────────────────────────────────────────────────────────────────────

def stats() -> dict:
    with _conn() as con:
        total    = con.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        open_cnt = con.execute("SELECT COUNT(*) FROM incidents WHERE state='open'").fetchone()[0]
        p1_open  = con.execute(
            "SELECT COUNT(*) FROM incidents WHERE state='open' AND severity='P1'"
        ).fetchone()[0]
    return {"total": total, "open": open_cnt, "resolved": total - open_cnt, "p1_open": p1_open}


init_db()
