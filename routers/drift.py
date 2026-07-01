"""
Drift API — scheduled envcompare snapshots, history, and alerts.
"""

from fastapi import APIRouter, Query, BackgroundTasks
from connectors import driftdb, scheduler

router = APIRouter(prefix="/api/drift", tags=["Drift"])


@router.get("/latest")
def drift_latest(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
):
    """Return counts from the most recent drift snapshot for this env pair."""
    counts = driftdb.get_latest(env1, env2)
    return {
        "env1": env1, "env2": env2,
        "counts": counts,
        "snapshot_count": driftdb.snapshot_count(env1, env2),
    }


@router.get("/history")
def drift_history(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
    days: int = Query(30, ge=1, le=365),
):
    """Return time-series drift data for sparkline rendering."""
    return driftdb.get_history(env1, env2, days=days)


@router.get("/alerts")
def drift_alerts(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
    include_resolved: bool = Query(False),
):
    """Return active drift alerts (or all including resolved)."""
    alerts = driftdb.get_alerts(env1, env2, include_resolved=include_resolved)
    return {"env1": env1, "env2": env2, "alerts": alerts}


@router.post("/snapshot")
def drift_snapshot(
    background_tasks: BackgroundTasks,
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
):
    """Trigger an immediate drift snapshot (runs in background)."""
    background_tasks.add_task(scheduler.run_drift_now, env1, env2)
    return {"status": "triggered", "env1": env1, "env2": env2}
