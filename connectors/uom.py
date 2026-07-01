from connectors import ae, peoplecode, psdb, ptmetadata


def object_id(object_type, name):
    return f"{object_type.lower()}:{name.upper()}"


def object_url(object_type, name):
    return f"/admin/object/{object_type.lower()}/{name.upper()}"


def api_url(object_type, name):
    return f"/api/peoplesoft/object/{object_type.lower()}/{name.upper()}"


def graph_url(object_type, name):
    return f"/api/peoplesoft/graph/{object_type.lower()}/{name.upper()}"


def canonical_base(env, object_type, name, **extra):
    object_type = object_type.lower()
    name = name.upper()
    registry = ptmetadata.OBJECT_REGISTRY.get(object_type, {})

    base = {
        "id": object_id(object_type, name),
        "type": object_type,
        "name": name,
        "display_name": name,
        "description": "",
        "owner": "",
        "market": "",
        "version": "",
        "status": "unknown",
        "warnings": [],
        "_links": {
            "self": api_url(object_type, name),
            "admin": object_url(object_type, name),
            "graph": graph_url(object_type, name),
        },
        "_relationships": {},
        "_graph": {},
        "_metadata": {
            "environment": env.upper(),
            "registry": registry,
        },
    }
    base.update(extra)
    return base


def safe_relationship(name, loader):
    try:
        return loader(), []
    except Exception as exc:
        return [], [ptmetadata.warning("relationship_unavailable", f"{name} unavailable: {exc}")]


def attach_object_links(row, env):
    linked = dict(row)

    recname = str(linked.get("recname") or "").strip()
    fieldname = str(linked.get("fieldname") or "").strip()
    pnlname = str(linked.get("pnlname") or "").strip()
    pnlgrpname = str(linked.get("pnlgrpname") or "").strip()
    classid = str(linked.get("classid") or "").strip()
    rolename = str(linked.get("rolename") or "").strip()
    oprid = str(linked.get("roleuser") or linked.get("oprid") or "").strip()
    portal_objname = str(linked.get("portal_objname") or "").strip()
    encoded_ref = str(linked.get("encoded_reference") or "").strip()

    if recname and fieldname:
        field = f"{recname}.{fieldname}"
        linked.setdefault("_links", {})["admin"] = object_url("field", field)
    elif recname:
        linked.setdefault("_links", {})["admin"] = object_url("record", recname)
    elif pnlname:
        linked.setdefault("_links", {})["admin"] = object_url("page", pnlname)
    elif pnlgrpname:
        linked.setdefault("_links", {})["admin"] = object_url("component", pnlgrpname)
    elif classid:
        linked.setdefault("_links", {})["admin"] = object_url("permissionlist", classid)
    elif rolename:
        linked.setdefault("_links", {})["admin"] = object_url("role", rolename)
    elif oprid:
        linked.setdefault("_links", {})["admin"] = object_url("operator", oprid)
    elif portal_objname:
        linked.setdefault("_links", {})["admin"] = object_url("portal_registry", portal_objname)
    elif encoded_ref:
        linked.setdefault("_links", {})["admin"] = f"/admin/object/peoplecode/{encoded_ref}"

    return linked


def field_object(env, field_ref):
    warnings = []

    try:
        definition = psdb.field_definition(env, field_ref)
    except Exception as exc:
        try:
            resolved = psdb.resolve_field_reference(env, field_ref)
        except Exception:
            resolved = {}

        resolved_name = resolved.get("canonical_name") or field_ref.upper()
        if "." not in resolved_name:
            resolved_name = f"UNKNOWN.{resolved_name}"
        definition = {
            "canonical_name": resolved_name,
            "recname": resolved_name.split(".", 1)[0],
            "fieldname": resolved_name.split(".", 1)[1],
            "resolved": bool(resolved.get("resolved")),
            "warnings": [str(exc)],
        }

    warnings.extend(
        ptmetadata.warning("metadata_unavailable", item)
        for item in definition.get("warnings", [])
        if item
    )

    canonical_name = definition.get("canonical_name") or field_ref.upper()
    recname = definition.get("recname")
    fieldname = definition.get("fieldname")
    status = "available" if definition.get("resolved") else "partial"

    records, record_warnings = safe_relationship("field records", lambda: psdb.field_records(env, canonical_name))
    pages, page_warnings = safe_relationship("field pages", lambda: psdb.field_pages(env, canonical_name))
    components, component_warnings = safe_relationship("field components", lambda: psdb.field_components(env, canonical_name))
    peoplecode, peoplecode_warnings = safe_relationship("field peoplecode", lambda: psdb.field_peoplecode_metadata(env, canonical_name))
    search_records, search_record_warnings = safe_relationship("field search records", lambda: psdb.field_search_records(env, canonical_name))
    views, view_warnings = safe_relationship("field views", lambda: psdb.field_views(env, canonical_name))

    warnings.extend(record_warnings)
    warnings.extend(page_warnings)
    warnings.extend(component_warnings)
    warnings.extend(peoplecode_warnings)
    warnings.extend(search_record_warnings)
    warnings.extend(view_warnings)

    relationships = {
        "records": [attach_object_links(row, env) for row in records],
        "pages": [attach_object_links(row, env) for row in pages],
        "components": [attach_object_links(row, env) for row in components],
        "peoplecode": [attach_object_links(row, env) for row in peoplecode],
        "search_records": [attach_object_links(row, env) for row in search_records],
        "views": [attach_object_links(row, env) for row in views],
        "sql": [],
    }

    overview = {
        "record": recname,
        "field": fieldname,
        "long_name": definition.get("long_name"),
        "short_name": definition.get("short_name"),
        "label": definition.get("label_id"),
        "field_type": definition.get("field_type"),
        "length": definition.get("length"),
        "decimal_positions": definition.get("decimal_positions"),
        "required": definition.get("required"),
        "key": definition.get("key"),
        "search_key": definition.get("search_key"),
        "alternate_search_key": definition.get("alternate_search_key"),
        "duplicate_order_key": definition.get("duplicate_order_key"),
        "prompt_table": definition.get("prompt_table"),
        "edit_table": definition.get("edit_table"),
        "translate_table": definition.get("translate_table"),
        "xlat": definition.get("xlat"),
        "default_value": definition.get("default_value"),
        "format": definition.get("format"),
        "currency_control": definition.get("currency_control"),
        "language_sensitivity": definition.get("language_sensitivity"),
        "fieldnum": definition.get("fieldnum"),
        "useedit": definition.get("useedit"),
        "useedit2": definition.get("useedit2"),
        "lastupddttm": definition.get("lastupddttm"),
        "lastupdoprid": definition.get("lastupdoprid"),
    }

    graph = field_graph(env, canonical_name, relationships=relationships)

    return canonical_base(
        env,
        "field",
        canonical_name,
        display_name=canonical_name,
        description=definition.get("description") or definition.get("long_name") or "",
        owner=recname or "",
        status=status,
        warnings=warnings,
        _links={
            "self": f"/api/peoplesoft/fields/{canonical_name}",
            "admin": object_url("field", canonical_name),
            "record": object_url("record", recname) if recname else "",
            "graph": f"/api/peoplesoft/fields/{canonical_name}/graph",
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "input": field_ref,
            "resolved": definition.get("resolved", False),
            "registry": ptmetadata.OBJECT_REGISTRY.get("field", {}),
            "raw": definition,
        },
    )


def graph_node(node_type, name, data=None):
    name = name.upper()
    return {
        "id": object_id(node_type, name),
        "type": node_type,
        "name": name,
        "label": name,
        "data": data or {},
        "_links": {
            "admin": object_url(node_type, name),
        },
    }


def graph_edge(source_type, source_name, target_type, target_name, relationship):
    return {
        "source": object_id(source_type, source_name),
        "target": object_id(target_type, target_name),
        "relationship": relationship,
    }


def add_node(nodes, node):
    nodes[node["id"]] = node


def _relation_value(row, selector):
    if callable(selector):
        return selector(row)
    return row.get(selector)


def relationship_graph(root_type, root_name, relationships, specs, root_data=None):
    """Build a small UOM graph from relationship rows and declarative specs."""
    root_name = root_name.upper()
    nodes = {}
    edges = []

    add_node(nodes, graph_node(root_type, root_name, root_data))

    for spec in specs:
        rows = relationships.get(spec["relationship"], []) or []
        for row in rows:
            target_name = _relation_value(row, spec["target_name"])
            source_name = _relation_value(row, spec["source_name"]) if spec.get("source_name") else root_name
            if target_name:
                target_type = _relation_value(row, spec.get("target_type")) if spec.get("target_type") else (
                    spec.get("target_node_type") or spec["node_type"]
                )
                target_type = target_type or spec["node_type"]
                source_type = _relation_value(row, spec.get("source_type")) if spec.get("source_type") else (
                    spec.get("source_node_type") or root_type
                )
                source_type = source_type or root_type
                if spec.get("source_name"):
                    add_node(nodes, graph_node(source_type, source_name, row))
                if object_id(target_type, target_name) != object_id(root_type, root_name):
                    add_node(nodes, graph_node(target_type, target_name, row))
                edges.append(graph_edge(
                    source_type,
                    source_name,
                    target_type,
                    target_name,
                    _relation_value(row, spec["edge"]) if spec.get("edge") else spec["default_edge"],
                ))

            for extra in spec.get("extra_edges", []):
                source_name = _relation_value(row, extra["source_name"])
                extra_target_name = _relation_value(row, extra["target_name"])
                if not source_name or not extra_target_name:
                    continue
                source_type = _relation_value(row, extra.get("source_type")) if extra.get("source_type") else extra["source_node_type"]
                source_type = source_type or extra["source_node_type"]
                target_type = _relation_value(row, extra.get("target_type")) if extra.get("target_type") else extra["target_node_type"]
                target_type = target_type or extra["target_node_type"]
                add_node(nodes, graph_node(source_type, source_name, row))
                add_node(nodes, graph_node(target_type, extra_target_name, row))
                edges.append(graph_edge(
                    source_type,
                    source_name,
                    target_type,
                    extra_target_name,
                    _relation_value(row, extra["edge"]) if callable(extra.get("edge")) else extra["edge"],
                ))

    return {"nodes": list(nodes.values()), "edges": edges}


def limit_relationships(relationships, limits):
    limited = {}
    for key, rows in relationships.items():
        limited[key] = (rows or [])[:limits[key]] if key in limits else rows
    return limited


def field_graph(env, field_ref, relationships=None):
    relationships = relationships or field_object(env, field_ref)["_relationships"]
    field_name = field_ref.upper()
    nodes = {}
    edges = []

    add_node(nodes, graph_node("field", field_name))

    for row in relationships.get("records", []):
        recname = row.get("recname")
        if recname:
            add_node(nodes, graph_node("record", recname, row))
            edges.append(graph_edge("record", recname, "field", field_name, "contains_field"))

    for row in relationships.get("pages", []):
        pnlname = row.get("pnlname")
        recname = row.get("recname")
        if pnlname:
            add_node(nodes, graph_node("page", pnlname, row))
            edges.append(graph_edge("page", pnlname, "field", field_name, "displays_field"))
        if pnlname and recname:
            add_node(nodes, graph_node("record", recname, row))
            edges.append(graph_edge("page", pnlname, "record", recname, "uses_record"))

    for row in relationships.get("components", []):
        component = row.get("pnlgrpname")
        page = row.get("pnlname")
        if component:
            add_node(nodes, graph_node("component", component, row))
        if component and page:
            add_node(nodes, graph_node("page", page, row))
            edges.append(graph_edge("component", component, "page", page, "contains_page"))

    seen_security = set()
    for component_row in relationships.get("components", []):
        component = component_row.get("pnlgrpname")
        if not component:
            continue
        access, _ = safe_relationship("field component security", lambda component=component: psdb.component_access(env, component))
        for access_row in access:
            classid = access_row.get("classid")
            rolename = access_row.get("rolename")
            roleuser = access_row.get("roleuser")
            if classid and ("permissionlist", classid, component) not in seen_security:
                seen_security.add(("permissionlist", classid, component))
                add_node(nodes, graph_node("permissionlist", classid, access_row))
                edges.append(graph_edge("permissionlist", classid, "component", component, "grants_component"))
            if rolename and classid and ("role", rolename, classid) not in seen_security:
                seen_security.add(("role", rolename, classid))
                add_node(nodes, graph_node("role", rolename, access_row))
                edges.append(graph_edge("role", rolename, "permissionlist", classid, "contains_permissionlist"))
            if roleuser and rolename and ("operator", roleuser, rolename) not in seen_security:
                seen_security.add(("operator", roleuser, rolename))
                add_node(nodes, graph_node("operator", roleuser, access_row))
                edges.append(graph_edge("operator", roleuser, "role", rolename, "has_role"))

    return {
        "root": object_id("field", field_name),
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def sections_for_field(field):
    relationships = field.get("_relationships", {})
    metadata = field.get("_metadata", {})
    raw = metadata.get("raw", {})

    return [
        {"name": "Field Metadata", "items": [], "data": raw},
        {"name": "Records", "items": relationships.get("records", []), "data": {"count": len(relationships.get("records", []))}},
        {"name": "Pages", "items": relationships.get("pages", []), "data": {"count": len(relationships.get("pages", []))}},
        {"name": "Components", "items": relationships.get("components", []), "data": {"count": len(relationships.get("components", []))}},
        {"name": "PeopleCode", "items": relationships.get("peoplecode", []), "data": {"metadata_only": True}},
        {"name": "Search Records", "items": relationships.get("search_records", []), "data": {"count": len(relationships.get("search_records", []))}},
        {"name": "Views", "items": relationships.get("views", []), "data": {"count": len(relationships.get("views", []))}},
        {"name": "SQL", "items": relationships.get("sql", []), "data": {"status": "Future placeholder"}},
        {"name": "Graph Preview", "items": field.get("_graph", {}).get("nodes", []), "data": {"edge_count": len(field.get("_graph", {}).get("edges", []))}},
        {"name": "Warnings", "items": field.get("warnings", []), "data": {"count": len(field.get("warnings", []))}},
    ]


def peoplecode_object(env, reference):
    result = peoplecode.program(reference, env)
    item = result["item"]
    refs = peoplecode.references(item["reference"], env)
    graph = peoplecode.graph(item["reference"], env)
    warnings = result["warnings"] + refs["warnings"]

    relationships = {
        "references": refs["references"],
        "calls": refs["calls"],
        "parent": [{
            "type": item.get("parent_type"),
            "name": item.get("parent_name"),
            "_links": {
                "admin": object_url(item.get("parent_type"), item.get("parent_name"))
            } if item.get("parent_type") and item.get("parent_name") else {},
        }] if item.get("parent_type") and item.get("parent_name") else [],
    }

    encoded = item.get("encoded_reference") or peoplecode.encode_reference(item["reference"])

    return canonical_base(
        env,
        "peoplecode",
        encoded,
        display_name=item["reference"],
        description=f"PeopleCode {item['reference']}",
        owner=item.get("parent_name") or "",
        status="available" if item.get("source") else "metadata_only",
        warnings=warnings,
        _links={
            "self": f"/api/peoplesoft/peoplecode/{encoded}",
            "admin": f"/admin/object/peoplecode/{encoded}",
            "graph": f"/api/peoplesoft/peoplecode/{encoded}/graph",
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "input": reference,
            "registry": ptmetadata.OBJECT_REGISTRY.get("peoplecode", {}),
            "raw": item,
        },
    )


def sections_for_peoplecode(pc):
    metadata = pc.get("_metadata", {})
    raw = metadata.get("raw", {})
    relationships = pc.get("_relationships", {})
    references = relationships.get("references", {})

    reference_items = []
    for ref_type, values in references.items():
        for value in values:
            object_type = {
                "records": "record",
                "fields": "field",
                "components": "component",
                "pages": "page",
                "sql_definitions": "sql_definition",
                "functions": "function",
                "classes": "application_class",
                "application_engines": "application_engine",
                "service_operations": "service_operation",
            }.get(ref_type, ref_type)
            reference_items.append({
                "relationship": ref_type,
                "type": object_type,
                "name": value,
                "_links": {"admin": object_url(object_type, value)},
            })

    return [
        {"name": "PeopleCode Metadata", "items": [], "data": {
            "reference": raw.get("reference"),
            "object_type": raw.get("object_type_label"),
            "event": raw.get("event"),
            "event_label": raw.get("event_label"),
            "event_scope": raw.get("event_scope"),
            "subtype": raw.get("subtype"),
            "semantic_path": raw.get("semantic_path_text"),
            "parent_type": raw.get("parent_type"),
            "parent_name": raw.get("parent_name"),
            "last_updated": raw.get("lastupddttm"),
            "updated_by": raw.get("lastupdoprid"),
        }},
        {"name": "Source", "items": [], "data": {"source": raw.get("source"), "warning": "Source unavailable" if not raw.get("source") else ""}},
        {"name": "Parent Object", "items": relationships.get("parent", []), "data": {}},
        {"name": "References", "items": reference_items, "data": {"count": len(reference_items)}},
        {"name": "Calls", "items": relationships.get("calls", []), "data": {"count": len(relationships.get("calls", []))}},
        {"name": "Graph Preview", "items": pc.get("_graph", {}).get("nodes", []), "data": {"edge_count": len(pc.get("_graph", {}).get("edges", []))}},
        {"name": "Warnings", "items": pc.get("warnings", []), "data": {"count": len(pc.get("warnings", []))}},
    ]


def object_payload(field):
    return {
        "type": field["type"],
        "name": field["name"],
        "title": field["display_name"],
        "overview": {
            "id": field["id"],
            "display_name": field["display_name"],
            "description": field["description"],
            "status": field["status"],
            **field.get("_metadata", {}).get("raw", {}),
        },
        "sections": sections_for_field(field),
        "_links": field["_links"],
        "_uom": field,
    }


def peoplecode_payload(pc):
    return {
        "type": pc["type"],
        "name": pc["name"],
        "title": pc["display_name"],
        "overview": {
            "id": pc["id"],
            "display_name": pc["display_name"],
            "description": pc["description"],
            "status": pc["status"],
            **pc.get("_metadata", {}).get("raw", {}),
        },
        "sections": sections_for_peoplecode(pc),
        "_links": pc["_links"],
        "_uom": pc,
    }


def ae_object(env, ae_applid):
    """Build a UOM canonical object for an Application Engine program."""
    ae_applid = ae_applid.upper()
    warnings = []

    prog_result = ae.program(env, ae_applid)
    warnings.extend(w for w in prog_result["warnings"] if w)
    item = prog_result["item"] or {}
    status = "available" if item else "not_found"

    sect_result = ae.sections(env, ae_applid)
    warnings.extend(w for w in sect_result["warnings"] if w)

    step_result = ae.steps(env, ae_applid)
    warnings.extend(w for w in step_result["warnings"] if w)

    state_result = ae.state_records(env, ae_applid)
    warnings.extend(w for w in state_result["warnings"] if w)

    tmp_result = ae.temp_tables(env, ae_applid)
    warnings.extend(w for w in tmp_result["warnings"] if w)

    proc_result = ae.process_definitions(env, ae_applid)
    warnings.extend(w for w in proc_result["warnings"] if w)

    pc_result = ae.ae_peoplecode(env, ae_applid)
    warnings.extend(w for w in pc_result["warnings"] if w)

    # Normalize AE PeopleCode rows so each has reference, event, and a deep-link to PeopleCode Explorer
    pc_items = []
    pc_by_step = {}  # (section, step) → encoded_reference
    for row in pc_result["items"]:
        normalized = peoplecode.normalize_program(row)
        enc = normalized.get("encoded_reference")
        if enc:
            normalized["_links"] = {"admin": f"/admin/object/peoplecode/{enc}"}
            section_key = (
                (row.get("objectvalue2") or "").strip().upper(),
                (row.get("objectvalue6") or "").strip().upper(),
            )
            pc_by_step[section_key] = enc
        pc_items.append(normalized)

    # Fetch SQL text for SQL-bearing steps (PSAESTMTDEFN → PSSQLTEXTDEFN SQLTYPE=1)
    sql_text_map, sql_warnings = ae.ae_sql_step_text(env, ae_applid)
    warnings.extend(w for w in sql_warnings if w)

    # Cross-reference: annotate steps with PeopleCode links and SQL text
    steps_annotated = []
    for step in step_result["items"]:
        s = dict(step)
        section_raw = (s.get("ae_section") or "").strip()
        step_raw = (s.get("ae_step") or "").strip()
        section_up = section_raw.upper()
        step_up = step_raw.upper()

        pc_ref = pc_by_step.get((section_up, step_up))
        if pc_ref:
            s.setdefault("_links", {})["peoplecode"] = f"/admin/object/peoplecode/{pc_ref}"
            s["has_peoplecode"] = True

        # Attach SQL text entries; sql_text_map keys use native DB case
        sql_entries = sql_text_map.get((section_raw, step_raw))
        if sql_entries:
            s["sql_statements"] = sql_entries
            s["has_sql"] = True
        steps_annotated.append(s)

    runtime_result = ae.runtime_instances(env, ae_applid, limit=20)
    warnings.extend(w for w in runtime_result["warnings"] if w)

    graph = ae.program_graph(env, ae_applid)

    relationships = {
        "sections": sect_result["items"],
        "steps": steps_annotated,
        "state_records": state_result["items"],
        "temp_tables": tmp_result["items"],
        "process_definitions": proc_result["items"],
        "peoplecode": pc_items,
        "runtime_instances": runtime_result["items"],
    }

    description = item.get("descr") or ""

    return canonical_base(
        env,
        "application_engine",
        ae_applid,
        display_name=f"AE: {ae_applid}",
        description=description,
        owner="SYSADM",
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/peoplesoft/ae/{ae_applid}",
            "admin": object_url("application_engine", ae_applid),
            "sections": f"/api/peoplesoft/ae/{ae_applid}/sections",
            "steps": f"/api/peoplesoft/ae/{ae_applid}/steps",
            "runtime": f"/api/peoplesoft/ae/{ae_applid}/runtime",
            "graph": f"/api/peoplesoft/ae/{ae_applid}/graph",
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("application_engine", {}),
            "raw": item,
        },
    )


def sections_for_ae(ae_obj):
    """Build object-page sections for an AE UOM object."""
    rels = ae_obj.get("_relationships", {})
    meta = ae_obj.get("_metadata", {})
    raw = meta.get("raw", {})

    section_items = rels.get("sections", [])
    step_items = rels.get("steps", [])
    state_items = rels.get("state_records", [])
    tmp_items = rels.get("temp_tables", [])
    proc_items = rels.get("process_definitions", [])
    pc_items = rels.get("peoplecode", [])
    runtime_items = rels.get("runtime_instances", [])
    graph_nodes = ae_obj.get("_graph", {}).get("nodes", [])
    graph_edges = ae_obj.get("_graph", {}).get("edges", [])

    action_counts = {}
    for step in step_items:
        label = step.get("action_type_label") or "Unknown"
        action_counts[label] = action_counts.get(label, 0) + 1

    # Build SQL Steps items: one entry per (step, stmt_type) that has sql text
    _stmt_labels = {
        "S": "SQL", "D": "Do Select", "H": "Do While",
        "W": "Do When", "U": "Do Until", "X": "Do Select (Extended)",
    }
    sql_step_items = []
    for step in step_items:
        sql_stmts = step.get("sql_statements")
        if not sql_stmts:
            continue
        section = str(step.get("ae_section") or "").strip()
        step_name = str(step.get("ae_step") or "").strip()
        descr = str(step.get("descr") or "").strip()
        for stmt in sql_stmts:
            stype = stmt.get("stmt_type", "")
            label = _stmt_labels.get(stype, stype or "SQL")
            entry = {
                "ae_section": section,
                "ae_step": step_name,
                "action_type": label,
                "descr": descr,
                "data": {"ddl": stmt.get("sql_text", "")},
            }
            if step.get("_links"):
                entry["_links"] = step["_links"]
            sql_step_items.append(entry)

    return [
        {"name": "Definition", "items": [], "data": raw},
        {"name": "Sections", "items": section_items,
         "data": {"count": len(section_items)}},
        {"name": "Steps", "items": step_items,
         "data": {"count": len(step_items), "action_types": action_counts}},
        {"name": "SQL Steps", "items": sql_step_items,
         "data": {"count": len(sql_step_items),
                  "note": "SQL text for each step with an executable SQL statement"}},
        {"name": "State Records", "items": state_items,
         "data": {"count": len(state_items)}},
        {"name": "Temp Tables", "items": tmp_items,
         "data": {"count": len(tmp_items)}},
        {"name": "Process Definitions", "items": proc_items,
         "data": {"count": len(proc_items)}},
        {"name": "PeopleCode", "items": pc_items,
         "data": {"count": len(pc_items), "note": "Metadata references only" if not pc_items else ""}},
        {"name": "Runtime Instances", "items": runtime_items,
         "data": {"count": len(runtime_items), "note": "Most recent 20 process requests"}},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": ae_obj.get("warnings", []),
         "data": {"count": len(ae_obj.get("warnings", []))}},
    ]


def ae_payload(ae_obj):
    """Build the object-page payload for an AE UOM object."""
    rels = ae_obj.get("_relationships", {})
    state_records = rels.get("state_records", [])
    restart_eligible = len(state_records) > 0
    return {
        "type": ae_obj["type"],
        "name": ae_obj["name"],
        "title": ae_obj["display_name"],
        "overview": {
            "id": ae_obj["id"],
            "display_name": ae_obj["display_name"],
            "description": ae_obj["description"],
            "status": ae_obj["status"],
            "restart_eligible": restart_eligible,
            "state_records": len(state_records),
            **ae_obj.get("_metadata", {}).get("raw", {}),
        },
        "sections": sections_for_ae(ae_obj),
        "_links": ae_obj["_links"],
        "_uom": ae_obj,
    }


def record_object(env, recname):
    """Build a UOM canonical object for a PeopleSoft Record (PSRECDEFN)."""
    recname = recname.upper()
    warnings = []

    detail, detail_warn = safe_relationship("record_detail", lambda: psdb.record_detail(env, recname))
    if detail_warn:
        warnings.extend(detail_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "not_found"
    rectype = detail.get("rectype") if detail else None
    description = (detail.get("recdescr") or "").strip() if detail else ""
    table_name = (detail.get("sqltablename") or "").strip() if detail else ""
    if not table_name:
        table_name = f"PS_{recname}"

    fields, field_warn = safe_relationship("record_fields", lambda: psdb.record_fields(env, recname))
    warnings.extend(field_warn)
    # Enrich fields with human-readable labels from PSDBFLDLABL
    if fields:
        try:
            _labels = psdb.field_labels_batch(env, [f.get("fieldname") for f in fields if f.get("fieldname")])
            for f in fields:
                fn = str(f.get("fieldname") or "").strip()
                lbl = _labels.get(fn)
                if lbl:
                    f["longname"] = lbl["longname"]
                    f["shortname"] = lbl["shortname"]
        except Exception:
            pass

    keys, key_warn = safe_relationship("record_keys", lambda: psdb.record_keys(env, recname))
    warnings.extend(key_warn)
    indexes, idx_warn = safe_relationship("record_indexes", lambda: psdb.record_indexes(env, recname))
    warnings.extend(idx_warn)
    components, comp_warn = safe_relationship("record_components", lambda: psdb.record_components(env, recname))
    warnings.extend(comp_warn)
    pages, page_warn = safe_relationship("record_pages", lambda: psdb.record_pages(env, recname))
    warnings.extend(page_warn)

    related = {}
    try:
        related = psdb.record_related(env, recname)
    except Exception as exc:
        warnings.append(ptmetadata.warning("relationship_unavailable", f"record_related unavailable: {exc}"))

    storage = {}
    try:
        storage = psdb.record_storage(env, recname) or {}
    except Exception:
        pass

    ddl_text = None
    if rectype in (0, 7):
        try:
            ddl_result = psdb.record_ddl(env, recname) or {}
            ddl_text = ddl_result.get("ddl")
        except Exception as exc:
            warnings.append(ptmetadata.warning("ddl_unavailable", f"DDL generation failed: {exc}"))

    # PeopleCode attached to this record (objectid1=1, OV1=recname)
    pc_items = []
    if ptmetadata.has_table(env, "PSPCMPROG"):
        try:
            pc_cols = psdb.select_existing_columns(
                env, "PSPCMPROG",
                ["OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3",
                 "OBJECTVALUE4", "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
                 "PROGSEQ", "LASTUPDDTTM", "LASTUPDOPRID"],
                required=["OBJECTVALUE1"],
            )
            pc_rows = psdb.query(env, f"""
                SELECT {", ".join(pc_cols)}
                  FROM SYSADM.PSPCMPROG
                 WHERE OBJECTID1 = 1
                   AND upper(OBJECTVALUE1) = upper(:recname)
                 ORDER BY OBJECTVALUE2, OBJECTVALUE3, PROGSEQ
                 FETCH FIRST 200 ROWS ONLY
            """, {"recname": recname})
            for row in pc_rows:
                normalized = peoplecode.normalize_program(row)
                enc = normalized.get("encoded_reference")
                if enc:
                    normalized["_links"] = {"admin": f"/admin/object/peoplecode/{enc}"}
                pc_items.append(normalized)
        except Exception:
            pass

    # Flatten related into relationship lists
    related_parent = [related["parent"]] if related.get("parent") else []
    related_lang = [related["lang"]] if related.get("lang") else []
    related_audit = [related["audit"]] if related.get("audit") else []
    related_views = related.get("views", [])

    # Rich dependency traversal: child records, AE state records, subrecord derivations
    usages = {}
    try:
        usages = psdb.record_usages(env, recname) or {}
    except Exception as exc:
        warnings.append(ptmetadata.warning("record_usages_unavailable", f"record_usages unavailable: {exc}"))

    child_records = usages.get("child_records", [])
    ae_state_records = usages.get("ae_state_records", [])
    subrecord_derivations = usages.get("subrecord_derivations", [])

    # Add admin links to child and derived records
    for r in child_records:
        rn = r.get("recname")
        if rn:
            r.setdefault("_links", {})["admin"] = f"/admin/object/record/{rn}"
    for r in subrecord_derivations:
        rn = r.get("recname")
        if rn:
            r.setdefault("_links", {})["admin"] = f"/admin/object/record/{rn}"
    for r in ae_state_records:
        ae = r.get("ae_applid")
        if ae:
            r.setdefault("_links", {})["admin"] = f"/admin/object/application_engine/{ae}"

    relationships = {
        "fields":               [attach_object_links(r, env) for r in (fields or [])],
        "keys":                 keys or [],
        "indexes":              indexes or [],
        "components":           [attach_object_links(r, env) for r in (components or [])],
        "pages":                [attach_object_links(r, env) for r in (pages or [])],
        "parent":               [attach_object_links(r, env) for r in related_parent],
        "lang":                 [attach_object_links(r, env) for r in related_lang],
        "audit":                [attach_object_links(r, env) for r in related_audit],
        "views":                [attach_object_links(r, env) for r in related_views],
        "storage":              [storage] if storage else [],
        "peoplecode":           pc_items,
        "child_records":        child_records,
        "ae_state_records":     ae_state_records,
        "subrecord_derivations": subrecord_derivations,
    }

    # Compact graph: record → fields, record ← parent, record → component
    nodes = {}
    edges = []
    add_node(nodes, graph_node("record", recname, detail or {}))
    for f in (fields or [])[:30]:
        fn = f.get("fieldname")
        if fn:
            add_node(nodes, graph_node("field", fn, f))
            edges.append(graph_edge("record", recname, "field", fn, "contains_field"))
    for r in related_parent:
        pn = r.get("recname")
        if pn:
            add_node(nodes, graph_node("record", pn, r))
            edges.append(graph_edge("record", pn, "record", recname, "parent_of"))
    for c in (components or [])[:10]:
        cn = c.get("pnlgrpname")
        if cn:
            add_node(nodes, graph_node("component", cn, c))
            edges.append(graph_edge("record", recname, "component", cn, "used_in_component"))

    rectype_label = psdb.RECTYPE_LABELS.get(rectype, f"Type {rectype}") if rectype is not None else ""

    return canonical_base(
        env,
        "record",
        recname,
        display_name=recname,
        description=description,
        owner="SYSADM",
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/record/{recname}",
            "admin": object_url("record", recname),
            "explorer": f"/admin/record/{recname}",
            "graph": graph_url("record", recname),
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "rectype": rectype,
            "rectype_label": rectype_label,
            "table": table_name,
            "ddl": ddl_text,
            "registry": ptmetadata.OBJECT_REGISTRY.get("record", {}),
            "raw": detail or {},
        },
    )


def sections_for_record(rec):
    """Build object-page sections for a Record UOM object."""
    rels = rec.get("_relationships", {})
    meta = rec.get("_metadata", {})
    raw = meta.get("raw", {})

    fields = rels.get("fields", [])
    keys = rels.get("keys", [])
    indexes = rels.get("indexes", [])
    components = rels.get("components", [])
    pages = rels.get("pages", [])
    parent = rels.get("parent", [])
    lang = rels.get("lang", [])
    audit = rels.get("audit", [])
    views = rels.get("views", [])
    storage = rels.get("storage", [])
    pc_items = rels.get("peoplecode", [])
    child_records = rels.get("child_records", [])
    ae_state_records = rels.get("ae_state_records", [])
    subrecord_derivations = rels.get("subrecord_derivations", [])
    ddl_text = meta.get("ddl")
    rectype = meta.get("rectype")
    graph_nodes = rec.get("_graph", {}).get("nodes", [])
    graph_edges = rec.get("_graph", {}).get("edges", [])

    related_all = parent + lang + audit + views
    storage_data = storage[0] if storage else {}

    return [
        {"name": "Definition", "items": [], "data": {
            "recname": rec["name"],
            "description": rec.get("description") or "",
            "rectype": meta.get("rectype_label") or raw.get("rectype"),
            "table": meta.get("table"),
            "parentrecname": raw.get("parentrecname") or "",
            "fieldcount": raw.get("fieldcount"),
            "keycount": raw.get("keycount"),
            "objectownerid": raw.get("objectownerid") or "",
            "auditrecname": raw.get("auditrecname") or "",
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
        {"name": "Fields", "items": fields,
         "data": {"count": len(fields)}},
        {"name": "Keys", "items": keys,
         "data": {"count": len(keys), "note": "From PSKEYDEFN" if keys else "PSKEYDEFN not accessible"}},
        {"name": "Indexes", "items": indexes,
         "data": {"count": len(indexes), "note": "From PSINDEXDEFN" if indexes else "PSINDEXDEFN not accessible"}},
        {"name": "Related Records", "items": related_all,
         "data": {"parent": len(parent), "lang_variant": len(lang), "audit": len(audit), "views": len(views)}},
        {"name": "Components", "items": components,
         "data": {"count": len(components), "note": "" if components else "PSPNLGRPDEFN not accessible"}},
        {"name": "Pages", "items": pages,
         "data": {"count": len(pages), "note": "" if pages else "PSPNLFIELD not accessible"}},
        {"name": "Storage", "items": [], "data": storage_data if storage_data else {"note": "ALL_TABLES not accessible or not a SQL table"}},
        {"name": "DDL", "items": [], "data": {"ddl": ddl_text} if ddl_text else {"note": "DDL not applicable" if rectype not in (0, 7) else "DDL unavailable (ALL_TAB_COLUMNS not accessible)"}},
        {"name": "PeopleCode", "items": pc_items, "data": {"count": len(pc_items)}},
        {"name": "Child Records", "items": child_records,
         "data": {"count": len(child_records),
                  "note": "Records with PARENTRECNAME pointing to this record"}},
        {"name": "Subrecord Derivations", "items": subrecord_derivations,
         "data": {"count": len(subrecord_derivations),
                  "note": "Records that inherit fields from this record via subrecord"}},
        {"name": "AE State Records", "items": ae_state_records,
         "data": {"count": len(ae_state_records),
                  "note": "Application Engine programs using this as a state/work record"}},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": rec.get("warnings", []),
         "data": {"count": len(rec.get("warnings", []))}},
    ]


def record_payload(rec):
    """Build the object-page payload for a Record UOM object."""
    meta = rec.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": rec["type"],
        "name": rec["name"],
        "title": rec["display_name"],
        "overview": {
            "id": rec["id"],
            "display_name": rec["display_name"],
            "description": rec.get("description") or "",
            "rectype": meta.get("rectype_label"),
            "table": meta.get("table"),
            "status": rec["status"],
            **raw,
        },
        "sections": sections_for_record(rec),
        "_links": rec["_links"],
        "_uom": rec,
    }


def operator_object(env, oprid):
    """Build a UOM canonical object for a PeopleSoft Operator (PSOPRDEFN)."""
    oprid = oprid.upper()
    warnings = []

    detail, d_warn = safe_relationship("operator_detail", lambda: psdb.operator_detail(env, oprid))
    if d_warn:
        warnings.extend(d_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "not_found"
    description = (detail.get("oprdefndesc") or "").strip() if detail else ""

    roles, r_warn = safe_relationship("operator_roles", lambda: psdb.operator_roles_full(env, oprid))
    warnings.extend(r_warn)
    permissionlists, pl_warn = safe_relationship("operator_permissionlists", lambda: psdb.operator_permissionlists(env, oprid))
    warnings.extend(pl_warn)

    relationships = {
        "roles": [attach_object_links(r, env) for r in (roles or [])],
        "permissionlists": [attach_object_links(r, env) for r in (permissionlists or [])],
    }

    nodes = {}
    edges = []
    add_node(nodes, graph_node("operator", oprid, detail or {}))
    for r in (roles or [])[:20]:
        rn = r.get("rolename")
        if rn:
            add_node(nodes, graph_node("role", rn, r))
            edges.append(graph_edge("operator", oprid, "role", rn, "has_role"))
    for pl in (permissionlists or [])[:20]:
        cn = pl.get("classid")
        if cn:
            add_node(nodes, graph_node("permissionlist", cn, pl))
            edges.append(graph_edge("operator", oprid, "permissionlist", cn, "has_permission"))

    return canonical_base(
        env, "operator", oprid,
        display_name=oprid,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/operator/{oprid}",
            "admin": object_url("operator", oprid),
            "explorer": f"/admin/operator/{oprid}",
            "tracing": f"/admin/tracing?oprid={oprid}&env={env}",
            "graph": graph_url("operator", oprid),
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("operator", {}),
            "raw": detail or {},
        },
    )


def sections_for_operator(op):
    rels = op.get("_relationships", {})
    meta = op.get("_metadata", {})
    raw = meta.get("raw", {})
    roles = rels.get("roles", [])
    permissionlists = rels.get("permissionlists", [])
    graph_nodes = op.get("_graph", {}).get("nodes", [])
    graph_edges = op.get("_graph", {}).get("edges", [])
    return [
        {"name": "Identity", "items": [], "data": {
            "oprid": op["name"],
            "description": op.get("description") or "",
            "email": raw.get("emailid") or "",
            "employee_id": raw.get("emplid") or "",
            "oprclass": raw.get("oprclass") or "",
            "oprtype": raw.get("oprtype_label") or raw.get("oprtype") or "",
            "acctlock": raw.get("acctlock_label") or "",
            "last_signon": raw.get("lastsignondttm") or "",
            "last_pwd_change": raw.get("lastpswdchange") or "",
            "failed_logins": raw.get("failedlogins"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
        {"name": "Roles", "items": roles, "data": {"count": len(roles)}},
        {"name": "Permission Lists", "items": permissionlists,
         "data": {"count": len(permissionlists), "note": "" if permissionlists else "Permission list traversal may require PSCLASSDEFN grant"}},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": op.get("warnings", []),
         "data": {"count": len(op.get("warnings", []))}},
    ]


def operator_payload(op):
    meta = op.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": op["type"],
        "name": op["name"],
        "title": op["display_name"],
        "overview": {
            "id": op["id"],
            "display_name": op["display_name"],
            "description": op.get("description") or "",
            "status": op["status"],
            **raw,
        },
        "sections": sections_for_operator(op),
        "_links": op["_links"],
        "_uom": op,
    }


def role_object(env, rolename):
    """Build a UOM canonical object for a PeopleSoft Role (PSROLEDEFN)."""
    rolename_upper = rolename.upper()
    warnings = []

    detail, d_warn = safe_relationship("role_detail", lambda: psdb.role_detail(env, rolename))
    if d_warn:
        warnings.extend(d_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    # role_detail uses case-insensitive match; resolved name comes from the row
    resolved_name = (detail.get("rolename") or rolename_upper) if detail else rolename_upper
    status = "available" if detail else "not_found"
    description = (detail.get("descr") or "").strip() if detail else ""

    members, m_warn = safe_relationship("role_members", lambda: psdb.role_users(env, rolename))
    warnings.extend(m_warn)
    permissionlists, pl_warn = safe_relationship("role_permissionlists", lambda: psdb.role_permissionlists(env, rolename))
    warnings.extend(pl_warn)

    relationships = {
        "members": [attach_object_links(r, env) for r in (members or [])],
        "permissionlists": [attach_object_links(r, env) for r in (permissionlists or [])],
    }

    nodes = {}
    edges = []
    add_node(nodes, graph_node("role", resolved_name, detail or {}))
    for m in (members or [])[:20]:
        op = m.get("roleuser")
        if op:
            add_node(nodes, graph_node("operator", op, m))
            edges.append(graph_edge("role", resolved_name, "operator", op, "has_member"))
    for pl in (permissionlists or [])[:15]:
        cn = pl.get("classid")
        if cn:
            add_node(nodes, graph_node("permissionlist", cn, pl))
            edges.append(graph_edge("role", resolved_name, "permissionlist", cn, "grants"))

    return canonical_base(
        env, "role", resolved_name,
        display_name=resolved_name,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/role/{resolved_name}",
            "admin": object_url("role", resolved_name),
            "explorer": f"/admin/role/{resolved_name}",
            "graph": graph_url("role", resolved_name),
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("role", {}),
            "raw": detail or {},
        },
    )


def sections_for_role(role):
    rels = role.get("_relationships", {})
    meta = role.get("_metadata", {})
    raw = meta.get("raw", {})
    members = rels.get("members", [])
    permissionlists = rels.get("permissionlists", [])
    graph_nodes = role.get("_graph", {}).get("nodes", [])
    graph_edges = role.get("_graph", {}).get("edges", [])

    sections = [
        {"name": "Definition", "items": [], "data": {
            "rolename": role["name"],
            "description": role.get("description") or "",
            "roletype": raw.get("roletype_label") or raw.get("roletype") or "",
            "rolestatus": raw.get("rolestatus_label") or raw.get("rolestatus") or "",
            "allownotify": raw.get("allownotify"),
            "allowlookup": raw.get("allowlookup"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
    ]

    # Dynamic membership: show query/PeopleCode/LDAP rule when role type is dynamic
    qryname = str(raw.get("qryname") or "").strip()
    pc_func = str(raw.get("pc_function_name") or "").strip()
    ldap_on = str(raw.get("ldap_rule_on") or raw.get("ldap_rule_on") or "").strip().upper()
    role_query_on = str(raw.get("role_query_rule_on") or "").strip().upper()
    role_pcode_on = str(raw.get("role_pcode_rule_on") or "").strip().upper()
    roletype = str(raw.get("roletype") or "").strip().upper()
    if roletype in ("Q", "P") or qryname or pc_func or ldap_on == "Y" or role_query_on == "Y" or role_pcode_on == "Y":
        dynamic_items = []
        rule_type = raw.get("roletype_label") or roletype or ("Dynamic Query" if role_query_on == "Y" else "Dynamic Role")
        security_query = str(raw.get("qryname_sec") or "").strip()
        if qryname:
            dynamic_items.append({
                "type": "query", "name": qryname,
                "label": f"Membership Query: {qryname}",
                "_links": {"admin": object_url("query", qryname)},
            })
        if security_query:
            dynamic_items.append({
                "type": "query", "name": security_query,
                "label": f"Security Query: {security_query}",
                "_links": {"admin": object_url("query", security_query)},
            })
        if pc_func:
            dynamic_items.append({
                "label": f"PeopleCode Function: {pc_func}",
                "name": pc_func,
            })
        pc_event_type = str(raw.get("pc_event_type") or "").strip()
        if pc_event_type:
            dynamic_items.append({
                "label": f"PeopleCode Event: {pc_event_type}",
                "name": pc_event_type,
            })
        if ldap_on == "Y":
            dynamic_items.append({"label": "LDAP Rule: Enabled", "name": "ldap"})
        recname = str(raw.get("recname") or "").strip()
        fieldname = str(raw.get("fieldname") or "").strip()
        if recname:
            dynamic_items.append({
                "label": f"Drives from field: {recname}.{fieldname}" if fieldname else f"Drives from record: {recname}",
                "type": "record", "name": recname,
                "_links": {"admin": object_url("record", recname)},
            })
        sections.append({
            "name": "Dynamic Membership",
            "items": dynamic_items,
            "data": {
                "rule_type": rule_type,
                "note": f"Membership is automatically managed ({rule_type}). Static members may also exist.",
            },
        })

    sections += [
        {"name": "Members", "items": members, "data": {"count": len(members)}},
        {"name": "Permission Lists", "items": permissionlists,
         "data": {"count": len(permissionlists), "note": "" if permissionlists else "PSROLECLASS not accessible"}},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": role.get("warnings", []),
         "data": {"count": len(role.get("warnings", []))}},
    ]
    return sections


def role_payload(role):
    meta = role.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": role["type"],
        "name": role["name"],
        "title": role["display_name"],
        "overview": {
            "id": role["id"],
            "display_name": role["display_name"],
            "description": role.get("description") or "",
            "status": role["status"],
            **raw,
        },
        "sections": sections_for_role(role),
        "_links": role["_links"],
        "_uom": role,
    }


def permissionlist_object(env, classid):
    """Build a UOM canonical object for a PeopleSoft Permission List (PSCLASSDEFN)."""
    classid = classid.upper()
    warnings = []

    detail, d_warn = safe_relationship("permissionlist_detail", lambda: psdb.permissionlist(env, classid))
    warnings.extend(d_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "not_found"
    description = ""
    if detail:
        description = (detail.get("classdefndesc") or detail.get("descr") or "").strip()

    roles, r_warn = safe_relationship("permissionlist_roles", lambda: psdb.permissionlist_roles(env, classid))
    menus, m_warn = safe_relationship("permissionlist_menus", lambda: psdb.permissionlist_menus(env, classid))
    components, c_warn = safe_relationship("permissionlist_components", lambda: psdb.permissionlist_components(env, classid))
    page_grants, pg_warn = safe_relationship("permissionlist_page_grants", lambda: psdb.permissionlist_page_grants(env, classid, limit=2000))
    warnings.extend(r_warn)
    warnings.extend(m_warn)
    warnings.extend(c_warn)
    warnings.extend(pg_warn)

    relationships = {
        "roles": [attach_object_links(r, env) for r in (roles or [])],
        "menus": [attach_object_links(m, env) for m in (menus or [])],
        "components": [attach_object_links(c, env) for c in (components or [])],
        "page_grants": page_grants or [],
    }

    nodes = {}
    edges = []
    add_node(nodes, graph_node("permissionlist", classid, detail or {}))
    for role in (roles or [])[:25]:
        rn = role.get("rolename")
        if rn:
            add_node(nodes, graph_node("role", rn, role))
            edges.append(graph_edge("role", rn, "permissionlist", classid, "contains_permissionlist"))
    for component in (components or [])[:40]:
        cn = component.get("pnlgrpname")
        if cn:
            add_node(nodes, graph_node("component", cn, component))
            edges.append(graph_edge("permissionlist", classid, "component", cn, "secures_component"))

    return canonical_base(
        env, "permissionlist", classid,
        display_name=classid,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/peoplesoft/permissionlists/{classid}",
            "admin": object_url("permissionlist", classid),
            "explorer": f"/admin/security?permissionlist={classid}",
            "graph": graph_url("permissionlist", classid),
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("permissionlist", {}),
            "raw": detail or {},
        },
    )


def _group_page_grants(page_grants):
    """Flatten PSAUTHITEM page-grant rows into a leveled list for Object Explorer rendering.

    Returns component header rows (level=0) interleaved with page rows (level=1).
    Uses `relationship` field for action chips and counts.
    """
    groups = {}
    order = []
    for row in page_grants:
        comp = row.get("baritemname") or ""
        if comp not in groups:
            groups[comp] = []
            order.append(comp)
        groups[comp].append(row)

    result = []
    for comp in order:
        rows = groups[comp]
        result.append({
            "name": comp,
            "pnlgrpname": comp,
            "relationship": f"{len(rows)} pages",
            "level": 0,
        })
        for r in rows:
            actions = ", ".join(r.get("decoded_actions") or [])
            result.append({
                "name": r.get("pnlitemname") or "",
                "pnlname": r.get("pnlitemname") or "",
                "relationship": actions if actions else ("Display Only" if r.get("displayonly") else ""),
                "level": 1,
            })
    return result


def sections_for_permissionlist(pl):
    rels = pl.get("_relationships", {})
    meta = pl.get("_metadata", {})
    raw = meta.get("raw", {})
    roles = rels.get("roles", [])
    menus = rels.get("menus", [])
    components = rels.get("components", [])
    page_grants = rels.get("page_grants", [])
    graph_nodes = pl.get("_graph", {}).get("nodes", [])
    graph_edges = pl.get("_graph", {}).get("edges", [])
    sections = [
        {"name": "Definition", "items": [], "data": {
            "classid": pl["name"],
            "description": pl.get("description") or "",
            "descr": raw.get("descr") or "",
            "classdefndesc": raw.get("classdefndesc") or "",
            "timeout_minutes": raw.get("timeoutminutes"),
            "start_app_server": raw.get("startappserver"),
            "allow_password_email": raw.get("allowpswdemail"),
            "version": raw.get("version"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
    ]

    dynamic_sw = str(raw.get("dynamic_sw") or "").strip().upper()
    if dynamic_sw == "Y":
        sections.append({
            "name": "Dynamic Membership",
            "items": [{"label": "Dynamic permission-list membership is enabled", "name": pl["name"]}],
            "data": {
                "rule_type": dynamic_sw,
                "note": "Some permission-list access paths may be derived dynamically from the underlying security configuration.",
            },
        })

    sections += [
        {"name": "Roles", "items": roles,
         "data": {"count": len(roles), "note": "" if roles else "PSROLECLASS not accessible or no roles assigned"}},
        {"name": "Menus", "items": menus,
         "data": {"count": len(menus), "note": "" if menus else "PSAUTHITEM not accessible or no menus granted"}},
        {"name": "Components", "items": [
            {**c, "relationship": ", ".join(c.get("decoded_actions") or [])}
            for c in components
        ], "data": {"count": len(components), "note": "" if components else "PSAUTHITEM/PSPNLGRPDEFN not accessible or no components granted"}},
        {"name": "Page Grants", "items": _group_page_grants(page_grants),
         "data": {
             "count": len(page_grants),
             "component_count": len({r.get("baritemname") for r in page_grants if r.get("baritemname")}),
             "note": "" if page_grants else "PSAUTHITEM not accessible or no page-level grants found",
         }},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": pl.get("warnings", []),
         "data": {"count": len(pl.get("warnings", []))}},
    ]
    return sections


def permissionlist_payload(pl):
    meta = pl.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": pl["type"],
        "name": pl["name"],
        "title": pl["display_name"],
        "overview": {
            "id": pl["id"],
            "display_name": pl["display_name"],
            "description": pl.get("description") or "",
            "status": pl["status"],
            **raw,
        },
        "sections": sections_for_permissionlist(pl),
        "_links": pl["_links"],
        "_uom": pl,
    }


def component_object(env, component_name):
    """Build a UOM canonical object for a PeopleSoft Component (PSPNLGRPDEFN)."""
    component_name = component_name.upper()
    warnings = []

    detail, d_warn = safe_relationship("component_detail", lambda: psdb.component(env, component_name))
    warnings.extend(d_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "partial"
    raw = detail or {
        "pnlgrpname": component_name,
        "metadata_status": "Component metadata unavailable",
    }
    description = (raw.get("descr") or "").strip()

    pages, page_warn = safe_relationship("component_pages", lambda: psdb.component_pages(env, component_name))
    permissionlists, pl_warn = safe_relationship("component_permissionlists", lambda: psdb.component_permissionlists(env, component_name))
    menu_placements, menu_warn = safe_relationship("component_menu_placements", lambda: psdb.component_menu_placements(env, component_name))
    menus, cmenu_warn = safe_relationship("component_menus", lambda: psdb.component_menus(env, component_name))
    page_records, record_warn = safe_relationship("component_records_used_by_pages", lambda: psdb.component_records_used_by_pages(env, component_name))
    portal_refs, portal_warn = safe_relationship("component_portal_refs", lambda: psdb.component_portal_refs(env, component_name))
    related_content, rc_warn = safe_relationship("component_related_content", lambda: psdb.component_related_content(env, component_name))
    event_mapping, event_warn = safe_relationship("component_event_mapping", lambda: psdb.component_event_mapping(env, component_name))
    drop_zones, dz_warn = safe_relationship("component_drop_zones", lambda: psdb.component_drop_zones(env, component_name))
    access_result, access_warn = safe_relationship("component_access", lambda: psdb.component_access(env, component_name))
    page_hierarchy, hier_warn = safe_relationship("component_page_hierarchy", lambda: psdb.component_page_hierarchy(env, component_name))
    warnings.extend(page_warn + pl_warn + menu_warn + cmenu_warn + record_warn + portal_warn + rc_warn + event_warn + dz_warn + access_warn + hier_warn)

    search_records = []
    for key in ("searchrecname", "addsrchrecname"):
        recname = raw.get(key)
        if recname:
            search_records.append({"recname": recname, "usage": key})

    # Component PeopleCode: objectid1=9 (event-level, OV1=pnlgrpname) and
    # objectid1=10 (record/field-level, OV1=pnlgrpname)
    pc_items = []
    if ptmetadata.has_table(env, "PSPCMPROG"):
        try:
            pc_cols = psdb.select_existing_columns(
                env, "PSPCMPROG",
                ["OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3",
                 "OBJECTVALUE4", "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
                 "PROGSEQ", "LASTUPDDTTM", "LASTUPDOPRID"],
                required=["OBJECTVALUE1"],
            )
            pc_rows = psdb.query(env, f"""
                SELECT {", ".join(pc_cols)}
                  FROM SYSADM.PSPCMPROG
                 WHERE OBJECTID1 IN (9, 10)
                   AND upper(OBJECTVALUE1) = upper(:pnlgrpname)
                 ORDER BY OBJECTID1, OBJECTVALUE2, OBJECTVALUE3
                 FETCH FIRST 500 ROWS ONLY
            """, {"pnlgrpname": component_name})
            for row in pc_rows:
                normalized = peoplecode.normalize_program(row)
                enc = normalized.get("encoded_reference")
                if enc:
                    normalized["_links"] = {"admin": f"/admin/object/peoplecode/{enc}"}
                pc_items.append(normalized)
        except Exception:
            pass

    relationships = {
        "pages": [attach_object_links(row, env) for row in (pages or [])],
        "page_hierarchy": page_hierarchy or [],
        "search_records": [attach_object_links(row, env) for row in search_records],
        "page_records": [attach_object_links(row, env) for row in (page_records or [])],
        "menu_placements": [attach_object_links(row, env) for row in (menu_placements or [])],
        "menus": [
            {**attach_object_links(row, env), "_links": {"admin": object_url("menu", str(row.get("menuname") or "").strip())}}
            for row in (menus or [])
        ],
        "portal_refs": [attach_object_links(row, env) for row in (portal_refs or [])],
        "permissionlists": [attach_object_links(row, env) for row in (permissionlists or [])],
        "security": [attach_object_links(row, env) for row in (access_result or [])],
        "related_content": [attach_object_links(row, env) for row in (related_content or [])],
        "event_mapping": [attach_object_links(row, env) for row in (event_mapping or [])],
        "drop_zones": [attach_object_links(row, env) for row in (drop_zones or [])],
        "peoplecode": pc_items,
    }

    users = sorted({row.get("roleuser") for row in (access_result or []) if row.get("roleuser")})
    roles = sorted({row.get("rolename") for row in (access_result or []) if row.get("rolename")})

    nodes = {}
    edges = []
    add_node(nodes, graph_node("component", component_name, raw))
    for page in (pages or [])[:30]:
        page_name = str(page.get("pnlname") or "").strip()
        if page_name:
            add_node(nodes, graph_node("page", page_name, page))
            edges.append(graph_edge("component", component_name, "page", page_name, "contains_page"))
    for record in search_records[:10]:
        recname = str(record.get("recname") or "").strip()
        if recname:
            add_node(nodes, graph_node("record", recname, record))
            edges.append(graph_edge("component", component_name, "record", recname, record.get("usage") or "uses_record"))
    for record in (page_records or [])[:30]:
        recname = str(record.get("recname") or "").strip()
        if recname:
            add_node(nodes, graph_node("record", recname, record))
            edges.append(graph_edge("component", component_name, "record", recname, "uses_page_record"))
    for pl in (permissionlists or [])[:40]:
        classid = pl.get("classid")
        if classid:
            add_node(nodes, graph_node("permissionlist", classid, pl))
            edges.append(graph_edge("permissionlist", classid, "component", component_name, "secures_component"))
    for row in (access_result or [])[:60]:
        role = row.get("rolename")
        oprid = row.get("roleuser")
        classid = row.get("classid")
        if role and classid:
            add_node(nodes, graph_node("role", role, row))
            edges.append(graph_edge("role", role, "permissionlist", classid, "contains_permissionlist"))
        if oprid and role:
            add_node(nodes, graph_node("operator", oprid, row))
            edges.append(graph_edge("operator", oprid, "role", role, "has_role"))

    return canonical_base(
        env, "component", component_name,
        display_name=component_name,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/peoplesoft/components/{component_name}",
            "admin": object_url("component", component_name),
            "graph": graph_url("component", component_name),
            "security": f"/api/peoplesoft/security/components/{component_name}/access?env={env}",
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("component", {}),
            "raw": raw,
            "counts": {
                "pages": len(pages or []),
                "menu_placements": len(menu_placements or []),
                "permissionlists": len(permissionlists or []),
                "operators": len(users),
                "roles": len(roles),
                "page_records": len(page_records or []),
                "portal_refs": len(portal_refs or []),
                "peoplecode": len(pc_items),
            },
        },
    )


def sections_for_component(component):
    rels = component.get("_relationships", {})
    meta = component.get("_metadata", {})
    raw = meta.get("raw", {})
    counts = meta.get("counts", {})
    graph_nodes = component.get("_graph", {}).get("nodes", [])
    graph_edges = component.get("_graph", {}).get("edges", [])
    security_rows = rels.get("security", [])
    access_summary = _access_summary(security_rows)
    return [
        {"name": "Definition", "items": [], "data": {
            "pnlgrpname": component["name"],
            "description": component.get("description") or "",
            "market": raw.get("market") or "",
            "searchrecname": raw.get("searchrecname") or "",
            "addsrchrecname": raw.get("addsrchrecname") or "",
            "version": raw.get("version"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
            **counts,
        }},
        {"name": "Pages", "items": rels.get("page_hierarchy") or rels.get("pages", []), "data": {
            "count": len(rels.get("pages", [])),
            "note": "Indented items show subpages and grids within each page" if rels.get("page_hierarchy") else "",
        }},
        {"name": "Search Records", "items": rels.get("search_records", []), "data": {"count": len(rels.get("search_records", []))}},
        {"name": "Records Used By Pages", "items": rels.get("page_records", []), "data": {"count": len(rels.get("page_records", []))}},
        {"name": "Menus", "items": [
            {**r, "relationship": str(r.get("menu_descr") or r.get("barname") or "").strip()}
            for r in rels.get("menus", [])
        ], "data": {"count": len(rels.get("menus", []))}},
        {"name": "Menu Placement", "items": rels.get("menu_placements", []), "data": {"count": len(rels.get("menu_placements", []))}},
        {"name": "Portal Registry", "items": [
            {**r, "relationship": r.get("nav_path") or r.get("portal_name") or ""}
            for r in rels.get("portal_refs", [])
        ], "data": {"count": len(rels.get("portal_refs", []))}},
        {"name": "Permission Lists", "items": [
            {**r, "relationship": ", ".join(psdb.decode_authorized_actions(
                r.get("authorizedactions"), r.get("displayonly")
            ).get("decoded_actions") or [])}
            for r in rels.get("permissionlists", [])
        ], "data": {"count": len(rels.get("permissionlists", []))}},
        {"name": "Who Has Access", "items": access_summary, "data": {
            "total_paths": len(security_rows),
            "permissionlists": counts.get("permissionlists", 0),
            "roles": counts.get("roles", 0),
            "operators": counts.get("operators", 0),
        }},
        {"name": "Related Content", "items": rels.get("related_content", []), "data": {"count": len(rels.get("related_content", []))}},
        {"name": "Event Mapping", "items": rels.get("event_mapping", []), "data": {"count": len(rels.get("event_mapping", []))}},
        {"name": "Drop Zones", "items": rels.get("drop_zones", []), "data": {"count": len(rels.get("drop_zones", []))}},
        {"name": "PeopleCode", "items": rels.get("peoplecode", []), "data": {
            "count": len(rels.get("peoplecode", [])),
            "note": "objectid1=9 (component event) and objectid1=10 (record/field event)" if rels.get("peoplecode") else "",
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": component.get("warnings", []), "data": {"count": len(component.get("warnings", []))}},
    ]


def component_payload(component):
    meta = component.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": component["type"],
        "name": component["name"],
        "title": component["display_name"],
        "overview": {
            "id": component["id"],
            "display_name": component["display_name"],
            "description": component.get("description") or "",
            "status": component["status"],
            **raw,
            **meta.get("counts", {}),
        },
        "sections": sections_for_component(component),
        "_links": component["_links"],
        "_uom": component,
    }


def page_object(env, page_name):
    """Build a UOM canonical object for a PeopleSoft Page (PSPNLDEFN)."""
    page_name = page_name.upper()
    warnings = []

    detail, d_warn = safe_relationship("page_detail", lambda: psdb.page(env, page_name))
    warnings.extend(d_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "partial"
    raw = detail or {
        "pnlname": page_name,
        "metadata_status": "Page metadata unavailable",
    }
    description = (raw.get("descr") or "").strip()

    components, component_warn = safe_relationship("page_components", lambda: psdb.page_components(env, page_name))
    records, record_warn = safe_relationship("page_records", lambda: psdb.page_records(env, page_name))
    fields, field_warn = safe_relationship("page_fields", lambda: psdb.page_fields(env, page_name))
    scroll, scroll_warn = safe_relationship("page_scroll_structure", lambda: psdb.page_scroll_structure(env, page_name))
    grids, grid_warn = safe_relationship("page_grids", lambda: psdb.page_grids(env, page_name))
    subpages, subpage_warn = safe_relationship("page_subpages", lambda: psdb.page_subpages(env, page_name))
    event_mapping, event_warn = safe_relationship("page_event_mapping", lambda: psdb.page_event_mapping(env, page_name))
    related_content, rc_warn = safe_relationship("page_related_content", lambda: psdb.page_related_content(env, page_name))
    drop_zones, dz_warn = safe_relationship("page_drop_zones", lambda: psdb.page_drop_zones(env, page_name))
    transfers, transfer_warn = safe_relationship("page_transfers", lambda: psdb.page_transfers(env, page_name))
    warnings.extend(component_warn + record_warn + field_warn + scroll_warn + grid_warn + subpage_warn + event_warn + rc_warn + dz_warn + transfer_warn)

    # PeopleCode: load component PeopleCode (objectid1=9/10) for each parent component.
    # Pages do not own PeopleCode directly — it is attached at the component level.
    pc_items = []
    if ptmetadata.has_table(env, "PSPCMPROG"):
        parent_comp_names = list({
            str(r.get("pnlgrpname") or "").strip().upper()
            for r in (components or [])
            if str(r.get("pnlgrpname") or "").strip()
        })
        try:
            pc_cols = psdb.select_existing_columns(
                env, "PSPCMPROG",
                ["OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3",
                 "OBJECTVALUE4", "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7",
                 "PROGSEQ", "LASTUPDDTTM", "LASTUPDOPRID"],
                required=["OBJECTVALUE1"],
            )
            for comp_name in parent_comp_names[:10]:
                pc_rows = psdb.query(env, f"""
                    SELECT {", ".join(pc_cols)}
                      FROM SYSADM.PSPCMPROG
                     WHERE OBJECTID1 IN (9, 10)
                       AND upper(OBJECTVALUE1) = upper(:comp_name)
                     ORDER BY OBJECTID1, OBJECTVALUE2, OBJECTVALUE3
                     FETCH FIRST 200 ROWS ONLY
                """, {"comp_name": comp_name})
                for row in pc_rows:
                    normalized = peoplecode.normalize_program(row)
                    normalized["_source_component"] = comp_name
                    enc = normalized.get("encoded_reference")
                    if enc:
                        normalized["_links"] = {"admin": f"/admin/object/peoplecode/{enc}"}
                    pc_items.append(normalized)
        except Exception:
            pass

    security_items = []
    permissionlists = {}
    roles = {}
    operators = {}
    for component_row in components or []:
        component_name = component_row.get("pnlgrpname")
        if not component_name:
            continue
        access_rows, access_warn = safe_relationship(
            f"page_component_access:{component_name}",
            lambda component_name=component_name: psdb.component_access(env, component_name),
        )
        warnings.extend(access_warn)
        for access_row in access_rows:
            linked = {"pnlgrpname": component_name, **access_row}
            security_items.append(linked)
            if access_row.get("classid"):
                permissionlists[access_row["classid"]] = True
            if access_row.get("rolename"):
                roles[access_row["rolename"]] = True
            if access_row.get("roleuser"):
                operators[access_row["roleuser"]] = True

    relationships = {
        "components": [attach_object_links(row, env) for row in (components or [])],
        "records": [attach_object_links(row, env) for row in (records or [])],
        "fields": [attach_object_links(row, env) for row in (fields or [])],
        "scroll_structure": [attach_object_links(row, env) for row in (scroll or [])],
        "grids": [attach_object_links(row, env) for row in (grids or [])],
        "subpages": [attach_object_links(row, env) for row in (subpages or [])],
        "peoplecode": pc_items,
        "event_mapping": [attach_object_links(row, env) for row in (event_mapping or [])],
        "related_content": [attach_object_links(row, env) for row in (related_content or [])],
        "drop_zones": [attach_object_links(row, env) for row in (drop_zones or [])],
        "transfers": [attach_object_links(row, env) for row in (transfers or [])],
        "security": [attach_object_links(row, env) for row in security_items],
    }

    graph_relationships = limit_relationships(relationships, {
        "components": 20,
        "records": 30,
        "fields": 40,
        "subpages": 20,
    })
    graph_relationships["permissionlists"] = [
        {"classid": classid}
        for classid in sorted(permissionlists)[:40]
    ]
    graph = relationship_graph("page", page_name, graph_relationships, [
        {
            "relationship": "components",
            "node_type": "page",
            "source_node_type": "component",
            "source_name": lambda row: str(row.get("pnlgrpname") or "").strip(),
            "target_name": lambda row: page_name,
            "default_edge": "contains_page",
        },
        {
            "relationship": "records",
            "node_type": "record",
            "target_name": lambda row: str(row.get("recname") or "").strip(),
            "default_edge": "uses_record",
        },
        {
            "relationship": "fields",
            "node_type": "field",
            "target_name": lambda row: (
                f"{str(row.get('recname') or '').strip()}.{str(row.get('fieldname') or '').strip()}"
                if str(row.get("recname") or "").strip() and str(row.get("fieldname") or "").strip()
                else ""
            ),
            "default_edge": "contains_field",
        },
        {
            "relationship": "subpages",
            "node_type": "page",
            "target_name": lambda row: str(row.get("pnlname") or "").strip(),
            "default_edge": "contains_subpage",
        },
        {
            "relationship": "permissionlists",
            "node_type": "page",
            "source_node_type": "permissionlist",
            "source_name": lambda row: str(row.get("classid") or "").strip(),
            "target_name": lambda row: page_name,
            "default_edge": "secures_page",
        },
    ], root_data=raw)

    return canonical_base(
        env, "page", page_name,
        display_name=page_name,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/peoplesoft/pages/{page_name}",
            "admin": object_url("page", page_name),
            "graph": graph_url("page", page_name),
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("page", {}),
            "raw": raw,
            "counts": {
                "components": len(components or []),
                "records": len(records or []),
                "fields": len(fields or []),
                "visible_fields": sum(1 for row in (fields or []) if str(row.get("invisible") or "0").upper() not in {"1", "Y", "YES", "T", "TRUE"}),
                "invisible_fields": sum(1 for row in (fields or []) if str(row.get("invisible") or "0").upper() in {"1", "Y", "YES", "T", "TRUE"}),
                "display_only_fields": sum(1 for row in (fields or []) if str(row.get("displayonly") or "0").upper() in {"1", "Y", "YES", "T", "TRUE"}),
                "subpages": len(subpages or []),
                "grids": len(grids or []),
                "permissionlists": len(permissionlists),
                "roles": len(roles),
                "operators": len(operators),
                "access_paths": len(security_items),
            },
        },
    )


def sections_for_page(page_obj):
    rels = page_obj.get("_relationships", {})
    meta = page_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    counts = meta.get("counts", {})
    graph_nodes = page_obj.get("_graph", {}).get("nodes", [])
    graph_edges = page_obj.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "pnlname": page_obj["name"],
            "description": page_obj.get("description") or "",
            "pnltype": raw.get("pnltype"),
            "version": raw.get("version"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
            **counts,
        }},
        {"name": "Components", "items": rels.get("components", []), "data": {"count": len(rels.get("components", []))}},
        {"name": "Records", "items": rels.get("records", []), "data": {"count": len(rels.get("records", []))}},
        {"name": "Fields", "items": rels.get("fields", []), "data": {
            "count": len(rels.get("fields", [])),
            "visible": counts.get("visible_fields", 0),
            "invisible": counts.get("invisible_fields", 0),
            "display_only": counts.get("display_only_fields", 0),
        }},
        {"name": "Scroll Structure", "items": rels.get("scroll_structure", []), "data": {"count": len(rels.get("scroll_structure", []))}},
        {"name": "Grids", "items": rels.get("grids", []), "data": {"count": len(rels.get("grids", []))}},
        {"name": "Subpages", "items": rels.get("subpages", []), "data": {"count": len(rels.get("subpages", []))}},
        {"name": "PeopleCode", "items": rels.get("peoplecode", []), "data": {"count": len(rels.get("peoplecode", []))}},
        {"name": "Event Mapping", "items": rels.get("event_mapping", []), "data": {"count": len(rels.get("event_mapping", []))}},
        {"name": "Related Content", "items": rels.get("related_content", []), "data": {"count": len(rels.get("related_content", []))}},
        {"name": "Drop Zones", "items": rels.get("drop_zones", []), "data": {"count": len(rels.get("drop_zones", []))}},
        {"name": "Transfers", "items": rels.get("transfers", []), "data": {"count": len(rels.get("transfers", []))}},
        {"name": "Who Has Access", "items": _access_summary(rels.get("security", [])), "data": {
            "total_paths": counts.get("access_paths", 0),
            "components": counts.get("components", 0),
            "permissionlists": counts.get("permissionlists", 0),
            "roles": counts.get("roles", 0),
            "operators": counts.get("operators", 0),
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": page_obj.get("warnings", []), "data": {"count": len(page_obj.get("warnings", []))}},
    ]


def page_payload(page_obj):
    meta = page_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": page_obj["type"],
        "name": page_obj["name"],
        "title": page_obj["display_name"],
        "overview": {
            "id": page_obj["id"],
            "display_name": page_obj["display_name"],
            "description": page_obj.get("description") or "",
            "status": page_obj["status"],
            **raw,
            **meta.get("counts", {}),
        },
        "sections": sections_for_page(page_obj),
        "_links": page_obj["_links"],
        "_uom": page_obj,
    }


def portal_registry_object(env, portal_objname):
    """Build a UOM canonical object for a PeopleSoft Portal Registry content reference."""
    portal_objname = portal_objname.upper()
    warnings = []

    detail, detail_warn = safe_relationship("portal_registry_ref", lambda: psdb.portal_registry_ref(env, portal_objname))
    warnings.extend(detail_warn)
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    status = "available" if detail else "partial"
    raw = detail or {
        "portal_objname": portal_objname,
        "metadata_status": "Portal registry metadata unavailable",
    }
    portal_name = raw.get("portal_name")
    description = (raw.get("portal_label") or raw.get("descr254") or "").strip()

    children, child_warn = safe_relationship(
        "portal_registry_children",
        lambda: psdb.portal_registry_children(env, portal_objname, portal_name),
    )
    breadcrumbs, crumb_warn = safe_relationship(
        "portal_registry_breadcrumbs",
        lambda: psdb.portal_registry_breadcrumbs(env, portal_objname, portal_name),
    )
    component_targets, component_warn = safe_relationship(
        "portal_registry_component_targets",
        lambda: psdb.portal_registry_component_targets(env, raw),
    )
    attributes, attr_warn = safe_relationship(
        "portal_registry_attributes",
        lambda: psdb.portal_registry_attributes(env, portal_objname, portal_name),
    )
    permissions, perm_warn = safe_relationship(
        "portal_registry_permissions",
        lambda: psdb.portal_registry_permissions(env, portal_objname, portal_name),
    )
    access_paths, access_warn = safe_relationship(
        "portal_registry_access",
        lambda: psdb.portal_registry_access(env, portal_objname, portal_name),
    )
    warnings.extend(child_warn + crumb_warn + component_warn + attr_warn + perm_warn + access_warn)

    relationships = {
        "breadcrumbs": [attach_object_links(row, env) for row in (breadcrumbs or [])],
        "children": [attach_object_links(row, env) for row in (children or [])],
        "component_targets": [attach_object_links(row, env) for row in (component_targets or [])],
        "attributes": [attach_object_links(row, env) for row in (attributes or [])],
        "permissions": [attach_object_links(row, env) for row in (permissions or [])],
        "access_paths": [attach_object_links(row, env) for row in (access_paths or [])],
    }

    nodes = {}
    edges = []
    add_node(nodes, graph_node("portal_registry", portal_objname, raw))

    previous = None
    for row in breadcrumbs or []:
        name = str(row.get("portal_objname") or "").strip()
        if not name:
            continue
        add_node(nodes, graph_node("portal_registry", name, row))
        if previous and previous != name:
            edges.append(graph_edge("portal_registry", previous, "portal_registry", name, "contains"))
        previous = name

    for row in (children or [])[:50]:
        child_name = str(row.get("portal_objname") or "").strip()
        if child_name:
            add_node(nodes, graph_node("portal_registry", child_name, row))
            edges.append(graph_edge("portal_registry", portal_objname, "portal_registry", child_name, "contains"))

    for row in component_targets or []:
        component_name = str(row.get("pnlgrpname") or "").strip()
        if component_name:
            add_node(nodes, graph_node("component", component_name, row))
            edges.append(graph_edge("portal_registry", portal_objname, "component", component_name, "launches_component"))
    for row in (permissions or [])[:60]:
        permtype = str(row.get("portal_permtype") or "").upper()
        classid = str(row.get("classid") or "").strip()
        rolename = str(row.get("rolename") or "").strip()
        if permtype == "P" and classid:
            add_node(nodes, graph_node("permissionlist", classid, row))
            edges.append(graph_edge("permissionlist", classid, "portal_registry", portal_objname, "secures_portal"))
        elif permtype == "R" and rolename:
            add_node(nodes, graph_node("role", rolename, row))
            edges.append(graph_edge("role", rolename, "portal_registry", portal_objname, "secures_portal"))
    for row in (access_paths or [])[:80]:
        classid = str(row.get("classid") or "").strip()
        rolename = str(row.get("rolename") or "").strip()
        roleuser = str(row.get("roleuser") or "").strip()
        if classid and rolename:
            add_node(nodes, graph_node("role", rolename, row))
            edges.append(graph_edge("role", rolename, "permissionlist", classid, "contains_permissionlist"))
        if roleuser and rolename:
            add_node(nodes, graph_node("operator", roleuser, row))
            edges.append(graph_edge("operator", roleuser, "role", rolename, "has_role"))

    return canonical_base(
        env, "portal_registry", portal_objname,
        display_name=raw.get("portal_label") or portal_objname,
        description=description,
        status=status,
        warnings=[w for w in warnings if w],
        _links={
            "self": f"/api/peoplesoft/portal-registry/{portal_objname}",
            "admin": object_url("portal_registry", portal_objname),
            "graph": graph_url("portal_registry", portal_objname),
            "compare": f"/api/envcompare/portal-object?name={portal_objname}",
        },
        _relationships=relationships,
        _graph={"nodes": list(nodes.values()), "edges": edges},
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("portal_registry", {}),
            "raw": raw,
            "counts": {
                "breadcrumbs": len(breadcrumbs or []),
                "children": len(children or []),
                "component_targets": len(component_targets or []),
                "attributes": len(attributes or []),
                "permissions": len(permissions or []),
                "access_paths": len(access_paths or []),
                "permissionlists": len({row.get("classid") for row in (permissions or []) if row.get("classid")}),
                "roles": len({
                    row.get("rolename")
                    for row in list(permissions or []) + list(access_paths or [])
                    if row.get("rolename")
                }),
                "operators": len({row.get("roleuser") for row in (access_paths or []) if row.get("roleuser")}),
            },
        },
    )


def _portal_label_items(items, use_reftype_chip=False):
    """Add title and optional relationship chip to portal registry rows for the generic renderer."""
    out = []
    for row in (items or []):
        r = dict(row)
        if not r.get("title") and not r.get("label"):
            r["title"] = (r.get("portal_label") or r.get("classid") or
                          r.get("pnlgrpname") or r.get("portal_permname") or
                          r.get("rolename") or r.get("roleuser") or
                          r.get("portal_objname") or "")
        if use_reftype_chip and not r.get("relationship") and r.get("portal_reftype"):
            r["relationship"] = psdb.PORTAL_REFTYPE_LABELS.get(
                str(r["portal_reftype"]).strip().upper(), r["portal_reftype"])
        out.append(r)
    return out


def _access_summary(access_rows, classid_key="classid", role_key="rolename", user_key="roleuser"):
    """
    Group flat access rows (permlist→role→operator) into one row per permission
    list, collecting role names, operator count, and granted actions.
    Applies to component security, page security, and portal access paths.
    """
    groups = {}
    for row in (access_rows or []):
        classid = str(row.get(classid_key) or row.get("portal_permname") or "").strip()
        rolename = str(row.get(role_key) or "").strip()
        roleuser = str(row.get(user_key) or "").strip()
        if not classid:
            continue
        if classid not in groups:
            groups[classid] = {"roles": {}, "actions": set()}
        if rolename:
            groups[classid]["roles"].setdefault(rolename, set())
            if roleuser:
                groups[classid]["roles"][rolename].add(roleuser)
        for act in (row.get("decoded_actions") or []):
            groups[classid]["actions"].add(str(act))

    summary = []
    for classid, info in sorted(groups.items()):
        roles = info["roles"]
        op_count = sum(len(ops) for ops in roles.values())
        role_list = sorted(roles.keys())
        role_sample = ", ".join(role_list[:3])
        if len(role_list) > 3:
            role_sample += f" +{len(role_list) - 3} more"
        item = {
            "classid": classid,
            "title": classid,
            "roles": len(roles),
            "operators": op_count,
            "via_roles": role_sample,
            "_links": {"admin": f"/admin/object/permissionlist/{classid}"},
        }
        if info["actions"]:
            item["actions"] = ", ".join(sorted(info["actions"]))
        summary.append(item)
    return summary


# Keep backward-compatible alias for portal code
_portal_access_summary = _access_summary


def sections_for_portal_registry(portal_obj):
    rels = portal_obj.get("_relationships", {})
    meta = portal_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    counts = meta.get("counts", {})
    graph_nodes = portal_obj.get("_graph", {}).get("nodes", [])
    graph_edges = portal_obj.get("_graph", {}).get("edges", [])

    breadcrumbs = _portal_label_items(rels.get("breadcrumbs", []), use_reftype_chip=True)
    children = _portal_label_items(rels.get("children", []), use_reftype_chip=True)
    component_targets = _portal_label_items(rels.get("component_targets", []))
    permissions = [
        {**r, "relationship": r.get("portal_permtype_label") or ""}
        for r in _portal_label_items(rels.get("permissions", []))
    ]
    access_paths = rels.get("access_paths", [])
    access_summary = _portal_access_summary(access_paths)

    nav_path = " → ".join(
        r.get("portal_label") or r.get("portal_objname") or ""
        for r in breadcrumbs if (r.get("portal_label") or r.get("portal_objname"))
    )

    sections = [
        {"name": "Definition", "items": [], "data": {
            "portal_name": raw.get("portal_name") or "",
            "portal_objname": portal_obj["name"],
            "portal_label": raw.get("portal_label") or "",
            "description": raw.get("descr254") or portal_obj.get("description") or "",
            "navigation_path": nav_path,
            "parent": raw.get("portal_prntobjname") or "",
            "reference_type": raw.get("portal_reftype") or "",
            "reference_type_label": psdb.PORTAL_REFTYPE_LABELS.get(str(raw.get("portal_reftype") or "").strip().upper(), ""),
            "url": raw.get("portal_urltext") or "",
            "uri": ".".join(str(raw.get(key) or "").strip() for key in ("portal_uri_seg1", "portal_uri_seg2", "portal_uri_seg3", "portal_uri_seg4") if str(raw.get(key) or "").strip()),
            "public": raw.get("portal_ispublic"),
            "fluid": raw.get("fluidmode"),
            "owner": raw.get("objectownerid") or "",
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
            **counts,
        }},
        {"name": "Navigation Path", "items": breadcrumbs, "data": {"count": len(breadcrumbs)}},
        {"name": "Children", "items": children, "data": {
            "count": len(children),
            "folders": sum(1 for r in children if str(r.get("portal_reftype") or "").upper() == "F"),
            "content_refs": sum(1 for r in children if str(r.get("portal_reftype") or "").upper() == "C"),
        }},
        {"name": "Target Components", "items": component_targets, "data": {"count": len(component_targets)}},
        {"name": "Attributes", "items": _portal_label_items(rels.get("attributes", [])), "data": {"count": len(rels.get("attributes", []))}},
        {"name": "Portal Security", "items": permissions, "data": {
            "count": len(permissions),
            "permissionlists": counts.get("permissionlists", 0),
            "roles": counts.get("roles", 0),
            "inherited": sum(1 for row in permissions if row.get("inherited")),
        }},
        {"name": "Who Has Access", "items": access_summary, "data": {
            "total_paths": len(access_paths),
            "permissionlists": len(access_summary),
            "operators": counts.get("operators", 0),
            "roles": counts.get("roles", 0),
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": portal_obj.get("warnings", []), "data": {"count": len(portal_obj.get("warnings", []))}},
    ]
    return [s for s in sections if s["items"] or (s["data"] and any(
        v not in (None, "", 0, False, {}) for k, v in s["data"].items() if k != "count"
    ) or s["name"] in ("Definition", "Warnings"))]


def portal_registry_payload(portal_obj):
    meta = portal_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": portal_obj["type"],
        "name": portal_obj["name"],
        "title": portal_obj["display_name"],
        "overview": {
            "id": portal_obj["id"],
            "display_name": portal_obj["display_name"],
            "description": portal_obj.get("description") or "",
            "status": portal_obj["status"],
            **raw,
            **meta.get("counts", {}),
        },
        "sections": sections_for_portal_registry(portal_obj),
        "_links": portal_obj["_links"],
        "_uom": portal_obj,
    }


from connectors import ib as ib_connector  # local import to avoid circular at module level


def _ib_links(explorer_type, name):
    return {
        "self":     f"/api/ib/{explorer_type}/{name}",
        "explorer": f"/admin/ib?tab={explorer_type}&show={name}",
        "admin":    object_url(explorer_type.rstrip("s"), name),
    }


def service_object(env, applname):
    applname = applname.upper()
    warnings = []

    # Try Application Service first (PSIBAPPLDEFN)
    result = ib_connector.service(env, applname)
    item = result.get("item") or {}
    warnings.extend(w for w in result.get("warnings", []) if w)
    operations = item.pop("operations", []) if item else []
    routings = item.pop("routings", []) if item else []
    is_app_service = bool(item)

    # Fall back to traditional IB service operation (PSIBRTNGDEFN.IB_OPERATIONNAME)
    ib_op = None
    if not is_app_service:
        op_result = ib_connector.ib_operation(env, applname)
        warnings.extend(w for w in op_result.get("warnings", []) if w)
        ib_op = op_result.get("item")
        if ib_op:
            routings = op_result.get("routings", [])
            item = ib_op

    pc_result = ib_connector.service_peoplecode(env, applname)
    peoplecode = pc_result.get("items", [])
    warnings.extend(w for w in pc_result.get("warnings", []) if w)

    graph_nodes_map = {}
    edges = []
    svc_node = graph_node("service_operation", applname, item)
    add_node(graph_nodes_map, svc_node)
    for r in routings[:20]:
        rn = r.get("routingdefnname")
        if rn:
            add_node(graph_nodes_map, graph_node("routing", rn, r))
            edges.append(graph_edge("routing", rn, "service_operation", applname, "routes"))
    for r in routings[:20]:
        for side, rel in (("sendernodename", "sends"), ("receivernodename", "receives")):
            nname = r.get(side)
            if nname:
                add_node(graph_nodes_map, graph_node("node", nname, {}))
                edges.append(graph_edge("node" if rel == "sends" else "service_operation",
                                        nname if rel == "sends" else applname,
                                        "service_operation" if rel == "sends" else "node",
                                        applname if rel == "sends" else nname, rel))

    return canonical_base(
        env, "service_operation", applname,
        display_name=applname,
        description=(item.get("descr") or "").strip(),
        status="available" if item else "not_found",
        warnings=warnings,
        _links={**_ib_links("services", applname), "admin": object_url("service_operation", applname)},
        _relationships={"operations": operations, "routings": routings, "peoplecode": peoplecode},
        _graph={"nodes": list(graph_nodes_map.values()), "edges": edges},
        _metadata={"environment": env.upper(), "raw": item, "is_app_service": is_app_service,
                   "registry": ptmetadata.OBJECT_REGISTRY.get("service_operation", {})},
    )


def sections_for_service(svc):
    rels = svc.get("_relationships", {})
    meta = svc.get("_metadata", {})
    raw = meta.get("raw", {})
    is_app_service = meta.get("is_app_service", False)
    operations  = rels.get("operations", [])
    routings    = rels.get("routings", [])
    peoplecode  = rels.get("peoplecode", [])
    gn = svc.get("_graph", {}).get("nodes", [])
    ge = svc.get("_graph", {}).get("edges", [])

    if is_app_service:
        defn_data = {
            "name": svc["name"],
            "description": svc.get("description") or "",
            "type": raw.get("appltype_label") or raw.get("ptibappltype"),
            "status": raw.get("status_label"),
            "service_name": raw.get("ib_servicename") or "",
            "owner": raw.get("objectownerid") or "",
            "app_server_group": raw.get("ptib_appsrvgrp") or "",
            "last_updated": raw.get("lastupddttm") or "",
        }
    else:
        defn_data = {
            "name": svc["name"],
            "routing_count": raw.get("routing_count") or len(routings),
            "queues": ", ".join(raw.get("queues") or []) or "",
            "sender_nodes": ", ".join(raw.get("sender_nodes") or []) or "",
            "receiver_nodes": ", ".join(raw.get("receiver_nodes") or []) or "",
            "note": "Traditional IB service operation — data from PSIBRTNGDEFN",
        }

    return [
        {"name": "Definition", "items": [], "data": defn_data},
        {"name": "Operations", "items": operations, "data": {"count": len(operations)}},
        {"name": "Routings", "items": routings, "data": {"count": len(routings)}},
        {"name": "PeopleCode", "items": peoplecode, "data": {"count": len(peoplecode)}},
        {"name": "Graph Preview", "items": gn, "data": {"edge_count": len(ge)}},
        {"name": "Warnings", "items": svc.get("warnings", []), "data": {"count": len(svc.get("warnings", []))}},
    ]


def service_payload(svc):
    meta = svc.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": svc["type"], "name": svc["name"], "title": svc["display_name"],
        "overview": {"id": svc["id"], "display_name": svc["display_name"],
                     "description": svc.get("description") or "", "status": svc["status"], **raw},
        "sections": sections_for_service(svc),
        "_links": svc["_links"], "_uom": svc,
    }


def node_object(env, nodename):
    nodename = nodename.upper()
    warnings = []
    result = ib_connector.node(env, nodename)
    item = result.get("item") or {}
    warnings.extend(w for w in result.get("warnings", []) if w)
    routings_sender   = item.pop("routings_as_sender", []) if item else []
    routings_receiver = item.pop("routings_as_receiver", []) if item else []

    nodes_g = {}
    edges = []
    add_node(nodes_g, graph_node("node", nodename, item))
    for r in (routings_sender + routings_receiver)[:20]:
        rn = r.get("routingdefnname")
        op = r.get("ib_operationname")
        if rn:
            add_node(nodes_g, graph_node("routing", rn, r))
            edges.append(graph_edge("node", nodename, "routing", rn, "uses"))
        if op:
            add_node(nodes_g, graph_node("service_operation", op, {}))
            edges.append(graph_edge("routing", rn, "service_operation", op, "routes"))

    return canonical_base(
        env, "node", nodename,
        display_name=nodename,
        description=(item.get("descr") or "").strip(),
        status="available" if item else "not_found",
        warnings=warnings,
        _links={**_ib_links("nodes", nodename), "admin": object_url("node", nodename)},
        _relationships={"routings_as_sender": routings_sender, "routings_as_receiver": routings_receiver},
        _graph={"nodes": list(nodes_g.values()), "edges": edges},
        _metadata={"environment": env.upper(), "raw": item,
                   "registry": ptmetadata.OBJECT_REGISTRY.get("node", {})},
    )


def sections_for_node(node_obj):
    rels = node_obj.get("_relationships", {})
    meta = node_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    gn = node_obj.get("_graph", {}).get("nodes", [])
    ge = node_obj.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "nodename": node_obj["name"],
            "description": node_obj.get("description") or "",
            "status": raw.get("active_label"),
            "node_type": raw.get("node_type_label"),
            "tools_release": raw.get("toolsrel") or "",
            "app_release": raw.get("apmsgapprel") or "",
            "local": raw.get("is_local"),
            "default_local": raw.get("is_default"),
            "target_location": raw.get("ib_tgtlocation") or "",
            "gateway": raw.get("conngatewayid") or "",
            "last_updated": raw.get("lastupddttm") or "",
        }},
        {"name": "Sends Via", "items": rels.get("routings_as_sender", []),
         "data": {"count": len(rels.get("routings_as_sender", []))}},
        {"name": "Receives Via", "items": rels.get("routings_as_receiver", []),
         "data": {"count": len(rels.get("routings_as_receiver", []))}},
        {"name": "Graph Preview", "items": gn, "data": {"edge_count": len(ge)}},
        {"name": "Warnings", "items": node_obj.get("warnings", []), "data": {"count": len(node_obj.get("warnings", []))}},
    ]


def node_payload(node_obj):
    meta = node_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": node_obj["type"], "name": node_obj["name"], "title": node_obj["display_name"],
        "overview": {"id": node_obj["id"], "display_name": node_obj["display_name"],
                     "description": node_obj.get("description") or "", "status": node_obj["status"], **raw},
        "sections": sections_for_node(node_obj),
        "_links": node_obj["_links"], "_uom": node_obj,
    }


def queue_object(env, queuename):
    queuename = queuename.upper()
    warnings = []
    result = ib_connector.queue(env, queuename)
    item = result.get("item") or {}
    warnings.extend(w for w in result.get("warnings", []) if w)
    runtime = item.pop("runtime", {}) if item else {}

    return canonical_base(
        env, "queue", queuename,
        display_name=queuename,
        description=(item.get("descr") or "").strip(),
        status="available" if item else "not_found",
        warnings=warnings,
        _links={**_ib_links("queues", queuename), "admin": object_url("queue", queuename)},
        _relationships={"pub_by_status": runtime.get("pub_by_status", []),
                        "sub_by_status": runtime.get("sub_by_status", [])},
        _graph={"nodes": [], "edges": []},
        _metadata={"environment": env.upper(), "raw": item,
                   "registry": ptmetadata.OBJECT_REGISTRY.get("queue", {})},
    )


def sections_for_queue(q_obj):
    rels = q_obj.get("_relationships", {})
    meta = q_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return [
        {"name": "Definition", "items": [], "data": {
            "queuename": q_obj["name"],
            "description": q_obj.get("description") or "",
            "status": raw.get("queuestatus_label"),
            "throughput": raw.get("thruput_label"),
            "priority": raw.get("ptib_queue_pri") or "",
            "archive": raw.get("archive") or "",
            "owner": raw.get("objectownerid") or "",
            "last_updated": raw.get("lastupddttm") or "",
        }},
        {"name": "Pub Status (runtime)", "items": rels.get("pub_by_status", []),
         "data": {"count": len(rels.get("pub_by_status", []))}},
        {"name": "Sub Status (runtime)", "items": rels.get("sub_by_status", []),
         "data": {"count": len(rels.get("sub_by_status", []))}},
        {"name": "Warnings", "items": q_obj.get("warnings", []), "data": {"count": len(q_obj.get("warnings", []))}},
    ]


def queue_payload(q_obj):
    meta = q_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": q_obj["type"], "name": q_obj["name"], "title": q_obj["display_name"],
        "overview": {"id": q_obj["id"], "display_name": q_obj["display_name"],
                     "description": q_obj.get("description") or "", "status": q_obj["status"], **raw},
        "sections": sections_for_queue(q_obj),
        "_links": q_obj["_links"], "_uom": q_obj,
    }


def routing_object(env, rtngname):
    rtngname = rtngname.upper()
    warnings = []
    result = ib_connector.routing(env, rtngname)
    item = result.get("item") or {}
    warnings.extend(w for w in result.get("warnings", []) if w)
    sub_defs = item.pop("sub_definitions", []) if item else []

    nodes_g = {}
    edges = []
    add_node(nodes_g, graph_node("routing", rtngname, item))
    sender   = item.get("sendernodename")
    receiver = item.get("receivernodename")
    op       = item.get("ib_operationname")
    if sender:
        add_node(nodes_g, graph_node("node", sender, {}))
        edges.append(graph_edge("node", sender, "routing", rtngname, "uses"))
    if receiver:
        add_node(nodes_g, graph_node("node", receiver, {}))
        edges.append(graph_edge("routing", rtngname, "node", receiver, "uses"))
    if op:
        add_node(nodes_g, graph_node("service_operation", op, {}))
        edges.append(graph_edge("routing", rtngname, "service_operation", op, "routes"))

    return canonical_base(
        env, "routing", rtngname,
        display_name=rtngname,
        description=(item.get("descr") or "").strip(),
        status="available" if item else "not_found",
        warnings=warnings,
        _links={**_ib_links("routings", rtngname), "admin": object_url("routing", rtngname)},
        _relationships={"sub_definitions": sub_defs},
        _graph={"nodes": list(nodes_g.values()), "edges": edges},
        _metadata={"environment": env.upper(), "raw": item,
                   "registry": ptmetadata.OBJECT_REGISTRY.get("routing", {})},
    )


def sections_for_routing(r_obj):
    rels = r_obj.get("_relationships", {})
    meta = r_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    gn = r_obj.get("_graph", {}).get("nodes", [])
    ge = r_obj.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "routingname": r_obj["name"],
            "description": r_obj.get("description") or "",
            "status": raw.get("eff_status_label"),
            "routing_type": raw.get("rtngtype_label"),
            "service_operation": raw.get("ib_operationname") or "",
            "sender_node": raw.get("sendernodename") or "",
            "receiver_node": raw.get("receivernodename") or "",
            "rest_method": raw.get("ib_restmethod") or "",
            "delivery_mode": raw.get("ib_deliverymode") or "",
            "effective_date": raw.get("effdt") or "",
            "owner": raw.get("objectownerid") or "",
            "last_updated": raw.get("lastupddttm") or "",
        }},
        {"name": "Sub-Definitions", "items": rels.get("sub_definitions", []),
         "data": {"count": len(rels.get("sub_definitions", []))}},
        {"name": "Graph Preview", "items": gn, "data": {"edge_count": len(ge)}},
        {"name": "Warnings", "items": r_obj.get("warnings", []), "data": {"count": len(r_obj.get("warnings", []))}},
    ]


def routing_payload(r_obj):
    meta = r_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": r_obj["type"], "name": r_obj["name"], "title": r_obj["display_name"],
        "overview": {"id": r_obj["id"], "display_name": r_obj["display_name"],
                     "description": r_obj.get("description") or "", "status": r_obj["status"], **raw},
        "sections": sections_for_routing(r_obj),
        "_links": r_obj["_links"], "_uom": r_obj,
    }


_SQL_TYPES = {
    "0": "SQL Object",
    "1": "AE SQL Action",
    "2": "AE PeopleCode SQL",
    "6": "Trigger",
}

_DB_TYPES = {
    " ": "Generic",
    "0": "Generic (alt)",
    "1": "Sybase",
    "2": "DB2/z",
    "3": "DB2/Unix",
    "4": "Microsoft SQL Server",
    "5": "DB2/400",
    "6": "Informix",
    "7": "Oracle",
}


def sql_object(env, sql_id):
    sql_id = sql_id.strip().upper()
    warnings = []
    defn = {}
    text_variants = {}

    if not ptmetadata.has_table(env, "PSSQLDEFN"):
        warnings.append(ptmetadata.warning("no_access", "PSSQLDEFN not accessible"))
        return canonical_base(
            env, "sql_definition", sql_id,
            display_name=sql_id, status="unavailable", warnings=warnings,
            _links={"admin": object_url("sql_definition", sql_id)},
            _metadata={"environment": env.upper()},
        )

    try:
        defn_cols = psdb.select_existing_columns(
            env, "PSSQLDEFN",
            ["SQLID", "SQLTYPE", "LASTUPDOPRID", "LASTUPDDTTM", "VERSION", "OBJECTOWNERID"],
            required=["SQLID"],
        )
        rows = psdb.query(env, f"""
            SELECT {", ".join(defn_cols)}
              FROM SYSADM.PSSQLDEFN
             WHERE SQLID = :sqlid
        """, {"sqlid": sql_id})
        if rows:
            defn = rows[0]
    except Exception:
        pass

    if ptmetadata.has_table(env, "PSSQLTEXTDEFN"):
        try:
            txt_cols = psdb.select_existing_columns(
                env, "PSSQLTEXTDEFN",
                ["SQLID", "SQLTYPE", "DBTYPE", "MARKET", "EFFDT", "SQLTEXT", "SEQNUM"],
                required=["SQLID", "SQLTEXT"],
            )
            txt_rows = psdb.query(env, f"""
                SELECT {", ".join(txt_cols)}
                  FROM SYSADM.PSSQLTEXTDEFN
                 WHERE SQLID = :sqlid
                 ORDER BY DBTYPE, SEQNUM
            """, {"sqlid": sql_id})
            for row in txt_rows:
                db = (str(row.get("dbtype") or " ").strip()) or " "
                if db not in text_variants:
                    text_variants[db] = {"label": _DB_TYPES.get(db, db), "chunks": []}
                text_variants[db]["chunks"].append(str(row.get("sqltext") or ""))
            for db, v in text_variants.items():
                v["text"] = "".join(v["chunks"])
                del v["chunks"]
        except Exception:
            pass

    sql_type_raw = str(defn.get("sqltype") or "0")
    sql_type_label = _SQL_TYPES.get(sql_type_raw, sql_type_raw)

    # Cross-references: AE SQL steps that use %SQL(sql_id) meta-SQL substitution.
    # Oracle LIKE requires escaping the literal '%' with an ESCAPE clause.
    xref_ae = []
    if ptmetadata.has_table(env, "PSSQLTEXTDEFN") and defn:
        try:
            xref_rows = psdb.query(env, """
                SELECT SQLID, SQLTYPE, DBTYPE, SEQNUM
                  FROM SYSADM.PSSQLTEXTDEFN
                 WHERE SQLTYPE = 1
                   AND UPPER(SQLTEXT) LIKE '%' || '\\%SQL(' || UPPER(:sqlid) || ')%' ESCAPE '\\'
                 FETCH FIRST 100 ROWS ONLY
            """, {"sqlid": sql_id})
            seen_ae = set()
            for xrow in xref_rows:
                ae_sqlid = str(xrow.get("sqlid") or "").strip()
                if ae_sqlid and ae_sqlid not in seen_ae:
                    seen_ae.add(ae_sqlid)
                    # AE SQL step SQLID format: "APPLID      SECTION  STEP   S"
                    parts = ae_sqlid.split()
                    ae_item = {"sqlid": ae_sqlid, "xref_type": "ae_sql_step"}
                    if len(parts) >= 1:
                        ae_item["ae_applid"] = parts[0]
                        ae_item["_links"] = {"admin": object_url("application_engine", parts[0])}
                    if len(parts) >= 2:
                        ae_item["ae_section"] = parts[1]
                    if len(parts) >= 3:
                        ae_item["ae_step"] = parts[2]
                    xref_ae.append(ae_item)
        except Exception:
            pass

    # Cross-references: PeopleCode programs that reference this SQL definition
    # via GetSQL(SQL.SQLID), CreateSQL(SQL.SQLID), or SQLExec(SQL.SQLID)
    xref_pc = []
    if ptmetadata.has_table(env, "PSPCMTXT") and defn:
        try:
            from connectors import peoplecode as _pc
            pc_pat = f"%SQL.{sql_id}%"
            pc_rows = psdb.query(env, """
                SELECT DISTINCT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                       OBJECTVALUE4, OBJECTVALUE5, OBJECTVALUE6, OBJECTVALUE7, PROGSEQ
                  FROM SYSADM.PSPCMTXT
                 WHERE UPPER(PCTEXT) LIKE UPPER(:pat)
                 FETCH FIRST 100 ROWS ONLY
            """, {"pat": pc_pat})
            for row in pc_rows:
                norm = _pc.normalize_program(row)
                ref = norm.get("reference") or ""
                enc = norm.get("encoded_reference") or _pc.encode_reference(ref)
                oid1 = row.get("objectid1")
                xref_item = {
                    "reference": ref,
                    "type_label": norm.get("object_type_label") or str(oid1),
                    "event": norm.get("event") or "",
                    "title": ref,
                    "_links": {"admin": f"/admin/object/peoplecode/{enc}"},
                }
                parent = norm.get("parent") or {}
                if parent.get("type") and parent.get("name"):
                    xref_item["parent_type"] = parent["type"]
                    xref_item["parent_name"] = parent["name"]
                    xref_item.setdefault("_links", {})["parent"] = (
                        f"/admin/object/{parent['type']}/{parent['name']}"
                    )
                xref_pc.append(xref_item)
        except Exception:
            pass

    nodes_g = {}
    add_node(nodes_g, graph_node("sql_definition", sql_id, defn))

    return canonical_base(
        env, "sql_definition", sql_id,
        display_name=sql_id,
        description=sql_type_label,
        status="available" if defn else "not_found",
        warnings=warnings,
        _links={"admin": object_url("sql_definition", sql_id)},
        _relationships={
            "text_variants": [
                {"dbtype": db, "label": v["label"], "text_length": len(v["text"])}
                for db, v in text_variants.items()
            ],
            "xref_ae": xref_ae,
            "xref_pc": xref_pc,
        },
        _graph={"nodes": list(nodes_g.values()), "edges": []},
        _metadata={
            "environment": env.upper(),
            "raw": defn,
            "sql_type": sql_type_raw,
            "sql_type_label": sql_type_label,
            "text_variants": text_variants,
            "registry": ptmetadata.OBJECT_REGISTRY.get("sql_definition", {}),
        },
    )


def sections_for_sql(s_obj):
    meta = s_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    variants = meta.get("text_variants", {})
    rels = s_obj.get("_relationships", {})

    primary_text = ""
    primary_note = ""
    if "7" in variants:
        primary_text = variants["7"]["text"]
        primary_note = "Oracle-specific variant"
    elif " " in variants:
        primary_text = variants[" "]["text"]
        primary_note = "Generic variant"
    elif variants:
        first = next(iter(variants.values()))
        primary_text = first["text"]
        primary_note = first["label"]

    xref_ae = rels.get("xref_ae", [])
    xref_pc = rels.get("xref_pc", [])
    sections = [
        {"name": "Definition", "items": [], "data": {
            "sqlid": s_obj["name"],
            "sql_type": meta.get("sql_type_label") or "",
            "owner": raw.get("objectownerid") or "",
            "version": raw.get("version") or "",
            "last_updated": raw.get("lastupddttm") or "",
            "last_updated_by": raw.get("lastupdoprid") or "",
        }},
        {"name": "SQL Source", "items": [], "data": {
            "note": primary_note,
            "length": len(primary_text),
            "ddl": primary_text,
        }},
        {"name": "DB Variants", "items": rels.get("text_variants", []),
         "data": {"count": len(variants)}},
    ]
    if xref_ae:
        sections.append({"name": "AE References", "items": xref_ae, "data": {
            "count": len(xref_ae),
            "note": "AE SQL steps using %SQL(" + s_obj["name"] + ") meta-SQL substitution",
        }})
    if xref_pc:
        sections.append({"name": "PeopleCode References", "items": xref_pc, "data": {
            "count": len(xref_pc),
            "note": f"PeopleCode programs referencing SQL.{s_obj['name']}",
        }})
    if s_obj.get("warnings"):
        sections.append({"name": "Warnings", "items": s_obj["warnings"],
                         "data": {"count": len(s_obj["warnings"])}})
    return sections


def sql_payload(s_obj):
    meta = s_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": s_obj["type"], "name": s_obj["name"], "title": s_obj["display_name"],
        "overview": {
            "id": s_obj["id"], "display_name": s_obj["display_name"],
            "description": s_obj.get("description") or "", "status": s_obj["status"], **raw,
        },
        "sections": sections_for_sql(s_obj),
        "_links": s_obj["_links"], "_uom": s_obj,
    }


_JOIN_TYPE_LABELS = {1: "Inner Join", 2: "Left Join", 3: "Left Outer Join", 4: "Exists Join"}
_QRY_FIELD_TYPES = {0: "Char", 1: "Long Char", 2: "Number", 3: "Signed Number", 4: "Date", 5: "Time", 6: "DateTime"}
_QRY_AGG_FUNCS = {" ": None, "": None, "S": "SUM", "A": "AVG", "C": "COUNT", "M": "MIN", "X": "MAX"}


def query_object(env, qryname):
    qryname = qryname.strip().upper()
    warnings = []

    if not ptmetadata.has_table(env, "PSQRYDEFN"):
        warnings.append(ptmetadata.warning("no_access", "PSQRYDEFN not accessible"))
        return canonical_base(
            env, "query", qryname,
            display_name=qryname, status="unavailable", warnings=warnings,
            _links={"admin": object_url("query", qryname)},
            _metadata={"environment": env.upper()},
        )

    defn = {}
    try:
        defn_cols = psdb.select_existing_columns(
            env, "PSQRYDEFN",
            ["QRYNAME", "OPRID", "QRYTYPE", "DESCR", "DESCRLONG", "QRYFOLDER",
             "QRYDISABLED", "QRYVALID", "SELCOUNT", "BNDCOUNT", "EXPCOUNT",
             "EXECLOGGING", "QRYAPPROVED", "LASTUPDDTTM", "LASTUPDOPRID",
             "CREATEOPRID", "CREATEDTTM"],
            required=["QRYNAME"],
        )
        rows = psdb.query(env, f"""
            SELECT {", ".join(defn_cols)}
              FROM SYSADM.PSQRYDEFN
             WHERE QRYNAME = :qn AND OPRID = ' '
        """, {"qn": qryname})
        if rows:
            defn = rows[0]
        else:
            warnings.append(ptmetadata.warning("not_found", f"Public query {qryname} not found"))
    except Exception as exc:
        warnings.append(ptmetadata.warning("query_error", str(exc)))

    records = []
    if defn and ptmetadata.has_table(env, "PSQRYRECORD"):
        try:
            rec_cols = psdb.select_existing_columns(
                env, "PSQRYRECORD",
                ["QRYNAME", "OPRID", "RCDNUM", "RECNAME", "CORRNAME", "JOINTYPE",
                 "JOINRCDNUM", "SELNUM"],
                required=["QRYNAME", "RCDNUM", "RECNAME"],
            )
            records = psdb.query(env, f"""
                SELECT {", ".join(rec_cols)}
                  FROM SYSADM.PSQRYRECORD
                 WHERE QRYNAME = :qn AND OPRID = ' '
                 ORDER BY RCDNUM
            """, {"qn": qryname})
        except Exception as exc:
            warnings.append(ptmetadata.warning("psqryrecord_error", str(exc)))

    fields = []
    if defn and ptmetadata.has_table(env, "PSQRYFIELD"):
        try:
            fld_cols = psdb.select_existing_columns(
                env, "PSQRYFIELD",
                ["QRYNAME", "OPRID", "FLDNUM", "FIELDNAME", "RECNAME", "FLDRCDNUM",
                 "COLUMNNUM", "HEADING", "HDGTYPE", "AGGREGATEFUNC", "ORDERBYNUM",
                 "ORDERBYDIR", "GROUPBYNUM"],
                required=["QRYNAME", "FLDNUM", "FIELDNAME"],
            )
            fields = psdb.query(env, f"""
                SELECT {", ".join(fld_cols)}
                  FROM SYSADM.PSQRYFIELD
                 WHERE QRYNAME = :qn AND OPRID = ' '
                 ORDER BY FLDNUM
            """, {"qn": qryname})
        except Exception as exc:
            warnings.append(ptmetadata.warning("psqryfield_error", str(exc)))

    binds = []
    if defn and ptmetadata.has_table(env, "PSQRYBIND"):
        try:
            bnd_cols = psdb.select_existing_columns(
                env, "PSQRYBIND",
                ["QRYNAME", "OPRID", "BNDNUM", "BNDNAME", "FIELDNAME", "FIELDTYPE",
                 "LENGTH", "HEADING", "HDGTYPE"],
                required=["QRYNAME", "BNDNUM"],
            )
            binds = psdb.query(env, f"""
                SELECT {", ".join(bnd_cols)}
                  FROM SYSADM.PSQRYBIND
                 WHERE QRYNAME = :qn AND OPRID = ' '
                 ORDER BY BNDNUM
            """, {"qn": qryname})
        except Exception as exc:
            warnings.append(ptmetadata.warning("psqrybind_error", str(exc)))

    rec_by_num = {r.get("rcdnum"): r for r in records}

    enriched_records = []
    for i, r in enumerate(records):
        jt_raw = r.get("jointype")
        jt_int = int(jt_raw) if str(jt_raw or "").isdigit() else 1
        corrname = str(r.get("corrname") or "").strip()
        recname = str(r.get("recname") or "")
        enriched_records.append({
            **r,
            "join_type_label": _JOIN_TYPE_LABELS.get(jt_int, f"Join({jt_raw})"),
            "alias": corrname,
            "is_primary": i == 0,
            "_links": {"admin": object_url("record", recname)},
        })

    output_fields = []
    all_fields = []
    for f in fields:
        agg_raw = str(f.get("aggregatefunc") or " ").strip()
        agg_label = _QRY_AGG_FUNCS.get(agg_raw if agg_raw else " ")
        rec_row = rec_by_num.get(f.get("fldrcdnum"))
        recname = str((rec_row or {}).get("recname") or f.get("recname") or "").strip()
        fieldname = str(f.get("fieldname") or "")
        col_num = int(f.get("columnnum") or 0)
        heading = str(f.get("heading") or "").strip()
        enriched = {
            **f,
            "recname_resolved": recname,
            "in_output": col_num > 0,
            "agg_label": agg_label,
            "heading_display": heading or fieldname,
            "_links": {
                "field": f"/admin/object/field/{fieldname}",
                "record": object_url("record", recname) if recname else None,
            },
        }
        all_fields.append(enriched)
        if col_num > 0:
            output_fields.append(enriched)

    enriched_binds = []
    for b in binds:
        ft = int(b.get("fieldtype") or 0)
        enriched_binds.append({
            **b,
            "fieldtype_label": _QRY_FIELD_TYPES.get(ft, f"Type({ft})"),
            "heading_display": str(b.get("heading") or b.get("bndname") or "").strip(),
        })

    descr = str(defn.get("descr") or "").strip()
    descrlong = str(defn.get("descrlong") or "").strip()

    raw = {
        "qrytype": defn.get("qrytype"),
        "qryfolder": str(defn.get("qryfolder") or "").strip() or None,
        "qrydisabled": defn.get("qrydisabled"),
        "qryvalid": defn.get("qryvalid"),
        "selcount": defn.get("selcount"),
        "bndcount": defn.get("bndcount"),
        "expcount": defn.get("expcount"),
        "execlogging": defn.get("execlogging"),
        "qryapproved": defn.get("qryapproved"),
        "lastupddttm": str(defn.get("lastupddttm") or ""),
        "lastupdoprid": str(defn.get("lastupdoprid") or ""),
        "createoprid": str(defn.get("createoprid") or ""),
        "createdttm": str(defn.get("createdttm") or ""),
    }

    return canonical_base(
        env, "query", qryname,
        display_name=qryname,
        description=descrlong or descr,
        status="ok" if defn else "partial",
        warnings=warnings,
        _links={"admin": object_url("query", qryname)},
        _metadata={
            "environment": env.upper(),
            "raw": raw,
            "defn": defn,
            "records": enriched_records,
            "fields": all_fields,
            "output_fields": output_fields,
            "binds": enriched_binds,
            "descr": descr,
            "descrlong": descrlong,
        },
    )


def sections_for_query(q_obj):
    meta = q_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    records = meta.get("records", [])
    output_fields = meta.get("output_fields", [])
    binds = meta.get("binds", [])
    descr = meta.get("descr", "")
    descrlong = meta.get("descrlong", "")
    warnings = q_obj.get("warnings", [])

    sections = []

    overview_rows = [
        {"label": "Query Name", "value": q_obj["name"]},
        {"label": "Description", "value": descrlong or descr or ""},
    ]
    if raw.get("qryfolder"):
        overview_rows.append({"label": "Folder", "value": raw["qryfolder"]})
    if raw.get("qrydisabled") not in (None, "", "N", "0", 0):
        overview_rows.append({"label": "Disabled", "value": "Yes"})
    if raw.get("lastupdoprid"):
        overview_rows.append({"label": "Last Updated By", "value": str(raw["lastupdoprid"])})
    if raw.get("lastupddttm"):
        overview_rows.append({"label": "Last Updated", "value": str(raw["lastupddttm"])})
    if raw.get("createoprid"):
        overview_rows.append({"label": "Created By", "value": str(raw["createoprid"])})
    sections.append({"title": "Overview", "type": "key_values", "rows": overview_rows})

    if records:
        rec_items = []
        for i, r in enumerate(records):
            recname = str(r.get("recname") or "")
            alias = str(r.get("alias") or "").strip()
            jt = r.get("join_type_label", "")
            label = f"{r.get('rcdnum', i+1)}. {recname}"
            if alias:
                label += f" [{alias}]"
            if not r.get("is_primary"):
                label += f" — {jt}"
            rec_items.append({
                "label": label,
                "type": "record",
                "name": recname,
                "_links": r.get("_links", {}),
            })
        sections.append({
            "title": f"Records Used ({len(records)})",
            "type": "list",
            "items": rec_items,
        })

    if output_fields:
        col_items = []
        for f in sorted(output_fields, key=lambda x: int(x.get("columnnum") or 0)):
            fieldname = str(f.get("fieldname") or "")
            recname = str(f.get("recname_resolved") or "")
            heading = f.get("heading_display") or fieldname
            agg = f.get("agg_label")
            label = f"{f.get('columnnum')}. {heading}"
            if agg:
                label += f" ({agg})"
            if recname:
                label += f" — {recname}.{fieldname}"
            col_items.append({
                "label": label,
                "type": "field",
                "name": f"{recname}.{fieldname}" if recname else fieldname,
                "_links": f.get("_links", {}),
            })
        sections.append({
            "title": f"Output Columns ({len(output_fields)})",
            "type": "list",
            "items": col_items,
        })

    if binds:
        bnd_items = []
        for b in binds:
            bndname = str(b.get("bndname") or "")
            heading = b.get("heading_display") or bndname
            ftype = b.get("fieldtype_label", "")
            fieldname = str(b.get("fieldname") or "").strip()
            label = f"{b.get('bndnum')}. {heading} ({ftype})"
            if fieldname:
                label += f" — {fieldname}"
            bnd_items.append({"label": label, "name": bndname})
        sections.append({
            "title": f"Prompt Parameters ({len(binds)})",
            "type": "list",
            "items": bnd_items,
        })

    if warnings:
        sections.append({"title": "Warnings", "type": "list",
                         "items": [{"label": str(w)} for w in warnings]})

    return sections


def query_payload(q_obj):
    meta = q_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    return {
        "type": q_obj["type"], "name": q_obj["name"], "title": q_obj["display_name"],
        "overview": {
            "id": q_obj["id"], "display_name": q_obj["display_name"],
            "description": q_obj.get("description") or meta.get("descr") or "",
            "status": q_obj["status"], **raw,
        },
        "sections": sections_for_query(q_obj),
        "_links": q_obj["_links"], "_uom": q_obj,
    }


def _tree_flag(value, yes="Yes", no="No"):
    if value is None:
        return ""
    text = str(value).strip().upper()
    if text in {"Y", "1", "T", "A"}:
        return yes
    if text in {"N", "0", "F", "I"}:
        return no
    return str(value)


def _tree_row_links(row, env):
    linked = attach_object_links(row, env)
    tree_name = str(linked.get("tree_name") or "").strip()
    if tree_name:
        linked.setdefault("_links", {})["admin"] = object_url("tree", tree_name)
    return linked


def _tree_record_link(row, key, rel_label):
    recname = str(row.get(key) or "").strip()
    if not recname:
        return None
    return {
        "relationship": rel_label,
        "recname": recname,
        "_links": {"admin": object_url("record", recname)},
    }


def _tree_field_link(row, rec_key, field_key, rel_label):
    recname = str(row.get(rec_key) or "").strip()
    fieldname = str(row.get(field_key) or "").strip()
    if not recname or not fieldname:
        return None
    field_ref = f"{recname}.{fieldname}"
    return {
        "relationship": rel_label,
        "recname": recname,
        "fieldname": fieldname,
        "name": field_ref,
        "_links": {"admin": object_url("field", field_ref)},
    }


def tree_graph(env, tree_name, relationships=None):
    relationships = relationships or tree_object(env, tree_name)["_relationships"]
    name = tree_name.upper()
    return relationship_graph("tree", name, relationships, [
        {
            "relationship": "records",
            "node_type": "record",
            "target_name": "recname",
            "edge": lambda row: row.get("relationship") or "uses_record",
        },
        {
            "relationship": "fields",
            "node_type": "field",
            "target_name": "name",
            "edge": lambda row: row.get("relationship") or "uses_field",
            "extra_edges": [
                {
                    "source_node_type": "record",
                    "source_name": "recname",
                    "target_node_type": "field",
                    "target_name": "name",
                    "edge": "contains_field",
                },
            ],
        },
    ])


def tree_object(env, tree_name):
    warnings = []
    name = tree_name.upper()

    if not ptmetadata.has_table(env, "PSTREEDEFN"):
        return canonical_base(
            env, "tree", name,
            display_name=name,
            status="partial",
            warnings=[ptmetadata.warning("pstreedefn_unavailable", "SYSADM.PSTREEDEFN is not accessible.")],
        )

    has_structure = ptmetadata.has_table(env, "PSTREESTRCT")
    join_sql = """
        left join sysadm.pstreestrct s
               on s.tree_strct_id = d.tree_strct_id
    """ if has_structure else ""
    structure_cols = """
            s.descr as tree_strct_descr,
            s.node_recname, s.node_fieldname,
            s.dtl_recname, s.dtl_fieldname,
            s.level_recname, s.tree_strct_type,
            s.setcntrl_ind
    """ if has_structure else """
            cast(null as varchar2(30)) as tree_strct_descr,
            cast(null as varchar2(30)) as node_recname,
            cast(null as varchar2(30)) as node_fieldname,
            cast(null as varchar2(30)) as dtl_recname,
            cast(null as varchar2(30)) as dtl_fieldname,
            cast(null as varchar2(30)) as level_recname,
            cast(null as varchar2(30)) as tree_strct_type,
            cast(null as varchar2(1)) as setcntrl_ind
    """

    try:
        rows = psdb.query(env, f"""
            select
                d.setid, d.setcntrlvalue, d.tree_name, d.effdt, d.eff_status,
                d.version, d.tree_strct_id, d.descr, d.all_values, d.use_levels,
                d.valid_tree, d.level_count, d.node_count, d.leaf_count,
                d.tree_has_ranges, d.duplicate_leaf, d.tree_category,
                d.tree_acc_method, d.tree_acc_selector, d.tree_acc_sel_opt,
                d.lastupddttm, d.lastupdoprid,
                {structure_cols}
              from sysadm.pstreedefn d
              {join_sql}
             where d.tree_name = upper(:tree_name)
             order by d.effdt desc, d.setid, d.setcntrlvalue
             fetch first 1 rows only
        """, {"tree_name": name})
    except Exception as exc:
        return canonical_base(
            env, "tree", name,
            display_name=name,
            status="partial",
            warnings=[ptmetadata.warning("tree_query_failed", str(exc))],
        )

    if not rows:
        return canonical_base(
            env, "tree", name,
            display_name=name,
            status="not_found",
            warnings=[ptmetadata.warning("not_found", f"Tree {name} not found")],
        )

    raw = rows[0]
    params = {
        "tree_name": raw.get("tree_name"),
        "setid": raw.get("setid"),
        "setcntrlvalue": raw.get("setcntrlvalue"),
        "effdt": str(raw.get("effdt") or "")[:10],
    }

    def run_related(label, table, sql, query_params=None):
        if not ptmetadata.has_table(env, table):
            warnings.append(ptmetadata.warning("metadata_unavailable", f"SYSADM.{table} is not accessible."))
            return []
        try:
            return psdb.query(env, sql, query_params or params)
        except Exception as exc:
            warnings.append(ptmetadata.warning("relationship_unavailable", f"{label} unavailable: {exc}"))
            return []

    variants = run_related("tree variants", "PSTREEDEFN", """
        select setid, setcntrlvalue, tree_name, effdt, eff_status, version,
               tree_strct_id, descr, node_count, leaf_count
          from sysadm.pstreedefn
         where tree_name = upper(:tree_name)
         order by effdt desc, setid, setcntrlvalue
         fetch first 50 rows only
    """, {"tree_name": name})

    levels = run_related("tree levels", "PSTREELEVEL", """
        select tree_level_num, tree_level, all_values
          from sysadm.pstreelevel
         where tree_name = upper(:tree_name)
           and setid = :setid
           and setcntrlvalue = :setcntrlvalue
           and trunc(effdt) = to_date(:effdt, 'YYYY-MM-DD')
         order by tree_level_num
    """)

    branches = run_related("tree branches", "PSTREEBRANCH", """
        select tree_branch, parent_branch, branch_level_num, parent_node_num,
               tree_level_num, tree_node_num, tree_node_num_end, node_count, leaf_count
          from sysadm.pstreebranch
         where tree_name = upper(:tree_name)
           and setid = :setid
           and setcntrlvalue = :setcntrlvalue
           and trunc(effdt) = to_date(:effdt, 'YYYY-MM-DD')
         order by branch_level_num, tree_branch
         fetch first 200 rows only
    """)

    nodes = run_related("tree nodes", "PSTREENODE", """
        select tree_node_num, tree_node, tree_branch, tree_node_num_end,
               tree_level_num, tree_node_type, parent_node_num, parent_node_name
          from sysadm.pstreenode
         where tree_name = upper(:tree_name)
           and setid = :setid
           and setcntrlvalue = :setcntrlvalue
           and trunc(effdt) = to_date(:effdt, 'YYYY-MM-DD')
         order by tree_node_num
         fetch first 200 rows only
    """)

    leaves = run_related("tree leaves", "PSTREELEAF", """
        select tree_node_num, range_from, range_to, tree_branch, dynamic_range
          from sysadm.pstreeleaf
         where tree_name = upper(:tree_name)
           and setid = :setid
           and setcntrlvalue = :setcntrlvalue
           and trunc(effdt) = to_date(:effdt, 'YYYY-MM-DD')
         order by tree_node_num, range_from
         fetch first 200 rows only
    """)

    records = [
        item for item in (
            _tree_record_link(raw, "node_recname", "node_record"),
            _tree_record_link(raw, "dtl_recname", "detail_record"),
            _tree_record_link(raw, "level_recname", "level_record"),
        )
        if item
    ]
    fields = [
        item for item in (
            _tree_field_link(raw, "node_recname", "node_fieldname", "node_field"),
            _tree_field_link(raw, "dtl_recname", "dtl_fieldname", "detail_field"),
        )
        if item
    ]

    relationships = {
        "variants": [_tree_row_links(row, env) for row in variants],
        "levels": levels,
        "branches": branches,
        "nodes": nodes,
        "leaves": leaves,
        "records": records,
        "fields": fields,
    }
    graph = tree_graph(env, name, relationships)

    status = "active" if str(raw.get("eff_status") or "").upper() == "A" else "inactive"
    return canonical_base(
        env, "tree", name,
        display_name=name,
        description=raw.get("descr") or "",
        owner=raw.get("setid") or "",
        version=str(raw.get("version") or ""),
        status=status,
        warnings=warnings,
        _links={
            "self": api_url("tree", name),
            "admin": object_url("tree", name),
            "graph": graph_url("tree", name),
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("tree", {}),
            "raw": raw,
            "sample_limits": {"nodes": 200, "leaves": 200, "branches": 200, "variants": 50},
        },
    )


def sections_for_tree(tree):
    rels = tree.get("_relationships", {})
    raw = tree.get("_metadata", {}).get("raw", {})
    graph_nodes = tree.get("_graph", {}).get("nodes", [])
    graph_edges = tree.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "tree_name": tree["name"],
            "description": tree.get("description") or "",
            "setid": raw.get("setid") or "",
            "setcntrlvalue": raw.get("setcntrlvalue") or "",
            "effdt": raw.get("effdt") or "",
            "status": tree.get("status"),
            "version": raw.get("version") or "",
            "tree_strct_id": raw.get("tree_strct_id") or "",
            "valid_tree": _tree_flag(raw.get("valid_tree")),
            "all_values": _tree_flag(raw.get("all_values")),
            "use_levels": _tree_flag(raw.get("use_levels")),
            "has_ranges": _tree_flag(raw.get("tree_has_ranges")),
            "duplicate_leaf": _tree_flag(raw.get("duplicate_leaf")),
            "node_count": raw.get("node_count"),
            "leaf_count": raw.get("leaf_count"),
            "level_count": raw.get("level_count"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
        {"name": "Tree Structure", "items": rels.get("records", []) + rels.get("fields", []), "data": {
            "tree_strct_id": raw.get("tree_strct_id") or "",
            "description": raw.get("tree_strct_descr") or "",
            "tree_strct_type": raw.get("tree_strct_type") or "",
            "set_controlled": _tree_flag(raw.get("setcntrl_ind")),
            "node_recname": raw.get("node_recname") or "",
            "node_fieldname": raw.get("node_fieldname") or "",
            "detail_recname": raw.get("dtl_recname") or "",
            "detail_fieldname": raw.get("dtl_fieldname") or "",
            "level_recname": raw.get("level_recname") or "",
        }},
        {"name": "Levels", "items": rels.get("levels", []), "data": {"count": len(rels.get("levels", []))}},
        {"name": "Branches", "items": rels.get("branches", []), "data": {
            "count": len(rels.get("branches", [])),
            "note": "Sample capped at 200 rows",
        }},
        {"name": "Nodes", "items": rels.get("nodes", []), "data": {
            "count": len(rels.get("nodes", [])),
            "defined_count": raw.get("node_count"),
            "note": "Sample capped at 200 rows",
        }},
        {"name": "Leaves", "items": rels.get("leaves", []), "data": {
            "count": len(rels.get("leaves", [])),
            "defined_count": raw.get("leaf_count"),
            "note": "Sample capped at 200 rows",
        }},
        {"name": "Effective-Dated Variants", "items": rels.get("variants", []), "data": {
            "count": len(rels.get("variants", [])),
            "note": "Latest 50 variants for this TREE_NAME",
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
        }},
        {"name": "Warnings", "items": tree.get("warnings", []), "data": {"count": len(tree.get("warnings", []))}},
    ]


def tree_payload(tree):
    raw = tree.get("_metadata", {}).get("raw", {})
    return {
        "type": tree["type"], "name": tree["name"], "title": tree["display_name"],
        "overview": {
            "id": tree["id"], "display_name": tree["display_name"],
            "description": tree.get("description") or "",
            "status": tree["status"], **raw,
        },
        "sections": sections_for_tree(tree),
        "_links": tree["_links"], "_uom": tree,
    }


def _ci_type_label(value):
    labels = {
        1: "Get Key",
        2: "Create Key",
        3: "Collection",
        4: "Property",
        5: "Find Key",
        6: "Method",
    }
    try:
        return labels.get(int(value), str(value))
    except Exception:
        return str(value or "")


def _ci_access_label(value):
    labels = {
        1: "Read/Write",
        2: "Read Only",
    }
    try:
        return labels.get(int(value), str(value))
    except Exception:
        return str(value or "")


def _ci_item_links(row, env):
    linked = dict(row)
    recname = str(linked.get("recname") or "").strip()
    fieldname = str(linked.get("fieldname") or "").strip()
    linked["bctype_label"] = _ci_type_label(linked.get("bctype"))
    linked["bcaccess_label"] = _ci_access_label(linked.get("bcaccess"))
    if recname and fieldname:
        linked.setdefault("_links", {})["admin"] = object_url("field", f"{recname}.{fieldname}")
    elif recname:
        linked.setdefault("_links", {})["admin"] = object_url("record", recname)
    return linked


def _dedupe_rows(rows, key_fields):
    seen = set()
    out = []
    for row in rows:
        key = tuple(str(row.get(k) or "").strip().upper() for k in key_fields)
        if not any(key) or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def ci_graph(env, ci_name, relationships=None):
    relationships = relationships or ci_object(env, ci_name)["_relationships"]
    name = ci_name.upper()
    return relationship_graph("ci", name, relationships, [
        {
            "relationship": "components",
            "node_type": "component",
            "target_name": "pnlgrpname",
            "default_edge": "wraps_component",
        },
        {
            "relationship": "menus",
            "node_type": "menu",
            "target_name": "menuname",
            "default_edge": "declared_on_menu",
        },
        {
            "relationship": "records",
            "node_type": "record",
            "target_name": "recname",
            "edge": lambda row: row.get("relationship") or "uses_record",
        },
        {
            "relationship": "fields",
            "node_type": "field",
            "target_name": "name",
            "edge": lambda row: row.get("relationship") or "exposes_field",
            "extra_edges": [
                {
                    "source_node_type": "record",
                    "source_name": "recname",
                    "target_node_type": "field",
                    "target_name": "name",
                    "edge": "contains_field",
                },
            ],
        },
    ])


def ci_object(env, ci_name):
    warnings = []
    name = ci_name.upper()

    if not ptmetadata.has_table(env, "PSBCDEFN"):
        return canonical_base(
            env, "ci", name,
            display_name=name,
            status="partial",
            warnings=[ptmetadata.warning("psbcdefn_unavailable", "SYSADM.PSBCDEFN is not accessible.")],
        )

    try:
        rows = psdb.query(env, """
            select bcname, bcdisplayname, bcpgname, market, menuname,
                   searchrecname, addsrchrecname, itemcount, descr, version,
                   bcstdmethods, lastupddttm, lastupdoprid, objectownerid, descrlong
              from sysadm.psbcdefn
             where bcname = upper(:name)
             fetch first 1 rows only
        """, {"name": name})
    except Exception as exc:
        return canonical_base(
            env, "ci", name,
            display_name=name,
            status="partial",
            warnings=[ptmetadata.warning("ci_query_failed", str(exc))],
        )

    if not rows:
        return canonical_base(
            env, "ci", name,
            display_name=name,
            status="not_found",
            warnings=[ptmetadata.warning("not_found", f"Component Interface {name} not found")],
        )

    raw = rows[0]
    items = []
    if ptmetadata.has_table(env, "PSBCITEM"):
        try:
            items = psdb.query(env, """
                select bcname, bctype, bcitemparent, bcitemname, sequence_nbr_6,
                       bcaccess, bcscroll, bcscrollnum, bcscrollname,
                       recname, fieldname, subrecname, commentshort
                  from sysadm.psbcitem
                 where bcname = upper(:name)
                 order by sequence_nbr_6, bcitemname
                 fetch first 500 rows only
            """, {"name": name})
        except Exception as exc:
            warnings.append(ptmetadata.warning("relationship_unavailable", f"CI items unavailable: {exc}"))
    else:
        warnings.append(ptmetadata.warning("metadata_unavailable", "SYSADM.PSBCITEM is not accessible."))

    linked_items = [_ci_item_links(row, env) for row in items]
    collections = [row for row in linked_items if row.get("bctype") == 3]
    properties = [row for row in linked_items if row.get("bctype") == 4]
    keys = [row for row in linked_items if row.get("bctype") in (1, 2, 5)]
    methods = [row for row in linked_items if row.get("bctype") == 6]

    record_rows = []
    for key, rel in (("searchrecname", "search_record"), ("addsrchrecname", "add_search_record")):
        recname = str(raw.get(key) or "").strip()
        if recname:
            record_rows.append({"relationship": rel, "recname": recname, "_links": {"admin": object_url("record", recname)}})
    for row in linked_items:
        recname = str(row.get("recname") or "").strip()
        if recname:
            record_rows.append({"relationship": row.get("bctype_label") or "item_record", "recname": recname,
                                "_links": {"admin": object_url("record", recname)}})
    records = _dedupe_rows(record_rows, ["recname"])

    field_rows = []
    for row in linked_items:
        recname = str(row.get("recname") or "").strip()
        fieldname = str(row.get("fieldname") or "").strip()
        if recname and fieldname:
            field_ref = f"{recname}.{fieldname}"
            field_rows.append({
                "relationship": row.get("bctype_label") or "item_field",
                "recname": recname,
                "fieldname": fieldname,
                "name": field_ref,
                "bcitemname": row.get("bcitemname"),
                "_links": {"admin": object_url("field", field_ref)},
            })
    fields = _dedupe_rows(field_rows, ["name"])

    components = []
    component = str(raw.get("bcpgname") or "").strip()
    if component:
        components.append({"pnlgrpname": component, "relationship": "component", "_links": {"admin": object_url("component", component)}})

    menus = []
    menu = str(raw.get("menuname") or "").strip()
    if menu:
        menus.append({"menuname": menu, "relationship": "menu", "_links": {"admin": object_url("menu", menu)}})

    relationships = {
        "components": components,
        "menus": menus,
        "records": records,
        "fields": fields,
        "items": linked_items,
        "collections": collections,
        "properties": properties,
        "keys": keys,
        "methods": methods,
    }
    graph = ci_graph(env, name, relationships)

    return canonical_base(
        env, "ci", name,
        display_name=raw.get("bcdisplayname") or name,
        description=raw.get("descrlong") or raw.get("descr") or "",
        owner=raw.get("objectownerid") or "",
        version=str(raw.get("version") or ""),
        status="available",
        warnings=warnings,
        _links={
            "self": api_url("ci", name),
            "admin": object_url("ci", name),
            "graph": graph_url("ci", name),
        },
        _relationships=relationships,
        _graph=graph,
        _metadata={
            "environment": env.upper(),
            "registry": ptmetadata.OBJECT_REGISTRY.get("ci", {}),
            "raw": raw,
            "sample_limits": {"items": 500},
        },
    )


def sections_for_ci(ci):
    rels = ci.get("_relationships", {})
    raw = ci.get("_metadata", {}).get("raw", {})
    graph_nodes = ci.get("_graph", {}).get("nodes", [])
    graph_edges = ci.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "bcname": ci["name"],
            "display_name": ci.get("display_name") or "",
            "description": ci.get("description") or "",
            "component": raw.get("bcpgname") or "",
            "menu": raw.get("menuname") or "",
            "market": raw.get("market") or "",
            "search_record": raw.get("searchrecname") or "",
            "add_search_record": raw.get("addsrchrecname") or "",
            "item_count": raw.get("itemcount"),
            "version": raw.get("version") or "",
            "standard_methods": raw.get("bcstdmethods") or "",
            "owner": raw.get("objectownerid") or "",
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
        }},
        {"name": "Component and Menu", "items": rels.get("components", []) + rels.get("menus", []),
         "data": {"component_count": len(rels.get("components", [])), "menu_count": len(rels.get("menus", []))}},
        {"name": "Search/Add Records", "items": rels.get("records", [])[:20],
         "data": {"record_count": len(rels.get("records", [])),
                  "note": "Includes search/add records and unique records exposed by CI items"}},
        {"name": "Keys", "items": rels.get("keys", []), "data": {"count": len(rels.get("keys", []))}},
        {"name": "Collections", "items": rels.get("collections", []), "data": {"count": len(rels.get("collections", []))}},
        {"name": "Properties", "items": rels.get("properties", []), "data": {
            "count": len(rels.get("properties", [])),
            "note": "Item sample capped at 500 rows",
        }},
        {"name": "Methods", "items": rels.get("methods", []), "data": {"count": len(rels.get("methods", []))}},
        {"name": "Fields", "items": rels.get("fields", [])[:200], "data": {
            "count": len(rels.get("fields", [])),
            "note": "Unique exposed record fields; display capped at 200 rows",
        }},
        {"name": "All Items", "items": rels.get("items", []), "data": {
            "count": len(rels.get("items", [])),
            "defined_count": raw.get("itemcount"),
            "note": "Sample capped at 500 rows",
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
        }},
        {"name": "Warnings", "items": ci.get("warnings", []), "data": {"count": len(ci.get("warnings", []))}},
    ]


def ci_payload(ci):
    raw = ci.get("_metadata", {}).get("raw", {})
    return {
        "type": ci["type"], "name": ci["name"], "title": ci["display_name"],
        "overview": {
            "id": ci["id"], "display_name": ci["display_name"],
            "description": ci.get("description") or "",
            "status": ci["status"], **raw,
        },
        "sections": sections_for_ci(ci),
        "_links": ci["_links"], "_uom": ci,
    }


def app_package_object(env, package_name):
    package_name = package_name.strip().upper()
    warnings = []
    defn = {}
    sub_packages = []
    classes = []
    peoplecode_items = []

    if not ptmetadata.has_table(env, "PSPACKAGEDEFN"):
        warnings.append(ptmetadata.warning("no_access", "PSPACKAGEDEFN not accessible"))
        return canonical_base(
            env, "application_package", package_name,
            display_name=package_name, status="unavailable", warnings=warnings,
            _links={"admin": object_url("application_package", package_name)},
            _metadata={"environment": env.upper()},
        )

    try:
        defn_cols = psdb.select_existing_columns(
            env, "PSPACKAGEDEFN",
            ["PACKAGEROOT", "PACKAGEID", "QUALIFYPATH", "PACKAGELEVEL", "DESCR",
             "VERSION", "LASTUPDDTTM", "LASTUPDOPRID", "OBJECTOWNERID"],
            required=["PACKAGEROOT"],
        )
        rows = psdb.query(env, f"""
            SELECT {", ".join(defn_cols)}
              FROM SYSADM.PSPACKAGEDEFN
             WHERE PACKAGEROOT = :pkg AND PACKAGELEVEL = 0
             FETCH FIRST 1 ROWS ONLY
        """, {"pkg": package_name})
        if rows:
            defn = dict(rows[0])
    except Exception as exc:
        warnings.append(ptmetadata.warning("query_error", str(exc)))

    try:
        sp_rows = psdb.query(env, """
            SELECT QUALIFYPATH, PACKAGELEVEL, DESCR
              FROM SYSADM.PSPACKAGEDEFN
             WHERE PACKAGEROOT = :pkg AND PACKAGELEVEL > 0
             ORDER BY QUALIFYPATH
        """, {"pkg": package_name})
        sub_packages = [dict(r) for r in sp_rows]
    except Exception as exc:
        warnings.append(ptmetadata.warning("sub_packages_error", str(exc)))

    if ptmetadata.has_table(env, "PSAPPCLASSDEFN"):
        try:
            cls_rows = psdb.query(env, """
                SELECT APPCLASSID, QUALIFYPATH, DESCR
                  FROM SYSADM.PSAPPCLASSDEFN
                 WHERE PACKAGEROOT = :pkg
                 ORDER BY QUALIFYPATH, APPCLASSID
            """, {"pkg": package_name})
            classes = [dict(r) for r in cls_rows]
        except Exception as exc:
            warnings.append(ptmetadata.warning("classes_error", str(exc)))

    if ptmetadata.has_table(env, "PSPCMPROG"):
        try:
            pc_rows = psdb.query(env, """
                SELECT DISTINCT OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                       OBJECTVALUE4, OBJECTVALUE5
                  FROM SYSADM.PSPCMPROG
                 WHERE OBJECTID1 = 104 AND OBJECTVALUE1 = :pkg
                 ORDER BY OBJECTVALUE2, OBJECTVALUE3, OBJECTVALUE4
                 FETCH FIRST 500 ROWS ONLY
            """, {"pkg": package_name})
            peoplecode_items = [dict(r) for r in pc_rows]
        except Exception as exc:
            warnings.append(ptmetadata.warning("peoplecode_error", str(exc)))

    descr = str(defn.get("descr") or "").strip() or None
    owner = str(defn.get("objectownerid") or "").strip() or None
    version = str(defn.get("version") or "").strip() or None

    return {
        "environment": env.upper(),
        "type": "application_package",
        "name": package_name,
        "display_name": package_name,
        "description": descr,
        "status": "resolved" if defn else "partial",
        "definition": {
            k: v for k, v in defn.items()
            if v not in (None, "", " ")
        },
        "sub_packages": sub_packages,
        "classes": classes,
        "peoplecode": peoplecode_items,
        "counts": {
            "sub_packages": len(sub_packages),
            "classes": len(classes),
            "peoplecode_programs": len(peoplecode_items),
        },
        "warnings": warnings,
        "_links": {"admin": object_url("application_package", package_name)},
        "_metadata": {
            "environment": env.upper(),
            "descr": descr,
            "owner": owner,
            "version": version,
        },
    }


def sections_for_app_package(pkg):
    sections = []
    warnings = list(pkg.get("warnings") or [])
    defn = pkg.get("definition") or {}
    counts = pkg.get("counts") or {}

    overview_fields = {}
    if defn.get("descr"):
        overview_fields["Description"] = defn["descr"]
    if defn.get("objectownerid"):
        overview_fields["Owner"] = defn["objectownerid"]
    if defn.get("version"):
        overview_fields["Version"] = defn["version"]
    if defn.get("lastupdoprid"):
        overview_fields["Last Updated By"] = defn["lastupdoprid"]
    if defn.get("lastupddttm"):
        overview_fields["Last Updated"] = str(defn["lastupddttm"])

    sections.append({
        "name": "Definition",
        "items": [],
        "data": overview_fields or defn,
    })

    # Sub-packages (folder structure)
    sub_pkgs = pkg.get("sub_packages") or []
    if sub_pkgs:
        sp_items = []
        for sp in sub_pkgs:
            qpath = str(sp.get("qualifypath") or "").strip()
            descr = str(sp.get("descr") or "").strip()
            level = sp.get("packagelevel", 1)
            item = {
                "title": qpath,
                "description": descr or None,
                "level": level,
                "qualifypath": qpath,
            }
            sp_items.append(item)
        sections.append({
            "name": "Sub-Packages",
            "items": sp_items,
            "data": {"count": len(sp_items)},
        })

    # Classes grouped by qualifypath
    classes = pkg.get("classes") or []
    if classes:
        cls_items = []
        for cls in classes:
            classid = str(cls.get("appclassid") or "").strip()
            qpath = str(cls.get("qualifypath") or "").strip()
            descr = str(cls.get("descr") or "").strip()
            full_path = f"{pkg['name']}:{qpath}:{classid}" if qpath else f"{pkg['name']}:{classid}"
            item = {
                "title": classid,
                "description": descr or None,
                "qualifypath": qpath or None,
                "full_path": full_path,
                "relationship": qpath or pkg["name"],
            }
            cls_items.append(item)
        sections.append({
            "name": "Classes",
            "items": cls_items,
            "data": {"count": len(cls_items)},
        })

    # PeopleCode programs grouped by class
    pc_items = pkg.get("peoplecode") or []
    if pc_items:
        seen = set()
        pc_display = []
        for row in pc_items:
            parts = [
                str(row.get(f"objectvalue{i}") or "").strip()
                for i in range(2, 6)
                if str(row.get(f"objectvalue{i}") or "").strip()
            ]
            # last part is the event (OnExecute), second-to-last is the class
            if len(parts) >= 2:
                class_name = parts[-2]
                event = parts[-1]
                sub_path = ":".join(parts[:-2]) if len(parts) > 2 else None
            elif parts:
                class_name = parts[0]
                event = "OnExecute"
                sub_path = None
            else:
                continue

            key = (sub_path or "", class_name)
            if key in seen:
                continue
            seen.add(key)

            full_ref = f"{pkg['name']}:{':'.join(parts[:-1])}"
            # Build encoded peoplecode reference: OV1.OV2.OV3.OV4.progseq
            from connectors import peoplecode as _pc
            # Reference uses dot notation: pkgroot.subpkg.classname.OnExecute
            pc_ref_raw = f"{pkg['name']}.{'.'.join(parts)}.0"
            pc_enc = _pc.encode_reference(pc_ref_raw)
            pc_display.append({
                "title": class_name,
                "sub_package": sub_path,
                "event": event,
                "full_ref": full_ref,
                "relationship": sub_path or pkg["name"],
                "_links": {"peoplecode": f"/admin/object/peoplecode/{pc_enc}"},
            })

        sections.append({
            "name": "PeopleCode",
            "items": pc_display,
            "data": {"programs": len(pc_items), "classes": len(seen)},
        })

    if warnings:
        sections.append({"name": "Warnings", "items": [], "data": {"warnings": warnings}})

    return sections


def app_package_payload(env, package_name):
    pkg = app_package_object(env, package_name)
    counts = pkg.get("counts") or {}
    defn = pkg.get("definition") or {}
    descr = pkg.get("description") or ""

    return {
        "environment": env.upper(),
        "type": "application_package",
        "name": package_name,
        "display_name": package_name,
        "description": descr,
        "status": pkg.get("status", "partial"),
        "overview": {
            "description": descr,
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "version": str(defn.get("version") or "").strip() or None,
            "sub_packages": counts.get("sub_packages", 0),
            "classes": counts.get("classes", 0),
            "peoplecode_programs": counts.get("peoplecode_programs", 0),
        },
        "sections": sections_for_app_package(pkg),
        "_links": pkg["_links"], "_uom": pkg,
    }


_MENU_TYPE_LABELS = {
    "0": "Standard",
    "1": "Pop-up",
}


def menu_object(env, menuname):
    menuname = menuname.strip().upper()
    warnings = []

    if not ptmetadata.has_table(env, "PSMENUDEFN"):
        warnings.append(ptmetadata.warning("no_access", "PSMENUDEFN not accessible"))
        return canonical_base(
            env, "menu", menuname,
            display_name=menuname, status="unavailable", warnings=warnings,
            _links={"admin": object_url("menu", menuname)},
            _metadata={"environment": env.upper()},
        )

    defn = psdb.menu(env, menuname) or {}
    items, item_warn = safe_relationship("items", lambda: psdb.menu_items(env, menuname))
    if item_warn:
        warnings.extend(item_warn)

    descr = str(defn.get("descr") or "").strip() or menuname
    menu_type_raw = str(defn.get("menutype") or "0")

    obj = canonical_base(
        env, "menu", menuname,
        display_name=menuname,
        description=descr,
        owner=str(defn.get("objectownerid") or "").strip(),
        status="found" if defn else "not_found",
        warnings=warnings,
        _links={"admin": object_url("menu", menuname)},
        _metadata={"environment": env.upper()},
        definition=defn,
        items=items or [],
    )

    obj["_relationships"]["items"] = items or []
    obj["_graph"] = {
        "node": {"id": object_id("menu", menuname), "type": "menu", "label": menuname, "description": descr},
        "edges": [
            {"source": object_id("menu", menuname), "target": object_id("component", str(r.get("pnlgrpname") or "").strip().upper()), "type": "LISTS", "label": "Lists"}
            for r in (items or [])
            if str(r.get("pnlgrpname") or "").strip()
        ],
    }
    return obj


def sections_for_menu(obj):
    defn = obj.get("definition") or {}
    items = obj.get("items") or []
    menu_type_raw = str(defn.get("menutype") or "0")

    bars = {}
    for item in items:
        bar = str(item.get("barname") or "").strip()
        bars.setdefault(bar, []).append(item)

    bar_sections = []
    for bar, bar_items in sorted(bars.items()):
        enriched = []
        for item in sorted(bar_items, key=lambda i: i.get("itemnum") or 0):
            component = str(item.get("pnlgrpname") or "").strip()
            entry = {**item, "relationship": str(item.get("itemlabel") or "").strip() or str(item.get("itemname") or "").strip()}
            if component:
                entry["_links"] = {"admin": object_url("component", component)}
            enriched.append(entry)
        bar_sections.append({
            "name": f"Bar: {bar}" if bar else "Menu Items",
            "items": enriched,
            "data": {"count": len(enriched)},
        })

    sections = [
        {
            "name": "Definition",
            "items": [],
            "data": {
                "type": _MENU_TYPE_LABELS.get(menu_type_raw, menu_type_raw),
                "group": str(defn.get("menugroup") or "").strip() or None,
                "owner": str(defn.get("objectownerid") or "").strip() or None,
                "last_updated": str(defn.get("lastupddttm") or "").strip() or None,
                "description": str(defn.get("descrlong") or "").strip() or None,
            },
        },
    ]
    sections.extend(bar_sections)
    return [s for s in sections if s.get("items") or s.get("data")]


def menu_payload(env, menuname):
    obj = menu_object(env, menuname)
    defn = obj.get("definition") or {}
    items = obj.get("items") or []
    components = list({str(r.get("pnlgrpname") or "").strip().upper() for r in items if str(r.get("pnlgrpname") or "").strip()})

    return {
        "environment": env.upper(),
        "type": "menu",
        "name": menuname,
        "display_name": menuname,
        "description": obj.get("description") or "",
        "status": obj.get("status", "unknown"),
        "overview": {
            "description": obj.get("description") or "",
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "menu_type": _MENU_TYPE_LABELS.get(str(defn.get("menutype") or "0"), "Standard"),
            "item_count": len(items),
            "component_count": len(components),
        },
        "sections": sections_for_menu(obj),
        "_links": obj["_links"],
        "_uom": obj,
    }


_EOAW_STATUS_CHIP = {"A": ("chip-ok", "Active"), "I": ("chip-muted", "Inactive")}


def approval_object(env, eoawprcs_id):
    data = psdb.get_approval(env, eoawprcs_id)
    if "error" in data:
        return {
            "environment": env.upper(),
            "type": "approval",
            "name": eoawprcs_id,
            "display_name": eoawprcs_id,
            "description": "",
            "status": "not_found",
            "data": data,
            "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
            "_links": {"admin": object_url("approval", eoawprcs_id)},
        }
    defn = data.get("definition") or {}
    return {
        "environment": env.upper(),
        "type": "approval",
        "name": defn.get("eoawprcs_id", eoawprcs_id),
        "display_name": defn.get("eoawprcs_id", eoawprcs_id),
        "description": str(defn.get("descr") or "").strip(),
        "status": "resolved",
        "data": data,
        "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
        "_links": {"admin": object_url("approval", defn.get("eoawprcs_id", eoawprcs_id))},
    }


def sections_for_approval(obj):
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    process_definitions = data.get("process_definitions") or []
    stages = data.get("stages") or []
    paths = data.get("paths") or []
    steps = data.get("steps") or []
    default_defn_id = data.get("default_process_definition")
    sections = []

    overview = {}
    if defn.get("descr"):
        overview["Description"] = str(defn["descr"]).strip()
    if defn.get("packageroot"):
        overview["Package Root"] = str(defn["packageroot"]).strip()
    if defn.get("appclass_path"):
        overview["App Class Path"] = str(defn["appclass_path"]).strip()
    if defn.get("eoawappr_component"):
        overview["Approval Component"] = str(defn["eoawappr_component"]).strip()
    if defn.get("menuname"):
        overview["Menu"] = str(defn["menuname"]).strip()
    if defn.get("objectownerid"):
        overview["Owner"] = str(defn["objectownerid"]).strip()
    overview["Email"] = "Yes" if str(defn.get("eoaw_email") or "") == "Y" else "No"
    overview["Worklist"] = "Yes" if str(defn.get("eoaw_worklist") or "") == "Y" else "No"
    overview["Push"] = "Yes" if str(defn.get("eoaw_push") or "") == "Y" else "No"
    counts = data.get("counts") or {}
    if counts:
        overview["Process Definitions"] = str(counts.get("process_definitions", 0))
        overview["Stages"] = str(counts.get("stages", 0))
        overview["Steps"] = str(counts.get("steps", 0))
        overview["Paths"] = str(counts.get("paths", 0))
    sections.append({"name": "Definition", "items": [], "data": overview})

    if process_definitions:
        pd_items = []
        for pd in process_definitions:
            _, status_label = _EOAW_STATUS_CHIP.get(str(pd.get("eff_status") or ""), ("chip-muted", pd.get("eff_status") or ""))
            is_default = pd.get("eoawdefn_id") == default_defn_id
            pd_items.append({
                "title": f"{pd.get('eoawdefn_id')}: {str(pd.get('descr') or '').strip()}",
                "relationship": status_label,
                "admin_role": str(pd.get("eoawadmin_rolename") or "").strip() or None,
                "auto_approve": pd.get("eoawauto_approve") == "Y",
                "default": is_default,
            })
        sections.append({"name": "Process Definitions", "items": pd_items, "count": len(pd_items)})

    if stages:
        stage_items = []
        steps_by_stage = {}
        for s in steps:
            steps_by_stage.setdefault(s.get("eoawstage_nbr"), []).append(s)
        for stage in stages:
            sn = stage.get("eoawstage_nbr")
            stage_items.append({
                "title": f"Stage {sn}: {str(stage.get('descr') or '').strip()}",
                "relationship": f"Level {stage.get('eoawlevel')}" if stage.get("eoawlevel") is not None else None,
                "stage_no": sn,
                "step_count": len(steps_by_stage.get(sn, [])),
            })
        sections.append({"name": "Stages", "items": stage_items, "count": len(stage_items)})

    if steps:
        step_items = []
        for st in steps:
            approver = str(st.get("eoawapprover_list") or "").strip() or str(st.get("eoawrolename") or "").strip()
            step_items.append({
                "title": (
                    f"Stage {st.get('eoawstage_nbr')} Step {st.get('eoawstep_nbr')}: "
                    f"{str(st.get('descr') or '').strip()}"
                ),
                "relationship": approver or None,
                "min_approvers": st.get("eoawmin_approvers"),
                "path_id": st.get("eoawpath_id"),
            })
        sections.append({"name": "Steps", "items": step_items, "count": len(step_items)})

    if paths:
        path_items = []
        for p in paths:
            escal = []
            if p.get("eoawnumber_days"):
                escal.append(f"{p['eoawnumber_days']}d")
            if p.get("eoawnumber_hours"):
                escal.append(f"{p['eoawnumber_hours']}h")
            path_items.append({
                "title": f"Stage {p.get('eoawstage_nbr')} Path {p.get('eoawpath_id')}: {str(p.get('descr') or '').strip()}",
                "relationship": " ".join(escal) or None,
            })
        sections.append({"name": "Paths", "items": path_items, "count": len(path_items)})

    return [s for s in sections if s.get("data") or s.get("items")]


def approval_payload(env, eoawprcs_id):
    obj = approval_object(env, eoawprcs_id)
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    counts = data.get("counts") or {}
    return {
        "environment": env.upper(),
        "type": "approval",
        "name": obj["name"],
        "display_name": obj["display_name"],
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "description": str(defn.get("descr") or "").strip(),
            "package_root": str(defn.get("packageroot") or "").strip() or None,
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "process_definition_count": counts.get("process_definitions", 0),
            "stage_count": counts.get("stages", 0),
            "step_count": counts.get("steps", 0),
            "path_count": counts.get("paths", 0),
        },
        "sections": sections_for_approval(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_MSG_SEVERITY_CHIP = {
    "0": ("chip-info",  "Message"),
    "1": ("chip-warn",  "Warning"),
    "2": ("chip-error", "Error"),
    "3": ("chip-crit",  "Cancel"),
}


def message_catalog_object(env, name):
    """Load a message catalog entry. Name must be '{set_nbr}.{msg_nbr}'."""
    warnings = []
    try:
        sn_str, mn_str = name.split(".", 1)
        set_nbr = int(sn_str)
        msg_nbr = int(mn_str)
    except (ValueError, AttributeError):
        return {
            "environment": env.upper(), "type": "message_catalog", "name": name,
            "status": "not_found", "warnings": [{"code": "invalid_name",
                "message": f"Invalid message catalog name: {name!r}. Expected SET.MSG format."}],
        }

    msg = psdb.get_message(env, set_nbr, msg_nbr)
    if not msg:
        warnings.append({"code": "not_found", "message": f"Message {name} not found."})

    set_info = psdb.message_set_info(env, set_nbr)

    return {
        "environment": env.upper(),
        "type": "message_catalog",
        "name": name,
        "display_name": f"Msg {name}",
        "description": str(msg.get("message_text") or "").strip() if msg else "",
        "status": "resolved" if msg else "not_found",
        "set_nbr": set_nbr,
        "msg_nbr": msg_nbr,
        "message": msg or {},
        "set_info": set_info or {},
        "warnings": warnings,
        "_links": {"admin": object_url("message_catalog", name)},
    }


def sections_for_message_catalog(obj):
    msg = obj.get("message") or {}
    set_info = obj.get("set_info") or {}
    sections = []

    overview = {}
    if msg.get("severity") is not None:
        severity_val = str(msg.get("severity") or "0")
        _, label = _MSG_SEVERITY_CHIP.get(severity_val, ("chip-muted", "Unknown"))
        overview["Severity"] = label
    if set_info.get("descr"):
        overview["Message Set"] = (
            f"{obj['set_nbr']} — {str(set_info['descr']).strip()}"
        )
    else:
        overview["Message Set"] = str(obj.get("set_nbr", ""))
    overview["Message Number"] = str(obj.get("msg_nbr", ""))

    msg_text = str(msg.get("message_text") or "").strip()
    if msg_text:
        overview["Message Text"] = msg_text

    explanation = str(msg.get("descrlong") or "").strip()
    if explanation:
        overview["Explanation"] = explanation

    sections.append({"name": "Definition", "items": [], "data": overview})

    return [s for s in sections if s.get("data") or s.get("items")]


def message_catalog_payload(env, name):
    obj = message_catalog_object(env, name)
    msg = obj.get("message") or {}
    set_info = obj.get("set_info") or {}

    return {
        "environment": env.upper(),
        "type": "message_catalog",
        "name": name,
        "display_name": obj.get("display_name", f"Msg {name}"),
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "set_nbr": obj.get("set_nbr"),
            "msg_nbr": obj.get("msg_nbr"),
            "severity": str(msg.get("severity") or ""),
            "severity_label": msg.get("severity_label") or "",
            "message_text": str(msg.get("message_text") or "").strip(),
            "explanation": str(msg.get("descrlong") or "").strip(),
            "set_description": str(set_info.get("descr") or "").strip() or None,
        },
        "sections": sections_for_message_catalog(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_XPUB_DATASRC_CHIP = {
    "XML": ("chip-info", "XML"),
    "CQR": ("chip-info", "Connected Query"),
    "QRY": ("chip-info", "PS Query"),
    "XMD": ("chip-info", "XML Data"),
    "RST": ("chip-info", "REST"),
}

_XPUB_STATUS_CHIP = {
    "A": ("chip-ok",    "Active"),
    "I": ("chip-muted", "Inactive"),
}


def xpub_report_object(env, report_defn_id):
    data = psdb.get_xpub_report(env, report_defn_id.upper())
    defn = data.get("definition")
    return {
        "environment": env.upper(),
        "type": "xml_publisher_report",
        "name": report_defn_id.upper(),
        "display_name": report_defn_id.upper(),
        "description": str(defn.get("descr") or "").strip() if defn else "",
        "status": "resolved" if defn else "not_found",
        "data": data,
        "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
        "_links": {"admin": object_url("xml_publisher_report", report_defn_id.upper())},
    }


def sections_for_xpub_report(obj):
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    datasrc = data.get("datasource") or {}
    category = data.get("category") or {}
    templates = data.get("templates") or []
    output_formats = data.get("output_formats") or []
    sections = []

    overview = {}
    if defn.get("descr"):
        overview["Description"] = str(defn["descr"]).strip()
    if defn.get("objectownerid"):
        overview["Owner"] = str(defn["objectownerid"]).strip()
    st = str(defn.get("pt_report_status") or "").strip()
    if st:
        _, status_label = _XPUB_STATUS_CHIP.get(st, ("chip-muted", st))
        overview["Status"] = status_label
    if defn.get("pt_template_type"):
        overview["Template Type"] = str(defn["pt_template_type"]).strip()
    if defn.get("ds_id"):
        overview["Data Source"] = str(defn["ds_id"]).strip()
    if category.get("descr"):
        overview["Category"] = str(category["descr"]).strip()
    if defn.get("lastupdoprid"):
        overview["Last Updated By"] = str(defn["lastupdoprid"]).strip()
    if defn.get("lastupddttm"):
        overview["Last Updated"] = str(defn["lastupddttm"])
    if overview:
        sections.append({"name": "Definition", "items": [], "data": overview})

    if templates:
        tmpl_items = []
        for t in templates:
            lang = str(t.get("tmpllangcd") or "").strip()
            ttype = str(t.get("pt_template_type") or "").strip()
            is_default = t.get("is_default") == "Y"
            tmpl_items.append({
                "title": f"{t.get('tmpldefn_id')}: {str(t.get('descr') or '').strip()}",
                "relationship": ttype or None,
                "lang": lang or None,
                "default": is_default,
            })
        sections.append({"name": "Templates", "items": tmpl_items, "count": len(tmpl_items)})

    if output_formats:
        fmt_items = []
        for f in output_formats:
            fmt_items.append({
                "title": str(f.get("pt_format_type") or "").strip(),
                "default": f.get("is_default") == "Y",
            })
        sections.append({"name": "Output Formats", "items": fmt_items, "count": len(fmt_items)})

    return [s for s in sections if s.get("data") or s.get("items")]


def xpub_report_payload(env, report_defn_id):
    obj = xpub_report_object(env, report_defn_id)
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    datasrc = data.get("datasource") or {}
    counts = data.get("counts") or {}
    return {
        "environment": env.upper(),
        "type": "xml_publisher_report",
        "name": report_defn_id.upper(),
        "display_name": report_defn_id.upper(),
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "description": str(defn.get("descr") or "").strip(),
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "ds_id": str(defn.get("ds_id") or "").strip() or None,
            "datasrc_descr": str(datasrc.get("descr") or "").strip() or None,
            "datasrc_type": str(datasrc.get("ds_type") or "").strip() or None,
            "datasrc_type_label": datasrc.get("ds_type_label") or None,
            "status_label": defn.get("pt_report_status_label") or None,
            "template_count": counts.get("templates", 0),
            "output_format_count": counts.get("output_formats", 0),
        },
        "sections": sections_for_xpub_report(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_NC_LINE_TYPE_CHIP = {
    "C": ("chip-info",  "Content Ref"),
    "F": ("chip-muted", "Folder"),
    "T": ("chip-ok",    "Tile"),
    "S": ("chip-muted", "Static Link"),
}

_NC_STATUS_CHIP = {
    "A": ("chip-ok",    "Active"),
    "I": ("chip-muted", "Inactive"),
}


def nav_collection_object(env, coll_id):
    data = psdb.get_nav_collection(env, coll_id.upper())
    defn = data.get("definition")
    return {
        "environment": env.upper(),
        "type": "nav_collection",
        "name": coll_id.upper(),
        "display_name": coll_id.upper(),
        "description": str(defn.get("coll_title") or "").strip() if defn else "",
        "status": "resolved" if defn else "not_found",
        "data": data,
        "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
        "_links": {"admin": object_url("nav_collection", coll_id.upper())},
    }


def sections_for_nav_collection(obj):
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    lines = data.get("lines") or []
    sections = []

    overview = {}
    if defn.get("coll_title"):
        overview["Title"] = str(defn["coll_title"]).strip()
    eff_status = str(defn.get("eff_status") or "").strip()
    if eff_status:
        _, label = _NC_STATUS_CHIP.get(eff_status, ("chip-muted", eff_status))
        overview["Status"] = label
    if defn.get("portal_name"):
        overview["Portal"] = str(defn["portal_name"]).strip()
    if defn.get("objectownerid"):
        overview["Owner"] = str(defn["objectownerid"]).strip()
    if defn.get("lastupdoprid"):
        overview["Last Updated By"] = str(defn["lastupdoprid"]).strip()
    if defn.get("lastupddttm"):
        overview["Last Updated"] = str(defn["lastupddttm"])
    overview["Lines"] = str(len(lines))
    sections.append({"name": "Definition", "items": [], "data": overview})

    if lines:
        line_items = []
        for ln in lines:
            lt = str(ln.get("line_type") or "")
            lt_label = ln.get("line_type_label") or lt
            url = str(ln.get("portal_urltext") or "").strip()
            label = str(ln.get("label") or "").strip()
            line_items.append({
                "title": label or url or f"Line {ln.get('line_nbr', '')}",
                "relationship": lt_label or None,
                "url": url or None,
                "line_nbr": ln.get("line_nbr"),
            })
        sections.append({"name": "Lines", "items": line_items, "count": len(line_items)})

    return [s for s in sections if s.get("data") or s.get("items")]


def nav_collection_payload(env, coll_id):
    obj = nav_collection_object(env, coll_id)
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    counts = data.get("counts") or {}
    return {
        "environment": env.upper(),
        "type": "nav_collection",
        "name": coll_id.upper(),
        "display_name": coll_id.upper(),
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "title": str(defn.get("coll_title") or "").strip(),
            "portal": str(defn.get("portal_name") or "").strip() or None,
            "eff_status": str(defn.get("eff_status") or "").strip() or None,
            "eff_status_label": defn.get("eff_status_label") or None,
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "line_count": counts.get("lines", 0),
        },
        "sections": sections_for_nav_collection(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_EF_STATUS_CHIP = {
    "A": ("chip-ok",    "Active"),
    "I": ("chip-muted", "Inactive"),
}


def event_mapping_object(env, efmappingid):
    data = psdb.get_event_mapping(env, efmappingid.upper())
    defn = data.get("definition")
    return {
        "environment": env.upper(),
        "type": "event_mapping",
        "name": efmappingid.upper(),
        "display_name": efmappingid.upper(),
        "description": str(defn.get("descr") or "").strip() if defn else "",
        "status": "resolved" if defn else "not_found",
        "data": data,
        "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
        "_links": {"admin": object_url("event_mapping", efmappingid.upper())},
    }


def sections_for_event_mapping(obj):
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    contexts = data.get("contexts") or []
    sections = []

    overview = {}
    if defn.get("descr"):
        overview["Description"] = str(defn["descr"]).strip()
    st = str(defn.get("status") or "").strip()
    if st:
        _, label = _EF_STATUS_CHIP.get(st, ("chip-muted", st))
        overview["Status"] = label
    if defn.get("objectownerid"):
        overview["Owner"] = str(defn["objectownerid"]).strip()
    if defn.get("lastupdoprid"):
        overview["Last Updated By"] = str(defn["lastupdoprid"]).strip()
    if defn.get("lastupddttm"):
        overview["Last Updated"] = str(defn["lastupddttm"])
    sections.append({"name": "Definition", "items": [], "data": overview})

    if contexts:
        ctx_items = []
        for c in contexts:
            ctx_type = str(c.get("efcontexttype") or "").strip()
            ctx_val = str(c.get("efcontextvalue") or "").strip()
            event = str(c.get("appeventname") or "").strip()
            handler = str(c.get("appeventhandler") or "").strip()
            ctx_items.append({
                "title": ctx_val or f"Context {c.get('seqno', '')}",
                "relationship": ctx_type or None,
                "event": event or None,
                "handler": handler or None,
            })
        sections.append({"name": "Contexts", "items": ctx_items, "count": len(ctx_items)})

    return [s for s in sections if s.get("data") or s.get("items")]


def event_mapping_payload(env, efmappingid):
    obj = event_mapping_object(env, efmappingid)
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    counts = data.get("counts") or {}
    return {
        "environment": env.upper(),
        "type": "event_mapping",
        "name": efmappingid.upper(),
        "display_name": efmappingid.upper(),
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "description": str(defn.get("descr") or "").strip(),
            "status": str(defn.get("status") or "").strip() or None,
            "owner": str(defn.get("objectownerid") or "").strip() or None,
            "context_count": counts.get("contexts", 0),
        },
        "sections": sections_for_event_mapping(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_RC_TYPE_CHIP = {
    "U": ("chip-info",  "URL"),
    "C": ("chip-info",  "Component"),
    "S": ("chip-info",  "Script"),
    "A": ("chip-info",  "App Class"),
    "P": ("chip-info",  "PS Page"),
    "I": ("chip-info",  "iScript"),
    "R": ("chip-info",  "Related Action"),
}


def related_content_object(env, relconid):
    data = psdb.get_related_content(env, relconid.upper())
    defn = data.get("definition")
    return {
        "environment": env.upper(),
        "type": "related_content",
        "name": relconid.upper(),
        "display_name": relconid.upper(),
        "description": str(defn.get("descr") or "").strip() if defn else "",
        "status": "resolved" if defn else "not_found",
        "data": data,
        "warnings": [{"code": w, "message": w} for w in data.get("warnings", [])],
        "_links": {"admin": object_url("related_content", relconid.upper())},
    }


def sections_for_related_content(obj):
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    sections = []

    overview = {}
    if defn.get("descr"):
        overview["Description"] = str(defn["descr"]).strip()
    st = str(defn.get("status") or "").strip()
    if st:
        _, label = _EF_STATUS_CHIP.get(st, ("chip-muted", st))
        overview["Status"] = label
    svc_type = str(defn.get("servicetype") or "").strip()
    if svc_type:
        overview["Service Type"] = defn.get("servicetype_label") or svc_type
    if defn.get("objectownerid"):
        overview["Owner"] = str(defn["objectownerid"]).strip()
    if defn.get("lastupdoprid"):
        overview["Last Updated By"] = str(defn["lastupdoprid"]).strip()
    if defn.get("lastupddttm"):
        overview["Last Updated"] = str(defn["lastupddttm"])
    sections.append({"name": "Definition", "items": [], "data": overview})

    return [s for s in sections if s.get("data") or s.get("items")]


def related_content_payload(env, relconid):
    obj = related_content_object(env, relconid)
    data = obj.get("data") or {}
    defn = data.get("definition") or {}
    return {
        "environment": env.upper(),
        "type": "related_content",
        "name": relconid.upper(),
        "display_name": relconid.upper(),
        "description": obj.get("description", ""),
        "status": obj.get("status", "unknown"),
        "overview": {
            "description": str(defn.get("descr") or "").strip(),
            "status": str(defn.get("status") or "").strip() or None,
            "servicetype": str(defn.get("servicetype") or "").strip() or None,
            "servicetype_label": defn.get("servicetype_label") or None,
            "owner": str(defn.get("objectownerid") or "").strip() or None,
        },
        "sections": sections_for_related_content(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_SRCH_SOURCE_TYPE_CHIP = {
    "Application Class": "chip-info",
    "Connected Query":   "chip-info",
    "PS Query":          "chip-info",
}


def search_definition_object(env, source_name):
    data = psdb.get_search_definition(env, source_name.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    return {
        "type": "search_definition",
        "name": defn.get("ptsf_source_name", source_name),
        "title": defn.get("descr100") or source_name,
        "source_type": defn.get("ptsf_source_type_label"),
        "owner": defn.get("objectownerid"),
        "_raw": data,
        "_links": {"admin": object_url("search_definition", source_name.upper())},
        "warnings": data.get("warnings", []),
    }


def sections_for_search_definition(obj):
    raw = obj.get("_raw", {})
    defn = raw.get("definition", {})
    fields = raw.get("fields", [])
    panel_groups = raw.get("panel_groups", [])
    counts = raw.get("counts", {})
    sections = []

    overview_rows = [
        ("Source Name", defn.get("ptsf_source_name")),
        ("Description", defn.get("descr100")),
        ("Source Type", defn.get("ptsf_source_type_label")),
        ("Search Business Object", defn.get("ptsf_sbo_name")),
        ("Owner", defn.get("objectownerid")),
        ("Package Root", str(defn.get("packageroot") or "").strip() or None),
        ("Global Search", "Yes" if str(defn.get("ptsf_isgblsrch") or "").strip() == "Y" else None),
        ("Last Refreshed", defn.get("lastrefreshdttm")),
        ("Last Updated", defn.get("lastupddttm")),
        ("Last Updated By", defn.get("lastupdoprid")),
    ]
    sections.append({"id": "overview", "title": "Overview",
                     "rows": [{"label": k, "value": v} for k, v in overview_rows if v is not None]})

    if fields:
        field_items = []
        for f in fields:
            chips = []
            if str(f.get("ptsf_isfieldtoidx") or "").strip() == "Y":
                chips.append({"label": "Indexed", "cls": "chip-info"})
            if str(f.get("ptsf_isfldtodispl") or "").strip() == "Y":
                chips.append({"label": "Displayed", "cls": "chip-info"})
            if str(f.get("ptsf_is_faceted") or "").strip() == "Y":
                chips.append({"label": "Faceted", "cls": "chip-info"})
            name = str(f.get("ptsf_srcattr_name") or "").strip() or f.get("qryfldname", "")
            field_items.append({
                "name": name,
                "label": name,
                "chips": chips,
                "meta": f"seq {f.get('seqnum', '')} · {f.get('qryfldname', '')}",
            })
        sections.append({"id": "fields", "title": f"Fields ({counts.get('fields', len(fields))})",
                         "items": field_items})

    if panel_groups:
        pg_items = []
        for pg in panel_groups:
            pg_items.append({
                "name": str(pg.get("pnlgrpname") or "").strip() or "(none)",
                "label": str(pg.get("pnlgrpname") or "").strip() or "(none)",
                "chips": [{"label": pg.get("market"), "cls": "chip-muted"}] if pg.get("market") else [],
                "meta": str(pg.get("ptsf_srch_criteria") or "").strip(),
            })
        sections.append({"id": "panel_groups", "title": f"Panel Groups ({counts.get('panel_groups', len(panel_groups))})",
                         "items": pg_items})

    return sections


def search_definition_payload(env, source_name):
    obj = search_definition_object(env, source_name)
    if obj is None:
        return None
    return {
        "type": "search_definition",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "source_type": obj.get("source_type"),
            "owner": obj.get("owner"),
        },
        "sections": sections_for_search_definition(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


def search_category_object(env, srccatname):
    data = psdb.get_search_category(env, srccatname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    return {
        "type": "search_category",
        "name": defn.get("ptsf_srccat_name", srccatname),
        "title": defn.get("descr100") or srccatname,
        "sbo_name": (data.get("sbo_links") or [{}])[0].get("ptsf_sbo_name"),
        "_raw": data,
        "_links": {"admin": object_url("search_category", srccatname.upper())},
        "warnings": data.get("warnings", []),
    }


def sections_for_search_category(obj):
    raw = obj.get("_raw", {})
    defn = raw.get("definition", {})
    sbo_links = raw.get("sbo_links", [])
    display_fields = raw.get("display_fields", [])
    advanced_fields = raw.get("advanced_fields", [])
    facets = raw.get("facets", [])
    counts = raw.get("counts", {})
    sections = []

    def _clean(v):
        v = str(v or "").strip()
        return v or None

    overview_rows = [
        ("Name", _clean(defn.get("ptsf_srccat_name"))),
        ("Description", _clean(defn.get("descr100"))),
        ("Owner", _clean(defn.get("objectownerid"))),
        ("Market", _clean(defn.get("market"))),
        ("Package Root", _clean(defn.get("packageroot"))),
        ("Menu", _clean(defn.get("menuname"))),
        ("Panel Group", _clean(defn.get("pnlgrpname"))),
        ("Search Engine", _clean(defn.get("ptsf_srch_eng"))),
        ("Display Type", _clean(defn.get("ptsf_display_type"))),
        ("Global Search", "Yes" if _clean(defn.get("ptsf_isgblsrch")) == "Y" else None),
        ("Allow Duplicates", "Yes" if _clean(defn.get("ptsf_allow_dups")) == "Y" else None),
        ("Last Updated", defn.get("lastupddttm")),
        ("Last Updated By", _clean(defn.get("lastupdoprid"))),
    ]
    sections.append({"id": "overview", "title": "Overview",
                     "rows": [{"label": k, "value": v} for k, v in overview_rows if v is not None]})

    if sbo_links:
        sbo_items = []
        for s in sbo_links:
            sbo_items.append({
                "name": s.get("ptsf_sbo_name", ""),
                "label": s.get("ptsf_sbo_name", ""),
                "chips": [],
                "meta": s.get("msgnodename", ""),
            })
        sections.append({"id": "sbo_links", "title": f"Search Business Objects ({counts.get('sbo_links', len(sbo_links))})",
                         "items": sbo_items})

    if display_fields:
        fld_items = []
        for f in display_fields:
            name = _clean(f.get("ptsf_srcattr_name")) or "(unnamed)"
            disp_type = _clean(f.get("ptsf_fld_disp_type"))
            chips = [{"label": disp_type, "cls": "chip-info"}] if disp_type else []
            fld_items.append({
                "name": name,
                "label": name,
                "chips": chips,
                "meta": f"Seq {f.get('seqno')}" if f.get("seqno") is not None else "",
            })
        sections.append({"id": "display_fields", "title": f"Display Fields ({counts.get('display_fields', len(display_fields))})",
                         "items": fld_items})

    if advanced_fields:
        adv_items = []
        for f in advanced_fields:
            adv_items.append({
                "name": f.get("ptsf_srcattr_name", ""),
                "label": f.get("ptsf_srcattr_name", ""),
                "chips": [],
                "meta": f"Seq {f.get('seqno')}" if f.get("seqno") is not None else "",
            })
        sections.append({"id": "advanced_fields", "title": f"Advanced Search Fields ({counts.get('advanced_fields', len(advanced_fields))})",
                         "items": adv_items})

    if facets:
        facet_items = []
        for f in facets:
            chips = [{"label": "Multi-select", "cls": "chip-muted"}] if f.get("ptsf_fct_multisel") == "Y" else []
            order = _clean(f.get("ptsf_facet_order"))
            facet_items.append({
                "name": f.get("ptsf_facet_name", ""),
                "label": f.get("ptsf_facet_name", ""),
                "chips": chips,
                "meta": f"Order {order}" if order else "",
            })
        sections.append({"id": "facets", "title": f"Facets ({counts.get('facets', len(facets))})",
                         "items": facet_items})

    return sections


def search_category_payload(env, srccatname):
    obj = search_category_object(env, srccatname)
    if obj is None:
        return None
    return {
        "type": "search_category",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "sbo_name": obj.get("sbo_name"),
        },
        "sections": sections_for_search_category(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


def drop_zone_object(env, dzname):
    data = psdb.get_drop_zone(env, dzname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    return {
        "type": "drop_zone",
        "name": defn.get("dzname", dzname),
        "title": defn.get("descr") or dzname,
        "owner": defn.get("objectownerid"),
        "_raw": data,
        "_links": {"admin": object_url("drop_zone", dzname.upper())},
        "warnings": data.get("warnings", []),
    }


def sections_for_drop_zone(obj):
    raw = obj.get("_raw", {})
    defn = raw.get("definition", {})
    components = raw.get("components", [])
    pages = raw.get("pages", [])
    items = raw.get("items", [])
    counts = raw.get("counts", {})
    sections = []

    overview_rows = [
        ("Name", defn.get("dzname")),
        ("Description", defn.get("descr")),
        ("Owner", defn.get("objectownerid")),
        ("Last Updated", defn.get("lastupddttm")),
        ("Last Updated By", defn.get("lastupdoprid")),
    ]
    sections.append({"id": "overview", "title": "Overview",
                     "rows": [{"label": k, "value": v} for k, v in overview_rows if v is not None]})

    if components:
        comp_items = [{"name": c.get("component", ""), "label": c.get("component", ""),
                       "chips": [], "meta": c.get("pnlgrpname", "")} for c in components]
        sections.append({"id": "components", "title": f"Components ({counts.get('components', len(components))})",
                         "items": comp_items})

    if pages:
        page_items = [{"name": p.get("page", ""), "label": p.get("page", ""),
                      "chips": [], "meta": p.get("pnlname", "")} for p in pages]
        sections.append({"id": "pages", "title": f"Pages ({counts.get('pages', len(pages))})",
                         "items": page_items})

    if items:
        item_items = [{"name": i.get("objectvalue1", ""), "label": i.get("objectvalue1", ""),
                      "chips": [], "meta": i.get("objectvalue2", "")} for i in items]
        sections.append({"id": "items", "title": f"Items ({counts.get('items', len(items))})",
                         "items": item_items})

    return sections


def drop_zone_payload(env, dzname):
    obj = drop_zone_object(env, dzname)
    if obj is None:
        return None
    return {
        "type": "drop_zone",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "owner": obj.get("owner"),
        },
        "sections": sections_for_drop_zone(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_PTPG_DSTYPE_CHIP = {
    "PSQUERY": "chip-info",
    "COMPONENT": "chip-info",
}
_PTPG_COLTYPE_CHIP = {
    "DIM": ("chip-ok", "Dimension"),
    "DISO": ("chip-muted", "Display Only"),
    "VAL": ("chip-ok", "Value"),
}


def pivot_grid_object(env, pgridname):
    data = psdb.get_pivot_grid(env, pgridname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    return {
        "type": "pivot_grid",
        "name": defn.get("ptpg_pgridname", pgridname),
        "title": defn.get("ptpg_pgridtitle") or pgridname,
        "ds_type": defn.get("ptpg_dstype"),
        "ds_type_label": defn.get("ptpg_dstype_label"),
        "datasource_name": data.get("datasource_name"),
        "owner": str(defn.get("objectownerid") or "").strip() or None,
        "_raw": data,
        "_links": {"admin": object_url("pivot_grid", pgridname.upper())},
        "warnings": data.get("warnings", []),
    }


def sections_for_pivot_grid(obj):
    raw = obj.get("_raw", {})
    defn = raw.get("definition", {})
    columns = raw.get("columns", [])
    nui = raw.get("nui_opts", {})
    counts = raw.get("counts", {})
    sections = []

    def _c(v):
        return str(v or "").strip() or None

    overview_rows = [
        ("Name", _c(defn.get("ptpg_pgridname"))),
        ("Title", _c(defn.get("ptpg_pgridtitle"))),
        ("Description", _c(defn.get("descrlong"))),
        ("Data Source Type", defn.get("ptpg_dstype_label")),
        ("Data Source", obj.get("datasource_name")),
        ("View Name", _c(nui.get("ptpg_viewname"))),
        ("Component Mapping", _c(nui.get("ptpg_compmapping"))),
        ("Access Group", _c(nui.get("access_group"))),
        ("Publish as Tile", "Yes" if _c(nui.get("ptpg_allowpubtile")) == "Y" else None),
        ("Allow Share", "Yes" if _c(nui.get("ptpg_allowshare")) == "Y" else None),
        ("Owner", obj.get("owner")),
        ("Valid Model", "Yes" if _c(defn.get("ptpg_isvalidmodel")) == "Y" else None),
        ("Last Updated", defn.get("lastupddttm")),
        ("Last Updated By", _c(defn.get("lastupdoprid"))),
    ]
    sections.append({"id": "overview", "title": "Overview",
                     "rows": [{"label": k, "value": v} for k, v in overview_rows if v is not None]})

    if columns:
        col_items = []
        for c in columns:
            ctype = _c(c.get("ptpg_colmntype"))
            chip_info = _PTPG_COLTYPE_CHIP.get(ctype)
            chips = [{"label": chip_info[1], "cls": chip_info[0]}] if chip_info else []
            col_items.append({
                "name": c.get("ptpg_dscolumn", ""),
                "label": c.get("ptpg_dscolumn", ""),
                "chips": chips,
                "meta": _c(c.get("ptpg_format")) or "",
            })
        sections.append({"id": "columns", "title": f"Data Model Columns ({counts.get('columns', len(columns))})",
                         "items": col_items})

    return sections


def pivot_grid_payload(env, pgridname):
    obj = pivot_grid_object(env, pgridname)
    if obj is None:
        return None
    return {
        "type": "pivot_grid",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "ds_type": obj.get("ds_type_label"),
            "datasource": obj.get("datasource_name"),
            "owner": obj.get("owner"),
        },
        "sections": sections_for_pivot_grid(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


_CONQRS_STATUS_CHIP = {"A": ("chip-ok", "Active"), "I": ("chip-muted", "Inactive")}


def connected_query_object(env, conqrsname):
    data = psdb.get_connected_query(env, conqrsname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    status = str(defn.get("pt_report_status") or "").strip()
    return {
        "type": "connected_query",
        "name": defn.get("conqrsname", conqrsname),
        "title": defn.get("descr") or conqrsname,
        "status": status,
        "status_label": defn.get("pt_report_status_label", ""),
        "owner": str(defn.get("objectownerid") or "").strip() or None,
        "_raw": data,
        "_links": {"admin": object_url("connected_query", conqrsname.upper())},
        "warnings": data.get("warnings", []),
    }


def sections_for_connected_query(obj):
    raw = obj.get("_raw", {})
    defn = raw.get("definition", {})
    query_map = raw.get("query_map", [])
    field_rels = raw.get("field_rels", [])
    counts = raw.get("counts", {})
    sections = []

    status = str(defn.get("pt_report_status") or "").strip()
    chip_cls, chip_lbl = _CONQRS_STATUS_CHIP.get(status, ("chip-muted", status or "Unknown"))

    overview_rows = [
        ("Name", str(defn.get("conqrsname") or "").strip() or None),
        ("Description", str(defn.get("descr") or "").strip() or None),
        ("Status", defn.get("pt_report_status_label") or None),
        ("Owner", str(defn.get("objectownerid") or "").strip() or None),
        ("Version", defn.get("version")),
        ("Long Description", str(defn.get("descrlong") or "").strip() or None),
        ("Last Updated", defn.get("lastupddttm")),
        ("Last Updated By", str(defn.get("lastupdoprid") or "").strip() or None),
    ]
    sections.append({"id": "overview", "title": "Overview",
                     "rows": [{"label": k, "value": v} for k, v in overview_rows if v is not None]})

    if query_map:
        qmap_items = []
        for m in query_map:
            parent = str(m.get("qrynameparent") or "").strip()
            child = str(m.get("qrynamechild") or "").strip()
            chips = [{"label": "Root", "cls": "chip-ok"}] if not parent else []
            meta = f"← {parent}" if parent else ""
            qmap_items.append({
                "name": child,
                "label": child,
                "chips": chips,
                "meta": meta,
            })
        sections.append({"id": "query_map", "title": f"Component Queries ({counts.get('sub_queries', len(query_map))})",
                         "items": qmap_items})

    if field_rels:
        frel_items = []
        for f in field_rels:
            par_fld = str(f.get("qryfldnamepar") or "").strip()
            chd_fld = str(f.get("qryfldnamechild") or "").strip()
            frel_items.append({
                "name": chd_fld,
                "label": chd_fld,
                "chips": [],
                "meta": f"← {par_fld}" if par_fld else "",
            })
        sections.append({"id": "field_joins", "title": f"Field Joins ({counts.get('field_joins', len(field_rels))})",
                         "items": frel_items})

    return sections


def connected_query_payload(env, conqrsname):
    obj = connected_query_object(env, conqrsname)
    if obj is None:
        return None
    return {
        "type": "connected_query",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "status": obj.get("status_label"),
            "owner": obj.get("owner"),
        },
        "sections": sections_for_connected_query(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


# ---------------------------------------------------------------------------
# IB Message Definitions (PSMSGDEFN)
# ---------------------------------------------------------------------------

_IB_MSG_STATUS_CLS = {0: ("chip-ok", "Active"), 1: ("chip-muted", "Inactive")}
_IB_MSG_TYPE_CLS = {
    0: "chip-muted", 1: "chip-muted", 2: "chip-info", 3: "chip-muted", 4: "chip-muted"
}


def ib_message_object(env, msgname):
    data = psdb.get_ib_message(env, msgname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    status = defn.get("msgstatus", 0)
    status_cls, status_label = _IB_MSG_STATUS_CLS.get(status, ("chip-muted", "Unknown"))
    return {
        "type": "message",
        "name": defn.get("msgname", msgname),
        "title": (defn.get("descr") or defn.get("msgdisplayname") or "").strip() or msgname,
        "channel": (defn.get("chnlname") or "").strip() or None,
        "default_ver": (defn.get("defaultver") or "").strip() or None,
        "status": status,
        "status_label": status_label,
        "status_cls": status_cls,
        "owner": (defn.get("objectownerid") or "").strip() or None,
        "xml_alias": (defn.get("xmlalias") or "").strip() or None,
        "lastupdoprid": (defn.get("lastupdoprid") or "").strip() or None,
        "lastupddttm": defn.get("lastupddttm"),
        "versions": data.get("versions", []),
        "schema_records": data.get("schema_records", []),
        "counts": data.get("counts", {}),
        "_raw": data,
        "_links": {"admin": "/admin/ibmessage"},
        "warnings": data.get("warnings", []),
    }


def sections_for_ib_message(obj):
    from connectors.psdb import _IB_MSG_TYPE
    sections = []

    # Overview
    ov_rows = []
    ov_rows.append({"label": "Status", "chips": [{"label": obj["status_label"], "cls": obj["status_cls"]}]})
    if obj.get("channel"):
        ov_rows.append({"label": "Queue/Channel", "value": obj["channel"]})
    if obj.get("default_ver"):
        ov_rows.append({"label": "Default Version", "value": obj["default_ver"]})
    if obj.get("owner"):
        ov_rows.append({"label": "Owner", "value": obj["owner"]})
    if obj.get("xml_alias"):
        ov_rows.append({"label": "XML Alias", "value": obj["xml_alias"]})
    if obj.get("lastupdoprid"):
        ov_rows.append({"label": "Last Updated By", "value": obj["lastupdoprid"]})
    if obj.get("lastupddttm"):
        ov_rows.append({"label": "Last Updated", "value": str(obj["lastupddttm"])[:19]})

    sections.append({"id": "overview", "title": "Overview", "type": "kv", "rows": ov_rows})

    # Versions
    vers = obj.get("versions", [])
    if vers:
        items = []
        for v in vers:
            ver_name = (v.get("apmsgver") or "").strip()
            type_label = _IB_MSG_TYPE.get(v.get("ib_msgtype"), f"Type {v.get('ib_msgtype')}")
            chips = [{"label": type_label, "cls": _IB_MSG_TYPE_CLS.get(v.get("ib_msgtype"), "chip-muted")}]
            if v.get("ib_parts"):
                chips.append({"label": "Multi-Part", "cls": "chip-info"})
            items.append({
                "name": ver_name,
                "chips": chips,
                "meta": None,
            })
        sections.append({
            "id": "versions",
            "title": f"Versions ({len(vers)})",
            "type": "items",
            "items": items,
        })

    # Schema records
    schema_recs = obj.get("schema_records", [])
    if schema_recs:
        items = []
        for r in schema_recs:
            rec = (r.get("recname") or "").strip()
            parent = (r.get("prntrecname") or "").strip() or None
            alias = (r.get("xmlalias") or "").strip() or None
            meta_parts = []
            if parent:
                meta_parts.append(f"parent: {parent}")
            if alias and alias != rec:
                meta_parts.append(f"alias: {alias}")
            items.append({
                "name": rec,
                "chips": [{"label": "Record", "cls": "chip-ok"}],
                "meta": " | ".join(meta_parts) if meta_parts else None,
            })
        sections.append({
            "id": "schema_records",
            "title": f"Schema Records ({len(schema_recs)})",
            "type": "items",
            "items": items,
        })

    return sections


def ib_message_payload(env, msgname):
    obj = ib_message_object(env, msgname)
    if obj is None:
        return None
    return {
        "type": "message",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {"status": obj["status_label"], "channel": obj.get("channel")},
        "sections": sections_for_ib_message(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


# ---------------------------------------------------------------------------
# App Designer Projects (PSPROJECTDEFN)
# ---------------------------------------------------------------------------

_PRJOBJ_TYPE_CLS = {
    0: "chip-ok",    # Record
    2: "chip-ok",    # Page
    4: "chip-ok",    # Component
    5: "chip-ok",    # Component Interface
    7: "chip-ok",    # Application Engine
    8: "chip-ok",    # Application Package
    44: "chip-info", # PeopleCode
    50: "chip-info", # Stylesheet
    58: "chip-muted", # Tree
    74: "chip-info", # PS Query
}


def project_object(env, projectname):
    data = psdb.get_project(env, projectname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    return {
        "type": "project",
        "name": defn.get("projectname", projectname),
        "title": (defn.get("projectdescr") or "").strip() or projectname,
        "release_label": (defn.get("releaselabel") or "").strip() or None,
        "lastupdoprid": (defn.get("lastupdoprid") or "").strip() or None,
        "lastupddttm": defn.get("lastupddttm"),
        "type_summary": data.get("type_summary", []),
        "items_by_type": data.get("items_by_type", {}),
        "counts": data.get("counts", {}),
        "_raw": data,
        "_links": {"admin": "/admin/project"},
        "warnings": data.get("warnings", []),
    }


def sections_for_project(obj):
    sections = []

    # Overview
    ov_rows = []
    if obj.get("release_label"):
        ov_rows.append({"label": "Release", "value": obj["release_label"]})
    if obj.get("lastupdoprid"):
        ov_rows.append({"label": "Last Updated By", "value": obj["lastupdoprid"]})
    if obj.get("lastupddttm"):
        ov_rows.append({"label": "Last Updated", "value": str(obj["lastupddttm"])[:19]})
    total = obj["counts"].get("total_items", 0)
    type_cnt = obj["counts"].get("types", 0)
    if total:
        ov_rows.append({"label": "Total Objects", "value": str(total)})
    if type_cnt:
        ov_rows.append({"label": "Object Types", "value": str(type_cnt)})

    if ov_rows:
        sections.append({"id": "overview", "title": "Overview", "type": "kv", "rows": ov_rows})

    # Object type summary as chips
    ts = obj.get("type_summary", [])
    if ts:
        from connectors.psdb import _PRJOBJ_TYPE_LABEL
        chips = []
        for t in ts:
            label_name = _PRJOBJ_TYPE_LABEL.get(t["objecttype"], f"Type {t['objecttype']}")
            chips.append({
                "label": f"{label_name} ({t['count']})",
                "cls": _PRJOBJ_TYPE_CLS.get(t["objecttype"], "chip-muted"),
            })
        sections.append({
            "id": "type_summary",
            "title": f"Object Types ({len(ts)})",
            "type": "chips",
            "chips": chips,
        })

    # Items grouped by type
    items_by_type = obj.get("items_by_type", {})
    from connectors.psdb import _PRJOBJ_TYPE_LABEL, _PRJOBJ_ENCODED
    for otype, type_items in sorted(items_by_type.items(), key=lambda x: -len(x[1])):
        label_name = _PRJOBJ_TYPE_LABEL.get(otype, f"Type {otype}")
        encoded = otype in _PRJOBJ_ENCODED
        row_items = []
        seen = set()
        for it in type_items:
            v1 = (it.get("objectvalue1") or "").strip()
            v2 = (it.get("objectvalue2") or "").strip()
            display_name = v1 if not encoded else f"[{v1}]"
            meta = v2 if v2 and v2 != v1 else None
            key = (v1, v2)
            if key in seen:
                continue
            seen.add(key)
            row_items.append({
                "name": display_name,
                "chips": [{"label": label_name, "cls": _PRJOBJ_TYPE_CLS.get(otype, "chip-muted")}],
                "meta": meta,
            })
        if row_items:
            sections.append({
                "id": f"objects_{otype}",
                "title": f"{label_name} ({len(row_items)})",
                "type": "items",
                "items": row_items[:100],  # cap per-type display
            })

    return sections


def project_payload(env, projectname):
    obj = project_object(env, projectname)
    if obj is None:
        return None
    return {
        "type": "project",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "release": obj.get("release_label"),
            "operator": obj.get("lastupdoprid"),
        },
        "sections": sections_for_project(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


# ---------------------------------------------------------------------------
# Translate Values (PSXLATITEM / PSXLATDEFN)
# ---------------------------------------------------------------------------

def xlat_field_object(env, fieldname):
    data = psdb.get_translate_values(env, fieldname.upper())
    if "error" in data:
        return None
    return {
        "type": "xlat_field",
        "name": data["fieldname"],
        "title": data["fieldname"],
        "values": data.get("values", []),
        "active_values": data.get("active_values", []),
        "inactive_values": data.get("inactive_values", []),
        "counts": data.get("counts", {}),
        "_raw": data,
        "_links": {"admin": "/admin/xlat"},
        "warnings": data.get("warnings", []),
    }


def sections_for_xlat_field(obj):
    sections = []

    active = obj.get("active_values", [])
    inactive = obj.get("inactive_values", [])

    if active:
        items = []
        for v in active:
            val = (v.get("fieldvalue") or "").strip()
            long_name = (v.get("xlatlongname") or "").strip()
            short_name = (v.get("xlatshortname") or "").strip()
            display = long_name if long_name and long_name != val else (short_name or val)
            items.append({
                "name": val,
                "chips": [{"label": "Active", "cls": "chip-ok"}],
                "meta": display if display != val else None,
            })
        sections.append({
            "id": "active_values",
            "title": f"Active Values ({len(active)})",
            "type": "items",
            "items": items,
        })

    if inactive:
        items = []
        for v in inactive:
            val = (v.get("fieldvalue") or "").strip()
            long_name = (v.get("xlatlongname") or "").strip()
            items.append({
                "name": val,
                "chips": [{"label": "Inactive", "cls": "chip-muted"}],
                "meta": long_name if long_name and long_name != val else None,
            })
        sections.append({
            "id": "inactive_values",
            "title": f"Inactive Values ({len(inactive)})",
            "type": "items",
            "items": items,
        })

    return sections


def xlat_field_payload(env, fieldname):
    obj = xlat_field_object(env, fieldname)
    if obj is None:
        return None
    return {
        "type": "xlat_field",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {"total": obj["counts"].get("total", 0)},
        "sections": sections_for_xlat_field(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


# ---------------------------------------------------------------------------
# File Layout Definitions (PSFLDDEFN)
# ---------------------------------------------------------------------------

_FILE_FMT_CLS = {"Fixed Width": "chip-info", "Delimited": "chip-ok", "XML": "chip-ok"}
_FILE_FMT_LABEL = {0: "Fixed Width", 1: "Delimited", 2: "XML"}
_FILE_FIELD_TYPE = {0: "Character", 1: "Number", 2: "Date", 3: "Time", 4: "DateTime", 6: "Image"}


def file_layout_object(env, flddefnname):
    data = psdb.get_file_layout(env, flddefnname.upper())
    if "error" in data:
        return None
    defn = data.get("definition", {})
    fmt_label = _FILE_FMT_LABEL.get(defn.get("fldformat"), "Unknown")
    return {
        "type": "file_layout",
        "name": defn.get("flddefnname", flddefnname),
        "title": (defn.get("descr") or "").strip() or flddefnname,
        "format": fmt_label,
        "seg_count": defn.get("fldsegcount") or 0,
        "delimiter": (defn.get("flddelimiter") or "").strip() or None,
        "qualifier": (defn.get("fldqualifier") or "").strip() or None,
        "lastupdoprid": (defn.get("lastupdoprid") or "").strip() or None,
        "lastupddttm": defn.get("lastupddttm"),
        "segments": data.get("segments", []),
        "fields": data.get("fields", []),
        "counts": data.get("counts", {}),
        "_raw": data,
        "_links": {"admin": "/admin/filelayout"},
        "warnings": data.get("warnings", []),
    }


def sections_for_file_layout(obj):
    sections = []

    # Overview
    ov_rows = []
    fmt = obj.get("format")
    if fmt:
        ov_rows.append({"label": "Format", "chips": [{"label": fmt, "cls": _FILE_FMT_CLS.get(fmt, "chip-muted")}]})
    if obj.get("seg_count"):
        ov_rows.append({"label": "Segments", "value": str(obj["seg_count"])})
    if obj.get("delimiter"):
        ov_rows.append({"label": "Delimiter", "value": obj["delimiter"]})
    if obj.get("qualifier"):
        ov_rows.append({"label": "Qualifier", "value": obj["qualifier"]})
    if obj.get("lastupdoprid"):
        ov_rows.append({"label": "Last Updated By", "value": obj["lastupdoprid"]})
    if obj.get("lastupddttm"):
        ov_rows.append({"label": "Last Updated", "value": str(obj["lastupddttm"])[:19]})

    if ov_rows:
        sections.append({"id": "overview", "title": "Overview", "type": "kv", "rows": ov_rows})

    # Segments
    segs = obj.get("segments", [])
    if segs:
        items = []
        for seg in segs:
            seg_name = (seg.get("fldsegname") or "").strip()
            seg_id = (seg.get("fldsegid") or "").strip()
            fld_cnt = seg.get("fldfieldcount") or 0
            rec = (seg.get("recname_file") or "").strip() or None
            meta_parts = []
            if seg_id:
                meta_parts.append(f"ID: {seg_id}")
            if fld_cnt:
                meta_parts.append(f"{fld_cnt} fields")
            if rec:
                meta_parts.append(f"Record: {rec}")
            items.append({
                "name": seg_name,
                "chips": [{"label": "Segment", "cls": "chip-muted"}],
                "meta": " | ".join(meta_parts) if meta_parts else None,
            })
        sections.append({
            "id": "segments",
            "title": f"Segments ({len(segs)})",
            "type": "items",
            "items": items,
        })

    # Fields (grouped by segment)
    fields = obj.get("fields", [])
    if fields:
        from collections import defaultdict
        by_seg = defaultdict(list)
        for f in fields:
            by_seg[(f.get("fldsegname") or "").strip()].append(f)

        for seg_name, seg_fields in by_seg.items():
            field_items = []
            for f in seg_fields:
                fname = (f.get("fldfieldname") or "").strip()
                ftype_code = f.get("fldfieldtype", 0)
                ftype_label = _FILE_FIELD_TYPE.get(ftype_code, f"Type {ftype_code}")
                flen = f.get("fldlength") or 0
                fstart = f.get("fldstart") or 0
                chips = [{"label": ftype_label, "cls": "chip-muted"}]
                meta_parts = []
                if fstart:
                    meta_parts.append(f"pos {fstart}")
                if flen:
                    meta_parts.append(f"len {flen}")
                field_items.append({
                    "name": fname,
                    "chips": chips,
                    "meta": " | ".join(meta_parts) if meta_parts else None,
                })
            sections.append({
                "id": f"fields_{seg_name}",
                "title": f"Fields — {seg_name} ({len(seg_fields)})",
                "type": "items",
                "items": field_items,
            })

    return sections


def file_layout_payload(env, flddefnname):
    obj = file_layout_object(env, flddefnname)
    if obj is None:
        return None
    return {
        "type": "file_layout",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {"format": obj.get("format")},
        "sections": sections_for_file_layout(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


# ---------------------------------------------------------------------------
# Process Definitions (PS_PRCSDEFN)
# ---------------------------------------------------------------------------

_PRCS_RUNLOC_LABEL = {"0": "Server", "1": "Client", "2": "Server"}
_PRCS_TYPE_CLS = {
    "Application Engine": "chip-ok",
    "SQR Report": "chip-info",
    "XML Publisher": "chip-info",
    "COBOL SQL": "chip-muted",
    "SQR Process": "chip-muted",
    "SQR Report For WF Delivery": "chip-muted",
    "Data Mover": "chip-muted",
}


def _prcs_type_chip(prcstype):
    return {"label": prcstype, "cls": _PRCS_TYPE_CLS.get(prcstype, "chip-muted")}


def process_defn_object(env, compound_key):
    data = psdb.get_process_definition(env, compound_key)
    if "error" in data:
        return None
    defn = data.get("definition", {})
    prcstype = defn.get("prcstype", "")
    prcsname = defn.get("prcsname", compound_key)
    return {
        "type": "prcs_defn",
        "name": compound_key,
        "prcsname": prcsname,
        "prcstype": prcstype,
        "title": defn.get("descr") or prcsname,
        "category": (defn.get("prcscategory") or "").strip() or None,
        "restart_enabled": defn.get("restartenabled") == "1",
        "retry_count": defn.get("retrycount") or 0,
        "timeout_minutes": defn.get("timeoutminutes") or 0,
        "max_concurrent": defn.get("maxconcurrent") or 0,
        "run_location": _PRCS_RUNLOC_LABEL.get(str(defn.get("runlocation") or "0"), "Server"),
        "server_name": (defn.get("servername") or "").strip() or None,
        "msg_log_tbl": (defn.get("msglogtbl") or "").strip() or None,
        "rqst_tbl": (defn.get("rqsttbl") or "").strip() or None,
        "recur_name": (defn.get("recurname") or "").strip() or None,
        "parm_list": (defn.get("parmlist") or "").strip() or None,
        "lastupddttm": defn.get("lastupddttm"),
        "lastupdoprid": (defn.get("lastupdoprid") or "").strip() or None,
        "run_cntl_pages": data.get("run_cntl_pages", []),
        "prcs_groups": data.get("prcs_groups", []),
        "counts": data.get("counts", {}),
        "_raw": data,
        "_links": {"admin": f"/admin/prcsdefn"},
        "warnings": data.get("warnings", []),
    }


def sections_for_process_defn(obj):
    sections = []

    # Overview
    overview_rows = []
    if obj.get("prcstype"):
        overview_rows.append({"label": "Type", "chips": [_prcs_type_chip(obj["prcstype"])]})
    if obj.get("category"):
        overview_rows.append({"label": "Category", "value": obj["category"]})
    if obj.get("run_location"):
        overview_rows.append({"label": "Run Location", "value": obj["run_location"]})
    if obj.get("server_name"):
        overview_rows.append({"label": "Server", "value": obj["server_name"]})
    if obj.get("restart_enabled"):
        overview_rows.append({"label": "Restart Enabled", "chips": [{"label": "Yes", "cls": "chip-ok"}]})
    if obj.get("retry_count"):
        overview_rows.append({"label": "Retry Count", "value": str(obj["retry_count"])})
    if obj.get("timeout_minutes"):
        overview_rows.append({"label": "Timeout (min)", "value": str(obj["timeout_minutes"])})
    if obj.get("max_concurrent"):
        overview_rows.append({"label": "Max Concurrent", "value": str(obj["max_concurrent"])})
    if obj.get("recur_name"):
        overview_rows.append({"label": "Schedule", "value": obj["recur_name"]})
    if obj.get("rqst_tbl"):
        overview_rows.append({"label": "Run Control Table", "value": obj["rqst_tbl"]})
    if obj.get("msg_log_tbl"):
        overview_rows.append({"label": "Log Table", "value": obj["msg_log_tbl"]})
    if obj.get("parm_list"):
        overview_rows.append({"label": "Parameters", "value": obj["parm_list"]})
    if obj.get("lastupdoprid"):
        overview_rows.append({"label": "Last Updated By", "value": obj["lastupdoprid"]})
    if obj.get("lastupddttm"):
        overview_rows.append({"label": "Last Updated", "value": str(obj["lastupddttm"])[:19]})

    if overview_rows:
        sections.append({
            "id": "overview",
            "title": "Overview",
            "type": "kv",
            "rows": overview_rows,
        })

    # Run Control Pages
    pages = obj.get("run_cntl_pages", [])
    if pages:
        sections.append({
            "id": "run_cntl_pages",
            "title": f"Run Control Pages ({len(pages)})",
            "type": "chips",
            "chips": [{"label": p, "cls": "chip-info"} for p in pages],
        })

    # Process Groups
    groups = obj.get("prcs_groups", [])
    if groups:
        sections.append({
            "id": "prcs_groups",
            "title": f"Process Groups ({len(groups)})",
            "type": "chips",
            "chips": [{"label": g, "cls": "chip-muted"} for g in groups],
        })

    return sections


def process_defn_payload(env, compound_key):
    obj = process_defn_object(env, compound_key)
    if obj is None:
        return None
    return {
        "type": "prcs_defn",
        "name": obj["name"],
        "title": obj["title"],
        "overview": {
            "prcstype": obj.get("prcstype"),
            "category": obj.get("category"),
        },
        "sections": sections_for_process_defn(obj),
        "warnings": obj.get("warnings", []),
        "_links": obj["_links"],
        "_uom": obj,
    }


def canonical_object(env, object_type, name):
    object_type = object_type.lower()
    if object_type == "component_interface":
        object_type = "ci"
    if object_type == "permission_list":
        object_type = "permissionlist"
    if object_type in {"portal", "content_reference"}:
        object_type = "portal_registry"

    if object_type == "field":
        return field_object(env, name)
    if object_type == "peoplecode":
        return peoplecode_object(env, name)
    if object_type == "application_engine":
        return ae_object(env, name)
    if object_type == "record":
        return record_object(env, name)
    if object_type == "operator":
        return operator_object(env, name)
    if object_type == "role":
        return role_object(env, name)
    if object_type == "permissionlist":
        return permissionlist_object(env, name)
    if object_type == "component":
        return component_object(env, name)
    if object_type == "page":
        return page_object(env, name)
    if object_type == "portal_registry":
        return portal_registry_object(env, name)
    if object_type == "service_operation":
        return service_object(env, name)
    if object_type == "node":
        return node_object(env, name)
    if object_type == "queue":
        return queue_object(env, name)
    if object_type == "routing":
        return routing_object(env, name)
    if object_type == "sql_definition":
        return sql_object(env, name)
    if object_type == "query":
        return query_object(env, name)
    if object_type == "tree":
        return tree_object(env, name)
    if object_type == "ci":
        return ci_object(env, name)
    if object_type == "application_package":
        return app_package_object(env, name)
    if object_type == "menu":
        return menu_object(env, name)
    if object_type == "message_catalog":
        return message_catalog_object(env, name)
    if object_type == "approval":
        return approval_object(env, name)
    if object_type == "xml_publisher_report":
        return xpub_report_object(env, name)
    if object_type == "nav_collection":
        return nav_collection_object(env, name)
    if object_type == "event_mapping":
        return event_mapping_object(env, name)
    if object_type == "related_content":
        return related_content_object(env, name)
    if object_type == "search_definition":
        return search_definition_object(env, name)
    if object_type == "search_category":
        return search_category_object(env, name)
    if object_type == "drop_zone":
        return drop_zone_object(env, name)
    if object_type == "pivot_grid":
        return pivot_grid_object(env, name)
    if object_type == "connected_query":
        return connected_query_object(env, name)
    if object_type == "prcs_defn":
        return process_defn_object(env, name)
    if object_type == "file_layout":
        return file_layout_object(env, name)
    if object_type == "xlat_field":
        return xlat_field_object(env, name)
    if object_type == "project":
        return project_object(env, name)
    if object_type == "message":
        return ib_message_object(env, name)

    resolved = ptmetadata.resolve_object(env, object_type, name)
    warnings = resolved.get("warnings", [])
    return canonical_base(
        env,
        object_type,
        name,
        display_name=resolved.get("name", name.upper()),
        status="resolved" if resolved.get("resolved") else "partial",
        warnings=warnings,
        _metadata={"environment": env.upper(), "resolver": resolved},
    )
