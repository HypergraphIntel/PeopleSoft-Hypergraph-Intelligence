"""
SQL Workspace connector — safe, read-only SQL execution against PeopleSoft Oracle databases.

Safety model:
- Block all DML, DDL, PL/SQL, and administrative statements.
- Only SELECT and WITH queries are executed. EXPLAIN PLAN FOR <select> is handled separately.
- Validate before every execution — anything that cannot be confidently classified as
  read-only is rejected with a structured error.
- Result sets are paged via ROW_NUMBER() wrapper — never load unbounded data into memory.
- All executions and validations are recorded in audit and history logs.
"""

import csv
import io
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import oracledb

CONFIG = Path("/opt/deathstar-api/config.json")
HISTORY_PATH = Path("/opt/deathstar-api/data/sqlws_history.jsonl")
AUDIT_PATH   = Path("/opt/deathstar-api/logs/sqlws_audit.jsonl")

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE     = 1000

# Keywords that must never appear as SQL statement keywords in user-submitted SQL.
# Checked against string-literal-stripped, comment-stripped SQL.
BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "BEGIN", "DECLARE", "CALL", "EXEC",
    "EXECUTE", "ANALYZE", "COMMENT", "FLASHBACK", "PURGE", "LOCK",
    "COMMIT", "ROLLBACK", "SAVEPOINT",
]

ALLOWED_LEADING = frozenset(["SELECT", "WITH"])


# ──────────────────────────────────────────────────────────────────────────────
# SQL parsing helpers
# ──────────────────────────────────────────────────────────────────────────────

def _strip_block_comments(sql: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)


def _strip_line_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", " ", sql)


def _strip_string_literals(sql: str) -> str:
    """Replace string literal contents with empty placeholders.
    Handles Oracle-style escaped quotes: 'it''s a test' → ''."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


def normalize_sql(sql: str) -> str:
    """Strip comments and normalize whitespace."""
    sql = _strip_block_comments(sql)
    sql = _strip_line_comments(sql)
    return re.sub(r"\s+", " ", sql).strip()


def classify_sql(sql: str) -> dict:
    """Return the leading keyword of a normalized SQL statement."""
    normalized = normalize_sql(sql)
    m = re.match(r"\s*(\w+)", normalized)
    keyword = m.group(1).upper() if m else "UNKNOWN"
    return {"statement_type": keyword, "normalized": normalized}


def validate_readonly(sql: str) -> dict:
    """
    Validate that sql is a safe, read-only statement.

    Returns:
        {
            "allowed": bool,
            "statement_type": str,
            "warnings": list[str],
            "blocked_reason": str | None,
        }
    """
    if not sql or not sql.strip():
        return {
            "allowed": False,
            "statement_type": None,
            "warnings": [],
            "blocked_reason": "Empty SQL",
        }

    stripped  = _strip_block_comments(sql)
    stripped  = _strip_line_comments(stripped)
    normalized = re.sub(r"\s+", " ", stripped).strip()
    no_strings = _strip_string_literals(normalized)

    # Reject multiple statements.
    if ";" in no_strings:
        return {
            "allowed": False,
            "statement_type": "MULTIPLE",
            "warnings": [],
            "blocked_reason": "Multiple statements separated by semicolons are not allowed",
        }

    # Identify leading keyword.
    m = re.match(r"\s*(\w+)", normalized)
    leading = m.group(1).upper() if m else "UNKNOWN"

    if leading not in ALLOWED_LEADING:
        return {
            "allowed": False,
            "statement_type": leading,
            "warnings": [],
            "blocked_reason": f"{leading} statements are not allowed",
        }

    # Scan for blocked keywords with word-boundary matching.
    for kw in BLOCKED_KEYWORDS:
        if re.search(r"\b" + kw + r"\b", no_strings, re.IGNORECASE):
            return {
                "allowed": False,
                "statement_type": leading,
                "warnings": [],
                "blocked_reason": f"{kw} statements are not allowed",
            }

    # Block DBMS_ package calls.
    if re.search(r"\bDBMS_\w+", no_strings, re.IGNORECASE):
        return {
            "allowed": False,
            "statement_type": leading,
            "warnings": [],
            "blocked_reason": "DBMS package calls are not allowed",
        }

    # Block dynamic SQL.
    if re.search(r"\bEXECUTE\s+IMMEDIATE\b", no_strings, re.IGNORECASE):
        return {
            "allowed": False,
            "statement_type": leading,
            "warnings": [],
            "blocked_reason": "Dynamic SQL (EXECUTE IMMEDIATE) is not allowed",
        }

    # Block UTL_ calls (file I/O, network, etc.)
    if re.search(r"\bUTL_\w+", no_strings, re.IGNORECASE):
        return {
            "allowed": False,
            "statement_type": leading,
            "warnings": [],
            "blocked_reason": "UTL package calls are not allowed",
        }

    # Block SYS privilege escalation patterns.
    if re.search(r"\bSYS\.(DBMS_|UTL_|KUPC\$|KUPV\$|KUPW\$|KUPF\$)", no_strings, re.IGNORECASE):
        return {
            "allowed": False,
            "statement_type": leading,
            "warnings": [],
            "blocked_reason": "SYS privilege escalation patterns are not allowed",
        }

    return {
        "allowed": True,
        "statement_type": leading,
        "warnings": [],
        "blocked_reason": None,
    }


def validate_explain(sql: str) -> dict:
    """
    Validate SQL for EXPLAIN PLAN execution.
    The user provides the query body (SELECT/WITH); we prefix EXPLAIN PLAN FOR.
    """
    result = validate_readonly(sql)
    return result


def extract_bind_names(sql: str) -> list:
    """Extract Oracle bind variable names (:name) from SQL."""
    stripped = _strip_block_comments(sql)
    stripped = _strip_line_comments(stripped)
    stripped = _strip_string_literals(stripped)
    names = re.findall(r":([A-Za-z_][A-Za-z0-9_$#]*)", stripped)
    seen = set()
    result = []
    for name in names:
        key = name.upper()
        if key not in seen:
            seen.add(key)
            result.append(name)
    return result


def _replace_bind_placeholders(sql: str, replacements: dict) -> str:
    """Replace bind placeholders outside strings/comments using uppercase keys."""
    if not replacements:
        return sql

    out = []
    i = 0
    n = len(sql)
    while i < n:
        if sql.startswith("--", i):
            j = sql.find("\n", i + 2)
            if j == -1:
                out.append(sql[i:])
                break
            out.append(sql[i:j])
            i = j
            continue

        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j == -1:
                out.append(sql[i:])
                break
            out.append(sql[i:j + 2])
            i = j + 2
            continue

        if sql[i] == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'" and j + 1 < n and sql[j + 1] == "'":
                    j += 2
                    continue
                if sql[j] == "'":
                    j += 1
                    break
                j += 1
            out.append(sql[i:j])
            i = j
            continue

        if sql[i] == ":" and i + 1 < n:
            m = re.match(r":([A-Za-z_][A-Za-z0-9_$#]*)", sql[i:])
            if m:
                name = m.group(1)
                replacement = replacements.get(name.upper())
                out.append(f":{replacement}" if replacement else m.group(0))
                i += len(m.group(0))
                continue

        out.append(sql[i])
        i += 1

    return "".join(out)


def _prepare_user_binds(sql: str, binds: dict) -> tuple[str, dict]:
    """Rewrite user bind placeholders to SQL Workspace-safe internal names."""
    normalized_binds = {}
    for raw_name, value in (binds or {}).items():
        name = str(raw_name).strip().lstrip(":")
        if not name:
            continue
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_$#]*$", name):
            raise ValueError(f"Invalid bind variable name: {raw_name}")
        normalized_binds[name.upper()] = value

    replacements = {}
    exec_binds = {}
    for idx, name in enumerate(extract_bind_names(sql), start=1):
        key = name.upper()
        if key not in normalized_binds:
            continue
        safe_name = f"sqlws_b_{idx}"
        replacements[key] = safe_name
        exec_binds[safe_name] = normalized_binds[key]

    return _replace_bind_placeholders(sql, replacements), exec_binds


# ──────────────────────────────────────────────────────────────────────────────
# Database connection
# ──────────────────────────────────────────────────────────────────────────────

def _load_env(env_name: str) -> dict:
    data = json.loads(CONFIG.read_text())
    name_up = env_name.upper()
    for env in data["peoplesoft"]["environments"]:
        if env["name"].upper() == name_up:
            return env
    raise ValueError(f"PeopleSoft environment not found: {env_name}")


def _connect(env_name: str):
    env = _load_env(env_name)
    dsn = f'{env["host"]}:{env["port"]}/{env["service"]}'
    return oracledb.connect(user=env["user"], password=env["password"], dsn=dsn)


def list_envs() -> list:
    data = json.loads(CONFIG.read_text())
    return [e["name"] for e in data["peoplesoft"]["environments"]]


# ──────────────────────────────────────────────────────────────────────────────
# Value cleaning
# ──────────────────────────────────────────────────────────────────────────────

def _clean_value(v):
    """Convert Oracle-returned values to JSON-serialisable types."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "read"):
        try:
            return v.read()
        except Exception:
            return "<LOB>"
    return str(v)


def _oracle_type_name(type_code) -> str:
    """Map oracledb type constant to a readable Oracle type name."""
    mapping = {
        oracledb.DB_TYPE_VARCHAR: "VARCHAR2",
        oracledb.DB_TYPE_CHAR: "CHAR",
        oracledb.DB_TYPE_NUMBER: "NUMBER",
        oracledb.DB_TYPE_DATE: "DATE",
        oracledb.DB_TYPE_TIMESTAMP: "TIMESTAMP",
        oracledb.DB_TYPE_TIMESTAMP_TZ: "TIMESTAMP WITH TZ",
        oracledb.DB_TYPE_TIMESTAMP_LTZ: "TIMESTAMP WITH LOCAL TZ",
        oracledb.DB_TYPE_LONG: "LONG",
        oracledb.DB_TYPE_CLOB: "CLOB",
        oracledb.DB_TYPE_NCLOB: "NCLOB",
        oracledb.DB_TYPE_BLOB: "BLOB",
        oracledb.DB_TYPE_RAW: "RAW",
        oracledb.DB_TYPE_LONG_RAW: "LONG RAW",
        oracledb.DB_TYPE_NVARCHAR: "NVARCHAR2",
        oracledb.DB_TYPE_NCHAR: "NCHAR",
        oracledb.DB_TYPE_BINARY_FLOAT: "BINARY_FLOAT",
        oracledb.DB_TYPE_BINARY_DOUBLE: "BINARY_DOUBLE",
        oracledb.DB_TYPE_ROWID: "ROWID",
        oracledb.DB_TYPE_CURSOR: "CURSOR",
    }
    return mapping.get(type_code, str(type_code))


# ──────────────────────────────────────────────────────────────────────────────
# Paged query execution
# ──────────────────────────────────────────────────────────────────────────────

def _strip_fetch_clause(sql: str) -> str:
    """Remove trailing FETCH FIRST/NEXT ... ROWS ONLY from user SQL so it doesn't
    conflict with our ROW_NUMBER paging envelope."""
    return re.sub(
        r"\s+FETCH\s+(FIRST|NEXT)\s+.*?\s+ROWS\s+(ONLY|WITH\s+TIES)\s*$",
        "",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    ).rstrip()


def _build_paged_sql(inner_sql: str, start_row: int, end_row: int) -> str:
    """Wrap the user's SELECT in an Oracle ROW_NUMBER paging envelope.

    Bind variable names must start with a letter in Oracle, so we use
    'sqlws_rn_s' and 'sqlws_rn_e' (not '__rn_start').
    """
    cleaned = _strip_fetch_clause(inner_sql)
    return (
        "SELECT * FROM (\n"
        "  SELECT q.*, ROW_NUMBER() OVER (ORDER BY 1) AS sqlws_rn\n"
        "  FROM (\n"
        f"    {cleaned}\n"
        "  ) q\n"
        ") WHERE sqlws_rn BETWEEN :sqlws_rn_s AND :sqlws_rn_e"
    )


MAX_TIMEOUT_SECS = 600


def _normalize_timeout_secs(value) -> int:
    """Normalize timeout input to a safe integer number of seconds."""
    if value is None or isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return 0
    else:
        try:
            seconds = int(str(value).strip())
        except (TypeError, ValueError):
            return 0
    if seconds < 0:
        return 0
    return min(seconds, MAX_TIMEOUT_SECS)


def execute_query(
    env_name: str,
    sql: str,
    binds: dict = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_rows: int = None,
    timeout_secs: int = 0,
    cancel_check=None,
    source: str = "human",
) -> dict:
    """
    Execute a read-only SELECT against the named PeopleSoft environment.

    source: tags the audit/history entry ("human" for SQL Workspace UI use,
    "ai" for AI-tool-originated executions — see connectors/ai_tools.py's
    execute_sql tool) so the one audit trail (logs/sqlws_audit.jsonl)
    distinguishes who/what ran a query without needing a second log.

    Parameters
    ----------
    env_name     : PeopleSoft environment name (e.g. "HCM")
    sql          : User-provided SQL text
    binds        : Bind variable dict  {name: value}
    page         : 1-based page number
    page_size    : Rows per page (capped at MAX_PAGE_SIZE)
    max_rows     : Hard limit on total rows returned (defaults to page_size)
    timeout_secs : Server-side call timeout in seconds (0 = no timeout, capped at MAX_TIMEOUT_SECS)

    Returns a structured result dict suitable for direct JSON serialisation.
    """
    binds        = binds or {}
    page         = max(1, int(page))
    page_size    = max(1, min(int(page_size), MAX_PAGE_SIZE))
    max_rows     = int(max_rows) if max_rows else page_size
    max_rows     = max(1, min(max_rows, MAX_PAGE_SIZE))
    timeout_secs = _normalize_timeout_secs(timeout_secs)

    # Reserved paging bind names — reject if user accidentally uses them.
    reserved = {"sqlws_rn_s", "sqlws_rn_e"}
    conflict = reserved & {str(k).strip().lstrip(":").lower() for k in binds.keys()}
    if conflict:
        return {
            "env": env_name.upper(),
            "statement_type": None,
            "elapsed_ms": 0,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "page": page,
            "page_size": page_size,
            "truncated": False,
            "warnings": [],
            "blocked": True,
            "blocked_reason": f"Bind variable names are reserved by SQL Workspace: {sorted(conflict)}",
            "query_id": str(uuid.uuid4()),
        }

    try:
        safe_sql, safe_binds = _prepare_user_binds(sql, binds)
    except ValueError as exc:
        return {
            "env": env_name.upper(),
            "statement_type": None,
            "elapsed_ms": 0,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "page": page,
            "page_size": page_size,
            "truncated": False,
            "warnings": [],
            "blocked": True,
            "blocked_reason": str(exc),
            "query_id": str(uuid.uuid4()),
        }

    query_id = str(uuid.uuid4())
    ts       = datetime.now(timezone.utc).isoformat()

    # Validate before touching the database.
    validation = validate_readonly(sql)

    if not validation["allowed"]:
        _history_append({
            "id": query_id,
            "timestamp": ts,
            "env": env_name.upper(),
            "sql": sql,
            "binds": _safe_binds_for_log(binds),
            "elapsed_ms": 0,
            "row_count": 0,
            "status": "blocked",
            "blocked_reason": validation["blocked_reason"],
            "pinned": False,
            "source": source,
        })
        audit_write("blocked", {
            "query_id": query_id,
            "env": env_name.upper(),
            "source": source,
            "sql": sql[:500],
            "blocked_reason": validation["blocked_reason"],
        })
        return {
            "env": env_name.upper(),
            "statement_type": validation["statement_type"],
            "elapsed_ms": 0,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "page": page,
            "page_size": page_size,
            "truncated": False,
            "warnings": [],
            "blocked": True,
            "blocked_reason": validation["blocked_reason"],
            "query_id": query_id,
        }

    start_row = (page - 1) * page_size + 1
    end_row   = start_row + page_size - 1

    paged_sql = _build_paged_sql(safe_sql, start_row, end_row)
    exec_binds = dict(safe_binds)
    exec_binds["sqlws_rn_s"] = start_row
    exec_binds["sqlws_rn_e"] = end_row

    t0 = time.monotonic()
    status = "success"
    error_msg = None
    timed_out = False
    cancelled = False
    columns = []
    rows = []
    warnings = validation.get("warnings", [])

    if cancel_check is not None and cancel_check():
        cancelled = True
        status = "cancelled"
        warnings.append("Query execution was cancelled by the client.")

    if not cancelled:
        try:
            conn = _connect(env_name)
            try:
                cur = conn.cursor()
                if timeout_secs and hasattr(cur, "callTimeout"):
                    try:
                        cur.callTimeout = timeout_secs * 1000
                    except Exception:
                        warnings.append("Execution timeout is not supported by the current Oracle driver configuration.")

                if cancel_check is not None and cancel_check():
                    cancelled = True
                    status = "cancelled"
                    warnings.append("Query execution was cancelled by the client.")
                else:
                    cur.execute(paged_sql, exec_binds)

                    # Build column metadata from cursor description, skip the rn sentinel.
                    raw_cols = cur.description or []
                    col_meta = []
                    col_indices = []
                    for i, desc in enumerate(raw_cols):
                        if desc[0].upper() == "SQLWS_RN":
                            continue
                        col_meta.append({
                            "name": desc[0],
                            "type": _oracle_type_name(desc[1]),
                        })
                        col_indices.append(i)
                    columns = col_meta

                    # Fetch rows.
                    for raw_row in cur.fetchall():
                        row = {}
                        for meta, idx in zip(col_meta, col_indices):
                            row[meta["name"]] = _clean_value(raw_row[idx])
                        rows.append(row)
            finally:
                conn.close()
        except oracledb.Error as exc:
            status = "error"
            error_msg = str(exc)
            if "DPI-1067" in error_msg or "call timeout" in error_msg.lower():
                timed_out = True
                status = "timeout"
                error_msg = f"Query exceeded the {timeout_secs}s timeout and was cancelled."
            elif "cancel" in error_msg.lower() or "abort" in error_msg.lower():
                cancelled = True
                status = "cancelled"
                error_msg = "Query execution was cancelled."
        except Exception as exc:
            status = "error"
            error_msg = str(exc)

    elapsed_ms = round((time.monotonic() - t0) * 1000)
    row_count  = len(rows)
    truncated  = row_count == page_size

    if error_msg:
        warnings.append(f"Execution error: {error_msg}")

    if timed_out:
        status = "timeout"
    elif cancelled:
        status = "cancelled"

    _history_append({
        "id": query_id,
        "timestamp": ts,
        "env": env_name.upper(),
        "sql": sql,
        "binds": _safe_binds_for_log(binds),
        "elapsed_ms": elapsed_ms,
        "row_count": row_count,
        "status": status,
        "blocked_reason": None,
        "pinned": False,
        "timed_out": timed_out,
        "cancelled": cancelled,
        "source": source,
    })

    audit_write("execute", {
        "query_id": query_id,
        "env": env_name.upper(),
        "source": source,
        "sql": sql[:500],
        "elapsed_ms": elapsed_ms,
        "row_count": row_count,
        "status": status,
        "page": page,
        "page_size": page_size,
    })

    result = {
        "env": env_name.upper(),
        "statement_type": validation["statement_type"],
        "elapsed_ms": elapsed_ms,
        "columns": columns,
        "rows": rows,
        "row_count": row_count,
        "page": page,
        "page_size": page_size,
        "truncated": truncated,
        "warnings": warnings,
        "blocked": False,
        "blocked_reason": None,
        "timed_out": timed_out,
        "cancelled": cancelled,
        "status": status,
        "query_id": query_id,
    }

    if error_msg:
        result["error"] = error_msg

    return result


# ──────────────────────────────────────────────────────────────────────────────
# EXPLAIN PLAN
# ──────────────────────────────────────────────────────────────────────────────

def explain_query(env_name: str, sql: str, binds: dict = None) -> dict:
    """
    Run EXPLAIN PLAN FOR <sql> then return DBMS_XPLAN.DISPLAY output.
    Only read-only SELECT/WITH statements are accepted.
    """
    binds    = binds or {}
    query_id = str(uuid.uuid4())
    ts       = datetime.now(timezone.utc).isoformat()

    validation = validate_explain(sql)

    if not validation["allowed"]:
        audit_write("explain_blocked", {
            "query_id": query_id,
            "env": env_name.upper(),
            "sql": sql[:500],
            "blocked_reason": validation["blocked_reason"],
        })
        return {
            "env": env_name.upper(),
            "allowed": False,
            "blocked_reason": validation["blocked_reason"],
            "plan": [],
            "warnings": [],
            "query_id": query_id,
        }

    t0 = time.monotonic()
    plan_lines = []
    warnings   = list(validation.get("warnings", []))
    error_msg  = None

    try:
        conn = _connect(env_name)
        try:
            cur = conn.cursor()
            # EXPLAIN PLAN FOR does not accept bind variables in Oracle
            # (the variables are irrelevant for plan generation — we pass dummies).
            # Use a unique statement_id to isolate our plan.
            stmt_id = f"SQLWS_{query_id[:8].upper()}"
            explain_sql = f"EXPLAIN PLAN SET STATEMENT_ID = '{stmt_id}' FOR {sql}"
            try:
                cur.execute(explain_sql)
            except oracledb.DatabaseError as exc:
                # Bind variable placeholders may cause issues; try without them.
                bare_sql = re.sub(r":\w+", "NULL", sql)
                explain_sql = f"EXPLAIN PLAN SET STATEMENT_ID = '{stmt_id}' FOR {bare_sql}"
                cur.execute(explain_sql)

            # Read back the plan.
            cur.execute(
                "SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY("
                "  statement_id => :stmt_id,"
                "  format       => 'ALL'))",
                {"stmt_id": stmt_id},
            )
            for row in cur.fetchall():
                plan_lines.append(str(row[0]) if row[0] is not None else "")
        finally:
            conn.close()
    except oracledb.DatabaseError as exc:
        error_msg = str(exc)
        if "ORA-01031" in error_msg or "insufficient privileges" in error_msg.lower():
            warnings.append(
                "EXPLAIN PLAN unavailable: insufficient privileges on PLAN_TABLE or DBMS_XPLAN"
            )
        else:
            warnings.append(f"EXPLAIN PLAN error: {error_msg}")
    except Exception as exc:
        error_msg = str(exc)
        warnings.append(f"EXPLAIN PLAN error: {error_msg}")

    elapsed_ms = round((time.monotonic() - t0) * 1000)

    audit_write("explain", {
        "query_id": query_id,
        "env": env_name.upper(),
        "sql": sql[:500],
        "elapsed_ms": elapsed_ms,
        "plan_lines": len(plan_lines),
        "warnings": warnings,
    })

    return {
        "env": env_name.upper(),
        "allowed": True,
        "blocked_reason": None,
        "plan": plan_lines,
        "elapsed_ms": elapsed_ms,
        "warnings": warnings,
        "query_id": query_id,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Schema browser
# ──────────────────────────────────────────────────────────────────────────────

def schema_search(env_name: str, q: str, limit: int = 50) -> dict:
    """
    Search for tables, views, and PeopleSoft records matching q.
    Returns combined results with object type and owner.
    """
    limit = max(1, min(int(limit), 200))
    q_clean = (q or "").strip().upper()
    owner_filter = None
    object_q = q_clean
    if "." in q_clean:
        owner_filter, object_q = q_clean.split(".", 1)
        owner_filter = owner_filter or None
        object_q = object_q or q_clean

    if owner_filter in ("PS", "PS_"):
        owner_filter = "SYSADM"
        if not object_q.startswith("PS_"):
            object_q = f"PS_{object_q}"

    ps_rec_q = object_q[3:] if object_q.startswith("PS_") else object_q
    pattern = f"%{object_q}%"
    ps_pattern = f"%{ps_rec_q}%"

    ps_results = []
    oracle_results = []
    warnings = []

    try:
        conn = _connect(env_name)
        try:
            cur = conn.cursor()

            # PeopleSoft record catalog.
            try:
                cur.execute(
                    """
                    SELECT recname, recdescr, sqltablename, rectype
                      FROM sysadm.psrecdefn
                     WHERE upper(recname) LIKE :ps_pattern
                        OR upper(recdescr) LIKE :ps_pattern
                        OR upper(NVL(sqltablename, 'PS_' || recname)) LIKE :pattern
                     ORDER BY
                       CASE
                         WHEN upper(recname) = :ps_exact THEN 0
                         WHEN upper(NVL(sqltablename, 'PS_' || recname)) = :obj_exact THEN 1
                         WHEN upper(recname) LIKE :ps_prefix THEN 2
                         WHEN upper(NVL(sqltablename, 'PS_' || recname)) LIKE :obj_prefix THEN 3
                         ELSE 4
                       END,
                       recname
                     FETCH FIRST :limit ROWS ONLY
                    """,
                    {
                        "pattern": pattern,
                        "ps_pattern": ps_pattern,
                        "obj_exact": object_q,
                        "ps_exact": ps_rec_q,
                        "obj_prefix": f"{object_q}%",
                        "ps_prefix": f"{ps_rec_q}%",
                        "limit": limit,
                    },
                )
                for row in cur.fetchall():
                    recname    = row[0]
                    recdescr   = row[1]
                    sqltable   = (row[2] or "").strip() or f"PS_{recname}"
                    ps_results.append({
                        "source": "peoplesoft",
                        "owner": "SYSADM",
                        "object_name": sqltable,
                        "object_type": "RECORD",
                        "description": (recdescr or "").strip(),
                        "ps_recname": recname,
                    })
            except oracledb.DatabaseError:
                warnings.append("PeopleSoft record catalog (PSRECDEFN) not accessible")

            # Oracle catalog: tables and views visible to this user.
            cur.execute(
                """
                SELECT owner, object_name, object_type
                  FROM all_objects
                 WHERE object_type IN ('TABLE', 'VIEW')
                   AND upper(object_name) LIKE :pattern
                   AND (:owner_filter IS NULL OR upper(owner) = :owner_filter)
                 ORDER BY
                   CASE WHEN upper(owner) = 'SYSADM' THEN 0 ELSE 1 END,
                   CASE
                     WHEN upper(object_name) = :obj_exact THEN 0
                     WHEN upper(object_name) LIKE :obj_prefix THEN 1
                     ELSE 2
                   END,
                   object_type, owner, object_name
                 FETCH FIRST :limit ROWS ONLY
                """,
                {
                    "pattern": pattern,
                    "owner_filter": owner_filter,
                    "obj_exact": object_q,
                    "obj_prefix": f"{object_q}%",
                    "limit": limit,
                },
            )
            for row in cur.fetchall():
                oracle_results.append({
                    "source": "oracle",
                    "owner": row[0],
                    "object_name": row[1],
                    "object_type": row[2],
                    "description": None,
                    "ps_recname": None,
                })
        finally:
            conn.close()
    except Exception as exc:
        warnings.append(f"Schema search error: {exc}")

    audit_write("schema_search", {"env": env_name.upper(), "q": q})

    results = []
    seen = set()
    for row in ps_results + oracle_results:
        key = (row["owner"], row["object_name"], row["object_type"])
        if key in seen:
            continue
        seen.add(key)
        results.append(row)
        if len(results) >= limit:
            break

    return {"results": results, "warnings": warnings}


def schema_columns(env_name: str, owner: str, object_name: str) -> dict:
    """Return column metadata for a table or view."""
    columns  = []
    warnings = []

    try:
        conn = _connect(env_name)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT column_id,
                       column_name,
                       data_type,
                       data_length,
                       data_precision,
                       data_scale,
                       nullable,
                       data_default
                  FROM all_tab_columns
                 WHERE upper(owner)      = upper(:owner)
                   AND upper(table_name) = upper(:table_name)
                 ORDER BY column_id
                """,
                {"owner": owner, "table_name": object_name},
            )
            for row in cur.fetchall():
                dtype = row[2]
                if dtype in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR") and row[3]:
                    dtype = f"{dtype}({row[3]})"
                elif dtype == "NUMBER":
                    if row[4] is not None and row[5] is not None:
                        dtype = f"NUMBER({row[4]},{row[5]})"
                    elif row[4] is not None:
                        dtype = f"NUMBER({row[4]})"
                columns.append({
                    "column_id": row[0],
                    "column_name": row[1],
                    "data_type": dtype,
                    "nullable": row[6] == "Y",
                    "data_default": _clean_value(row[7]),
                })
        finally:
            conn.close()
    except Exception as exc:
        warnings.append(f"Column lookup error: {exc}")

    audit_write("schema_columns", {
        "env": env_name.upper(),
        "owner": owner,
        "object_name": object_name,
    })

    return {
        "env": env_name.upper(),
        "owner": owner,
        "object_name": object_name,
        "columns": columns,
        "warnings": warnings,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Export helpers
# ──────────────────────────────────────────────────────────────────────────────

def export_csv(result: dict) -> str:
    """Convert an execution result dict to CSV text."""
    out = io.StringIO()
    cols = [c["name"] for c in result.get("columns", [])]
    writer = csv.writer(out)
    writer.writerow(cols)
    for row in result.get("rows", []):
        writer.writerow([row.get(c) for c in cols])
    return out.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# History management
# ──────────────────────────────────────────────────────────────────────────────

def _safe_binds_for_log(binds: dict) -> dict:
    """Return binds without any values that look like credentials."""
    return {k: str(v)[:200] for k, v in (binds or {}).items()}


def _history_append(entry: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _history_load_all() -> list:
    if not HISTORY_PATH.exists():
        return []
    entries = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def history_list(pinned_only: bool = False, limit: int = 100) -> list:
    """Return query history, newest first."""
    entries = _history_load_all()
    if pinned_only:
        entries = [e for e in entries if e.get("pinned")]
    # Deduplicate by id, keep last occurrence.
    seen = {}
    for entry in entries:
        seen[entry.get("id")] = entry
    entries = list(seen.values())
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries[:limit]


def history_pin(query_id: str, pinned: bool = True) -> dict:
    """Toggle pin state for a history entry by rewriting the file."""
    entries = _history_load_all()
    found = False
    updated = []
    for entry in entries:
        if entry.get("id") == query_id:
            entry = dict(entry)
            entry["pinned"] = pinned
            found = True
        updated.append(entry)

    if not found:
        return {"ok": False, "error": "Query ID not found"}

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        for entry in updated:
            f.write(json.dumps(entry, default=str) + "\n")

    audit_write("pin" if pinned else "unpin", {"query_id": query_id})
    return {"ok": True, "pinned": pinned}


def history_delete(query_id: str) -> dict:
    """Delete a history entry by id."""
    entries = _history_load_all()
    original_count = len(entries)
    entries = [e for e in entries if e.get("id") != query_id]

    if len(entries) == original_count:
        return {"ok": False, "error": "Query ID not found"}

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, default=str) + "\n")

    audit_write("history_delete", {"query_id": query_id})
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# Audit logging
# ──────────────────────────────────────────────────────────────────────────────

def audit_write(action: str, detail: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **detail,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
