You are continuing development on the **DeathStar / PeopleSoft Hypergraph Intelligence** project.

Before changing code, read and reconcile:

1. `ARCHITECTURE.md`
2. `ROADMAP.md`
3. `DEVELOPMENT_DIARY.md`
4. `README.md`
5. Existing code patterns in `connectors/`, `routers/`, `static/`, and `scripts/`

---

## Admin UI package structure

`routers/admin.py` no longer exists. The admin UI is the package `routers/admin/` with:

- `_core.py` — router object, `_NAV_GROUPS`, `_NAV_CSS`, `_ESC_JS`, `_nav_html()`, `_shell()`
- `__init__.py` — re-exports `router`; importing it registers all sub-module routes
- `home.py`, `security.py`, `graph.py`, `runtime.py`, `data.py`, `integration.py`,
  `objects.py`, `portal.py`, `platform.py`, `perf.py`, `logs.py`, `tools.py`,
  `compflow.py`, `rca.py`, `sqr_view.py`
- Each sub-module imports `router, _shell, _nav_html, _NAV_CSS, _ESC_JS` from `._core`
- New admin pages go in the sub-module matching their nav group (see `_NAV_GROUPS` in `_core.py`)

## Nav bar

Grouped CSS-only dropdown bar. Groups: Runtime · Data · Integration · Objects · Portal · Platform · Perf · Security · Tools.
Direct links: Home · Users. Active group highlights on any child page.
Styles in `/static/app.css` (`.ds-nav-group`, `.ds-nav-dropdown`, `.ds-nav-drop-link`).

Security group items: Security Audit (`/admin/secaudit`), Security Explorer (`/admin/security`), Operators (`/admin/operator`), Roles (`/admin/role`), Permission Lists (`/admin/permissionlist`).

**`_NAV_CSS` rule:** `_NAV_CSS` is a complete `<style>…</style>` block. Always place `{_NAV_CSS}`
directly in `<head>`, never inside another `<style>` block. Standalone pages (no `app.css`) call
`_nav_html(active, env)` to render the nav bar. `_ESC_JS` provides the `esc()` HTML-escape helper
for inline `<script>` blocks.

Pages using `_shell()` get the nav, page header, and `/static/app.css` automatically — do not
embed `_NAV_CSS` on those pages.

## Connectors

All database/file/AI logic lives in `connectors/`. Key modules:

| Module | Purpose |
|--------|---------|
| `psdb.py` | Core PeopleSoft DB metadata queries |
| `ptmetadata.py` | PeopleTools/version-aware metadata discovery |
| `graphdb.py` | Knowledge graph store; `neighbors()`, `adjacency()`, `build()` |
| `graphshape.py` | Shared graph payload annotations and edge type aliases |
| `uom.py` | Unified Object Model providers |
| `ae.py` | Application Engine metadata/runtime |
| `peoplecode.py` | PeopleCode decoding/source helpers |
| `envcompare.py` | Cross-environment comparison logic |
| `driftdb.py` | SQLite drift snapshot store (`data/drift.db`) |
| `impact.py` | Impact forecasting: project KG traversal + env risk scoring |
| `logparser.py` | Line parsers: PIA, APPSRV, Tuxedo, Apache, F5, IGW, PRCS AE |
| `logdb.py` | SQLite log store (`data/logs.db`) |
| `logingest.py` | Log ingestion orchestrator (SSH → parse → store) |
| `sqrparser.py` | SQR/SQC file parser (description, tables, includes, procedures) |
| `sqrdb.py` | SQLite SQR index (`data/sqr.db`); schema: `UNIQUE(filename, source_key)` + `source_type` column; `overrides(env_source_keys)` returns delivered+custom duplicates |
| `sqringest.py` | SSH-based SQR filesystem indexer; reads `source["ssh_host"]` (was `alias`), passes `source_type` to `upsert_program()` |
| `cobolparser.py` | PeopleSoft `.cbl` parser; classifies program vs copybook (COPY target, no separate `.cpy` file), COPY deps, static CALL targets, EXEC SQL table refs |
| `cobol_db.py` | SQLite COBOL index (`data/cobol.db`); recursive-CTE `get_copy_deps()`; `content_hash` for incremental scan |
| `cobolingest.py` | SSH-based COBOL filesystem indexer (`cobol_sources` in config.json); treats per-file `PermissionError` as `denied`, not a crash |
| `sshclient.py` | Paramiko SSH/SFTP wrapper with per-host connection pooling |
| `runtimedb.py` | SQLite runtime snapshot store |
| `promotiondb.py` | SQLite promotion event log (`data/promotions.db`) |
| `ai.py` / `ai_tools.py` | AI provider abstraction and tool dispatch |
| `scheduler.py` | Background scheduler: graph snapshots + 60s log ingest |

---

## Architecture rules

- SQL belongs in `connectors/`, not routers.
- Routers stay thin.
- All database access must be grant-aware and read-only.
- Missing PeopleSoft tables, Oracle views, grants, or optional metadata must produce warnings, not crashes.
- Preserve existing endpoint shapes and URLs.
- Prefer UOM/provider-based object implementation.
- Keep `/` redirect, `/static`, `/admin`, and port `8088` assumptions intact unless explicitly instructed otherwise.
- New admin pages: add a `_NAV_GROUPS` entry in `_core.py` and a route in the appropriate sub-module.

## Documentation rules

- `ARCHITECTURE.md` = design rules, subsystem boundaries, provider contracts.
- `ROADMAP.md` = current status and remaining work only.
- `DEVELOPMENT_DIARY.md` = dated chronological engineering journal.
- Do not duplicate large blocks between them.
- Update `ARCHITECTURE.md` only for architecture changes.
- Update `ROADMAP.md` when status or remaining work changes.
- Append to `DEVELOPMENT_DIARY.md` after meaningful work: changed files, reason, behavior, verification, blockers, next step.

---

## Verification and CI

- `make check` — runs syntax check on all Python files
- `python3 scripts/smoke_admin_shell.py` — headless Chrome smoke test for all admin pages (expect 57/57 as of 2026-07-02)
- `.github/workflows/ci.yml` — runs `make check` on push/PR
- Always run `python3 -c "import py_compile; py_compile.compile('path/to/file.py', doraise=True)"` on touched files before restart
- Restart server with `pkill -f "uvicorn main:app"; .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8088 &`
- Verify affected API endpoints with `curl`
- Record verification results in `DEVELOPMENT_DIARY.md`

---

## Current development priorities

Drawn from `ROADMAP.md` remaining sections — pick the highest-value slice:

### Phase 4 — Runtime Intelligence (remaining)
- Browser session tracking
- WebLogic session tracking
- (App server process tracking, runtime history persistence, and incident
  recording are done — see `connectors/appsrvproc.py`, `runtimedb.py`,
  `routers/admin/incidents.py`)

### Phase 5 — Knowledge Graph (remaining)
- (Dynamic SQL READS/WRITES coverage and message/tree/project/portal
  cross-references are done — see `peoplecode.extract_dynamic_sql()` and
  `routers/peoplesoft.py` `attach_graph_context()`)
- Continue aligning provider-specific KG ingestion with UOM `_relationships`

### Phase 6 — Environment Intelligence (remaining)
- Auto-detect promotions from `PSPROJECTDEFN.LASTUPDDTTM` across environments
  (needs real DV/TST/UAT/PRD Oracle connections — blocked until available)

### Phase 9 — Platform Extensibility (remaining)
- Plugin SDK: custom object/graph/runtime providers, custom dashboards

### Phase 10 — Source Artifact Intelligence (remaining)
- (none open — COBOL KG wiring done: `cobol_program` node type with READS/WRITES/
  COPIES/CALLS edges, see `connectors/graphdb.py` `cobol_programs()`)
- **Note**: After any `sqr_sources` or `cobol_sources` config change, a re-index is
  required (`POST /api/sqr/ingest` / `POST /api/cobol/ingest`)
- **Note**: most delivered `.cbl` files are mode 700 on the PeopleSoft filesystem and
  are not readable by the SSH service account — the COBOL ingestor reports these as
  `denied`, not errors; this is expected (115/977 readable per environment on this box)

## Key pages added since last handoff (2026-07-02)

| URL | Sub-module | Description |
|-----|-----------|-------------|
| `/admin/ae` | `platform.py` | AE Explorer: steps, SQL, runtime history, cross-refs |
| `/admin/component` | `platform.py` | Component Explorer: pages, security, PeopleCode, access paths |
| `/admin/page` | `platform.py` | Page Explorer: records, components, PeopleCode, security |
| `/admin/permissionlist` | `security.py` | Permission List Explorer: components, roles, menus |
| `/admin/object/{type}/{name}` | `graph.py` | Unified Object Explorer; auto-redirects to dedicated explorers |
| `/admin/compflow` | `compflow.py` | Component Event Flow Explorer with inline PeopleCode source |
| `/admin/rca` | `rca.py` | Incident RCA: log+runtime+ASH+IB+KG correlation |
| `/admin/sqrsearch` | `sqr_view.py` | SQR Full-Text Search with syntax-highlighted snippets |
| `/admin/access` | `security.py` | Access Path Explorer: component-centric and operator-centric |
| `/admin/riskanalysis` | `platform.py` | Change Risk Analyzer: project KG blast radius + affected users |
| `/admin/secaudit` | `security.py` | Security Audit Dashboard: stats, orphan detection, sign-on history |
| `/admin/sqrdeps` | `sqr_view.py` | SQR Include Dependency Graph: forward tree, reverse "Included By", force-directed canvas |
| `/admin/sqrcompare` | `sqr_view.py` | SQR Environment Comparison: HCM vs FSCM side-by-side diff (Changed / Only A / Only B / Identical) |
| `/admin/cobol` | `cobol_view.py` | COBOL Explorer: list/search programs & copybooks, COPY dependency graph, live source view |

---

## Working style

- Work in small vertical slices.
- Inspect existing implementation before changing anything.
- Prefer existing project patterns over new abstractions.
- Do not broad-rewrite working modules.
- Leave the repo runnable at all times.
- If blocked by grants, missing tables, or unavailable metadata, implement graceful degradation and document the blocker.
