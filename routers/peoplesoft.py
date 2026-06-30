from fastapi import APIRouter, HTTPException
from connectors import ae, graphdb, peoplecode, peoplesoft, psdb, ptmetadata, uom

router = APIRouter()


def explorer_links(env: str, **objects):
    params = f"?env={env}"
    links = {}

    if objects.get("rolename"):
        role = objects["rolename"]
        links["admin"] = f"/admin/object/role/{role}"
        links["self"] = f"/api/peoplesoft/roles/{role}{params}"
        links["permissionlists"] = f"/api/peoplesoft/roles/{role}/permissionlists{params}"

    if objects.get("oprid"):
        oprid = objects["oprid"]
        links["admin"] = f"/admin/object/operator/{oprid}"
        links["security"] = f"/api/peoplesoft/security/operators/{oprid}{params}"

    if objects.get("classid"):
        classid = objects["classid"]
        links["admin"] = f"/admin/object/permissionlist/{classid}"
        links["self"] = f"/api/peoplesoft/permissionlists/{classid}{params}"
        links["menus"] = f"/api/peoplesoft/permissionlists/{classid}/menus{params}"
        links["components"] = f"/api/peoplesoft/permissionlists/{classid}/components{params}"

    if objects.get("component"):
        component = objects["component"]
        links["admin"] = f"/admin/object/component/{component}"
        links["self"] = f"/api/peoplesoft/components/{component}{params}"
        links["pages"] = f"/api/peoplesoft/components/{component}/pages{params}"

    if objects.get("page"):
        page = objects["page"]
        links["admin"] = f"/admin/object/page/{page}"
        links["self"] = f"/api/peoplesoft/pages/{page}{params}"
        links["components"] = f"/api/peoplesoft/pages/{page}/components{params}"

    if objects.get("record"):
        record = objects["record"]
        links["admin"] = f"/admin/object/record/{record}"
        links["self"] = f"/api/peoplesoft/records/{env}/{record}/ddl"
        links["fields"] = f"/api/peoplesoft/records/{env}/{record}/fields"
        links["where_used"] = f"/api/peoplesoft/records/{env}/{record}/where-used"

    if objects.get("field"):
        field = objects["field"]
        links["admin"] = f"/admin/object/field/{field}"

    if objects.get("peoplecode"):
        reference = objects["peoplecode"]
        links["admin"] = f"/admin/object/peoplecode/{reference}"

    return links


def attach_links(row, env: str):
    linked = dict(row)

    rolename = linked.get("rolename")
    oprid = linked.get("roleuser") or linked.get("oprid")
    classid = linked.get("classid")
    component = linked.get("pnlgrpname") or linked.get("component")
    page = linked.get("pnlname")
    record = linked.get("recname")
    if not record and not component:
        record = linked.get("searchrecname") or linked.get("addsearchrecname")
    field = f"{record}.{linked.get('fieldname')}" if record and linked.get("fieldname") else None

    links = explorer_links(
        env,
        oprid=oprid,
        rolename=rolename,
        classid=classid,
        component=component,
        page=page,
        record=record,
        field=field,
    )

    portal_objname = str(linked.get("portal_objname") or "").strip()
    if portal_objname and "admin" not in links:
        links["admin"] = f"/admin/object/portal_registry/{portal_objname}"

    linked["_links"] = links
    return linked


def node(node_type, node_id, label=None, data=None):
    return {
        "id": f"{node_type}:{node_id}",
        "type": node_type,
        "name": node_id,
        "label": label or node_id,
        "data": data or {},
    }


def edge(source_type, source_id, target_type, target_id, relationship):
    return {
        "source": f"{source_type}:{source_id}",
        "target": f"{target_type}:{target_id}",
        "relationship": relationship,
    }


def add_node(nodes, item):
    nodes[item["id"]] = item


def graph_response(root_type, root_name, nodes, edges):
    return {
        "root": f"{root_type}:{root_name}",
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def graphdb_response(env, root_type, root_name):
    root = f"{root_type}:{root_name}"
    graph_node = graphdb.get_node(env, root)

    if not graph_node:
        return None

    neighborhood = graphdb.neighbors(env, root, direction="both", depth=1)
    nodes = {root: {
        "id": graph_node["id"],
        "type": graph_node["type"],
        "name": graph_node["name"],
        "label": graph_node.get("display_name") or graph_node["name"],
        "data": graph_node.get("metadata", {}),
        "_links": {"admin": graph_node.get("canonical_url")},
    }}

    for item in neighborhood.get("nodes", []):
        nodes[item["id"]] = {
            "id": item["id"],
            "type": item["type"],
            "name": item["name"],
            "label": item.get("display_name") or item["name"],
            "data": item.get("metadata", {}),
            "_links": {"admin": item.get("canonical_url")},
        }

    edges = [
        {
            "source": item["source"],
            "target": item["target"],
            "relationship": item["type"],
            "data": item.get("metadata", {}),
        }
        for item in neighborhood.get("edges", [])
    ]

    return {
        "root": root,
        "nodes": list(nodes.values()),
        "edges": edges,
        "_source": "knowledge_graph",
    }


def section(name, items=None, data=None):
    return {
        "name": name,
        "items": items or [],
        "data": data or {},
    }


def safe_section(name, loader, env):
    try:
        return section(name, [attach_links(row, env) for row in loader()])
    except Exception as exc:
        return section(name, data={"warning": str(exc)})


def safe_rows(loader):
    try:
        return loader()
    except Exception:
        return []


def safe_items(name, loader, env):
    try:
        return section(name, [attach_links(row, env) for row in loader()])
    except Exception as exc:
        return section(name, data={"warning": str(exc)})


def attach_graph_context(payload, env):
    # Guard against double-application (e.g. called inside object_payload and again at route level)
    if any(s.get("name") == "Knowledge Graph Neighbors" for s in payload.get("sections", [])):
        return payload
    try:
        node_id = f"{payload['type']}:{payload['name']}"
        graph = graphdb.neighbors(env, node_id, direction="both", depth=1)
    except Exception:
        return payload

    if not graph.get("nodes") and not graph.get("edges"):
        return payload

    items = []
    for node_row in graph.get("nodes", []):
        items.append({
            "relationship": "neighbor",
            "type": node_row.get("type"),
            "name": node_row.get("name"),
            "id": node_row.get("id"),
            "_links": {"admin": node_row.get("canonical_url")},
        })

    payload.setdefault("sections", []).append(section("Knowledge Graph Neighbors", items, {
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
    }))
    payload.setdefault("_links", {})["knowledge_graph"] = f"/api/graph/neighbors/{node_id}?env={env}"
    return payload


def normalize_object_type(object_type: str) -> str:
    object_type = (object_type or "").strip().lower()
    aliases = {
        "permission_list": "permissionlist",
        "permissionlist": "permissionlist",
        "portal": "portal_registry",
        "content_reference": "portal_registry",
        "application_engine": "application_engine",
        "sql_definition": "sql_definition",
        "service_operation": "service_operation",
        "tree": "tree",
    }
    return aliases.get(object_type, object_type)


def object_payload(env, object_type, object_name):
    object_type = normalize_object_type(object_type)
    object_name = object_name.upper()
    graph_link = f"/api/peoplesoft/graph/{object_type}/{object_name}?env={env}"
    admin_link = f"/admin/object/{object_type}/{object_name}"

    if object_type == "operator":
        op_obj = uom.operator_object(env, object_name)
        if op_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Operator not found")
        return attach_graph_context(uom.operator_payload(op_obj), env)

    if object_type == "role":
        role_obj = uom.role_object(env, object_name)
        if role_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Role not found")
        return attach_graph_context(uom.role_payload(role_obj), env)

    if object_type == "permissionlist":
        pl_obj = uom.permissionlist_object(env, object_name)
        if pl_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Permission list not found")
        return attach_graph_context(uom.permissionlist_payload(pl_obj), env)

    if object_type == "component":
        component_obj = uom.component_object(env, object_name)
        return attach_graph_context(uom.component_payload(component_obj), env)

    if object_type == "page":
        page_obj = uom.page_object(env, object_name)
        return attach_graph_context(uom.page_payload(page_obj), env)

    if object_type == "portal_registry":
        portal_obj = uom.portal_registry_object(env, object_name)
        return attach_graph_context(uom.portal_registry_payload(portal_obj), env)

    if object_type == "record":
        rec_obj = uom.record_object(env, object_name)
        if rec_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Record not found")
        return attach_graph_context(uom.record_payload(rec_obj), env)

    if object_type == "field":
        if "." not in object_name:
            raise HTTPException(status_code=400, detail="Field name must be RECORD.FIELD")

        return uom.object_payload(uom.field_object(env, object_name))

    if object_type == "peoplecode":
        return uom.peoplecode_payload(uom.peoplecode_object(env, object_name))

    if object_type == "application_engine":
        ae_obj = uom.ae_object(env, object_name)
        payload = uom.ae_payload(ae_obj)
        return attach_graph_context(payload, env)

    if object_type == "service_operation":
        svc_obj = uom.service_object(env, object_name)
        return attach_graph_context(uom.service_payload(svc_obj), env)

    if object_type == "node":
        node_obj = uom.node_object(env, object_name)
        return attach_graph_context(uom.node_payload(node_obj), env)

    if object_type == "queue":
        q_obj = uom.queue_object(env, object_name)
        return uom.queue_payload(q_obj)

    if object_type == "routing":
        r_obj = uom.routing_object(env, object_name)
        return attach_graph_context(uom.routing_payload(r_obj), env)

    if object_type == "sql_definition":
        s_obj = uom.sql_object(env, object_name)
        return uom.sql_payload(s_obj)

    if object_type == "query":
        q_obj = uom.query_object(env, object_name)
        return uom.query_payload(q_obj)

    if object_type == "tree":
        tree_obj = uom.tree_object(env, object_name)
        if tree_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Tree not found")
        return attach_graph_context(uom.tree_payload(tree_obj), env)

    raise HTTPException(status_code=400, detail="Unsupported object type")


@router.get("/api/peoplesoft/summary")
def peoplesoft_summary():
    return peoplesoft.summary()


@router.get("/api/peoplesoft/env/{env}")
def peoplesoft_environment(env: str):
    return peoplesoft.environment(env)

@router.get("/api/peoplesoft/db/{env}/count/{table}")
def peoplesoft_table_count(env: str, table: str):
    return psdb.table_count(env, table.upper())

@router.get("/api/peoplesoft/db/{env}/tables/{pattern}")
def peoplesoft_find_tables(env: str, pattern: str):
    sql = """
        select owner, table_name
        from all_tables
        where upper(table_name) like :pattern
        order by table_name
    """

    return psdb.query(
        env,
        sql,
        {"pattern": f"%{pattern.upper()}%"}
    )


@router.get("/api/peoplesoft/schema/search")
def peoplesoft_schema_search(env: str = "HCM", q: str = "", owner: str = "SYSADM"):
    return psdb.search_objects(env, q, owner)


@router.get("/api/peoplesoft/schema/{env}/{owner}/{object_name}/columns")
def peoplesoft_schema_columns(env: str, owner: str, object_name: str):
    return psdb.object_columns(env, object_name, owner)


@router.get("/api/peoplesoft/schema/{env}/{owner}/{object_name}/count")
def peoplesoft_schema_count(env: str, owner: str, object_name: str):
    return psdb.object_count(env, object_name, owner)


@router.get("/api/peoplesoft/schema/{env}/{owner}/{object_name}/sample")
def peoplesoft_schema_sample(env: str, owner: str, object_name: str, limit: int = 20):
    return psdb.sample_rows(env, object_name, owner, limit)


@router.get("/api/peoplesoft/records/search")
def peoplesoft_record_search(env: str = "HCM", q: str = ""):
    return psdb.search_records(env, q)


@router.get("/api/peoplesoft/records/{env}/{recname}/fields")
def peoplesoft_record_fields(env: str, recname: str):
    return psdb.record_fields(env, recname)


@router.get("/api/peoplesoft/records/{env}/{recname}/indexes")
def peoplesoft_record_indexes(env: str, recname: str):
    return psdb.record_indexes(env, recname)


@router.get("/api/peoplesoft/records/{env}/{recname}/keys")
def peoplesoft_record_keys(env: str, recname: str):
    return psdb.record_keys(env, recname)


@router.get("/api/peoplesoft/records/{env}/{recname}/ddl")
def peoplesoft_record_ddl(env: str, recname: str):
    return psdb.record_ddl(env, recname)


@router.get("/api/peoplesoft/records/{env}/{recname}/count")
def peoplesoft_record_count(env: str, recname: str):
    return psdb.record_count(env, recname)


@router.get("/api/peoplesoft/records/{env}/{recname}/sample")
def peoplesoft_record_sample(env: str, recname: str, limit: int = 20):
    return psdb.record_sample(env, recname, limit)


@router.get("/api/peoplesoft/records/{env}/{recname}/where-used")
def peoplesoft_record_where_used(env: str, recname: str):
    return {
        "record": recname.upper(),
        "children": [
            attach_links(row, env)
            for row in safe_rows(lambda: psdb.record_children(env, recname))
        ],
        "components": [
            attach_links(row, env)
            for row in safe_rows(lambda: psdb.record_components(env, recname))
        ],
        "pages": [
            attach_links(row, env)
            for row in safe_rows(lambda: psdb.record_pages(env, recname))
        ],
    }


@router.get("/api/peoplesoft/fields")
def peoplesoft_fields(env: str = "HCM", q: str = "", limit: int = 100):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.fields(env, q, limit))
    ]


@router.get("/api/peoplesoft/fields/{field_ref}/records")
def peoplesoft_field_records(field_ref: str, env: str = "HCM"):
    field = uom.field_object(env, field_ref)
    return field["_relationships"]["records"]


@router.get("/api/peoplesoft/fields/{field_ref}/pages")
def peoplesoft_field_pages(field_ref: str, env: str = "HCM"):
    field = uom.field_object(env, field_ref)
    return field["_relationships"]["pages"]


@router.get("/api/peoplesoft/fields/{field_ref}/components")
def peoplesoft_field_components(field_ref: str, env: str = "HCM"):
    field = uom.field_object(env, field_ref)
    return field["_relationships"]["components"]


@router.get("/api/peoplesoft/fields/{field_ref}/graph")
def peoplesoft_field_graph(field_ref: str, env: str = "HCM"):
    return uom.field_object(env, field_ref)["_graph"]


@router.get("/api/peoplesoft/fields/{field_ref}")
def peoplesoft_field(field_ref: str, env: str = "HCM"):
    return uom.field_object(env, field_ref)


@router.get("/api/peoplesoft/peoplecode/search")
def peoplesoft_peoplecode_search(q: str = "", env: str = "HCM", limit: int = 100):
    return peoplecode.programs(env, q, limit)


@router.get("/api/peoplesoft/peoplecode")
def peoplesoft_peoplecode(env: str = "HCM", q: str = "", limit: int = 100):
    return peoplecode.programs(env, q, limit)


@router.get("/api/peoplesoft/peoplecode/{reference:path}/references")
def peoplesoft_peoplecode_references(reference: str, env: str = "HCM"):
    return peoplecode.references(reference, env)


@router.get("/api/peoplesoft/peoplecode/{reference:path}/graph")
def peoplesoft_peoplecode_graph(reference: str, env: str = "HCM"):
    return peoplecode.graph(reference, env)


@router.get("/api/peoplesoft/peoplecode/{reference:path}")
def peoplesoft_peoplecode_program(reference: str, env: str = "HCM"):
    return uom.peoplecode_object(env, reference)


# ---------------------------------------------------------------------------
# Application Engine Explorer
# ---------------------------------------------------------------------------


@router.get("/api/peoplesoft/ae")
def peoplesoft_ae_list(env: str = "HCM", q: str = "", limit: int = 100):
    return ae.programs(env, q, limit)


@router.get("/api/peoplesoft/ae/{ae_applid}/sections")
def peoplesoft_ae_sections(ae_applid: str, env: str = "HCM"):
    return ae.sections(env, ae_applid)


@router.get("/api/peoplesoft/ae/{ae_applid}/steps")
def peoplesoft_ae_steps(ae_applid: str, env: str = "HCM", section: str = ""):
    return ae.steps(env, ae_applid, ae_section=section or None)


@router.get("/api/peoplesoft/ae/{ae_applid}/state-records")
def peoplesoft_ae_state_records(ae_applid: str, env: str = "HCM"):
    return ae.state_records(env, ae_applid)


@router.get("/api/peoplesoft/ae/{ae_applid}/process-definitions")
def peoplesoft_ae_process_definitions(ae_applid: str, env: str = "HCM"):
    return ae.process_definitions(env, ae_applid)


@router.get("/api/peoplesoft/ae/{ae_applid}/runtime")
def peoplesoft_ae_runtime(ae_applid: str, env: str = "HCM", limit: int = 20):
    return ae.runtime_instances(env, ae_applid, limit)


@router.get("/api/peoplesoft/ae/{ae_applid}/peoplecode")
def peoplesoft_ae_peoplecode(ae_applid: str, env: str = "HCM"):
    return ae.ae_peoplecode(env, ae_applid)


@router.get("/api/peoplesoft/ae/{ae_applid}/graph")
def peoplesoft_ae_graph(ae_applid: str, env: str = "HCM"):
    return ae.program_graph(env, ae_applid)


@router.get("/api/peoplesoft/ae/{ae_applid}")
def peoplesoft_ae_program(ae_applid: str, env: str = "HCM"):
    return uom.ae_object(env, ae_applid)


# ---------------------------------------------------------------------------
# Process Explorer (Process Scheduler / PSPROCESSDEFN)
# ---------------------------------------------------------------------------


@router.get("/api/peoplesoft/processes")
def peoplesoft_processes(env: str = "HCM", q: str = "", limit: int = 100):
    """List process scheduler process definitions."""
    limit = max(1, min(int(limit), 500))
    if not ptmetadata.has_table(env, "PSPROCESSDEFN"):
        return {"items": [], "warnings": [{"code": "psprocessdefn_unavailable",
                                           "message": "SYSADM.PSPROCESSDEFN not accessible"}]}
    try:
        available = psdb.table_columns(env, "PSPROCESSDEFN")
        candidates = ["PRCSTYPE", "PRCSNAME", "DESCR", "PRCSCATEGORY",
                      "JOBNAME", "SERVERNAMERUN", "PRIORITY", "LASTUPDDTTM"]
        selected = [c for c in candidates if c.lower() in available]
        if not selected or "prcsname" not in {c.lower() for c in selected}:
            return {"items": [], "warnings": []}

        predicates = ["upper(prcsname) like :pattern"]
        if "descr" in {c.lower() for c in selected}:
            predicates.append("upper(descr) like :pattern")

        rows = psdb.query(env, f"""
            SELECT {", ".join(selected)}
              FROM SYSADM.PSPROCESSDEFN
             WHERE {" OR ".join(predicates)}
             ORDER BY prcsname
             FETCH FIRST {limit} ROWS ONLY
        """, {"pattern": f"%{q.upper()}%"})
        return {"items": rows, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [{"code": "processes_failed", "message": str(exc)}]}


@router.get("/api/peoplesoft/search")
def peoplesoft_global_search(env: str = "HCM", q: str = "", limit: int = 20):
    if not q.strip():
        return []

    rows = []
    for row in ptmetadata.global_search(env, q, limit):
        links = {
            "admin": f"/admin/object/{row['type']}/{row['name']}"
        } if row.get("name") else {}
        graph_node = None

        if row.get("name"):
            graph_id = f"{row['type']}:{row['name']}"
            graph_node = graphdb.get_node(env, graph_id)
            if graph_node:
                links["graph"] = f"/api/graph/node/{graph_id}?env={env}"

        rows.append({
            **row,
            "_links": links,
            "_graph": graph_node,
        })

    return rows


@router.get("/api/peoplesoft/object/{object_type}/{object_name}")
def peoplesoft_object(object_type: str, object_name: str, env: str = "HCM"):
    return attach_graph_context(object_payload(env, object_type, object_name), env)


@router.get("/api/peoplesoft/portal-registry/{portal_objname}")
def peoplesoft_portal_registry_ref(portal_objname: str, env: str = "HCM"):
    portal_obj = uom.portal_registry_object(env, portal_objname)
    return attach_graph_context(uom.portal_registry_payload(portal_obj), env)


@router.get("/api/peoplesoft/portal-registry/{portal_objname}/security")
def peoplesoft_portal_registry_security(portal_objname: str, env: str = "HCM"):
    portal_row = psdb.portal_registry_ref(env, portal_objname)
    portal_name = (portal_row or {}).get("portal_name")
    permissions = [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.portal_registry_permissions(env, portal_objname, portal_name))
    ]
    access_paths = [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.portal_registry_access(env, portal_objname, portal_name))
    ]

    return {
        "portal": attach_links(portal_row, env) if portal_row else {"portal_objname": portal_objname.upper()},
        "counts": {
            "permissions": len(permissions),
            "access_paths": len(access_paths),
            "permissionlists": len({row.get("classid") for row in permissions if row.get("classid")}),
            "roles": len({row.get("rolename") for row in permissions + access_paths if row.get("rolename")}),
            "operators": len({row.get("roleuser") for row in access_paths if row.get("roleuser")}),
        },
        "permissions": permissions,
        "access_paths": access_paths,
        "_links": {
            "object": f"/admin/object/portal_registry/{portal_objname.upper()}",
            "graph": f"/api/peoplesoft/graph/portal_registry/{portal_objname.upper()}?env={env}",
        },
    }


@router.get("/api/peoplesoft/oprids")
def search_oprids(env: str = "HCM", q: str = ""):
    return psdb.search_oprids(env, q)

@router.get("/api/peoplesoft/oprids/{oprid}/roles")
def peoplesoft_oprid_roles(oprid: str, env: str = "HCM"):
    return psdb.oprid_roles(oprid, env, columns="summary")


@router.get("/api/peoplesoft/security/operators/{oprid}")
def peoplesoft_operator_security(oprid: str, env: str = "HCM"):
    operator = psdb.oprid(oprid, env)

    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    warnings = []
    roles = [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.oprid_roles(oprid, env, columns="summary"))
    ]

    try:
        permissionlists = [
            attach_links(row, env)
            for row in psdb.operator_permissionlists(env, oprid)
        ]
    except Exception as exc:
        warnings.append(str(exc))
        permissionlists = []

    try:
        menus = [
            attach_links(row, env)
            for row in psdb.operator_menus(env, oprid)
        ]
    except Exception as exc:
        warnings.append(str(exc))
        menus = []

    try:
        components = [
            attach_links(row, env)
            for row in psdb.operator_components(env, oprid)
        ]
    except Exception as exc:
        warnings.append(str(exc))
        components = []

    return {
        "operator": attach_links(operator, env),
        "counts": {
            "roles": len(roles),
            "permissionlists": len(permissionlists),
            "menus": len(menus),
            "components": len(components),
        },
        "roles": roles,
        "permissionlists": permissionlists,
        "menus": menus,
        "components": components,
        "warnings": warnings,
        "_links": {
            "graph": f"/api/peoplesoft/graph/operator/{oprid.upper()}?env={env}",
        },
    }


@router.get("/api/peoplesoft/security/operators/{oprid}/permissionlists")
def peoplesoft_operator_permissionlists(oprid: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.operator_permissionlists(env, oprid)
    ]


@router.get("/api/peoplesoft/security/operators/{oprid}/menus")
def peoplesoft_operator_menus(oprid: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.operator_menus(env, oprid)
    ]


@router.get("/api/peoplesoft/security/operators/{oprid}/components")
def peoplesoft_operator_components(oprid: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.operator_components(env, oprid)
    ]


@router.get("/api/peoplesoft/security/components/{component}/access")
def peoplesoft_component_access(component: str, env: str = "HCM"):
    warnings = []

    try:
        component_row = psdb.component(env, component)
    except Exception as exc:
        component_row = None
        warnings.append(str(exc))

    if not component_row:
        component_row = {
            "pnlgrpname": component.upper(),
            "metadata_status": "Component metadata unavailable",
        }

    try:
        access = [
            attach_links(row, env)
            for row in psdb.component_access(env, component)
        ]
    except Exception as exc:
        warnings.append(str(exc))
        access = []

    users = sorted({row["roleuser"] for row in access if row.get("roleuser")})
    roles = sorted({row["rolename"] for row in access if row.get("rolename")})
    permissionlists = sorted({row["classid"] for row in access if row.get("classid")})

    return {
        "component": attach_links(component_row, env),
        "counts": {
            "users": len(users),
            "roles": len(roles),
            "permissionlists": len(permissionlists),
            "access_paths": len(access),
        },
        "users": users,
        "roles": roles,
        "permissionlists": permissionlists,
        "access": access,
        "warnings": warnings,
        "_links": {
            "graph": f"/api/peoplesoft/graph/component/{component.upper()}?env={env}",
        },
    }


@router.get("/api/peoplesoft/security/explain")
def peoplesoft_security_explain(oprid: str, component: str, env: str = "HCM"):
    result = psdb.explain_operator_component_access(env, oprid, component)
    result["operator"] = attach_links(result["operator"], env) if result.get("operator") else None
    result["component_row"] = attach_links(result["component_row"], env)
    result["operator_roles"] = [attach_links(row, env) for row in result.get("operator_roles", [])]
    result["operator_permissionlists"] = [
        attach_links(row, env) for row in result.get("operator_permissionlists", [])
    ]
    result["component_permissionlists"] = [
        attach_links(row, env) for row in result.get("component_permissionlists", [])
    ]
    result["grant_paths"] = [attach_links(row, env) for row in result.get("grant_paths", [])]
    result["_links"] = {
        "operator": f"/admin/object/operator/{result['oprid']}",
        "component": f"/admin/object/component/{result['component']}",
        "graph": f"/api/peoplesoft/graph/operator/{result['oprid']}?env={env}",
    }
    return result


@router.get("/api/peoplesoft/security/explain-page")
def peoplesoft_security_explain_page(oprid: str, page: str, env: str = "HCM"):
    result = psdb.explain_operator_page_access(env, oprid, page)
    result["page_row"] = attach_links(result["page_row"], env)
    result["components"] = [attach_links(row, env) for row in result.get("components", [])]
    result["fields"] = [attach_links(row, env) for row in result.get("fields", [])]
    result["grant_paths"] = [attach_links(row, env) for row in result.get("grant_paths", [])]
    result["_links"] = {
        "operator": f"/admin/object/operator/{result['oprid']}",
        "page": f"/admin/object/page/{result['page']}",
    }
    return result


@router.get("/api/peoplesoft/security/explain-menu")
def peoplesoft_security_explain_menu(oprid: str, menu: str, env: str = "HCM"):
    result = psdb.explain_operator_menu_access(env, oprid, menu)
    result["grant_paths"] = [attach_links(row, env) for row in result.get("grant_paths", [])]
    result["_links"] = {
        "operator": f"/admin/object/operator/{result['oprid']}",
        "menu": f"/admin/object/menu/{result['menu']}",
    }
    return result


@router.get("/api/peoplesoft/security/explain-portal")
def peoplesoft_security_explain_portal(oprid: str, portal: str, env: str = "HCM"):
    result = psdb.explain_operator_portal_access(env, oprid, portal)
    result["operator"] = attach_links(result["operator"], env) if result.get("operator") else None
    result["portal_row"] = attach_links(result["portal_row"], env) if result.get("portal_row") else None
    result["operator_roles"] = [attach_links(row, env) for row in result.get("operator_roles", [])]
    result["operator_permissionlists"] = [
        attach_links(row, env) for row in result.get("operator_permissionlists", [])
    ]
    result["portal_permissions"] = [
        attach_links(row, env) for row in result.get("portal_permissions", [])
    ]
    result["grant_paths"] = [attach_links(row, env) for row in result.get("grant_paths", [])]
    result["_links"] = {
        "operator": f"/admin/object/operator/{result['oprid']}",
        "portal": f"/admin/object/portal_registry/{result['portal_objname']}",
    }
    return result


@router.get("/api/peoplesoft/security/compare-operators")
def peoplesoft_compare_operators(oprid1: str, oprid2: str, env: str = "HCM"):
    """Diff the security profiles of two operators: roles, permission lists, and component access."""
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return []

    roles1 = {str(r.get("rolename") or "").strip() for r in _safe(lambda: psdb.oprid_roles(oprid1, env, columns="summary"))}
    roles2 = {str(r.get("rolename") or "").strip() for r in _safe(lambda: psdb.oprid_roles(oprid2, env, columns="summary"))}
    pls1 = {str(r.get("classid") or "").strip() for r in _safe(lambda: psdb.operator_permissionlists(env, oprid1))}
    pls2 = {str(r.get("classid") or "").strip() for r in _safe(lambda: psdb.operator_permissionlists(env, oprid2))}
    comps1 = {str(r.get("pnlgrpname") or "").strip() for r in _safe(lambda: psdb.operator_components(env, oprid1))}
    comps2 = {str(r.get("pnlgrpname") or "").strip() for r in _safe(lambda: psdb.operator_components(env, oprid2))}

    return {
        "oprid1": oprid1.upper(),
        "oprid2": oprid2.upper(),
        "env": env.upper(),
        "roles": {
            "only_in_oprid1": sorted(roles1 - roles2),
            "only_in_oprid2": sorted(roles2 - roles1),
            "shared": sorted(roles1 & roles2),
            "counts": {"oprid1": len(roles1), "oprid2": len(roles2), "shared": len(roles1 & roles2)},
        },
        "permission_lists": {
            "only_in_oprid1": sorted(pls1 - pls2),
            "only_in_oprid2": sorted(pls2 - pls1),
            "shared": sorted(pls1 & pls2),
            "counts": {"oprid1": len(pls1), "oprid2": len(pls2), "shared": len(pls1 & pls2)},
        },
        "components": {
            "only_in_oprid1": sorted(comps1 - comps2),
            "only_in_oprid2": sorted(comps2 - comps1),
            "shared_count": len(comps1 & comps2),
            "counts": {"oprid1": len(comps1), "oprid2": len(comps2), "shared": len(comps1 & comps2)},
        },
        "_links": {
            "oprid1": f"/admin/object/operator/{oprid1.upper()}",
            "oprid2": f"/admin/object/operator/{oprid2.upper()}",
        },
    }


@router.get("/api/peoplesoft/sql_definitions")
def peoplesoft_sql_definitions(env: str = "HCM", q: str = "", sqltype: str = "", limit: int = 100):
    """Search SQL definitions with optional SQLTYPE filter (0=standalone, 1=AE, 2=PC, 6=trigger)."""
    st = int(sqltype) if sqltype.strip().lstrip("-").isdigit() else None
    rows = psdb.search_sql_definitions(env, q=q, sqltype=st, limit=limit)
    for row in rows:
        sid = row.get("sqlid")
        if sid:
            row.setdefault("_links", {})["admin"] = f"/admin/object/sql_definition/{sid}"
    return rows


@router.get("/api/peoplesoft/security/reports")
def peoplesoft_security_report(report: str = "empty_roles", env: str = "HCM", limit: int = 100):
    """Run a canned security audit report."""
    return psdb.security_report(env, report, limit=limit)


@router.get("/api/peoplesoft/roles")
def peoplesoft_roles(env: str = "HCM", q: str = "", limit: int = 100):
    return [attach_links(row, env) for row in psdb.roles(env, q, limit)]


@router.get("/api/peoplesoft/roles/{rolename}")
def peoplesoft_role(rolename: str, env: str = "HCM"):
    role = psdb.role(env, rolename)

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    result = attach_links(role, env)
    result["permissionlist_count"] = len(psdb.role_permissionlists(env, rolename))
    return result


@router.get("/api/peoplesoft/roles/{rolename}/permissionlists")
def peoplesoft_role_permissionlists(rolename: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.role_permissionlists(env, rolename)
    ]


@router.get("/api/peoplesoft/permissionlists")
def peoplesoft_permissionlists(env: str = "HCM", q: str = "", limit: int = 100):
    return [
        attach_links(row, env)
        for row in psdb.permissionlists(env, q, limit)
    ]


@router.get("/api/peoplesoft/permissionlists/{classid}")
def peoplesoft_permissionlist(classid: str, env: str = "HCM"):
    permissionlist = psdb.permissionlist(env, classid)

    if not permissionlist:
        raise HTTPException(status_code=404, detail="Permission list not found")

    result = attach_links(permissionlist, env)
    result["menu_count"] = len(psdb.permissionlist_menus(env, classid))
    result["component_count"] = len(psdb.permissionlist_components(env, classid))
    return result


@router.get("/api/peoplesoft/permissionlists/{classid}/menus")
def peoplesoft_permissionlist_menus(classid: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.permissionlist_menus(env, classid)
    ]


@router.get("/api/peoplesoft/permissionlists/{classid}/components")
def peoplesoft_permissionlist_components(classid: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.permissionlist_components(env, classid)
    ]


@router.get("/api/peoplesoft/components")
def peoplesoft_components(env: str = "HCM", q: str = "", limit: int = 100):
    return [
        attach_links(row, env)
        for row in psdb.components(env, q, limit)
    ]


@router.get("/api/peoplesoft/components/{component}")
def peoplesoft_component(component: str, env: str = "HCM"):
    result = psdb.component(env, component)

    if not result:
        raise HTTPException(status_code=404, detail="Component not found")

    linked = attach_links(result, env)
    linked["page_count"] = len(psdb.component_pages(env, component))
    linked["permissionlist_count"] = len(psdb.component_permissionlists(env, component))
    return linked


@router.get("/api/peoplesoft/components/{component}/pages")
def peoplesoft_component_pages(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.component_pages(env, component)
    ]


@router.get("/api/peoplesoft/components/{component}/permissionlists")
def peoplesoft_component_permissionlists(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in psdb.component_permissionlists(env, component)
    ]


@router.get("/api/peoplesoft/components/{component}/menu-placements")
def peoplesoft_component_menu_placements(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_menu_placements(env, component))
    ]


@router.get("/api/peoplesoft/components/{component}/records")
def peoplesoft_component_records(component: str, env: str = "HCM"):
    component_row = safe_rows(lambda: [psdb.component(env, component)])
    component_row = component_row[0] if component_row else None

    records = []
    if component_row:
        for key in ("searchrecname", "addsearchrecname"):
            record = component_row.get(key)
            if record:
                records.append(attach_links({"recname": record, "usage": key}, env))

    records.extend(
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_records_used_by_pages(env, component))
    )

    return records


@router.get("/api/peoplesoft/components/{component}/portal-refs")
def peoplesoft_component_portal_refs(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_portal_refs(env, component))
    ]


@router.get("/api/peoplesoft/components/{component}/related-content")
def peoplesoft_component_related_content(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_related_content(env, component))
    ]


@router.get("/api/peoplesoft/components/{component}/event-mapping")
def peoplesoft_component_event_mapping(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_event_mapping(env, component))
    ]


@router.get("/api/peoplesoft/components/{component}/drop-zones")
def peoplesoft_component_drop_zones(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_drop_zones(env, component))
    ]


@router.get("/api/peoplesoft/pages")
def peoplesoft_pages(env: str = "HCM", q: str = "", limit: int = 100):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.pages(env, q, limit))
    ]


@router.get("/api/peoplesoft/pages/{page_name}")
def peoplesoft_page(page_name: str, env: str = "HCM"):
    result = safe_rows(lambda: [psdb.page(env, page_name)])
    result = result[0] if result else None

    if not result:
        return attach_links({
            "pnlname": page_name.upper(),
            "metadata_status": "Page metadata unavailable",
        }, env)

    linked = attach_links(result, env)
    linked["component_count"] = len(safe_rows(lambda: psdb.page_components(env, page_name)))
    return linked


@router.get("/api/peoplesoft/pages/{page_name}/components")
def peoplesoft_page_components(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_components(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/records")
def peoplesoft_page_records(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_records(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/fields")
def peoplesoft_page_fields(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_fields(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/scroll-structure")
def peoplesoft_page_scroll_structure(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_scroll_structure(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/grids")
def peoplesoft_page_grids(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_grids(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/subpages")
def peoplesoft_page_subpages(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_subpages(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/peoplecode")
def peoplesoft_page_peoplecode(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_peoplecode_metadata(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/event-mapping")
def peoplesoft_page_event_mapping(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_event_mapping(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/related-content")
def peoplesoft_page_related_content(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_related_content(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/drop-zones")
def peoplesoft_page_drop_zones(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_drop_zones(env, page_name))
    ]


@router.get("/api/peoplesoft/pages/{page_name}/transfers")
def peoplesoft_page_transfers(page_name: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.page_transfers(env, page_name))
    ]


@router.get("/api/peoplesoft/graph/{object_type}/{object_name}")
def peoplesoft_graph(object_type: str, object_name: str, env: str = "HCM"):
    object_type = object_type.lower()
    object_name = object_name.upper()

    persistent_graph = graphdb_response(env, object_type, object_name)
    if persistent_graph:
        return persistent_graph

    if object_type == "peoplecode":
        return peoplecode.graph(object_name, env)

    if object_type == "field":
        return uom.field_object(env, object_name)["_graph"]

    if object_type == "tree":
        tree_graph = uom.tree_object(env, object_name).get("_graph", {})
        return {
            "root": f"tree:{object_name.upper()}",
            "nodes": tree_graph.get("nodes", []),
            "edges": tree_graph.get("edges", []),
        }

    nodes = {}
    edges = []

    add_node(nodes, node(object_type, object_name))

    if object_type == "operator":
        for row in psdb.oprid_roles(object_name, env, columns="summary"):
            role = row["rolename"]
            add_node(nodes, node("role", role, data=row))
            edges.append(edge("operator", object_name, "role", role, "has_role"))

        for row in psdb.operator_permissionlists(env, object_name):
            classid = row["classid"]
            add_node(nodes, node("permissionlist", classid, data=row))
            edges.append(edge("role", row["rolename"], "permissionlist", classid, "contains_permissionlist"))

        for row in psdb.operator_components(env, object_name):
            component = row["pnlgrpname"]
            add_node(nodes, node("component", component, data=row))
            edges.append(edge("permissionlist", row["classid"], "component", component, "grants_component"))

    elif object_type == "role":
        for row in psdb.role_users(env, object_name):
            operator = row["roleuser"]
            add_node(nodes, node("operator", operator, data=row))
            edges.append(edge("operator", operator, "role", object_name, "has_role"))

        for row in psdb.role_permissionlists(env, object_name):
            classid = row["classid"]
            add_node(nodes, node("permissionlist", classid, data=row))
            edges.append(edge("role", object_name, "permissionlist", classid, "contains_permissionlist"))

    elif object_type == "permissionlist":
        for row in psdb.permissionlist_roles(env, object_name):
            role = row["rolename"]
            add_node(nodes, node("role", role, data=row))
            edges.append(edge("role", role, "permissionlist", object_name, "contains_permissionlist"))

        for row in psdb.permissionlist_components(env, object_name):
            component = row["pnlgrpname"]
            add_node(nodes, node("component", component, data=row))
            edges.append(edge("permissionlist", object_name, "component", component, "grants_component"))

    elif object_type == "component":
        for row in psdb.component_permissionlists(env, object_name):
            classid = row["classid"]
            add_node(nodes, node("permissionlist", classid, data=row))
            edges.append(edge("permissionlist", classid, "component", object_name, "grants_component"))

        for row in psdb.component_pages(env, object_name):
            page = row["pnlname"]
            add_node(nodes, node("page", page, data=row))
            edges.append(edge("component", object_name, "page", page, "contains_page"))

        component = psdb.component(env, object_name) or {}
        for key, relationship in (
            ("searchrecname", "uses_search_record"),
            ("addsearchrecname", "uses_add_search_record"),
        ):
            record = component.get(key)
            if record:
                add_node(nodes, node("record", record, data={"source": key}))
                edges.append(edge("component", object_name, "record", record, relationship))

    elif object_type == "page":
        for row in safe_rows(lambda: psdb.page_components(env, object_name)):
            component = row["pnlgrpname"]
            add_node(nodes, node("component", component, data=row))
            edges.append(edge("component", component, "page", object_name, "contains_page"))

        for row in safe_rows(lambda: psdb.page_records(env, object_name)):
            record = row["recname"]
            add_node(nodes, node("record", record, data=row))
            edges.append(edge("page", object_name, "record", record, "uses_record"))

        for row in safe_rows(lambda: psdb.page_fields(env, object_name)):
            record = row.get("recname")
            field = row.get("fieldname")

            if record and field:
                field_name = f"{record}.{field}"
                add_node(nodes, node("field", field_name, data=row))
                edges.append(edge("page", object_name, "field", field_name, "contains_field"))

        for row in safe_rows(lambda: psdb.page_subpages(env, object_name)):
            page = row.get("pnlname")

            if page:
                add_node(nodes, node("page", page, data=row))
                edges.append(edge("page", object_name, "page", page, "contains_subpage"))

        permissionlists = set()

        for row in safe_rows(lambda: psdb.page_components(env, object_name)):
            component = row.get("pnlgrpname")

            if not component:
                continue

            for access_row in safe_rows(lambda component=component: psdb.component_permissionlists(env, component)):
                classid = access_row.get("classid")

                if classid and classid not in permissionlists:
                    permissionlists.add(classid)
                    add_node(nodes, node("permissionlist", classid, data=access_row))
                    edges.append(edge("permissionlist", classid, "component", component, "grants_component"))

    elif object_type in {"portal", "portal_registry", "content_reference"}:
        portal_graph = uom.portal_registry_object(env, object_name).get("_graph", {})
        return {
            "root": f"portal_registry:{object_name.upper()}",
            "nodes": portal_graph.get("nodes", []),
            "edges": portal_graph.get("edges", []),
        }

    elif object_type == "record":
        for row in psdb.record_children(env, object_name):
            child = row["recname"]
            add_node(nodes, node("record", child, data=row))
            edges.append(edge("record", object_name, "record", child, "parent_of"))

        for row in psdb.record_components(env, object_name):
            component = row["pnlgrpname"]
            add_node(nodes, node("component", component, data=row))
            edges.append(edge("component", component, "record", object_name, "uses_record"))

        for row in psdb.record_pages(env, object_name):
            page = row["pnlname"]
            add_node(nodes, node("page", page, data=row))
            edges.append(edge("page", page, "record", object_name, "uses_record"))

    else:
        raise HTTPException(status_code=400, detail="Unsupported graph object type")

    return graph_response(object_type, object_name, nodes, edges)


@router.get("/api/peoplesoft/debug/roleuser-count")
def debug_roleuser_count(env: str = "HCM"):
    sql = """
        SELECT COUNT(*) AS CNT
          FROM SYSADM.PSROLEUSER
    """

    return psdb.query(env, sql)

@router.get("/api/peoplesoft/debug/connection")
def debug_connection(env: str = "HCM"):
    sql = """
        SELECT
            sys_context('USERENV','DB_NAME') db_name,
            sys_context('USERENV','CON_NAME') con_name,
            user,
            sys_context('USERENV','CURRENT_SCHEMA') current_schema
        FROM dual
    """
    return psdb.query(env, sql)
