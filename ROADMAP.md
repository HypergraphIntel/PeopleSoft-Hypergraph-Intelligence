# DeathStar Implementation Roadmap

> **Architecture, vision, principles, provider contracts, and long-term
> capabilities** are documented in `ARCHITECTURE.md`.
>
> This roadmap tracks **current implementation status** and **remaining
> work**. Historical implementation notes have been consolidated into
> the appropriate module to eliminate duplication.

------------------------------------------------------------------------

# Module Status

## Frontend Shell

**Status:** Foundation Complete

### Completed

-   `/static` frontend asset mount
-   Root `/` redirect to `/static/index.html`
-   Shared sticky top banner
-   Banner links for Home, API Docs, Tracing Config, Live Events, IB Nodes, and HCM/FSCM graph builds
-   Active-link highlighting where the current page can be matched
-   Shared CSS in `/static/app.css`
-   Shared frontend behavior in `/static/app.js`
-   HTML shell injection for existing frontend pages
-   Single shared shell brand link with logo/text treatment
-   Shared environment selector persistence with legacy `#envSel` synchronization
    and `deathstar:envchange` event emission for migrated admin pages
-   Headless browser smoke harness for core admin shell pages, including
    shared-shell render checks and high-risk tab/sidebar interaction checks
-   Full navigation architecture redesign: two-level shell (global nav bar +
    page header), `_shell()` function, `_NAV` list, global env selector,
    `localStorage` persistence, new landing page, `/admin/users`, `/admin/docs`

### Remaining

------------------------------------------------------------------------

## Object Explorer Architecture

**Status:** In Progress

### Completed

-   Canonical object URLs
-   Reusable object payload API
-   Global search
-   Search landing page
-   Reusable object renderer
-   Graph navigation
-   Admin links
-   Canonical pages for Operator, Role, Permission List, Record,
    Component, Page, Field, Portal Registry, Application Engine,
    Integration Broker objects
-   Canonical Tree object pages backed by PSTREEDEFN/PSTREENODE/PSTREELEAF
    metadata, with graph links to tree structure records and fields
-   Canonical Component Interface object pages backed by PSBCDEFN/PSBCITEM,
    with graph links to wrapped components, menus, records, and exposed fields
-   Breadcrumbs in Object Explorer (type-aware trail with field record parent support)
-   Recently Viewed: relative timestamps, descriptions, per-item remove button

-   SQL syntax highlighting in Object Explorer: `highlightSQL()` tokenizer for `data.ddl` sections and inline SQL step items (SQL keywords in blue, PeopleSoft meta-SQL in purple, strings in orange, comments in green)
-   Visual hierarchy redesign: merged object header (type chip + name + description +
    overview kv-grid + action links); count badges on section h2; DDL/source sections
    span full grid width; Warnings section with amber treatment; relationship chip in
    rows; `renderKeyValues` uses app.css `.kv-grid`

### Remaining

------------------------------------------------------------------------

## PeopleTools Metadata Engine

**Status:** Foundation Complete

### Completed

-   TTL metadata discovery
-   Version adapters
-   OBJECT_REGISTRY
-   Universal provider search
-   Metadata diagnostics
-   Capability helpers

### Completed

-   Relationship providers: `"relationships"` field added to OBJECT_REGISTRY entries for operator/role/permissionlist/component/page/record/field/peoplecode/application_engine/menu — each declares typed edges (direction, edge_type, target_type, label). `GET /api/metadata/relationship-map` returns the full declarative object-type graph (nodes + edges, excludes planned types). 27 relationship declarations across 24 active object types.

-   Additional object providers: `menu` fully implemented — `search_menus()`, `menu()`, `menu_items()`, `component_menus()` in psdb.py; `menu_object()`, `sections_for_menu()`, `menu_payload()` in uom.py; OBJECT_REGISTRY entry with discovery (`PSMENUDEFN`) + search (`MENUNAME/DESCR/MENUGROUP/OBJECTOWNERID`) + relationship declaration; `GET /api/peoplesoft/menus`, `GET /api/peoplesoft/menus/{name}`, `GET /api/peoplesoft/menus/{name}/items`, `GET /api/peoplesoft/components/{component}/menus` endpoints; `object_payload()` handles `menu` type; global search auto-includes menu (637 menus in HCM); Component Explorer gains "Menus" section showing which menus list the component (via PSMENUITEM), clickable to Menu Object Explorer.

### Completed

-   Version-specific adapters: `VERSION_ADAPTERS` populated with real per-version data for 8.58–8.62 — each entry has `status`, `notes`, `new_tables` (tables introduced in that version), `removed_tables`, `column_aliases` (logical name → actual column for known cross-version variations like `PSPCMTXT.source_column` → `PCTEXT` vs `PROGTXT` in 8.58). `version_column(env, table, logical, default)` helper resolves the correct column name for a detected version. `version_tables(env)` returns declared table delta for the detected version. `GET /api/metadata/version` returns full version context with live table probes for declared new tables.

### Remaining

------------------------------------------------------------------------

## Universal Object Model (UOM)

**Status:** In Progress

### Completed

-   Canonical UOM schema
-   Field objects
-   Record objects
-   Operator objects
-   Role objects
-   Permission List objects
-   Component objects
-   Page objects
-   Portal Registry objects
-   Shared graph integration
-   Object Explorer integration
-   Graph context enrichment
-   Dynamic-membership sections for Role and Permission List UOM payloads

### Completed

-   Query objects: `query_object()` / `sections_for_query()` / `query_payload()` — fetches PSQRYDEFN + PSQRYRECORD + PSQRYFIELD + PSQRYBIND for public queries (OPRID=\' \'); shows records with join types/aliases, output columns with headings/aggregates, and prompt parameters with field types
-   Tree objects: `tree_object()` / `sections_for_tree()` / `tree_payload()` — fetches effective-dated PSTREEDEFN metadata with structure records/fields, levels, branches, node/leaf samples, variants, and graph preview
-   Component Interface objects: `ci_object()` / `sections_for_ci()` / `ci_payload()` — fetches PSBCDEFN + PSBCITEM metadata with definition, component/menu links, search/add records, keys, collections, properties, fields, item samples, and graph preview

### Completed

-   Shared relationship provider registration: `"relationships"` field added to OBJECT_REGISTRY entries (see PeopleTools Metadata Engine above). Each object type declares its typed relationships to other types. `GET /api/metadata/relationship-map` exposes the full declarative graph. UOM payloads continue to populate `_relationships` from live SQL; the registry provides the schema-level declaration layer.

### Remaining

------------------------------------------------------------------------

## Knowledge Graph Engine

**Status:** Foundation Complete

### Completed

-   Graph backend
-   Graph algorithms
-   JSON / DOT / GraphML export
-   Graph APIs
-   Graph Explorer
-   Snapshot creation
-   Snapshot comparison
-   Environment graph diff
-   Integration Broker graph providers
-   Scheduled daily snapshots with retention pruning (connectors/scheduler.py)
-   `/api/graph/snapshots/schedule` status endpoint
-   `/api/graph/snapshots/prune` manual prune endpoint
-   Force-directed SVG visualization in Graph Explorer (Visual tab)

### Completed

-   Security traversal: operator → role → permission list → component edges in graph build; graph API already supports multi-hop traversal via `/api/graph/neighbors/{node}?depth=N` and shortest path via `/api/graph/path`

### Completed

-   Graph compaction: `compact(env)` function in graphdb.py deduplicates edges in-place and persists the result; `POST /api/graph/compact` endpoint; "Compact" button in Graph Explorer UI; O(1) edge dedup: `_edge_ids` set added to graph dict (not persisted), rebuilt on load from `current()`, used in `add_edge()` instead of O(N) `any()` scan; `save()` excludes `_edge_ids` from JSON serialization.

### Completed

-   Large-environment indexing: `_batch_in_query()` helper in psdb.py chunks IN-clause queries at 500 items (Oracle 1000-item limit); `batch_operator_roles()`, `batch_role_permissionlists()`, `batch_permissionlist_components()`, `batch_component_pages()` replace N+1 per-item queries in the graph build; build limit raised from 250 to 2000; graph build auto-selects batch mode when limit>250 — operators/roles/permissionlists/components all use batch queries; `peoplecode_programs()` and `application_engines()` providers still use per-item queries (source-loading is inherently sequential).

### Remaining

------------------------------------------------------------------------

## Field Explorer

**Status:** Feature Complete

### Completed

-   Canonical Field Explorer
-   Cross-record search
-   Dedicated Field UI
-   Relationships
-   Graph integration
-   Metadata fallback
-   PSDBFIELD support
-   Field label resolution (longname/shortname from PSDBFLDLABL, DEFAULT_LABEL=1, batch-enriched on record objects)

-   Rich PeopleCode decoding: `field_peoplecode_metadata()` rebuilt to query PSPCMPROG with correct objectid1=2 (record/field) and objectid1=10 (component record/field) predicates; results normalized via `peoplecode.normalize_program()`; `attach_object_links()` extended to add `_links.admin` for rows with `encoded_reference`. Field Explorer now shows 80+ clickable PC programs for fields like DERIVED_GL.GL_DEL_COMBO_PB.

### Remaining

------------------------------------------------------------------------

## PeopleCode Explorer

**Status:** In Progress

### Completed

-   Canonical object support
-   Source reconstruction
-   Syntax highlighting
-   Event decoding
-   Semantic path decoding
-   AE linkage
-   IB linkage
-   Graph provider

### Completed

-   Application Package UOM: `app_package_object()` / `sections_for_app_package()` /
    `app_package_payload()` backed by PSPACKAGEDEFN + PSAPPCLASSDEFN + PSPCMPROG
    (objectid1=104); Object Explorer canonical pages; global search provider;
    selector wired into Graph Explorer and Object Explorer; objectid1=104 corrected
    from "IB Handler" to "App Package Class" across PEOPLECODE_OBJECT_TYPES,
    \_OID1_PARENT_TYPES, and decode_semantic_path()

-   PCTEXT column fix: `source_for_reference()` and `source_search()` were looking for `PROGTXT`/`TXT`/`TEXT` columns but PSPCMTXT uses `PCTEXT` in PeopleTools 8.5+. Fixed candidate list and priority order in both functions; also expanded objectvalue key range from 4 to 7 for correct matching. PeopleCode source now loads in all Object Explorer views.

-   Larger source pagination: `programs()` now supports `offset` parameter with `OFFSET n ROWS FETCH NEXT n+1 ROWS ONLY` (Oracle row-skip pagination); returns `{has_more, offset, limit}` metadata; limit raised to 2000; search predicate fixed to only match OBJECTVALUE columns (not numeric ID columns); PeopleCode Explorer UI gains "Load more" button when `has_more=true`, appends to existing results.

### Remaining

------------------------------------------------------------------------

## Security Explorer

**Status:** In Progress

### Completed

-   Role Explorer
-   Operator Explorer
-   Permission List Explorer
-   Security explanation APIs
-   Component/Page/Menu explanation
-   Portal security
-   Portal explanation
-   Graph traversal
-   Operator comparison: role/permission list/component set diff (`/api/peoplesoft/security/compare-operators`)
-   Security reports: 6 canned audit reports via `/api/peoplesoft/security/reports?report=<type>`, Reports card in `/admin/security`
-   Dynamic-membership enrichment for role and permission-list UOM views
-   Permission-decoding grant-path enrichment with permission-list detail and decoded actions for component, page, and menu access explanations
-   SQL Workspace backend cancellation handling with explicit cancelled status propagation for aborted executions
-   Canonical object routing for permission-list aliases in the Object Explorer

### Completed (access-path visualization pass)

-   Component UOM: "Security" flat rows → "Who Has Access" grouped by permlist
    with role count, operator count, decoded actions; "Permission Lists" items
    now show action chips (Update/Display / Add, Update/Display)
-   Page UOM: same "Who Has Access" grouped section
-   Permission List UOM: "Components" items now show action chips
-   `_access_summary()` shared helper (generalized from portal helper)
-   `_DETAIL_SKIP` noise fields removed (authorizedactions, displayonly, raw_*)
-   `labelFor()` now checks `row.title`/`row.label` before field fallbacks

-   Page-level action grants: `permissionlist_page_grants()` and `component_page_grants()` from PSAUTHITEM; Page Grants section in permission-list UOM (grouped by component, decoded actions); Security Explorer `selectPermissionList` renders grouped page grants inline with action chips; `selectComponent` annotates each structural page with the permission lists that grant it and their decoded actions

### Remaining

------------------------------------------------------------------------

## Record Explorer

**Status:** In Progress

### Completed

-   Dedicated Record UI
-   UOM integration
-   DDL
-   Keys
-   Indexes
-   Sample data
-   Storage
-   Relationships
-   Rich dependency traversal: child records (PSRECDEFN.PARENTRECNAME), subrecord derivations (PSRECFIELD.DEFRECNAME), AE state records (PSAEAPPLSTATE)
-   record_components() fix: SQL used `addsearchrecname` in WHERE clause but actual PSPNLGRPDEFN column is `ADDSRCHRECNAME` — caused ORA-00904 crash, silently swallowed by safe_relationship(), returning 0. Fixed to use ADDSRCHRECNAME and conditionalize its inclusion. Components section now correctly shows 8 results for EMPLMT_SRCH_ALL.

------------------------------------------------------------------------

## Component Explorer

**Status:** Feature Complete

### Completed

-   Canonical pages
-   UOM integration
-   Portal
-   Related Content
-   Drop Zones
-   Security
-   Graph preview
-   Component PeopleCode (objectid1=9 event-level, 10 record/field-level)

-   Rich visualization: `component_page_hierarchy()` in psdb.py batch-fetches PSPNLFIELD structural elements (FIELDTYPE 11/18=Subpage, 21=Grid) for all component pages in one query; Pages section now shows flat leveled items (level 0=page with type chip Standard/Subpage/Popup, level 1=subpage/grid inclusion with kind chip); `renderRows()` indents level 1 items and makes all rows clickable via `_links.admin`; JOB_DATA shows 12 pages / 65 structural elements, WEB_PROFILE shows 11 pages / 117 grids.

-   Better portal reconstruction: `component_portal_refs()` rewritten to use exact `PORTAL_URI_SEG2 = component` match (content refs) instead of broad LIKE search (eliminated false positives — JOB_DATA dropped from 36 misleading results to 5 accurate ones); LEFT JOINs to parent and grandparent PSPRSMDEFN rows reconstruct full navigation breadcrumb (e.g., "Workforce Administration › Job Information › Job Data"); `nav_path` rendered as relationship chip in Portal Registry section.

### Remaining

------------------------------------------------------------------------

## Page Explorer

**Status:** UOM Integrated

### Completed

-   Canonical pages
-   UOM integration
-   Components
-   Records
-   Fields
-   Security
-   Event Mapping
-   Related Content
-   PeopleCode (normalized from parent components, with explorer links)

-   Scroll Structure / Subpages / Grids fixed: `page_scroll_structure()` was classifying ALL PSPNLFIELD rows as "Subpage" because `row.get("subpnlname")` returns `' '` (space) which is truthy in Python. Rewritten with proper numeric FIELDTYPE checks (11=Subpage, 18=Scroll Area, 21=Grid) and blank-space stripping — Scroll Structure for EMPLOYMENT_DTA1 now shows 4 correct subpages instead of 56 false positives.
-   PeopleCode source: PeopleCode source now loads in the Object Explorer thanks to the PCTEXT column fix (see PeopleCode Explorer entry).

### Remaining

------------------------------------------------------------------------

## Portal Explorer

**Status:** Feature Complete

### Completed

-   Portal Registry UOM
-   Content reference object API
-   Portal Registry global search
-   Breadcrumb reconstruction
-   Child content references
-   Component target inference
-   Menu/folder type decoding
-   Portal security grants
-   Portal access path expansion
-   Operator-to-Portal explanation
-   Dedicated Portal UI
-   Graph preview
-   Rich portal reconstruction: navigation path breadcrumbs with reftype chips,
    human-readable children labels (Folder/Content Reference chips), grouped
    "Who Has Access" access-path summary (permlist → role count + operator count),
    Portal Security permission chips, navigation_path string in Definition,
    empty section filtering; `labelFor()` and `_DETAIL_SKIP` updated for generic
    renderer
-   Portal object deep comparison: `compare_portal_object()` in envcompare.py;
    `/api/envcompare/portal-object` endpoint; Deep Compare panel in
    `/admin/envcompare` Portals tab with stat boxes + field diffs + children
    add/remove/label-change chips + permission diffs; portal UOM `_links.compare`

------------------------------------------------------------------------

## Application Engine Explorer

**Status:** In Progress

### Completed

-   Metadata
-   UOM
-   Runtime
-   Graph
-   PeopleCode linkage
-   Process Explorer
-   AE step SQL text: `PSAESTMTDEFN` → `PSSQLTEXTDEFN` (SQLTYPE=1) batch-resolved, displayed in "SQL Steps" section of AE object page
-   Runtime instance deep-linking: `runtime_instances()` enriches each item with
    title (#N), runstatus chip, computed duration, and `_links.admin` →
    `/admin/runtime?instance=N`; Runtime Monitor page handles `?instance=N` URL
    param to auto-open the process detail panel
-   Restart eligibility: `state_records()` fixed to handle `AE_STATE_RECNAME`
    column (vs older `RECNAME`); `ae_payload()` overview now includes
    `restart_eligible` (bool) and `state_records` count; State Records section
    shows AET records with Default chip and record cross-links

### Remaining

------------------------------------------------------------------------

## Integration Broker Explorer

**Status:** Active Development

### Completed

-   Services
-   Service Operations
-   Nodes
-   Queues
-   Routings
-   Dashboard
-   UOM
-   Graph integration
-   PeopleCode linkage
-   Service operation drilldown for versions, handlers, security,
    messages, queues, and sender/receiver routing nodes

### Completed

-   Relationship Explorer redesign: master-detail layout (list panel left, detail panel right); breadcrumb nav stack (IB › Service › Operation › Routing › Node); clickable relationship strips at top of every detail view; "View Transactions" quick-filter action on operation, routing, queue, and node; sub-definition nodes clickable in routing detail; pub/sub contract nodes clickable in transaction detail; active-item highlighting in list when detail is open

### Current Limitations

-   Runtime grants unavailable
-   Payload inspection pending
-   Some service-operation sections depend on optional PeopleTools views
    (`PSOPRVERMSGS_VW`, `PSSRVQUEUE_VW`, `PSSERVPERM_VW`)

------------------------------------------------------------------------

## SQL Definition Explorer

**Status:** Feature Complete

### Completed

-   `sql_object()` / `sql_payload()` UOM
-   PSSQLDEFN + PSSQLTEXTDEFN access (grant-aware)
-   Oracle-specific variant priority (DBTYPE=7 → Generic)
-   SQL Source section rendered via `data.ddl` in Object Explorer
-   DB Variants section (Generic / Oracle / Sybase / DB2 / MSSQL)
-   Global search via `PSSQLDEFN.SQLID`
-   `sql_definition` added to Object Explorer and Graph Explorer selectors
-   `/api/peoplesoft/object/sql_definition/{id}?env=` endpoint
-   AE References section: AE SQL steps using `%SQL(SQLID)` meta-SQL (PSSQLTEXTDEFN LIKE search)
-   SQL type filter in search: `GET /api/peoplesoft/sql_definitions?sqltype=0|1|2|6`; Object Explorer shows SQL type filter UI when sql_definition type is selected
-   PeopleCode References section: searches PSPCMTXT.PCTEXT for `SQL.SQLID` pattern;
    returns normalized references with type label, parent object cross-links,
    and PeopleCode Explorer deep-links

------------------------------------------------------------------------

## SQL Workspace

**Status:** Foundation Complete

### Completed

-   Read-only execution
-   Explain Plan
-   History
-   Audit
-   Schema browser
-   Export
-   Search filters

### Completed

-   SQL autocomplete: Ctrl+Space or typing triggers dropdown — table names from schema search, column names from alias resolution (table alias extracted from SQL), column cache per session; Arrow/Enter/Tab/Escape navigation
-   Typed bind parameters: Structured key/value bind editor replaces raw JSON textarea; auto-detects `:name` placeholders from SQL as you type; history load restores saved binds; rows add/remove individually

### Completed

-   Timeout / cancellation: server-side timeout propagation, client-side cancel button, explicit timed-out/cancelled messaging, and history status markers

------------------------------------------------------------------------

## Environment Comparison

**Status:** Foundation Complete

### Completed

-   Generic comparison engine
-   Record/Field/Role/Permission/AE/Role comparison
-   Graph snapshot comparison
-   Explorer drill-down
-   PeopleCode program catalog comparison (objectid1+OV key, lastupddttm diff)
-   SQL Definition comparison (PSSQLDEFN catalog)
-   Portal Registry comparison (PSPRSMDEFN catalog)
-   Object count summary expanded: PeopleCode programs, SQL definitions, Portal entries
-   PS Query comparison: `compare_queries()` against PSQRYDEFN (public queries, OPRID=\' \'); PS Queries tab in `/admin/envcompare`; count in summary

-   Deep PeopleCode source diff: `compare_peoplecode_source()` in envcompare.py queries
    PSPCMTXT.PCTEXT directly (plain text — no binary decode needed; prior "blocked" note
    was incorrect); accepts OV1.OV2.EVENT reference without PROGSEQ suffix, concatenates
    all PROGSEQ chunks for full-program comparison; unified diff via difflib.unified_diff;
    `/api/envcompare/peoplecode-source`; "Deep Source Diff" panel in PeopleCode tab of
    `/admin/envcompare` with syntax-highlighted diff view (+green, -red, @@ blue)

------------------------------------------------------------------------

## Transaction Tracing

**Status:** Foundation Complete

### Completed

-   Unified timeline
-   Oracle correlation
-   Process Scheduler correlation
-   IB correlation
-   Operator activity

### Current Limitations

-   Missing grants in some environments
-   ASH unavailable without Diagnostics Pack

------------------------------------------------------------------------

## Runtime Monitor

**Status:** Foundation Complete

### Completed

-   Oracle monitoring
-   Process Scheduler
-   IB queue summary
-   Runtime dashboard
-   Runtime graph API
-   Runtime graph visualization (force-directed SVG, `/admin/runtime` Graph card)
-   Process Scheduler Server status: `process_scheduler_servers()` in psdb.py
    queries PSSERVERSTAT; `/api/runtime/servers`; card in `/admin/runtime`
-   App Server Domain Topology: `app_server_domains()` in psdb.py discovers
    `PSPMDOMAIN_VW` (primary) or `PS_PSPMDOMAIN1_VW` (fallback) at runtime via
    `ptmetadata.has_table()` — no hard dependency on PSAPPSRV/PSAPPSRVDOM;
    `/api/runtime/domains`; "App Server Domains" card in `/admin/runtime` with
    domain type chips (App Server / Process Scheduler / Web PIA / Integration Broker);
    non-fatal warning when neither view is accessible
-   Oracle ASH Integration: `oracle_ash_summary()` / `oracle_ash_top_sql()` in
    execution.py query `V$ACTIVE_SESSION_HISTORY` (now accessible); `/api/runtime/ash`
    and `/api/runtime/ash/sql`; "Oracle Active Session History" card in `/admin/runtime`
    with wait class chips, top-8 wait events (color-coded by class), top-10 SQL by
    samples (with V$SQL text if cached), and top process module breakdown
-   Runtime Monitor Alerts: `connectors/alerts.py` evaluates six checks — process errors
    (last 1h), long-running processes (>2h), queue depth (>10), Oracle blocking chains,
    ASH high-wait (single wait class >70%), domain no-listener; `/api/runtime/alerts`;
    "Active Alerts" card at top of `/admin/runtime` with severity chips (error/warn),
    card border color shift (red/amber/cyan), and deep-links to affected resources
-   Process-level Oracle Activity (ASH): `oracle_ash_for_process(db, env, instance)` in
    execution.py looks up PSPRCSRQST time window and correlates by module/action
    (Application Engine → module='PSAE', action=prcsname); `/api/runtime/ash/process`;
    Process Detail panel auto-loads Oracle Activity section (wait events + top SQL) after
    basic fields render; falls back to DBA_HIST_ACTIVE_SESS_HISTORY if V$ASH empty;
    ORA-00918 avoided by aliasing both table refs as `a` and qualifying all WHERE cols

------------------------------------------------------------------------

## Identity Management

**Status:** Feature Complete

### Completed

-   Authelia integration
-   Identity sync
-   Provisioning
-   Audit

### Completed

-   MFA: `_sqlite_query()` in authelia_admin.py reads/writes Authelia SQLite at `/opt/authelia/config/db.sqlite3`; `GET /authelia/mfa/status` returns MFA status for all users (totp_configured, webauthn_count, preferred_method, last_seen, login counts); `GET /authelia/mfa/status/{username}` returns full detail + recent auth log; `DELETE /authelia/mfa/{username}/totp` revokes TOTP; `DELETE /authelia/mfa/{username}/webauthn` revokes WebAuthn (single or all devices); `DELETE /authelia/mfa/{username}` revokes all MFA; `GET /authelia/logs` returns auth log with optional username filter + failed_only; Users page shows MFA chips (TOTP/WebAuthn×N), Last Seen column, Revoke MFA button, and Authentication Log table.

### Completed

-   Bulk operations: `POST /api/identity/bulk-provision` accepts `{oprids, password?}`; auto-generates per-user passwords when no shared password provided; returns per-oprid status (provisioned/already_exists/not_found/error); Users page OPRID search adds checkboxes per row, "Select All" toggle, "0 selected" counter, and "Provision Selected" button that calls bulk-provision and shows a result summary.

-   Approval workflow: `POST /api/identity/requests` creates a pending request (validates PS OPRID, blocks duplicates); `GET /api/identity/requests?status=` lists all requests; `POST /api/identity/requests/{id}/approve` provisions the user and records temp password; `POST /api/identity/requests/{id}/reject` records rejection reason; `DELETE /api/identity/requests/{id}` cancels a pending request; all actions audit-logged; Provision Requests card in Users page shows filterable table with Approve/Reject/Cancel buttons per pending row; "Request" button added to each OPRID search result alongside "Provision".

### Remaining

------------------------------------------------------------------------

## Infrastructure

**Status:** Partial

### Completed

-   System APIs
-   Oracle APIs
-   NGINX APIs
-   Live monitoring
-   Topology

### Completed

-   Expanded infrastructure management: `services_summary()`, `restart_service()`, `reload_nginx()`, `containers()`, `container_logs()`, `restart_container()` added to system.py connector. New REST endpoints: `GET /api/system/services`, `POST /api/system/service/{unit}/restart`, `POST /api/system/nginx/reload`, `GET /api/system/containers`, `GET /api/system/containers/{name}/logs`, `POST /api/system/containers/{name}/restart`. `/admin/infra` page with 2-column grid: Host Metrics (CPU/memory/disk/load), Services table (active chip + Restart buttons, NGINX Reload), Containers table (running status + Restart buttons, populates log selector), Oracle Health (instance count + tablespace + listener), Container Log viewer (tail N lines from any container), Journal Log viewer (any unit combination). "Infra" added to global nav.

### Remaining

------------------------------------------------------------------------

# Upcoming Priorities

## Medium Priority — Completed

-   Advanced Portal Registry reconstruction: Two bugs fixed — `portal_registry_portals()` root detection changed from `TRIM(PORTAL_PRNTOBJNAME) = ' '` to `LENGTH(TRIM(PORTAL_PRNTOBJNAME)) = 0`; `portal_registry_breadcrumbs_fast()` CONNECT BY query updated to include `AND UPPER(PORTAL_NAME) = UPPER(:pn)` in both the START WITH clause and CONNECT BY predicate, plus `NOCYCLE`, eliminating cross-portal row multiplication.
-   Graph indexing: Five new bulk graph providers added to `graphdb.build()`: `menus` (PSMENUDEFN + PSMENUITEM → menu→component CONTAINS edges), `trees` (PSTREEDEFN → tree→record USES edges), `sql_definitions` (PSSQLDEFN standalone type=0), `queries` (PSQRYDEFN public OPRID=' '), `component_interfaces` (PSBCDEFN → ci→component WRAPS edges). Each uses a single SQL call with ROWNUM limit. WRAPS edge type added to EDGE_TYPES and DEPENDENCY_EDGES. OBJECT_REGISTRY entries for tree/query/ci/menu updated with correct column names and relationship declarations.
-   Advanced dependency analysis: `graphdb.impact(env, node, depth)` combines forward + reverse `dependency_tree()` traversal and returns per-direction type summaries. `GET /api/graph/impact/{node_id}` endpoint added. Graph Explorer gains an IMPACT tab with type+name picker, depth selector, and side-by-side upstream/downstream panels grouped by node type with clickable object links.

## Blocked

-   Runtime IB inspection (missing grants)

## Long-Term

-   Deployment Center
-   Logging Platform
-   AI Assistant
-   Automation
-   Reporting
