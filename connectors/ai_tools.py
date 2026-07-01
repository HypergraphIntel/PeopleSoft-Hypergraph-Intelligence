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


def _envcompare_summary(env1: str, env2: str) -> dict:
    result = envcompare.summary(env1.upper(), env2.upper())
    return result


def _project_impact(env: str, project: str) -> dict:
    result = impact.project_impact(env.upper(), project.upper())
    # Trim top_impacted_objects list for token efficiency
    if "top_impacted_objects" in result:
        result["top_impacted_objects"] = result["top_impacted_objects"][:10]
    return result


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
    "log_search":         _log_search,
    "log_errors":         _log_errors,
    "session_log_chain":  _session_log_chain,
}
