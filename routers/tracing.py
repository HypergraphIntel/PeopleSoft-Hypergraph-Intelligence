"""
Transaction Tracing router.
All endpoints are read-only and grant-aware.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Query
from connectors import tracing, psdb
from connectors.execution import ps_env_names, oracle_db_names
from connectors import paths

router = APIRouter(prefix="/api/tracing", tags=["Transaction Tracing"])

CONFIG = paths.CONFIG_FILE


@router.get("/config")
def tracing_config():
    """Return available environments and Oracle databases."""
    return {
        "envs": ps_env_names(),
        "dbs":  oracle_db_names(),
    }


@router.get("/operators")
def search_operators(
    env: str = Query(psdb.default_env()),
    q:   str = Query(""),
):
    """Search PSOPRDEFN for matching OPRIDs (autocomplete support)."""
    return tracing.operator_search(env, q=q, limit=20)


@router.get("/active")
def active_operators(
    env: str = Query(psdb.default_env()),
    limit: int = Query(30),
):
    """Return operators with login activity in the last 24 hours."""
    return tracing.recent_active_operators(env, limit=limit)


@router.get("/trace")
def trace_operator(
    env: str = Query(psdb.default_env()),
    db:    str = Query(None, description="Oracle DB name for session correlation (optional)"),
    oprid: str = Query(..., description="PeopleSoft operator ID to trace"),
    hours: int = Query(24, description="How far back to look (hours)"),
):
    """
    Build a unified timeline for a specific OPRID across login history,
    process scheduler runs, active Oracle sessions, and IB transactions.
    """
    return tracing.trace(env, db, oprid, hours_back=hours)


@router.get("/sessions")
def operator_sessions(
    env: str = Query(psdb.default_env()),
    oprid: str = Query(...),
    hours: int = Query(24),
):
    """Return PSACCESSLOG login/logout history for an OPRID."""
    return tracing.access_history(env, oprid, hours_back=hours)


@router.get("/processes")
def operator_processes(
    env: str = Query(psdb.default_env()),
    oprid: str = Query(...),
    hours: int = Query(24),
):
    """Return PSPRCSRQST process runs submitted by an OPRID."""
    return tracing.process_history(env, oprid, hours_back=hours)


@router.get("/oracle")
def operator_oracle_sessions(
    db:    str = Query(..., description="Oracle DB name"),
    oprid: str = Query(None, description="OPRID for CLIENT_IDENTIFIER correlation"),
):
    """Return active Oracle sessions correlated to an OPRID via V$SESSION.CLIENT_IDENTIFIER."""
    return tracing.oracle_sessions_for_oprid(db, oprid=oprid)
