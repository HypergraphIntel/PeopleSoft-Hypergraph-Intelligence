"""
SQLite store for runtime history snapshots.
Persisted at data/runtime.db.

One row is recorded every SNAPSHOT_INTERVAL_SECONDS (default 5 min) per environment.
Captures process queue totals, IB pending message count, and active alert count.
Retention: 30 days by default.
"""

import sqlite3
import time
from pathlib import Path

DATA_DIR = Path("/opt/deathstar-api/data")
DB_PATH  = DATA_DIR / "runtime.db"

RETAIN_DAYS = 30


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS runtime_snapshots (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                ts               TEXT NOT NULL,
                env              TEXT NOT NULL,
                process_active   INTEGER,
                process_error    INTEGER,
                process_total    INTEGER,
                ae_running       INTEGER,
                ib_pending       INTEGER,
                alert_count      INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_rt_env_ts
                ON runtime_snapshots(env, ts DESC);
        """)


def record(env: str, data: dict) -> int:
    """Persist one runtime snapshot row. Returns the new row id."""
    init_db()
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO runtime_snapshots
               (ts, env, process_active, process_error, process_total,
                ae_running, ib_pending, alert_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ts,
                env,
                data.get("process_active"),
                data.get("process_error"),
                data.get("process_total"),
                data.get("ae_running"),
                data.get("ib_pending"),
                data.get("alert_count"),
            ),
        )
        return cur.lastrowid


def get_history(env: str, hours: int = 24) -> list[dict]:
    """Return snapshot rows for the specified env ordered oldest-first."""
    init_db()
    cutoff = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() - hours * 3600)
    )
    with _conn() as con:
        rows = con.execute(
            """SELECT ts, process_active, process_error, process_total,
                      ae_running, ib_pending, alert_count
               FROM runtime_snapshots
               WHERE env = ? AND ts >= ?
               ORDER BY ts ASC""",
            (env, cutoff)
        ).fetchall()
    return [dict(r) for r in rows]


def prune(env: str, keep_days: int = RETAIN_DAYS) -> int:
    """Delete rows older than keep_days for the given env. Returns deleted count."""
    init_db()
    cutoff = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() - keep_days * 86400)
    )
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM runtime_snapshots WHERE env = ? AND ts < ?",
            (env, cutoff)
        )
        return cur.rowcount
