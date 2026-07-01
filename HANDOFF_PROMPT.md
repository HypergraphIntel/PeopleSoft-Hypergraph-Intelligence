You are continuing development on the **DeathStar / PeopleSoft Hypergraph Intelligence** project.

Before changing code, read and reconcile:

1. `ARCHITECTURE.md`
2. `ROADMAP.md`
3. `DEVELOPMENT_DIARY.md`
4. `README.md`
5. Existing code patterns in `connectors/`, `routers/`, `static/`, and `scripts/`

**Admin UI package structure** (split 2026-07-01): `routers/admin.py` no longer exists.
The admin UI is now the package `routers/admin/` with these files:
- `_core.py` — router object, `_NAV_GROUPS`, `_NAV_CSS`, `_ESC_JS`, `_nav_html()`, `_shell()`
- `__init__.py` — re-exports `router`; importing it registers all sub-module routes
- `home.py`, `security.py`, `graph.py`, `runtime.py`, `data.py`, `integration.py`,
  `objects.py`, `portal.py`, `platform.py`, `perf.py`, `tools.py`
- Each sub-module imports `router, _shell, _nav_html, _NAV_CSS, _ESC_JS` from `._core`
- New admin pages go in the sub-module matching their nav group (see `_NAV_GROUPS` in `_core.py`)

**Nav bar** (redesigned 2026-07-01): was 49 flat links; now a grouped CSS-only dropdown bar.
Groups: Runtime · Data · Integration · Objects · Portal · Platform · Perf · Tools
Direct links: Home · Users. Active group highlights on any child page.
Styles in `/static/app.css` (`.ds-nav-group`, `.ds-nav-dropdown`, `.ds-nav-drop-link`).
Standalone pages (no `app.css`) embed `_NAV_CSS` inline and call `_nav_html(active, env)`.
`_ESC_JS` provides the `esc()` HTML-escape helper embedded in standalone page `<script>` blocks.

Follow the architecture exactly:

* SQL belongs in `connectors/`, not routers.
* Routers stay thin.
* All database access must be grant-aware and read-only.
* Missing PeopleSoft tables, Oracle views, grants, or optional metadata must produce warnings, not crashes.
* Preserve existing endpoint shapes and URLs.
* Prefer UOM/provider-based object implementation.
* Keep `/` redirect, `/static`, `/admin`, and port `8088` assumptions intact unless explicitly instructed otherwise.

Documentation rules:

* `ARCHITECTURE.md` = design rules, subsystem boundaries, provider contracts.
* `ROADMAP.md` = current status and remaining work only.
* `DEVELOPMENT_DIARY.md` = dated chronological engineering journal.
* Do not duplicate large blocks between them.
* Update `ARCHITECTURE.md` only for architecture changes.
* Update `ROADMAP.md` when status or remaining work changes.
* Append to `DEVELOPMENT_DIARY.md` after meaningful work with changed files, reason, behavior, verification, blockers, and next step.

Current development priorities:

1. Improve Object Explorer visual hierarchy.
2. Extract/shared relationship provider registration for UOM and graph relationships.
3. Improve rich portal reconstruction and portal comparison.
4. Improve access-path visualization and broader permission decoding.
5. Add graph compaction and large-environment indexing.
6. Improve Application Engine runtime detail and restart analysis.
7. Add App Server monitoring and runtime alerts.
8. Expand PeopleCode parsing, especially Application Package parsing and larger-source pagination.
9. Add CI/deployment wiring for the admin shell smoke harness.
10. Continue SQL Definition Explorer only where grants allow, especially PeopleCode cross-reference if feasible.

Verification expectations:

* Run syntax checks/tests available in the repo.
* At minimum, run `python -m py_compile` or equivalent against touched Python files.
* Run/import `main.py` if possible.
* Use `scripts/smoke_admin_shell.py` when frontend/admin shell behavior changes.
* Verify affected API endpoints with `curl`.
* Verify affected `/admin` pages in browser when practical.
* Record verification results in `DEVELOPMENT_DIARY.md`.

Working style:

* Work in small vertical slices.
* Inspect existing implementation before changing anything.
* Prefer existing project patterns over new abstractions.
* Do not broad-rewrite working modules.
* Leave the repo runnable.
* If blocked by grants, missing tables, or unavailable metadata, implement graceful degradation and document the blocker.


A lot of changes have been made since you last looked at this.  Please pickup from here.