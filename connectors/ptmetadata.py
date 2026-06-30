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
    },
    "role": {
        "display_title": "Role",
        "icon": "shield",
        "graph_node_type": "role",
        "object_page": "/admin/object/role/{name}",
        "discovery": {"table": "PSROLEDEFN", "name_column": "ROLENAME"},
        "search": {"table": "PSROLEDEFN", "name_column": "ROLENAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "permissionlist": {
        "display_title": "Permission List",
        "icon": "key",
        "graph_node_type": "permissionlist",
        "object_page": "/admin/object/permissionlist/{name}",
        "discovery": {"table": "PSCLASSDEFN", "name_column": "CLASSID"},
        "search": {"table": "PSCLASSDEFN", "name_column": "CLASSID", "description_columns": ["DESCR", "CLASSDEFNDESC"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "component": {
        "display_title": "Component",
        "icon": "panel",
        "graph_node_type": "component",
        "object_page": "/admin/object/component/{name}",
        "discovery": {"table": "PSPNLGRPDEFN", "name_column": "PNLGRPNAME"},
        "search": {"table": "PSPNLGRPDEFN", "name_column": "PNLGRPNAME", "description_columns": ["DESCR"], "extra_search_columns": ["SEARCHRECNAME", "ADDSEARCHRECNAME"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "page": {
        "display_title": "Page",
        "icon": "file",
        "graph_node_type": "page",
        "object_page": "/admin/object/page/{name}",
        "discovery": {"table": "PSPNLDEFN", "name_column": "PNLNAME"},
        "search": {"table": "PSPNLDEFN", "name_column": "PNLNAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "record": {
        "display_title": "Record",
        "icon": "table",
        "graph_node_type": "record",
        "object_page": "/admin/object/record/{name}",
        "discovery": {"table": "PSRECDEFN", "name_column": "RECNAME"},
        "search": {"table": "PSRECDEFN", "name_column": "RECNAME", "description_columns": ["RECDESCR"], "extra_search_columns": ["SQLTABLENAME"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "field": {
        "display_title": "Field",
        "icon": "type",
        "graph_node_type": "field",
        "object_page": "/admin/object/field/{name}",
        "discovery": {"table": "PSDBFIELD", "name_column": "FIELDNAME"},
        "search": {"provider": "field", "table": "PSRECFIELD", "name_column": "FIELDNAME", "description_columns": ["DESCR"]},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
    },
    "peoplecode": {
        "display_title": "PeopleCode",
        "icon": "code",
        "graph_node_type": "peoplecode",
        "object_page": "/admin/object/peoplecode/{name}",
        "discovery": {"table": "PSPCMPROG", "name_column": "PROGSEQ"},
        "search": {"provider": "peoplecode", "table": "PSPCMPROG", "name_column": "PROGSEQ", "description_columns": []},
        "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
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
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
    },
    "application_class": {
        "display_title": "Application Class",
        "icon": "box",
        "graph_node_type": "application_class",
        "object_page": "/admin/object/application_class/{name}",
        "discovery": None,
        "search": None,
        "supported_versions": ["planned"],
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
})

OBJECT_REGISTRY.setdefault("tree", {
    "display_title": "Tree",
    "icon": "git-branch",
    "graph_node_type": "tree",
    "object_page": "/admin/object/tree/{name}",
    "discovery": {"table": "PSTREEDEFN", "name_column": "TREE_NAME"},
    "search": {"table": "PSTREEDEFN", "name_column": "TREE_NAME",
               "description_columns": ["DESCR"],
               "extra_search_columns": ["TREE_STRCT_ID", "SETID"]},
    "supported_versions": ["8.58", "8.59", "8.60", "8.61", "8.62"],
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
})

for object_type in [
    "menu",
    "content_reference",
    "section",
    "step",
    "sql",
    "message",
    "approval",
    "event_mapping",
    "related_content",
    "drop_zone",
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
    "8.58": {"status": "baseline", "notes": "Uses common PeopleTools metadata names."},
    "8.59": {"status": "baseline", "notes": "Uses common PeopleTools metadata names."},
    "8.60": {"status": "baseline", "notes": "Uses common PeopleTools metadata names."},
    "8.61": {"status": "baseline", "notes": "Uses common PeopleTools metadata names."},
    "8.62": {"status": "baseline", "notes": "Uses common PeopleTools metadata names."},
    "unknown": {"status": "fallback", "notes": "Capabilities are detected from database metadata and direct probes."},
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
