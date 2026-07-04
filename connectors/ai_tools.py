"""
AI tool definitions and dispatch.

Each tool wraps an existing DeathStar connector function — no new SQL.
Tool schemas are in Anthropic format (name, description, input_schema).
The dispatch() function routes a tool call to its implementation.
"""

import json
from connectors import ptmetadata, peoplecode, graphdb, psdb
from connectors import envcompare, impact

# ── Tool definitions (Anthropic format; converted to OpenAI by provider layer) ──

TOOLS = [
    {
        "name": "search_objects",
        "description": (
            "Search for PeopleSoft objects (records, fields, components, pages, AE programs, "
            "PeopleCode programs, SQL definitions, queries, menus, trees, roles, permission lists, "
            "IB routings, messages, nodes, CI, etc.) by name. Use this to find what objects exist "
            "or to get the object ID for further lookups."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":   {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "query": {"type": "string", "description": "Name or partial name to search for"},
                "type":  {"type": "string", "description": "Optional: filter to a specific object type (record, field, component, page, application_engine, peoplecode, sql_definition, query, menu, role, permissionlist, etc.)"},
            },
            "required": ["env", "query"],
        },
    },
    {
        "name": "peoplecode_search",
        "description": (
            "Full-text search through PeopleCode source across all programs. Use this to find "
            "where a function, method, field reference, or SQL statement appears in PeopleCode. "
            "Returns program references and code snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":   {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "query": {"type": "string", "description": "Text to search for in PeopleCode source"},
                "limit": {"type": "integer", "description": "Max results (default 20, max 100)"},
            },
            "required": ["env", "query"],
        },
    },
    {
        "name": "graph_dependencies",
        "description": (
            "Find what a PeopleSoft object DEPENDS ON — i.e. traverse forward in the knowledge "
            "graph to see what other objects this object uses or references. Use this to understand "
            "what an object is built from."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":     {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "node_id": {"type": "string", "description": "Node ID from search_objects (e.g. record:PS_JOB or component:JOB_DATA)"},
                "depth":   {"type": "integer", "description": "Traversal depth (default 2, max 4)"},
            },
            "required": ["env", "node_id"],
        },
    },
    {
        "name": "graph_impact",
        "description": (
            "Find what DEPENDS ON a PeopleSoft object — i.e. traverse reverse in the knowledge "
            "graph to see what other objects reference or use this object. Use this to understand "
            "the blast radius of changing something."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":     {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "node_id": {"type": "string", "description": "Node ID from search_objects"},
                "depth":   {"type": "integer", "description": "Traversal depth (default 2, max 4)"},
            },
            "required": ["env", "node_id"],
        },
    },
    {
        "name": "who_has_access",
        "description": (
            "Find which roles and permission lists grant access to a component, and how many "
            "operators hold those roles. Use this to answer security and access questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":       {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "component": {"type": "string", "description": "Component name (PNLGRPNAME)"},
            },
            "required": ["env", "component"],
        },
    },
    {
        "name": "ae_steps",
        "description": (
            "List the sections and steps of an Application Engine program, including SQL text "
            "and PeopleCode references. Use this to understand what an AE does."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":      {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "ae_name":  {"type": "string", "description": "AE program name (AE_APPLID)"},
            },
            "required": ["env", "ae_name"],
        },
    },
    {
        "name": "sql_lookup",
        "description": (
            "Look up a SQL definition by name (SQLID) and return its SQL text. Use this to see "
            "what a named SQL object does, or to understand what tables/columns it touches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":   {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "sqlid": {"type": "string", "description": "SQL definition name (SQLID in PSSQLDEFN)"},
            },
            "required": ["env", "sqlid"],
        },
    },
    {
        "name": "envcompare_summary",
        "description": (
            "Return a high-level count comparison of all object types between two environments. "
            "Use this to understand the overall scale of difference between HCM and FSCM."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env1": {"type": "string", "description": "First environment", "enum": ["HCM", "FSCM"]},
                "env2": {"type": "string", "description": "Second environment", "enum": ["HCM", "FSCM"]},
            },
            "required": ["env1", "env2"],
        },
    },
    {
        "name": "project_impact",
        "description": (
            "Assess the downstream impact of a PeopleSoft project before migration. Enumerates "
            "project objects, looks them up in the knowledge graph, and returns affected node "
            "counts by type plus a risk label."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":     {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "project": {"type": "string", "description": "Project name (PSPROJECTDEFN)"},
            },
            "required": ["env", "project"],
        },
    },
    {
        "name": "active_sessions",
        "description": (
            "Show active and recent PeopleSoft user sessions from PSACCESSLOG. "
            "IMPORTANT: In PeopleSoft, each page request creates its own log row (LOGINDTTM=LOGOUTDTTM). "
            "A user is 'currently active' if they have made a request within the last `active_minutes` minutes — "
            "returned in the `recently_active` list with is_active=true. "
            "Returns: (1) recently_active — users active RIGHT NOW within `active_minutes` window; "
            "(2) currently_active — sessions with open LOGOUTDTTM (rare in PS, usually 0); "
            "(3) recent_users — all users in the broader `hours` window; "
            "(4) signon type breakdown (type 1 = SSO/web browser users, type 0 = service accounts/IB). "
            "Use this for: 'Who is in HCM right now?', 'Show active sessions', "
            "'Is GUACUSER logged in?', 'How many users are currently using the system?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":            {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "hours":          {"type": "integer", "description": "Lookback window in hours for recent_users history (default 8)"},
                "active_minutes": {"type": "integer", "description": "Window in minutes for 'currently active' detection (default 30). Increase to 60 if unsure."},
                "limit":          {"type": "integer", "description": "Max users to return (default 50)"},
            },
            "required": ["env"],
        },
    },
    {
        "name": "record_usage",
        "description": (
            "Find every component, page, and AE program that uses a PeopleSoft record. "
            "Queries live metadata tables (PSPNLFIELD, PSPNLGROUP, PSPNLGRPDEFN, PSAEAPPLSTATE, PSRECFIELD) "
            "directly — not limited by Knowledge Graph coverage. "
            "Use this for questions like: 'What components use record JOB?', "
            "'What pages display JOB data?', 'What records inherit from JOB?', "
            "'What AE programs use JOB as a state record?'. "
            "PREFER this over graph_impact for record dependency questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":    {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "record": {"type": "string", "description": "Record name (RECNAME), e.g. JOB, JOB_DATA, PERSONAL_DATA"},
            },
            "required": ["env", "record"],
        },
    },
    {
        "name": "environment_health",
        "description": (
            "Perform a live health check on a PeopleSoft environment. "
            "ALWAYS call this first when you see connectivity errors, HTTP 502/503, "
            "ExternalApplicationException, IB timeout errors, or any 'system unavailable' symptoms. "
            "Returns: Oracle DB connectivity status, active user session count, "
            "recent error spike (log errors in last hour vs last 24h), "
            "IB domain dispatcher status, Integration Broker failed/cancelled transaction counts, "
            "and process scheduler queue health. "
            "This tells you if the environment is UP or DOWN before giving any advice."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "description": "Environment to health-check: HCM or FSCM", "enum": ["HCM", "FSCM"]},
            },
            "required": ["env"],
        },
    },
    {
        "name": "ib_diagnostics",
        "description": (
            "Deep Integration Broker diagnostics for a specific environment. "
            "Use when you see IB errors, message failures, node connectivity issues, "
            "ExternalApplicationException, or when environment_health shows IB problems. "
            "Returns: all IB node definitions (active/inactive, local/remote, target URL), "
            "IB domain dispatcher status, failed/cancelled transaction counts by queue and status, "
            "and recent failed transactions with error detail. "
            "Use node_name to focus on a specific node (e.g. PSFT_EP for a remote node)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":       {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "node_name": {"type": "string", "description": "Optional: filter to a specific IB node name (e.g. PSFT_EP, ANONYMOUS)"},
            },
            "required": ["env"],
        },
    },
    {
        "name": "process_scheduler_health",
        "description": (
            "Check Process Scheduler queue status and recent job failures. "
            "Use when users report processes not running, stuck jobs, or scheduler unavailability. "
            "Returns: counts by run status (running, queued, error, success), "
            "recently failed jobs with error message, stuck/long-running jobs, "
            "and server heartbeat (last contact from each scheduler server). "
            "Also flags if no scheduler server has checked in recently (offline indicator)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":   {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "hours": {"type": "integer", "description": "Hours to look back for recent jobs (default 24)"},
            },
            "required": ["env"],
        },
    },
    {
        "name": "log_search",
        "description": (
            "Search ingested web server and application server logs. "
            "Use this to find what an OPRID was doing in the logs, or to search for errors, "
            "component access, or any text pattern across web/app log entries. "
            "Requires log sources to be configured and ingested. "
            "Use for: 'What was GUACUSER doing in HCM at 10am?', "
            "'Show me errors in the app server logs', 'Did anyone access component X today?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":         {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "tier":        {"type": "string", "description": "web | app | both (default: both)", "enum": ["web", "app", "both"]},
                "oprid":       {"type": "string", "description": "Filter to a specific user OPRID"},
                "component":   {"type": "string", "description": "Filter web entries to a specific component name"},
                "errors_only": {"type": "boolean", "description": "If true, return only error entries"},
                "start":       {"type": "string", "description": "ISO datetime start (e.g. 2026-07-01T08:00:00)"},
                "end":         {"type": "string", "description": "ISO datetime end"},
                "limit":       {"type": "integer", "description": "Max rows to return (default 100)"},
            },
            "required": ["env"],
        },
    },
    {
        "name": "log_errors",
        "description": (
            "Return a summary of errors from ingested logs, grouped by error code and object. "
            "Shows which errors occur most frequently, which objects/components are responsible, "
            "and which users triggered them. "
            "Use this for: 'What errors are we seeing in HCM?', 'Are there ORA errors in the app logs?', "
            "'What objects are causing errors?'. "
            "Returns error_code, object_ref, count, first_seen, last_seen, and sample OPRIDs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env":        {"type": "string", "description": "Environment: HCM or FSCM", "enum": ["HCM", "FSCM"]},
                "error_code": {"type": "string", "description": "Filter to a specific error code (e.g. ORA-00942)"},
                "object_ref": {"type": "string", "description": "Filter to errors related to a specific object name"},
                "limit":      {"type": "integer", "description": "Max error groups to return (default 50)"},
            },
            "required": ["env"],
        },
    },
    {
        "name": "session_log_chain",
        "description": (
            "Return the full web-tier + app-tier log chain for a specific user (OPRID) in a time window. "
            "Shows what pages/components they accessed in the web layer AND what the app server logged "
            "for them simultaneously — correlated by OPRID and timestamp. "
            "Use this to reconstruct exactly what a user was doing: "
            "'What was GUACUSER doing between 9am and 10am?', "
            "'Show me the full session trace for JNORRIS on Tuesday', "
            "'Walk me through what happened during the GUACUSER error'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "oprid": {"type": "string", "description": "User OPRID to trace"},
                "start": {"type": "string", "description": "ISO datetime start of the window"},
                "end":   {"type": "string", "description": "ISO datetime end of the window"},
            },
            "required": ["oprid"],
        },
    },
    {
        "name": "sqr_program",
        "description": (
            "Look up a PeopleSoft SQR batch report or SQC library file. "
            "Returns the program's metadata (description, release, revision), the database tables it reads and writes, "
            "the SQC include files it depends on, and (when indexed) its full source code — "
            "use the source to explain, summarize, or assess modernization for the program when asked. "
            "Use this for questions about what a batch report does, which tables it touches, "
            "which programs include a given SQC library, or impact analysis on SQR programs. "
            "Examples: 'What does AMAE1100.SQR do?', 'Explain PAYCHECK.SQR in plain English', "
            "'What tables does PAYCHECK.SQR write to?', 'Which SQR programs include SETENV.SQC?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "SQR/SQC filename (e.g. 'AMAE1100.SQR', 'SETENV.SQC'). "
                                   "Can also be a partial name to search.",
                },
                "lookup_type": {
                    "type": "string",
                    "enum": ["program", "table_users", "sqc_users", "search"],
                    "description": "program=look up a specific file; table_users=which SQRs use this table; "
                                   "sqc_users=which SQRs include this SQC; search=keyword search across programs.",
                },
                "query": {
                    "type": "string",
                    "description": "Search term (used with lookup_type=search or table_users or sqc_users)",
                },
            },
            "required": ["lookup_type"],
        },
    },
    {
        "name": "cobol_program",
        "description": (
            "Look up a PeopleSoft COBOL program or copybook file. "
            "Returns the program's metadata (description, compiled status), the database tables it reads and writes, "
            "the COPY dependencies it pulls in, and (when indexed) its full source code — "
            "use the source to explain, summarize, or assess modernization for the program when asked. "
            "Use this for questions about what a COBOL program does, which tables it touches, "
            "which programs COPY a given copybook, or impact analysis on COBOL programs. "
            "Examples: 'What does PSPPMTAX.CBL do?', 'Explain this COBOL program in plain English', "
            "'What tables does it write to?', 'Which programs COPY PTCALOGM?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "COBOL filename (e.g. 'PSPPMTAX.CBL'). Can also be a partial name to search.",
                },
                "lookup_type": {
                    "type": "string",
                    "enum": ["program", "table_users", "copy_deps", "search"],
                    "description": "program=look up a specific file; table_users=which programs use this table; "
                                   "copy_deps=forward+reverse COPY dependency closure for this file; "
                                   "search=keyword search across programs.",
                },
                "query": {
                    "type": "string",
                    "description": "Search term (used with lookup_type=search or table_users)",
                },
            },
            "required": ["lookup_type"],
        },
    },
    {
        "name": "component_events",
        "description": (
            "Return the PeopleCode event flow for a PeopleSoft component. "
            "Shows all PeopleCode events defined for the component, grouped by processing phase "
            "(Search Phase → Component Build → User Interaction → Save Phase), "
            "along with which record and field each event fires on. "
            "Use this to understand the processing sequence, debug event-driven behavior, "
            "or identify where business logic runs. "
            "Examples: 'What PeopleCode events fire on JOB_DATA?', "
            "'When does RowInit run for the job data component?', "
            "'What save-phase logic exists on HR_JOBDATA_ADD_FL?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "description": "PeopleSoft environment (e.g. HCM)"},
                "component": {"type": "string", "description": "Component name (e.g. JOB_DATA, HR_JOBDATA_ADD_FL)"},
            },
            "required": ["env", "component"],
        },
    },
    {
        "name": "peoplecode_sequence",
        "description": (
            "Return the CANONICAL ORDERED processing sequence for a PeopleSoft component, "
            "record, or page — i.e. what fires before/after what, not just which events exist. "
            "For components/records, slots real PeopleCode into the canonical phase order "
            "(Search -> Build -> Interaction -> Save for components; Build -> Interaction -> Save "
            "for records, which have no component-only phases) and marks each slot empty/"
            "delivered/custom. For pages, returns the flat list of Page Activate PeopleCode "
            "(no phase ordering applies at the page level). "
            "Use this specifically for ORDERING questions — 'what fires before X', 'what's the "
            "first/last thing that runs', 'is Y in the save phase or the build phase' — "
            "component_events is better for a flat listing without ordering context. "
            "Examples: 'What fires before Save on JOB_DATA?', 'Is RowInit part of the Build phase "
            "or Interaction phase?', 'What Record Field PeopleCode does JOB have, in order?', "
            "'What Page Activate PeopleCode exists on JOB_DATA_1?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "description": "PeopleSoft environment (e.g. HCM)"},
                "target_type": {
                    "type": "string",
                    "enum": ["component", "record", "page"],
                    "description": "component=component-scoped canonical sequence; "
                                   "record=record-owned Field PeopleCode canonical sequence; "
                                   "page=flat list of Page-owned (Page Activate) PeopleCode, no ordering.",
                },
                "name": {"type": "string", "description": "Component, record, or page name"},
            },
            "required": ["env", "target_type", "name"],
        },
    },
    {
        "name": "execute_sql",
        "description": (
            "Execute a read-only ad-hoc SELECT against a PeopleSoft Oracle environment, when "
            "the existing structured tools (search_objects, record_usage, etc.) aren't enough to "
            "confirm a hypothesis — e.g. checking whether a specific error is caused by a bad or "
            "missing DATA row (out-of-range value, orphaned foreign key, unexpected NULL) rather "
            "than a program/code defect. Only SELECT/WITH statements are allowed; anything else "
            "(INSERT/UPDATE/DELETE/DDL/PL-SQL/DBMS_*/UTL_*) is rejected before it ever reaches the "
            "database — this is the same validation the human-facing SQL Workspace uses. "
            "IMPORTANT: sensitive columns (EMPLID, NAME, EMAIL_ADDR, SSN, etc.) are automatically "
            "replaced with masked tokens like 'EMP_9a41c2f0' before you see them — you will NEVER "
            "see real employee names, IDs, emails, or other PII. The masking is deterministic: the "
            "same real value always produces the same token everywhere, so you CAN still correlate "
            "the same person/entity across multiple tables and queries using these tokens — you "
            "just can't see who they really are. When reporting a finding, reference the masked "
            "token (e.g. 'row EMP_9a41c2f0 in PS_JOB has a NULL DEPTID') — a human operator can "
            "decode that specific token back to the real record on their end. "
            "Examples: 'SELECT COUNT(*) FROM PS_JOB WHERE EMPLID=... AND DEPTID IS NULL', "
            "'SELECT EMPLID, EFFDT, HR_STATUS FROM PS_JOB WHERE EMPLID IN (...) ORDER BY EFFDT'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "env": {"type": "string", "description": "PeopleSoft environment (e.g. HCM)"},
                "sql": {"type": "string", "description": "A single read-only SELECT or WITH statement (no semicolons, no DML/DDL)"},
                "max_rows": {"type": "integer", "description": "Max rows to return (default 50, max 200)"},
            },
            "required": ["env", "sql"],
        },
    },
]

# Tool name → schema lookup
TOOL_BY_NAME = {t["name"]: t for t in TOOLS}


# ── Tool dispatch ─────────────────────────────────────────────────────────────

def dispatch(name: str, inputs: dict) -> str:
    """
    Execute a tool call by name with the given inputs.
    Returns a JSON string suitable for passing back to the AI as a tool result.
    """
    try:
        result = _HANDLERS[name](**inputs)
        return json.dumps(result, default=str)
    except KeyError:
        return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as exc:
        return json.dumps({"error": str(exc), "tool": name})


def _search_objects(env: str, query: str, type: str = None) -> dict:
    from connectors import ptmetadata as pm
    results = pm.global_search(env.upper(), query, limit=20)
    if type:
        results = [r for r in results if r.get("type") == type]
    return {"results": results[:20], "count": len(results)}


def _peoplecode_search(env: str, query: str, limit: int = 20) -> dict:
    limit = min(int(limit), 100)
    raw = peoplecode.source_search(env.upper(), query, limit=limit)
    # source_search returns {items: [...], warnings: [...]}
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    trimmed = []
    for r in items:
        if not isinstance(r, dict):
            continue
        src = r.get("pctext") or r.get("source") or ""
        entry = {k: v for k, v in r.items() if k not in ("pctext", "source")}
        idx = src.lower().find(query.lower())
        start = max(0, idx - 100) if idx >= 0 else 0
        entry["snippet"] = src[start:start + 300]
        trimmed.append(entry)
    warnings = raw.get("warnings", []) if isinstance(raw, dict) else []
    return {"results": trimmed, "count": len(trimmed), "warnings": warnings}


def _graph_dependencies(env: str, node_id: str, depth: int = 2) -> dict:
    depth = min(int(depth), 4)
    result = graphdb.dependency_tree(env.upper(), node_id, reverse=False, depth=depth)
    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    # Summarise by type rather than returning raw node list
    by_type: dict = {}
    for n in nodes:
        if n.get("id") == node_id:
            continue
        t = n.get("type", "unknown")
        by_type.setdefault(t, []).append(n.get("name") or n.get("id"))
    return {"node_id": node_id, "dependency_summary": by_type, "total_nodes": len(nodes), "total_edges": len(edges)}


def _graph_impact(env: str, node_id: str, depth: int = 2) -> dict:
    depth = min(int(depth), 4)
    result = graphdb.dependency_tree(env.upper(), node_id, reverse=True, depth=depth)
    nodes = result.get("nodes", [])
    by_type: dict = {}
    for n in nodes:
        if n.get("id") == node_id:
            continue
        t = n.get("type", "unknown")
        by_type.setdefault(t, []).append(n.get("name") or n.get("id"))
    return {"node_id": node_id, "impact_summary": by_type, "total_affected": len(nodes)}


def _who_has_access(env: str, component: str) -> dict:
    from connectors import psdb as db
    env = env.upper()
    component = component.upper()
    if not ptmetadata.has_table(env, "PSAUTHITEM"):
        return {"error": "PSAUTHITEM not accessible", "env": env}

    # Get all permission list grants for this component (uses BARITEMNAME — version-safe)
    page_rows = db.component_page_grants(env, component, limit=500)
    if not page_rows:
        return {"component": component, "access_grants": [], "note": "No grants found — check component name"}

    # Aggregate by CLASSID (permission list)
    from collections import Counter
    classid_counts: Counter = Counter()
    classid_actions: dict = {}
    for r in page_rows:
        cid = (r.get("classid") or "").strip()
        if cid:
            classid_counts[cid] += 1
            classid_actions[cid] = r.get("actions_label") or r.get("authorizedactions") or ""

    # Enrich with operator counts via PSROLEUSER
    classids = list(classid_counts.keys())[:50]
    op_counts = {}
    if classids and ptmetadata.has_table(env, "PSROLEUSER"):
        placeholders = ",".join(f":c{i}" for i in range(len(classids)))
        bind = {f"c{i}": v for i, v in enumerate(classids)}
        try:
            role_rows = db.query(env, f"""
                SELECT r.ROLENAME, COUNT(DISTINCT r.ROLEUSER) AS op_count
                  FROM SYSADM.PSROLEUSER r
                 WHERE r.ROLENAME IN ({placeholders})
                 GROUP BY r.ROLENAME
            """, bind)
            op_counts = {r.get("rolename", ""): r.get("op_count", 0) for r in role_rows}
        except Exception:
            pass

    grants = sorted([
        {
            "classid":        cid,
            "page_count":     classid_counts[cid],
            "actions":        classid_actions.get(cid, ""),
            "operator_count": op_counts.get(cid, 0),
        }
        for cid in classids
    ], key=lambda x: -x["operator_count"])

    return {"component": component, "access_grants": grants}


def _ae_steps(env: str, ae_name: str) -> dict:
    from connectors import ae as ae_conn
    result = ae_conn.ae_steps(env.upper(), ae_name.upper())
    # Keep it compact — step key + action type + first 200 chars of SQL
    steps = []
    for s in (result or []):
        entry = {
            "section": s.get("ae_section"),
            "step":    s.get("ae_step"),
            "type":    s.get("ae_action") or s.get("action_type"),
        }
        sql = s.get("sql_text") or s.get("stmt") or ""
        if sql:
            entry["sql_preview"] = sql[:200]
        steps.append(entry)
    return {"ae_name": ae_name.upper(), "steps": steps, "count": len(steps)}


def _sql_lookup(env: str, sqlid: str) -> dict:
    from connectors import psdb as db
    if not ptmetadata.has_table(env.upper(), "PSSQLTEXTDEFN"):
        return {"error": "PSSQLTEXTDEFN not accessible"}
    rows = db.query(env.upper(), """
        SELECT SEQNUM, SQLTEXT
          FROM SYSADM.PSSQLTEXTDEFN
         WHERE SQLID = :sid
         ORDER BY SEQNUM
    """, {"sid": sqlid.upper()})
    sql_text = "".join(r.get("sqltext", "") for r in rows)
    if not sql_text:
        return {"error": f"SQL definition not found: {sqlid}"}
    return {"sqlid": sqlid.upper(), "sql_text": sql_text}


def _active_sessions(env: str, hours: int = 8, active_minutes: int = 30, limit: int = 50) -> dict:
    from connectors import psdb as db
    return db.active_sessions(env.upper(), hours=hours, active_minutes=active_minutes, limit=limit)


def _record_usage(env: str, record: str) -> dict:
    from connectors import psdb as db
    return db.record_usage(env.upper(), record.upper())


def _log_search(env: str, tier: str = "both", oprid: str = None,
                component: str = None, errors_only: bool = False,
                start: str = None, end: str = None, limit: int = 100) -> dict:
    from connectors import logdb
    logdb.init_db()
    result: dict = {"env": env, "tier": tier}
    if tier in ("web", "both"):
        result["web"] = logdb.query_web(
            env=env, oprid=oprid, component=component,
            errors_only=errors_only, start=start, end=end, limit=limit
        )
    if tier in ("app", "both"):
        result["app"] = logdb.query_app(
            env=env, oprid=oprid, errors_only=errors_only,
            start=start, end=end, limit=limit
        )
    if not result.get("web") and not result.get("app"):
        result["note"] = "No log entries found. Ensure log sources are configured and enabled in config.json."
    return result


def _log_errors(env: str, error_code: str = None, object_ref: str = None,
                limit: int = 50) -> dict:
    from connectors import logdb
    from connectors.logdb import _conn
    logdb.init_db()
    groups = logdb.error_summary(env=env, limit=limit)
    if error_code:
        groups = [g for g in groups if (g.get("error_code") or "") == error_code]
    if object_ref:
        groups = [g for g in groups if (g.get("object_ref") or "").upper() == object_ref.upper()]
    if not groups:
        return {
            "env": env,
            "groups": [],
            "note": "No errors found. Ensure log sources are configured and ingestion is running.",
        }
    # Enrich each group with up to 3 sample error messages so the AI can explain what's happening
    c = _conn()
    for g in groups[:30]:
        ecode = g.get("error_code")
        oref  = g.get("object_ref")
        clauses, params = ["env=?"], [env]
        if ecode:
            clauses.append("error_code=?"); params.append(ecode)
        else:
            clauses.append("error_code IS NULL")
        if oref:
            clauses.append("object_ref=?"); params.append(oref)
        else:
            clauses.append("object_ref IS NULL")
        rows = c.execute(
            f"SELECT ts, oprid, source_name, level, message FROM log_errors "
            f"WHERE {' AND '.join(clauses)} ORDER BY ts DESC LIMIT 3",
            params
        ).fetchall()
        g["sample_messages"] = [dict(r) for r in rows]
    return {"env": env, "groups": groups, "count": len(groups)}


def _session_log_chain(oprid: str, start: str = None, end: str = None) -> dict:
    from connectors import logdb
    from datetime import datetime, timedelta
    logdb.init_db()
    if not start:
        start = (datetime.utcnow() - timedelta(hours=8)).isoformat(timespec="seconds")
    if not end:
        end = datetime.utcnow().isoformat(timespec="seconds")
    chain = logdb.session_chain(oprid.upper(), start, end)
    if not chain["web"] and not chain["app"]:
        chain["note"] = "No log entries for this OPRID in the given window. Ensure log sources are configured."
    return chain


def _environment_health(env: str) -> dict:
    """Live health check: DB connectivity, sessions, IB dispatcher, error spike, process queue."""
    from connectors import ib as ib_conn, logdb
    env = env.upper()
    result: dict = {"env": env, "checks": []}

    def check(name, status, detail=""):
        result["checks"].append({"name": name, "status": status, "detail": detail})

    # 1. Oracle DB connectivity
    try:
        rows = psdb.query(env, "SELECT 1 FROM DUAL")
        check("oracle_db", "UP", "SELECT 1 FROM DUAL succeeded")
    except Exception as exc:
        check("oracle_db", "DOWN", f"DB connection failed: {exc}")
        result["verdict"] = "ENVIRONMENT OFFLINE — Oracle DB unreachable"
        result["recommendation"] = "The Oracle database is not responding. Check that the DB listener and instance are running before diagnosing further."
        return result

    # 2. Active user sessions (last 30 min)
    try:
        from connectors import tracing
        sess = tracing.recent_active_operators(env, limit=100)
        active = sess.get("items", [])
        check("user_sessions", "OK", f"{len(active)} user(s) active in last 30 min")
        result["active_users"] = [u.get("oprid") for u in active[:10]]
    except Exception as exc:
        check("user_sessions", "WARN", str(exc))

    # 3. IB domain dispatcher heartbeat
    try:
        dom = ib_conn.domain_status(env)
        items = dom.get("items", [])
        if not items:
            check("ib_dispatcher", "UNKNOWN", "No rows in PSAPMSGDOMSTAT — dispatcher may never have started")
        else:
            statuses = [r.get("domain_status", "") for r in items]
            all_running = all(str(s).strip() in ("1", "A", "Running", "RUNNING") for s in statuses)
            check("ib_dispatcher",
                  "UP" if all_running else "DEGRADED",
                  f"{len(items)} domain(s): {', '.join(str(s) for s in statuses)}")
        result["ib_domains"] = items[:5]
    except Exception as exc:
        check("ib_dispatcher", "ERROR", str(exc))

    # 4. IB transaction backlog (failed/cancelled)
    try:
        if ptmetadata.has_table(env, "PSAPMSGPUBHDR"):
            rows = psdb.query(env, """
                SELECT PUBSTATUS, COUNT(*) AS CNT
                  FROM SYSADM.PSAPMSGPUBHDR
                 WHERE CREATEDTTM > SYSDATE - 1
                 GROUP BY PUBSTATUS ORDER BY PUBSTATUS
            """)
            status_map = {str(r.get("pubstatus")): int(r.get("cnt", 0)) for r in rows}
            cancelled = status_map.get("3", 0) + status_map.get("6", 0)
            failed    = status_map.get("4", 0)
            pending   = status_map.get("1", 0)
            check("ib_transactions",
                  "ERROR" if (failed + cancelled) > 50 else "WARN" if (failed + cancelled) > 5 else "OK",
                  f"Last 24h: {pending} pending, {failed} failed, {cancelled} cancelled")
            result["ib_txn_summary"] = status_map
    except Exception as exc:
        check("ib_transactions", "WARN", str(exc))

    # 5. Process scheduler heartbeat
    try:
        if ptmetadata.has_table(env, "PSPRCSRQST"):
            rows = psdb.query(env, """
                SELECT RUNSTATUS, COUNT(*) AS CNT
                  FROM SYSADM.PSPRCSRQST
                 WHERE LASTUPDDTTM > SYSDATE - 1/24
                 GROUP BY RUNSTATUS ORDER BY RUNSTATUS
            """)
            status_map = {str(r.get("runstatus")): int(r.get("cnt", 0)) for r in rows}
            running = status_map.get("7", 0)
            errors  = status_map.get("3", 0)
            check("process_scheduler",
                  "OK" if running >= 0 else "WARN",
                  f"Last hour: {running} running, {errors} error(s)")
    except Exception as exc:
        check("process_scheduler", "WARN", str(exc))

    # 6. Log error spike (last hour vs 24h baseline)
    try:
        logdb.init_db()
        from connectors.logdb import _conn
        c = _conn()
        recent = c.execute(
            "SELECT count(*) FROM log_errors WHERE env=? AND ts > datetime('now','-1 hour')", (env,)
        ).fetchone()[0]
        daily = c.execute(
            "SELECT count(*) FROM log_errors WHERE env=? AND ts > datetime('now','-1 day')", (env,)
        ).fetchone()[0]
        hourly_rate = daily / 24.0 if daily else 0
        spike = recent > max(hourly_rate * 3, 5)
        check("log_error_rate",
              "SPIKE" if spike else "OK",
              f"Last hour: {recent} errors (24h avg/hr: {hourly_rate:.1f})")
        result["log_error_recent"] = recent
    except Exception as exc:
        check("log_error_rate", "UNKNOWN", str(exc))

    # Overall verdict
    statuses = [c["status"] for c in result["checks"]]
    if "DOWN" in statuses:
        result["verdict"] = "ENVIRONMENT OFFLINE — critical component down"
    elif "ERROR" in statuses or "SPIKE" in statuses:
        result["verdict"] = "ENVIRONMENT DEGRADED — errors detected"
    elif "WARN" in statuses or "DEGRADED" in statuses:
        result["verdict"] = "ENVIRONMENT UNHEALTHY — warnings present"
    else:
        result["verdict"] = "ENVIRONMENT HEALTHY"

    return result


def _ib_diagnostics(env: str, node_name: str = None) -> dict:
    """Deep IB diagnostics: nodes, dispatcher, recent failed transactions."""
    from connectors import ib as ib_conn
    env = env.upper()
    result: dict = {"env": env}

    # Node definitions
    node_q = node_name or ""
    node_data = ib_conn.nodes(env, q=node_q, limit=50)
    nodes = node_data.get("items", [])

    if node_name:
        # Include the specific node's full config
        node_detail = ib_conn.node(env, node_name.upper())
        result["node_detail"] = node_detail.get("item")

    # Summarise node status
    result["nodes"] = [
        {
            "name":       r.get("msgnodename"),
            "active":     r.get("active_label"),
            "type":       r.get("node_type_label"),
            "local":      r.get("is_local"),
            "default":    r.get("is_default"),
            "target_url": r.get("ib_tgtlocation"),
            "toolsrel":   r.get("toolsrel"),
        }
        for r in nodes
    ]

    # IB domain dispatcher
    dom = ib_conn.domain_status(env)
    result["domains"] = dom.get("items", [])

    # Recent failed/cancelled transactions (last 24h)
    if ptmetadata.has_table(env, "PSAPMSGPUBHDR"):
        try:
            cols = psdb.select_existing_columns(
                env, "PSAPMSGPUBHDR",
                ["IBTRANSACTIONID", "IBOPERATIONNAME", "QUEUENAME", "PUBNODE",
                 "SUBNODE", "PUBSTATUS", "CREATEDTTM", "ERRORSTRING"],
                required=["IBTRANSACTIONID"],
            )
            where = "WHERE PUBSTATUS IN (3,4,6) AND CREATEDTTM > SYSDATE - 1"
            if node_name:
                where += f" AND (upper(PUBNODE) = '{node_name.upper()}' OR upper(SUBNODE) = '{node_name.upper()}')"
            rows = psdb.query(env, f"""
                SELECT {', '.join(cols)} FROM SYSADM.PSAPMSGPUBHDR
                {where}
                ORDER BY CREATEDTTM DESC FETCH FIRST 20 ROWS ONLY
            """)
            result["failed_transactions"] = [
                {
                    "id":        r.get("ibtransactionid"),
                    "operation": r.get("iboperationname"),
                    "queue":     r.get("queuename"),
                    "pub_node":  r.get("pubnode"),
                    "sub_node":  r.get("subnode"),
                    "status":    r.get("pubstatus"),
                    "created":   str(r.get("createdttm") or ""),
                    "error":     (r.get("errorstring") or "")[:200],
                }
                for r in rows
            ]
        except Exception as exc:
            result["failed_transactions_error"] = str(exc)

        # Status summary
        try:
            summary_rows = psdb.query(env, """
                SELECT PUBSTATUS, COUNT(*) AS CNT
                  FROM SYSADM.PSAPMSGPUBHDR
                 WHERE CREATEDTTM > SYSDATE - 1
                 GROUP BY PUBSTATUS ORDER BY CNT DESC
            """)
            result["txn_status_summary_24h"] = {
                str(r.get("pubstatus")): int(r.get("cnt", 0)) for r in summary_rows
            }
        except Exception:
            pass

    return result


def _process_scheduler_health(env: str, hours: int = 24) -> dict:
    """Check process scheduler: status counts, recent failures, server heartbeat."""
    env = env.upper()
    hours = min(int(hours), 168)
    result: dict = {"env": env, "hours_back": hours}

    if not ptmetadata.has_table(env, "PSPRCSRQST"):
        return {"env": env, "error": "PSPRCSRQST not accessible"}

    # Status breakdown
    try:
        rows = psdb.query(env, f"""
            SELECT RUNSTATUS, COUNT(*) AS CNT
              FROM SYSADM.PSPRCSRQST
             WHERE LASTUPDDTTM > SYSDATE - {hours}/24
             GROUP BY RUNSTATUS ORDER BY CNT DESC
        """)
        RUNSTATUS = {
            "1": "Pending", "2": "Initiated", "3": "Error", "5": "Cancelled",
            "6": "Hold", "7": "Queued", "8": "Processing", "9": "Success",
            "10": "Invalid", "11": "Posted", "12": "Not Posted",
            "14": "Content", "17": "Blocked",
        }
        result["status_counts"] = {
            RUNSTATUS.get(str(r.get("runstatus")), str(r.get("runstatus"))): int(r.get("cnt", 0))
            for r in rows
        }
    except Exception as exc:
        result["status_counts_error"] = str(exc)

    # Recent failures
    try:
        fail_cols = psdb.select_existing_columns(
            env, "PSPRCSRQST",
            ["PRCSINSTANCE", "PRCSTYPE", "PRCSNAME", "OPRID", "RUNCNTLID",
             "RUNSTATUS", "BEGINDTTM", "ENDDTTM", "SERVERBATCH", "MSGSETBASES", "MSGNUM"],
            required=["PRCSINSTANCE"],
        )
        fail_rows = psdb.query(env, f"""
            SELECT {', '.join(fail_cols)} FROM SYSADM.PSPRCSRQST
             WHERE RUNSTATUS IN (3, 5, 10)
               AND LASTUPDDTTM > SYSDATE - {hours}/24
             ORDER BY LASTUPDDTTM DESC FETCH FIRST 10 ROWS ONLY
        """)
        result["recent_failures"] = [dict(r) for r in fail_rows]
    except Exception as exc:
        result["recent_failures_error"] = str(exc)

    # Server heartbeat — when did each scheduler server last respond
    try:
        if ptmetadata.has_table(env, "PSPRCSSRVCL"):
            srv_rows = psdb.query(env, """
                SELECT SERVERNAME, SERVERTYPE,
                       MAX(LASTUPDDTTM) AS LAST_HEARTBEAT,
                       MAX(NUMSERVPROC) AS WORKERS
                  FROM SYSADM.PSPRCSSRVCL
                 GROUP BY SERVERNAME, SERVERTYPE
                 ORDER BY LAST_HEARTBEAT DESC
            """)
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            servers = []
            for r in srv_rows:
                hb = r.get("last_heartbeat")
                minutes_ago = None
                status = "UNKNOWN"
                if hb:
                    try:
                        delta = now - hb if hasattr(hb, 'replace') else None
                        if delta:
                            minutes_ago = int(delta.total_seconds() / 60)
                            status = "ONLINE" if minutes_ago < 10 else "STALE" if minutes_ago < 60 else "OFFLINE"
                    except Exception:
                        pass
                servers.append({
                    "name":        r.get("servername"),
                    "type":        r.get("servertype"),
                    "last_seen":   str(hb or ""),
                    "minutes_ago": minutes_ago,
                    "status":      status,
                    "workers":     r.get("workers"),
                })
            result["scheduler_servers"] = servers
            if servers and all(s["status"] == "OFFLINE" for s in servers):
                result["verdict"] = "PROCESS SCHEDULER OFFLINE — all servers stopped responding"
    except Exception as exc:
        result["scheduler_servers_error"] = str(exc)

    return result


def _envcompare_summary(env1: str, env2: str) -> dict:
    result = envcompare.summary(env1.upper(), env2.upper())
    return result


def _project_impact(env: str, project: str) -> dict:
    result = impact.project_impact(env.upper(), project.upper())
    # Trim top_impacted_objects list for token efficiency
    if "top_impacted_objects" in result:
        result["top_impacted_objects"] = result["top_impacted_objects"][:10]
    return result


_SOURCE_TRUNCATE_CHARS = 12000


def _truncate_source(detail: dict) -> dict:
    src = detail.get("source_text")
    if src and len(src) > _SOURCE_TRUNCATE_CHARS:
        detail["source_text"] = src[:_SOURCE_TRUNCATE_CHARS]
        detail["source_truncated"] = True
        detail["source_full_length"] = len(src)
    return detail


def _sqr_program(lookup_type: str, filename: str = None, query: str = None) -> dict:
    from connectors import sqrdb
    sqrdb.init_db()
    if lookup_type == "program":
        name = (filename or "").strip()
        if not name:
            return {"error": "filename required for lookup_type=program"}
        detail = sqrdb.get_program(name)
        if not detail:
            # Try search fallback
            results = sqrdb.search_programs(q=name, per_page=5)
            return {"found": False, "suggestions": results.get("results", [])}
        return {"found": True, "program": _truncate_source(detail)}
    elif lookup_type == "table_users":
        tbl = (filename or query or "").strip().upper()
        if not tbl:
            return {"error": "provide filename or query with table name"}
        return sqrdb.get_programs_for_table(tbl)
    elif lookup_type == "sqc_users":
        sqc = (filename or query or "").strip().lower()
        if not sqc:
            return {"error": "provide filename or query with SQC name"}
        return sqrdb.get_includes_for_sqc(sqc)
    elif lookup_type == "search":
        q = (query or filename or "").strip()
        results = sqrdb.search_programs(q=q, per_page=20)
        return results
    return {"error": f"Unknown lookup_type: {lookup_type}"}


def _cobol_program(lookup_type: str, filename: str = None, query: str = None) -> dict:
    from connectors import cobol_db
    cobol_db.init_db()
    if lookup_type == "program":
        name = (filename or "").strip()
        if not name:
            return {"error": "filename required for lookup_type=program"}
        detail = cobol_db.get_program(name)
        if not detail:
            results = cobol_db.search_programs(q=name, per_page=5)
            return {"found": False, "suggestions": results.get("results", [])}
        return {"found": True, "program": _truncate_source(detail)}
    elif lookup_type == "table_users":
        tbl = (filename or query or "").strip().upper()
        if not tbl:
            return {"error": "provide filename or query with table name"}
        return {"programs": cobol_db.get_programs_for_table(tbl)}
    elif lookup_type == "copy_deps":
        name = (filename or query or "").strip()
        if not name:
            return {"error": "provide filename for lookup_type=copy_deps"}
        return cobol_db.get_copy_deps(name)
    elif lookup_type == "search":
        q = (query or filename or "").strip()
        return cobol_db.search_programs(q=q, per_page=20)
    return {"error": f"Unknown lookup_type: {lookup_type}"}


def _component_events(env: str, component: str) -> dict:
    from connectors import peoplecode
    result = peoplecode.component_events(env.upper(), component.upper())
    events = result.get("events", [])
    summary = {}
    for e in events:
        ph = e.get("phase", "other")
        summary[ph] = summary.get(ph, 0) + 1
    result["phase_summary"] = summary
    result["total"] = len(events)

    # Enrich with canonical ordering so the assistant can reason about
    # execution order (e.g. "what fires before save?"), not just counts.
    try:
        sequence = peoplecode.component_sequence(env.upper(), component.upper())
        result["canonical_sequence"] = [
            {
                "phase": ph["phase"],
                "label": ph["label"],
                "events": [
                    {"name": e["name"], "ordinal": e["ordinal"], "status": e["status"]}
                    for e in ph["events"] if e["status"] != "empty"
                ],
            }
            for ph in sequence.get("phases", [])
        ]
    except Exception:
        pass

    return result


def _peoplecode_sequence(env: str, target_type: str, name: str) -> dict:
    from connectors import peoplecode
    env = env.upper()
    if target_type == "component":
        return peoplecode.component_sequence(env, name.upper())
    elif target_type == "record":
        return peoplecode.record_sequence(env, name.upper())
    elif target_type == "page":
        return peoplecode.page_owned_events(env, name.upper())
    return {"error": f"Unknown target_type: {target_type}"}


def _execute_sql(env: str, sql: str, max_rows: int = 50) -> dict:
    """AI-facing ad-hoc SQL execution — Phase 11 SQL Proxy.

    Reuses connectors.sqlws.execute_query()'s validation/paging/audit path
    unchanged (source="ai" tags the shared audit trail), then masks the
    result through connectors.sqlmask before returning it. This function is
    the ONLY path by which the AI dispatch table can reach live Oracle data
    ad hoc; it never returns unmasked values and has no route to
    sqlmask.reveal() — that stays human-only by construction, not by a
    runtime permission check.
    """
    from connectors import sqlws, sqlmask

    max_rows = max(1, min(int(max_rows or 50), 200))
    result = sqlws.execute_query(
        env.upper(), sql, page=1, page_size=max_rows, max_rows=max_rows, source="ai",
    )
    if result.get("blocked"):
        return {"error": result.get("blocked_reason"), "blocked": True}
    if result.get("status") == "error":
        return {"error": result.get("error") or "Query execution failed", "warnings": result.get("warnings")}
    return sqlmask.mask_result(result)


_HANDLERS = {
    "search_objects":     _search_objects,
    "peoplecode_search":  _peoplecode_search,
    "graph_dependencies": _graph_dependencies,
    "graph_impact":       _graph_impact,
    "who_has_access":     _who_has_access,
    "ae_steps":           _ae_steps,
    "sql_lookup":         _sql_lookup,
    "envcompare_summary": _envcompare_summary,
    "project_impact":     _project_impact,
    "active_sessions":    _active_sessions,
    "record_usage":       _record_usage,
    "log_search":              _log_search,
    "log_errors":              _log_errors,
    "session_log_chain":       _session_log_chain,
    "environment_health":      _environment_health,
    "ib_diagnostics":          _ib_diagnostics,
    "process_scheduler_health": _process_scheduler_health,
    "sqr_program":             _sqr_program,
    "cobol_program":           _cobol_program,
    "component_events":        _component_events,
    "peoplecode_sequence":     _peoplecode_sequence,
    "execute_sql":             _execute_sql,
}
