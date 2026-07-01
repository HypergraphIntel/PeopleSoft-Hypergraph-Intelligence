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

## What is DeathStar?

**DeathStar is a PeopleSoft Digital Twin.**

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
Nothing in DeathStar writes to this layer. Read-only by design.

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

## Module Implementation Order

Modules should be built in an order that fills the provider stack from bottom to top.
Lower layers (connectors, UOM) unlock higher layers (graph, search, intelligence).

```
Priority 1 — Foundation (complete)
  Object Explorer · Metadata Engine · UOM · Knowledge Graph · Field Explorer

Priority 2 — Core Object Coverage (in progress)
  Security Explorer · Component Explorer · Page Explorer · Record Explorer
  PeopleCode Explorer · Application Engine Explorer

Priority 3 — Operations (complete)
  Runtime Monitor · SQL Workspace · Integration Broker Explorer · Environment Comparison

Priority 4 — Observability
  Transaction Tracing · Logging Platform · Performance Analysis

Priority 5 — Intelligence
  Impact Analysis · Security Explanation · Configuration Drift · Dependency Graph

Priority 6 — Automation & Reporting
  Deployment Center · Reporting · Automation

Priority 7 — AI
  AI Assistant · Predictive Analysis
```

---

## Design Constraints

**Read-only by default.** DeathStar never writes to PeopleSoft or Oracle databases.
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
