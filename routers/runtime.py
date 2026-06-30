import json
from pathlib import Path

from fastapi import APIRouter

from connectors import execution, psdb, alerts as alerts_conn

router = APIRouter(prefix="/api/runtime", tags=["Runtime"])

CONFIG = Path("/opt/deathstar-api/config.json")


@router.get("/config")
def runtime_config():
    """Return available PeopleSoft environments and Oracle monitoring databases."""
    data = json.loads(CONFIG.read_text())
    envs = [e["name"] for e in data["peoplesoft"]["environments"]]
    dbs  = [db["name"] for db in data["oracle"]["databases"]]
    return {"envs": envs, "dbs": dbs}


@router.get("/status")
def runtime_status(env: str = "HCM", db: str = None):
    """Combined runtime snapshot: process scheduler + AE active + IB queue + Oracle sessions."""
    return execution.runtime_status(env, db_name=db or None)


@router.get("/processes")
def runtime_processes(
    env: str = "HCM",
    status: str = None,
    limit: int = 100,
):
    """
    List processes from PSPRCSRQST.

    status — comma-separated RUNSTATUS codes (e.g. '2,6,7' for active).
    Omit to return most recent regardless of status.
    """
    statuses = [s.strip() for s in status.split(",")] if status else None
    return execution.process_queue(env, statuses=statuses, limit=limit)


@router.get("/process/{instance}")
def runtime_process_detail(instance: int, env: str = "HCM"):
    """Return full detail for a single process instance."""
    return execution.process_instance(env, instance)


@router.get("/ae")
def runtime_ae(env: str = "HCM", limit: int = 50):
    """Return running/queued Application Engine processes."""
    return execution.ae_running(env, limit=limit)


@router.get("/oracle")
def runtime_oracle_sessions(db: str, limit: int = 50):
    """Return non-idle Oracle sessions with current SQL text (V$SESSION + V$SQL)."""
    return execution.oracle_active_sessions(db, limit=limit)


@router.get("/sql")
def runtime_top_sql(db: str, limit: int = 20):
    """Return top SQL statements from V$SQL ordered by cumulative elapsed time."""
    return execution.oracle_top_sql(db, limit=limit)


@router.get("/sessions")
def runtime_session_counts(db: str):
    """Return Oracle session counts grouped by status and type."""
    return execution.oracle_session_counts(db)


@router.get("/blocking")
def runtime_blocking(db: str):
    """Return blocking session chains from V$SESSION."""
    return execution.oracle_blocking(db)


@router.get("/longops")
def runtime_longops(db: str):
    """Return in-progress long-running Oracle operations from V$SESSION_LONGOPS."""
    return execution.oracle_longops(db)


@router.get("/ib")
def runtime_ib(env: str = "HCM"):
    """Return Integration Broker queue depth summary."""
    return execution.ib_queue_summary(env)


@router.get("/user-sessions")
def runtime_user_sessions(env: str = "HCM", limit: int = 50):
    """Return recent/active PeopleSoft user sessions from PSACCESSLOG."""
    return execution.user_sessions(env, limit=limit)


@router.get("/servers")
def runtime_servers(env: str = "HCM"):
    """Return Process Scheduler server status from PSSERVERSTAT."""
    return psdb.process_scheduler_servers(env)


@router.get("/alerts")
def runtime_alerts(env: str = "HCM", db: str = None):
    """Evaluate runtime alert thresholds and return active alerts."""
    return alerts_conn.evaluate_alerts(env, db_name=db or None)


@router.get("/ash")
def runtime_ash(db: str, minutes: int = 30):
    """Return Oracle ASH wait class breakdown from V$ACTIVE_SESSION_HISTORY."""
    return execution.oracle_ash_summary(db, minutes=minutes)


@router.get("/ash/sql")
def runtime_ash_sql(db: str, minutes: int = 30, limit: int = 10):
    """Return top SQL from Oracle ASH by sample count (approx. time in DB)."""
    return execution.oracle_ash_top_sql(db, minutes=minutes, limit=limit)


@router.get("/domains")
def runtime_domains(env: str = "HCM"):
    """Return App Server domain topology from PSPMDOMAIN_VW (or PS_PSPMDOMAIN1_VW fallback)."""
    return psdb.app_server_domains(env)


@router.get("/graph")
def runtime_graph(env: str = "HCM", db: str = None, process_limit: int = 30, session_limit: int = 30):
    """Return a best-effort graph of active runtime relationships."""
    return execution.runtime_graph(
        env,
        db_name=db or None,
        process_limit=process_limit,
        session_limit=session_limit,
    )
