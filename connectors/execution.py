"""
Execution Model connector — bridges Oracle V$ views and PeopleSoft process scheduler
tables for live runtime monitoring.

Data sources:
  psdb.query()          → SYSADM.PSPRCSRQST, PSAPMSGPUBHDR/SUBHDR, PSACCESSLOG
  oracle.query_db()     → V$SESSION, V$SQL, V$SESSION_LONGOPS, V$INSTANCE,
                          V$ACTIVE_SESSION_HISTORY
"""

import json
from pathlib import Path
from connectors import oracle as oracle_connector
from connectors import psdb, ptmetadata

CONFIG = Path("/opt/deathstar-api/config.json")

RUNSTATUS_LABELS = {
    "0":  "Cancel",
    "1":  "Cancel Pending",
    "2":  "Processing",
    "3":  "Cancelled",
    "4":  "Error",
    "5":  "Hold",
    "6":  "Queued",
    "7":  "Initiated",
    "8":  "No Success",
    "9":  "Success",
    "10": "Distributing",
    "11": "Generated",
    "12": "Posted",
    "13": "Not Posted",
    "14": "Content Deleted",
}

OUTDEST_LABELS = {
    "0": "None",
    "2": "File",
    "3": "Printer",
    "5": "Email",
    "6": "Web/Report",
    "8": "IB Notification",
    "9": "Feed",
}

ACTIVE_STATUSES = {"1", "2", "6", "7"}
ERROR_STATUSES  = {"0", "3", "4", "8"}

IB_PUBSTATUS_LABELS = {
    "1": "New",
    "2": "Started",
    "3": "Done",
    "4": "Cancelled",
    "5": "Error",
    "6": "Retry",
    "7": "Timeout",
}

IB_SUB_STATUS_LABELS = {
    "1": "New",
    "2": "Started",
    "3": "Done",
    "4": "Cancelled",
    "5": "Error",
    "6": "Retry",
}


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _db_by_name(db_name):
    data = json.loads(CONFIG.read_text())
    name_upper = db_name.upper()
    for db in data["oracle"]["databases"]:
        if db["name"].upper() == name_upper:
            return db
    raise ValueError(f"Oracle database not found: {db_name}")


def oracle_db_names():
    data = json.loads(CONFIG.read_text())
    return [db["name"] for db in data["oracle"]["databases"]]


def ps_env_names():
    data = json.loads(CONFIG.read_text())
    return [e["name"] for e in data["peoplesoft"]["environments"]]


def _clean(rows):
    """Convert datetime/LOB values to JSON-safe strings."""
    result = []
    for row in rows:
        cleaned = {}
        for k, v in row.items():
            if v is None or isinstance(v, (str, int, float, bool)):
                cleaned[k] = v
            elif hasattr(v, "isoformat"):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = str(v)
        result.append(cleaned)
    return result


def _label_process_row(row):
    status = str(row.get("runstatus") or "").strip()
    row["runstatus_label"] = RUNSTATUS_LABELS.get(status, f"Status {status}")
    out_type = str(row.get("outdesttype") or "").strip()
    row["outdest_label"] = OUTDEST_LABELS.get(out_type, out_type)
    return row


# ──────────────────────────────────────────────────────────────
# PeopleSoft Process Scheduler
# ──────────────────────────────────────────────────────────────

_PRCSRQST_LIST_COLS = [
    "PRCSINSTANCE", "PRCSTYPE", "PRCSNAME", "OPRID", "RUNCNTLID",
    "RUNSTATUS", "BEGINDTTM", "ENDDTTM", "SERVERNAMERUN", "OUTDESTTYPE",
    "SESSIONIDNUM",
]

_PRCSRQST_DETAIL_COLS = [
    "PRCSINSTANCE", "PRCSTYPE", "PRCSNAME", "OPRID", "RUNCNTLID",
    "RUNSTATUS", "BEGINDTTM", "ENDDTTM", "RQSTDTTM", "SERVERNAMERUN",
    "OUTDESTTYPE", "OUTDESTFORMAT", "OUTDEST", "SESSIONIDNUM",
    "RUNLOCATION", "ORIGINATION", "DISTSTATUS", "PRCSSERVERNAME",
    "JOBINSTANCE", "JOBNAME",
]


def process_queue(env, statuses=None, limit=100):
    """Return PSPRCSRQST rows, optionally filtered by status list."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        warnings.append(ptmetadata.warning("NO_PSPRCSRQST", "SYSADM.PSPRCSRQST not accessible"))
        return {"items": [], "warnings": warnings}

    cols = psdb.select_existing_columns(env, "PSPRCSRQST", _PRCSRQST_LIST_COLS, required=["PRCSINSTANCE"])
    col_list = ", ".join(cols)

    if statuses:
        placeholders = ", ".join(f"'{s.strip()}'" for s in statuses)
        status_clause = f"AND RUNSTATUS IN ({placeholders})"
    else:
        status_clause = ""

    sql = f"""
        SELECT * FROM (
            SELECT {col_list}
            FROM SYSADM.PSPRCSRQST
            WHERE 1=1
            {status_clause}
            ORDER BY PRCSINSTANCE DESC
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = _clean(psdb.query(env, sql))
        for row in rows:
            _label_process_row(row)
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSPRCSRQST_QUERY_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def process_instance(env, instance_id):
    """Return full detail for a single PSPRCSRQST row."""
    warnings = []

    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        warnings.append(ptmetadata.warning("NO_PSPRCSRQST", "SYSADM.PSPRCSRQST not accessible"))
        return {"item": None, "warnings": warnings}

    cols = psdb.select_existing_columns(env, "PSPRCSRQST", _PRCSRQST_DETAIL_COLS, required=["PRCSINSTANCE"])
    col_list = ", ".join(cols)

    sql = f"""
        SELECT {col_list}
        FROM SYSADM.PSPRCSRQST
        WHERE PRCSINSTANCE = :instance_id
    """

    try:
        rows = _clean(psdb.query(env, sql, {"instance_id": int(instance_id)}))
        if not rows:
            return {"item": None, "warnings": warnings}
        row = rows[0]
        _label_process_row(row)
        return {"item": row, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSPRCSRQST_DETAIL_ERR", str(exc), severity="error"))
        return {"item": None, "warnings": warnings}


def process_status_summary(env):
    """Return process count by status covering recent 10 000 instances."""
    warnings = []

    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        warnings.append(ptmetadata.warning("NO_PSPRCSRQST", "SYSADM.PSPRCSRQST not accessible"))
        return {"summary": [], "totals": {}, "warnings": warnings}

    sql = """
        SELECT RUNSTATUS, COUNT(*) AS CNT
        FROM SYSADM.PSPRCSRQST
        WHERE PRCSINSTANCE > (
            SELECT GREATEST(MAX(PRCSINSTANCE) - 10000, 0) FROM SYSADM.PSPRCSRQST
        )
        GROUP BY RUNSTATUS
        ORDER BY RUNSTATUS
    """

    try:
        rows = psdb.query(env, sql)
        summary = []
        totals = {"active": 0, "error": 0, "success": 0, "other": 0, "total": 0}
        for row in rows:
            status = str(row.get("runstatus") or "").strip()
            count = int(row.get("cnt") or 0)
            label = RUNSTATUS_LABELS.get(status, f"Status {status}")
            summary.append({"status": status, "label": label, "count": count})
            totals["total"] += count
            if status in ACTIVE_STATUSES:
                totals["active"] += count
            elif status in ERROR_STATUSES:
                totals["error"] += count
            elif status == "9":
                totals["success"] += count
            else:
                totals["other"] += count
        return {"summary": summary, "totals": totals, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PS_SUMMARY_ERR", str(exc), severity="error"))
        return {"summary": [], "totals": {}, "warnings": warnings}


def ae_running(env, limit=50):
    """Return currently active or queued Application Engine processes."""
    warnings = []
    limit = max(1, min(int(limit), 200))

    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        warnings.append(ptmetadata.warning("NO_PSPRCSRQST", "SYSADM.PSPRCSRQST not accessible"))
        return {"items": [], "warnings": warnings}

    ae_cols = psdb.select_existing_columns(
        env, "PSPRCSRQST",
        ["PRCSINSTANCE", "PRCSNAME", "OPRID", "RUNCNTLID", "RUNSTATUS",
         "BEGINDTTM", "SERVERNAMERUN", "SESSIONIDNUM"],
        required=["PRCSINSTANCE"],
    )
    sql = f"""
        SELECT * FROM (
            SELECT {', '.join(ae_cols)}
            FROM SYSADM.PSPRCSRQST
            WHERE PRCSTYPE = 'Application Engine'
              AND RUNSTATUS IN ('1','2','6','7')
            ORDER BY PRCSINSTANCE DESC
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = _clean(psdb.query(env, sql))
        for row in rows:
            status = str(row.get("runstatus") or "").strip()
            row["runstatus_label"] = RUNSTATUS_LABELS.get(status, f"Status {status}")
        return {"items": rows, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("AE_RUNNING_ERR", str(exc), severity="error"))
        return {"items": [], "warnings": warnings}


def ib_queue_summary(env):
    """Return Integration Broker queue depth from PSAPMSGPUBHDR and PSAPMSGSUBCON."""
    warnings = []
    result = {"published": [], "subscribed": []}

    if ptmetadata.has_table(env, "PSAPMSGPUBHDR"):
        try:
            sql = """
                SELECT PUBSTATUS, COUNT(*) AS CNT
                FROM SYSADM.PSAPMSGPUBHDR
                GROUP BY PUBSTATUS
                ORDER BY PUBSTATUS
            """
            rows = psdb.query(env, sql)
            for row in rows:
                status = str(row.get("pubstatus") or "").strip()
                row["status_label"] = IB_PUBSTATUS_LABELS.get(status, f"Status {status}")
            result["published"] = rows
        except Exception as exc:
            warnings.append(ptmetadata.warning("IB_PUB_ERR", str(exc)))
    else:
        warnings.append(ptmetadata.warning("NO_IB_PUB", "PSAPMSGPUBHDR not accessible — IB may not be configured"))

    if ptmetadata.has_table(env, "PSAPMSGSUBCON"):
        try:
            sql = """
                SELECT SUBCONSTATUS, COUNT(*) AS CNT
                FROM SYSADM.PSAPMSGSUBCON
                GROUP BY SUBCONSTATUS
                ORDER BY SUBCONSTATUS
            """
            rows = psdb.query(env, sql)
            for row in rows:
                status = str(row.get("sub_status") or "").strip()
                row["status_label"] = IB_SUB_STATUS_LABELS.get(status, f"Status {status}")
            result["subscribed"] = rows
        except Exception as exc:
            warnings.append(ptmetadata.warning("IB_SUB_ERR", str(exc)))
    else:
        warnings.append(ptmetadata.warning("NO_IB_SUB", "PSAPMSGSUBCON not accessible — IB may not be configured"))

    return {"ib": result, "warnings": warnings}


def user_sessions(env, limit=50):
    """Return recent/active user logins from PSACCESSLOG."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    if not ptmetadata.has_table(env, "PSACCESSLOG"):
        warnings.append(ptmetadata.warning("NO_PSACCESSLOG", "PSACCESSLOG not accessible"))
        return {"active": [], "recent": [], "warnings": warnings}

    cols = psdb.select_existing_columns(
        env,
        "PSACCESSLOG",
        ["LOGOUTDTTM", "TOOLSREL", "CONNECTDBBNAME", "LOGIPADDRESS", "PT_SIGNON_TYPE", "PT_SIGNOUT_REASON", "PT_TRACING_ID"],
        required=["OPRID", "LOGINDTTM"],
    )

    sql = f"""
        SELECT * FROM (
            SELECT {", ".join(cols)}
            FROM SYSADM.PSACCESSLOG
            WHERE LOGINDTTM > SYSDATE - 1
            ORDER BY LOGINDTTM DESC
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = _clean(psdb.query(env, sql))
        active = [r for r in rows if r.get("logoutdttm") is None]
        recent = [r for r in rows if r.get("logoutdttm") is not None]
        return {"active": active, "recent": recent, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("PSACCESSLOG_ERR", str(exc), severity="error"))
        return {"active": [], "recent": [], "warnings": warnings}


# ──────────────────────────────────────────────────────────────
# Oracle V$ session monitoring
# ──────────────────────────────────────────────────────────────

def oracle_active_sessions(db_name, limit=50):
    """Return non-idle Oracle sessions with current SQL text from V$SESSION + V$SQL."""
    warnings = []
    limit = max(1, min(int(limit), 500))

    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"items": [], "db": db_name, "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    sql = f"""
        SELECT * FROM (
            SELECT
                s.SID,
                s.SERIAL# AS SERIAL_NUM,
                s.USERNAME,
                s.STATUS,
                s.PROGRAM,
                s.MODULE,
                s.ACTION,
                s.MACHINE,
                s.OSUSER,
                s.SQL_ID,
                s.EVENT,
                s.WAIT_CLASS,
                s.SECONDS_IN_WAIT,
                s.STATE,
                TO_CHAR(s.LOGON_TIME, 'YYYY-MM-DD HH24:MI:SS') AS LOGON_TIME,
                s.BLOCKING_SESSION,
                SUBSTR(q.SQL_TEXT, 1, 300) AS SQL_TEXT
            FROM V$SESSION s
            LEFT JOIN V$SQL q
                ON q.SQL_ID = s.SQL_ID
               AND q.CHILD_NUMBER = s.SQL_CHILD_NUMBER
            WHERE s.TYPE = 'USER'
              AND s.STATUS != 'INACTIVE'
            ORDER BY s.SECONDS_IN_WAIT DESC NULLS LAST
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = _clean(oracle_connector.query_db(db, sql))
        return {"items": rows, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_SESSIONS_ERR", str(exc), severity="error"))
        return {"items": [], "db": db_name, "warnings": warnings}


def oracle_top_sql(db_name, limit=20):
    """Return top SQL from V$SQL by cumulative elapsed time."""
    warnings = []
    limit = max(1, min(int(limit), 100))

    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"items": [], "db": db_name, "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    sql = f"""
        SELECT * FROM (
            SELECT
                SQL_ID,
                SUBSTR(SQL_TEXT, 1, 300) AS SQL_TEXT,
                EXECUTIONS,
                ROUND(ELAPSED_TIME / 1000000, 2) AS ELAPSED_SECS,
                ROUND(CPU_TIME / 1000000, 2) AS CPU_SECS,
                ROUND(ELAPSED_TIME / NULLIF(EXECUTIONS, 0) / 1000000, 4) AS ELAPSED_PER_EXEC,
                BUFFER_GETS,
                ROUND(BUFFER_GETS / NULLIF(EXECUTIONS, 0), 0) AS GETS_PER_EXEC,
                DISK_READS,
                ROWS_PROCESSED,
                PARSING_SCHEMA_NAME,
                TO_CHAR(LAST_ACTIVE_TIME, 'YYYY-MM-DD HH24:MI:SS') AS LAST_ACTIVE
            FROM V$SQL
            WHERE EXECUTIONS > 0
              AND PARSING_SCHEMA_NAME NOT IN ('SYS', 'SYSTEM')
            ORDER BY ELAPSED_TIME DESC
        ) WHERE ROWNUM <= {limit}
    """

    try:
        rows = _clean(oracle_connector.query_db(db, sql))
        return {"items": rows, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_SQL_ERR", str(exc), severity="error"))
        return {"items": [], "db": db_name, "warnings": warnings}


def oracle_blocking(db_name):
    """Return blocking session chains from V$SESSION."""
    warnings = []

    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"chains": [], "raw": [], "db": db_name,
                "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    # Fetch all sessions that are either blocking or being blocked
    sql = """
        SELECT
            s.SID,
            s.SERIAL# AS SERIAL_NUM,
            s.USERNAME,
            s.STATUS,
            s.MACHINE,
            s.PROGRAM,
            s.MODULE,
            s.BLOCKING_SESSION,
            s.EVENT,
            s.SECONDS_IN_WAIT,
            TO_CHAR(s.LOGON_TIME, 'YYYY-MM-DD HH24:MI:SS') AS LOGON_TIME
        FROM V$SESSION s
        WHERE s.TYPE = 'USER'
          AND (
              s.BLOCKING_SESSION IS NOT NULL
              OR s.SID IN (
                  SELECT BLOCKING_SESSION
                  FROM V$SESSION
                  WHERE BLOCKING_SESSION IS NOT NULL
              )
          )
        ORDER BY s.BLOCKING_SESSION NULLS FIRST, s.SECONDS_IN_WAIT DESC
    """

    try:
        raw = _clean(oracle_connector.query_db(db, sql))

        # Build chains: find root blockers (not waiting on anyone in this set)
        blocked_by_map = {}
        for r in raw:
            bs = r.get("blocking_session")
            if bs is not None:
                blocked_by_map.setdefault(bs, []).append(r)

        blocker_sids = set(blocked_by_map.keys())
        chains = []
        for bsid in sorted(blocker_sids):
            blocker = next((r for r in raw if r.get("sid") == bsid), {"sid": bsid})
            chains.append({
                "blocker_sid": bsid,
                "blocker": blocker,
                "waiters": blocked_by_map[bsid],
            })

        return {"chains": chains, "raw": raw, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_BLOCKING_ERR", str(exc), severity="error"))
        return {"chains": [], "raw": [], "db": db_name, "warnings": warnings}


def oracle_longops(db_name):
    """Return in-progress long-running Oracle operations from V$SESSION_LONGOPS."""
    warnings = []

    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"items": [], "db": db_name,
                "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    sql = """
        SELECT
            SID,
            SERIAL# AS SERIAL_NUM,
            OPNAME,
            TARGET,
            SOFAR,
            TOTALWORK,
            ROUND(SOFAR / NULLIF(TOTALWORK, 0) * 100, 2) AS PCT_DONE,
            ELAPSED_SECONDS,
            TIME_REMAINING,
            TO_CHAR(START_TIME, 'YYYY-MM-DD HH24:MI:SS') AS START_TIME
        FROM V$SESSION_LONGOPS
        WHERE TOTALWORK > 0
          AND SOFAR < TOTALWORK
        ORDER BY TIME_REMAINING DESC
    """

    try:
        rows = _clean(oracle_connector.query_db(db, sql))
        return {"items": rows, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_LONGOPS_ERR", str(exc), severity="error"))
        return {"items": [], "db": db_name, "warnings": warnings}


def oracle_session_counts(db_name):
    """Return session count summary grouped by status and type from V$SESSION."""
    warnings = []

    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"counts": [], "db": db_name,
                "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    sql = """
        SELECT STATUS, TYPE, COUNT(*) AS CNT
        FROM V$SESSION
        GROUP BY STATUS, TYPE
        ORDER BY STATUS, TYPE
    """

    try:
        rows = oracle_connector.query_db(db, sql)
        return {"counts": rows, "db": db_name, "warnings": warnings}
    except Exception as exc:
        warnings.append(ptmetadata.warning("ORACLE_COUNTS_ERR", str(exc), severity="error"))
        return {"counts": [], "db": db_name, "warnings": warnings}


def oracle_ash_summary(db_name, minutes=30):
    """Return Oracle ASH wait class breakdown and top wait events from V$ACTIVE_SESSION_HISTORY."""
    warnings = []
    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"wait_classes": [], "top_events": [], "top_modules": [], "total_samples": 0,
                "db": db_name, "minutes": minutes,
                "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    mins = max(1, min(int(minutes), 1440))

    try:
        wc_rows = oracle_connector.query_db(db, f"""
            SELECT NVL(wait_class, 'CPU') as wait_class,
                   COUNT(*) as samples
              FROM V$ACTIVE_SESSION_HISTORY
             WHERE sample_time >= SYSDATE - {mins}/1440
               AND session_type = 'FOREGROUND'
             GROUP BY wait_class
             ORDER BY samples DESC
        """)
        total = sum(r["samples"] for r in wc_rows)

        wait_classes = [
            {
                "wait_class": r["wait_class"],
                "samples": r["samples"],
                "pct": round(r["samples"] * 100.0 / total, 1) if total else 0,
            }
            for r in wc_rows
        ]

        ev_rows = oracle_connector.query_db(db, f"""
            SELECT NVL(event, 'On CPU') as event,
                   NVL(wait_class, 'CPU') as wait_class,
                   COUNT(*) as samples
              FROM V$ACTIVE_SESSION_HISTORY
             WHERE sample_time >= SYSDATE - {mins}/1440
               AND session_type = 'FOREGROUND'
             GROUP BY event, wait_class
             ORDER BY samples DESC
             FETCH FIRST 10 ROWS ONLY
        """)
        top_events = [
            {
                "event": r["event"],
                "wait_class": r["wait_class"],
                "samples": r["samples"],
                "pct": round(r["samples"] * 100.0 / total, 1) if total else 0,
            }
            for r in ev_rows
        ]

        mod_rows = oracle_connector.query_db(db, f"""
            SELECT NVL(module, '(unknown)') as module,
                   COUNT(*) as samples
              FROM V$ACTIVE_SESSION_HISTORY
             WHERE sample_time >= SYSDATE - {mins}/1440
               AND session_type = 'FOREGROUND'
             GROUP BY module
             ORDER BY samples DESC
             FETCH FIRST 10 ROWS ONLY
        """)
        top_modules = [
            {
                "module": r["module"],
                "samples": r["samples"],
                "pct": round(r["samples"] * 100.0 / total, 1) if total else 0,
            }
            for r in mod_rows
        ]

        return {
            "db": db_name,
            "minutes": mins,
            "total_samples": total,
            "wait_classes": wait_classes,
            "top_events": top_events,
            "top_modules": top_modules,
            "warnings": warnings,
        }

    except Exception as exc:
        warnings.append(ptmetadata.warning("ASH_SUMMARY_ERR", str(exc), severity="warn"))
        return {
            "db": db_name, "minutes": minutes, "total_samples": 0,
            "wait_classes": [], "top_events": [], "top_modules": [],
            "warnings": warnings,
        }


def oracle_ash_top_sql(db_name, minutes=30, limit=10):
    """Return top SQL from V$ACTIVE_SESSION_HISTORY by sample count (approx. time in DB)."""
    warnings = []
    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"items": [], "total_samples": 0, "db": db_name, "minutes": minutes,
                "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    mins = max(1, min(int(minutes), 1440))
    lim = max(1, min(int(limit), 50))

    try:
        rows = oracle_connector.query_db(db, f"""
            SELECT a.sql_id,
                   COUNT(*) as samples,
                   MAX(a.sql_opname) as sql_opname,
                   MAX(a.module) as module,
                   SUBSTR(MAX(s.sql_text), 1, 200) as sql_text
              FROM V$ACTIVE_SESSION_HISTORY a
              LEFT JOIN V$SQL s ON a.sql_id = s.sql_id AND s.child_number = 0
             WHERE a.sample_time >= SYSDATE - {mins}/1440
               AND a.sql_id IS NOT NULL
               AND a.session_type = 'FOREGROUND'
             GROUP BY a.sql_id
             ORDER BY samples DESC
             FETCH FIRST {lim} ROWS ONLY
        """)
        tot_rows = oracle_connector.query_db(db, f"""
            SELECT COUNT(*) as cnt
              FROM V$ACTIVE_SESSION_HISTORY
             WHERE sample_time >= SYSDATE - {mins}/1440
               AND session_type = 'FOREGROUND'
        """)
        total = (tot_rows[0]["cnt"] if tot_rows else 0) or 1

        items = [
            {
                "sql_id": r["sql_id"],
                "samples": r["samples"],
                "pct": round(r["samples"] * 100.0 / total, 1),
                "sql_opname": r.get("sql_opname") or "",
                "module": r.get("module") or "",
                "sql_text": (r.get("sql_text") or "")[:200],
            }
            for r in rows
        ]

        return {
            "db": db_name,
            "minutes": mins,
            "total_samples": total,
            "items": items,
            "warnings": warnings,
        }

    except Exception as exc:
        warnings.append(ptmetadata.warning("ASH_SQL_ERR", str(exc), severity="warn"))
        return {
            "items": [], "total_samples": 0, "db": db_name, "minutes": minutes,
            "warnings": warnings,
        }


# ── ASH correlation: PeopleSoft process → Oracle activity ───────────────────

_PS_PROCESS_MODULE_MAP = {
    # prcstype (lower) → ASH module value
    "application engine": "PSAE",
    # Others run under PSPRCSRV but aren't individually distinguishable by name
}


def _ash_module_filter(prcstype, prcsname):
    """Return (module_filter, action_filter) SQL fragments for a process type.
    Column refs are qualified with alias 'a' for use in joins with V$SQL.
    """
    pt = (prcstype or "").strip().lower()
    if pt == "application engine":
        return ("a.module = 'PSAE'", f"AND a.action = '{prcsname}'")
    # Generic: PSPRCSRV handles all other types; no action filter
    return ("a.module LIKE 'PSPRCSRV%'", "")


def oracle_ash_for_process(db_name, env, instance_id):
    """Return Oracle ASH activity for a specific PeopleSoft process instance.

    Looks up PSPRCSRQST for time window and process type, then queries
    V$ACTIVE_SESSION_HISTORY (or DBA_HIST fallback) filtered to that
    process's Oracle activity signature.
    """
    warnings = []
    try:
        db = _db_by_name(db_name)
    except ValueError as exc:
        return {"events": [], "top_sql": [], "total_samples": 0, "source": None,
                "db": db_name, "warnings": [ptmetadata.warning("DB_NOT_FOUND", str(exc))]}

    # Fetch process row from PeopleSoft
    prcs = process_instance(env, instance_id)
    item = prcs.get("item")
    if not item:
        return {"events": [], "top_sql": [], "total_samples": 0, "source": None,
                "db": db_name, "warnings": prcs.get("warnings", []) +
                [ptmetadata.warning("PROCESS_NOT_FOUND", f"Instance {instance_id} not found in {env}")]}

    prcstype = str(item.get("prcstype") or "")
    prcsname = str(item.get("prcsname") or "")
    begin_dt = item.get("begindttm")
    end_dt   = item.get("enddttm")

    if not begin_dt:
        return {"events": [], "top_sql": [], "total_samples": 0, "source": None,
                "db": db_name, "prcstype": prcstype, "prcsname": prcsname,
                "warnings": [ptmetadata.warning("NO_BEGINDTTM", "Process has not started yet")]}

    # Format timestamps for Oracle (isoformat from _clean gives YYYY-MM-DDTHH:MM:SS.ffffff)
    def _ts(s):
        if not s:
            return None
        clean = str(s).replace("T", " ")[:19]
        return f"TIMESTAMP '{clean}'"

    begin_ts = _ts(begin_dt)
    end_ts   = _ts(end_dt) if end_dt else "SYSDATE"

    mod_filter, action_filter = _ash_module_filter(prcstype, prcsname)
    time_filter = f"a.SAMPLE_TIME >= {begin_ts} AND a.SAMPLE_TIME <= {end_ts}"

    def _run_ash(table):
        ev_sql = f"""
            SELECT NVL(a.event, 'On CPU') as event,
                   NVL(a.wait_class, 'CPU') as wait_class,
                   COUNT(*) as samples
              FROM {table} a
             WHERE {mod_filter}
               {action_filter}
               AND {time_filter}
             GROUP BY a.event, a.wait_class
             ORDER BY samples DESC
             FETCH FIRST 10 ROWS ONLY
        """
        sql_sql = f"""
            SELECT a.sql_id, COUNT(*) as samples,
                   MAX(a.sql_opname) as sql_opname,
                   SUBSTR(MAX(s.sql_text), 1, 200) as sql_text
              FROM {table} a
              LEFT JOIN V$SQL s ON a.sql_id = s.sql_id AND s.child_number = 0
             WHERE {mod_filter}
               {action_filter}
               AND {time_filter}
               AND a.sql_id IS NOT NULL
             GROUP BY a.sql_id
             ORDER BY samples DESC
             FETCH FIRST 10 ROWS ONLY
        """
        ev_rows  = oracle_connector.query_db(db, ev_sql)
        sql_rows = oracle_connector.query_db(db, sql_sql)
        total    = sum(r["samples"] for r in ev_rows)
        events   = [
            {**r, "pct": round(r["samples"] * 100.0 / total, 1) if total else 0}
            for r in ev_rows
        ]
        top_sql  = [
            {
                "sql_id":    r["sql_id"],
                "samples":   r["samples"],
                "pct":       round(r["samples"] * 100.0 / total, 1) if total else 0,
                "sql_opname": r.get("sql_opname") or "",
                "sql_text":  (r.get("sql_text") or "")[:200],
            }
            for r in sql_rows
        ]
        return total, events, top_sql

    # Try V$ASH first, fall back to DBA_HIST
    source = None
    total = 0
    events = []
    top_sql = []

    try:
        total, events, top_sql = _run_ash("V$ACTIVE_SESSION_HISTORY")
        source = "V$ACTIVE_SESSION_HISTORY"
    except Exception as exc:
        warnings.append(ptmetadata.warning("ASH_VASH_ERR", str(exc), severity="warn"))

    if not total:
        try:
            total, events, top_sql = _run_ash("DBA_HIST_ACTIVE_SESS_HISTORY")
            source = "DBA_HIST_ACTIVE_SESS_HISTORY"
        except Exception as exc:
            warnings.append(ptmetadata.warning("ASH_HIST_ERR", str(exc), severity="warn"))

    return {
        "db": db_name,
        "env": env,
        "instance": instance_id,
        "prcstype": prcstype,
        "prcsname": prcsname,
        "begin_dt": begin_dt,
        "end_dt": end_dt,
        "total_samples": total,
        "events": events,
        "top_sql": top_sql,
        "source": source,
        "warnings": warnings,
    }


def instance_trace(env, instance_id, db_name=None):
    """AE-focused runtime trace for a single Process Scheduler instance.

    Composes what's real and already queryable today into one view: the
    PSPRCSRQST run detail, the AE program/section definitions (if this
    instance is an Application Engine run), Oracle ASH wait events/top SQL
    correlated to the run window (via oracle_ash_for_process(), which
    already filters by PSAE module/action), and log errors within the run
    window. Does NOT claim step-by-step execution timing — no AE trace/
    runtime-log table (PSAERUNCNTL/PS_AE_TRACE/PSAEMSGLOG) is present or
    queried in this environment, so that narrower "which step ran when"
    view isn't attempted; this is a correlation of what's real, not a
    simulation of what isn't.
    """
    from connectors import logdb, ae

    warnings = []
    prcs = process_instance(env, instance_id)
    item = prcs.get("item")
    if not item:
        return {
            "instance": instance_id, "env": env.upper(), "process": None,
            "ae_program": None, "ash": None, "log_errors": [],
            "warnings": prcs.get("warnings", []) +
            [ptmetadata.warning("PROCESS_NOT_FOUND", f"Instance {instance_id} not found in {env}")],
        }

    prcstype = str(item.get("prcstype") or "")
    prcsname = str(item.get("prcsname") or "")
    begin_dt = item.get("begindttm")
    end_dt   = item.get("enddttm")

    ae_program = None
    if prcstype.strip().lower() == "application engine":
        try:
            prog_result = ae.program(env, prcsname)
            ae_program = prog_result.get("item") if isinstance(prog_result, dict) else prog_result
        except Exception as exc:
            warnings.append(f"ae_program: {exc}")

    ash = None
    if db_name:
        try:
            ash = oracle_ash_for_process(db_name, env, instance_id)
        except Exception as exc:
            warnings.append(f"ash: {exc}")

    log_errors = []
    if begin_dt:
        try:
            end_for_query = end_dt or begin_dt
            log_errors = logdb.query_errors(
                env=env.upper(),
                start=str(begin_dt).replace("T", " ")[:19],
                end=str(end_for_query).replace("T", " ")[:19],
                limit=50,
            )
        except Exception as exc:
            warnings.append(f"log_errors: {exc}")

    return {
        "instance": instance_id,
        "env": env.upper(),
        "process": item,
        "ae_program": ae_program,
        "ash": ash,
        "log_errors": log_errors,
        "warnings": warnings,
    }


def _runtime_node(node_type, name, label=None, data=None, links=None):
    name = str(name or "").strip()
    return {
        "id": f"{node_type}:{name}",
        "type": node_type,
        "name": name,
        "label": label or name,
        "data": data or {},
        "_links": links or {},
    }


def _runtime_edge(source_type, source_name, target_type, target_name, relationship, data=None):
    return {
        "source": f"{source_type}:{str(source_name or '').strip()}",
        "target": f"{target_type}:{str(target_name or '').strip()}",
        "relationship": relationship,
        "data": data or {},
    }


def runtime_graph(env, db_name=None, process_limit=30, session_limit=30):
    """Build a best-effort graph of the current PeopleSoft runtime surface."""
    process_limit = max(1, min(int(process_limit), 100))
    session_limit = max(1, min(int(session_limit), 100))
    env_name = env.upper()
    nodes = {}
    edges = []
    warnings = []

    def add_node(node):
        if node["name"]:
            nodes[node["id"]] = node

    def add_edge(edge):
        if edge["source"].split(":", 1)[1] and edge["target"].split(":", 1)[1]:
            edges.append(edge)

    add_node(_runtime_node(
        "environment",
        env_name,
        label=f"{env_name} Runtime",
        data={"env": env_name, "db": db_name},
        links={"runtime": f"/admin/runtime?env={env_name}"},
    ))

    db_node_name = None
    if db_name:
        db_node_name = db_name.upper()
        add_node(_runtime_node("oracle_database", db_node_name, label=db_node_name, data={"db": db_name}))
        add_edge(_runtime_edge("environment", env_name, "oracle_database", db_node_name, "uses_database"))

    processes = process_queue(env, statuses=ACTIVE_STATUSES, limit=process_limit)
    warnings.extend(processes.get("warnings", []))
    for row in processes.get("items", []):
        instance = row.get("prcsinstance")
        prcsname = row.get("prcsname")
        oprid = row.get("oprid")
        server = row.get("servernamerun") or row.get("prcssservername")

        if instance:
            add_node(_runtime_node(
                "process_instance",
                instance,
                label=f"{prcsname or 'Process'} #{instance}",
                data=row,
                links={"detail": f"/api/runtime/process/{instance}?env={env_name}"},
            ))
            add_edge(_runtime_edge("environment", env_name, "process_instance", instance, "runs_process"))

        if prcsname:
            add_node(_runtime_node(
                "process",
                prcsname,
                label=prcsname,
                data={"prcsname": prcsname, "prcstype": row.get("prcstype")},
                links={"object": f"/admin/object/process/{prcsname}"},
            ))
            if instance:
                add_edge(_runtime_edge("process_instance", instance, "process", prcsname, "instance_of"))

        if oprid:
            add_node(_runtime_node(
                "operator",
                oprid,
                label=oprid,
                data={"oprid": oprid},
                links={"admin": f"/admin/object/operator/{oprid}"},
            ))
            if instance:
                add_edge(_runtime_edge("operator", oprid, "process_instance", instance, "submitted_process"))

        if server:
            add_node(_runtime_node("process_server", server, label=server, data={"server": server}))
            if instance:
                add_edge(_runtime_edge("process_server", server, "process_instance", instance, "executes_process"))

    ae = ae_running(env, limit=process_limit)
    warnings.extend(ae.get("warnings", []))
    for row in ae.get("items", []):
        instance = row.get("prcsinstance")
        prcsname = row.get("prcsname")
        if instance and prcsname:
            add_node(_runtime_node(
                "application_engine",
                prcsname,
                label=prcsname,
                data={"ae_applid": prcsname},
                links={"admin": f"/admin/object/application_engine/{prcsname}"},
            ))
            add_edge(_runtime_edge("process_instance", instance, "application_engine", prcsname, "runs_ae"))

    sessions = user_sessions(env, limit=session_limit)
    warnings.extend(sessions.get("warnings", []))
    for session_state, rows in (("active", sessions.get("active", [])), ("recent", sessions.get("recent", []))):
        for row in rows:
            oprid = row.get("oprid")
            login = row.get("logindttm")
            session_id = f"{oprid}:{login}" if login else oprid
            add_node(_runtime_node("ps_session", session_id, label=oprid, data={**row, "session_state": session_state}))
            add_edge(_runtime_edge("environment", env_name, "ps_session", session_id, f"has_{session_state}_session"))
            if oprid:
                add_node(_runtime_node(
                    "operator",
                    oprid,
                    label=oprid,
                    data={"oprid": oprid},
                    links={"admin": f"/admin/object/operator/{oprid}"},
                ))
                add_edge(_runtime_edge("operator", oprid, "ps_session", session_id, "owns_session"))

    ib = ib_queue_summary(env)
    warnings.extend(ib.get("warnings", []))
    ib_root = "Integration Broker"
    add_node(_runtime_node("integration_broker", ib_root, label=ib_root, data={"env": env_name}))
    add_edge(_runtime_edge("environment", env_name, "integration_broker", ib_root, "has_ib_runtime"))
    for direction, status_key in (("published", "pubstatus"), ("subscribed", "sub_status")):
        for row in ib.get("ib", {}).get(direction, []):
            status = row.get(status_key) or row.get("subconstatus") or row.get("pubstatus")
            label = row.get("status_label") or f"Status {status}"
            name = f"{direction}:{status}"
            add_node(_runtime_node("ib_status", name, label=f"{direction} {label}", data=row))
            add_edge(_runtime_edge("integration_broker", ib_root, "ib_status", name, f"has_{direction}_status"))

    if db_name:
        oracle_sessions = oracle_active_sessions(db_name, limit=session_limit)
        warnings.extend(oracle_sessions.get("warnings", []))
        for row in oracle_sessions.get("items", []):
            sid = row.get("sid")
            serial = row.get("serial_num")
            session_name = f"{sid},{serial}" if serial else sid
            if not session_name:
                continue
            add_node(_runtime_node("oracle_session", session_name, label=f"SID {session_name}", data=row))
            if db_node_name:
                add_edge(_runtime_edge("oracle_database", db_node_name, "oracle_session", session_name, "has_session"))

            sql_id = row.get("sql_id")
            if sql_id:
                add_node(_runtime_node("sql", sql_id, label=sql_id, data={"sql_id": sql_id, "sql_text": row.get("sql_text")}))
                add_edge(_runtime_edge("oracle_session", session_name, "sql", sql_id, "executes_sql"))

            client = row.get("client_identifier") or row.get("osuser")
            if client:
                add_node(_runtime_node("runtime_identity", client, label=client, data={"identity": client}))
                add_edge(_runtime_edge("runtime_identity", client, "oracle_session", session_name, "owns_oracle_session"))

    return {
        "root": f"environment:{env_name}",
        "env": env_name,
        "db": db_name,
        "nodes": list(nodes.values()),
        "edges": edges,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "warnings": len(warnings),
        },
        "warnings": warnings,
    }


# ──────────────────────────────────────────────────────────────
# Combined runtime status snapshot
# ──────────────────────────────────────────────────────────────

def runtime_status(env, db_name=None):
    """
    Combined snapshot for the runtime dashboard.
    Always queries process scheduler; optionally adds Oracle session data.
    """
    result = {
        "env": env,
        "db": db_name,
        "process_summary": None,
        "ae_running": None,
        "ib_summary": None,
        "oracle_sessions": None,
        "blocking": None,
        "warnings": [],
    }

    ps = process_status_summary(env)
    result["process_summary"] = ps
    result["warnings"].extend(ps.get("warnings", []))

    ae = ae_running(env, limit=20)
    result["ae_running"] = ae
    result["warnings"].extend(ae.get("warnings", []))

    ib = ib_queue_summary(env)
    result["ib_summary"] = ib
    result["warnings"].extend(ib.get("warnings", []))

    if db_name:
        sessions = oracle_session_counts(db_name)
        result["oracle_sessions"] = sessions
        result["warnings"].extend(sessions.get("warnings", []))

        blocking = oracle_blocking(db_name)
        result["blocking"] = blocking
        result["warnings"].extend(blocking.get("warnings", []))

    return result


# ── Root Cause Analysis ───────────────────────────────────────────────────

def rca_snapshot(env: str, start_iso: str, end_iso: str, db_name: str = None) -> dict:
    """
    Correlate process failures, log errors, Oracle ASH, and IB errors
    for a specific time window to support incident/root-cause analysis.
    """
    from connectors import logdb
    import datetime as _dt

    result = {
        "env": env.upper(),
        "window": {"start": start_iso, "end": end_iso},
        "process_failures": [],
        "log_errors": [],
        "ash": None,
        "ib_errors": [],
        "timeline": [],
        "warnings": [],
    }

    # ── 1. Process failures (PSPRCSRQST) ────────────────────────────────
    try:
        if ptmetadata.has_table(env, "PSPRCSRQST"):
            fail_rows = psdb.query(env, """
                SELECT PRCSINSTANCE, PRCSTYPE, PRCSNAME, OPRID, RUNSTATUS,
                       BEGINDTTM, ENDDTTM, RQSTDTTM, SERVERNAMERUN
                  FROM SYSADM.PSPRCSRQST
                 WHERE RUNSTATUS IN ('3','4','8','9','10')
                   AND RQSTDTTM >= TO_DATE(:s, 'YYYY-MM-DD HH24:MI:SS')
                   AND RQSTDTTM <= TO_DATE(:e, 'YYYY-MM-DD HH24:MI:SS')
                 ORDER BY RQSTDTTM DESC
                 FETCH FIRST 50 ROWS ONLY
            """, {"s": start_iso[:19], "e": end_iso[:19]})
            result["process_failures"] = [dict(r) for r in fail_rows]
    except Exception as exc:
        result["warnings"].append(f"process_failures: {exc}")

    # ── 2. Log errors ────────────────────────────────────────────────────
    try:
        log_errs = logdb.query_errors(env=env.upper(), start=start_iso, end=end_iso, limit=100)
        result["log_errors"] = log_errs
    except Exception as exc:
        result["warnings"].append(f"log_errors: {exc}")

    # ── 3. Oracle ASH (if db_name provided) ─────────────────────────────
    if db_name:
        try:
            db = _db_by_name(db_name)
            ash_rows = oracle_connector.query_db(db, """
                SELECT NVL(wait_class, 'CPU') as wait_class,
                       NVL(event, 'On CPU') as event,
                       COUNT(*) as samples
                  FROM V$ACTIVE_SESSION_HISTORY
                 WHERE sample_time >= TO_DATE(:s, 'YYYY-MM-DD HH24:MI:SS')
                   AND sample_time <= TO_DATE(:e, 'YYYY-MM-DD HH24:MI:SS')
                   AND session_type = 'FOREGROUND'
                 GROUP BY wait_class, event
                 ORDER BY samples DESC
                 FETCH FIRST 15 ROWS ONLY
            """, {"s": start_iso[:19], "e": end_iso[:19]})
            total_ash = sum(r["samples"] for r in ash_rows)
            result["ash"] = {
                "total_samples": total_ash,
                "db": db_name,
                "top_events": [
                    {**dict(r), "pct": round(r["samples"] * 100.0 / total_ash, 1) if total_ash else 0}
                    for r in ash_rows[:10]
                ],
            }
        except Exception as exc:
            result["warnings"].append(f"ash: {exc}")

    # ── 4. IB errors (PSAPMSGPUBHDR) ─────────────────────────────────────
    try:
        if ptmetadata.has_table(env, "PSAPMSGPUBHDR"):
            ib_rows = psdb.query(env, """
                SELECT IBTRANSACTIONID, IB_OPERATIONNAME, QUEUENAME, PUBSTATUS,
                       PUBNODE, ORIGPUBNODE, CREATEDTTM, STATUSSTRING
                  FROM SYSADM.PSAPMSGPUBHDR
                 WHERE PUBSTATUS NOT IN ('0','1','2')
                   AND CREATEDTTM >= TO_DATE(:s, 'YYYY-MM-DD HH24:MI:SS')
                   AND CREATEDTTM <= TO_DATE(:e, 'YYYY-MM-DD HH24:MI:SS')
                 ORDER BY CREATEDTTM DESC
                 FETCH FIRST 30 ROWS ONLY
            """, {"s": start_iso[:19], "e": end_iso[:19]})
            result["ib_errors"] = [dict(r) for r in ib_rows]
    except Exception as exc:
        result["warnings"].append(f"ib_errors: {exc}")

    # ── 5. Build unified timeline ─────────────────────────────────────────
    timeline = []
    for r in result["process_failures"]:
        ts = str(r.get("rqstdttm") or r.get("begindttm") or "")
        timeline.append({
            "ts": ts, "type": "process_fail",
            "label": f"Process FAILED: {r.get('prcstype','')} {r.get('prcsname','')} (inst {r.get('prcsinstance','')})",
            "severity": "error", "detail": r,
        })
    for r in result["log_errors"]:
        timeline.append({
            "ts": r.get("ts", ""), "type": "log_error",
            "label": f"[{r.get('source','')}] {(r.get('message') or '')[:100]}",
            "severity": "error" if r.get("level") == "ERROR" else "warn", "detail": r,
        })
    for r in result["ib_errors"]:
        timeline.append({
            "ts": str(r.get("createdttm", "")), "type": "ib_error",
            "label": f"IB {r.get('pubstatus','')}: {r.get('ib_operationname','')} [{r.get('queuename','')}] {r.get('origpubnode','')}→{r.get('pubnode','')}",
            "severity": "error", "detail": r,
        })
    timeline.sort(key=lambda x: x.get("ts", ""), reverse=True)
    result["timeline"] = timeline[:200]

    result["summary"] = {
        "process_failures": len(result["process_failures"]),
        "log_errors": len(result["log_errors"]),
        "ib_errors": len(result["ib_errors"]),
        "ash_samples": result["ash"]["total_samples"] if result["ash"] else None,
        "timeline_events": len(result["timeline"]),
    }
    return result
