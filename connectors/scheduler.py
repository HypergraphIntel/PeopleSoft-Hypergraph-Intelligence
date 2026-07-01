"""
Background scheduler for periodic graph snapshots, drift comparison,
and log ingestion.

Threads
-------
snapshot-scheduler  — builds knowledge-graph snapshots daily (INTERVAL_HOURS)
log-ingest          — ingests new log bytes from all enabled sources every 60s

No external dependencies — pure threading.
"""

import logging
import threading
import time

from connectors import driftdb, graphdb

logger = logging.getLogger("deathstar.scheduler")

# Configuration — values can be overridden before calling start().
ENVS: list[str] = ["HCM"]
DRIFT_ENV_PAIRS: list[tuple] = [("HCM", "FSCM")]   # env pairs for drift comparison
INTERVAL_HOURS: int = 24
RETAIN_COUNT: int = 7
DRIFT_RETAIN_DAYS: int = 90
INITIAL_DELAY_SECONDS: int = 300   # 5-minute startup grace period
BUILD_LIMIT: int = 100

_thread: threading.Thread | None = None
_stop_event = threading.Event()
_last_run: dict = {}    # env → ISO timestamp of last successful graph snapshot
_last_error: dict = {}  # env → last error string
_last_drift_run: dict = {}   # "env1/env2" → ISO timestamp
_last_drift_error: dict = {} # "env1/env2" → last error

# Log ingest thread
LOG_INGEST_INTERVAL_SECONDS: int = 60
_log_thread: threading.Thread | None = None
_log_stop_event = threading.Event()
_last_log_ingest: str = ""
_last_log_error: str = ""


def _run_for_env(env: str) -> None:
    try:
        logger.info("Scheduler: building graph for %s", env)
        graphdb.build(env, limit=BUILD_LIMIT)
        entry = graphdb.create_snapshot(
            env,
            name="scheduled",
            note=f"Auto-snapshot (daily scheduler) — {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        )
        graphdb.prune_snapshots(env, keep=RETAIN_COUNT)
        _last_run[env] = entry.get("created_at", "")
        _last_error.pop(env, None)
        logger.info("Scheduler: snapshot complete for %s (id=%s, nodes=%s, edges=%s)",
                    env, entry.get("id"), entry.get("node_count"), entry.get("edge_count"))
    except Exception as exc:
        _last_error[env] = str(exc)
        logger.warning("Scheduler: snapshot failed for %s: %s", env, exc)


def _run_drift(env1: str, env2: str) -> None:
    key = f"{env1}/{env2}"
    try:
        from connectors import envcompare
        logger.info("Scheduler: running drift comparison %s vs %s", env1, env2)
        result = envcompare.summary(env1, env2)
        counts = result.get("counts", [])
        info = driftdb.record_summary(env1, env2, counts)
        driftdb.prune(env1, env2, keep=DRIFT_RETAIN_DAYS)
        _last_drift_run[key] = info.get("snapped_at", "")
        _last_drift_error.pop(key, None)
        logger.info("Scheduler: drift snapshot %s (id=%s, alerts=%s)",
                    key, info.get("snapshot_id"), info.get("alerts_created"))
    except Exception as exc:
        _last_drift_error[key] = str(exc)
        logger.warning("Scheduler: drift comparison failed %s: %s", key, exc)


def _loop() -> None:
    logger.info("Snapshot scheduler started (envs=%s, drift_pairs=%s, interval=%dh, retain=%d, initial_delay=%ds)",
                ENVS, DRIFT_ENV_PAIRS, INTERVAL_HOURS, RETAIN_COUNT, INITIAL_DELAY_SECONDS)
    # Initial delay
    if _stop_event.wait(INITIAL_DELAY_SECONDS):
        return  # stopped before first run
    while not _stop_event.is_set():
        for env in ENVS:
            if _stop_event.is_set():
                break
            _run_for_env(env)
        for env1, env2 in DRIFT_ENV_PAIRS:
            if _stop_event.is_set():
                break
            _run_drift(env1, env2)
        _stop_event.wait(INTERVAL_HOURS * 3600)
    logger.info("Snapshot scheduler stopped")


def _log_ingest_loop() -> None:
    global _last_log_ingest, _last_log_error
    logger.info("Log ingest scheduler started (interval=%ds)", LOG_INGEST_INTERVAL_SECONDS)
    while not _log_stop_event.is_set():
        try:
            from connectors.logingest import run_ingest
            run_ingest()
            _last_log_ingest = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _last_log_error = ""
        except Exception as exc:
            _last_log_error = str(exc)
            logger.warning("Log ingest error: %s", exc)
        _log_stop_event.wait(LOG_INGEST_INTERVAL_SECONDS)
    logger.info("Log ingest scheduler stopped")


def start() -> None:
    global _thread, _log_thread
    if _thread and _thread.is_alive():
        logger.debug("Scheduler already running")
    else:
        _stop_event.clear()
        _thread = threading.Thread(target=_loop, name="snapshot-scheduler", daemon=True)
        _thread.start()
        logger.info("Snapshot scheduler thread started")

    if _log_thread and _log_thread.is_alive():
        logger.debug("Log ingest scheduler already running")
    else:
        _log_stop_event.clear()
        _log_thread = threading.Thread(target=_log_ingest_loop, name="log-ingest", daemon=True)
        _log_thread.start()
        logger.info("Log ingest scheduler thread started")


def stop() -> None:
    _stop_event.set()
    _log_stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    if _log_thread:
        _log_thread.join(timeout=5)
    logger.info("All scheduler threads stopped")


def status() -> dict:
    return {
        "running": bool(_thread and _thread.is_alive()),
        "log_ingest_running": bool(_log_thread and _log_thread.is_alive()),
        "envs": ENVS,
        "drift_env_pairs": DRIFT_ENV_PAIRS,
        "interval_hours": INTERVAL_HOURS,
        "retain_count": RETAIN_COUNT,
        "drift_retain_days": DRIFT_RETAIN_DAYS,
        "initial_delay_seconds": INITIAL_DELAY_SECONDS,
        "build_limit": BUILD_LIMIT,
        "last_run": _last_run,
        "last_error": _last_error,
        "last_drift_run": _last_drift_run,
        "last_drift_error": _last_drift_error,
        "last_log_ingest": _last_log_ingest,
        "last_log_error": _last_log_error,
    }


def run_drift_now(env1: str, env2: str) -> dict:
    """Trigger an immediate drift snapshot (blocking, for manual use)."""
    _run_drift(env1, env2)
    key = f"{env1}/{env2}"
    return {
        "last_run": _last_drift_run.get(key),
        "last_error": _last_drift_error.get(key),
    }
