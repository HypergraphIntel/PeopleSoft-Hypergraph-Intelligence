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


@router.get("/process/{instance}/trace")
def runtime_process_trace(instance: int, env: str = "HCM", db: str = None):
    """AE-focused runtime trace for a single process instance: PSPRCSRQST
    detail + AE program definition (if applicable) + Oracle ASH wait events/
    top SQL correlated to the run window (if db is given) + log errors in
    that window. A narrower, buildable slice of the blocked full Runtime
    Trace Correlation item — see execution.instance_trace()'s docstring for
    what this deliberately does and doesn't claim."""
    return execution.instance_trace(env, instance, db_name=db)


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


@router.get("/ash/process")
def runtime_ash_process(db: str, env: str = "HCM", instance: int = None):
    """Return Oracle ASH activity correlated to a specific PeopleSoft process instance."""
    if not instance:
        return {"events": [], "top_sql": [], "total_samples": 0, "source": None, "warnings": []}
    return execution.oracle_ash_for_process(db, env, instance)


@router.get("/domains")
def runtime_domains(env: str = "HCM"):
    """Return App Server domain topology from PSPMDOMAIN_VW (or PS_PSPMDOMAIN1_VW fallback)."""
    return psdb.app_server_domains(env)


@router.get("/appserver-processes")
def runtime_appserver_processes(env: str = "HCM"):
    """
    Return live Tuxedo/PeopleSoft server processes (PSAPPSRV, PSAESRV, WSL,
    BBL, ...) on the app server host for this env, via SSH `ps`. This goes
    one level below the domain-level view in /domains (which only sees
    PSPMDOMAIN_VW, an Oracle view) down to actual OS processes with live
    PID/CPU/MEM/uptime.
    """
    from connectors import appsrvproc

    data = json.loads(CONFIG.read_text())
    log_sources = data.get("log_sources", [])
    candidate = next(
        (s for s in log_sources if s.get("env", "").upper() == env.upper()
         and s.get("type") in ("appsrv", "prcs_ae")),
        None,
    )
    if not candidate:
        return {
            "processes": [], "domains": [], "by_server_type": {}, "total_processes": 0,
            "warnings": [{
                "code": "no_ssh_host_configured",
                "message": f"No log_sources entry with type appsrv/prcs_ae found for env {env}",
                "severity": "warning",
            }],
        }

    result = appsrvproc.list_processes(candidate["ssh_host"])
    summary = appsrvproc.summarize(result["processes"])
    return {**summary, "processes": result["processes"], "warnings": result["warnings"]}


@router.get("/process-log")
def process_log(env: str = "HCM", instance: int = 0, limit: int = 200):
    """
    Return PRCS AE server log entries for a specific process instance.
    Queries app_entries for sources of type prcs_ae where raw contains the instance number.
    """
    if not instance:
        return {"items": [], "instance": instance, "warnings": ["No instance provided"]}
    from connectors import logdb
    logdb.init_db()
    from connectors.logdb import _conn
    c = _conn()
    pattern = f"%Process Instance={instance}%"
    rows = c.execute(
        """SELECT ts, level, object_ref AS ae_applid, message, raw
           FROM app_entries
           WHERE lower(source_name) LIKE '%prcs%'
             AND raw LIKE ?
           ORDER BY ts ASC
           LIMIT ?""",
        (pattern, limit)
    ).fetchall()
    return {
        "instance": instance,
        "env":      env,
        "items":    [dict(r) for r in rows],
    }


@router.get("/history")
def runtime_history(env: str = "HCM", hours: int = 24):
    """Return time-series runtime metric snapshots for trend charts."""
    from connectors import runtimedb
    runtimedb.init_db()
    return {"env": env, "hours": hours, "snapshots": runtimedb.get_history(env, hours=hours)}


@router.get("/history/snapshot")
def runtime_snapshot_now(env: str = "HCM"):
    """Trigger an immediate runtime snapshot (blocking)."""
    from connectors.scheduler import _run_runtime_snapshot
    _run_runtime_snapshot(env)
    return {"status": "ok", "env": env}


@router.get("/graph")
def runtime_graph(env: str = "HCM", db: str = None, process_limit: int = 30, session_limit: int = 30):
    """Return a best-effort graph of active runtime relationships."""
    return execution.runtime_graph(
        env,
        db_name=db or None,
        process_limit=process_limit,
        session_limit=session_limit,
    )


@router.get("/rca")
def runtime_rca(env: str = "HCM", start: str = "", end: str = "", db: str = None):
    """Root cause analysis: correlate process failures, log errors, ASH, and IB errors."""
    import datetime as _dt
    if not end:
        end = _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if not start:
        start = (_dt.datetime.utcnow() - _dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    return execution.rca_snapshot(env, start, end, db_name=db or None)


@router.get("/plugins")
def runtime_plugins_list():
    """List registered plugin runtime providers (Phase 9 Plugin SDK)."""
    from connectors import plugins
    return {"providers": [
        {"name": name, "label": meta["label"]}
        for name, meta in plugins.get_runtime_providers().items()
    ]}


@router.get("/plugins/{name}")
def runtime_plugin_status(name: str, env: str = "HCM"):
    """Return live status from a registered plugin runtime provider."""
    from connectors import plugins
    provider = plugins.get_runtime_providers().get(name)
    if not provider:
        from fastapi import HTTPException
        raise HTTPException(404, f"No runtime provider registered as '{name}'")
    return provider["fetch_fn"](env)


@router.get("/health-checks")
def runtime_health_checks(env: str = "HCM"):
    """Run every registered plugin health check and return their results.

    Each check is executed on demand (not polled/cached) — a broken check
    (raises an exception) is reported as its own 'error' result rather than
    failing the whole endpoint, same isolation philosophy as plugin loading
    itself (connectors/pluginloader.py)."""
    from connectors import plugins
    results = []
    for name, meta in plugins.get_health_checks().items():
        try:
            outcome = meta["check_fn"](env)
        except Exception as exc:
            outcome = {"status": "error", "message": f"Health check raised: {exc}"}
        results.append({
            "name": name,
            "label": meta["label"],
            "status": outcome.get("status", "unknown"),
            "message": outcome.get("message", ""),
            **{k: v for k, v in outcome.items() if k not in ("status", "message")},
        })
    return {"checks": results}
