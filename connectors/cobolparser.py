"""
Pure PeopleSoft COBOL (.cbl) file parser — no I/O, takes a string and returns
structured metadata.

PeopleSoft COBOL sources come in two flavors, both using the .cbl extension:
  - programs — have an IDENTIFICATION DIVISION / PROGRAM-ID and are compiled
    standalone (e.g. PTPCBLAE.cbl)
  - copybooks — no PROGRAM-ID; pulled into programs via COPY statements
    (e.g. PTCLOGMS.cbl, referenced as `COPY PTCLOGMS.`). These typically
    define a single 01-level record or SECTION.

Extracts:
  - PROGRAM-ID (member_name) and file_type (program|copybook)
  - a best-effort description (first non-boilerplate comment line)
  - COPY dependencies (other .cbl members pulled in)
  - static CALL targets (CALL 'X' / CALL "X" — dynamic CALL WS-VAR unresolved)
  - PS_ table references inside EXEC SQL ... END-EXEC blocks
"""

import re

# ── compiled patterns ────────────────────────────────────────────────────────

_RE_PROGRAM_ID = re.compile(r'\bPROGRAM-ID\.\s+([\w-]+)', re.IGNORECASE)
_RE_SECTION    = re.compile(r'^\s*([\w-]+)\s+SECTION\s*\.', re.IGNORECASE | re.MULTILINE)

_RE_COPY       = re.compile(r'\bCOPY\s+([\w-]+)', re.IGNORECASE)
_RE_CALL       = re.compile(r'\bCALL\s+[\'"]([\w-]+)[\'"]', re.IGNORECASE)

_RE_EXEC_SQL   = re.compile(r'EXEC\s+SQL(.*?)END-EXEC', re.IGNORECASE | re.DOTALL)

_RE_FROM_TABLE   = re.compile(r'\bFROM\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_JOIN_TABLE   = re.compile(r'\bJOIN\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_UPDATE_TABLE = re.compile(r'\bUPDATE\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_INSERT_TABLE = re.compile(r'\bINSERT\s+INTO\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)
_RE_DELETE_TABLE = re.compile(r'\bDELETE\s+FROM\s+(PS_[A-Z0-9_]+)', re.IGNORECASE)

_SQL_PATTERNS = [
    ("SELECT", _RE_FROM_TABLE),
    ("SELECT", _RE_JOIN_TABLE),
    ("UPDATE", _RE_UPDATE_TABLE),
    ("INSERT", _RE_INSERT_TABLE),
    ("DELETE", _RE_DELETE_TABLE),
]

# The Oracle/PeopleSoft license preamble is a fixed multi-line paragraph ending
# in "All Rights Reserved." — only comment lines *after* that marker are
# candidates for a description, since the paragraph itself wraps across many
# lines with no other reliable per-line signature.
_RE_RIGHTS_RESERVED = re.compile(r'all rights reserved', re.IGNORECASE)
_RE_DECORATIVE = re.compile(r'^[\s*#=\-]*$')

# Comment line: fixed-format COBOL marks column 7 with '*' (leading whitespace
# is the sequence-area padding this codebase's SSH reader doesn't strip).
_RE_COMMENT_LINE = re.compile(r'^\s*\*(.*)$')


def parse(content: str, filename: str = "") -> dict:
    """
    Parse a PeopleSoft .cbl file and return a dict with:
        member_name, file_type ("program"|"copybook"), description,
        tables (dict: table_name → list[op]),
        copies (list of COPY'd member names),
        calls (list of statically-CALL'd program names)
    """
    result = {
        "member_name": "",
        "file_type": "copybook",
        "description": "",
        "tables": {},
        "copies": [],
        "calls": [],
    }

    m = _RE_PROGRAM_ID.search(content)
    if m:
        result["member_name"] = m.group(1).upper()
        result["file_type"] = "program"
    else:
        m = _RE_SECTION.search(content)
        if m:
            result["member_name"] = m.group(1).upper()

    if not result["member_name"] and filename:
        result["member_name"] = re.sub(r'\.cbl$', '', filename, flags=re.IGNORECASE).upper()

    # ── best-effort description: first real comment line after the license
    # preamble (which always ends in "All Rights Reserved.") ────────────────
    lines = content.splitlines()[:200]
    past_preamble = False
    for line in lines:
        cm = _RE_COMMENT_LINE.match(line)
        if not cm:
            continue
        raw_text = cm.group(1)
        if not past_preamble:
            if _RE_RIGHTS_RESERVED.search(raw_text):
                past_preamble = True
            continue
        if _RE_DECORATIVE.match(raw_text):
            continue
        text = raw_text.strip(" *")
        if len(text) < 8:
            continue
        result["description"] = text
        break

    # ── COPY dependencies ─────────────────────────────────────────────────────
    result["copies"] = sorted({m.group(1).upper() for m in _RE_COPY.finditer(content)})

    # ── static CALL targets ──────────────────────────────────────────────────
    result["calls"] = sorted({m.group(1).upper() for m in _RE_CALL.finditer(content)})

    # ── PS_ table references inside EXEC SQL blocks ─────────────────────────
    tables: dict[str, set] = {}
    for sql_block in _RE_EXEC_SQL.findall(content):
        for op, pattern in _SQL_PATTERNS:
            for m in pattern.finditer(sql_block):
                tbl = m.group(1).upper()
                tables.setdefault(tbl, set()).add(op)
    result["tables"] = {k: sorted(v) for k, v in sorted(tables.items())}

    return result
