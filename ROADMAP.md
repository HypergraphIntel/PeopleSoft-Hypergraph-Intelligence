# PeopleSoft Explorer Roadmap

## Vision

PeopleSoft Explorer is evolving into a complete operational intelligence platform for PeopleSoft.

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
- Version-aware metadata adapters
- Shared frontend shell with global navigation and environment selector
- Admin shell smoke test harness (24+ pages; 18 new providers added in Phase 5)
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

### Remaining

- Interactive topology diagram showing Browser → nginx → WebLogic → App Server → Process Scheduler → Oracle → Integration Broker → OpenSearch
- Live status indicators per infrastructure component

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

### Remaining Providers

- BI Publisher report definitions
- WorkCenters
- Dashboards
- Homepage Tiles
- Branding
- Page Composer

---

## Relationship Expansion

Continue enriching graph relationships.

### ✅ Completed

- Shared UOM relationship graph helper introduced; Tree, Component Interface, and Page providers use it
- Page graph API unified with UOM Page provider so Object Explorer and Graph Explorer share the same relationship model
- CALLS, REFERENCES, USES, CONTAINS, WRAPS, SECURES edge types in active use
- Component security graph edges through Permission Lists → Roles → Operators
- Menu → Component CONTAINS edges
- CI → Component WRAPS edges
- Tree → Record USES edges
- Impact analysis (forward and reverse dependency traversal with depth control)

### Remaining

- Continue migrating mature UOM providers from ad hoc graph loops to declarative relationship specs
- Align UOM `_relationships`, UOM `_graph`, and Knowledge Graph ingestion around one relationship vocabulary
- GENERATES and DEPLOYS edge types
- Full relationship coverage examples: WRITES, READS

---

## Cross References

Every object should answer:

### ✅ Completed

- What references me? (implemented for AE SQL steps via `%SQL()`, PeopleCode source references, SQL cross-references)
- What do I reference? (implemented for Components, Pages, Records, AE programs, Portal Registry)
- Who secures me? (implemented for Components, Pages, Permission Lists, Portal Registry with access-path visualization)
- What breaks if I change? (impact analysis via Knowledge Graph traversal)
- Child records, subrecord derivations, and AE state records for Record objects

### Remaining

- Universal "what references me / what do I reference" coverage across all object types
- "Who executes me?" for runtime-linked objects (AEs, Service Operations)
- Consistent cross-reference sections in every UOM provider

---

# Phase 6 — Environment Intelligence

## Continuous Drift Detection

### ✅ Completed

- Knowledge Graph drift: compares current live graph against most-recent snapshot; surfaces new, removed, and changed nodes by type in the Graph Explorer DRIFT tab

### Remaining

Automatically detect changes in:

- PeopleCode (changed programs between environments)
- SQL definitions
- Security (changed permission lists, roles)
- Menus
- Trees
- Integration Broker metadata

---

## Environment History

Maintain historical snapshots.

### ✅ Completed

- Environment comparison across HCM and FSCM for Records, Fields, PeopleCode, SQL Definitions, PS Queries, Portals, and Knowledge Graph
- Portal object deep comparison (definition diff, children diff, permissions diff)
- Operator comparison (roles, permission lists, component access diff between two OPRIDs)

### Remaining

- Promotion history tracking across environments (DEV → TEST → UAT → PROD)
- Point-in-time runtime snapshots
- Temporal history of security and metadata changes

---

## Impact Forecasting

Predict downstream impact before migration.

### ✅ Completed

- Knowledge Graph impact analysis (forward and reverse dependency traversal, upstream/downstream node enumeration by type)
- AE restart eligibility analysis

### Remaining

- Pre-migration impact reports summarizing affected components, security, runtime behavior, and integrations
- Deployment risk scoring

---

# Phase 7 — AI Engineering Assistant

Leverage the knowledge graph for engineering assistance.

## Natural Language Search

### Remaining

Examples:

- Where is employee termination implemented?
- Show every SQL touching PS_JOB.
- Which AEs update JOB?
- Which Components use this record?

---

# Phase 8 — Platform Extensibility

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

PeopleSoft Explorer should become the definitive engineering, observability, and operational intelligence platform for PeopleSoft environments.

---

# Next Slice

## Session 2026-06-30 Completed

All existing providers have been rewritten against the verified live SYSADM schema:
- Approval Framework, XML Publisher, Search Definitions, Search Categories: fully rewritten and live-verified end-to-end
- Navigation Collections, Event Mappings, Related Content, Drop Zones: confirmed as stubs (no backing tables in HCM); gracefully handled via `has_table()` guards; marked `"stub": True` in OBJECT_REGISTRY

## Phase 5 — Next Providers to Implement

New providers should follow the established verification methodology:
1. Query `all_tables`/`all_tab_columns` to find the real table and column names
2. Pull live sample rows to confirm usable keys (never assume PeopleTools naming conventions)
3. Write psdb.py → ptmetadata.py → graphdb.py → uom.py → routers/peoplesoft.py → routers/admin.py in that order
4. Compile-check and smoke-test at each layer before proceeding

Completed in this session:
- **PivotGrid Explorer** — implemented against verified `PSPGCORE` (154 rows); exposes data model columns, data source type (PS Query vs Component), query name, NUI options
- **Connected Query Explorer** — implemented against verified `PSCONQRSDEFN` (97 rows); shows parent-child query composition and field join relationships
- **Process Definition Explorer** — implemented against verified `PS_PRCSDEFN` (2873 rows); composite key PRCSTYPE~PRCSNAME; shows run control pages and process groups
- **File Layout Explorer** — implemented against verified `PSFLDDEFN` (533 rows); shows segments (PSFLDSEGDEFN) and fields (PSFLDFIELDDEFN); supports Fixed Width/Delimited/XML formats

Completed this session (2026-06-30 continued):
- **IB Application Services** — implemented against verified `PSIBAPPLDEFN` (13 apps); exposes REST endpoint operations via PSIBAPPMETHOD/PSIBAPPURI with HTTP methods and URI templates
- **Application Class Definitions** — implemented against verified `PSAPPCLASSDEFN` (12622 rows, 1860 packages); compound key PACKAGEROOT~QUALIFYPATH~APPCLASSID; shows full class path with sibling classes and sub-package tree
- **Content Service Provider Definitions** — implemented against verified `PSPTCSSRVDEFN` (1016 rows); powers Related Actions, WorkCenter actions, Fluid navigation; shows parameters and where-used portal objects
- **PeopleTools Test Framework (PTF) Tests** — implemented against verified `PSPTTSTDEFN` (161 rows); Script/Shell/Library types; shows test cases and up to 150 commands with page/field context

Candidates for next session:
Implemented in this session:
- ADS Definitions, IB Service Groups, URL Definitions, Chatbot Skills, IB Routings, Style Sheets, Data Archive Objects

Deprioritized (no backing tables or too few rows):
- **WorkCenters** — no standalone definition header table; EOWC tables are runtime config keyed by portal object name
- **Dashboards** — no definition tables (PS_EOEN_DASHBRD is 0 rows)
- **BI Publisher / Branding / Page Composer** — no backing definition tables in HCM SYSADM schema
- **Fluid Homepage / Tile Definitions** — all tile/homepage tables (PSPGEDEFN, PSFLPGCOLLECT, PSHPDEFN, PSTILEDEFN, PS_PTTILE_*) absent or 0 rows in HCM
- **Activity Guide Collections** — PS_AGC_TILE_TBL (2 rows): too few
- **File Reference Definitions** — PSFILEREDEFN (19622 rows): mostly system graphics/script refs, no descriptions, marginal value
- **Business Process Definitions** — PSBUSPROCDEFN (133 rows): legacy Workflow Navigator definitions from 2000-2002; deprecated framework
- **IB Local Schema** — PSLSDEFN (319 rows): XML schema stored as compressed binary data; display impractical
- **IB Service Setup** — PSIBSVCSETUP (1 row): single-row global IB gateway configuration; not a browsable catalog

Candidates for future sessions:
- **IB Schema Definitions** — PSIBSCMADATA/PSIBSCMADFN (3680/3618 rows): IB XML schema metadata; investigate if human-readable name + type columns exist for browsing
- **Performance Monitor Metrics** — PSPMMETRICDEFN (206 rows) + PSPMTRANSDEFN (74 rows) + PSPMEVENTDEFN (32 rows): metric/transaction/event catalog for PeopleSoft Performance Monitor

Completed (previous candidates now implemented):
- **Timezone Definitions** — PSTIMEZONEDEFN (61 rows) + PSTIMEZONEIANA (592 rows): timezone catalog with IANA mappings; effective-dated; UTCOFFSET in minutes; full admin UI with search and detail panel
- **Locale Definitions** — PSLOCALEDEFN (191 rows) + PSLOCALEOPTNDFN (923 rows): ISO locale catalog with format options (decimal/thousands separators, date/time format, AM/PM designators)
