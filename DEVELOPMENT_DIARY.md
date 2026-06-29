# DeathStar Development Diary

This diary records implementation changes as they land. `ROADMAP.md` remains
the status tracker; this file keeps the narrative trail: what changed, why it
matters, and how it was verified.

------------------------------------------------------------------------

## 2026-06-29

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
