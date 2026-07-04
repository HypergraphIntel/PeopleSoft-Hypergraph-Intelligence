# Plugin SDK

DeathStar can be extended without touching core files. Drop a Python file
(or package) into `plugins/` at the repo root; it's discovered and loaded
automatically at server startup.

A plugin is any module under `plugins/` exposing a `register(sdk)` function.
`sdk` is `connectors/plugins.py` — call its `register_*` functions to plug
into one or more of five extension points. See `plugins/example_hello.py`
for a complete, minimal, working example that exercises all five; the
snippets below are extracted from it.

## Loading

- `plugins/<name>.py` or `plugins/<name>/__init__.py` — both work.
- Loaded once at startup, from `main.py`'s `lifespan()`, via
  `connectors/pluginloader.py`.
- **Isolated**: if a plugin fails to import or its `register()` raises, it's
  logged (`pluginloader: failed to load plugin '<name>' — <error>`) and
  skipped — the server and every other plugin still start normally. Verified
  by deliberately breaking `example_hello.py` and confirming the rest of the
  platform kept working.
- Nothing is hot-reloaded — changes require an app restart, same as every
  other config-driven source in this codebase (`sqr_sources`, `cobol_sources`).

## The five extension points

### 1. Object provider — new object type in Object/Graph Explorer

```python
sdk.register_object_provider(
    "hello_widget", _widget_object, _widget_payload,
    registry_meta={
        "display_title": "Hello Widget", "icon": "puzzle",
        "graph_node_type": "hello_widget",
        "object_page": "/admin/object/hello_widget/{name}",
        "discovery": None, "search": None, "supported_versions": [],
        "relationships": ["USES"],
    },
)
```

- `object_fn(env, name)` — return a `connectors.uom.canonical_base(...)`-shaped
  dict (or `{"status": "not_found"}` if the name doesn't resolve).
- `payload_fn(obj)` — return the API/UI payload: `{"type", "name", "title",
  "sections": [...]}`. Reachable at `GET /api/peoplesoft/object/hello_widget/{name}`
  and `/admin/object/hello_widget/{name}`.
- `registry_meta` is merged into `ptmetadata.OBJECT_REGISTRY` so the new type
  gets an icon, a graph node type, etc., same as any built-in type.

### 2. Graph provider — new Knowledge Graph nodes/edges

```python
def _widget_graph_loader(graph, env, limit):
    from connectors import graphdb
    graphdb.add_node(graph, "hello_widget", "ALPHA", "ALPHA", {})
    graphdb.add_edge(graph, "hello_widget", "ALPHA", "record", "JOB", "USES", {})
    return 1  # item count, shown in graph["providers"]

sdk.register_graph_provider("hello_widgets", _widget_graph_loader)
```

Runs on every `graphdb.build(env, limit, persist)` (manual re-index or the
scheduled snapshot loop), alongside the ~50 built-in providers. Same
isolation contract as those: an exception here is caught, logged into
`graph["providers"]` as a warning, and never aborts the rest of the build.

### 3. Runtime provider — status data on `/admin/runtime`

```python
def _widget_runtime_status(env):
    return {"widgets_total": 3, "widgets_healthy": 2}

sdk.register_runtime_provider("hello", _widget_runtime_status, label="Hello Widgets")
```

Reachable at `GET /api/runtime/plugins/hello?env=HCM`, and shown as a
generic JSON block in the "Plugin Providers" card on `/admin/runtime` (no
UI work required — that card renders any registered provider automatically).

### 4. Health check — operational status on `/admin/runtime`

```python
def _widget_health_check(env):
    degraded = [n for n, w in _WIDGETS.items() if w["status"] != "OK"]
    if not degraded:
        return {"status": "ok", "message": "All widgets healthy"}
    return {"status": "warn", "message": f"{len(degraded)} widget(s) degraded"}

sdk.register_health_check("hello_widgets", _widget_health_check, label="Hello Widgets Health")
```

`check_fn(env)` returns `{"status": "ok"|"warn"|"error", "message": str}` —
any extra keys are passed through too. Reachable at `GET
/api/runtime/health-checks?env=HCM` (runs every registered check on demand,
not polled/cached), and shown in the "Plugin Health Checks" card on
`/admin/runtime` (no UI work required). Same isolation contract as the other
registries: a check that raises is reported as its own `"error"` result
rather than failing the whole endpoint.

Distinct from a runtime provider: a runtime provider returns raw status data
for a human to read; a health check returns a judgment (`ok`/`warn`/`error`)
a dashboard can roll up or alert on. Use a runtime provider for "here's what's
happening," a health check for "is this OK."

### 5. Admin page + nav entry

```python
_router = APIRouter()

@_router.get("/admin/plugin/hello", response_class=HTMLResponse)
def _admin_hello_page():
    from routers.admin._core import _shell
    return HTMLResponse(_shell("Hello Plugin", "plugin_hello", "<p>...</p>"))

sdk.register_nav_entry("Plugins", "plugin_hello", "Hello Plugin", "/admin/plugin/hello")
sdk.register_router(_router)
```

`register_router()` gets `app.include_router()`'d automatically right after
your plugin loads. `register_nav_entry(group_label, key, label, href)` adds
a link to that nav group (creating it if it doesn't already exist) — use
`key` matching the `active` argument you pass to `_shell()` so the nav
highlights correctly on your page.

## What a plugin should NOT do

- Don't import anything under `routers/admin/_core.py` besides `_shell`,
  `_nav_html`, `_NAV_CSS`, `_ESC_JS` (the same convention every built-in
  admin page follows).
- Don't mutate `ptmetadata.OBJECT_REGISTRY` directly — go through
  `register_object_provider(..., registry_meta=...)` so the metadata and the
  dispatch registration stay in sync.
- Don't assume your plugin loads before or after another plugin — load order
  is directory-scan order (`sorted()`), not declared dependency order. If two
  plugins need to coordinate, that's a v2 problem this SDK doesn't solve yet.

## Not yet covered (v2 candidates)

- **Custom health checks** — hook into `connectors/alerts.py`'s
  `evaluate_alerts()`. Not built; the runtime-provider mechanism above is a
  reasonable stand-in for now (surface a status dict, alert on it yourself).
- **Config-driven data sources** (a plugin bundling its own `config.json`
  source list + SSH ingest + SQLite store, like the SQR/COBOL pipelines) —
  the object-provider and graph-provider registries are sufficient building
  blocks for this today; a plugin can just do it manually inside its own
  module the way `sqringest.py`/`cobolingest.py` do, there's no dedicated
  "source registration" registry yet.
