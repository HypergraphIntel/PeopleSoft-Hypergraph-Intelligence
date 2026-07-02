"""
Log line parsers for each supported log type.

Each parser accepts a single text line and returns a dict (or None to skip).
Block parsers (igw_error_log) accept an entire content chunk and return list[dict].

Supported types:
  pia_access    — WebLogic PIA NCSA extended access log (PIA_access.log)
  pia_error     — WebLogic PIA stderr log (PIA_stderr*.log)
  pia_servlet   — PIA servlet activity log tab-separated (PIA_servlets*.log)
  pia_weblogic  — WebLogic domain log ####<...> format (PIA_weblogic.log)
  pia_stdout    — WebLogic JVM stdout (PIA_stdout*.log) — info only
  appsrv        — PeopleSoft APPSRV_MMDD.LOG.N (Tuxedo app server)
  tuxedo        — Tuxedo ULOG.MMDDYY domain-level log
  apache_access — Apache / nginx combined access log (also F5 HSL iRule)
  apache_error  — Apache / nginx error log
  f5_access     — alias for apache_access (HSL iRules output NCSA combined)
  igw_error_log — Integration Gateway errorLog.html (block parser)
"""

import json
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


_ORA_RE      = re.compile(r"\b(ORA-\d{5})\b")
_HTTP_ERR_RE = re.compile(r"\bHTTP[/ ](\d{3})\b")
# PCodeWTL: "PCodeWTL(1/3): Operation:SVC_NAME[method]" or just any PCodeWTL
_PCODEWOL_RE = re.compile(r"PCodeW[OT]L", re.IGNORECASE)
# Java IB exceptions
_IB_EXT_RE   = re.compile(r"ExternalApplicationException|HttpTargetConnector", re.IGNORECASE)

def _extract_error_codes(text: str) -> list[str]:
    codes: list[str] = []

    for m in _ORA_RE.finditer(text):
        c = m.group(1)
        if c not in codes:
            codes.append(c)

    for m in _HTTP_ERR_RE.finditer(text):
        c = f"HTTP_{m.group(1)}"
        if c not in codes:
            codes.append(c)

    # PeopleSoft-specific synthetic codes
    low = text.lower()
    if _PCODEWOL_RE.search(text):
        if "IB_PCODEWOL" not in codes:
            codes.append("IB_PCODEWOL")
    elif _IB_EXT_RE.search(text):
        if "IB_EXT_APP" not in codes:
            codes.append("IB_EXT_APP")

    if "authentication failed" in low or "invalid password" in low:
        if "AUTH_FAIL" not in codes:
            codes.append("AUTH_FAIL")
    elif "webprofile has set incorrectly" in low:
        if "WEBPROFILE_ERR" not in codes:
            codes.append("WEBPROFILE_ERR")

    return codes


# Patterns ordered by specificity — first match wins.
_OBJ_PATTERNS: list[tuple] = [
    # PCodeWTL Operation: SVC_NAME[method]
    (re.compile(r"Operation:\s*([A-Z][A-Z0-9_$]{2,50})\[", re.IGNORECASE), 1),
    # "Can not load remote categorys : NAME from node"
    (re.compile(r"load remote categor\w+\s*:\s*([A-Z][A-Z0-9_$]{2,50})\s+from", re.IGNORECASE), 1),
    # "Error: WebProfile has set incorrectly, RECORD_NAME, null"
    (re.compile(r"WebProfile has set incorrectly,\s*([A-Z][A-Z0-9_$]{2,50}),", re.IGNORECASE), 1),
    # "Invalid password for user OPRID@IP"  (oprid, not object — handled separately)
    # "XXX PeopleCode" — generic fallback
    (re.compile(r"\b([A-Z][A-Z0-9_$]{2,30})\s+PeopleCode\b", re.IGNORECASE), 1),
]

# Patterns to extract OPRID from message text
_MSG_OPRID_RE = re.compile(
    r"(?:for user|Error for User)\s*[:\s]*([A-Z][A-Z0-9_$]{1,29})[@\s]",
    re.IGNORECASE,
)

def _extract_object_ref(text: str) -> Optional[str]:
    """Best-effort extraction of a PS object name from a log message."""
    for pat, grp in _OBJ_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(grp).upper()
    return None


def _extract_oprid_from_message(text: str) -> Optional[str]:
    """Extract OPRID from error messages like 'Invalid password for user JARED@...'"""
    m = _MSG_OPRID_RE.search(text)
    if m:
        return m.group(1).upper()
    return None


# ---------------------------------------------------------------------------
# PIA access log  (NCSA extended)
# Format: IP - OPRID [DD/Mon/YYYY:HH:MM:SS tz] "METHOD URL HTTP/1.1" STATUS BYTES "ref" "ua" ms
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

    ts = _parse_ncsa_ts(m.group("ts"))
    if ts is None:
        return None

    oprid = m.group("oprid")
    if oprid == "-":
        oprid = None

    url    = m.group("url")
    ps     = _extract_ps_path(url)
    status = int(m.group("status"))

    bytes_raw = m.group("bytes")
    byte_count = int(bytes_raw) if bytes_raw.isdigit() else 0

    ms_raw = m.group("ms")
    ms = int(ms_raw) if ms_raw else None

    return {
        "log_type":   "pia_access",
        "ts":         ts.astimezone(timezone.utc).replace(tzinfo=None),
        "ip":         m.group("ip"),
        "oprid":      oprid,
        "method":     m.group("method"),
        "url":        url,
        "component":  ps.get("component"),
        "page":       ps.get("page"),
        "menu":       ps.get("menu"),
        "status":     status,
        "bytes":      byte_count,
        "ms":         ms,
        "useragent":  m.group("useragent") or None,
        "is_error":   status >= 500,
        "error_codes": [],
        "object_ref": ps.get("component"),
        "raw":        line,
    }


# ---------------------------------------------------------------------------
# PIA error / stderr log (WebLogic PIA_stderr*.log)
# WebLogic mixes Java exception stack traces with WebLogic messages.
# Lines starting with \t or spaces are continuation lines (stack frames) — skip them.
# ---------------------------------------------------------------------------

_PIA_ERR_TS_RE  = re.compile(r"####<(\w{3}\s+\w{3}\s+\d+\s+[\d:,]+\s+\w+\s+\w+\s+\d{4})>")
_PIA_ERR_LEV_RE = re.compile(r"<(Error|Warning|Critical|Alert|Notice|Info)>", re.IGNORECASE)

def parse_pia_error(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    # Skip stack trace continuation lines (Java exception frames)
    if line.startswith(("\t", "  ", "Caused by:")):
        return None
    # Skip WebLogic structured lines (handle via pia_weblogic instead)
    if line.startswith("####"):
        return None

    error_codes = _extract_error_codes(line)
    is_error = bool(error_codes) or any(
        w in line for w in ("Exception", "Error:", "SEVERE", "FATAL")
    )
    if not is_error:
        return None

    return {
        "log_type":    "pia_error",
        "ts":          datetime.utcnow(),
        "oprid":       _extract_oprid_from_message(line),
        "level":       "ERROR",
        "message":     line[:2000],
        "error_codes": error_codes,
        "object_ref":  _extract_object_ref(line),
        "is_error":    True,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# PIA servlet log (PIA_servlets*.log.N)
# Tab-separated with a header line that names all columns:
#   Timestamp  Seq  Thread  Group  TRID  TopInstanceID  OperID  Level  Class  Method  Message
#
# The OperID column (index 6) contains the PS OPRID for authenticated requests.
# ---------------------------------------------------------------------------

_SERVLET_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"

def parse_pia_servlet(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line or not line[0].isdigit():
        return None

    parts = line.split("\t", 10)
    if len(parts) < 8:
        return None

    ts_str  = parts[0].strip()
    oprid   = parts[6].strip() if len(parts) > 6 else "-"
    level   = parts[7].strip() if len(parts) > 7 else "INFO"
    src_cls = parts[8].strip() if len(parts) > 8 else ""
    message = parts[10].strip() if len(parts) > 10 else parts[-1].strip()

    ts = None
    try:
        ts = datetime.strptime(ts_str[:26], _SERVLET_DT_FMT)
    except ValueError:
        try:
            ts = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None

    if oprid in ("-", "", "unknown", "null"):
        oprid = None

    error_codes = _extract_error_codes(message)
    is_error    = level in ("SEVERE", "ERROR") or bool(error_codes)

    # Extract PS component from class name (e.g. psft.pt8.comp.HR_EMPLOYEE_COMP)
    obj_ref = None
    if src_cls:
        parts_cls = src_cls.rsplit(".", 1)
        last = parts_cls[-1]
        if len(last) > 3 and re.match(r'^[A-Z][A-Z0-9_$]{2,}$', last):
            obj_ref = last

    return {
        "log_type":    "pia_servlet",
        "ts":          ts,
        "oprid":       oprid,
        "level":       level,
        "message":     message[:2000],
        "error_codes": error_codes,
        "object_ref":  obj_ref,
        "is_error":    is_error,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# PIA WebLogic domain log (PIA_weblogic.log)
# Format: ####<timestamp> <Level> <Subsystem> <Server> <...> <BEA-code> <Message>
# Fields are <angle-bracket> delimited; message is the last field.
# ---------------------------------------------------------------------------

_WL_RE = re.compile(
    r"####<(?P<ts>[^>]+)>\s+"
    r"<(?P<level>[^>]+)>\s+"
    r"<(?P<subsys>[^>]+)>(?:.*?)"
    r"<(?P<bea_code>BEA-\d+)>\s*"
    r"<(?P<msg>[^>]{0,2000})>",
    re.DOTALL
)

_WL_DT_FMTS = [
    "%b %d, %Y, %I:%M:%S,%f %p %Z",
    "%b %d, %Y, %I:%M:%S,%f %p Central Daylight Time",
    "%b %d, %Y, %I:%M:%S,%f %p Central Standard Time",
]

def parse_pia_weblogic(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line or not line.startswith("####"):
        return None

    m = _WL_RE.match(line)
    if not m:
        return None

    level    = m.group("level")
    is_error = level.lower() in ("error", "critical", "alert", "emergency")
    if not is_error:
        # Only keep errors and warnings from the domain log — info is noise
        if level.lower() not in ("warning",):
            return None

    ts = datetime.utcnow()
    ts_raw = m.group("ts")
    # Normalize timestamp string
    ts_raw = re.sub(r'\s+', ' ', ts_raw).strip()
    # Remove timezone name at end if it's a wordy one
    ts_clean = re.sub(r'\s+(Central Daylight Time|Central Standard Time|UTC|GMT)$', '', ts_raw)
    for fmt in ("%b %d, %Y, %I:%M:%S,%f %p", "%b %d, %Y, %I:%M:%S %p"):
        try:
            ts = datetime.strptime(ts_clean, fmt)
            break
        except ValueError:
            pass

    msg       = m.group("msg")
    bea_code  = m.group("bea_code")
    error_codes = [bea_code] if is_error else []
    error_codes += _extract_error_codes(msg)

    return {
        "log_type":    "pia_weblogic",
        "ts":          ts,
        "oprid":       None,
        "level":       level.upper(),
        "message":     f"[{bea_code}] {msg[:1800]}",
        "error_codes": error_codes,
        "object_ref":  None,
        "is_error":    is_error,
        "raw":         line[:4000],
    }


# ---------------------------------------------------------------------------
# PIA stdout (PIA_stdout*.log)
# JVM startup and configuration output — low signal.
# Only index lines that look like actual log messages (not classpath/java opts).
# ---------------------------------------------------------------------------

def parse_pia_stdout(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line or len(line) > 1000:
        return None
    # Skip classpath/java option noise
    if any(line.startswith(p) for p in ("Java ", "-", " -", "/opt/")):
        return None
    error_codes = _extract_error_codes(line)
    is_error = bool(error_codes) or "error" in line.lower()
    if not is_error:
        return None
    return {
        "log_type":    "pia_stdout",
        "ts":          datetime.utcnow(),
        "oprid":       None,
        "level":       "ERROR",
        "message":     line[:2000],
        "error_codes": error_codes,
        "object_ref":  None,
        "is_error":    True,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# APPSRV log (PeopleSoft APPSRV_MMDD.LOG.N)
#
# Real format observed:
#   PSAPPSRV.7801 (2424) [2026-07-01T09:00:58.458 GUACUSER@47.219.13.182 (CHROME 139.0.0.0; LINUX) ICScript] token sessid GUACUSER (0) message
#   PSAPPSRV.7801 (2117) [2026-07-01T00:00:28.842 GetCertificate] - - - (3) Detected time zone is CDT
#   PSAPPSRV.7801 (2117) [2026-07-01T00:00:28.842 GetCertificate] token sessid - (3) Returning context. ID=GUACUSER, Lang=ENG...
#
# Context bracket formats:
#   OPRID@IP (BROWSER VERSION; OS) ServiceName
#   ServiceName   (e.g. GetCertificate, ICPanel, ICScript)
# ---------------------------------------------------------------------------

_APPSRV_RE = re.compile(
    r'(?P<proc>[A-Z]+\.\d+)\s+\((?P<reqno>\d+)\)\s+'
    r'\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\s+(?P<context>[^\]]+)\]\s+'
    r'(?P<rest>.+)',
    re.DOTALL
)
_APPSRV_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"

# Context: OPRID@IP (BROWSER INFO) ServiceName
_APPSRV_CTX_USER_RE = re.compile(
    r'^(?P<oprid>[A-Z0-9_$@.]{2,30})@(?P<ip>[\d.]+)\s+\((?P<browser>[^)]+)\)\s+(?P<service>\S+)',
    re.IGNORECASE
)

# GetCertificate return: ID=OPRID,
_APPSRV_CERT_RE = re.compile(r'Returning context\.\s+ID=(?P<oprid>[A-Z0-9_$@.]{2,30}),')

# Fields after context bracket: token sessid OPRID-or-dash (level) message
# Third token can be a real OPRID or "-" for system/unauthenticated contexts
_APPSRV_FIELDS_RE = re.compile(
    r'(?P<token>\S+)\s+(?P<sessid>\S+)\s+(?P<oprid_field>\S+)\s+\((?P<level>\d+)\)\s+(?P<msg>.+)',
    re.DOTALL
)
_APPSRV_OPRID_RE = re.compile(r'^[A-Z][A-Z0-9_$]{1,29}$')


def parse_appsrv(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None

    m = _APPSRV_RE.match(line)
    if not m:
        return None

    ts_str  = m.group("ts")
    context = m.group("context").strip()
    rest    = m.group("rest").strip()

    try:
        ts = datetime.strptime(ts_str[:26], _APPSRV_DT_FMT)
    except ValueError:
        return None

    oprid    = None
    ip       = None
    service  = context
    level    = "INFO"
    message  = rest
    browser  = None

    # Try to extract OPRID from context: OPRID@IP (BROWSER) Service
    cu = _APPSRV_CTX_USER_RE.match(context)
    if cu:
        oprid   = cu.group("oprid").upper()
        ip      = cu.group("ip")
        browser = cu.group("browser")
        service = cu.group("service")

    # Parse fields: token sessid oprid_or_dash (level) message
    fm = _APPSRV_FIELDS_RE.match(rest)
    if fm:
        level   = "DEBUG" if fm.group("level") == "0" else "INFO"
        message = fm.group("msg")
        # If context had no OPRID, try the field position
        if oprid is None:
            field_oprid = fm.group("oprid_field")
            if _APPSRV_OPRID_RE.match(field_oprid):
                oprid = field_oprid.upper()

    # For GetCertificate responses, OPRID is in the message body
    if oprid is None:
        cert = _APPSRV_CERT_RE.search(message)
        if cert:
            oprid = cert.group("oprid").upper()

    # Last-resort: extract OPRID from message text (e.g. "Invalid password for user JARED@...")
    if oprid is None:
        oprid = _extract_oprid_from_message(message)

    # Skip system/service accounts for session chain (PS, IBAPPS, etc.)
    # but keep them — they're useful for IB tracing
    error_codes = _extract_error_codes(line)
    is_error    = bool(error_codes) or any(
        w in message for w in ("Error", "error", "FATAL", "Exception", "failed", "ORA-")
    )
    if is_error:
        level = "ERROR"

    return {
        "log_type":    "appsrv",
        "ts":          ts,
        "process":     m.group("proc"),
        "oprid":       oprid,
        "ip":          ip,
        "browser":     browser,
        "service":     service,
        "level":       level,
        "message":     message[:2000],
        "error_codes": error_codes,
        "object_ref":  _extract_object_ref(message),
        "is_error":    is_error,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Process Scheduler AE Server  (AESRV_MMDD.LOG.N in PRCS domain LOGS/)
# Format: PSAESRV.PID (req) [TIMESTAMP] - - - (level) message
# No OPRID in the timestamp bracket — extract from message body.
# ---------------------------------------------------------------------------

_PRCS_AE_RE = re.compile(
    r'(?P<proc>PS[A-Z]+\.\d+)\s+\((?P<reqno>\d+)\)\s+'
    r'\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\]\s+'
    r'[-\s]+\((?P<level>\d+)\)\s+(?P<msg>.+)',
    re.DOTALL
)

_PRCS_AE_APPLID_RE   = re.compile(r'Application ID=([A-Z0-9_]+)',    re.IGNORECASE)
_PRCS_AE_INSTANCE_RE = re.compile(r'Process Instance=(\d+)')
_PRCS_AE_RUNCNTL_RE  = re.compile(r'Run Control ID=([A-Z0-9_]+)',    re.IGNORECASE)
_PRCS_AE_STEP_RE     = re.compile(r'Current Step=([A-Z0-9_.]+)',     re.IGNORECASE)
_PRCS_AE_STATUS_RE   = re.compile(r'\bStatus=(\w+)')

_PRCS_AE_LEVEL_MAP = {
    "0": "INFO",
    "1": "WARN",
    "2": "WARN",
    "3": "INFO",
    "4": "DEBUG",
}


def parse_prcs_ae(line: str) -> Optional[dict]:
    """Parse PeopleSoft Process Scheduler AESRV log lines."""
    line = line.rstrip()
    if not line:
        return None

    m = _PRCS_AE_RE.match(line)
    if not m:
        return None

    ts_str  = m.group("ts")
    level_n = m.group("level")
    msg     = m.group("msg").strip()

    try:
        ts = datetime.strptime(ts_str[:26], _APPSRV_DT_FMT)   # same format
    except ValueError:
        return None

    level = _PRCS_AE_LEVEL_MAP.get(level_n, "INFO")

    # Extract structured fields from message body
    applid   = (_PRCS_AE_APPLID_RE.search(msg)   or type("", (), {"group": lambda *_: None})()).group(1)
    step     = (_PRCS_AE_STEP_RE.search(msg)      or type("", (), {"group": lambda *_: None})()).group(1)
    status   = (_PRCS_AE_STATUS_RE.search(msg)    or type("", (), {"group": lambda *_: None})()).group(1)

    # Detect errors: explicit failure, error keywords, or error status
    is_error = (
        "error" in msg.lower()
        or "failed" in msg.lower()
        or "exception" in msg.lower()
        or status in ("Error", "Failed")
    )
    if is_error:
        level = "ERROR"

    error_codes = _extract_error_codes(msg) if is_error else []

    return {
        "log_type":    "prcs_ae",
        "ts":          ts,
        "process":     m.group("proc"),
        "oprid":       None,        # no user context in AESRV logs
        "level":       level,
        "message":     msg[:2000],
        "error_codes": error_codes,
        "object_ref":  applid,      # AE program name for cross-reference
        "is_error":    is_error,
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Tuxedo ULOG  (TUXLOG.MMDDYY)
# Format: HH:MM:SS.mmm hostname!proc.pid.grp.seq: Mon DD HH:MM:SS message
# ---------------------------------------------------------------------------

_TUXEDO_RE = re.compile(
    r"(?P<ts>\w{3}\s+\d+\s+[\d:]+)\s+(?P<host>\S+)!(?P<proc>[^.]+\.\d+\.\d+\.\d+):\s+(?P<msg>.+)"
)
_TUXEDO_DT_FMT = "%b %d %H:%M:%S"

def parse_tuxedo(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    m = _TUXEDO_RE.search(line)
    if not m:
        return None

    ts_str = m.group("ts").strip()
    try:
        ts = datetime.strptime(f"{datetime.utcnow().year} {ts_str}", "%Y %b %d %H:%M:%S")
    except ValueError:
        ts = datetime.utcnow()

    msg         = m.group("msg")
    error_codes = _extract_error_codes(msg)
    is_error    = bool(error_codes) or any(
        w in msg.lower() for w in ("error", "fatal", "abort", "fail", "userlog")
    )

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
# ---------------------------------------------------------------------------

def parse_apache_access(line: str) -> Optional[dict]:
    row = parse_pia_access(line)
    if row:
        row["log_type"] = "apache_access"
    return row


parse_f5_access = parse_apache_access


# ---------------------------------------------------------------------------
# Apache / nginx error log
# ---------------------------------------------------------------------------

_APACHE_ERR_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\]\s+\[(?P<level>[^\]]+)\](?:\s+\[pid\s+\d+\])?\s+(?P<msg>.+)"
)
_APACHE_ERR_DT_FMT  = "%a %b %d %H:%M:%S.%f %Y"
_APACHE_ERR_DT_FMT2 = "%a %b %d %H:%M:%S %Y"

def parse_apache_error(line: str) -> Optional[dict]:
    line = line.rstrip()
    if not line:
        return None
    m = _APACHE_ERR_RE.match(line)
    if not m:
        return None

    ts = datetime.utcnow()
    ts_raw = m.group("ts")
    for fmt in (_APACHE_ERR_DT_FMT, _APACHE_ERR_DT_FMT2):
        try:
            ts = datetime.strptime(ts_raw, fmt)
            break
        except ValueError:
            pass

    msg   = m.group("msg")
    level = m.group("level").upper()
    return {
        "log_type":    "apache_error",
        "ts":          ts,
        "oprid":       None,
        "level":       level,
        "message":     msg[:2000],
        "error_codes": _extract_error_codes(msg),
        "object_ref":  _extract_object_ref(msg),
        "is_error":    level in ("ERROR", "CRIT", "ALERT", "EMERG"),
        "raw":         line,
    }


# ---------------------------------------------------------------------------
# Integration Gateway errorLog.html  (block parser — NOT line-by-line)
# ---------------------------------------------------------------------------
# Format: each error entry starts with <BODY ...><H4>TIMESTAMP</H4> and
# runs ~100 HTML lines until the next <BODY> tag or EOF.
# Fields extracted via regex on the HTML block:
#   Description  — INPUT VALUE attr after "Description"
#   Exception    — INPUT VALUE attr after "Exception"
#   ErrorLevel   — SPAN text after "ErrorLevel"
#   Stack Trace  — first <TEXTAREA> content
#   Request XML  — second <TEXTAREA> (IBInfo + MIME body)
# ---------------------------------------------------------------------------

_IGW_ENTRY_SPLIT_RE  = re.compile(r'<BODY\b[^>]*>', re.IGNORECASE)
_IGW_TS_RE           = re.compile(r'<H4>(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.\d]*)</H4>',
                                   re.IGNORECASE)
_IGW_INPUT_VAL_RE    = re.compile(r'VALUE="([^"]*)"', re.IGNORECASE)
_IGW_ERR_LEVEL_RE    = re.compile(
    r'ErrorLevel\s*&nbsp;.*?<SPAN[^>]*>(.*?)</SPAN>', re.IGNORECASE | re.DOTALL)
_IGW_TEXTAREA_RE     = re.compile(
    r'<TEXTAREA\b[^>]*>(.*?)</TEXTAREA>', re.IGNORECASE | re.DOTALL)
_IGW_IB_OP_RE        = re.compile(
    r'<ExternalOperationName>\s*<!\[CDATA\[([^\]]+)\]\]>', re.IGNORECASE)
_IGW_QUEUE_RE        = re.compile(
    r'<Queue>\s*<!\[CDATA\[([^\]]+)\]\]>', re.IGNORECASE)
_IGW_FROM_NODE_RE    = re.compile(
    r'<RequestingNode>\s*<!\[CDATA\[([^\]]+)\]\]>', re.IGNORECASE)
_IGW_HTTP_STATUS_RE  = re.compile(r'HttpStatusCode\s+Returned\s*=\s*(\d{3})')
_IGW_MSGSET_RE       = re.compile(r'MessageSet:\s*<INPUT[^>]+VALUE="(\d+)"', re.IGNORECASE)
_IGW_MSGID_RE        = re.compile(r'MessageID:\s*<INPUT[^>]+VALUE="(\d+)"', re.IGNORECASE)
_IGW_MSGPARMS_RE     = re.compile(r'MessageParms:\s*<INPUT[^>]+VALUE="([^"]*)"', re.IGNORECASE)

# Error-code labels specific to IGW
_IGW_ERROR_LABELS = {
    "ExternalApplicationException": "IB_EXT_APP",
    "GeneralFrameworkException":    "IB_GFW",
    "ExternalSystemContactException": "IB_EXT_CONTACT",
    "PeoplesoftListeningConnector": "IB_LISTEN",
    "HttpTargetConnector":          "IB_HTTP_TC",
}

_IGW_DT_FMTS = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]


def _igw_parse_block(block: str) -> Optional[dict]:
    """Parse a single IGW error entry HTML block. Returns None if invalid."""
    ts_m = _IGW_TS_RE.search(block)
    if not ts_m:
        return None

    ts_raw = ts_m.group(1).strip()
    ts = None
    for fmt in _IGW_DT_FMTS:
        try:
            ts = datetime.strptime(ts_raw[:len(fmt) + 3], fmt)
            break
        except ValueError:
            pass
    if ts is None:
        return None

    # All INPUT VALUE= matches — [0]=Description, [1]=Exception (if present)
    input_vals = _IGW_INPUT_VAL_RE.findall(block)
    description = input_vals[0].strip() if len(input_vals) > 0 else ""
    exception   = input_vals[1].strip() if len(input_vals) > 1 else ""

    # ErrorLevel span text
    el_m = _IGW_ERR_LEVEL_RE.search(block)
    error_level = el_m.group(1).strip() if el_m else "Error"

    # TextAreas: [0] = Stack Trace, [1] = Request (IB MIME)
    textareas = _IGW_TEXTAREA_RE.findall(block)
    stack_trace = textareas[0].strip() if len(textareas) > 0 else ""
    request_xml = textareas[1].strip() if len(textareas) > 1 else ""

    # Extract IB context from request XML
    _m = _IGW_IB_OP_RE.search(request_xml);    ib_operation    = _m.group(1) if _m else None
    _m = _IGW_QUEUE_RE.search(request_xml);    queue_name      = _m.group(1) if _m else None
    _m = _IGW_FROM_NODE_RE.search(request_xml); requesting_node = _m.group(1) if _m else None

    # HTTP status from description
    http_m = _IGW_HTTP_STATUS_RE.search(description)
    http_status = http_m.group(1) if http_m else None

    # Message catalog
    _m = _IGW_MSGSET_RE.search(block);  msgset   = _m.group(1) if _m else None
    _m = _IGW_MSGID_RE.search(block);   msgid    = _m.group(1) if _m else None
    _m = _IGW_MSGPARMS_RE.search(block); msgparms = _m.group(1) if _m else None

    # Build error code list — match only in description/exception, not the full stack
    error_codes = []
    if http_status:
        error_codes.append(f"HTTP_{http_status}")
    check_text = f"{description} {exception}"
    for key, label in _IGW_ERROR_LABELS.items():
        if key in check_text and label not in error_codes:
            error_codes.append(label)
    if msgset and msgid:
        error_codes.append(f"MSG_{msgset}_{msgid}")

    # Object ref — IB operation name takes priority
    obj_ref = (ib_operation or "").split(".")[0] or None

    # Primary message: description is most useful; fall back to msgparms
    message = description or msgparms or exception or error_level
    if requesting_node:
        message += f" [node:{requesting_node}]"
    if queue_name and queue_name != ib_operation:
        message += f" [queue:{queue_name}]"

    # raw = compact 1-line representation (not storing full HTML)
    raw = f"{ts_raw}|{description}|{exception}|{ib_operation or ''}|{requesting_node or ''}"

    return {
        "log_type":       "igw_error_log",
        "ts":             ts,
        "oprid":          None,
        "level":          "ERROR",
        "message":        message[:2000],
        "error_codes":    error_codes,
        "object_ref":     obj_ref,
        "is_error":       True,
        "raw":            raw[:500],
        # Extra IGW fields stored in message; full detail below for caller use
        "_igw": {
            "description":     description,
            "exception":       exception,
            "error_level":     error_level,
            "stack_trace":     stack_trace[:1000],
            "ib_operation":    ib_operation,
            "queue_name":      queue_name,
            "requesting_node": requesting_node,
            "http_status":     http_status,
            "msg_set":         msgset,
            "msg_id":          msgid,
            "msg_parms":       msgparms,
        },
    }


def parse_igw_error_log(content: str) -> list[dict]:
    """
    Block parser for IGW errorLog.html content.
    Splits on <BODY> tags and parses each entry block.
    Returns a list of dicts (may be empty).
    """
    results = []
    # Split on <BODY> to get individual entry blocks
    blocks = _IGW_ENTRY_SPLIT_RE.split(content)
    for block in blocks:
        if not block.strip() or '<H4>' not in block:
            continue
        try:
            row = _igw_parse_block(block)
            if row:
                results.append(row)
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_PARSERS = {
    "pia_access":    parse_pia_access,
    "pia_error":     parse_pia_error,
    "pia_servlet":   parse_pia_servlet,
    "pia_weblogic":  parse_pia_weblogic,
    "pia_stdout":    parse_pia_stdout,
    "appsrv":        parse_appsrv,
    "prcs_ae":       parse_prcs_ae,
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
