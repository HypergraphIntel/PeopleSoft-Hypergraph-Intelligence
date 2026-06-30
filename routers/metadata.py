from fastapi import APIRouter

from connectors import ptmetadata

router = APIRouter(prefix="/api/metadata", tags=["PeopleTools Metadata"])


@router.get("/version")
def metadata_version(env: str = "HCM"):
    """Return detected PeopleTools version with version-specific adapter context.

    Includes declared new tables, column aliases, and live probe results for
    version-specific tables to confirm what is actually accessible.
    """
    adapter_data = ptmetadata.version_adapter(env)
    tables_data = ptmetadata.version_tables(env)
    key = adapter_data.get("adapter_key", "unknown")
    adapter = adapter_data.get("adapter", {})

    new_table_probes = {}
    for t in adapter.get("new_tables", []):
        new_table_probes[t] = ptmetadata.has_table(env, t)

    return {
        "environment": env.upper(),
        "peopletools_version": adapter_data.get("peopletools_version"),
        "adapter_key": key,
        "status": adapter.get("status", "unknown"),
        "notes": adapter.get("notes", ""),
        "new_tables_declared": adapter.get("new_tables", []),
        "new_tables_accessible": new_table_probes,
        "column_aliases": {f"{t}/{l}": c for (t, l), c in adapter.get("column_aliases", {}).items()},
        "known_versions": list(ptmetadata.VERSION_ADAPTERS.keys()),
    }


@router.get("/capabilities")
def metadata_capabilities(env: str = "HCM"):
    return ptmetadata.capabilities(env)


@router.get("/tables")
def metadata_tables(env: str = "HCM"):
    return ptmetadata.accessible_objects(env, "TABLE")


@router.get("/views")
def metadata_views(env: str = "HCM"):
    return ptmetadata.accessible_objects(env, "VIEW")


@router.get("/cache")
def metadata_cache():
    return ptmetadata.cache_status()


@router.post("/cache/clear")
def metadata_cache_clear():
    return ptmetadata.clear_cache()


@router.get("/object-types")
def metadata_object_types():
    return ptmetadata.object_types()


@router.get("/discovery")
def metadata_discovery(env: str = "HCM"):
    return ptmetadata.discovery(env)


@router.get("/products")
def metadata_products(env: str = "HCM"):
    return ptmetadata.installed_products(env)


@router.get("/resolve/{object_type}/{name}")
def metadata_resolve(object_type: str, name: str, env: str = "HCM"):
    return ptmetadata.resolve_object(env, object_type, name)


@router.get("/capabilities/table/{table_name}")
def metadata_has_table(table_name: str, env: str = "HCM"):
    return {
        "table": table_name.upper(),
        "available": ptmetadata.has_table(env, table_name),
    }


@router.get("/capabilities/table/{table_name}/column/{column_name}")
def metadata_has_column(table_name: str, column_name: str, env: str = "HCM"):
    return {
        "table": table_name.upper(),
        "column": column_name.upper(),
        "available": ptmetadata.has_column(env, table_name, column_name),
    }


@router.get("/capabilities/view/{view_name}")
def metadata_has_view(view_name: str, env: str = "HCM"):
    return {
        "view": view_name.upper(),
        "available": ptmetadata.has_view(env, view_name),
    }


@router.get("/relationship-map")
def metadata_relationship_map():
    """Return the declarative object-type relationship graph from OBJECT_REGISTRY.

    Each node is an object type. Each edge is a declared relationship between types.
    Useful for understanding what traversals are possible in the Knowledge Graph and
    what related objects appear in the Object Explorer.
    """
    nodes = []
    edges = []
    seen_edges = set()

    for type_name, entry in ptmetadata.OBJECT_REGISTRY.items():
        if entry.get("supported_versions") == ["planned"]:
            continue
        nodes.append({
            "id": type_name,
            "label": entry.get("display_title", type_name),
            "icon": entry.get("icon", "circle"),
        })
        for rel in entry.get("relationships", []):
            target = rel.get("target_type", "")
            edge_type = rel.get("edge_type", "")
            direction = rel.get("direction", "out")
            src = type_name if direction == "out" else target
            tgt = target if direction == "out" else type_name
            key = (src, tgt, edge_type)
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({
                    "source": src,
                    "target": tgt,
                    "type": edge_type,
                    "label": rel.get("label", edge_type),
                })

    return {"nodes": nodes, "edges": edges}
