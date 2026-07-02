"""
Pure SQR/SQC file parser — no I/O, takes a string and returns structured metadata.

Extracts from PeopleSoft SQR source files:
  - program description and header comments
  - PS_ table references (FROM / UPDATE / INSERT INTO / DELETE FROM)
  - #include SQC dependencies
  - begin-procedure definitions
  - DO / GOSUB calls to procedures
"""

import re

# ── compiled patterns ────────────────────────────────────────────────────────

_RE_REPORT_NAME  = re.compile(r'!\s*Report Name[:\s]+(\S+)', re.IGNORECASE)
_RE_PROG_DESCR   = re.compile(r'!\s*Program Descr[:\s]+(.*)', re.IGNORECASE)
_RE_RELEASE      = re.compile(r'\$Release:\s*(\S+)', re.IGNORECASE)
_RE_REVISION     = re.compile(r'\$Revision:\s*(\S+)', re.IGNORECASE)
_RE_DATE         = re.compile(r'\$Date:\s*(\S+)', re.IGNORECASE)

# PS_ table names in SQL — case-insensitive, word-boundary aware
_RE_FROM_TABLE   = re.compile(r'\bFROM\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_JOIN_TABLE   = re.compile(r'\bJOIN\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_UPDATE_TABLE = re.compile(r'\bUPDATE\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_INSERT_TABLE = re.compile(r'\bINSERT\s+INTO\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_DELETE_TABLE = re.compile(r'\bDELETE\s+FROM\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_CREATE_TABLE = re.compile(r'\bCREATE\s+(?:TEMP\s+)?TABLE\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)

_SQL_PATTERNS = [
    ("SELECT",  _RE_FROM_TABLE),
    ("SELECT",  _RE_JOIN_TABLE),
    ("UPDATE",  _RE_UPDATE_TABLE),
    ("INSERT",  _RE_INSERT_TABLE),
    ("DELETE",  _RE_DELETE_TABLE),
    ("CREATE",  _RE_CREATE_TABLE),
]

_RE_INCLUDE    = re.compile(r"#include\s+'([^']+)'", re.IGNORECASE)
_RE_BEGIN_PROC = re.compile(r'^begin-procedure\s+(\S+)', re.IGNORECASE | re.MULTILINE)
_RE_DO_CALL    = re.compile(r'^\s+(?:do|gosub)\s+(\S+)', re.IGNORECASE | re.MULTILINE)

# strip ! comment lines before SQL scanning to avoid false matches in comments
_RE_COMMENT_LINE = re.compile(r'^\s*!.*$', re.MULTILINE)


def parse(content: str, filename: str = "") -> dict:
    """
    Parse SQR/SQC file content and return a dict with:
        program_name, description, release, revision, date,
        tables (dict: table_name → set of ops),
        includes (list of .sqc filenames),
        procedures (list of proc names),
        calls (list of called proc names, from DO/GOSUB)
    """
    result = {
        "program_name": "",
        "description": "",
        "release": "",
        "revision": "",
        "date": "",
        "tables": {},        # table_name (upper) → list[op]
        "includes": [],
        "procedures": [],
        "calls": [],
    }

    # ── header metadata (first 60 lines to stay fast) ────────────────────────
    header = "\n".join(content.splitlines()[:60])

    m = _RE_REPORT_NAME.search(header)
    if m:
        result["program_name"] = m.group(1).rstrip(".-").upper()

    m = _RE_PROG_DESCR.search(header)
    if m:
        result["description"] = m.group(1).strip()

    m = _RE_RELEASE.search(header)
    if m:
        result["release"] = m.group(1).strip()

    m = _RE_REVISION.search(header)
    if m:
        result["revision"] = m.group(1).strip()

    m = _RE_DATE.search(header)
    if m:
        result["date"] = m.group(1).strip()

    # fall back to filename for program_name
    if not result["program_name"] and filename:
        result["program_name"] = re.sub(r'\.(sqr|sqc)$', '', filename, flags=re.IGNORECASE).upper()

    # ── strip comment lines before scanning for SQL / includes ──────────────
    no_comments = _RE_COMMENT_LINE.sub('', content)

    # ── #include dependencies ────────────────────────────────────────────────
    result["includes"] = sorted({
        m.group(1).lower()
        for m in _RE_INCLUDE.finditer(content)   # keep in original (includes may be in comments as docs)
    })

    # ── SQL table references ─────────────────────────────────────────────────
    tables: dict[str, set] = {}
    for op, pattern in _SQL_PATTERNS:
        for m in pattern.finditer(no_comments):
            tbl = m.group(1).upper()
            tables.setdefault(tbl, set()).add(op)

    result["tables"] = {k: sorted(v) for k, v in sorted(tables.items())}

    # ── procedure definitions ─────────────────────────────────────────────────
    result["procedures"] = sorted({
        m.group(1) for m in _RE_BEGIN_PROC.finditer(content)
    })

    # ── DO / GOSUB calls ─────────────────────────────────────────────────────
    result["calls"] = sorted({
        m.group(1) for m in _RE_DO_CALL.finditer(content)
    })

    return result
