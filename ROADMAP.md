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
- Admin shell smoke test harness (28+ pages; 23 new providers added in Phase 5)
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

### Remaining

- Browser session tracking
- WebLogic session tracking
- App Server process tracking beyond domain enumeration

---

## Runtime Timeline

Persist runtime snapshots.

### ✅ Completed

- Knowledge Graph snapshots (creation, listing, loading, deletion, scheduled daily builds, retention pruning)
- Graph-based drift detection comparing live graph to most-recent snapshot

### Remaining

- Runtime history persistence (process history, queue depth history, alert history, Oracle ASH history)
- Trend graphs over time
- Runtime snapshot creation (separate from graph snapshots)

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

### Remaining

- Incident recording with full runtime state capture
- Replay support for troubleshooting

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
- Broader READS/WRITES coverage for non-literal PeopleCode dynamic SQL

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

### Remaining

- Universal "what references me / what do I reference" coverage across all object types
- Consistent cross-reference sections across remaining UOM providers (message, tree, project, portal)

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

Automatically detect changes in:

- PeopleCode (changed programs between environments) — ✅ already done (`/api/envcompare/peoplecode` + deep source diff)
- SQL definitions — ✅ already done (`/api/envcompare/sql_definitions`)
- Security (changed permission lists, roles) — ✅ already done (`/api/envcompare/permissions`, `/api/envcompare/roles`)
- Menus — ✅ added 2026-07-01
- Trees — ✅ added 2026-07-01
- Integration Broker metadata — ✅ added 2026-07-01 (routings + messages)

- Component interface comparison (`/api/envcompare/ci`) — diffs PSBCDEFN; shows type, description, backing component — ✅ added 2026-07-01
- AE program body comparison (`/api/envcompare/ae-body`) — step-level diff of PSAESTEPDEFN + SQL text from PSAESTMTDEFN/PSSQLTEXTDEFN; unified diff per changed step — ✅ added 2026-07-01

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

### Remaining

Support:

- Custom object providers
- Custom graph providers
- Custom runtime providers
- Custom dashboards
- Custom health checks
- Organization-specific plugins
- Third-party integrations

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

- COBOL Explorer
- COPYBOOK Explorer
- Dependency graph (SQC include tree, visual)
- Environment presence (HCM vs FSCM side-by-side)

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

## Remaining

### Canonical PeopleCode Event Model

Add a canonical event sequence model for PeopleSoft component processing.

Initial event coverage:

- SearchInit
- SearchSave
- RowSelect
- PreBuild
- FieldDefault
- FieldFormula
- RowInit
- PostBuild
- Activate
- FieldEdit
- FieldChange
- PrePopup
- ItemSelected
- RowInsert
- RowDelete
- SaveEdit
- SavePreChange
- Workflow
- SavePostChange

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

## Phase 6 — Environment Intelligence (Substantially Complete as of 2026-07-01)

Continuous drift detection, environment history, and impact forecasting are complete.

**Remaining:** Promotion history tracking (DEV → TEST → UAT → PROD) — needs design before implementation.

**What was delivered:**
- 16-type envcompare coverage (records, fields, components, pages, permissions, roles, AE, PeopleCode, SQL defs, portals, queries, menus, trees, IB routings, IB messages, comp. interfaces)
- AE step-level body comparison with unified SQL diff
- Scheduled drift snapshots (SQLite) with threshold + growth alerts, history time series
- KG-independent deployment risk scoring (weighted by object type) via `/api/impact/risk`
- Project impact reports via KG reverse traversal via `/api/impact/project`
- Admin pages: `/admin/drift`, `/admin/impact`
