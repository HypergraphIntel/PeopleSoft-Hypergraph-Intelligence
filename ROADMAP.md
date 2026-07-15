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
- Upgrade Retrofit: universal customization detection + object/page-field-level
  compare across environments, AI-directed "here's exactly what needs to
  change" guidance with a closure-verification loop (RESOLVED/STILL_DIVERGENT/
  NEW_ISSUE_INTRODUCED) — entirely read-only, no automated metadata writes
- Admin shell smoke test harness (74 pages)

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

### ✅ Formerly-stub providers, now fixed (2026-07-14)
Navigation Collections, Event Mappings, Related Content, and Drop Zones were
originally built against PeopleTools table names that don't exist on delivered
PeopleTools (`PTNC_COLLECTION`, `PSEFMAPPINGDEFN`, `PSRELCONDEFN`, `PSPTDZDEFN`
and friends) and silently returned empty results. All four were root-caused
against live data and rewritten against the real schema:
- Navigation Collections → `PSPRSMDEFN` (folder-type Content References under
  `PORTAL_PRNTOBJNAME = 'CO_NAVIGATION_COLLECTIONS'`).
- Related Content → `PSPTCSSRVDEFN` (same table Content Services uses),
  filtered to rows with `FIELDNAME` populated.
- Event Mappings → `PSPTCSSRVDEFN` filtered to `PC_EVENT_TYPE` populated;
  event/handler are columns on the row itself, no child table.
- Drop Zones → `PSPNLFIELD` (`FIELDTYPE IN (11, 18)`) joined to the
  system-wide stub subpage in `PSOPTIONS.PTSTUBSUBPAGE` — not a named
  definition at all.

See `DEVELOPMENT_DIARY.md` session 51 for full investigation detail.

### ⛔ Deprioritized providers
Investigated and deprioritized — reference table for future re-evaluation on other
environments/PeopleTools versions:

| Provider | Tables | Reason |
|---|---|---|
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

### Promotion auto-detection (Phase 2) — Done 2026-07-15
~~blocked on real promotion-chain environments~~ — **this assumption was wrong and
was corrected by the user**: HRDEV/HRTST/HRUAT/HRPRD are all pillar `HCM` in
`config.json` and are a real DV→TST→UAT→PRD chain with live Oracle connectivity to
all four (confirmed: `SELECT PROJECTNAME, LASTUPDDTTM FROM SYSADM.PSPROJECTDEFN`
returns real data — 3487-3488 rows — against every one of them). Implemented:
`connectors/promotiondb.py`'s `detect_promotions(pillar, chain)` snapshots
`PSPROJECTDEFN.LASTUPDDTTM` for every environment in a configured chain
(`config.json` `promotion_chains`, e.g. `"HCM": ["HRDEV","HRTST","HRUAT","HRPRD"]`)
into a new `project_state` table, and auto-records a promotion (`promoted_by:
"auto-detected"`) whenever a downstream environment's timestamp for a project
changes since the last check *and* the new value matches its immediate upstream
neighbor's current timestamp — reusing the existing Phase 1 `record_promotion()`
so auto-detected and manually-logged promotions share one timeline/API. First run
against a pillar only establishes a baseline (nothing to diff against yet); no
false positives on cold start. Wired into `connectors/scheduler.py` as a new
15-minute background thread (`promotion-detect`), gated on `promotion_chains`
being configured — no-op if unset. New endpoints: `POST /api/promotions/detect`
(manual trigger), `GET /api/promotions/chains`.

**Verified live**: baseline run against the real 4-environment chain found 0
false positives (project sets differ only by count — HRTST has one fewer project
than the others, nothing changed). Since there was no real in-flight promotion to
observe, verified the detection *logic* itself by seeding a synthetic stale prior
state for one real project in `project_state` (same verification approach used
for the SQR/COBOL structural diff work, where no real differing files existed
either) and confirming a second run correctly detected and recorded the
promotion, a third run did not re-fire (idempotent), and the result appeared
correctly in `list_promotions()`.

### Remaining — domain topology port/listener detail
- **2026-07-13**: Domain discovery (`connectors/domaindisc.py`) was rebuilt on SSH
  filesystem listing instead of `PSPMDOMAIN_VW` (see DEVELOPMENT_DIARY.md 2026-07-13),
  since that Oracle view depends on Performance Monitor being configured/running and was
  returning empty/stale/wrong data in environments where PSPM wasn't set up.
- **2026-07-13 (session 2)**: first live check found environments sharing one physical
  app-server host (all of HRDMO/HRDEV/HRTST/HRUAT/HRPRD here) were each re-querying the
  same `ps_cfg_home` and showing 5x duplicated results — fixed by discovering each unique
  `(ssh_host, ps_cfg_home)` pair once and attributing it to every environment sharing it
  (labeled by shared pillar name when all grouped envs share one, else joined env names),
  rather than one row-set per environment name (`connectors/domaindisc.py`
  `discover_domains_by_path`).
- **2026-07-13 (session 3)**: added port/listener parsing — `_app_server_port()` reads
  `psappsrv.cfg` and extracts `Port=` from the Jolt/WSL listener section;
  `_web_domain_ports()` reads WebLogic `config/config.xml` and extracts `<listen-port>`/
  `<ssl-listen-port>`. Both are best-effort (`_read_text()` returns `None` on any SSH/read
  failure rather than raising), so a domain with an unreadable/missing config file still
  shows up with `—` ports instead of failing the whole listing. Process Scheduler domains
  intentionally have no port (no listener) — that's expected, not a gap.
- **Done 2026-07-15**: `_domain_dbname()` parses `DBName=` from each domain's
  `[Startup]` section (`psappsrv.cfg` for App Server, `psprcs.cfg` for Process
  Scheduler — confirmed live no `ServerName` field exists, only `DBName`).
  `attribute_domains_to_envs()` now matches on this first (ground truth) before
  falling back to the old name-substring heuristic, which stays as the only
  signal for Web/IB domains (no equivalent config file to read). Confirmed live
  this resolves correctly even where the domain directory name actively
  disagrees with its environment (`HCMDMO_APP` → `DBName=HRDMO`) and where the
  environment's display name differs from its Oracle service name (FSCM:
  `name=FSCM` but `service=FSCMDMO`, and `DBName` matches `service`, not
  `name` — verified live, not assumed). Also found and fixed a real, unrelated
  discovery bug while investigating Process Scheduler domains for this: entries
  like `appserv/prcs` are container directories with no config file of their
  own, nesting the real domain one level deeper (`appserv/prcs/HCMDMO_PRCS`) —
  the old code treated the container itself as a fake domain with no ports, no
  DBName, no correct name, and never discovered the real nested domain at all.
  Fixed by detecting the missing config file and listing the container's
  subdirectories as the real domains instead. Verified through the full
  production path, `GET /api/runtime/domains/all`, not just the connector
  function directly.

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
- ~~Process Scheduler log ingestion for **Windows-hosted** schedulers (SMB/WinRM
  transport) — blocked until a Windows scheduler server is available to test
  against.~~ **Done 2026-07-15**: a real Windows 11 VM running HRDEV's Process
  Scheduler (`HRDEV_PRCS_WIN`) became available. Implemented the SMB transport:
  `connectors/smbconn.py` (new, `smbprotocol` library) mirrors `sshclient.py`'s
  `list_files`/`read_bytes`/`file_size` API so `logingest.py` can dispatch to
  either transport by a new per-source `"transport"` field (`ssh_sftp` default,
  `smb` for Windows), resolved via a new `smb_hosts` config section (same
  `env:VAR_NAME` secret-indirection pattern as `ssh_hosts`). `log_sources`
  table gained a `transport` column via migration. WinRM/local/agent transports
  remain unimplemented — SMB was sufficient for this real target and is the
  simpler of the two to provision (a shared folder vs. enabling PS Remoting).
  Verified live end-to-end: real SMB auth (guest access is disabled on Windows
  11 by default even on an "Everyone"-shared folder — needed a real domain
  account), a real file-locking issue found and fixed (`share_access='rwd'`,
  since PeopleSoft's own server process holds the log file open), the existing
  `prcs_ae` parser consuming real Windows AESRV log lines unmodified, offset
  tracking correctly returning 0 new bytes on a second run, and the existing
  SSH-based sources continuing to work unaffected.
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
- ~~Syntax-aware diffing (AST-level comparison, not just comment/whitespace
  normalization) — no concrete blocker, just a larger lift than this pass.~~
  **Done 2026-07-15.** Added block-level structural diffing to both
  `connectors/sqrdb.py` and `connectors/cobol_db.py`: `_extract_blocks()` splits
  source into named blocks using each language's natural PeopleSoft-delivered
  convention (SQR: `begin-procedure`/`end-procedure`; COBOL: `SECTION.` headers
  within PROCEDURE DIVISION), and `_structural_diff()` compares blocks pairwise
  (reusing the existing `_normalize_source()` comment/whitespace normalizer per
  block) to report `blocks_added`/`blocks_removed`/`blocks_changed`/`blocks_same`.
  Wired into `envcompare_sqr()`/`envcompare_cobol()`'s normalized-diff path for
  any file still different after whole-file normalization. Not a full AST/grammar
  parser — a pragmatic middle ground using the delivered-source structural
  convention, verified live: SQR `begin-procedure` blocks are not nested (checked
  `battimes.sqr`), COBOL `SECTION.` blocks are reliably present across 6 diverse
  delivered programs. Since delivered source is identical across all indexed
  environments in this dataset (no real differing files exist to exercise the
  path end-to-end), verified the extraction/diff functions directly against real
  file content with synthetic modifications, then verified the new
  `structural_diff` field renders correctly on `/admin/sqrcompare` and
  `/admin/cobolcompare` via real V8 execution (`py_mini_racer`) of the actual
  served `renderChanged()` JS.

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

**Status: ✅ Phase A + Phase B built and verified (read-only, directive-then-verify).
Phase C remains theorized only — see below.**

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
per-object today).

**Reframed starting point (this is the actual initiative, not a stepping
stone to something bigger):** rather than building toward automated writes
at all, the near-term goal is a **directive-then-verify loop** — the AI
tells the user exactly what object and what specific change needs to happen,
the human makes the change themselves (in Application Designer, as they
already do today), and the AI re-checks and gives an explicit "resolved /
still divergent / new issue introduced" verdict. This is not a new
interaction pattern for this platform — it's the exact shape Phase 12's
trace-escalation step already uses (tell the user precisely what to do →
they act → the AI checks the result and continues) applied to retrofit
instead of trace files. It requires **zero new write capability**, so
none of Phase C's risk category applies to this initiative at all — Phase C
is retained below only as a possible, much later, separately-evaluated
idea, not part of this plan.

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

This phase requires no new write capability, no new risk category, and
reuses `envcompare.py`, the KG, the delivered-OPRID heuristic, and the
Phase 6 risk-scoring pattern directly. It is the necessary foundation the
directive-then-verify loop below is built on — there's no way to tell a
user precisely what needs modification without this detection layer
existing first.

### Phase B — AI-Directed Retrofit Guidance & Closure Verification (read-only; the actual initiative; buildable now)

This is the reframed core deliverable. For each object in Phase A's
worklist that needs human review, the assistant (extending the Phase 12
Universal Diagnostics / Phase 12 trace-escalation pattern) does two things,
in two separate turns of a conversation — not one shot:

1. **Direct the user to exactly what needs modification.** Not "this object
   is at risk" — the specific, concrete delta. E.g.: *"Page `JOB_DATA1`:
   your custom field `CUST_FLAG` sits at field position 15. The new
   delivered page inserted 2 fields before position 12, shifting everything
   after it — reposition `CUST_FLAG` to position 17 to preserve its
   placement immediately after `DEPTID`."* Or: *"PeopleCode event
   `SavePreChange` on record `JOB`: your custom validation block (lines
   40-52) checks `FIELD_X` against a hardcoded list. The new delivered code
   added validation logic at line 30 that changes what `FIELD_X` means
   after a status change — move your block after the new delivered logic
   and re-check against the new `FIELD_X` semantics."* This has to come
   from the real 3-way diff data (old-delivered vs. new-delivered structural
   delta, applied to where the customization actually sits), not a generic
   "something changed" — genuinely specific instructions are the entire
   point of this phase.
2. **Verify closure after the user acts.** Once the user reports the change
   is made (the same "user reproduces, AI checks" shape as trace escalation),
   the assistant re-runs the object-level compare for that specific object
   and gives an explicit verdict: **RESOLVED** (now correctly reconciled with
   the new baseline), **STILL DIVERGENT** (the described change wasn't fully
   applied, or wasn't enough), or **NEW ISSUE INTRODUCED** (the change
   created a fresh divergence from what was actually needed). Never leave
   the user wondering whether they're done — the same "reach an explicit
   verdict" discipline the Phase 12 investigation method already mandates
   for root-cause diagnosis applies here to retrofit closure.

New AI tools needed: something like `retrofit_worklist(env, target_env)` (Phase
A's ranked list), `retrofit_guidance(env, object_type, object_name)` (the
specific per-object instruction), and `retrofit_verify(env, target_env,
object_type, object_name)` (the closure check, re-running the same compare
against the object's current state). All three are read-only, all three
follow the existing tool-registration and system-prompt patterns from
Phase 11/12 directly — no new architecture, just new tools plus a new
system-prompt section describing the two-turn directive-then-verify shape.

## What was built

`connectors/retrofit.py` implements both phases in one module (they turned
out inseparable in practice — Phase B's guidance/verify tools are thin
wrappers over Phase A's compare primitives, not a separate layer):

- **`_OBJECT_TABLES`** — 7 object types (page, record, field,
  component_interface, permission_list, menu, ae_program), each mapped to its
  real table/key-column pair. These were verified against this codebase's own
  existing usage (`psdb.py`'s `global_search()` specs, `ptmetadata.py`'s
  discovery specs) rather than re-guessed — e.g. `page` → `PSPNLDEFN.PNLNAME`,
  `record` → `PSRECDEFN.RECNAME`. A live-data investigation (via a background
  research agent, before writing any code) confirmed `LASTUPDOPRID` exists on
  every one of these tables except `PSAPPCLASSDEFN` (Application Packages —
  that table is a pure name/path mapping with no audit column; the actual
  App Package *source* lives in `PSPCMPROG OBJECTID1=104`, already covered by
  the existing PeopleCode detection, so Application Packages didn't need a
  new path at all).
- **`customization_inventory(env, object_types)`** — the universal
  customization inventory: server-side-filtered (not fetch-all-then-filter —
  real customer tables can be 500K+ rows) `LASTUPDOPRID NOT IN
  (delivered set)` query per object type, reusing `peoplecode.py`'s existing
  `_DELIVERED_OPRIDS` constant directly rather than duplicating it.
- **`compare_object_header(env_a, env_b, object_type, name)`** — a generic
  single-object structural compare, working uniformly across all 7 types:
  fetches the header row from each environment, reports which columns differ
  (excluding audit-noise columns like `LASTUPDDTTM` itself), and whether the
  object is missing from one side entirely (a real, important finding —
  upstream sometimes deletes or renames things).
- **`compare_page_fields(env_a, env_b, pnlname)`** — the concrete "page
  manipulation" case from the original ask: a `PSPNLFIELD`-level diff
  reporting fields added/removed and, critically, fields present in both
  environments but repositioned (different `FIELDNUM`/`FIELDTOP`/`FIELDLEFT`)
  — exactly the signal needed to tell a user "your custom field needs to move
  from position X to Y because delivered fields were inserted before it."
- **`retrofit_worklist`/`retrofit_guidance`/`retrofit_verify`** — the three
  functions ROADMAP sketched, plus a refinement during implementation:
  `retrofit_verify` accepts an optional `previous_diff_columns` (the diff
  columns from the `retrofit_guidance` call earlier in the conversation) so
  it can distinguish **STILL_DIVERGENT** (the same problem persists) from
  **NEW_ISSUE_INTRODUCED** (the original problem is fixed but the change
  caused a different divergence) — without it, both collapse to
  STILL_DIVERGENT, which is still correct but less specific. This wasn't in
  the original sketch; it fell out of actually implementing the three-verdict
  requirement from the plan.

New AI tools `retrofit_worklist`, `retrofit_guidance`, `retrofit_verify`
wired into `connectors/ai_tools.py`; new "Upgrade Retrofit" section in
`routers/assistant.py`'s `_SYSTEM` describing the four-step directive-then-
verify method.

### Verification

**Real data**: `customization_inventory` run against live HCM data across
all 7 object types — real totals matching the research investigation exactly
(17,342 pages, 52,773 records, 90,630 fields, 458 CIs, 1,370 permission
lists, 637 menus, 2,747 AE programs), 0 customized in every type — an
honest result: this lab's demo databases are pristine vendor copies with
zero real customizations anywhere, confirmed before writing any code, not
a sign anything's broken. `compare_object_header('HCM', 'FSCM', 'record',
'JOB')` found 5 real structural differences (field count 107 vs. 98, index
count 14 vs. 5, different parent record, etc.) — proving the mechanism
correctly detects real divergence when it exists, using the two live
environments as a stand-in pair since this lab has no genuine "old
release"/"new release" pair of the same pillar.

**Synthetic verification for the parts real data couldn't exercise** (same
discipline as the SQR override-intelligence work earlier this session — a
scratch/synthetic test proving classification logic works, since the real
environment has nothing to classify): no common HCM/FSCM page has real
layout differences (they run identical PeopleTools-level pages), so
`compare_page_fields`'s moved/added/removed-field detection was verified
with constructed `PSPNLFIELD` rows simulating exactly the scenario from the
plan — a custom field whose position shifts because 2 delivered fields were
inserted before it, plus one deleted and two newly-added delivered fields —
and confirmed all three detections fire correctly. `retrofit_verify`'s three
verdicts (RESOLVED / STILL_DIVERGENT / NEW_ISSUE_INTRODUCED) were each
constructed and confirmed correct the same way. Both are now permanent
regression tests in `tests/test_retrofit.py` (5 tests).

**Live, unscripted, multi-turn test against the real OpenAI-backed
assistant**: asked it to retrofit the `JOB` record from HCM toward an FSCM
target — it called `retrofit_guidance` and gave a specific, itemized
breakdown of every real differing column. A follow-up turn ("I updated the
parent record name, please verify") correctly triggered `retrofit_verify`
with the right `previous_diff_columns`, and correctly reported
**STILL_DIVERGENT** with the real remaining diffs (since the simulated
"I made the change" was never actually applied to the live database — the
tool correctly re-queried and found the same real divergence, exactly as it
should).

Verification: `python3 scripts/smoke_admin_shell.py` → 73/73 (unchanged — no
new admin pages, this is connector + AI tool + system-prompt work); `make
check` → 100/100 files, 24/24 tests (19 previous + 5 new).

## Recommended starting point

Phase A and Phase B are both built — this was the complete near-term plan
for this initiative, and it's now done. Both are entirely read-only and
reuse existing infrastructure directly (no new risk category, no write
capability, nothing that departs from this platform's "read-only by
default" principle).

## Phase C (retained only as a note; not part of this initiative)

The earlier draft of this plan also sketched an eventual automated-write
retrofit (driving Application Designer's own migration mechanics rather than
raw metadata SQL). That remains true as an idea, but is explicitly **not**
part of this initiative — the reframing above replaces "the AI writes the
fix" with "the AI tells you precisely what to write, then confirms you got
it right," which delivers the practical value (turning a slow, expert-
dependent manual process into a directed, verified one) without taking on
any write-side risk at all. Revisit Phase C only as a separate, much later
decision, if the directive-then-verify loop below proves itself in real use
and an automated-write capability is deliberately requested on its own
merits.

---

# Digital Twin Persistence

**Status: ✅ Complete.** All four previously-open items closed; see below.

### Completed
- Knowledge Graph snapshots (creation, listing, comparison, scheduled daily builds,
  retention pruning); graph drift detection against snapshot baseline
- Incident recording with full runtime state capture (see Phase 4)
- Environment/security change history via drift time series (see Phase 6)

**Drift coverage expansion (23 → 45 types).** Added 22 more `(label, sql)` rows to
`envcompare.py`'s `summary()`: Approval Framework, Message Catalog, Search
Definitions/Categories, Pivot Grids, Connected Queries, File Layouts, App Designer
Projects, IB Applications/Service Groups/Operations, Application Classes, Content
Services, PTF Tests, ADS Definitions, Chatbot Skills, Archive Objects, Timezones,
Locales, PM Metrics/Transactions/Events. Each real table name was found by tracing
the corresponding `uom.py` object function down through `psdb.py` (not guessed —
several naive `PS<Name>DEFN` guesses came back `ORA-00942` and were discarded, e.g.
Search Definitions is really `PSPTSF_SD`, not `PSSRCHDEFN`), then verified live with
real, queryable HCM/FSCM counts before adding (same standard as the prior 17→23
expansion). Persisted snapshot refreshed via `POST /api/drift/snapshot`, confirmed
all 45 types present in `/api/drift/latest`. At the time of this Phase 5 work,
Navigation Collections/Event Mappings/Related Content/Drop Zones were believed to
have no backing table and were left out of drift coverage; that assumption was
wrong and all four were fixed on 2026-07-14 against real tables (see the "Formerly-
stub providers" section above), and added to drift coverage on 2026-07-15 — drift
coverage is now 50 types, not 45.

**Deployment/Configuration History.** New `connectors/deploymentdb.py`
(`data/deployment_events.db`) links what the promotion log already records (*that* a
promotion happened) to concrete evidence of *what* the environment looked like around
it: a SHA-256 fingerprint of `config.json` (only the full text is stored when the
hash changes, deduped like `envcompare.py`'s unchanged-content skip) plus the nearest
`driftdb` snapshot. `routers/promotions.py`'s `POST /api/promotions` now calls
`record_deployment_snapshot()` automatically after every promotion — no extra user
action. New `GET /api/promotions/{id}/deployment` (before/after view) and `GET
/api/deployments/{env}/history` (config-fingerprint timeline). `/admin/promotions`
gained a per-row "Config fingerprint" expand showing the linked drift snapshot.
**Security fix caught during verification**: the first version stored raw
`config.json` — including live Oracle passwords, the OpenAI API key, and the SQL
Proxy HMAC salt — in SQLite and served it back over `GET`. Added `_redact()`
(recursive secret-key masking on `password`/`api_key`/`salt`/`key_path`/etc.) before
any hash or storage; re-verified live that a fetched deployment snapshot no longer
contains any real credential.

**Runtime Replay.** `incidentdb.py`'s `incident_snapshots` table already supported
multiple snapshots per incident; only the *latest* was ever surfaced. Added
`get_snapshot_series()` (all snapshots for one source, chronological) and
`replay_timeline()` (all sources merged chronologically); new `GET
/api/incidents/{id}/replay`. `/admin/incidents`' "Snapshot History" tab is now a real
step-through replay — click any row (or Prev/Next) to re-render that point-in-time
RCA snapshot in the existing RCA tab, instead of only ever showing the newest one.
Verified live: created a real incident, triggered a second RCA re-capture, confirmed
`/api/incidents/{id}/replay` returns both snapshots in chronological order.

**Architecture Assistant.** New `connectors/archreport.py` — reports, not a new graph
engine, built entirely on existing KG primitives (`graphdb.impact()`,
`dependency_tree()`, and `peoplecode.py`'s `component_sequence()`/`record_sequence()`):
`dependency_report()` (Markdown: overview, forward deps, reverse/blast-radius deps,
direct typed edges), `sequence_narrative()` (phase-ordered narrative + an embedded
Mermaid flowchart code block — text only, no new rendering library, paste into any
Mermaid-compatible viewer), `impact_summary_doc()` (prose blast-radius paragraph for
a change ticket). New `GET /api/architecture/{dependency-report,sequence-report,
impact-summary}`; new `/admin/architecture` page (env/type/name form, "Generate
Report" + "Copy as Markdown"); new AI tool `architecture_report` in `ai_tools.py`.
Verified against real data: `dependency_report('HCM','component','JOB_DATA')`
correctly found 2 real upstream dependents (a content_service and a portal_registry
entry) matching `/admin/impact`'s own data; `sequence_narrative('HCM','record','JOB')`
correctly rendered JOB's real Build/Interaction/Save PeopleCode events with a valid
Mermaid diagram.

**Verification (all four)**: `make check` → 111/111 files, 24/24 tests. Admin smoke
test → 74/74 pages (added `/admin/architecture` to the suite).

### Remaining (acknowledged, not blocking)
- ~~Drift coverage is now 45 of ~54 UOM types — the remainder (Navigation Collections,
  Event Mappings, Related Content, Drop Zones) were excluded...~~ **Done 2026-07-15**:
  all four added to `envcompare.summary()` (drift coverage is now 50 types) —
  Navigation Collections (`PSPRSMDEFN` filtered to the nav-collection folder subtree),
  Related Content and Event Mappings (`PSPTCSSRVDEFN`, filtered on `FIELDNAME` and
  `PC_EVENT_TYPE` respectively), Drop Zones (`PSPNLGROUP`/`PSPNLFIELD` joined to
  `PSOPTIONS.PTSTUBSUBPAGE`) — verified live with real non-zero counts, through the
  full HTTP path, and through an actual persisted drift snapshot
  (`scheduler.run_drift_now()` → `driftdb.get_latest()`).
- Deployment history correlates config.json + drift snapshots; it does not track
  PeopleTools metadata-level changes beyond what drift already counts (that's Phase
  13's retrofit-compare territory, not this phase's).
- ~~Architecture Assistant renders diagrams as Mermaid text, not an in-app rendered
  graphic~~ **Done 2026-07-15**: reports now render as formatted markdown (via
  `marked`) with `\`\`\`mermaid` code blocks rendered as actual in-app SVG diagrams
  (via `mermaid.js`), with a "View Raw Markdown" toggle and "Copy as Markdown"
  preserved for the original paste-into-a-doc workflow. Diagram extraction uses
  placeholder substitution around `marked.parse()` rather than overriding its
  `renderer.code()`, since that override's call signature has changed across
  `marked` versions and the CDN isn't pinned to one. Verified with a real embedded
  V8 (`py_mini_racer`), not just static review — this session had already shipped
  two backslash-escaping bugs in `new RegExp(string)` calls that looked correct on
  read-through, so the same real-execution discipline was applied here too, and
  caught one: the mermaid fence-matching regex's `\n` was written as a single
  Python backslash, which Python's string parser (not a raw string) turned into
  an actual embedded newline byte inside a JS *regex literal* — invalid, since
  regex literals can't span a raw newline any more than string literals can.

---

# Phase 14 — Containerization, IB Transactions Redesign, and Admin UI Reliability Sweep (2026-07-14)

**Containerized deployment.** `Dockerfile` (Python 3.12-slim, non-root user, tini
entrypoint, healthcheck) and `compose.yml` added, alongside CI build/publish
workflows. `connectors/paths.py` is the new single source of truth for path
resolution (`APP_ROOT`, `CONFIG_FILE`, `DATA_DIR`, `LOG_DIR`), each overridable via
`PHI_CONFIG_FILE`/`PHI_DATA_DIR`/`PHI_LOG_DIR` env vars; `PHI_PORT` makes the
container port configurable end-to-end (compose port mapping + `uvicorn --port`).
Eliminated ~26 hardcoded `/opt/deathstar-api` absolute-path occurrences and 14
`Path(__file__).parent.parent / "config.json"` patterns across the codebase so the
same image runs standalone or containerized. Verified via real `podman build`/
`podman run` (Docker not available in-session; Docker buildx confirmed working via
CI "Container check" after the fact).

**IB Explorer Transactions redesigned.** Moved from a flat single-record view to the
real PeopleSoft data model: Operation Instance (`PSAPMSGPUBHDR`) → Publication
Transaction(s) (`PSAPMSGPUBCON`) → Subscription Transaction(s) (`PSAPMSGSUBCON`,
fixing a join that used the wrong correlation column and always returned 0 rows).
Added Request Message Body (decompressed from `PSAPMSGPUBDATA`, verified against a
real zlib-compressed MIME payload) and IB Errors (`PSIBERR`/`PSIBERRP` joined to
`PSMSGCATDEFN`). Response Message Body deliberately **not** implemented — no live
data or schema path bridges `PSAPMSGPUBCON` to the `PUBID`-keyed
`PSAPMSGSCONDATA`/`PCONDATA` tables in this environment; user confirmed skipping it
rather than guessing.

**Fabricated-table fixes.** Navigation Collections, Related Content, Event Mappings,
and Drop Zones were all built against PeopleTools table names that don't exist on
delivered PeopleTools and always returned empty results (not a missing-grant issue —
the tables themselves aren't real). All four root-caused against live data and
rewritten against the actual schema (`PSPRSMDEFN`, `PSPTCSSRVDEFN` ×2,
`PSPNLFIELD`+`PSOPTIONS.PTSTUBSUBPAGE`) — see the Phase 5 update above for detail.
One additional real SQL injection vulnerability was found and fixed in the Change
Risk Analyzer / Impact Forecasting pages (`routers/admin/platform.py`,
`routers/admin/tools.py`): user-typed project names were interpolated directly into
SQL strings instead of using the existing bind-parameter support in
`/api/sqlws/execute`.

**Admin UI reliability sweep.** A systematic, page-by-page audit found the same bug
pattern repeated across roughly 30 admin pages: an Env selector that either wasn't
present, was a disconnected second selector, or — the most common root cause —
captured the selected environment once (`const ENV = window.dsGetEnv() || 'X'`) at
page load instead of reading it live, so switching environments silently kept
showing stale data or crashed against the wrong environment's data. Fixed
end-to-end across `routers/admin/{integration,platform,objects,security,portal,
tools,perf,graph}.py`: converted every capture to a live `ENV_VAL()` read and wired
`window.onEnvChange`/`deathstar:envchange` reload handlers, choosing the correct
reload behavior per page (auto-refresh a live list, re-load a URL-driven object, or
just clear stale state for pages that are fully user-triggered).

**Verification (all of the above)**: `ast.parse()` after every scripted edit (one
f-string brace-escaping mistake caught this way before shipping); live queries
against HRTST for every schema fix; `TestClient` round-trips through the full HTTP
path for every affected route, not just the underlying connector function.

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
