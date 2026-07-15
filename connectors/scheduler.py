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

from connectors import driftdb, graphdb, psdb

logger = logging.getLogger("deathstar.scheduler")


def _default_envs() -> list[str]:
    try:
        return [e["name"] for e in psdb.load_envs()]
    except Exception:
        return ["HCM"]


def _default_drift_pairs() -> list[tuple]:
    """Consecutive pairs from the configured environment list (e.g.
    [(env[0], env[1]), (env[1], env[2]), ...]) — a reasonable default so
    every configured environment is covered by at least one scheduled
    drift comparison, without guessing at a specific lifecycle ordering."""
    envs = _default_envs()
    if len(envs) < 2:
        return []
    return [(envs[i], envs[i + 1]) for i in range(len(envs) - 1)]


def _default_promotion_chains() -> dict:
    """pillar -> ordered [upstream..downstream] env list, from config.json's
    promotion_chains section. Empty dict (no scheduled detection) if unset."""
    try:
        import json
        from connectors import paths
        with open(paths.CONFIG_FILE) as f:
            cfg = json.load(f)
        return {k: v for k, v in cfg.get("promotion_chains", {}).items() if k != "_comment"}
    except Exception:
        return {}


# Configuration — values can be overridden before calling start().
ENVS: list[str] = _default_envs()
DRIFT_ENV_PAIRS: list[tuple] = _default_drift_pairs()   # env pairs for drift comparison
PROMOTION_CHAINS: dict = _default_promotion_chains()    # pillar -> ordered env chain
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

# Runtime history thread
RUNTIME_SNAPSHOT_INTERVAL_SECONDS: int = 300   # every 5 minutes
_rt_thread: threading.Thread | None = None
_rt_stop_event = threading.Event()
_last_rt_run: str = ""
_last_rt_error: str = ""

# Promotion auto-detection thread
PROMOTION_CHECK_INTERVAL_SECONDS: int = 900   # every 15 minutes
_promo_thread: threading.Thread | None = None
_promo_stop_event = threading.Event()
_last_promo_run: str = ""
_last_promo_error: str = ""
_last_promo_detected: int = 0


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


def _run_runtime_snapshot(env: str) -> None:
    """Capture a lightweight runtime metrics snapshot for history tracking."""
    try:
        from connectors import runtimedb
        from connectors.execution import process_status_summary, ib_queue_summary, ae_running
        from connectors import alerts as alerts_conn

        ps  = process_status_summary(env)
        tot = ps.get("totals", {})

        ib  = ib_queue_summary(env)
        ib_rows = ib.get("ib", {})
        ib_pending = sum(
            r.get("cnt", 0)
            for rows in ib_rows.values()
            for r in rows
            if r.get("pubstatus", r.get("subconstatus", 4)) not in (4,)  # exclude Cancelled
        )

        ae = ae_running(env, limit=1)
        ae_cnt = ae.get("count", 0) if isinstance(ae, dict) else 0

        alrt = alerts_conn.evaluate_alerts(env, db_name=None)
        alert_cnt = alrt.get("alert_count", 0)

        data = {
            "process_active": tot.get("active", 0),
            "process_error":  tot.get("error",  0),
            "process_total":  tot.get("total",  0),
            "ae_running":     ae_cnt,
            "ib_pending":     ib_pending,
            "alert_count":    alert_cnt,
        }
        runtimedb.record(env, data)
        runtimedb.prune(env)
    except Exception as exc:
        raise exc


def _runtime_snapshot_loop() -> None:
    global _last_rt_run, _last_rt_error
    logger.info("Runtime snapshot scheduler started (interval=%ds)", RUNTIME_SNAPSHOT_INTERVAL_SECONDS)
    while not _rt_stop_event.is_set():
        for env in ENVS:
            if _rt_stop_event.is_set():
                break
            try:
                _run_runtime_snapshot(env)
                _last_rt_run = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                _last_rt_error = ""
            except Exception as exc:
                _last_rt_error = str(exc)
                logger.warning("Runtime snapshot error for %s: %s", env, exc)
        _rt_stop_event.wait(RUNTIME_SNAPSHOT_INTERVAL_SECONDS)
    logger.info("Runtime snapshot scheduler stopped")


def _run_promotion_check(pillar: str, chain: list) -> None:
    global _last_promo_detected
    from connectors import promotiondb
    result = promotiondb.detect_promotions(pillar, chain)
    _last_promo_detected += len(result.get("detected", []))
    if result.get("detected"):
        logger.info("Scheduler: promotion auto-detect %s found %d new promotion(s)",
                    pillar, len(result["detected"]))


def _promotion_loop() -> None:
    global _last_promo_run, _last_promo_error
    logger.info("Promotion auto-detect scheduler started (chains=%s, interval=%ds)",
                PROMOTION_CHAINS, PROMOTION_CHECK_INTERVAL_SECONDS)
    while not _promo_stop_event.is_set():
        for pillar, chain in PROMOTION_CHAINS.items():
            if _promo_stop_event.is_set():
                break
            try:
                _run_promotion_check(pillar, chain)
                _last_promo_run = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                _last_promo_error = ""
            except Exception as exc:
                _last_promo_error = str(exc)
                logger.warning("Promotion auto-detect error for %s: %s", pillar, exc)
        _promo_stop_event.wait(PROMOTION_CHECK_INTERVAL_SECONDS)
    logger.info("Promotion auto-detect scheduler stopped")


def start() -> None:
    global _thread, _log_thread, _rt_thread, _promo_thread
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

    if _rt_thread and _rt_thread.is_alive():
        logger.debug("Runtime snapshot scheduler already running")
    else:
        _rt_stop_event.clear()
        _rt_thread = threading.Thread(target=_runtime_snapshot_loop, name="runtime-snapshot", daemon=True)
        _rt_thread.start()
        logger.info("Runtime snapshot scheduler thread started")

    if not PROMOTION_CHAINS:
        logger.debug("No promotion_chains configured — promotion auto-detect thread not started")
    elif _promo_thread and _promo_thread.is_alive():
        logger.debug("Promotion auto-detect scheduler already running")
    else:
        _promo_stop_event.clear()
        _promo_thread = threading.Thread(target=_promotion_loop, name="promotion-detect", daemon=True)
        _promo_thread.start()
        logger.info("Promotion auto-detect scheduler thread started")


def stop() -> None:
    _stop_event.set()
    _log_stop_event.set()
    _rt_stop_event.set()
    _promo_stop_event.set()
    if _thread:
        _thread.join(timeout=5)
    if _log_thread:
        _log_thread.join(timeout=5)
    if _rt_thread:
        _rt_thread.join(timeout=5)
    if _promo_thread:
        _promo_thread.join(timeout=5)
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
        "last_log_ingest":    _last_log_ingest,
        "last_log_error":     _last_log_error,
        "runtime_snapshot_running": bool(_rt_thread and _rt_thread.is_alive()),
        "last_rt_run":        _last_rt_run,
        "last_rt_error":      _last_rt_error,
        "promotion_chains":         PROMOTION_CHAINS,
        "promotion_detect_running": bool(_promo_thread and _promo_thread.is_alive()),
        "last_promo_run":           _last_promo_run,
        "last_promo_error":         _last_promo_error,
        "last_promo_detected_total": _last_promo_detected,
    }


def run_drift_now(env1: str, env2: str) -> dict:
    """Trigger an immediate drift snapshot (blocking, for manual use)."""
    _run_drift(env1, env2)
    key = f"{env1}/{env2}"
    return {
        "last_run": _last_drift_run.get(key),
        "last_error": _last_drift_error.get(key),
    }
