# DeathStar Implementation Roadmap

> **Architecture, vision, principles, provider contracts, and long-term
> capabilities** are documented in `ARCHITECTURE.md`.
>
> This roadmap tracks **current implementation status** and **remaining
> work**. Historical implementation notes have been consolidated into
> the appropriate module to eliminate duplication.

------------------------------------------------------------------------

# Module Status

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
-   Breadcrumbs in Object Explorer (type-aware trail with field record parent support)
-   Recently Viewed: relative timestamps, descriptions, per-item remove button

-   SQL syntax highlighting in Object Explorer: `highlightSQL()` tokenizer for `data.ddl` sections and inline SQL step items (SQL keywords in blue, PeopleSoft meta-SQL in purple, strings in orange, comments in green)

### Remaining

-   Remaining object types (Tree, CI)
-   Improved visual hierarchy

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

### Remaining

-   Relationship providers
-   Version-specific adapters
-   Additional object providers

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

### Remaining

-   Tree / CI models
-   Shared relationship provider registration

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

### Remaining

-   Graph compaction
-   Large-environment indexing

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

### Remaining

-   Rich PeopleCode decoding

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

### Remaining

-   Application Package parsing
-   Larger source pagination

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

### Remaining

-   Broader permission-decoding and access-path visualization improvements

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

------------------------------------------------------------------------

## Component Explorer

**Status:** UOM Integrated

### Completed

-   Canonical pages
-   UOM integration
-   Portal
-   Related Content
-   Drop Zones
-   Security
-   Graph preview
-   Component PeopleCode (objectid1=9 event-level, 10 record/field-level)

### Remaining

-   Rich visualization
-   Better portal reconstruction

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

### Remaining

-   Rich hierarchy
-   PeopleCode source

------------------------------------------------------------------------

## Portal Explorer

**Status:** Active Development

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

### Remaining

-   Rich portal reconstruction
-   Portal comparison

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

### Remaining

-   Runtime detail
-   Restart analysis

------------------------------------------------------------------------

## Integration Broker Explorer

**Status:** Active Development

### Completed

-   Services
-   Nodes
-   Queues
-   Routings
-   Dashboard
-   UOM
-   Graph integration
-   PeopleCode linkage

### Current Limitations

-   Runtime grants unavailable
-   Payload inspection pending

------------------------------------------------------------------------

## SQL Definition Explorer

**Status:** Foundation Complete

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

### Remaining

-   PeopleCode cross-reference (binary BLOB search)

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

### Remaining

-   Deep PeopleCode source diff (requires binary BLOB decode)

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

### Remaining

-   App Server monitoring
-   Alerts

------------------------------------------------------------------------

## Identity Management

**Status:** Feature Complete

### Completed

-   Authelia integration
-   Identity sync
-   Provisioning
-   Audit

### Remaining

-   MFA
-   Bulk operations
-   Approval workflow

------------------------------------------------------------------------

## Infrastructure

**Status:** Partial

### Completed

-   System APIs
-   Oracle APIs
-   NGINX APIs
-   Live monitoring
-   Topology

### Remaining

-   Expanded infrastructure management

------------------------------------------------------------------------

# Upcoming Priorities

## Medium Priority

-   Advanced Portal Registry reconstruction
-   Graph indexing
-   Advanced dependency analysis

## Blocked

-   AE SQL actions (database grants)
-   Oracle ASH integration (Diagnostics Pack)
-   Runtime IB inspection (missing grants)

## Long-Term

-   Deployment Center
-   Logging Platform
-   AI Assistant
-   Automation
-   Reporting
