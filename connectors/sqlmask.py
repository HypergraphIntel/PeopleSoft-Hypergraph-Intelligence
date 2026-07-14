"""
Deterministic data masking engine — SQL Proxy Phase 11.

Purpose: let the AI Assistant see the *structure* of a query result (row
counts, joins, non-sensitive columns) while every sensitive value is
replaced with a stable, non-reversible token. The same real value always
maps to the same token everywhere (across columns, across tables, across
queries), so cross-table joins and troubleshooting still work for the AI —
it just never learns the real identity. A human operator can look a token
up in the vault to get the real value back; the AI never has that path.

See SQL_PROXY.md (repo root) for the original design sketch and
ROADMAP.md's "Phase 11 — SQL Proxy" section for what was actually built and
why (this reuses connectors/sqlws.py's validation/execution/audit path
rather than reimplementing it — this module only does masking).
"""

import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH = DATA_DIR / "sql_proxy_vault.db"
CONFIG_PATH = paths.CONFIG_FILE

# Fallback catalog/salt used only if config.json has no "sql_proxy" section —
# real deployments should override both in config.json.
_DEFAULT_SALT = "deathstar-sql-proxy-default-salt-change-me"
_DEFAULT_CATALOG = {
    "EMPLID":       "EMP",
    "OPRID":        "USER",
    "USERID":       "USER",
    "NAME":         "PERSON",
    "FIRST_NAME":   "PERSON",
    "LAST_NAME":    "PERSON",
    "NAME1":        "PERSON",
    "EMAIL_ADDR":   "EMAIL",
    "EMAILID":      "EMAIL",
    "PHONE":        "PHONE",
    "EXTENSION":    "PHONE",
    "ADDRESS1":     "ADDR",
    "ADDRESS2":     "ADDR",
    "ADDRESS3":     "ADDR",
    "ADDRESS4":     "ADDR",
    "NATIONAL_ID":  "SSN",
    "SSN":          "SSN",
    "BIRTHDATE":    "DOB",
    "BANK_ACCOUNT": "ACCT",
    "ACCOUNT_NUM":  "ACCT",
    "DEPTID":       "DEPT",
    "VENDOR_ID":    "VENDOR",
}
# Regex fallbacks for custom-field variants that don't match the exact-name
# catalog above (e.g. CUST_SSN, HOME_EMAIL_ADDR).
_DEFAULT_PATTERNS = [
    (re.compile(r"SSN$|_SSN$|NATIONAL_ID"), "SSN"),
    (re.compile(r"EMAIL"), "EMAIL"),
    (re.compile(r"PHONE"), "PHONE"),
    (re.compile(r"^ADDRESS\d*$"), "ADDR"),
    (re.compile(r"^EMPLID$"), "EMP"),
    (re.compile(r"^(OPRID|USERID)$"), "USER"),
]


def _load_proxy_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return cfg.get("sql_proxy", {}) or {}


def _salt() -> str:
    return _load_proxy_config().get("salt") or _DEFAULT_SALT


def _catalog() -> dict:
    configured = _load_proxy_config().get("sensitive_columns")
    return {k.upper(): v for k, v in configured.items()} if configured else dict(_DEFAULT_CATALOG)


def category_for_column(column_name: str) -> str | None:
    """Return the sensitivity category for a column name, or None if the
    column isn't configured as sensitive (i.e. should pass through unmasked)."""
    col = (column_name or "").strip().upper()
    catalog = _catalog()
    if col in catalog:
        return catalog[col]
    for pattern, category in _DEFAULT_PATTERNS:
        if pattern.search(col):
            return category
    return None


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS token_vault (
                category     TEXT NOT NULL,
                real_value   TEXT NOT NULL,
                masked_token TEXT NOT NULL,
                created_ts   TEXT NOT NULL,
                last_used_ts TEXT NOT NULL,
                PRIMARY KEY (category, real_value)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_vault_token
                ON token_vault(masked_token);
        """)


def _generate_token(category: str, real_value: str) -> str:
    digest = hmac.new(
        _salt().encode("utf-8"),
        real_value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:8]
    return f"{category}_{digest}"


def mask_value(column_name: str, value) -> object:
    """Mask a single value if its column is sensitive; pass through
    unchanged (including None) otherwise. Deterministic and vault-backed —
    repeated calls with the same real value return the same token."""
    if value is None:
        return None
    category = category_for_column(column_name)
    if category is None:
        return value

    real_value = str(value)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    token = _generate_token(category, real_value)

    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT masked_token FROM token_vault WHERE category=? AND real_value=?",
            (category, real_value),
        ).fetchone()
        if row:
            con.execute(
                "UPDATE token_vault SET last_used_ts=? WHERE category=? AND real_value=?",
                (now, category, real_value),
            )
        else:
            con.execute(
                "INSERT INTO token_vault (category, real_value, masked_token, created_ts, last_used_ts) "
                "VALUES (?, ?, ?, ?, ?)",
                (category, real_value, token, now, now),
            )
    return token


def mask_result(result: dict) -> dict:
    """Mask a connectors.sqlws.execute_query()-shaped result dict in place
    (returns a new dict; does not mutate the input). Only 'columns'/'rows'
    are touched — statement_type, elapsed_ms, warnings, etc. pass through.
    Non-sensitive columns are returned exactly as executed; sensitive
    columns are replaced with their deterministic token."""
    columns = result.get("columns") or []
    rows = result.get("rows") or []
    col_names = [c.get("name") if isinstance(c, dict) else c for c in columns]

    masked_rows = []
    for row in rows:
        if isinstance(row, dict):
            masked_rows.append({k: mask_value(k, v) for k, v in row.items()})
        else:
            # row is a positional list/tuple aligned to col_names
            masked_rows.append([mask_value(col_names[i] if i < len(col_names) else None, v)
                                for i, v in enumerate(row)])

    masked = dict(result)
    masked["rows"] = masked_rows
    masked["masked"] = True
    return masked


def reveal(token: str) -> dict:
    """Human-only reverse lookup: masked token -> real value. Never call
    this from AI-facing code paths — connectors/ai_tools.py's dispatch
    table has no entry that reaches this function, by construction."""
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT category, real_value, created_ts, last_used_ts FROM token_vault WHERE masked_token=?",
            (token,),
        ).fetchone()
    if not row:
        return {"found": False, "token": token}
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _conn() as con:
        con.execute("UPDATE token_vault SET last_used_ts=? WHERE masked_token=?", (now, token))
    return {
        "found": True,
        "token": token,
        "category": row["category"],
        "real_value": row["real_value"],
        "created_ts": row["created_ts"],
        "last_used_ts": row["last_used_ts"],
    }


def vault_stats() -> dict:
    """Introspection only — counts, not values."""
    init_db()
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) AS n FROM token_vault").fetchone()["n"]
        by_category = con.execute(
            "SELECT category, COUNT(*) AS n FROM token_vault GROUP BY category ORDER BY n DESC"
        ).fetchall()
    return {
        "total_tokens": total,
        "by_category": [{"category": r["category"], "count": r["n"]} for r in by_category],
    }
