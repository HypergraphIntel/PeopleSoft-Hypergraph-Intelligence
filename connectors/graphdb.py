import json
import time
from collections import defaultdict, deque
from pathlib import Path

from connectors import ae, ib, peoplecode, psdb, ptmetadata, uom

DATA_DIR = Path("/opt/deathstar-api/data")
SNAPSHOT_DIR = DATA_DIR / "graph_snapshots"
SNAPSHOT_MANIFEST = SNAPSHOT_DIR / "manifest.json"
GRAPHS = {}
BUILD_STATE = {}

EDGE_TYPES = {
    "USES",
    "CONTAINS",
    "BELONGS_TO",
    "CALLS",
    "CALLED_BY",
    "REFERENCES",
    "REFERENCED_BY",
    "SECURES",
    "EXPOSES",
    "OWNS",
    "DEPENDS_ON",
    "GENERATES",
    "READS",
    "WRITES",
}

EDGE_TYPES.add("ROUTES")
EDGE_TYPES.add("WRAPS")

DEPENDENCY_EDGES = {"USES", "CONTAINS", "REFERENCES", "DEPENDS_ON", "CALLS", "READS", "WRITES", "SECURES", "EXPOSES", "ROUTES", "WRAPS"}


def empty_graph(env="HCM"):
    return {
        "environment": env.upper(),
        "nodes": {},
        "edges": [],
        "_edge_ids": set(),  # not persisted; rebuilt on load
        "warnings": [],
        "built_at": None,
        "build_seconds": 0,
        "providers": [],
    }


def graph_path(env):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"knowledge_graph_{env.upper()}.json"


def snapshot_dir():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR


def _safe_snapshot_name(name):
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in (name or "").strip())
    safe = safe.strip("._")
    if not safe:
        safe = time.strftime("snapshot_%Y%m%dT%H%M%SZ", time.gmtime())
    return safe[:80]


def _manifest():
    snapshot_dir()
    if SNAPSHOT_MANIFEST.exists():
        return json.loads(SNAPSHOT_MANIFEST.read_text())
    return {"snapshots": []}


def _write_manifest(data):
    snapshot_dir()
    SNAPSHOT_MANIFEST.write_text(json.dumps(data, indent=2, default=str))
    return data


def current(env="HCM"):
    env = env.upper()
    if env not in GRAPHS:
        path = graph_path(env)
        if path.exists():
            g = json.loads(path.read_text())
            g["_edge_ids"] = {e["id"] for e in g.get("edges", [])}
            GRAPHS[env] = g
        else:
            GRAPHS[env] = empty_graph(env)
    return GRAPHS[env]


def save(env="HCM"):
    graph = current(env)
    saveable = {k: v for k, v in graph.items() if k != "_edge_ids"}
    graph_path(env).write_text(json.dumps(saveable, indent=2, default=str))
    return graph


def create_snapshot(env="HCM", name="", note="", include_graph=True):
    env = env.upper()
    graph = current(env)
    safe_name = _safe_snapshot_name(name)
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    filename = f"{env}_{created_at.replace(':', '').replace('-', '')}_{safe_name}.json"
    path = snapshot_dir() / filename

    payload = graph if include_graph else {
        "environment": env,
        "nodes": graph.get("nodes", {}),
        "edges": graph.get("edges", []),
        "warnings": graph.get("warnings", []),
        "built_at": graph.get("built_at"),
        "build_seconds": graph.get("build_seconds", 0),
        "providers": graph.get("providers", []),
    }
    path.write_text(json.dumps(payload, indent=2, default=str))

    entry = {
        "id": path.stem,
        "env": env,
        "name": safe_name,
        "note": note or "",
        "created_at": created_at,
        "built_at": graph.get("built_at"),
        "node_count": len(graph.get("nodes", {})),
        "edge_count": len(graph.get("edges", [])),
        "warning_count": len(graph.get("warnings", [])),
        "path": str(path),
    }

    manifest = _manifest()
    manifest["snapshots"] = [
        item for item in manifest.get("snapshots", [])
        if item.get("id") != entry["id"]
    ] + [entry]
    manifest["snapshots"] = sorted(manifest["snapshots"], key=lambda item: item.get("created_at", ""), reverse=True)
    _write_manifest(manifest)
    return entry


def list_snapshots(env=None):
    env_filter = env.upper() if env else None
    snapshots = _manifest().get("snapshots", [])
    if env_filter:
        snapshots = [item for item in snapshots if item.get("env") == env_filter]
    return {"snapshots": snapshots, "count": len(snapshots), "path": str(SNAPSHOT_MANIFEST)}


def _snapshot_entry(snapshot_id):
    for entry in _manifest().get("snapshots", []):
        if entry.get("id") == snapshot_id:
            return entry
    return None


def load_snapshot(snapshot_id):
    entry = _snapshot_entry(snapshot_id)
    if not entry:
        raise FileNotFoundError(f"Graph snapshot not found: {snapshot_id}")
    path = Path(entry["path"])
    if not path.exists():
        raise FileNotFoundError(f"Graph snapshot file missing: {path}")
    graph = json.loads(path.read_text())
    return {"snapshot": entry, "graph": graph}


def delete_snapshot(snapshot_id):
    entry = _snapshot_entry(snapshot_id)
    if not entry:
        raise FileNotFoundError(f"Graph snapshot not found: {snapshot_id}")
    path = Path(entry["path"])
    if path.exists():
        path.unlink()
    manifest = _manifest()
    manifest["snapshots"] = [
        item for item in manifest.get("snapshots", [])
        if item.get("id") != snapshot_id
    ]
    _write_manifest(manifest)
    return {"deleted": snapshot_id, "path": str(path)}


def prune_snapshots(env=None, keep=7):
    """Delete oldest snapshots per environment, retaining at most `keep` per env."""
    manifest = _manifest()
    all_snaps = manifest.get("snapshots", [])
    envs = [env.upper()] if env else sorted({s.get("env") for s in all_snaps if s.get("env")})
    deleted_ids = set()
    for e in envs:
        env_snaps = sorted(
            [s for s in all_snaps if s.get("env") == e],
            key=lambda s: s.get("created_at", ""),
            reverse=True,
        )
        for old in env_snaps[keep:]:
            p = Path(old.get("path", ""))
            if p.exists():
                p.unlink()
            deleted_ids.add(old.get("id"))
    manifest["snapshots"] = [s for s in all_snaps if s.get("id") not in deleted_ids]
    _write_manifest(manifest)
    return {"deleted": sorted(deleted_ids), "count": len(deleted_ids)}


def clear(env="HCM"):
    env = env.upper()
    GRAPHS[env] = empty_graph(env)
    path = graph_path(env)
    if path.exists():
        path.unlink()
    return stats(env)


def compact(env="HCM"):
    """Remove duplicate edges and rebuild the O(1) edge index.

    Duplicate edges can accumulate if a graph file was written before the
    _edge_ids set was introduced. This function deduplicates in-place and
    persists the cleaned graph.
    """
    env = env.upper()
    graph = current(env)
    edges = graph["edges"]
    original_count = len(edges)
    original_nodes = len(graph["nodes"])

    # Deduplicate edges preserving order
    seen: dict[str, dict] = {}
    for edge in edges:
        eid = edge.get("id", "")
        if eid and eid not in seen:
            seen[eid] = edge
    graph["edges"] = list(seen.values())
    graph["_edge_ids"] = set(seen.keys())

    edges_removed = original_count - len(graph["edges"])
    save(env)

    return {
        "environment": env,
        "node_count": original_nodes,
        "original_edges": original_count,
        "edges_after": len(graph["edges"]),
        "edges_removed": edges_removed,
        "status": "compacted" if edges_removed > 0 else "already_clean",
    }


def node_id(node_type, name):
    return uom.object_id(node_type, name)


def node_url(node_type, name):
    return uom.object_url(node_type, name)


def icon_for(node_type):
    return ptmetadata.OBJECT_REGISTRY.get(node_type, {}).get("icon", "circle")


def add_node(graph, node_type, name, display_name=None, metadata=None, warnings=None):
    if not name:
        return None

    node_type = node_type.lower()
    name = str(name).upper()
    node = {
        "id": node_id(node_type, name),
        "type": node_type,
        "name": name,
        "display_name": display_name or name,
        "metadata": metadata or {},
        "canonical_url": node_url(node_type, name),
        "icon": icon_for(node_type),
        "warnings": warnings or [],
    }

    existing = graph["nodes"].get(node["id"])
    if existing:
        existing["metadata"].update(node["metadata"])
        existing["warnings"].extend(item for item in node["warnings"] if item not in existing["warnings"])
        return existing

    graph["nodes"][node["id"]] = node
    return node


def add_edge(graph, source_type, source_name, target_type, target_name, edge_type, metadata=None):
    source = add_node(graph, source_type, source_name)
    target = add_node(graph, target_type, target_name)

    if not source or not target:
        return None

    edge_type = edge_type.upper()
    edge = {
        "id": f"{source['id']}->{edge_type}->{target['id']}",
        "source": source["id"],
        "target": target["id"],
        "type": edge_type,
        "metadata": metadata or {},
    }

    edge_ids = graph.setdefault("_edge_ids", set())
    if edge["id"] not in edge_ids:
        edge_ids.add(edge["id"])
        graph["edges"].append(edge)

    return edge


def add_warning(graph, provider, exc):
    graph["warnings"].append(ptmetadata.warning(
        "graph_provider_unavailable",
        f"{provider} provider unavailable: {exc}",
        detail={"provider": provider},
    ))


def provider(graph, name, loader):
    start = time.time()
    try:
        count = loader()
        graph["providers"].append({
            "name": name,
            "status": "ok",
            "items": count or 0,
            "seconds": round(time.time() - start, 3),
        })
    except Exception as exc:
        add_warning(graph, name, exc)
        graph["providers"].append({
            "name": name,
            "status": "warning",
            "items": 0,
            "seconds": round(time.time() - start, 3),
            "warning": str(exc),
        })


def build(env="HCM", limit=50, persist=True):
    env = env.upper()
    # Limits above 250 trigger batch-query mode (single IN-clause queries instead of N+1).
    # Standard mode: limit≤250, N+1 queries. Full mode: limit≤2000, batch queries.
    limit = max(1, min(int(limit), 2000))
    batch_mode = limit > 250
    graph = empty_graph(env)
    start = time.time()
    BUILD_STATE[env] = {"status": "building", "started_at": start}

    def operators():
        rows = psdb.search_oprids(env, "", limit)
        if batch_mode:
            oprids = [row.get("oprid") for row in rows if row.get("oprid")]
            roles_map = psdb.batch_operator_roles(env, oprids)
            for row in rows:
                oprid = row.get("oprid")
                add_node(graph, "operator", oprid, oprid, row)
                for role in roles_map.get(oprid, []):
                    add_node(graph, "role", role.get("rolename"), role.get("rolename"), role)
                    add_edge(graph, "operator", oprid, "role", role.get("rolename"), "OWNS", role)
        else:
            for row in rows:
                add_node(graph, "operator", row.get("oprid"), row.get("oprid"), row)
                for role in psdb.oprid_roles(row.get("oprid"), env, columns="summary"):
                    add_node(graph, "role", role.get("rolename"), role.get("rolename"), role)
                    add_edge(graph, "operator", row.get("oprid"), "role", role.get("rolename"), "OWNS", role)
        return len(rows)

    def roles():
        rows = psdb.roles(env, "", limit)
        if batch_mode:
            rolenames = [row.get("rolename") for row in rows if row.get("rolename")]
            pl_map = psdb.batch_role_permissionlists(env, rolenames)
            for row in rows:
                rolename = row.get("rolename")
                add_node(graph, "role", rolename, rolename, row)
                for pl in pl_map.get((rolename or "").upper(), []):
                    add_node(graph, "permissionlist", pl.get("classid"), pl.get("classid"), pl)
                    add_edge(graph, "role", rolename, "permissionlist", pl.get("classid"), "CONTAINS", pl)
        else:
            for row in rows:
                add_node(graph, "role", row.get("rolename"), row.get("rolename"), row)
                for permissionlist in psdb.role_permissionlists(env, row.get("rolename"))[:limit]:
                    add_node(graph, "permissionlist", permissionlist.get("classid"), permissionlist.get("classid"), permissionlist)
                    add_edge(graph, "role", row.get("rolename"), "permissionlist", permissionlist.get("classid"), "CONTAINS", permissionlist)
        return len(rows)

    def permissionlists():
        rows = psdb.permissionlists(env, "", limit)
        if batch_mode:
            classids = [row.get("classid") for row in rows if row.get("classid")]
            comp_map = psdb.batch_permissionlist_components(env, classids)
            for row in rows:
                classid = row.get("classid")
                add_node(graph, "permissionlist", classid, classid, row)
                for component in comp_map.get((classid or "").upper(), []):
                    add_node(graph, "component", component.get("pnlgrpname"), component.get("pnlgrpname"), component)
                    add_edge(graph, "permissionlist", classid, "component", component.get("pnlgrpname"), "SECURES", component)
                    if component.get("menuname"):
                        add_node(graph, "menu", component.get("menuname"), component.get("menuname"), component)
                        add_edge(graph, "menu", component.get("menuname"), "component", component.get("pnlgrpname"), "CONTAINS", component)
        else:
            for row in rows:
                add_node(graph, "permissionlist", row.get("classid"), row.get("classid"), row)
                for component in psdb.permissionlist_components(env, row.get("classid"))[:limit]:
                    add_node(graph, "component", component.get("pnlgrpname"), component.get("pnlgrpname"), component)
                    add_edge(graph, "permissionlist", row.get("classid"), "component", component.get("pnlgrpname"), "SECURES", component)
                    if component.get("menuname"):
                        add_node(graph, "menu", component.get("menuname"), component.get("menuname"), component)
                        add_edge(graph, "menu", component.get("menuname"), "component", component.get("pnlgrpname"), "CONTAINS", component)
        return len(rows)

    def components():
        rows = psdb.components(env, "", limit)
        if batch_mode:
            component_names = [row.get("pnlgrpname") for row in rows if row.get("pnlgrpname")]
            pages_map = psdb.batch_component_pages(env, component_names)
            for row in rows:
                component = row.get("pnlgrpname")
                add_node(graph, "component", component, component, row)
                for key, rel in (("searchrecname", "USES"), ("addsrchrecname", "USES")):
                    if row.get(key):
                        add_node(graph, "record", row.get(key), row.get(key), {"source": key})
                        add_edge(graph, "component", component, "record", row.get(key), rel, {"source": key})
                for page in pages_map.get((component or "").upper(), []):
                    add_node(graph, "page", page.get("pnlname"), page.get("pnlname"), page)
                    add_edge(graph, "component", component, "page", page.get("pnlname"), "CONTAINS", page)
        else:
            for row in rows:
                component = row.get("pnlgrpname")
                add_node(graph, "component", component, component, row)
                for key, rel in (("searchrecname", "USES"), ("addsrchrecname", "USES")):
                    if row.get(key):
                        add_node(graph, "record", row.get(key), row.get(key), {"source": key})
                        add_edge(graph, "component", component, "record", row.get(key), rel, {"source": key})
                for page in psdb.component_pages(env, component)[:limit]:
                    add_node(graph, "page", page.get("pnlname"), page.get("pnlname"), page)
                    add_edge(graph, "component", component, "page", page.get("pnlname"), "CONTAINS", page)
        return len(rows)

    def pages():
        rows = psdb.pages(env, "", limit)
        for row in rows:
            page = row.get("pnlname")
            add_node(graph, "page", page, page, row)
            for field in psdb.page_fields(env, page)[:limit]:
                record = field.get("recname")
                fieldname = field.get("fieldname")
                if record:
                    add_node(graph, "record", record, record, field)
                    add_edge(graph, "page", page, "record", record, "USES", field)
                if record and fieldname:
                    full_field = f"{record}.{fieldname}"
                    add_node(graph, "field", full_field, full_field, field)
                    add_edge(graph, "page", page, "field", full_field, "EXPOSES", field)
                    add_edge(graph, "record", record, "field", full_field, "CONTAINS", field)
        return len(rows)

    def fields():
        rows = psdb.fields(env, "", limit)
        for row in rows:
            record = row.get("recname")
            field = row.get("fieldname")
            if record and field:
                full_field = f"{record}.{field}"
                add_node(graph, "record", record, record, row)
                add_node(graph, "field", full_field, full_field, row)
                add_edge(graph, "record", record, "field", full_field, "CONTAINS", row)
        return len(rows)

    def peoplecode_programs():
        rows = peoplecode.programs(env, "", limit)
        for row in rows["items"]:
            reference = row.get("reference")
            if not reference:
                continue

            add_node(graph, "peoplecode", row.get("encoded_reference") or peoplecode.encode_reference(reference), reference, row, rows.get("warnings", []))

            if row.get("parent_type") and row.get("parent_name"):
                add_node(graph, row["parent_type"], row["parent_name"], row["parent_name"], {})
                add_edge(
                    graph,
                    "peoplecode",
                    row.get("encoded_reference") or peoplecode.encode_reference(reference),
                    row["parent_type"],
                    row["parent_name"],
                    "BELONGS_TO",
                    row,
                )

            refs = peoplecode.references(reference, env)
            for record in refs["references"].get("records", []):
                add_node(graph, "record", record, record, {})
                add_edge(graph, "peoplecode", row.get("encoded_reference") or peoplecode.encode_reference(reference), "record", record, "REFERENCES")
            for field in refs["references"].get("fields", []):
                add_node(graph, "field", field, field, {})
                add_edge(graph, "peoplecode", row.get("encoded_reference") or peoplecode.encode_reference(reference), "field", field, "REFERENCES")
            for sql_name in refs["references"].get("sql_definitions", []):
                add_node(graph, "sql_definition", sql_name, sql_name, {})
                add_edge(graph, "peoplecode", row.get("encoded_reference") or peoplecode.encode_reference(reference), "sql_definition", sql_name, "USES")
            for call in refs.get("calls", []):
                add_node(graph, "function", call.get("name"), call.get("name"), call)
                add_edge(graph, "peoplecode", row.get("encoded_reference") or peoplecode.encode_reference(reference), "function", call.get("name"), "CALLS", call)

        if rows["warnings"]:
            for item in rows["warnings"]:
                graph["warnings"].append(item)

        return len(rows["items"])

    def application_engines():
        result = ae.programs(env, "", limit)
        for row in result["items"]:
            applid = row.get("ae_applid")
            if not applid:
                continue

            add_node(graph, "application_engine", applid, applid, row)

            sect_result = ae.sections(env, applid)
            for sect in sect_result["items"]:
                sect_name = sect.get("ae_section")
                if sect_name:
                    sect_node_name = f"{applid}.{sect_name}"
                    add_node(graph, "ae_section", sect_node_name, sect_name, sect)
                    add_edge(graph, "application_engine", applid, "ae_section", sect_node_name, "CONTAINS", sect)

            state_result = ae.state_records(env, applid)
            for state in state_result["items"]:
                recname = state.get("recname")
                if recname:
                    add_node(graph, "record", recname, recname, state)
                    add_edge(graph, "application_engine", applid, "record", recname, "USES", state)

            proc_result = ae.process_definitions(env, applid)
            for proc in proc_result["items"]:
                prcsname = proc.get("prcsname")
                if prcsname:
                    add_node(graph, "process", prcsname, prcsname, proc)
                    add_edge(graph, "application_engine", applid, "process", prcsname, "GENERATES", proc)

        if result.get("warnings"):
            for w in result["warnings"]:
                if w:
                    graph["warnings"].append(w)

        return len(result["items"])

    def integration_broker():
        seen_ops = set()

        # Nodes from PSMSGNODEDEFN
        node_result = ib.nodes(env, "", min(limit, 200))
        for row in node_result.get("items", []):
            nodename = row.get("msgnodename")
            if nodename:
                add_node(graph, "node", nodename, nodename, row)

        # Queues from PSQUEUEDEFN
        queue_result = ib.queues(env, "", min(limit, 200))
        for row in queue_result.get("items", []):
            queuename = row.get("queuename")
            if queuename:
                add_node(graph, "queue", queuename, queuename, row)

        # Services from PSIBAPPLDEFN
        svc_result = ib.services(env, "", min(limit, 200))
        for row in svc_result.get("items", []):
            svcname = row.get("ptibapplname")
            if svcname:
                seen_ops.add(svcname.upper())
                add_node(graph, "service_operation", svcname, svcname, row)
                svc_detail = ib.service(env, svcname)
                for routing in (svc_detail.get("item") or {}).get("routings", [])[:limit]:
                    rname = routing.get("routingdefnname")
                    if rname:
                        add_node(graph, "routing", rname, rname, routing)
                        add_edge(graph, "service_operation", svcname, "routing", rname, "ROUTES", routing)
                pc_result = ib.service_peoplecode(env, svcname)
                for pc in pc_result.get("items", [])[:limit]:
                    ref = pc.get("reference")
                    encoded = pc.get("encoded_reference") or (peoplecode.encode_reference(ref) if ref else None)
                    if encoded and ref:
                        add_node(graph, "peoplecode", encoded, ref, pc)
                        add_edge(graph, "service_operation", svcname, "peoplecode", encoded, "CONTAINS", pc)

        # Routings with edges: service_operation -> routing -> queue/nodes
        rtng_result = ib.routings(env, "", min(limit, 300))
        for row in rtng_result.get("items", []):
            rname = row.get("routingdefnname")
            op    = row.get("ib_operationname")
            sender   = row.get("sendernodename")
            receiver = row.get("receivernodename")
            queue = row.get("queuename")
            if not rname:
                continue
            add_node(graph, "routing", rname, rname, row)
            if op:
                seen_ops.add(op.upper())
                add_node(graph, "service_operation", op, op, {})
                add_edge(graph, "service_operation", op, "routing", rname, "ROUTES", row)
                add_edge(graph, "routing", rname, "service_operation", op, "BELONGS_TO", row)
            if sender:
                add_node(graph, "node", sender, sender, {})
                add_edge(graph, "node", sender, "routing", rname, "USES", row)
            if receiver:
                add_node(graph, "node", receiver, receiver, {})
                add_edge(graph, "routing", rname, "node", receiver, "USES", row)
            if queue:
                add_node(graph, "queue", queue, queue, {})
                add_edge(graph, "routing", rname, "queue", queue, "USES", row)
                if op:
                    add_edge(graph, "service_operation", op, "queue", queue, "USES", row)

        # Traditional IB operations may not exist in PSIBAPPLDEFN; attach their PeopleCode too.
        for opname in sorted(seen_ops)[:limit]:
            pc_result = ib.service_peoplecode(env, opname)
            for pc in pc_result.get("items", [])[:limit]:
                ref = pc.get("reference")
                encoded = pc.get("encoded_reference") or (peoplecode.encode_reference(ref) if ref else None)
                if encoded and ref:
                    add_node(graph, "peoplecode", encoded, ref, pc)
                    add_edge(graph, "service_operation", opname, "peoplecode", encoded, "CONTAINS", pc)

        total = (
            len(node_result.get("items", []))
            + len(queue_result.get("items", []))
            + len(svc_result.get("items", []))
            + len(rtng_result.get("items", []))
        )
        for warnings_list in (node_result, queue_result, svc_result, rtng_result):
            for w in warnings_list.get("warnings", []):
                if w:
                    graph["warnings"].append(w)
        return total

    def menus():
        if not ptmetadata.has_table(env, "PSMENUDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT d.MENUNAME, d.DESCR, d.MENUTYPE, d.OBJECTOWNERID,
                   i.PNLGRPNAME AS component
              FROM (SELECT MENUNAME, DESCR, MENUTYPE, OBJECTOWNERID
                      FROM SYSADM.PSMENUDEFN
                     WHERE ROWNUM <= {limit}) d
              LEFT JOIN SYSADM.PSMENUITEM i
                ON i.MENUNAME = d.MENUNAME
               AND TRIM(i.PNLGRPNAME) IS NOT NULL
               AND i.PNLGRPNAME != ' '
        """) or []
        seen = set()
        for r in rows:
            mn = r.get("menuname")
            if not mn:
                continue
            if mn not in seen:
                add_node(graph, "menu", mn, r.get("descr") or mn, r)
                seen.add(mn)
            comp = r.get("component")
            if comp and comp.strip():
                add_node(graph, "component", comp, comp, {})
                add_edge(graph, "menu", mn, "component", comp, "CONTAINS", r)
        return len(seen)

    def trees():
        if not ptmetadata.has_table(env, "PSTREEDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT TREENAME, SETID, SETCNTRLVALUE, TREESTRCTPNM,
                   TREE_RECNAME, DESCR, EFF_STATUS, OBJECTOWNERID
              FROM SYSADM.PSTREEDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY TREENAME, EFFDT DESC
        """) or []
        seen = set()
        for r in rows:
            tn = r.get("treename")
            if not tn or tn in seen:
                continue
            seen.add(tn)
            add_node(graph, "tree", tn, r.get("descr") or tn, r)
            strct_rec = r.get("treestrctpnm")
            if strct_rec and strct_rec.strip():
                add_node(graph, "record", strct_rec, strct_rec, {})
                add_edge(graph, "tree", tn, "record", strct_rec, "USES", r)
            leaf_rec = r.get("tree_recname")
            if leaf_rec and leaf_rec.strip() and leaf_rec != strct_rec:
                add_node(graph, "record", leaf_rec, leaf_rec, {})
                add_edge(graph, "tree", tn, "record", leaf_rec, "USES", r)
        return len(seen)

    def sql_definitions():
        if not ptmetadata.has_table(env, "PSSQLDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT SQLID, SQLTYPE, OBJECTOWNERID, LASTUPDDTTM
              FROM SYSADM.PSSQLDEFN
             WHERE SQLTYPE = 0
               AND ROWNUM <= {limit}
             ORDER BY SQLID
        """) or []
        for r in rows:
            sqlid = r.get("sqlid")
            if sqlid:
                add_node(graph, "sql_definition", sqlid, sqlid, r)
        return len(rows)

    def queries():
        if not ptmetadata.has_table(env, "PSQRYDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT QRYNAME, OPRID, DESCR, QRYFOLDER, QRYTYPE,
                   LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSQRYDEFN
             WHERE OPRID = ' '
               AND ROWNUM <= {limit}
             ORDER BY QRYNAME
        """) or []
        for r in rows:
            qn = r.get("qryname")
            if qn:
                add_node(graph, "query", qn, r.get("descr") or qn, r)
        return len(rows)

    def component_interfaces():
        if not ptmetadata.has_table(env, "PSBCDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT b.BCNAME, b.DESCR, b.VERSION, b.BCTYPE,
                   b.PNLGRPNAME AS component, b.OBJECTOWNERID, b.LASTUPDDTTM
              FROM SYSADM.PSBCDEFN b
             WHERE ROWNUM <= {limit}
             ORDER BY b.BCNAME
        """) or []
        for r in rows:
            ci_name = r.get("bcname")
            if not ci_name:
                continue
            add_node(graph, "ci", ci_name, r.get("descr") or ci_name, r)
            comp = r.get("component")
            if comp and comp.strip():
                add_node(graph, "component", comp, comp, {})
                add_edge(graph, "ci", ci_name, "component", comp, "WRAPS", r)
        return len(rows)

    def approvals():
        if not ptmetadata.has_table(env, "PS_EOAW_TXN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT EOAWPRCS_ID, DESCR, OBJECTOWNERID
              FROM SYSADM.PS_EOAW_TXN
             WHERE ROWNUM <= {limit}
             ORDER BY EOAWPRCS_ID
        """) or []
        for r in rows:
            aid = r.get("eoawprcs_id")
            if not aid:
                continue
            add_node(graph, "approval", aid, r.get("descr") or aid, r)
        return len(rows)

    def messages():
        if not ptmetadata.has_table(env, "PSMSGCATDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT MESSAGE_SET_NBR, MESSAGE_NBR, SEVERITY, MESSAGE_TEXT
              FROM SYSADM.PSMSGCATDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY MESSAGE_SET_NBR, MESSAGE_NBR
        """) or []
        for r in rows:
            sn = r.get("message_set_nbr")
            mn = r.get("message_nbr")
            if sn is None or mn is None:
                continue
            name = f"{sn}.{mn}"
            text = str(r.get("message_text") or "").strip() or name
            add_node(graph, "message_catalog", name, text[:80], r)
        return len(rows)

    def event_mappings():
        if not ptmetadata.has_table(env, "PSEFMAPPINGDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT EFMAPPINGID, DESCR, STATUS, OBJECTOWNERID
              FROM SYSADM.PSEFMAPPINGDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY EFMAPPINGID
        """) or []
        for r in rows:
            eid = r.get("efmappingid")
            if not eid:
                continue
            add_node(graph, "event_mapping", eid, r.get("descr") or eid, r)
        return len(rows)

    def related_content_defs():
        if not ptmetadata.has_table(env, "PSRELCONDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT RELCONID, DESCR, STATUS, SERVICETYPE, OBJECTOWNERID
              FROM SYSADM.PSRELCONDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY RELCONID
        """) or []
        for r in rows:
            rid = r.get("relconid")
            if not rid:
                continue
            add_node(graph, "related_content", rid, r.get("descr") or rid, r)
        return len(rows)

    def nav_collections():
        if not ptmetadata.has_table(env, "PTNC_COLLECTION"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PORTAL_NAME, COLL_ID, COLL_TITLE, EFF_STATUS
              FROM SYSADM.PTNC_COLLECTION
             WHERE ROWNUM <= {limit}
             ORDER BY PORTAL_NAME, COLL_ID
        """) or []
        for r in rows:
            cid = r.get("coll_id")
            if not cid:
                continue
            add_node(graph, "nav_collection", cid, r.get("coll_title") or cid, r)
        return len(rows)

    def xpub_reports():
        if not ptmetadata.has_table(env, "PSXPRPTDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT REPORT_DEFN_ID, DESCR, OBJECTOWNERID, DS_ID
              FROM SYSADM.PSXPRPTDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY REPORT_DEFN_ID
        """) or []
        for r in rows:
            rid = r.get("report_defn_id")
            if not rid:
                continue
            add_node(graph, "xml_publisher_report", rid, r.get("descr") or rid, r)
        return len(rows)

    def search_definitions():
        if not ptmetadata.has_table(env, "PSPTSF_SD"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTSF_SOURCE_NAME, DESCR100, PTSF_SOURCE_TYPE, OBJECTOWNERID
              FROM SYSADM.PSPTSF_SD
             WHERE ROWNUM <= {limit}
             ORDER BY PTSF_SOURCE_NAME
        """) or []
        for r in rows:
            sid = r.get("ptsf_source_name")
            if not sid:
                continue
            add_node(graph, "search_definition", sid, r.get("descr100") or sid, r)
        return len(rows)

    def search_categories():
        if not ptmetadata.has_table(env, "PSPTSF_SRCCAT"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTSF_SRCCAT_NAME, DESCR100, OBJECTOWNERID
              FROM SYSADM.PSPTSF_SRCCAT
             WHERE ROWNUM <= {limit}
             ORDER BY PTSF_SRCCAT_NAME
        """) or []
        for r in rows:
            cid = r.get("ptsf_srccat_name")
            if not cid:
                continue
            add_node(graph, "search_category", cid, r.get("descr100") or cid, r)
        return len(rows)

    def drop_zones():
        if not ptmetadata.has_table(env, "PSPTDZDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT DZNAME, DESCR, OBJECTOWNERID
              FROM SYSADM.PSPTDZDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY DZNAME
        """) or []
        for r in rows:
            dz = r.get("dzname")
            if not dz:
                continue
            add_node(graph, "drop_zone", dz, r.get("descr") or dz, r)
        return len(rows)

    def pivot_grids():
        if not ptmetadata.has_table(env, "PSPGCORE"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTPG_PGRIDNAME, PTPG_PGRIDTITLE, PTPG_DSTYPE, OBJECTOWNERID
              FROM SYSADM.PSPGCORE
             WHERE ROWNUM <= {limit}
             ORDER BY PTPG_PGRIDNAME
        """) or []
        for r in rows:
            pid = r.get("ptpg_pgridname")
            if not pid:
                continue
            add_node(graph, "pivot_grid", pid, r.get("ptpg_pgridtitle") or pid, r)
        return len(rows)

    def connected_queries():
        if not ptmetadata.has_table(env, "PSCONQRSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT CONQRSNAME, DESCR, PT_REPORT_STATUS, OBJECTOWNERID
              FROM SYSADM.PSCONQRSDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY CONQRSNAME
        """) or []
        for r in rows:
            cid = r.get("conqrsname")
            if not cid:
                continue
            add_node(graph, "connected_query", cid, r.get("descr") or cid, r)
        return len(rows)

    def ptf_tests():
        if not ptmetadata.has_table(env, "PSPTTSTDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTTST_NAME, PTTST_TYPE, DESCR, PTTST_PARENTFOLDER
              FROM SYSADM.PSPTTSTDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PTTST_NAME
        """) or []
        for r in rows:
            tid = r.get("pttst_name")
            if not tid:
                continue
            label = (r.get("descr") or "").strip() or tid
            add_node(graph, "ptf_test", tid, label, r)
        return len(rows)

    def content_services():
        if not ptmetadata.has_table(env, "PSPTCSSRVDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTCS_SERVICEID, PTCS_SERVICENAME, DESCR254,
                   PTCS_SERVICEURLTYP, OBJECTOWNERID
              FROM SYSADM.PSPTCSSRVDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PTCS_SERVICEID
        """) or []
        for r in rows:
            sid = r.get("ptcs_serviceid")
            if not sid:
                continue
            label = (r.get("ptcs_servicename") or "").strip() or sid
            add_node(graph, "content_service", sid, label, r)
        return len(rows)

    def app_classes():
        if not ptmetadata.has_table(env, "PSAPPCLASSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT APPCLASSID, PACKAGEROOT, QUALIFYPATH, APPCLASSREF
              FROM SYSADM.PSAPPCLASSDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PACKAGEROOT, QUALIFYPATH, APPCLASSID
        """) or []
        for r in rows:
            pkg = r.get("packageroot") or ""
            qp = r.get("qualifypath") or ""
            cid = r.get("appclassid") or ""
            if not (pkg and cid):
                continue
            key = f"{pkg}~{qp}~{cid}"
            qp_stripped = qp.strip()
            if qp_stripped == ":" or not qp_stripped:
                label = f"{pkg}:{cid}"
            else:
                label = f"{pkg}:{qp_stripped}:{cid}"
            add_node(graph, "app_class", key, label, r)
        return len(rows)

    def archive_objects():
        if not ptmetadata.has_table(env, "PSARCHOBJDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PSARCH_OBJECT, DESCR, OBJECTOWNERID
              FROM SYSADM.PSARCHOBJDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PSARCH_OBJECT
        """) or []
        for r in rows:
            aname = r.get("psarch_object")
            if not aname:
                continue
            label = (r.get("descr") or "").strip() or aname
            add_node(graph, "archive_object", aname, label, r)
        return len(rows)

    def style_sheets():
        if not ptmetadata.has_table(env, "PSSTYLSHEETDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT STYLESHEETNAME, STYLESHEETTYPE, DESCR, OBJECTOWNERID
              FROM SYSADM.PSSTYLSHEETDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY STYLESHEETTYPE, STYLESHEETNAME
        """) or []
        for r in rows:
            sname = r.get("stylesheetname")
            if not sname:
                continue
            label = (r.get("descr") or "").strip() or sname
            add_node(graph, "style_sheet", sname, label, r)
        return len(rows)

    def timezones():
        if not ptmetadata.has_table(env, "PSTIMEZONEDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT t.TIMEZONE, t.TZDESCR, t.UTCOFFSET, t.OBSERVEDST
              FROM SYSADM.PSTIMEZONEDEFN t
             WHERE t.PTEFFDTTM = (
                   SELECT MAX(t2.PTEFFDTTM) FROM SYSADM.PSTIMEZONEDEFN t2
                    WHERE t2.TIMEZONE = t.TIMEZONE)
               AND ROWNUM <= {limit}
             ORDER BY t.TIMEZONE
        """) or []
        for r in rows:
            tzname = r.get("timezone")
            if not tzname:
                continue
            label = (r.get("tzdescr") or "").strip() or tzname
            add_node(graph, "timezone", tzname, label, r)
        return len(rows)

    def locales():
        if not ptmetadata.has_table(env, "PSLOCALEDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT d.LOCALECD, d.DESCR
              FROM SYSADM.PSLOCALEDEFN d
             WHERE ROWNUM <= {limit}
             ORDER BY d.LOCALECD
        """) or []
        for r in rows:
            lcode = r.get("localecd")
            if not lcode:
                continue
            label = (r.get("descr") or "").strip() or lcode
            add_node(graph, "locale", lcode, label, r)
        return len(rows)

    def pm_metrics():
        if not ptmetadata.has_table(env, "PSPMMETRICDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT m.PM_METRICID, m.PM_METRICLABEL, m.PM_METRICTYPE
              FROM SYSADM.PSPMMETRICDEFN m
             WHERE ROWNUM <= {limit}
             ORDER BY m.PM_METRICID
        """) or []
        for r in rows:
            mid = r.get("pm_metricid")
            if mid is None:
                continue
            label = (r.get("pm_metriclabel") or "").strip() or str(mid)
            add_node(graph, "pm_metric", str(mid), label, r)
        return len(rows)


    def ib_routings():
        if not ptmetadata.has_table(env, "PSIBRTNGDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT ROUTINGDEFNNAME, EFF_STATUS, SENDERNODENAME, RECEIVERNODENAME,
                   IB_OPERATIONNAME, RTNGTYPE, DESCR
              FROM SYSADM.PSIBRTNGDEFN
             WHERE ROUTINGDEFNNAME NOT LIKE '~%'
               AND ROWNUM <= {limit}
             ORDER BY IB_OPERATIONNAME, ROUTINGDEFNNAME
        """) or []
        for r in rows:
            rname = r.get("routingdefnname")
            if not rname:
                continue
            label = rname
            add_node(graph, "ib_routing", rname, label, r)
        return len(rows)

    def chatbot_skills():
        if not ptmetadata.has_table(env, "PSCBAPPLDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTCBAPPLNAME, DESCR50, PTCBURLPARAMNAME, PACKAGEROOT, STATUS
              FROM SYSADM.PSCBAPPLDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PTCBAPPLNAME
        """) or []
        for r in rows:
            sname = r.get("ptcbapplname")
            if not sname:
                continue
            label = (r.get("descr50") or "").strip() or sname
            add_node(graph, "chatbot_skill", sname, label, r)
        return len(rows)

    def url_definitions():
        if not ptmetadata.has_table(env, "PSURLDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT URL_ID, DESCR, URL, OBJECTOWNERID
              FROM SYSADM.PSURLDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY URL_ID
        """) or []
        for r in rows:
            uid = r.get("url_id")
            if not uid:
                continue
            label = (r.get("descr") or "").strip() or uid
            add_node(graph, "url_definition", uid, label, r)
        return len(rows)

    def ib_service_groups():
        if not ptmetadata.has_table(env, "PSIBGROUPDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT IB_INTGROUPNAME, DESCR, DESCRLONG, OBJECTOWNERID
              FROM SYSADM.PSIBGROUPDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY IB_INTGROUPNAME
        """) or []
        for r in rows:
            gname = r.get("ib_intgroupname")
            if not gname:
                continue
            label = (r.get("descr") or "").strip() or gname
            add_node(graph, "ib_service_group", gname, label, r)
        return len(rows)

    def ads_definitions():
        if not ptmetadata.has_table(env, "PSADSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTADSNAME, DESCR, DESCR254, OBJECTOWNERID
              FROM SYSADM.PSADSDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PTADSNAME
        """) or []
        for r in rows:
            ads_name = r.get("ptadsname")
            if not ads_name:
                continue
            label = (r.get("descr") or "").strip() or ads_name
            add_node(graph, "ads_definition", ads_name, label, r)
        return len(rows)

    def ib_applications():
        if not ptmetadata.has_table(env, "PSIBAPPLDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTIBAPPLNAME, PTIB_APPSRVGRP, STATUS, PTIBAPPLTYPE,
                   IB_SERVICENAME, OBJECTOWNERID
              FROM SYSADM.PSIBAPPLDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PTIBAPPLNAME
        """) or []
        for r in rows:
            aid = r.get("ptibapplname")
            if not aid:
                continue
            label = aid
            descr_long = ""
            add_node(graph, "ib_application", aid, label, r)
        return len(rows)

    def ib_messages():
        if not ptmetadata.has_table(env, "PSMSGDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT MSGNAME, DESCR, CHNLNAME, MSGSTATUS, OBJECTOWNERID
              FROM SYSADM.PSMSGDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY MSGNAME
        """) or []
        for r in rows:
            mid = r.get("msgname")
            if not mid:
                continue
            add_node(graph, "message", mid, r.get("descr") or mid, r)
        return len(rows)

    def projects():
        if not ptmetadata.has_table(env, "PSPROJECTDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PROJECTNAME, PROJECTDESCR, LASTUPDOPRID, LASTUPDDTTM
              FROM SYSADM.PSPROJECTDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY LASTUPDDTTM DESC
        """) or []
        for r in rows:
            pid = r.get("projectname")
            if not pid:
                continue
            add_node(graph, "project", pid, r.get("projectdescr") or pid, r)
        return len(rows)

    def xlat_fields():
        if not ptmetadata.has_table(env, "PSXLATDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT d.FIELDNAME, COUNT(i.FIELDVALUE) AS VALUE_COUNT
              FROM SYSADM.PSXLATDEFN d
              LEFT JOIN SYSADM.PSXLATITEM i ON i.FIELDNAME = d.FIELDNAME AND i.EFF_STATUS = 'A'
             WHERE ROWNUM <= {limit}
             GROUP BY d.FIELDNAME
             ORDER BY d.FIELDNAME
        """) or []
        for r in rows:
            fid = r.get("fieldname")
            if not fid:
                continue
            add_node(graph, "xlat_field", fid, fid, r)
        return len(rows)

    def file_layouts():
        if not ptmetadata.has_table(env, "PSFLDDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT FLDDEFNNAME, FLDFORMAT, FLDSEGCOUNT, DESCR
              FROM SYSADM.PSFLDDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY FLDDEFNNAME
        """) or []
        for r in rows:
            fid = r.get("flddefnname")
            if not fid:
                continue
            add_node(graph, "file_layout", fid, r.get("descr") or fid, r)
        return len(rows)

    def process_definitions():
        if not ptmetadata.has_table(env, "PS_PRCSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PRCSTYPE, PRCSNAME, DESCR, PRCSCATEGORY
              FROM SYSADM.PS_PRCSDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PRCSTYPE, PRCSNAME
        """) or []
        for r in rows:
            pname = r.get("prcsname")
            ptype = r.get("prcstype", "")
            if not pname:
                continue
            key = f"{ptype}~{pname}"
            add_node(graph, "prcs_defn", key, r.get("descr") or pname, r)
        return len(rows)

    for name, loader in (
        ("operators", operators),
        ("roles", roles),
        ("permissionlists", permissionlists),
        ("components", components),
        ("pages", pages),
        ("fields", fields),
        ("peoplecode", peoplecode_programs),
        ("application_engines", application_engines),
        ("integration_broker", integration_broker),
        ("menus", menus),
        ("trees", trees),
        ("sql_definitions", sql_definitions),
        ("queries", queries),
        ("component_interfaces", component_interfaces),
        ("approvals", approvals),
        ("messages", messages),
        ("xpub_reports", xpub_reports),
        ("nav_collections", nav_collections),
        ("event_mappings", event_mappings),
        ("related_content", related_content_defs),
        ("search_definitions", search_definitions),
        ("search_categories", search_categories),
        ("drop_zones", drop_zones),
        ("pivot_grids", pivot_grids),
        ("connected_queries", connected_queries),
        ("ib_messages", ib_messages),
        ("projects", projects),
        ("xlat_fields", xlat_fields),
        ("file_layouts", file_layouts),
        ("process_definitions", process_definitions),
        ("ib_applications", ib_applications),
        ("app_classes", app_classes),
        ("content_services", content_services),
        ("ptf_tests", ptf_tests),
        ("archive_objects", archive_objects),
        ("style_sheets", style_sheets),
        ("ib_routings", ib_routings),
        ("chatbot_skills", chatbot_skills),
        ("url_definitions", url_definitions),
        ("ib_service_groups", ib_service_groups),
        ("ads_definitions", ads_definitions),
        ("timezones", timezones),
        ("locales", locales),
        ("pm_metrics", pm_metrics),
    ):
        provider(graph, name, loader)

    graph["built_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    graph["build_seconds"] = round(time.time() - start, 3)
    GRAPHS[env] = graph
    if persist:
        save(env)
    BUILD_STATE[env] = {"status": "ready", "completed_at": time.time()}
    return stats(env)


def adjacency(graph, reverse=False, edge_types=None):
    edge_types = {item.upper() for item in edge_types} if edge_types else None
    adjacent = defaultdict(list)
    for edge in graph["edges"]:
        if edge_types and edge["type"] not in edge_types:
            continue
        source = edge["target"] if reverse else edge["source"]
        target = edge["source"] if reverse else edge["target"]
        adjacent[source].append((target, edge))
    return adjacent


def stats(env="HCM"):
    graph = current(env)
    by_type = defaultdict(int)
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for node in graph["nodes"].values():
        by_type[node["type"]] += 1

    for edge in graph["edges"]:
        out_degree[edge["source"]] += 1
        in_degree[edge["target"]] += 1

    disconnected = [
        node_id for node_id in graph["nodes"]
        if not in_degree[node_id] and not out_degree[node_id]
    ]
    orphaned = [
        node_id for node_id in graph["nodes"]
        if in_degree[node_id] and not out_degree[node_id]
    ]

    return {
        "environment": graph["environment"],
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "object_counts": dict(sorted(by_type.items())),
        "graph_health": "warning" if graph["warnings"] else "ok",
        "warning_count": len(graph["warnings"]),
        "warnings": graph["warnings"],
        "disconnected_count": len(disconnected),
        "disconnected_objects": disconnected[:100],
        "orphaned_count": len(orphaned),
        "orphaned_nodes": orphaned[:100],
        "built_at": graph["built_at"],
        "build_seconds": graph["build_seconds"],
        "cache_status": {
            "memory_loaded": graph["environment"] in GRAPHS,
            "persisted": graph_path(env).exists(),
            "path": str(graph_path(env)),
            "build_state": BUILD_STATE.get(graph["environment"], {"status": "idle"}),
        },
        "providers": graph["providers"],
    }


def get_node(env, node):
    return current(env)["nodes"].get(node)


def neighbors(env, node, direction="both", depth=1, edge_types=None):
    graph = current(env)
    depth = max(1, min(int(depth), 5))
    edge_types = {item.upper() for item in edge_types.split(",")} if isinstance(edge_types, str) and edge_types else edge_types
    forward = adjacency(graph, False, edge_types)
    reverse = adjacency(graph, True, edge_types)
    seen = {node}
    queue = deque([(node, 0)])
    nodes = []
    edges = []

    while queue:
        current_node, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        candidates = []
        if direction in ("out", "both"):
            candidates.extend(forward.get(current_node, []))
        if direction in ("in", "both"):
            candidates.extend(reverse.get(current_node, []))
        for target, edge in candidates:
            edges.append(edge)
            if target not in seen:
                seen.add(target)
                if graph["nodes"].get(target):
                    nodes.append(graph["nodes"][target])
                queue.append((target, current_depth + 1))

    return {
        "root": node,
        "nodes": nodes,
        "edges": edges,
    }


def shortest_path(env, source, target, edge_types=None):
    graph = current(env)
    adjacent = adjacency(graph, False, edge_types)
    reverse = adjacency(graph, True, edge_types)
    queue = deque([(source, [])])
    seen = {source}

    while queue:
        node, path = queue.popleft()
        if node == target:
            ids = [source]
            for edge in path:
                ids.append(edge["target"] if edge["source"] == ids[-1] else edge["source"])
            return {
                "found": True,
                "nodes": [graph["nodes"][node_id] for node_id in ids if node_id in graph["nodes"]],
                "edges": path,
                "length": len(path),
            }

        for next_node, edge in forward_reverse_neighbors(adjacent, reverse, node):
            if next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, path + [edge]))

    return {"found": False, "nodes": [], "edges": [], "length": None}


def forward_reverse_neighbors(forward, reverse, node):
    yield from forward.get(node, [])
    yield from reverse.get(node, [])


def dependency_tree(env, node, reverse=False, depth=3):
    direction = "in" if reverse else "out"
    return neighbors(env, node, direction=direction, depth=depth, edge_types=DEPENDENCY_EDGES)


def impact(env, node, depth=3):
    """Combined forward + reverse dependency traversal for impact analysis.

    Returns:
      - the node itself
      - forward_deps: things this node depends on (depth levels out)
      - reverse_deps: things that depend on this node (impact if it changes)
      - summary counts by type for each direction
    """
    graph = current(env)
    node_data = graph["nodes"].get(node)
    if not node_data:
        return {"found": False, "node": None, "forward_deps": {}, "reverse_deps": {}, "summary": {}}

    forward_result = dependency_tree(env, node, reverse=False, depth=depth)
    reverse_result = dependency_tree(env, node, reverse=True, depth=depth)

    def summarize(result):
        by_type = defaultdict(int)
        for n in result.get("nodes", []):
            ndata = graph["nodes"].get(n["id"])
            if ndata:
                by_type[ndata["type"]] += 1
        return dict(sorted(by_type.items()))

    return {
        "found": True,
        "node": node_data,
        "forward_deps": forward_result,
        "reverse_deps": reverse_result,
        "summary": {
            "forward_by_type": summarize(forward_result),
            "reverse_by_type": summarize(reverse_result),
            "total_downstream": len(forward_result.get("nodes", [])),
            "total_upstream": len(reverse_result.get("nodes", [])),
        },
    }


def connected_components(env):
    graph = current(env)
    forward = adjacency(graph, False)
    reverse = adjacency(graph, True)
    seen = set()
    components = []

    for node in graph["nodes"]:
        if node in seen:
            continue
        group = []
        queue = deque([node])
        seen.add(node)
        while queue:
            current_node = queue.popleft()
            group.append(current_node)
            for target, _ in forward_reverse_neighbors(forward, reverse, current_node):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        components.append(group)

    return sorted(components, key=len, reverse=True)


def cycles(env):
    graph = current(env)
    forward = adjacency(graph, False)
    visited = set()
    stack = set()
    found = []

    def visit(node, path):
        if node in stack:
            found.append(path[path.index(node):] if node in path else path)
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for target, _ in forward.get(node, []):
            visit(target, path + [target])
        stack.remove(node)

    for node in graph["nodes"]:
        visit(node, [node])
    return found[:100]


def topological_order(env):
    graph = current(env)
    indegree = defaultdict(int)
    outgoing = defaultdict(list)
    for edge in graph["edges"]:
        if edge["type"] in DEPENDENCY_EDGES:
            outgoing[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1
            indegree.setdefault(edge["source"], 0)

    queue = deque([node for node in graph["nodes"] if indegree[node] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for target in outgoing.get(node, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return {
        "complete": len(order) == len(graph["nodes"]),
        "order": order,
        "cycle_count": 0 if len(order) == len(graph["nodes"]) else len(cycles(env)),
    }


def _stable_json(value):
    return json.dumps(value or {}, sort_keys=True, default=str)


def _edge_key(edge):
    return edge.get("id") or f"{edge.get('source')}->{edge.get('type')}->{edge.get('target')}"


def _diff_graphs(g1, g2, env1="HCM", env2="FSCM", node_types=None, limit=200, snapshot_meta=None):
    limit = max(1, min(int(limit), 1000))
    type_filter = None
    if node_types:
        if isinstance(node_types, str):
            type_filter = {item.strip().lower() for item in node_types.split(",") if item.strip()}
        else:
            type_filter = {str(item).lower() for item in node_types if item}

    nodes1 = {
        node_id: node for node_id, node in g1.get("nodes", {}).items()
        if not type_filter or node.get("type") in type_filter
    }
    nodes2 = {
        node_id: node for node_id, node in g2.get("nodes", {}).items()
        if not type_filter or node.get("type") in type_filter
    }

    only1_ids = sorted(set(nodes1) - set(nodes2))
    only2_ids = sorted(set(nodes2) - set(nodes1))
    common_ids = sorted(set(nodes1) & set(nodes2))

    changed_nodes = []
    for node_id in common_ids:
        n1 = nodes1[node_id]
        n2 = nodes2[node_id]
        diffs = []
        for field in ("display_name", "canonical_url", "icon"):
            if str(n1.get(field) or "") != str(n2.get(field) or ""):
                diffs.append({"field": field, "env1": n1.get(field), "env2": n2.get(field)})
        if _stable_json(n1.get("metadata")) != _stable_json(n2.get("metadata")):
            diffs.append({"field": "metadata", "env1": n1.get("metadata"), "env2": n2.get("metadata")})
        if diffs:
            changed_nodes.append({"id": node_id, "env1": n1, "env2": n2, "diffs": diffs})

    allowed_nodes = set(nodes1) | set(nodes2)
    edges1 = {
        _edge_key(edge): edge for edge in g1.get("edges", [])
        if edge.get("source") in allowed_nodes and edge.get("target") in allowed_nodes
    }
    edges2 = {
        _edge_key(edge): edge for edge in g2.get("edges", [])
        if edge.get("source") in allowed_nodes and edge.get("target") in allowed_nodes
    }

    only_edge1 = sorted(set(edges1) - set(edges2))
    only_edge2 = sorted(set(edges2) - set(edges1))

    changed_edges = []
    for edge_id in sorted(set(edges1) & set(edges2)):
        e1 = edges1[edge_id]
        e2 = edges2[edge_id]
        if _stable_json(e1.get("metadata")) != _stable_json(e2.get("metadata")):
            changed_edges.append({"id": edge_id, "env1": e1, "env2": e2})

    return {
        "env1": env1.upper(),
        "env2": env2.upper(),
        "node_types": sorted(type_filter) if type_filter else [],
        "limit": limit,
        "summary": {
            "env1_nodes": len(nodes1),
            "env2_nodes": len(nodes2),
            "common_nodes": len(common_ids),
            "only_in_env1_nodes": len(only1_ids),
            "only_in_env2_nodes": len(only2_ids),
            "changed_nodes": len(changed_nodes),
            "env1_edges": len(edges1),
            "env2_edges": len(edges2),
            "only_in_env1_edges": len(only_edge1),
            "only_in_env2_edges": len(only_edge2),
            "changed_edges": len(changed_edges),
        },
        "only_in_env1_nodes": [nodes1[node_id] for node_id in only1_ids[:limit]],
        "only_in_env2_nodes": [nodes2[node_id] for node_id in only2_ids[:limit]],
        "changed_nodes": changed_nodes[:limit],
        "only_in_env1_edges": [edges1[edge_id] for edge_id in only_edge1[:limit]],
        "only_in_env2_edges": [edges2[edge_id] for edge_id in only_edge2[:limit]],
        "changed_edges": changed_edges[:limit],
        "snapshot": {
            "env1_built_at": g1.get("built_at"),
            "env2_built_at": g2.get("built_at"),
            "env1_path": str(graph_path(env1)),
            "env2_path": str(graph_path(env2)),
            **(snapshot_meta or {}),
        },
        "warnings": [
            item for item in [
                ptmetadata.warning("graph_snapshot_empty", f"{env1.upper()} graph snapshot is empty; build it with /api/graph/build?env={env1}") if not g1.get("nodes") else None,
                ptmetadata.warning("graph_snapshot_empty", f"{env2.upper()} graph snapshot is empty; build it with /api/graph/build?env={env2}") if not g2.get("nodes") else None,
            ] if item
        ],
    }


def diff(env1="HCM", env2="FSCM", node_types=None, limit=200):
    """Compare two persisted/current knowledge graph snapshots."""
    return _diff_graphs(current(env1), current(env2), env1, env2, node_types=node_types, limit=limit)


def diff_snapshots(snapshot1, snapshot2, node_types=None, limit=200):
    left = load_snapshot(snapshot1)
    right = load_snapshot(snapshot2)
    env1 = left["snapshot"].get("env") or left["graph"].get("environment") or "SNAPSHOT1"
    env2 = right["snapshot"].get("env") or right["graph"].get("environment") or "SNAPSHOT2"
    return _diff_graphs(
        left["graph"],
        right["graph"],
        env1,
        env2,
        node_types=node_types,
        limit=limit,
        snapshot_meta={
            "snapshot1": left["snapshot"],
            "snapshot2": right["snapshot"],
            "env1_path": left["snapshot"].get("path"),
            "env2_path": right["snapshot"].get("path"),
        },
    )


def drift(env="HCM", node_types=None, limit=500):
    """Compare current in-memory graph against the most recent snapshot for the same environment.

    Returns a diff shaped like _diff_graphs(), plus:
      - baseline_snapshot: the snapshot metadata used as the baseline
      - drift_summary: counts of new / removed / changed objects with per-type breakdowns
    """
    snaps = list_snapshots(env)
    if not snaps.get("snapshots"):
        return {
            "error": "no_baseline",
            "message": (
                f"No snapshots found for {env.upper()}. "
                "Build the graph and create a snapshot first via POST /api/graph/snapshots."
            ),
            "env": env.upper(),
        }

    baseline_entry = snaps["snapshots"][0]   # most-recent first per list_snapshots sort
    try:
        baseline_data = load_snapshot(baseline_entry["id"])
    except FileNotFoundError:
        return {
            "error": "snapshot_missing",
            "message": f"Snapshot file for {baseline_entry['id']} not found.",
            "env": env.upper(),
            "baseline_snapshot": baseline_entry,
        }

    baseline_graph = baseline_data["graph"]
    live_graph = current(env)
    baseline_at = baseline_entry.get("created_at", "?")[:16].replace("T", " ")

    result = _diff_graphs(
        baseline_graph,
        live_graph,
        env1=f"{env.upper()} @ {baseline_at}",
        env2=f"{env.upper()} (current)",
        node_types=node_types,
        limit=limit,
        snapshot_meta={
            "baseline_id": baseline_entry["id"],
            "baseline_at": baseline_entry.get("created_at"),
            "baseline_note": baseline_entry.get("note") or "",
            "live_built_at": live_graph.get("built_at"),
        },
    )

    def _type_counts(nodes):
        counts = {}
        for n in nodes:
            t = n.get("type") or "unknown"
            counts[t] = counts.get(t, 0) + 1
        return dict(sorted(counts.items()))

    result["baseline_snapshot"] = baseline_entry
    result["drift_summary"] = {
        "new_count": result["summary"]["only_in_env2_nodes"],
        "removed_count": result["summary"]["only_in_env1_nodes"],
        "changed_count": result["summary"]["changed_nodes"],
        "new_by_type": _type_counts(result["only_in_env2_nodes"]),
        "removed_by_type": _type_counts(result["only_in_env1_nodes"]),
        "baseline_at": baseline_entry.get("created_at"),
        "baseline_id": baseline_entry["id"],
    }
    return result


def search(env="HCM", q="", limit=50):
    graph = current(env)
    q = q.upper()
    limit = max(1, min(int(limit), 200))
    rows = []

    for node in graph["nodes"].values():
        haystack = " ".join([
            node.get("id", ""),
            node.get("type", ""),
            node.get("name", ""),
            node.get("display_name", ""),
            json.dumps(node.get("metadata", {}), default=str),
        ]).upper()
        if q in haystack:
            score = 10
            if node["name"] == q or node["id"].upper() == q:
                score += 100
            elif node["name"].startswith(q):
                score += 50
            rows.append({**node, "score": score})

    return sorted(rows, key=lambda item: (-item["score"], item["type"], item["name"]))[:limit]


def export_json(env="HCM"):
    return current(env)


def export_dot(env="HCM"):
    graph = current(env)
    lines = ["digraph DeathStar {"]
    for node in graph["nodes"].values():
        safe_id = node["id"].replace(":", "_").replace(".", "_").replace("-", "_")
        label = f"{node['type']}:{node['name']}".replace('"', "'")
        lines.append(f'  "{safe_id}" [label="{label}"];')
    for edge in graph["edges"]:
        source = edge["source"].replace(":", "_").replace(".", "_").replace("-", "_")
        target = edge["target"].replace(":", "_").replace(".", "_").replace("-", "_")
        lines.append(f'  "{source}" -> "{target}" [label="{edge["type"]}"];')
    lines.append("}")
    return "\n".join(lines)


def export_graphml(env="HCM"):
    graph = current(env)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">', '<graph edgedefault="directed">']
    for node in graph["nodes"].values():
        lines.append(f'<node id="{node["id"]}"><data key="type">{node["type"]}</data><data key="name">{node["name"]}</data></node>')
    for edge in graph["edges"]:
        lines.append(f'<edge id="{edge["id"]}" source="{edge["source"]}" target="{edge["target"]}"><data key="type">{edge["type"]}</data></edge>')
    lines.extend(["</graph>", "</graphml>"])
    return "\n".join(lines)
