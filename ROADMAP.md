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
- Tree → Record USES edges
- Impact analysis (forward and reverse dependency traversal with depth control)

### Remaining

- Align persisted Knowledge Graph ingestion with UOM `_relationships`, UOM `_graph`, and domain graph vocabulary metadata
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
connectors/ai_tools.py    ← Tool definitions wrapping existing DeathStar connectors
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

### Tools (AI-callable DeathStar capabilities)

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
3. **What object**: record/component/AE name extracted from error message → links to DeathStar pages
4. **Fix**: "Ask AI" pre-loads the assistant with the error context; AI uses existing tools
   (`peoplecode_search`, `record_usage`, `sql_lookup`) to diagnose and suggest a fix

### AI Tools Added

| Tool | Purpose |
|------|---------|
| `log_search` | Search web+app entries by OPRID, time range, component, text, level |
| `log_errors` | Surface and group errors; returns error_code, object_ref, count, sample |
| `session_log_chain` | Full web→app chain for an OPRID in a time window |

---

## Implementation Status

### ✅ Completed (2026-07-01)

- Architecture design and config schema
- Phase 8 roadmap documentation

### In Progress

- `connectors/sshclient.py` — paramiko SSH/SFTP wrapper
- `connectors/logparser.py` — PIA / APPSRV / Apache / F5 parsers
- `connectors/logdb.py` — SQLite storage
- `connectors/logingest.py` — ingestion orchestration
- `connectors/scheduler.py` — 60s log ingest job
- `routers/logs.py` — REST API
- `routers/admin/logs.py` — Log viewer + error surface + session chain UI
- AI tools: `log_search`, `log_errors`, `session_log_chain`

### Design Decisions

- **F5**: Supported via `f5_access` type using Apache-combined parser (HSL iRules log in NCSA format)
- **Future F5 native**: When F5 Analytics/AVR logs become available, add `f5_avr` parser with VS name, pool, irule fields
- **Retention**: 30 days of web entries, 90 days of app entries, 90 days of errors (configurable)
- **Dedup**: log_errors has UNIQUE(source_name, ts, raw) — safe to re-ingest overlapping byte ranges
- **OPRID extraction**: web logs — second NCSA field (auth user); app logs — `N.OPRID` pattern in APPSRV format

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
