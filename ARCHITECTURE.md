# PeopleSoft Hypergraph Intelligence - PHI
*Project Codename: DeathStar*

# Vision

PeopleSoft Hypergraph Intelligence is an operational intelligence platform for Oracle PeopleSoft.

Rather than functioning as a collection of independent tools, the platform is built around a unified metadata and runtime model that enables engineers, administrators, and architects to understand every aspect of a PeopleSoft environment from a single interface.

The platform combines:

- Metadata exploration
- Dependency analysis
- Runtime observability
- Security analysis
- Environment comparison
- Infrastructure monitoring
- Identity management
- AI-assisted engineering

Every feature ultimately feeds one of three platform pillars:

1. Metadata Intelligence
2. Runtime Intelligence
3. Engineering Intelligence

These pillars share a common foundation:

- Unified Object Model (UOM)
- Version-aware metadata adapters
- Knowledge Graph
- Relationship providers
- Runtime providers

This architecture allows new PeopleSoft object types, runtime providers, and analysis engines to be added with minimal changes to the surrounding platform.

---

## Engineering Principles

Every subsystem should follow these principles.

- Read-only by default
- Discover before assuming
- Version-aware metadata
- Provider-based architecture
- Graceful degradation
- Runtime and metadata are first-class citizens
- Every object participates in the Knowledge Graph
- Every feature is API-first

---

## What is PeopleSoft Hypergraph Intelligence?

**PeopleSoft Hypergraph Intelligence is a PeopleSoft Digital Twin.**

It mirrors every aspect of a live PeopleSoft enterprise in a structured, queryable, navigable
form. It does not replicate PeopleTools or App Designer — it models the *enterprise* that runs
on top of them: the metadata, security posture, runtime behavior, integration topology,
Oracle footprint, source code, dependencies, and transactional history.

The platform serves every persona in a PeopleSoft organization:

| Persona | Primary Use |
|---|---|
| Developer | Object navigation, dependency analysis, code search, AE/PeopleCode inspection |
| DBA | Oracle session monitoring, SQL workspace, top-SQL analysis, blocking chains |
| System Administrator | Runtime monitor, process scheduler, IB status, infrastructure health |
| Security Administrator | Role/permission traversal, access explanation, user comparison |
| Middleware Administrator | IB services, service operations, handlers, security, messages, nodes, routings, queue depth, transaction tracing |
| Functional Analyst | Record/field exploration, component navigation, data sampling |
| Operations / Help Desk | User session lookup, process status, recent activity |
| Architect | Environment comparison, dependency graph, impact analysis |

---

## Architecture Layers

```
                        ┌────────────────────────────────┐
                        │         AI Assistant           │
                        │  Natural-language queries,     │
                        │  diagnostics, recommendations  │
                        └──────────────┬─────────────────┘
                                       │
                        ┌──────────────┴──────────────────┐
                        │      Intelligence Layer         │
                        │  Reasoning, impact analysis,    │
                        │  anomaly detection, prediction  │
                        └──────────────┬──────────────────┘
                                       │
              ┌────────────────────────┴───────────────────────────┐
              │                  Knowledge Layer                   │
              │   Knowledge Graph · Universal Search · Reporting   │
              │   Graph algorithms, path traversal, cross-object   │
              │   relationship queries, snapshot diffing           │
              └────────────────────────┬───────────────────────────┘
                                       │
              ┌────────────────────────┴──────────────────────────┐
              │                   Object Model Layer              │
              │     Universal Object Model (UOM) · Providers      │
              │     Canonical object identity, relationships,     │
              │     graph shape, metadata, links, warnings        │
              └────────────────────────┬──────────────────────────┘
                                       │
     ┌─────────────────────────────────┴──────────────────────────────────┐
     │                         Connector Layer                            │
     │   psdb · ptmetadata · ae · peoplecode · ib · execution · oracle    │
     │   sqlws · envcompare · graphdb · uom · identity · nginx · system   │
     │   Grant-aware SQL, version-adaptive queries, structured warnings   │
     └─────────────────────────────────┬──────────────────────────────────┘
                                       │
       ┌───────────────────────────────┴────────────────────────────────┐
       │                          Data Layer                            │
       │       Oracle Database        PeopleSoft Metadata Tables        │
       │   V$SESSION · V$SQL         PSRECDEFN · PSPNLGRPDEFN           │
       │   DBA_OBJECTS               PSPCMPROG · PSAEAPPLDEFN           │
       │   ALL_TAB_COLUMNS           PSROLEDEFN · PSCLASSDEFN           │
       │                             PSIBAPPLDEFN · PSPRCSRQST          │
       └────────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

**Data Layer** — Oracle databases (HCM, FSCM) and their PeopleSoft metadata tables.
Nothing in PeopleSoft Hypergraph Intelligence writes to this layer. Read-only by design.

**Connector Layer** — Grant-aware, version-adaptive SQL queries. Each connector module owns
SQL for a domain. Returns structured Python dicts. Degrades gracefully when grants are missing.
For Integration Broker, connector data separates application services, service operations,
operation versions, handlers, message/queue mappings, security, routing, and node
relationships rather than flattening them into one routing-centric object.

**Object Model Layer** — The Universal Object Model (UOM) defines a canonical identity and
shape for every PeopleSoft object type. Providers implement object composition: metadata
assembly, relationship resolution, graph shape, links, and warnings.

**Knowledge Layer** — The in-memory graph database (`graphdb.py`) holds typed nodes and edges
built from UOM relationships. Global search aggregates provider results. Snapshots enable
point-in-time comparison and drift detection.

Graph-shaped API payloads preserve the UI-facing `relationship` edge label and
also expose a Knowledge Graph-compatible `type` edge alias where possible.
Shared metadata fields identify graph semantics:

- `_source` — provider family (`uom`, `peoplecode`, `application_engine`, `knowledge_graph`)
- `_vocabulary` — vocabulary flavor (`compact_uom`, `domain_peoplecode`, `domain_ae`, `knowledge_graph`)
- `_semantics` — intent such as `compact object preview` or `application-engine dependency graph`

**Intelligence Layer** — Cross-object reasoning: impact analysis, access explanation,
anomaly detection, configuration drift, performance correlation. Consumes graph + runtime
data to answer questions that cannot be answered by querying a single table.

**AI Assistant** — Natural-language interface over the Intelligence Layer. Graph traversal
plus LLM reasoning to answer freeform questions about the PeopleSoft enterprise.

---

## Platform Principles

Every subsystem must:

- **Expose REST APIs** — all data accessible as structured JSON via FastAPI routes
- **Expose UOM objects** — every object type has a canonical identity and shape
- **Expose graph providers** — relationships registered in the Knowledge Graph
- **Integrate into global search** — provider registered in ptmetadata OBJECT_REGISTRY
- **Expose runtime state where applicable** — live status, counts, activity
- **Expose diagnostics** — warnings, grant gaps, degraded capabilities are surfaced explicitly
- **Expose admin UI** — every module has a corresponding `/admin/<module>` page
- **Expose frontend shell** — static frontend assets live under `/static`; `/`
  redirects to `/static/index.html`; shared navigation is a grouped dropdown
  bar (8 functional groups + Home + Users) defined in `routers/admin/_core.py`
  (`_NAV_GROUPS`, `_nav_html`, `_NAV_CSS`) and styled in `/static/app.css`
- **Expose OpenAPI** — FastAPI auto-generates docs at `/docs`
- **Degrade gracefully** — missing grants, missing tables, missing data → structured warnings,
  not 500 errors. Never crash on the absence of an optional capability.
- **Preserve backward compatibility** — existing URLs and API shapes never break without
  a deliberate versioning decision

---

## Provider Contract

Every new subsystem should implement the following providers in order. Earlier providers
enable later ones — build vertically, not horizontally.

| # | Provider | File | Purpose |
|---|---|---|---|
| 1 | **Connector**| `connectors/<module>.py` | Grant-aware SQL; returns structured dicts; owns all SQL for the domain |
| 2 | **REST API** | `routers/<module>.py` | Thin FastAPI router; no SQL; delegates to connector |
| 3 | **Metadata Provider** | `connectors/ptmetadata.py` OBJECT_REGISTRY | Object type registration; discovery table; description columns |
| 4 | **UOM Provider** | `connectors/uom.py` | Canonical object: id, type, name, description, owner, status, warnings, _links, _relationships, _graph, _metadata. Object graph previews should use the shared UOM relationship graph helper so object pages and graph previews stay aligned; domain-specific graph providers may still supply richer external graphs when they own specialized traversal semantics. |
| 5 | **Graph Provider** | `connectors/graphdb.py` | Nodes and typed edges contributed to the Knowledge Graph |
| 6 | **Search Provider** | `connectors/ptmetadata.py` search | Results returned by `/api/peoplesoft/search` |
| 7 | **Runtime Provider** | `connectors/execution.py` or domain connector | Live state: active instances, queue depths, error counts |
| 8 | **Object Explorer Page** | via `connectors/uom.py` → `canonical_object()` | Object page at `/admin/object/<type>/<name>` rendered by the UOM renderer |
| 9 | **Admin Page** | `routers/admin/<group>.py` | Module-level UI at `/admin/<module>`; add route to the file matching the nav group (see `_core.py` `_NAV_GROUPS`) |
| 10 | **Frontend Shell** | `static/` + `routers/admin/_core.py` | Grouped dropdown nav (`_NAV_GROUPS`), shared `_shell()` / `_nav_html()`, CSS in `/static/app.css` |
| 11 | **Validation** | compile check + smoke test | `python -c "import main"` passes; key HTTP routes return 200; admin shell pages pass `scripts/smoke_admin_shell.py` |
| 12 | **ROADMAP update** | `ROADMAP.md` | Status, completed items, limitations documented |

Providers 7 and 8 are optional when the domain has no runtime state or no object-level
canonical page (e.g., environment comparison has no single "object" to navigate to).

### Plugin path (alternative to editing core files)

The table above assumes you're editing this codebase directly. `connectors/plugins.py`
offers a second path for providers 4, 5, 7, and 9 that doesn't require touching
`uom.py`/`graphdb.py`/`routers/peoplesoft.py`/`routers/admin/_core.py` at all:

| Provider | Core-file mechanism | Plugin mechanism |
|---|---|---|
| UOM Provider | `if object_type == "x":` branch in `routers/peoplesoft.py` | `plugins.register_object_provider(type, object_fn, payload_fn, registry_meta)` |
| Graph Provider | closure inside `graphdb.py`'s `build()`, added to its literal tuple | `plugins.register_graph_provider(name, loader)` — `loader(graph, env, limit)` |
| Runtime Provider | new endpoint in `routers/runtime.py` + hand-written admin card | `plugins.register_runtime_provider(name, fetch_fn, label)` — surfaces automatically on the generic "Plugin Providers" `/admin/runtime` card |
| Health Check | ad hoc status logic, no dedicated surface | `plugins.register_health_check(name, check_fn, label)` — surfaces automatically on the generic "Plugin Health Checks" `/admin/runtime` card; runs on demand via `GET /api/runtime/health-checks` |
| Config-Driven Source | dedicated ingest module + router, the `sqringest.py`/`cobolingest.py` pattern | `plugins.register_source_type(name, config_key, ingest_fn, status_fn)` — generic `GET/POST /api/plugins/sources/*` endpoints, SDK handles background-thread/lock/status-tracking |
| Admin Page + Nav | route in `routers/admin/<group>.py` + entry in `_core.py`'s `_NAV_GROUPS` | `plugins.register_router(router)` + `plugins.register_nav_entry(group, key, label, href)` |

A module dropped into `plugins/` and exposing `register(sdk)` is discovered and loaded
automatically at startup (`connectors/pluginloader.py`), with per-plugin failure
isolation — a broken plugin is logged and skipped, never crashes the server or other
plugins. See `PLUGINS.md` for the full walkthrough and `plugins/example_hello.py` for
a working reference implementation of all six extension points.

Use the plugin path for organization-specific extensions that shouldn't live in this
repo's core files; use the core-file path (table above) for anything meant to become a
permanent part of the platform itself.

---

## Planned Platform Capabilities

These are the long-term capabilities that the Architecture Layers will enable.
Individual modules contribute toward one or more of these.

### Digital Twin

A complete structural model of every PeopleSoft object and relationship in the enterprise —
fields, records, pages, components, menus, permission lists, roles, operators, application
engines, integration services, and Oracle objects — queryable as a graph.

*Enabled by:* Object Explorer, UOM, Knowledge Graph, all connector modules.

### Impact Analysis

Given any object or change, enumerate every downstream dependency:
"If I modify record PSOPRDEFN, what components, pages, AEs, PeopleCode programs, and
integration services will be affected?"

*Enabled by:* Knowledge Graph, REFERENCED_BY / CALLS / DEPENDS_ON edges, UOM relationships.

### Security Explanation

Answer: "Why does user JSMITH have (or not have) access to component USERMAINT?"
Traverse: operator → roles → permission lists → component access → page → fields.
Show the exact path. Show where access is granted and where it is blocked.

*Enabled by:* Security Explorer, Knowledge Graph SECURES edges, UOM role/permission providers.

### Runtime Visualization

Display live execution state across the full PeopleSoft stack:
Oracle sessions, blocking chains, long ops, Process Scheduler queue, active AE programs,
IB transaction queue depth, web server request rates, tuxedo domain status.

**App Server Domain Topology** is read from runtime views discovered at query time:

| View | Columns | Notes |
|------|---------|-------|
| `SYSADM.PSPMDOMAIN_VW` | PM_SYSTEMID, PM_DOMAIN_NAME, PM_HOST_PORT | Primary; available in PeopleTools 8.58+ |
| `SYSADM.PS_PSPMDOMAIN1_VW` | PM_DOMAIN_NAME, PM_HOST_PORT | Fallback; same data, no system ID |

The connector (`psdb.app_server_domains`) discovers which view is accessible at runtime
using `ptmetadata.has_table()`, queries the first available one, groups rows by
PM_DOMAIN_NAME, infers domain type from name suffix (`_APP` → App Server, `_PRCS` →
Process Scheduler, `_WEB` → Web/PIA), and returns a structured domain list with listener
counts and host:port breakdown. If neither view is accessible, a non-fatal warning is
returned and the UI degrades gracefully. `PSAPPSRV` and `PSAPPSRVDOM` are not required.

*Enabled by:* Execution Monitor, Oracle connectors, IB connector, infrastructure connectors.

### Transaction Replay

Capture a full user transaction (web request → PeopleCode → AE → IB → Oracle DML →
response) and replay it as a diagnostic trace — useful for debugging, performance tuning,
and regression testing.

*Enabled by:* Transaction Tracing module (planned), PeopleCode connector, IB connector,
Oracle session/SQL connectors.

### Configuration Drift

Detect differences between environments (HCM vs FSCM, production vs staging) at the
metadata, security, and configuration level. Alert when environments diverge from a known
good baseline.

*Enabled by:* Environment Comparison (implemented), Knowledge Graph snapshots, future
snapshot-diff APIs.

### Performance Analysis

Correlate slow Oracle SQL with the PeopleCode or AE that generated it, the component the
user was on, and the IB transaction it may have spawned. Identify root causes of performance
problems across layers without grepping logs manually.

*Enabled by:* SQL Workspace, Oracle session connector, AE connector, PeopleCode connector,
IB transaction connector — plus cross-layer join logic in the Intelligence Layer.

### AI Diagnostics

Answer natural-language questions by traversing the Knowledge Graph and reasoning over
live runtime data:

- "Which AE programs ran in the last hour and what SQL did they execute?"
- "Who has access to the payroll components and when did they last log in?"
- "Which records are referenced by EMPLID but have no key defined on that field?"
- "What changed in FSCM since last Tuesday?"

*Enabled by:* AI Assistant module (planned), Knowledge Graph, SQL Workspace, global search.

### Predictive Analysis

Before a migration or deployment, evaluate risk:
- Identify objects modified in both environments (conflict risk)
- Flag records with active Oracle sessions during a proposed maintenance window
- Identify PeopleCode that references tables being restructured
- Detect permission changes that would lock users out

*Enabled by:* Environment Comparison, Knowledge Graph, Runtime Monitor, Intelligence Layer.

---

## Processing Sequence Intelligence

**Status: ✅ substantially implemented — see ROADMAP.md's "Processing Sequence
Intelligence" section for exact scope/verification.** The prose below is the original
vision statement; implementation notes are inlined per subsection rather than
rewriting the vision itself.

PHI must understand not only what PeopleSoft objects exist, but also the order in which PeopleSoft evaluates and executes them.

PeopleSoft logic is sequence-sensitive. Component behavior is shaped by event order across search processing, component buffer construction, page activation, field interaction, row operations, and save processing. PHI will model this as first-class platform knowledge so analysis can answer questions like:

- What runs before this page is displayed?
- What logic fires when this field changes?
- What validation can block save?
- What code executes after a successful save?
- Which custom PeopleCode, Application Packages, SQRs, COBOLs, Integration Broker handlers, or Application Engine programs participate in the same processing path?
- Where does delivered logic differ from custom override behavior?

### PeopleCode Event Sequence Model — ✅ implemented (Component + Record; Page differently-shaped)

`connectors/peoplecode.py`'s `CANONICAL_COMPONENT_SEQUENCE` + `component_sequence()`
implement exactly the event list below for components. `record_sequence()` reuses the
same canonical vocabulary/order for genuinely record-owned PeopleCode (`PSPCMPROG
OBJECTID1=1`), filtered to the events that apply without a component context.
`page_owned_events()` covers Page-owned PeopleCode (`OBJECTID1=8`) as a flat list, not
a mirrored sequence — Pages don't have a rich multi-phase lifecycle the way
Components/Records do.

PHI will maintain a canonical PeopleCode event sequence model for component processing.

Initial sequence coverage includes:

- Menu/component entry
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

This model is based on standard PeopleSoft component processing behavior, where events fire in a defined order as users search, load a component buffer, interact with fields and rows, and save data.

### Sequence-Aware Object Graph — ✅ partially implemented (semantically-groundable edges only)

`FIRES_BEFORE`/`FIRES_AFTER` (ordering) and `VALIDATES_BEFORE_SAVE`/`MUTATES_BUFFER`/
`MUTATES_DATABASE` (semantic classification, derived from each event's own documented
PeopleTools meaning — see `peoplecode.event_semantic_edges()`) are implemented in
`graphdb.py`'s `component_sequences()`/`record_sequences()`. `PART_OF_SEQUENCE` (largely
redundant with the existing `BELONGS_TO` edge), `CALLS_DURING_EVENT`,
`BLOCKS_PROCESSING`, and `TRIGGERS_RUNTIME_ACTION` remain unimplemented — each would
need data this platform doesn't track (a real PeopleCode call graph, workflow-trigger
detection, or save-failure/error-path data), not just a classification of what's
already known, so they weren't faked.

The Unified Object Model will be extended with processing-sequence relationships.

New relationship types should include:

- `FIRES_BEFORE`
- `FIRES_AFTER`
- `PART_OF_SEQUENCE`
- `VALIDATES_BEFORE_SAVE`
- `MUTATES_BUFFER`
- `MUTATES_DATABASE`
- `CALLS_DURING_EVENT`
- `BLOCKS_PROCESSING`
- `TRIGGERS_RUNTIME_ACTION`

PeopleCode definitions should no longer be treated only as isolated code artifacts. They should be attached to their execution context:

- Component
- Page
- Record
- Field
- Component record
- Component record field
- Menu/component entry point
- Event name
- Event sequence phase
- Save phase
- Runtime interaction phase

### Processing Path Explorer — ✅ implemented (Component + Record)

`/admin/compseq` ("PC Timeline") — ordered phase-card visualization (not just a
table) with a Component/Record mode toggle, delivered/custom/empty coloring, and
click-to-expand slot detail. Field/Component-Interface/Transaction-path contexts are
not covered — no concrete UOM object type maps cleanly onto those yet.

PHI should provide a Processing Path Explorer that can display the expected execution flow for a component, page, field, or transaction.

For a selected component, PHI should show:

- Component entry path
- Search events
- Buffer build events
- Page activation events
- Field interaction events
- Row insert/delete events
- Save validation events
- Post-save events
- PeopleCode attached at each point
- Application Package calls made from each event
- SQL executed or referenced by event logic
- Message Catalog references
- Component Interface participation
- Integration Broker calls
- Application Engine, SQR, or COBOL handoffs when detectable

The goal is to make PHI capable of explaining PeopleSoft behavior in terms of ordered execution, not just static dependencies.

### Delivered vs Custom Sequence Behavior — 📋 planned, not built for PeopleCode

Implemented for SQR/COBOL (real parallel delivered+custom source trees exist — see
Source Artifact Intelligence's Override Detection/Source Comparison sections). Not
implemented for PeopleCode: there's no delivered-source baseline to diff a component's
PeopleCode against (delivered PeopleCode isn't distributed as separate comparable
source files the way SQR/COBOL are) — the existing `LASTUPDOPRID`-based
delivered/custom heuristic in `component_sequence()`/`record_sequence()` is the
practical substitute today.

For delivered PeopleCode, SQRs, COBOLs, Application Engine programs, and Application Packages, PHI should identify whether custom logic overrides, extends, or changes the delivered processing path.

The platform should be able to show:

- Delivered event logic
- Custom event logic
- Custom overrides
- Custom additions
- Sequence position of custom logic
- Differences between delivered and custom source
- Risk introduced by custom logic based on where it executes
- Upgrade impact when delivered sequence behavior changes

This is especially important for events such as `SearchSave`, `FieldEdit`, `FieldChange`, `SaveEdit`, and `SavePostChange`, where misplaced or modified logic can alter validation, persistence, integration behavior, or downstream processing.

### Runtime Correlation — ✅ implemented for Application Engine; PeopleCode/Component-level blocked

`execution.instance_trace()` (`GET /api/runtime/process/{instance}/trace`) composes
AE program definitions + Oracle ASH wait events/top SQL correlated to a process
instance's run window + log errors in-window — real data, real correlation, verified
against a genuine multi-hour AE run. Does not claim step-by-step AE execution timing
(no `PSAERUNCNTL`/`PS_AE_TRACE`/`PSAEMSGLOG` table present in this environment).
Full PeopleCode/Component-level trace correlation (PIA request/session activity,
PeopleCode trace output) remains blocked on missing PIA browser-traffic data — see
Phase 4's Runtime Intelligence section in ROADMAP.md.

Processing-sequence intelligence should eventually correlate static metadata with runtime evidence.

Where possible, PHI should connect:

- PIA request/session activity
- Component access
- PeopleCode trace output
- SQL trace output
- Oracle ASH samples
- Integration Broker activity
- Process Scheduler execution
- Application Engine/SQR/COBOL execution

This allows PHI to answer not only “what should run?” but also “what actually ran?”.

---

# Source Artifact Intelligence

## Philosophy

Not every PeopleSoft object lives inside the Oracle database.

Large portions of a PeopleSoft implementation exist as filesystem artifacts, including:

- SQR programs
- SQC include files
- COBOL programs
- COBOL copybooks
- Shell scripts
- Batch utilities
- SQL scripts
- Data Mover scripts
- Configuration templates
- Custom deployment assets

These artifacts are first-class components of the PeopleSoft enterprise and therefore become
first-class objects within the PeopleSoft Hypergraph Intelligence Digital Twin.

The platform treats filesystem artifacts exactly like database metadata:

- discoverable
- searchable
- graph-aware
- version-aware
- environment-aware
- impact-analyzable

---

## Delivered vs Custom Source Model

PeopleSoft source code typically exists in two logical layers.

### Delivered Source

Vendor-delivered source distributed by Oracle.

Examples:

- delivered SQR
- delivered COBOL
- delivered SQC
- delivered COPY libraries

These files are considered the canonical baseline.

### Custom Source

Customer-developed artifacts.

Custom source may:

- override delivered programs
- extend delivered functionality
- introduce entirely new programs
- replace individual include files
- introduce custom copybooks

Custom artifacts are maintained separately from delivered source.

PHI models both layers simultaneously.

---

## Configuration

Filesystem locations are configured as flat, per-artifact-type source lists in
`config.json` (`sqr_sources`, `cobol_sources`) — one entry per (env, delivered/custom)
combination, not a nested `{env: {delivered: {...}, custom: {...}}}` tree. Each entry
carries its own `ssh_host` so delivered and custom trees can even live on different
hosts if needed.

Example (as actually implemented — see `connectors/sqringest.py`/`cobolingest.py`):

```json
{
  "sqr_sources": [
    {
      "env": "HCM", "key": "hcm_sqr_delivered", "source_type": "delivered",
      "ssh_host": "hcm_appserver", "label": "HCM SQR Library - Delivered",
      "sqr_dir": "/opt/psoft/hcm/ps_app_home/ps_home8.62.07/sqr"
    },
    {
      "env": "HCM", "key": "hcm_sqr_custom", "source_type": "custom",
      "ssh_host": "hcm_appserver", "label": "HCM SQR Library - Custom",
      "sqr_dir": "/opt/psoft/hcm/ps_cust_home/sqr"
    }
  ],
  "cobol_sources": [
    {
      "env": "HCM", "key": "hcm_cobol_delivered", "source_type": "delivered",
      "ssh_host": "hcm_appserver", "label": "HCM COBOL Library - Delivered",
      "cbl_src_dir": "/opt/psoft/hcm/ps_app_home/ps_home8.62.07/src/cbl",
      "cbl_compiled_dir": "/opt/psoft/hcm/ps_app_home/ps_home8.62.07/cblbin"
    }
  ]
}
```

**No separate `copybook` artifact type**: PeopleSoft COBOL copybooks are not a
distinct file type/extension/directory. They're plain `.cbl` files distinguished only
by the *absence* of a `PROGRAM-ID` (they're pulled into programs via `COPY name.`) —
`connectors/cobolparser.py` classifies `file_type` as `program`/`copybook` by content,
not by config path. No true `.cpy`-style copybook files exist in any environment this
platform has been run against so far; if one ever does, it would need its own
`source_type`/parser branch, not a new top-level config key.

`source_type: "delivered"|"custom"` on each entry drives resolution: SQR/COBOL admin
pages and the `overrides()` query (`GET /api/sqr/overrides`) find filenames present in
*both* a delivered and custom entry for the same env to surface customizations —
there's no separate "search order" merge logic; delivered and custom trees are indexed
and queried as distinct, comparable sets rather than resolved into one effective view.

---

## Source Resolution — ✅ implemented (as distinct comparable sets, not a merged view)

Every source file is indexed as its own row, keyed by `(filename, source_key)` where
`source_key` identifies which configured source (env × delivered/custom) it came from
— e.g. `PAY003.sqr` indexed under both `hcm_sqr_delivered` and `hcm_sqr_custom` produces
two distinct rows, not one merged `SQR:PAY003` logical object with a resolved
"effective version." There is no custom-over-delivered layering/precedence — delivered
and custom are peers you compare, not a stack you resolve.

## Override Detection — ✅ implemented (overridden / custom-only / delivered-only)

`sqrdb.overrides()` / `GET /api/sqr/overrides` finds filenames present in *both* a
delivered and custom source for the same env — genuine customizations of a delivered
program. `sqrdb.override_summary()` / `GET /api/sqr/override-summary` (and
`/admin/sqroverrides`) extends this to the full picture: **overridden** (in both),
**custom-only** (net-new custom code, or a former override whose delivered baseline
was later removed — a single snapshot can't distinguish these), and
**delivered-only** (count only, not a browsable list — can be tens of thousands of
rows). No per-object "Effective Version" field on the UOM object — delivered and
custom remain distinct comparable rows, not resolved into one merged view.

## Source Comparison — ✅ implemented for SQR and COBOL, with a normalized diff mode

`/admin/sqrcompare` and `/admin/cobolcompare` (`GET /api/sqr/envcompare` / `GET
/api/cobol/envcompare`) compare two environments' libraries side-by-side (Changed /
Only A / Only B / Identical tabs). Two diff modes: `exact` (raw MD5 `content_hash`
equality) and `normalized` (ignore comment lines and insignificant whitespace,
reusing each language's own parser comment convention — SQR's `!` lines, COBOL's
column-7 `*` — so a whitespace/comment-only edit doesn't register as a real change).
**Not implemented**: delivered-vs-custom diff view, or syntax-aware (AST-level)
diffing beyond comment/whitespace normalization.

## Source Relationships — ✅ implemented, different edge names than originally planned

Real edge types emitted by `connectors/graphdb.py` (`sqr_programs()`/`cobol_programs()`
builders) — simpler than the originally-planned `CALLS_PROGRAM`/`CALLS_REPORT`/
`EXECUTES_SQL`/`REFERENCES_PROCESS` naming, reusing the same edge vocabulary the rest
of the Knowledge Graph uses rather than inventing artifact-specific edge types:

- **SQR**: `sqr_program → record` `READS`/`WRITES`; `sqr_program → sqr_program`
  `INCLUDES` (SQC includes); `prcs_defn → sqr_program` `WRAPS`
- **COBOL**: `cobol_program → record` `READS`/`WRITES` (from `EXEC SQL` blocks);
  `cobol_program → cobol_program` `COPIES` (COPY statements) and `CALLS` (static
  `CALL 'X'` targets — dynamic `CALL WS-VAR` can't be resolved and is skipped)

## Source Intelligence — ✅ implemented for what each parser actually extracts

- **SQR** (`connectors/sqrparser.py`): include hierarchy, `PS_` table references
  (SELECT/UPDATE/INSERT/DELETE), procedure definitions, header metadata (description,
  release, revision)
- **COBOL** (`connectors/cobolparser.py`): program-vs-copybook classification (by
  `PROGRAM-ID` presence, not file extension), COPY dependencies, static CALL targets,
  `EXEC SQL...END-EXEC` table references, description extraction (skips the fixed
  Oracle license preamble)
- **Not implemented for either**: dynamic SQL extraction (SQR/COBOL don't have
  PeopleCode's `extract_dynamic_sql()` variable-reconstruction treatment), process/AE
  launch references, file I/O tracking, external command execution tracking

## Effective Source View — 📋 planned, not built

No "effective implementation" UI exists — the closest equivalent today is opening the
delivered and custom detail pages side-by-side, or using the override/comparison
endpoints above. A dedicated effective-view page (showing resolved implementation with
delivered/custom provenance inline) remains open work if wanted.

## Source Analytics — ✅ implemented for SQR and COBOL, narrower than originally planned

`/admin/sqr/analytics` (`GET /api/sqr/analytics`): top 30 PS_ tables by reference count,
top 20 most complex SQR programs, top 20 most-included SQC files, release breakdown.
`/admin/cobol/analytics` (`GET /api/cobol/analytics`): the same shape for COBOL — top
tables, most-complex programs, most-COPYd copybooks, delivered/custom breakdown.
**Not implemented**: customization/override percentage metrics, cyclomatic complexity,
dead-include detection, duplicate-source detection, dependency fan-out/fan-in metrics.

---

## Future Intelligence

Future releases may provide:

- automatic source lineage
- customization heat maps
- migration impact prediction
- AI-generated code summaries
- AI-generated documentation
- automated refactoring recommendations
- modernization analysis
- dead code detection
- duplicate logic detection

---

## Module Implementation Order

Modules should be built in an order that fills the provider stack from bottom to top.
Lower layers (connectors, UOM) unlock higher layers (graph, search, intelligence).

```
Priority 1 — Foundation (✅ complete)
  Object Explorer · Metadata Engine · UOM · Knowledge Graph · Field Explorer

Priority 2 — Core Object Coverage (✅ complete)
  Security Explorer · Component Explorer · Page Explorer · Record Explorer
  PeopleCode Explorer · Application Engine Explorer

Priority 3 — Operations (✅ complete)
  Runtime Monitor · SQL Workspace · Integration Broker Explorer · Environment Comparison

Priority 4 — Observability (✅ complete)
  Log Intelligence (PIA/APPSRV/Tuxedo/nginx/F5/IGW/PRCS-AE) · App Server live
  process tracking · Incident recording + replay
  Remaining: Performance Analysis (cross-layer SQL↔PeopleCode↔component
  correlation) — not started

Priority 5 — Intelligence (✅ complete)
  Impact Analysis · Security Explanation (Access Path Explorer) · Configuration
  Drift (scheduled snapshots + alerts) · Dependency Graph (Knowledge Graph,
  full UOM/KG alignment audit closed)

Priority 6 — Source Artifact Intelligence (✅ complete)
  SQR + COBOL discovery, indexing, dependency graphs, full-text search;
  SQR + COBOL environment comparison (with whitespace/comment-normalized
  diff mode) and analytics dashboards; override intelligence
  (delivered/custom/overridden classification). Remaining: syntax-aware
  (AST-level) diffing — see ROADMAP.md.

Priority 7 — Automation & Reporting (not started)
  Deployment Center · Automation

Priority 8 — AI (✅ complete)
  AI Assistant (3 providers, 21+ tools). Remaining: Predictive Analysis —
  not started.

Priority 9 — Platform Extensibility (✅ v1 + v2 complete)
  Plugin SDK, six extension points — see Provider Contract → Plugin path,
  above. No open candidates.
```

---

## Design Constraints

**Read-only by default.** PeopleSoft Hypergraph Intelligence never writes to PeopleSoft or Oracle databases.
Write operations (identity sync, future deployment center) are explicitly scoped and
separately authorized.

**Grant-aware everywhere.** Database accounts (`deathstar_admin` for HCM,
`deathstar_mon` for FSCM) have limited grants. Every query guards against ORA-00942
and similar with `ptmetadata.has_table()` or try/except. Missing capability → warning,
not crash.

**Two environments.** HCM → `HRDMO` (deathstar_admin, broader grants).
FSCM → `FSCMDMO` (deathstar_mon, narrower grants). Environment name is always
a first-class parameter in connector functions.

**Port 8088 is sacred.** The FastAPI app runs on `127.0.0.1:8088` and is proxied
through nginx at `https://admin.deathstar.chickenkiller.com:10443/admin/`. Never change
the port.

**No breaking changes.** Existing URLs, API response shapes, and connector function
signatures are preserved. New fields may be added; existing fields are never removed
or renamed without a deliberate versioning decision.

**SQL in connectors, not routers.** All Oracle SQL lives in `connectors/`. Routers
are thin delegation layers. This keeps SQL testable and auditable.
