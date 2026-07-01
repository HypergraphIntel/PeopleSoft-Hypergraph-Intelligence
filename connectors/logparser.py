"""
Log line parsers for each supported log type.

Each parser accepts a single text line and returns a dict (or None to skip).

Supported types:
  pia_access    — WebLogic PIA NCSA extended access log
  pia_error     — WebLogic PIA stderr / error log
  appsrv        — PeopleSoft APPSRV_MMDD.LOG (Tuxedo app server)
  tuxedo        — Tuxedo ULOG.MMDDYY domain-level log
  apache_access — Apache / nginx combined access log (also F5 HSL iRule)
  apache_error  — Apache / nginx error log
  f5_access     — alias for apache_access (HSL iRules output NCSA combined)
"""

import re
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# PeopleSoft URL patterns:
#   /psp/{site}/{portal}/{node}/c/{MENU}.{COMPONENT}.{PAGE}.GBL
#   /psp/{site}/{portal}/{node}/c/{MENU}.{COMPONENT}.GBL   (no separate page)
#   /pspc/...  (portal)
_PS_URL_RE = re.compile(
    r"/psp[c]?/[^/]+/[^/]+/[^/]+/[cC]/([A-Z0-9_$]+)\.([A-Z0-9_$]+)(?:\.([A-Z0-9_$]+))?\.GBL",
    re.IGNORECASE,
)

def _extract_ps_path(url: str) -> dict:
    """Extract menu/component/page from a PeopleSoft URL."""
    m = _PS_URL_RE.search(url)
    if m:
        menu      = m.group(1).upper()
        component = m.group(2).upper()
        page      = m.group(3).upper() if m.group(3) else component
        return {"menu": menu, "component": component, "page": page}
    return {}


_OBJ_RE = re.compile(
    r"\b(ORA-\d{5}|SQLSTATE[\s=]+\S+|"
    r"(?:Record|Component|Page|Field|AE|SQL)\s+([A-Z][A-Z0-9_$]{1,30}))\b",
    re.IGNORECASE,
)

_ORA_RE    = re.compile(r"\b(ORA-\d{5})\b")
_OPRID_RE  = re.compile(r"\bN\.OPRID=([A-Z0-9_$@.]{1,30})\b", re.IGNORECASE)
_PC_OBJ_RE = re.compile(r"\b([A-Z][A-Z0-9_$]{2,30})\s+PeopleCode\b", re.IGNORECASE)

def _extract_error_codes(text: str) -> list[str]:
    codes = []
    for m in _ORA_RE.finditer(text):
        c = m.group(1)
        if c not in codes:
            codes.append(c)
    return codes

def _extract_object_ref(text: str) -> Optional[str]:
    """Best-effort extraction of a PS object name from a log message."""
    m = _PC_OBJ_RE.search(text)
    if m:
        return m.group(1).upper()
    return None


# ---------------------------------------------------------------------------
# PIA access log  (NCSA extended — space-delimited, date in [DD/Mon/YYYY:HH:MM:SS tz])
# Example:
#   10.0.0.1 - GUACUSER [01/Jul/2026:09:15:22 +0000] "GET /psp/HCM/... HTTP/1.1" 200 4321 "-" "Mozilla/5.0"
# ---------------------------------------------------------------------------

_NCSA_RE = re.compile(
    r'(?P<ip>\S+)\s+'
    r'\S+\s+'
    r'(?P<oprid>\S+)\s+'
    r'\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<url>\S+)\s+\S+"\s+'
    r'(?P<status>\d+)\s+'
    r'(?P<bytes>\S+)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<useragent>[^"]*)")?'
    r'(?:\s+(?P<ms>\d+))?',
)

_NCSA_DT_FMT = "%d/%b/%Y:%H:%M:%S %z"

def _parse_ncsa_ts(raw: str) -> Optional[datetime]:
    try:
        return datetime.strptime(raw, _NCSA_DT_FMT)
    except ValueError:
        return None


def parse_pia_access(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    m = _NCSA_RE.match(line)
    if not m:
        return None

    ts_raw = m.group("ts")
    ts = _parse_ncsa_ts(ts_raw)
    if ts is None:
        return None

    oprid = m.group("oprid")
    if oprid == "-":
        oprid = None

    url   = m.group("url")
    ps    = _extract_ps_path(url)
    status = int(m.group("status"))

    bytes_raw = m.group("bytes")
    byte_count = int(bytes_raw) if bytes_raw.isdigit() else 0

    ms_raw = m.group("ms")
    ms = int(ms_raw) if ms_raw else None

    return {
        "log_type":  "pia_access",
        "ts":        ts.astimezone(timezone.utc).replace(tzinfo=None),
        "ip":        m.group("ip"),
        "oprid":     oprid,
        "method":    m.group("method"),
        "url":       url,
        "component": ps.get("component"),
        "page":      ps.get("page"),
        "menu":      ps.get("menu"),
        "status":    status,
        "bytes":     byte_count,
        "ms":        ms,
        "useragent": m.group("useragent") or None,
        "is_error":  status >= 500,
        "error_codes": [],
        "object_ref": ps.get("component"),
        "raw":       line,
    }


# ---------------------------------------------------------------------------
# PIA error / stderr log
# WebLogic mixes several formats; we capture anything that looks like a problem.
# ---------------------------------------------------------------------------

_PIA_ERR_TS_RE = re.compile(r"####<(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\w+\s+\d{4})>")
_PIA_ERR_MSG_RE = re.compile(r"<([^>]{5,200})>\s*$")

def parse_pia_error(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line or line.startswith("#"):
        return None

    ts_m = _PIA_ERR_TS_RE.search(line)
    ts = None
    if ts_m:
        try:
            ts = datetime.strptime(ts_m.group(1), "%a %b %d %H:%M:%S %Z %Y")
        except ValueError:
            pass

    if ts is None:
        ts = datetime.utcnow()

    oprid_m = _OPRID_RE.search(line)
    oprid = oprid_m.group(1).upper() if oprid_m else None

    error_codes = _extract_error_codes(line)
    obj_ref = _extract_object_ref(line)

    return {
        "log_type":    "pia_error",
        "ts":          ts,
        "oprid":       oprid,
        "level":       "ERROR",
        "message":     line[:2000],
        "error_codes": error_codes,
        "object_ref":  obj_ref,
        "is_error":    True,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# APPSRV log  (PeopleSoft app server: APPSRV_MMDD.LOG)
# Format examples:
#   PSAPPSRV.12345 (0) [07/01/26 09:15:22] (1) N.OPRID=GUACUSER...
#   PSAPPSRV.12345 (0) [07/01/26 09:15:22] (1) ORA-00942: table or view does not exist
# ---------------------------------------------------------------------------

_APPSRV_HEADER_RE = re.compile(
    r"(?P<proc>[A-Z]+\.\d+)\s+\(\d+\)\s+\[(?P<ts>\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\]\s+\(\d+\)\s+(?P<msg>.+)",
)
_APPSRV_DT_FMT = "%m/%d/%y %H:%M:%S"

def parse_appsrv(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    m = _APPSRV_HEADER_RE.match(line)
    if not m:
        return None

    try:
        ts = datetime.strptime(m.group("ts"), _APPSRV_DT_FMT)
    except ValueError:
        return None

    msg = m.group("msg")
    oprid_m = _OPRID_RE.search(msg)
    oprid = oprid_m.group(1).upper() if oprid_m else None

    error_codes = _extract_error_codes(msg)
    obj_ref = _extract_object_ref(msg)
    is_error = bool(error_codes) or "error" in msg.lower() or "fatal" in msg.lower()

    level = "ERROR" if is_error else "INFO"

    return {
        "log_type":    "appsrv",
        "ts":          ts,
        "process":     m.group("proc"),
        "oprid":       oprid,
        "level":       level,
        "message":     msg[:2000],
        "error_codes": error_codes,
        "object_ref":  obj_ref,
        "is_error":    is_error,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Tuxedo ULOG  (TUXLOG.MMDDYY or ULOG.MMDDYY)
# Format: 092531.pshcm01!PSMSTPRC.30012.1.0: Jul  1 09:25:31 ...
# ---------------------------------------------------------------------------

_TUXEDO_RE = re.compile(
    r"(?P<ts>\w{3}\s+\d+\s+[\d:]+)\s+(?P<host>\S+)!(?P<proc>[^.]+\.\d+\.\d+\.\d+):\s+(?P<msg>.+)"
)
_TUXEDO_DT_FMT = "%b %d %H:%M:%S"

def parse_tuxedo(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None

    # Tuxedo lines start with the short time then have full datetime inside
    # Try to pull a datetime; year is not in the timestamp so use current year
    m = _TUXEDO_RE.search(line)
    if not m:
        return None

    ts_str = m.group("ts")
    try:
        ts = datetime.strptime(f"{datetime.utcnow().year} {ts_str.strip()}", "%Y %b %d %H:%M:%S")
    except ValueError:
        ts = datetime.utcnow()

    msg = m.group("msg")
    error_codes = _extract_error_codes(msg)
    is_error = bool(error_codes) or any(w in msg.lower() for w in ("error", "fatal", "abort", "fail"))

    return {
        "log_type":    "tuxedo",
        "ts":          ts,
        "host":        m.group("host"),
        "process":     m.group("proc"),
        "oprid":       None,
        "level":       "ERROR" if is_error else "INFO",
        "message":     msg[:2000],
        "error_codes": error_codes,
        "object_ref":  _extract_object_ref(msg),
        "is_error":    is_error,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Apache / nginx combined access  (also F5 HSL iRule output)
# Same as NCSA but without the 4th ms field; reuse NCSA parser.
# ---------------------------------------------------------------------------

def parse_apache_access(line: str) -> Optional[dict]:
    row = parse_pia_access(line)
    if row:
        row["log_type"] = "apache_access"
    return row


parse_f5_access = parse_apache_access


# ---------------------------------------------------------------------------
# Apache / nginx error log
# Format: [Tue Jul 01 09:15:22.123456 2026] [error] [pid 1234] [client 10.0.0.1:port] message
# ---------------------------------------------------------------------------

_APACHE_ERR_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\]\s+\[(?P<level>[^\]]+)\](?:\s+\[pid\s+\d+\])?\s+(?P<msg>.+)"
)
_APACHE_ERR_DT_FMT = "%a %b %d %H:%M:%S.%f %Y"
_APACHE_ERR_DT_FMT2 = "%a %b %d %H:%M:%S %Y"

def parse_apache_error(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    m = _APACHE_ERR_RE.match(line)
    if not m:
        return None

    ts = None
    ts_raw = m.group("ts")
    for fmt in (_APACHE_ERR_DT_FMT, _APACHE_ERR_DT_FMT2):
        try:
            ts = datetime.strptime(ts_raw, fmt)
            break
        except ValueError:
            pass
    if ts is None:
        ts = datetime.utcnow()

    msg     = m.group("msg")
    level   = m.group("level").upper()
    error_codes = _extract_error_codes(msg)

    return {
        "log_type":    "apache_error",
        "ts":          ts,
        "oprid":       None,
        "level":       level,
        "message":     msg[:2000],
        "error_codes": error_codes,
        "object_ref":  _extract_object_ref(msg),
        "is_error":    level in ("ERROR", "CRIT", "ALERT", "EMERG"),
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_PARSERS = {
    "pia_access":    parse_pia_access,
    "pia_error":     parse_pia_error,
    "appsrv":        parse_appsrv,
    "tuxedo":        parse_tuxedo,
    "apache_access": parse_apache_access,
    "apache_error":  parse_apache_error,
    "f5_access":     parse_f5_access,
}


def parse_line(log_type: str, line: str) -> Optional[dict]:
    """Parse a single log line using the parser for log_type. Returns None to skip."""
    parser = _PARSERS.get(log_type)
    if parser is None:
        raise ValueError(f"Unknown log type: {log_type!r}. Valid: {list(_PARSERS)}")
    return parser(line)
