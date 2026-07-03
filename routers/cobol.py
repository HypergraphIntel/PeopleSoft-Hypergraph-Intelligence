"""
PeopleSoft COBOL Source Artifact Intelligence API.

Endpoints:
  GET  /api/cobol/stats
  GET  /api/cobol/sources?env=HCM
  GET  /api/cobol/programs?q=&type=program|copybook&env=HCM&page=1&per_page=50
  GET  /api/cobol/program/{filename}
  GET  /api/cobol/program/{filename}/source
  GET  /api/cobol/table/{table_name}
  GET  /api/cobol/deps/{filename}
  GET  /api/cobol/search
  GET  /api/cobol/search/status
  POST /api/cobol/ingest
  GET  /api/cobol/ingest/status
"""

import threading
import time

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/api/cobol", tags=["COBOL"])

_last_ingest: dict = {}
_ingest_lock = threading.Lock()
_ingest_running = False


def _run_ingest():
    global _last_ingest, _ingest_running
    from connectors import cobolingest, cobol_db
    cobol_db.init_db()
    try:
        results = cobolingest.index_all()
        _last_ingest = {
            "status": "ok", "results": results,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as exc:
        _last_ingest = {
            "status": "error", "error": str(exc),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    finally:
        _ingest_running = False


@router.get("/stats")
def cobol_stats():
    from connectors import cobol_db
    cobol_db.init_db()
    return cobol_db.stats()


@router.get("/sources")
def cobol_sources_list(env: Optional[str] = Query(None)):
    import json
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)
    all_sources = cfg.get("cobol_sources", [])
    envs = sorted({s["env"] for s in all_sources if s.get("env")})
    if env:
        sources = [s for s in all_sources if s.get("env", "").upper() == env.upper()]
    else:
        sources = all_sources
    return {"envs": envs, "sources": sources}


@router.get("/programs")
def cobol_programs(
    q:        Optional[str] = Query(None),
    type:     Optional[str] = Query(None, alias="type"),
    env:      Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    import json
    from pathlib import Path
    from connectors import cobol_db
    cobol_db.init_db()

    source_keys: list[str] | None = None
    if env:
        cfg_path = Path(__file__).parent.parent / "config.json"
        with open(cfg_path) as f:
            cfg = json.load(f)
        source_keys = list({
            s["key"] for s in cfg.get("cobol_sources", [])
            if s.get("env", "").upper() == env.upper()
        })

    return cobol_db.search_programs(
        q=q or "", file_type=type or "", source_keys=source_keys,
        page=page, per_page=per_page,
    )


@router.get("/program/{filename}")
def cobol_program(filename: str):
    from connectors import cobol_db
    cobol_db.init_db()
    prog = cobol_db.get_program(filename)
    if not prog:
        raise HTTPException(404, f"Program '{filename}' not found in index")
    return prog


@router.get("/table/{table_name}")
def cobol_table_users(table_name: str):
    from connectors import cobol_db
    cobol_db.init_db()
    return {"table_name": table_name.upper(), "programs": cobol_db.get_programs_for_table(table_name)}


@router.post("/ingest")
def cobol_ingest_trigger():
    global _ingest_running
    with _ingest_lock:
        if _ingest_running:
            return {"status": "already_running"}
        _ingest_running = True
    t = threading.Thread(target=_run_ingest, daemon=True, name="cobol-ingest")
    t.start()
    return {"status": "started"}


@router.get("/ingest/status")
def cobol_ingest_status():
    return {"running": _ingest_running, "last": _last_ingest}


@router.get("/search")
def cobol_search(q: str = Query(""), type: str = Query(None), source_key: str = Query(None),
                  limit: int = Query(50, ge=1, le=200)):
    from connectors import cobol_db
    cobol_db.init_db()
    return cobol_db.search_source(q.strip(), file_type=type or None, source_key=source_key or None, limit=limit)


@router.get("/search/status")
def cobol_search_status():
    from connectors import cobol_db
    cobol_db.init_db()
    return cobol_db.source_index_status()


@router.get("/program/{filename}/source")
def cobol_source(filename: str, max_kb: int = Query(256, ge=1, le=512)):
    """Return raw source content for a program (fetched live from SSH)."""
    import json
    from pathlib import Path
    from connectors import cobol_db, sshclient

    cobol_db.init_db()
    prog = cobol_db.get_program(filename)
    if not prog:
        raise HTTPException(404, f"Program '{filename}' not found in index")

    source_key = prog.get("source_key")
    if not source_key:
        raise HTTPException(503, "No source_key on this program — re-index required")

    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)

    source = next((s for s in cfg.get("cobol_sources", []) if s["key"] == source_key), None)
    if not source:
        raise HTTPException(503, f"Source '{source_key}' not in config.json cobol_sources")

    src_dir  = source["cbl_src_dir"].rstrip("/")
    ssh_host = source["ssh_host"]
    path     = f"{src_dir}/{filename}"

    try:
        raw = sshclient.read_bytes(ssh_host, path, max_bytes=max_kb * 1024)
        content = raw.decode("utf-8", errors="replace")
    except FileNotFoundError:
        raise HTTPException(404, f"File not found on {ssh_host}: {path}")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))

    return {
        "filename": filename, "source": content, "size": len(raw),
        "truncated": len(raw) >= max_kb * 1024,
    }


@router.get("/deps/{filename}")
def cobol_deps(filename: str, max_depth: int = Query(6, ge=1, le=10)):
    """Return full COPY dependency information for a program (forward + reverse closure)."""
    from connectors import cobol_db
    cobol_db.init_db()
    return cobol_db.get_copy_deps(filename, max_depth=max_depth)


@router.get("/envcompare")
def cobol_envcompare(env_a: str = Query("HCM"), env_b: str = Query("FSCM")):
    """Return side-by-side comparison of COBOL programs/copybooks across two environments."""
    import json
    from pathlib import Path
    from connectors import cobol_db
    cobol_db.init_db()

    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)

    all_sources = cfg.get("cobol_sources", [])
    keys_a = [s["key"] for s in all_sources if s.get("env", "").upper() == env_a.upper()]
    keys_b = [s["key"] for s in all_sources if s.get("env", "").upper() == env_b.upper()]

    return cobol_db.envcompare_cobol(keys_a, keys_b, label_a=env_a.upper(), label_b=env_b.upper())
