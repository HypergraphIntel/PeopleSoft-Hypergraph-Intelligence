import time

from connectors import psdb

CACHE_TTL_SECONDS = 300
_CACHE = {}


def _now():
    return time.time()


def warning(code, message, severity="warning", detail=None):
    return {
        "code": code,
        "message": message,
        "severity": severity,
        "detail": detail,
    }


def cache_get(key):
    item = _CACHE.get(key)

    if not item:
        return None

    if item["expires_at"] < _now():
        _CACHE.pop(key, None)
        return None

    return item["value"]


def cache_set(key, value, ttl=CACHE_TTL_SECONDS):
    _CACHE[key] = {
        "value": value,
        "created_at": _now(),
        "expires_at": _now() + ttl,
    }
    return value


def cached(key, loader, ttl=CACHE_TTL_SECONDS):
    value = cache_get(key)

    if value is not None:
        return value

    return cache_set(key, loader(), ttl)


def cache_status():
    now = _now()
    return {
        "ttl_seconds": CACHE_TTL_SECONDS,
        "entries": [
            {
                "key": key,
                "age_seconds": round(now - item["created_at"], 2),
                "expires_in_seconds": max(0, round(item["expires_at"] - now, 2)),
            }
            for key, item in sorted(_CACHE.items())
        ],
    }


def clear_cache():
    _CACHE.clear()
    return cache_status()


def safe_query(env, sql, params=None):
    try:
        return psdb.query(env, sql, params or {}), None
    except Exception as exc:
        return [], warning("metadata_query_failed", str(exc), detail={"sql": sql})


def oracle_version(env):
    rows, err = safe_query(env, """
        select banner_full as version
          from v$version
         fetch first 1 rows only
    """)

    if rows:
        return rows[0]["version"], None

    rows, fallback_err = safe_query(env, """
        select product || ' ' || version as version
          from product_component_version
         where rownum = 1
    """)

    if rows:
        return rows[0]["version"], err

    return None, fallback_err or err


def peopletools_version(env):
    probes = [
        ("PSSTATUS", "TOOLSREL"),
        ("PSOPTIONS", "TOOLSREL"),
    ]

    for table_name, column_name in probes:
        rows, err = safe_query(env, f"""
            select {column_name} as version
              from sysadm.{table_name}
             fetch first 1 rows only
        """)

        if rows:
            return rows[0]["version"], None

    return None, warning(
        "peopletools_version_unavailable",
        "Unable to read PeopleTools version from known metadata tables.",
    )


def current_schema(env):
    rows, err = safe_query(env, """
        select
            user as connected_user,
            sys_context('USERENV','CURRENT_SCHEMA') as current_schema,
            sys_context('USERENV','DB_NAME') as db_name,
            sys_context('USERENV','CON_NAME') as con_name
        from dual
    """)

    return (rows[0] if rows else {}), err


def available_owners(env):
    return cached((env.upper(), "owners"), lambda: _available_owners(env))


def _available_owners(env):
    rows, err = safe_query(env, """
        select distinct owner
          from all_objects
         where owner is not null
         order by owner
    """)

    return {
        "owners": [row["owner"] for row in rows],
        "warnings": [err] if err else [],
    }


def accessible_objects(env, object_type=None):
    cache_key = (env.upper(), "objects", object_type or "ALL")
    return cached(cache_key, lambda: _accessible_objects(env, object_type))


def _accessible_objects(env, object_type=None):
    params = {}
    predicate = ""

    if object_type:
        predicate = "and object_type = upper(:object_type)"
        params["object_type"] = object_type

    rows, err = safe_query(env, f"""
        select owner, object_name, object_type
          from all_objects
         where owner = 'SYSADM'
           {predicate}
         order by object_type, object_name
    """, params)

    return {
        "objects": rows,
        "warnings": [err] if err else [],
    }


def table_columns(env, table_name, owner="SYSADM"):
    cache_key = (env.upper(), "columns", owner.upper(), table_name.upper())
    return cached(cache_key, lambda: _table_columns(env, table_name, owner))


def _table_columns(env, table_name, owner="SYSADM"):
    rows, err = safe_query(env, """
        select column_name
          from all_tab_columns
         where owner = upper(:owner)
           and table_name = upper(:table_name)
         order by column_id
    """, {"owner": owner, "table_name": table_name})

    return {
        "columns": [row["column_name"] for row in rows],
        "warnings": [err] if err else [],
    }


def has_table(env, table_name, owner="SYSADM"):
    rows, err = safe_query(env, """
        select object_name
          from all_objects
         where owner = upper(:owner)
           and object_name = upper(:table_name)
           and object_type in ('TABLE', 'VIEW', 'SYNONYM')
         fetch first 1 rows only
    """, {"owner": owner, "table_name": table_name})

    if rows:
        return True

    _, probe_err = safe_query(env, f"""
        select 1 as ok
          from {owner}.{psdb.safe_identifier(table_name)}
         where 1 = 0
    """)

    return probe_err is None


def has_view(env, view_name, owner="SYSADM"):
    rows, _ = safe_query(env, """
        select object_name
          from all_objects
         where owner = upper(:owner)
           and object_name = upper(:view_name)
           and object_type = 'VIEW'
         fetch first 1 rows only
    """, {"owner": owner, "view_name": view_name})
    return bool(rows)


def has_column(env, table_name, column_name, owner="SYSADM"):
    columns = table_columns(env, table_name, owner)["columns"]
    return column_name.upper() in {col.upper() for col in columns}


OBJECT_REGISTRY = {
    "operator": {
        "display_title": "Operator",
        "icon": "user",
        "graph_node_type": "operator",
        "object_page": "/admin/object/operator/{name}",
        "discovery": {"table": "PSOPRDEFN", "name_column": "OPRID"},
        "search": {"table": "PSOPRDEFN", "name_column": "OPRID", "description_columns": ["OPRDEFNDESC"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "ASSIGNED_ROLE", "target_type": "role", "direction": "out", "label": "Roles"},
        ],
    },
    "role": {
        "display_title": "Role",
        "icon": "shield",
        "graph_node_type": "role",
        "object_page": "/admin/object/role/{name}",
        "discovery": {"table": "PSROLEDEFN", "name_column": "ROLENAME"},
        "search": {"table": "PSROLEDEFN", "name_column": "ROLENAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "ASSIGNED_ROLE", "target_type": "operator", "direction": "in", "label": "Operators"},
            {"edge_type": "HAS_PERMLIST", "target_type": "permissionlist", "direction": "out", "label": "Permission Lists"},
        ],
    },
    "permissionlist": {
        "display_title": "Permission List",
        "icon": "key",
        "graph_node_type": "permissionlist",
        "object_page": "/admin/object/permissionlist/{name}",
        "discovery": {"table": "PSCLASSDEFN", "name_column": "CLASSID"},
        "search": {"table": "PSCLASSDEFN", "name_column": "CLASSID", "description_columns": ["DESCR", "CLASSDEFNDESC"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "HAS_PERMLIST", "target_type": "role", "direction": "in", "label": "Roles"},
            {"edge_type": "GRANTS_ACCESS", "target_type": "component", "direction": "out", "label": "Components"},
            {"edge_type": "GRANTS_MENU", "target_type": "menu", "direction": "out", "label": "Menus"},
        ],
    },
    "component": {
        "display_title": "Component",
        "icon": "panel",
        "graph_node_type": "component",
        "object_page": "/admin/object/component/{name}",
        "discovery": {"table": "PSPNLGRPDEFN", "name_column": "PNLGRPNAME"},
        "search": {"table": "PSPNLGRPDEFN", "name_column": "PNLGRPNAME", "description_columns": ["DESCR"], "extra_search_columns": ["SEARCHRECNAME", "ADDSRCHRECNAME"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "HAS_PAGE", "target_type": "page", "direction": "out", "label": "Pages"},
            {"edge_type": "GRANTS_ACCESS", "target_type": "permissionlist", "direction": "in", "label": "Permission Lists"},
            {"edge_type": "LISTED_IN", "target_type": "menu", "direction": "in", "label": "Menus"},
            {"edge_type": "REFERENCED_BY", "target_type": "portal_registry", "direction": "in", "label": "Portal Registry"},
            {"edge_type": "USES", "target_type": "record", "direction": "out", "label": "Records"},
        ],
    },
    "page": {
        "display_title": "Page",
        "icon": "file",
        "graph_node_type": "page",
        "object_page": "/admin/object/page/{name}",
        "discovery": {"table": "PSPNLDEFN", "name_column": "PNLNAME"},
        "search": {"table": "PSPNLDEFN", "name_column": "PNLNAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "HAS_PAGE", "target_type": "component", "direction": "in", "label": "Components"},
            {"edge_type": "CONTAINS", "target_type": "record", "direction": "out", "label": "Records"},
            {"edge_type": "CONTAINS", "target_type": "field", "direction": "out", "label": "Fields"},
        ],
    },
    "record": {
        "display_title": "Record",
        "icon": "table",
        "graph_node_type": "record",
        "object_page": "/admin/object/record/{name}",
        "discovery": {"table": "PSRECDEFN", "name_column": "RECNAME"},
        "search": {"table": "PSRECDEFN", "name_column": "RECNAME", "description_columns": ["RECDESCR"], "extra_search_columns": ["SQLTABLENAME"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "CONTAINS", "target_type": "field", "direction": "out", "label": "Fields"},
            {"edge_type": "CONTAINS", "target_type": "record", "direction": "in", "label": "Parent Records"},
            {"edge_type": "USES", "target_type": "component", "direction": "in", "label": "Components"},
        ],
    },
    "field": {
        "display_title": "Field",
        "icon": "type",
        "graph_node_type": "field",
        "object_page": "/admin/object/field/{name}",
        "discovery": {"table": "PSDBFIELD", "name_column": "FIELDNAME"},
        "search": {"provider": "field", "table": "PSRECFIELD", "name_column": "FIELDNAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "CONTAINS", "target_type": "record", "direction": "in", "label": "Records"},
            {"edge_type": "HAS_PEOPLECODE", "target_type": "peoplecode", "direction": "out", "label": "PeopleCode"},
        ],
    },
    "peoplecode": {
        "display_title": "PeopleCode",
        "icon": "code",
        "graph_node_type": "peoplecode",
        "object_page": "/admin/object/peoplecode/{name}",
        "discovery": {"table": "PSPCMPROG", "name_column": "PROGSEQ"},
        "search": {"provider": "peoplecode", "table": "PSPCMPROG", "name_column": "PROGSEQ", "description_columns": []},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
        "relationships": [
            {"edge_type": "HAS_PEOPLECODE", "target_type": "component", "direction": "in", "label": "Components"},
            {"edge_type": "HAS_PEOPLECODE", "target_type": "record", "direction": "in", "label": "Records"},
            {"edge_type": "HAS_PEOPLECODE", "target_type": "application_engine", "direction": "in", "label": "Application Engines"},
            {"edge_type": "CALLS", "target_type": "application_package", "direction": "out", "label": "App Package Classes"},
        ],
    },
    "peoplecode_event": {
        "display_title": "PeopleCode Event",
        "icon": "zap",
        "graph_node_type": "peoplecode_event",
        "object_page": "/admin/object/peoplecode_event/{name}",
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
    },
    "peoplecode_reference": {
        "display_title": "PeopleCode Reference",
        "icon": "link",
        "graph_node_type": "peoplecode_reference",
        "object_page": "/admin/object/peoplecode_reference/{name}",
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
    },
    "function": {
        "display_title": "Function",
        "icon": "function",
        "graph_node_type": "function",
        "object_page": "/admin/object/function/{name}",
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
    },
    "application_package": {
        "display_title": "Application Package",
        "icon": "package",
        "graph_node_type": "application_package",
        "object_page": "/admin/object/application_package/{name}",
        "discovery": {"table": "PSPACKAGEDEFN", "name_column": "PACKAGEROOT"},
        "search": {"provider": "app_package", "table": "PSPACKAGEDEFN", "name_column": "PACKAGEROOT",
                   "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "application_class": {
        "display_title": "Application Class",
        "icon": "box",
        "graph_node_type": "application_class",
        "object_page": "/admin/object/application_class/{name}",
        "discovery": {"table": "PSAPPCLASSDEFN", "name_column": "APPCLASSID"},
        "search": {"table": "PSAPPCLASSDEFN", "name_column": "APPCLASSID",
                   "description_columns": ["DESCR"],
                   "extra_search_columns": ["PACKAGEROOT", "QUALIFYPATH"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "sql_definition": {
        "display_title": "SQL Definition",
        "icon": "database",
        "graph_node_type": "sql_definition",
        "object_page": "/admin/object/sql_definition/{name}",
        "discovery": {"table": "PSSQLDEFN", "name_column": "SQLID"},
        "search": {"table": "PSSQLDEFN", "name_column": "SQLID", "description_columns": [],
                   "extra_search_columns": ["OBJECTOWNERID"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
}

OBJECT_REGISTRY.setdefault("application_engine", {
    "display_title": "Application Engine",
    "icon": "cpu",
    "graph_node_type": "application_engine",
    "object_page": "/admin/object/application_engine/{name}",
    "discovery": {"table": "PSAEAPPLDEFN", "name_column": "AE_APPLID"},
    "search": {"table": "PSAEAPPLDEFN", "name_column": "AE_APPLID", "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [
        {"edge_type": "HAS_PEOPLECODE", "target_type": "peoplecode", "direction": "out", "label": "PeopleCode"},
        {"edge_type": "USES", "target_type": "record", "direction": "out", "label": "State Records"},
        {"edge_type": "CALLS", "target_type": "sql_definition", "direction": "out", "label": "SQL Definitions"},
    ],
})

OBJECT_REGISTRY.setdefault("ae_section", {
    "display_title": "AE Section",
    "icon": "layers",
    "graph_node_type": "ae_section",
    "object_page": "/admin/object/ae_section/{name}",
    "discovery": {"table": "PSAESECTDEFN", "name_column": "AE_SECTION"},
    "search": None,
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("ae_step", {
    "display_title": "AE Step",
    "icon": "chevron-right",
    "graph_node_type": "ae_step",
    "object_page": "/admin/object/ae_step/{name}",
    "discovery": {"table": "PSAESTEPDEFN", "name_column": "AE_STEP"},
    "search": None,
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("process", {
    "display_title": "Process",
    "icon": "play-circle",
    "graph_node_type": "process",
    "object_page": "/admin/object/process/{name}",
    "discovery": {"table": "PSPROCESSDEFN", "name_column": "PRCSNAME"},
    "search": {"table": "PSPROCESSDEFN", "name_column": "PRCSNAME", "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("service_operation", {
    "display_title": "IB Service Operation",
    "icon": "globe",
    "graph_node_type": "service_operation",
    "object_page": "/admin/object/service_operation/{name}",
    "discovery": {"table": "PSIBRTNGDEFN", "name_column": "IB_OPERATIONNAME"},
    "search": {"provider": "ib_service_operation", "table": "PSIBRTNGDEFN", "name_column": "IB_OPERATIONNAME"},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("queue", {
    "display_title": "IB Queue",
    "icon": "queue",
    "graph_node_type": "queue",
    "object_page": "/admin/object/queue/{name}",
    "discovery": {"table": "PSQUEUEDEFN", "name_column": "QUEUENAME"},
    "search": {"table": "PSQUEUEDEFN", "name_column": "QUEUENAME", "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("node", {
    "display_title": "IB Node",
    "icon": "node",
    "graph_node_type": "node",
    "object_page": "/admin/object/node/{name}",
    "discovery": {"table": "PSMSGNODEDEFN", "name_column": "MSGNODENAME"},
    "search": {"table": "PSMSGNODEDEFN", "name_column": "MSGNODENAME", "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("routing", {
    "display_title": "IB Routing",
    "icon": "routing",
    "graph_node_type": "routing",
    "object_page": "/admin/object/routing/{name}",
    "discovery": {"table": "PSIBRTNGDEFN", "name_column": "ROUTINGDEFNNAME"},
    "search": {"table": "PSIBRTNGDEFN", "name_column": "ROUTINGDEFNNAME", "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("portal_registry", {
    "display_title": "Portal Registry",
    "icon": "sitemap",
    "graph_node_type": "portal_registry",
    "object_page": "/admin/object/portal_registry/{name}",
    "discovery": {"table": "PSPRSMDEFN", "name_column": "PORTAL_OBJNAME"},
    "search": {
        "table": "PSPRSMDEFN",
        "name_column": "PORTAL_OBJNAME",
        "description_columns": ["PORTAL_LABEL", "DESCR254"],
        "extra_search_columns": ["PORTAL_URI_SEG1", "PORTAL_URI_SEG2", "PORTAL_URI_SEG3", "PORTAL_URLTEXT"],
    },
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
})

OBJECT_REGISTRY.setdefault("query", {
    "display_title": "PS Query",
    "icon": "search",
    "graph_node_type": "query",
    "object_page": "/admin/object/query/{name}",
    "discovery": {"table": "PSQRYDEFN", "name_column": "QRYNAME"},
    "search": {"provider": "query", "table": "PSQRYDEFN", "name_column": "QRYNAME",
               "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("tree", {
    "display_title": "Tree",
    "icon": "git-branch",
    "graph_node_type": "tree",
    "object_page": "/admin/object/tree/{name}",
    "discovery": {"table": "PSTREEDEFN", "name_column": "TREE_NAME"},
    "search": {"provider": "tree", "table": "PSTREEDEFN", "name_column": "TREE_NAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["TREE_STRCT_ID", "SETID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [
        {"edge_type": "USES", "target_type": "record", "direction": "out", "label": "Structure Record"},
    ],
})

OBJECT_REGISTRY.setdefault("ci", {
    "display_title": "Component Interface",
    "icon": "plug",
    "graph_node_type": "ci",
    "object_page": "/admin/object/ci/{name}",
    "discovery": {"table": "PSBCDEFN", "name_column": "BCNAME"},
    "search": {"table": "PSBCDEFN", "name_column": "BCNAME",
               "description_columns": ["DESCR", "BCDISPLAYNAME"],
               "extra_search_columns": ["BCPGNAME", "SEARCHRECNAME", "ADDSRCHRECNAME", "OBJECTOWNERID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [
        {"edge_type": "WRAPS", "target_type": "component", "direction": "out", "label": "Component"},
    ],
})

OBJECT_REGISTRY.setdefault("menu", {
    "display_title": "Menu",
    "icon": "menu",
    "graph_node_type": "menu",
    "object_page": "/admin/object/menu/{name}",
    "discovery": {"table": "PSMENUDEFN", "name_column": "MENUNAME"},
    "search": {"table": "PSMENUDEFN", "name_column": "MENUNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["MENUGROUP", "OBJECTOWNERID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [
        {"edge_type": "CONTAINS", "target_type": "component", "direction": "out", "label": "Components"},
    ],
})

OBJECT_REGISTRY.setdefault("message_catalog", {
    "display_title": "Message Catalog",
    "icon": "message-square",
    "graph_node_type": "message_catalog",
    "object_page": "/admin/object/message_catalog/{name}",
    "discovery": {"table": "PSMSGCATDEFN", "name_column": "MESSAGE_SET_NBR"},
    "search": {"provider": "message_catalog", "table": "PSMSGCATDEFN"},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("approval", {
    "display_title": "Approval Framework",
    "icon": "check-square",
    "graph_node_type": "approval",
    "object_page": "/admin/object/approval/{name}",
    "discovery": {"table": "PS_EOAW_TXN", "name_column": "EOAWPRCS_ID"},
    "search": {"table": "PS_EOAW_TXN", "name_column": "EOAWPRCS_ID",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID", "PACKAGEROOT"]},
    "supported_versions": ["8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("xml_publisher_report", {
    "display_title": "XML Publisher Report",
    "icon": "file-text",
    "graph_node_type": "xml_publisher_report",
    "object_page": "/admin/object/xml_publisher_report/{name}",
    "discovery": {"table": "PSXPRPTDEFN", "name_column": "REPORT_DEFN_ID"},
    "search": {"table": "PSXPRPTDEFN", "name_column": "REPORT_DEFN_ID",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID", "DS_ID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("xml_publisher_datasource", {
    "display_title": "XML Publisher Data Source",
    "icon": "database",
    "graph_node_type": "xml_publisher_datasource",
    "object_page": "/admin/object/xml_publisher_datasource/{name}",
    "discovery": {"table": "PSXPDATASRC", "name_column": "DS_ID"},
    "search": {"table": "PSXPDATASRC", "name_column": "DS_ID",
               "description_columns": ["DESCR"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

# ---------------------------------------------------------------------------
# Stub providers — no backing tables confirmed in the live SYSADM schema as
# of 2026-06-30.  has_table() guards in psdb.py and graphdb.py ensure all
# queries gracefully return empty results.  "stub": True lets callers surface
# appropriate "not available" messaging without hard-coding object-type names.
# ---------------------------------------------------------------------------
OBJECT_REGISTRY.setdefault("nav_collection", {
    "display_title": "Navigation Collection",
    "icon": "navigation",
    "graph_node_type": "nav_collection",
    "object_page": "/admin/object/nav_collection/{name}",
    "stub": True,
    "discovery": {"table": "PTNC_COLLECTION", "name_column": "COLL_ID"},
    "search": {"table": "PTNC_COLLECTION", "name_column": "COLL_ID",
               "description_columns": ["COLL_TITLE"],
               "extra_search_columns": ["PORTAL_NAME"]},
    "supported_versions": ["8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("event_mapping", {
    "display_title": "Event Mapping",
    "icon": "zap",
    "graph_node_type": "event_mapping",
    "object_page": "/admin/object/event_mapping/{name}",
    "stub": True,
    "discovery": {"table": "PSEFMAPPINGDEFN", "name_column": "EFMAPPINGID"},
    "search": {"table": "PSEFMAPPINGDEFN", "name_column": "EFMAPPINGID",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("related_content", {
    "display_title": "Related Content",
    "icon": "link",
    "graph_node_type": "related_content",
    "object_page": "/admin/object/related_content/{name}",
    "stub": True,
    "discovery": {"table": "PSRELCONDEFN", "name_column": "RELCONID"},
    "search": {"table": "PSRELCONDEFN", "name_column": "RELCONID",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("search_definition", {
    "display_title": "Search Definition",
    "icon": "search",
    "graph_node_type": "search_definition",
    "object_page": "/admin/object/search_definition/{name}",
    "discovery": {"table": "PSPTSF_SD", "name_column": "PTSF_SOURCE_NAME"},
    "search": {"table": "PSPTSF_SD", "name_column": "PTSF_SOURCE_NAME",
               "description_columns": ["DESCR100"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("search_category", {
    "display_title": "Search Category",
    "icon": "search",
    "graph_node_type": "search_category",
    "object_page": "/admin/object/search_category/{name}",
    "discovery": {"table": "PSPTSF_SRCCAT", "name_column": "PTSF_SRCCAT_NAME"},
    "search": {"table": "PSPTSF_SRCCAT", "name_column": "PTSF_SRCCAT_NAME",
               "description_columns": ["DESCR100"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("drop_zone", {
    "display_title": "Drop Zone",
    "icon": "layout",
    "graph_node_type": "drop_zone",
    "object_page": "/admin/object/drop_zone/{name}",
    "stub": True,
    "discovery": {"table": "PSPTDZDEFN", "name_column": "DZNAME"},
    "search": {"table": "PSPTDZDEFN", "name_column": "DZNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("pivot_grid", {
    "display_title": "PivotGrid",
    "icon": "bar-chart-2",
    "graph_node_type": "pivot_grid",
    "object_page": "/admin/object/pivot_grid/{name}",
    "discovery": {"table": "PSPGCORE", "name_column": "PTPG_PGRIDNAME"},
    "search": {"table": "PSPGCORE", "name_column": "PTPG_PGRIDNAME",
               "description_columns": ["PTPG_PGRIDTITLE"],
               "extra_search_columns": ["OBJECTOWNERID", "PTPG_DSTYPE"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("connected_query", {
    "display_title": "Connected Query",
    "icon": "git-merge",
    "graph_node_type": "connected_query",
    "object_page": "/admin/object/connected_query/{name}",
    "discovery": {"table": "PSCONQRSDEFN", "name_column": "CONQRSNAME"},
    "search": {"table": "PSCONQRSDEFN", "name_column": "CONQRSNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID", "PT_REPORT_STATUS"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("project", {
    "display_title": "App Designer Project",
    "icon": "package",
    "graph_node_type": "project",
    "object_page": "/admin/project",
    "discovery": {"table": "PSPROJECTDEFN", "name_column": "PROJECTNAME"},
    "search": {"table": "PSPROJECTDEFN", "name_column": "PROJECTNAME",
               "description_columns": ["PROJECTDESCR"],
               "extra_search_columns": ["LASTUPDOPRID", "RELEASELABEL"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("xlat_field", {
    "display_title": "Translate Values",
    "icon": "list",
    "graph_node_type": "xlat_field",
    "object_page": "/admin/xlat",
    "discovery": {"table": "PSXLATDEFN", "name_column": "FIELDNAME"},
    "search": {"table": "PSXLATDEFN", "name_column": "FIELDNAME",
               "description_columns": [],
               "extra_search_columns": []},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("file_layout", {
    "display_title": "File Layout",
    "icon": "file-text",
    "graph_node_type": "file_layout",
    "object_page": "/admin/filelayout",
    "discovery": {"table": "PSFLDDEFN", "name_column": "FLDDEFNNAME"},
    "search": {"table": "PSFLDDEFN", "name_column": "FLDDEFNNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["FLDFORMAT"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

# Compound key: "{PRCSTYPE}~{PRCSNAME}" — PRCSNAME alone is not unique across types
OBJECT_REGISTRY.setdefault("prcs_defn", {
    "display_title": "Process Definition",
    "icon": "cpu",
    "graph_node_type": "prcs_defn",
    "object_page": "/admin/prcsdefn",
    "discovery": {"table": "PS_PRCSDEFN", "name_column": "PRCSNAME"},
    "search": {"table": "PS_PRCSDEFN", "name_column": "PRCSNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["PRCSTYPE", "PRCSCATEGORY"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY["message"] = {
    "display_title": "IB Message",
    "icon": "mail",
    "graph_node_type": "message",
    "object_page": "/admin/ibmessage",
    "discovery": {"table": "PSMSGDEFN", "name_column": "MSGNAME"},
    "search": {"table": "PSMSGDEFN", "name_column": "MSGNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["CHNLNAME", "OBJECTOWNERID", "MSGSTATUS"]},
    "supported_versions": ["8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
}

OBJECT_REGISTRY.setdefault("ib_application", {
    "display_title": "IB Application Service",
    "icon": "globe",
    "graph_node_type": "ib_application",
    "object_page": "/admin/ibapp",
    "discovery": {"table": "PSIBAPPLDEFN", "name_column": "PTIBAPPLNAME"},
    "search": {"table": "PSIBAPPLDEFN", "name_column": "PTIBAPPLNAME",
               "description_columns": ["DESCRLONG"],
               "extra_search_columns": ["PTIB_APPSRVGRP", "OBJECTOWNERID"]},
    "supported_versions": ["8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("app_class", {
    "display_title": "Application Class",
    "icon": "code",
    "graph_node_type": "app_class",
    "object_page": "/admin/appclass",
    "discovery": {"table": "PSAPPCLASSDEFN", "name_column": "APPCLASSID"},
    "search": {"table": "PSAPPCLASSDEFN", "name_column": "APPCLASSID",
               "description_columns": [],
               "extra_search_columns": ["PACKAGEROOT", "QUALIFYPATH"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55",
                           "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("content_service", {
    "display_title": "Content Service",
    "icon": "layers",
    "graph_node_type": "content_service",
    "object_page": "/admin/contsvc",
    "discovery": {"table": "PSPTCSSRVDEFN", "name_column": "PTCS_SERVICEID"},
    "search": {"table": "PSPTCSSRVDEFN", "name_column": "PTCS_SERVICEID",
               "description_columns": ["DESCR254"],
               "extra_search_columns": ["PTCS_SERVICENAME", "OBJECTOWNERID"]},
    "supported_versions": ["8.52", "8.53", "8.54", "8.55", "8.56",
                           "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("ptf_test", {
    "display_title": "PTF Test",
    "icon": "check-square",
    "graph_node_type": "ptf_test",
    "object_page": "/admin/ptftest",
    "discovery": {"table": "PSPTTSTDEFN", "name_column": "PTTST_NAME"},
    "search": {"table": "PSPTTSTDEFN", "name_column": "PTTST_NAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["PTTST_PARENTFOLDER", "PTTST_TYPE"]},
    "supported_versions": ["8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("timezone", {
    "display_title": "Timezone",
    "icon": "clock",
    "graph_node_type": "timezone",
    "object_page": "/admin/timezone",
    "discovery": {"table": "PSTIMEZONEDEFN", "name_column": "TIMEZONE"},
    "search": {"table": "PSTIMEZONEDEFN", "name_column": "TIMEZONE",
               "description_columns": ["TZDESCR"], "extra_search_columns": []},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("locale", {
    "display_title": "Locale",
    "icon": "globe",
    "graph_node_type": "locale",
    "object_page": "/admin/locale",
    "discovery": {"table": "PSLOCALEDEFN", "name_column": "LOCALECD"},
    "search": {"table": "PSLOCALEDEFN", "name_column": "LOCALECD",
               "description_columns": ["DESCR"], "extra_search_columns": []},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("archive_object", {
    "display_title": "Archive Object",
    "icon": "archive",
    "graph_node_type": "archive_object",
    "object_page": "/admin/archobj",
    "discovery": {"table": "PSARCHOBJDEFN", "name_column": "PSARCH_OBJECT"},
    "search": {"table": "PSARCHOBJDEFN", "name_column": "PSARCH_OBJECT",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("style_sheet", {
    "display_title": "Style Sheet",
    "icon": "layout",
    "graph_node_type": "style_sheet",
    "object_page": "/admin/stylesheet",
    "discovery": {"table": "PSSTYLSHEETDEFN", "name_column": "STYLESHEETNAME"},
    "search": {"table": "PSSTYLSHEETDEFN", "name_column": "STYLESHEETNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("ib_routing", {
    "display_title": "IB Routing",
    "icon": "shuffle",
    "graph_node_type": "ib_routing",
    "object_page": "/admin/ibrtng",
    "discovery": {"table": "PSIBRTNGDEFN", "name_column": "ROUTINGDEFNNAME"},
    "search": {"table": "PSIBRTNGDEFN", "name_column": "ROUTINGDEFNNAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["IB_OPERATIONNAME", "SENDERNODENAME", "RECEIVERNODENAME"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("chatbot_skill", {
    "display_title": "Chatbot Skill",
    "icon": "message-square",
    "graph_node_type": "chatbot_skill",
    "object_page": "/admin/cbskill",
    "discovery": {"table": "PSCBAPPLDEFN", "name_column": "PTCBAPPLNAME"},
    "search": {"table": "PSCBAPPLDEFN", "name_column": "PTCBAPPLNAME",
               "description_columns": ["DESCR50"],
               "extra_search_columns": ["PTCBURLPARAMNAME", "APPCLASSID"]},
    "supported_versions": ["8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("url_definition", {
    "display_title": "URL Definition",
    "icon": "link",
    "graph_node_type": "url_definition",
    "object_page": "/admin/urldef",
    "discovery": {"table": "PSURLDEFN", "name_column": "URL_ID"},
    "search": {"table": "PSURLDEFN", "name_column": "URL_ID",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["URL", "OBJECTOWNERID"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("ib_service_group", {
    "display_title": "IB Service Group",
    "icon": "layers",
    "graph_node_type": "ib_service_group",
    "object_page": "/admin/ibsvcgrp",
    "discovery": {"table": "PSIBGROUPDEFN", "name_column": "IB_INTGROUPNAME"},
    "search": {"table": "PSIBGROUPDEFN", "name_column": "IB_INTGROUPNAME",
               "description_columns": ["DESCR", "DESCRLONG"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.50", "8.51", "8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

OBJECT_REGISTRY.setdefault("ads_definition", {
    "display_title": "ADS Definition",
    "icon": "package",
    "graph_node_type": "ads_definition",
    "object_page": "/admin/adsdef",
    "discovery": {"table": "PSADSDEFN", "name_column": "PTADSNAME"},
    "search": {"table": "PSADSDEFN", "name_column": "PTADSNAME",
               "description_columns": ["DESCR", "DESCR254"],
               "extra_search_columns": ["OBJECTOWNERID"]},
    "supported_versions": ["8.52", "8.53", "8.54", "8.55", "8.56", "8.57", "8.58", "8.59", "8.60", "8.61", "8.62"],
    "relationships": [],
})

for object_type in [
    "content_reference",
    "section",
    "step",
    "sql",
    "process_scheduler",
    "runtime_instance",
]:
    OBJECT_REGISTRY.setdefault(object_type, {
        "display_title": object_type.replace("_", " ").title(),
        "icon": "circle",
        "graph_node_type": object_type,
        "object_page": f"/admin/object/{object_type}" + "/{name}",
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
    })


VERSION_ADAPTERS = {
    # PeopleTools version → known behavioral differences from baseline.
    # "column_aliases": maps (table, logical_name) → actual_column_name override
    # "new_tables": tables introduced in this version
    # "removed_tables": tables removed or renamed in this version
    # "notes": human-readable summary
    "8.58": {
        "status": "supported",
        "notes": "Baseline PeopleTools version. All common metadata tables present.",
        "new_tables": [],
        "removed_tables": [],
        "column_aliases": {
            # PSPNLGRPDEFN may use ADDSEARCHRECNAME instead of ADDSRCHRECNAME
            ("PSPNLGRPDEFN", "add_search_rec"): "ADDSEARCHRECNAME",
            # PSPCMTXT used PROGTXT in older installs
            ("PSPCMTXT", "source_column"): "PROGTXT",
        },
    },
    "8.59": {
        "status": "supported",
        "notes": "Introduced Fluid UI framework tables. PSPCMTXT standardized on PCTEXT.",
        "new_tables": ["PSPNLGRPFLUID", "PSFLDFMTDEFN"],
        "removed_tables": [],
        "column_aliases": {
            ("PSPCMTXT", "source_column"): "PCTEXT",
        },
    },
    "8.60": {
        "status": "supported",
        "notes": "Connected Content (PSCBKOPERPROG). Fluid enhancements. PCTEXT standard.",
        "new_tables": ["PSCBKOPERPROG", "PSCBKDEFN", "PSCBKPROGHDR"],
        "removed_tables": [],
        "column_aliases": {
            ("PSPCMTXT", "source_column"): "PCTEXT",
            ("PSPNLGRPDEFN", "add_search_rec"): "ADDSRCHRECNAME",
        },
    },
    "8.61": {
        "status": "supported",
        "notes": "Enhanced security framework. Application Package enhancements.",
        "new_tables": ["PSPKGDEFN"],
        "removed_tables": [],
        "column_aliases": {
            ("PSPCMTXT", "source_column"): "PCTEXT",
            ("PSPNLGRPDEFN", "add_search_rec"): "ADDSRCHRECNAME",
        },
    },
    "8.62": {
        "status": "supported",
        "notes": "Current supported version. Key management (PSPKMGMTDEFN). Full Fluid.",
        "new_tables": ["PSPKMGMTDEFN", "PSPKEYDEFN"],
        "removed_tables": [],
        "column_aliases": {
            ("PSPCMTXT", "source_column"): "PCTEXT",
            ("PSPNLGRPDEFN", "add_search_rec"): "ADDSRCHRECNAME",
        },
    },
    "unknown": {
        "status": "fallback",
        "notes": "Version not detected. All capabilities probed live via has_table()/has_column().",
        "new_tables": [],
        "removed_tables": [],
        "column_aliases": {},
    },
}


def version_column(env, table: str, logical_name: str, default: str) -> str:
    """Return the correct column name for a known alias in the detected PeopleTools version.

    Falls back to live has_column() probe if version is unknown or alias not declared.
    """
    version, _ = peopletools_version(env)
    key = str(version or "unknown")[:4]
    adapter = VERSION_ADAPTERS.get(key, VERSION_ADAPTERS["unknown"])
    declared = adapter.get("column_aliases", {}).get((table, logical_name))
    if declared:
        return declared
    # Probe live: try default first, then fallback
    if has_column(env, table, default):
        return default
    return default


def version_tables(env) -> dict:
    """Return version-specific table availability context for the detected PeopleTools version."""
    version, _ = peopletools_version(env)
    key = str(version or "unknown")[:4]
    adapter = VERSION_ADAPTERS.get(key, VERSION_ADAPTERS["unknown"])
    return {
        "version": version,
        "adapter_key": key,
        "new_tables_declared": adapter.get("new_tables", []),
        "removed_tables_declared": adapter.get("removed_tables", []),
        "notes": adapter.get("notes", ""),
    }


def object_types():
    return OBJECT_REGISTRY


def version_adapter(env):
    version, _ = peopletools_version(env)
    key = str(version or "unknown")[:4]
    return {
        "peopletools_version": version,
        "adapter_key": key if key in VERSION_ADAPTERS else "unknown",
        "adapter": VERSION_ADAPTERS.get(key, VERSION_ADAPTERS["unknown"]),
        "known_adapters": VERSION_ADAPTERS,
    }


def capabilities(env):
    entries = []

    for object_type, entry in OBJECT_REGISTRY.items():
        discovery = entry.get("discovery") or {}
        table_name = discovery.get("table")
        name_column = discovery.get("name_column")

        if not table_name:
            entries.append({
                "type": object_type,
                "supported": False,
                "reason": "No discovery provider registered yet.",
            })
            continue

        table_available = has_table(env, table_name)
        column_available = has_column(env, table_name, name_column) if table_available and name_column else False

        entries.append({
            "type": object_type,
            "table": table_name,
            "name_column": name_column,
            "table_available": table_available,
            "name_column_available": column_available,
            "supported": table_available,
            "object_page": entry["object_page"],
            "graph_node_type": entry["graph_node_type"],
            "icon": entry["icon"],
        })

    missing = [
        warning(
            "metadata_unavailable",
            f"{entry['type']} metadata is unavailable.",
            detail=entry,
        )
        for entry in entries
        if not entry.get("supported")
    ]

    return {
        "capabilities": entries,
        "warnings": missing,
    }


def discovery(env):
    schema, schema_warning = current_schema(env)
    oracle, oracle_warning = oracle_version(env)
    tools, tools_warning = peopletools_version(env)
    owners = available_owners(env)
    tables = accessible_objects(env, "TABLE")
    views = accessible_objects(env, "VIEW")
    caps = capabilities(env)

    warnings = []
    for item in (schema_warning, oracle_warning, tools_warning):
        if item:
            warnings.append(item)
    warnings.extend(owners.get("warnings", []))
    warnings.extend(tables.get("warnings", []))
    warnings.extend(views.get("warnings", []))

    return {
        "environment": env.upper(),
        "oracle_version": oracle,
        "peopletools_version": tools,
        "schema": schema,
        "owners": owners["owners"],
        "metadata_tables": tables["objects"],
        "metadata_views": views["objects"],
        "capabilities": caps["capabilities"],
        "warnings": warnings + caps["warnings"],
        "version_adapter": version_adapter(env),
    }


def installed_products(env):
    probes = [
        ("PS_INSTALLATION", ["INSTALLED_APPS", "LICENSE_CODE", "DBNAME"]),
        ("PSSTATUS", ["OWNERID", "TOOLSREL"]),
    ]
    products = []
    warnings = []

    for table_name, columns in probes:
        existing = [
            col for col in columns
            if has_column(env, table_name, col)
        ]

        if not existing:
            continue

        rows, err = safe_query(env, f"""
            select {", ".join(existing)}
              from sysadm.{table_name}
             fetch first 25 rows only
        """)
        products.extend({"source": table_name, **row} for row in rows)
        if err:
            warnings.append(err)

    return {
        "products": products,
        "warnings": warnings,
    }


def resolve_object(env, object_type, name):
    object_type = object_type.lower()
    name = name.upper()
    entry = OBJECT_REGISTRY.get(object_type)

    if not entry:
        return {
            "resolved": False,
            "warnings": [warning("unsupported_object_type", f"Unsupported object type: {object_type}")],
        }

    if object_type == "field" and "." in name:
        try:
            resolved = psdb.resolve_field_reference(env, name)
        except Exception as exc:
            resolved = {
                "canonical_name": name,
                "resolved": False,
                "warning": str(exc),
            }

        name = resolved.get("canonical_name") or name
        warnings = []
        if not resolved.get("resolved"):
            warnings.append(warning("object_not_installed", resolved.get("warning", "Field not found.")))

        return {
            "resolved": bool(resolved.get("resolved")),
            "type": object_type,
            "name": name,
            "display_title": entry["display_title"],
            "object_url": entry["object_page"].format(name=name),
            "graph_node": {
                "id": f"{entry['graph_node_type']}:{name}",
                "type": entry["graph_node_type"],
                "name": name,
            },
            "search": entry.get("search"),
            "icon": entry["icon"],
            "warnings": warnings,
        }

    return {
        "resolved": True,
        "type": object_type,
        "name": name,
        "display_title": entry["display_title"],
        "object_url": entry["object_page"].format(name=name),
        "graph_node": {
            "id": f"{entry['graph_node_type']}:{name}",
            "type": entry["graph_node_type"],
            "name": name,
        },
        "search": entry.get("search"),
        "icon": entry["icon"],
        "warnings": [],
    }


def global_search(env, q, limit=20):
    limit = max(1, min(int(limit), 50))
    pattern = f"%{q.upper()}%"
    results = []

    for object_type, entry in OBJECT_REGISTRY.items():
        provider = entry.get("search")

        if not provider:
            continue

        if provider.get("provider") == "field":
            try:
                field_rows = psdb.fields(env, q, limit)
                for row in field_rows:
                    recname = row.get("recname")
                    fieldname = row.get("fieldname")
                    if not recname or not fieldname:
                        continue

                    name = f"{recname}.{fieldname}"
                    description = row.get("db_descr") or row.get("db_longname") or row.get("label_id")
                    name_upper = name.upper()
                    score = 12

                    if name_upper == q.upper() or fieldname.upper() == q.upper():
                        score += 100
                    elif name_upper.startswith(q.upper()) or fieldname.upper().startswith(q.upper()):
                        score += 50

                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": description,
                        "score": score,
                        "icon": entry["icon"],
                        "_links": {
                            "admin": entry["object_page"].format(name=name),
                        },
                    })
            except Exception as exc:
                results.append({
                    "type": object_type,
                    "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0,
                    "icon": entry["icon"],
                    "error": True,
                })
            continue

        if provider.get("provider") == "ib_service_operation":
            # DISTINCT search over PSIBRTNGDEFN.IB_OPERATIONNAME
            try:
                table_name = provider["table"]
                name_col = provider["name_column"]
                if not has_table(env, table_name):
                    continue
                rows = psdb.query(env, f"""
                    SELECT DISTINCT upper({name_col}) as name
                      FROM sysadm.{table_name}
                     WHERE upper({name_col}) LIKE :pat
                       AND {name_col} IS NOT NULL
                       AND {name_col} != ' '
                     ORDER BY 1
                     FETCH FIRST {limit} ROWS ONLY
                """, {"pat": f"%{q.upper()}%"})
                for row in rows:
                    name = row.get("name", "").strip()
                    if not name:
                        continue
                    score = 18
                    if name == q.upper():
                        score += 100
                    elif name.startswith(q.upper()):
                        score += 50
                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": "IB Service Operation",
                        "score": score,
                        "icon": entry["icon"],
                        "_links": {"admin": entry["object_page"].format(name=name)},
                    })
            except Exception as exc:
                results.append({
                    "type": object_type, "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0, "icon": entry["icon"], "error": True,
                })
            continue

        if provider.get("provider") == "query":
            try:
                table_name = provider["table"]
                if not has_table(env, table_name):
                    continue
                qry_cols = psdb.select_existing_columns(
                    env, table_name,
                    ["QRYNAME", "DESCR", "DESCRLONG", "QRYFOLDER"],
                    required=["QRYNAME"],
                )
                available_q = {c.upper() for c in qry_cols}
                desc_col = "DESCR" if "DESCR" in available_q else "null"
                extra_pred = " OR UPPER(DESCR) LIKE :pat" if "DESCR" in available_q else ""
                rows = psdb.query(env, f"""
                    SELECT QRYNAME as name, {desc_col} as description
                      FROM SYSADM.{table_name}
                     WHERE OPRID = ' '
                       AND (UPPER(QRYNAME) LIKE :pat{extra_pred})
                     ORDER BY QRYNAME
                     FETCH FIRST {limit} ROWS ONLY
                """, {"pat": pattern})
                for row in rows:
                    name = str(row.get("name") or "").strip()
                    if not name:
                        continue
                    description = str(row.get("description") or "").strip() or None
                    score = 14
                    if name == q.upper():
                        score += 100
                    elif name.startswith(q.upper()):
                        score += 50
                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": description,
                        "score": score,
                        "icon": entry["icon"],
                        "_links": {"admin": entry["object_page"].format(name=name)},
                    })
            except Exception as exc:
                results.append({
                    "type": object_type, "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0, "icon": entry["icon"], "error": True,
                })
            continue

        if provider.get("provider") == "tree":
            try:
                rows = psdb.search_trees(env, q=q, limit=limit)
                seen_names = set()
                for row in rows:
                    name = str(row.get("treename") or "").strip()
                    if not name:
                        continue
                    if name.upper() in seen_names:
                        continue
                    seen_names.add(name.upper())

                    name_upper = name.upper()
                    score = 10
                    if name_upper == q.upper():
                        score += 100
                    elif name_upper.startswith(q.upper()):
                        score += 50

                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": row.get("descr") or "",
                        "score": score,
                        "icon": entry["icon"],
                        "metadata": {
                            "setid": row.get("setid"),
                            "setcntrlvalue": row.get("setcntrlvalue"),
                            "tree_structure": row.get("treestrctpnm"),
                            "effdt": row.get("effdt"),
                            "status": row.get("eff_status"),
                        },
                        "_links": {"admin": entry["object_page"].format(name=name)},
                    })
            except Exception as exc:
                results.append({
                    "type": object_type, "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0, "icon": entry["icon"], "error": True,
                })
            continue

        if provider.get("provider") == "peoplecode":
            try:
                from connectors import peoplecode

                peoplecode_rows = peoplecode.programs(env, q, limit)
                for row in peoplecode_rows["items"]:
                    reference = row.get("reference")
                    if not reference:
                        continue

                    source = row.get("source") or ""
                    score = 20
                    if reference == q.upper():
                        score += 100
                    elif reference.startswith(q.upper()):
                        score += 50
                    if source and q.upper() in source.upper():
                        score += 10

                    results.append({
                        "type": object_type,
                        "name": row.get("encoded_reference") or peoplecode.encode_reference(reference),
                        "description": reference,
                        "score": score,
                        "icon": entry["icon"],
                        "_links": {
                            "admin": entry["object_page"].format(name=row.get("encoded_reference") or peoplecode.encode_reference(reference)),
                        },
                    })
            except Exception as exc:
                results.append({
                    "type": object_type,
                    "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0,
                    "icon": entry["icon"],
                    "error": True,
                })
            continue

        if provider.get("provider") == "app_package":
            try:
                table_name = provider["table"]
                if not has_table(env, table_name):
                    continue
                rows = psdb.query(env, f"""
                    SELECT DISTINCT PACKAGEROOT as name, MAX(DESCR) as description,
                           COUNT(*) as class_count
                      FROM sysadm.PSPACKAGEDEFN
                     WHERE UPPER(PACKAGEROOT) LIKE :pat
                        OR UPPER(DESCR) LIKE :pat
                     GROUP BY PACKAGEROOT
                     ORDER BY PACKAGEROOT
                     FETCH FIRST {limit} ROWS ONLY
                """, {"pat": f"%{q.upper()}%"})
                for row in rows:
                    name = str(row.get("name") or "").strip()
                    if not name:
                        continue
                    description = str(row.get("description") or "").strip() or None
                    score = 16
                    if name.upper() == q.upper():
                        score += 100
                    elif name.upper().startswith(q.upper()):
                        score += 50
                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": description,
                        "score": score,
                        "icon": entry["icon"],
                        "_links": {"admin": entry["object_page"].format(name=name)},
                    })
            except Exception as exc:
                results.append({
                    "type": object_type, "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0, "icon": entry["icon"], "error": True,
                })
            continue

        if provider.get("provider") == "message_catalog":
            try:
                table_name = provider["table"]
                if not has_table(env, table_name):
                    continue
                # Search message text; also match numeric set queries like "50" or "50.1180"
                rows = psdb.query(env, f"""
                    SELECT MESSAGE_SET_NBR, MESSAGE_NBR, SEVERITY, MESSAGE_TEXT
                      FROM SYSADM.{table_name}
                     WHERE UPPER(MESSAGE_TEXT) LIKE :pat
                        OR UPPER(DESCRLONG)    LIKE :pat
                     ORDER BY MESSAGE_SET_NBR, MESSAGE_NBR
                     FETCH FIRST {limit} ROWS ONLY
                """, {"pat": f"%{q.upper()}%"})
                for row in rows:
                    sn = row.get("message_set_nbr")
                    mn = row.get("message_nbr")
                    name = f"{sn}.{mn}"
                    text = str(row.get("message_text") or "").strip()
                    results.append({
                        "type": object_type,
                        "name": name,
                        "description": text[:120] if text else None,
                        "score": 12,
                        "icon": entry["icon"],
                        "_links": {"admin": entry["object_page"].format(name=name)},
                    })
            except Exception as exc:
                results.append({
                    "type": object_type, "name": None,
                    "description": f"Search failed: {exc}",
                    "score": 0, "icon": entry["icon"], "error": True,
                })
            continue

        table_name = provider["table"]
        name_col = provider["name_column"]
        description_candidates = provider.get("description_columns", [])
        search_candidates = description_candidates + provider.get("extra_search_columns", [])

        try:
            columns = psdb.select_existing_columns(
                env,
                table_name,
                description_candidates + search_candidates,
                required=[name_col],
            )
            available = {col.upper() for col in columns}
            descriptions = [col for col in description_candidates if col.upper() in available]
            searches = [col for col in search_candidates if col.upper() in available]
            description_expr = descriptions[0] if descriptions else "null"
            predicates = [f"upper({name_col}) like :pattern"]
            predicates.extend(f"upper({col}) like :pattern" for col in searches)

            rows = psdb.query(env, f"""
                select {name_col} as name,
                       {description_expr} as description
                  from sysadm.{table_name}
                 where {" or ".join(predicates)}
                 order by {name_col}
                 fetch first {limit} rows only
            """, {"pattern": pattern})

            for row in rows:
                name = row["name"]
                description = row.get("description")
                name_upper = str(name or "").upper()
                description_upper = str(description or "").upper()
                score = 10

                if name_upper == q.upper():
                    score += 100
                elif name_upper.startswith(q.upper()):
                    score += 50

                if object_type == "page":
                    score += 8

                if q.upper() in description_upper:
                    score += 5

                results.append({
                    "type": object_type,
                    "name": name,
                    "description": description,
                    "score": score,
                    "icon": entry["icon"],
                    "_links": {
                        "admin": entry["object_page"].format(name=name),
                    },
                })
        except Exception as exc:
            results.append({
                "type": object_type,
                "name": None,
                "description": f"Search failed: {exc}",
                "score": 0,
                "icon": entry["icon"],
                "error": True,
            })

    return sorted(
        (r for r in results if not r.get("error") and r.get("name")),
        key=lambda item: (
            -item.get("score", 0),
            item.get("type") or "",
            item.get("name") or "",
        ),
    )


def relationship_stub(env, object_type, name, relationship):
    return {
        "environment": env.upper(),
        "type": object_type,
        "name": name.upper(),
        "relationship": relationship,
        "items": [],
        "warnings": [
            warning(
                "relationship_provider_pending",
                f"Relationship provider '{relationship}' is not yet implemented in the metadata engine.",
            )
        ],
    }


def parents(env, object_type, name):
    return relationship_stub(env, object_type, name, "parents")


def children(env, object_type, name):
    return relationship_stub(env, object_type, name, "children")


def references(env, object_type, name):
    return relationship_stub(env, object_type, name, "references")


def referenced_by(env, object_type, name):
    return relationship_stub(env, object_type, name, "referenced_by")


def security(env, object_type, name):
    return relationship_stub(env, object_type, name, "security")
