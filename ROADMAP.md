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
- Version-aware metadata adapters
- Shared frontend shell with global navigation and environment selector
- Admin shell smoke test harness (22 pages)
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

Candidates for next session:
- **WorkCenters** — no standalone definition header table found; EOWC tables are runtime config keyed by portal object name, not metadata definitions; deprioritized
- **Dashboards** — no definition tables found (PS_EOEN_DASHBRD/PS_PT_ACMDASHTBL are 0-row log/cache tables); deprioritized
- **BI Publisher / Branding / Page Composer** — no backing definition tables found in live HCM SYSADM schema; deprioritized
- **Activity Guide Collections** — `PS_AGC_TILE_TBL` (2 rows): too few rows to be useful
- **Translate Values** — `PSXLATITEM` (49177 rows): valid candidate if field-level translate lookup is needed
