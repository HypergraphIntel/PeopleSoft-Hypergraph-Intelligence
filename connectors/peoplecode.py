import re
from urllib.parse import quote, unquote

from connectors import graphshape, psdb, ptmetadata

PEOPLECODE_OBJECT_TYPES = {
    1:  "Record",
    3:  "Menu",
    8:  "Page",
    9:  "Component",
    10: "Component",
    43: "Menu",
    46: "Menu Item",
    58: "Component Interface",
    60: "Subscription",        # IB subscription PeopleCode (OV1=service_op, OV3="Subscription")
    66: "Application Engine",  # AE PeopleCode (OV1=applid, OV2=section, OV6=step, OV7=OnExecute)
    74: "Component Interface",
    104: "App Package Class",  # App Package class PeopleCode (OV1=packageroot, OV2...=path, OVn-1=classid, OVn=OnExecute)
}

# Known PeopleCode event names (uppercase for comparison)
PEOPLECODE_EVENTS = {
    "FIELDDEFAULT", "FIELDFORMULA", "FIELDEDIT", "FIELDCHANGE",
    "ROWINIT", "ROWINSERT", "ROWDELETE", "ROWSELECT",
    "SAVEPRECHANGE", "SAVEPOSTCHANGE", "SAVEEDIT", "WORKFLOW",
    "PREBUILD", "POSTBUILD",
    "ACTIVATE",
    "ITEMSELECTED",
    "ONEXECUTE", "ONNOTIFY", "ONSELECT",
    "SEARCHINIT", "SEARCHSAVE",
    "ROWACTION",
}

PEOPLECODE_EVENT_LABELS = {
    "FIELDDEFAULT": "FieldDefault",
    "FIELDFORMULA": "FieldFormula",
    "FIELDEDIT": "FieldEdit",
    "FIELDCHANGE": "FieldChange",
    "ROWINIT": "RowInit",
    "ROWINSERT": "RowInsert",
    "ROWDELETE": "RowDelete",
    "ROWSELECT": "RowSelect",
    "SAVEPRECHANGE": "SavePreChange",
    "SAVEPOSTCHANGE": "SavePostChange",
    "SAVEEDIT": "SaveEdit",
    "WORKFLOW": "Workflow",
    "PREBUILD": "PreBuild",
    "POSTBUILD": "PostBuild",
    "ACTIVATE": "Activate",
    "ITEMSELECTED": "ItemSelected",
    "ONEXECUTE": "OnExecute",
    "ONNOTIFY": "OnNotify",
    "ONSELECT": "OnSelect",
    "SEARCHINIT": "SearchInit",
    "SEARCHSAVE": "SearchSave",
    "ROWACTION": "RowAction",
}

CALL_NAMES = [
    "SQLExec",
    "CreateSQL",
    "GetSQL",
    "CallAppEngine",
    "Transfer",
    "DoSave",
    "DoModal",
    "CreateRecord",
    "GetRecord",
    "GetField",
    "GetComponent",
    "GetRowset",
    "GetLevel0",
    "MessageBox",
    "WinMessage",
]

REFERENCE_PATTERNS = {
    "record": re.compile(r"\b(?:CreateRecord|GetRecord)\s*\(\s*Record\.([A-Z0-9_]+)", re.I),
    "field": re.compile(r"\b(?:GetField)\s*\(\s*Field\.([A-Z0-9_]+)", re.I),
    "sql_definition": re.compile(r"\b(?:GetSQL|CreateSQL|SQLExec)\s*\(\s*SQL\.([A-Z0-9_]+)", re.I),
    "application_engine": re.compile(r"\bCallAppEngine\s*\(\s*['\"]?([A-Z0-9_]+)", re.I),
    "component": re.compile(r"\bTransfer\s*\([^)]*Component\.([A-Z0-9_]+)", re.I),
    "application_package": re.compile(r"\bimport\s+([A-Z0-9_:]+)", re.I),
    "service_operation": re.compile(r"\b(?:CreateMessage|GetMessage)\s*\(\s*(?:Operation\.)?([A-Z0-9_]+)", re.I),
}
LITERAL_SQL_CALL_RE = re.compile(
    r"\b(?P<call>SQLExec|CreateSQL)\s*\(\s*(?P<literal>\"(?:\"\"|[^\"])*\"|'(?:''|[^'])*')",
    re.I | re.S,
)

# SQLExec/CreateSQL called with a variable rather than an inline literal —
# the actual SQL text lives in one or more prior `&var = ...` assignments.
_VAR_SQL_CALL_RE = re.compile(
    r"\b(?P<call>SQLExec|CreateSQL)\s*\(\s*(?P<var>&[A-Za-z_][A-Za-z0-9_]*)\s*[,)]",
    re.I,
)
# `&var = <expr>;` or `&var = &var | <expr>;` (self-append) assignment,
# single statement (PeopleCode statements are `;`-terminated, may wrap lines).
_VAR_ASSIGN_RE_TMPL = r"&{var}\s*=\s*(?:&{var}\s*\|\s*)?(.*?);"
_STRING_LITERAL_RE = re.compile(r"\"(?:\"\"|[^\"])*\"|'(?:''|[^'])*'")


def encode_reference(reference):
    return quote(reference, safe="")


def decode_reference(reference):
    return unquote(reference).upper()


def warning(code, message, detail=None):
    return ptmetadata.warning(code, message, detail=detail)


def source_tables_available(env):
    return {
        "pspcmprog": ptmetadata.has_table(env, "PSPCMPROG"),
        "pspcmtxt": ptmetadata.has_table(env, "PSPCMTXT"),
        "pspcmname": ptmetadata.has_table(env, "PSPCMNAME"),
        "pspcmdefn": ptmetadata.has_table(env, "PSPCMDEFN"),
    }


def capabilities(env):
    tables = source_tables_available(env)
    warnings = []
    if not tables["pspcmprog"]:
        warnings.append(warning(
            "peoplecode_metadata_unavailable",
            "PSPCMPROG is unavailable. PeopleCode metadata search will return no rows.",
        ))
    if not tables["pspcmtxt"]:
        warnings.append(warning(
            "peoplecode_source_unavailable",
            "PSPCMTXT is unavailable. PeopleCode source text cannot be reconstructed.",
        ))
    return {
        "tables": tables,
        "warnings": warnings,
    }


def safe_columns(env, table_name, candidates, required=None):
    try:
        return psdb.select_existing_columns(env, table_name, candidates, required=required or [])
    except Exception:
        return required or []


def reference_from_row(row):
    values = []

    for key in (
        "objectvalue1",
        "objectvalue2",
        "objectvalue3",
        "objectvalue4",
        "objectvalue5",
        "objectvalue6",
        "objectvalue7",
        "progseq",
    ):
        value = row.get(key)
        if value not in (None, "", " "):
            values.append(str(value).strip())

    if not values:
        for key in ("objectid1", "objectid2", "objectid3", "objectid4"):
            value = row.get(key)
            if value not in (None, "", " "):
                values.append(str(value).strip())

    return ".".join(values).upper() if values else None


def parent_from_reference(reference):
    parts = reference.split(".")
    if not parts:
        return {}

    first = parts[0].lower()

    if first == "record" and len(parts) >= 2:
        parent = {"type": "record", "name": parts[1]}
        if len(parts) >= 3:
            parent = {"type": "field", "name": f"{parts[1]}.{parts[2]}"}
        return parent

    if first == "component" and len(parts) >= 2:
        return {"type": "component", "name": parts[1]}

    if first in ("page", "panel") and len(parts) >= 2:
        return {"type": "page", "name": parts[1]}

    if first == "ae" and len(parts) >= 2:
        return {"type": "application_engine", "name": parts[1]}

    if first == "funclib" and len(parts) >= 2:
        return {"type": "record", "name": parts[1]}

    return {}


def extract_event(row):
    """Find the PeopleCode event name by scanning objectvalue columns for known events."""
    for key in ("objectvalue7", "objectvalue6", "objectvalue5", "objectvalue4", "objectvalue3", "objectvalue2"):
        val = (row.get(key) or "").strip()
        if val.upper() in PEOPLECODE_EVENTS:
            return val
    # fallback: last non-blank objectvalue
    for key in ("objectvalue5", "objectvalue4", "objectvalue3"):
        val = (row.get(key) or "").strip()
        if val:
            return val
    return None


def event_label(event):
    if not event:
        return None
    return PEOPLECODE_EVENT_LABELS.get(str(event).strip().upper(), event)


def _clean_value(row, key):
    val = row.get(key)
    if val in (None, "", " "):
        return None
    return str(val).strip()


def _path_item(kind, name):
    return {"kind": kind, "name": name} if name else None


def decode_semantic_path(row):
    """Decode PSPCMPROG objectvalue slots into a stable semantic path."""
    try:
        oid1 = int(row.get("objectid1"))
    except (TypeError, ValueError):
        oid1 = None

    ov = {i: _clean_value(row, f"objectvalue{i}") for i in range(1, 8)}
    event = extract_event(row)
    event_norm = event.upper() if event else None
    path = []
    event_scope = None
    subtype = None

    if oid1 == 1:
        path = [
            _path_item("record", ov[1]),
            _path_item("field", ov[2]),
            _path_item("event", event_label(event)),
        ]
        event_scope = "record_field" if ov[2] else "record"
    elif oid1 == 3:
        path = [
            _path_item("menu", ov[1]),
            _path_item("menu_item_slot", ov[2]),
            _path_item("menu_item", ov[3]),
            _path_item("event", event_label(event)),
        ]
        event_scope = "menu_item"
    elif oid1 == 9:
        path = [
            _path_item("component", ov[1]),
            _path_item("event", event_label(event)),
        ]
        event_scope = "component"
    elif oid1 == 10:
        path = [_path_item("component", ov[1]), _path_item("market", ov[2])]
        if event_norm == (ov[3] or "").upper():
            path.append(_path_item("event", event_label(event)))
            event_scope = "component_market"
        elif event_norm == (ov[4] or "").upper():
            path.extend([_path_item("record", ov[3]), _path_item("event", event_label(event))])
            event_scope = "component_record"
        else:
            path.extend([
                _path_item("record", ov[3]),
                _path_item("field", ov[4]),
                _path_item("event", event_label(event)),
            ])
            event_scope = "component_record_field"
    elif oid1 == 60:
        subtype = event_label(ov[3]) or "Subscription"
        path = [
            _path_item("service_operation", ov[1]),
            _path_item("subscription", ov[2]),
            _path_item("event", subtype),
        ]
        event_scope = "ib_subscription"
    elif oid1 == 66:
        path = [
            _path_item("application_engine", ov[1]),
            _path_item("section", ov[2]),
            _path_item("market", ov[3]),
            _path_item("database_type", ov[4]),
            _path_item("effective_date", ov[5]),
            _path_item("step", ov[6]),
            _path_item("event", event_label(event)),
        ]
        event_scope = "application_engine_step"
    elif oid1 == 74:
        subtype = event_label(ov[2]) or ov[2]
        path = [
            _path_item("component_interface", ov[1]),
            _path_item("event", subtype),
        ]
        event_scope = "component_interface"
    elif oid1 == 104:
        # App Package class PeopleCode: OV1=packageroot, OV2...(n-1)=path, OVn=OnExecute
        # Collect all non-blank OVs; the last one is the event, the rest form the class path
        parts = [ov[i] for i in range(1, 8) if ov[i]]
        if len(parts) >= 2:
            pkg_parts = parts[:-1]   # everything before the event
            path = [_path_item("application_package", pkg_parts[0])]
            if len(pkg_parts) > 2:
                path.append(_path_item("sub_package", ":".join(pkg_parts[1:-1])))
            if len(pkg_parts) > 1:
                path.append(_path_item("app_class", pkg_parts[-1]))
            path.append(_path_item("event", event_label(event)))
        else:
            path = [_path_item("application_package", ov[1]), _path_item("event", event_label(event))]
        event_scope = "app_package_class"
    else:
        path = [_path_item(f"objectvalue{i}", ov[i]) for i in range(1, 8)]

    path = [item for item in path if item and item.get("name")]
    return {
        "event_label": event_label(event),
        "event_scope": event_scope,
        "subtype": subtype,
        "semantic_path": path,
        "semantic_path_text": " / ".join(item["name"] for item in path),
    }


_OID1_PARENT_TYPES = {
    1:  "record",
    3:  "menu",
    8:  "page",
    9:  "component",
    10: "component",
    43: "menu",
    58: "component_interface",
    60: "service_operation",    # IB subscription PeopleCode: OV1 = service op name
    66: "application_engine",   # AE PeopleCode: OV1 = AE applid
    74: "component_interface",
    104: "application_package", # App Package class PeopleCode: OV1 = package root
}


def normalize_program(row, source=None):
    reference = row.get("reference") or reference_from_row(row)
    if not reference:
        reference = f"peoplecode.{row.get('progseq') or row.get('objectid1') or 'unknown'}"

    reference = reference.upper()
    parent = parent_from_reference(reference)

    oid1 = row.get("objectid1")
    object_type_label = PEOPLECODE_OBJECT_TYPES.get(
        int(oid1) if oid1 is not None else -1, f"Type {oid1}"
    )

    # Derive parent from objectid1 + objectvalue1 when reference-based detection misses
    ov1 = (row.get("objectvalue1") or "").strip()
    if oid1 is not None and ov1 and not parent.get("type"):
        derived = _OID1_PARENT_TYPES.get(int(oid1))
        if derived:
            parent = {"type": derived, "name": ov1}

    decoded = decode_semantic_path(row)

    return {
        **row,
        "reference": reference,
        "encoded_reference": encode_reference(reference),
        "parent_type": parent.get("type"),
        "parent_name": parent.get("name"),
        "object_type_label": object_type_label,
        "event": extract_event(row),
        **decoded,
        "source": source,
    }


def programs(env, q="", limit=100, offset=0):
    """Return PeopleCode program metadata from PSPCMPROG with optional search and pagination.

    Supports:
      - q: filter by object name (OBJECTVALUE columns) or source text (PSPCMTXT)
      - limit: max 2000 rows per page
      - offset: ROWS ONLY pagination for large result sets
    Returns: {items, total_hint, offset, limit, has_more, warnings}
    """
    limit = max(1, min(int(limit), 2000))
    offset = max(0, int(offset))
    caps = capabilities(env)
    if not caps["tables"]["pspcmprog"]:
        return {
            "items": [], "total_hint": 0, "offset": offset, "limit": limit,
            "has_more": False, "warnings": caps["warnings"],
        }

    candidates = [
        "OBJECTID1", "OBJECTID2", "OBJECTID3", "OBJECTID4",
        "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4",
        "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
        "PROGSEQ", "LASTUPDDTTM", "LASTUPDOPRID",
    ]
    columns = safe_columns(env, "PSPCMPROG", candidates)
    if not columns:
        return {
            "items": [], "total_hint": 0, "offset": offset, "limit": limit,
            "has_more": False,
            "warnings": [warning("peoplecode_columns_unavailable", "No readable PSPCMPROG columns were detected.")],
        }

    # Only search text (OBJECTVALUE) columns — not numeric ID or sequence columns
    text_cols = [c for c in columns if c.startswith("OBJECTVALUE")]

    predicates = []
    params = {}
    if q:
        params["q"] = f"%{q.upper()}%"
        if text_cols:
            predicates.append("(" + " OR ".join(f"UPPER({c}) LIKE :q" for c in text_cols) + ")")
    where_clause = f"WHERE {' AND '.join(predicates)}" if predicates else ""

    try:
        rows = psdb.query(env, f"""
            SELECT {", ".join(columns)}
              FROM sysadm.PSPCMPROG
              {where_clause}
             ORDER BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3, OBJECTVALUE5
             OFFSET {offset} ROWS FETCH NEXT {limit + 1} ROWS ONLY
        """, params)
    except Exception as exc:
        return {
            "items": [], "total_hint": 0, "offset": offset, "limit": limit,
            "has_more": False,
            "warnings": [warning("peoplecode_metadata_unavailable", str(exc))],
        }

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [normalize_program(row) for row in page_rows]

    # Merge source-text search results only on the first page (offset=0) with no q or with q
    if q and caps["tables"]["pspcmtxt"] and offset == 0:
        text_rows = source_search(env, q, limit)
        seen = {item["reference"] for item in items}
        for item in text_rows["items"]:
            if item["reference"] not in seen:
                items.append(item)
                seen.add(item["reference"])
        items = items[:limit]

    return {
        "items": items,
        "total_hint": None,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "warnings": caps["warnings"],
    }


def source_search(env, q, limit=100):
    columns = safe_columns(
        env,
        "PSPCMTXT",
        ["OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4",
         "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7", "PROGSEQ",
         "PCTEXT", "PROGTXT", "TXT", "TEXT", "LINE_NBR"],
    )
    # PCTEXT is canonical in PeopleTools 8.5+; older releases used PROGTXT/TXT/TEXT
    text_col = next((col for col in ("PCTEXT", "PROGTXT", "TXT", "TEXT") if col in columns), None)
    if not text_col:
        return {"items": [], "warnings": [warning("peoplecode_source_unavailable", "No source text column found in PSPCMTXT.")]}

    try:
        rows = psdb.query(env, f"""
            SELECT {", ".join(c for c in columns if c != text_col)}, {text_col}
              FROM sysadm.PSPCMTXT
             WHERE UPPER({text_col}) LIKE :q
             FETCH FIRST {max(1, min(int(limit), 500))} ROWS ONLY
        """, {"q": f"%{q.upper()}%"})
    except Exception as exc:
        return {"items": [], "warnings": [warning("peoplecode_source_unavailable", str(exc))]}

    return {
        "items": [normalize_program(row, source=row.get(text_col.lower())) for row in rows],
        "warnings": [],
    }


def program(reference, env):
    reference = decode_reference(reference)
    # Search by the first component (object name); the full dotted reference won't match
    # any single PSPCMPROG column, so we anchor on OV1 then filter for exact reference.
    first_component = reference.split(".")[0]
    rows = programs(env, first_component, 500)
    for row in rows["items"]:
        if row["reference"] == reference:
            source = source_for_reference(env, row)
            return {
                "item": normalize_program(row, source=source.get("source")),
                "warnings": rows["warnings"] + source["warnings"],
            }

    parent = parent_from_reference(reference)
    return {
        "item": {
            "reference": reference,
            "encoded_reference": encode_reference(reference),
            "parent_type": parent.get("type"),
            "parent_name": parent.get("name"),
            "source": None,
        },
        "warnings": rows["warnings"] + [warning("peoplecode_not_found", "PeopleCode metadata was not found for this reference.")],
    }


def source_for_reference(env, program_row):
    caps = capabilities(env)
    if not caps["tables"]["pspcmtxt"]:
        return {
            "source": None,
            "warnings": [warning("peoplecode_source_unavailable", "PSPCMTXT is unavailable.")],
        }

    columns = safe_columns(
        env,
        "PSPCMTXT",
        ["OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4", "OBJECTVALUE5",
         "OBJECTVALUE6", "OBJECTVALUE7", "PROGSEQ", "PCTEXT", "PROGTXT", "TXT", "TEXT", "LINE_NBR"],
    )
    # PCTEXT is the canonical column name in PeopleTools 8.5+; older releases used PROGTXT/TXT/TEXT
    text_col = next((col for col in ("PCTEXT", "PROGTXT", "TXT", "TEXT") if col in columns), None)
    if not text_col:
        return {
            "source": None,
            "warnings": [warning("peoplecode_source_unavailable", "No source text column found in PSPCMTXT.")],
        }

    # Match on OBJECTVALUEn columns that have data (skip blanks/spaces)
    # PSPCMPROG has objectvalue1..7; PSPCMTXT has the same key columns
    predicates = []
    params = {}
    for key in ("objectvalue1", "objectvalue2", "objectvalue3", "objectvalue4",
                "objectvalue5", "objectvalue6", "objectvalue7"):
        col = key.upper()
        if col in columns and program_row.get(key) not in (None, "", " "):
            predicates.append(f"UPPER({col}) = UPPER(:{key})")
            params[key] = program_row.get(key)

    if "PROGSEQ" in columns and program_row.get("progseq") not in (None, "", " "):
        predicates.append("PROGSEQ = :progseq")
        params["progseq"] = program_row.get("progseq")

    if not predicates:
        return {
            "source": program_row.get("source"),
            "warnings": [warning("peoplecode_source_unavailable", "Insufficient metadata to reconstruct source text.")],
        }

    try:
        rows = psdb.query(env, f"""
            SELECT {text_col} AS source_chunk
              FROM sysadm.PSPCMTXT
             WHERE {" AND ".join(predicates)}
             ORDER BY PROGSEQ
        """, params)
    except Exception as exc:
        return {
            "source": program_row.get("source"),
            "warnings": [warning("peoplecode_source_unavailable", str(exc))],
        }

    return {
        "source": "".join(str(row.get("source_chunk") or "") for row in rows).rstrip(),
        "warnings": [],
    }


def extract_calls(source):
    if not source:
        return []

    calls = []
    for name in CALL_NAMES:
        pattern = re.compile(rf"\b{name}\s*\(", re.I)
        count = len(pattern.findall(source))
        if count:
            calls.append({
                "name": name,
                "count": count,
                "type": "function",
            })
    return calls


def extract_references(source):
    if not source:
        return {
            "records": [],
            "fields": [],
            "components": [],
            "pages": [],
            "sql_definitions": [],
            "functions": [],
            "classes": [],
            "application_engines": [],
            "service_operations": [],
        }

    refs = {
        "records": sorted(set(REFERENCE_PATTERNS["record"].findall(source))),
        "fields": sorted(set(REFERENCE_PATTERNS["field"].findall(source))),
        "components": sorted(set(REFERENCE_PATTERNS["component"].findall(source))),
        "pages": [],
        "sql_definitions": sorted(set(REFERENCE_PATTERNS["sql_definition"].findall(source))),
        "functions": [call["name"] for call in extract_calls(source)],
        "classes": sorted(set(REFERENCE_PATTERNS["application_package"].findall(source))),
        "application_engines": sorted(set(REFERENCE_PATTERNS["application_engine"].findall(source))),
        "service_operations": sorted(set(REFERENCE_PATTERNS["service_operation"].findall(source))),
    }
    return refs


def _decode_peoplecode_string_literal(literal):
    literal = str(literal or "")
    if len(literal) < 2:
        return ""
    quote = literal[0]
    body = literal[1:-1]
    if quote == '"':
        return body.replace('""', '"')
    if quote == "'":
        return body.replace("''", "'")
    return body


def extract_literal_sql(source):
    """Return literal SQL strings passed directly to SQLExec/CreateSQL."""
    if not source:
        return []

    statements = []
    for match in LITERAL_SQL_CALL_RE.finditer(source):
        sql_text = _decode_peoplecode_string_literal(match.group("literal")).strip()
        if not sql_text:
            continue
        statements.append({
            "call": match.group("call"),
            "sql_text": sql_text,
        })
    return statements


def extract_dynamic_sql(source):
    """
    Best-effort recovery of SQL text for `SQLExec(&var, ...)` / `CreateSQL(&var)`
    calls where the SQL is built via variable assignment/concatenation instead
    of passed as an inline literal — e.g.:

        &strSQL = "SELECT * FROM PS_JOB WHERE ...";
        &strSQL = &strSQL | " AND EFFDT = (SELECT MAX(EFFDT) FROM PS_JOB ...";
        SQLExec(&strSQL, %This.EmplId, &recJob);

    This is a purely textual, best-effort reconstruction (no expression
    evaluation): it concatenates every string *literal* fragment assigned to
    the variable anywhere earlier in the same program, in source order, and
    ignores non-literal fragments (other variables, function calls, %Table()
    macros with bind-parameter table names, etc.). That means dynamically
    chosen table names (`"FROM PS_" | &recname`) are silently dropped from
    the reconstructed text rather than guessed — consistent with the rest of
    this codebase's "conservative, no crash, best-effort" extraction rules.
    """
    if not source:
        return []

    statements = []
    for match in _VAR_SQL_CALL_RE.finditer(source):
        var = match.group("var")
        call_start = match.start()
        var_name = re.escape(var[1:])  # drop leading '&', escape for embedding
        assign_re = re.compile(_VAR_ASSIGN_RE_TMPL.format(var=var_name), re.I | re.S)

        literal_fragments = []
        for assign in assign_re.finditer(source, 0, call_start):
            rhs = assign.group(1)
            for lit in _STRING_LITERAL_RE.finditer(rhs):
                decoded = _decode_peoplecode_string_literal(lit.group(0)).strip()
                if decoded:
                    literal_fragments.append(decoded)

        if not literal_fragments:
            continue

        statements.append({
            "call": match.group("call"),
            "var": var,
            "sql_text": " ".join(literal_fragments),
        })
    return statements


def references(reference, env):
    result = program(reference, env)
    source = result["item"].get("source")
    return {
        "reference": result["item"]["reference"],
        "references": extract_references(source),
        "calls": extract_calls(source),
        "literal_sql": extract_literal_sql(source),
        "dynamic_sql": extract_dynamic_sql(source),
        "warnings": result["warnings"],
    }


def references_for_program(env, program_row):
    """Extract references using an already-loaded PSPCMPROG row."""
    item = normalize_program(program_row, source=program_row.get("source"))
    source = item.get("source")
    warnings = []
    if source is None:
        source_result = source_for_reference(env, item)
        source = source_result.get("source")
        warnings = source_result.get("warnings", [])

    return {
        "reference": item["reference"],
        "references": extract_references(source),
        "calls": extract_calls(source),
        "literal_sql": extract_literal_sql(source),
        "dynamic_sql": extract_dynamic_sql(source),
        "warnings": warnings,
    }


def graph(reference, env):
    result = program(reference, env)
    item = result["item"]
    ref = item["reference"]
    refs = extract_references(item.get("source"))
    calls = extract_calls(item.get("source"))
    nodes = [{
        "id": f"peoplecode:{ref}",
        "type": "peoplecode",
        "name": ref,
        "label": ref,
        "data": item,
        "_links": {"admin": f"/admin/object/peoplecode/{encode_reference(ref)}"},
    }]
    edges = []

    if item.get("parent_type") and item.get("parent_name"):
        nodes.append({
            "id": f"{item['parent_type']}:{item['parent_name']}",
            "type": item["parent_type"],
            "name": item["parent_name"],
            "label": item["parent_name"],
            "data": {},
            "_links": {"admin": f"/admin/object/{item['parent_type']}/{item['parent_name']}"},
        })
        edges.append({
            "source": f"peoplecode:{ref}",
            "target": f"{item['parent_type']}:{item['parent_name']}",
            "relationship": "BELONGS_TO",
        })

    for record in refs["records"]:
        nodes.append({"id": f"record:{record}", "type": "record", "name": record, "label": record, "data": {}, "_links": {"admin": f"/admin/object/record/{record}"}})
        edges.append({"source": f"peoplecode:{ref}", "target": f"record:{record}", "relationship": "REFERENCES"})

    for field in refs["fields"]:
        nodes.append({"id": f"field:{field}", "type": "field", "name": field, "label": field, "data": {}, "_links": {"admin": f"/admin/object/field/{field}"}})
        edges.append({"source": f"peoplecode:{ref}", "target": f"field:{field}", "relationship": "REFERENCES"})

    for sql_name in refs["sql_definitions"]:
        nodes.append({"id": f"sql_definition:{sql_name}", "type": "sql_definition", "name": sql_name, "label": sql_name, "data": {}, "_links": {"admin": f"/admin/object/sql_definition/{sql_name}"}})
        edges.append({"source": f"peoplecode:{ref}", "target": f"sql_definition:{sql_name}", "relationship": "USES"})

    for call in calls:
        nodes.append({"id": f"function:{call['name'].upper()}", "type": "function", "name": call["name"], "label": call["name"], "data": call, "_links": {"admin": f"/admin/object/function/{call['name']}"}})
        edges.append({"source": f"peoplecode:{ref}", "target": f"function:{call['name'].upper()}", "relationship": "CALLS"})

    return graphshape.annotate_graph({
        "root": f"peoplecode:{ref}",
        "nodes": nodes,
        "edges": edges,
        "warnings": result["warnings"],
    }, "peoplecode", "domain_peoplecode", "source-reference graph")


# ── Component Event Flow ──────────────────────────────────────────────────────

_PHASE_MAP = {
    "SearchInit": "search", "SearchSave": "search", "SearchDefault": "search",
    "PreBuild": "build", "FieldDefault": "build", "FieldFormula": "build",
    "RowInit": "build", "PostBuild": "build", "Activate": "build",
    "RowSelect": "build",
    "FieldEdit": "interaction", "FieldChange": "interaction",
    "PrePopup": "interaction", "ItemSelected": "interaction",
    "RowInsert": "interaction", "RowDelete": "interaction",
    "SaveEdit": "save", "SavePreChange": "save",
    "Workflow": "save", "SavePostChange": "save",
}

_DELIVERED_OPRIDS = {"PPLSOFT", "PSOPRDEFN", "BATCH", "PTADMIN", ""}

# Canonical PeopleSoft component processing sequence — the same ordered
# event list the /admin/compseq ("PC Timeline") page renders, moved here so
# it's a real, independently queryable backend artifact instead of only
# existing as a hardcoded JS array (routers/admin/compflow.py). Ordinal is
# the position within the whole sequence (not just within its phase).
CANONICAL_COMPONENT_SEQUENCE = [
    {
        "phase": "search", "label": "Search Phase",
        "desc": "Executes before the component search dialog opens",
        "events": [
            {"name": "SearchInit", "scope": "Component", "note": "Initialise search page"},
            {"name": "SearchSave", "scope": "Component", "note": "Validate search criteria"},
            {"name": "SearchDefault", "scope": "Record/Field", "note": "Default search keys"},
        ],
    },
    {
        "phase": "build", "label": "Build Phase",
        "desc": "Executes when the component buffer is loaded",
        "events": [
            {"name": "PreBuild", "scope": "Component", "note": "Before buffers loaded"},
            {"name": "FieldDefault", "scope": "Record/Field", "note": "Default field values"},
            {"name": "FieldFormula", "scope": "Record/Field", "note": "Derived / formula fields"},
            {"name": "RowInit", "scope": "Record/Field", "note": "Initialise each row"},
            {"name": "PostBuild", "scope": "Component", "note": "After buffers loaded"},
            {"name": "Activate", "scope": "Component", "note": "Page activation"},
            {"name": "RowSelect", "scope": "Record/Field", "note": "Filter rows on select"},
        ],
    },
    {
        "phase": "interaction", "label": "Interaction Phase",
        "desc": "Executes during user interaction (field changes, row actions)",
        "events": [
            {"name": "FieldEdit", "scope": "Record/Field", "note": "Validate field value"},
            {"name": "FieldChange", "scope": "Record/Field", "note": "React to field change"},
            {"name": "PrePopup", "scope": "Record/Field", "note": "Before popup menu"},
            {"name": "ItemSelected", "scope": "Record/Field", "note": "List item selected"},
            {"name": "RowInsert", "scope": "Record", "note": "Row inserted"},
            {"name": "RowDelete", "scope": "Record", "note": "Row deleted"},
        ],
    },
    {
        "phase": "save", "label": "Save Phase",
        "desc": "Executes during the save cycle",
        "events": [
            {"name": "SaveEdit", "scope": "Record/Field", "note": "Validate before save"},
            {"name": "SavePreChange", "scope": "Record/Field", "note": "Before DB write"},
            {"name": "Workflow", "scope": "Component", "note": "Workflow/notification"},
            {"name": "SavePostChange", "scope": "Record/Field", "note": "After DB write"},
        ],
    },
]


# Semantic classification of canonical events, for KG edge typing beyond plain
# ordering (FIRES_BEFORE/FIRES_AFTER). Derived directly from each event's own
# documented PeopleTools semantics — the same meaning already captured in the
# "note" field above (e.g. SavePreChange/SavePostChange are literally "before/
# after DB write") — not a new or fabricated classification.
#   VALIDATES_BEFORE_SAVE — the event whose entire purpose is validating the
#     buffer before the save commits.
#   MUTATES_DATABASE      — events that fire immediately around the actual
#     database write (as opposed to in-memory buffer changes).
#   MUTATES_BUFFER        — Build/Interaction-phase events that change the
#     in-memory component buffer (field values, row membership) but do not
#     themselves touch the database.
_EVENT_SEMANTIC_EDGES: dict[str, list[str]] = {
    "SaveEdit":        ["VALIDATES_BEFORE_SAVE"],
    "SavePreChange":   ["MUTATES_DATABASE"],
    "SavePostChange":  ["MUTATES_DATABASE"],
    "RowInit":         ["MUTATES_BUFFER"],
    "FieldDefault":    ["MUTATES_BUFFER"],
    "FieldFormula":    ["MUTATES_BUFFER"],
    "RowSelect":       ["MUTATES_BUFFER"],
    "FieldEdit":       ["MUTATES_BUFFER"],
    "FieldChange":     ["MUTATES_BUFFER"],
    "RowInsert":       ["MUTATES_BUFFER"],
    "RowDelete":       ["MUTATES_BUFFER"],
}


def event_semantic_edges(event_name: str) -> list[str]:
    """Return the semantic KG edge relations (beyond FIRES_BEFORE/AFTER) that
    apply to a canonical event name, e.g. 'SaveEdit' -> ['VALIDATES_BEFORE_SAVE'].
    Empty list for events with no additional semantic classification."""
    return list(_EVENT_SEMANTIC_EDGES.get(event_name, []))


def component_sequence(env, comp):
    """Slot a component's real PeopleCode events into the canonical ordered
    sequence, marking each slot empty/delivered/custom.

    Returns:
        {component, owner, phases: [{phase, label, desc, events: [
            {name, scope, note, ordinal, status, record, field,
             last_oprid, last_dttm}
        ]}], warnings}

    status is one of "empty" (no PeopleCode for this event in this
    component), "delivered", or "custom" (per the same LASTUPDOPRID
    heuristic component_events() already uses).
    """
    result = component_events(env, comp)
    events_by_name: dict[str, list[dict]] = {}
    for ev in result.get("events", []):
        events_by_name.setdefault(ev["event"], []).append(ev)

    ordinal = 0
    phases = []
    for phase_def in CANONICAL_COMPONENT_SEQUENCE:
        phase_events = []
        for ev_def in phase_def["events"]:
            matches = events_by_name.get(ev_def["name"], [])
            if not matches:
                phase_events.append({
                    "name": ev_def["name"], "scope": ev_def["scope"], "note": ev_def["note"],
                    "ordinal": ordinal, "status": "empty",
                    "record": None, "field": None, "last_oprid": None, "last_dttm": None,
                })
            else:
                for m in matches:
                    phase_events.append({
                        "name": ev_def["name"], "scope": ev_def["scope"], "note": ev_def["note"],
                        "ordinal": ordinal,
                        "status": "custom" if m.get("modified") else "delivered",
                        "record": m.get("record"), "field": m.get("field"),
                        "last_oprid": m.get("last_oprid"), "last_dttm": m.get("last_dttm"),
                    })
            ordinal += 1
        phases.append({
            "phase": phase_def["phase"], "label": phase_def["label"],
            "desc": phase_def["desc"], "events": phase_events,
        })

    return {
        "component": result.get("component", comp.upper()),
        "owner": result.get("component_owner"),
        "phases": phases,
        "warnings": result.get("warnings", []),
    }


# Record Field PeopleCode (PSPCMPROG OBJECTID1=1) is owned by the record
# itself, independent of any component — a genuinely different PeopleSoft
# object category from Component-scoped PeopleCode, not a re-skin of it.
# It uses the same real event vocabulary as CANONICAL_COMPONENT_SEQUENCE
# (these are literally the same PeopleCode event names), just without the
# Component-only events (PreBuild/PostBuild/Activate/Workflow/SearchInit/
# SearchSave) that require a component context to exist at all.
_RECORD_OWNED_SCOPES = {"Record/Field", "Record"}


def _record_field_events(env, recname):
    """Query PSPCMPROG OBJECTID1=1 rows for a record — the record's own
    Field PeopleCode, independent of any component."""
    if not ptmetadata.has_table(env, "PSPCMPROG"):
        return {"events": [], "warnings": ["PSPCMPROG not accessible."]}

    try:
        columns = psdb.select_existing_columns(env, "PSPCMPROG", [
            "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4",
            "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
            "PROGSEQ", "LASTUPDOPRID", "LASTUPDDTTM",
        ])
    except Exception as exc:
        return {"events": [], "warnings": [str(exc)]}

    try:
        rows = psdb.query(env, f"""
            SELECT {", ".join(columns)}
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 = 1
               AND UPPER(OBJECTVALUE1) = UPPER(:recname)
             ORDER BY OBJECTVALUE2, OBJECTVALUE3, PROGSEQ
        """, {"recname": recname.upper()})
    except Exception as exc:
        return {"events": [], "warnings": [str(exc)]}

    events = []
    for row in rows:
        r = {k.lower(): v for k, v in row.items()}
        ev = extract_event(r)
        if not ev:
            continue
        field = (r.get("objectvalue2") or "").strip() or None
        oprid = (r.get("lastupdoprid") or "").strip()
        dttm = r.get("lastupddttm")
        modified = oprid.upper() not in _DELIVERED_OPRIDS
        events.append({
            "event": PEOPLECODE_EVENT_LABELS.get(ev.upper(), ev),
            "field": field,
            "modified": modified,
            "last_oprid": oprid if modified else None,
            "last_dttm": str(dttm)[:19] if dttm and modified else None,
        })

    return {"events": events, "warnings": []}


def record_sequence(env, recname):
    """Slot a record's own Field PeopleCode (OBJECTID1=1, independent of any
    component) into the canonical event order, marking each slot
    empty/delivered/custom — the same status semantics as
    component_sequence(), but scoped to genuinely record-owned PeopleCode.

    Returns:
        {record, phases: [{phase, label, desc, events: [
            {name, note, ordinal, status, field, last_oprid, last_dttm}
        ]}], warnings}
    """
    result = _record_field_events(env, recname)
    events_by_name: dict[str, list[dict]] = {}
    for ev in result.get("events", []):
        events_by_name.setdefault(ev["event"], []).append(ev)

    ordinal = 0
    phases = []
    for phase_def in CANONICAL_COMPONENT_SEQUENCE:
        phase_events = []
        for ev_def in phase_def["events"]:
            if ev_def["scope"] not in _RECORD_OWNED_SCOPES:
                continue
            matches = events_by_name.get(ev_def["name"], [])
            if not matches:
                phase_events.append({
                    "name": ev_def["name"], "note": ev_def["note"],
                    "ordinal": ordinal, "status": "empty",
                    "field": None, "last_oprid": None, "last_dttm": None,
                })
            else:
                for m in matches:
                    phase_events.append({
                        "name": ev_def["name"], "note": ev_def["note"],
                        "ordinal": ordinal,
                        "status": "custom" if m.get("modified") else "delivered",
                        "field": m.get("field"),
                        "last_oprid": m.get("last_oprid"), "last_dttm": m.get("last_dttm"),
                    })
            ordinal += 1
        if not phase_events:
            continue
        phases.append({
            "phase": phase_def["phase"], "label": phase_def["label"],
            "desc": phase_def["desc"], "events": phase_events,
        })

    return {
        "record": recname.upper(),
        "phases": phases,
        "warnings": result.get("warnings", []),
    }


def page_owned_events(env, pnlname):
    """Return Page-owned PeopleCode (PSPCMPROG OBJECTID1=8) — a real,
    distinct PeopleTools category (Page Activate etc.) independent of
    Component-level PeopleCode, which is what /admin/page already shows.

    No canonical ordering: unlike Component/Record, Page-owned PeopleCode
    doesn't have a rich multi-phase lifecycle — just a flat set of
    page-object-level events. Gracefully returns an empty list rather than
    erroring when a PeopleTools version/environment has none (this
    category is legitimately unpopulated in some environments).
    """
    if not ptmetadata.has_table(env, "PSPCMPROG"):
        return {"page": pnlname.upper(), "events": [], "warnings": ["PSPCMPROG not accessible."]}

    try:
        columns = psdb.select_existing_columns(env, "PSPCMPROG", [
            "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4",
            "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
            "PROGSEQ", "LASTUPDOPRID", "LASTUPDDTTM",
        ])
    except Exception as exc:
        return {"page": pnlname.upper(), "events": [], "warnings": [str(exc)]}

    try:
        rows = psdb.query(env, f"""
            SELECT {", ".join(columns)}
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 = 8
               AND UPPER(OBJECTVALUE1) = UPPER(:pnlname)
             ORDER BY OBJECTVALUE2, PROGSEQ
        """, {"pnlname": pnlname.upper()})
    except Exception as exc:
        return {"page": pnlname.upper(), "events": [], "warnings": [str(exc)]}

    events = []
    for row in rows:
        r = {k.lower(): v for k, v in row.items()}
        ev = extract_event(r)
        if not ev:
            continue
        oprid = (r.get("lastupdoprid") or "").strip()
        dttm = r.get("lastupddttm")
        modified = oprid.upper() not in _DELIVERED_OPRIDS
        events.append({
            "event": PEOPLECODE_EVENT_LABELS.get(ev.upper(), ev),
            "modified": modified,
            "last_oprid": oprid if modified else None,
            "last_dttm": str(dttm)[:19] if dttm and modified else None,
        })

    return {"page": pnlname.upper(), "events": events, "warnings": []}


def component_events(env, comp):
    """Return all PeopleCode events for a component, structured for the event flow UI."""
    caps = capabilities(env)
    if not caps["tables"]["pspcmprog"]:
        return {"component": comp.upper(), "events": [], "warnings": ["PSPCMPROG not accessible."]}

    try:
        columns = psdb.select_existing_columns(env, "PSPCMPROG", [
            "OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3",
            "OBJECTVALUE4", "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
            "PROGSEQ", "LASTUPDOPRID", "LASTUPDDTTM",
        ])
    except Exception as exc:
        return {"component": comp.upper(), "events": [], "warnings": [str(exc)]}

    col_list = ", ".join(columns)
    try:
        rows = psdb.query(env, f"""
            SELECT {col_list}
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 IN (9, 10)
               AND UPPER(OBJECTVALUE1) = UPPER(:comp)
             ORDER BY OBJECTID1, OBJECTVALUE3, OBJECTVALUE4, OBJECTVALUE5, OBJECTVALUE6
        """, {"comp": comp.upper()})
    except Exception as exc:
        return {"component": comp.upper(), "events": [], "warnings": [str(exc)]}

    comp_owner = None
    try:
        owner_rows = psdb.query(env, """
            SELECT OBJECTOWNERID FROM SYSADM.PSPNLGRPDEFN
             WHERE UPPER(PNLGRPNAME) = UPPER(:comp) AND ROWNUM = 1
        """, {"comp": comp.upper()})
        if owner_rows:
            comp_owner = (owner_rows[0].get("objectownerid") or "").strip() or None
    except Exception:
        pass

    events = []
    for row in rows:
        r = {k.lower(): v for k, v in row.items()}
        oid1 = int(r.get("objectid1") or 0)
        ov = {i: (r.get(f"objectvalue{i}") or "").strip() for i in range(1, 8)}

        ev = extract_event(r)
        if not ev:
            continue
        ev_label = PEOPLECODE_EVENT_LABELS.get(ev.upper(), ev)
        ev_up = ev.upper()

        if oid1 == 9:
            record, field, scope = None, None, "Component"
        elif oid1 == 10:
            if ov[3] and ev_up == ov[3].upper():
                record, field, scope = None, None, "Component"
            elif ov[4] and ev_up == ov[4].upper():
                record, field, scope = ov[3] or None, None, "Record"
            else:
                record = ov[3] or None
                field = ov[4] or None
                scope = "Field" if field else "Record"
        else:
            continue

        oprid = (r.get("lastupdoprid") or "").strip()
        dttm = r.get("lastupddttm")
        modified = oprid.upper() not in _DELIVERED_OPRIDS

        events.append({
            "event": ev_label,
            "record": record,
            "field": field,
            "scope": scope,
            "phase": _PHASE_MAP.get(ev_label, "other"),
            "modified": modified,
            "last_oprid": oprid if modified else None,
            "last_dttm": str(dttm)[:19] if dttm and modified else None,
        })

    return {
        "component": comp.upper(),
        "component_owner": comp_owner,
        "events": events,
        "warnings": [],
    }


def component_event_source(env, comp, event, record=None, field=None):
    """Fetch PeopleCode source for one specific component event."""
    caps = capabilities(env)
    if not caps["tables"]["pspcmprog"]:
        return {"source": None, "warnings": ["PSPCMPROG not accessible."]}

    try:
        columns = psdb.select_existing_columns(env, "PSPCMPROG", [
            "OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3",
            "OBJECTVALUE4", "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
            "PROGSEQ",
        ])
    except Exception as exc:
        return {"source": None, "warnings": [str(exc)]}

    col_list = ", ".join(columns)
    try:
        rows = psdb.query(env, f"""
            SELECT {col_list}
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 IN (9, 10)
               AND UPPER(OBJECTVALUE1) = UPPER(:comp)
        """, {"comp": comp.upper()})
    except Exception as exc:
        return {"source": None, "warnings": [str(exc)]}

    ev_up = event.upper()
    rec_up = record.upper() if record else None
    fld_up = field.upper() if field else None

    for row in rows:
        r = {k.lower(): v for k, v in row.items()}
        oid1 = int(r.get("objectid1") or 0)
        ov = {i: (r.get(f"objectvalue{i}") or "").strip() for i in range(1, 8)}

        ev = extract_event(r)
        if not ev or ev.upper() != ev_up:
            continue

        if oid1 == 9:
            if not rec_up and not fld_up:
                return source_for_reference(env, r)
        elif oid1 == 10:
            if ov[3] and ev_up == ov[3].upper():
                if not rec_up and not fld_up:
                    return source_for_reference(env, r)
            elif ov[4] and ev_up == ov[4].upper():
                row_rec = ov[3].upper() if ov[3] else None
                if not fld_up and (not rec_up or row_rec == rec_up):
                    return source_for_reference(env, r)
            else:
                row_rec = ov[3].upper() if ov[3] else None
                row_fld = ov[4].upper() if ov[4] else None
                if rec_up and row_rec == rec_up and fld_up and row_fld == fld_up:
                    return source_for_reference(env, r)

    return {"source": None, "warnings": [f"No PeopleCode found for {event} on {comp}."]}
