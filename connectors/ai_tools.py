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
    results = peoplecode.source_search(env.upper(), query, limit=limit)
    # Trim source snippets so the tool result stays manageable
    trimmed = []
    for r in results:
        entry = {k: v for k, v in r.items() if k != "source"}
        src = r.get("source") or ""
        # Return up to 300 chars around the first match
        idx = src.lower().find(query.lower())
        if idx >= 0:
            start = max(0, idx - 100)
            entry["snippet"] = src[start:start + 300]
        else:
            entry["snippet"] = src[:300]
        trimmed.append(entry)
    return {"results": trimmed, "count": len(trimmed)}


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
    if not ptmetadata.has_table(env.upper(), "PSAUTHITEM"):
        return {"error": "PSAUTHITEM not accessible", "env": env}
    rows = db.query(env.upper(), """
        SELECT a.CLASSID, a.AUTHORIZATIONS,
               COUNT(DISTINCT r.ROLEUSER) AS operator_count
          FROM SYSADM.PSAUTHITEM a
          LEFT JOIN SYSADM.PSROLEUSER r ON r.ROLENAME = a.CLASSID
         WHERE UPPER(a.PNLGRPNAME) = UPPER(:comp)
           AND a.PORTAL_OBJNAME = ' '
         GROUP BY a.CLASSID, a.AUTHORIZATIONS
         ORDER BY operator_count DESC
    """, {"comp": component})
    return {"component": component, "access_grants": rows[:50]}


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
}
