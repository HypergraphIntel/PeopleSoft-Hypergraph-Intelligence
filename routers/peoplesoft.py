from fastapi import APIRouter, HTTPException
from connectors import ae, graphdb, graphshape, peoplecode, peoplesoft, psdb, ptmetadata, uom

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
        record = linked.get("searchrecname") or linked.get("addsrchrecname")
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


def uom_graph_response(env, object_type, object_name):
    """Return the compact UOM graph preview for a canonical object.

    Graph Explorer expects a list-shaped graph response. UOM objects already
    own the compact preview used by Object Explorer, so this helper keeps the
    route-specific graph API aligned with the canonical object model.
    """
    canonical = uom.canonical_object(env, object_type, object_name)
    graph = canonical.get("_graph") or {}
    return graphshape.annotate_graph({
        "root": canonical.get("id") or f"{canonical.get('type', object_type)}:{canonical.get('name', object_name)}",
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
    }, "uom", "compact_uom", "compact object preview")


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

    return graphshape.annotate_graph({
        "root": root,
        "nodes": list(nodes.values()),
        "edges": edges,
    }, "knowledge_graph", "knowledge_graph", "persisted graph neighborhood")


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

    # Build a lookup from node id → edge relationships for richer display
    edge_by_target: dict[str, list[str]] = {}
    edge_by_source: dict[str, list[str]] = {}
    for edge in graph.get("edges", []):
        rel = edge.get("type") or edge.get("relationship") or "neighbor"
        tgt = edge.get("target", "")
        src = edge.get("source", "")
        edge_by_target.setdefault(tgt, []).append(rel)
        edge_by_source.setdefault(src, []).append(rel)

    items = []
    for node_row in graph.get("nodes", []):
        nid = node_row.get("id", "")
        # Prefer the relationship that points *to* this neighbor (outgoing from root)
        rels = edge_by_target.get(nid) or edge_by_source.get(nid) or ["neighbor"]
        primary_rel = rels[0]
        items.append({
            "relationship": primary_rel,
            "type": node_row.get("type"),
            "name": node_row.get("name"),
            "id": nid,
            "_links": {"admin": node_row.get("canonical_url")},
        })

    payload.setdefault("sections", []).append(section("Knowledge Graph Neighbors", items, {
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
    }))
    payload.setdefault("_links", {})["knowledge_graph"] = f"/api/graph/neighbors/{node_id}?env={env}"

    # ── Type-specific cross-reference sections ───────────────────────────
    obj_type = payload.get("type")
    if obj_type == "record":
        _attach_record_rw_xref(payload, env, node_id)
        _attach_record_components_xref(payload, env, node_id)
        _attach_inbound_xref(payload, env, node_id,
                             src_type="page", edge_type="USES",
                             section_name="Pages Using This Record",
                             note="Pages that use this record as their data source (from Knowledge Graph)")
        _attach_inbound_xref(payload, env, node_id,
                             src_type="project", edge_type="DEPLOYS",
                             section_name="Projects Deploying This Record",
                             note="Projects that include this record in a deployment (from Knowledge Graph)")
        _attach_inbound_xref(payload, env, node_id,
                             src_type="query", edge_type="USES",
                             section_name="Queries Using This Record",
                             note="PS Query definitions that include this record (from Knowledge Graph)")
        _attach_inbound_xref(payload, env, node_id,
                             src_type="ptf_test", edge_type="USES",
                             section_name="PTF Tests Covering This Record",
                             note="PTF automated tests that reference this record (from Knowledge Graph)")
    elif obj_type in ("application_engine", "sql_definition", "peoplecode"):
        _attach_outbound_rw_xref(payload, env, node_id)
    if obj_type == "application_engine":
        _attach_ae_schedulers(payload, env, node_id)
    if obj_type == "page":
        _attach_inbound_xref(payload, env, node_id,
                             src_type="project", edge_type="DEPLOYS",
                             section_name="Projects Deploying This Page",
                             note="Projects that include this page in a deployment (from Knowledge Graph)")
    if obj_type == "component":
        _attach_inbound_xref(payload, env, node_id,
                             src_type="project", edge_type="DEPLOYS",
                             section_name="Projects Deploying This Component",
                             note="Projects that include this component in a deployment (from Knowledge Graph)")

    return payload


def _attach_record_rw_xref(payload, env: str, node_id: str) -> None:
    """Add a 'READS / WRITES' cross-reference section to a record object.

    Queries the persisted Knowledge Graph for all READS and WRITES edges that
    point to this record and groups them by source object type.  Silently skips
    if the graph has not been built or has no matching edges.
    """
    # Already present — guard against double-add
    if any(s.get("name") == "READS / WRITES" for s in payload.get("sections", [])):
        return
    try:
        rw_graph = graphdb.neighbors(env, node_id, direction="in", depth=1,
                                     edge_types=["READS", "WRITES"])
    except Exception:
        return

    rw_edges = rw_graph.get("edges", [])
    rw_nodes_by_id = {n["id"]: n for n in rw_graph.get("nodes", [])}

    if not rw_edges:
        return

    items = []
    seen = set()
    for edge in rw_edges:
        src_id = edge.get("source", "")
        if src_id in seen:
            continue
        seen.add(src_id)
        src_node = rw_nodes_by_id.get(src_id, {})
        rel = edge.get("type") or edge.get("relationship") or "READS"
        items.append({
            "relationship": rel,
            "type": src_node.get("type", src_id.split(":")[0] if ":" in src_id else ""),
            "name": src_node.get("name", src_id),
            "id": src_id,
            "_links": {"admin": src_node.get("canonical_url") or f"/admin/object/{src_node.get('type','')}/{src_node.get('name','')}"},
        })

    # Sort: WRITES first (higher impact), then READS; within each group by type then name
    items.sort(key=lambda x: (0 if x["relationship"] == "WRITES" else 1, x["type"], x["name"]))

    reads_count = sum(1 for it in items if it["relationship"] == "READS")
    writes_count = sum(1 for it in items if it["relationship"] == "WRITES")

    payload.setdefault("sections", []).append(section(
        "READS / WRITES",
        items,
        {
            "count": len(items),
            "reads": reads_count,
            "writes": writes_count,
            "note": "Objects that read or write this record (from Knowledge Graph)",
        },
    ))


def _attach_outbound_rw_xref(payload, env: str, node_id: str) -> None:
    """Add a 'Records Read / Written' section to AE or SQL definition objects.

    Queries outbound READS/WRITES edges from this object to records so engineers
    can see exactly which tables a program touches without reading its SQL.
    Silently skips if the graph has not been built or has no matching edges.
    """
    section_name = "Records Read / Written"
    if any(s.get("name") == section_name for s in payload.get("sections", [])):
        return
    try:
        rw_graph = graphdb.neighbors(env, node_id, direction="out", depth=1,
                                     edge_types=["READS", "WRITES"])
    except Exception:
        return

    rw_edges = rw_graph.get("edges", [])
    rw_nodes_by_id = {n["id"]: n for n in rw_graph.get("nodes", [])}

    if not rw_edges:
        return

    items = []
    seen = set()
    for edge in rw_edges:
        tgt_id = edge.get("target", "")
        if tgt_id in seen:
            continue
        seen.add(tgt_id)
        tgt_node = rw_nodes_by_id.get(tgt_id, {})
        rel = edge.get("type") or edge.get("relationship") or "READS"
        items.append({
            "relationship": rel,
            "type": tgt_node.get("type", tgt_id.split(":")[0] if ":" in tgt_id else ""),
            "name": tgt_node.get("name", tgt_id),
            "id": tgt_id,
            "_links": {"admin": tgt_node.get("canonical_url") or ""},
        })

    # Sort: WRITES first (higher impact), then READS; within each group alphabetically
    items.sort(key=lambda x: (0 if x["relationship"] == "WRITES" else 1, x["name"]))

    reads_count = sum(1 for it in items if it["relationship"] == "READS")
    writes_count = sum(1 for it in items if it["relationship"] == "WRITES")

    payload.setdefault("sections", []).append(section(
        section_name,
        items,
        {
            "count": len(items),
            "reads": reads_count,
            "writes": writes_count,
            "note": "Records read or written by this object (from Knowledge Graph)",
        },
    ))


def _attach_ae_schedulers(payload, env: str, node_id: str) -> None:
    """Add a 'Process Definitions' cross-reference section to AE objects.

    Queries inbound WRAPS edges to find Process Scheduler definitions that
    wrap / invoke this Application Engine.  Silently skips if none exist in
    the current Knowledge Graph build.
    """
    section_name = "Invoked By (Process Definitions)"
    if any(s.get("name") == section_name for s in payload.get("sections", [])):
        return
    try:
        wrap_graph = graphdb.neighbors(env, node_id, direction="in", depth=1,
                                       edge_types=["WRAPS"])
    except Exception:
        return

    wrap_nodes_by_id = {n["id"]: n for n in wrap_graph.get("nodes", [])}
    wrap_edges = wrap_graph.get("edges", [])

    if not wrap_edges:
        return

    items = []
    seen = set()
    for edge in wrap_edges:
        src_id = edge.get("source", "")
        if src_id in seen:
            continue
        seen.add(src_id)
        src_node = wrap_nodes_by_id.get(src_id, {})
        # prcs_defn node name is "PTYPE~PNAME"; display the process name cleanly
        raw_name = src_node.get("name", src_id)
        display_name = raw_name.split("~", 1)[-1] if "~" in raw_name else raw_name
        prcs_type = raw_name.split("~", 1)[0] if "~" in raw_name else ""
        items.append({
            "relationship": "WRAPS",
            "type": "prcs_defn",
            "name": display_name,
            "prcs_type": prcs_type,
            "id": src_id,
            "_links": {"admin": src_node.get("canonical_url") or ""},
        })

    items.sort(key=lambda x: x["name"])

    payload.setdefault("sections", []).append(section(
        section_name,
        items,
        {
            "count": len(items),
            "note": "Process Scheduler definitions that invoke this Application Engine",
        },
    ))


def _attach_record_components_xref(payload, env: str, node_id: str) -> None:
    """Add a 'Components Using This Record' section to record objects.

    Queries inbound USES edges from component nodes to surface which components
    reference this record (via search record, add search record, or page usage).
    Silently skips if no component USES edges exist in the current KG build.
    """
    section_name = "Components Using This Record"
    if any(s.get("name") == section_name for s in payload.get("sections", [])):
        return
    try:
        use_graph = graphdb.neighbors(env, node_id, direction="in", depth=1,
                                      edge_types=["USES"])
    except Exception:
        return

    use_edges = use_graph.get("edges", [])
    use_nodes_by_id = {n["id"]: n for n in use_graph.get("nodes", [])}

    # Filter to only component-type sources
    comp_items = []
    seen = set()
    for edge in use_edges:
        src_id = edge.get("source", "")
        if src_id in seen or not src_id.startswith("component:"):
            continue
        seen.add(src_id)
        src_node = use_nodes_by_id.get(src_id, {})
        comp_items.append({
            "relationship": "USES",
            "type": "component",
            "name": src_node.get("name", src_id.split(":", 1)[-1]),
            "id": src_id,
            "_links": {"admin": src_node.get("canonical_url") or ""},
        })

    if not comp_items:
        return

    comp_items.sort(key=lambda x: x["name"])

    payload.setdefault("sections", []).append(section(
        section_name,
        comp_items,
        {
            "count": len(comp_items),
            "note": "Components that use this record as a search or data record (from Knowledge Graph)",
        },
    ))


def _attach_inbound_xref(payload, env: str, node_id: str,
                          src_type: str, edge_type: str,
                          section_name: str, note: str = "") -> None:
    """Generic inbound cross-reference section builder.

    Queries the KG for all edges of ``edge_type`` pointing *to* ``node_id``
    whose source type matches ``src_type``, then appends a section.
    Silently skips if no matching edges exist or on any error.
    """
    if any(s.get("name") == section_name for s in payload.get("sections", [])):
        return
    try:
        xgraph = graphdb.neighbors(env, node_id, direction="in", depth=1,
                                   edge_types=[edge_type])
    except Exception:
        return

    xnodes_by_id = {n["id"]: n for n in xgraph.get("nodes", [])}
    prefix = f"{src_type}:"
    items = []
    seen = set()
    for edge in xgraph.get("edges", []):
        src_id = edge.get("source", "")
        if src_id in seen or not src_id.startswith(prefix):
            continue
        seen.add(src_id)
        src_node = xnodes_by_id.get(src_id, {})
        items.append({
            "relationship": edge_type,
            "type": src_type,
            "name": src_node.get("name", src_id.split(":", 1)[-1]),
            "id": src_id,
            "_links": {"admin": src_node.get("canonical_url") or ""},
        })

    if not items:
        return

    items.sort(key=lambda x: x["name"])
    payload.setdefault("sections", []).append(section(
        section_name,
        items,
        {"count": len(items), "note": note},
    ))


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
        "component_interface": "ci",
        "ci": "ci",
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

    if object_type == "ci":
        ci_obj = uom.ci_object(env, object_name)
        if ci_obj.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Component Interface not found")
        return attach_graph_context(uom.ci_payload(ci_obj), env)

    if object_type == "application_package":
        return uom.app_package_payload(env, object_name)

    if object_type == "menu":
        return attach_graph_context(uom.menu_payload(env, object_name), env)

    if object_type == "message_catalog":
        return uom.message_catalog_payload(env, object_name)

    if object_type == "approval":
        return uom.approval_payload(env, object_name)

    if object_type == "xml_publisher_report":
        return uom.xpub_report_payload(env, object_name)

    if object_type == "nav_collection":
        return uom.nav_collection_payload(env, object_name)

    if object_type == "event_mapping":
        return uom.event_mapping_payload(env, object_name)

    if object_type == "related_content":
        return uom.related_content_payload(env, object_name)

    if object_type == "search_definition":
        return uom.search_definition_payload(env, object_name)

    if object_type == "search_category":
        return uom.search_category_payload(env, object_name)

    if object_type == "drop_zone":
        return uom.drop_zone_payload(env, object_name)

    if object_type == "pivot_grid":
        return uom.pivot_grid_payload(env, object_name)

    if object_type == "connected_query":
        return uom.connected_query_payload(env, object_name)

    if object_type == "prcs_defn":
        return uom.process_defn_payload(env, object_name)
    if object_type == "file_layout":
        return uom.file_layout_payload(env, object_name)
    if object_type == "xlat_field":
        return uom.xlat_field_payload(env, object_name)
    if object_type == "project":
        return uom.project_payload(env, object_name)
    if object_type == "message":
        return uom.ib_message_payload(env, object_name)
    if object_type == "ib_application":
        return uom.object_payload(uom.ib_application_object(env, object_name))
    if object_type == "app_class":
        return uom.object_payload(uom.app_class_object(env, object_name))
    if object_type == "content_service":
        return uom.object_payload(uom.content_service_object(env, object_name))
    if object_type == "ptf_test":
        return uom.object_payload(uom.ptf_test_object(env, object_name))
    if object_type == "ads_definition":
        return uom.object_payload(uom.ads_definition_object(env, object_name))
    if object_type == "ib_service_group":
        return uom.object_payload(uom.ib_service_group_object(env, object_name))
    if object_type == "url_definition":
        return uom.object_payload(uom.url_definition_object(env, object_name))
    if object_type == "chatbot_skill":
        return uom.object_payload(uom.chatbot_skill_object(env, object_name))
    if object_type == "ib_routing":
        return uom.object_payload(uom.ib_routing_object(env, object_name))
    if object_type == "style_sheet":
        return uom.object_payload(uom.style_sheet_object(env, object_name))
    if object_type == "archive_object":
        return uom.object_payload(uom.archive_object_object(env, object_name))
    if object_type == "timezone":
        return uom.object_payload(uom.timezone_object(env, object_name))
    if object_type == "locale":
        return uom.object_payload(uom.locale_object(env, object_name))
    if object_type == "pm_metric":
        return uom.object_payload(uom.pm_metric_object(env, object_name))
    if object_type == "pm_transaction":
        return uom.object_payload(uom.pm_transaction_object(env, object_name))
    if object_type == "pm_event":
        return uom.object_payload(uom.pm_event_object(env, object_name))
    if object_type == "ib_operation":
        return uom.object_payload(uom.ib_operation_object(env, object_name))

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


@router.get("/api/peoplesoft/peoplecode/source-search")
def peoplesoft_peoplecode_source_search(q: str, env: str = "HCM", limit: int = 100):
    """Search PeopleCode source text (PSPCMTXT.PCTEXT) for a literal string."""
    if not q.strip():
        return {"items": [], "warnings": []}
    return peoplecode.source_search(env, q.strip(), limit=limit)


@router.get("/api/peoplesoft/peoplecode")
def peoplesoft_peoplecode(env: str = "HCM", q: str = "", limit: int = 100, offset: int = 0):
    return peoplecode.programs(env, q, limit=limit, offset=offset)


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


@router.get("/api/peoplesoft/portal/portals")
def portal_portals(env: str = "HCM"):
    """List all portals with counts and root folder."""
    return psdb.portal_registry_portals(env)


@router.get("/api/peoplesoft/portal/folders")
def portal_folder_children(
    portal_name: str = "EMPLOYEE",
    parent: str = "PORTAL_ROOT_OBJECT",
    folders_only: bool = False,
    env: str = "HCM",
):
    """Return immediate children of a portal folder — used for lazy tree navigation."""
    rows = safe_rows(lambda: psdb.portal_registry_folder_children(env, portal_name, parent, include_crefs=not folders_only))
    return [
        {
            **r,
            "has_children": bool(safe_rows(lambda rr=r: psdb.portal_registry_folder_children(env, portal_name, rr["portal_objname"], include_crefs=False)))
            if r.get("portal_reftype") == "F" else False,
            "_links": {"admin": f"/admin/portal?portal={r.get('portal_objname', '')}"},
        }
        for r in rows
    ]


@router.get("/api/peoplesoft/portal/breadcrumbs/{portal_objname}")
def portal_breadcrumbs_fast(portal_objname: str, portal_name: str = "EMPLOYEE", env: str = "HCM"):
    """Fast breadcrumb chain using Oracle CONNECT BY (single query)."""
    return psdb.portal_registry_breadcrumbs_fast(env, portal_objname, portal_name)


@router.get("/api/peoplesoft/portal/analysis")
def portal_analysis(portal_name: str = "EMPLOYEE", env: str = "HCM"):
    """Structural analysis: orphans, empty folders, top-referenced components."""
    return psdb.portal_registry_analysis(env, portal_name)


@router.get("/api/peoplesoft/portal/subtree")
def portal_subtree(
    portal_name: str = "EMPLOYEE",
    parent: str = "",
    max_depth: int = 6,
    max_rows: int = 500,
    env: str = "HCM",
):
    """Full descendant subtree of a portal folder (CONNECT BY, ordered, depth-annotated)."""
    rows = psdb.portal_registry_subtree(env, portal_name, parent,
                                        max_depth=max_depth, max_rows=max_rows)
    return {"items": rows, "count": len(rows)}


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


@router.get("/api/peoplesoft/queries")
def peoplesoft_queries(env: str = "HCM", q: str = "", folder: str = "", limit: int = 100):
    """Search public PS Queries (OPRID=' ') by name or description."""
    rows = psdb.search_queries(env, q=q, folder=folder or None, limit=limit)
    for row in rows:
        name = row.get("qryname")
        if name:
            row.setdefault("_links", {})["admin"] = f"/admin/object/query/{name}"
    return rows


@router.get("/api/peoplesoft/query-folders")
def peoplesoft_query_folders(env: str = "HCM"):
    """Return distinct query folder names for public queries."""
    return psdb.query_folders(env)


@router.get("/api/peoplesoft/trees")
def peoplesoft_trees(env: str = "HCM", q: str = "", setid: str = "", limit: int = 100):
    """Search PSTREEDEFN tree definitions."""
    rows = psdb.search_trees(env, q=q, setid=setid or None, limit=limit)
    for row in rows:
        name = row.get("treename")
        if name:
            row.setdefault("_links", {})["admin"] = f"/admin/object/tree/{name}"
    return rows


@router.get("/api/peoplesoft/cis")
def peoplesoft_cis(env: str = "HCM", q: str = "", limit: int = 100):
    """Search PSBCDEFN component interfaces."""
    rows = psdb.search_cis(env, q=q, limit=limit)
    for row in rows:
        name = row.get("bcname")
        if name:
            row.setdefault("_links", {})["admin"] = f"/admin/object/ci/{name}"
    return rows


@router.get("/api/peoplesoft/approvals")
def peoplesoft_approvals(env: str = "HCM", q: str = "", status: str = "", limit: int = 100):
    """Search Approval Workflow Engine transaction definitions (PS_EOAW_TXN)."""
    result = psdb.search_approvals(env, q=q, status=status or None, limit=limit)
    for item in result.get("items", []):
        aid = item.get("eoawprcs_id")
        if aid:
            item.setdefault("_links", {})["admin"] = f"/admin/object/approval/{aid}"
    return result


@router.get("/api/peoplesoft/messages")
def peoplesoft_messages(env: str = "HCM", q: str = "", set_nbr: str = "",
                        severity: str = "", limit: int = 100):
    """Search Message Catalog (PSMSGCATDEFN) by text or message set number."""
    sn = int(set_nbr) if set_nbr.strip().isdigit() else None
    sv = int(severity) if severity.strip().isdigit() else None
    result = psdb.search_messages(env, q=q, set_nbr=sn, severity=sv, limit=limit)
    for item in result.get("items", []):
        name = item.get("name")
        if name:
            item.setdefault("_links", {})["admin"] = f"/admin/object/message_catalog/{name}"
    return result


@router.get("/api/peoplesoft/message-sets")
def peoplesoft_message_sets(env: str = "HCM"):
    """Return list of message sets with descriptions and message counts."""
    return psdb.message_sets(env)


@router.get("/api/peoplesoft/xpub/reports")
def peoplesoft_xpub_reports(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_xpub_reports(env, q=q, limit=limit)


@router.get("/api/peoplesoft/xpub/datasources")
def peoplesoft_xpub_datasources(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_xpub_datasources(env, q=q, limit=limit)


@router.get("/api/peoplesoft/nav-collections")
def peoplesoft_nav_collections(env: str = "HCM", q: str = "", portal: str = "EMPLOYEE", limit: int = 100):
    return psdb.search_nav_collections(env, q=q, portal=portal or "EMPLOYEE", limit=limit)


@router.get("/api/peoplesoft/event-mappings")
def peoplesoft_event_mappings(env: str = "HCM", q: str = "", status: str = "", limit: int = 100):
    return psdb.search_event_mappings(env, q=q, status=status or None, limit=limit)


@router.get("/api/peoplesoft/related-content")
def peoplesoft_related_content(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_related_content(env, q=q, limit=limit)


@router.get("/api/peoplesoft/search-definitions")
def peoplesoft_search_definitions(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_search_definitions(env, q=q, limit=limit)


@router.get("/api/peoplesoft/search-categories")
def peoplesoft_search_categories(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_search_categories(env, q=q, limit=limit)


@router.get("/api/peoplesoft/drop-zones")
def peoplesoft_drop_zones_list(env: str = "HCM", q: str = "", limit: int = 100):
    return psdb.search_drop_zones(env, q=q, limit=limit)


@router.get("/api/peoplesoft/pivot-grids")
def peoplesoft_pivot_grids(env: str = "HCM", q: str = "", limit: int = 100):
    """Search PivotGrid definitions (PSPGCORE)."""
    return psdb.search_pivot_grids(env, q=q, limit=limit)


@router.get("/api/peoplesoft/connected-queries")
def peoplesoft_connected_queries(env: str = "HCM", q: str = "", limit: int = 100):
    """Search Connected Query definitions (PSCONQRSDEFN)."""
    return psdb.search_connected_queries(env, q=q, limit=limit)


@router.get("/api/peoplesoft/process-definitions")
def peoplesoft_process_definitions(env: str = "HCM", q: str = "", prcstype: str = "", limit: int = 200):
    """Search Process Scheduler definitions (PS_PRCSDEFN)."""
    return psdb.search_process_definitions(env, q=q, prcstype=prcstype, limit=limit)


@router.get("/api/peoplesoft/file-layouts")
def peoplesoft_file_layouts(env: str = "HCM", q: str = "", limit: int = 200):
    """Search File Layout definitions (PSFLDDEFN)."""
    return psdb.search_file_layouts(env, q=q, limit=limit)


@router.get("/api/peoplesoft/translate-fields")
def peoplesoft_translate_fields(env: str = "HCM", q: str = "", limit: int = 200):
    """Search fields with translate values (PSXLATDEFN)."""
    return psdb.search_translate_fields(env, q=q, limit=limit)


@router.get("/api/peoplesoft/projects")
def peoplesoft_projects(env: str = "HCM", q: str = "", limit: int = 200):
    """Search App Designer projects (PSPROJECTDEFN)."""
    return psdb.search_projects(env, q=q, limit=limit)


@router.get("/api/peoplesoft/ib-messages")
def peoplesoft_ib_messages(env: str = "HCM", q: str = "", limit: int = 200):
    """Search IB Message definitions (PSMSGDEFN)."""
    return psdb.search_ib_messages(env, q=q, limit=limit)


@router.get("/api/peoplesoft/ib-applications")
def peoplesoft_ib_applications(env: str = "HCM", q: str = "", limit: int = 100):
    """Search IB Application Service definitions (PSIBAPPLDEFN)."""
    return psdb.search_ib_applications(env, q=q, limit=limit)


@router.get("/api/peoplesoft/app-classes")
def peoplesoft_app_classes(env: str = "HCM", q: str = "", pkg: str = "", limit: int = 200):
    """Search Application Class definitions (PSAPPCLASSDEFN)."""
    return psdb.search_app_classes(env, q=q, pkg=pkg, limit=limit)


@router.get("/api/peoplesoft/content-services")
def peoplesoft_content_services(env: str = "HCM", q: str = "", owner: str = "", limit: int = 200):
    """Search Content Service Provider definitions (PSPTCSSRVDEFN)."""
    return psdb.search_content_services(env, q=q, owner=owner, limit=limit)


@router.get("/api/peoplesoft/ptf-tests")
def peoplesoft_ptf_tests(env: str = "HCM", q: str = "", ptf_type: str = "", limit: int = 200):
    """Search PeopleTools Test Framework definitions (PSPTTSTDEFN)."""
    return psdb.search_ptf_tests(env, q=q, ptf_type=ptf_type, limit=limit)


@router.get("/api/peoplesoft/ads-definitions")
def peoplesoft_ads_definitions(env: str = "HCM", q: str = "", owner: str = "", limit: int = 200):
    """Search Application Data Set definitions (PSADSDEFN)."""
    return psdb.search_ads_definitions(env, q=q, owner=owner, limit=limit)


@router.get("/api/peoplesoft/ib-service-groups")
def peoplesoft_ib_service_groups(env: str = "HCM", q: str = "", owner: str = "", limit: int = 200):
    """Search IB Service Group definitions (PSIBGROUPDEFN)."""
    return psdb.search_ib_service_groups(env, q=q, owner=owner, limit=limit)


@router.get("/api/peoplesoft/url-definitions")
def peoplesoft_url_definitions(env: str = "HCM", q: str = "", limit: int = 200):
    """Search URL definitions (PSURLDEFN)."""
    return psdb.search_url_definitions(env, q=q, limit=limit)


@router.get("/api/peoplesoft/chatbot-skills")
def peoplesoft_chatbot_skills(env: str = "HCM", q: str = "", limit: int = 200):
    """Search Chatbot Skill definitions (PSCBAPPLDEFN)."""
    return psdb.search_chatbot_skills(env, q=q, limit=limit)


@router.get("/api/peoplesoft/ib-routings")
def peoplesoft_ib_routings(env: str = "HCM", q: str = "", rtng_type: str = "", status: str = "", limit: int = 200):
    """Search IB Routing definitions (PSIBRTNGDEFN)."""
    return psdb.search_ib_routings(env, q=q, rtng_type=rtng_type, status=status, limit=limit)


@router.get("/api/peoplesoft/style-sheets")
def peoplesoft_style_sheets(env: str = "HCM", q: str = "", ss_type: str = "", limit: int = 200):
    """Search Style Sheet definitions (PSSTYLSHEETDEFN)."""
    return psdb.search_style_sheets(env, q=q, ss_type=ss_type, limit=limit)


@router.get("/api/peoplesoft/archive-objects")
def peoplesoft_archive_objects(env: str = "HCM", q: str = "", limit: int = 200):
    """Search Data Archive Object definitions (PSARCHOBJDEFN)."""
    return psdb.search_archive_objects(env, q=q, limit=limit)


@router.get("/api/peoplesoft/timezones")
def peoplesoft_timezones(env: str = "HCM", q: str = "", limit: int = 200):
    """Search Timezone definitions (PSTIMEZONEDEFN)."""
    return psdb.search_timezones(env, q=q, limit=limit)


@router.get("/api/peoplesoft/locales")
def peoplesoft_locales(env: str = "HCM", q: str = "", limit: int = 200):
    """Search Locale definitions (PSLOCALEDEFN)."""
    return psdb.search_locales(env, q=q, limit=limit)


@router.get("/api/peoplesoft/pm-metrics")
def peoplesoft_pm_metrics(env: str = "HCM", q: str = "", limit: int = 200):
    """Search Performance Monitor metric definitions (PSPMMETRICDEFN)."""
    return psdb.search_pm_metrics(env, q=q, limit=limit)


@router.get("/api/peoplesoft/pm-transactions")
def peoplesoft_pm_transactions(env: str = "HCM", q: str = "", limit: int = 100):
    """Search Performance Monitor transaction definitions (PSPMTRANSDEFN)."""
    return psdb.search_pm_transactions(env, q=q, limit=limit)


@router.get("/api/peoplesoft/pm-events")
def peoplesoft_pm_events(env: str = "HCM", q: str = "", limit: int = 50):
    """Search Performance Monitor event definitions (PSPMEVENTDEFN)."""
    return psdb.search_pm_events(env, q=q, limit=limit)


@router.get("/api/peoplesoft/ib-operations")
def peoplesoft_ib_operations(env: str = "HCM", q: str = "", rtype: str = "", limit: int = 100):
    """Search IB service operation definitions (PSOPERATION)."""
    return psdb.search_ib_operations(env, q=q, rtype=rtype, limit=limit)


@router.get("/api/peoplesoft/security/reports")
def peoplesoft_security_report(report: str = "empty_roles", env: str = "HCM", limit: int = 100):
    """Run a canned security audit report."""
    return psdb.security_report(env, report, limit=limit)


@router.get("/api/peoplesoft/reports")
def peoplesoft_report(report: str, env: str = "HCM", limit: int = 200):
    """Run any report from the full catalog by key."""
    return psdb.security_report(env, report, limit=limit)


@router.get("/api/peoplesoft/reports/catalog")
def peoplesoft_reports_catalog(env: str = "HCM"):
    """Return list of all available reports with title, category, and key."""
    result = psdb.security_report(env, "__catalog__", limit=1)
    return result.get("available_reports", [])


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


@router.get("/api/peoplesoft/permissionlists/{classid}/page-grants")
def peoplesoft_permissionlist_page_grants(classid: str, env: str = "HCM", limit: int = 200):
    return psdb.permissionlist_page_grants(env, classid, limit=limit)


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


@router.get("/api/peoplesoft/components/{component}/page-grants")
def peoplesoft_component_page_grants(component: str, env: str = "HCM", limit: int = 300):
    """Return page-level security for a component — which permission lists grant each page."""
    return psdb.component_page_grants(env, component, limit=limit)


@router.get("/api/peoplesoft/components/{component}/hierarchy")
def peoplesoft_component_hierarchy(component: str, env: str = "HCM"):
    """Return page hierarchy with structural contents (subpages/grids) for a component."""
    return psdb.component_page_hierarchy(env, component)


@router.get("/api/peoplesoft/components/{component}/menu-placements")
def peoplesoft_component_menu_placements(component: str, env: str = "HCM"):
    return [
        attach_links(row, env)
        for row in safe_rows(lambda: psdb.component_menu_placements(env, component))
    ]


@router.get("/api/peoplesoft/menus")
def peoplesoft_search_menus(q: str = "", env: str = "HCM"):
    rows = safe_rows(lambda: psdb.search_menus(env, q))
    return [
        {**r, "_links": {"admin": f"/admin/object/menu/{r.get('menuname','')}"}}
        for r in rows
    ]


@router.get("/api/peoplesoft/menus/{menuname}")
def peoplesoft_menu(menuname: str, env: str = "HCM"):
    defn = psdb.menu(env, menuname.upper())
    if not defn:
        raise HTTPException(status_code=404, detail="Menu not found")
    return defn


@router.get("/api/peoplesoft/menus/{menuname}/items")
def peoplesoft_menu_items(menuname: str, env: str = "HCM"):
    return safe_rows(lambda: psdb.menu_items(env, menuname.upper()))


@router.get("/api/peoplesoft/components/{component}/menus")
def peoplesoft_component_menus(component: str, env: str = "HCM"):
    rows = safe_rows(lambda: psdb.component_menus(env, component.upper()))
    return [
        {**r, "_links": {"admin": f"/admin/object/menu/{r.get('menuname','')}"}}
        for r in rows
    ]


@router.get("/api/peoplesoft/components/{component}/records")
def peoplesoft_component_records(component: str, env: str = "HCM"):
    component_row = safe_rows(lambda: [psdb.component(env, component)])
    component_row = component_row[0] if component_row else None

    records = []
    if component_row:
        for key in ("searchrecname", "addsrchrecname"):
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
    object_type = normalize_object_type(object_type)
    object_name = object_name.upper()

    if object_type == "peoplecode":
        return peoplecode.graph(object_name, env)

    if object_type == "application_engine":
        return ae.program_graph(env, object_name)

    try:
        return uom_graph_response(env, object_type, object_name)
    except Exception:
        persistent_graph = graphdb_response(env, object_type, object_name)
        if persistent_graph:
            return persistent_graph

    raise HTTPException(status_code=400, detail="Unsupported graph object type")


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


@router.get("/api/peoplesoft/{env}/component/{name}/events")
def component_peoplecode_events(env: str, name: str):
    return psdb.get_component_peoplecode_events(env, name)


@router.get("/api/peoplesoft/{env}/component/search")
def component_search(env: str, q: str = "", limit: int = 30):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env, "PSPNLGRPDEFN"):
        return {"results": [], "warnings": ["PSPNLGRPDEFN not accessible"]}
    rows = psdb.query(env, """
        SELECT PNLGRPNAME, DESCR, MARKET
          FROM SYSADM.PSPNLGRPDEFN
         WHERE UPPER(PNLGRPNAME) LIKE :q
           AND MARKET = 'GBL'
         ORDER BY PNLGRPNAME
         FETCH FIRST :lim ROWS ONLY
    """, {"q": f"%{q.upper()}%", "lim": limit})
    return {"results": [dict(r) for r in rows]}
