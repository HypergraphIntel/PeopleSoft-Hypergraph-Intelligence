"""
SQLite storage for ingested log data.

DB path: data/logs.db  (relative to repo root, created on first use)

Tables
------
log_sources     — source registry + per-file byte-offset tracking (JSON blob)
web_entries     — parsed access-log rows (web tier: pia_access, apache_access, f5_access)
app_entries     — parsed app-server rows (app tier: appsrv, tuxedo, pia_error, apache_error)
log_errors      — deduplicated errors extracted from both tiers
"""

import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

_DB_PATH: Path | None = None
_local = threading.local()   # per-thread connection


def _db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = Path(__file__).parent.parent / "data" / "logs.db"
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _DB_PATH


def _conn() -> sqlite3.Connection:
    """Return a per-thread SQLite connection, opening one if needed."""
    if not hasattr(_local, "conn") or _local.conn is None:
        db = _db_path()
        conn = sqlite3.connect(str(db), detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return _local.conn


def init_db():
    """Create all tables and indices if they don't exist."""
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS log_sources (
            name        TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            env         TEXT NOT NULL,
            ssh_host    TEXT NOT NULL,
            path        TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1,
            offsets     TEXT NOT NULL DEFAULT '{}',
            last_ingest TEXT,
            error_msg   TEXT
        );

        CREATE TABLE IF NOT EXISTS web_entries (
            id          INTEGER PRIMARY KEY,
            source_name TEXT NOT NULL,
            env         TEXT NOT NULL,
            ts          TEXT NOT NULL,
            ip          TEXT,
            oprid       TEXT,
            method      TEXT,
            url         TEXT,
            component   TEXT,
            page        TEXT,
            menu        TEXT,
            status      INTEGER,
            bytes       INTEGER,
            ms          INTEGER,
            is_error    INTEGER NOT NULL DEFAULT 0,
            raw         TEXT
        );

        CREATE TABLE IF NOT EXISTS app_entries (
            id          INTEGER PRIMARY KEY,
            source_name TEXT NOT NULL,
            env         TEXT NOT NULL,
            ts          TEXT NOT NULL,
            process     TEXT,
            oprid       TEXT,
            level       TEXT,
            message     TEXT,
            error_codes TEXT,
            object_ref  TEXT,
            is_error    INTEGER NOT NULL DEFAULT 0,
            raw         TEXT
        );

        CREATE TABLE IF NOT EXISTS log_errors (
            id          INTEGER PRIMARY KEY,
            source_name TEXT NOT NULL,
            env         TEXT NOT NULL,
            ts          TEXT NOT NULL,
            log_type    TEXT NOT NULL,
            error_code  TEXT,
            object_ref  TEXT,
            oprid       TEXT,
            level       TEXT,
            message     TEXT,
            raw         TEXT,
            UNIQUE(source_name, ts, raw)
        );

        CREATE INDEX IF NOT EXISTS idx_web_ts        ON web_entries(ts);
        CREATE INDEX IF NOT EXISTS idx_web_oprid     ON web_entries(oprid);
        CREATE INDEX IF NOT EXISTS idx_web_component ON web_entries(component);
        CREATE INDEX IF NOT EXISTS idx_web_status    ON web_entries(status);
        CREATE INDEX IF NOT EXISTS idx_web_env       ON web_entries(env);

        CREATE INDEX IF NOT EXISTS idx_app_ts        ON app_entries(ts);
        CREATE INDEX IF NOT EXISTS idx_app_oprid     ON app_entries(oprid);
        CREATE INDEX IF NOT EXISTS idx_app_object    ON app_entries(object_ref);
        CREATE INDEX IF NOT EXISTS idx_app_level     ON app_entries(level);
        CREATE INDEX IF NOT EXISTS idx_app_env       ON app_entries(env);

        CREATE INDEX IF NOT EXISTS idx_err_ts        ON log_errors(ts);
        CREATE INDEX IF NOT EXISTS idx_err_oprid     ON log_errors(oprid);
        CREATE INDEX IF NOT EXISTS idx_err_code      ON log_errors(error_code);
        CREATE INDEX IF NOT EXISTS idx_err_object    ON log_errors(object_ref);
        CREATE INDEX IF NOT EXISTS idx_err_env       ON log_errors(env);
    """)
    c.commit()


def _ts(dt: datetime | None) -> str:
    if dt is None:
        return datetime.utcnow().isoformat(timespec="seconds")
    return dt.isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

def upsert_sources(sources: list[dict]):
    """
    Sync config log_sources into the log_sources table.
    Preserves existing offsets/last_ingest; adds new rows; does NOT delete removed sources.
    """
    c = _conn()
    for src in sources:
        c.execute("""
            INSERT INTO log_sources(name, type, env, ssh_host, path, enabled)
            VALUES(:name, :type, :env, :ssh_host, :path, :enabled)
            ON CONFLICT(name) DO UPDATE SET
                type     = excluded.type,
                env      = excluded.env,
                ssh_host = excluded.ssh_host,
                path     = excluded.path,
                enabled  = excluded.enabled
        """, {
            "name":     src["name"],
            "type":     src["type"],
            "env":      src["env"],
            "ssh_host": src["ssh_host"],
            "path":     src["path"],
            "enabled":  1 if src.get("enabled", True) else 0,
        })
    c.commit()


def get_sources(enabled_only: bool = True) -> list[dict]:
    c = _conn()
    where = "WHERE enabled=1" if enabled_only else ""
    rows = c.execute(f"SELECT * FROM log_sources {where} ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_offsets(source_name: str) -> dict:
    c = _conn()
    row = c.execute("SELECT offsets FROM log_sources WHERE name=?", (source_name,)).fetchone()
    if row is None:
        return {}
    return json.loads(row["offsets"] or "{}")


def save_offsets(source_name: str, offsets: dict):
    c = _conn()
    c.execute("UPDATE log_sources SET offsets=? WHERE name=?",
              (json.dumps(offsets), source_name))
    c.commit()


def mark_ingest_done(source_name: str, error: str | None = None):
    c = _conn()
    c.execute("UPDATE log_sources SET last_ingest=?, error_msg=? WHERE name=?",
              (_ts(None), error, source_name))
    c.commit()


# ---------------------------------------------------------------------------
# Web entry insertion
# ---------------------------------------------------------------------------

_WEB_ACCESS_TYPES = {"pia_access", "apache_access", "f5_access"}

def insert_web_entries(source_name: str, env: str, rows: list[dict]):
    c = _conn()
    c.executemany("""
        INSERT OR IGNORE INTO web_entries
            (source_name, env, ts, ip, oprid, method, url, component, page, menu,
             status, bytes, ms, is_error, raw)
        VALUES
            (:source_name, :env, :ts, :ip, :oprid, :method, :url, :component, :page, :menu,
             :status, :bytes, :ms, :is_error, :raw)
    """, [{
        "source_name": source_name,
        "env":         env,
        "ts":          _ts(r.get("ts")),
        "ip":          r.get("ip"),
        "oprid":       r.get("oprid"),
        "method":      r.get("method"),
        "url":         (r.get("url") or "")[:2000],
        "component":   r.get("component"),
        "page":        r.get("page"),
        "menu":        r.get("menu"),
        "status":      r.get("status"),
        "bytes":       r.get("bytes"),
        "ms":          r.get("ms"),
        "is_error":    1 if r.get("is_error") else 0,
        "raw":         (r.get("raw") or "")[:4000],
    } for r in rows])
    c.commit()


# ---------------------------------------------------------------------------
# App entry insertion
# ---------------------------------------------------------------------------

def insert_app_entries(source_name: str, env: str, rows: list[dict]):
    c = _conn()
    c.executemany("""
        INSERT OR IGNORE INTO app_entries
            (source_name, env, ts, process, oprid, level, message, error_codes, object_ref, is_error, raw)
        VALUES
            (:source_name, :env, :ts, :process, :oprid, :level, :message, :error_codes, :object_ref, :is_error, :raw)
    """, [{
        "source_name": source_name,
        "env":         env,
        "ts":          _ts(r.get("ts")),
        "process":     r.get("process"),
        "oprid":       r.get("oprid"),
        "level":       r.get("level"),
        "message":     (r.get("message") or "")[:4000],
        "error_codes": json.dumps(r.get("error_codes") or []),
        "object_ref":  r.get("object_ref"),
        "is_error":    1 if r.get("is_error") else 0,
        "raw":         (r.get("raw") or "")[:4000],
    } for r in rows])
    c.commit()


# ---------------------------------------------------------------------------
# Error insertion (deduplicated)
# ---------------------------------------------------------------------------

def insert_errors(source_name: str, env: str, log_type: str, rows: list[dict]):
    c = _conn()
    for r in rows:
        error_codes: list = r.get("error_codes") or []
        if not error_codes:
            # Use a synthetic code so we still record the error
            error_codes = [None]
        for code in error_codes:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO log_errors
                        (source_name, env, ts, log_type, error_code, object_ref,
                         oprid, level, message, raw)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    source_name,
                    env,
                    _ts(r.get("ts")),
                    log_type,
                    code,
                    r.get("object_ref"),
                    r.get("oprid"),
                    r.get("level", "ERROR"),
                    (r.get("message") or r.get("raw") or "")[:2000],
                    (r.get("raw") or "")[:4000],
                ))
            except Exception:
                pass
    c.commit()


# ---------------------------------------------------------------------------
# Query helpers (used by routers/logs.py and AI tools)
# ---------------------------------------------------------------------------

def query_web(env: str | None = None, oprid: str | None = None,
              component: str | None = None, status: int | None = None,
              errors_only: bool = False, start: str | None = None,
              end: str | None = None, limit: int = 200) -> list[dict]:
    c = _conn()
    clauses, params = [], []
    if env:
        clauses.append("env=?"); params.append(env)
    if oprid:
        clauses.append("oprid=?"); params.append(oprid.upper())
    if component:
        clauses.append("component=?"); params.append(component.upper())
    if status:
        clauses.append("status=?"); params.append(status)
    if errors_only:
        clauses.append("is_error=1")
    if start:
        clauses.append("ts>=?"); params.append(start)
    if end:
        clauses.append("ts<=?"); params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(
        f"SELECT * FROM web_entries {where} ORDER BY ts DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    return [dict(r) for r in rows]


def query_app(env: str | None = None, oprid: str | None = None,
              object_ref: str | None = None, level: str | None = None,
              errors_only: bool = False, start: str | None = None,
              end: str | None = None, limit: int = 200) -> list[dict]:
    c = _conn()
    clauses, params = [], []
    if env:
        clauses.append("env=?"); params.append(env)
    if oprid:
        clauses.append("oprid=?"); params.append(oprid.upper())
    if object_ref:
        clauses.append("object_ref=?"); params.append(object_ref.upper())
    if level:
        clauses.append("level=?"); params.append(level.upper())
    if errors_only:
        clauses.append("is_error=1")
    if start:
        clauses.append("ts>=?"); params.append(start)
    if end:
        clauses.append("ts<=?"); params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(
        f"SELECT * FROM app_entries {where} ORDER BY ts DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    return [dict(r) for r in rows]


def query_errors(env: str | None = None, error_code: str | None = None,
                 object_ref: str | None = None, oprid: str | None = None,
                 start: str | None = None, end: str | None = None,
                 limit: int = 200) -> list[dict]:
    c = _conn()
    clauses, params = [], []
    if env:
        clauses.append("env=?"); params.append(env)
    if error_code:
        clauses.append("error_code=?"); params.append(error_code)
    if object_ref:
        clauses.append("object_ref=?"); params.append(object_ref.upper())
    if oprid:
        clauses.append("oprid=?"); params.append(oprid.upper())
    if start:
        clauses.append("ts>=?"); params.append(start)
    if end:
        clauses.append("ts<=?"); params.append(end)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(
        f"SELECT * FROM log_errors {where} ORDER BY ts DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    return [dict(r) for r in rows]


def error_summary(env: str | None = None, limit: int = 50) -> list[dict]:
    """Group errors by (error_code, object_ref) sorted by occurrence count desc."""
    c = _conn()
    clauses, params = [], []
    if env:
        clauses.append("env=?"); params.append(env)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = c.execute(f"""
        SELECT
            error_code,
            object_ref,
            env,
            COUNT(*) AS cnt,
            MIN(ts)   AS first_seen,
            MAX(ts)   AS last_seen,
            COUNT(DISTINCT oprid) AS unique_users,
            GROUP_CONCAT(DISTINCT oprid) AS oprids_sample
        FROM log_errors
        {where}
        GROUP BY error_code, object_ref, env
        ORDER BY cnt DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    return [dict(r) for r in rows]


def session_chain(oprid: str, start: str, end: str) -> dict:
    """
    Return web + app log rows for an OPRID in a time window.
    Used for session chain correlation.
    """
    web = query_web(oprid=oprid, start=start, end=end, limit=500)
    app = query_app(oprid=oprid, start=start, end=end, limit=500)
    return {"oprid": oprid, "start": start, "end": end, "web": web, "app": app}


def prune_old_entries(web_days: int = 30, app_days: int = 90, error_days: int = 90):
    """Remove rows older than the retention windows."""
    c = _conn()
    c.execute(
        "DELETE FROM web_entries WHERE ts < datetime('now', ? || ' days')",
        (f"-{web_days}",)
    )
    c.execute(
        "DELETE FROM app_entries WHERE ts < datetime('now', ? || ' days')",
        (f"-{app_days}",)
    )
    c.execute(
        "DELETE FROM log_errors WHERE ts < datetime('now', ? || ' days')",
        (f"-{error_days}",)
    )
    c.commit()
