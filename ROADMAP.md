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
- Environment Compare (23 object types) with scheduled drift alerts
- Runtime Monitor: Oracle ASH, runtime alerts, App Server domain + live process tracking,
  AE-focused process trace correlation
- SQL Workspace with autocomplete, typed binds, timeout/cancellation
- Integration Broker, Identity/Security, Portal, SQL/Query/Tree/Menu/Component Interface explorers
- AI Engineering Assistant (Claude/OpenAI/Ollama) with 21+ tools
- Log Intelligence: PIA/APPSRV/Tuxedo/nginx/F5/IGW/PRCS-AE ingestion pipeline
- SQR + COBOL source artifact intelligence (index, search, dependency graphs, env
  comparison with normalized diff mode, analytics, override intelligence)
- Plugin SDK v1 + v2 (object/graph/runtime providers, health checks, config-driven
  sources, admin pages) — no open candidates
- SQL Proxy: AI-safe deterministic data masking, ad-hoc `execute_sql` tool, human
  token-reveal endpoint/UI — the AI queries live data but only ever sees masked
  tokens, never real PII
- Universal Root-Cause Diagnostics: systematic cross-subsystem investigation
  method (PeopleCode/SQL/SQR/COBOL/IB/data) ending in an explicit code-vs-data
  verdict and a concrete fix recommendation, escalating to live server trace
  analysis when logic and data inspection alone are inconclusive
- Admin shell smoke test harness (73 pages)

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
- 23-type environment comparison (records, fields, components, pages, permissions,
  roles, AE, PeopleCode, SQL defs, portals, queries, menus, trees, IB routings, IB
  messages, component interfaces, process definitions, operators, translate values,
  IB nodes, style sheets, URL definitions, application packages) with AE step-level
  body diff
- Scheduled drift snapshots (SQLite `driftdb.py`) with threshold + growth-rate alerts
- Point-in-time runtime snapshots and drift history time series (`/admin/drift`)
- Deployment risk scoring (`/api/impact/risk`) and project impact reports
  (`/api/impact/project`, `/admin/impact`)
- Promotion event log (Phase 1): manual `POST /api/promotions` + timeline UI
  (`/admin/promotions`)

**Drift coverage expansion (17 → 23 types)**: `connectors/envcompare.py`'s `summary()`
is a single literal `(label, sql)` tuple list — purely additive, no UI changes needed
since `/admin/drift` renders whatever `/api/drift/latest` returns generically. Added
Operators (`PSOPRDEFN`), Translate Values (`PSXLATITEM`), IB Nodes (`PSMSGNODEDEFN`),
Style Sheets (`PSSTYLEDEFN`), URL Definitions (`PSURLDEFN`), and Application Packages
(`PSPACKAGEDEFN`) — each verified queryable with real, differing HCM/FSCM counts
before adding (e.g. Operators: 141 vs 398; Translate Values: 49,177 vs 60,749) rather
than assumed from UOM's ~54-type provider list. Two other UOM-adjacent candidates,
`PSFILELAYOUTDEFN` and `PSPRJDEFN`, were checked and don't exist under those names in
this environment (`ORA-00942`) — skipped rather than guessed at the real table name.
Since `/api/drift/latest` reads a **persisted** snapshot (not a live query), a fresh
`POST /api/drift/snapshot` had to be triggered to pick up the new types — pre-existing
snapshots only have the original 17.

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
`ai_<name>.py` file. 21+ tools in `connectors/ai_tools.py`, each a thin adapter over an
existing connector (no new SQL): `search_objects`, `peoplecode_search`,
`graph_dependencies`, `graph_impact`, `who_has_access`, `ae_steps`, `sql_lookup`,
`envcompare_summary`, `project_impact`, `active_sessions`, `record_usage`,
`log_search`, `log_errors`, `session_log_chain`, `environment_health`,
`ib_diagnostics`, `process_scheduler_health`, `component_events` (now enriched with
canonical processing-sequence context), `sqr_program`, `cobol_program` (source-aware,
truncated to 12,000 chars — feeds "explain this program" questions), and
`peoplecode_sequence` (unified Component/Record/Page ordering questions). Streaming
chat UI at `/admin/assistant` with an agentic tool loop (up to 8 rounds).

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

**Status: ✅ v1 + v2 complete — no remaining candidates.**

Every extension surface (object providers, KG builders, runtime providers, admin
dashboards, health checks, config-driven ingest sources) was previously a hardcoded
literal list/dict/if-chain only core code could append to. `connectors/plugins.py`
adds one appendable registry per surface; `connectors/pluginloader.py` discovers and
loads `plugins/*.py` at startup with per-plugin isolation (a broken plugin logs a
warning and is skipped — verified the rest of the platform keeps working).
`plugins/example_hello.py` is a worked example exercising all six extension points.
Full SDK documentation in `PLUGINS.md`.

**Custom health checks**: `register_health_check(name, check_fn, label)` — distinct
from a runtime provider (raw status data for a human to read) in that a health check
returns a judgment (`ok`/`warn`/`error`) a dashboard can roll up or alert on. New
`GET /api/runtime/health-checks?env=` runs every registered check on demand (same
isolation contract as the rest of the SDK — a check that raises is reported as its
own `error` result, not a failed endpoint); new "Plugin Health Checks" card on
`/admin/runtime` (no per-check UI work needed, same as the existing Plugin Providers
card). `example_hello.py`'s worked example deliberately returns a real, non-trivial
`warn` (one of its three demo widgets, `CHARLIE`, is genuinely marked degraded) rather
than an always-`ok` stub — verified live via curl (`{"status": "warn", "message": "1
widget(s) degraded: CHARLIE"}`) and in a real headless Chrome session (card renders
correctly, zero console errors).

**Config-driven source API**: `register_source_type(name, config_key, ingest_fn,
status_fn)` replicates the SQR/COBOL ingest pattern (a `config.json` array of source
entries + an SSH-fetch-and-index pipeline) without a plugin needing to hand-roll its
own background-thread/lock/status-tracking boilerplate — the SDK runs `ingest_fn()`
in a background thread and tracks running/last-result generically. New
`routers/plugin_sources.py`: `GET /api/plugins/sources` (list registered types), `GET
/api/plugins/sources/{name}/entries?env=` (this type's config.json entries), `POST
/api/plugins/sources/{name}/ingest` (trigger background reindex), `GET
/api/plugins/sources/{name}/status`. `example_hello.py`'s worked example
(`hello_widgets` source type) increments a real counter each ingest rather than
returning a static stub — verified live via curl: `source_count: 0` correctly since
`hello_sources` isn't in `config.json` (honest, not an error), two separate `POST
.../ingest` calls correctly ran in background threads and `ingest_count` incremented
1 → 2 across them, and a request to an unregistered source type correctly 404s.

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

### Runtime Correlation — ✅ Complete (gracefully degrading, no real data to verify against)
Ties Process Scheduler executions back to SQR/COBOL source: `psdb.process_runs_for_program()`
queries `PSPRCSRQST` by `PRCSNAME` (derived from the source filename's base name) and
`PRCSTYPE` (`SQR Report`/`SQR Process` for SQR, `COBOL SQL` for COBOL), reusing the
`_RUNSTATUS_LABEL` map and column-existence detection already established by
`operator_processes()`. New `GET /api/sqr/program/{filename}/runs` and `GET
/api/cobol/program/{filename}/runs`; new "Process Runs" tab on both program detail
admin pages showing instance/run-control/start-time/duration/status/server/OPRID.

**Verified this was worth building despite zero real data before writing any code**:
researched via a background agent first — `PS_PRCSDEFN` confirms the join key
(`PRCSNAME`) is real (1510 SQR Report + 21 SQR Process + 52 COBOL SQL defs in HCM
alone), but `PSPRCSRQST` (actual run history) has **zero rows** for those `PRCSTYPE`
values in either HCM or FSCM — every real run-history row there is Application
Engine only. Confirmed with the user this is worth building anyway (same call as
Page-owned PeopleCode): the query mechanics are real and will activate automatically
the moment an environment has real SQR/COBOL run history, so it's verified two ways
— (1) gracefully empty for real SQR/COBOL programs today (not an error), and (2)
proven correct against a real *populated* process name (`PSPM_REAPER`, Application
Engine, 512 real runs) to confirm the SQL/dispatch logic itself works, not just that
it always returns nothing.

**Bug found and fixed**: `duration_secs` (computed as `end_dt - run_dt`) was always
`None` even for completed runs with both timestamps populated — `psdb.query()`
returns Oracle datetimes as ISO strings, not Python `datetime` objects, so the
subtraction silently raised `TypeError` inside a bare `except: pass`. Fixed by
parsing both timestamps with `datetime.fromisoformat()` before subtracting;
re-verified against `PSPM_REAPER`'s real runs (31.2s, 29.5s durations, correctly
`None` for the still-running instance with no `end_dt`).

**Bigger bug found and fixed, pre-existing before this session**: while wiring up
COBOL's new tab, `cobol_detail`'s entire JS (not just the new tab — Dependency Graph
and Source too) turned out to already be broken in a way identical to the SQR
Overrides brace-doubling bug from earlier this session, just never caught: the
segment after `""" + _ESC_JS + """` is a plain string, not an f-string, but the code
used `{filename!r}` (three times) expecting f-string evaluation — it never
evaluated, emitting the literal text `{filename!r}` into served JavaScript and
breaking it outright. `git show HEAD` confirmed this predates all of today's
session work; it was never caught because individual object detail pages
(`/admin/cobol/{filename}`) aren't in the smoke test's page list, only list/compare
pages are. Fixed by precomputing `filename_js = json.dumps(filename)` and
concatenating it in (matching the established `+ variable +` convention used
elsewhere in this file), and de-doubling every brace in that segment to match its
actual plain-string nature. Verified all three previously-broken tabs (Overview
was fine; Dependency Graph, Source, and the new Process Runs) now render real data
with zero console errors in a real headless Chrome session.

### Remaining
- Syntax-aware diffing (AST-level comparison, not just comment/whitespace
  normalization) — no concrete blocker, just a larger lift than this pass.

---

# Phase 11 — SQL Proxy: AI-Safe Data Access

**Status: ✅ v1 complete (steps 1-4).**

## Why

The AI Assistant (Phase 7) could previously only reason about *metadata* — object
definitions, dependencies, log errors, runtime state — but every one of its tools
wrapped a fixed, pre-written query. It couldn't ask its own ad-hoc question of the
data (e.g. "show me the actual JOB rows for employees where this Application
Engine step failed"). That was a real gap: diagnosing whether an incident is
*program-related* (a bug in delivered/custom code) or *data-related* (a bad row,
an out-of-range value, a broken foreign key) usually requires looking at the data
itself, not just the schema.

The blocker to closing that gap isn't capability, it's exposure: PeopleSoft data
is full of PII/PHI/financial data (`PS_PERSONAL_DATA`, `PS_JOB`, `PS_PAYCHECK`,
`PS_BENEFITS`, ...), and hosting-provider AI models should never see raw employee
names, SSNs, salaries, or emails. `SQL_PROXY.md` (repo root) sketches an idealized
architecture for this: every AI SQL request flows through a proxy that validates,
executes, and *deterministically masks* the result before the AI ever sees it — the
same employee always maps to the same masked token everywhere, so cross-table
joins/troubleshooting still work, but the AI never learns who the employee
actually is. A human operator can then decode a specific masked token back to the
real value to act on the finding.

## What already exists that this builds on (not a from-scratch build)

`SQL_PROXY.md`'s design reads as if the read-only-execution/validation/audit layer
needs to be built. It doesn't — `connectors/sqlws.py` (SQL Workspace, the existing
human-facing query tool at `/admin/sqlws`) already implements almost the entire
"Query Validation," "Read Only," "Automatic Row Limiting," and "Query Audit
Logging" sections of `SQL_PROXY.md`, in production:

- `validate_readonly()` — blocks all DML/DDL/PL·SQL, rejects `DBMS_*`/`UTL_*`
  package calls, `EXECUTE IMMEDIATE` dynamic SQL, `SYS.*` privilege-escalation
  patterns, and multi-statement submissions — comment/string-literal-stripped
  before keyword scanning, not naive substring matching.
- `execute_query()` — `ROW_NUMBER()`-wrapper paging (never loads unbounded result
  sets), bind-variable support, server-side timeout, cancellation.
- `audit_write()` / `logs/sqlws_audit.jsonl` — every execution and every blocked
  attempt logged with timestamp, env, SQL text, elapsed time, row count, status.

This phase reuses that validation/execution/audit path as-is and adds only a
masking layer between "query executed" and "AI sees the result" — the piece
`SQL_PROXY.md` calls "Deterministic Data Masking."

## What's built (steps 1-3; step 4 below)

- **Step 1 — Deterministic masking engine** (`connectors/sqlmask.py`): a
  configurable sensitive-column catalog (`config.json["sql_proxy"]`, seeded from
  `SQL_PROXY.md`'s own Token Categories table) drives `TOKEN = PREFIX + "_" +
  HMAC-SHA256(secret_salt, value)[:8]` — HMAC (not plain concatenation) so the
  salt can't be brute-forced out of a leaked token set. Deterministic: the same
  real value always produces the same token, so `PS_PERSONAL_DATA`/`PS_JOB`/
  `PS_BENEFITS` rows for the same employee mask to the *same* `EMP_xxxxxxxx`
  token — cross-table joins/reasoning stay possible for the AI, it just never
  learns the real identity. A SQLite token vault (`data/sql_proxy_vault.db`,
  mirroring the `data/*.db` side-store convention already used by
  `driftdb.py`/`incidentdb.py`) stores the mapping, populated lazily. Non-
  sensitive columns (dates, statuses, counts) pass through untouched.
- **Step 2 — AI-facing `execute_sql` tool** (`connectors/ai_tools.py`): reuses
  `sqlws.execute_query()` unchanged (same validation/paging, now with a
  `source="ai"`/`"human"` tag threaded through so the one audit trail
  distinguishes who/what ran a query), then masks the result before returning it
  to the AI. Tighter `max_rows` cap (50 vs. the human Workspace's 100-1000
  default) — the AI needs enough rows to spot a pattern, not a full dump.
- **Step 3 — Human reveal capability** (`routers/sql_proxy.py`): `POST
  /api/sql-proxy/reveal` decodes a token back to its real value (audit-logged);
  `GET /api/sql-proxy/stats` for vault introspection (counts only, never values).
  Structurally unreachable from AI — `ai_tools._HANDLERS` has no entry that
  reaches `sqlmask.reveal()`, confirmed directly (not just a permission check
  that could be bypassed by a prompt). A clickable "token chip" UI on
  `/admin/assistant` lets a human reveal a masked token inline in the chat —
  the concrete answer to "the AI reports where the problem is, the user sees
  the actual data."

**Verified end-to-end against the real OpenAI-backed assistant** (not just
dispatch-level tests): asked it to investigate `PS_PERSONAL_DATA` via
`execute_sql`; it correctly executed the query and reported back *only* masked
tokens (`EMP_6ef9f65d`, `PERSON_...`), explicitly noting they were masked for
privacy — it never saw a real name or EMPLID. Separately called `POST
/api/sql-proxy/reveal` with that exact token and got the real value back
(`AA0001`) — the full "AI sees masked, human sees real" loop working with real
data, not synthetic test fixtures. Also verified: determinism/non-collision (8
unit tests, `tests/test_sqlmask.py`), `validate_readonly()`'s existing blocked-
statement test coverage unaffected (`tests/test_sqlws_timeout.py` still 19/19
passing overall), and the AI dispatch table confirmed to have zero path to
`sqlmask.reveal()`.

**Two bugs found and fixed while building the reveal-chip UI**, both caught by
headless-Chrome testing rather than assumed correct:
1. `routers/admin/tools.py`'s `admin_assistant()` content is one continuous
   f-string (unlike most admin pages' three-part `f"""...""" + _ESC_JS + """..."""`
   convention) — the new `TOKEN_PATTERN` regex used `\b` and `{8}` unescaped,
   which Python silently mangled (`\b` is a real Python backspace escape;
   `{8}` was evaluated as an f-string expression) before ever reaching the
   browser. The regex simply never matched anything until fixed to `\\b`/`{{8}}`.
2. A JS closure bug: `chip.onclick = () => revealToken(chip, m[0])` captured the
   loop variable `m` by reference, not its value at chip-creation time — by
   click time `m` was `null` (the last `regex.exec()` call in the `while` loop),
   throwing `Cannot read properties of null`. Fixed by copying `m[0]` into a
   local `const` before advancing the loop.

## Step 4 — Workflow integration — ✅ Complete (built as part of Phase 12)

The remaining piece of this phase — teaching the assistant to reach for
`execute_sql` specifically when triaging an error, rather than relying on the
model to make that connection unprompted — turned out to be exactly what
Phase 12's "Root Cause Investigation Method" delivers: its step 3
(`routers/assistant.py`'s `_SYSTEM`) explicitly instructs "check the data
itself when a data-side explanation is plausible, using `execute_sql`" as
part of a systematic identify-subsystems → inspect-logic → check-data →
verdict method, not a bolt-on afterthought.

This isn't a re-statement of intent — it's already verified live, twice, in
Phase 12's own testing: the `JOB_DATA`/`DEPTID` investigation chained
`record_usage` → `component_events` → `peoplecode_search` → `execute_sql`
unprompted, and the `PRCSYSPURGE` investigation chained `ae_steps` →
`sqr_program`/`cobol_program` → (on the next turn) three `execute_sql` calls
— in both cases the model reached for `execute_sql` on its own once logic
inspection alone wasn't conclusive, which is precisely what step 4 asked
for. See Phase 12's "Verification" section for the full transcripts.

## Explicitly out of scope (unchanged from original plan, not required for v1)

- Free-text field masking (`COMMENTS`/`DESCRLONG`/`MESSAGE_TEXT` — named-entity
  masking is materially harder than column-based tokenization), numeric range-
  bucketing/date-shifting, Dynamic Policy Engine/YAML policies, AI Trust Levels
  (Observer/Analyst/Engineer/Administrator), Oracle Data Safe integration — all
  explicitly listed as "Future Enhancements" in `SQL_PROXY.md` itself.

---

# Phase 12 — Universal Root-Cause Diagnostics

**Status: ✅ Core capability complete — verified end-to-end against a real
mixed code/data scenario.**

## Why

The user's ask, verbatim: *"The AI Agent should be able to answer ANY question
about anything in the system. If the AI Agent is asked to investigate any
problem or error it should be able to examine every piece of logic (PeopleCode,
SQL, SQR, COBOL, IB Messaging, anything literally) and the data itself and
determine what the problem is. It should tell the user that info. It should
also instruct the user how to resolve the issue, whether it is with data or
code."* See `ARCHITECTURE.md`'s "Universal Diagnostic Capability" section for
the corresponding design-principle-level statement of this mandate.

## What was already true before this phase

Almost every piece this mandate requires already existed as an individual AI
tool (`connectors/ai_tools.py`): `peoplecode_search`/`component_events`/
`peoplecode_sequence` (PeopleCode), `sql_lookup` (SQL definitions),
`sqr_program` (SQR), `cobol_program` (COBOL), `ib_diagnostics` (Integration
Broker), `ae_steps` (Application Engine), `search_objects`/`graph_dependencies`/
`graph_impact` (general object metadata), and — as of Phase 11 —
`execute_sql` (the data itself, safely, through the masking layer). The gap
was never tool *coverage*; it was that the assistant's system prompt
(`routers/assistant.py`'s `_SYSTEM`) had no section instructing a systematic
cross-subsystem investigation method, and didn't even mention three of the
newer tools (`cobol_program`, `execute_sql`, `peoplecode_sequence`) despite
them being fully registered and functional.

## What was built

Added a "Root Cause Investigation Method" section to `_SYSTEM` instructing the
assistant, when investigating any reported problem or error, to:

1. Identify which subsystem(s) are plausibly implicated (PeopleCode/component
   event, SQL/AE step, SQR/COBOL batch program, Integration Broker message,
   or the data itself) rather than defaulting to only one.
2. Inspect the relevant logic using the matching tool(s) —
   `peoplecode_search`/`component_events`/`peoplecode_sequence` for PeopleCode,
   `sql_lookup`/`ae_steps` for SQL/AE, `sqr_program`/`cobol_program` for batch
   programs, `ib_diagnostics` for integration failures.
3. Check the data itself with `execute_sql` when a data-side explanation is
   plausible (bad/missing/out-of-range values, orphaned keys) — not just the
   schema shape.
4. Synthesize an explicit **verdict**: code, data, or both/inconclusive —
   never leave the user with facts and no conclusion.
5. Give a **concrete recommendation** matched to the verdict: a code fix
   (which program, which event, what's wrong) or a data fix (which
   record — by its masked token — and what value is wrong), not a generic
   "you may want to check X."

Also added `cobol_program` and `execute_sql` tool-usage guidance to the system
prompt (previously entirely absent despite both tools being registered and
working) and cross-referenced `peoplecode_sequence` alongside the existing
`component_events` guidance for ordering-specific questions.

## Verification

Ran two real investigations against the live OpenAI-backed assistant (not
scripted/mocked conversations):

1. **Mixed PeopleCode + data scenario**: described a plausible symptom
   ("some employees have incorrect `JOB_DATA` records — missing/invalid
   department assignments"). The assistant — unprompted, using only its
   system-prompt guidance — chained `record_usage` → `component_events` →
   `peoplecode_search` → `execute_sql`, reached an explicit verdict
   ("likely not a systematic PeopleCode/application logic error," based on
   a real query confirming zero `PS_JOB` rows have a NULL `DEPTID`), and gave
   concrete recommendations. It never saw a real EMPLID or name.
2. **Batch-program scenario**: asked it to investigate the `PRCSYSPURGE`
   Application Engine program across two conversation turns. First turn
   chained `ae_steps` → `sqr_program` (search) → `cobol_program` (search) to
   explain the program's real logic. Second turn (user said "proceed and
   check the data") chained three `execute_sql` calls against real
   `PSPRCSRQST`/`PSBATCHAUTH`/`PSSERVERSTAT` data, correctly distinguishing a
   real finding (0 rows old enough to purge) from its own wrong column-name
   guesses (honestly flagged as likely-wrong-schema rather than silently
   fabricating a plausible-sounding answer).

**Bug found via the AI's own real tool_log, not manual testing**: the second
scenario's first `ae_steps` call came back with `"error": "module
'connectors.ae' has no attribute 'ae_steps'"` — `connectors/ai_tools.py`'s
`_ae_steps` handler called a function name (`ae_conn.ae_steps`) that has
never existed; the real function is `ae_conn.steps()`, with a completely
different return shape (`{"items": [...], "warnings": [...]}` keyed by
`ae_section`/`ae_step`/`action_type_label`, not `ae_action`/`action_type`).
This means the `ae_steps` AI tool had silently returned an error on every
invocation since it was first added — never caught before because nothing
had exercised it against a real investigation until this session's testing.
Fixed to call the real `steps()` function and merge in step-level SQL text
via the separate `ae_sql_step_text()` lookup (matching the tool's original
stated purpose: step key + action type + first 200 chars of SQL). Re-ran the
same investigation after the fix — `ae_steps` returned 16 real steps with
correct SQL previews, and the model explained the program's actual logic
correctly.

## Trace-Assisted Diagnostics — ✅ Complete

Closes the last gap in the diagnostic method: when code and data inspection
are both inconclusive, the assistant can now instruct the user how to enable
a live PeopleSoft server trace, then locate and read the resulting trace
file(s) itself as further evidence, rather than stopping at "here's how to
get more data."

- **Confirmed real infrastructure before building anything**, per this
  session's established discipline: live SSH inspection of
  `psappsrv.cfg`'s `[Trace]` section confirmed `TraceSql=0`/`TracePC=0`
  (tracing genuinely off by default, as expected), that no `TraceDir` is
  configured so trace files land in the same domain `LOGS` directory that
  already holds `APPSRV_*.LOG` files, and that both the HCM (`HCMDMO_APP`)
  and FSCM (`FSCMDMO_APP`) app server domains are reachable via the existing
  `hcm_appserver` SSH host.
- New `connectors/traceconn.py`: `trace_config(env)` reads the *live*
  `TraceSql`/`TracePC`/mask values from `psappsrv.cfg` (so instructions are
  always correct for the current state, never a stale assumption),
  `list_trace_files(env, pattern)` lists `*.tracesql`/`*.tracepc` files (an
  empty result is a legitimate, common outcome — tracing not yet enabled or
  reproduced — not a tool failure), `read_trace_file(env, filename)` reads
  content via the existing `sshclient` connector.
- **Deliberately no bespoke trace-file-format parser** — PeopleTools SQL/
  PeopleCode trace text is dense but genuinely human/LLM-readable
  (`Sql:`/`Bind-n:` lines, PeopleCode statement lines), and zero real trace
  samples exist in this environment to build/verify a parser against
  (`TraceSql=0` by default). Raw truncated text is handed to the AI to read
  directly — the same pattern already used for source code via
  `peoplecode_search`/`sqr_program`/`cobol_program` — rather than risking an
  unverified parser.
- New AI tools: `trace_status`, `list_trace_files`, `read_trace_file`. New
  system-prompt step 6 in the Root Cause Investigation Method: after steps
  1-4 (identify subsystems, inspect logic, check data, reach for a verdict)
  are inconclusive, check live trace config, give the user exact real
  instructions (file path + bitfield values), wait for reproduction, locate
  and read the resulting trace, then return to the verdict step with that
  new evidence.
- New `config.json["trace_sources"]` (mirrors the `sqr_sources`/
  `cobol_sources`/`log_sources` convention): per-env `ssh_host`, `trace_dir`,
  `cfg_path`.

**Verified with two real, unscripted multi-turn conversations** against the
live OpenAI-backed assistant: (1) described a "we've exhausted code and data
investigation" scenario — the assistant called `trace_status`, then gave the
exact real config file path with correct bitfield values (`TraceSql=3` — bit
1 "SQL statements" + bit 2 "SQL statement variables", i.e. see the query and
its actual bind values; `TracePC=2048` — the value the config file's own
comments literally mark "(recommended)"), and correctly explained the
dynamic-change/domain-wide tradeoff and to revert afterward. (A first draft
of this guidance had an arithmetic mistake — `1032` instead of the correct
`1+2=3` — caught and fixed before commit.) (2) A follow-up turn where the
user claimed to have reproduced the issue: the assistant called
`list_trace_files`, got a real empty result (honest — tracing isn't actually
enabled in this demo environment), and correctly asked the user to confirm
rather than fabricating trace content.

## Remaining

- This phase closes the *capability* gap (every subsystem is reachable, the
  method is systematic, verdicts are explicit, and trace-level evidence is
  reachable as a last resort). It does not add new subsystem coverage beyond
  what already existed — if a genuinely new logic type is added to the
  platform in the future (e.g. a new integration type), it must get an AI
  tool at the same time it gets a UOM provider, per `ARCHITECTURE.md`'s
  mandate, or this phase's guarantee quietly erodes.
- `_MAX_TOOL_ROUNDS = 8` in `routers/assistant.py` caps how many tool calls one
  investigation can chain — adequate for the scenarios tested so far; a
  genuinely deep multi-subsystem investigation (e.g. PeopleCode → SQR →
  data → IB → trace) could in principle need more rounds. Not raised in this
  phase since no real investigation has hit the cap; revisit if one does.
- No real trace file has ever been generated in this environment (tracing is
  off by default) — the file-locating/reading mechanics are verified against
  real SSH infrastructure and real non-trace files in the same directory,
  but the trace-content-reading step itself has only been verified for
  graceful-empty, not against a real populated trace file. If this matters,
  enable tracing once, reproduce a real request, and re-verify
  `read_trace_file` against genuine trace content.

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

### AE-Focused Runtime Trace Slice — ✅ Complete
The narrower, unblocked half of "Runtime Trace Correlation": `execution.instance_trace()`
composes what's already real and queryable for a single Process Scheduler instance —
`PSPRCSRQST` run detail, the AE program definition (`ae.program()`, if this instance is
an Application Engine run), Oracle ASH wait events/top SQL correlated to the run window
(reusing the existing `oracle_ash_for_process()`, which already filters by PSAE
module/action), and log errors within the run window (`logdb.query_errors()`). New
`GET /api/runtime/process/{instance}/trace`; new "AE / Log Errors" tab on the process
detail panel (`/admin/runtime`), alongside the pre-existing Oracle ASH and Exec Log
tabs (left untouched — the ASH view there already covered that ground well; this adds
the AE program description and correlated log errors that weren't shown anywhere).

**Deliberately does not claim step-by-step AE execution timing** — no
`PSAERUNCNTL`/`PS_AE_TRACE`/`PSAEMSGLOG` table is present or queryable in this
environment (confirmed via research before building), so that narrower "which step
ran when" view isn't attempted or faked; this composes what's real, not a simulation
of what isn't.

**Verified live** against a real 6.6-hour Application Engine run (`PRCSYSPURGE`,
instance 606596): correct AE program description ("Prcs Rqst & Rpt Mgr Purge"), real
ASH wait events (`db file sequential read`, 100%) with real top SQL text (`SELECT
AE_MESSAGE_PARMS FROM PSAESTEPMSGDEFN...`) correlated to the run window — a short
~15s `PSPM_REAPER` run was tried first and correctly showed 0 ASH samples (thin
sample density for short runs, not a bug), so a longer-running instance was used to
prove the correlation logic itself works. Verified live in a real headless Chrome
session: the new tab renders correctly with zero console errors, and the
pre-existing ASH/Exec Log tabs show no regression.

### Sequence-Aware Graph Relationships — ✅ Partially complete (the semantically-groundable half)
Added `VALIDATES_BEFORE_SAVE`, `MUTATES_DATABASE`, and `MUTATES_BUFFER` edges to
`component_sequences()`/`record_sequences()`, alongside the existing `FIRES_BEFORE`/
`FIRES_AFTER`/`BELONGS_TO`. `connectors/peoplecode.py`'s new `event_semantic_edges()`
classifies each canonical event by its own already-documented PeopleTools semantics
(the same meaning already captured in each event's `note` field, e.g. SavePreChange/
SavePostChange are literally "before/after DB write") — not a new or fabricated
classification, just wiring existing knowledge into the graph as edges: `SaveEdit` →
`VALIDATES_BEFORE_SAVE`, `SavePreChange`/`SavePostChange` → `MUTATES_DATABASE`, and
the Build/Interaction-phase buffer-mutating events (`RowInit`, `FieldDefault`,
`FieldFormula`, `RowSelect`, `FieldEdit`, `FieldChange`, `RowInsert`, `RowDelete`) →
`MUTATES_BUFFER`.

`PART_OF_SEQUENCE`, `CALLS_DURING_EVENT`, `BLOCKS_PROCESSING`, and
`TRIGGERS_RUNTIME_ACTION` remain unbuilt — each would need data this platform doesn't
track (a real PeopleCode call graph, workflow-trigger detection, or save-failure/
error-path data), not just a classification of what's already known, so they weren't
attempted rather than faked.

**Verified**: full graph rebuild (`env=HCM, limit=50, persist=true`) — both providers
ran clean (`component_sequences`: 38 items, `record_sequences`: 29 items, zero
errors); directly inspected the persisted graph (`data/knowledge_graph_HCM.json`) and
confirmed 49 real semantic edges (38 `MUTATES_BUFFER`, 8 `VALIDATES_BEFORE_SAVE`, 3
`MUTATES_DATABASE`) correctly connecting real `component_event` nodes to their real
`component` nodes, zero self-loops.

### Remaining
- **Delivered vs Custom Sequence Comparison** beyond the existing `LASTUPDOPRID`
  heuristic — PeopleCode has no delivered-source baseline to diff against (unlike
  SQR/COBOL, which have real parallel delivered+custom trees)
- True step-by-step AE execution timing — blocked on no `PSAERUNCNTL`/`PS_AE_TRACE`/
  `PSAEMSGLOG` table being present in this environment; PeopleCode-component-level
  trace correlation remains blocked on the same missing-PIA-data issue as Phase 4's
  session tracking
- `PART_OF_SEQUENCE`, `CALLS_DURING_EVENT`, `BLOCKS_PROCESSING`,
  `TRIGGERS_RUNTIME_ACTION` — blocked on call-graph/workflow-trigger/error-path data
  this platform doesn't track (see above)

---

# Phase 13 — Upgrade Automation: Customization Retrofit

**Status: 📋 Theorized — game plan below, nothing built yet. This section is a
plan to be reviewed and approved before any implementation starts, not a
description of existing capability.**

## The real problem

Every PeopleSoft shop periodically re-bases onto a newer PeopleTools release, a
newer application release (a PUM/Update Image or a full upgrade), or both at
once. Oracle delivers the new baseline; the customer's environment has
diverged from the *old* baseline via customizations (custom fields on
delivered pages, custom PeopleCode bolted onto delivered events, custom SQR/
COBOL overrides, custom Application Engine steps, security customizations).
Upgrading means reconciling three versions of every touched object — **my
current customized object**, **the old delivered baseline it was customized
from**, and **the new delivered baseline it must move to** — and deciding,
per object, whether the customization still applies cleanly, needs to be
re-positioned because the delivered structure shifted, or needs to be
re-thought because Oracle solved the same problem differently upstream.

Today this is done by hand with Oracle's own tools (Application Designer's
Upgrade → Compare and Report, Change Assistant) plus a lot of institutional
memory about which objects were customized and why. It's slow, expert-
dependent, and error-prone — a missed retrofit silently reverts a
customization; a wrong retrofit corrupts a delivered structure.

## Why this is hard — three distinct hard problems, not one

1. **Customization detection is already fuzzy today, at any single point in
   time.** This platform already has to solve "is this delivered or
   customized" for individual object types (the `LASTUPDOPRID not in
   _DELIVERED_OPRIDS` heuristic in `connectors/peoplecode.py`, the SQR/COBOL
   `overridden`/`custom-only`/`delivered-only` classification in
   `sqrdb.override_summary()`). An upgrade retrofit needs this at *every*
   customizable object type at once (pages, records, fields, PeopleCode,
   Application Packages, Component Interfaces, permission lists/menus,
   Application Engine, SQR, COBOL) — and the heuristic itself is imperfect
   (a customer OPRID that happens to match a delivered pattern, or delivered
   objects a customer re-saved without changing, both fool a naive check).
2. **The upstream baseline moves too — a 2-way diff is the wrong shape.**
   The user's framing is exactly right: "metadata structures change in the
   upstream." A customer's custom field inserted at page-field position 15
   is meaningless to blindly reapply if the new delivered page has 6 new
   fields inserted before position 15 — positions shifted, occurs levels may
   have changed, the field the customization was anchored to may have been
   renamed or removed entirely. The only correct comparison is a **3-way
   diff**: mine vs. old-delivered vs. new-delivered, the same shape a
   version-control merge uses (common ancestor + two divergent branches) —
   not the 2-way `envcompare.py`/SQR-COBOL-compare pattern this platform
   already has, which only ever compares two live environments to each
   other, never a customer environment against two different points in a
   vendor's release timeline.
3. **"Manipulate pages" means writing PeopleTools metadata, which is a
   fundamentally different risk class than anything this platform does
   today.** Every existing feature in this platform is deliberately read-only
   (`ARCHITECTURE.md`'s "Read-only by default" principle, `connectors/sqlws.py`
   and `connectors/sqlmask.py`'s entire design, the SQL Proxy's `validate_readonly()`
   blocking all DML/DDL unconditionally). Automating retrofit means actually
   *changing* page/record/PeopleCode definitions in a target environment — and
   doing that via raw SQL `UPDATE`/`INSERT` against `PSPNLFIELD`/`PSPNLDEFN`/
   `PSPCMPROG` would be unsupported and dangerous: PeopleTools metadata has
   integrity constraints, cache invalidation, and versioning semantics that
   only its own object model enforces correctly. The safe path is to drive
   PeopleTools' *own* supported migration mechanics — Application Designer's
   Compare/Copy and Project (XML) export/import, which already exist
   specifically to move object definitions between environments — not to
   reinvent metadata writes from scratch.

## Honest feasibility assessment

**Yes, with a phased answer, not a single yes/no.** The value in an upgrade
retrofit isn't evenly distributed — most of it is in *knowing precisely what
changed and what's at risk* (a detection/analysis problem this platform is
already good at) rather than in the mechanical act of copying a field
definition (which PeopleTools' own tools already do, just manually and
per-object today). The game plan below is ordered by that value/risk curve,
each phase useful on its own even if the ones after it are never built:

### Phase A — Customization Detection & 3-Way Impact Analysis (read-only; high confidence; buildable now)

Extends existing, proven infrastructure rather than inventing new mechanisms:

- **Universal customization inventory**: generalize the `LASTUPDOPRID`
  heuristic already used for PeopleCode (`peoplecode.py`) and the
  `overridden`/`custom-only` classification already used for SQR/COBOL
  (`sqrdb.override_summary()`) across every customizable UOM object type —
  pages, records, fields, Application Packages, Component Interfaces,
  permission lists, menus, Application Engine programs. Most of the plumbing
  (UOM providers, KG nodes) already exists per object type from Phase 5;
  this is a classification pass over data already being queried, not new
  discovery.
- **3-way compare**: register a **target environment** (a stood-up copy of
  the new PeopleTools/application release, before the customer's
  customizations are reapplied) the same way `sqr_sources`/`cobol_sources`/
  `trace_sources` already register per-environment source locations in
  `config.json`. For each customized object, compare: my-current-object vs.
  old-delivered-baseline (already have this via the OPRID heuristic) vs.
  new-delivered-baseline (a live query against the target environment). This
  is the same "compare two environments" mechanism `connectors/envcompare.py`
  already implements for 23 object types — extended to be object-instance-
  level (not just row-count) and 3-way instead of 2-way.
- **Risk-ranked retrofit worklist**: classify each customized object into a
  small number of real, actionable buckets — *unchanged upstream* (safe,
  no-op), *upstream changed but customization doesn't overlap* (likely safe
  to reapply as-is), *upstream changed and customization overlaps* (needs
  human review — this is the actual hard case), *upstream deleted/renamed
  the object or anchor point* (needs a decision, not just a merge). Surface
  this the same way the Change Risk Analyzer (`/admin/riskanalysis`, Phase
  6) already surfaces blast-radius scoring, and make it walkable via the
  Knowledge Graph so a reviewer can see what else depends on a
  hard-to-retrofit object before deciding how to handle it.
- **AI-reachable**: register this worklist as new AI tools (following the
  Phase 12 pattern), so "what customizations are at risk in the HCM upgrade
  to PeopleTools 8.63?" becomes an assistant question with a real, current
  answer — not a report someone has to remember to regenerate and read.

This phase requires no new write capability, no new risk category, and
reuses `envcompare.py`, the KG, the delivered-OPRID heuristic, and the
Phase 6 risk-scoring pattern directly. It is the recommended starting point
if this plan is approved.

### Phase B — AI-Assisted Merge Recommendations (advisory; medium risk; still no writes)

For the subset of Phase A's worklist that's mechanically simple — a clean,
isolated customization that doesn't structurally overlap with what changed
upstream (e.g., a self-contained custom validation block appended to an
otherwise-unchanged PeopleCode event) — use the AI (extending the Phase 12
Universal Diagnostics tool-calling pattern) to *propose* a merged
definition or a project-diff artifact, presented for human review — never
auto-applied. This is the same posture Phase 11's SQL Proxy and Phase 12's
diagnostics already take toward anything consequential: the AI reasons and
recommends, a human decides. The deliverable here is a reviewable diff/patch,
not a live change.

### Phase C — Automated Retrofit Application (write-side; longer horizon; opt-in and gated)

Only for the narrowest, best-understood subset of Phase B's recommendations,
and only by driving PeopleTools' own supported migration mechanics (Project
XML export/import, Application Designer's command-line compare/copy) —
never raw metadata SQL. This is a deliberate, first-ever exception to this
platform's "read-only by default" principle and must be treated as a
different product, not a feature toggle:

- **Opt-in per customer, off by default.**
- **Sandbox/non-production target environments only**, at least initially —
  never a customer's actual PRD or a shared UAT without explicit,
  reconfirmed authorization for that specific run.
- **Dry-run/simulation mode is mandatory before any real run** — show
  exactly what would be written, in the same project-XML/diff form a human
  reviewer would read, before ever touching a target environment.
- **Every write goes through PeopleTools' own object model** (Application
  Designer automation / project copy), preserving `LASTUPDOPRID`/
  `LASTUPDDTTM`, referential integrity, and cache invalidation exactly as a
  human using the tool would — not a shortcut around it.
- **Full audit trail and rollback path** — reuse the project/backup
  mechanics PeopleTools already provides (a project is inherently a
  restorable unit) rather than inventing new rollback machinery.
- Start with the lowest-risk object types (isolated PeopleCode block
  insertions) and only consider structural page-layout changes — literally
  moving/repositioning fields — after the simpler cases are proven reliable
  in real use; page-layout retrofit is the single hardest case in this whole
  plan and should be the last thing attempted, not the first.

## Recommended starting point

Build Phase A. It's squarely in this platform's existing strengths (read-only
metadata comparison, KG-based impact analysis, AI tool integration), it's
valuable standalone even if Phase B/C are never greenlit, and getting the
3-way compare and risk-ranking right is the foundation everything else in
this plan depends on — there's no responsible way to attempt Phase B or C
without first getting Phase A's detection right.

---

# Digital Twin Persistence

**Status: Foundational pieces complete; full vision open-ended.**

### Completed
- Knowledge Graph snapshots (creation, listing, comparison, scheduled daily builds,
  retention pruning); graph drift detection against snapshot baseline
- Incident recording with full runtime state capture (see Phase 4)
- Environment/security change history via drift time series (see Phase 6)

### Remaining
- Full change history across all object types (drift covers 23 types, not universal —
  UOM has ~54; remaining types are either row-count-uninteresting or need real
  table-name verification before adding, per the process used to add the last 6)
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
