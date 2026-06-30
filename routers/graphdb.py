from fastapi import APIRouter, HTTPException, Response

from connectors import graphdb, scheduler

router = APIRouter(prefix="/api/graph", tags=["DeathStar Knowledge Graph"])


@router.get("/build")
def graph_build(env: str = "HCM", limit: int = 50, persist: bool = True):
    return graphdb.build(env, limit, persist)


@router.get("/stats")
def graph_stats(env: str = "HCM"):
    return graphdb.stats(env)


@router.post("/snapshots")
def graph_snapshot_create(env: str = "HCM", name: str = "", note: str = ""):
    return graphdb.create_snapshot(env, name=name, note=note)


@router.get("/snapshots")
def graph_snapshot_list(env: str = ""):
    return graphdb.list_snapshots(env or None)


@router.get("/snapshots/schedule")
def graph_snapshot_schedule():
    """Return scheduler status and configuration."""
    return scheduler.status()


@router.post("/snapshots/prune")
def graph_snapshot_prune(env: str = "", keep: int = 7):
    """Manually trigger snapshot retention pruning."""
    return graphdb.prune_snapshots(env or None, keep=keep)


@router.get("/snapshots/{snapshot_id}")
def graph_snapshot_get(snapshot_id: str):
    try:
        return graphdb.load_snapshot(snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/snapshots/{snapshot_id}")
def graph_snapshot_delete(snapshot_id: str):
    try:
        return graphdb.delete_snapshot(snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/clear")
def graph_clear(env: str = "HCM"):
    return graphdb.clear(env)


@router.post("/compact")
def graph_compact(env: str = "HCM"):
    """Deduplicate edges and rebuild the O(1) edge index. Persists the result."""
    return graphdb.compact(env)


@router.get("/node/{node_id}")
def graph_node(node_id: str, env: str = "HCM"):
    node = graphdb.get_node(env, node_id)

    if not node:
        raise HTTPException(status_code=404, detail="Graph node not found")

    return node


@router.get("/neighbors/{node_id}")
def graph_neighbors(node_id: str, env: str = "HCM", direction: str = "both", depth: int = 1, edge_types: str = ""):
    return graphdb.neighbors(env, node_id, direction, depth, edge_types)


@router.get("/path")
def graph_path(source: str, target: str, env: str = "HCM", edge_types: str = ""):
    edge_type_set = {item.strip().upper() for item in edge_types.split(",") if item.strip()} if edge_types else None
    return graphdb.shortest_path(env, source, target, edge_type_set)


@router.get("/dependencies/{node_id}")
def graph_dependencies(node_id: str, env: str = "HCM", depth: int = 3):
    return graphdb.dependency_tree(env, node_id, reverse=False, depth=depth)


@router.get("/reverse-dependencies/{node_id}")
def graph_reverse_dependencies(node_id: str, env: str = "HCM", depth: int = 3):
    return graphdb.dependency_tree(env, node_id, reverse=True, depth=depth)


@router.get("/impact/{node_id}")
def graph_impact(node_id: str, env: str = "HCM", depth: int = 3):
    """Combined impact analysis: what this node depends on + what depends on it."""
    return graphdb.impact(env, node_id, depth=depth)


@router.get("/search")
def graph_search(env: str = "HCM", q: str = "", limit: int = 50):
    if not q.strip():
        return []

    return graphdb.search(env, q, limit)


@router.get("/export")
def graph_export(env: str = "HCM", format: str = "json"):
    format = format.lower()

    if format == "json":
        return graphdb.export_json(env)

    if format == "dot":
        return Response(graphdb.export_dot(env), media_type="text/vnd.graphviz")

    if format == "graphml":
        return Response(graphdb.export_graphml(env), media_type="application/graphml+xml")

    raise HTTPException(status_code=400, detail="Unsupported graph export format")


@router.get("/components")
def graph_components(env: str = "HCM"):
    groups = graphdb.connected_components(env)
    return {
        "component_count": len(groups),
        "components": [
            {"size": len(group), "nodes": group[:100]}
            for group in groups[:100]
        ],
    }


@router.get("/cycles")
def graph_cycles(env: str = "HCM"):
    found = graphdb.cycles(env)
    return {
        "cycle_count": len(found),
        "cycles": found,
    }


@router.get("/topological-order")
def graph_topological_order(env: str = "HCM"):
    return graphdb.topological_order(env)


@router.get("/diff")
def graph_diff(env1: str = "HCM", env2: str = "FSCM", node_types: str = "", limit: int = 200):
    return graphdb.diff(env1, env2, node_types=node_types, limit=limit)


@router.get("/snapshot-diff")
def graph_snapshot_diff(snapshot1: str, snapshot2: str, node_types: str = "", limit: int = 200):
    try:
        return graphdb.diff_snapshots(snapshot1, snapshot2, node_types=node_types, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
