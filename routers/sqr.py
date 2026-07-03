"""
SQR Source Artifact Intelligence API.

Endpoints:
  GET  /api/sqr/stats
  GET  /api/sqr/sources?env=HCM          — list sqr_sources from config (env-filtered)
  GET  /api/sqr/programs?q=&type=sqr|sqc&env=HCM&page=1&per_page=50
  GET  /api/sqr/program/{filename}
  GET  /api/sqr/table/{table_name}
  GET  /api/sqr/sqc/{sqc_name}/users
  POST /api/sqr/ingest          — trigger full reindex (background thread)
  GET  /api/sqr/ingest/status   — last ingest result
"""

import threading
import time

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/api/sqr", tags=["SQR"])

# track last ingest result
_last_ingest: dict = {}
_ingest_lock = threading.Lock()
_ingest_running = False


def _run_ingest():
    global _last_ingest, _ingest_running
    from connectors import sqringest, sqrdb
    sqrdb.init_db()
    try:
        results = sqringest.index_all()
        _last_ingest = {
            "status": "ok",
            "results": results,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as exc:
        _last_ingest = {
            "status": "error",
            "error": str(exc),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    finally:
        _ingest_running = False


@router.get("/stats")
def sqr_stats():
    from connectors import sqrdb
    sqrdb.init_db()
    return sqrdb.stats()


@router.get("/sources")
def sqr_sources_list(env: Optional[str] = Query(None)):
    """Return sqr_sources from config.json, optionally filtered by env.

    Also returns the list of unique environment names so the UI can build
    its env selector in one request.
    """
    import json
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)
    all_sources = cfg.get("sqr_sources", [])
    envs = sorted({s["env"] for s in all_sources if s.get("env")})
    if env:
        sources = [s for s in all_sources if s.get("env", "").upper() == env.upper()]
    else:
        sources = all_sources
    return {"envs": envs, "sources": sources}


@router.get("/overrides")
def sqr_overrides(env: Optional[str] = Query(None)):
    """Return filenames that exist in BOTH delivered and custom sources.

    These are customised overrides of delivered SQR programs.
    Filter by env to scope to a specific environment.
    """
    import json
    from pathlib import Path
    from connectors import sqrdb
    sqrdb.init_db()

    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)

    all_sources = cfg.get("sqr_sources", [])
    if env:
        all_sources = [s for s in all_sources if s.get("env", "").upper() == env.upper()]

    # Build {env: {delivered: [keys], custom: [keys]}} map
    env_source_keys: dict = {}
    for s in all_sources:
        e = s.get("env", "UNKNOWN")
        st = s.get("source_type", "")
        if st not in ("delivered", "custom"):
            continue
        env_source_keys.setdefault(e, {"delivered": [], "custom": []})
        env_source_keys[e][st].append(s["key"])

    results = sqrdb.overrides(env_source_keys)
    return {"overrides": results, "count": len(results)}


@router.get("/analytics")
def sqr_analytics():
    from connectors import sqrdb
    sqrdb.init_db()
    return sqrdb.analytics()


@router.get("/programs")
def sqr_programs(
    q:        Optional[str] = Query(None),
    type:     Optional[str] = Query(None, alias="type"),
    env:      Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    import json
    from pathlib import Path
    from connectors import sqrdb
    sqrdb.init_db()

    source_keys: list[str] | None = None
    if env:
        cfg_path = Path(__file__).parent.parent / "config.json"
        with open(cfg_path) as f:
            cfg = json.load(f)
        source_keys = list({
            s["key"] for s in cfg.get("sqr_sources", [])
            if s.get("env", "").upper() == env.upper()
        })

    return sqrdb.search_programs(
        q=q or "",
        file_type=type or "",
        source_keys=source_keys,
        page=page,
        per_page=per_page,
    )


@router.get("/program/{filename}")
def sqr_program(filename: str):
    from connectors import sqrdb
    sqrdb.init_db()
    prog = sqrdb.get_program(filename)
    if not prog:
        raise HTTPException(404, f"Program '{filename}' not found in index")
    return prog


@router.get("/table/{table_name}")
def sqr_table_users(table_name: str):
    from connectors import sqrdb
    sqrdb.init_db()
    return {
        "table_name": table_name.upper(),
        "programs":   sqrdb.get_programs_for_table(table_name),
    }


@router.get("/sqc/{sqc_name}/users")
def sqc_users(sqc_name: str):
    from connectors import sqrdb
    sqrdb.init_db()
    return {
        "sqc_name": sqc_name,
        "programs": sqrdb.get_includes_for_sqc(sqc_name),
    }


@router.post("/ingest")
def sqr_ingest_trigger():
    global _ingest_running
    with _ingest_lock:
        if _ingest_running:
            return {"status": "already_running"}
        _ingest_running = True
    t = threading.Thread(target=_run_ingest, daemon=True, name="sqr-ingest")
    t.start()
    return {"status": "started"}


@router.get("/ingest/status")
def sqr_ingest_status():
    return {
        "running": _ingest_running,
        "last":    _last_ingest,
    }


@router.get("/search")
def sqr_search(q: str = Query(""), type: str = Query(None), source_key: str = Query(None),
               limit: int = Query(50, ge=1, le=200)):
    """Full-text search within indexed SQR/SQC source code."""
    from connectors import sqrdb
    sqrdb.init_db()
    return sqrdb.search_source(q.strip(), file_type=type or None,
                               source_key=source_key or None, limit=limit)


@router.get("/search/status")
def sqr_search_status():
    """Return how many programs have source_text indexed for search."""
    from connectors import sqrdb
    sqrdb.init_db()
    return sqrdb.source_index_status()


@router.get("/program/{filename}/tree")
def sqr_include_tree(filename: str):
    """Return recursive SQC include tree for a program."""
    from connectors import sqrdb
    sqrdb.init_db()
    return sqrdb.get_include_tree(filename)


@router.get("/program/{filename}/source")
def sqr_source(filename: str, max_kb: int = Query(128, ge=1, le=512)):
    """Return raw source content for a program (fetched live from SSH)."""
    import json
    from pathlib import Path
    from connectors import sqrdb, sshclient

    sqrdb.init_db()
    prog = sqrdb.get_program(filename)
    if not prog:
        raise HTTPException(404, f"Program '{filename}' not found in index")

    source_key = prog.get("source_key")
    if not source_key:
        raise HTTPException(503, "No source_key on this program — re-index required")

    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)

    source = next((s for s in cfg.get("sqr_sources", []) if s["key"] == source_key), None)
    if not source:
        raise HTTPException(503, f"Source '{source_key}' not in config.json sqr_sources")

    sqr_dir  = source["sqr_dir"].rstrip("/")
    ssh_host = source["ssh_host"]
    path     = f"{sqr_dir}/{filename}"

    try:
        raw = sshclient.read_bytes(ssh_host, path, max_bytes=max_kb * 1024)
        content = raw.decode("utf-8", errors="replace")
    except FileNotFoundError:
        raise HTTPException(404, f"File not found on {ssh_host}: {path}")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))

    return {
        "filename": filename,
        "source":   content,
        "size":     len(raw),
        "truncated": len(raw) >= max_kb * 1024,
    }
