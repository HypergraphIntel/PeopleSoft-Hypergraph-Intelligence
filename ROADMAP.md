# PeopleSoft Hypergraph Intelligence Roadmap

## Vision

PeopleSoft Hypergraph Intelligence is a unified operational intelligence platform for PeopleSoft, covering:

- Metadata exploration
- Dependency analysis
- Runtime observability
- Environment comparison
- Security analysis
- Operational tooling
- AI-assisted engineering workflows

This file tracks current status and remaining work only. For the dated, narrative
account of *how* and *why* each change landed — including bugs found and fixed,
verification steps, and design tradeoffs — see `DEVELOPMENT_DIARY.md`.

---

# Current Status

## Platform Status — ✅ Production-ready

- Unified Object Model (UOM) covering ~54 PeopleSoft object types
- Object Explorer, Graph Explorer (List / Visual / Impact / Drift)
- Knowledge Graph with scheduled snapshots, drift detection, and impact analysis
- Environment Compare (17 object types) with scheduled drift alerts
- Runtime Monitor: Oracle ASH, runtime alerts, App Server domain + live process tracking
- SQL Workspace with autocomplete, typed binds, timeout/cancellation
- Integration Broker, Identity/Security, Portal, SQL/Query/Tree/Menu/Component Interface explorers
- AI Engineering Assistant (Claude/OpenAI/Ollama) with 17+ tools
- Log Intelligence: PIA/APPSRV/Tuxedo/nginx/F5/IGW/PRCS-AE ingestion pipeline
- SQR + COBOL source artifact intelligence (index, search, dependency graphs, env comparison)
- Plugin SDK v1 (object/graph/runtime providers, admin pages)
- Admin shell smoke test harness (69 pages)

---

# Phase 4 — Runtime Intelligence

**Status: Substantially complete.**

### Completed
- Oracle session tracking, SQL/wait-event visibility, lock/blocking analysis
- Process Scheduler + Integration Broker runtime linkage; unified runtime graph API
- Runtime alerts (process errors, long processes, queue depth, blocking, domain health)
- Operational dashboard (`/admin/`) — live alerts, health, log intelligence, trend sparklines
- Runtime history persistence (`runtimedb.py`, 5-min snapshots, 1h/6h/24h/7d trend charts)
- Interactive infrastructure topology (`/admin/topology`)
- Incident Recording: full RCA snapshot capture (`incidentdb.py`) + replay UI (`/admin/incidents`)
- App Server live process tracking (`connectors/appsrvproc.py`, SSH `ps` + Tuxedo arg parsing) —
  goes one level below the domain-only `PSPMDOMAIN_VW` view

### Remaining — blocked on live traffic data
- **Browser session tracking**: `PIA_access.log` is 0 bytes in this environment (no HTTP
  access logging enabled) — nothing to ingest or verify against.
- **WebLogic session tracking**: `PIA_weblogic.log` has real content but zero
  session-lifecycle events — infrastructure/health noise only.
- Both need either real end-user PIA traffic or WebLogic access/session logging enabled
  before there's anything to build against.

---

# Phase 5 — Complete Knowledge Graph

**Status: ✅ Complete.** All ~54 UOM object-type providers are implemented and
KG-aligned (see "UOM/KG Alignment Audit" below).

### Provider coverage
Operators, Roles, Permission Lists, Components, Pages, Records, Fields, PeopleCode,
Application Engines, Integration Broker (Services/Nodes/Queues/Routings), Menus, Trees,
SQL Definitions, PS Queries, Component Interfaces, Portal Registry, Application Packages,
Message Catalog, Approval Framework, XML Publisher, Search Definitions/Categories,
Pivot Grids, Connected Queries, Process Definitions, File Layouts, Translate Values,
App Designer Projects, IB Messages/Applications/Service Groups/Routings, Application
Classes, Content Services, PTF Tests, ADS Definitions, URL Definitions, Chatbot Skills,
Style Sheets, Archive Objects, Timezones, Locales, PM Metrics/Transactions/Events,
SQR programs, COBOL programs/copybooks.

### ⚠️ Stub providers (no backing tables in this environment)
Guarded by `has_table()`, return empty/stub results without crashing:
Navigation Collections, Event Mappings, Related Content, Drop Zones.

### ⛔ Deprioritized providers
Investigated and deprioritized — reference table for future re-evaluation on other
environments/PeopleTools versions:

| Provider | Tables | Reason |
|---|---|---|
| IB Schema Definitions | PSIBSCMADATA / PSIBSCMADFN | CLOB-only / no grant / redundant with PSMSGDEFN |
| Navigation Collections | PTNC_COLLECTION | Does not exist |
| Event Mappings | PSEFMAPPINGDEFN | Does not exist |
| Related Content | PSRELCONDEFN | Does not exist |
| Drop Zones | PSPTDZDEFN | Does not exist |
| WorkCenters | — | No standalone definition table |
| Dashboards | PS_EOEN_DASHBRD | 0 rows |
| BI Publisher / Branding / Page Composer | — | No backing tables |
| Fluid Homepage / Tiles | PSPGEDEFN etc. | Absent or 0 rows |
| Activity Guide Collections | PS_AGC_TILE_TBL | 2 rows — too few |
| File Reference Definitions | PSFILEREDEFN | 19,622 rows, mostly system refs — marginal |
| Business Process Definitions | PSBUSPROCDEFN | Deprecated Workflow Navigator (2000–2002) |
| IB Local Schema | PSLSDEFN | Compressed binary — impractical |
| IB Service Setup | PSIBSVCSETUP | Single-row global config, not a catalog |

### Knowledge Graph relationships
Edge types in active use: `CALLS`, `REFERENCES`, `USES`, `CONTAINS`, `WRAPS`, `SECURES`,
`READS`/`WRITES`, `DEPLOYS`, `HAS_PERMISSION`, `HAS_MEMBER`, `SENDS`/`RECEIVES`,
`DECLARED_ON`, `EXPOSES`, `FIRES_BEFORE`/`FIRES_AFTER`, `BELONGS_TO`, `GENERATES`.

**✅ UOM/KG Alignment Audit — complete.** Every UOM object type's declared
`_relationships`/`_graph` now matches what's actually persisted in the Knowledge Graph.
Two-pass Explore-agent audit (all 54 provider types) found 10 genuine mismatches, all
fixed: `operator↔permissionlist`, `role↔operator`, `service_operation↔node`,
`portal_registry` (had zero KG persistence at all), `tree→field`,
`component_interface→menu/record/field`, AE `section` node-type unification + `CALLS`
edges, `component→record` broader page-usage, `page→page` subpages, and
`content_service↔portal_registry`. One item (page-level security) was correctly
re-scoped as not-a-gap — the data is already reachable via existing edges. Three
independent bugs were found and fixed along the way (an Oracle NULL-comparison bug in
`portal_registry_portals()`, a SQL-generation bug in a column-fallback rewrite, and a
self-loop bug in AE `CALLS` edges). Full narrative in `DEVELOPMENT_DIARY.md`.

**✅ Dynamic SQL READS/WRITES coverage.** PeopleCode `SQLExec(&var)`/`CreateSQL(&var)`
calls (SQL built into a variable beforehand) now contribute KG edges — previously only
inline-literal calls did. `connectors/peoplecode.py:extract_dynamic_sql()`
reconstructs the SQL text from prior `&var = ...` assignments; dynamically-chosen table
names are correctly left unresolved rather than guessed.

### Cross-references (Object Explorer "what references me / what do I reference")
Implemented for Records, Application Engines, SQL Definitions, PeopleCode, Pages,
Components, Menus, Queries, Trees, Portal Registry, Messages (READS/WRITES, "Used By",
"Deploys", access-path security chains). Universal coverage across *all* object types
remains open-ended — no further concrete gaps identified.

### AE PeopleCode-step edges — known limitation, not actionable here
`AE_ACTTYPE == 'P'` never matches in this environment's schema version, so AE→PeopleCode
`CONTAINS` edges are a no-op on both the UOM reference implementation and the KG side.
Pre-existing schema-version gap, not introduced by any work in this repo.

---

# Phase 6 — Environment Intelligence

**Status: Substantially complete.**

### Completed
- 17-type environment comparison (records, fields, components, pages, permissions,
  roles, AE, PeopleCode, SQL defs, portals, queries, menus, trees, IB routings, IB
  messages, component interfaces, process definitions) with AE step-level body diff
- Scheduled drift snapshots (SQLite `driftdb.py`) with threshold + growth-rate alerts
- Point-in-time runtime snapshots and drift history time series (`/admin/drift`)
- Deployment risk scoring (`/api/impact/risk`) and project impact reports
  (`/api/impact/project`, `/admin/impact`)
- Promotion event log (Phase 1): manual `POST /api/promotions` + timeline UI
  (`/admin/promotions`)

### Remaining — blocked on real promotion-chain environments
- **Promotion auto-detection** (Phase 2): snapshot `PSPROJECTDEFN.LASTUPDDTTM` per
  environment and auto-record a promotion when a target env's timestamp advances to
  match the source. The Phase 1 schema/API already accommodate this without structural
  changes. **Lab context**: HCM and FSCM here are separate pillars, not a promotion
  chain — this needs real DV/TST/UAT/PRD connections to implement meaningfully.

---

# Phase 7 — AI Engineering Assistant

**Status: ✅ Complete.**

3-provider architecture (`connectors/ai.py` abstract interface; `ai_claude.py`/
`ai_openai.py`/`ai_ollama.py` implementations) so provider swaps require only a new
`ai_<name>.py` file. 17+ tools in `connectors/ai_tools.py`, each a thin adapter over an
existing connector (no new SQL): `search_objects`, `peoplecode_search`,
`graph_dependencies`, `graph_impact`, `who_has_access`, `ae_steps`, `sql_lookup`,
`envcompare_summary`, `project_impact`, `active_sessions`, `record_usage`,
`log_search`, `log_errors`, `session_log_chain`, `environment_health`,
`ib_diagnostics`, `process_scheduler_health`, `component_events` (now enriched with
canonical processing-sequence context). Streaming chat UI at `/admin/assistant` with
an agentic tool loop (up to 8 rounds).

Config: `config.json["ai"]`, provider selection + per-provider settings; env var
overrides (`CLAUDE_API_KEY`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`) take precedence.

---

# Phase 8 — Log Intelligence

**Status: ✅ Complete** for Linux-hosted tiers.

### Architecture
All log sources are remote, fetched via SSH/SFTP (`connectors/sshclient.py`) with
per-file byte-offset tracking (only new content re-fetched). `ssh_hosts` in
`config.json` defines reusable connection profiles; `log_sources` / `igw_log_sources`
define what to ingest and how to parse it (`connectors/logparser.py`).

| Tier | Log type | Notes |
|------|----------|-------|
| F5 LTM | `f5_access` | Apache-combined (HSL iRule output) |
| nginx/Apache | `apache_access`/`apache_error` | Standard NCSA |
| WebLogic PIA | `pia_access`/`pia_error` | OPRID in auth field |
| Tuxedo App Server | `appsrv` | OPRID, ORA-, PC errors |
| Tuxedo ULOG | `tuxedo` | Domain-level events |
| Integration Gateway | `igw_error_log` | HTML block parser, 12 regex patterns |
| Process Scheduler (AESRV) | `prcs_ae` | Applid, process instance, error detection |

Storage: SQLite `data/logs.db` (`web_entries`, `app_entries`, `log_errors`), 30/90/90-day
retention. Session-chain correlation joins `PSACCESSLOG` → `web_entries` → `app_entries`
→ `log_errors` by OPRID and time window.

### Completed
- Full ingestion pipeline + 60s scheduler cycle; `/admin/logs`, `/admin/log_errors`,
  `/admin/log_viewer`, `/admin/log_session`, `/admin/igw`, `/admin/prcs-ae`
- AI tools: `log_search`, `log_errors`, `session_log_chain`
- Error surface grouped by code+object with "Ask AI" deep-links

### Remaining
- Process Scheduler log ingestion for **Windows-hosted** schedulers (SMB/WinRM
  transport) — blocked until a Windows scheduler server is available to test against.
  Design (`prcs_log_sources` transport types: `local`/`ssh_sftp`/`smb`/`winrm`/`agent`)
  is documented but unimplemented.
- `msgLog.html` (`igw_msg_log`): message logging is disabled in this environment — no
  file exists to parse against.

---

# Phase 9 — Platform Extensibility

**Status: ✅ v1 complete.**

Every extension surface (object providers, KG builders, runtime providers, admin
dashboards) was previously a hardcoded literal list/dict/if-chain only core code could
append to. `connectors/plugins.py` adds one appendable registry per surface;
`connectors/pluginloader.py` discovers and loads `plugins/*.py` at startup with
per-plugin isolation (a broken plugin logs a warning and is skipped — verified the rest
of the platform keeps working). `plugins/example_hello.py` is a worked example
exercising all four extension points. Full SDK documentation in `PLUGINS.md`.

### Remaining (v2 candidates, not built)
- Custom health checks (no dedicated registry yet — a plugin's runtime provider is a
  reasonable stand-in today)
- A dedicated "config-driven source" registration API for plugins that want to
  replicate the SQR/COBOL ingest pattern (object + graph provider registries are
  already sufficient building blocks; just not formalized into their own API)

---

# Phase 10 — Source Artifact Intelligence

**Status: ✅ Complete.** SQR, SQC, and COBOL/copybook files are first-class UOM
objects participating in search, graph traversal, dependency analysis, and environment
comparison.

### SQR
- Source discovery + indexing (`sqringest.py`/`sqrdb.py`/`sqrparser.py`) — delivered +
  custom trees per env, incremental scan via MD5 `content_hash`
- `/admin/sqr` (list/detail/analytics), `/admin/sqrsearch` (full-text), `/admin/sqrdeps`
  (include dependency graph — forward tree, reverse "Included By", force-directed
  canvas), `/admin/sqrcompare` (HCM vs FSCM side-by-side diff)
- KG edges: `sqr_program → record` READS/WRITES, `sqr_program → sqr_program` INCLUDES,
  `prcs_defn → sqr_program` WRAPS

### COBOL
- `cobol_sources` config (4 entries: HCM/FSCM × delivered/custom). Discovery: PeopleSoft
  COBOL "copybooks" are `.cbl` files distinguished by the *absence* of `PROGRAM-ID`
  (pulled in via `COPY name.`), not a separate `.cpy` extension — none exist in this
  environment. Most delivered `.cbl` source is mode 700 (not readable by the SSH service
  account) — ingestor counts this as `denied`, not an error (115/977 readable here).
- `connectors/cobolparser.py`/`cobol_db.py`/`cobolingest.py`; `/admin/cobol` list +
  detail (Overview / COPY Dependency Graph / Source)
- KG edges: `cobol_program → record` READS/WRITES, `→ cobol_program` COPIES/CALLS
- `/admin/cobolcompare` (`cobol_db.envcompare_cobol()`, `GET /api/cobol/envcompare`) —
  HCM vs FSCM side-by-side diff, same shape/UI language as `/admin/sqrcompare` (a
  patch/drift-integrity check, not assumed feature parity — verified real data first:
  in this environment HCM/FSCM's 115 delivered `.cbl` files are byte-identical by
  content_hash, so it correctly reports 0 differences today; will surface real drift
  automatically the moment one environment gets patched independently of the other)

### SQR Override Intelligence — ✅ Complete
- `connectors/sqrdb.py`'s `override_summary()` classifies every configured delivered/
  custom source pair per env into three categories: **overridden** (same filename in
  both — customized copy of a delivered program), **custom-only** (filename exists only
  in custom — net-new custom code), **delivered-only** (count only, to avoid dumping
  hundreds of unmodified rows). Extends the older `/overrides` endpoint (which only
  detected the overridden/duplicate-filename case) to the full picture.
- `GET /api/sqr/override-summary?env=` — verified live against real Oracle-backed index
  data (`hcm_sqr_delivered`/`fscm_sqr_delivered`, 179 programs each); this environment's
  custom-source trees are empty so the honest live result is `0 overridden / 0 custom-only
  / 179 delivered-only` per env — correctness of the categorization logic itself was
  proven separately against a scratch copy of `sqr.db` seeded with a synthetic override
  row and a synthetic custom-only row.
- `/admin/sqroverrides` — new admin page (stat cards + tabbed overridden/custom-only
  tables per environment).

### AI-Assisted Explanation — ✅ Complete
- `connectors/ai_tools.py`'s existing `sqr_program` tool now also returns indexed
  `source_text` (previously only metadata/tables/includes), truncated to 12,000 chars
  (`_truncate_source()`) to stay within a reasonable tool-result token budget —
  verified against the largest indexed program (`sysrtdfn.sqc`, 171,506 chars raw).
- New `cobol_program` tool (mirrors `sqr_program`'s shape: `program`/`table_users`/
  `search` lookup types, plus COBOL-specific `copy_deps`) — COBOL had no AI tool at
  all before this; same source-text truncation applied.
- With real source in the tool result, "explain/summarize/assess this program" falls
  out of the existing agentic tool loop for free — no new endpoint, no separate
  summarization pipeline. Verified live end-to-end against the real OpenAI-backed
  assistant (`/admin/assistant`): asked it to explain both `PTCALOGM.cbl` (COBOL) and
  `sysrtdfn.sqc` (SQR) — it correctly invoked the new/updated tools and produced
  accurate plain-English explanations matching the real source.

### Analytics Dashboards — ✅ Complete
- SQR already had `/admin/sqr/analytics` (top tables, most-complex programs, most-
  included SQCs, release breakdown) — pre-existing, no change.
- Added the COBOL equivalent: `connectors/cobol_db.py`'s `analytics()` (top tables,
  most-complex programs by table count, most-COPYd copybooks, delivered/custom
  breakdown), `GET /api/cobol/analytics`, and `/admin/cobol/analytics` (linked from
  the COBOL Explorer toolbar). Also added `/admin/cobol/table/{table_name}` (COBOL
  had `/api/cobol/table/{table_name}` already, but no admin page for it — SQR's
  equivalent page existed, COBOL's didn't).
- **Real finding, not a bug**: `top_tables` is empty for COBOL — `cobol_tables` has
  0 rows in this environment (verified: `SELECT COUNT(*) FROM cobol_tables` → 0),
  while `cobol_copies` (806 rows) and `cobol_calls` (328 rows) are populated. The
  page renders this honestly (empty table section) rather than erroring.
- **Bug found and fixed while adding this**: registering `/cobol/table/{table_name}`
  and `/cobol/analytics` *after* the existing `/cobol/{filename}` catch-all route
  caused FastAPI to match `/admin/cobol/analytics` against `/cobol/{filename}`
  (filename="analytics") first, since routes match in registration order — the new
  analytics page silently served the wrong content. Fixed by moving both new routes
  before the catch-all. Also fixed a small pre-existing bug copied from the SQR
  analytics page pattern: an undefined `$()` DOM helper (SQR's `/admin/sqr/table/
  {table_name}` page has the same latent bug, out of scope to fix here since it
  predates this work and isn't part of what broke).

### Broader Diff Modes — ✅ Complete
`envcompare_sqr()`/`envcompare_cobol()` gained a `diff_mode` parameter: `"exact"`
(unchanged, raw `content_hash` equality) or `"normalized"` (ignore comment lines and
insignificant whitespace). Normalized mode only re-checks pairs whose `content_hash`
already differs — an extra `source_text` fetch + comparison for just those rows — so
exact mode stays exactly as cheap as before. Comment-stripping reuses each parser's
own existing convention rather than inventing a new one: SQR's `!`-prefixed comment
lines (`sqrparser.py`'s `_RE_COMMENT_LINE`) and COBOL's fixed-format column-7 `*`
(`cobolparser.py`'s `_RE_COMMENT_LINE`). `/admin/sqrcompare` and `/admin/cobolcompare`
both got an "Exact match" / "Ignore whitespace/comments" toggle; the changed-files
table now labels whitespace/comment-only diffs distinctly (`DIFFERS (whitespace/
comments only)`) instead of just `DIFFERS`.

Since HCM/FSCM are byte-identical in this environment for both SQR and COBOL (no real
diffs to demonstrate against), verified correctness with scratch-DB tests (same
methodology as SQR Override Intelligence): cloned a real program into the other
environment's source tree with (a) an added comment line + trailing whitespace only
— confirmed normalized mode correctly reports `changed: false`, `content_normalized_
same: true`, while exact mode still reports `changed: true`; and (b) a genuine
non-comment token inserted mid-file — confirmed normalized mode still catches it
(`changed: true`, `content_normalized_same: false`). Repeated for both SQR (`!`
comments) and COBOL (column-7 `*` comments) source. Also verified live in a headless
browser: toggling to "Ignore whitespace/comments" on `/admin/sqrcompare` and calling
`load()` correctly re-fetches with `diff_mode=normalized` and renders real counts.

### Remaining
- Syntax-aware diffing (AST-level comparison, not just comment/whitespace
  normalization) — no concrete blocker, just a larger lift than this pass.
- Runtime correlation (tie Process Scheduler executions back to SQR/COBOL source) is
  Planned; no work started.

---

# Processing Sequence Intelligence

**Status: v1 + Record extension complete** (Component and Record contexts — see
Remaining for why Page was *not* given a mirrored "sequence").

Teaches the platform how PeopleSoft component/record processing executes in order,
not just which events exist.

### Completed — Component (v1)
- `/admin/compflow` (Component Event Flow) and `/admin/compseq` (PC Timeline): canonical
  20-event sequence (Search → Build → Interaction → Save) with delivered/custom
  detection and inline source viewing
- `connectors/peoplecode.py`: `CANONICAL_COMPONENT_SEQUENCE` + `component_sequence()` —
  moved the canonical sequence from a page-local JS array into a real, independently
  queryable backend artifact (`GET /api/peoplesoft/components/{comp}/sequence`)
- KG: `component_event` node type with `FIRES_BEFORE`/`FIRES_AFTER` edges between
  consecutive non-empty canonical events (`connectors/graphdb.py:component_sequences()`)
- AI: `component_events` tool fixed to call the real backing function (was calling a
  stale duplicate) and enriched with canonical sequence context
- Incident RCA (`/admin/rca`): correlates Process Failures, Log Errors, Oracle ASH, and
  IB Errors into one timeline

### Completed — Record + Page (extension, not a Component mirror)
Extending this to Page/Record was initially scoped as "give them the same sequence
Component has" — investigation (confirmed against live HCM/FSCM data) showed that's
wrong for Page and right, but differently-shaped, for Record:

- **Record** has a genuinely independent PeopleCode event set (`PSPCMPROG
  OBJECTID1=1` — Record Field PeopleCode: FieldDefault, FieldFormula, RowInit,
  RowSelect, FieldEdit, FieldChange, RowInsert, RowDelete, SaveEdit, SavePreChange,
  SavePostChange — owned by the record itself, independent of any component).
  `connectors/peoplecode.py`: `record_sequence()` reuses
  `CANONICAL_COMPONENT_SEQUENCE`'s real event vocabulary/order, filtered to only the
  events valid for record-owned code (excludes Component-only events like
  PreBuild/PostBuild/Activate/Workflow/SearchInit/SearchSave, which require a
  component context). `GET /api/peoplesoft/records/{rec}/sequence`. New "Processing
  Sequence" tab on the Record Explorer (`routers/admin/security.py`). KG:
  `record_event` node type with `FIRES_BEFORE`/`FIRES_AFTER` edges
  (`connectors/graphdb.py:record_sequences()`).
- **Page has no independent processing sequence** — `uom.py` already documents "Pages
  do not own PeopleCode directly; it is attached at the component level" for the
  events Component sequencing already covers. A synthetic "canonical Page sequence"
  would have been fake. What Page *does* have is a real, separate, currently-unindexed
  category: `OBJECTID1=8` ("Page" — already mapped in `peoplecode.py`'s
  `PEOPLECODE_OBJECT_TYPES` dict, but nothing queried it before this). Confirmed via
  live query this is 0 rows in both HCM and FSCM — real and queryable, just
  unpopulated here (same class of gap as several existing 0-row stub providers).
  `connectors/peoplecode.py`: `page_owned_events()` — a flat list (no multi-phase
  ordering, since there's no rich lifecycle at this level), gracefully returns empty
  rather than erroring. `GET /api/peoplesoft/pages/{page}/owned-events`. New
  "Page-Owned PeopleCode" tab on the Page Explorer (`routers/admin/platform.py`),
  clearly distinct from the existing per-component PeopleCode tab. **Not added to the
  KG in this pass** — 0 rows everywhere means nothing to verify the edge-building
  logic against; add a builder later if an environment has real `OBJECTID1=8` data.

**Verified**: `record_sequence('HCM', 'JOB')` correctly slots real Build/Interaction/
Save events and correctly excludes Search-phase Component-only events; graph rebuild
produced `record_event` nodes/edges with zero self-loops from the start (applied the
`component_sequences()` dedup fix proactively); `page_owned_events()` returns
`{"events": []}` gracefully for a real page, not an error. `make check` 91/91; smoke
test 69/69 (additions to existing pages, not new dedicated routes).

### Processing Path Explorer UI — ✅ Complete (Component + Record)
`/admin/compseq` ("PC Timeline") already had a rich ordered phase-card visualization
for Component sequences (grid of phase columns, per-slot delivered/custom/empty
coloring, inline source viewing) — the Record Explorer's "Processing Sequence" tab,
by contrast, only had a plain per-phase table. Added a Component/Record mode toggle
to `/admin/compseq` reusing the exact same visual language (phase cards, stats row,
legend, click-to-expand slots) for Record sequences too, rather than building a
separate page or a generic new visualization — `renderRecord()` consumes the
already-phased `record_sequence()` API response directly (no client-side canonical-
sequence re-derivation needed, unlike Component mode, since Record's backend already
groups events by phase). Record-mode slots show field/last-editor/timestamp metadata
on click (no source-code viewing — no per-event source endpoint exists for
record-owned PeopleCode, unlike Component's `/event-source`; the page says so
honestly rather than pretending).

**Verified live in a real headless browser** (not just curl): switched to Record
mode, entered `JOB`, confirmed 4 phase cards / 158 slots / 154-with-PeopleCode
render matching `record_sequence('HCM','JOB')` directly; clicked a populated slot
and confirmed the metadata panel opens with correct field/status; re-verified
Component mode (`JOB_DATA`) still renders identically post-change (20 slots, no
regression).

### AI-Assisted Sequence Explanation — ✅ Complete
Added `peoplecode_sequence` to `connectors/ai_tools.py` — a unified AI tool covering
Component/Record/Page ordering questions ("what fires before Save on JOB_DATA?", "is
FieldDefault in Build or Interaction phase?"), dispatching to the existing
`component_sequence()`/`record_sequence()`/`page_owned_events()` connector functions
by a `target_type` parameter rather than three separate tools. Complements the
existing `component_events` tool (flat listing, no ordering context) — this one is
specifically for ordering/sequence reasoning. No new chat UI needed: with real
canonical-sequence data in the tool result, ordering questions fall out of the
existing agentic tool loop for free, the same pattern used for SQR/COBOL explain.

**Verified live against the real OpenAI-backed assistant** (`/admin/assistant`, not
just dispatch()-level): asked "is FieldDefault in the Build phase or Interaction
phase?" for record JOB — correctly answered Build phase; asked "what fires
immediately before SaveEdit?" for component JOB_DATA — correctly answered RowDelete
(independently confirmed against `component_sequence('HCM','JOB_DATA')` directly:
Interaction Phase ends with RowDelete, Save Phase begins with SaveEdit).

### Remaining
- **Delivered vs Custom Sequence Comparison** beyond the existing `LASTUPDOPRID`
  heuristic — PeopleCode has no delivered-source baseline to diff against (unlike
  SQR/COBOL, which have real parallel delivered+custom trees)
- **Runtime Trace Correlation** tying processing sequence to live traces — blocked on
  the same missing-PIA-data issue as Phase 4's session tracking. Oracle ASH and
  AE/Process-Scheduler logs *are* populated and already power `/admin/rca`, so a
  narrower AE-focused (not PeopleCode-component-focused) trace slice is viable later.
- Broader Sequence-Aware Graph Relationships (`PART_OF_SEQUENCE`, `CALLS_DURING_EVENT`,
  `VALIDATES_BEFORE_SAVE`, `MUTATES_BUFFER`/`_DATABASE`, `BLOCKS_PROCESSING`,
  `TRIGGERS_RUNTIME_ACTION`) — `FIRES_BEFORE`/`FIRES_AFTER` are done; these others
  aren't started.

---

# Digital Twin Persistence

**Status: Foundational pieces complete; full vision open-ended.**

### Completed
- Knowledge Graph snapshots (creation, listing, comparison, scheduled daily builds,
  retention pruning); graph drift detection against snapshot baseline
- Incident recording with full runtime state capture (see Phase 4)
- Environment/security change history via drift time series (see Phase 6)

### Remaining
- Full change history across all object types (drift covers 17 types, not universal)
- Deployment/configuration history beyond the promotion event log
- Runtime replay beyond incident snapshots
- Architecture Assistant: auto-generated dependency reports, sequence diagrams,
  technical documentation, impact summaries — not started

---

# Long-Term Goals

PeopleSoft Hypergraph Intelligence should become the definitive engineering,
observability, and operational intelligence platform for PeopleSoft environments.

---

## Provider methodology (for adding new UOM/KG providers)

1. Query `all_tab_columns` to find the real table/column names — never assume
   PeopleTools naming conventions.
2. Pull live sample rows to confirm usable keys and human-readable content.
3. Write `psdb.py` → `ptmetadata.py` → `graphdb.py` → `uom.py` →
   `routers/peoplesoft.py` → `routers/admin/<group>.py`, in that order.
4. Compile-check and smoke-test at each layer before proceeding.
5. Verify against a real graph rebuild (`curl /api/graph/build`) and inspect
   `graph["providers"][].status` — a clean compile does not mean the SQL runs
   correctly. Several real bugs this project has hit were only caught this way.
6. Document deprioritization reasons in the table above when a table is unimplementable
   in this environment.
