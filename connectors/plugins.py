"""
Plugin SDK registries (Phase 9 — Platform Extensibility).

Five appendable registries that let a plugin extend the platform without
editing core files:
  - object providers  (new UOM object types, e.g. /admin/object/{type}/{name})
  - graph providers    (new Knowledge Graph node/edge builders)
  - runtime providers   (new /admin/runtime status sources)
  - health checks       (new operational health checks, e.g. /admin/runtime)
  - nav entries         (new admin dashboard pages in the nav bar)

Plugins call `register_*()` at import time (see connectors/pluginloader.py).
This module is pure Python — no FastAPI/DB imports at module scope — so it
can be imported early and by anything without cycles.
"""

import logging

logger = logging.getLogger("deathstar.plugins")

_OBJECT_PROVIDERS: dict[str, dict] = {}
_GRAPH_PROVIDERS: list[tuple[str, callable]] = []
_RUNTIME_PROVIDERS: dict[str, dict] = {}
_HEALTH_CHECKS: dict[str, dict] = {}
_NAV_ENTRIES: list[tuple[str, tuple]] = []
_ROUTERS: list = []
_LOADED_PLUGINS: list[str] = []


def register_object_provider(object_type: str, object_fn, payload_fn, registry_meta: dict | None = None):
    """Register a new UOM object type.

    object_fn(env, name) -> object dict (canonical UOM shape)
    payload_fn(obj) -> API/UI payload dict (sections, etc.)
    registry_meta is merged into ptmetadata.OBJECT_REGISTRY[object_type]
    (icon, display_title, graph_node_type, object_page, relationships, ...).
    """
    _OBJECT_PROVIDERS[object_type] = {"object_fn": object_fn, "payload_fn": payload_fn}
    if registry_meta:
        from connectors import ptmetadata
        ptmetadata.OBJECT_REGISTRY.setdefault(object_type, registry_meta)


def register_graph_provider(name: str, loader):
    """Register a Knowledge Graph builder. loader(graph, env, limit) -> int (item count)."""
    _GRAPH_PROVIDERS.append((name, loader))


def register_runtime_provider(name: str, fetch_fn, label: str = "", admin_render=None):
    """Register a runtime status source. fetch_fn(env) -> dict.
    admin_render(data) -> HTML string, optional (falls back to a generic
    key/value dump in the admin UI if omitted)."""
    _RUNTIME_PROVIDERS[name] = {"fetch_fn": fetch_fn, "label": label or name, "admin_render": admin_render}


def register_health_check(name: str, check_fn, label: str = ""):
    """Register an operational health check. check_fn(env) -> dict, at
    minimum {"status": "ok"|"warn"|"error", "message": str}. Run on demand
    (not polled) by GET /api/runtime/health-checks; surfaced on
    /admin/runtime alongside the existing Plugin Providers card."""
    _HEALTH_CHECKS[name] = {"check_fn": check_fn, "label": label or name}


def register_nav_entry(group_label: str, key: str, label: str, href: str):
    """Register a nav bar entry pointing at a plugin's own admin page."""
    _NAV_ENTRIES.append((group_label, (key, label, href)))


def register_router(router):
    """Register a FastAPI APIRouter (the plugin's own admin page/API routes)."""
    _ROUTERS.append(router)


def get_object_provider(object_type: str):
    return _OBJECT_PROVIDERS.get(object_type)


def get_graph_providers() -> list[tuple[str, callable]]:
    return list(_GRAPH_PROVIDERS)


def get_runtime_providers() -> dict[str, dict]:
    return dict(_RUNTIME_PROVIDERS)


def get_health_checks() -> dict[str, dict]:
    return dict(_HEALTH_CHECKS)


def get_nav_entries() -> list[tuple[str, tuple]]:
    return list(_NAV_ENTRIES)


def get_routers() -> list:
    return list(_ROUTERS)


def mark_loaded(plugin_name: str):
    _LOADED_PLUGINS.append(plugin_name)


def status() -> dict:
    """Introspection: what got loaded and what each registry currently holds."""
    return {
        "loaded_plugins": list(_LOADED_PLUGINS),
        "object_providers": sorted(_OBJECT_PROVIDERS.keys()),
        "graph_providers": [name for name, _ in _GRAPH_PROVIDERS],
        "runtime_providers": sorted(_RUNTIME_PROVIDERS.keys()),
        "health_checks": sorted(_HEALTH_CHECKS.keys()),
        "nav_entries": [entry[1][0] for entry in _NAV_ENTRIES],
        "routers": len(_ROUTERS),
    }
