"""
Plugin SDK — config-driven source types (Phase 9 v2).

Generic API surface over connectors/plugins.py's source-type registry, so a
plugin that registers a source type (via sdk.register_source_type()) gets
GET /list, POST /ingest, and GET /status for free, mirroring the SQR/COBOL
ingest pattern without needing to write its own threading/routing.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from connectors import paths

router = APIRouter(prefix="/api/plugins/sources", tags=["Plugin Sources"])


@router.get("")
def list_source_types():
    """List registered source types and their config.json entries."""
    from connectors import plugins

    cfg_path = paths.CONFIG_FILE
    with open(cfg_path) as f:
        cfg = json.load(f)

    result = []
    for name, entry in plugins.get_source_types().items():
        sources = cfg.get(entry["config_key"], [])
        result.append({
            "name": name,
            "label": entry["label"],
            "config_key": entry["config_key"],
            "source_count": len(sources),
            "running": entry["running"],
        })
    return {"source_types": result}


@router.get("/{name}/entries")
def source_type_entries(name: str, env: Optional[str] = Query(None)):
    """Return this source type's raw config.json entries, optionally env-filtered."""
    from connectors import plugins

    entry = plugins.get_source_types().get(name)
    if not entry:
        raise HTTPException(404, f"No source type registered as '{name}'")

    cfg_path = paths.CONFIG_FILE
    with open(cfg_path) as f:
        cfg = json.load(f)

    sources = cfg.get(entry["config_key"], [])
    if env:
        sources = [s for s in sources if s.get("env", "").upper() == env.upper()]
    envs = sorted({s["env"] for s in cfg.get(entry["config_key"], []) if s.get("env")})
    return {"envs": envs, "sources": sources}


@router.post("/{name}/ingest")
def trigger_source_ingest(name: str):
    """Trigger a background reindex for a registered source type."""
    from connectors import plugins

    if name not in plugins.get_source_types():
        raise HTTPException(404, f"No source type registered as '{name}'")
    return plugins.trigger_source_ingest(name)


@router.get("/{name}/status")
def source_ingest_status(name: str):
    """Return the last ingest result (or a plugin-provided live status) for a source type."""
    from connectors import plugins

    if name not in plugins.get_source_types():
        raise HTTPException(404, f"No source type registered as '{name}'")
    return plugins.get_source_type_status(name)
