"""
REST API for log intelligence data.

GET /api/logs/sources         — list all log sources with status
GET /api/logs/web             — query web access entries
GET /api/logs/app             — query app server entries
GET /api/logs/errors          — list/group errors
GET /api/logs/session/{oprid} — full session chain for an OPRID
POST /api/logs/ingest         — trigger immediate ingest (admin)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/logs", tags=["Logs"])


def _db():
    from connectors import logdb
    logdb.init_db()
    return logdb


@router.get("/sources")
def log_sources():
    db = _db()
    return db.get_sources(enabled_only=False)


@router.get("/web")
def query_web(
    env:        Optional[str] = Query(None),
    oprid:      Optional[str] = Query(None),
    component:  Optional[str] = Query(None),
    status:     Optional[int] = Query(None),
    errors_only: bool         = Query(False),
    start:      Optional[str] = Query(None, description="ISO datetime"),
    end:        Optional[str] = Query(None, description="ISO datetime"),
    limit:      int           = Query(200, le=2000),
):
    db = _db()
    return db.query_web(
        env=env, oprid=oprid, component=component, status=status,
        errors_only=errors_only, start=start, end=end, limit=limit,
    )


@router.get("/app")
def query_app(
    env:        Optional[str] = Query(None),
    oprid:      Optional[str] = Query(None),
    object_ref: Optional[str] = Query(None),
    level:      Optional[str] = Query(None),
    errors_only: bool         = Query(False),
    start:      Optional[str] = Query(None),
    end:        Optional[str] = Query(None),
    limit:      int           = Query(200, le=2000),
):
    db = _db()
    return db.query_app(
        env=env, oprid=oprid, object_ref=object_ref, level=level,
        errors_only=errors_only, start=start, end=end, limit=limit,
    )


@router.get("/errors")
def query_errors(
    env:        Optional[str] = Query(None),
    error_code: Optional[str] = Query(None),
    object_ref: Optional[str] = Query(None),
    oprid:      Optional[str] = Query(None),
    summary:    bool          = Query(False, description="Group by error_code+object_ref"),
    start:      Optional[str] = Query(None),
    end:        Optional[str] = Query(None),
    limit:      int           = Query(100, le=1000),
):
    db = _db()
    if summary:
        return db.error_summary(env=env, limit=limit)
    return db.query_errors(
        env=env, error_code=error_code, object_ref=object_ref,
        oprid=oprid, start=start, end=end, limit=limit,
    )


@router.get("/session/{oprid}")
def session_chain(
    oprid: str,
    start: Optional[str] = Query(None),
    end:   Optional[str] = Query(None),
):
    db = _db()
    if not start:
        from datetime import datetime, timedelta
        start = (datetime.utcnow() - timedelta(hours=8)).isoformat(timespec="seconds")
    if not end:
        from datetime import datetime
        end = datetime.utcnow().isoformat(timespec="seconds")
    return db.session_chain(oprid.upper(), start, end)


@router.post("/ingest")
def trigger_ingest():
    """Trigger an immediate log ingest cycle (non-blocking — spawns in background)."""
    import threading
    from connectors.logingest import run_ingest

    t = threading.Thread(target=run_ingest, daemon=True, name="log-ingest-manual")
    t.start()
    return {"status": "ingest started", "thread": t.name}


@router.post("/re-extract")
def re_extract():
    """Re-run extraction on existing log_errors rows with null error_code/object_ref."""
    db = _db()
    return db.re_extract_errors(limit=10000)


@router.get("/igw-summary")
def igw_summary(env: Optional[str] = Query(None)):
    """Aggregate IGW error log data: by error code, IB operation, requesting node."""
    db = _db()
    return db.igw_summary(env=env)


@router.get("/prcs-ae-summary")
def prcs_ae_summary(env: Optional[str] = Query(None)):
    """Aggregate PRCS AE server log data: by program, with recent error detail."""
    db = _db()
    return db.prcs_ae_summary(env=env)


@router.post("/search")
def search_logs(
    q:     str           = Query(..., description="Text to search in messages/URLs"),
    env:   Optional[str] = Query(None),
    tier:  str           = Query("both", description="web | app | both"),
    limit: int           = Query(100, le=500),
):
    """Full-text search across web and app log messages."""
    db = _db()
    from connectors.logdb import _conn
    c = _conn()
    results: dict = {}

    like = f"%{q}%"

    if tier in ("web", "both"):
        clauses = ["(url LIKE ? OR raw LIKE ?)"]
        params  = [like, like]
        if env:
            clauses.append("env=?"); params.append(env)
        rows = c.execute(
            f"SELECT * FROM web_entries WHERE {' AND '.join(clauses)} ORDER BY ts DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        results["web"] = [dict(r) for r in rows]

    if tier in ("app", "both"):
        clauses = ["(message LIKE ? OR raw LIKE ?)"]
        params  = [like, like]
        if env:
            clauses.append("env=?"); params.append(env)
        rows = c.execute(
            f"SELECT * FROM app_entries WHERE {' AND '.join(clauses)} ORDER BY ts DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        results["app"] = [dict(r) for r in rows]

    return results
