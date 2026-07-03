# PeopleSoft Hypergraph Intelligence Roadmap

## Vision

PeopleSoft Hypergraph Intelligence is evolving into a complete operational intelligence platform for PeopleSoft.

The long-term objective is to provide a unified interface for:

- Metadata exploration
- Dependency analysis
- Runtime observability
- Environment comparison
- Security analysis
- Operational tooling
- AI-assisted engineering workflows

---

# Current Status

## Platform Status

### ✅ Completed

The following major subsystems are production-ready:

- Unified Object Model (UOM)
- Object Explorer
- Object Explorer section map and visual hierarchy for canonical UOM sections
- Graph Explorer (List / Visual / Impact / Drift tabs)
- Knowledge Graph with graph snapshot and drift detection
- Environment Compare (Records, Fields, PeopleCode, SQL Definitions, PS Queries, Portals, Graph)
- Runtime Monitor with Oracle ASH integration and runtime alerts
- Runtime Graph visualization
- SQL Workspace with autocomplete, typed bind parameters, timeout, and cancellation
- Integration Broker Explorer with master-detail relationship navigation
- Identity Management and Security Explorer
- Oracle ASH Integration
- Runtime Alerts
- App Server Domain Monitoring
- Application Package Explorer
- Component Interface Explorer
- Portal Explorer with security explanation
- SQL Definition Explorer
- PS Query Explorer
- Tree Explorer
- Menu Explorer
- PeopleCode Source Search
- Reporting Center
- Message Catalog Explorer
- Approval Framework Explorer
- XML Publisher Explorer
- Navigation Collections Explorer
- Event Mapping Explorer
- Related Content Explorer
- Search Definition Explorer
- Search Category Explorer
- Drop Zone Explorer
- Timezone Explorer
- Locale Explorer
- PM Metrics Explorer
- PM Transaction Explorer
- PM Event Explorer
- IB Service Operations Explorer
- Version-aware metadata adapters
- Shared frontend shell with grouped dropdown navigation (8 functional groups + Home/Users direct links) and environment selector
- Admin shell smoke test harness (57 pages; 23 new providers added in Phase 5)
- Scheduled graph snapshots with retention pruning

Development focus now shifts from feature parity toward platform intelligence.

---

# Phase 4 — Runtime Intelligence

## Live Session Explorer

Provide complete end-to-end session visibility.

### ✅ Completed

- Oracle session tracking (V$SESSION, V$SQL)
- SQL execution visibility and top-SQL analysis
- Wait events and Oracle ASH integration
- Lock analysis and blocking chains
- Process Scheduler linkage and instance deep-linking
- Integration Broker activity and queue depth
- Runtime graph API connecting sessions, processes, operators, AEs, Oracle SQL, and IB services
- Runtime alerts for process errors, long processes, queue depth, blocking sessions, high wait, and domain health

### ✅ Completed (2026-07-02) — Operational Dashboard

- `/admin/` home page replaced with a live operational dashboard; auto-refreshes every 60s
- **Active Alerts panel** — calls `GET /api/runtime/alerts`; shows all active alerts with severity badges and deep-links; green "All Clear" when 0 alerts
- **Runtime Health panel** — calls `GET /api/runtime/status`; shows process total/active/error, AE running, IB pending with color-coded values
- **Log Intelligence panel** — aggregates source count, source errors, PRCS AE error count, IGW error total; shows last ingest timestamp
- **Environment & Trends panel** — drift alert count vs FSCM; 6h runtime metric sparklines (Active, Errors, IB, Alerts) from runtimedb history
- **Quick Navigation** — 16 deep-links to every major platform section in one bar
- Log-based alert checks added to `connectors/alerts.py`: `_check_igw_errors()` (IGW spike >20/h), `_check_log_error_spike()` (non-IGW errors >30/h), `_check_prcs_ae_failures()` (PRCS AE failures in last 24h), `_check_error_trend()` (runtimedb trend detection: process_error going from 0→N)

### ✅ Completed (2026-07-02) — Runtime History Persistence

- `connectors/runtimedb.py` — SQLite store at `data/runtime.db`; one row per 5-minute scheduler cycle per env; columns: process_active, process_error, process_total, ae_running, ib_pending, alert_count; `record()`, `get_history()`, `prune()` (30-day retention)
- `connectors/scheduler.py` — `_runtime_snapshot_loop()` thread (5-minute interval); calls process_status_summary + ib_queue_summary + evaluate_alerts; records to runtimedb; integrated into `start()`/`stop()`/`status()`
- `routers/runtime.py` — `GET /api/runtime/history?env&hours` time-series endpoint; `GET /api/runtime/history/snapshot` manual trigger
- `routers/admin/runtime.py` — "Metrics History" card on Runtime Monitor: 1h/6h/24h/7d period selector; sparkline SVG charts for Active Processes, Process Errors, AE Running, IB Pending, Alerts; trend arrows (↑↓→) colored by whether the metric increasing is good or bad; `loadHistory()` called on every refresh cycle

### ✅ Completed (2026-07-03) — App Server Process Tracking

Domain-level enumeration (`psdb.app_server_domains`) only sees Oracle's
`PSPMDOMAIN_VW` view — no live process detail. This goes one level deeper:

- `connectors/sshclient.py` — new `run_command(alias, command, timeout)`
  generic SSH command runner (read-only; joins the existing `list_files`/
  `read_bytes` helpers)
- `connectors/appsrvproc.py` — SSH `ps -eo pid,ppid,pcpu,pmem,etime,cmd` on
  the app server host; parses Tuxedo command lines for known PeopleSoft
  server binaries (PSAPPSRV, PSAESRV, PSSAMSRV, PSBRKHND, PSMSTPRC, PSDSTSRV,
  PSMONITORSRV, BBL, WSL/WSH, JSL/JSH); extracts domain name (`-C dom=`),
  group/server ID, and database name (`-D`/`-CD`/`-PS`) from each process's
  Tuxedo-encoded arguments. Note: `-S NAME` is a legitimate, more-specific
  server-group name for PeopleSoft app-level servers (e.g. `PSBRKHND_dflt`)
  but means something else entirely (shared-memory key, buffer size) for
  Tuxedo infrastructure processes (BBL/WSL/WSH/JSL/JSH) — the parser only
  applies that override for the former.
- `routers/runtime.py` — `GET /api/runtime/appserver-processes?env=` resolves
  the SSH host from `log_sources` (type `appsrv`/`prcs_ae`) for the env, lists
  live processes, and rolls up per-domain/per-server-type summaries
- `routers/admin/runtime.py` — new "App Server Processes" card on the Runtime
  Monitor page, refreshed on every cycle alongside domains/servers

**Remaining — blocked on live traffic data (2026-07-03 investigation):**
- **Browser session tracking**: would reconstruct sessions from `web_entries`
  (PIA access log: ip/oprid/url/ts — plenty of columns to group into sessions
  by idle-gap) but `PIA_access.log` is 0 bytes on this box — no HTTP access
  logging is active in this lab's WebLogic domain, so there is nothing to
  ingest or verify against. Triggered a full `/api/logs/ingest` and confirmed
  `web_entries` stays empty.
- **WebLogic session tracking**: `PIA_weblogic.log` does have 2.2MB of real
  content, but it's exclusively startup/health/diagnostics noise (`<PIA>`,
  `<WorkManager>`, `<Health>`, etc.) — zero session-lifecycle log lines
  (`grep -i session` returns nothing). No live HTTP session activity to track
  in this environment either.
- Both would need either real end-user browser traffic hitting PIA, or
  enabling WebLogic HTTP access + session-event logging on the domain, before
  there's anything to build against.

---

## Runtime Timeline

Persist runtime snapshots.

### ✅ Completed

- Knowledge Graph snapshots (creation, listing, loading, deletion, scheduled daily builds, retention pruning)
- Graph-based drift detection comparing live graph to most-recent snapshot

### ✅ Completed (2026-07-02)

- Runtime history persistence: `connectors/runtimedb.py` SQLite store, 5-minute snapshot loop in scheduler
- Trend graphs (1h/6h/24h/7d sparklines) on Runtime Monitor for Active Processes, Process Errors, AE Running, IB Pending, Alerts
- Runtime snapshot creation integrated into scheduler (separate from graph snapshots)

---

## Runtime Topology

Interactive infrastructure topology.

### ✅ Completed

- App Server domain enumeration with type classification (App Server, Process Scheduler, Web/PIA, Integration Broker)
- Runtime graph visualization with force-directed layout connecting all runtime object types
- Interactive topology diagram `/admin/topology` — fixed SVG layout: Browser → nginx → WebLogic → App Server → Process Scheduler → Oracle → Integration Broker; kind-colored borders, left-edge status bars, ONLINE/OFFLINE/UNKNOWN indicators (2026-07-02)
- Live status indicators per infrastructure component — status dot top-right, left status bar, click-to-detail panel (2026-07-02)

---

## Incident Recording

Capture complete runtime incidents.

### ✅ Completed

- `connectors/incidentdb.py` (`data/incidents.db`) — `incidents` (title, env,
  severity, state, RCA window, notes) + `incident_snapshots` (source:
  rca/process/log/ash/ib/kg, JSON blob, timestamp) — full runtime state
  capture, not just a summary row
- `routers/incident.py` — `/api/incidents` CRUD + `/api/incidents/{id}/snapshot`
  (re-run RCA and attach a fresh snapshot to an existing incident)
- `routers/admin/incidents.py` — `/admin/incidents` list + `/admin/incidents/{id}`
  detail/replay page (walks back through the captured snapshots for
  post-incident troubleshooting)
- Integrated with Incident RCA (`/admin/rca`) for pre-populated capture

---

# Phase 5 — Complete Knowledge Graph

Continue expanding object coverage.

## Knowledge Graph Providers

### ✅ Completed Providers

- Operators, Roles, Permission Lists
- Components, Pages, Records, Fields
- PeopleCode programs
- Application Engines
- Integration Broker (Services, Nodes, Queues, Routings)
- Menus
- Trees
- SQL Definitions (standalone)
- PS Queries (public)
- Component Interfaces
- Portal Registry
- Application Packages
- Message Catalog
- Approval Framework (rewritten 2026-06-30 against verified EOAW tables: PS_EOAW_TXN/PRCS/STAGE/STEP/PATH)
- XML Publisher Reports (rewritten 2026-06-30 against verified PSXPRPTDEFN/PSXPDATASRC/PSXPRPTTMPL/PSXPTMPLDEFN/PSXPRPTOUTFMT)
- Search Definitions (rewritten 2026-06-30 against verified PSPTSF_SD keyed by PTSF_SOURCE_NAME; prior version used APPCLASSID which is blank on all rows)
- Search Categories (rewritten 2026-06-30 against verified PSPTSF_SRCCAT keyed by PTSF_SRCCAT_NAME)
- PivotGrid Definitions (added 2026-06-30; PSPGCORE, 154 rows, keyed by PTPG_PGRIDNAME; sub-tables PSPGMODEL/PSPGSETTINGS/PSPGNUIOPT)
- Connected Query Definitions (added 2026-06-30; PSCONQRSDEFN, 97 rows, keyed by CONQRSNAME; sub-tables PSCONQRSMAP/PSCONQRSFLDREL showing parent-child query composition)
- Process Definitions (added 2026-06-30; PS_PRCSDEFN, 2873 rows, composite key PRCSTYPE~PRCSNAME; sub-tables PS_PRCSDEFNPNL/PS_PRCSDEFNGRP; types: AE, SQR, XML Publisher, COBOL, Data Mover)
- File Layout Definitions (added 2026-06-30; PSFLDDEFN, 533 rows, keyed by FLDDEFNNAME; sub-tables PSFLDSEGDEFN/PSFLDFIELDDEFN; formats: Fixed Width, Delimited, XML)
- Translate Values (added 2026-06-30; PSXLATDEFN/PSXLATITEM, 10769 fields with 49177 values total; keyed by FIELDNAME; effective-dated; shows active/inactive value sets with long/short names)
- App Designer Projects (added 2026-06-30; PSPROJECTDEFN, 3488 rows, keyed by PROJECTNAME; sub-table PSPROJECTITEM with 200086 object items; 40+ object type codes decoded; includes PTADS* automated delivery projects)
- IB Message Definitions (added 2026-06-30; PSMSGDEFN, 4272 rows, keyed by MSGNAME; sub-tables PSMSGVER/PSMSGREC; shows versions and schema record hierarchy for each message)
- IB Application Services (added 2026-06-30; PSIBAPPLDEFN, 13 apps, keyed by PTIBAPPLNAME; sub-tables PSIBAPPMETHOD/PSIBAPPURI/PSIBAPPTRAN/PSIBAPPLSTATES; shows REST endpoint operations with HTTP methods and URI templates; covers Chatbot, Fluid/Mobile, Payroll, Absence, Recruitment ASF services)
- Application Class Definitions (added 2026-06-30; PSAPPCLASSDEFN, 12622 rows across 1860 packages; compound key PACKAGEROOT~QUALIFYPATH~APPCLASSID; displays full PeopleCode path, sibling classes in same sub-package, and sub-package inventory; QUALIFYPATH `:` indicates root-level class)
- Content Service Provider Definitions (added 2026-06-30; PSPTCSSRVDEFN, 1016 rows; keyed by PTCS_SERVICEID; URL types: Page Component/App Class/Utility/Generic/Script; sub-tables PSPTCS_PARAMS (parameters) and PSPTCS_MNULINKS (where-used portal objects); powers Related Actions, WorkCenters, Fluid navigation)
- PeopleTools Test Framework Tests (added 2026-06-30; PSPTTSTDEFN, 161 rows; keyed by PTTST_NAME; types Script/Shell/Library; sub-tables PSPTTSTCASE (test cases) and PSPTTSTCOMMAND (step-by-step commands with page/field context); NOTE: PTTST_LANG_CD is a single space for most rows — filter uses IN (' ', 'ENG') not TRIM)
- Application Data Set Definitions (added 2026-06-30; PSADSDEFN, 309 rows; keyed by PTADSNAME; PTKEYCOL1-8 enumerate primary key columns for the managed data; sub-table PSADSDEFNITEM (1706 rows) lists the PeopleSoft records composing each ADS with parent-child hierarchy; sub-tables PSADSGROUP/PSADSGROUPMEMB show field grouping; ADS is the PeopleTools framework for migrating configuration data between environments)
- IB Service Groups (added 2026-06-30; PSIBGROUPDEFN, 111 rows; keyed by IB_INTGROUPNAME; PSIBSRVGROUP membership table (456 rows) lists member service operations per group; groups are logical channels for IB service operation routing)
- URL Definitions (added 2026-06-30; PSURLDEFN, 268 rows; keyed by URL_ID; stores named URL catalog entries — types include Record (record://), HTTP, FTP, Email (mailto:), and Variable (%VAR%); used by components and application classes to reference configurable external URLs)
- Chatbot Skill Definitions (added 2026-06-30; PSCBAPPLDEFN, 60 rows; keyed by PTCBAPPLNAME; PeopleSoft Digital Assistant chatbot skill handlers backed by App Class methods; sub-tables PSCBAPPLPARAM (441 rows, typed input/output parameters with STR/INT/DATE/BOOL/OBJ types) and PSCBAPPLSTATES (200 rows, named result states with Success/Error/Warning/Info categories); all 60 skills are Active type M)
- IB Routing Definitions (added 2026-06-30; PSIBRTNGDEFN, 546 named rows (filter NOT LIKE '~%' to exclude ~GENERATED~ and ~GEN~UPG~ rows); keyed by ROUTINGDEFNNAME; shows sender→receiver node mapping for each IB operation version; types S=Synchronous/A=Asynchronous/R=REST; sub-table PSIBRTNGSUBDEFN (559 named rows) shows aliasname entries per routing; transform handlers (ONSNDHDLRNAME/ONRCVHDLRNAME/ONPREHDLRNAME/ONPOSTHDLRNAME) shown when set)
- Style Sheet Definitions (added 2026-06-30; PSSTYLSHEETDEFN, 602 rows; keyed by STYLESHEETNAME; types 0=Classic(53)/1=Fluid Theme(39)/2=Component Style(510); PSSTYLECLASS (3490 rows) lists CSS class names per sheet (capped at 300 per detail view); PTSTYLEDEF_TANGERINE and PTSTYLEDEF are the main Fluid themes with 300+ classes; search supports type filter)
- Data Archive Object Definitions (added 2026-06-30; PSARCHOBJDEFN, 76 rows; keyed by PSARCH_OBJECT; PSARCHOBJREC (493 rows) shows source record → history record mapping with PSARCH_BASETABLE flag; supports PeopleSoft Data Archiver framework for compliance/housekeeping)

### ⚠️ Stub Providers (no live backing tables found in verified HCM schema)

Live schema verification (2026-06-30) found no SYSADM tables for these features.
All four are gracefully guarded by `has_table()` in psdb.py/graphdb.py and return empty/error results without crashing.
Marked `"stub": True` in OBJECT_REGISTRY. Table-name candidates in ptmetadata.py preserved for future investigation on other environments.

- Navigation Collections — `PTNC_COLLECTION` does not exist (PSPTPNCOLL is Push Notification Collections, 3 rows, unrelated feature)
- Event Mappings — `PSEFMAPPINGDEFN` does not exist
- Related Content — `PSRELCONDEFN` does not exist
- Drop Zones — `PSPTDZDEFN` does not exist

### ⛔ Deprioritized Providers

Investigated and deprioritized as of 2026-07-01. All are guarded by `has_table()` returns empty/stub results without crashing. Documented here for future re-evaluation on different environments or PeopleTools versions.

| Provider | Tables | Reason deprioritized |
|---|---|---|
| IB Schema Definitions | PSIBSCMADATA / PSIBSCMADFN | PSIBSCMADATA stores raw XML as CLOB chunks — not browsable; PSIBSCMADFN visible in `all_objects` but no SELECT grant in HCM; PSMSGDEFN already covers message structure |
| Navigation Collections | PTNC_COLLECTION | Does not exist in HCM; PSPTPNCOLL is Push Notification Collections (unrelated) |
| Event Mappings | PSEFMAPPINGDEFN | Does not exist in HCM |
| Related Content | PSRELCONDEFN | Does not exist in HCM |
| Drop Zones | PSPTDZDEFN | Does not exist in HCM |
| WorkCenters | — | No standalone definition header table; EOWC tables are runtime config keyed by portal object name |
| Dashboards | PS_EOEN_DASHBRD | 0 rows in HCM |
| BI Publisher / Branding / Page Composer | — | No backing definition tables in HCM SYSADM schema |
| Fluid Homepage / Tile Definitions | PSPGEDEFN / PSFLPGCOLLECT / PSHPDEFN / PSTILEDEFN | All absent or 0 rows in HCM |
| Activity Guide Collections | PS_AGC_TILE_TBL | 2 rows — too few to be useful |
| File Reference Definitions | PSFILEREDEFN | 19,622 rows but mostly system graphics/script refs with no descriptions; marginal value |
| Business Process Definitions | PSBUSPROCDEFN | 133 rows of legacy Workflow Navigator definitions from 2000–2002; deprecated framework |
| IB Local Schema | PSLSDEFN | 319 rows of XML schema stored as compressed binary data; display impractical |
| IB Service Setup | PSIBSVCSETUP | Single-row global IB gateway config; not a browsable catalog |

---

## Relationship Expansion

Continue enriching graph relationships.

### ✅ Completed

- Shared UOM relationship graph helper introduced; all in-module UOM object graph previews now use it, including Field, Record, Component, Page, Portal Registry, Operator, Role, Permission List, IB Service Operation, IB Node, IB Queue, IB Routing, SQL Definition, Tree, Component Interface, and other compact UOM previews
- Generic `/api/peoplesoft/graph/{type}/{name}` now resolves canonical object types through UOM first, so Graph Explorer compact graph previews align with Object Explorer for Record, Operator, Role, Permission List, Component, Page, Portal Registry, IB Node/Queue/Routing, Tree, CI, SQL Definition, and future UOM-backed providers
- PeopleCode and Application Engine domain graph endpoints now declare `_source`, `_vocabulary`, and `_semantics` and expose Knowledge Graph-compatible edge `type` aliases while preserving existing `relationship` labels
- Page graph API unified with UOM Page provider so Object Explorer and Graph Explorer share the same relationship model
- Component graph API unified with UOM Component provider so Object Explorer and Graph Explorer share the same relationship model
- CALLS, REFERENCES, USES, CONTAINS, WRAPS, SECURES edge types in active use
- Component security graph edges through Permission Lists → Roles → Operators
- Menu → Component CONTAINS edges
- CI → Component WRAPS edges
- Application Engine → Process Definition GENERATES edges in persisted Knowledge Graph ingestion
- Application Engine SQL step READS/WRITES edges in persisted Knowledge Graph ingestion, with AE section/step metadata
- SQL Definition body READS/WRITES edges in persisted Knowledge Graph ingestion, using PSSQLTEXTDEFN text where grants allow
- PeopleCode literal SQL READS/WRITES edges in persisted Knowledge Graph ingestion for direct `SQLExec("...")` and `CreateSQL("...")` calls
- Project → object DEPLOYS edges in persisted Knowledge Graph ingestion for safely mapped PSPROJECTITEM object types
- Project UOM object pages and compact graph previews expose the same Project → object DEPLOYS relationship model
- Persisted Knowledge Graph payloads now advertise `_source`, `_vocabulary`, and `_semantics`, and normalize edge `relationship` aliases to match UOM/domain graph contracts
- PS Query UOM objects now expose records/output fields as `_relationships` and compact graph previews; persisted Knowledge Graph ingestion emits Query → Record `USES`, Query → Field `EXPOSES`, and Record → Field `CONTAINS` edges for public queries
- Menu UOM compact graph previews now use the shared relationship graph helper and align Menu → Component `CONTAINS` edges with persisted Knowledge Graph semantics
- Application Package UOM objects now expose classes/PeopleCode relationships and compact graph previews; persisted Knowledge Graph ingestion emits Application Package → App Class `CONTAINS` edges
- Application Package PeopleCode relationships now use real PSPCMPROG `PROGSEQ` identities and persisted Knowledge Graph ingestion emits App Class → PeopleCode `CONTAINS` edges
- Standalone App Class UOM objects now expose package/PeopleCode relationships and compact graph previews with App Class → Package `BELONGS_TO` and App Class → PeopleCode `CONTAINS` edges
- Content Service UOM objects now expose component/menu/app-class/query/portal usage relationships and compact graph previews; persisted Knowledge Graph ingestion emits Content Service → target `USES` edges
- Connected Query UOM objects now expose component query and field-join relationships with compact graph previews; persisted Knowledge Graph ingestion emits Connected Query → PS Query `USES` and parent Query → child Query `CONTAINS` edges
- XML Publisher Report UOM objects now expose datasource relationships and compact graph previews for PS Query / Connected Query data sources; persisted Knowledge Graph ingestion emits XML Publisher Report → PS Query / Connected Query `USES` edges where `DS_TYPE` is `QRY` or `CQR`
- PTF Test UOM objects now expose menu/component/page/record/field relationships from command metadata with compact graph previews; persisted Knowledge Graph ingestion emits PTF Test → touched object `USES` edges
- Process Definition UOM objects now expose run-control component relationships and implementation links for Application Engine / XML Publisher process types; persisted Knowledge Graph ingestion emits Process Definition → Component `USES` and Process Definition → implementation `WRAPS` edges
- IB Message UOM objects now expose schema record relationships with compact graph previews; persisted Knowledge Graph ingestion emits Message → Record and parent Record → child Record `CONTAINS` edges from PSMSGREC default-version metadata
- File Layout UOM objects now expose segment record and layout field relationships with compact graph previews; persisted Knowledge Graph ingestion emits File Layout → Record/Field and Record → Field `CONTAINS` edges from PSFLDSEGDEFN/PSFLDFIELDDEFN metadata
- ADS Definition UOM objects now expose managed record relationships with compact graph previews; persisted Knowledge Graph ingestion emits ADS Definition → Record and parent Record → child Record `CONTAINS` edges from PSADSDEFNITEM metadata
- Tree → Record USES edges
- Impact analysis (forward and reverse dependency traversal with depth control)

### Remaining

- Continue aligning provider-specific Knowledge Graph ingestion with UOM `_relationships` / `_graph` relationship definitions

### ✅ Completed (2026-07-03) — Dynamic SQL READS/WRITES coverage

Closes the "non-literal PeopleCode dynamic SQL" gap. Previously,
`extract_literal_sql()` only captured `SQLExec("...", ...)` /
`CreateSQL("...")` calls whose *first argument* was an inline string
literal — `SQLExec(&strSQL, ...)` (SQL built into a variable beforehand)
produced zero READS/WRITES edges, silently dropping real table access.

- `connectors/peoplecode.py` — new `extract_dynamic_sql()`: finds
  `SQLExec(&var, ...)` / `CreateSQL(&var)` calls, then scans backward for
  every `&var = ...` / `&var = &var | ...` (self-append) assignment earlier
  in the same program, extracts the string *literal* fragments from each
  assignment's RHS (ignoring variables, function calls, `%Table()` bind
  placeholders), and concatenates them in source order into reconstructed
  SQL text. Purely textual — no expression evaluation. Returned as
  `dynamic_sql` alongside the existing `literal_sql` in `references()` /
  `references_for_program()`.
- `connectors/graphdb.py` — persisted KG ingestion loop now also processes
  `refs["dynamic_sql"]` through the existing `sql_record_access()` table
  scanner, adding `peoplecode → record` READS/WRITES edges tagged
  `source: peoplecode_dynamic_sql, confidence: low` (vs. `peoplecode_literal_sql`
  for the original single-literal-call path)
- Dynamically-chosen table names (e.g. `"FROM PS_" | &recname`) are
  correctly **not** guessed — the reconstructed text has a dangling `PS_`
  with no adjacent word characters, which the existing `PS_[A-Z0-9_]+`
  table-name regex simply doesn't match, so no edge is produced. Verified
  this directly: `sql_record_access('SELECT ... FROM PS_ WHERE ...')` →
  `{"reads": [], "writes": []}`, no false positive.

**Verified against real PeopleCode from this environment**:
`HR_JOBDATA_UTILITIES.ADDITIONALINFO.PERSONINFO.ONEXECUTE.0` builds its JOB
lookup SQL across four `&strSQL = ...` / `&strSQL = &strSQL | ...`
statements before calling `SQLExec(&strSQL, ...)` — previously invisible to
KG ingestion entirely. `extract_dynamic_sql()` correctly reconstructs the
full SQL text and `sql_record_access()` correctly derives `READS: JOB`.
`make check` 91/91; smoke test 68/68.

---

## Cross References

Every object should answer:

### ✅ Completed

- What references me? (implemented for AE SQL steps via `%SQL()`, PeopleCode source references, SQL cross-references)
- What do I reference? (implemented for Components, Pages, Records, AE programs, Portal Registry)
- Who secures me? (implemented for Components, Pages, Permission Lists, Portal Registry with access-path visualization)
- What breaks if I change? (impact analysis via Knowledge Graph traversal)
- Child records, subrecord derivations, and AE state records for Record objects

### ✅ Completed (2026-07-02)

- Record objects: `READS / WRITES` section — lists every AE/SQL/PeopleCode program that reads or writes this record, sourced from Knowledge Graph inbound READS/WRITES edges; WRITES-first sort
- Record objects: `Components Using This Record` section — lists components with inbound USES edges from the KG; surfaces components that reference this record as search/data record
- Application Engine objects: `Records Read / Written` section — lists every record touched by this AE, sourced from outbound READS/WRITES KG edges
- Application Engine objects: `Invoked By (Process Definitions)` section — lists process scheduler definitions that wrap/invoke this AE via inbound WRAPS KG edges
- SQL Definition objects: `Records Read / Written` section — lists records accessed by this SQL definition, sourced from outbound READS/WRITES KG edges
- PeopleCode objects: `Records Read / Written` section — lists records accessed by PeopleCode programs with READS edges in the KG
- Knowledge Graph Neighbors edge types: all neighbor items now show the actual edge type (CONTAINS, USES, REFERENCES, READS, …) instead of generic 'neighbor'
- Record objects: `Pages Using This Record` section — lists pages with inbound USES edges from the KG
- Record objects: `Projects Deploying This Record` section — lists projects with inbound DEPLOYS edges from the KG
- Page objects: `Projects Deploying This Page` section — lists projects with inbound DEPLOYS edges
- Component objects: `Projects Deploying This Component` section — lists projects with inbound DEPLOYS edges
- Record objects: `Queries Using This Record` section — lists PS Query definitions with USES edges (171 edges in HCM KG)
- Record objects: `PTF Tests Covering This Record` section — lists PTF automated tests with USES edges (235 edges in HCM KG)
- Generic `_attach_inbound_xref()` helper in `routers/peoplesoft.py` — reusable cross-reference builder for any (src_type, edge_type) combination; silently skips when no KG edges exist

### ✅ Completed (2026-07-02)

- IB Message UOM: `Service Operations` section — operations that reference this message via PSOPERATION.MSGNAME (REST) or IB_OPERATIONNAME match (traditional IB)
- IB Message UOM: `Routings` section — routings carrying this message via PSIBRTNGDEFN.IB_OPERATIONNAME
- IB Message UOM: `Subscriptions` section — pub/sub subscriptions registered for this message (PSSUBDEFN.MSGNAME)

### Remaining

- Universal "what references me / what do I reference" coverage across all object types
- ✅ Consistent cross-reference sections for tree, portal UOM providers (Done 2026-07-03)
  - Tree: "Record Keyed by This Tree" (outbound USES → record), "Projects Deploying This Tree" (inbound DEPLOYS)
  - Portal Registry: "Projects Deploying This Portal Object", "Content Services Linking to This Portal Object"
  - Generic `_attach_outbound_xref()` helper added alongside existing `_attach_inbound_xref()`
- ✅ Consistent cross-reference sections for message UOM provider (Done 2026-07-03)
  - Message: "Records Contained in This Message" (outbound CONTAINS → record), "Projects Deploying This Message" (inbound DEPLOYS)
  - Project provider intentionally left to the generic "Knowledge Graph Neighbors" section — its DEPLOYS targets span nearly every object type, so a dedicated per-type xref section would just duplicate that list

---

# Phase 6 — Environment Intelligence

## Continuous Drift Detection

### ✅ Completed

- Knowledge Graph drift: compares current live graph against most-recent snapshot; surfaces new, removed, and changed nodes by type in the Graph Explorer DRIFT tab

### ✅ Completed (2026-07-01)

- Knowledge Graph drift: compares current live graph against most-recent snapshot; surfaces new, removed, and changed nodes by type in the Graph Explorer DRIFT tab
- Menu comparison (`/api/envcompare/menus`) — diffs PSMENUDEFN (637 rows) including menutype, description, owner, timestamp
- Tree comparison (`/api/envcompare/trees`) — diffs PSTREEDEFN (326 rows), latest effective row per tree; shows status, description, timestamp
- IB Routing comparison (`/api/envcompare/ib_routings`) — diffs PSIBRTNGDEFN named routings (auto-generated excluded); shows type, operation, sender/receiver nodes
- IB Message comparison (`/api/envcompare/ib_messages`) — diffs PSMSGDEFN (4272 rows); shows status, description, owner
- Component Interface comparison (`/api/envcompare/ci`) — diffs PSBCDEFN; shows type, description, backing component (added 2026-07-01)
- AE step/body comparison (`/api/envcompare/ae-body`) — step-level diff; SQL text via PSAESTMTDEFN/PSSQLTEXTDEFN; unified diff per changed step (added 2026-07-01)
- Summary sidebar updated with Menus, Trees, IB Routings, IB Messages, Comp. Interfaces counts
- Environment Compare UI updated with 5 new tabs (Menus, Trees, IB Routings, IB Messages, Comp. Interfaces) + AE body drill-down within AE tab

### Remaining

- **Auto-detection from PSPROJECTDEFN**: see Promotion History section below.

### ✅ Completed (2026-07-01)

- Scheduled drift reports: `driftdb.py` SQLite store + scheduler daemon integration — runs envcompare summary after each graph snapshot cycle, persists point-in-time counts, auto-generates threshold alerts (|delta| ≥ 50) and growth-rate alerts (delta grows >10%), auto-resolves when drift subsides
- `/api/drift/snapshot` (POST) — manual trigger
- `/api/drift/latest`, `/api/drift/history`, `/api/drift/alerts` (GET)
- `/admin/drift` — drift history UI with sparklines, alert table, and Snapshot Now button

---

## Environment History

Maintain historical snapshots.

### ✅ Completed

- Environment comparison across HCM and FSCM for Records, Fields, PeopleCode, SQL Definitions, PS Queries, Portals, and Knowledge Graph
- Portal object deep comparison (definition diff, children diff, permissions diff)
- Operator comparison (roles, permission lists, component access diff between two OPRIDs)

### ✅ Completed (2026-07-01)

- Point-in-time runtime snapshots: every drift cycle stores a full count snapshot in `drift.db` (16 object types per environment pair, timestamped)
- Temporal history of security and metadata changes: drift history API returns per-type time series; Drift History admin page visualizes trends with delta sparklines

### ✅ Completed (Phase 1 — 2026-07-01)

- Promotion event log: `connectors/promotiondb.py` SQLite store + `routers/promotions.py` REST API
  - `POST /api/promotions` — record an event (pillar, project, from_env, to_env, date, by, notes, ticket_ref)
  - `GET /api/promotions` — list events with pillar/project/env filters
  - `GET /api/promotions/timeline` — chronological view for a single project
  - `GET /api/promotions/summary` — per-project latest promotion summary for a pillar
  - `DELETE /api/promotions/{id}` — remove a record
  - `/admin/promotions` — log form + filterable timeline table; env suggestions (DV/TST/UAT/CRP/PAR/PER/PRD)
  - Phase 1 note displayed in UI; "Promotions" added to Runtime nav group

### Remaining (Phase 2 — Future)

- **Auto-detection from PSPROJECTDEFN**: when DV/TST/UAT/PRD Oracle DB connections are added to
  `config.json`, snapshot `PSPROJECTDEFN.LASTUPDDTTM` per environment, detect when a project's
  timestamp in the target env advances to match the source env — automatically record a promotion event.
  The Phase 1 SQLite schema and API are already designed to accommodate this without structural changes.
- **Lab context**: this system is a development lab. Promotion-chain environments (DV/TST/UAT/PRD)
  do not exist yet. HCM and FSCM are separate application pillars and are NOT in a promotion chain
  with each other. Phase 2 implementation begins when real promotion-chain DB connections are available.

---

## Impact Forecasting

Predict downstream impact before migration.

### ✅ Completed

- Knowledge Graph impact analysis (forward and reverse dependency traversal, upstream/downstream node enumeration by type)
- AE restart eligibility analysis

### ✅ Completed (2026-07-01)

- Pre-migration impact reports: `/admin/impact` — full project impact report with KG traversal, affected node breakdown by type, and per-object downstream count; warns when KG coverage is insufficient
- Deployment risk scoring: `/api/impact/risk` — KG-independent risk assessment using drift snapshot data; weights object types by risk (security=5×, PeopleCode/IB=4×, AE/SQL=3×, others=1×); returns per-type drift level (Minor/Moderate/Significant/Major) and overall risk label (Low/Medium/High/Critical); auto-loads on `/admin/impact` page open

---

# Phase 7 — AI Engineering Assistant

Leverage the knowledge graph and source search for natural-language engineering assistance.
Answer questions like "Where is employee termination implemented?", "Which AEs update PS_JOB?",
"Who has access to this component?", or "Show me the SQL definitions that touch COMPENSATION."

---

## Architecture (decided 2026-07-01)

### Provider Abstraction

All AI communication goes through a single abstract interface in `connectors/ai.py`.
Provider-specific implementations live in separate modules. Nothing above the connector
layer touches provider-specific code.

```
connectors/ai.py          ← get_provider() factory + AIProvider ABC
connectors/ai_claude.py   ← Anthropic SDK, native tool_use blocks
connectors/ai_openai.py   ← OpenAI SDK, function calling
connectors/ai_ollama.py   ← Ollama local REST API (no external key required)
connectors/ai_tools.py    ← Tool definitions wrapping existing PeopleSoft Hypergraph Intelligence connectors
```

**Design decision:** All three providers ship at launch. Ollama enables air-gap / lab use
with no external API key. The factory pattern means adding a fourth provider later requires
only a new `ai_<name>.py` file and a config entry.

### Config Shape (`config.json`)

```json
"ai": {
  "provider": "claude",
  "claude":  { "api_key": "sk-ant-...", "model": "claude-sonnet-4-6" },
  "openai":  { "api_key": "sk-...",     "model": "gpt-4o" },
  "ollama":  { "base_url": "http://localhost:11434", "model": "llama3.1" }
}
```

Only the active provider's section is used at runtime. API keys may also be supplied via
environment variables (`CLAUDE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`) — env vars
take precedence over config.json values when both are present.

**Design decision:** `config.json` is the primary source (consistent with DB credentials).
Environment variable override is available for CI/container deployments.

### Tools (AI-callable PeopleSoft Hypergraph Intelligence capabilities)

Each tool is a thin adapter over an existing connector function — no new SQL.

| Tool | Backs |
|------|-------|
| `search_objects` | `ptmetadata` global search |
| `peoplecode_search` | `peoplecode.source_search()` |
| `graph_dependencies` | `graphdb.dependency_tree()` forward |
| `graph_impact` | `graphdb.dependency_tree()` reverse |
| `who_has_access` | permlist/role/component security connectors |
| `ae_steps` | `ae.ae_steps()` |
| `sql_lookup` | `sqlws` read-only query execution |
| `envcompare_summary` | `envcompare.summary()` |
| `project_impact` | `impact.project_impact()` |

### UI — `/admin/assistant`

- Streaming chat window (SSE or chunked response)
- Provider/model badge showing active configuration
- Tool calls shown as collapsible "thinking" blocks (what was queried, what came back)
- Conversation history held in session (not persisted to disk)
- Example prompts for first-time users

---

## Natural Language Search Examples

- Where is employee termination implemented?
- Show every SQL touching PS_JOB.
- Which AEs update JOB?
- Which Components use this record?
- Who has access to the Benefits Administration component?
- What PeopleCode fires on save for PERSONAL_DATA?
- Compare security between HCM and FSCM.

---

## Implementation Status

### ✅ Completed (2026-07-01)

- Architecture design and provider abstraction pattern
- Tool inventory defined (backed by existing connectors)
- Config schema defined

### ✅ Completed (2026-07-01)

- `connectors/ai.py` — `AIProvider` ABC with `chat()`, `format_tool_call_turn()`, `format_tool_results_turn()` abstract methods; `get_provider()` factory; `provider_status()` (no secrets exposed)
- `connectors/ai_claude.py` — Anthropic SDK; native tool_use content blocks; Anthropic message history format
- `connectors/ai_openai.py` — OpenAI SDK; function calling; OpenAI message history format
- `connectors/ai_ollama.py` — Ollama local REST (`/api/chat`); OpenAI-compatible tool format; no external key required
- `connectors/ai_tools.py` — 9 tool definitions + dispatch: `search_objects`, `peoplecode_search`, `graph_dependencies`, `graph_impact`, `who_has_access`, `ae_steps`, `sql_lookup`, `envcompare_summary`, `project_impact`
- `routers/assistant.py` — `POST /api/assistant/chat` (blocking + SSE streaming); agentic loop up to 8 tool rounds; `GET /api/assistant/status`
- `/admin/assistant` — Chat UI: example prompts sidebar, provider/model badge, collapsible tool-call blocks, auto-resize textarea, Enter to send
- Provider message format isolation: each provider implements its own `format_tool_call_turn()` / `format_tool_results_turn()` so the router stays provider-agnostic
- `anthropic` and `openai` packages installed in venv
- `config.json["ai"]` section with provider selection + per-provider config; env var overrides (`CLAUDE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`)
- Tested end-to-end with OpenAI GPT-4o: `search_objects` tool called, 20 records returned, synthesized answer ✓

---

# Phase 8 — Log Intelligence

Ingest, store, query, and AI-analyze web server and application server logs from all
PeopleSoft infrastructure tiers. Surface errors with drill-down to responsible objects
and users, and guide engineers to a fix.

---

## Architecture (decided 2026-07-01)

### Infrastructure Tiers

PeopleSoft log sources covered:

| Tier | Log type | Parser | Notes |
|------|----------|--------|-------|
| F5 LTM load balancer | `f5_access` | Apache combined | HSL iRule output |
| nginx / Apache reverse proxy | `apache_access` / `apache_error` | Apache combined | Standard NCSA format |
| WebLogic PIA (web) | `pia_access` / `pia_error` | PIA NCSA extended | OPRID in auth field |
| Tuxedo App Server | `appsrv` | APPSRV format | OPRID, ORA-, PC errors |
| Tuxedo ULOG | `tuxedo` | ULOG format | Domain-level events |

### SSH Log Fetching

All log sources are remote — fetched via SSH/SFTP using paramiko.
- `ssh_hosts` in `config.json` defines reusable connection profiles (host, port, user, key or password)
- Each log source references an `ssh_host` alias
- File byte-offset tracking: only new content is fetched per cycle (no re-reading)
- Connection pool per host; auto-reconnect on failure
- Sources with `ssh_host: "local"` read files directly without SSH

### Config Shape

```json
"ssh_hosts": {
  "webserver1": { "host": "10.0.0.10", "port": 22, "username": "psadm1", "key_path": "~/.ssh/id_rsa" },
  "appserver1": { "host": "10.0.0.11", "port": 22, "username": "psadm1", "key_path": "~/.ssh/id_rsa" }
},
"log_sources": [
  { "name": "WEB1_ACCESS", "type": "pia_access",   "env": "HCM", "ssh_host": "webserver1",
    "path": "/opt/oracle/psft/pt/webserv/HCM/servers/PIA/logs/PIA_access*.log", "enabled": true },
  { "name": "WEB1_ERROR",  "type": "pia_error",    "env": "HCM", "ssh_host": "webserver1",
    "path": "/opt/oracle/psft/pt/webserv/HCM/servers/PIA/logs/PIA_stderr*.log", "enabled": true },
  { "name": "APP1",        "type": "appsrv",       "env": "HCM", "ssh_host": "appserver1",
    "path": "/opt/oracle/psft/cfg/appserv/HCM/LOGS/APPSRV_*.LOG", "enabled": true },
  { "name": "APP1_TUX",   "type": "tuxedo",        "env": "HCM", "ssh_host": "appserver1",
    "path": "/opt/oracle/psft/cfg/appserv/HCM/LOGS/TUXLOG.*", "enabled": true },
  { "name": "PROXY1",     "type": "apache_access",  "env": "HCM", "ssh_host": "webserver1",
    "path": "/etc/nginx/logs/access.log", "enabled": true },
  { "name": "F5_LTM",     "type": "f5_access",      "env": "HCM", "ssh_host": "local",
    "path": "/var/log/f5/access.log", "enabled": false }
]
```

### Storage — SQLite `data/logs.db`

```
log_sources    — source registry with last-ingest offset tracking (JSON per file)
web_entries    — parsed access log rows (oprid, component, page, status, ms, ts)
app_entries    — parsed APPSRV/ULOG rows (oprid, level, message, object_ref, ts)
log_errors     — extracted errors deduped by (source, ts, raw)
```

Indices on `ts`, `oprid`, `status`, `error_code`, `object_ref` for fast filtering.

### Session Chain Correlation

```
PSACCESSLOG (OPRID=GUACUSER, ts=10:22)
   ↓
web_entries WHERE oprid='GUACUSER' AND ts ∈ [login-15min, login+4h]
   ↓ component/page extracted from URL pattern /psp/{site}/{portal}/{node}/c/{menu}.{component}.{page}.GBL
app_entries WHERE oprid='GUACUSER' AND ts in same window
   ↓ ORA-, PeopleCode errors → extract table/component/AE names
log_errors  WHERE oprid='GUACUSER' → cross-ref with PS metadata
```

### Error Drill-Down

1. **Surface**: `/admin/log_errors` — grouped by error_code + object_ref, top-N by count
2. **Who**: which OPRIDs triggered the error, first/last seen
3. **What object**: record/component/AE name extracted from error message → links to PeopleSoft Hypergraph Intelligence pages
4. **Fix**: "Ask AI" pre-loads the assistant with the error context; AI uses existing tools
   (`peoplecode_search`, `record_usage`, `sql_lookup`) to diagnose and suggest a fix

### AI Tools Added

| Tool | Purpose |
|------|---------|
| `log_search` | Search web+app entries by OPRID, time range, component, text, level |
| `log_errors` | Surface and group errors; returns error_code, object_ref, count, sample |
| `session_log_chain` | Full web→app chain for an OPRID in a time window |

### Integration Gateway Log Consumption

PeopleSoft Integration Gateway writes gateway-specific diagnostic logs that must be consumed independently from standard PIA/WebLogic logs.

Additional log sources:

| Tier | Log type | Parser | Notes |
|------|----------|--------|-------|
| Integration Gateway | `igw_msg_log` | IGW HTML log parser | `msgLog.html`; gateway message activity, routing, service operation details |
| Integration Gateway | `igw_error_log` | IGW HTML log parser | `errorLog.html`; gateway exceptions, target connector failures, authentication failures, routing errors |

### Config Shape — Integration Gateway Logs

Integration Gateway logs are configured independently in `config.json`, allowing each web server to define its own gateway log paths.

```json
"igw_log_sources": [
  {
    "name": "HCM_WEB1_IGW_MSG",
    "type": "igw_msg_log",
    "env": "HCM",
    "ssh_host": "hcm_web1",
    "path": "/opt/oracle/psft/pt/webserv/HCM/applications/peoplesoft/PSIGW/msgLog.html",
    "enabled": true
  },
  {
    "name": "HCM_WEB1_IGW_ERROR",
    "type": "igw_error_log",
    "env": "HCM",
    "ssh_host": "hcm_web1",
    "path": "/opt/oracle/psft/pt/webserv/HCM/applications/peoplesoft/PSIGW/errorLog.html",
    "enabled": true
  }
]
```

### Process Scheduler Transport Support

Process Scheduler log retrieval must support both Unix/Linux and Windows-hosted scheduler servers.

Unlike app server and web server log ingestion, Process Scheduler domains may run on:

- Linux / Unix
- Windows Server
- mixed platform deployments

Therefore `prcs_log_sources` must allow an explicit retrieval method per source.

Supported transport types:

| Transport | Use case |
|----------|----------|
| `local` | Same-host file reads |
| `ssh_sftp` | Linux/Unix Process Scheduler servers |
| `smb` | Windows Process Scheduler servers via file share |
| `winrm` | Windows Process Scheduler servers via remote command/file retrieval |
| `agent` | Future lightweight PHI collector agent installed on scheduler host |

### Updated Config Shape — Process Scheduler Logs

```json
"prcs_log_sources": [
  {
    "name": "HCM_PRCS_LINUX_DOMAIN",
    "type": "prcs_scheduler",
    "env": "HCM",
    "platform": "linux",
    "transport": "ssh_sftp",
    "ssh_host": "hcm_prcs_linux1",
    "path": "/opt/oracle/psft/cfg/appserv/prcs/HCM/LOGS/*.LOG",
    "enabled": true
  },
  {
    "name": "HCM_PRCS_WINDOWS_OUTPUT",
    "type": "prcs_process_log",
    "env": "HCM",
    "platform": "windows",
    "transport": "smb",
    "smb_host": "hcm-prcs-win1",
    "share": "PS_CFG_HOME",
    "path": "appserv\\prcs\\HCM\\files\\log_output\\*\\*\\*.log",
    "enabled": true
  },
  {
    "name": "HCM_PRCS_WINDOWS_TRACE",
    "type": "prcs_trace",
    "env": "HCM",
    "platform": "windows",
    "transport": "winrm",
    "winrm_host": "hcm-prcs-win1",
    "path": "C:\\psft\\pt\\8.61\\appserv\\prcs\\HCM\\files\\log_output\\*\\*\\*.tracesql",
    "enabled": false
  }
]
```

---

## Implementation Status

### ✅ Completed (2026-07-01)

- Architecture design and config schema
- `connectors/sshclient.py` — paramiko SSH/SFTP wrapper with connection pooling and byte-offset tracking
- `connectors/logparser.py` — PIA access/error/servlet/weblogic/stdout, APPSRV, Tuxedo ULOG, Apache/nginx, F5 parsers; PS-specific error code extraction (ORA-XXXXX, HTTP_NNN, IB_PCODEWOL, IB_EXT_APP, AUTH_FAIL, WEBPROFILE_ERR); object reference extraction; OPRID extraction from message body
- `connectors/logdb.py` — SQLite storage with web_entries/app_entries/log_errors tables; `re_extract_errors()` backfill for improved extraction patterns
- `connectors/logingest.py` — ingestion orchestration with per-file byte-offset tracking
- `connectors/scheduler.py` — 60s log ingest job integrated with graph snapshot scheduler
- `routers/logs.py` — REST API: sources, web, app, errors (with summary grouping), session chain, search, ingest trigger, re-extract trigger
- `routers/admin/logs.py` — `/admin/logs` (source overview), `/admin/log_errors` (grouped error surface with Ask AI), `/admin/log_viewer` (filtered web/app/error browser), `/admin/log_session` (OPRID session chain)
- AI tools: `log_search`, `log_errors`, `session_log_chain` in `connectors/ai_tools.py`
- 7+ active log sources ingesting live HCM data; error surface groups errors by code+object (HTTP_502, IB_PCODEWOL, WEBPROFILE_ERR, AUTH_FAIL, IB_EXT_APP)
- Transaction Tracing timeline: sort toggle (ascending/descending), web log entries included via `_SYSTEM_LOG_SOURCES` correlation

### ✅ Completed (2026-07-02) — PRCS AE server log pipeline

- `connectors/logparser.py` — `parse_prcs_ae()` parser for PSAESRV Tuxedo log format; extracts AE applid → `object_ref`, process instance from message body, error detection on Status=Error / Java exceptions
- `connectors/logingest.py` — `prcs_ae` added to `_APP_TYPES`; registered in standard ingest path
- `connectors/logdb.py` — `prcs_ae_summary()` aggregates by program with run_count/error_count/date range, extracts process instance from recent error messages
- `config.json` — `HCMDMO_PRCS_AE` source ingesting `AESRV_*.LOG*` files via SSH glob; 2,604 entries ingested from 11 historical files; 4 errors (PTSF_GENFEED × 2 June 22/23)
- `routers/runtime.py` — `GET /api/runtime/process-log?env&instance` returns chronological AESRV entries for a process instance via `raw LIKE '%Process Instance=N%'`
- `routers/admin/runtime.py` — "Exec Log" tab added to Process Instance detail panel; lazily loaded on tab click; links AE programs to AE Explorer
- `routers/logs.py` — `GET /api/logs/prcs-ae-summary` endpoint
- `routers/admin/logs.py` — `/admin/prcs-ae` analytics page: stat cards, program breakdown table with error rate bar, recent errors with process instance links to Runtime Monitor

### ✅ Completed (2026-07-02) — IGW errorLog.html pipeline

- `connectors/logparser.py` — `parse_igw_error_log()` HTML block parser; 12 regex patterns extract timestamp, description, exception, error_level, stack trace, request XML, IB operation, requesting node, HTTP status, message codes; `_IGW_ERROR_LABELS` maps exception class names to error codes (IB_EXT_APP, IB_GFW, IB_HTTP_TC, IB_EXT_CONTACT, IB_LISTEN)
- `connectors/logingest.py` — `_BLOCK_TYPES = {"igw_error_log"}` branch; processes entire HTML content, holds back partial trailing `<BODY>` block across ingest cycles
- `connectors/logdb.py` — `igw_summary()` aggregation: by error_code / IB operation / requesting node; schema migrations `idx_app_unique` (dedup) and `idx_err_unique` (multi-code per entry)
- `connectors/logdb.py` — `_SYSTEM_LOG_SOURCES` includes `"igw"` so IGW entries appear in session chain timelines
- `config.json` — `igw_log_sources` array; HCM_IGW_ERROR source ingesting `errorLog*.html` via SSH glob
- `routers/logs.py` — `GET /api/logs/igw-summary` endpoint
- `routers/admin/logs.py` — `/admin/igw` IGW Error Analytics page: stat cards, error code chips, IB operation breakdown with relative bars, requesting node breakdown with Ask AI links, recent entries table with IB Explorer cross-links
- `routers/admin/_core.py` — "IGW Errors" nav entry
- `routers/assistant.py` — AI system prompt updated: IGW error codes (IB_EXT_APP/HTTP_404 from IGW source) indicate gateway-level failures; AI guided to identify operation, node, and HTTP status from log entries
- AI diagnostic tools: `environment_health`, `ib_diagnostics`, `process_scheduler_health` added to `connectors/ai_tools.py` with proactive diagnostics system prompt

### Design Decisions

- **F5**: Supported via `f5_access` type using Apache-combined parser (HSL iRules log in NCSA format)
- **Future F5 native**: When F5 Analytics/AVR logs become available, add `f5_avr` parser with VS name, pool, irule fields
- **Retention**: 30 days of web entries, 90 days of app entries, 90 days of errors (configurable)
- **Dedup**: `log_errors` has `UNIQUE(source_name, ts, coalesce(raw,''), coalesce(error_code,''))` — allows multiple error codes per entry; `app_entries` has `UNIQUE(source_name, ts, coalesce(raw,''))` — safe to re-ingest overlapping byte ranges
- **OPRID extraction**: web logs — second NCSA field (auth user); app logs — context field + message body fallback
- **IGW raw field format**: pipe-delimited `ts|description|exception|ib_operation|requesting_node` (≤500 chars) — parsed server-side for analytics grouping
- **msgLog.html** (`igw_msg_log` type): Not implemented — message logging disabled in this HCM environment; no file present to parse against

---

# Phase 9 — Platform Extensibility

## Plugin SDK

### ✅ Completed (2026-07-03) — v1

Full design in the approved plan (`connectors/plugins.py` docstring / this
section). Every extension surface investigated turned out to be the same
shape: a hardcoded literal list/dict/if-chain only core code could append
to. Solved by adding one appendable registry per surface, plus a loader.

- **`connectors/plugins.py`** — four registries + `register_*`/`get_*`
  functions: object providers, graph providers, runtime providers, nav
  entries (+ router registration). Pure Python, no FastAPI/DB imports at
  module scope.
- **`connectors/pluginloader.py`** — `discover_and_load(app, plugins_dir=
  "plugins")`: imports every `plugins/<name>.py` or `plugins/<name>/
  __init__.py`, calls `register(sdk)`. Isolated per-plugin try/except — a
  broken plugin logs a warning and is skipped, never crashes startup or
  affects other plugins (verified: deliberately broke the example plugin's
  syntax, confirmed the server still started and every other admin page
  still returned 200, then restored it).
- **Wiring** (each is a small, additive change, zero risk to existing
  built-in types/pages):
  - `routers/peoplesoft.py` `object_payload()` checks
    `plugins.get_object_provider(type)` before the existing 50+-branch
    if/elif chain
  - `connectors/graphdb.py` `build()` appends `plugins.get_graph_providers()`
    to its literal provider tuple (each loader wrapped so it receives
    `(graph, env, limit)`, matching the zero-arg `loader()` contract the
    existing closures rely on)
  - `routers/runtime.py` — generic `GET /api/runtime/plugins` (list) and
    `GET /api/runtime/plugins/{name}` (fetch); `routers/admin/runtime.py`
    "Plugin Providers" card renders any registered provider automatically
    (generic JSON dump — no per-plugin UI code needed)
  - `routers/admin/_core.py` `_nav_html()` merges `_NAV_GROUPS` with
    `plugins.get_nav_entries()` (new group label creates a new dropdown,
    e.g. "Plugins")
  - `main.py` `lifespan()` calls `pluginloader.discover_and_load(app)` once
    at startup, before `scheduler.start()`
- **`plugins/example_hello.py`** — worked example exercising all four
  registries with trivial in-memory data (no DB/SSH), meant as a copy-paste
  starting point. Verified end-to-end through the *running server*
  (not just unit-level): `/admin/plugin/hello` renders, appears in nav under
  a new "Plugins" group; `GET /api/peoplesoft/object/hello_widget/ALPHA`
  returns a real payload; `GET /api/runtime/plugins/hello` returns live
  status; `POST /api/graph/build?env=HCM&limit=50` produces real
  `hello_widget:*` nodes/edges in the persisted KG JSON.
- **`PLUGINS.md`** (repo root) — the actual SDK documentation: each
  extension point with a code snippet, loading/isolation semantics, and an
  explicit "not yet covered" section (see below).

**v2 candidates, not built now** (documented in `PLUGINS.md`): custom health
checks (no registry yet — a plugin's runtime provider is a reasonable stand-in
today), and a dedicated "config-driven source" registry for plugins that want
to replicate the SQR/COBOL ingest pattern (object-provider + graph-provider
registries are sufficient building blocks for this already, just not formalized
into their own registration API).

**Verified**: `make check` 91/91; `python3 scripts/smoke_admin_shell.py`
69/69 (including the new `/admin/plugin/hello` entry).

---

# Phase 10 — Source Artifact Intelligence

## Vision

Extend PeopleSoft Hypergraph Intelligence beyond Oracle metadata by incorporating filesystem-based source artifacts into the Digital Twin.

SQR, COBOL, COPYBOOK, and SQC files become first-class UOM objects that fully participate in search, graph traversal, dependency analysis, environment comparison, runtime correlation, and AI engineering workflows.

---

## Source Discovery

### Done (2026-07-02)

- Configurable `sqr_sources` in config.json (alias, dir, label, key)
- SSH-based filesystem discovery via existing `sshclient.py` pool
- FSCM SQR library indexed: 507 SQR + 698 SQC = 1,205 files
- 2,019 distinct PS_ tables, 5,183 table references, 9,142 #include references
- Background re-index via `POST /api/sqr/ingest` with polling at `/api/sqr/ingest/status`
- `connectors/sqrparser.py` — pure parser (description, release, revision, tables, includes, procedures)
- `connectors/sqrdb.py` — SQLite at data/sqr.db (sqr_programs, sqr_tables, sqr_includes, sqr_procedures)
- `connectors/sqringest.py` — SSH-based indexer

### Planned

- Incremental scanning (checksum-based change detection)
- Custom override layer detection (custom dir vs delivered dir)
- HCM-specific SQR directories
- Configurable custom source roots

---

## Source Explorer

### Done (2026-07-02)

- `/admin/sqr` — list view with search, type filter (SQR/SQC), pagination, stat cards, Re-index button
- `/admin/sqr/{filename}` — program detail: metadata, PS_ tables with operation badges, #include tree, procedures list
- `/admin/sqr/table/{PS_TABLE}` — which programs reference a given table and how (SELECT/UPDATE/INSERT/DELETE)
- `GET /api/sqr/programs`, `GET /api/sqr/program/{filename}`, `GET /api/sqr/table/{name}`, `GET /api/sqr/sqc/{name}/users`
- Nav entry under Platform → SQR Explorer

### Done (2026-07-02)

- Source preview tab in program detail (live SSH fetch, SQR syntax highlighting: comments, #include, begin/end sections, SQL keywords, SQR keywords)
- `GET /api/sqr/program/{filename}/source` — live SSH source fetch (up to 512KB)

### Done (2026-07-02 pass 2)

- `/admin/sqr/analytics` — Top 30 PS_ tables by reference count, top 20 most complex SQR programs, top 20 most-included SQC files, release breakdown (1,200 FSCM92 + 5 others)
- `GET /api/sqr/analytics` — analytics data endpoint
- `sqr_program` added to OBJECT_REGISTRY — icon, display_title, graph_node_type; Object Explorer `/admin/object/sqr_program/{name}` → 302 redirect to `/admin/sqr/{name}.sqr`
- Runtime process instance panel — SQR Report/Process type now shows "SQR Source" link next to program name, linking directly to `/admin/sqr/{prcsname}.sqr`
- Analytics button added to SQR Explorer toolbar

### Planned

(none remaining — see COBOL/Copybook Explorer below)

### ✅ Done (2026-07-03)

- **SQR Include Dependency Graph** — `/admin/sqrdeps?q=` page with collapsible forward
  include tree, reverse "Included By" panel (direct + indirect), and force-directed
  canvas graph
- `GET /api/sqr/deps/{filename}` — recursive CTE forward + reverse traversal with DISTINCT
- `connectors/sqrdb.get_include_deps()` — recursive CTE traversal
- **SQR Environment Side-by-Side Comparison** — `/admin/sqrcompare` with 4 tabs (Changed /
  Only A / Only B / Identical); `GET /api/sqr/envcompare`; compares table counts, include
  counts, and MD5 content hashes
- **Incremental SQR Scanning** — MD5 `content_hash` column in `sqr_programs`; ingestor
  skips unchanged files (hash match); `skipped` count in ingest summary

---

## Override Intelligence

### Planned

Automatically identify

- custom overrides
- delivered-only objects
- custom-only objects
- duplicate overrides
- orphaned customizations
- missing delivered files

---

## Source Comparison

### Planned

Support comparison between

- Delivered vs Custom
- HCM vs FSCM
- DEV vs TEST
- TEST vs PROD
- Snapshot vs Current

Comparison modes

- Unified diff
- Side-by-side diff
- Syntax-aware diff
- Ignore comments
- Ignore whitespace

---

## Dependency Analysis

### Done (2026-07-02)

- SQC #include dependency extraction (sqrparser.py → sqrdb.sqr_includes)
- PS_ table READS/WRITES edges in Knowledge Graph (sqr_program → record)
- SQC INCLUDES edges in Knowledge Graph (sqr_program → sqr_program)
- prcs_defn WRAPS sqr_program edge for "SQR Report"/"SQR Process" types
- INCLUDES added to EDGE_TYPES and DEPENDENCY_EDGES — traversable via impact API
- Impact analysis: `GET /api/graph/dependencies/sqr_program:AMAE1100.SQR` returns 20 nodes (4 records + 16 SQC includes)
- setenv.sqc has 495 SQR programs as reverse-dependencies

### Planned

- COBOL COPY library dependencies
- Application Engine launch references
- External executable references

---

## Search

### ✅ Done (2026-07-02) — SQR Source Full-Text Search

- `source_text TEXT` column added to `sqr_programs` via schema migration in `init_db()`; also fixed stale FK references in sub-tables that pointed to dropped `sqr_programs_v1`
- `sqringest.py` now passes `content` (full source) to `upsert_program(source_text=content)` — populated on each re-index
- `sqrdb.search_source(q, file_type, source_key, limit)` — LIKE search, deduplicates by filename, returns per-file hit count + up to 5 snippet contexts with line numbers
- `sqrdb.source_index_status()` — returns indexed/total/pct for UI progress display
- `GET /api/sqr/search?q=&type=&source_key=&limit=` and `GET /api/sqr/search/status` in `routers/sqr.py`
- `/admin/sqrsearch` in `routers/admin/sqr_view.py`: sidebar results sorted by hit count, inline source viewer with SQR syntax highlighting and term highlighting; "Open in SQR Explorer" cross-link per result; re-index notice when not yet indexed
- "SQR Search" added to Platform nav group

### Planned

Global search

- filenames
- program names
- SQL
- comments
- literals
- identifiers
- include references
- COPY references

---

## Environment Intelligence

### Planned

Detect

- customization drift
- delivered drift
- override drift
- deleted customizations
- added customizations
- checksum differences

---

## Analytics

### Planned

Dashboards for

- customization inventory
- override inventory
- source metrics
- complexity metrics
- dependency metrics
- unused programs
- duplicate logic
- customization hotspots

---

## AI Engineering

### Planned

Support

- explain this SQR
- summarize this COBOL
- compare customizations
- identify customization risk
- modernization recommendations
- impact prediction
- code documentation
- dead code detection
- dependency explanation

---

## Runtime Correlation

### Planned

Correlate Process Scheduler executions with source artifacts to provide

- executed source
- execution history
- runtime metrics
- SQL generated
- log correlation
- performance analysis
- end-to-end transaction tracing

---

## Status

Planned.

---

# Phase — Processing Sequence Intelligence

## Goal

Teach PHI how PeopleSoft processing flows execute over time.

PHI should understand event order, execution context, and sequence-sensitive behavior across PeopleCode, component processing, save processing, integration activity, and batch handoffs.

## Completed

- Unified Object Model foundation exists
- Object Explorer exists
- Graph Explorer exists
- Knowledge Graph foundation exists
- PeopleCode metadata extraction exists or is planned as part of metadata intelligence
- Runtime Monitor and Oracle ASH integration provide a foundation for later runtime correlation

## ✅ Completed (2026-07-02) — Component Event Flow

- `/admin/compflow` — Component Event Flow Explorer: enter any component name (autocomplete search), view all PeopleCode events grouped by phase (Search/Build/Interaction/Save/Other); click any event row to expand inline PeopleCode source with full syntax highlighting; modification detection shows user-modified events; record cross-links to Record Explorer; env-aware
- `GET /api/peoplesoft/components/{comp}/events?env=` — returns all PSPCMPROG rows for objectid1∈{9,10} for the component; decodes phase, scope (Component/Record/Field), record, field, event name, lastupdoprid/dttm; also returns component OBJECTOWNERID from PSPNLGRPDEFN
- `GET /api/peoplesoft/components/{comp}/event-source?env=&event=&record=&field=` — fetches PeopleCode source text from PSPCMTXT for the specific event; matches on objectvalue columns to narrow to the exact program
- Both functions in `connectors/peoplecode.py`: `component_events()` and `component_event_source()`

## ✅ Completed (2026-07-02) — Incident RCA

- `/admin/rca` — Incident RCA dashboard: select time window (15m/1h/4h/24h quick buttons or custom datetime-local inputs), pick Oracle DB for ASH data, click Investigate; correlated view across Process Failures, Log Errors, Oracle ASH, IB Errors; summary stat cards, timeline list, cross-links to Runtime Monitor and IB Explorer
- `GET /api/runtime/rca?env=&start=&end=&db=` — `rca_snapshot()` in execution.py correlates PSPRCSRQST failures, logdb errors, V$ACTIVE_SESSION_HISTORY, and PSAPMSGPUBHDR IB errors into a single time-windowed report with unified timeline

## Remaining

### Event-Aware Metadata Indexing

Index PeopleCode by execution context:

- Component
- Page
- Record
- Field
- Component record
- Component record field
- Event name
- Sequence phase
- Save phase
- Runtime interaction phase

### Sequence-Aware Graph Relationships

Extend the Knowledge Graph with ordered processing relationships:

- `FIRES_BEFORE`
- `FIRES_AFTER`
- `PART_OF_SEQUENCE`
- `CALLS_DURING_EVENT`
- `VALIDATES_BEFORE_SAVE`
- `MUTATES_BUFFER`
- `MUTATES_DATABASE`
- `BLOCKS_PROCESSING`
- `TRIGGERS_RUNTIME_ACTION`

### Processing Path Explorer

Create a UI that shows ordered execution flow for:

- Component
- Page
- Field
- Record
- Component Interface
- Transaction path

The explorer should show which PeopleCode, Application Packages, SQL, Message Catalog entries, integrations, and batch handoffs participate at each point in the sequence.

### Delivered vs Custom Sequence Comparison

Add comparison tools that show how custom logic changes delivered processing behavior.

Capabilities:

- Detect custom PeopleCode additions
- Detect delivered PeopleCode changes
- Compare delivered vs custom source
- Show custom logic in sequence position
- Highlight risky event placements
- Flag upgrade impact where delivered sequence behavior changed

### Runtime Trace Correlation

Correlate static processing paths with runtime evidence.

Target inputs:

- PeopleCode trace
- SQL trace
- PIA access/session activity
- Oracle ASH
- Integration Broker monitor data
- Process Scheduler logs
- Application Engine/SQR/COBOL execution logs

### AI-Assisted Sequence Explanation

Add AI-assisted explanations for selected processing paths.

Example questions PHI should answer:

- What happens when this component opens?
- What happens when this field changes?
- What validates before save?
- What can prevent this transaction from saving?
- What runs after save?
- Where is this custom logic inserted into delivered processing?
- What downstream integrations or batch processes can be triggered?

---

# Phase X — Digital Twin Persistence

Persist everything.

### ✅ Completed

- Knowledge Graph snapshots (creation, listing, comparison, scheduled daily builds)
- Graph drift detection against snapshot baseline

### Remaining

Support:

- Historical runtime persistence
- Deployment history
- Configuration history
- Security change history
- Runtime replay
- Full change history across all object types

The platform evolves from a live explorer into a persistent Digital Twin of the PeopleSoft enterprise.

---

## Root Cause Analysis

Correlate:

- Runtime
- Graph
- Oracle ASH
- Alerts
- Deployments

Answer:

Why did this happen?

---

## Change Risk Analysis

Given a project:

Predict:

- affected objects
- affected users
- deployment risk
- runtime impact

---

## Architecture Assistant

Generate:

- dependency reports
- sequence diagrams
- technical documentation
- impact summaries
- architecture documentation

---

# Long-Term Goals

PeopleSoft Hypergraph Intelligence should become the definitive engineering, observability, and operational intelligence platform for PeopleSoft environments.

---

# Current Focus

## ✅ Phase 5 — Complete (as of 2026-07-01)

Phase 5 Knowledge Graph coverage is complete. 23 new providers were added across multiple sessions. All viable tables have been implemented; all unimplementable tables are documented in the Deprioritized Providers table above with reasons.

**IB Schema Definitions** (PSIBSCMADATA / PSIBSCMADFN) was the last candidate. Investigated 2026-07-01: no SELECT grant exists in HCM; PSIBSCMADATA stores raw XML as CLOB chunks — not browsable even with grants; PSIBSCMADFN header is redundant with existing PSMSGDEFN coverage. Deprioritized.

**Provider methodology for future sessions:**
1. Query `all_tab_columns` to find the real table and column names — never assume PeopleTools naming
2. Pull live sample rows to confirm usable keys and human-readable content
3. Write psdb.py → ptmetadata.py → graphdb.py → uom.py → routers/peoplesoft.py → routers/admin/<group>.py in order
4. Compile-check and smoke-test at each layer before proceeding
5. Document deprioritization reasons when tables are unimplementable

## ✅ Phase 7 — AI Engineering Assistant (Complete as of 2026-07-01)

3-provider AI assistant (Claude / OpenAI / Ollama) with 12+ tool definitions backed by live connectors.
Streaming chat at `/admin/assistant`; agentic tool loop up to 8 rounds; collapsible tool-call blocks.
Tools: `search_objects`, `peoplecode_search`, `graph_dependencies`, `graph_impact`, `who_has_access`,
`ae_steps`, `sql_lookup`, `envcompare_summary`, `project_impact`, `active_sessions`, `record_usage`,
`log_search`, `log_errors`, `session_log_chain`, `environment_health`, `ib_diagnostics`, `process_scheduler_health`.

## ✅ Phase 8 — Log Intelligence (Complete as of 2026-07-02)

Full log ingestion pipeline: PIA access/error, APPSRV, Tuxedo, nginx/Apache, F5, IGW errorLog.html, PRCS AE AESRV logs.
SSH/SFTP fetch with byte-offset tracking; 60s ingest cycle; SQLite `data/logs.db`.
Admin pages: `/admin/logs`, `/admin/log_errors`, `/admin/log_viewer`, `/admin/log_session`, `/admin/igw`, `/admin/prcs-ae`.
AI tools for log diagnosis; session chain correlation web→app; error surface with Ask AI deep-links.

**Remaining:** Process Scheduler log ingestion for Windows-hosted schedulers (SMB/WinRM transport) — blocked until a Windows scheduler server is available.

## ✅ Component Processing Sequence Timeline (2026-07-02)

- `/admin/compseq` — PC Timeline: enter component name (same autocomplete as compflow), renders canonical PeopleSoft processing lifecycle in 4 phase columns (Search → Build → Interaction → Save)
- Each of the 20 canonical event slots rendered as a card: cyan if delivered PC exists, amber if custom PC, dark-grey if empty; click to expand inline source with PeopleCode syntax highlighting
- Summary stats bar: Total Slots (20), With PeopleCode, Custom Events, Delivered Events, Empty Slots
- Per-program source fetch via /api/peoplesoft/components/{comp}/event-source (up to 6 per event); custom programs show lastupdoprid in amber
- Event metadata includes canonical scope (Component/Record/Field), purpose note, program count, and record names involved
- "PC Timeline" added to Platform nav and home page Quick Navigation
- Addresses Processing Sequence Intelligence roadmap: Event-Aware Metadata Indexing (the canonical sequence view exposes event execution context), Delivered vs Custom comparison (custom badge + source expansion)

## ✅ What Changed Expansion + Security Audit (2026-07-02)

- **What Changed** expanded from 9 → 20 object types: Records, Components, Pages, AE Programs, Fields, PeopleCode, SQL Defs, Perm Lists, Roles (original 9) + Menus (PSMENUDEFN), Queries (PSQRYDEFN), Projects (PSPROJECTDEFN.descrlong), Processes (PS_PRCSDEFN), App Packages (PSPACKAGEDEFN), IB Messages (PSMSGDEFN), IB Routings (PSIBRTNGDEFN, filtered ~GENERATED~), Trees (PSTREEDEFN.tree_name), Translate Values (PSXLATITEM GROUP BY fieldname), Component Interfaces (PSBCDEFN)
- **OPRID filter** added to What Changed toolbar — client-side filter on the `op` column shows N/Total counts per type pill when active; empty filter string shows all results; filter applies immediately on input without re-querying
- **Security Audit Dashboard** at `/admin/secaudit`: stat cards (total operators/roles/PLs/active-30d), top roles by member count, top operators by role count, recent sign-ons (30d), orphaned roles panel, operator type breakdown; all via POST /api/sqlws/execute
- **Security nav group** consolidates secaudit/security/operator/role/permissionlist; permissionlist moved from Objects
- **SQR cross-reference in Record Explorer** — record UOM calls sqrdb.get_programs_for_table(table_name); "SQR Programs" section with _links.admin → /admin/sqr/{filename}; re-index triggered 2026-07-03 — 344 rows, 123 distinct tables

## ✅ Phase 10 — SQR Explorer (Substantially Complete as of 2026-07-02)

SQR/SQC source artifact intelligence is live for FSCM (507 SQR + 698 SQC = 1,205 files indexed).
Admin pages: `/admin/sqr`, `/admin/sqr/{filename}`, `/admin/sqr/table/{table}`, `/admin/sqr/analytics`, `/admin/sqrsearch`.
KG edges: `sqr_program → record` READS/WRITES, `sqr_program → sqr_program` INCLUDES, `prcs_defn → sqr_program` WRAPS.
Runtime process panel: SQR Report/Process type links directly to source.

### Done (2026-07-02, session 3)

- **SQR Override Intelligence infrastructure**: `sqr_sources` keys split per source_type (`fscm_sqr_delivered` / `fscm_sqr_custom` / `hcm_sqr_delivered` / `hcm_sqr_custom`); `source_type: delivered|custom` field added to config; sqrdb schema migrated to `UNIQUE(filename, source_key)` + `source_type` column; `GET /api/sqr/overrides?env=` returns filenames present in both delivered and custom; re-index required to populate source_type in DB
- **SQR KG Records tab**: all detail pages now have a "KG Records" lazy-load tab; queries `/api/graph/neighbors/sqr_program:FILE?env=HCM`; renders READS (blue) / WRITES (amber) groups with links to Record Explorer
- **SQR Full-Text Search** at `/admin/sqrsearch`: SQLite-backed source text index with automatic schema migration; syntax-highlighted snippets; deduplication across delivered/custom trees; cross-link to SQR Explorer
- **EnvCompare Process Definitions tab**: `GET /api/envcompare/process_definitions` compares PS_PRCSDEFN (PRCSTYPE, PRCSNAME, DESCR, LASTUPDDTTM) using composite TYPE~NAME key; "Processes" tab in EnvCompare UI between Trees and IB Routings
- **EnvCompare summary**: Process Definitions count row added (PS_PRCSDEFN)
- **Env-based filtering** in SQR Explorer: env selector dropdown populated from `/api/sqr/sources`; stats and search results scoped to selected env
- **SQC Included By tab**: SQC detail pages show a third "Included By" tab listing programs that #include this SQC (lazy-loaded from `/api/sqr/sqc/{name}/users`)

### ✅ Done (2026-07-03) — COBOL/Copybook Explorer

- **`cobol_sources`** config block added: 4 entries (HCM/FSCM × delivered/custom),
  each with `cbl_src_dir` and `cbl_compiled_dir`
- **Discovery**: PeopleSoft COBOL "copybooks" are `.cbl` files distinguished by the
  *absence* of `PROGRAM-ID` (they're pulled in via `COPY name.` — e.g. `COPY PTCLOGMS.`
  targets `PTCLOGMS.cbl`), not a separate `.cpy` extension. No true `.cpy` files exist
  in this environment. `connectors/cobolparser.py` classifies `file_type` as
  `program`/`copybook` on that basis, and description extraction skips past the fixed
  Oracle license preamble (bounded by an "All Rights Reserved." marker) plus decorative
  box-border comment lines before taking the first real comment as description.
  Also extracts static `CALL 'X'` targets and `EXEC SQL ... END-EXEC` PS_ table refs.
- **`connectors/cobol_db.py`** (`data/cobol.db`): `cobol_programs`/`cobol_tables`/
  `cobol_copies`/`cobol_calls`; recursive-CTE `get_copy_deps()` (forward + reverse
  COPY closure, joining on filename-minus-extension since COPY names target files,
  not parsed member names); MD5 `content_hash` for incremental scanning; full-text
  `search_source()`
- **`connectors/cobolingest.py`**: SSH scan of `cbl_src_dir` (`*.cbl`); best-effort
  listing of `cbl_compiled_dir` to flag whether a compiled binary exists; per-file
  `PermissionError` is counted as `denied` and never raised — most delivered `.cbl`
  files are mode 700 (owner `ps_hcm`, not readable by the `oracle` SSH service
  account) and this is expected, not an error
  (confirmed: 862/977 denied, 115/977 indexed per environment)
- **`routers/cobol.py`**: `/api/cobol/{stats,sources,programs,program/{f},
  program/{f}/source,table/{t},deps/{f},search,search/status,ingest,ingest/status}`
- **`/admin/cobol`** (Platform nav) list/search page + **`/admin/cobol/{filename}`**
  detail page (Overview / COPY Dependency Graph / Source tabs)
- **`hcm_cobol_src_custom`/`fscm_cobol_src_custom`** sources point at
  `ps_cust_home/src/cbl`, which doesn't exist on this demo box (`ps_cust_home` only
  has an `sqr` folder) — ingestor reports `cbl_src_dir not found` as a warning, not
  a crash; will populate automatically once a real customer environment has custom
  COBOL

**Verified**: fresh ingest → 230 files indexed (88 programs, 142 copybooks) across
HCM+FSCM delivered; `PTPCBLAE.cbl` → 8 direct COPY deps resolved correctly;
`PTCALOGM.cbl` correctly classified as copybook (`ZM000-LOG-MESSAGE` SECTION, no
PROGRAM-ID) with description "CALL THE MESSAGE LOGGER WITH A TRANSACTION EDIT
MESSAGE." (license-preamble-skipping fix verified); `make check` 91/91;
`python3 scripts/smoke_admin_shell.py` 68/68.

**Remaining:** environment side-by-side SQR comparison (done — see `/admin/sqrcompare`
above); no true copybook (`.cpy`) support was needed since none exist in this
PeopleSoft install, but the schema's `file_type` column already generalizes to that
case if a future customer environment has them.

### ✅ Done (2026-07-03, session 2) — COBOL Knowledge Graph wiring

- New `cobol_program` KG node type: `connectors/graphdb.py` `cobol_programs()` builder
  (registered in the env build list) adds `cobol_program → record` READS/WRITES edges
  (from EXEC SQL table refs), `cobol_program → cobol_program` COPIES edges, and
  `cobol_program → cobol_program` CALLS edges (static `CALL 'X'` targets — dynamic
  `CALL WS-VAR` calls can't be resolved and are skipped, same limitation as SQR's
  `DO`/`GOSUB` handling)
- `connectors/ptmetadata.py` `OBJECT_REGISTRY["cobol_program"]` entry (icon,
  `object_page: /admin/cobol`, relationships) — mirrors the existing `sqr_program` entry
- `routers/admin/graph.py` `/admin/object/cobol_program/{name}` redirects to
  `/admin/cobol/{name}.cbl`, matching the `sqr_program` → `/admin/sqr/{name}` pattern

**Verified**: fresh `graphdb.build(env='HCM', limit=2000)` produced 163 `cobol_program`
nodes and 567 edges (164 CALLS, 403 COPIES; 0 READS/WRITES since none of the 115
readable delivered `.cbl` files use `EXEC SQL`); `/api/graph/neighbors/cobol_program:
PTCALOGM.CBL` resolves real CALLS edges to `PTPLOGMS.CBL`/`PTPTEDIT.CBL`; redirect
`/admin/object/cobol_program/PTCALOGM.CBL` → `/admin/cobol/ptcalogm.cbl` (302);
`make check` 91/91; smoke test 68/68.

## ✅ Phase 6 — Environment Intelligence (Substantially Complete as of 2026-07-01)

Continuous drift detection, environment history, and impact forecasting are complete.

**Remaining:** Promotion history tracking (DEV → TEST → UAT → PROD) — needs real promotion-chain DB connections before implementation.

**What was delivered:**
- 17-type envcompare coverage (records, fields, components, pages, permissions, roles, AE, PeopleCode, SQL defs, portals, queries, menus, trees, IB routings, IB messages, comp. interfaces, **process definitions**)
- AE step-level body comparison with unified SQL diff
- Scheduled drift snapshots (SQLite) with threshold + growth alerts, history time series
- KG-independent deployment risk scoring (weighted by object type) via `/api/impact/risk`
- Project impact reports via KG reverse traversal via `/api/impact/project`
- Admin pages: `/admin/drift`, `/admin/impact`

## ✅ Dedicated Object Explorers (2026-07-02)

Rich dedicated explorer pages for major PeopleSoft object types, providing deep contextual analysis beyond the generic Object Explorer.

- **AE Explorer** at `/admin/ae`: search catalog, tabbed detail (Overview, Steps, Runtime History, Cross-References, KG Graph); live runtime history from Process Scheduler; step/section/SQL deep dive; Invoked By (Process Definitions) cross-reference
- **Component Explorer** at `/admin/component`: tabbed analysis — Overview, Pages, Security, PeopleCode, Portal, Records; Who Has Access (complete PL → Role → Operator chain); grouped PeopleCode by event; component-to-page cross-linking
- **Page Explorer** at `/admin/page`: Overview, Records, Components, PeopleCode, Security; hierarchical page/subpage navigation
- **Permission List Explorer** at `/admin/permissionlist`: Overview, Components, Roles, Menus; access coverage analysis
- **Unified Object Explorer** at `/admin/object/{type}/{name}`: cross-type search; auto-redirects to dedicated explorer for supported types; generic UOM provider view for all other types
- Cross-linking updated throughout platform: AE/Component/Page/Permission List deep-links from process definitions, runtime monitor, record explorer, security explorer

## ✅ Component Event Flow Explorer (2026-07-02)

- `/admin/compflow`: enter component, renders canonical PeopleSoft processing lifecycle (20 event slots across 4 phases: Search → Build → Interaction → Save); each slot shows delivered/custom PeopleCode with inline source viewer and syntax highlighting; custom events highlighted in amber with LASTUPDOPRID
- `/api/peoplesoft/components/{comp}/events`: enumerate component, record, and field-level PeopleCode events with execution phase, scope, customization status; decode 20 canonical events with purpose/phase metadata
- `/api/peoplesoft/components/{comp}/event-source`: fetch PeopleCode source for specific event context from PSPCMTXT
- Inline source viewer within event flow; SQR syntax highlighting for PeopleCode
- Addressed Processing Sequence Intelligence roadmap: canonical event sequence model, event-aware indexing, delivered vs custom comparison

## ✅ Incident RCA (2026-07-02)

- `/admin/rca`: single-pane root-cause analysis; correlates process failure with Oracle ASH, app/web logs, IB errors, and Knowledge Graph; tabbed output (Process, Logs, ASH, IB, KG); pre-populated from runtime process panel
- Integrated with Component Event Flow for PeopleCode-level correlation

## ✅ SQR Full-Text Search (2026-07-02)

- `/admin/sqrsearch`: SQLite-backed source text index; search across all indexed SQR/SQC source code; syntax-highlighted snippets with matching term highlight; sorted by hit count; deduplication across delivered/custom; "Open in SQR Explorer" cross-link per result
- Schema migration for source text column applied automatically on first use

## ✅ Access Path Explorer (2026-07-02)

- `/admin/access` (Security nav group): dual-mode security analysis — component-centric (who can access this component?) and operator-centric (what can this operator access?)
- Component mode: complete Permission List → Role → Operator authorization paths; access level breakdown; count summary
- Operator mode: component permissions, access levels, and granting security objects
- Environment-aware; URL deep-linking; client-side filtering for rapid security investigation

## ✅ Change Risk Analyzer (2026-07-02)

- `/admin/riskanalysis` (Tools nav group): evaluate project impact, blast radius, and affected users before deployment; computes risk scores based on affected records, components, AE programs, and user population
- Direct navigation from risk results to Component Explorer, Record Explorer, and Access Path Explorer
- IB Message cross-references: UOM IB Message objects now show correlated Service Operations, Routings, and Subscriptions

## ✅ Security Audit Dashboard (2026-07-02)

- `/admin/secaudit`: stat cards (total operators/roles/PLs/active-30d), top roles by member count, top operators by role count, recent sign-ons (30d), orphaned roles, operator type breakdown
- Security nav group consolidates: Security Audit, Security Explorer, Operators, Roles, Permission Lists

## ✅ What Changed Expansion (2026-07-02)

Expanded from 9 → 20 supported object types: added Menus, Queries, Projects, Processes, App Packages, IB Messages, IB Routings, Trees, Translate Values, Component Interfaces.
OPRID filter added: client-side filter on updater shows N/Total counts per type pill.

## ✅ SQR Cross-References in Record Explorer (2026-07-02)

Record objects now have a "SQR Programs" section (sourced from `sqrdb.get_programs_for_table()`); shows which SQR programs read or write this record with operation badges and links to SQR Explorer.

## ✅ Field PeopleCode Impact Tab (2026-07-02)

`/admin/field/{name}` now has a "PeopleCode" tab alongside Records/Keyed/ByType: shows all PeopleCode programs that reference this field, grouped by object type (Record/Component/Page), with event name and direct links to source.
