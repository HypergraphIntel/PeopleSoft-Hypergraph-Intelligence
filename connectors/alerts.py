"""
Runtime alert evaluation for the DeathStar Runtime Monitor.

Evaluates current state against fixed thresholds and returns structured alerts.
All checks are non-fatal — a check failure becomes a warning, not a crash.
"""

from connectors import psdb, ptmetadata, execution as exec_conn
from connectors import oracle as oracle_connector

# ── thresholds ──────────────────────────────────────────────────────────────

LONG_PROCESS_MINUTES = 120      # flag processes running longer than this
ERROR_WINDOW_HOURS   = 1        # look for PS errors within this window
QUEUE_DEPTH_WARN     = 10       # alert when queued count exceeds this
ASH_WAIT_PCT_WARN    = 70       # alert when a single non-CPU wait class > this %
BLOCKING_WARN        = True     # always alert when blocking sessions exist


# ── helpers ─────────────────────────────────────────────────────────────────

def _alert(severity, code, message, data=None):
    return {"severity": severity, "code": code, "message": message, "data": data or {}}


def _safe(label, fn):
    try:
        return fn()
    except Exception as exc:
        return {"_error": f"{label}: {exc}"}


# ── individual checks ────────────────────────────────────────────────────────

def _check_process_errors(env):
    alerts = []
    rows = psdb.query(env, """
        SELECT COUNT(*) as cnt FROM sysadm.PSPRCSRQST
         WHERE RUNSTATUS IN ('3','4','8')
           AND (SYSDATE - CAST(RQSTDTTM AS DATE)) < :window_h/24
    """, {"window_h": ERROR_WINDOW_HOURS})
    cnt = rows[0]["cnt"] if rows else 0
    if cnt > 0:
        alerts.append(_alert(
            "warn", "PROCESS_ERRORS",
            f"{cnt} failed process{'es' if cnt != 1 else ''} in the last {ERROR_WINDOW_HOURS}h",
            {"count": cnt, "_links": {"admin": f"/admin/runtime?env={env}"}},
        ))
    return alerts


def _check_long_processes(env):
    alerts = []
    rows = psdb.query(env, """
        SELECT PRCSINSTANCE, PRCSTYPE, PRCSNAME,
               ROUND((SYSDATE - CAST(BEGINDTTM AS DATE)) * 1440, 0) as run_minutes
          FROM sysadm.PSPRCSRQST
         WHERE RUNSTATUS IN ('2','7')
           AND BEGINDTTM IS NOT NULL
           AND (SYSDATE - CAST(BEGINDTTM AS DATE)) > :thresh/1440
         ORDER BY BEGINDTTM
         FETCH FIRST 5 ROWS ONLY
    """, {"thresh": LONG_PROCESS_MINUTES})
    for r in rows:
        mins = int(r.get("run_minutes") or 0)
        h = mins // 60
        m = mins % 60
        alerts.append(_alert(
            "warn", "LONG_PROCESS",
            f"Process #{r['prcsinstance']} ({r['prcsname']}) running {h}h {m}m",
            {
                "instance": r["prcsinstance"],
                "prcsname": r["prcsname"],
                "prcstype": r["prcstype"],
                "run_minutes": mins,
                "_links": {"admin": f"/admin/runtime?env={env}&instance={r['prcsinstance']}"},
            },
        ))
    return alerts


def _check_queue_depth(env):
    alerts = []
    rows = psdb.query(env, """
        SELECT COUNT(*) as cnt FROM sysadm.PSPRCSRQST
         WHERE RUNSTATUS IN ('6','1')
           AND (SYSDATE - CAST(RQSTDTTM AS DATE)) < 2/24
    """, {})
    cnt = rows[0]["cnt"] if rows else 0
    if cnt >= QUEUE_DEPTH_WARN:
        alerts.append(_alert(
            "warn", "QUEUE_DEPTH",
            f"{cnt} processes queued or pending cancellation (last 2h)",
            {"count": cnt},
        ))
    return alerts


def _check_blocking(db_name):
    alerts = []
    if not db_name:
        return alerts
    try:
        from connectors import execution as exec_conn
        result = exec_conn.oracle_blocking(db_name)
        chains = result.get("chains", [])
        if chains:
            total_blocked = sum(len(c.get("blocked", [])) for c in chains)
            max_wait = max(
                (s.get("seconds_in_wait") or 0)
                for c in chains for s in c.get("blocked", [])
            ) if total_blocked else 0
            alerts.append(_alert(
                "error" if max_wait > 300 else "warn",
                "BLOCKING_SESSIONS",
                f"{len(chains)} blocking chain{'s' if len(chains) != 1 else ''}, "
                f"{total_blocked} session{'s' if total_blocked != 1 else ''} blocked"
                + (f", longest {max_wait}s" if max_wait else ""),
                {"chains": len(chains), "blocked": total_blocked, "max_wait_seconds": max_wait},
            ))
    except Exception:
        pass
    return alerts


def _check_ash_waits(db_name, minutes=30):
    alerts = []
    if not db_name:
        return alerts
    try:
        summary = exec_conn.oracle_ash_summary(db_name, minutes=minutes)
        if summary.get("warnings"):
            return alerts
        for wc in summary.get("wait_classes", []):
            if wc["wait_class"] not in ("CPU", "(unknown)") and wc["pct"] >= ASH_WAIT_PCT_WARN:
                alerts.append(_alert(
                    "warn", "HIGH_WAIT",
                    f"Oracle DB {db_name}: {wc['pct']}% of ASH samples in '{wc['wait_class']}' (last {minutes}m)",
                    {"wait_class": wc["wait_class"], "pct": wc["pct"], "db": db_name},
                ))
    except Exception:
        pass
    return alerts


def _check_domains(env):
    alerts = []
    try:
        result = psdb.app_server_domains(env)
        if result.get("warnings"):
            return alerts
        for item in result.get("items", []):
            if item.get("listener_count", 0) == 0:
                alerts.append(_alert(
                    "warn", "DOMAIN_NO_LISTENERS",
                    f"App domain '{item['name']}' ({item.get('domain_type_label','?')}) has no active listeners",
                    {"domain": item["name"], "domain_type": item.get("domain_type_key")},
                ))
    except Exception:
        pass
    return alerts


# ── public API ───────────────────────────────────────────────────────────────

def evaluate_alerts(env, db_name=None):
    """
    Evaluate all runtime alert checks and return active alerts.
    Each alert has: severity (error|warn|info), code, message, data.
    """
    all_alerts = []
    warnings = []

    checks = [
        ("process_errors",  lambda: _check_process_errors(env)),
        ("long_processes",  lambda: _check_long_processes(env)),
        ("queue_depth",     lambda: _check_queue_depth(env)),
        ("blocking",        lambda: _check_blocking(db_name)),
        ("ash_waits",       lambda: _check_ash_waits(db_name)),
        ("domains",         lambda: _check_domains(env)),
    ]

    for label, fn in checks:
        try:
            all_alerts.extend(fn())
        except Exception as exc:
            warnings.append(ptmetadata.warning(f"ALERT_CHECK_FAILED:{label}", str(exc), severity="warn"))

    # sort: errors first, then warns
    all_alerts.sort(key=lambda a: 0 if a["severity"] == "error" else 1)

    return {
        "env": env,
        "db": db_name,
        "alert_count": len(all_alerts),
        "error_count": sum(1 for a in all_alerts if a["severity"] == "error"),
        "warn_count":  sum(1 for a in all_alerts if a["severity"] == "warn"),
        "alerts": all_alerts,
        "warnings": warnings,
    }
