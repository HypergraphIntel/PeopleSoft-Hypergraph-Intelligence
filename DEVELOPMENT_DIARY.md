# DeathStar Development Diary

This diary records implementation changes as they land. `ROADMAP.md` remains
the status tracker; this file keeps the narrative trail: what changed, why it
matters, and how it was verified.

------------------------------------------------------------------------

## 2026-06-30 — Page Graph API Uses UOM Provider

Date/time: 2026-06-30 11:47 CDT

Features implemented:
- Reconciled the older `/api/peoplesoft/graph/page/{name}` route with the
  Page UOM provider.
- Removed the duplicate router-local Page graph construction loop from
  `routers/peoplesoft.py`.
- Graph Explorer Page requests now receive the same Page relationship model as
  Object Explorer Graph Preview.

Files modified:
- `routers/peoplesoft.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the endpoint URL and response shape unchanged: `{root, nodes, edges}`.
- Accepted the intentional content alignment: the route now returns the capped,
  cleaner UOM Page preview graph rather than the older router graph. For
  `JOB_DATA1`, this means 112 nodes / 111 edges and no blank record node.
- Left Field, Tree, CI, and Portal graph route delegation patterns unchanged.

Bugs fixed:
- Removed one source of duplicated Page relationship logic.
- Removed the older Page graph route behavior that could include a blank
  `record: ` node from untrimmed metadata rows.

Technical debt:
- Reduced router-owned graph construction; routers remain thinner.
- Component, Record, Operator, Role, and Permission List graph routes still
  contain router-local graph construction and should be migrated cautiously.

Verification:
- `python -m py_compile routers/peoplesoft.py connectors/uom.py` — OK.
- Direct `routers.peoplesoft.peoplesoft_graph('page', 'JOB_DATA1', env='HCM')`
  check returned `page:JOB_DATA1`, 112 nodes, and 111 edges.
- `python -m py_compile routers/peoplesoft.py routers/admin.py connectors/uom.py connectors/psdb.py connectors/ptmetadata.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/graph/page/JOB_DATA1?env=HCM` — OK, returned
  `page:JOB_DATA1`, 112 nodes, and 111 edges.
- `GET /api/peoplesoft/object/page/JOB_DATA1?env=HCM` — OK, Graph Preview
  returned matching `node_count=112` and `edge_count=111`.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Continue reducing router-local graph construction, likely Component next
  because it overlaps heavily with the existing UOM Component graph.

------------------------------------------------------------------------

## 2026-06-30 — Page UOM Relationship Graph Extraction

Date/time: 2026-06-30 11:38 CDT

Features implemented:
- Continued the relationship-provider extraction roadmap slice by moving the
  Page UOM graph preview onto the shared `relationship_graph()` helper.
- Extended the helper to support explicit source-node types/names for inbound
  edges such as Component -> Page and Permission List -> Page.
- Added optional root-node data support so providers can preserve existing
  root metadata when using the shared helper.
- Added `limit_relationships()` so providers can keep existing preview caps
  while declaring relationship graph specs.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Migrated the UOM Page graph builder only. The older router-specific
  `/api/peoplesoft/graph/page/...` path still exists and should be reconciled
  separately to avoid changing legacy graph behavior inside this slice.
- Preserved the previous Page UOM preview caps: components 20, records 30,
  fields 40, subpages 20, permission lists 40.
- Preserved Page root metadata in graph preview nodes.

Bugs fixed:
- None; this was an internal maintainability slice.

Technical debt:
- Removed another ad hoc UOM graph loop.
- Remaining debt: Record, Component, Portal, and security graph builders still
  have imperative graph construction. The legacy router page graph also still
  duplicates Page relationship logic.

Verification:
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- Direct `uom.page_object('HCM', 'JOB_DATA1')['_graph']` check returned 112
  nodes and 111 edges, matching the pre-refactor UOM graph count.
- Direct Page graph preview retained root page metadata (`pnlname=JOB_DATA1`)
  and did not include the blank record node present in the older router graph.
- Direct synthetic Tree and Component Interface graph checks still returned the
  expected shared-helper edges.
- Direct `uom.page_payload(...)` check showed Graph Preview `node_count=112`
  and `edge_count=111`.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/object/page/JOB_DATA1?env=HCM` — OK, Graph Preview
  returned `node_count=112`, `edge_count=111`, and root node metadata retained
  `pnlname=JOB_DATA1`.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Reconcile or retire the older router-specific Page graph path in favor of
  UOM graph output.
- Continue relationship extraction with Component or Record after capturing
  before/after graph counts.

------------------------------------------------------------------------

## 2026-06-30 — Shared UOM Relationship Graph Helper

Date/time: 2026-06-30 11:11 CDT

Features implemented:
- Started the relationship-provider extraction roadmap slice with a shared
  `relationship_graph()` helper in `connectors/uom.py`.
- Refactored Tree and Component Interface graph previews to use declarative
  relationship specs instead of local hand-written node/edge loops.
- Preserved existing UOM payload and `/api/peoplesoft/graph/...` response
  shapes: graph previews still return `nodes` and `edges`, with the same root,
  target object types, admin links, and relationship labels.
- Fixed Tree metadata discovery/search column names for PeopleTools tables that
  expose `TREE_NAME` and `TREE_STRCT_ID` instead of the older aliases.
- Routed global Tree search through the dedicated grant-aware tree search
  provider and de-duplicated global results by tree name while preserving
  variant rows in `/api/peoplesoft/trees`.

Files modified:
- `connectors/uom.py`
- `connectors/ptmetadata.py`
- `connectors/psdb.py`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the first extraction narrow and provider-local: Tree and CI were the
  newest providers and already had similar field/record relationship loops.
- Left older Record, Page, Component, Portal, and security graph builders alone
  until each can be migrated with endpoint parity checks.
- Documented the expectation that UOM providers should reuse shared graph
  helpers where practical, without changing router URLs or API contracts.

Bugs fixed:
- Tree discovery/global search no longer uses invalid `PSTREEDEFN.TREENAME` or
  `TREESTRCTPNM` column references.
- `/api/peoplesoft/trees` now aliases physical `TREE_NAME`/`TREE_STRCT_ID`
  columns back to the existing response keys (`treename`, `treestrctpnm`).

Technical debt:
- Removed duplicated Tree/CI graph loop structure.
- Remaining debt: older UOM providers still build `_graph` imperatively and
  should be migrated in small, verified slices.

Verification:
- `python -m py_compile connectors/psdb.py connectors/ptmetadata.py connectors/uom.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Direct synthetic `tree_graph()` and `ci_graph()` checks returned expected
  root nodes, object nodes, and relationship edges.
- Restart note: direct `systemctl restart/start deathstar-api` required
  interactive authentication in this shell. An old orphaned manual uvicorn
  process was also occupying 8088. Cleared the port and started the same uvicorn
  command manually from the project venv for live HTTP verification; systemd
  subsequently reclaimed the service and is active on port 8088.
- `GET /api/sqlws/config` — OK, returned `['HCM', 'FSCM']`.
- `GET /api/peoplesoft/graph/ci/CI_JOB_DATA?env=HCM` — OK, returned
  `ci:CI_JOB_DATA` with 504 nodes and 988 edges.
- `GET /api/peoplesoft/trees?env=HCM&q=DEPT&limit=10` — OK, returned Tree rows
  with `treename` and `treestrctpnm`.
- `GET /api/peoplesoft/search?env=HCM&q=DEPT&limit=25` — OK, returned unique
  Tree names in global search.
- `GET /api/peoplesoft/graph/tree/DEPT_SECURITY?env=HCM` — OK, returned
  `tree:DEPT_SECURITY` with 4 nodes and 4 edges.

Next recommended work:
- Continue relationship extraction with a similarly small provider, likely
  Page or Component after comparing current graph output.

------------------------------------------------------------------------

## 2026-06-30 — Oracle ASH Integration + Runtime Monitor Alerts

**Oracle ASH (V$ACTIVE_SESSION_HISTORY) is now accessible** following the AE/Oracle grant
expansion. Previously listed as "Blocked (Diagnostics Pack)", it now has 3370+ in-memory
samples and DBA_HIST_ACTIVE_SESS_HISTORY provides 10 days of historical AWR data.

**`connectors/execution.py`** — added `oracle_ash_summary(db_name, minutes=30)` and
`oracle_ash_top_sql(db_name, minutes=30, limit=10)`:
- `oracle_ash_summary`: returns wait class breakdown (CPU / Commit / User I/O / …),
  top-10 wait events with sample counts and percentages, top-10 process modules — all
  from foreground sessions in V$ACTIVE_SESSION_HISTORY
- `oracle_ash_top_sql`: joins V$ACTIVE_SESSION_HISTORY to V$SQL (child_number=0) to
  return top SQL IDs by sample count (≈ approximate time in DB), with SQL text snippets
  where the cursor is still cached
- TIMESTAMP date math: PSPRCSRQST uses TIMESTAMP(6), so arithmetic against SYSDATE
  (DATE) must cast via `CAST(BEGINDTTM AS DATE)` to avoid ORA-00932

**`routers/runtime.py`** — added `/api/runtime/ash?db=&minutes=` and
`/api/runtime/ash/sql?db=&minutes=&limit=` endpoints.

**`routers/admin.py`** — added "Oracle Active Session History" card between Oracle DB
and Runtime Graph; `loadAsh()` fetches both endpoints in parallel; wait class chips
use per-class color coding (`_WC_COLOR` map); two-column layout (events left, SQL right);
top process modules shown as chips at the bottom; `loadAsh()` added to `refresh()`.

**Verification:** `/api/runtime/ash?db=HRDMO&minutes=30` returns 104 samples:
68.3% Commit (log file sync), 30.8% CPU, 1% User I/O. Top SQL includes DeathStar's own
queries plus IB dispatcher SELECTs.

---

**Runtime Monitor Alerts** — `connectors/alerts.py` implements six independent checks:
1. **PROCESS_ERRORS** — counts PSPRCSRQST rows with RUNSTATUS 3/4/8 in last 1h
2. **LONG_PROCESS** — flags processes with RUNSTATUS 2/7 and elapsed >120m (using
   `CAST(BEGINDTTM AS DATE)` for TIMESTAMP arithmetic)
3. **QUEUE_DEPTH** — warns when 10+ processes are queued/pending-cancel in last 2h
4. **BLOCKING_SESSIONS** — delegates to `execution.oracle_blocking()`, escalates to
   "error" severity when max wait exceeds 300s
5. **HIGH_WAIT** — flags when a single non-CPU wait class exceeds 70% of ASH samples
6. **DOMAIN_NO_LISTENERS** — surfaces app server domains with no active listeners

`/api/runtime/alerts?env=&db=` endpoint. "Active Alerts" card at top of `/admin/runtime`:
all-clear shown in green when clean; card border shifts to red/amber when errors/warns
are present; each alert has a severity chip, code tag, message, and where applicable a
deep-link to `/admin/runtime?instance=N` or similar.

**Verification:** `GET /api/runtime/alerts?env=HCM&db=HRDMO` → `{"alert_count": 0, ...}`
(all clear on a quiet lab environment). Alert thresholds are conservative defaults that
will fire on real-world production anomalies.

------------------------------------------------------------------------

## 2026-06-30

### Component Interface UOM and Object Explorer Support

Date/time: 2026-06-30 01:37:21 CDT

- Added first-class read-only Component Interface object support to the
  Universal Object Model.
- Registered CI metadata in the PeopleTools metadata registry so global search
  can find `PSBCDEFN` rows by CI name, display name, description, component,
  search/add record, or owner.
- Added CI object payloads with definition metadata, component/menu links,
  search/add records, key items, collections, properties, methods, exposed
  fields, sampled item catalog rows, warnings, and graph preview sections.
- Wired CI into `/api/peoplesoft/object/ci/{name}`,
  `/api/peoplesoft/graph/ci/{name}`, Object Explorer selectors, and Graph
  Explorer selectors.

Files modified:

- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Used `ci` as the canonical object type and accepted `component_interface` as
  an alias for API/object URLs.
- Kept `PSBCITEM` rows capped at 500 for browser safety while preserving
  `PSBCDEFN.ITEMCOUNT` and section counts in the payload.
- Linked graph relationships to the wrapped component, declared menu,
  search/add records, unique exposed records, and unique exposed fields rather
  than modeling every property as a separate graph node.

Bugs fixed:

- None in production behavior; this closes the final planned object-type gap
  in the Object Explorer/UOM roadmap.

Technical debt:

- Removed CI from the planned-only metadata placeholder list.
- Remaining UOM debt is now about shared relationship provider registration,
  not missing first-class object types.

Next recommended work:

- Improve Object Explorer visual hierarchy now that the remaining planned
  object types are represented.
- Start extracting shared relationship provider registration so object-specific
  graph and UOM relationship logic can be reused more consistently.

### Tree UOM and Object Explorer Support

Date/time: 2026-06-30 01:26:26 CDT

- Added first-class read-only Tree object support to the Universal Object Model.
- Registered Tree in the PeopleTools metadata registry so global search can find
  `PSTREEDEFN` rows by tree name, description, structure ID, or setID.
- Added Tree object payloads with definition metadata, tree structure records
  and fields, levels, branch samples, node samples, leaf samples, effective-dated
  variants, warnings, and graph preview sections.
- Wired Tree into `/api/peoplesoft/object/tree/{name}`,
  `/api/peoplesoft/graph/tree/{name}`, Object Explorer selectors, and Graph
  Explorer selectors.

Files modified:

- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Resolved Tree objects by `TREE_NAME` and selected the latest effective-dated
  definition row, while showing the latest 50 variants for duplicate setID or
  effective-date combinations.
- Kept node, leaf, and branch sections capped at 200 rows each so large trees
  remain navigable in the Object Explorer.
- Linked tree structure records and fields into the UOM graph rather than
  exploding every node and leaf into graph nodes.

Bugs fixed:

- Normalized related tree lookups to compare `EFFDT` by date so Oracle date
  values returned through Python still match `PSTREENODE`, `PSTREELEAF`, and
  related metadata rows.
- Avoided passing unused bind values to Oracle queries after the driver rejected
  extra placeholders for the variants lookup.

Technical debt:

- Removed Tree from the planned-only metadata placeholder list.
- Remaining debt: Component Interface (CI) is still the remaining planned UOM
  object type.

Next recommended work:

- Add CI metadata/UOM support as the next Object Explorer object-type slice.
- Consider a dedicated Tree admin page only if users need full hierarchical
  visualization beyond the canonical Object Explorer payload.

### Admin Shell Interaction Smoke Checks

Date/time: 2026-06-30 01:16:04 CDT

- Expanded the headless admin shell smoke harness from page-load validation to
  targeted interaction checks for the tabs and panes that have been fragile
  during the shared shell migration.
- Added browser-driven checks for Runtime process/Oracle tabs, SQL Workspace
  Schema/History/Pinned tabs, Integration Broker Overview/Service Ops tabs,
  Environment Compare Records/Fields/PS Queries tabs, and Graph Explorer
  List/Visual tabs.
- Continued to collect DevTools runtime/log errors after interactions so
  click-triggered JavaScript regressions are reported by the harness.

Files modified:

- `scripts/smoke_admin_shell.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept interaction checks close to each page definition so future page smoke
  coverage can be added surgically without introducing a larger test framework.
- Used visible pane/class-state assertions rather than API-dependent data
  assertions, keeping the checks focused on frontend shell behavior.

Bugs fixed:

- No production code bugs were changed in this slice; this adds regression
  coverage for the tab/sidebar failures fixed earlier.

Technical debt:

- Reduced manual testing burden for shared-shell page migrations.
- Remaining debt: the harness should still be wired into CI or deployment
  validation.

Next recommended work:

- Add one lightweight data/search interaction smoke for SQL Workspace,
  Integration Broker, Object Explorer, and Environment Compare where the
  endpoint data is stable enough for repeatable tests.

### Admin Shell Browser Smoke Harness

Date/time: 2026-06-30 01:08:27 CDT

- Added a lightweight headless Chrome smoke harness for core admin shell pages
  so rendered JavaScript and shared-shell regressions are caught outside of
  `py_compile`.
- Covered `/admin/`, Runtime, SQL Workspace, Integration Broker, Environment
  Compare, Graph Explorer, and Object Explorer with page markers, shell brand
  checks, environment selector checks, active nav checks where applicable, and
  browser runtime/log error detection.
- Fixed the shared shell favicon SVG path to use the existing cyan icon asset.

Files modified:

- `scripts/smoke_admin_shell.py`
- `routers/admin.py`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept the harness dependency-free by driving Chrome through the DevTools
  protocol with Python standard library modules.
- Made page expectations explicit so pages without top-level nav items, such as
  Graph and Object Explorer, are still validated without false active-link
  failures.

Bugs fixed:

- Removed a stale `/static/images/empire_logo_sith.svg` favicon reference that
  produced a browser 404 in the shared shell.

Technical debt:

- Reduced the browser-rendered JavaScript coverage gap that allowed recent UI
  initialization regressions to reach manual testing.
- Remaining debt: the harness is local tooling and is not yet wired into CI or
  a deploy-time smoke step.

Next recommended work:

- Add the admin shell smoke harness to CI or the service deployment checklist.
- Expand the harness with one interaction smoke per high-risk page as pages are
  migrated into the shared frontend shell.

### Frontend Shell Stabilization

Date/time: 2026-06-30 00:54:51 CDT

- Implemented a small shared-shell cleanup as the next slice of the Frontend
  Shell roadmap work.
- Replaced the duplicate shell brand/nav construction with a single brand link
  that contains the cyan logo and `PeopleSoft Explorer` title.
- Added `deathstar:envchange` event emission in `/static/app.js` whenever the
  shared environment selector initializes, changes, or falls back to a stored
  environment.
- Preserved backwards compatibility by keeping legacy page `#envSel`
  synchronization and the existing `window.onEnvChange`, `window.dsGetEnv`,
  `window.dsSetEnv`, and `window.dsGetStoredEnv` helpers.

Files modified:

- `routers/admin.py`
- `static/app.js`
- `static/app.css`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept the shell event additive rather than replacing existing hooks so
  migrated pages and legacy pages can coexist during visual unification.
- Kept page-specific environment selectors working while newer pages can
  consume the shared `deathstar:envchange` event.

Bugs fixed:

- Removed duplicate brand anchors in the shared admin shell navigation.

Technical debt:

- Removed one shell markup inconsistency.
- Remaining debt: several legacy admin pages still carry page-local
  environment controls and page-local styling while the shared shell migration
  continues.

Next recommended work:

- Continue the Frontend Shell roadmap item by migrating legacy admin pages to
  the shared environment event and reducing page-local nav/header CSS.
- Add a lightweight browser-smoke harness for shell pages so future UI
  migrations catch JavaScript initialization regressions automatically.

## 2026-06-29

### Integration Broker Service Operations

- Added first-class read-only Service Operations APIs under `/api/ib/operations`.
- Expanded the Integration Broker connector to decode operation versions, handlers,
  service security, messages, queue mappings, runtime queue summaries, and
  sender/receiver routing nodes using grant-aware PeopleTools metadata views.
- Redesigned the `/admin/ib` sidebar to include a `Service Ops` tab and moved
  routing/transaction operation links to the new operation detail view.
- Normalized Integration Broker service kind labels so REST operations and standard
  operations are shown separately in the UI where metadata permits.

Verification:

- Compiled `connectors/ib.py`, `routers/ib.py`, and `routers/admin.py`.
- Smoke-tested HCM operation lookup for `BEN_CHATBOT_SVC_ASF_POST`.

### UOM Foundation and Object Explorer Unification

- Added canonical Universal Object Model coverage for Field, Record, Operator,
  Role, Permission List, Application Engine, PeopleCode, and Integration Broker
  objects.
- Standardized reusable object payloads with `overview`, `sections`, `_links`,
  `_uom`, and graph context.
- Routed the generic Object Explorer through reusable payload APIs so canonical
  object pages share navigation, graph links, relationship sections, and admin
  links.
- Added graph context enrichment for object payloads where Knowledge Graph
  neighbors exist.

Verification:

- Compiled `main.py`, `connectors`, and `routers`.
- Smoke-tested representative object payloads through direct Python calls and
  HTTP object endpoints.

### Security Explorer Expansion

- Added Permission List UOM and permission-list object payloads.
- Enriched menu-access grant paths with permission-list detail and decoded authorization actions, matching the existing component/page explanation experience.
- Added adaptive `PSAUTHITEM` component traversal for PeopleTools schemas that
  expose `PNLGRPNAME` directly and schemas that require `PNLITEMNAME` to
  `PSPNLGROUP` resolution.
- Added security explanation APIs for Operator to Component, Operator to Page,
  and Operator to Menu.
- Updated admin security workflows with Explain Access, Explain Page, and
  Explain Menu actions.

Verification:

- Smoke-tested explanation APIs against HCM sample metadata.
- Confirmed component/page/menu grant paths include roles, permission lists,
  and operators where available.

### PeopleCode Semantic Paths

- Added PeopleCode event decoding, event labels, semantic path decoding, event
  scope, subtype, and canonical path metadata.
- Surfaced PeopleCode semantic metadata in UOM and admin detail views.
- Preserved encoded references for safe Object Explorer navigation.

Verification:

- Compiled connectors and routers.
- Smoke-tested PeopleCode detail payloads with semantic path fields.

### Integration Broker Graph Expansion

- Expanded Integration Broker graph providers to connect service operations,
  routings, queues, nodes, and PeopleCode relationships.
- Added richer IB UOM relationships for services, nodes, queues, and routings.

Verification:

- Compiled graph and IB modules.
- Smoke-tested representative IB object payloads and graph neighborhoods.

### SQL Workspace Timeout and Cancellation

- Added server-side execution timeout normalization and propagation from the SQL Workspace router into the connector execution path.
- Added backend cancellation handling so SQL Workspace executions can return an explicit `cancelled` status when a client-side abort is detected, and the connector records that state in history/audit output.
- The connector now applies `cursor.callTimeout` when available, returns a clear `timed_out` flag for timed-out queries, and records timeout status in history/audit entries.
- The admin SQL Workspace page now exposes a timeout input, a Cancel button, and client-side `AbortController` handling so execution can be interrupted cleanly and the UI surfaces cancelled/timed-out feedback without leaving the interface in a stuck state.
- Preserved the existing read-only execution, pagination, explain-plan, export, and history behavior while keeping successful query execution unchanged.

Verification:

- Ran `python -m unittest -q tests.test_sqlws_timeout`.
- Ran `python -m py_compile routers/admin.py routers/sqlws.py connectors/sqlws.py connectors/uom.py connectors/psdb.py connectors/envcompare.py routers/envcompare.py`.
- Smoke-tested `/api/sqlws/config` and `/api/envcompare/queries` after service restart.

### Graph Snapshot, Diff, and Environment Compare

- Added graph snapshot creation, listing, loading, deletion, and manifest
  helpers.
- Added graph diff and snapshot diff APIs.
- Added Graph tab support to Environment Compare.
- Added snapshot create/open/delete/compare workflows to Graph Explorer.

Verification:

- Compiled graph router and connector modules.
- Smoke-tested snapshot API paths and graph diff payloads.

### Component UOM Integration

- Replaced the ad hoc Component object route with canonical Component UOM.
- Added component relationships for definition, pages, search records, page
  records, menu placement, Portal Registry references, permission lists,
  security, related content, event mapping, drop zones, and graph preview.
- Added component security graph edges through permission lists, roles, and
  operators.

Verification:

- `uom.component_object('HCM', 'GDP_SELECT_PRCS')` returned available metadata
  with pages, menu placement, permission lists, roles, operators, portal refs,
  and graph preview.
- `/api/peoplesoft/object/component/GDP_SELECT_PRCS?env=HCM` returned `200`.

### Page UOM Integration

- Added canonical Page UOM and replaced the ad hoc Page object route.
- Added page relationships for definition, components, records, fields, scroll
  structure, grids, subpages, PeopleCode, event mapping, related content, drop
  zones, transfers, security, and graph preview.
- Tightened object-link generation so whitespace-only PeopleTools placeholder
  rows do not become clickable canonical object links.

Verification:

- `uom.page_object('HCM', 'GDP_SELECT_PRCS')` returned available metadata with
  components, records, fields, subpages, security grants, and graph preview.
- `/api/peoplesoft/object/page/GDP_SELECT_PRCS?env=HCM` returned `200`.

### Portal Registry Foundation

- Added Portal Registry database helpers around `PSPRSMDEFN`.
- Added canonical Portal Registry UOM and object payloads.
- Added content reference object API and direct Portal Registry API route.
- Added breadcrumb reconstruction, child content references, component target
  inference, global search registration, and graph preview.
- Added Portal Registry options to generic Object Explorer and Graph Explorer
  selectors.

Verification:

- `HC_GDP_SELECT_PRCS_GBL` resolved with label, breadcrumbs to
  `PORTAL_ROOT_OBJECT`, component target `GDP_SELECT_PRCS`, and graph preview.
- Object, direct Portal Registry, graph, and global search endpoints returned
  `200`.

### Portal Security

- Added Portal Registry type decoding for content references and folders.
- Added `PSPRSMPERM` portal grant loading with permission-list and role grant
  decoding.
- Added inherited/cascading portal permission handling through breadcrumb
  ancestry.
- Added portal access path expansion through permission lists, roles, and
  operators.
- Added Operator-to-Portal explanation API.
- Surfaced Portal Security and Access Paths sections in Portal Registry UOM.

Verification:

- `/api/peoplesoft/portal-registry/HC_GDP_SELECT_PRCS_GBL/security?env=HCM`
  returned `200` with 3 portal grants and 15 access paths.
- `/api/peoplesoft/security/explain-portal?env=HCM&oprid=GUACUSER&portal=HC_GDP_SELECT_PRCS_GBL`
  returned `200` with access confirmed through 3 matching grants.
- Portal object payload includes `Attributes`, `Portal Security`, and
  `Access Paths` sections.

### Dedicated Portal Explorer UI

- Added `/admin/portal` as a focused Portal Explorer page.
- Added Portal Explorer navigation to the admin home page.
- Built the page over existing UOM/security APIs instead of duplicating portal
  traversal logic in the UI.
- Added search, direct `PORTAL_OBJNAME` loading, breadcrumbs, definition,
  counts, target components, children, portal grants, access paths, and
  Operator-to-Portal explain controls.
- Updated `ROADMAP.md` to mark Dedicated Portal UI complete and remove Portal
  Explorer expansion from the high-priority queue.

Verification:

- `python -m compileall -q main.py connectors routers`
- `/admin/portal?portal=HC_GDP_SELECT_PRCS_GBL` returned `200`.
- `/api/peoplesoft/object/portal_registry/HC_GDP_SELECT_PRCS_GBL?env=HCM`
  returned `200`.
- `/api/peoplesoft/security/explain-portal?env=HCM&oprid=GUACUSER&portal=HC_GDP_SELECT_PRCS_GBL`
  returned `200`.

### Runtime Graph API

- Added `execution.runtime_graph()` to assemble a best-effort runtime graph from
  existing read-only runtime feeds.
- Added `/api/runtime/graph` with capped process/session limits.
- Runtime graph nodes currently include environment, Integration Broker status,
  PeopleSoft sessions, operators, process instances, process definitions,
  Application Engine programs, process servers, Oracle databases, Oracle
  sessions, SQL IDs, and runtime identities when source data is available.
- Runtime graph edges include environment-to-runtime relationships, operator
  session/process ownership, process instance relationships, IB status
  summaries, Oracle session ownership, and SQL execution relationships.
- Made `PSACCESSLOG` user-session loading column-adaptive so environments
  without `CONNECTDBBNAME` or `TOOLSREL` still return session data.
- Updated `ROADMAP.md` to mark Runtime graph API complete and remove Runtime
  graph from the high-priority queue.

Verification:

- `python -m compileall -q main.py connectors routers`
- `execution.runtime_graph('HCM', process_limit=10, session_limit=10)` returned
  15 nodes, 23 edges, and 0 warnings in the current HCM sample.
- `/api/runtime/graph?env=HCM&process_limit=10&session_limit=10` returned
  `200` with root `environment:HCM`.

### Shared Frontend Shell and Navigation

- Added `/static` frontend assets:
  - `/static/index.html`
  - `/static/app.css`
  - `/static/app.js`
- Mounted static assets in FastAPI with `StaticFiles`.
- Added root `/` route redirecting to `/static/index.html`.
- Added a sticky shared top banner with links to Home, API Docs, Tracing Config,
  Live Events, IB Nodes, Build HCM Graph, and Build FSCM Graph.
- Added active-link highlighting in `/static/app.js` where the current path and
  query string can be matched.
- Added HTML shell injection in `main.py` so existing frontend HTML pages load
  the shared CSS/JS without removing existing routers or API behavior.
- Updated README, Architecture, and Roadmap documentation for the frontend shell
  layer.

Verification:

- `python -m py_compile main.py routers/admin.py routers/tracing.py connectors/uom.py`
  completed successfully. Existing inline-JS regex `SyntaxWarning` messages in
  `routers/admin.py` remain pre-existing.
- Import smoke confirmed `main.app` mounts `/static` and exposes root `/`.
- `/` returned `307` redirecting to `/static/index.html`.
- `/static/index.html` returned `200` and includes `/static/app.css` and
  `/static/app.js`.
- `/admin/` and `/docs` returned `200` with injected shared shell assets.
- `/api/tracing/config` returned JSON without injected frontend assets.
- Required banner targets returned `200`: `/api/live/events` (SSE stream),
  `/api/ib/nodes`, `/api/graph/build?env=HCM`, and
  `/api/graph/build?env=FSCM`.

### Runtime Oracle Sub-Tab Active State Fix

- Fixed `/admin/runtime` Oracle DB sub-tabs so Blocking, Long Ops, and Top SQL
  illuminate when selected.
- Replaced brittle `.card:nth-child(...) .tab` selectors with explicit
  `.proc-tabs .tab` and `.ora-tabs .tab` selectors. This keeps tab highlighting
  stable now that the shared frontend shell injects a sticky banner into admin
  pages.
- Preserved existing pane switching and data-loading behavior.

Verification:

- `python -m py_compile routers/admin.py main.py` completed successfully.
  Existing inline-JS regex `SyntaxWarning` messages in `routers/admin.py`
  remain pre-existing.
- `/admin/runtime` returned `200` and contains `proc-tabs`, `ora-tabs`, and the
  scoped selector calls.

### Security Explorer Mixed-Case Role Permission Lists

- Fixed role-to-permission-list lookup for mixed-case PeopleSoft role names.
- `connectors/psdb.py::role_permissionlists()` now compares
  `upper(rc.rolename) = upper(:rolename)` instead of comparing the stored
  mixed-case role name to an uppercased bind value.
- This restores Security Explorer role selection for roles such as
  `PeopleSoft Administrator`, `PeopleSoft Guest`, and `PeopleSoft HCM User`.

Verification:

- `PeopleSoft Administrator` now returns permission list `PSADMIN`.
- `PeopleSoft Guest` now returns `PTPT1400`.
- `PeopleSoft HCM User` now returns 9 permission lists in HCM.
- Temp HTTP smoke:
  `/api/peoplesoft/roles/PeopleSoft%20Administrator/permissionlists?env=HCM`
  returned `200` with `PSADMIN`.
- `/admin/security` returned `200`.
- Live service restart was attempted but blocked by interactive system
  authentication; restart `deathstar-api` from an authenticated shell to deploy
  the fix on port 8088.

### Graph Explorer Explore Button Fix

- Fixed `/admin/graph` Explore button appearing to do nothing.
- `loadGraph()` referenced `normalizedType` before it was defined, causing a
  JavaScript exception before the graph API call was made.
- Added `const normalizedType = type;` and wrapped graph loading in a visible
  `try/catch` so future API/client failures appear in the status line.

Verification:

- `python -m py_compile routers/admin.py routers/peoplesoft.py` completed
  successfully. Existing inline-JS regex `SyntaxWarning` messages remain
  pre-existing.
- `/admin/graph` returned `200` and contains the fixed `normalizedType`
  assignment and visible `Graph load failed` status path.
- `/api/peoplesoft/graph/component/JOB_DATA?env=HCM` returned `200` with
  58 nodes and 286 edges.

### Object Explorer Open Button Resilience

- Fixed `/admin/object` Open behavior for canonical Object Explorer routes such
  as Component `JOB_DATA`.
- `openTypedObject()` now loads `/admin/object/{type}/{name}` targets in place
  via the existing object API, updates browser history with `pushState`, and
  preserves existing redirects for dedicated routes such as operator/role pages.
- Wrapped object loading in a visible error path so client/API failures update
  the status line instead of leaving the page looking inert.
- Added `popstate` handling for object URLs loaded into the Explorer.
- Fixed Python-template escaping in the Object Explorer PeopleCode/SQL
  highlighters so the generated JavaScript emits regex word boundaries and
  `\\n` correctly. Before this, the served page could contain a literal newline
  inside `sql.indexOf('...')`, causing a parse-time JavaScript error that made
  both Search and Open appear inert.

Verification:

- `python -m py_compile routers/admin.py routers/peoplesoft.py connectors/uom.py connectors/psdb.py`
  completed successfully. The remaining inline-JS regex `SyntaxWarning` in
  `routers/admin.py` is outside Object Explorer.
- Extracted Object Explorer JavaScript from `object_explorer_page()` and
  verified it parses/initializes with QuickJS DOM stubs.
- `object_payload('HCM', 'component', 'JOB_DATA')` returned `status=available`
  with 14 sections.
- `object_payload('HCM', 'record', 'JOB')` returned `status=available` with
  16 sections.
- `/api/peoplesoft/search?env=HCM&q=JOB_DATA` returned 168 results including
  `component:JOB_DATA`.
- `/api/peoplesoft/object/component/JOB_DATA?env=HCM` returned `200` with the
  expected component payload.

### SQL Workspace Sidebar and Schema Search Fix

- Fixed `/admin/sqlws` JavaScript initialization by making the SQL Workspace
  HTML template a raw Python string. This preserves JavaScript escapes such as
  `\\n`, `\\w`, and `\\s` in regex/string literals; before this, the Explain
  Plan renderer emitted a literal newline inside a JavaScript string and caused
  a parse-time failure.
- Restored sidebar tab behavior for Schema, History, and Pinned by allowing the
  page script to initialize successfully.
- Fixed History/Pinned Load actions by replacing inline JSON-stringified SQL in
  `onclick` attributes with index-based row loading from in-memory history
  arrays. This avoids broken HTML attributes when SQL text contains quotes.
- Improved schema browser search ordering and matching:
  - PeopleSoft `PSRECDEFN` results are collected first.
  - `JOB`, `PS_JOB`, and `SYSADM.PS_JOB` all resolve toward `SYSADM.PS_JOB`.
  - SYSADM Oracle catalog objects are preferred ahead of generic SYS objects.
  - Duplicate PeopleSoft/Oracle rows are collapsed in the combined result.

Verification:

- `python -m py_compile routers/admin.py routers/sqlws.py connectors/sqlws.py`
  completed successfully.
- Extracted SQL Workspace JavaScript from `admin_sqlws()` and verified it
  parses/initializes with QuickJS DOM stubs.
- Verified rendered history rows produce valid `loadHistoryItem('historyList',
  index)` handlers and that loading a row updates the SQL textarea.
- `schema_search('HCM', 'JOB', 10)`, `schema_search('HCM', 'PS_JOB', 10)`,
  and `schema_search('HCM', 'SYSADM.PS_JOB', 10)` now return
  `peoplesoft SYSADM PS_JOB RECORD JOB` as the first result.

### SQL Workspace Execute Thread Fix

- Fixed `/api/sqlws/execute` returning plain-text `500 Internal Server Error`
  when executing from the SQL Workspace UI.
- Removed an unsafe cancellation callback that called
  `asyncio.get_running_loop()` from inside the worker thread used by
  `asyncio.to_thread()`. That raised `RuntimeError: no running event loop`
  before the connector could return its normal JSON result.
- Added a JSON error envelope around unexpected execute-router exceptions.
- Updated the SQL Workspace Execute button to check `res.ok` before parsing
  JSON, so any future non-OK response displays a readable request error instead
  of `Unexpected token 'I'`.

Verification:

- `python -m py_compile routers/sqlws.py routers/admin.py connectors/sqlws.py`
  completed successfully.
- Connector execution of the pinned `PSOPRDEFN` query returned 3 rows.
- Live `/api/sqlws/execute` for the same query returned `200 OK` with 3 rows
  and columns `OPRID`, `OPRDEFNDESC`, `EMPLID`, `EMAILID`, `ACCTLOCK`,
  `OPRTYPE`, `LASTSIGNONDTTM`, and `FAILEDLOGINS`.

### SQL Workspace Bind Name Normalization

- Fixed Oracle bind execution for user-friendly bind names that collide with
  Oracle reserved words or pseudocolumns, such as `:rownum`.
- SQL Workspace now rewrites user bind placeholders outside strings/comments to
  safe internal names like `:sqlws_b_1` before sending SQL to Oracle, while
  preserving the original SQL and bind names in history/audit records.
- Added validation for malformed bind names and kept SQL Workspace paging binds
  (`sqlws_rn_s`, `sqlws_rn_e`) reserved.

Verification:

- `python -m unittest tests.test_sqlws_timeout` passed.
- `python -m py_compile connectors/sqlws.py routers/sqlws.py routers/admin.py`
  completed successfully.
- Connector execution of
  `SELECT OPRID, OPRDEFNDESC FROM SYSADM.PSOPRDEFN WHERE ROWNUM <= :rownum`
  with bind `rownum=3` returned 3 rows.
- Live `/api/sqlws/execute` for the same `:rownum` query returned `200 OK`,
  3 rows, and no warnings.

------------------------------------------------------------------------

## 2026-06-29 (continued)

### Component PeopleCode in UOM

- Added PSPCMPROG query to `component_object()` in `connectors/uom.py` for
  objectid1 IN (9, 10) where OBJECTVALUE1 = component name.
  - objectid1=9: component event-level PeopleCode (PreBuild, PostBuild,
    Activate, SavePreChange, SavePostChange, etc.)
  - objectid1=10: component record/field-level PeopleCode (FieldChange,
    FieldDefault, RowInit, etc.)
- Each PSPCMPROG row is normalized with `peoplecode.normalize_program()` to
  produce a canonical reference path and event label.
- Each normalized item gets a `_links.admin` pointing to `/admin/object/peoplecode/{ref}`.
- Added `"peoplecode"` key to `_relationships` and `"peoplecode"` count to
  `_metadata.counts`.
- Added "PeopleCode" section to `sections_for_component()`.

Verification:

- `uom.component_object('HCM', 'GDP_SELECT_PRCS')` returned 7 PeopleCode items
  with proper `reference`, `event`, and `_links.admin` fields.
- `uom.component_object('HCM', 'ABS_NEONATAL_UK')` returned 16 items including
  both objectid1=9 (Activate event) and objectid1=10 (FieldDefault, FieldChange,
  RowInit) entries.
- `/api/peoplesoft/object/component/GDP_SELECT_PRCS?env=HCM` returned 200 with
  "PeopleCode" section showing count=7 after Uvicorn reload.

### Page PeopleCode Normalization

- Replaced `psdb.page_peoplecode_metadata()` (fuzzy multi-table search returning
  raw OBJECTVALUE columns, no objectid1) with a direct PSPCMPROG query per
  parent component.
- For each component that contains the page, queries objectid1 IN (9, 10) with
  OBJECTVALUE1 = component name. Results normalized with `normalize_program()`.
- Each item gets `_source_component` and `_links.admin` for the PeopleCode
  Explorer.
- Capped at 10 parent components and 200 rows per component to bound query cost.

Why: pages do not own PeopleCode directly in PSPCMPROG — PeopleCode is attached
at the component level (objectid1=9/10, OV1=pnlgrpname). The old fuzzy search
returned raw rows with no reference path or explorer links.

Verification:

- `uom.page_object('HCM', 'GDP_SELECT_PRCS')` returned 7 normalized PeopleCode
  items with correct `reference` paths and `/admin/object/peoplecode/...` links.
- `/api/peoplesoft/object/page/GDP_SELECT_PRCS?env=HCM` returned 200 with
  "PeopleCode" section showing count=7 after reload.

### Security Explorer UOM and Permission Decoding Refinements

- Added dynamic-membership sections to Role and Permission List UOM payloads so
  role/permission-list security metadata surfaces more clearly in the explorer.
- Enriched permission-decoding grant paths with permission-list detail and
  decoded authorized actions so security explanations are more actionable.
- Normalized object routing so the explorer uses a single canonical
  `/admin/object/permissionlist/...` route for permission-list aliases.
- Added regression tests for the new UOM and permission-decoding behaviors.

Verification:

- `python -m unittest tests.test_permissionlist_uom tests.test_role_uom_dynamic_membership`
- `python -m unittest tests.test_permission_decoding`
- `python -m unittest tests.test_object_type_normalization`

### Scheduled Graph Snapshots and Retention Pruning

- Added `prune_snapshots(env, keep=7)` to `connectors/graphdb.py`. Deletes
  oldest snapshots per environment, retaining at most `keep`.
- Created `connectors/scheduler.py`: a daemon `threading.Thread` that:
  - Waits 300s after startup before first run (avoids DB load on every restart).
  - Calls `graphdb.build()` then `graphdb.create_snapshot()` for each configured
    environment.
  - Calls `graphdb.prune_snapshots()` to enforce retention.
  - Sleeps 24h between runs.
  - Exposes `start()`, `stop()`, `status()`.
- Wired into FastAPI via `@asynccontextmanager lifespan` in `main.py`.
- Added two endpoints to `routers/graphdb.py`:
  - `GET /api/graph/snapshots/schedule` — returns scheduler status/config.
  - `POST /api/graph/snapshots/prune?keep=N` — manual retention trigger.
  - Both declared before `GET /api/graph/snapshots/{snapshot_id}` to avoid
    route shadowing.

Verification:

- `python -m compileall -q main.py connectors/scheduler.py routers/graphdb.py`
  passed.
- `python -c "import main"` passed.
- After Uvicorn reload: `GET /api/graph/snapshots/schedule` returned 200 with
  `running: true`, `interval_hours: 24`, `retain_count: 7`.
- `POST /api/graph/snapshots/prune?keep=7` returned `{"deleted": [], "count": 0}`
  (no pruning needed with current snapshot count).

### Runtime Graph Visualization

- Added "Runtime Graph" card to `/admin/runtime` (routers/admin.py).
- Card has a "Build Runtime Graph" button that calls
  `/api/runtime/graph?env=HCM&process_limit=60&session_limit=60`.
- Implemented a self-contained force-directed layout in plain JS (Fruchterman-
  Reingold-style: repulsion between all nodes, spring attraction along edges,
  gravity to center). No external dependencies.
- Renders to an inline SVG (100% × 560px) with per-type colored circles,
  edge lines, truncated labels, and a type legend.
- Node type colors: environment (cyan), operator (blue), process (green),
  application_engine (orange), oracle_session (yellow), oracle_database (pink),
  service_operation (purple), process_server (teal), sql_id (red).
- Clicking a node shows label, type, data fields, and an Object Explorer link
  when available.
- Pre-existing JS syntax warning (`\d` in a regex) in admin.py is not from this
  change.

Verification:

- `/admin/runtime` returned 200 after Uvicorn reload.
- Page source contains `loadRtGraph`, `rtForce`, `rtRender`, "Runtime Graph" (9 matches).
- `/api/runtime/graph?env=HCM&process_limit=20&session_limit=20` returned 25 nodes
  and 43 edges (environment, ib_status, integration_broker, operator, ps_session types).

### Richer Knowledge Graph UI — Visual Tab in Graph Explorer

- Added LIST / VISUAL tab bar to `/admin/graph` (the Knowledge Graph Explorer).
- LIST tab: existing text-based node/edge grid + Selected Node panel (unchanged).
- VISUAL tab: force-directed SVG (100% × 580px) using Fruchterman-Reingold-style
  physics — same engine as the Runtime Graph visualization.
- Color map covers all object types: operator, role, permission_list, component,
  page, record, field, portal_registry, application_engine, peoplecode,
  service_operation, node, queue, routing, process, process_server.
- Focal node (first node returned, i.e. the queried object) is rendered larger
  with higher fill-opacity to distinguish it from neighbors.
- Clicking a node shows type, name, data fields, and an "explore" link to its
  Object Explorer page.
- Legend bar shows each node type color and count below the SVG.
- Force simulation (400 ticks) runs eagerly on every `loadGraph()` call; the SVG
  draws on `showTab('visual')` or immediately if Visual is already active.
- All force/render functions (`kgForce`, `kgDrawSvg`, `kgShowDetail`,
  `kgRenderForce`) are self-contained in the page — no external dependencies.

Verification:

- `python -m compileall -q routers/admin.py` passes (only pre-existing `\\d` warning).
- `/admin/graph` returned 200 after Uvicorn reload.
- Page source contains `kgForce`, `kgRenderForce`, `showTab`, `tabVisual` (8 matches).
- All key elements present: `#kgSvg`, `#kgLegend`, `#kgDetail`, `#listView`,
  `#visualView`, `#tabList`, `#tabVisual`, `KG_COLORS`.

### SQL Definition Explorer

- Confirmed `PSSQLDEFN` and `PSSQLTEXTDEFN` are accessible in HCM.
  `PSSQLDDEFN` and `PSSQLRT` are not accessible (grant-aware guards skip them).
- SQLTYPE distribution: 0=SQL Object (7,729), 1=AE SQL Action (38,409),
  2=AE PeopleCode SQL (23,635), 6=Trigger (44).
- DBTYPE distribution: ' '=Generic (69,773), '7'=Oracle (742), '2'=DB2/z (675), etc.
- Added `sql_object()`, `sections_for_sql()`, `sql_payload()` to `connectors/uom.py`.
  - Fetches PSSQLDEFN for definition metadata.
  - Fetches PSSQLTEXTDEFN rows ordered by DBTYPE, SEQNUM; concatenates chunks per DBTYPE.
  - Oracle-specific text (DBTYPE='7') takes priority over Generic (DBTYPE=' ').
  - SQL Source section uses `data.ddl` field so Object Explorer renders it in a `<pre>`.
  - DB Variants section lists all available database types with text lengths.
- Updated `sql_definition` entry in `OBJECT_REGISTRY` (ptmetadata.py) from "planned"
  to live: discovery=PSSQLDEFN/SQLID, search=PSSQLDEFN/SQLID, all 8.5x versions.
- Added `if object_type == "sql_definition":` dispatch in `routers/peoplesoft.py`.
- Added `sql_definition` to `canonical_object()` dispatch in `connectors/uom.py`.
- Added "SQL Definition" option to Object Explorer and Graph Explorer type selectors.

Verification:

- `python -m compileall -q main.py connectors/uom.py connectors/ptmetadata.py
  routers/peoplesoft.py routers/admin.py` passed.
- `uom.sql_object('HCM', 'FORM_INFO')` returned status=available, sql_type=SQL Object,
  1 variant (Generic, 227 chars).
- `uom.sql_object('HCM', 'ACA_MMDD')` returned 5 variants; Oracle variant selected
  for SQL Source.
- `/api/peoplesoft/object/sql_definition/FORM_INFO?env=HCM` returned 200 with
  correct sections.
- `/admin/object/sql_definition/FORM_INFO?env=HCM` returned 200.
- `/api/peoplesoft/search?q=FORM_INFO&env=HCM&types=sql_definition` returned 2 matches.

### SQL %SQL() Cross-References and Environment Comparison Extensions

**SQL AE cross-references:**
- Added `xref_ae` section to `sql_object()` in `connectors/uom.py`.
- Queries PSSQLTEXTDEFN for SQLTYPE=1 (AE SQL action) rows where SQLTEXT LIKE
  `%\%SQL(SQLID)%` ESCAPE `\` — finds AE steps using `%SQL()` meta-SQL substitution.
- Parses the AE SQL step SQLID format (`APPLID SECTION STEP T`) to extract
  `ae_applid`, `ae_section`, `ae_step`; adds `_links.admin` pointing to the AE Explorer.
- Added "AE References" section to `sections_for_sql()`.

Why: standalone SQL objects are reused via `%SQL(SQLID)` in AE SQL steps. Previously there
was no way to discover which AE programs depend on a given SQL object.

Verification:
- `uom.sql_object('HCM', 'ACA_MMDD')` returned 6 AE references across ACA_EXTRACT.
- `/api/peoplesoft/object/sql_definition/ACA_MMDD?env=HCM` returned "AE References"
  section with 6 items after Uvicorn reload.
- `uom.sql_object('HCM', 'FORM_INFO')` returned 0 AE references (correct).

**Environment comparison extensions:**
- Added `compare_peoplecode(env1, env2, q, limit)` to `connectors/envcompare.py`.
  Groups PSPCMPROG by (OBJECTID1, OV1..5), takes MAX(LASTUPDDTTM) per program, diffs
  across environments. Filter by parent object name (e.g. record or component) to scope.
- Added `compare_sql_definitions(env1, env2, q, limit)` to compare PSSQLDEFN.
- Added `compare_portals(env1, env2, q, limit)` to compare PSPRSMDEFN.
- Updated `summary()` to include counts for PeopleCode programs (85K in HCM),
  SQL definitions (69K), and Portal entries (20K).
- Added three new router endpoints:
  - `GET /api/envcompare/peoplecode`
  - `GET /api/envcompare/sql_definitions`
  - `GET /api/envcompare/portals`
- Added three new tabs (PeopleCode, SQL Defs, Portals) to `/admin/envcompare`.
  Each tab has a filter input + Compare button. The PeopleCode tab shows a guidance
  note explaining the key structure and the 500-row cap.

Verification:
- `compare_peoplecode('HCM', 'HCM', q='JOB', limit=10)` → 10 identical, 0 diff.
- `compare_sql_definitions('HCM', 'HCM', q='FORM', limit=10)` → 10 identical.
- `compare_portals('HCM', 'HCM', q='HC_GDP', limit=10)` → 0 identical, 0 diff (no match).
- All three `/api/envcompare/` endpoints returned 200 after Uvicorn reload.
- `/admin/envcompare` returned 200; page contains 20 matches for new tab/pane identifiers.

------------------------------------------------------------------------

### Field Label Resolution

Record objects now include `longname` and `shortname` for every field, resolved
from `PSDBFLDLABL` (with `DEFAULT_LABEL=1`).

Background: `PSDBFIELD` in this HCM environment lacks `LONGNAME`/`SHORTNAME`
columns entirely. `PSDBFLDLABL` holds per-language, per-record, per-field labels
with a `DEFAULT_LABEL` flag identifying the canonical label row.

Changes:
- Added `field_labels_batch(env_name, fieldnames)` to `connectors/psdb.py`.
  Accepts a list of field names; returns a `{fieldname: {longname, shortname}}`
  dict in a single `IN (...)` query against `PSDBFLDLABL WHERE DEFAULT_LABEL=1`.
  Returns empty dict gracefully if the table is absent (grant-aware via
  `table_columns()`).
- Enriched `record_object()` in `connectors/uom.py`: after fetching fields from
  `record_fields()`, calls `field_labels_batch()` in a try/except and merges
  `longname`/`shortname` into each field dict.

Verification:
- HTTP: `GET /api/peoplesoft/object/record/JOB?env=HCM` returns all 107 JOB
  fields with label data:
  - EMPLID → longname="Empl ID", shortname="ID"
  - EFFDT → longname="Effective Date", shortname="Eff Date"
  - EMPL_RCD → longname="Empl Record", shortname="Empl Record"

------------------------------------------------------------------------

### Security Operator Comparison

Added an operator diff endpoint and UI to the Security Explorer, allowing
side-by-side comparison of two PeopleSoft OPRIDs.

Changes:
- Added `GET /api/peoplesoft/security/compare-operators?env=&oprid1=&oprid2=`
  in `routers/peoplesoft.py`. Fetches roles (`PSROLEUSER`), permission lists
  (`PSROLECLASS` via `oprid_permissionlists()`), and components (`PSAUTHITEM`
  via `oprid_components()`) for both operators. Returns set diffs:
  `{only_in_oprid1, only_in_oprid2, shared, counts}` for each category.
- Added `compareOperators()` async JS function to the Security admin page
  (`/admin/security`). Reads `operatorSearch` (existing) and `compareOprid`
  (new) inputs; calls the endpoint and renders color-coded diff HTML into
  `#accessSummary`: orange for items exclusive to oprid1, blue for items
  exclusive to oprid2, green checkmark for identical totals.
- Added `<input id="compareOprid">` and `<button onclick="compareOperators()">
  Compare Operators</button>` to the security page toolbar.

Verification:
- `GET .../compare-operators?oprid1=PTDOMAINADMIN&oprid2=PJOHNSON&env=HCM`
  returned 200:
  - roles: 2 shared, 3 only PTDOMAINADMIN, 4 only PJOHNSON
  - permission_lists: 3 shared, 2 only PTDOMAINADMIN, 3 only PJOHNSON
  - components: 113 shared, 0 only PTDOMAINADMIN, 3 only PJOHNSON

------------------------------------------------------------------------

### AE Step SQL Text Viewer

AE object pages now include a "SQL Steps" section that shows the actual SQL
text for every AE step that has an executable statement.

Background: `PSAESTEPDEFN` provides step metadata but carries no SQL text
(and `AE_ACTTYPE` is absent in this HCM environment). The actual SQL text
lives in `PSSQLTEXTDEFN` (SQLTYPE=1), linked through `PSAESTMTDEFN` which
maps `(AE_APPLID, AE_SECTION, AE_STEP)` → `SQLID`.

Changes:
- Added `ae_sql_step_text(env, ae_applid)` to `connectors/ae.py`.
  Queries `PSAESTMTDEFN` (latest EFFDT per step, DBTYPE=' ', MARKET='GBL'),
  collects all non-empty `SQLID`s, batch-fetches from `PSSQLTEXTDEFN`
  (SQLTYPE=1, DBTYPE IN (' ', '7'), Oracle variant preferred), concatenates
  chunks by SEQNUM. Returns `{(section, step): [{stmt_type, sql_text}]}`.
- Updated `ae_object()` in `connectors/uom.py`: calls `ae_sql_step_text()`,
  cross-references each step by native-case `(ae_section, ae_step)` key
  (not uppercased — uppercase is only used for PeopleCode lookup which has a
  separate key), attaches `sql_statements` list and `has_sql=True` flag.
- Updated `sections_for_ae()` in `connectors/uom.py`: builds "SQL Steps"
  section with one item per `(step, stmt_type)` carrying `data.ddl` for the
  existing `<pre>` code rendering path in the Object Explorer.

Verification:
- `ae_sql_step_text('HCM', 'ACA_EXTRACT')` → 127 entries, 0 warnings.
- `ae_object('HCM', 'ACA_EXTRACT')` steps section: 135 steps, 112 with
  `has_sql=True`; SQL Steps section: 127 items.
- HTTP: `GET /api/peoplesoft/object/application_engine/ACA_EXTRACT?env=HCM`
  returned 200 with "SQL Steps" count=127, first entry:
  `MAIN.Step025 [Do Select]: %Select(ACA_EXTRACT_AET.NUM_ROWS) SELECT ...`

------------------------------------------------------------------------

### Rich Record Dependency Traversal

Record object pages now include three new dependency sections that show what
uses or derives from a given record.

Background: The existing record UOM shows which components and pages use a
record. This extends it upstream (what records are based on this record) and
sideways (what AE programs treat this as state/work storage).

Changes:
- Added `record_usages(env_name, recname)` to `connectors/psdb.py`.
  Uses `table_columns()` guards (not `has_table` — that lives in ptmetadata,
  not psdb) before each query:
  - **Child Records**: `PSRECDEFN WHERE PARENTRECNAME = recname` — records
    that extend or specialize this record as their parent.
  - **AE State Records**: `PSAEAPPLSTATE WHERE UPPER(AE_STATE_RECNAME) = recname`
    — AE programs using this as a state/work record, with deep link to AE Explorer.
  - **Subrecord Derivations**: `PSRECFIELD JOIN PSRECDEFN WHERE DEFRECNAME = recname`
    — records that inherit fields from this record via subrecord inclusion.
  All queries cap at 100 rows and deep-link to admin object pages.
- Updated `record_object()` in `connectors/uom.py`: calls `record_usages()`
  with try/except and adds `child_records`, `ae_state_records`,
  `subrecord_derivations` to `_relationships`.
- Updated `sections_for_record()` in `connectors/uom.py`: added three new
  sections — "Child Records", "Subrecord Derivations", "AE State Records".

Verification:
- `record_usages('HCM', 'JOB')` → 70 child records, 0 AE state records,
  100 subrecord derivations.
- `record_usages('HCM', 'ACA_BAC020_AET')` → 0 child, 2 AE programs
  (ACA1095CA, ACA1095CB), 0 subrecord.
- HTTP: `GET /api/peoplesoft/object/record/JOB?env=HCM` returned 200 with
  Child Records=70 (first: ADDL_HB_ARG), Subrecord Derivations=100 (first:
  ACCOM_DIAGNOSIS), AE State Records=0.

------------------------------------------------------------------------

### Security Reports

Added a suite of canned security audit reports accessible via API and UI.

Changes:
- Added `security_report(env_name, report_type, limit)` to `connectors/psdb.py`.
  Runs one of 6 parameterized SQL reports and returns `{title, columns, rows, note,
  available_reports}`. Reports:
  - `empty_roles` — roles in PSROLEDEFN with zero PSROLEUSER rows
  - `unused_permission_lists` — PSCLASSDEFN entries not in PSROLECLASS
  - `top_operators_by_roles` — operators ranked by role count (joins PSOPRDEFN for email)
  - `top_roles_by_users` — roles ranked by user count
  - `permission_list_role_coverage` — permission lists ranked by role usage
  - `locked_operators` — operators with ACCTLOCK > 0
- Added `GET /api/peoplesoft/security/reports?env=&report=&limit=` endpoint
  in `routers/peoplesoft.py`.
- Added a "Security Reports" card at the bottom of `/admin/security`:
  dropdown selector for report type, limit input, "Run Report" button,
  results rendered as a styled table with deep links on rolename/classid/oprid values.

Verification:
- `security_report('HCM', 'empty_roles', limit=5)` → 5 rows, no error.
- HTTP: `GET .../security/reports?report=top_operators_by_roles&limit=3`
  → PSFED (621 roles), JARED (604), NODE_USER (603).
- `/admin/security` returned 200; page contains 8 report-UI element references.

------------------------------------------------------------------------

### Object Explorer Breadcrumbs

The Object Explorer (`/admin/object/{type}/{name}`) now shows a breadcrumb
trail above the object title when an object is loaded.

Changes:
- Added `<nav id="breadcrumb">` div above `<h2 id="objectTitle">` in
  `routers/admin.py`'s `object_explorer_page()`.
- Added `buildBreadcrumbs(type, name)` JS function that generates
  typed breadcrumb HTML:
  - All objects start with `Admin › Object Explorer`
  - Each object type maps to its canonical home section:
    Records, AE Programs, Security (Operators/Roles/Permission Lists),
    Portal Registry, Integration Broker (Services/Nodes/Queues/Routings), etc.
  - For `field` objects with a dotted name (e.g., `JOB.EMPLID`):
    inserts the parent record as an intermediate breadcrumb with a deep link.
  - Name segments are plain text; group segments are hyperlinked.
- Updated `renderObject()` to call `buildBreadcrumbs()` and show the nav.

Verification:
- `/admin/object/record/JOB` HTML contains 5 breadcrumb element references.
- Breadcrumb for a record: `Admin › Records › JOB`
- Breadcrumb for a field `JOB.EMPLID`: `Admin › Fields › JOB › EMPLID`
- Breadcrumb for an AE: `Admin › AE Programs › ACA_EXTRACT`

------------------------------------------------------------------------

### SQL Definition Type Filter

SQL Definition search now supports SQLTYPE filtering so users can find
standalone SQL objects separately from AE SQL actions.

Background: PSSQLDEFN SQLTYPE values: 0=Standalone SQL, 1=AE SQL Action,
2=AE PeopleCode SQL, 6=Trigger. HCM has ~7.7K standalone, ~38K AE SQL,
~23K PeopleCode SQL, 44 triggers. Without a filter, searching `ACA_MMDD`
returns both the standalone definition and any AE step definitions.

Changes:
- Added `search_sql_definitions(env_name, q, sqltype, limit)` to
  `connectors/psdb.py`. Uses `table_columns()` (lowercase keys) to build
  the SELECT list, applies optional `AND SQLTYPE = :sqltype` clause, returns
  rows enriched with `sqltype_label` (from `_SQL_TYPE_LABELS` dict).
- Added `GET /api/peoplesoft/sql_definitions?env=&q=&sqltype=&limit=` endpoint
  in `routers/peoplesoft.py`. `sqltype` defaults to blank (all); if numeric,
  filters to that type. Returns rows with `_links.admin` set.
- Added SQL type filter UI to Object Explorer: when the type selector is set
  to `sql_definition`, a `<select id="sqlTypeFilter">` and "Search SQL" button
  appear via JS `change` event listener. `searchSqlDefinitions()` calls the
  new endpoint and renders results in the Search Results panel.

Verification:
- `search_sql_definitions('HCM', 'ACA_MMDD', limit=5)` → 2 rows (ACA_MMDD,
  ACA_MMDD_CMN), both labeled "Standalone SQL".
- `search_sql_definitions('HCM', '', sqltype=1, limit=3)` → AE SQL Actions.
- HTTP: `GET /api/peoplesoft/sql_definitions?sqltype=1&limit=3` → 3 AE SQL rows.
- Object Explorer HTML contains 5 `sqlTypeFilter`/`searchSqlDefinitions` references.

------------------------------------------------------------------------

### Recently Viewed Enhancements

The Object Explorer's "Recently Viewed" panel now shows descriptions, relative
timestamps, and per-item remove buttons.

Changes in `routers/admin.py` (`object_explorer_page()`):
- Added `relativeTime(ts)` helper: converts epoch milliseconds to "just now",
  "Xm ago", "Xh ago", or "Xd ago".
- Updated `pushRecent(type, name, title, description)` to accept and store a
  `description` field (sourced from `object.overview.description` in `loadObject()`).
- Added `removeRecent(type, name, event)` function that removes a single entry
  from `localStorage` and re-renders.
- Updated `renderRecentList()`:
  - Flex layout per entry (name + timestamp left, × button right).
  - Shows description below the name (truncated with `text-overflow:ellipsis`)
    when it differs from the name/title.
  - Shows relative timestamp ("5m ago") in muted text.
  - Each entry has a `×` remove button that stops click propagation.

Verification:
- `/admin/object/record/JOB` HTML contains 6 references to
  `relativeTime`/`removeRecent`/`pushRecent`.

------------------------------------------------------------------------

### SQL Syntax Highlighting in Object Explorer

All SQL content in the Object Explorer now renders with syntax highlighting
instead of plain text.

Changes in `routers/admin.py` (`object_explorer_page()`):
- Added `highlightSQL(sql)` tokenizer function. Uses a hand-rolled tokenizer
  (block comments, line comments, single-quoted strings, code segments) to
  avoid regex-based false positives. Color scheme:
  - SQL keywords (SELECT/FROM/WHERE/JOIN/etc.) → blue (`#569cd6`)
  - PeopleSoft meta-SQL (%Table/%Bind/%Select/etc.) → purple (`#c586c0`)
  - String literals → orange (`#ce9178`)
  - Comments → green (`#6a9955`)
  - Numbers → light green (`#b5cea8`)
- Updated section renderer: changed `pre.textContent = section.data.ddl` to
  `pre.innerHTML = highlightSQL(section.data.ddl)` for DDL sections (Record
  DDL, SQL Definition source).
- Updated `renderRows()`: items that carry `row.data.ddl` (e.g., AE SQL Steps)
  now render an inline `<pre>` with `highlightSQL()` below the item title.

Verification:
- `/admin/object/record/JOB` HTML contains 3 `highlightSQL` references.
- SQL Definition objects show colored keywords in their SQL Source section.
- AE object SQL Steps show inline highlighted SQL under each step row.

------------------------------------------------------------------------

### SQL Workspace Autocomplete and Typed Bind Parameters

**SQL Autocomplete** (`routers/admin.py` — `admin_sqlws()`):

- Added `<div id="sqlAC">` fixed-position overlay with `position:fixed;z-index:9999` — appears below the SQL textarea when triggered.
- `_tokenBeforeCursor()`: extracts the current word from the textarea before the cursor (including dots).
- `_acContext()`: determines whether the token is a table reference (no dot, ≥2 chars → `{type:"table", prefix}`) or a column reference (contains dot → `{type:"column", qualifier, prefix}`).
- `_extractAliases(sql)`: regex over FROM/JOIN clauses to build `alias → table` map (skips SQL keywords).
- `_fetchAC(ctx)`: calls `/api/sqlws/schema/search` for table completion; calls `/api/sqlws/schema/SYSADM/{table}/columns` for column completion after resolving the qualifier via alias map. Column results are cached per `env|table`.
- `_showAC()`: positions dropdown using `getBoundingClientRect()`, renders items with label + detail; `_acCommit(i)` splices the selected token into the textarea at cursor position.
- Keyboard: ArrowUp/Down to navigate, Enter/Tab to commit (when item selected), Escape to close, Ctrl+Space to trigger manually.
- Fires automatically on `input` (debounced 200ms) when token ≥2 chars; hides on `blur` with 150ms delay.
- Hint label "Ctrl+Space to autocomplete" added to SQL Query label.

**Typed Bind Parameters** (`routers/admin.py` — `admin_sqlws()`):

- Replaced raw JSON `<textarea id="bindsInput">` with a structured editor `<div id="bindsEditor">`.
- Each bind is a row: `[name input] [value input] [× remove button]`.
- `addBind(name, val)`: creates a new bind row.
- `clearBinds()`: removes all rows.
- `setBinds(obj)`: clears and repopulates from a `{name: value}` object.
- `bindsObj()`: iterates `.bind-row` elements, strips leading `:` from names, returns `{name: value}` dict.
- `_detectBinds(sql)`: regex-scans SQL for `:name` placeholders, adds missing ones as empty rows — fires automatically on SQL input (debounced 400ms) and when loading from history.
- History "Load" now passes saved binds as second argument to `loadQueryFromHistory(sqlJson, bindsJson)`, restoring bind rows from history.
- CSS: `.bind-row`, `.bnd-name`, `.bnd-val`, `.bnd-rm` with monospace styling consistent with the dark theme.

Verification:
- `admin_sqlws()` HTML contains `bindsEditor`, `addBind`, `clearBinds`, `setBinds`, `_detectBinds`, `bnd-name` (CSS), and no `bindsInput`.
- `admin_sqlws()` HTML contains `sqlAC`, `_acTrigger`, `_extractAliases`, and `Ctrl+Space` hint text.
- Schema browser API confirmed: table search returns `PSOPRDEFN` etc., column search returns `OPRID, OPRDEFNDESC, EMPLID` for `PSOPRDEFN`.

------------------------------------------------------------------------

### PS Query Explorer

Added full PS Query object type support via the UOM pattern:

**`connectors/ptmetadata.py`**:
- Replaced the "planned" stub for `"query"` in the fallback loop with a proper
  `OBJECT_REGISTRY.setdefault("query", {...})` entry pointing to `PSQRYDEFN`
  with `provider: "query"` search config.
- Added `provider: "query"` branch in `global_search()` that filters
  `WHERE OPRID = ' '` (public/shared queries only) when searching `PSQRYDEFN`.

**`connectors/uom.py`**:
- `query_object(env, qryname)`: fetches definition from `PSQRYDEFN` (public
  only, `OPRID=' '`), records from `PSQRYRECORD` (with join types and
  correlation name aliases), output columns from `PSQRYFIELD` (with heading,
  aggregate function, record resolution), and prompt parameters from
  `PSQRYBIND` (with field type labels). All tables guarded with
  `ptmetadata.has_table()` + `psdb.select_existing_columns()`.
- `sections_for_query(q_obj)`: renders Overview, Records Used (join type +
  alias per record), Output Columns (column position, heading, aggregate,
  RECNAME.FIELD display), and Prompt Parameters (bind name, type, related
  field).
- `query_payload(q_obj)`: standard UOM payload envelope.
- `canonical_object()`: added `if object_type == "query": return query_object()`
  dispatch.

**`routers/peoplesoft.py`**:
- Added `if object_type == "query"` dispatch in `object_payload()`, returning
  `uom.query_payload(uom.query_object(...))`.

**`routers/admin.py`**:
- Added `<option value="query">PS Query</option>` to both the Graph Explorer
  type selector and the Object Explorer type selector.

Verification:
- `query_object('HCM', 'OPRDEFN2')`: status=ok, 1 record, 2 output columns.
- `query_object('HCM', 'FPA_JOB_SUM')`: status=ok, 5 records with join types,
  17 output columns, 2 prompt parameters.
- `GET /api/peoplesoft/object/query/FPA_JOB_SUM?env=HCM`: 200 OK, sections
  `['Overview', 'Records Used (5)', 'Output Columns (17)', 'Prompt Parameters (2)']`.
- Global search `?q=FPA_JOB`: returns `query: FPA_JOB_SUM | FPS Job Data`.

------------------------------------------------------------------------

### PS Queries Tab — Environment Comparison

Added a PS Queries comparison tab to `/admin/envcompare`:

**`connectors/envcompare.py`** (already complete):
- `compare_queries(env1, env2, q, limit)`: diffs `PSQRYDEFN` public queries
  (`OPRID=' '`) between two environments by `QRYNAME`, comparing `DESCR`,
  `QRYTYPE`, `QRYFOLDER`, `QRYDISABLED`, `LASTUPDDTTM`.
- `summary()`: includes `PS Queries` count query.

**`routers/envcompare.py`** (already complete):
- `GET /api/envcompare/queries`: public diff endpoint.

**`routers/admin.py`**:
- Added "PS Queries" tab button after "Portals" in the envcompare tab row.
- Added `<div id="pane-queries">` with `<input id="queryQ">`, Compare button,
  spinner, and result div.
- Updated `TABS` constant to include `'queries'` between `'portals'` and `'graph'`.
- Added `queries: 'queryQ'` to `Q_IDS` map so `runCompare('queries')` picks
  up the filter input.

------------------------------------------------------------------------

### SQL Workspace — Timeout and Cancellation

Added server-side call timeout and client-side cancel support:

**`connectors/sqlws.py`**:
- `MAX_TIMEOUT_SECS = 600` constant.
- `_normalize_timeout_secs(seconds)`: clamps to `[0, MAX_TIMEOUT_SECS]`.
- `execute_query()`: accepts `timeout_secs` and `cancel_check` parameters.
  Sets `cursor.callTimeout = timeout_secs * 1000` when driver supports it.
  Catches `oracledb.Error` with DPI-1067 or "call timeout" message to set
  `timed_out=True, status="timeout"`. Cancellation detected via `cancel_check`
  callable or oracle "cancel/abort" error message.
- Result dict includes `timed_out`, `cancelled`, and `status` fields.
- History entries record `timed_out` and `cancelled` flags.

**`routers/sqlws.py`**:
- `ExecuteRequest`: added `timeout_secs: int = 0`.
- `execute_sql()`: now `async`, uses `asyncio.to_thread()` to run the blocking
  DB call without blocking the event loop.
- Pre- and post-execution `request.is_disconnected()` checks set `cancelled`
  flag when the HTTP client aborts before or after the query runs.

**`routers/admin.py`** (SQL Workspace UI):
- Added Cancel button (`id="cancelBtn"`, hidden while idle) next to Execute.
- Added Timeout selector (`id="timeoutSel"`) with None/10s/30s/60s/2m/5m options
  (default 30s).
- `currentAbortController`: module-level `AbortController` for the live request.
- `_setExecRunning(running)`: toggles Execute disabled state + Cancel button
  visibility.
- `cancelSQL()`: calls `currentAbortController.abort()`.
- `executeSQL()`: creates `AbortController`, passes `signal` to fetch and
  `timeout_secs` to request body; handles `AbortError` to show "Query
  cancelled by user." message without crashing.
- Timing display shows `— TIMED OUT` suffix when `data.timed_out` is set.

------------------------------------------------------------------------

### IB Explorer — Overview Duplication Fix + Services Count

**`routers/admin.py`**:
- `loadDashboard()`: removed the duplicate `<h2>Integration Broker Overview</h2>`
  and stat-grid from the injected HTML — these counts are already in the static
  card (populated via `$('ovSvc').textContent` etc.). The `#dashboard` div now
  only renders live runtime data (Publications/Subscriptions/Domain Status).
- `loadServices()`: increased limit to 500; appended a footer note showing
  "N services — all services (no status filter) · PSIBAPPLDEFN" so users can
  confirm the list is unfiltered (PSIBAPPLDEFN has no EFF_STATUS filter in the
  services query).

------------------------------------------------------------------------

### IB Relationship Explorer Redesign

Rewrote `/admin/ib` from a table-centric tab browser into a relationship
explorer with master-detail navigation.

**Layout**:
- `<div class="explorer">` replaces `.content` — flexbox row with a 290px
  `.list-panel` on the left and a `.detail-panel` (flex:1) on the right.
- All list tabs (`tab-services`, `tab-operations`, etc.) now live inside
  `.list-panel` so the list stays visible when viewing a detail.
- `.detail-panel` contains `#breadcrumb` bar + `#detailScroll > #detailContent`.

**Navigation stack**:
- `navStack[]` tracks the path taken: `[{type, name}, ...]`.
- `pushNav(type, name, push)` adds to the stack and calls `renderBreadcrumb()`.
- `renderBreadcrumb()` renders `IB › &#9881; SVC_OP › &#8652; ROUTING › ...`
  with clickable segments that call `navTo(i)` to jump back.
- `navTo(idx)` slices the stack to idx+1 and re-invokes the appropriate `showXxx()`.
- `clearDetail()` resets stack, restores placeholder, and clears active states.

**All `showXxx()` functions** now:
- Accept optional `push=true` parameter (false when called from breadcrumb nav).
- Call `switchTab()` to show the relevant list tab.
- Call `markActive(listId, name)` to highlight the selected list item.
- Call `setDetail(html)` instead of replacing `contentArea`.
- Start with a `relStrip()` relationship bar showing clickable tags to related
  objects (operation → service + routings + queues + Transactions;
  routing → operation + sender + receiver + Transactions;
  node → related operations + Transactions; queue → Transactions;
  transaction → operation + queue + pubnode).

**Relationship strip**:
- `relStrip(label, tags)` renders a compact horizontal bar at the top of each
  detail view with `rel-tag` buttons for each related object.
- `rel-action` class for "View Transactions" tags (green tint).
- `viewTxnsFor(q)` switches to the Txns tab and prefills the filter with the
  given operation/node/queue name.

**Compact overview**:
- Replaced large `stat-box` elements with `cstat-row` 3-column compact grid
  fitting in the 290px left panel.
- Quick-action buttons are full-width stacked buttons in the left panel.

**Additional click-through fixes**:
- Routing sub-definitions: sender/receiver nodes now clickable.
- Transaction pub/sub contracts: sub nodes and routings now clickable.
- Messages table in operation detail: queue names now clickable.
- Routing table in service detail: sender/receiver nodes now clickable.
- `showNode()` guards against null/undefined names.

------------------------------------------------------------------------

## 2026-06-30

### Navigation Architecture Redesign

Completed a full navigation overhaul of the admin shell (`routers/admin.py`,
`static/app.css`, `static/app.js`).

**`static/app.css`** — full rewrite with design-system tokens:
- `--nav-h: 42px`, `--hdr-h: 46px`, `--bg`, `--panel`, `--line`, `--text`,
  `--muted`, `--cyan` CSS variables.
- `.ds-nav` sticky global navbar; `.ds-page-hdr` per-page header strip;
  `.ds-env` / `.ds-env-sel` environment selector.
- `.ds-content` (scrollable) and `.ds-content.ds-noscroll` (overflow:hidden
  flex-column, for master-detail layouts).
- `.ds-toolbar` for page-specific action bars.
- Preserved `.pe-home`, `.pe-hero`, `.pe-kicker`, `.pe-grid`, `.pe-card` for
  the landing page.

**`static/app.js`** — full rewrite:
- `localStorage['ps_env']` persistence for environment selector across pages.
- `initGlobalEnv()` populates all `.ds-env-sel` selects from
  `/api/sqlws/config` and restores saved selection.
- `syncPageEnvSel(val)` syncs legacy per-page `#envSel` selects.
- `window.dsGetEnv()`, `window.dsSetEnv()`, `window.dsGetStoredEnv()` helpers.

**`routers/admin.py`** — major refactor:
- `_NAV` list + `_shell(title, active, content, env=True, noscroll=False)`
  function replaces per-page HTML boilerplate. One `<!DOCTYPE html>` in the
  entire file.
- Navigation: `Home · Users · Runtime · SQL Workspace · IB Explorer · Env
  Compare · Tools · Docs`.
- New `/admin/users` page (moved user management from `/admin/`).
- New `/admin/` landing page with `.pe-hero` + `.pe-grid` module cards.
- New `/admin/docs` page linking to Swagger UI and ReDoc.
- All 18 page functions use `return _shell(...)`.
- Fixed `noscroll=True` on Runtime Monitor (was preventing scroll through
  stacked Process Scheduler / IB / Oracle sections).
- Removed `body { padding: 40px }` inline overrides that created dead space
  above the nav bar on Home, Runtime, Security, Graph, Portal, Metadata,
  Knowledge Graph, and Object Explorer pages.
- Fixed double `<style>` tag in `object_explorer_page()` (migration artifact).

**Verification:**
- `python -m py_compile routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all core pages return 200.
- All 25 routes registered; server boots clean on port 8088.

------------------------------------------------------------------------

### Object Explorer Visual Hierarchy

Improved the Object Explorer (`/admin/object`) rendering without touching the
UOM or API layer.

**`routers/admin.py`** (JavaScript/HTML/CSS in `object_explorer_page()`):

**Layout change** — the left panel no longer has separate "Overview" and
"Actions" cards. Instead the right panel opens with a single rich
`#objectHeader` (`div.obj-hdr`) card that shows:
- Type chip (color-coded, using `TYPE_CHIP_CFG`) + monospace object name.
- Description subtitle (from `overview.description`).
- Up to 12 key-value pairs from the object overview (`.kv-grid`/`.kv-key`/
  `.kv-val` from `app.css`; skips `id`, `display_name`, `description`,
  `status`).
- Action links as compact button chips (`div.obj-hdr-actions > a`).
- Section count in small muted text.

**Section cards**:
- `<h2>` now includes a `span.count-badge` when `section.items.length > 0`
  (e.g., "Fields (24)", "Pages (75)").
- Sections containing DDL or PeopleCode source get class `section-wide`
  which spans both columns of the `.sections` grid (`grid-column: 1 / -1`).
- The "Warnings" section gets class `section-warn` (amber border + amber h2).

**`renderKeyValues(target, data)`** — replaced custom `<dl>/<dt>/<dd>` with
`.kv-grid`/`.kv-key`/`.kv-val` from `app.css`; also filters out null/empty
values and skips `ddl`/`source` keys.

**`renderRows(target, rows)`** — each row now renders:
- `div.row-header` flex container holding a `span.rel-chip` (if
  `row.relationship` is set) + the title span + a `span.row-arrow` (→) for
  clickable rows.
- The old `"relationship: labelFor(row)"` prefix text replaced by the chip.

**`renderActions()`** — stubbed (logic folded into `renderObject()`).

New CSS classes: `.obj-hdr`, `.obj-hdr-row`, `.obj-hdr-name`, `.obj-type-chip`,
`.obj-hdr-desc`, `.obj-hdr-actions`, `.count-badge`, `.section-wide`,
`.section-warn`, `.row-header`, `.rel-chip`, `.row-arrow`.

**Verification:**
- `python -m py_compile routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all core pages pass (including `/admin/object`).
- `GET /admin/object/record/PSRECDEFN`: obj-hdr, type chip, description,
  kv-grid, action links, count badges on Fields/Keys/Indexes sections, DDL
  section spans full width.
- API `GET /api/peoplesoft/object/record/PSRECDEFN?env=HCM` — 15 sections,
  unchanged shape.

### Portal Registry — Rich Reconstruction

Improved `sections_for_portal_registry()` in `connectors/uom.py` and the
generic row renderer in `routers/admin.py`.

**`connectors/uom.py`**:

- `_portal_label_items(items, use_reftype_chip=False)` — new helper that adds
  `title` (portal_label → classid → pnlgrpname → portal_permname → rolename →
  roleuser → portal_objname) and optionally sets `relationship` to the decoded
  reftype label (Folder / Content Reference) for use as a renderer chip.

- `_portal_access_summary(access_paths)` — new helper that groups the flat
  permission-list→role→operator rows into one summary row per permission list,
  with `roles` count, `operators` count, and a `via_roles` sample string. Turns
  152+ flat rows into 3–5 grouped rows.

- `sections_for_portal_registry()` — updated:
  - "Breadcrumbs" renamed to **"Navigation Path"**; items get titles from
    `portal_label` and a "Folder"/"Content Reference" chip via `relationship`.
  - "Children" items get human-readable `title` from `portal_label` and a
    reftype chip.
  - **"Access Paths"** section replaced by **"Who Has Access"** — 3-column
    grouped summary (permlist → roles → operators). Original raw paths still
    in `_relationships` for the graph layer.
  - "Portal Security" items get `relationship` chip from `portal_permtype_label`
    (Permission List / Role).
  - "Definition" data now includes `navigation_path` — a `→`-separated string
    of ancestor folder labels all the way to the current item.
  - Children data includes `folders` and `content_refs` counts.
  - Empty sections (0 items, no meaningful data) filtered from the output.

**`routers/admin.py`** (Object Explorer JS):

- `labelFor(row)` — now checks `row.title` and `row.label` before falling back
  to specific field names; applies to all object types.
- `_DETAIL_SKIP` — added `title`, `label`, `portal_permtype_label`,
  `portal_reftype_label`, `portal_reftype`, `portal_permtype` so those
  helper fields don't clutter the detail text line.

**Verification:**
- `python -m py_compile connectors/uom.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/portal_registry/EOEC_CCI_INSTAL?env=HCM` —
  "Navigation Path" (5 items, each with portal_label title + reftype chip),
  "Who Has Access" (3 rows: EOCO9000 1 role 6 ops, EOEC9000 1 role 141 ops,
  EOEC9010 1 role 5 ops), Definition.navigation_path shows full ancestor trail.
- `GET /api/peoplesoft/object/portal_registry/EOCO_EOEC?env=HCM` — folder
  object: "Children" shows 9 items (5 folders, 4 content refs) with human
  labels and reftype chips.

### Access-Path Visualization — Component, Page, Permission List

Improved access-path and permission decoding display across three UOM object types.

**`connectors/uom.py`**:

- `_portal_access_summary()` generalized into `_access_summary(access_rows, ...)` —
  groups flat permlist→role→operator rows into one row per permission list,
  collecting role count, operator count, role sample, and unique `decoded_actions`.
  `_portal_access_summary` kept as backward-compatible alias.

- `sections_for_component()` — "Security" (flat 158-row list) replaced by
  **"Who Has Access"** (3 grouped rows, one per permission list) using
  `_access_summary()`; each row shows classid, roles count, operators count,
  and `actions` field for the granted permissions (Update/Display, Add, etc.).
  "Permission Lists" section items now carry a `relationship` chip decoded from
  `authorizedactions` (Update/Display / Add, Update/Display / etc.).

- `sections_for_page()` — "Security" (flat 158-row list) replaced by
  **"Who Has Access"** using `_access_summary()`.

- `sections_for_permissionlist()` — "Components" items now carry a
  `relationship` chip from each row's `decoded_actions` list.

**`routers/admin.py`** (Object Explorer JS):

- `_DETAIL_SKIP` — added `authorizedactions`, `displayonly`,
  `raw_authorizedactions`, `raw_displayonly`, `pnlitemname`,
  `target_portal_objname`, `portal_iscascade` to eliminate noise from
  permission-decoded rows.

**Verification:**
- `python -m py_compile connectors/uom.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/component/EOEC_CCI_INSTAL?env=HCM` —
  "Permission Lists": [EOCO9000 chip=Update/Display, EOEC9000 chip=Update/Display,
  EOEC9010 chip=Add, Update/Display]; "Who Has Access": [EOCO9000 6 ops,
  EOEC9000 141 ops, EOEC9010 5 ops] — 3 rows vs prior 158 flat rows.
- `GET /api/peoplesoft/object/permissionlist/EOCO9000?env=HCM` — "Components":
  items have action chips (Update/Display / Add, Update/Display).

### AE Runtime Detail — Instance Deep-Linking

Enhanced AE Object Explorer Runtime Instances section and added process instance
deep-linking between the AE Object Explorer and the Runtime Monitor.

**`connectors/ae.py`** — `runtime_instances()`:
- Each item now gets `title = f"#{prcsinstance}"` so `labelFor()` shows the
  instance number instead of falling through to `oprid`.
- `relationship = runstatus_label` — status chip (Success / Error / Hold /
  Queued) shown as a colored chip next to the instance number.
- `_links.admin = f"/admin/runtime?instance={prcsinstance}"` — deep-link to
  the Runtime Monitor's process detail panel.
- `duration` field computed from `begindttm`/`enddttm` when both are present
  (e.g., "15s", "2m 30s", "1h 5m").

**`routers/admin.py`** (Runtime Monitor init):
- Added `URLSearchParams` parsing in the runtime page init block.
- `?env=ENV` selects the correct environment on load.
- `?instance=N` auto-invokes `showProc(N)` after data loads, opening the
  process detail slide-in panel directly.
- `_DETAIL_SKIP` expanded with `runstatus`, `runstatus_label`, `prcstype`,
  `prcsname`, `runlocation`, `outdesttype`, `outdestformat` to suppress noise
  from runtime rows.

**Verification:**
- `python -m py_compile connectors/ae.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/application_engine/PSPM_REAPER?env=HCM` —
  Runtime Instances: 20 items, first 3 show title=#606394, chip=Success,
  duration=15s, _links.admin=/admin/runtime?instance=606394.
- Deep-link `/admin/runtime?instance=606394` supported by URL param handler.

---

## 2026-06-30 — Application Package UOM (Priority #8)

**What changed:**
- `connectors/peoplecode.py` — corrected objectid1=104 from "Handler (IB new)" to "App Package Class". Updated `PEOPLECODE_OBJECT_TYPES`, `_OID1_PARENT_TYPES`, and `decode_semantic_path()` to properly parse the variable-depth path structure (OV1=packageroot, OV2..OVn-1=qualifypath segments, OVn=OnExecute).
- `connectors/ptmetadata.py` — wired `application_package` in `OBJECT_REGISTRY` with real PSPACKAGEDEFN discovery/search; added `app_package` custom search provider in `global_search()` (searches PACKAGEROOT + DESCR, returns root-level packages distinct). Also wired `application_class` with PSAPPCLASSDEFN discovery.
- `connectors/uom.py` — added `app_package_object()`, `sections_for_app_package()`, `app_package_payload()`. Sections: Definition (PSPACKAGEDEFN PACKAGELEVEL=0), Sub-Packages (PACKAGELEVEL>0), Classes (PSAPPCLASSDEFN with qualifypath+classid), PeopleCode (PSPCMPROG objectid1=104 grouped by class).
- `routers/peoplesoft.py` — added `application_package` branch to canonical object dispatcher calling `app_package_payload()`.
- `routers/admin.py` — added App Package option to Object Explorer and Graph Explorer selectors; updated `inferObject()` for packageroot, `labelFor()` for packageroot+appclassid, `_DETAIL_SKIP` for packageroot/appclassid/qualifypath/full_path; added TYPE_CHIP_CFG entries for application_package and application_class.

**Data confirmed:**
- PSPACKAGEDEFN: 4245 rows, PSAPPCLASSDEFN: 12622 rows — both accessible
- objectid1=104 in PSPCMPROG: 15300 programs — ALL are App Package class PeopleCode (not IB handlers; IB handler classes ARE app classes)
- Largest packages: HRS_CANDIDATE_MANAGER (303 classes), PTUNI_REVIEW (256), HCR_PERSON_SERVICES (250)
- HRS_COMMON: 91 sub-packages, 170 classes, 160 PeopleCode programs

**Live test results:**
- `/api/peoplesoft/object/application_package/HRS_COMMON?env=HCM` → 4 sections, 170 classes ✓
- Global search "HRS_CANDID" → application_package HRS_CANDIDATE_MANAGER score=66 ✓
- Object Explorer `/admin/object/application_package/HRS_COMMON` → renders with "App Package" chip ✓

---

## 2026-06-30 — AE Restart Eligibility, SQL PeopleCode Cross-Reference, Portal Object Comparison

### AE Restart Eligibility (Priority #6 completion)
- `ae.state_records()` was broken — required column `RECNAME` but actual column is `AE_STATE_RECNAME` (column names vary by PeopleTools version). Fixed to accept both `AE_STATE_RECNAME` / `RECNAME` / `AE_DEFAULT_STATE` / `AE_ISBASESTATE` and normalize into consistent `recname`, `title`, `is_default`, `relationship` (chip) keys.
- `ae_payload()` overview now includes `restart_eligible: bool` and `state_records: int`. GPGB_EDIEXPT shows `restart_eligible=true, state_records=1` (GPGB_EDILIB_AET). State Records section now shows AET records with Default chip and record cross-links.

### SQL PeopleCode Cross-Reference (Priority #10 completion)
- PSPCMTXT.PCTEXT is plain text — searchable via Oracle LIKE.
- Added PeopleCode cross-reference block to `sql_object()`: searches `UPPER(PCTEXT) LIKE '%SQL.{sqlid}%'` against PSPCMTXT, normalizes each matching program via `peoplecode.normalize_program()`, adds type_label, parent cross-link, PeopleCode Explorer deep-link.
- `sections_for_sql()` now adds "PeopleCode References" section when results exist (hidden when empty).
- Test: `SQL.HR_GET_SETID_LOCATION` → 17 PeopleCode references.

### Portal Object Deep Comparison (Priority #3 completion)
- `compare_portal_object(env1, env2, portal_objname)` in `connectors/envcompare.py`: independently queries each env for PSPRSMDEFN definition, children (PORTAL_PRNTOBJNAME), and PSPORTALDEFN permissions; diffs by field and by presence.
- `/api/envcompare/portal-object?env1=HCM&env2=FSCM&name=X` endpoint in `routers/envcompare.py`.
- UI: `/admin/envcompare` Portals tab enhanced with "Deep Object Comparison" sub-panel; `runPortalObjectCompare()` + `renderPortalObjectDiff()` JS; shows stat boxes + definition diff table + collapsible children/permissions diff sections with add/remove/change chips.
- Portal UOM `_links` now includes `compare` link to `/api/envcompare/portal-object?name=X`.
- Test: PORTAL_GROUPLETS → 141 children differ (FSCM has FSCM-specific grouplets: Asset Management, Accounts Payable, etc.).

---

## 2026-06-30 — App Server Domain Monitoring (PSPMDOMAIN_VW)

**Context:** AE grants unblocked. Previous implementation assumed PSAPPSRV / PSAPPSRVDOM which do not exist in HCMDMO or FSCMDMO. Neither table exists in any environment.

**What changed:**

- `connectors/psdb.py` — added `app_server_domains(env_name)`:
  - Discovery-first: checks `PSPMDOMAIN_VW` then `PS_PSPMDOMAIN1_VW` using `ptmetadata.has_table()`; returns a non-fatal warning dict if neither is accessible — no crash, no hard-coded dependency
  - Groups raw rows by `PM_DOMAIN_NAME`; parses `PM_HOST_PORT` into `{host, port, alt_port}`; infers domain type from name suffix (`_APP` → App Server, `_PRCS` → Process Scheduler, `_WEB` → Web/PIA, default → Integration Broker)
  - Returns `{items, source_view, counts, warnings}` — `source_view` tells the caller which view was actually used
  - Added constants: `_APPSRV_DOMAIN_VIEWS`, `_DOMAIN_TYPE_RULES`, helpers `_classify_domain()`, `_parse_host_port()`

- `routers/runtime.py` — added `GET /api/runtime/domains?env=` endpoint

- `routers/admin.py` — added "App Server Domains" card (above the Process Scheduler Servers card); `loadDomains()` JS function with type chips (green=App Server, amber=Proc Sched, blue=Web/PIA, grey=IB); source view attribution footer; wired into `refresh()` via `Promise.allSettled`

- `ARCHITECTURE.md` — added App Server Domain Topology data source table and discovery contract description

**Live results (2026-06-30):**
- HCM (PSPMDOMAIN_VW): 4 domains — HCMDMO (IB), HCMDMO_APP (App Server :9043), HCMDMO_PRCS (Proc Sched), HCMDMO_WEB (Web/PIA)
- FSCM (PSPMDOMAIN_VW): 8 domains — FSCMDMO_APP, APPDOM (App Server), FSCMDMO_PRCS, PRCSDOM (Proc Sched), FSCMDMO_WEB, ps/peoplesoft (Web/PIA), FSCMDMO (IB)

---

## 2026-06-29 — Graph Indexing, Impact Analysis, Explorer Pages, Reporting Center, PeopleCode Source Search

### Portal Registry Bug Fixes

Two long-standing bugs in portal reconstruction were fixed.

**`connectors/psdb.py`**:

- `portal_registry_portals()` root detection: `TRIM(PORTAL_PRNTOBJNAME) = ' '` was
  wrong because TRIM strips the space, making the comparison `'' = ' '` (false). Fixed
  to `LENGTH(TRIM(PORTAL_PRNTOBJNAME)) = 0`.

- `portal_registry_breadcrumbs_fast()` CONNECT BY duplicate rows: `START WITH
  UPPER(PORTAL_OBJNAME) = UPPER(:objname)` without a portal-name filter matched the same
  objname across all 9 portals, producing N× ancestor chains. Fixed by adding `AND
  UPPER(PORTAL_NAME) = UPPER(:pn)` to both START WITH and CONNECT BY; also added NOCYCLE.

### Graph Indexing — 5 New Bulk Providers

**`connectors/graphdb.py`** — added to `build()`:

- `menus()`: joins PSMENUDEFN + PSMENUITEM, adds menu→component CONTAINS edges; guarded by `has_table("PSMENUDEFN")`.
- `trees()`: queries PSTREEDEFN, adds tree→record USES edges for treestrctpnm and tree_recname; `seen` set deduplicates tree names.
- `sql_definitions()`: queries PSSQLDEFN WHERE SQLTYPE=0 (standalone SQL), nodes only.
- `queries()`: queries PSQRYDEFN WHERE OPRID=' ' (public queries), nodes only.
- `component_interfaces()`: queries PSBCDEFN, adds ci→component WRAPS edges. Node type is `ci` (matching OBJECT_REGISTRY key, not `component_interface`).

All 5 use a single SQL call with ROWNUM limit. `WRAPS` edge type added to `EDGE_TYPES` and `DEPENDENCY_EDGES`.

**`connectors/ptmetadata.py`**: Fixed tree OBJECT_REGISTRY entry — `name_column` changed from `TREE_NAME` to `TREENAME`; `extra_search_columns` changed from `TREE_STRCT_ID` to `TREESTRCTPNM`. Added `"relationships"` field to query/tree/ci/menu entries.

### Advanced Dependency Analysis — `impact()`

**`connectors/graphdb.py`**: Added `impact(env, node, depth=3)` — runs `dependency_tree()` forward (downstream) and reverse (upstream), returns per-direction node lists plus per-type count summaries.

**`routers/graphdb.py`**: Added `GET /api/graph/impact/{node_id}?env=&depth=`.

**`routers/admin.py`** — Graph Explorer IMPACT tab:
- New tab button `#tabImpact` wired to `showTab('impact')`.
- `#impactView` div with node type/name pickers, depth selector, Analyse button, and side-by-side upstream/downstream panels.
- `renderImpactNodes(nodes, containerId)` — groups by `n.type`, renders object links via `objectUrl()` and `escHtml()`.
- `renderImpactSummary(byType, containerId)` — type-count chip badges.
- `runImpact()` — calls impact API, renders both panels.
- Node click in LIST view pre-fills the IMPACT type/name pickers.

### PS Query, Tree, CI, Menu Explorer Pages

New search functions in `connectors/psdb.py`:
- `search_queries(env, q, folder, limit)` — PSQRYDEFN WHERE OPRID=' ', optional folder filter.
- `query_folders(env)` — distinct QRYFOLDER values from public queries.
- `search_trees(env, q, setid, limit)` — correlated subquery to get latest EFFDT per (TREENAME, SETID, SETCNTRLVALUE).
- `search_cis(env, q, limit)` — PSBCDEFN.

New REST endpoints in `routers/peoplesoft.py`:
- `GET /api/peoplesoft/queries`, `GET /api/peoplesoft/query-folders`
- `GET /api/peoplesoft/trees`
- `GET /api/peoplesoft/cis`

New admin pages in `routers/admin.py` (all two-panel search/detail layout):
- `/admin/query` — folder filter dropdown, col/bind count stats, Object Explorer deep-link.
- `/admin/tree` — SETID filter, active/inactive chip, record cross-links.
- `/admin/ci` — type chip, wrapped component cross-link.
- `/admin/menu` — reuses existing menus API; detail renders items as a table with component cross-links.

Nav entries added: Queries, Trees, CIs, Menus.

### Reporting Center

**`connectors/psdb.py`** — `security_report()` extended with 10 new reports (total 16) across three categories — Security, Objects, System. Each report has a `category` field. `"params": {}` spec suppresses `:limit` injection for GROUP BY reports.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/reports`, `GET /api/peoplesoft/reports/catalog`.

**`routers/admin.py`** — `/admin/reports`: catalog sidebar grouped by category; result panel with live filter and CSV export; cells for known types (role, operator, permlist, component, record, AE, menu) auto-link to their Object Explorer pages.

### PeopleCode Source Search

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/peoplecode/source-search?q=&env=&limit=` — wraps `peoplecode.source_search()` which queries PSPCMTXT.PCTEXT with LIKE.

**`routers/admin.py`** — `/admin/pcsearch`: search box + result limit selector; sidebar shows matching programs with parent type chip + event chip; detail panel shows syntax-highlighted PeopleCode source with search term highlighted in amber `.hit` spans; "Open in PC Explorer" and parent cross-links.

**Verification:**
- `python -c "from routers import admin, peoplesoft; from connectors import psdb, peoplecode; print('OK')"` → OK

---

## 2026-06-30 — Admin Shell Smoke Harness — Priority #9 (CI/Deployment Wiring)

Extended `scripts/smoke_admin_shell.py` to cover all explorer pages added since the last harness update.

**`scripts/smoke_admin_shell.py`**:

- Added 6 new entries to `DEFAULT_PAGES`:
  - `/admin/query` → marker `#qSearch`, env=True, active nav
  - `/admin/tree` → marker `#tSearch`, env=True, active nav
  - `/admin/ci` → marker `#ciSearch`, env=True, active nav
  - `/admin/menu` → marker `#mSearch`, env=True, active nav
  - `/admin/reports` → marker `#catalog`, env=True, active nav
  - `/admin/pcsearch` → marker `#pcq`, env=True, active nav

- Upgraded Graph Explorer interaction check from "list/visual" to "list/visual/impact":
  - `showTab('impact')` → asserts `#impactView` not hidden and `#tabImpact` has class `active`.
  - `showTab('list')` → also now asserts `#tabList` has class `active` (was only checking pane visibility).

Harness now covers 13 pages (was 7).

**Verification:**
- `python -m py_compile scripts/smoke_admin_shell.py` → OK
- `python3 -c "import main"` → OK
- Page count confirmed: 13 entries across `DEFAULT_PAGES`.
- Blocker: headless Chrome is not available in this environment; harness requires `--base-url` pointing to a running DeathStar instance. Run against staging to validate the new page entries before next deploy.

---

## 2026-06-30 — Message Catalog Explorer (Phase 5 Knowledge Graph)

Full vertical slice for PeopleSoft Message Catalog (PSMSGCATDEFN / PSMSGSETDEFN).
Messages are referenced throughout PeopleCode via `MsgGet()`, `MessageBox()`, `Error MsgGet()`, etc.
Previously completely absent from the platform.

**`connectors/psdb.py`**:
- `search_messages(env, q, set_nbr, severity, limit)` — searches PSMSGCATDEFN by MESSAGE_TEXT and DESCRLONG (LIKE). Supports optional set_nbr and severity filters. Returns items with computed `severity_label` and `name` (`set.msg` format). Degrades if PSMSGCATDEFN is not accessible.
- `message_sets(env)` — attempts PSMSGSETDEFN JOIN PSMSGCATDEFN for counts+descriptions; falls back to GROUP BY on PSMSGCATDEFN alone. Returns `source` field indicating which path was used.
- `get_message(env, set_nbr, msg_nbr)` — fetches a specific message. Returns None gracefully if not found or table missing.
- `message_set_info(env, set_nbr)` — fetches set description from PSMSGSETDEFN (optional; returns None if table missing).
- `_MSG_SEVERITY` labels: 0=Message, 1=Warning, 2=Error, 3=Cancel.

**`connectors/ptmetadata.py`**:
- Added `message_catalog` to `OBJECT_REGISTRY` with `discovery.table=PSMSGCATDEFN`, custom `search.provider="message_catalog"`, icon `message-square`.
- Added `message_catalog` provider handler in `global_search()` — searches MESSAGE_TEXT and DESCRLONG. Returns `{set_nbr}.{msg_nbr}` as `name`, truncated message text as description.

**`connectors/uom.py`**:
- `message_catalog_object(env, name)` — parses `{set_nbr}.{msg_nbr}` name, calls `get_message` + `message_set_info`, returns structured object with `message` and `set_info` dicts.
- `sections_for_message_catalog(obj)` — single "Definition" section: Severity chip label, Message Set, Message Number, Message Text, Explanation.
- `message_catalog_payload(env, name)` — full UOM payload with overview kv grid + sections.
- Wired into `canonical_object()`.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/messages?env=&q=&set_nbr=&severity=&limit=` — search endpoint. Adds `_links.admin` to each result.
- `GET /api/peoplesoft/message-sets?env=` — returns all message sets.
- `message_catalog` wired into `object_payload()` dispatcher.

**`connectors/graphdb.py`**:
- `messages()` provider added to `build()`: queries PSMSGCATDEFN with ROWNUM limit, creates `message_catalog` nodes with `{set_nbr}.{msg_nbr}` as node name, message text (truncated to 80 chars) as display name. No edges (messages are referenced by PeopleCode but edge detection would require source parsing). `has_table("PSMSGCATDEFN")` guard.

**`routers/admin.py`**:
- Added `("msgcat", "Messages", "/admin/msgcat")` to `_NAV`.
- Added `message_catalog` / `menu` / `query` / `tree` / `ci` / `sql_definition` to `TYPE_CHIP_CFG` (was previously falling through to grey default).
- Added `message_set_nbr`, `message_nbr`, `severity`, `severity_label` to `_DETAIL_SKIP`.
- `/admin/msgcat` page: two-panel layout; top bar has text search + Set filter dropdown (populated from `/api/peoplesoft/message-sets`) + Severity filter dropdown; sidebar shows messages with severity chip, `set.msg` ref, and truncated text; detail panel shows severity chip + stat boxes + message text block + explanation block + "Object Explorer ↗" link.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/msgcat` → marker `#mcSearch`, env=True, nav=True. Harness now covers 14 pages (was 13).

**Verification:**
- `python -m py_compile connectors/psdb.py connectors/ptmetadata.py connectors/uom.py connectors/graphdb.py routers/peoplesoft.py routers/admin.py` → ALL OK (pre-existing `\-` warning in admin.py PC tokenizer regex, not introduced here)
- `python3 -c "import main"` → OK
- Live tests require DB access; message catalog tables (PSMSGCATDEFN, PSMSGSETDEFN) expected to be accessible given SYSADM schema grants on HCM.

---

## 2026-06-30 — Drift Detection & Approval Framework

### Priority #10: Drift Detection (Graph Explorer DRIFT tab)

**Goal:** Surface configuration drift by comparing the live in-memory graph against the most-recent snapshot directly inside the Object Explorer admin page.

**`connectors/graphdb.py`**:
- `drift(env, node_types, limit)` — loads the most-recent snapshot via `list_snapshots(env)["snapshots"][0]`, calls `load_snapshot()` to rehydrate, calls `current(env)` for the live graph, then delegates to `_diff_graphs(baseline, live, ...)`.
- Wraps result with `baseline_snapshot` metadata and `drift_summary` dict: `new_count`, `removed_count`, `changed_count`, `new_by_type`, `removed_by_type`, `baseline_at`, `baseline_id`.
- Semantics: `only_in_env2_nodes` = NEW objects (in live but not baseline), `only_in_env1_nodes` = REMOVED objects (in baseline but not live).

**`routers/graphdb.py`**:
- `GET /api/graphdb/drift?env=&node_types=&limit=` — thin router delegating to `graphdb.drift()`.

**`routers/admin.py`**:
- Added DRIFT tab button (`#tabDrift`) to Graph Explorer tab strip.
- Added `#driftView` div: env selector, type-filter text input, "Check Drift" button, summary chips panel (new/removed/changed counts), side-by-side new/removed node panels, changed node panel.
- `showTab()` extended to handle `'drift'` — shows `#driftView`, sets `#tabDrift.active`.
- `runDrift()` JS function: calls `/api/graphdb/drift`, renders summary chips, populates `renderDriftNodes()` panels.
- `renderDriftNodes(nodes, container)` — renders node cards with type chip, name, labels.
- `renderDriftChanged(nodes, container)` — renders changed nodes showing which properties differed.

**`scripts/smoke_admin_shell.py`**:
- Graph Explorer check upgraded from `list/visual/impact` to `list/visual/impact/drift`: added `showTab('drift')`, asserts `#driftView` visible and `#tabDrift.active`.

**Verification:**
- `python -m py_compile` → OK on all modified files.
- Live drift test: `drift('HCM')` against 7 existing HCM snapshots returned 0/0/0 (expected — no graph rebuild between snapshot and drift call).

---

### Priority #11: Approval Framework Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft Approval Framework workflow definitions (PSAWDEFN + sub-tables).

**Data model:** PSAWDEFN (definition) → PSAWSTAGEDEFN (stages) → PSAWPATHDEFN (paths) → PSAWSTEPDEFN (steps). Sub-tables individually optional — each guarded by `has_table()`.

**`connectors/psdb.py`**:
- `_AW_STATUS` dict: `{"A": "Active", "I": "Inactive"}`
- `_AW_PROCESS_TYPE` dict: maps `"0"`–`"8"` to No Approval / User / Role / Query / Application Class / Supervisory / Position / Department Security / Role User.
- `search_approvals(env, q, status, limit)` — searches PSAWDEFN.AWDEFNID + DESCR; optional STATUS filter; returns list of `{awdefnid, descr, status, objectownerid, status_label}`.
- `get_approval(env, awdefnid)` — fetches PSAWDEFN row; conditionally fetches each sub-table if present. Returns `{definition, stages, paths, steps, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `"approval"` entry promoted from planned to full `OBJECT_REGISTRY` entry: `display_title="Approval Framework"`, `icon="check-square"`, `discovery.table="PSAWDEFN"`, search on AWDEFNID + DESCR + OBJECTOWNERID.

**`connectors/uom.py`**:
- `_AW_STATUS_CHIP` and `_AW_PROCESS_LABELS` label dicts.
- `approval_object(env, awdefnid)` — fetches raw data, wraps into canonical object dict.
- `sections_for_approval(obj)` — produces three sections:
  - "Definition": kv grid (Description, Status label, Owner, Last Updated By, Last Updated, stage/path/step counts).
  - "Stages": one item per stage with `title="Stage N: {descr}"`, `relationship=process_type_label`, `path_count`, `step_count`.
  - "Steps": one item per step with `title="SN PN Step N: {descr}"`, `relationship=process_type_label`, `userlist`.
- `approval_payload(env, awdefnid)` — full UOM payload with `overview` kv grid keyed by `stage_count`, `path_count`, `step_count`, `status`, `owner`.
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `approvals()` provider added to `build()`: queries PSAWDEFN with ROWNUM limit, creates `approval` nodes. `has_table("PSAWDEFN")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/approvals?env=&q=&status=&limit=` — search endpoint.
- `approval` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("approval", "Approvals", "/admin/approval")` to `_NAV`.
- `/admin/approval` page: two-panel layout; top bar has text search (`#awSearch`) + Status filter (All/Active/Inactive); sidebar shows approval definitions with status chip (Active=green/chip-ok, Inactive=grey/chip-muted) and description; detail panel shows stat boxes (stage/path/step counts), Stages section with process type chips, Steps section with S/P/Step references and process type chips; "Object Explorer ↗" link for each selected approval.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/approval` → marker `#awSearch`, env=True, nav=True. Harness now covers 15 pages.

**Verification:**
- `python -m py_compile routers/admin.py` → OK (pre-existing `\-` warning unchanged).
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — XML Publisher Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft XML Publisher report definitions, data sources, and template layouts.

**Data model:**
- `PSXPREPORTDEFN` — report definition header (REPORTID PK, DESCR, OBJECTOWNERID, DATASRCID FK, LASTUPDOPRID, LASTUPDDTTM)
- `PSXPDATASRC` — data source definitions (DATASRCID PK, DESCR, DATASRCTYPE: A/Q/S/C/G/F)
- `PSXPTEMPLDEFN` — template/layout definitions (REPORTID FK, PSFBDILANGCD, TEMPLATEFORMAT, OUTPUTFORMAT, EFFDT, EFF_STATUS)

Sub-tables PSXPDATASRC and PSXPTEMPLDEFN individually guarded with `has_table()` — missing tables produce warnings, not crashes.

**`connectors/psdb.py`**:
- `_XPUB_DATASRC_TYPE` dict: A=App Engine, Q=PS Query, S=SQL, C=Connected Query, G=Group, F=File.
- `_XPUB_TEMPLATE_FORMAT` dict: RTF, XSL, Excel, eText, PDF Form, Flash.
- `_XPUB_OUTPUT_FORMAT` dict: PDF, Excel, RTF, HTML, CSV, XML, PCL.
- `search_xpub_reports(env, q, limit)` — searches PSXPREPORTDEFN by REPORTID/DESCR pattern; returns `{items, warnings}`.
- `search_xpub_datasources(env, q, limit)` — searches PSXPDATASRC; adds `datasrctype_label`; returns `{items, warnings}`.
- `get_xpub_report(env, reportid)` — full detail: PSXPREPORTDEFN row + PSXPDATASRC join + PSXPTEMPLDEFN rows with format labels; returns `{definition, datasource, templates, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `xml_publisher_report` entry: `discovery.table=PSXPREPORTDEFN`, search on REPORTID/DESCR/OBJECTOWNERID/DATASRCID.
- `xml_publisher_datasource` entry: `discovery.table=PSXPDATASRC`, search on DATASRCID/DESCR.

**`connectors/uom.py`**:
- `_XPUB_DATASRC_CHIP`, `_XPUB_STATUS_CHIP` label dicts.
- `xpub_report_object(env, reportid)` — wraps `get_xpub_report()` into canonical object dict.
- `sections_for_xpub_report(obj)` — "Definition" kv section (desc, owner, data source, type, last updated) + "Templates" section (one item per template row: lang—format→output, status chip, effdt).
- `xpub_report_payload(env, reportid)` — full UOM payload with `overview` (description, owner, datasrcid, datasrc_type_label, template_count).
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `xpub_reports()` provider added to `build()`: queries PSXPREPORTDEFN with ROWNUM limit, creates `xml_publisher_report` nodes. `has_table("PSXPREPORTDEFN")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/xpub/reports?env=&q=&limit=` — report search endpoint.
- `GET /api/peoplesoft/xpub/datasources?env=&q=&limit=` — data source search endpoint.
- `xml_publisher_report` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("xpub", "XML Publisher", "/admin/xpub")` to `_NAV`.
- Added `approval`, `xml_publisher_report`, `xml_publisher_datasource` to `TYPE_CHIP_CFG`.
- `/admin/xpub` page: two-panel layout with Reports/Data Sources mode toggle; search input (`#xpubSearch`); sidebar lists reports with ID + description + data source ID, or data sources with type chip + ID + description; report detail shows stat boxes (template count, owner), data source kv grid, Templates section with status chip + language/format/output/effdt rows; data source detail shows type chip + kv grid; "Object Explorer ↗" link for reports.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/xpub` → marker `#xpubSearch`, env=True, nav=True. Harness now covers 16 pages.

**Verification:**
- `python -m py_compile` all modified files → ALL OK.
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — Navigation Collections Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft Fluid Navigation Collections.

**Data model:**
- `PTNC_COLLECTION` — collection header (PORTAL_NAME + COLL_ID PK, COLL_TITLE, EFF_STATUS A/I, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID)
- `PTNC_COLL_LINE` — collection lines (PORTAL_NAME + COLL_ID + LINE_NBR PK, LINE_TYPE: C=Content Ref/F=Folder/T=Tile/S=Static Link, LABEL, PORTAL_URLTEXT)

`PTNC_COLL_LINE` individually guarded with `has_table()`.

**`connectors/psdb.py`**:
- `_NC_LINE_TYPE`, `_NC_EFF_STATUS` dicts.
- `search_nav_collections(env, q, portal, limit)` — searches PTNC_COLLECTION by COLL_ID/COLL_TITLE with optional PORTAL_NAME filter (defaults to 'EMPLOYEE'); adds `eff_status_label`; returns `{items, warnings}`.
- `get_nav_collection(env, coll_id, portal)` — fetches PTNC_COLLECTION row + PTNC_COLL_LINE rows with `line_type_label`; returns `{definition, lines, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `nav_collection` entry: `discovery.table=PTNC_COLLECTION`, supported_versions starts at 8.55 (Fluid).

**`connectors/uom.py`**:
- `_NC_LINE_TYPE_CHIP`, `_NC_STATUS_CHIP` label dicts.
- `nav_collection_object(env, coll_id)` — wraps `get_nav_collection()` into canonical object dict.
- `sections_for_nav_collection(obj)` — "Definition" kv section (title, status, portal, owner, last updated, line count) + "Lines" section (one item per line: relationship=type label, title=LABEL, url=PORTAL_URLTEXT, line_nbr).
- `nav_collection_payload(env, coll_id)` — full UOM payload with `overview` (title, portal, eff_status, owner, line_count).
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `nav_collections()` provider added to `build()`: queries PTNC_COLLECTION with ROWNUM limit, creates `nav_collection` nodes. `has_table("PTNC_COLLECTION")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/nav-collections?env=&q=&portal=&limit=` — search endpoint.
- `nav_collection` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("navcoll", "Nav Collections", "/admin/navcoll")` to `_NAV`.
- Added `nav_collection` to `TYPE_CHIP_CFG` (green palette, distinct from tree green).
- `/admin/navcoll` page: two-panel layout; top bar has text search (`#ncSearch`) + Portal dropdown (EMPLOYEE/All); sidebar shows collections with status chip, COLL_ID, title; detail panel shows stat boxes (line count, portal, owner), Lines section with line number, type chip (Tile=teal/Content Ref=green/Folder|Static=muted), label, URL; "Object Explorer ↗" link.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/navcoll` → marker `#ncSearch`, env=True, nav=True. Harness now covers 17 pages.

**Verification:**
- `python -m py_compile` all modified files → ALL OK.
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — Event Mapping & Related Content Vertical Slices

### Event Mapping (PT 8.55+)

**Tables:** `PSEFMAPPINGDEFN` (header), `PSEFMAPPINGCTXT` (contexts, optional).

**`connectors/psdb.py`**:
- `search_event_mappings(env, q, status, limit)` — searches PSEFMAPPINGDEFN by EFMAPPINGID/DESCR with optional STATUS filter.
- `get_event_mapping(env, efmappingid)` — fetches definition + PSEFMAPPINGCTXT rows (SEQNO, EFCONTEXTTYPE, EFCONTEXTVALUE, APPEVENTNAME, APPEVENTHANDLER); `has_table()` guard on context table.

**`connectors/ptmetadata.py`**: `event_mapping` promoted from planned stub to full registry entry (table=PSEFMAPPINGDEFN, supported from PT 8.55).

**`connectors/uom.py`**: `event_mapping_object()`, `sections_for_event_mapping()` (Definition kv + optional Contexts section), `event_mapping_payload()`. Wired into `canonical_object()`.

**`connectors/graphdb.py`**: `event_mappings()` provider.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/event-mappings`, wired into `object_payload()`.

**`routers/admin.py`**: `("efmapping", "Event Mapping", "/admin/efmapping")` in `_NAV`; `event_mapping` chip (yellow palette); `/admin/efmapping` two-panel page with status filter, context section showing type/value/event/handler.

**`scripts/smoke_admin_shell.py`**: Added `/admin/efmapping` → `#efSearch`. Harness now 18 pages.

---

### Related Content (Service Framework)

**Table:** `PSRELCONDEFN` (header only; service attachments are out of scope for this slice).

Service type codes: U=URL, C=Component, S=Script, A=App Class, P=PS Page, I=iScript, R=Related Action.

**`connectors/psdb.py`**:
- `_RC_SERVICE_TYPE` dict.
- `search_related_content(env, q, limit)` — searches PSRELCONDEFN by RELCONID/DESCR; adds `servicetype_label`.
- `get_related_content(env, relconid)` — fetches PSRELCONDEFN definition row with type label.

**`connectors/ptmetadata.py`**: `related_content` promoted from planned stub to full registry entry (table=PSRELCONDEFN).

**`connectors/uom.py`**: `related_content_object()`, `sections_for_related_content()` (Definition kv), `related_content_payload()`. Wired into `canonical_object()`.

**`connectors/graphdb.py`**: `related_content_defs()` provider.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/related-content`, wired into `object_payload()`.

**`routers/admin.py`**: `("relcontent", "Related Content", "/admin/relcontent")` in `_NAV`; `related_content` chip (purple palette); `/admin/relcontent` two-panel page with service type chip in sidebar, kv detail panel.

**`scripts/smoke_admin_shell.py`**: Added `/admin/relcontent` → `#rcSearch`. Harness now 19 pages.

**Verification:** `python -m py_compile` → ALL OK. `python3 -c "import main"` → OK.

---

## Search Definitions (PTSF_SRCDEFN)

Implemented the Search Definitions vertical slice — the PeopleSoft Search Framework definition object.

**`connectors/psdb.py`**: `_SRCH_STATUS` dict; `search_search_definitions(env, q, status, limit)` querying `PTSF_SRCDEFN` with has_table() guard; `get_search_definition(env, srcdefnid)` fetching definition row plus optional sub-tables `PTSF_SRCMAP` (mapped fields) and `PTSF_SRCAT` (categories) each guarded by has_table() + try/except.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY.setdefault("search_definition", {...})` entry with `PTSF_SRCDEFN` discovery/search tables, versions 8.54–8.62.

**`connectors/uom.py`**: `_SRCH_STATUS_CHIP`; `search_definition_object()`, `sections_for_search_definition()`, `search_definition_payload()`; added `search_definition` dispatch in `canonical_object()`.

**`connectors/graphdb.py`**: `search_definitions()` provider querying `PTSF_SRCDEFN` with `has_table()` guard; added to provider loop as `("search_definitions", search_definitions)`.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/search-definitions` endpoint; `search_definition` dispatch in `object_payload()`.

**`routers/admin.py`**: `("srchdef", "Search Defs", "/admin/srchdef")` in `_NAV`; `search_definition` chip (blue palette `#2299ee`); `/admin/srchdef` two-panel page with status filter dropdown, fields section, categories section.

**`scripts/smoke_admin_shell.py`**: Added `/admin/srchdef` → `#sdSearch`. Harness now 20 pages.

**`ROADMAP.md`**: Search Definitions promoted to Completed Providers; platform status updated to 20 smoke test pages; "Next Slice" section added at bottom.

---

## Search Categories (PTSF_SRCAT) and Drop Zones (PSPTDZDEFN)

Implemented two more Phase 5 providers in the same session cycle: Search Categories (sibling of Search Definitions in the Search Framework) and Drop Zones (promoted from the planned stub loop — `page_drop_zones()`/`component_drop_zones()` relationship helpers already existed and pointed at the real backing tables `PSPTDZDEFN`/`PSPTDZITEM`/`PSPTDZCOMP`/`PSPTDZPNL`, which made this a natural promotion rather than a fresh discovery).

**`connectors/psdb.py`**: `search_search_categories()` / `get_search_category()` over `PTSF_SRCAT`; `search_drop_zones()` / `get_drop_zone()` over `PSPTDZDEFN` with has_table()-guarded sub-table reads from `PSPTDZCOMP` (components), `PSPTDZPNL` (pages), and `PSPTDZITEM` (items).

**`connectors/ptmetadata.py`**: `search_category` and `drop_zone` promoted to full `OBJECT_REGISTRY` entries; `drop_zone` removed from the planned stub loop (now only `content_reference`, `section`, `step`, `sql`, `message`, `process_scheduler`, `runtime_instance` remain planned).

**`connectors/uom.py`**: `search_category_object()`/`sections_for_search_category()`/`search_category_payload()`; `drop_zone_object()`/`sections_for_drop_zone()`/`drop_zone_payload()`; both dispatched in `canonical_object()`.

**`connectors/graphdb.py`**: `search_categories()` and `drop_zones()` providers added to the build loop.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/search-categories`, `GET /api/peoplesoft/drop-zones`; both dispatched in `object_payload()`. Verified no collision with the existing component/page-scoped `.../drop-zones` relationship endpoints.

**`routers/admin.py`**: `("srchcat", "Search Cats", "/admin/srchcat")` and `("dropzone", "Drop Zones", "/admin/dropzone")` in `_NAV`; `search_category` (violet) and `drop_zone` (amber) chips; two new two-panel explorer pages.

**`scripts/smoke_admin_shell.py`**: Added `/admin/srchcat` → `#scSearch` and `/admin/dropzone` → `#dzSearch`. Harness now 22 pages.

**`ROADMAP.md`**: Search Categories and Drop Zones promoted to Completed Providers; platform status updated to 22 smoke test pages; "Next Slice" section rewritten for WorkCenters, Dashboards, Homepage Tiles, BI Publisher.

**Verification:** `python -m py_compile` on all seven touched files → ALL OK (pre-existing `\-` SyntaxWarning in the unrelated pcsearch tokenizer regex, not introduced here). `python3 -c "import main"` → OK.
