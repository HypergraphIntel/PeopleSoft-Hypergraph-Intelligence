import json
import re
import time
from collections import defaultdict, deque
from pathlib import Path

from connectors import ae, ib, peoplecode, psdb, ptmetadata, uom

DATA_DIR = Path("/opt/deathstar-api/data")
SNAPSHOT_DIR = DATA_DIR / "graph_snapshots"
SNAPSHOT_MANIFEST = SNAPSHOT_DIR / "manifest.json"
GRAPHS = {}
BUILD_STATE = {}
GRAPH_SOURCE = "knowledge_graph"
GRAPH_VOCABULARY = "knowledge_graph"
GRAPH_SEMANTICS = "persisted enterprise relationship graph"

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
    "DEPLOYS",
}

EDGE_TYPES.add("ROUTES")
EDGE_TYPES.add("WRAPS")
EDGE_TYPES.add("INCLUDES")

DEPENDENCY_EDGES = {"USES", "CONTAINS", "REFERENCES", "DEPENDS_ON", "CALLS", "READS", "WRITES", "DEPLOYS", "SECURES", "EXPOSES", "ROUTES", "WRAPS", "INCLUDES"}

_SQL_COMMENT_RE = re.compile(r"/\*.*?\*/|--[^\n\r]*", re.S)
_SQL_STRING_RE = re.compile(r"'(?:''|[^'])*'")
_WRITE_PATTERNS = [
    re.compile(r"\bINSERT\s+INTO\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
    re.compile(r"\bUPDATE\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
    re.compile(r"\bDELETE\s+FROM\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
    re.compile(r"\bMERGE\s+INTO\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
]
_READ_PATTERNS = [
    re.compile(r"\bFROM\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
    re.compile(r"\bJOIN\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
    re.compile(r"\bUSING\s+(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))", re.I),
]
_FROM_BLOCK_RE = re.compile(
    r"\bFROM\b(?P<body>.*?)(?=\bWHERE\b|\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b|"
    r"\bUNION\b|\bMINUS\b|\bINTERSECT\b|\bCONNECT\s+BY\b|\bSTART\s+WITH\b|$)",
    re.I | re.S,
)
_COMMA_JOIN_RE = re.compile(
    r",\s*(?:TABLE\s+)?([A-Z0-9_$#.]+|\%TABLE\s*\(\s*[A-Z0-9_]+\s*\))"
    r"(?=\s+(?:[A-Z][A-Z0-9_$#]*|WHERE|JOIN|ON|$)|\s*,|\s*\))",
    re.I,
)
_META_WRITE_PATTERNS = [
    re.compile(r"%TRUNCATETABLE\s*\(\s*([A-Z0-9_$#.]+)\s*\)", re.I),
]
_META_INSERT_SELECT_RE = re.compile(r"%INSERTSELECT\s*\(\s*([A-Z0-9_$#.]+)\s*,\s*([A-Z0-9_$#.]+)", re.I)


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
        "_source": GRAPH_SOURCE,
        "_vocabulary": GRAPH_VOCABULARY,
        "_semantics": GRAPH_SEMANTICS,
    }


def normalize_graph_shape(graph):
    """Apply the shared graph payload contract to persisted KG graphs.

    Older snapshots may only have edge `type`, while UOM/domain graph payloads
    expose both `type` and `relationship` plus graph vocabulary metadata.
    Normalize in memory so exports and loaded snapshots share the same shape
    without requiring an immediate rebuild.
    """
    graph.setdefault("_source", GRAPH_SOURCE)
    graph.setdefault("_vocabulary", GRAPH_VOCABULARY)
    graph.setdefault("_semantics", GRAPH_SEMANTICS)
    for edge in graph.get("edges", []) or []:
        edge_type = str(edge.get("type") or edge.get("relationship") or "").strip().upper()
        if edge_type:
            edge["type"] = edge_type
            edge.setdefault("relationship", edge_type)
    return graph


def _strip_sql_for_table_scan(sql_text):
    text = _SQL_COMMENT_RE.sub(" ", sql_text or "")
    text = _SQL_STRING_RE.sub(" ", text)
    return text


def _normalize_peopletools_table_name(raw_name):
    name = str(raw_name or "").strip().upper()
    if not name:
        return ""

    table_macro = re.match(r"%TABLE\s*\(\s*([A-Z0-9_]+)\s*\)", name, re.I)
    if table_macro:
        return table_macro.group(1).upper()

    # Remove owner/database qualifiers and common quoting.
    name = name.split("@", 1)[0]
    name = name.split(".")[-1]
    name = name.strip('"')

    if name.startswith("SYSADM."):
        name = name[7:]
    if name.startswith("PS_"):
        name = name[3:]

    if not re.match(r"^[A-Z][A-Z0-9_#$]*$", name):
        return ""
    return name


def _comma_join_record_names(sql_text):
    """Extract additional records from comma-style FROM lists."""
    records = set()
    for block in _FROM_BLOCK_RE.finditer(sql_text or ""):
        for match in _COMMA_JOIN_RE.finditer(block.group("body") or ""):
            record = _normalize_peopletools_table_name(match.group(1))
            if record:
                records.add(record)
    return records


def sql_record_access(sql_text):
    """Extract conservative PeopleSoft record READS/WRITES from SQL text."""
    text = _strip_sql_for_table_scan(sql_text)
    writes = {
        rec
        for pattern in _WRITE_PATTERNS
        for rec in (_normalize_peopletools_table_name(m.group(1)) for m in pattern.finditer(text))
        if rec
    }
    writes.update(
        rec
        for pattern in _META_WRITE_PATTERNS
        for rec in (_normalize_peopletools_table_name(m.group(1)) for m in pattern.finditer(text))
        if rec
    )
    reads = {
        rec
        for pattern in _READ_PATTERNS
        for rec in (_normalize_peopletools_table_name(m.group(1)) for m in pattern.finditer(text))
        if rec
    }
    reads.update(_comma_join_record_names(text))
    for match in _META_INSERT_SELECT_RE.finditer(text):
        target = _normalize_peopletools_table_name(match.group(1))
        source = _normalize_peopletools_table_name(match.group(2))
        if target:
            writes.add(target)
        if source:
            reads.add(source)
    # INSERT INTO target also appears in some FROM-like constructs; write wins.
    reads -= writes
    return {"reads": sorted(reads), "writes": sorted(writes)}


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
            normalize_graph_shape(g)
            g["_edge_ids"] = {e["id"] for e in g.get("edges", [])}
            GRAPHS[env] = g
        else:
            GRAPHS[env] = empty_graph(env)
    return GRAPHS[env]


def save(env="HCM"):
    graph = current(env)
    normalize_graph_shape(graph)
    saveable = {k: v for k, v in graph.items() if k != "_edge_ids"}
    graph_path(env).write_text(json.dumps(saveable, indent=2, default=str))
    return graph


def create_snapshot(env="HCM", name="", note="", include_graph=True):
    env = env.upper()
    graph = current(env)
    normalize_graph_shape(graph)
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
        "_source": graph.get("_source", GRAPH_SOURCE),
        "_vocabulary": graph.get("_vocabulary", GRAPH_VOCABULARY),
        "_semantics": graph.get("_semantics", GRAPH_SEMANTICS),
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
    normalize_graph_shape(graph)
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
    node_metadata = dict(metadata or {})
    node = {
        "id": node_id(node_type, name),
        "type": node_type,
        "name": name,
        "display_name": display_name or name,
        "metadata": node_metadata,
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
        "relationship": edge_type,
        "metadata": dict(metadata or {}),
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

    def component_peoplecode():
        """Static canonical PC event sequence + component HAS_HANDLER edges."""
        from connectors.psdb import _COMP_EVENT_ORDER, _COMP_EVENT_PHASE

        ordered = sorted(_COMP_EVENT_ORDER, key=lambda k: _COMP_EVENT_ORDER[k])
        ev_set = set(ordered)

        phase_seen: set = set()
        for ev in ordered:
            phase_key, phase_label = _COMP_EVENT_PHASE.get(ev, ("other", "Other"))
            if phase_key not in phase_seen:
                add_node(graph, "pc_phase", phase_key, phase_label,
                         {"phase_key": phase_key})
                phase_seen.add(phase_key)
            add_node(graph, "event_type", ev, ev,
                     {"phase": phase_key, "order": _COMP_EVENT_ORDER[ev]})
            add_edge(graph, "event_type", ev, "pc_phase", phase_key, "IN_PHASE")

        for i in range(len(ordered) - 1):
            add_edge(graph, "event_type", ordered[i], "event_type", ordered[i + 1], "PRECEDES",
                     {"from_order": _COMP_EVENT_ORDER[ordered[i]],
                      "to_order": _COMP_EVENT_ORDER[ordered[i + 1]]})

        count = len(ordered)

        if not ptmetadata.has_table(env, "PSPCMPROG"):
            return count

        comp_names = sorted({
            n["name"] for n in graph["nodes"].values()
            if n.get("type") == "component" and n.get("name")
        })[:200]

        if not comp_names:
            return count

        for chunk_start in range(0, len(comp_names), 100):
            chunk = comp_names[chunk_start:chunk_start + 100]
            params = {f"c{i}": c.upper() for i, c in enumerate(chunk)}
            placeholders = ",".join(f":c{i}" for i in range(len(chunk)))
            try:
                rows = psdb.query(env, f"""
                    SELECT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2,
                           OBJECTVALUE3, OBJECTVALUE4, OBJECTVALUE5
                      FROM SYSADM.PSPCMPROG
                     WHERE OBJECTID1 IN (9, 10)
                       AND UPPER(OBJECTVALUE1) IN ({placeholders})
                """, params)
            except Exception:
                continue

            for r in rows:
                oid = r.get("objectid1")
                comp = (r.get("objectvalue1") or "").strip().upper()
                ov2 = (r.get("objectvalue2") or "").strip().upper()
                ov3 = (r.get("objectvalue3") or "").strip().upper()
                ov4 = (r.get("objectvalue4") or "").strip().upper()
                ov5 = (r.get("objectvalue5") or "").strip().upper()

                if oid == 9:
                    ev = ov2
                elif ov3 in ev_set:
                    ev = ov3
                elif not ov5:
                    ev = ov4
                else:
                    ev = ov5

                if ev in ev_set and comp:
                    add_edge(graph, "component", comp, "event_type", ev, "HAS_HANDLER",
                             {"component": comp, "event": ev})
                    count += 1

        return count

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

            refs = peoplecode.references_for_program(env, row)
            pc_reference = refs.get("reference") or reference
            pc_node_name = peoplecode.encode_reference(pc_reference)

            add_node(graph, "peoplecode", pc_node_name, pc_reference, row, rows.get("warnings", []))

            if row.get("parent_type") and row.get("parent_name"):
                add_node(graph, row["parent_type"], row["parent_name"], row["parent_name"], {})
                add_edge(
                    graph,
                    "peoplecode",
                    pc_node_name,
                    row["parent_type"],
                    row["parent_name"],
                    "BELONGS_TO",
                    row,
                )

            for record in refs["references"].get("records", []):
                add_node(graph, "record", record, record, {})
                add_edge(graph, "peoplecode", pc_node_name, "record", record, "REFERENCES")
            for field in refs["references"].get("fields", []):
                add_node(graph, "field", field, field, {})
                add_edge(graph, "peoplecode", pc_node_name, "field", field, "REFERENCES")
            for sql_name in refs["references"].get("sql_definitions", []):
                add_node(graph, "sql_definition", sql_name, sql_name, {})
                add_edge(graph, "peoplecode", pc_node_name, "sql_definition", sql_name, "USES")
            for statement in refs.get("literal_sql", []):
                access = sql_record_access(statement.get("sql_text", ""))
                edge_meta = {
                    "peoplecode_reference": pc_reference,
                    "call": statement.get("call"),
                    "source": "peoplecode_literal_sql",
                }
                for recname in access["reads"]:
                    add_node(graph, "record", recname, recname, edge_meta)
                    add_edge(graph, "peoplecode", pc_node_name, "record", recname, "READS", edge_meta)
                for recname in access["writes"]:
                    add_node(graph, "record", recname, recname, edge_meta)
                    add_edge(graph, "peoplecode", pc_node_name, "record", recname, "WRITES", edge_meta)
            for call in refs.get("calls", []):
                add_node(graph, "function", call.get("name"), call.get("name"), call)
                add_edge(graph, "peoplecode", pc_node_name, "function", call.get("name"), "CALLS", call)

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

            sql_text_map, sql_warnings = ae.ae_sql_step_text(env, applid)
            for warning in sql_warnings:
                if warning:
                    graph["warnings"].append(warning)
            for (section_name, step_name), statements in sql_text_map.items():
                for statement in statements:
                    access = sql_record_access(statement.get("sql_text", ""))
                    edge_meta = {
                        "ae_section": section_name,
                        "ae_step": step_name,
                        "stmt_type": statement.get("stmt_type"),
                        "source": "ae_sql_step_text",
                    }
                    for recname in access["reads"]:
                        add_node(graph, "record", recname, recname, edge_meta)
                        add_edge(graph, "application_engine", applid, "record", recname, "READS", edge_meta)
                    for recname in access["writes"]:
                        add_node(graph, "record", recname, recname, edge_meta)
                        add_edge(graph, "application_engine", applid, "record", recname, "WRITES", edge_meta)

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
        cols = psdb.table_columns(env, "PSTREEDEFN")
        name_col = "TREE_NAME" if "tree_name" in cols else "TREENAME"
        strct_col = "TREE_STRCT_ID" if "tree_strct_id" in cols else "TREESTRCTPNM"
        setid_col = "SETID" if "setid" in cols else "NULL AS SETID"
        setcntrl_col = "SETCNTRLVALUE" if "setcntrlvalue" in cols else "NULL AS SETCNTRLVALUE"
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        status_col = "EFF_STATUS" if "eff_status" in cols else "NULL AS EFF_STATUS"
        owner_col = "OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        leaf_col = "TREE_RECNAME" if "tree_recname" in cols else "NULL AS TREE_RECNAME"
        rows = psdb.query(env, f"""
            SELECT {name_col} AS TREENAME, {setid_col}, {setcntrl_col},
                   {strct_col} AS TREESTRCTPNM, {leaf_col}, {descr_col},
                   {status_col}, {owner_col}
              FROM SYSADM.PSTREEDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY {name_col}
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

        selected_text = {}
        selected_dbtype = {}
        sqlids = [str(r.get("sqlid") or "").strip().upper() for r in rows if r.get("sqlid")]
        if sqlids and ptmetadata.has_table(env, "PSSQLTEXTDEFN"):
            text_variants = defaultdict(lambda: defaultdict(list))
            for start in range(0, len(sqlids), 900):
                chunk = sqlids[start:start + 900]
                quoted = ",".join("'" + sqlid.replace("'", "''") + "'" for sqlid in chunk)
                text_rows = psdb.query(env, f"""
                    SELECT SQLID, SQLTYPE, DBTYPE, SEQNUM, SQLTEXT
                      FROM SYSADM.PSSQLTEXTDEFN
                     WHERE SQLTYPE = 0
                       AND SQLID IN ({quoted})
                       AND DBTYPE IN (' ', '7')
                     ORDER BY SQLID, DBTYPE, SEQNUM
                """) or []
                for text_row in text_rows:
                    sqlid = str(text_row.get("sqlid") or "").strip().upper()
                    dbtype = str(text_row.get("dbtype") or " ").strip() or " "
                    sqltext = text_row.get("sqltext")
                    if sqlid and sqltext:
                        text_variants[sqlid][dbtype].append(str(sqltext))

            for sqlid, variants in text_variants.items():
                # Prefer Oracle-specific SQL when present; fall back to generic PeopleTools SQL.
                dbtype = "7" if variants.get("7") else " "
                selected_text[sqlid] = "\n".join(variants.get(dbtype) or [])
                selected_dbtype[sqlid] = dbtype

        for r in rows:
            sqlid = r.get("sqlid")
            if sqlid:
                add_node(graph, "sql_definition", sqlid, sqlid, r)
                sql_key = str(sqlid).strip().upper()
                access = sql_record_access(selected_text.get(sql_key, ""))
                edge_meta = {
                    "sqlid": sql_key,
                    "sqltype": r.get("sqltype"),
                    "dbtype": selected_dbtype.get(sql_key),
                    "source": "pssqltextdefn",
                }
                for recname in access["reads"]:
                    add_node(graph, "record", recname, recname, edge_meta)
                    add_edge(graph, "sql_definition", sqlid, "record", recname, "READS", edge_meta)
                for recname in access["writes"]:
                    add_node(graph, "record", recname, recname, edge_meta)
                    add_edge(graph, "sql_definition", sqlid, "record", recname, "WRITES", edge_meta)
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
        query_names = [str(r.get("qryname") or "").strip().upper() for r in rows if r.get("qryname")]
        records_by_query = defaultdict(list)
        record_by_number = {}
        fields_by_query = defaultdict(list)
        if query_names and ptmetadata.has_table(env, "PSQRYRECORD"):
            for start in range(0, len(query_names), 900):
                chunk = query_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                rec_rows = psdb.query(env, f"""
                    SELECT QRYNAME, RCDNUM, RECNAME, CORRNAME, JOINTYPE
                      FROM SYSADM.PSQRYRECORD
                     WHERE OPRID = ' '
                       AND QRYNAME IN ({quoted})
                     ORDER BY QRYNAME, RCDNUM
                """) or []
                for rec in rec_rows:
                    qn = str(rec.get("qryname") or "").strip().upper()
                    rcdnum = rec.get("rcdnum")
                    recname = str(rec.get("recname") or "").strip().upper()
                    if not qn or not recname:
                        continue
                    records_by_query[qn].append(rec)
                    record_by_number[(qn, str(rcdnum))] = recname

        if query_names and ptmetadata.has_table(env, "PSQRYFIELD"):
            for start in range(0, len(query_names), 900):
                chunk = query_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                field_rows = psdb.query(env, f"""
                    SELECT QRYNAME, FLDNUM, FIELDNAME, RECNAME, FLDRCDNUM,
                           COLUMNNUM, HEADING, AGGREGATEFUNC
                      FROM SYSADM.PSQRYFIELD
                     WHERE OPRID = ' '
                       AND QRYNAME IN ({quoted})
                       AND NVL(COLUMNNUM, 0) > 0
                     ORDER BY QRYNAME, COLUMNNUM, FLDNUM
                """) or []
                for field in field_rows:
                    qn = str(field.get("qryname") or "").strip().upper()
                    fieldname = str(field.get("fieldname") or "").strip().upper()
                    if qn and fieldname:
                        fields_by_query[qn].append(field)

        for r in rows:
            qn = r.get("qryname")
            if qn:
                add_node(graph, "query", qn, r.get("descr") or qn, r)
                qn_key = str(qn).strip().upper()
                for rec in records_by_query.get(qn_key, []):
                    recname = str(rec.get("recname") or "").strip().upper()
                    add_node(graph, "record", recname, recname, rec)
                    add_edge(graph, "query", qn, "record", recname, "USES", rec)
                for field in fields_by_query.get(qn_key, []):
                    fieldname = str(field.get("fieldname") or "").strip().upper()
                    recname = str(field.get("recname") or "").strip().upper()
                    if not recname:
                        recname = record_by_number.get((qn_key, str(field.get("fldrcdnum"))), "")
                    field_ref = f"{recname}.{fieldname}" if recname else fieldname
                    metadata = {**field, "recname_resolved": recname}
                    add_node(graph, "field", field_ref, field_ref, metadata)
                    add_edge(graph, "query", qn, "field", field_ref, "EXPOSES", metadata)
                    if recname:
                        add_node(graph, "record", recname, recname, metadata)
                        add_edge(graph, "record", recname, "field", field_ref, "CONTAINS", metadata)
        return len(rows)

    def component_interfaces():
        if not ptmetadata.has_table(env, "PSBCDEFN"):
            return 0
        cols = psdb.table_columns(env, "PSBCDEFN")
        descr_col = "b.DESCR" if "descr" in cols else "NULL AS DESCR"
        version_col = "b.VERSION" if "version" in cols else "NULL AS VERSION"
        type_col = "b.BCTYPE" if "bctype" in cols else "NULL AS BCTYPE"
        if "bcpgname" in cols:
            component_col = "b.BCPGNAME"
        elif "pnlgrpname" in cols:
            component_col = "b.PNLGRPNAME"
        else:
            component_col = "NULL"
        owner_col = "b.OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        ts_col = "b.LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        rows = psdb.query(env, f"""
            SELECT b.BCNAME, {descr_col}, {version_col}, {type_col},
                   {component_col} AS component, {owner_col}, {ts_col}
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
        cols = psdb.table_columns(env, "PSMSGCATDEFN")
        if "severity" in cols:
            severity_expr = "SEVERITY AS SEVERITY"
        elif "msg_severity" in cols:
            severity_expr = "MSG_SEVERITY AS SEVERITY"
        else:
            severity_expr = "NULL AS SEVERITY"
        rows = psdb.query(env, f"""
            SELECT MESSAGE_SET_NBR, MESSAGE_NBR, {severity_expr}, MESSAGE_TEXT
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
            SELECT REPORT_DEFN_ID, DESCR, OBJECTOWNERID, DS_ID, DS_TYPE
              FROM SYSADM.PSXPRPTDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY REPORT_DEFN_ID
        """) or []
        for r in rows:
            rid = r.get("report_defn_id")
            if not rid:
                continue
            add_node(graph, "xml_publisher_report", rid, r.get("descr") or rid, r)
            ds_id = str(r.get("ds_id") or "").strip().upper()
            ds_type = str(r.get("ds_type") or "").strip().upper()
            if ds_id and ds_type == "QRY":
                add_node(graph, "query", ds_id, ds_id, r)
                add_edge(graph, "xml_publisher_report", rid, "query", ds_id, "USES", r)
            elif ds_id and ds_type == "CQR":
                add_node(graph, "connected_query", ds_id, ds_id, r)
                add_edge(graph, "xml_publisher_report", rid, "connected_query", ds_id, "USES", r)
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
        conqrs_names = [str(r.get("conqrsname") or "").strip().upper() for r in rows if r.get("conqrsname")]
        maps_by_conqrs = defaultdict(list)
        if conqrs_names and ptmetadata.has_table(env, "PSCONQRSMAP"):
            for start in range(0, len(conqrs_names), 900):
                chunk = conqrs_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                map_rows = psdb.query(env, f"""
                    SELECT CONQRSNAME, SEQNUM, QRYNAMEPARENT, QRYNAMECHILD,
                           EFFDTCONDTYPE, CQ_SUPPORTSORDERBY, RECNAME
                      FROM SYSADM.PSCONQRSMAP
                     WHERE CONQRSNAME IN ({quoted})
                     ORDER BY CONQRSNAME, SEQNUM
                """) or []
                for item in map_rows:
                    cq = str(item.get("conqrsname") or "").strip().upper()
                    if cq:
                        maps_by_conqrs[cq].append(item)
        for r in rows:
            cid = r.get("conqrsname")
            if not cid:
                continue
            add_node(graph, "connected_query", cid, r.get("descr") or cid, r)
            cq_key = str(cid).strip().upper()
            for item in maps_by_conqrs.get(cq_key, []):
                child = str(item.get("qrynamechild") or "").strip()
                parent = str(item.get("qrynameparent") or "").strip()
                if child:
                    add_node(graph, "query", child, child, item)
                    add_edge(graph, "connected_query", cid, "query", child, "USES", item)
                if parent and child:
                    add_node(graph, "query", parent, parent, item)
                    add_edge(graph, "query", parent, "query", child, "CONTAINS", item)
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
        test_names = [str(r.get("pttst_name") or "").strip().upper() for r in rows if r.get("pttst_name")]
        commands_by_test = defaultdict(list)
        if test_names and ptmetadata.has_table(env, "PSPTTSTCOMMAND"):
            for start_idx in range(0, len(test_names), 900):
                chunk = test_names[start_idx:start_idx + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                cmd_rows = psdb.query(env, f"""
                    SELECT PTTST_NAME, SEQNBR, PTTST_CMD_ID, PTTST_CMD_TYPE,
                           PTTST_CMD_OBJ_ID, MENUNAME, PNLGRPNAME, PNLNAME,
                           PTTST_PAGEFIELD_NM, RECNAME, FIELDNAME
                      FROM SYSADM.PSPTTSTCOMMAND
                     WHERE PTTST_NAME IN ({quoted}) AND PTTST_LANG_CD IN (' ', 'ENG')
                     ORDER BY PTTST_NAME, SEQNBR
                """) or []
                for item in cmd_rows:
                    test_name = str(item.get("pttst_name") or "").strip().upper()
                    if test_name:
                        commands_by_test[test_name].append(item)
        for r in rows:
            tid = r.get("pttst_name")
            if not tid:
                continue
            label = (r.get("descr") or "").strip() or tid
            add_node(graph, "ptf_test", tid, label, r)
            seen = set()
            for cmd in commands_by_test.get(str(tid).strip().upper(), []):
                metadata = dict(cmd)
                targets = [
                    ("menu", str(cmd.get("menuname") or "").strip().upper()),
                    ("component", str(cmd.get("pnlgrpname") or "").strip().upper()),
                    ("page", str(cmd.get("pnlname") or "").strip().upper()),
                    ("record", str(cmd.get("recname") or "").strip().upper()),
                ]
                recname = str(cmd.get("recname") or "").strip().upper()
                fieldname = str(cmd.get("fieldname") or "").strip().upper()
                if recname and fieldname:
                    targets.append(("field", f"{recname}.{fieldname}"))
                for target_type, target_name in targets:
                    if not target_name:
                        continue
                    edge_key = (target_type, target_name)
                    if edge_key in seen:
                        continue
                    seen.add(edge_key)
                    add_node(graph, target_type, target_name, target_name, metadata)
                    add_edge(graph, "ptf_test", tid, target_type, target_name, "USES", metadata)
        return len(rows)

    def content_services():
        if not ptmetadata.has_table(env, "PSPTCSSRVDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PTCS_SERVICEID, PTCS_SERVICENAME, DESCR254,
                   PTCS_SERVICEURLTYP, OBJECTOWNERID,
                   PORTAL_MENUNAME, PNLGRPNAME, PTCS_QUERYNAME,
                   PACKAGEROOT, QUALIFYPATH, APPCLASSID
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
            menu = str(r.get("portal_menuname") or "").strip()
            component = str(r.get("pnlgrpname") or "").strip()
            query_name = str(r.get("ptcs_queryname") or "").strip()
            pkg = str(r.get("packageroot") or "").strip()
            qp = str(r.get("qualifypath") or "").strip() or ":"
            cid = str(r.get("appclassid") or "").strip()
            if component:
                add_node(graph, "component", component, component, r)
                add_edge(graph, "content_service", sid, "component", component, "USES", r)
            if menu:
                add_node(graph, "menu", menu, menu, r)
                add_edge(graph, "content_service", sid, "menu", menu, "USES", r)
            if query_name:
                add_node(graph, "query", query_name, query_name, r)
                add_edge(graph, "content_service", sid, "query", query_name, "USES", r)
            if pkg and cid:
                class_key = f"{pkg}~{qp}~{cid}"
                label = f"{pkg}:{cid}" if qp == ":" else f"{pkg}:{qp}:{cid}"
                add_node(graph, "app_class", class_key, label, r)
                add_edge(graph, "content_service", sid, "app_class", class_key, "USES", r)
        return len(rows)

    def app_packages():
        if not ptmetadata.has_table(env, "PSPACKAGEDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PACKAGEROOT, DESCR, VERSION, OBJECTOWNERID
              FROM SYSADM.PSPACKAGEDEFN
             WHERE PACKAGELEVEL = 0
               AND ROWNUM <= {limit}
             ORDER BY PACKAGEROOT
        """) or []
        package_names = [str(r.get("packageroot") or "").strip().upper() for r in rows if r.get("packageroot")]
        classes_by_package = defaultdict(list)
        peoplecode_by_package = defaultdict(list)
        if package_names and ptmetadata.has_table(env, "PSAPPCLASSDEFN"):
            for start in range(0, len(package_names), 900):
                chunk = package_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                cls_rows = psdb.query(env, f"""
                    SELECT PACKAGEROOT, QUALIFYPATH, APPCLASSID, APPCLASSREF
                      FROM SYSADM.PSAPPCLASSDEFN
                     WHERE PACKAGEROOT IN ({quoted})
                     ORDER BY PACKAGEROOT, QUALIFYPATH, APPCLASSID
                """) or []
                for cls in cls_rows:
                    pkg = str(cls.get("packageroot") or "").strip().upper()
                    if pkg:
                        classes_by_package[pkg].append(cls)
        if package_names and ptmetadata.has_table(env, "PSPCMPROG"):
            for start in range(0, len(package_names), 900):
                chunk = package_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                pc_rows = psdb.query(env, f"""
                    SELECT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                           OBJECTVALUE4, OBJECTVALUE5, PROGSEQ
                      FROM SYSADM.PSPCMPROG
                     WHERE OBJECTID1 = 104
                       AND OBJECTVALUE1 IN ({quoted})
                     ORDER BY OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                              OBJECTVALUE4, PROGSEQ
                """) or []
                for pc in pc_rows:
                    pkg = str(pc.get("objectvalue1") or "").strip().upper()
                    if pkg:
                        peoplecode_by_package[pkg].append(pc)

        for r in rows:
            pkg = str(r.get("packageroot") or "").strip().upper()
            if not pkg:
                continue
            add_node(graph, "application_package", pkg, r.get("descr") or pkg, r)
            for cls in classes_by_package.get(pkg, []):
                qpath = str(cls.get("qualifypath") or "").strip() or ":"
                classid = str(cls.get("appclassid") or "").strip()
                if not classid:
                    continue
                key = f"{pkg}~{qpath}~{classid}"
                label = f"{pkg}:{classid}" if qpath == ":" else f"{pkg}:{qpath}:{classid}"
                metadata = {**cls, "packageroot": pkg}
                add_node(graph, "app_class", key, label, metadata)
                add_edge(graph, "application_package", pkg, "app_class", key, "CONTAINS", metadata)
            for pc in peoplecode_by_package.get(pkg, []):
                parts = [
                    str(pc.get(f"objectvalue{i}") or "").strip()
                    for i in range(2, 6)
                    if str(pc.get(f"objectvalue{i}") or "").strip()
                ]
                if len(parts) < 2:
                    continue
                class_name = parts[-2]
                sub_path = ":".join(parts[:-2]) if len(parts) > 2 else ":"
                class_key = f"{pkg}~{sub_path or ':'}~{class_name}"
                reference = peoplecode.reference_from_row(pc)
                if not reference:
                    continue
                pc_node_name = peoplecode.encode_reference(reference)
                metadata = {**pc, "app_class_key": class_key, "peoplecode_reference": reference}
                add_node(graph, "peoplecode", pc_node_name, reference, metadata)
                add_edge(graph, "app_class", class_key, "peoplecode", pc_node_name, "CONTAINS", metadata)
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

    def pm_transactions():
        if not ptmetadata.has_table(env, "PSPMTRANSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT t.PM_TRANS_DEFN_ID, t.PM_TRANS_LABEL, t.PM_FILTER_LEVEL
              FROM SYSADM.PSPMTRANSDEFN t
             WHERE ROWNUM <= {limit}
             ORDER BY t.PM_TRANS_DEFN_ID
        """) or []
        for r in rows:
            tid = r.get("pm_trans_defn_id")
            if tid is None:
                continue
            label = (r.get("pm_trans_label") or "").strip() or str(tid)
            add_node(graph, "pm_transaction", str(tid), label, r)
        return len(rows)

    def pm_events():
        if not ptmetadata.has_table(env, "PSPMEVENTDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT e.PM_EVENT_DEFN_ID, e.PM_EVENT_LABEL, e.PM_FILTER_LEVEL
              FROM SYSADM.PSPMEVENTDEFN e
             WHERE ROWNUM <= {limit}
             ORDER BY e.PM_EVENT_DEFN_ID
        """) or []
        for r in rows:
            eid = r.get("pm_event_defn_id")
            if eid is None:
                continue
            label = (r.get("pm_event_label") or "").strip() or str(eid)
            add_node(graph, "pm_event", str(eid), label, r)
        return len(rows)


    def ib_operations():
        if not ptmetadata.has_table(env, "PSOPERATION"):
            return 0
        rows = psdb.query(env, f"""
            SELECT IB_OPERATIONNAME, IB_SERVICENAME, RTNGTYPE, DESCR
              FROM SYSADM.PSOPERATION
             WHERE ROWNUM <= {limit}
             ORDER BY IB_OPERATIONNAME
        """) or []
        for r in rows:
            oname = r.get("ib_operationname")
            if not oname:
                continue
            label = (r.get("descr") or "").strip() or oname
            add_node(graph, "ib_operation", oname, label, r)
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
        ads_names = [str(r.get("ptadsname") or "").strip().upper() for r in rows if r.get("ptadsname")]
        records_by_ads = defaultdict(list)
        if ads_names and ptmetadata.has_table(env, "PSADSDEFNITEM"):
            for start_idx in range(0, len(ads_names), 900):
                chunk = ads_names[start_idx:start_idx + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                item_rows = psdb.query(env, f"""
                    SELECT PTADSNAME, RECNAME, PTPARENTRECNAME, PTPEERORDER
                      FROM SYSADM.PSADSDEFNITEM
                     WHERE PTADSNAME IN ({quoted})
                     ORDER BY PTADSNAME, PTPARENTRECNAME, RECNAME
                """) or []
                for item in item_rows:
                    ads_name = str(item.get("ptadsname") or "").strip().upper()
                    recname = str(item.get("recname") or "").strip().upper()
                    if ads_name and recname:
                        records_by_ads[ads_name].append({**item, "recname": recname})
        for r in rows:
            ads_name = r.get("ptadsname")
            if not ads_name:
                continue
            label = (r.get("descr") or "").strip() or ads_name
            add_node(graph, "ads_definition", ads_name, label, r)
            seen_records = set()
            for item in records_by_ads.get(str(ads_name).strip().upper(), []):
                recname = str(item.get("recname") or "").strip().upper()
                parent = str(item.get("ptparentrecname") or "").strip().upper()
                if not recname:
                    continue
                if recname not in seen_records:
                    seen_records.add(recname)
                    add_node(graph, "record", recname, recname, item)
                    add_edge(graph, "ads_definition", ads_name, "record", recname, "CONTAINS", item)
                if parent:
                    add_node(graph, "record", parent, parent, item)
                    add_edge(graph, "record", parent, "record", recname, "CONTAINS", item)
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
            SELECT MSGNAME, DESCR, CHNLNAME, DEFAULTVER, MSGSTATUS, OBJECTOWNERID
              FROM SYSADM.PSMSGDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY MSGNAME
        """) or []
        records_by_message = defaultdict(list)
        message_keys = [
            (str(r.get("msgname") or "").strip().upper(), str(r.get("defaultver") or "").strip())
            for r in rows
            if r.get("msgname") and str(r.get("defaultver") or "").strip()
        ]
        if message_keys and ptmetadata.has_table(env, "PSMSGREC"):
            clauses = []
            params = {}
            for idx, (msgname, version) in enumerate(message_keys[:900]):
                clauses.append(f"(MSGNAME = :msg{idx} AND APMSGVER = :ver{idx})")
                params[f"msg{idx}"] = msgname
                params[f"ver{idx}"] = version
            rec_rows = psdb.query(env, f"""
                SELECT MSGNAME, APMSGVER, RECNAME, PRNTRECNAME, SEQNO, XMLALIAS
                  FROM SYSADM.PSMSGREC
                 WHERE ({' OR '.join(clauses)})
                 ORDER BY MSGNAME, APMSGVER, SEQNO, RECNAME
            """, params) or []
            for rec in rec_rows:
                msgname = str(rec.get("msgname") or "").strip().upper()
                recname = str(rec.get("recname") or "").strip().upper()
                if msgname and recname:
                    records_by_message[msgname].append({**rec, "recname": recname})
        for r in rows:
            mid = r.get("msgname")
            if not mid:
                continue
            add_node(graph, "message", mid, r.get("descr") or mid, r)
            seen_records = set()
            for rec in records_by_message.get(str(mid).strip().upper(), []):
                recname = str(rec.get("recname") or "").strip().upper()
                parent = str(rec.get("prntrecname") or "").strip().upper()
                if not recname:
                    continue
                if recname not in seen_records:
                    seen_records.add(recname)
                    add_node(graph, "record", recname, recname, rec)
                    add_edge(graph, "message", mid, "record", recname, "CONTAINS", rec)
                if parent and parent != "--":
                    add_node(graph, "record", parent, parent, rec)
                    add_edge(graph, "record", parent, "record", recname, "CONTAINS", rec)
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
        project_names = [str(r.get("projectname") or "").strip().upper() for r in rows if r.get("projectname")]
        items_by_project = defaultdict(list)
        if project_names and ptmetadata.has_table(env, "PSPROJECTITEM"):
            for start in range(0, len(project_names), 900):
                chunk = project_names[start:start + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                item_rows = psdb.query(env, f"""
                    SELECT PROJECTNAME, OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2,
                           OBJECTVALUE3, OBJECTVALUE4, SOURCESTATUS, TARGETSTATUS,
                           UPGRADEACTION
                      FROM SYSADM.PSPROJECTITEM
                     WHERE PROJECTNAME IN ({quoted})
                     ORDER BY PROJECTNAME, OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2
                """) or []
                for item in item_rows:
                    project = str(item.get("projectname") or "").strip().upper()
                    if project:
                        items_by_project[project].append(item)

        for r in rows:
            pid = r.get("projectname")
            if not pid:
                continue
            add_node(graph, "project", pid, r.get("projectdescr") or pid, r)
            for item in items_by_project.get(str(pid).strip().upper(), []):
                target = psdb.project_item_target(item)
                if not target:
                    continue
                metadata = {
                    **item,
                    "projectname": str(pid).strip().upper(),
                    "objecttype_label": target.get("label"),
                    "source": "psprojectitem",
                }
                add_node(graph, target["type"], target["name"], target["name"], metadata)
                add_edge(graph, "project", pid, target["type"], target["name"], "DEPLOYS", metadata)
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
        layout_names = [str(r.get("flddefnname") or "").strip().upper() for r in rows if r.get("flddefnname")]
        segments_by_layout = defaultdict(list)
        fields_by_layout = defaultdict(list)
        if layout_names and ptmetadata.has_table(env, "PSFLDSEGDEFN"):
            for start_idx in range(0, len(layout_names), 900):
                chunk = layout_names[start_idx:start_idx + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                seg_rows = psdb.query(env, f"""
                    SELECT FLDDEFNNAME, FLDSEGNAME, FLDSEGID, FLDSEGPARENT,
                           FLDSEQNO, FLDFIELDCOUNT, RECNAME_FILE
                      FROM SYSADM.PSFLDSEGDEFN
                     WHERE FLDDEFNNAME IN ({quoted})
                     ORDER BY FLDDEFNNAME, FLDSEQNO, FLDSEGNAME
                """) or []
                for seg in seg_rows:
                    layout = str(seg.get("flddefnname") or "").strip().upper()
                    segment = str(seg.get("fldsegname") or "").strip().upper()
                    recname_file = str(seg.get("recname_file") or "").strip().upper()
                    record_name = recname_file or segment
                    if layout and record_name:
                        segments_by_layout[layout].append({**seg, "record_name": record_name})
        if layout_names and ptmetadata.has_table(env, "PSFLDFIELDDEFN"):
            for start_idx in range(0, len(layout_names), 900):
                chunk = layout_names[start_idx:start_idx + 900]
                quoted = ",".join("'" + name.replace("'", "''") + "'" for name in chunk)
                field_rows = psdb.query(env, f"""
                    SELECT FLDDEFNNAME, FLDSEGNAME, FLDFIELDNAME, FLDSEQNO,
                           FLDSTART, FLDLENGTH, FLDFIELDTYPE, DESCR100, FLDTAG
                      FROM SYSADM.PSFLDFIELDDEFN
                     WHERE FLDDEFNNAME IN ({quoted})
                     ORDER BY FLDDEFNNAME, FLDSEGNAME, FLDSEQNO
                """) or []
                for field in field_rows:
                    layout = str(field.get("flddefnname") or "").strip().upper()
                    segment = str(field.get("fldsegname") or "").strip().upper()
                    field_name = str(field.get("fldfieldname") or "").strip().upper()
                    if layout and segment and field_name:
                        fields_by_layout[layout].append({
                            **field,
                            "record_name": segment,
                            "field_ref": f"{segment}.{field_name}",
                        })
        for r in rows:
            fid = r.get("flddefnname")
            if not fid:
                continue
            add_node(graph, "file_layout", fid, r.get("descr") or fid, r)
            layout = str(fid).strip().upper()
            seen_records = set()
            for seg in segments_by_layout.get(layout, []):
                record_name = str(seg.get("record_name") or "").strip().upper()
                if not record_name or record_name in seen_records:
                    continue
                seen_records.add(record_name)
                add_node(graph, "record", record_name, record_name, seg)
                add_edge(graph, "file_layout", fid, "record", record_name, "CONTAINS", seg)
            seen_fields = set()
            for field in fields_by_layout.get(layout, []):
                record_name = str(field.get("record_name") or "").strip().upper()
                field_ref = str(field.get("field_ref") or "").strip().upper()
                if not record_name or not field_ref or field_ref in seen_fields:
                    continue
                seen_fields.add(field_ref)
                add_node(graph, "record", record_name, record_name, field)
                add_node(graph, "field", field_ref, field_ref, field)
                add_edge(graph, "file_layout", fid, "field", field_ref, "CONTAINS", field)
                add_edge(graph, "record", record_name, "field", field_ref, "CONTAINS", field)
        return len(rows)

    def sqr_programs():
        """Add SQR/SQC source artifact nodes with table-access and include edges."""
        try:
            from connectors import sqrdb as _sqrdb
            _sqrdb.init_db()
        except Exception:
            return 0

        added = 0
        page = 1
        per_page = 500
        while True:
            result = _sqrdb.search_programs(page=page, per_page=per_page)
            rows = result.get("results", [])
            if not rows:
                break

            for row in rows:
                filename = row.get("filename")
                if not filename:
                    continue
                node_name = filename.lower()
                add_node(graph, "sqr_program", node_name,
                         row.get("program_name") or node_name,
                         {**row, "_links": {"admin": f"/admin/sqr/{filename}"}})
                added += 1

                # Fetch full detail for edges (tables + includes)
                detail = _sqrdb.get_program(filename)
                if not detail:
                    continue

                for tbl in detail.get("tables", []):
                    tbl_name = (tbl.get("table_name") or "").strip().upper()
                    if not tbl_name:
                        continue
                    ops = tbl.get("operations") or ""
                    add_node(graph, "record", tbl_name, tbl_name,
                             {"source": "sqr_program", "sqr_program": node_name})
                    # Classify as read vs write based on operations
                    if any(o in ops for o in ("UPDATE", "INSERT", "DELETE", "CREATE")):
                        add_edge(graph, "sqr_program", node_name, "record", tbl_name, "WRITES",
                                 {"operations": ops})
                    else:
                        add_edge(graph, "sqr_program", node_name, "record", tbl_name, "READS",
                                 {"operations": ops})

                for inc in detail.get("includes", []):
                    inc_name = (inc or "").strip().lower()
                    if not inc_name:
                        continue
                    add_node(graph, "sqr_program", inc_name, inc_name.upper(), {})
                    add_edge(graph, "sqr_program", node_name, "sqr_program", inc_name, "INCLUDES",
                             {"include_file": inc_name})

            if len(rows) < per_page:
                break
            page += 1

        return added

    def process_definitions():
        if not ptmetadata.has_table(env, "PS_PRCSDEFN"):
            return 0
        rows = psdb.query(env, f"""
            SELECT PRCSTYPE, PRCSNAME, DESCR, PRCSCATEGORY
              FROM SYSADM.PS_PRCSDEFN
             WHERE ROWNUM <= {limit}
             ORDER BY PRCSTYPE, PRCSNAME
        """) or []
        keys = [
            (str(r.get("prcstype") or "").strip(), str(r.get("prcsname") or "").strip().upper())
            for r in rows
            if r.get("prcsname")
        ]
        components_by_key = defaultdict(list)
        if keys and ptmetadata.has_table(env, "PS_PRCSDEFNPNL"):
            clauses = []
            params = {}
            for idx, (ptype, pname) in enumerate(keys[:900]):
                clauses.append(f"(PRCSTYPE = :pt{idx} AND PRCSNAME = :pn{idx})")
                params[f"pt{idx}"] = ptype
                params[f"pn{idx}"] = pname
            pnl_rows = psdb.query(env, f"""
                SELECT PRCSTYPE, PRCSNAME, PNLGRPNAME
                  FROM SYSADM.PS_PRCSDEFNPNL
                 WHERE ({' OR '.join(clauses)})
                   AND TRIM(PNLGRPNAME) IS NOT NULL
                 ORDER BY PRCSTYPE, PRCSNAME, PNLGRPNAME
            """, params) or []
            for pnl in pnl_rows:
                ptype = str(pnl.get("prcstype") or "").strip()
                pname = str(pnl.get("prcsname") or "").strip().upper()
                component = str(pnl.get("pnlgrpname") or "").strip().upper()
                if component:
                    components_by_key[(ptype, pname)].append({**pnl, "component": component})
        for r in rows:
            pname = r.get("prcsname")
            ptype = r.get("prcstype", "")
            if not pname:
                continue
            key = f"{ptype}~{pname}"
            add_node(graph, "prcs_defn", key, r.get("descr") or pname, r)
            ptype_clean = str(ptype or "").strip()
            pname_clean = str(pname or "").strip().upper()
            if ptype_clean == "Application Engine":
                add_node(graph, "application_engine", pname_clean, pname_clean, r)
                add_edge(graph, "prcs_defn", key, "application_engine", pname_clean, "WRAPS", r)
            elif ptype_clean == "XML Publisher":
                add_node(graph, "xml_publisher_report", pname_clean, pname_clean, r)
                add_edge(graph, "prcs_defn", key, "xml_publisher_report", pname_clean, "WRAPS", r)
            elif ptype_clean in ("SQR Report", "SQR Process"):
                # Link to sqr_program node using lowercase filename convention
                sqr_node = f"{pname_clean.lower()}.sqr"
                add_node(graph, "sqr_program", sqr_node, pname_clean, r)
                add_edge(graph, "prcs_defn", key, "sqr_program", sqr_node, "WRAPS", r)
            seen_components = set()
            for pnl in components_by_key.get((ptype_clean, pname_clean), []):
                component = pnl.get("component")
                if not component or component in seen_components:
                    continue
                seen_components.add(component)
                add_node(graph, "component", component, component, pnl)
                add_edge(graph, "prcs_defn", key, "component", component, "USES", pnl)
        return len(rows)

    for name, loader in (
        ("operators", operators),
        ("roles", roles),
        ("permissionlists", permissionlists),
        ("components", components),
        ("component_peoplecode", component_peoplecode),
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
        ("sqr_programs", sqr_programs),
        ("ib_applications", ib_applications),
        ("app_packages", app_packages),
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
        ("pm_transactions", pm_transactions),
        ("pm_events", pm_events),
        ("ib_operations", ib_operations),
    ):
        provider(graph, name, loader)

    graph["built_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    graph["build_seconds"] = round(time.time() - start, 3)
    normalize_graph_shape(graph)
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
        "_source": graph.get("_source", GRAPH_SOURCE),
        "_vocabulary": graph.get("_vocabulary", GRAPH_VOCABULARY),
        "_semantics": graph.get("_semantics", GRAPH_SEMANTICS),
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


def search(env="HCM", q="", limit=50, node_types=None):
    """Search knowledge graph nodes by free text with optional type filter.

    Args:
        env: Environment name (e.g. "HCM").
        q: Search string (case-insensitive substring match across id/name/metadata).
        limit: Maximum results (1–200).
        node_types: Optional comma-separated list of node types to restrict the
            search to, e.g. "component,record".  When omitted or empty, all types
            are searched.
    """
    graph = current(env)
    q = q.upper()
    limit = max(1, min(int(limit), 200))

    # Build an allow-set for type filtering (None = no filter)
    allow_types = None
    if node_types:
        allow_types = {t.strip().lower() for t in str(node_types).split(",") if t.strip()}

    rows = []
    for node in graph["nodes"].values():
        if allow_types and node.get("type", "").lower() not in allow_types:
            continue
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
