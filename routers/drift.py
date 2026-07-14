"""
Drift API — scheduled envcompare snapshots, history, and alerts.
"""

from fastapi import APIRouter, Query, BackgroundTasks, HTTPException
from connectors import driftdb, scheduler, psdb

router = APIRouter(prefix="/api/drift", tags=["Drift"])


@router.get("/latest")
def drift_latest(
    env1: str = Query(psdb.default_env()),
    env2: str = Query(psdb.default_env2()),
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
    env1: str = Query(psdb.default_env()),
    env2: str = Query(psdb.default_env2()),
    days: int = Query(30, ge=1, le=365),
):
    """Return time-series drift data for sparkline rendering."""
    return driftdb.get_history(env1, env2, days=days)


@router.get("/alerts")
def drift_alerts(
    env1: str = Query(psdb.default_env()),
    env2: str = Query(psdb.default_env2()),
    include_resolved: bool = Query(False),
):
    """Return active drift alerts (or all including resolved)."""
    alerts = driftdb.get_alerts(env1, env2, include_resolved=include_resolved)
    return {"env1": env1, "env2": env2, "alerts": alerts}


@router.post("/snapshot")
def drift_snapshot(
    background_tasks: BackgroundTasks,
    env1: str = Query(psdb.default_env()),
    env2: str = Query(psdb.default_env2()),
):
    """Trigger an immediate drift snapshot (runs in background)."""
    background_tasks.add_task(scheduler.run_drift_now, env1, env2)
    return {"status": "triggered", "env1": env1, "env2": env2}


@router.delete("/snapshot/{snapshot_id}")
def drift_delete_snapshot(snapshot_id: int):
    """Delete a single drift snapshot by id."""
    deleted = driftdb.delete_snapshot(snapshot_id)
    if not deleted:
        raise HTTPException(404, f"No drift snapshot with id {snapshot_id}")
    return {"status": "deleted", "id": snapshot_id}
