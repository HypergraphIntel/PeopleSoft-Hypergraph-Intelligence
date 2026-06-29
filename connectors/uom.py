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
    return {
        "type": ae_obj["type"],
        "name": ae_obj["name"],
        "title": ae_obj["display_name"],
        "overview": {
            "id": ae_obj["id"],
            "display_name": ae_obj["display_name"],
            "description": ae_obj["description"],
            "status": ae_obj["status"],
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
    ldap_on = str(raw.get("ldap_rule_on") or "").strip().upper()
    roletype = str(raw.get("roletype") or "").strip().upper()
    if roletype in ("Q", "P") or qryname or pc_func or ldap_on == "Y":
        dynamic_items = []
        rule_type = raw.get("roletype_label") or roletype
        if qryname:
            dynamic_items.append({
                "type": "query", "name": qryname,
                "label": f"Membership Query: {qryname}",
                "_links": {"admin": object_url("query", qryname)},
            })
        if pc_func:
            dynamic_items.append({
                "label": f"PeopleCode Function: {pc_func}",
                "name": pc_func,
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
    warnings.extend(r_warn)
    warnings.extend(m_warn)
    warnings.extend(c_warn)

    relationships = {
        "roles": [attach_object_links(r, env) for r in (roles or [])],
        "menus": [attach_object_links(m, env) for m in (menus or [])],
        "components": [attach_object_links(c, env) for c in (components or [])],
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


def sections_for_permissionlist(pl):
    rels = pl.get("_relationships", {})
    meta = pl.get("_metadata", {})
    raw = meta.get("raw", {})
    roles = rels.get("roles", [])
    menus = rels.get("menus", [])
    components = rels.get("components", [])
    graph_nodes = pl.get("_graph", {}).get("nodes", [])
    graph_edges = pl.get("_graph", {}).get("edges", [])
    return [
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
        {"name": "Roles", "items": roles,
         "data": {"count": len(roles), "note": "" if roles else "PSROLECLASS not accessible or no roles assigned"}},
        {"name": "Menus", "items": menus,
         "data": {"count": len(menus), "note": "" if menus else "PSAUTHITEM not accessible or no menus granted"}},
        {"name": "Components", "items": components,
         "data": {"count": len(components), "note": "" if components else "PSAUTHITEM/PSPNLGRPDEFN not accessible or no components granted"}},
        {"name": "Graph Preview", "items": graph_nodes,
         "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": pl.get("warnings", []),
         "data": {"count": len(pl.get("warnings", []))}},
    ]


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
    page_records, record_warn = safe_relationship("component_records_used_by_pages", lambda: psdb.component_records_used_by_pages(env, component_name))
    portal_refs, portal_warn = safe_relationship("component_portal_refs", lambda: psdb.component_portal_refs(env, component_name))
    related_content, rc_warn = safe_relationship("component_related_content", lambda: psdb.component_related_content(env, component_name))
    event_mapping, event_warn = safe_relationship("component_event_mapping", lambda: psdb.component_event_mapping(env, component_name))
    drop_zones, dz_warn = safe_relationship("component_drop_zones", lambda: psdb.component_drop_zones(env, component_name))
    access_result, access_warn = safe_relationship("component_access", lambda: psdb.component_access(env, component_name))
    warnings.extend(page_warn + pl_warn + menu_warn + record_warn + portal_warn + rc_warn + event_warn + dz_warn + access_warn)

    search_records = []
    for key in ("searchrecname", "addsearchrecname"):
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
        "search_records": [attach_object_links(row, env) for row in search_records],
        "page_records": [attach_object_links(row, env) for row in (page_records or [])],
        "menu_placements": [attach_object_links(row, env) for row in (menu_placements or [])],
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
    return [
        {"name": "Definition", "items": [], "data": {
            "pnlgrpname": component["name"],
            "description": component.get("description") or "",
            "market": raw.get("market") or "",
            "searchrecname": raw.get("searchrecname") or "",
            "addsearchrecname": raw.get("addsearchrecname") or "",
            "version": raw.get("version"),
            "lastupddttm": raw.get("lastupddttm") or "",
            "lastupdoprid": raw.get("lastupdoprid") or "",
            **counts,
        }},
        {"name": "Pages", "items": rels.get("pages", []), "data": {"count": len(rels.get("pages", []))}},
        {"name": "Search Records", "items": rels.get("search_records", []), "data": {"count": len(rels.get("search_records", []))}},
        {"name": "Records Used By Pages", "items": rels.get("page_records", []), "data": {"count": len(rels.get("page_records", []))}},
        {"name": "Menu Placement", "items": rels.get("menu_placements", []), "data": {"count": len(rels.get("menu_placements", []))}},
        {"name": "Portal Registry", "items": rels.get("portal_refs", []), "data": {"count": len(rels.get("portal_refs", []))}},
        {"name": "Permission Lists", "items": rels.get("permissionlists", []), "data": {"count": len(rels.get("permissionlists", []))}},
        {"name": "Security", "items": rels.get("security", []), "data": {
            "access_paths": len(rels.get("security", [])),
            "operators": counts.get("operators", 0),
            "roles": counts.get("roles", 0),
            "permissionlists": counts.get("permissionlists", 0),
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

    nodes = {}
    edges = []
    add_node(nodes, graph_node("page", page_name, raw))
    for component_row in (components or [])[:20]:
        component_name = str(component_row.get("pnlgrpname") or "").strip()
        if component_name:
            add_node(nodes, graph_node("component", component_name, component_row))
            edges.append(graph_edge("component", component_name, "page", page_name, "contains_page"))
    for record in (records or [])[:30]:
        recname = str(record.get("recname") or "").strip()
        if recname:
            add_node(nodes, graph_node("record", recname, record))
            edges.append(graph_edge("page", page_name, "record", recname, "uses_record"))
    for field in (fields or [])[:40]:
        recname = str(field.get("recname") or "").strip()
        fieldname = str(field.get("fieldname") or "").strip()
        if recname and fieldname:
            full_field = f"{recname}.{fieldname}"
            add_node(nodes, graph_node("field", full_field, field))
            edges.append(graph_edge("page", page_name, "field", full_field, "contains_field"))
    for subpage in (subpages or [])[:20]:
        subpage_name = str(subpage.get("pnlname") or "").strip()
        if subpage_name:
            add_node(nodes, graph_node("page", subpage_name, subpage))
            edges.append(graph_edge("page", page_name, "page", subpage_name, "contains_subpage"))
    for classid in sorted(permissionlists)[:40]:
        add_node(nodes, graph_node("permissionlist", classid, {"classid": classid}))
        edges.append(graph_edge("permissionlist", classid, "page", page_name, "secures_page"))

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
        _graph={"nodes": list(nodes.values()), "edges": edges},
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
        {"name": "Security", "items": rels.get("security", []), "data": {
            "components": counts.get("components", 0),
            "permissionlists": counts.get("permissionlists", 0),
            "roles": counts.get("roles", 0),
            "operators": counts.get("operators", 0),
            "access_paths": counts.get("access_paths", 0),
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


def sections_for_portal_registry(portal_obj):
    rels = portal_obj.get("_relationships", {})
    meta = portal_obj.get("_metadata", {})
    raw = meta.get("raw", {})
    counts = meta.get("counts", {})
    graph_nodes = portal_obj.get("_graph", {}).get("nodes", [])
    graph_edges = portal_obj.get("_graph", {}).get("edges", [])
    return [
        {"name": "Definition", "items": [], "data": {
            "portal_name": raw.get("portal_name") or "",
            "portal_objname": portal_obj["name"],
            "portal_label": raw.get("portal_label") or "",
            "description": raw.get("descr254") or portal_obj.get("description") or "",
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
        {"name": "Breadcrumbs", "items": rels.get("breadcrumbs", []), "data": {"count": len(rels.get("breadcrumbs", []))}},
        {"name": "Children", "items": rels.get("children", []), "data": {"count": len(rels.get("children", []))}},
        {"name": "Target Components", "items": rels.get("component_targets", []), "data": {"count": len(rels.get("component_targets", []))}},
        {"name": "Attributes", "items": rels.get("attributes", []), "data": {"count": len(rels.get("attributes", []))}},
        {"name": "Portal Security", "items": rels.get("permissions", []), "data": {
            "count": len(rels.get("permissions", [])),
            "permissionlists": counts.get("permissionlists", 0),
            "roles": counts.get("roles", 0),
            "inherited": sum(1 for row in rels.get("permissions", []) if row.get("inherited")),
        }},
        {"name": "Access Paths", "items": rels.get("access_paths", []), "data": {
            "count": len(rels.get("access_paths", [])),
            "operators": counts.get("operators", 0),
            "roles": counts.get("roles", 0),
        }},
        {"name": "Graph Preview", "items": graph_nodes, "data": {"node_count": len(graph_nodes), "edge_count": len(graph_edges)}},
        {"name": "Warnings", "items": portal_obj.get("warnings", []), "data": {"count": len(portal_obj.get("warnings", []))}},
    ]


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
    return [
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
        {"name": "AE References", "items": xref_ae, "data": {
            "count": len(xref_ae),
            "note": "AE SQL steps using %SQL(" + s_obj["name"] + ") meta-SQL substitution" if xref_ae else "",
        }},
        {"name": "Warnings", "items": s_obj.get("warnings", []),
         "data": {"count": len(s_obj.get("warnings", []))}},
    ]


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


def canonical_object(env, object_type, name):
    object_type = object_type.lower()
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
