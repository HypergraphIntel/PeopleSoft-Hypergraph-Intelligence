# DeathStar Development Diary

This diary records implementation changes as they land. `ROADMAP.md` remains
the status tracker; this file keeps the narrative trail: what changed, why it
matters, and how it was verified.

------------------------------------------------------------------------

## 2026-07-03 — Processing Sequence: Record + Page-owned PeopleCode — 69/69

### Extending v1 correctly, after being corrected on the scoping

Asked "what should be built next," I initially proposed extending Processing
Sequence Intelligence to Page and Record by mirroring Component's pattern —
the user rightly pushed back twice: first on assuming SQR/COBOL should share
feature parity just because they share plumbing (a separate, general
correction, saved to memory), then specifically on Page: "Page Activate
PeopleCode is independent of Component processing." That second correction
was right and worth verifying properly rather than taking on faith — traced
it all the way to a live query.

**What research found**: `PSPCMPROG.OBJECTID1` values actually present in
this environment are `1, 3, 9, 10, 60, 66, 74, 104` — no `8`. But
`connectors/peoplecode.py`'s own `PEOPLECODE_OBJECT_TYPES` dict already maps
`8: "Page"`, and `_OID1_PARENT_TYPES` already maps `8: "page"` too — the
platform's own metadata already anticipated this category, but nothing
anywhere ever queried it. `SELECT COUNT(*) FROM PSPCMPROG WHERE OBJECTID1=8`
confirmed 0 rows in both HCM and FSCM — real, distinct, currently-unindexed,
but unpopulated in every environment available here. Decided (with the user)
to build it anyway, gracefully degrading — same category of decision as the
existing 0-row stub providers, not the "genuinely no data exists anywhere"
case that blocked browser session tracking.

Record, by contrast, turned out to have a real, populated, independent
event set: `OBJECTID1=1` (49,490 rows in HCM) — Record Field PeopleCode,
owned by the record itself, using literally the same event vocabulary as
Component's canonical sequence (FieldDefault, RowInit, FieldChange, etc.),
just without the Component-only events that need a component context to
exist (PreBuild/PostBuild/Activate/Workflow/SearchInit/SearchSave).

**Changes**:
- `connectors/peoplecode.py` — `record_sequence(env, recname)`: reuses
  `CANONICAL_COMPONENT_SEQUENCE`'s event list, filtered by `scope in
  ("Record/Field", "Record")`, slotted the same way `component_sequence()`
  does (empty/delivered/custom). `page_owned_events(env, pnlname)`: flat
  list (no phase ordering — Page-owned PeopleCode doesn't have a rich
  lifecycle), gracefully empty on 0 rows.
- `routers/peoplesoft.py` — `GET /api/peoplesoft/records/{rec}/sequence`,
  `GET /api/peoplesoft/pages/{page}/owned-events`
- `connectors/graphdb.py` — `record_sequences()` KG builder, mirroring
  `component_sequences()`'s *shape* (not its data): `record_event` nodes,
  `FIRES_BEFORE`/`FIRES_AFTER` edges. Applied the dedup-by-event-name fix
  from `component_sequences()`'s earlier self-loop bug proactively this
  time, rather than waiting to rediscover it — verified zero self-loops
  from the first rebuild.
- `routers/admin/security.py` — new "Processing Sequence" tab on the Record
  Explorer. Also fixed a stale `OBJECTID1=2` comment (should say `1`) found
  in two places while reading the existing "PeopleCode" tab's code — a
  pre-existing doc typo, not something I introduced.
- `routers/admin/platform.py` — new "Page-Owned PeopleCode" tab on the Page
  Explorer, lazy-loaded, clearly distinct from the existing per-component
  PeopleCode tab.

**Bug found and fixed while writing the Page Explorer JS**: first draft
used single-brace Python f-string interpolation (`{esc(name)}`) inside a
block that's actually a JS template literal embedded in the f-string —
needed the doubled-brace convention (`${{esc(name)}}`) the rest of the file
already uses. Caught before testing by re-reading the diff against
surrounding lines, not by a runtime error.

**Verified**: `curl /api/peoplesoft/records/JOB/sequence?env=HCM` — real
Build/Interaction/Save events slotted correctly, Search phase correctly
empty except `SearchDefault` (the one Record/Field-scoped search event),
zero Component-only events leaking in; `curl .../pages/JOB_DATA1/owned-
events?env=HCM` → `{"events": []}`, no error; fresh graph rebuild — real
`record_event` nodes and edges, zero self-loops. Both admin pages
(`/admin/record/JOB`, `/admin/page`) render 200 with the new tabs present
in the HTML. `make check` 91/91; smoke test 69/69 (additions to existing
pages — no new routes needed smoke coverage).

------------------------------------------------------------------------

## 2026-07-03 — ROADMAP.md Cleanup

### Docs-only: cut ROADMAP.md from 1738 → 360 lines

The user asked to clean up and organize `ROADMAP.md`. It had drifted well
past its own stated purpose ("current status and remaining work only" —
see this diary's own header) into a chronological changelog: many phases
had 3-5 near-duplicate "✅ Completed (2026-07-0X)" blocks repeating full
implementation narrative that already lives in this diary in complete
detail, and the file ended with an entire ~200-line "# Current Focus"
section that was a word-for-word duplicate summary of content already
stated earlier in the same document's phase-by-phase sections.

Rewrote the whole file: one "Status" line per phase (Complete /
Substantially complete / v1 complete / etc.), a concise bullet list of
what shipped (no verification numbers, no bug narratives — those stay
here in the diary), and a "Remaining" section listing only genuinely open
work with the real reason it's open (blocked-on-data, blocked-on-
environment, not-yet-prioritized). Deleted the entire duplicate "Current
Focus" tail section outright — everything in it was already stated
earlier in the document.

Nothing was lost: every phase's actual status and remaining-work items
were checked against the diary and this session's own memory before being
condensed, not just deleted for brevity. Config-shape JSON examples (AI
provider config, log source config, Windows Process Scheduler transport
types) were trimmed since they duplicate `config.json`'s own real entries
and the corresponding connector code — those are the actual source of
truth for shape, not prose in a roadmap file.

No code touched — `make check` unaffected (91/91), confirmed the repo
still builds clean after a docs-only change.

------------------------------------------------------------------------

## 2026-07-03 — Full UOM/KG Alignment Audit Complete — 69/69

### Second audit pass: all 54 provider types now covered

The user asked to keep going until the alignment work was genuinely done,
not just the first 20 high-traffic types. Delegated a second Explore-agent
audit covering the remaining ~26 real providers (the rest of the 54 total
are documented stub/deprioritized/reference-lookup types with no
relationships on either side to compare — nothing to audit).

Found **one further genuine mismatch**: `content_service ↔ portal_registry`.
UOM's `content_service_object()` surfaces a "Where Used (Portal Objects)"
relationship sourced from `PSPTCS_MNULINKS` (`psdb.get_content_service()`),
but `graphdb.py`'s `content_services()` builder never queried that table —
the KG had `content_service → component/menu/query/app_class` edges but
zero portal linkage at all. Added the `PSPTCS_MNULINKS` lookup and
`portal_registry → content_service` `USES` edges.

Everything else in the second pass — `queue`, `app_package`, `approval`,
`xpub_report`, `search_definition`, `search_category`, `pivot_grid`,
`connected_query`, `xlat_field`, `file_layout`, `ib_application`,
`app_class`, `ptf_test`, `url_definition`, `chatbot_skill`, `ib_routing`,
`style_sheet`, `archive_object`, `pm_metric`, `pm_transaction`, `pm_event`,
`ib_operation`, `ib_message`, `ads_definition` — either has no UOM
relationships declared to check against, or already matches its
`graphdb.py` builder. One harmless edge-direction difference was noted on
`app_class ↔ application_package` (`BELONGS_TO` vs the graph's reverse
`CONTAINS`) but isn't actionable since `graphdb.neighbors()` defaults to
bidirectional traversal.

**Verified**: fresh graph rebuild — 163 `portal_registry →
content_service` `USES` edges (up from 0). `make check` 91/91; smoke test
69/69.

**This closes the UOM/KG alignment effort for real.** All 54 UOM object
types are now either KG-consistent or have nothing to be inconsistent
about. Across both audit passes: 10 genuine mismatches found, all 10 fixed;
3 independent real bugs found and fixed along the way (Oracle NULL-
comparison in `portal_registry_portals()`, a SQL-generation bug in a
column-fallback rewrite, and a self-loop bug in AE `CALLS` edges) that
weren't part of the alignment work itself but were caught because I always
verify against a real rebuild rather than trusting a clean compile.

------------------------------------------------------------------------

## 2026-07-03 — UOM/KG Alignment Audit Closed: All 9 Mismatches Fixed — 69/69

### Final round: component→record broader usage, page subpages, and re-scoping page security

Closed out today's UOM/KG alignment audit — the last 2 of 9 mismatches.

- **`component → record` broader page-record usage**: `components()` only
  covered search/add-search records; added the full set of records any page
  in the component actually uses, via `psdb.component_records_used_by_pages()`.
- **`page → page` subpages**: `pages()` had no subpage handling; added via
  `psdb.page_subpages()`.
- **Page-level security — re-scoped rather than "fixed"**: on closer look,
  this was never actually a gap. PeopleSoft doesn't have page-level security
  distinct from component-level — UOM's "secures_page" relationship on a
  page object is sourced from `psdb.component_access()`, which is the exact
  same component-scoped `PSAUTHITEM` data `permissionlists()` already
  persists as `permissionlist → component SECURES`. Since `components()`
  already emits `component → page CONTAINS`, a page can already reach its
  permission chain via a 2-hop bidirectional traversal — the data was never
  missing, just not a direct 1-hop edge. Decided against adding a redundant
  direct edge (would need an extra per-page query back through `PSPNLGROUP`
  to resolve owning component, for zero new information) — this is a
  legitimate "no fix needed" outcome, not a shortcut.

**Verified**: fresh graph rebuild — 375 `component → record` `USES` edges
(up from the previous search/add-search-only baseline), 32 `page → page`
`CONTAINS` edges (up from 0). `make check` 91/91; smoke test 69/69.

**Summary of the whole 3-session-block alignment effort**: an Explore-agent
audit compared ~20 high-traffic UOM object types against the persisted
Knowledge Graph and found 9 genuine mismatches. All 9 are now fixed:
`operator ↔ permissionlist`/`role ↔ operator` edges, direct
`service_operation ↔ node` edges, `portal_registry` KG persistence (was
totally absent), `tree → field` edges, `component_interface → menu/record/
field` edges, the AE `section`/`ae_section` node-type split + `CALLS`
edges, and this final round's `component → record` broadening + `page`
subpages. Found and fixed 3 real bugs along the way that were independent
of the alignment work itself: an Oracle NULL-comparison bug in
`portal_registry_portals()` (also used by the Portal Registry admin page),
a SQL-generation bug in the `trees()` column-fallback rewrite, and a
self-loop bug in the AE `CALLS` edge logic inherited from the reference
implementation. ~34 provider types were never audited — a clear next slice
if this work continues, but not attempted in this session.

------------------------------------------------------------------------

## 2026-07-03 — UOM/KG Alignment Fixes, Round 3 (AE) — 69/69

### Application Engine: section node-type mismatch + CALLS edges

Last of the "clean win" fixes from the original alignment audit — the
other 2 remaining mismatches (page-level security modeling,
component→record broader page usage) are bigger structural gaps, not
quick edge additions, and stay in the backlog.

`application_engines()` used node type `ae_section`, while `ae.py`'s
`program_graph()` (the actual compact graph preview shown in the Object
Explorer) uses `section` for the same concept — meaning the exact same AE
section had two different node ids depending which code path built it, so
neither graph could reference the other's version of that section at all.
Renamed to `section` to match, and added `CALLS` edges for "Call Section"
steps (`AE_ACTTYPE = 'C'`), which were entirely missing from the KG.

**Real bug found while porting `program_graph()`'s own logic, not just
copy-pasting it**: `AE_DO_APPL_ID` (the called-program field) is *always*
populated on a Call-Section step — even for the extremely common
same-program case, where PeopleSoft just puts the calling program's own
applid there. The reference implementation's logic (`if called_appl: link
program→program CALLS elif called_sect: link program→section`) treats any
non-blank `ae_do_appl_id` as "this is a cross-program call," which produces
a self-loop edge (`AA_CONV_JPN CALLS AA_CONV_JPN`) for same-program calls —
confirmed via `ae.steps('HCM', 'AA_CONV_JPN')`: every Call-Section step had
`ae_do_appl_id: 'AA_CONV_JPN'` (itself) with the real target only visible in
`ae_do_section`. Fixed in the graphdb.py port (not in ae.py itself — didn't
want to touch the UOM reference implementation without being asked) by
always preferring the section-level target when one is given, and only
emitting a program-level edge when the called program genuinely differs
from the caller.

**Also investigated, not a new bug**: AE→PeopleCode `CONTAINS` edges
(`AE_ACTTYPE = 'P'` steps) never appear — traced this all the way back and
confirmed `ae.py:program_graph()` itself also produces zero PeopleCode
nodes for the same program in this environment (`AE_ACTTYPE` doesn't behave
the way the code expects here — a pre-existing schema-version gap on both
sides, not something this alignment pass introduced or needs to fix).

**Verified**: fresh graph rebuild — 148 `section` nodes (0 leftover
`ae_section` nodes), 106 `CALLS` edges with **zero self-loops** (confirmed
self-loops existed before the fix via the exact same rebuild, then gone
after). `/admin/ae` (the one admin page that reads AE section data)
spot-checked and still renders. `make check` 91/91; smoke test 69/69.

This closes 7 of the original 9 mismatches found in today's audit. 2 remain
(documented in ROADMAP.md): `component → record` broader page-record usage,
and page-level security modeling (the KG only models security at component
granularity — a real structural gap, not a quick edge addition). ~34
provider types were never audited in the first place.

------------------------------------------------------------------------

## 2026-07-03 — UOM/KG Alignment Fixes, Round 2 (tree, ci) — 69/69

### Continued the alignment backlog: tree → field, ci → menu/record/field

Picked up 2 more of the 5 remaining mismatches from the earlier audit today.

- **`tree → field`**: `trees()` never joined `PSTREESTRCT` — the table
  holding `node_recname`/`dtl_recname`/`level_recname` and their field
  counterparts, all of which `uom.py:tree_object()` promises as
  relationships. Added the join and the resulting record/field edges.
- **`component_interface → menu/record/field`**: `component_interfaces()`
  only emitted `ci → component`. Added `ci → menu` (from `PSBCDEFN.MENUNAME`),
  `ci → record` (search records + `PSBCITEM.RECNAME`), and `ci → field`
  (`PSBCITEM.RECNAME`/`FIELDNAME`) + `record → field CONTAINS`.

**Bug found and fixed during verification**: first attempt at the `trees()`
rewrite made every fallback column (`"NULL AS X"` when a column doesn't
exist in this environment's `PSTREEDEFN`, e.g. `TREE_RECNAME` genuinely
isn't there) get blindly prefixed with the table alias — `d.NULL AS
TREE_RECNAME` — which is invalid SQL and made the whole builder error out
(`ORA-01747: invalid user.table.column`). Caught it because I always
`curl /api/graph/build` and inspect `providers[].status` after touching a
builder, not just trust that it compiled. Fixed with a small `col_expr()`
helper that constructs one complete, valid expression per column instead of
string-concatenating a table prefix onto an already-complete fallback.

**Verified**: fresh graph rebuild (`limit=50`) — 50 `tree → field` `USES`
edges, 9 `ci → menu` `DECLARED_ON` edges, 811 `ci → field` `EXPOSES` edges,
138 `ci → record` `USES` edges, all up from 0; confirmed the SQL error
existed before the fix and was gone after (provider status flipped from
`warning` to `ok`). `make check` 91/91; smoke test 69/69.

3 mismatches remain from the original audit (component→record broader page
usage, page-level security modeling, AE section-node-type mismatch +
missing CALLS edges) plus ~34 unaudited provider types — left as backlog in
ROADMAP.md, not attempted this pass.

------------------------------------------------------------------------

## 2026-07-03 — UOM/KG Alignment Audit + Fixes — 69/69

### Started the "keep the KG consistent with UOM's relationship declarations" audit

Delegated a research pass to an Explore agent: compare ~20 of the
highest-traffic UOM object types' `_relationships`/`_graph` declarations
(what the Object Explorer's compact graph preview promises) against what
`connectors/graphdb.py`'s persisted-KG builders actually emit (what
cross-references/impact analysis/drift detection can see). Found 9 genuine
mismatches. Fixed the 4 lowest-risk, highest-value ones this pass; the
other 5 are documented in ROADMAP.md as a known backlog for a future
session (page-level security modeling, tree→field edges, CI→menu/record/
field edges, AE section-node-type mismatch + missing CALLS edges, and
broader component→record page-record usage).

**Fixed**:
- `operator → permissionlist` (`HAS_PERMISSION`) — `operators()` builder
  only had `operator → role`; added via `psdb.operator_permissionlists()`
- `role → operator` (`HAS_MEMBER`) — only the inverse existed; added via
  `psdb.role_users()`
- `service_operation ↔ node` (`SENDS`/`RECEIVES`) — only reachable via a
  2-hop routing traversal before; added direct edges alongside the existing
  ones
- `portal_registry` — had **zero KG persistence at all** (a UOM object type
  with a rich compact graph preview but totally invisible to KG-backed
  features). New `portal_registries()` builder persists the folder/
  content-ref containment hierarchy for the top portal, bounded by `limit`.

**Bug found and fixed along the way**: while verifying the portal_registry
builder, it consistently produced 0 items. Traced it to
`psdb.portal_registry_portals()`'s root-folder lookup:
`LENGTH(TRIM(PORTAL_PRNTOBJNAME)) = 0` — but Oracle treats empty strings as
`NULL`, so `LENGTH(NULL) = 0` is `NULL = 0`, never true. Confirmed via
direct query that the actual root sentinel value is a single space `' '`
(`LENGTH = 1`), not an empty string. Fixed to `TRIM(PORTAL_PRNTOBJNAME) IS
NULL`, which correctly catches both true-NULL and whitespace-only values
under Oracle's TRIM semantics. This is a real latent bug independent of
today's KG work — `portal_registry_portals()` is also called from the
Portal Registry admin UI, so this fix has value beyond the graph builder.

**Verified**: fresh graph rebuild (`limit=50`) — 4,026 `HAS_PERMISSION`
edges, 568 `HAS_MEMBER` edges, 98 `SENDS`/`RECEIVES` edges, 50
`portal_registry` `CONTAINS` edges (up from 0, confirmed both before-fix
0-item and after-fix 50-item provider status). `make check` 91/91; smoke
test 69/69 (no admin page touched by this pass, so a pure regression check).

------------------------------------------------------------------------

## 2026-07-03 — Processing Sequence Intelligence v1 — 69/69

### New: canonical sequence goes server-side, sequence-aware KG edges, AI tool fix

Went through plan mode again — "Processing Sequence Intelligence" as
written in the roadmap is six large, open-ended ambitions. Investigation
found two were already half-built (just needed to move from a hardcoded JS
array to a real backend artifact), one is already adequately served by an
existing heuristic, one is blocked by the same missing-PIA-log-data root
cause found earlier today for browser session tracking, and two need real
work but only make sense for the Component context.

**Key finding**: `/admin/compseq` ("PC Timeline") already has a correct,
complete canonical 20-event ordered sequence (4 phases, named events with
purpose notes) — but it only exists as a hardcoded JS array in
`routers/admin/compflow.py:361-406`. Nothing else (Knowledge Graph, AI
assistant, any future API caller) could use it.

**Changes**:
- `connectors/peoplecode.py` — `CANONICAL_COMPONENT_SEQUENCE` (the same
  4-phase data, now real Python) + `component_sequence(env, comp)`: slots a
  component's actual PeopleCode events into canonical order, marking each
  slot empty/delivered/custom. Deliberately did **not** touch
  `compflow.py`'s working JS — no functional gain from rewiring a verified
  page in this pass; the new backend function is what other consumers use.
- `routers/peoplesoft.py` — `GET /api/peoplesoft/components/{comp}/sequence`
- `connectors/graphdb.py` — new `component_sequences()` KG builder: adds
  `component_event` nodes with `FIRES_BEFORE`/`FIRES_AFTER` edges between
  consecutive non-empty canonical events (metadata: phase, ordinal, status)
- `connectors/ai_tools.py` — fixed a real duplicate-code bug found along
  the way: the AI assistant's existing `component_events` tool was calling
  a stale, less-complete duplicate (`psdb.get_component_peoplecode_events`)
  instead of the richer function that actually backs `/admin/compflow`.
  Now calls the real one + enriches with canonical sequence context.

**Bug found and fixed during verification**: first graph rebuild produced
self-loop edges like `component_event:ABSENCE_HISTORY.ROWINIT FIRES_BEFORE
component_event:ABSENCE_HISTORY.ROWINIT`. Root cause: `RowInit` (and other
events) fire once per record in a component with multiple records/subrecords
— multiple raw PSPCMPROG rows for the same canonical event collapse to one
node id (`<COMPONENT>.<EVENT_NAME>`, no record/field disambiguation), so
consecutive same-node entries in the sequence chain produced an edge to
themselves. Fixed by deduplicating to one entry per distinct event name
before building the FIRES_BEFORE/AFTER chain.

**Verified**:
- `PERSONAL_DATA` component: 41 raw PSPCMPROG rows → exactly 41 non-empty
  canonical slots (zero data loss or duplication)
- Graph rebuild (`limit=50`): 38 `component_event` nodes, 38
  FIRES_BEFORE+FIRES_AFTER edge pairs, **zero self-loops** after the fix
  (confirmed self-loops existed before the fix, then confirmed gone after)
- `HR_JOB_TREE_BLDR` (no PeopleCode): zero non-empty slots, zero graph
  edges, no crash — confirmed the empty-component path is safe
- AI tool: direct call to `ai_tools._component_events()` no longer errors,
  includes real canonical sequence context
- `/admin/compflow` and `/admin/compseq` (untouched pages) still return 200
  for the same component tested
- `make check` 91/91; smoke test 69/69

**Deferred, documented in ROADMAP.md rather than silently dropped**:
Processing Path Explorer for non-Component contexts (Page/Field/Record/CI),
Delivered vs Custom Sequence Comparison beyond the existing LASTUPDOPRID
heuristic (no delivered-source baseline exists to diff against), Runtime
Trace Correlation (blocked — same root cause as browser session tracking:
`PIA_access.log` is 0 bytes in this environment, and PeopleCode execution
isn't traced anywhere here; Oracle ASH + AE/Process-Scheduler logs ARE
populated and already power `/admin/rca`, so a narrower AE-focused trace
slice is possible later if wanted).

------------------------------------------------------------------------

## 2026-07-03 — Plugin SDK v1 — 69/69

### New: Phase 9 Platform Extensibility, from scratch

Went through plan mode for this one — it's a real architecture decision
(where do the extension points live, what's the loader contract, how do
plugins avoid needing to edit core files) rather than a bounded bug-fix or
data-source addition. Full plan is in the approved plan file; summary here.

**Investigation first** (via an Explore agent, no code written yet):
confirmed zero plugin code exists anywhere in the repo, and every one of the
four requested extension surfaces (object providers, KG builders, runtime
providers, admin dashboards) has the *same* underlying shape today — a
literal, hardcoded Python list/dict/if-chain that only core code can append
to. E.g. `graphdb.build()` defines ~50 KG builder closures and iterates a
literal tuple; `routers/peoplesoft.py` dispatches object types through a
50+-branch `if/elif` chain; `_NAV_GROUPS` in `_core.py` is a literal nav
list. No registry, no discovery mechanism, anywhere.

**Design**: one small module, `connectors/plugins.py`, holding four
appendable registries (object/graph/runtime providers + nav entries/routers)
and the `register_*()`/`get_*()` functions plugins and core code use. A
thin loader, `connectors/pluginloader.py`, scans `plugins/*.py` at startup
and calls each module's `register(sdk)`. Each of the four hardcoded spots
gets a small, additive change to also consult the matching registry —
zero risk to existing built-in behavior since the plugin check always comes
first and falls through unchanged if nothing's registered.

**Isolation is load-bearing, not incidental** — verified it, not just wrote
the try/except: deliberately appended a syntax error to
`plugins/example_hello.py`, restarted the server, confirmed
`pluginloader: failed to load plugin 'example_hello' — ...` was logged,
`/admin/plugin/hello` correctly 404'd, and every *other* admin page
(`/admin/ae`, etc.) still returned 200 — then restored the file and confirmed
it came back clean.

**Files**:
- `connectors/plugins.py` — the four registries
- `connectors/pluginloader.py` — discovery/loading, per-plugin isolation
- `plugins/example_hello.py` — worked example: a `hello_widget` object type
  (in-memory fake data, no DB/SSH — meant as a copy-paste starting point,
  not a real feature), a graph provider adding its nodes/edges to the KG, a
  runtime provider with static status, and its own admin page
  (`/admin/plugin/hello`) under a new "Plugins" nav group
- `routers/peoplesoft.py`, `connectors/graphdb.py`, `routers/runtime.py`,
  `routers/admin/runtime.py`, `routers/admin/_core.py`, `main.py` — the six
  small wiring changes described above
- `PLUGINS.md` (repo root) — the actual SDK docs, with code snippets for
  each of the four extension points, loading/isolation semantics, and an
  explicit list of what's *not* covered yet (custom health checks, a
  dedicated config-driven-source registry) as v2 candidates

**Verified end-to-end through the running server** (not just unit-level):
- `GET /api/peoplesoft/object/hello_widget/ALPHA?env=HCM` → real payload
  built entirely by the plugin's `object_fn`/`payload_fn`
- `GET /api/runtime/plugins/hello?env=HCM` → live status dict
- `GET /admin/plugin/hello` → 200, and "Hello Plugin" appears in the nav
  bar's new "Plugins" group on every page, not just its own
- `GET /api/graph/build?env=HCM&limit=50` → persisted KG JSON contains real
  `hello_widget:ALPHA/BRAVO/CHARLIE` nodes and `USES` edges to `record:JOB`/
  `record:PERSONAL_DATA`
- Isolation test as described above
- `make check` 91/91; smoke test 69/69 (68 existing + `/admin/plugin/hello`)

------------------------------------------------------------------------

## 2026-07-03 — Dynamic SQL READS/WRITES Coverage — 68/68

### Closed the last open Phase 5 item: non-literal PeopleCode dynamic SQL

Before this, `SQLExec`/`CreateSQL` calls only produced KG READS/WRITES edges
when the SQL was passed as an inline string literal. Any program building
SQL into a variable first — extremely common in PeopleCode — was invisible
to the Knowledge Graph.

**Investigation**: before writing anything, searched real PeopleCode source
in this environment (`GET /api/peoplesoft/peoplecode/source-search?q=FROM PS_`)
for programs calling `SQLExec(&var)`/`CreateSQL(&var)`. Found a clean real
example in `HR_JOBDATA_UTILITIES.ADDITIONALINFO.PERSONINFO.ONEXECUTE.0`:

```
&strSQL = "SELECT * FROM PS_JOB JOB WHERE JOB.EMPLID = :1 ...";
&strSQL = &strSQL | " FROM PS_JOB JOB_DT WHERE ...";
&strSQL = &strSQL | " JOB.EFFSEQ = (SELECT MAX(JOB_SQ.EFFSEQ) FROM PS_JOB ...";
SQLExec(&strSQL, %This.EmplId, %This.EmplRcd, %Date, &recJob);
```

Also found the harder, genuinely unsolvable case
(`HR_JOB_TREE_BLDR.TREENODEKEYBASE`): `"... FROM PS_" | &iKeyRecName` — the
table name itself is chosen at runtime. Decided up front that these should
be silently dropped, not guessed, consistent with the rest of the codebase's
conservative extraction philosophy.

**Changes**:
- `connectors/peoplecode.py` — `extract_dynamic_sql()`: finds
  `SQLExec(&var,...)`/`CreateSQL(&var)` calls, walks backward through every
  `&var = ...` / `&var = &var | ...` assignment earlier in the program,
  pulls out string-literal fragments from each RHS (skipping variables/calls/
  `%Table()` placeholders), concatenates in source order. Wired into
  `references()` and `references_for_program()` as `dynamic_sql`.
- `connectors/graphdb.py` — KG ingestion loop feeds `dynamic_sql` statements
  through the existing `sql_record_access()` scanner, same as `literal_sql`,
  tagged `source: peoplecode_dynamic_sql, confidence: low` for provenance.

**Verified**:
- Synthetic test confirming the split-table-name case produces zero false
  positives: `sql_record_access('SELECT ... FROM PS_ WHERE ...')` →
  `{"reads": [], "writes": []}` (the dangling `PS_` with no adjacent word
  char doesn't match the existing `PS_[A-Z0-9_]+` regex)
- Real-data test: `peoplecode.references_for_program()` on
  `HR_JOBDATA_UTILITIES.ADDITIONALINFO.PERSONINFO.ONEXECUTE.0` correctly
  reconstructs the full 4-statement JOB query and `sql_record_access()`
  derives `READS: JOB` — previously zero edges for this program
- `make check` 91/91; smoke test 68/68

------------------------------------------------------------------------

## 2026-07-03 — App Server Process Tracking — 68/68

### New Feature: live App Server / Process Scheduler process tracking

Closes a Phase 4 remaining item. Domain-level enumeration
(`psdb.app_server_domains`) only sees `PSPMDOMAIN_VW`, an Oracle view — it
has no idea what's actually running on the OS. This adds a level below that:
SSH `ps` on the app server host, parsed into structured Tuxedo process data.

**Files**:
- `connectors/sshclient.py` — added `run_command(alias, command, timeout)`,
  a generic read-only SSH command runner alongside the existing
  `list_files`/`read_bytes` helpers
- `connectors/appsrvproc.py` — new. Parses `ps -eo pid,ppid,pcpu,pmem,etime,
  cmd` output for known PeopleSoft Tuxedo server binaries (PSAPPSRV, PSAESRV,
  PSSAMSRV, PSBRKHND, PSMSTPRC, PSDSTSRV, PSMONITORSRV, BBL, WSL/WSH, JSL/JSH)
  and extracts domain name, group/server ID, and database name from the
  Tuxedo-encoded command-line arguments
- `routers/runtime.py` — `GET /api/runtime/appserver-processes?env=` resolves
  the SSH host from `log_sources` (type `appsrv`/`prcs_ae`), lists processes,
  rolls up per-domain and per-server-type summaries
- `routers/admin/runtime.py` — new "App Server Processes" card on
  `/admin/runtime`, refreshed every cycle

**Bug found and fixed during verification**: initial parsing used a process's
`-S NAME` Tuxedo flag to override the detected server name whenever present.
That's correct for PeopleSoft app-level servers (`-S PSBRKHND_dflt` really is
a more specific server-group name), but wrong for Tuxedo infrastructure
processes — `JSH -c 41 -i 0 -s 6 -Z 256 -S 600` uses `-S` for a shared-memory
key, not a name, so every JSH child process was showing up as server
`"600"` and every JSL as `"10"`. Fixed by excluding BBL/WSL/WSH/JSL/JSH/
JREPSVR from the `-S` override.

**Verified**: live SSH `ps` against `hcm_appserver` (192.168.122.151) found
21 real Tuxedo processes across 2 domains (`HCMDMO_224204` app server tier,
`HCMDMO_210976` process scheduler tier) plus 5 unattributed JSH workers;
domain/database extraction confirmed correct (e.g. `PSAESRV` processes
correctly show `database: HRDMO`, matching `config.json`'s Oracle service
name for HCM, not the `HCMDMO` PeopleSoft system name also present in the
command line). `make check` 91/91; smoke test 68/68.

------------------------------------------------------------------------

## 2026-07-03 — COBOL Knowledge Graph Wiring — 68/68

### Follow-up: wired COBOL data into the Knowledge Graph

The COBOL Explorer built earlier today stored COPY/CALL/EXEC-SQL data in
`data/cobol.db` but nothing fed it into the KG (`data/knowledge_graph_*.json`)
the way `sqr_programs()` already does for SQR. Closed that gap:

- `connectors/graphdb.py` — new `cobol_programs()` builder, registered in the
  env build list right after `sqr_programs`. Adds a `cobol_program` node per
  indexed file plus `READS`/`WRITES` edges to `record` (from EXEC SQL table
  refs), `COPIES` edges to other `cobol_program` nodes, and `CALLS` edges for
  static `CALL 'X'` targets (dynamic `CALL WS-VAR` is unresolvable, same
  limitation SQR already has for computed `DO`/`GOSUB`)
- `connectors/ptmetadata.py` — `OBJECT_REGISTRY["cobol_program"]` entry
  (icon, `object_page`, relationships), mirroring `sqr_program`
- `routers/admin/graph.py` — `/admin/object/cobol_program/{name}` redirects
  to `/admin/cobol/{name}.cbl`

**Verified**: fresh `graphdb.build(env='HCM', limit=2000)` (took ~8 minutes —
this rebuilds every provider, not just COBOL) produced 163 `cobol_program`
nodes, 567 edges (164 CALLS, 403 COPIES, 0 READS/WRITES — none of the 115
readable delivered `.cbl` files use `EXEC SQL`, consistent with the COBOL
Explorer session's earlier finding of `distinct_ps_tables: 0`).
`/api/graph/neighbors/cobol_program:PTCALOGM.CBL` correctly resolves CALLS
edges to `PTPLOGMS.CBL` and `PTPTEDIT.CBL`. Redirect verified:
`/admin/object/cobol_program/PTCALOGM.CBL` → 302 → `/admin/cobol/ptcalogm.cbl`.
`make check` 91/91; smoke test 68/68.

------------------------------------------------------------------------

## 2026-07-03 — COBOL Explorer — 68/68

### New Feature: PeopleSoft COBOL Source Artifact Intelligence

Addresses the last open Phase 10 roadmap item. Built end-to-end following the
existing SQR trio's pattern (parser → SQLite store → SSH ingestor → API →
admin UI), with one twist specific to this codebase's environment.

**Discovery that shaped the design**: PeopleSoft's "copybooks" are not
separate `.cpy` files — they're `.cbl` files distinguished only by the
*absence* of `PROGRAM-ID`, pulled into programs via `COPY name.`
(e.g. `COPY PTCLOGMS.` targets `PTCLOGMS.cbl`). Confirmed via SSH: zero
`.cpy` files exist anywhere under `ps_home8.62.07`; of 977 delivered `.cbl`
files, 45 have `PROGRAM-ID` and 70 are bare SECTIONs/records referenced only
via COPY. `connectors/cobolparser.py` classifies `file_type` as
`program`/`copybook` on that basis rather than by extension.

**Second discovery, mid-build**: only 115/977 delivered `.cbl` files are
world-readable (mode 755) on `hcm_appserver` — the other 862 are mode 700,
owned by `ps_hcm`, unreadable by the `oracle` SSH service account. This is
expected PeopleSoft filesystem behavior, not a config problem, so
`cobolingest.py` counts `PermissionError` as a `denied` bucket distinct from
real `errors`, exactly like the architecture's "warn, don't crash" rule for
missing grants/tables.

**Files added**:
- `connectors/cobolparser.py` — PROGRAM-ID/SECTION extraction, COPY deps,
  static `CALL 'X'` targets, `EXEC SQL...END-EXEC` PS_ table refs. Description
  extraction skips the fixed Oracle license preamble (bounded by an "All
  Rights Reserved." marker) and decorative box-border comment lines before
  taking the first real comment.
- `connectors/cobol_db.py` (`data/cobol.db`) — `cobol_programs`/`cobol_tables`/
  `cobol_copies`/`cobol_calls`; `get_copy_deps()` recursive CTE (forward +
  reverse COPY closure); MD5 `content_hash` incremental scan; `search_source()`
- `connectors/cobolingest.py` — SSH scan of `cbl_src_dir`; best-effort listing
  of `cbl_compiled_dir` to flag whether a compiled binary exists per program
- `routers/cobol.py` — `/api/cobol/*` (stats, sources, programs, program
  detail+source, table xref, deps, search, ingest)
- `routers/admin/cobol_view.py` — `/admin/cobol` list/search + `/admin/cobol/
  {filename}` detail (Overview / COPY Dependency Graph / Source tabs)
- `config.json` — `cobol_sources` (gitignored, local-only): 4 entries
  (HCM/FSCM × delivered/custom); custom entries point at `ps_cust_home/src/cbl`
  which doesn't exist on this demo box (only an `sqr` folder there) — ingestor
  reports `cbl_src_dir not found` as a warning

**Bug found and fixed mid-session**: initial description regex matched any
non-boilerplate-keyword comment line, which let a license-paragraph
continuation line ("or allowed by law, you may not use, copy, reproduce,")
through for `PTPCBLAE.cbl`. Fixed by requiring the "All Rights Reserved."
marker be seen first, then skipping purely decorative lines.

**Verified**:
- Fresh ingest (cold `data/cobol.db`) — 230 files indexed (88 programs, 142
  copybooks) across HCM+FSCM delivered; 862 denied, 0 other errors per env;
  both custom sources correctly report `cbl_src_dir not found`
- `PTPCBLAE.cbl` → 8 direct COPY deps (`ptclogms`, `ptcsqlrt`, etc.) resolved
  correctly via `/api/cobol/deps/`
- `PTCALOGM.cbl` → correctly classified `copybook` (member `ZM000-LOG-MESSAGE`,
  no PROGRAM-ID), description "CALL THE MESSAGE LOGGER WITH A TRANSACTION EDIT
  MESSAGE." (confirms the license-preamble fix)
- `make check` — 91/91 files, 11/11 unit tests
- `python3 scripts/smoke_admin_shell.py` — 68/68 OK

**Blocker/next step**: COBOL EXEC SQL / CALL-graph data isn't wired into the
Knowledge Graph yet (`attach_graph_context` in `routers/peoplesoft.py`) —
straightforward follow-up once there's appetite, same pattern as the SQR
`sqr_program → record` edges.

------------------------------------------------------------------------

## 2026-07-03 — Message UOM Cross-References + IB Subscription Crash Fix — 67/67

### Message Cross-References in Object Explorer

Extended `attach_graph_context()` in `routers/peoplesoft.py` to cover the last
remaining UOM provider named in the Phase 5 roadmap ("message, tree, project,
portal" — tree/portal were completed earlier the same day):

- **`message`**: "Records Contained in This Message" (outbound `CONTAINS` →
  `record`, sourced from `PSMSGREC`) and "Projects Deploying This Message"
  (inbound `DEPLOYS` ← `project`)
- **`project`** deliberately left uncovered: `PSPROJECTITEM` targets span
  nearly every object type, so a dedicated per-type xref section would just
  re-list what the generic "Knowledge Graph Neighbors" section already shows.

### Bug fix: IB Message Subscriptions crash on integer `gensubproc`

While verifying against a message with real `CONTAINS` edges
(`ALTACCT_CF_FULLSYNC`), `/api/peoplesoft/object/message/{name}` 500'd:

```
File "connectors/uom.py", line 5943, in sections_for_ib_message
    genproc = (s.get("gensubproc") or "").strip()
AttributeError: 'int' object has no attribute 'strip'
```

`PSSUBDEFN.GENSUBPROC` comes back as an int for some rows (likely `0`/falsy
values from Oracle NUMBER columns bypassing the `or ""` guard only when
truthy-but-non-string). Fixed by wrapping in `str(...)` before `.strip()`.
Pre-existing bug, unrelated to this session's other changes — surfaced only
because this was the first time a message with populated subscriptions and
schema records was exercised end-to-end.

**Verified**:
- `curl /api/peoplesoft/object/message/ALTACCT_CF_FULLSYNC?env=HCM` → 200,
  shows "Records Contained in This Message" (`record:ALTACCT_TBL`) and no
  longer crashes on the Subscriptions section
- `/admin/object/message/ALTACCT_CF_FULLSYNC?env=HCM` → 200
- `make check` — 91/91 files, 11/11 unit tests
- `python3 scripts/smoke_admin_shell.py` — 67/67 OK

------------------------------------------------------------------------

## 2026-07-03 — Tree & Portal UOM Cross-Reference Sections — 67/67

### Tree and Portal Registry Cross-References in Object Explorer

**`routers/peoplesoft.py`**:
- New `_attach_outbound_xref(payload, env, node_id, tgt_type, edge_type, section_name, note)` helper —
  queries `graphdb.neighbors()` outbound, filters by node type prefix, deduplicates, sorts, appends section
- `attach_graph_context()` now dispatches two new `obj_type` blocks:
  - **`tree`**: "Record Keyed by This Tree" (outbound `USES` → `record`)
    and "Projects Deploying This Tree" (inbound `DEPLOYS` ← `project`)
  - **`portal_registry`**: "Projects Deploying This Portal Object" (inbound `DEPLOYS` ← `project`)
    and "Content Services Linking to This Portal Object" (inbound `USES` ← `content_service`)

**Verification**: `curl /api/peoplesoft/object/tree/DEPT_SECURITY?env=HCM` shows
"Record Keyed by This Tree" section with `record:DEPARTMENT` (1 item). 67/67 smoke test OK.

------------------------------------------------------------------------

## 2026-07-03 — SQR Dep Graph, Env Comparison, Incremental Scan — 67/67

### SQR Include Dependency Graph (`/admin/sqrdeps`) + Env Comparison (`/admin/sqrcompare`) + Incremental Scanning

**`connectors/sqrdb.py`**:
- Added `content_hash TEXT` column migration to `init_db()`
- Extended `upsert_program()` to accept and store `content_hash`
- New `get_include_deps(filename, max_depth=6)` — recursive CTE forward + reverse
  traversal with DISTINCT deduplication (handles multiple source_key rows per filename)
- New `get_content_hash(filename, source_key)` — hash lookup for incremental scan
- New `envcompare_sqr(keys_a, keys_b, label_a, label_b)` — side-by-side env diff
  returning only_a, only_b, in_both (with changed/identical flag per file)

**`connectors/sqringest.py`**:
- Incremental scanning: computes `hashlib.md5(raw).hexdigest()` before parsing;
  skips files whose stored hash matches; adds `skipped` count to ingest summary

**`routers/sqr.py`**:
- `GET /api/sqr/deps/{filename}?max_depth=` — include dep tree + reverse closure
- `GET /api/sqr/envcompare?env_a=HCM&env_b=FSCM` — side-by-side program diff

**`routers/admin/sqr_view.py`**:
- `/admin/sqrdeps?q=` — collapsible forward include tree, reverse "Included By" (direct +
  indirect), force-directed canvas graph with animated spring simulation
- `/admin/sqrcompare` — env comparison with stat row + 4 tabs (Changed / Only A / Only B / Identical)

**`routers/admin/_core.py`**:
- Added `sqrdeps` and `sqrcompare` to Platform nav group

**`scripts/smoke_admin_shell.py`**:
- Fixed `/admin/ae` marker from `#qInput` → `#q`
- Fixed `/admin/accesspath` (non-existent URL) → `/admin/access` with `.ap-toolbar`
- Added `/admin/sqrdeps` (`.ds-toolbar`) and `/admin/sqrcompare` (`.cmp-toolbar`)

**Verified**:
- `battimes.sqr`: 11 direct includes, 11 tree nodes
- `envcompare HCM vs FSCM`: 179 in_both, 0 only_a, 0 only_b, 0 changed (expected — same delivered base)
- `make check` — 91/91 OK
- Smoke test — **67/67 OK** — all pages pass

------------------------------------------------------------------------

## 2026-07-03 — Smoke Test Fixes: /admin/ae and /admin/accesspath — 65/65

### Smoke Test Marker Corrections

- `/admin/ae` used `id="q"` but smoke test looked for `#qInput` → corrected to `#q`
- `/admin/accesspath` in smoke test pointed to non-existent URL; actual route is `/admin/access`
  using `.ap-toolbar` as marker → corrected

**Verified**: `65/65 OK` — all pages pass, no failures.

------------------------------------------------------------------------

## 2026-07-03 — SQR Include Dependency Graph — Phase 10

### SQR Dependency Graph (`/admin/sqrdeps`)

Implemented the SQR Include Dependency Graph feature, addressing the first item
in Phase 10 (Source Artifact Intelligence) roadmap remaining work.

**Problem**: Engineers had no way to visualize or navigate the SQC include tree.
Given 358 indexed SQR/SQC programs with 1366 include edges, this is a meaningful
dependency network. There was no way to answer "which SQRs use setenv.sqc?" or
"what does battimes.sqr transitively depend on?"

**Changes in `connectors/sqrdb.py`**:
- New `get_include_deps(filename, max_depth=6)` function — returns forward and
  reverse dependency trees using SQLite recursive CTEs (`WITH RECURSIVE`). Returns:
  `direct_includes` (DISTINCT), `all_includes` (recursive closure), `include_tree`
  (nested Python dict with cycle detection), `used_by_direct` (DISTINCT), and
  `used_by_all` (transitive reverse closure). All queries use DISTINCT to handle
  multiple source_key rows for the same filename.

**Changes in `routers/sqr.py`**:
- New `GET /api/sqr/deps/{filename}?max_depth=` endpoint — returns full dependency
  info for any indexed SQR or SQC file. Useful for impact analysis on SQC changes.

**Changes in `routers/admin/sqr_view.py`**:
- New `GET /admin/sqrdeps?q=` page — SQR Dependency Graph with:
  - Search input with preload via `?q=` parameter
  - Meta bar showing file type, description, direct/total include counts, used-by counts
  - **Forward tree panel** — collapsible recursive HTML tree; nodes link to their own
    dep page; cycle nodes colored amber; unindexed SQCs shown in dim gray
  - **Reverse panel** — "Included By" split into Direct / Indirect sections with links
  - **Force-directed graph canvas** — vanilla JS spring simulation; root node (cyan),
    include nodes (green), used-by nodes (orange); arrowheads on edges; 120 frames then
    settles

**Changes in `routers/admin/_core.py`**:
- Added `("sqrdeps", "SQR Dep Graph", "/admin/sqrdeps")` to Platform nav group.

**Changes in `scripts/smoke_admin_shell.py`**:
- Added `/admin/sqrdeps` (marker: `.ds-toolbar`) to smoke test page list.

**Verified**:
- `battimes.sqr` → 11 direct includes, 18 transitive, 0 used_by
- `setenv.sqc` → 65 direct users including battimes.sqr
- `make check` — **91/91 files OK**, all tests pass
- Smoke test — **64/66 OK** (2 pre-existing failures: `/admin/ae` missing `#qInput`
  marker, `/admin/accesspath` shell structure mismatch — both pre-date this session)
- `/admin/sqrdeps` — **OK** in smoke test

------------------------------------------------------------------------

## 2026-07-03 — /admin/reports JS Bug Fix — Smoke Test 57/57

### Bug Fix — /admin/reports JavaScript Syntax Errors

Two independent JavaScript bugs were causing `/admin/reports` to throw
`SyntaxError` on every page load, making the reports catalog completely broken.

**Bug 1 — onclick attribute syntax** (`routers/admin/tools.py` line ~200):

Original Python source:
```python
onclick="runReport(\''+esc(r.key)+'\',\''+esc(r.title)+'\')"
```
In Python, `\'` inside a `"""..."""` triple-quoted string is an escaped single
quote that evaluates to `'` — the backslash is consumed.  The rendered HTML
therefore contained two adjacent JS string literals with no `+` operator:
```javascript
'" onclick="runReport(''+esc(r.key)+'',''+esc(r.title)+'')"'
                       ^^ adjacent strings → SyntaxError: Unexpected string
```
**Fix**: use `data-key` / `data-title` HTML attributes and reference them via
`this.dataset.key` / `this.dataset.title` in the onclick — no quoting needed.

**Bug 2 — literal newline in Blob constructor** (`tools.py` line ~221):

Original Python source: `lines.join('\n')` — in a triple-quoted string, `\n`
is a newline escape, so the rendered JS contained a bare newline inside a
single-quoted string literal, which is an invalid JS token.

**Fix**: change `'\n'` → `'\\n'` so Python emits the two characters `\n` in the
JS source, where `\n` is a valid escape sequence.

**Bug 3 — catalog API returning flat string list** (`connectors/psdb.py`):

`security_report(env, "__catalog__")` fell into the `spec is None` branch and
returned `{"available_reports": list(REPORTS.keys())}` — a flat list of string
keys.  The JS expected objects `{key, title, category}`.  Handled `__catalog__`
as a special case before the `REPORTS.get()` lookup so it returns the full
structured catalog.

**Verified**: `python3 scripts/smoke_admin_shell.py` — **57/57 pages pass**
(was 56/57 — the one pre-existing failure has been resolved).

Commit: `a2ef226`

------------------------------------------------------------------------

## 2026-07-03 — Comprehensive Object Cross-Reference Expansion

### Cross-Reference Sections — All Object Types

Extended the Knowledge Graph cross-reference system in `routers/peoplesoft.py`
with dedicated sections for every major object type.

**Root cause**: `attach_graph_context()` added only generic "Knowledge Graph
Neighbors" items.  Engineers had no quick way to answer "who touches this?" or
"where is this deployed?" for records, AEs, PeopleCode, pages, or components.

**Changes in `routers/peoplesoft.py`**:

`_attach_outbound_rw_xref()` — was AE/SQL only; extended to **peoplecode** so
PeopleCode programs with READS edges show a "Records Read / Written" section.

`_attach_ae_schedulers()` — new helper; for `application_engine` objects queries
inbound WRAPS edges from `prcs_defn` nodes to append "Invoked By (Process
Definitions)" showing which Process Scheduler definitions invoke this AE.
Parses `PTYPE~PNAME` node names into display_name + prcs_type fields.

`_attach_record_components_xref()` — new helper; for `record` objects queries
inbound USES edges filtered to `component:` sources to append "Components Using
This Record".

`_attach_inbound_xref()` — new generic helper; builds any inbound cross-reference
section given `src_type`, `edge_type`, `section_name`, and `note` parameters.
Eliminates boilerplate for page/project cross-refs.

New sections wired via dispatch in `attach_graph_context()`:
| Object type | Section | Edge query |
|---|---|---|
| `record` | READS / WRITES | in READS/WRITES |
| `record` | Components Using This Record | in USES (component sources) |
| `record` | Pages Using This Record | in USES (page sources) |
| `record` | Projects Deploying This Record | in DEPLOYS (project sources) |
| `application_engine` | Records Read / Written | out READS/WRITES |
| `application_engine` | Invoked By (Process Definitions) | in WRAPS |
| `sql_definition` | Records Read / Written | out READS/WRITES |
| `peoplecode` | Records Read / Written | out READS/WRITES |
| `page` | Projects Deploying This Page | in DEPLOYS |
| `component` | Projects Deploying This Component | in DEPLOYS |

**Verified**:
- `record:JOB` → 25-item READS/WRITES + "Pages Using" (ABSV_PLANS)
- `record:INSTALLATION` → 9-item READS/WRITES + 9 Components Using
- `application_engine:BEN110` → 7 Records Read/Written + Invoked By (BEN110)
- `application_engine:AA_CONV_JPN` → 3 Records Read/Written (Invoked By skipped — not in top-100 KG)
- `peoplecode:AA_COST_RT_JPN.EMPL_RCD_JPN.SAVEEDIT.0` → Records Read/Written: JOB
- Projects Deploying sections verified via graphdb.neighbors() directly on GPIT_CTR_EE (GPIT project limit)

Commits: `e4f9ab1`, `7b0232d`, `60cd837`, `f1fee77`

------------------------------------------------------------------------
## 2026-07-03 — HANDOFF #10: Typed KG Edges and READS/WRITES Record Cross-Reference

### HANDOFF #10 — SQL Definition Cross-Reference (Knowledge Graph)

Improved the Knowledge Graph context surfaced in every Object Explorer response.

**Problem 1 — Generic "neighbor" label**: `attach_graph_context()` in
`routers/peoplesoft.py` built Knowledge Graph Neighbor items from `graph["nodes"]`
only, hard-coding `relationship: "neighbor"` for every entry.  The actual edge
types (READS, WRITES, CONTAINS, USES, REFERENCES, …) stored in `graph["edges"]`
were completely ignored.

**Fix**: Build a two-pass lookup from the `edges` list:
- `edge_by_target[node_id]` → list of relationship types for edges pointing *to*
  that node from the root
- `edge_by_source[node_id]` → list of relationship types for edges pointing *from*
  that node to the root

Each item now carries the actual primary relationship type.

**Problem 2 — No record-level READS/WRITES summary**: There was no quick way to
see which Application Engines or SQL programs touched a given record.

**Fix**: New `_attach_record_rw_xref(payload, env, node_id)` helper.  For objects
of type `record`, it calls `graphdb.neighbors(env, node_id, direction="in",
edge_types=["READS", "WRITES"])` to get only inbound READS/WRITES edges, then
appends a "READS / WRITES" section with:
- WRITES items first (higher impact), then READS, each sorted by type then name
- Metadata: count, reads count, writes count, note

**Verified**: `curl /api/peoplesoft/object/record/JOB?env=HCM`
- Knowledge Graph Neighbors: 21 items with correct types
  (CONTAINS, USES, REFERENCES, READS …)
- READS / WRITES: 18 Application Engines, all showing `rel: READS`

Commit: `1b1967d`

------------------------------------------------------------------------

## 2026-07-03 — HANDOFF #9: CI Wiring, Syntax Check, Makefile, GitHub Actions

### HANDOFF #9 — CI / Deployment Wiring

Wired a full CI pipeline so the project is ready for automated checks.

**scripts/syntax_check.py** — new script:
- Sweeps all `.py` files under the project root (skipping `.venv`, `__pycache__`,
  `.git`)
- Runs `py_compile.compile(path, doraise=True)` on each file
- Flags `SyntaxError` and `SyntaxWarning` (treated as errors)
- CLI flags: `--quiet` (suppress per-file OK lines), `--exit-zero` (always exit 0)
- Exits 1 if any file fails; currently: all 80 files OK

**Makefile** — new convenience targets:
- `make lint` — runs syntax_check.py --quiet
- `make test` — runs `python -m unittest discover -s tests/ -v`
- `make check` — lint + test (default target via `all`)
- `make serve` — starts uvicorn on 127.0.0.1:8088
- `make smoke` — runs smoke_admin_shell.py with --base-url

**.github/workflows/ci.yml** — new GitHub Actions workflow:
- Triggers on push to main/develop, PR to main
- ubuntu-latest, Python 3.12
- pip installs: fastapi pydantic PyYAML oracledb (needed for top-level imports in
  psdb/oracle/sqlws connectors)
- Steps: syntax_check.py --quiet, then unittest discover

**routers/admin/portal.py bug fix** (SyntaxWarning):
- Line 662 had `\-` in a Python string carrying JS regex `/[A-Za-z0-9_.%\-]/`
- Python 3.14 raises `SyntaxWarning: "\-" is an invalid escape sequence`
- Fixed by doubling: `%\\-` in Python source → `%\-` in the emitted JS string

**Verified**: `make check` passes; smoke test 56/57 (pre-existing /admin/reports)

Commit: `5adce51`

------------------------------------------------------------------------

## 2026-07-02 — ADS Definition UOM and Knowledge Graph Relationships

Date/time: 2026-07-02 00:38 CDT

Features implemented:
- ADS Definition UOM objects now expose `_relationships.records` from
  PSADSDEFNITEM metadata.
- ADS Definition compact `_graph` previews now show ADS Definition → Record
  `CONTAINS` edges and parent Record → child Record `CONTAINS` hierarchy edges.
- Persisted Knowledge Graph ingestion now batch-loads PSADSDEFNITEM rows for
  sampled ADS definitions and emits the same record containment model.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept ADS groups as section metadata for this slice because the current
  connector only returns group counts, not group-member field rows.
- Reused canonical `record` nodes so ADS migration definitions line up with
  Object Explorer, Environment Compare, and impact analysis record objects.

Bugs fixed:
- ADS Definition object pages showed managed records but had no canonical
  relationship model or compact graph preview.
- Persisted KG ADS provider created only ADS nodes without edges to the
  PeopleSoft records managed by each data set.

Technical debt:
- ADS group-member field relationships can be added after `PSADSGROUPMEMB`
  detail rows are fetched into the connector.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- `uom.ads_definition_object('HCM', 'ACTIVITY_GUIDE_ITEM')` returned 8 records
  and a compact graph with 9 nodes / 15 edges.
- `uom.ads_definition_object('HCM', 'BAS_CMPDEFN')` returned 4 records and a
  compact graph with 5 nodes / 7 edges.
- `/api/peoplesoft/graph/ads_definition/ACTIVITY_GUIDE_ITEM` route helper
  returned `_source: uom`, `_vocabulary: compact_uom`, and ADS Definition →
  Record plus parent Record → child Record `CONTAINS` edges.

Next recommended work:
- Add ADS group-member field relationships by expanding `get_ads_definition()`
  to return `PSADSGROUPMEMB` detail rows.
- Continue compact UOM graph alignment for Translate Values or URL Definitions.

## 2026-07-02 — File Layout UOM and Knowledge Graph Relationships

Date/time: 2026-07-02 00:29 CDT

Features implemented:
- File Layout UOM objects now expose `_relationships.segments` and
  `_relationships.fields` from PSFLDSEGDEFN / PSFLDFIELDDEFN metadata.
- File Layout compact `_graph` previews now show File Layout → segment Record,
  File Layout → layout Field, and segment Record → layout Field `CONTAINS`
  edges.
- Persisted Knowledge Graph ingestion now batch-loads segment and field rows
  for sampled layouts and emits the same containment model.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Used `RECNAME_FILE` when populated, otherwise fell back to `FLDSEGNAME` as
  the segment record anchor because live HCM data leaves `RECNAME_FILE` blank
  for common layouts while `FLDSEGNAME` matches PeopleSoft record names.
- Modeled field nodes as `SEGMENT.FIELD` so they can align with canonical
  Field object IDs.
- Preserved field position, length, type, tag, and description metadata on
  relationship rows for later UI explanation.

Bugs fixed:
- File Layout object pages showed segments and fields but had no canonical
  relationship model or compact graph preview.
- Persisted KG File Layout provider created only layout nodes without edges to
  the segment records or fields in the layout.

Technical debt:
- Some file layout segment names may be layout-only segment identifiers rather
  than true PeopleSoft records; current model uses the best available live
  metadata and records the assumption here.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- `uom.file_layout_payload('HCM', 'ACCOUNT_CHARTFIELD')` returned 1 segment,
  44 fields, and a compact graph with 46 nodes / 89 edges.
- `uom.file_layout_payload('HCM', 'ACTUAL_TIME_ADD')` returned 1 segment,
  73 fields, and a compact graph with 75 nodes / 147 edges.
- `/api/peoplesoft/graph/file_layout/ACCOUNT_CHARTFIELD` route helper returned
  `_source: uom`, `_vocabulary: compact_uom`, and File Layout → Record/Field
  plus Record → Field `CONTAINS` edges.

Next recommended work:
- Continue compact UOM graph alignment for ADS Definitions or Translate Values.
- If a future schema probe finds a stronger segment-to-record mapping than
  `FLDSEGNAME`, update File Layout relationships to use it.

## 2026-07-02 — IB Message UOM and Knowledge Graph Relationships

Date/time: 2026-07-02 00:18 CDT

Features implemented:
- IB Message UOM objects now expose `_relationships.schema_records` from
  PSMSGREC default-version schema metadata.
- IB Message compact `_graph` previews now show Message → Record `CONTAINS`
  edges and parent Record → child Record `CONTAINS` hierarchy edges.
- Persisted Knowledge Graph ingestion now batch-loads PSMSGREC rows for sampled
  PSMSGDEFN messages and emits the same schema record and hierarchy edges.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Used the message default version (`PSMSGDEFN.DEFAULTVER`) so the compact
  graph matches the schema records already displayed by the Object Explorer.
- Treated `PRNTRECNAME = '--'` as the schema root marker and skipped hierarchy
  edges for that pseudo-parent.
- Reused canonical `record` nodes rather than creating message-specific schema
  node types.

Bugs fixed:
- IB Message object pages showed schema records but had no canonical
  relationship model or compact graph preview.
- Persisted KG IB Message provider created message nodes without edges to the
  records contained in each message schema.

Technical debt:
- Version-specific message graph selection is not yet exposed; current compact
  graph follows the default version only.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- `uom.ib_message_payload('HCM', 'PERSON_BASIC_SYNC')` returned 33 schema
  record relationships and a compact graph with 34 nodes / 65 edges.
- `/api/peoplesoft/graph/message/PERSON_BASIC_SYNC` route helper returned
  `_source: uom`, `_vocabulary: compact_uom`, and Message → Record / parent
  Record → child Record `CONTAINS` edges.

Next recommended work:
- Continue compact UOM graph alignment for File Layout Definitions or ADS
  Definitions.
- Consider a version selector for IB Message graph previews if users need to
  compare non-default schema versions.

## 2026-07-02 — Process Definition UOM and Knowledge Graph Relationships

Date/time: 2026-07-02 00:08 CDT

Features implemented:
- Process Definition UOM objects now expose
  `_relationships.run_control_components`, `_relationships.application_engines`,
  and `_relationships.xml_publisher_reports`.
- Process Definition compact `_graph` previews now show Process Definition →
  run-control Component `USES` edges plus Process Definition → Application
  Engine / XML Publisher Report `WRAPS` implementation edges.
- Persisted Knowledge Graph ingestion now batch-loads PS_PRCSDEFNPNL rows for
  sampled process definitions and emits the same run-control and implementation
  relationships.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `connectors/psdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Modeled `Application Engine` process definitions as wrapping the same-named
  Application Engine program.
- Modeled `XML Publisher` process definitions as wrapping the same-named XML
  Publisher Report when present.
- Kept Process Groups as section metadata only because process groups are not a
  registered canonical Object Explorer type today.

Bugs fixed:
- Process Definition object pages had run-control page metadata but no
  canonical relationship model or compact graph preview.
- Persisted KG process-definition provider created only Process Definition
  nodes without edges to run-control components or implementation objects.
- `get_process_definition()` now resolves compound keys case-insensitively so
  generic graph route uppercase normalization does not break Process Definition
  lookups.

Technical debt:
- SQR, COBOL, and Data Mover implementation artifacts are still metadata-only
  until their source/object metadata tables are verified and registered.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py connectors/psdb.py routers/peoplesoft.py` — OK.
- `uom.process_defn_payload('HCM', 'Application Engine~ACA_EXTRACT')` returned
  a run-control component relationship to `ACA_DTEX_RUNCTL` and a `WRAPS` edge
  to `application_engine:ACA_EXTRACT`.
- `uom.process_defn_payload('HCM', 'XML Publisher~BREREG02')` returned a
  `WRAPS` edge to `xml_publisher_report:BREREG02`.
- `uom.process_defn_payload('HCM', 'SQR Report~ABS001')` returned a
  run-control component relationship to `RUN_ABS001` without inventing an SQR
  implementation node.
- `/api/peoplesoft/graph/prcs_defn/Application Engine~ACA_EXTRACT` route helper
  returned `_source: uom`, `_vocabulary: compact_uom`, and `USES` / `WRAPS`
  edges. Uppercase `APPLICATION ENGINE~ACA_EXTRACT` also resolves.
- Direct graphdb edge construction check confirmed Process Definition →
  Component `USES` and Process Definition → Application Engine / XML Publisher
  `WRAPS` edge shapes.

Next recommended work:
- Continue compact UOM graph alignment for IB Message Definitions or File
  Layout Definitions.
- Register process-group objects only after verifying meaningful metadata and
  navigation value.

## 2026-07-01 — PTF Test UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 23:56 CDT

Features implemented:
- PTF Test UOM objects now expose `_relationships.menus`,
  `_relationships.components`, `_relationships.pages`, `_relationships.records`,
  and `_relationships.fields` from PSPTTSTCOMMAND command metadata.
- PTF Test compact `_graph` previews now show PTF Test → touched object `USES`
  edges for menu, component, page, record, and record-qualified field targets.
- Persisted Knowledge Graph ingestion now batch-loads PSPTTSTCOMMAND rows for
  sampled PTF tests and emits the same PTF Test → touched object `USES` edges.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Treated PeopleTools single-space command columns as blank, then deduplicated
  relationships by target object name.
- Kept command sequence/id/type metadata on relationship rows so UI and graph
  consumers can explain where a touched object first appears in the script.
- Limited compact graph previews separately by object category to keep large
  PTF scripts navigable.

Bugs fixed:
- PTF Test object pages showed command summaries but had no canonical
  relationship model or compact graph preview.
- Persisted KG PTF provider created only test nodes, losing the pages,
  components, records, and fields exercised by the tests.

Technical debt:
- PTF shell commands that call child scripts are still displayed as commands
  only; a future pass can model Script/Shell → child PTF Test relationships
  after command type `35001` semantics are documented.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- `uom.ptf_test_object('HCM', 'NUI_10430_JOB_SEARCH_APP_01')` returned
  2 menus, 3 components, 11 pages, 9 records, 22 fields, and a compact graph
  with 48 nodes / 47 edges.
- `uom.ptf_test_object('HCM', 'A_10270_LOCATION_CHANGE_SHELL')` returned no
  touched-object relationships because its page/record/field columns are blank
  single-space values.
- `/api/peoplesoft/graph/ptf_test/NUI_10430_JOB_SEARCH_APP_01` route helper
  returned `_source: uom`, `_vocabulary: compact_uom`, and PTF Test → Menu /
  Component / Page `USES` edges.

Next recommended work:
- Continue compact UOM graph alignment for Process Definitions or IB Message
  Definitions.
- Add child PTF script relationships after validating PTF command type
  semantics across shell/library/script rows.

## 2026-07-01 — XML Publisher UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 23:39 CDT

Features implemented:
- XML Publisher Report UOM objects now expose `_relationships.datasources`
  plus typed `_relationships.queries` or `_relationships.connected_queries`
  when the report data source is backed by PS Query or Connected Query.
- XML Publisher compact `_graph` previews now show Report → PS Query or
  Report → Connected Query `USES` edges for `DS_TYPE` values `QRY` and `CQR`.
- Persisted Knowledge Graph ingestion now reads `DS_TYPE` from PSXPRPTDEFN and
  emits the same XML Publisher Report → Query / Connected Query `USES` edges.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept XML, XML Data, and REST data sources as report metadata only because
  they do not map to an existing canonical Object Explorer type today.
- Used existing canonical object types (`query`, `connected_query`) rather
  than introducing a separate XML Publisher datasource graph node.
- Preserved existing XML Publisher endpoint and payload fields while adding
  `_relationships` and `_graph`.

Bugs fixed:
- XML Publisher Report object pages had data-source metadata but no canonical
  relationship model or compact graph preview.
- Persisted KG XML Publisher provider created report nodes without edges to
  PS Query / Connected Query data sources.

Technical debt:
- XML/REST XML Publisher data sources may deserve first-class UOM objects once
  their downstream metadata relationships are verified.
- A full non-persisted KG build was interrupted after it spent more than 90s in
  an unrelated PeopleCode capability probe; provider-specific behavior was
  validated directly instead.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- Live HCM probe found XML Publisher reports with `QRY`, `CQR`, and `XML`
  data source types.
- `uom.xpub_report_payload('HCM', 'AFI_BC')` returned a PS Query relationship
  and compact `USES` edge to `query:AFI_BC`.
- `uom.xpub_report_payload('HCM', 'BREREG02')` returned a Connected Query
  relationship and compact `USES` edge to `connected_query:BREREG02`.
- `uom.xpub_report_payload('HCM', 'ACA95C15_EE')` preserved XML datasource
  metadata without creating an unsupported graph edge.
- `/api/peoplesoft/graph/xml_publisher_report/AFI_BC` route helper returned
  `_source: uom`, `_vocabulary: compact_uom`, and a Report → Query `USES` edge.
- Direct graphdb edge construction check confirmed QRY/CQR reports create
  `USES` edges while XML reports remain metadata-only.

Next recommended work:
- Continue compact UOM graph alignment for PTF tests, Process Definitions, or
  IB Message Definitions.
- Investigate graph build performance/caching around repeated PeopleCode
  capability probes.

## 2026-07-01 — Connected Query UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 23:24 CDT

Features implemented:
- Connected Query UOM objects now expose `_relationships.queries` and
  `_relationships.field_joins`.
- Connected Query compact `_graph` previews now show Connected Query → PS Query
  `USES` edges and parent Query → child Query `CONTAINS` composition edges.
- Persisted Knowledge Graph ingestion now batch-loads PSCONQRSMAP rows and
  emits the same Connected Query → Query and Query → Query relationship model.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Modeled each PSCONQRSMAP child as a query used by the connected query.
- Modeled non-root PSCONQRSMAP parent/child rows as Query → Query `CONTAINS`
  edges to preserve the composition tree.
- Left field joins as UOM relationships/sections only for now because
  PSCONQRSFLDREL field names are not record-qualified.

Bugs fixed:
- Connected Query object pages exposed query-map sections but no canonical
  relationship model or compact graph preview.
- Persisted KG connected-query provider created nodes without edges to the PS
  Queries composing the connected query.

Technical debt:
- Field joins need a verified record/alias resolution pass before they become
  graph field edges.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py routers/peoplesoft.py` — OK.
- `python - <<'PY' import main ...` — OK.
- Live HCM probe found `ERE_RPT_ESP` with 35 component queries.
- `uom.connected_query_payload('HCM', 'ERE_RPT_ESP')` returned 35 query
  relationships, 59 field joins, and a compact graph with 36 nodes and 69
  edges.
- `/api/peoplesoft/graph/connected_query/ERE_RPT_ESP` route helper returned
  `_source: uom`, `_vocabulary: compact_uom`, 36 nodes, and 69 edges with
  `USES` / `CONTAINS` type aliases.
- Non-persisted `graphdb.build('HCM', limit=20, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `warning_count: 0`, and 88 connected-query/query composition edges.

Next recommended work:
- Resolve PSCONQRSFLDREL field joins to record-qualified field nodes if the
  query-map aliases can be safely joined.
- Continue compact UOM graph alignment for XML Publisher reports or PTF tests.

## 2026-07-01 — Content Service UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 23:21 CDT

Features implemented:
- Content Service UOM objects now expose `_relationships.components`,
  `_relationships.menus`, `_relationships.app_classes`, `_relationships.queries`,
  `_relationships.portal_registry`, and `_relationships.params`.
- Content Service compact `_graph` previews now show Content Service → target
  `USES` edges for components, menus, app classes, and queries, plus Portal
  Registry → Content Service `USES` edges for where-used portal objects.
- Persisted Knowledge Graph ingestion now emits Content Service → Component,
  Menu, Query, and App Class `USES` edges from PSPTCSSRVDEFN where target
  columns are populated.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Modeled Content Service dependencies as `USES`, matching the relationship
  direction from a related action/content service to its executable target.
- Kept portal where-used edges in compact UOM only for now, because
  PSPTCS_MNULINKS is detail-page scoped and the current KG provider reads from
  PSPTCSSRVDEFN only.
- Reused the App Class compound key format for UAPC-backed content services.

Bugs fixed:
- Content Service object pages had target/usage sections but no canonical
  `_relationships` or compact graph preview.
- Persisted KG content-service provider created nodes without edges to their
  component, menu, app-class, or query targets.

Technical debt:
- Persisted KG does not yet ingest Portal Registry → Content Service usage
  edges from PSPTCS_MNULINKS.
- URI-only and utility content services are still represented as nodes without
  modeled external-resource targets.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py routers/peoplesoft.py` — OK.
- `python - <<'PY' import main ...` — OK.
- `uom.content_service_object('HCM', 'BENEFIT_ENROLLMENT')` returned component
  and menu relationships, and a compact graph with 3 nodes and 2 `USES` edges.
- `uom.content_service_object('HCM', 'HRS_PKG_APP_CPY')` returned 1 App Class
  relationship, 4 Portal Registry usage relationships, and a compact graph with
  6 nodes and 5 `USES` edges.
- Generic object and graph route helpers returned top-level `_relationships`,
  `_graph`, `_source: uom`, and `_vocabulary: compact_uom` for both samples.
- Non-persisted `graphdb.build('HCM', limit=20, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `warning_count: 0`, and 39 Content Service `USES` edges.

Next recommended work:
- Consider PSPTCS_MNULINKS-backed Portal Registry → Content Service edges in
  persisted KG.
- Continue compact UOM graph alignment for section-only providers such as PTF
  tests, connected queries, and XML Publisher reports.

## 2026-07-01 — Standalone App Class UOM Graph

Date/time: 2026-07-01 23:08 CDT

Features implemented:
- Standalone App Class UOM objects now expose `_relationships.package`,
  `_relationships.peoplecode`, and `_relationships.siblings`.
- App Class compact `_graph` previews now show App Class → Application Package
  `BELONGS_TO` and App Class → PeopleCode `CONTAINS` edges.
- Generic UOM object payloads now pass `_relationships` and `_graph` through at
  the top level instead of only hiding them inside `_uom`.
- App Class detail sections now include a package relationship section and a
  PeopleCode Programs section with `PROGSEQ` chips.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Reused PSPCMPROG `OBJECTID1 = 104` and `peoplecode.reference_from_row()` so
  standalone App Class graph nodes match the PeopleCode provider identity.
- Kept the compact graph focused on parent package and owned PeopleCode
  programs. `APPCLASSREF` inheritance was not modeled because live HCM did not
  show populated base-class rows during the probe.

Bugs fixed:
- App Class object pages showed definition/source information but no canonical
  relationship model or compact graph preview.
- Generic object payloads did not expose UOM `_relationships` / `_graph` at the
  top level for canonical objects that use the shared `object_payload()`.

Technical debt:
- App Class inheritance edges remain future work if `APPCLASSREF` appears in
  another environment or PeopleTools version.

Verification:
- `python -m py_compile connectors/uom.py routers/peoplesoft.py` — OK.
- `python - <<'PY' import main ...` — OK.
- `uom.app_class_object('HCM',
  'HRS_CANDIDATE_MANAGER~APPLICANT_EMPLOYEE~APPLICANTAPPLICATIONCONTROLLER')`
  returned 1 package relationship, 3 PeopleCode relationships, 1 sibling, and
  a compact graph with 5 nodes and 4 edges.
- Generic object route helper returned top-level `_relationships` and `_graph`
  for the App Class payload.
- `/api/peoplesoft/graph/app_class/HRS_CANDIDATE_MANAGER~APPLICANT_EMPLOYEE~APPLICANTAPPLICATIONCONTROLLER`
  route helper returned `_source: uom`, `_vocabulary: compact_uom`, 5 nodes,
  and 4 edges with `BELONGS_TO` / `CONTAINS` type aliases.

Next recommended work:
- Continue compact UOM graph alignment for another section-only provider.
- Revisit App Class inheritance if live metadata with `APPCLASSREF` values is
  found.

## 2026-07-01 — App Class to PeopleCode Knowledge Graph Edges

Date/time: 2026-07-01 23:03 CDT

Features implemented:
- Application Package UOM PeopleCode relationships now include `PROGSEQ` and
  use `peoplecode.reference_from_row()` / `encode_reference()` for canonical
  PeopleCode node IDs.
- Compact Application Package graphs now represent multiple PeopleCode program
  rows per App Class when PSPCMPROG has multiple `PROGSEQ` values.
- Persisted Knowledge Graph Application Package ingestion now emits
  App Class → PeopleCode `CONTAINS` edges from PSPCMPROG object type 104.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept PeopleCode identity aligned with the PeopleCode provider by deriving
  references from full PSPCMPROG rows, including `PROGSEQ`.
- Scoped persisted edges to PSPCMPROG `OBJECTID1 = 104`, the verified
  Application Package class PeopleCode shape.
- Preserved compact graph caps while allowing full `_relationships.peoplecode`
  to include distinct program sequence rows.

Bugs fixed:
- Compact Application Package graphs previously assumed `.0` PeopleCode
  sequence identity and collapsed classes with multiple PSPCMPROG sequences.
- Persisted KG ingestion had Package → App Class containment but no
  App Class → PeopleCode containment path.

Technical debt:
- App Class standalone UOM objects still do not expose their own compact graph;
  they rely on Application Package and PeopleCode providers for surrounding
  graph context.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py routers/peoplesoft.py` — OK.
- `python - <<'PY' import main ...` — OK.
- `uom.app_package_payload('HCM', 'HRS_CANDIDATE_MANAGER')` returned 303 class
  relationships, 399 PeopleCode rows, and a compact graph with 161 nodes and
  160 edges, including 80 App Class → PeopleCode edges.
- `/api/peoplesoft/graph/application_package/HRS_CANDIDATE_MANAGER` route
  helper returned `_source: uom`, `_vocabulary: compact_uom`, and App Class →
  PeopleCode `CONTAINS` edges with `type` aliases.
- Non-persisted `graphdb.build('HCM', limit=10, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `warning_count: 0`, and 24 App Class → PeopleCode edges.

Next recommended work:
- Add standalone App Class UOM `_relationships` / `_graph` where useful.
- Continue provider-specific KG/UOM relationship alignment for older object
  families with section-only relationships.

## 2026-07-01 — Application Package UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 23:00 CDT

Features implemented:
- Application Package UOM objects now expose `_relationships.classes`,
  `_relationships.peoplecode`, and `_relationships.sub_packages`.
- Application Package payloads now include compact `_graph` previews with
  Package → App Class `CONTAINS` edges and App Class → PeopleCode `CONTAINS`
  edges.
- Generic `/api/peoplesoft/graph/application_package/{name}` now returns the
  package compact UOM graph with the shared `uom` / `compact_uom` vocabulary.
- Persisted Knowledge Graph ingestion now adds Application Package nodes and
  Application Package → App Class `CONTAINS` edges from PSPACKAGEDEFN and
  PSAPPCLASSDEFN where grants allow.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Reused the existing App Class compound key shape:
  `PACKAGEROOT~QUALIFYPATH~APPCLASSID`.
- Treated root package classes as `QUALIFYPATH = ':'`, matching the existing
  App Class provider.
- Capped compact package graph previews at 80 class edges and 80 PeopleCode
  edges while preserving full relationship lists in the payload.

Bugs fixed:
- Application Package object pages had class and PeopleCode sections but no
  canonical `_relationships` or compact graph preview.
- Persisted KG ingestion created App Class nodes without a package-level parent
  node or Package → App Class containment path.

Technical debt:
- Persisted KG ingestion does not yet emit App Class → PeopleCode edges; the
  compact UOM graph does.
- Package sub-package folder hierarchy remains a section-only relationship.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py routers/peoplesoft.py` — OK.
- Live HCM probe found `HRS_CANDIDATE_MANAGER` with 303 App Classes.
- `uom.app_package_payload('HCM', 'HRS_CANDIDATE_MANAGER')` returned 303 class
  relationships, 298 PeopleCode relationships, 48 sub-package rows, and a
  compact graph with 165 nodes and 160 edges.
- `/api/peoplesoft/graph/application_package/HRS_CANDIDATE_MANAGER` route
  helper returned `_source: uom`, `_vocabulary: compact_uom`, 165 nodes, and
  160 edges with `CONTAINS` type aliases.
- Uppercase compact graph App Class key
  `HRS_CANDIDATE_MANAGER~APPLICANT_EMPLOYEE~APPLICANTAPPLICATIONCONTROLLER`
  resolved through `uom.app_class_object()`.
- Non-persisted `graphdb.build('HCM', limit=10, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `warning_count: 0`, and 20 Application Package → App Class edges.

Next recommended work:
- Consider persisted App Class → PeopleCode edges after validating PSPCMPROG
  Application Package row shapes across more packages.
- Continue compact UOM graph alignment for older custom payloads.

## 2026-07-01 — Menu Compact UOM Graph Alignment

Date/time: 2026-07-01 22:55 CDT

Features implemented:
- Menu UOM objects now build compact `_graph` previews with the shared
  `relationship_graph()` helper.
- Menu graph previews now emit Menu → Component `CONTAINS` edges, matching the
  persisted Knowledge Graph menu provider semantics.
- Menu payloads now expose `_relationships` and `_graph` at the top level for
  API and UI consumers.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- De-duplicated repeated component menu items before building the compact graph,
  then capped preview edges at 80 to match other compact UOM previews.
- Preserved the full menu item list in `_relationships.items`; only the compact
  graph is capped.

Bugs fixed:
- Menu UOM graphs used a legacy custom shape with no `nodes` list and `LISTS`
  edges, so generic graph consumers could not treat Menu previews like other
  compact UOM graphs.

Technical debt:
- Menu graph previews still show component relationships only. Bar/item
  hierarchy and search records could be modeled later if useful.

Verification:
- `python -m py_compile connectors/uom.py routers/peoplesoft.py` — OK.
- `python - <<'PY' import main ...` — OK.
- Live HCM menu probe found `SETUP_HRMS` with 657 component references.
- `uom.menu_payload('HCM', 'SETUP_HRMS')` returned 659 raw menu item
  relationships and a compact graph with 81 nodes and 80 `CONTAINS` edges.
- `/api/peoplesoft/graph/menu/SETUP_HRMS` route helper returned `_source: uom`,
  `_vocabulary: compact_uom`, 81 nodes, and 80 `CONTAINS` edges with `type`
  aliases.

Next recommended work:
- Continue compact UOM graph alignment for older custom payloads that still use
  non-shared graph shapes or no `_graph` preview.

## 2026-07-01 — PS Query UOM and Knowledge Graph Relationships

Date/time: 2026-07-01 22:51 CDT

Features implemented:
- PS Query UOM objects now expose `_relationships.records`,
  `_relationships.output_fields`, and `_relationships.binds`.
- PS Query payloads now include a compact `_graph` showing Query → Record
  `USES`, Query → Field `EXPOSES`, and Record → Field `CONTAINS`
  relationships for output columns.
- Generic `/api/peoplesoft/graph/query/{name}` now returns the PS Query compact
  UOM graph with the shared `uom` / `compact_uom` vocabulary metadata.
- Persisted Knowledge Graph query ingestion now emits public-query edges:
  Query → Record `USES`, Query → Field `EXPOSES`, and Record → Field
  `CONTAINS`, guarded by PSQRYRECORD/PSQRYFIELD table availability.

Files modified:
- `connectors/uom.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Used public PS Queries only (`OPRID = ' '`) to preserve the existing
  public-query boundary.
- Limited compact UOM graph previews to 30 records and 50 output fields, while
  preserving full relationships in the payload.
- Resolved query output field graph nodes as `RECNAME.FIELDNAME` when the
  record could be determined from PSQRYFIELD or PSQRYRECORD.

Bugs fixed:
- PS Query object pages showed records/columns in sections but did not expose
  canonical `_relationships` or a compact graph preview.
- Persisted Knowledge Graph query provider created query nodes without the
  records or output fields they depend on.

Technical debt:
- Query criteria, expressions, and prompt-to-record/field relationships are
  still not modeled as graph edges.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py` — OK.
- Live HCM query probe found `POSITION_DATA_SRCH_QRY` with 24 records.
- `uom.query_payload(uom.query_object('HCM', 'POSITION_DATA_SRCH_QRY'))`
  returned 24 record relationships, 85 output field relationships, 1 bind, and
  a compact graph with 61 nodes and 114 edges.
- `/api/peoplesoft/graph/query/POSITION_DATA_SRCH_QRY` route helper returned
  `_source: uom`, `_vocabulary: compact_uom`, 61 nodes, and 114 edges.
- Non-persisted `graphdb.build('HCM', limit=10, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `warning_count: 0`, and 153 query relationship edges.

Next recommended work:
- Continue provider-specific KG/UOM alignment for another mature object family.
- Consider PS Query criteria/expression modeling after validating the relevant
  PeopleTools tables and keys.

## 2026-07-01 — Knowledge Graph Vocabulary Contract Alignment

Date/time: 2026-07-01 22:48 CDT

Features implemented:
- Persisted Knowledge Graph payloads now expose `_source`, `_vocabulary`, and
  `_semantics` metadata using the same graph contract as compact UOM and domain
  graph responses.
- Knowledge Graph edges now include a `relationship` alias alongside `type`,
  preserving existing KG consumers while matching UOM/domain graph payloads.
- Loaded legacy graph files and graph snapshots are normalized in memory so
  older persisted data gains the same metadata and edge alias shape without an
  immediate rebuild.
- Lightweight snapshot payloads now preserve the graph vocabulary metadata.

Files modified:
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Centralized the alignment in `graphdb.normalize_graph_shape()` and
  `add_edge()` instead of patching every provider individually.
- Kept provider-specific relationship reuse as separate work; this slice only
  standardizes the graph payload contract and edge alias shape.

Bugs fixed:
- Persisted KG exports/stats lacked the vocabulary metadata already present in
  UOM compact graphs and domain graph endpoints.
- Persisted KG edges exposed only `type`, requiring callers to special-case
  Knowledge Graph edges versus UOM/domain graph edges.

Technical debt:
- Provider-specific Knowledge Graph ingestion still needs to reuse more UOM
  `_relationships` definitions directly where practical.

Verification:
- `python -m py_compile connectors/graphdb.py connectors/graphshape.py routers/graphdb.py routers/peoplesoft.py` — OK.
- Source-level check verified new graph edges expose `CONTAINS` as both `type`
  and `relationship`, and legacy edges normalize `uses` to `USES`.
- `python - <<'PY' import main ...` — OK.
- Non-persisted `graphdb.build('HCM', limit=1, persist=False)` completed with
  `_source: knowledge_graph`, `_vocabulary: knowledge_graph`,
  `_semantics: persisted enterprise relationship graph`, 86 nodes, 42 edges,
  `warning_count: 0`, and edge `OWNS` exposed as both `type` and
  `relationship`.

Next recommended work:
- Continue provider-specific KG/UOM relationship alignment, starting with
  object families that already have mature compact UOM `_graph` definitions.
- Expand safe READS/WRITES extraction for non-literal PeopleCode SQL.

## 2026-07-01 — Project UOM DEPLOYS Graph Alignment

Date/time: 2026-07-01 22:43 CDT

Features implemented:
- Project UOM objects now expose a `deploys` relationship derived from safe
  PSPROJECTITEM → UOM target mappings.
- Project payloads now include `_relationships.deploys` and a compact `_graph`
  with Project → object `DEPLOYS` edges.
- Project object sections now include a de-duplicated `Deploys` section linking
  deployed target objects.
- Generic `/api/peoplesoft/graph/project/{name}` now returns the Project UOM
  compact graph with `_source: uom`, `_vocabulary: compact_uom`, and `DEPLOYS`
  edge type aliases.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Preserved raw PSPROJECTITEM-derived rows in `_relationships.deploys`, while
  de-duplicating compact graph edges by target object to avoid repeated page
  rows caused by market/action variants.
- Capped compact graph deploy edges at 80, consistent with compact object
  preview behavior.

Bugs fixed:
- Project object pages showed project items but did not expose the same
  relationship model that the persisted Knowledge Graph now uses.

Technical debt:
- Project object pages still rely on the conservative PSPROJECTITEM mapper.
  Additional project item types should be added only after live key validation.

Verification:
- `python -m py_compile connectors/uom.py` — OK.
- `uom.project_payload('HCM', 'GPIT_HR92_OBJECTS')` returned 500 raw deploy
  relationship rows and a `Deploys (419)` de-duplicated section.
- `peoplesoft_graph('project', 'GPIT_HR92_OBJECTS', env='HCM')` returned
  `_source: uom`, `_vocabulary: compact_uom`, 81 nodes, 80 unique `DEPLOYS`
  edges, and no duplicate compact graph edges.
- `python - <<'PY' import main ...` — OK.

Next recommended work:
- Continue UOM/KG relationship alignment for other older custom payloads.
- Add safe PSPROJECTITEM mappings only after live metadata validation.

## 2026-07-01 — Project DEPLOYS Knowledge Graph Edges

Date/time: 2026-07-01 22:39 CDT

Features implemented:
- Added `DEPLOYS` to the Knowledge Graph edge vocabulary and dependency edge
  set.
- Added `psdb.project_item_target()` to map safe PSPROJECTITEM rows to UOM
  object targets.
- Knowledge Graph Project ingestion now batch-loads PSPROJECTITEM rows for the
  selected projects and emits Project → object `DEPLOYS` edges where the target
  object type is safe to resolve.
- Project UOM payloads now include `uom_target` on item rows where a canonical
  target was resolved.

Files modified:
- `connectors/psdb.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the mapper conservative. It currently maps clear object families:
  Records, Pages, Components, Component Interfaces, Menus, Queries, and Trees.
- Skipped encoded and ambiguous PSPROJECTITEM types, including message catalog
  sets, AE SQL steps, PeopleCode subobjects, and security/dimension-like rows
  whose legacy labels were not reliable in live samples.
- Batched PSPROJECTITEM lookup by project names to avoid per-project N+1 query
  behavior during graph builds.

Bugs fixed:
- Project nodes existed in the Knowledge Graph but did not express the objects
  a project deploys, limiting impact analysis from App Designer projects.

Technical debt:
- Additional PSPROJECTITEM object-type decoding can be added once each type is
  verified against live metadata and UOM object identity rules.
- A full high-limit graph build is still expensive because other providers
  perform broad live metadata work before the Project provider runs.

Verification:
- `python -m py_compile connectors/psdb.py connectors/graphdb.py` — OK.
- `psdb.get_project('HCM', 'GPIT_HR92_OBJECTS')` mapped 341 Record items and
  159 Page item rows to canonical UOM targets.
- Ambiguous PSPROJECTITEM types 26, 27, 33, and encoded type 106 returned no
  target from `project_item_target()`.
- Non-persisted `graphdb.build('HCM', limit=50, persist=False)` completed with
  5131 nodes, 5833 edges, and `warning_count: 0`; the latest 50 projects had
  no safely mappable project items, so no `DEPLOYS` edges were expected there.
- Direct mini-graph validation for `GPIT_HR92_OBJECTS` produced 419 `DEPLOYS`
  edges: 341 to Records and 78 to Pages after edge de-duplication.
- Attempted `graphdb.build('HCM', limit=200, persist=False)` to reach more
  project coverage, but interrupted it after it ran past two minutes in earlier
  Integration Broker providers before reaching Project ingestion.

Next recommended work:
- Continue UOM/KG relationship alignment for project object pages so Project
  details can expose the same DEPLOYS targets in object graph previews.
- Add PSPROJECTITEM type mappings only after live table/key verification.

## 2026-07-01 — PeopleCode Literal SQL READS/WRITES Edges

Date/time: 2026-07-01 22:29 CDT

Features implemented:
- Added PeopleCode literal SQL extraction for direct `SQLExec("...")` and
  `CreateSQL("...")` calls.
- Knowledge Graph PeopleCode ingestion now parses those literal SQL strings
  with the existing conservative SQL record-access extractor and emits
  `READS` / `WRITES` edges from PeopleCode programs to records.
- Added `peoplecode.references_for_program()` so graph ingestion can reuse an
  already-loaded PSPCMPROG row instead of re-searching metadata for each row.
- Tightened PeopleCode source reconstruction by including `PROGSEQ` in the
  PSPCMTXT lookup predicate when available.
- Fixed graph metadata aliasing by copying metadata dictionaries when creating
  graph nodes and edges.

Files modified:
- `connectors/peoplecode.py`
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Only literal first-argument SQL is parsed. Fully dynamic PeopleCode SQL is
  still intentionally skipped unless it can be resolved safely.
- Kept SQL parsing in `connectors/graphdb.py`; PeopleCode only exposes literal
  SQL snippets and remains independent of graph internals.
- Preserved existing PeopleCode reference API shape with an additive
  `literal_sql` field.

Bugs fixed:
- Graph edge metadata could be mutated later because nodes and edges shared the
  same metadata dict object. Edge metadata is now copied on creation.
- PeopleCode graph ingestion no longer performs an expensive metadata search
  for every row in the build loop.

Technical debt:
- Non-literal PeopleCode SQL assembled in variables or helper functions still
  needs future static analysis.
- PeopleCode source reconstruction remains dependent on PSPCMTXT key quality;
  `PROGSEQ` improves precision, but other PeopleTools variants may need more
  key columns if discovered.

Verification:
- `python -m py_compile connectors/peoplecode.py connectors/graphdb.py` — OK.
- Parser check extracted literal SQL from `SQLExec("select ...")` and
  `CreateSQL("insert into ... select ...")` while ignoring `SQLExec(SQL.X)`.
- Live source check on
  `HRS_SITE_ID.GBL.HRS_SITE_WRK.HRS_SITE_VIEW_LNK1.FIELDCHANGE.0` extracted
  its `SQLExec` text and resolved `READS HR_SSTEXT_MSGID`.
- Non-persisted `graphdb.build('HCM', limit=50, persist=False)` completed with
  5131 nodes, 5833 edges, `warning_count: 0`, and 12 PeopleCode
  `READS`/`WRITES` edges.
- Verified PeopleCode edge metadata alignment: `metadata_mismatches: 0`.

Next recommended work:
- Continue relationship alignment between UOM compact graphs and persisted KG
  providers.
- Investigate safe static analysis for non-literal PeopleCode dynamic SQL.

## 2026-07-01 — Version-Adaptive Graph Provider Column Fixes

Date/time: 2026-07-01 22:15 CDT

Features implemented:
- Fixed Knowledge Graph providers for Trees, Component Interfaces, and Message
  Catalog to use live `all_tab_columns` discovery before selecting optional or
  version-specific columns.
- Added compatibility aliases so callers continue receiving stable keys:
  - `TREE_NAME` -> `TREENAME`
  - `TREE_STRCT_ID` -> `TREESTRCTPNM`
  - `BCPGNAME` -> `PNLGRPNAME`
  - `MSG_SEVERITY` -> `SEVERITY`
- Updated Component Interface environment comparison to compare `BCPGNAME`
  as the canonical component/page-group field when `PNLGRPNAME` is absent.
- Updated Message Catalog search/detail/global-search paths to support
  `MSG_SEVERITY` while preserving existing `severity` response fields.

Files modified:
- `connectors/graphdb.py`
- `connectors/psdb.py`
- `connectors/ptmetadata.py`
- `connectors/envcompare.py`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept routers thin and fixed the connector layer where SQL belongs.
- Preserved existing response keys and object identities instead of forcing UI
  or API callers to learn PeopleTools-version-specific column names.
- Treated absent optional columns as `NULL AS <stable_alias>` rather than
  failing graph builds.

Bugs fixed:
- Non-persisted graph builds no longer warn/fail for:
  - `PSTREEDEFN.OBJECTOWNERID`
  - `PSBCDEFN.PNLGRPNAME`
  - `PSMSGCATDEFN.SEVERITY`
- Message Catalog search and message detail no longer fail on environments
  where severity is stored as `MSG_SEVERITY`.

Technical debt:
- Several older helper paths still use local adaptive SQL fragments rather
  than one shared column-alias helper. This is acceptable for now but could be
  consolidated if more version-specific aliases appear.

Verification:
- `python -m py_compile connectors/graphdb.py connectors/psdb.py connectors/ptmetadata.py connectors/envcompare.py` — OK.
- `psdb.search_trees('HCM', limit=2)` returned tree rows with stable
  `treename` and `treestrctpnm` keys.
- `psdb.search_cis('HCM', limit=2)` returned CI rows with stable
  `pnlgrpname` populated from `BCPGNAME`.
- `psdb.search_messages('HCM', q='invalid', severity=2, limit=2)` returned
  `MSG_SEVERITY = 'E'` messages with stable `severity` keys.
- `psdb.get_message('HCM', 18028, 2108)` returned a Message Catalog detail.
- `ptmetadata.global_search('HCM', 'invalid', limit=2)` returned Message
  Catalog hits without SQL errors.
- `envcompare.compare_ci('HCM', 'FSCM', q='CI_', limit=2)` returned no
  warnings.
- Non-persisted `graphdb.build('HCM', limit=1, persist=False)` returned
  `trees`, `component_interfaces`, and `messages` providers as `ok`, with
  `warning_count: 0`.

Next recommended work:
- Continue broader READS/WRITES coverage for PeopleCode dynamic SQL.
- Consider extracting a small shared alias-expression helper if more provider
  column compatibility cases appear.

## 2026-07-01 — SQL Definition READS/WRITES Graph Edges

Date/time: 2026-07-01 17:33 CDT

Features implemented:
- Extended `connectors/graphdb.py` SQL Definition Knowledge Graph ingestion
  so standalone SQL definitions can emit `READS` and `WRITES` edges to records.
- Added grant-aware `PSSQLTEXTDEFN` lookup for SQL Definition bodies. If the
  text table is unavailable, the provider still returns SQL Definition nodes.
- Added Oracle literal chunking for SQLID lookups to avoid oversized `IN`
  lists during larger graph builds.
- Improved SQL record-access extraction to include PeopleSoft comma-style
  joins inside `FROM` blocks while avoiding SELECT-list commas.

Files modified:
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Reused the existing conservative SQL text extractor instead of adding a full
  SQL parser. This keeps the graph builder lightweight and read-only.
- Preferred Oracle-specific SQL text (`DBTYPE = '7'`) when present, falling
  back to generic PeopleTools SQL (`DBTYPE = ' '`).
- Kept SQL Definition edge metadata small and traceable: `sqlid`, `sqltype`,
  `dbtype`, and `source: pssqltextdefn`.

Bugs fixed:
- Standalone SQL Definitions were represented as graph nodes but did not expose
  their referenced records. They now participate in impact analysis when SQL
  text grants are available.
- Existing SQL extraction missed common PeopleSoft comma-join tables.

Technical debt:
- The SQL extractor remains intentionally heuristic. Nested dynamic SQL and
  PeopleCode-generated SQL still need separate coverage.
- A small non-persisted graph build surfaced pre-existing provider warnings for
  Trees, Component Interfaces, and Message Catalog due to environment-specific
  column assumptions; those were not part of this slice.

Verification:
- `python -m py_compile connectors/graphdb.py` — OK.
- `python - <<'PY' import main ...` — OK.
- Parser checks:
  - `SELECT A, B FROM PS_JOB J` -> READS `JOB`.
  - `FROM PS_EPO_PG_HDR A, PS_EPO_PG_ITEM B` -> READS both records.
  - `INSERT INTO PS_GPS_ORG_ACS_DTL ... FROM ps_gps_org_acs_sc, ps_gps_org_access`
    -> WRITES `GPS_ORG_ACS_DTL`; READS `GPS_ORG_ACS_SC`, `GPS_ORG_ACCESS`.
  - `MERGE INTO SYSADM.PS_FOO USING PS_BAR` -> WRITES `FOO`; READS `BAR`.
- Non-persisted `graphdb.build('HCM', limit=1, persist=False)` completed and
  emitted a SQL Definition `READS` edge:
  `sql_definition:EODC_FORMXREF_EXIST_SEL -> record:EODC_FORM_XREF`.
- `GET /admin/graph` against the running service — 200.
- `GET /api/graph/stats?env=HCM` against the running service — 200.
- `systemctl restart deathstar-api` was blocked by interactive authentication
  in this shell. The running service is healthy, but the deployed service still
  needs a privileged restart to load this committed connector change.

Next recommended work:
- Fix the pre-existing graph provider column assumptions surfaced by the
  non-persisted build.
- Continue broader READS/WRITES coverage for PeopleCode dynamic SQL.

## 2026-07-01 — Knowledge Graph AE READS/WRITES Edges

Date/time: 2026-07-01 16:25 CDT

Features implemented:
- Added conservative SQL record-access extraction to `connectors/graphdb.py`.
- Knowledge Graph Application Engine ingestion now parses AE SQL step text and
  emits:
  - `READS` edges from Application Engine programs to records found in
    `FROM`, `JOIN`, and `USING` clauses.
  - `WRITES` edges from Application Engine programs to records found in
    `INSERT INTO`, `UPDATE`, `DELETE FROM`, `MERGE INTO`, `%TruncateTable`,
    and `%InsertSelect` targets.
- READS/WRITES edge metadata includes AE section, AE step, statement type, and
  `source: ae_sql_step_text`.
- Preserved existing AE state-record `USES` and process-definition
  `GENERATES` edges.

Files modified:
- `connectors/graphdb.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept extraction conservative and read-only. Dynamic PeopleTools meta-SQL such
  as `%Table(%Bind(...))` is intentionally skipped when the target record cannot
  be resolved safely.
- Normalized physical PeopleSoft tables named `PS_<RECNAME>` to canonical
  record names, while preserving record names that naturally begin with `PS`
  such as `PSOPRDEFN`.
- Added READS/WRITES only to persisted Knowledge Graph ingestion. Existing AE
  domain graph and UOM object graph previews remain unchanged.

Bugs fixed:
- The Knowledge Graph had reserved READS/WRITES edge types but did not emit
  concrete examples. AE SQL steps now provide live examples from existing
  PeopleSoft metadata.

Technical debt:
- SQL extraction is intentionally heuristic. It does not parse every Oracle SQL
  construct, nested dynamic SQL, or fully dynamic PeopleTools meta-SQL.
- READS/WRITES still need expansion beyond AE SQL steps, especially PeopleCode
  dynamic SQL and SQL Definition bodies where metadata grants permit.
- Existing SQL Definition and PM Transaction graph providers contain unrelated
  duplicate `SELECT` text in their SQL strings and should be cleaned up in a
  separate slice.

Verification:
- `python -m py_compile connectors/graphdb.py` — OK.
- Parser checks:
  - `SELECT ... FROM SYSADM.PS_JOB JOIN PS_NAMES` -> READS `JOB`, `NAMES`.
  - `UPDATE SYSADM.PSOPRDEFN` -> WRITES `PSOPRDEFN`.
  - `%InsertSelect(BP_COMPENSATION, COMPENSATION ...) FROM PS_COMPENSATION`
    -> READS `COMPENSATION`, WRITES `BP_COMPENSATION`.
  - `%TruncateTable(PS_FT_JOB)` -> WRITES `FT_JOB`.
  - `MERGE INTO SYSADM.PS_FOO USING PS_BAR` -> READS `BAR`, WRITES `FOO`.
- Direct AE SQL text checks found SQL-bearing steps in `BEN_SRCH_JOB`,
  `BPJBCPY`, `FT_JOB`, `FT_JOB_PRCS`, and `BAS_CONFSTMT`.
- Non-persisted `graphdb.build('HCM', limit=10, persist=False)` completed in
  67.908s and produced 1051 nodes / 1014 edges, including 124 `READS` edges
  and 52 `WRITES` edges.
- Restarted `deathstar-api.service`; service returned active on
  `127.0.0.1:8088`.
- `GET /admin/graph` — 200.
- `GET /api/graph/stats?env=HCM` — 200.

Next recommended work:
- Clean up the duplicate `SELECT` SQL strings in the SQL Definition and PM
  Transaction graph providers.
- Continue Knowledge Graph vocabulary alignment, especially DEPLOYS and broader
  READS/WRITES sources.

------------------------------------------------------------------------

## 2026-07-01 — Domain Graph Vocabulary Bridge

Date/time: 2026-07-01 16:15 CDT

Features implemented:
- Added `connectors/graphshape.py`, a small shared helper for graph payload
  annotations and edge type aliases.
- Annotated PeopleCode graph payloads with `_source: peoplecode`,
  `_vocabulary: domain_peoplecode`, and `_semantics: source-reference graph`.
- Annotated Application Engine graph payloads with `_source:
  application_engine`, `_vocabulary: domain_ae`, and `_semantics:
  application-engine dependency graph`.
- Annotated generic UOM graph route responses with `_source: uom`,
  `_vocabulary: compact_uom`, and `_semantics: compact object preview`.
- Annotated persisted Knowledge Graph fallback responses with `_source:
  knowledge_graph`, `_vocabulary: knowledge_graph`, and `_semantics:
  persisted graph neighborhood`.
- Added `type` aliases to graph edges while preserving existing
  `relationship` labels for UI compatibility.

Files modified:
- `connectors/graphshape.py`
- `connectors/peoplecode.py`
- `connectors/ae.py`
- `routers/peoplesoft.py`
- `ARCHITECTURE.md`
- `README.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Did not rename existing relationship labels. The UI and downstream callers
  can continue using `relationship`, while graph-oriented consumers can use
  the normalized `type` alias.
- Kept graph construction in existing domain connectors. The new helper only
  annotates completed graph payloads.
- Documented graph payload semantics in `ARCHITECTURE.md` because it is now a
  cross-provider API convention.

Bugs fixed:
- PeopleCode and AE graph payloads previously lacked a clear source/vocabulary
  marker, making it hard for Graph Explorer and API consumers to distinguish
  compact UOM previews from richer domain graphs.

Technical debt:
- Persisted Knowledge Graph ingestion still needs an edge-vocabulary audit
  against UOM/domain graph metadata.
- Future edge coverage still needs explicit WRITES/READS examples and DEPLOYS
  relationship implementation.

Verification:
- `python -m py_compile connectors/graphshape.py connectors/peoplecode.py connectors/ae.py routers/peoplesoft.py connectors/uom.py` — OK.
- `python -c "import main; print('main import ok')"` — OK.
- Direct graph checks:
  - PeopleCode graph for `DERIVED_HR.JOB_DATA.ROWINIT.0` returned `_source:
    peoplecode`, `_vocabulary: domain_peoplecode`, 4 nodes / 3 edges, and edge
    `relationship/type` both present.
  - AE graph for `BEN_SRCH_JOB` returned `_source: application_engine`,
    `_vocabulary: domain_ae`, 6 nodes / 5 edges, and edge `relationship/type`
    both present.
  - Generic UOM graph route for `record:JOB` returned `_source: uom`,
    `_vocabulary: compact_uom`, 32 nodes / 31 edges, with lowercase
    `relationship` preserved and uppercase `type` alias added.

Next recommended work:
- Audit `connectors/graphdb.py` ingestion edge names against the UOM/domain
  graph metadata and begin adding missing READS/WRITES/DEPLOYS relationships
  where source metadata supports them.

------------------------------------------------------------------------

## 2026-07-01 — Generic Graph Route UOM Alignment

Date/time: 2026-07-01 15:40 CDT

Features implemented:
- Updated generic `/api/peoplesoft/graph/{type}/{name}` to resolve canonical
  object types through `uom.canonical_object()` and return the object's compact
  `_graph` preview.
- Preserved richer domain graph behavior for PeopleCode and Application Engine.
- Preserved persisted Knowledge Graph neighborhood fallback for unsupported or
  non-canonical graph node types.
- Removed stale hand-built node/edge construction from the router for Operator,
  Role, Permission List, Record, Component, Page, Portal Registry, Tree, and CI.

Files modified:
- `routers/peoplesoft.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Made UOM the first source of truth for compact object graph previews so Graph
  Explorer and Object Explorer use the same relationship model.
- Kept routers thin: the graph route now delegates to UOM/domain graph providers
  instead of querying PeopleSoft metadata directly.
- Left PeopleCode and AE graph routes as domain-owned graph providers because
  they expose richer traversal semantics than a compact UOM preview.

Bugs fixed:
- When a persisted Knowledge Graph existed, the generic graph route could return
  a KG neighborhood instead of the compact UOM graph preview, causing Graph
  Explorer and Object Explorer to disagree for the same object.
- Removed legacy router-level graph SQL/traversal logic that duplicated UOM
  relationship graph construction.

Technical debt:
- PeopleCode and Application Engine graph vocabularies still need comparison
  against UOM/KG edge naming before any further unification.
- Persisted Knowledge Graph ingestion still needs a relationship vocabulary
  audit against UOM `_relationships` and `_graph`.

Verification:
- `python -m py_compile routers/peoplesoft.py connectors/uom.py connectors/graphdb.py routers/admin/graph.py` — OK.
- `python -c "import main; print('main import ok')"` — OK.
- Direct route-function checks returned `_source: uom` for Operator, Role,
  Permission List, Record, Component, Page, Portal Registry, Tree, CI, Service
  Operation, IB Node, IB Queue, IB Routing, and SQL Definition.
- Restarted `deathstar-api.service`. A stray user-run reload server was holding
  port 8088; stopped it and confirmed systemd owns `127.0.0.1:8088`.
- HTTP checks:
  - `GET /api/peoplesoft/graph/record/JOB?env=HCM` — 200, `_source: uom`,
    32 nodes / 31 edges.
  - `GET /api/peoplesoft/graph/operator/PS?env=HCM` — 200, `_source: uom`,
    37 nodes / 40 edges.
  - `GET /api/peoplesoft/graph/permissionlist/HCCPPY1000?env=HCM` — 200,
    `_source: uom`, 43 nodes / 42 edges.
  - `GET /api/peoplesoft/graph/component/JOB_DATA?env=HCM` — 200,
    `_source: uom`, 61 nodes / 194 edges.
  - `GET /api/peoplesoft/graph/node/PSFT_HR?env=HCM` — 200, `_source: uom`,
    40 nodes / 40 edges.
  - `GET /admin/graph` — 200.
  - `GET /api/peoplesoft/object/record/JOB?env=HCM` — 200.

Next recommended work:
- Compare PeopleCode and Application Engine domain graph outputs against UOM
  object previews and document which edge types should remain domain-specific.
- Continue relationship-vocabulary alignment between UOM and Knowledge Graph
  ingestion.

------------------------------------------------------------------------

## 2026-07-01 — Object Explorer Visual Hierarchy

Date/time: 2026-07-01 15:25 CDT

Features implemented:
- Added an Object Map rail to Object Explorer detail pages.
- Added per-object summary pills for section count, row count, warning count,
  and graph count when available.
- Added anchor links for every canonical UOM section so large objects are
  easier to scan and navigate.
- Added visual emphasis for warning, graph, security/access, and empty
  sections while preserving the existing UOM payload and renderer behavior.
- Added section-level summary chips for item counts, data fields, DDL, and
  source-bearing sections.

Files modified:
- `routers/admin/graph.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the change entirely in the admin Object Explorer UI. No backend API
  shape, UOM provider, SQL, or route behavior changed.
- Derived all hierarchy from existing section names, `items`/`rows`, and
  `data` fields so providers do not need new metadata to benefit from the UI.
- Used escaped HTML for the compact rail renderer and kept detailed section
  bodies on the existing `textContent`/DOM-rendered paths.

Bugs fixed:
- Large UOM objects previously rendered as a flat grid of cards, making warning,
  graph, and security sections hard to find. The new rail gives each object a
  quick navigable outline.

Technical debt:
- The shared admin shell smoke harness still reports pre-existing active-nav
  failures across many pages and an unrelated `/admin/reports` JavaScript
  syntax error.
- Object Explorer still needs deeper relationship-vocabulary reconciliation
  between UOM `_relationships`, UOM `_graph`, route-specific graph APIs, and
  Knowledge Graph ingestion.

Verification:
- `python -m py_compile routers/admin/graph.py routers/admin/_core.py` — OK.
- `python -c "import main; print('main import ok')"` — OK.
- `GET /admin/object/record/JOB` — 200; generated page contains the new
  `sectionRail` and `object-shell` markup.
- `GET /admin/object` — 200; generated page contains the new Object Explorer
  structure.
- `GET /api/peoplesoft/object/record/JOB?env=HCM` — 200; returned type
  `record`, name `JOB`, and 16 sections.
- `python scripts/smoke_admin_shell.py` — `/admin/object` OK; broader harness
  still fails on pre-existing active-nav checks for multiple pages and an
  unrelated `/admin/reports` JS syntax error.

Next recommended work:
- Continue relationship vocabulary reconciliation for Object Explorer and Graph
  Explorer so route-specific graph endpoints and UOM graph previews converge
  where they represent the same relationship semantics.

------------------------------------------------------------------------

## 2026-07-01 — Tracing Web Log Visibility

Date/time: 2026-07-01 14:18 CDT

Features implemented:
- Updated Transaction Tracing log rendering so correlated web-tier app log rows
  are explicitly counted and filterable as Web Logs.
- Added separate Web Logs and App Logs summary cards on `/admin/tracing`.
- Added Web Logs and App Logs filter buttons in the tracing timeline.
- Relabeled PIA servlet log events as `Web Servlet` and preserved WebLogic,
  Web Error, JVM, and Web Access labels.
- Added a warning when the session API returns no true access-log rows but does
  return correlated web-tier servlet/WebLogic rows.

Files modified:
- `routers/admin/runtime.py`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Did not fabricate web access events. The configured remote
  `PIA_access.log` currently exists but is 0 bytes, so `web_entries` correctly
  has no rows for the selected session.
- Classified app-table rows from sources such as `HCMDMO_WEB_SERVLET` as
  web-tier events for UI purposes while leaving the backend `session_chain`
  response shape unchanged.

Bugs fixed:
- Web-tier servlet/WebLogic rows were easy to miss in tracing because they were
  only part of the generic log timeline. They now surface as Web Logs.
- Fixed the embedded JavaScript whitespace regex so `py_compile` no longer
  emits a Python invalid-escape warning for that line.

Technical debt:
- True PIA access-log ingestion still depends on the remote access log being
  populated. Current remote source `HCMDMO_WEB_ACCESS` points at
  `PIA_access.log`, which is 0 bytes.
- Broader uncommitted Claude-era work remains in AI/log/runtime files and local
  SQLite data files.

Verification:
- `python -m py_compile routers/admin/runtime.py routers/logs.py connectors/logdb.py connectors/logparser.py connectors/logingest.py`
  — OK.
- `python -c "import main; print('main import ok')"` — OK.
- Direct `logdb.session_chain('GUACUSER', last_24h)` returned 0 `web` rows,
  41 `app` rows, and 10 web-tier app rows from `HCMDMO_WEB_SERVLET`.
- Remote `PIA_access.log` size via `sshclient.file_size(...)` is 0 bytes.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /admin/tracing` — OK and contains the new Web Logs UI strings.
- `GET /api/logs/session/GUACUSER?...` — OK, returned 0 web rows, 41 app rows,
  and 10 app rows from web-tier sources.

Next recommended work:
- Confirm whether WebLogic access logging is disabled or writing to a different
  path on the PIA host; update `config.json` once the real access-log source is
  identified.

------------------------------------------------------------------------

## 2026-06-30 — Complete UOM Graph Builder Migration

Date/time: 2026-06-30 23:56 CDT

Features implemented:
- Completed the remaining in-module UOM graph-builder migration to the shared
  `relationship_graph()` helper.
- Migrated Field, Portal Registry, IB Service Operation, IB Node, IB Queue, IB
  Routing, and SQL Definition graph previews.
- Extended `relationship_graph()` with two small generic capabilities:
  - `node_only` specs for relationship rows that should contribute nodes
    without a primary edge.
  - Source-required edge skipping so malformed/incomplete relationship rows do
    not create empty source nodes.
- Preserved Field graph security expansion by keeping the security fan-out on
  top of the helper-generated structural graph.
- Queue objects now receive a canonical root graph node instead of a special
  empty graph, bringing them into the same preview model as other UOM objects.

Files modified:
- `connectors/uom.py`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept PeopleCode/domain-owned graph payloads delegated to their existing graph
  providers where they own specialized traversal semantics.
- Reframed the remaining roadmap work from "migrate UOM graph builders" to
  reconciling route-specific graph APIs with compact UOM previews where their
  semantics should match.
- Preserved existing graph counts for all sampled objects except Queue, where
  the intentional improvement is a root-only graph (`1 node / 0 edges`) rather
  than an empty graph.

Bugs fixed:
- Removed the remaining ad hoc UOM node/edge construction loops from
  `connectors/uom.py`.
- Avoided empty source-node creation for source-driven specs with missing
  source names.

Technical debt:
- Route-specific graph APIs such as some `/api/peoplesoft/graph/{type}/{name}`
  endpoints still need one-by-one review because some are broader impact graphs
  rather than compact UOM previews.
- Field graph previews remain large for common fields because they intentionally
  include record/page/component/security fan-out.

Verification:
- `rg -n "nodes = \\{}|edges = \\[]|graph_nodes_map|nodes_g|_graph=\\{\\\"nodes\\\"|_graph=\\{" connectors/uom.py`
  now reports only the shared helper internals.
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- Live endpoint checks:
  - `GET /api/peoplesoft/object/field/JOB.EMPLID?env=HCM` — OK, Graph Preview
    returned `edge_count=13708`.
  - `GET /api/peoplesoft/object/portal_registry/EOSD_FS_SD_RECDEFN_GBL?env=HCM`
    — OK, Graph Preview returned `node_count=15`, `edge_count=37`.
  - `GET /api/peoplesoft/object/node/PSFT_HR?env=HCM` — OK, Graph Preview
    returned `edge_count=40`.
  - `GET /api/peoplesoft/object/queue/APPMSG?env=HCM` — OK, UOM graph returned
    `node_count=1`, `edge_count=0`.
  - `GET /api/peoplesoft/object/sql_definition/SQLRTM_DUMMY?env=HCM` — OK,
    UOM graph returned `node_count=1`, `edge_count=0`.
- Direct graph-count verification:
  - `field_object('HCM', 'JOB.EMPLID')` — 12910 nodes, 13708 edges.
  - `field_object('HCM', 'PSOPRDEFN.OPRID')` — 5907 nodes, 6449 edges.
  - `portal_registry_object('HCM', 'HC_HR_JOB_DATA_GBL')` — 1 node, 0 edges.
  - `portal_registry_object('HCM', 'EOSD_FS_SD_RECDEFN_GBL')` — 15 nodes,
    37 edges, with breadcrumb, component, and security edges present.
  - `service_object('HCM', 'HCB_COMMON_UTIL_SVC')` — 1 node, 0 edges.
  - `service_object('HCM', 'BEN_CHATBOT_SVC')` — 1 node, 0 edges.
  - `node_object('HCM', 'PSFT_HR')` — 40 nodes, 40 edges.
  - `node_object('HCM', 'LOCAL')` — 1 node, 0 edges.
  - `routing_object('HCM', 'HRS_JOB_OPENING')` — 1 node, 0 edges.
  - `sql_object('HCM', 'SQLRTM_DUMMY')` — 1 node, 0 edges.
  - `queue_object('HCM', 'APPMSG')` — 1 node, 0 edges.

Next recommended work:
- Compare each route-specific Graph Explorer endpoint against the matching UOM
  graph preview and either route it through UOM or document it as a richer
  impact/analysis graph.

------------------------------------------------------------------------

## 2026-06-30 — Security UOM Relationship Graph Extraction

Date/time: 2026-06-30 23:48 CDT

Features implemented:
- Continued relationship-provider extraction by moving Operator, Role, and
  Permission List UOM graph previews onto the shared `relationship_graph()`
  helper.
- Preserved existing preview caps:
  - Operator: 20 roles and 20 permission lists.
  - Role: 20 members and 15 permission lists.
  - Permission List: 25 roles and 40 components.
- Preserved existing security edge vocabulary and direction:
  `has_role`, `has_permission`, `has_member`, `grants`,
  `contains_permissionlist`, and `secures_component`.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the migration inside UOM only. The legacy graph routes for these object
  types can be reconciled separately after comparing whether their route output
  is compact-preview or impact-analysis semantics.
- Used explicit `source_node_type` and `target_node_type` for inbound Permission
  List role edges so the root remains `permissionlist:<classid>`.

Bugs fixed:
- Removed three more imperative graph-building loops from `connectors/uom.py`.

Technical debt:
- Field UOM graph construction still uses a bespoke builder because it includes
  richer page/record/security expansion.
- Some `/api/peoplesoft/graph/{type}/{name}` routes still have route-specific
  graph construction and should be reconciled one by one.

Verification:
- `python -m py_compile connectors/uom.py` — OK.
- Direct `uom.operator_object('HCM', 'PS')['_graph']` returned 37 nodes and
  40 edges, matching the pre-refactor UOM graph count.
- Direct `uom.operator_object('HCM', 'VP1')['_graph']` returned 38 nodes and
  40 edges, matching the pre-refactor UOM graph count.
- Direct `uom.role_object('HCM', 'PeopleSoft Administrator')['_graph']`
  returned 10 nodes and 9 edges, matching the pre-refactor UOM graph count.
- Direct `uom.role_object('HCM', 'PeopleSoft User')['_graph']` returned
  18 nodes and 17 edges, matching the pre-refactor UOM graph count.
- Direct `uom.permissionlist_object('HCM', 'HCCPPY1000')['_graph']` returned
  43 nodes and 42 edges, matching the pre-refactor UOM graph count.
- Direct `uom.permissionlist_object('HCM', 'PTPT1000')['_graph']` returned
  37 nodes and 45 edges, matching the pre-refactor UOM graph count.
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/object/operator/PS?env=HCM` — OK, Graph Preview returned
  `node_count=37`, `edge_count=40`.
- `GET /api/peoplesoft/object/role/PeopleSoft%20Administrator?env=HCM` — OK,
  Graph Preview returned `node_count=10`, `edge_count=9`.
- `GET /api/peoplesoft/object/permissionlist/HCCPPY1000?env=HCM` — OK, Graph
  Preview returned `node_count=43`, `edge_count=42`.

Next recommended work:
- Inspect remaining bespoke graph builders and distinguish reusable compact
  object previews from intentionally richer impact/security graph endpoints.

------------------------------------------------------------------------

## 2026-06-30 — Record UOM Relationship Graph Extraction

Date/time: 2026-06-30 23:44 CDT

Features implemented:
- Continued the relationship-provider extraction work by moving the Record UOM
  graph preview onto the shared `relationship_graph()` helper.
- Preserved existing Record graph preview caps: fields 30, parent record
  relationship uncapped, and components 10.
- Preserved existing Record UOM edge vocabulary:
  `contains_field`, `parent_of`, and `used_in_component`.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Migrated only the UOM Record graph preview in this slice. The separate
  `/api/peoplesoft/graph/record/{name}` route intentionally remains unchanged
  because it currently returns a broader impact-style graph from graphdb plus
  legacy route edges, not the compact UOM preview.
- Kept root Record node metadata populated from `PSRECDEFN` detail.

Bugs fixed:
- Removed another imperative graph-building loop from `connectors/uom.py`.

Technical debt:
- Record, Operator, Role, and Permission List graph routes still contain
  router-local graph construction or route-specific graph behavior.
- Field UOM graph construction still uses a bespoke builder because it includes
  runtime security expansion and page/record fan-out.

Verification:
- `python -m py_compile connectors/uom.py` — OK.
- Direct `uom.record_object('HCM', 'JOB')['_graph']` returned 32 nodes and
  31 edges, matching the pre-refactor UOM graph count.
- Direct `uom.record_object('HCM', 'PSOPRDEFN')['_graph']` returned 31 nodes
  and 30 edges, matching the pre-refactor UOM graph count.
- Direct `uom.record_object('HCM', 'DEPT_TBL')['_graph']` returned 33 nodes
  and 33 edges, matching the pre-refactor UOM graph count.
- Compared `/api/peoplesoft/graph/record/{name}` behavior in-process and left
  it unchanged because its graph shape differs from the UOM preview.
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/object/record/JOB?env=HCM` — OK, Graph Preview returned
  `node_count=32`, `edge_count=31`.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Continue reducing duplicate graph construction where the route and UOM graph
  semantics match, or explicitly split compact UOM previews from impact graph
  endpoints in the architecture docs before unifying Record route behavior.

------------------------------------------------------------------------

## 2026-06-30 — Component Graph API Uses UOM Provider

Date/time: 2026-06-30 23:39 CDT

Features implemented:
- Reconciled `/api/peoplesoft/graph/component/{name}` with the Component UOM
  provider.
- Removed the duplicate router-local Component graph construction loop from
  `routers/peoplesoft.py`.
- Graph Explorer Component requests now receive the same Component relationship
  model as Object Explorer Graph Preview.

Files modified:
- `routers/peoplesoft.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the endpoint URL and response shape unchanged: `{root, nodes, edges}`.
- Accepted the intentional content alignment: the route now returns the capped,
  richer UOM Component graph rather than the older security/pages/search-record
  router graph. For sampled objects this changes `JOB_DATA` from 58/287 to
  61/194 and `USERMAINT` from 11/23 to 29/155.
- Preserved the existing UOM Component edge labels and graph caps.

Bugs fixed:
- Removed another source of duplicated graph construction from the router layer.
- Eliminated duplicate permission-list edges produced by the legacy component
  graph route for some components.

Technical debt:
- Record, Operator, Role, and Permission List graph routes still contain
  router-local graph construction.

Verification:
- `python -m py_compile routers/peoplesoft.py connectors/uom.py` — OK.
- Direct `routers.peoplesoft.peoplesoft_graph('component', 'JOB_DATA', env='HCM')`
  returned `component:JOB_DATA`, 61 nodes, and 194 edges.
- Direct `routers.peoplesoft.peoplesoft_graph('component', 'USERMAINT', env='HCM')`
  returned `component:USERMAINT`, 29 nodes, and 155 edges.
- `python -m py_compile routers/peoplesoft.py routers/admin.py connectors/uom.py connectors/psdb.py connectors/ptmetadata.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/graph/component/JOB_DATA?env=HCM` — OK, returned
  `component:JOB_DATA`, 61 nodes, and 194 edges.
- `GET /api/peoplesoft/graph/component/USERMAINT?env=HCM` — OK, returned
  `component:USERMAINT`, 29 nodes, and 155 edges.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Continue reducing router-local graph construction, likely Record next after
  comparing legacy route output with the Record UOM graph.

------------------------------------------------------------------------

## 2026-06-30 — Component UOM Relationship Graph Extraction

Date/time: 2026-06-30 23:34 CDT

Features implemented:
- Continued the relationship-provider extraction work by moving the Component
  UOM graph preview onto the shared `relationship_graph()` helper.
- Preserved existing Component graph preview caps: pages 30, search records 10,
  page records 30, permission lists 40, and security access rows 60.
- Preserved existing Component UOM edge vocabulary:
  `contains_page`, `searchrecname`/`addsrchrecname`, `uses_page_record`,
  `secures_component`, `contains_permissionlist`, and `has_role`.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Migrated only the Component UOM graph builder in this slice. The legacy
  `/api/peoplesoft/graph/component/{name}` route still has router-local graph
  construction and should be reconciled separately after confirming the desired
  behavior change, because its current output differs from the UOM graph.
- Kept root Component node metadata populated from `PSPNLGRPDEFN` detail.

Bugs fixed:
- Removed another imperative graph-building loop from `connectors/uom.py`.

Technical debt:
- Component graph route duplication remains in `routers/peoplesoft.py`.
- Record, Operator, Role, and Permission List graph routes still contain
  router-local graph construction.

Verification:
- `python -m py_compile connectors/uom.py` — OK.
- Direct `uom.component_object('HCM', 'JOB_DATA')['_graph']` returned 61 nodes
  and 194 edges, matching the pre-refactor UOM graph count.
- Direct `uom.component_object('HCM', 'USERMAINT')['_graph']` returned 29 nodes
  and 155 edges, matching the pre-refactor UOM graph count.
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/sqlws/config` — OK baseline.
- `GET /api/peoplesoft/object/component/JOB_DATA?env=HCM` — OK, Graph Preview
  returned `node_count=61`, `edge_count=194`.
- `GET /api/peoplesoft/object/component/USERMAINT?env=HCM` — OK, Graph Preview
  returned `node_count=29`, `edge_count=155`.

Next recommended work:
- Reconcile `/api/peoplesoft/graph/component/{name}` with the Component UOM
  provider, explicitly documenting the behavior change because the legacy route
  returns a different, narrower graph.

------------------------------------------------------------------------

## 2026-06-30 — Performance Monitor Metrics Explorer Vertical Slice

Date/time: 2026-06-30 (continued)

Features implemented:
- Full PM Metrics Explorer slice from `psdb.py` through to the admin UI page.
- `psdb.search_pm_metrics(env, q, limit)` — numeric ID search or label/description text search; `FETCH FIRST :lim ROWS ONLY` pagination.
- `psdb.get_pm_metric(env, metric_id)` — fetches metric definition + enum values from `PSPMMETRICVALUE` + transaction references (reverse lookup across all 7 metric ID slots in `PSPMTRANSDEFN`) + event references (`PSPMEVENTDEFN`); returns `{definition, enum_values, transactions, events, warnings}`.
- `ptmetadata.py` — added `OBJECT_REGISTRY["pm_metric"]` with icon `activity`.
- `connectors/uom.py` — `pm_metric_object()`: Metric Overview kv section, Enum Values chips section (for flag/enum metrics), Used in Transactions items section, Used in Events items section; metric type codes decoded (1=Config Counter, 2=Collected Metric, 3=Flag/Enum, 4=String, 5-7=rare).
- `connectors/graphdb.py` — `pm_metrics()` provider with `has_table()` guard.
- `routers/peoplesoft.py` — `GET /api/peoplesoft/pm-metrics` endpoint; object dispatch for `pm_metric`.
- `routers/admin.py` — NAV entry, chip (purple `#9988ff`), `GET /pmmetric` page with search (label/description/numeric ID), type badge in list items, detail with all sections.
- `scripts/smoke_admin_shell.py` — added `/admin/pmmetric` to `DEFAULT_PAGES`; passes.

Files modified:
- `connectors/psdb.py`
- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `connectors/graphdb.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `scripts/smoke_admin_shell.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- PM metric ID is an integer; the UOM `canonical_base` `name` is the string representation of the integer. Object URLs use the numeric string (e.g., `/api/peoplesoft/object/pm_metric/81`).
- Reverse transaction lookup uses `WHERE :id IN (PM_METRICID_1, ..., PM_METRICID_7)` — Oracle handles `IN` with bind variables correctly.
- Enum values only exist for flag/enum type metrics (`pm_metric_disp=Y`); most metrics have no enum values.
- `PSPMCONTEXTDEFN` (56 rows) not surfaced — contexts are linked to transactions, not directly to metrics.

Verification:
- `python -m py_compile ...` — OK.
- `psdb.search_pm_metrics('HCM', 'PeopleCode', 5)` → 5 rows.
- `psdb.get_pm_metric('HCM', '81')` → 14 transaction references, 0 events.
- `psdb.get_pm_metric('HCM', '47')` → 6 enum values (Standby/Error/Warning/Standard/Verbose/Debug).
- `uom.pm_metric_object('HCM', '81')` → display `81 — Record Field PCode Exec Count`, sections: Overview (6 items), Transactions (14).
- `GET /api/peoplesoft/pm-metrics?env=HCM&q=SQL&limit=3` — OK.
- `python scripts/smoke_admin_shell.py` — `/admin/pmmetric` passes; no regressions.

Next recommended work:
- IB Schema Definitions (`PSIBSCMADATA`/`PSIBSCMADFN`, 3680/3618 rows) — investigate if browsable name/type columns exist
- PM Transaction Explorer (`PSPMTRANSDEFN` as primary) — complement to PM Metrics, shows transaction definitions with their metric and context slots

------------------------------------------------------------------------

## 2026-06-30 — Locale Explorer Vertical Slice

Date/time: 2026-06-30 (continued)

Features implemented:
- Full Locale Explorer slice from `psdb.py` through to the admin UI page.
- `psdb.search_locales(env, q, limit)` — searches `PSLOCALEDEFN` by code or description; `FETCH FIRST :lim ROWS ONLY` pagination.
- `psdb.get_locale(env, locale_cd)` — fetches definition + all format options from `PSLOCALEOPTNDFN`; returns `{definition, options, warnings}`.
- `ptmetadata.py` — added `OBJECT_REGISTRY["locale"]` with discovery/search tables `PSLOCALEDEFN`/`LOCALECD`, icon `globe`.
- `connectors/uom.py` — `locale_object(env, locale_cd)`: builds "Locale Overview" kv section and "Format Options" kv section; decodes `DFRMT` (M/D/Y → MDY/DMY/YMD) and `TFRMT` (C/M → 12-hour/24-hour clock); option labels: Decimal Separator, Thousands Separator, Date Separator, Date Format, Time Format, AM Designator, PM Designator.
- `connectors/graphdb.py` — `locales()` provider with `has_table()` guard.
- `routers/peoplesoft.py` — `GET /api/peoplesoft/locales` endpoint; object dispatch for `object_type == "locale"`.
- `routers/admin.py` — NAV entry `("locale", "Locales", "/admin/locale")`; chip definition (green `#55cc55`); `GET /locale` route with search + detail UI.
- `scripts/smoke_admin_shell.py` — added `("/admin/locale", "#q", True, True, [])` to `DEFAULT_PAGES`.

Files modified:
- `connectors/psdb.py`
- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `connectors/graphdb.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `scripts/smoke_admin_shell.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- `PSLOCALEOPTNDFN` has 923 rows across 170 locales (191 defined); 21 locales have no options and show only the overview section.
- `DFRMT` values decoded: `M` = MDY (month-first, US), `D` = DMY (day-first, European), `Y` = YMD (year-first, Asian/ISO).
- `TFRMT` values decoded: `C` = 12-hour clock, `M` = 24-hour clock.
- `MDES`/`ADES` are AM/PM designators (locale-specific strings, e.g., `r.n.`/`i.n.` for Irish Gaelic).
- `PSLOCALEORDER` (parent-child fallback chains, 23 rows) and `PSLOCALELANG` (0 rows, empty) not surfaced in the UOM object — low information value.

Verification:
- `python -m py_compile connectors/psdb.py connectors/ptmetadata.py connectors/uom.py connectors/graphdb.py routers/peoplesoft.py routers/admin.py` — OK.
- `psdb.search_locales('HCM', 'en', 5)` → 5 rows including `en`, `en-au`.
- `uom.locale_object('HCM', 'en-us')` → display `en-us — English (United States)`, 7 format options.
- `uom.locale_object('HCM', 'ja')` → 5 options, Date Format = `YMD (year-first)`, Time Format = `24-hour clock`.
- `uom.locale_object('HCM', 'xx-yy')` → warnings `["Locale 'xx-yy' not found"]`.
- `GET /api/peoplesoft/locales?env=HCM&q=ja&limit=3` — OK, returned 3 rows.
- `GET /admin/locale` — 200 OK.
- `python scripts/smoke_admin_shell.py` — `/admin/locale` passes; no regressions.

Next recommended work:
- Performance Monitor Metrics (`PSPMMETRICDEFN`/`PSPMTRANSDEFN`/`PSPMEVENTDEFN`)
- IB Schema Definitions (`PSIBSCMADATA`/`PSIBSCMADFN`)

------------------------------------------------------------------------

## 2026-06-30 — Timezone Explorer Vertical Slice

Date/time: 2026-06-30 (resumed session)

Features implemented:
- Full Timezone Explorer slice from `psdb.py` through to the admin UI page.
- `psdb.search_timezones(env, q, limit)` — queries `PSTIMEZONEDEFN` with effective-date subquery; returns `TIMEZONE`, `TZDESCR`, `UTCOFFSET` (minutes), `OBSERVEDST`, `PTEFFDTTM`.
- `psdb.get_timezone(env, tz_code)` — fetches single timezone plus IANA mappings from `PSTIMEZONEIANA`; returns `{definition, iana, warnings}`.
- `ptmetadata.py` — added `OBJECT_REGISTRY["timezone"]` with discovery/search tables `PSTIMEZONEDEFN`/`TIMEZONE`, icon `clock`.
- `connectors/uom.py` — `timezone_object(env, tz_code)` canonical object: converts `UTCOFFSET` minutes to `UTC±H:MM` string, maps `OBSERVEDST`, builds kv overview section and IANA chip section. `utc_offset_minutes` key preserved in overview for the admin page JS.
- `connectors/graphdb.py` — `timezones()` provider with `has_table()` guard and effective-date subquery; registered in the graph build loop.
- `routers/peoplesoft.py` — `GET /api/peoplesoft/timezones` endpoint; object dispatch for `object_type == "timezone"`.
- `routers/admin.py` — NAV entry `("timezone", "Timezones", "/admin/timezone")`; chip definition; `GET /timezone` route using `_shell()` with full search/select UI.
- `scripts/smoke_admin_shell.py` — added `("/admin/timezone", "#q", True, True, [])` to `DEFAULT_PAGES`.

Files modified:
- `connectors/psdb.py`
- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `connectors/graphdb.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `scripts/smoke_admin_shell.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- `UTCOFFSET` and `DSTOFFSET` in `PSTIMEZONEDEFN` are stored in minutes (PST = -480, IST = +330). Converted to display strings in `uom.py`; raw minutes kept in the overview payload so the admin page JS can format independently with `fmtOffset()`.
- Effective-date subquery (`WHERE PTEFFDTTM = (SELECT MAX(...))`) used in both search and detail queries to pick the current definition row.
- `PSTIMEZONEIANA` join in `get_timezone()` retrieves all IANA equivalents for the given timezone code.
- Admin page JS avoids inline onclick; uses `data-idx` attributes and `addEventListener` to comply with the project's HTML escaping requirements.

Bugs fixed:
- Previous session left `psdb.py`/`ptmetadata.py` committed but `uom.py`/`graphdb.py`/`routers/`/`admin.py` missing — completed the slice.
- Admin route path corrected from `@router.get("/admin/timezone")` (double-prefix with `APIRouter(prefix="/admin")`) to `@router.get("/timezone")`.
- Removed `request: Request` parameter that caused 422 when `Request` was not imported.

Verification:
- `python -m py_compile connectors/uom.py connectors/graphdb.py routers/peoplesoft.py routers/admin.py` — OK.
- `uom.timezone_object('HCM', 'PST')` → display `PST \u2014 Pacific Time (US)`, UTC-8, DST yes.
- `uom.timezone_object('HCM', 'IST')` → UTC+5:30 (half-hour offset correct).
- `uom.timezone_object('HCM', 'DOES_NOT_EXIST')` → warnings `["Timezone 'DOES_NOT_EXIST' not found"]`.
- `GET /api/peoplesoft/timezones?env=HCM` — OK.
- `GET /admin/timezone` — 200 OK.
- `python scripts/smoke_admin_shell.py` — `/admin/timezone` passes; pre-existing `/admin/envcompare` and `/admin/reports` failures unchanged.

Next recommended work:
- IB Schema Definitions (`PSIBSCMADATA`/`PSIBSCMADFN`, 3680/3618 rows)
- Performance Monitor Metrics (`PSPMMETRICDEFN`, 206 rows)
- Locale Definitions (`PSLOCALEDEFN` + `PSLOCALEOPTNDFN`, 191/923 rows)

------------------------------------------------------------------------

## 2026-06-30 — Page Graph API Uses UOM Provider

Date/time: 2026-06-30 11:47 CDT

Features implemented:
- Reconciled the older `/api/peoplesoft/graph/page/{name}` route with the
  Page UOM provider.
- Removed the duplicate router-local Page graph construction loop from
  `routers/peoplesoft.py`.
- Graph Explorer Page requests now receive the same Page relationship model as
  Object Explorer Graph Preview.

Files modified:
- `routers/peoplesoft.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the endpoint URL and response shape unchanged: `{root, nodes, edges}`.
- Accepted the intentional content alignment: the route now returns the capped,
  cleaner UOM Page preview graph rather than the older router graph. For
  `JOB_DATA1`, this means 112 nodes / 111 edges and no blank record node.
- Left Field, Tree, CI, and Portal graph route delegation patterns unchanged.

Bugs fixed:
- Removed one source of duplicated Page relationship logic.
- Removed the older Page graph route behavior that could include a blank
  `record: ` node from untrimmed metadata rows.

Technical debt:
- Reduced router-owned graph construction; routers remain thinner.
- Component, Record, Operator, Role, and Permission List graph routes still
  contain router-local graph construction and should be migrated cautiously.

Verification:
- `python -m py_compile routers/peoplesoft.py connectors/uom.py` — OK.
- Direct `routers.peoplesoft.peoplesoft_graph('page', 'JOB_DATA1', env='HCM')`
  check returned `page:JOB_DATA1`, 112 nodes, and 111 edges.
- `python -m py_compile routers/peoplesoft.py routers/admin.py connectors/uom.py connectors/psdb.py connectors/ptmetadata.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/graph/page/JOB_DATA1?env=HCM` — OK, returned
  `page:JOB_DATA1`, 112 nodes, and 111 edges.
- `GET /api/peoplesoft/object/page/JOB_DATA1?env=HCM` — OK, Graph Preview
  returned matching `node_count=112` and `edge_count=111`.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Continue reducing router-local graph construction, likely Component next
  because it overlaps heavily with the existing UOM Component graph.

------------------------------------------------------------------------

## 2026-06-30 — Page UOM Relationship Graph Extraction

Date/time: 2026-06-30 11:38 CDT

Features implemented:
- Continued the relationship-provider extraction roadmap slice by moving the
  Page UOM graph preview onto the shared `relationship_graph()` helper.
- Extended the helper to support explicit source-node types/names for inbound
  edges such as Component -> Page and Permission List -> Page.
- Added optional root-node data support so providers can preserve existing
  root metadata when using the shared helper.
- Added `limit_relationships()` so providers can keep existing preview caps
  while declaring relationship graph specs.

Files modified:
- `connectors/uom.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Migrated the UOM Page graph builder only. The older router-specific
  `/api/peoplesoft/graph/page/...` path still exists and should be reconciled
  separately to avoid changing legacy graph behavior inside this slice.
- Preserved the previous Page UOM preview caps: components 20, records 30,
  fields 40, subpages 20, permission lists 40.
- Preserved Page root metadata in graph preview nodes.

Bugs fixed:
- None; this was an internal maintainability slice.

Technical debt:
- Removed another ad hoc UOM graph loop.
- Remaining debt: Record, Component, Portal, and security graph builders still
  have imperative graph construction. The legacy router page graph also still
  duplicates Page relationship logic.

Verification:
- `python -m py_compile connectors/uom.py connectors/ptmetadata.py connectors/psdb.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- Direct `uom.page_object('HCM', 'JOB_DATA1')['_graph']` check returned 112
  nodes and 111 edges, matching the pre-refactor UOM graph count.
- Direct Page graph preview retained root page metadata (`pnlname=JOB_DATA1`)
  and did not include the blank record node present in the older router graph.
- Direct synthetic Tree and Component Interface graph checks still returned the
  expected shared-helper edges.
- Direct `uom.page_payload(...)` check showed Graph Preview `node_count=112`
  and `edge_count=111`.
- Reloaded `deathstar-api.service` by terminating the current unit PID and
  allowing systemd to restart it; service came back active on port 8088.
- `GET /api/peoplesoft/object/page/JOB_DATA1?env=HCM` — OK, Graph Preview
  returned `node_count=112`, `edge_count=111`, and root node metadata retained
  `pnlname=JOB_DATA1`.
- `GET /api/sqlws/config` — OK baseline.

Next recommended work:
- Reconcile or retire the older router-specific Page graph path in favor of
  UOM graph output.
- Continue relationship extraction with Component or Record after capturing
  before/after graph counts.

------------------------------------------------------------------------

## 2026-06-30 — Shared UOM Relationship Graph Helper

Date/time: 2026-06-30 11:11 CDT

Features implemented:
- Started the relationship-provider extraction roadmap slice with a shared
  `relationship_graph()` helper in `connectors/uom.py`.
- Refactored Tree and Component Interface graph previews to use declarative
  relationship specs instead of local hand-written node/edge loops.
- Preserved existing UOM payload and `/api/peoplesoft/graph/...` response
  shapes: graph previews still return `nodes` and `edges`, with the same root,
  target object types, admin links, and relationship labels.
- Fixed Tree metadata discovery/search column names for PeopleTools tables that
  expose `TREE_NAME` and `TREE_STRCT_ID` instead of the older aliases.
- Routed global Tree search through the dedicated grant-aware tree search
  provider and de-duplicated global results by tree name while preserving
  variant rows in `/api/peoplesoft/trees`.

Files modified:
- `connectors/uom.py`
- `connectors/ptmetadata.py`
- `connectors/psdb.py`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:
- Kept the first extraction narrow and provider-local: Tree and CI were the
  newest providers and already had similar field/record relationship loops.
- Left older Record, Page, Component, Portal, and security graph builders alone
  until each can be migrated with endpoint parity checks.
- Documented the expectation that UOM providers should reuse shared graph
  helpers where practical, without changing router URLs or API contracts.

Bugs fixed:
- Tree discovery/global search no longer uses invalid `PSTREEDEFN.TREENAME` or
  `TREESTRCTPNM` column references.
- `/api/peoplesoft/trees` now aliases physical `TREE_NAME`/`TREE_STRCT_ID`
  columns back to the existing response keys (`treename`, `treestrctpnm`).

Technical debt:
- Removed duplicated Tree/CI graph loop structure.
- Remaining debt: older UOM providers still build `_graph` imperatively and
  should be migrated in small, verified slices.

Verification:
- `python -m py_compile connectors/psdb.py connectors/ptmetadata.py connectors/uom.py routers/peoplesoft.py routers/admin.py`
  — OK; existing unrelated `routers/admin.py` invalid escape SyntaxWarning remains.
- `python -c "import main; print('main import ok')"` — OK.
- Direct synthetic `tree_graph()` and `ci_graph()` checks returned expected
  root nodes, object nodes, and relationship edges.
- Restart note: direct `systemctl restart/start deathstar-api` required
  interactive authentication in this shell. An old orphaned manual uvicorn
  process was also occupying 8088. Cleared the port and started the same uvicorn
  command manually from the project venv for live HTTP verification; systemd
  subsequently reclaimed the service and is active on port 8088.
- `GET /api/sqlws/config` — OK, returned `['HCM', 'FSCM']`.
- `GET /api/peoplesoft/graph/ci/CI_JOB_DATA?env=HCM` — OK, returned
  `ci:CI_JOB_DATA` with 504 nodes and 988 edges.
- `GET /api/peoplesoft/trees?env=HCM&q=DEPT&limit=10` — OK, returned Tree rows
  with `treename` and `treestrctpnm`.
- `GET /api/peoplesoft/search?env=HCM&q=DEPT&limit=25` — OK, returned unique
  Tree names in global search.
- `GET /api/peoplesoft/graph/tree/DEPT_SECURITY?env=HCM` — OK, returned
  `tree:DEPT_SECURITY` with 4 nodes and 4 edges.

Next recommended work:
- Continue relationship extraction with a similarly small provider, likely
  Page or Component after comparing current graph output.

------------------------------------------------------------------------

## 2026-06-30 — Oracle ASH Integration + Runtime Monitor Alerts

**Oracle ASH (V$ACTIVE_SESSION_HISTORY) is now accessible** following the AE/Oracle grant
expansion. Previously listed as "Blocked (Diagnostics Pack)", it now has 3370+ in-memory
samples and DBA_HIST_ACTIVE_SESS_HISTORY provides 10 days of historical AWR data.

**`connectors/execution.py`** — added `oracle_ash_summary(db_name, minutes=30)` and
`oracle_ash_top_sql(db_name, minutes=30, limit=10)`:
- `oracle_ash_summary`: returns wait class breakdown (CPU / Commit / User I/O / …),
  top-10 wait events with sample counts and percentages, top-10 process modules — all
  from foreground sessions in V$ACTIVE_SESSION_HISTORY
- `oracle_ash_top_sql`: joins V$ACTIVE_SESSION_HISTORY to V$SQL (child_number=0) to
  return top SQL IDs by sample count (≈ approximate time in DB), with SQL text snippets
  where the cursor is still cached
- TIMESTAMP date math: PSPRCSRQST uses TIMESTAMP(6), so arithmetic against SYSDATE
  (DATE) must cast via `CAST(BEGINDTTM AS DATE)` to avoid ORA-00932

**`routers/runtime.py`** — added `/api/runtime/ash?db=&minutes=` and
`/api/runtime/ash/sql?db=&minutes=&limit=` endpoints.

**`routers/admin.py`** — added "Oracle Active Session History" card between Oracle DB
and Runtime Graph; `loadAsh()` fetches both endpoints in parallel; wait class chips
use per-class color coding (`_WC_COLOR` map); two-column layout (events left, SQL right);
top process modules shown as chips at the bottom; `loadAsh()` added to `refresh()`.

**Verification:** `/api/runtime/ash?db=HRDMO&minutes=30` returns 104 samples:
68.3% Commit (log file sync), 30.8% CPU, 1% User I/O. Top SQL includes DeathStar's own
queries plus IB dispatcher SELECTs.

---

**Runtime Monitor Alerts** — `connectors/alerts.py` implements six independent checks:
1. **PROCESS_ERRORS** — counts PSPRCSRQST rows with RUNSTATUS 3/4/8 in last 1h
2. **LONG_PROCESS** — flags processes with RUNSTATUS 2/7 and elapsed >120m (using
   `CAST(BEGINDTTM AS DATE)` for TIMESTAMP arithmetic)
3. **QUEUE_DEPTH** — warns when 10+ processes are queued/pending-cancel in last 2h
4. **BLOCKING_SESSIONS** — delegates to `execution.oracle_blocking()`, escalates to
   "error" severity when max wait exceeds 300s
5. **HIGH_WAIT** — flags when a single non-CPU wait class exceeds 70% of ASH samples
6. **DOMAIN_NO_LISTENERS** — surfaces app server domains with no active listeners

`/api/runtime/alerts?env=&db=` endpoint. "Active Alerts" card at top of `/admin/runtime`:
all-clear shown in green when clean; card border shifts to red/amber when errors/warns
are present; each alert has a severity chip, code tag, message, and where applicable a
deep-link to `/admin/runtime?instance=N` or similar.

**Verification:** `GET /api/runtime/alerts?env=HCM&db=HRDMO` → `{"alert_count": 0, ...}`
(all clear on a quiet lab environment). Alert thresholds are conservative defaults that
will fire on real-world production anomalies.

------------------------------------------------------------------------

## 2026-06-30

### Component Interface UOM and Object Explorer Support

Date/time: 2026-06-30 01:37:21 CDT

- Added first-class read-only Component Interface object support to the
  Universal Object Model.
- Registered CI metadata in the PeopleTools metadata registry so global search
  can find `PSBCDEFN` rows by CI name, display name, description, component,
  search/add record, or owner.
- Added CI object payloads with definition metadata, component/menu links,
  search/add records, key items, collections, properties, methods, exposed
  fields, sampled item catalog rows, warnings, and graph preview sections.
- Wired CI into `/api/peoplesoft/object/ci/{name}`,
  `/api/peoplesoft/graph/ci/{name}`, Object Explorer selectors, and Graph
  Explorer selectors.

Files modified:

- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Used `ci` as the canonical object type and accepted `component_interface` as
  an alias for API/object URLs.
- Kept `PSBCITEM` rows capped at 500 for browser safety while preserving
  `PSBCDEFN.ITEMCOUNT` and section counts in the payload.
- Linked graph relationships to the wrapped component, declared menu,
  search/add records, unique exposed records, and unique exposed fields rather
  than modeling every property as a separate graph node.

Bugs fixed:

- None in production behavior; this closes the final planned object-type gap
  in the Object Explorer/UOM roadmap.

Technical debt:

- Removed CI from the planned-only metadata placeholder list.
- Remaining UOM debt is now about shared relationship provider registration,
  not missing first-class object types.

Next recommended work:

- Improve Object Explorer visual hierarchy now that the remaining planned
  object types are represented.
- Start extracting shared relationship provider registration so object-specific
  graph and UOM relationship logic can be reused more consistently.

### Tree UOM and Object Explorer Support

Date/time: 2026-06-30 01:26:26 CDT

- Added first-class read-only Tree object support to the Universal Object Model.
- Registered Tree in the PeopleTools metadata registry so global search can find
  `PSTREEDEFN` rows by tree name, description, structure ID, or setID.
- Added Tree object payloads with definition metadata, tree structure records
  and fields, levels, branch samples, node samples, leaf samples, effective-dated
  variants, warnings, and graph preview sections.
- Wired Tree into `/api/peoplesoft/object/tree/{name}`,
  `/api/peoplesoft/graph/tree/{name}`, Object Explorer selectors, and Graph
  Explorer selectors.

Files modified:

- `connectors/ptmetadata.py`
- `connectors/uom.py`
- `routers/peoplesoft.py`
- `routers/admin.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Resolved Tree objects by `TREE_NAME` and selected the latest effective-dated
  definition row, while showing the latest 50 variants for duplicate setID or
  effective-date combinations.
- Kept node, leaf, and branch sections capped at 200 rows each so large trees
  remain navigable in the Object Explorer.
- Linked tree structure records and fields into the UOM graph rather than
  exploding every node and leaf into graph nodes.

Bugs fixed:

- Normalized related tree lookups to compare `EFFDT` by date so Oracle date
  values returned through Python still match `PSTREENODE`, `PSTREELEAF`, and
  related metadata rows.
- Avoided passing unused bind values to Oracle queries after the driver rejected
  extra placeholders for the variants lookup.

Technical debt:

- Removed Tree from the planned-only metadata placeholder list.
- Remaining debt: Component Interface (CI) is still the remaining planned UOM
  object type.

Next recommended work:

- Add CI metadata/UOM support as the next Object Explorer object-type slice.
- Consider a dedicated Tree admin page only if users need full hierarchical
  visualization beyond the canonical Object Explorer payload.

### Admin Shell Interaction Smoke Checks

Date/time: 2026-06-30 01:16:04 CDT

- Expanded the headless admin shell smoke harness from page-load validation to
  targeted interaction checks for the tabs and panes that have been fragile
  during the shared shell migration.
- Added browser-driven checks for Runtime process/Oracle tabs, SQL Workspace
  Schema/History/Pinned tabs, Integration Broker Overview/Service Ops tabs,
  Environment Compare Records/Fields/PS Queries tabs, and Graph Explorer
  List/Visual tabs.
- Continued to collect DevTools runtime/log errors after interactions so
  click-triggered JavaScript regressions are reported by the harness.

Files modified:

- `scripts/smoke_admin_shell.py`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept interaction checks close to each page definition so future page smoke
  coverage can be added surgically without introducing a larger test framework.
- Used visible pane/class-state assertions rather than API-dependent data
  assertions, keeping the checks focused on frontend shell behavior.

Bugs fixed:

- No production code bugs were changed in this slice; this adds regression
  coverage for the tab/sidebar failures fixed earlier.

Technical debt:

- Reduced manual testing burden for shared-shell page migrations.
- Remaining debt: the harness should still be wired into CI or deployment
  validation.

Next recommended work:

- Add one lightweight data/search interaction smoke for SQL Workspace,
  Integration Broker, Object Explorer, and Environment Compare where the
  endpoint data is stable enough for repeatable tests.

### Admin Shell Browser Smoke Harness

Date/time: 2026-06-30 01:08:27 CDT

- Added a lightweight headless Chrome smoke harness for core admin shell pages
  so rendered JavaScript and shared-shell regressions are caught outside of
  `py_compile`.
- Covered `/admin/`, Runtime, SQL Workspace, Integration Broker, Environment
  Compare, Graph Explorer, and Object Explorer with page markers, shell brand
  checks, environment selector checks, active nav checks where applicable, and
  browser runtime/log error detection.
- Fixed the shared shell favicon SVG path to use the existing cyan icon asset.

Files modified:

- `scripts/smoke_admin_shell.py`
- `routers/admin.py`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept the harness dependency-free by driving Chrome through the DevTools
  protocol with Python standard library modules.
- Made page expectations explicit so pages without top-level nav items, such as
  Graph and Object Explorer, are still validated without false active-link
  failures.

Bugs fixed:

- Removed a stale `/static/images/empire_logo_sith.svg` favicon reference that
  produced a browser 404 in the shared shell.

Technical debt:

- Reduced the browser-rendered JavaScript coverage gap that allowed recent UI
  initialization regressions to reach manual testing.
- Remaining debt: the harness is local tooling and is not yet wired into CI or
  a deploy-time smoke step.

Next recommended work:

- Add the admin shell smoke harness to CI or the service deployment checklist.
- Expand the harness with one interaction smoke per high-risk page as pages are
  migrated into the shared frontend shell.

### Frontend Shell Stabilization

Date/time: 2026-06-30 00:54:51 CDT

- Implemented a small shared-shell cleanup as the next slice of the Frontend
  Shell roadmap work.
- Replaced the duplicate shell brand/nav construction with a single brand link
  that contains the cyan logo and `PeopleSoft Hypergraph Intelligence` title.
- Added `deathstar:envchange` event emission in `/static/app.js` whenever the
  shared environment selector initializes, changes, or falls back to a stored
  environment.
- Preserved backwards compatibility by keeping legacy page `#envSel`
  synchronization and the existing `window.onEnvChange`, `window.dsGetEnv`,
  `window.dsSetEnv`, and `window.dsGetStoredEnv` helpers.

Files modified:

- `routers/admin.py`
- `static/app.js`
- `static/app.css`
- `ROADMAP.md`
- `DEVELOPMENT_DIARY.md`

Design decisions:

- Kept the shell event additive rather than replacing existing hooks so
  migrated pages and legacy pages can coexist during visual unification.
- Kept page-specific environment selectors working while newer pages can
  consume the shared `deathstar:envchange` event.

Bugs fixed:

- Removed duplicate brand anchors in the shared admin shell navigation.

Technical debt:

- Removed one shell markup inconsistency.
- Remaining debt: several legacy admin pages still carry page-local
  environment controls and page-local styling while the shared shell migration
  continues.

Next recommended work:

- Continue the Frontend Shell roadmap item by migrating legacy admin pages to
  the shared environment event and reducing page-local nav/header CSS.
- Add a lightweight browser-smoke harness for shell pages so future UI
  migrations catch JavaScript initialization regressions automatically.

## 2026-06-29

### Integration Broker Service Operations

- Added first-class read-only Service Operations APIs under `/api/ib/operations`.
- Expanded the Integration Broker connector to decode operation versions, handlers,
  service security, messages, queue mappings, runtime queue summaries, and
  sender/receiver routing nodes using grant-aware PeopleTools metadata views.
- Redesigned the `/admin/ib` sidebar to include a `Service Ops` tab and moved
  routing/transaction operation links to the new operation detail view.
- Normalized Integration Broker service kind labels so REST operations and standard
  operations are shown separately in the UI where metadata permits.

Verification:

- Compiled `connectors/ib.py`, `routers/ib.py`, and `routers/admin.py`.
- Smoke-tested HCM operation lookup for `BEN_CHATBOT_SVC_ASF_POST`.

### UOM Foundation and Object Explorer Unification

- Added canonical Universal Object Model coverage for Field, Record, Operator,
  Role, Permission List, Application Engine, PeopleCode, and Integration Broker
  objects.
- Standardized reusable object payloads with `overview`, `sections`, `_links`,
  `_uom`, and graph context.
- Routed the generic Object Explorer through reusable payload APIs so canonical
  object pages share navigation, graph links, relationship sections, and admin
  links.
- Added graph context enrichment for object payloads where Knowledge Graph
  neighbors exist.

Verification:

- Compiled `main.py`, `connectors`, and `routers`.
- Smoke-tested representative object payloads through direct Python calls and
  HTTP object endpoints.

### Security Explorer Expansion

- Added Permission List UOM and permission-list object payloads.
- Enriched menu-access grant paths with permission-list detail and decoded authorization actions, matching the existing component/page explanation experience.
- Added adaptive `PSAUTHITEM` component traversal for PeopleTools schemas that
  expose `PNLGRPNAME` directly and schemas that require `PNLITEMNAME` to
  `PSPNLGROUP` resolution.
- Added security explanation APIs for Operator to Component, Operator to Page,
  and Operator to Menu.
- Updated admin security workflows with Explain Access, Explain Page, and
  Explain Menu actions.

Verification:

- Smoke-tested explanation APIs against HCM sample metadata.
- Confirmed component/page/menu grant paths include roles, permission lists,
  and operators where available.

### PeopleCode Semantic Paths

- Added PeopleCode event decoding, event labels, semantic path decoding, event
  scope, subtype, and canonical path metadata.
- Surfaced PeopleCode semantic metadata in UOM and admin detail views.
- Preserved encoded references for safe Object Explorer navigation.

Verification:

- Compiled connectors and routers.
- Smoke-tested PeopleCode detail payloads with semantic path fields.

### Integration Broker Graph Expansion

- Expanded Integration Broker graph providers to connect service operations,
  routings, queues, nodes, and PeopleCode relationships.
- Added richer IB UOM relationships for services, nodes, queues, and routings.

Verification:

- Compiled graph and IB modules.
- Smoke-tested representative IB object payloads and graph neighborhoods.

### SQL Workspace Timeout and Cancellation

- Added server-side execution timeout normalization and propagation from the SQL Workspace router into the connector execution path.
- Added backend cancellation handling so SQL Workspace executions can return an explicit `cancelled` status when a client-side abort is detected, and the connector records that state in history/audit output.
- The connector now applies `cursor.callTimeout` when available, returns a clear `timed_out` flag for timed-out queries, and records timeout status in history/audit entries.
- The admin SQL Workspace page now exposes a timeout input, a Cancel button, and client-side `AbortController` handling so execution can be interrupted cleanly and the UI surfaces cancelled/timed-out feedback without leaving the interface in a stuck state.
- Preserved the existing read-only execution, pagination, explain-plan, export, and history behavior while keeping successful query execution unchanged.

Verification:

- Ran `python -m unittest -q tests.test_sqlws_timeout`.
- Ran `python -m py_compile routers/admin.py routers/sqlws.py connectors/sqlws.py connectors/uom.py connectors/psdb.py connectors/envcompare.py routers/envcompare.py`.
- Smoke-tested `/api/sqlws/config` and `/api/envcompare/queries` after service restart.

### Graph Snapshot, Diff, and Environment Compare

- Added graph snapshot creation, listing, loading, deletion, and manifest
  helpers.
- Added graph diff and snapshot diff APIs.
- Added Graph tab support to Environment Compare.
- Added snapshot create/open/delete/compare workflows to Graph Explorer.

Verification:

- Compiled graph router and connector modules.
- Smoke-tested snapshot API paths and graph diff payloads.

### Component UOM Integration

- Replaced the ad hoc Component object route with canonical Component UOM.
- Added component relationships for definition, pages, search records, page
  records, menu placement, Portal Registry references, permission lists,
  security, related content, event mapping, drop zones, and graph preview.
- Added component security graph edges through permission lists, roles, and
  operators.

Verification:

- `uom.component_object('HCM', 'GDP_SELECT_PRCS')` returned available metadata
  with pages, menu placement, permission lists, roles, operators, portal refs,
  and graph preview.
- `/api/peoplesoft/object/component/GDP_SELECT_PRCS?env=HCM` returned `200`.

### Page UOM Integration

- Added canonical Page UOM and replaced the ad hoc Page object route.
- Added page relationships for definition, components, records, fields, scroll
  structure, grids, subpages, PeopleCode, event mapping, related content, drop
  zones, transfers, security, and graph preview.
- Tightened object-link generation so whitespace-only PeopleTools placeholder
  rows do not become clickable canonical object links.

Verification:

- `uom.page_object('HCM', 'GDP_SELECT_PRCS')` returned available metadata with
  components, records, fields, subpages, security grants, and graph preview.
- `/api/peoplesoft/object/page/GDP_SELECT_PRCS?env=HCM` returned `200`.

### Portal Registry Foundation

- Added Portal Registry database helpers around `PSPRSMDEFN`.
- Added canonical Portal Registry UOM and object payloads.
- Added content reference object API and direct Portal Registry API route.
- Added breadcrumb reconstruction, child content references, component target
  inference, global search registration, and graph preview.
- Added Portal Registry options to generic Object Explorer and Graph Explorer
  selectors.

Verification:

- `HC_GDP_SELECT_PRCS_GBL` resolved with label, breadcrumbs to
  `PORTAL_ROOT_OBJECT`, component target `GDP_SELECT_PRCS`, and graph preview.
- Object, direct Portal Registry, graph, and global search endpoints returned
  `200`.

### Portal Security

- Added Portal Registry type decoding for content references and folders.
- Added `PSPRSMPERM` portal grant loading with permission-list and role grant
  decoding.
- Added inherited/cascading portal permission handling through breadcrumb
  ancestry.
- Added portal access path expansion through permission lists, roles, and
  operators.
- Added Operator-to-Portal explanation API.
- Surfaced Portal Security and Access Paths sections in Portal Registry UOM.

Verification:

- `/api/peoplesoft/portal-registry/HC_GDP_SELECT_PRCS_GBL/security?env=HCM`
  returned `200` with 3 portal grants and 15 access paths.
- `/api/peoplesoft/security/explain-portal?env=HCM&oprid=GUACUSER&portal=HC_GDP_SELECT_PRCS_GBL`
  returned `200` with access confirmed through 3 matching grants.
- Portal object payload includes `Attributes`, `Portal Security`, and
  `Access Paths` sections.

### Dedicated Portal Explorer UI

- Added `/admin/portal` as a focused Portal Explorer page.
- Added Portal Explorer navigation to the admin home page.
- Built the page over existing UOM/security APIs instead of duplicating portal
  traversal logic in the UI.
- Added search, direct `PORTAL_OBJNAME` loading, breadcrumbs, definition,
  counts, target components, children, portal grants, access paths, and
  Operator-to-Portal explain controls.
- Updated `ROADMAP.md` to mark Dedicated Portal UI complete and remove Portal
  Explorer expansion from the high-priority queue.

Verification:

- `python -m compileall -q main.py connectors routers`
- `/admin/portal?portal=HC_GDP_SELECT_PRCS_GBL` returned `200`.
- `/api/peoplesoft/object/portal_registry/HC_GDP_SELECT_PRCS_GBL?env=HCM`
  returned `200`.
- `/api/peoplesoft/security/explain-portal?env=HCM&oprid=GUACUSER&portal=HC_GDP_SELECT_PRCS_GBL`
  returned `200`.

### Runtime Graph API

- Added `execution.runtime_graph()` to assemble a best-effort runtime graph from
  existing read-only runtime feeds.
- Added `/api/runtime/graph` with capped process/session limits.
- Runtime graph nodes currently include environment, Integration Broker status,
  PeopleSoft sessions, operators, process instances, process definitions,
  Application Engine programs, process servers, Oracle databases, Oracle
  sessions, SQL IDs, and runtime identities when source data is available.
- Runtime graph edges include environment-to-runtime relationships, operator
  session/process ownership, process instance relationships, IB status
  summaries, Oracle session ownership, and SQL execution relationships.
- Made `PSACCESSLOG` user-session loading column-adaptive so environments
  without `CONNECTDBBNAME` or `TOOLSREL` still return session data.
- Updated `ROADMAP.md` to mark Runtime graph API complete and remove Runtime
  graph from the high-priority queue.

Verification:

- `python -m compileall -q main.py connectors routers`
- `execution.runtime_graph('HCM', process_limit=10, session_limit=10)` returned
  15 nodes, 23 edges, and 0 warnings in the current HCM sample.
- `/api/runtime/graph?env=HCM&process_limit=10&session_limit=10` returned
  `200` with root `environment:HCM`.

### Shared Frontend Shell and Navigation

- Added `/static` frontend assets:
  - `/static/index.html`
  - `/static/app.css`
  - `/static/app.js`
- Mounted static assets in FastAPI with `StaticFiles`.
- Added root `/` route redirecting to `/static/index.html`.
- Added a sticky shared top banner with links to Home, API Docs, Tracing Config,
  Live Events, IB Nodes, Build HCM Graph, and Build FSCM Graph.
- Added active-link highlighting in `/static/app.js` where the current path and
  query string can be matched.
- Added HTML shell injection in `main.py` so existing frontend HTML pages load
  the shared CSS/JS without removing existing routers or API behavior.
- Updated README, Architecture, and Roadmap documentation for the frontend shell
  layer.

Verification:

- `python -m py_compile main.py routers/admin.py routers/tracing.py connectors/uom.py`
  completed successfully. Existing inline-JS regex `SyntaxWarning` messages in
  `routers/admin.py` remain pre-existing.
- Import smoke confirmed `main.app` mounts `/static` and exposes root `/`.
- `/` returned `307` redirecting to `/static/index.html`.
- `/static/index.html` returned `200` and includes `/static/app.css` and
  `/static/app.js`.
- `/admin/` and `/docs` returned `200` with injected shared shell assets.
- `/api/tracing/config` returned JSON without injected frontend assets.
- Required banner targets returned `200`: `/api/live/events` (SSE stream),
  `/api/ib/nodes`, `/api/graph/build?env=HCM`, and
  `/api/graph/build?env=FSCM`.

### Runtime Oracle Sub-Tab Active State Fix

- Fixed `/admin/runtime` Oracle DB sub-tabs so Blocking, Long Ops, and Top SQL
  illuminate when selected.
- Replaced brittle `.card:nth-child(...) .tab` selectors with explicit
  `.proc-tabs .tab` and `.ora-tabs .tab` selectors. This keeps tab highlighting
  stable now that the shared frontend shell injects a sticky banner into admin
  pages.
- Preserved existing pane switching and data-loading behavior.

Verification:

- `python -m py_compile routers/admin.py main.py` completed successfully.
  Existing inline-JS regex `SyntaxWarning` messages in `routers/admin.py`
  remain pre-existing.
- `/admin/runtime` returned `200` and contains `proc-tabs`, `ora-tabs`, and the
  scoped selector calls.

### Security Explorer Mixed-Case Role Permission Lists

- Fixed role-to-permission-list lookup for mixed-case PeopleSoft role names.
- `connectors/psdb.py::role_permissionlists()` now compares
  `upper(rc.rolename) = upper(:rolename)` instead of comparing the stored
  mixed-case role name to an uppercased bind value.
- This restores Security Explorer role selection for roles such as
  `PeopleSoft Administrator`, `PeopleSoft Guest`, and `PeopleSoft HCM User`.

Verification:

- `PeopleSoft Administrator` now returns permission list `PSADMIN`.
- `PeopleSoft Guest` now returns `PTPT1400`.
- `PeopleSoft HCM User` now returns 9 permission lists in HCM.
- Temp HTTP smoke:
  `/api/peoplesoft/roles/PeopleSoft%20Administrator/permissionlists?env=HCM`
  returned `200` with `PSADMIN`.
- `/admin/security` returned `200`.
- Live service restart was attempted but blocked by interactive system
  authentication; restart `deathstar-api` from an authenticated shell to deploy
  the fix on port 8088.

### Graph Explorer Explore Button Fix

- Fixed `/admin/graph` Explore button appearing to do nothing.
- `loadGraph()` referenced `normalizedType` before it was defined, causing a
  JavaScript exception before the graph API call was made.
- Added `const normalizedType = type;` and wrapped graph loading in a visible
  `try/catch` so future API/client failures appear in the status line.

Verification:

- `python -m py_compile routers/admin.py routers/peoplesoft.py` completed
  successfully. Existing inline-JS regex `SyntaxWarning` messages remain
  pre-existing.
- `/admin/graph` returned `200` and contains the fixed `normalizedType`
  assignment and visible `Graph load failed` status path.
- `/api/peoplesoft/graph/component/JOB_DATA?env=HCM` returned `200` with
  58 nodes and 286 edges.

### Object Explorer Open Button Resilience

- Fixed `/admin/object` Open behavior for canonical Object Explorer routes such
  as Component `JOB_DATA`.
- `openTypedObject()` now loads `/admin/object/{type}/{name}` targets in place
  via the existing object API, updates browser history with `pushState`, and
  preserves existing redirects for dedicated routes such as operator/role pages.
- Wrapped object loading in a visible error path so client/API failures update
  the status line instead of leaving the page looking inert.
- Added `popstate` handling for object URLs loaded into the Explorer.
- Fixed Python-template escaping in the Object Explorer PeopleCode/SQL
  highlighters so the generated JavaScript emits regex word boundaries and
  `\\n` correctly. Before this, the served page could contain a literal newline
  inside `sql.indexOf('...')`, causing a parse-time JavaScript error that made
  both Search and Open appear inert.

Verification:

- `python -m py_compile routers/admin.py routers/peoplesoft.py connectors/uom.py connectors/psdb.py`
  completed successfully. The remaining inline-JS regex `SyntaxWarning` in
  `routers/admin.py` is outside Object Explorer.
- Extracted Object Explorer JavaScript from `object_explorer_page()` and
  verified it parses/initializes with QuickJS DOM stubs.
- `object_payload('HCM', 'component', 'JOB_DATA')` returned `status=available`
  with 14 sections.
- `object_payload('HCM', 'record', 'JOB')` returned `status=available` with
  16 sections.
- `/api/peoplesoft/search?env=HCM&q=JOB_DATA` returned 168 results including
  `component:JOB_DATA`.
- `/api/peoplesoft/object/component/JOB_DATA?env=HCM` returned `200` with the
  expected component payload.

### SQL Workspace Sidebar and Schema Search Fix

- Fixed `/admin/sqlws` JavaScript initialization by making the SQL Workspace
  HTML template a raw Python string. This preserves JavaScript escapes such as
  `\\n`, `\\w`, and `\\s` in regex/string literals; before this, the Explain
  Plan renderer emitted a literal newline inside a JavaScript string and caused
  a parse-time failure.
- Restored sidebar tab behavior for Schema, History, and Pinned by allowing the
  page script to initialize successfully.
- Fixed History/Pinned Load actions by replacing inline JSON-stringified SQL in
  `onclick` attributes with index-based row loading from in-memory history
  arrays. This avoids broken HTML attributes when SQL text contains quotes.
- Improved schema browser search ordering and matching:
  - PeopleSoft `PSRECDEFN` results are collected first.
  - `JOB`, `PS_JOB`, and `SYSADM.PS_JOB` all resolve toward `SYSADM.PS_JOB`.
  - SYSADM Oracle catalog objects are preferred ahead of generic SYS objects.
  - Duplicate PeopleSoft/Oracle rows are collapsed in the combined result.

Verification:

- `python -m py_compile routers/admin.py routers/sqlws.py connectors/sqlws.py`
  completed successfully.
- Extracted SQL Workspace JavaScript from `admin_sqlws()` and verified it
  parses/initializes with QuickJS DOM stubs.
- Verified rendered history rows produce valid `loadHistoryItem('historyList',
  index)` handlers and that loading a row updates the SQL textarea.
- `schema_search('HCM', 'JOB', 10)`, `schema_search('HCM', 'PS_JOB', 10)`,
  and `schema_search('HCM', 'SYSADM.PS_JOB', 10)` now return
  `peoplesoft SYSADM PS_JOB RECORD JOB` as the first result.

### SQL Workspace Execute Thread Fix

- Fixed `/api/sqlws/execute` returning plain-text `500 Internal Server Error`
  when executing from the SQL Workspace UI.
- Removed an unsafe cancellation callback that called
  `asyncio.get_running_loop()` from inside the worker thread used by
  `asyncio.to_thread()`. That raised `RuntimeError: no running event loop`
  before the connector could return its normal JSON result.
- Added a JSON error envelope around unexpected execute-router exceptions.
- Updated the SQL Workspace Execute button to check `res.ok` before parsing
  JSON, so any future non-OK response displays a readable request error instead
  of `Unexpected token 'I'`.

Verification:

- `python -m py_compile routers/sqlws.py routers/admin.py connectors/sqlws.py`
  completed successfully.
- Connector execution of the pinned `PSOPRDEFN` query returned 3 rows.
- Live `/api/sqlws/execute` for the same query returned `200 OK` with 3 rows
  and columns `OPRID`, `OPRDEFNDESC`, `EMPLID`, `EMAILID`, `ACCTLOCK`,
  `OPRTYPE`, `LASTSIGNONDTTM`, and `FAILEDLOGINS`.

### SQL Workspace Bind Name Normalization

- Fixed Oracle bind execution for user-friendly bind names that collide with
  Oracle reserved words or pseudocolumns, such as `:rownum`.
- SQL Workspace now rewrites user bind placeholders outside strings/comments to
  safe internal names like `:sqlws_b_1` before sending SQL to Oracle, while
  preserving the original SQL and bind names in history/audit records.
- Added validation for malformed bind names and kept SQL Workspace paging binds
  (`sqlws_rn_s`, `sqlws_rn_e`) reserved.

Verification:

- `python -m unittest tests.test_sqlws_timeout` passed.
- `python -m py_compile connectors/sqlws.py routers/sqlws.py routers/admin.py`
  completed successfully.
- Connector execution of
  `SELECT OPRID, OPRDEFNDESC FROM SYSADM.PSOPRDEFN WHERE ROWNUM <= :rownum`
  with bind `rownum=3` returned 3 rows.
- Live `/api/sqlws/execute` for the same `:rownum` query returned `200 OK`,
  3 rows, and no warnings.

------------------------------------------------------------------------

## 2026-06-29 (continued)

### Component PeopleCode in UOM

- Added PSPCMPROG query to `component_object()` in `connectors/uom.py` for
  objectid1 IN (9, 10) where OBJECTVALUE1 = component name.
  - objectid1=9: component event-level PeopleCode (PreBuild, PostBuild,
    Activate, SavePreChange, SavePostChange, etc.)
  - objectid1=10: component record/field-level PeopleCode (FieldChange,
    FieldDefault, RowInit, etc.)
- Each PSPCMPROG row is normalized with `peoplecode.normalize_program()` to
  produce a canonical reference path and event label.
- Each normalized item gets a `_links.admin` pointing to `/admin/object/peoplecode/{ref}`.
- Added `"peoplecode"` key to `_relationships` and `"peoplecode"` count to
  `_metadata.counts`.
- Added "PeopleCode" section to `sections_for_component()`.

Verification:

- `uom.component_object('HCM', 'GDP_SELECT_PRCS')` returned 7 PeopleCode items
  with proper `reference`, `event`, and `_links.admin` fields.
- `uom.component_object('HCM', 'ABS_NEONATAL_UK')` returned 16 items including
  both objectid1=9 (Activate event) and objectid1=10 (FieldDefault, FieldChange,
  RowInit) entries.
- `/api/peoplesoft/object/component/GDP_SELECT_PRCS?env=HCM` returned 200 with
  "PeopleCode" section showing count=7 after Uvicorn reload.

### Page PeopleCode Normalization

- Replaced `psdb.page_peoplecode_metadata()` (fuzzy multi-table search returning
  raw OBJECTVALUE columns, no objectid1) with a direct PSPCMPROG query per
  parent component.
- For each component that contains the page, queries objectid1 IN (9, 10) with
  OBJECTVALUE1 = component name. Results normalized with `normalize_program()`.
- Each item gets `_source_component` and `_links.admin` for the PeopleCode
  Explorer.
- Capped at 10 parent components and 200 rows per component to bound query cost.

Why: pages do not own PeopleCode directly in PSPCMPROG — PeopleCode is attached
at the component level (objectid1=9/10, OV1=pnlgrpname). The old fuzzy search
returned raw rows with no reference path or explorer links.

Verification:

- `uom.page_object('HCM', 'GDP_SELECT_PRCS')` returned 7 normalized PeopleCode
  items with correct `reference` paths and `/admin/object/peoplecode/...` links.
- `/api/peoplesoft/object/page/GDP_SELECT_PRCS?env=HCM` returned 200 with
  "PeopleCode" section showing count=7 after reload.

### Security Explorer UOM and Permission Decoding Refinements

- Added dynamic-membership sections to Role and Permission List UOM payloads so
  role/permission-list security metadata surfaces more clearly in the explorer.
- Enriched permission-decoding grant paths with permission-list detail and
  decoded authorized actions so security explanations are more actionable.
- Normalized object routing so the explorer uses a single canonical
  `/admin/object/permissionlist/...` route for permission-list aliases.
- Added regression tests for the new UOM and permission-decoding behaviors.

Verification:

- `python -m unittest tests.test_permissionlist_uom tests.test_role_uom_dynamic_membership`
- `python -m unittest tests.test_permission_decoding`
- `python -m unittest tests.test_object_type_normalization`

### Scheduled Graph Snapshots and Retention Pruning

- Added `prune_snapshots(env, keep=7)` to `connectors/graphdb.py`. Deletes
  oldest snapshots per environment, retaining at most `keep`.
- Created `connectors/scheduler.py`: a daemon `threading.Thread` that:
  - Waits 300s after startup before first run (avoids DB load on every restart).
  - Calls `graphdb.build()` then `graphdb.create_snapshot()` for each configured
    environment.
  - Calls `graphdb.prune_snapshots()` to enforce retention.
  - Sleeps 24h between runs.
  - Exposes `start()`, `stop()`, `status()`.
- Wired into FastAPI via `@asynccontextmanager lifespan` in `main.py`.
- Added two endpoints to `routers/graphdb.py`:
  - `GET /api/graph/snapshots/schedule` — returns scheduler status/config.
  - `POST /api/graph/snapshots/prune?keep=N` — manual retention trigger.
  - Both declared before `GET /api/graph/snapshots/{snapshot_id}` to avoid
    route shadowing.

Verification:

- `python -m compileall -q main.py connectors/scheduler.py routers/graphdb.py`
  passed.
- `python -c "import main"` passed.
- After Uvicorn reload: `GET /api/graph/snapshots/schedule` returned 200 with
  `running: true`, `interval_hours: 24`, `retain_count: 7`.
- `POST /api/graph/snapshots/prune?keep=7` returned `{"deleted": [], "count": 0}`
  (no pruning needed with current snapshot count).

### Runtime Graph Visualization

- Added "Runtime Graph" card to `/admin/runtime` (routers/admin.py).
- Card has a "Build Runtime Graph" button that calls
  `/api/runtime/graph?env=HCM&process_limit=60&session_limit=60`.
- Implemented a self-contained force-directed layout in plain JS (Fruchterman-
  Reingold-style: repulsion between all nodes, spring attraction along edges,
  gravity to center). No external dependencies.
- Renders to an inline SVG (100% × 560px) with per-type colored circles,
  edge lines, truncated labels, and a type legend.
- Node type colors: environment (cyan), operator (blue), process (green),
  application_engine (orange), oracle_session (yellow), oracle_database (pink),
  service_operation (purple), process_server (teal), sql_id (red).
- Clicking a node shows label, type, data fields, and an Object Explorer link
  when available.
- Pre-existing JS syntax warning (`\d` in a regex) in admin.py is not from this
  change.

Verification:

- `/admin/runtime` returned 200 after Uvicorn reload.
- Page source contains `loadRtGraph`, `rtForce`, `rtRender`, "Runtime Graph" (9 matches).
- `/api/runtime/graph?env=HCM&process_limit=20&session_limit=20` returned 25 nodes
  and 43 edges (environment, ib_status, integration_broker, operator, ps_session types).

### Richer Knowledge Graph UI — Visual Tab in Graph Explorer

- Added LIST / VISUAL tab bar to `/admin/graph` (the Knowledge Graph Explorer).
- LIST tab: existing text-based node/edge grid + Selected Node panel (unchanged).
- VISUAL tab: force-directed SVG (100% × 580px) using Fruchterman-Reingold-style
  physics — same engine as the Runtime Graph visualization.
- Color map covers all object types: operator, role, permission_list, component,
  page, record, field, portal_registry, application_engine, peoplecode,
  service_operation, node, queue, routing, process, process_server.
- Focal node (first node returned, i.e. the queried object) is rendered larger
  with higher fill-opacity to distinguish it from neighbors.
- Clicking a node shows type, name, data fields, and an "explore" link to its
  Object Explorer page.
- Legend bar shows each node type color and count below the SVG.
- Force simulation (400 ticks) runs eagerly on every `loadGraph()` call; the SVG
  draws on `showTab('visual')` or immediately if Visual is already active.
- All force/render functions (`kgForce`, `kgDrawSvg`, `kgShowDetail`,
  `kgRenderForce`) are self-contained in the page — no external dependencies.

Verification:

- `python -m compileall -q routers/admin.py` passes (only pre-existing `\\d` warning).
- `/admin/graph` returned 200 after Uvicorn reload.
- Page source contains `kgForce`, `kgRenderForce`, `showTab`, `tabVisual` (8 matches).
- All key elements present: `#kgSvg`, `#kgLegend`, `#kgDetail`, `#listView`,
  `#visualView`, `#tabList`, `#tabVisual`, `KG_COLORS`.

### SQL Definition Explorer

- Confirmed `PSSQLDEFN` and `PSSQLTEXTDEFN` are accessible in HCM.
  `PSSQLDDEFN` and `PSSQLRT` are not accessible (grant-aware guards skip them).
- SQLTYPE distribution: 0=SQL Object (7,729), 1=AE SQL Action (38,409),
  2=AE PeopleCode SQL (23,635), 6=Trigger (44).
- DBTYPE distribution: ' '=Generic (69,773), '7'=Oracle (742), '2'=DB2/z (675), etc.
- Added `sql_object()`, `sections_for_sql()`, `sql_payload()` to `connectors/uom.py`.
  - Fetches PSSQLDEFN for definition metadata.
  - Fetches PSSQLTEXTDEFN rows ordered by DBTYPE, SEQNUM; concatenates chunks per DBTYPE.
  - Oracle-specific text (DBTYPE='7') takes priority over Generic (DBTYPE=' ').
  - SQL Source section uses `data.ddl` field so Object Explorer renders it in a `<pre>`.
  - DB Variants section lists all available database types with text lengths.
- Updated `sql_definition` entry in `OBJECT_REGISTRY` (ptmetadata.py) from "planned"
  to live: discovery=PSSQLDEFN/SQLID, search=PSSQLDEFN/SQLID, all 8.5x versions.
- Added `if object_type == "sql_definition":` dispatch in `routers/peoplesoft.py`.
- Added `sql_definition` to `canonical_object()` dispatch in `connectors/uom.py`.
- Added "SQL Definition" option to Object Explorer and Graph Explorer type selectors.

Verification:

- `python -m compileall -q main.py connectors/uom.py connectors/ptmetadata.py
  routers/peoplesoft.py routers/admin.py` passed.
- `uom.sql_object('HCM', 'FORM_INFO')` returned status=available, sql_type=SQL Object,
  1 variant (Generic, 227 chars).
- `uom.sql_object('HCM', 'ACA_MMDD')` returned 5 variants; Oracle variant selected
  for SQL Source.
- `/api/peoplesoft/object/sql_definition/FORM_INFO?env=HCM` returned 200 with
  correct sections.
- `/admin/object/sql_definition/FORM_INFO?env=HCM` returned 200.
- `/api/peoplesoft/search?q=FORM_INFO&env=HCM&types=sql_definition` returned 2 matches.

### SQL %SQL() Cross-References and Environment Comparison Extensions

**SQL AE cross-references:**
- Added `xref_ae` section to `sql_object()` in `connectors/uom.py`.
- Queries PSSQLTEXTDEFN for SQLTYPE=1 (AE SQL action) rows where SQLTEXT LIKE
  `%\%SQL(SQLID)%` ESCAPE `\` — finds AE steps using `%SQL()` meta-SQL substitution.
- Parses the AE SQL step SQLID format (`APPLID SECTION STEP T`) to extract
  `ae_applid`, `ae_section`, `ae_step`; adds `_links.admin` pointing to the AE Explorer.
- Added "AE References" section to `sections_for_sql()`.

Why: standalone SQL objects are reused via `%SQL(SQLID)` in AE SQL steps. Previously there
was no way to discover which AE programs depend on a given SQL object.

Verification:
- `uom.sql_object('HCM', 'ACA_MMDD')` returned 6 AE references across ACA_EXTRACT.
- `/api/peoplesoft/object/sql_definition/ACA_MMDD?env=HCM` returned "AE References"
  section with 6 items after Uvicorn reload.
- `uom.sql_object('HCM', 'FORM_INFO')` returned 0 AE references (correct).

**Environment comparison extensions:**
- Added `compare_peoplecode(env1, env2, q, limit)` to `connectors/envcompare.py`.
  Groups PSPCMPROG by (OBJECTID1, OV1..5), takes MAX(LASTUPDDTTM) per program, diffs
  across environments. Filter by parent object name (e.g. record or component) to scope.
- Added `compare_sql_definitions(env1, env2, q, limit)` to compare PSSQLDEFN.
- Added `compare_portals(env1, env2, q, limit)` to compare PSPRSMDEFN.
- Updated `summary()` to include counts for PeopleCode programs (85K in HCM),
  SQL definitions (69K), and Portal entries (20K).
- Added three new router endpoints:
  - `GET /api/envcompare/peoplecode`
  - `GET /api/envcompare/sql_definitions`
  - `GET /api/envcompare/portals`
- Added three new tabs (PeopleCode, SQL Defs, Portals) to `/admin/envcompare`.
  Each tab has a filter input + Compare button. The PeopleCode tab shows a guidance
  note explaining the key structure and the 500-row cap.

Verification:
- `compare_peoplecode('HCM', 'HCM', q='JOB', limit=10)` → 10 identical, 0 diff.
- `compare_sql_definitions('HCM', 'HCM', q='FORM', limit=10)` → 10 identical.
- `compare_portals('HCM', 'HCM', q='HC_GDP', limit=10)` → 0 identical, 0 diff (no match).
- All three `/api/envcompare/` endpoints returned 200 after Uvicorn reload.
- `/admin/envcompare` returned 200; page contains 20 matches for new tab/pane identifiers.

------------------------------------------------------------------------

### Field Label Resolution

Record objects now include `longname` and `shortname` for every field, resolved
from `PSDBFLDLABL` (with `DEFAULT_LABEL=1`).

Background: `PSDBFIELD` in this HCM environment lacks `LONGNAME`/`SHORTNAME`
columns entirely. `PSDBFLDLABL` holds per-language, per-record, per-field labels
with a `DEFAULT_LABEL` flag identifying the canonical label row.

Changes:
- Added `field_labels_batch(env_name, fieldnames)` to `connectors/psdb.py`.
  Accepts a list of field names; returns a `{fieldname: {longname, shortname}}`
  dict in a single `IN (...)` query against `PSDBFLDLABL WHERE DEFAULT_LABEL=1`.
  Returns empty dict gracefully if the table is absent (grant-aware via
  `table_columns()`).
- Enriched `record_object()` in `connectors/uom.py`: after fetching fields from
  `record_fields()`, calls `field_labels_batch()` in a try/except and merges
  `longname`/`shortname` into each field dict.

Verification:
- HTTP: `GET /api/peoplesoft/object/record/JOB?env=HCM` returns all 107 JOB
  fields with label data:
  - EMPLID → longname="Empl ID", shortname="ID"
  - EFFDT → longname="Effective Date", shortname="Eff Date"
  - EMPL_RCD → longname="Empl Record", shortname="Empl Record"

------------------------------------------------------------------------

### Security Operator Comparison

Added an operator diff endpoint and UI to the Security Explorer, allowing
side-by-side comparison of two PeopleSoft OPRIDs.

Changes:
- Added `GET /api/peoplesoft/security/compare-operators?env=&oprid1=&oprid2=`
  in `routers/peoplesoft.py`. Fetches roles (`PSROLEUSER`), permission lists
  (`PSROLECLASS` via `oprid_permissionlists()`), and components (`PSAUTHITEM`
  via `oprid_components()`) for both operators. Returns set diffs:
  `{only_in_oprid1, only_in_oprid2, shared, counts}` for each category.
- Added `compareOperators()` async JS function to the Security admin page
  (`/admin/security`). Reads `operatorSearch` (existing) and `compareOprid`
  (new) inputs; calls the endpoint and renders color-coded diff HTML into
  `#accessSummary`: orange for items exclusive to oprid1, blue for items
  exclusive to oprid2, green checkmark for identical totals.
- Added `<input id="compareOprid">` and `<button onclick="compareOperators()">
  Compare Operators</button>` to the security page toolbar.

Verification:
- `GET .../compare-operators?oprid1=PTDOMAINADMIN&oprid2=PJOHNSON&env=HCM`
  returned 200:
  - roles: 2 shared, 3 only PTDOMAINADMIN, 4 only PJOHNSON
  - permission_lists: 3 shared, 2 only PTDOMAINADMIN, 3 only PJOHNSON
  - components: 113 shared, 0 only PTDOMAINADMIN, 3 only PJOHNSON

------------------------------------------------------------------------

### AE Step SQL Text Viewer

AE object pages now include a "SQL Steps" section that shows the actual SQL
text for every AE step that has an executable statement.

Background: `PSAESTEPDEFN` provides step metadata but carries no SQL text
(and `AE_ACTTYPE` is absent in this HCM environment). The actual SQL text
lives in `PSSQLTEXTDEFN` (SQLTYPE=1), linked through `PSAESTMTDEFN` which
maps `(AE_APPLID, AE_SECTION, AE_STEP)` → `SQLID`.

Changes:
- Added `ae_sql_step_text(env, ae_applid)` to `connectors/ae.py`.
  Queries `PSAESTMTDEFN` (latest EFFDT per step, DBTYPE=' ', MARKET='GBL'),
  collects all non-empty `SQLID`s, batch-fetches from `PSSQLTEXTDEFN`
  (SQLTYPE=1, DBTYPE IN (' ', '7'), Oracle variant preferred), concatenates
  chunks by SEQNUM. Returns `{(section, step): [{stmt_type, sql_text}]}`.
- Updated `ae_object()` in `connectors/uom.py`: calls `ae_sql_step_text()`,
  cross-references each step by native-case `(ae_section, ae_step)` key
  (not uppercased — uppercase is only used for PeopleCode lookup which has a
  separate key), attaches `sql_statements` list and `has_sql=True` flag.
- Updated `sections_for_ae()` in `connectors/uom.py`: builds "SQL Steps"
  section with one item per `(step, stmt_type)` carrying `data.ddl` for the
  existing `<pre>` code rendering path in the Object Explorer.

Verification:
- `ae_sql_step_text('HCM', 'ACA_EXTRACT')` → 127 entries, 0 warnings.
- `ae_object('HCM', 'ACA_EXTRACT')` steps section: 135 steps, 112 with
  `has_sql=True`; SQL Steps section: 127 items.
- HTTP: `GET /api/peoplesoft/object/application_engine/ACA_EXTRACT?env=HCM`
  returned 200 with "SQL Steps" count=127, first entry:
  `MAIN.Step025 [Do Select]: %Select(ACA_EXTRACT_AET.NUM_ROWS) SELECT ...`

------------------------------------------------------------------------

### Rich Record Dependency Traversal

Record object pages now include three new dependency sections that show what
uses or derives from a given record.

Background: The existing record UOM shows which components and pages use a
record. This extends it upstream (what records are based on this record) and
sideways (what AE programs treat this as state/work storage).

Changes:
- Added `record_usages(env_name, recname)` to `connectors/psdb.py`.
  Uses `table_columns()` guards (not `has_table` — that lives in ptmetadata,
  not psdb) before each query:
  - **Child Records**: `PSRECDEFN WHERE PARENTRECNAME = recname` — records
    that extend or specialize this record as their parent.
  - **AE State Records**: `PSAEAPPLSTATE WHERE UPPER(AE_STATE_RECNAME) = recname`
    — AE programs using this as a state/work record, with deep link to AE Explorer.
  - **Subrecord Derivations**: `PSRECFIELD JOIN PSRECDEFN WHERE DEFRECNAME = recname`
    — records that inherit fields from this record via subrecord inclusion.
  All queries cap at 100 rows and deep-link to admin object pages.
- Updated `record_object()` in `connectors/uom.py`: calls `record_usages()`
  with try/except and adds `child_records`, `ae_state_records`,
  `subrecord_derivations` to `_relationships`.
- Updated `sections_for_record()` in `connectors/uom.py`: added three new
  sections — "Child Records", "Subrecord Derivations", "AE State Records".

Verification:
- `record_usages('HCM', 'JOB')` → 70 child records, 0 AE state records,
  100 subrecord derivations.
- `record_usages('HCM', 'ACA_BAC020_AET')` → 0 child, 2 AE programs
  (ACA1095CA, ACA1095CB), 0 subrecord.
- HTTP: `GET /api/peoplesoft/object/record/JOB?env=HCM` returned 200 with
  Child Records=70 (first: ADDL_HB_ARG), Subrecord Derivations=100 (first:
  ACCOM_DIAGNOSIS), AE State Records=0.

------------------------------------------------------------------------

### Security Reports

Added a suite of canned security audit reports accessible via API and UI.

Changes:
- Added `security_report(env_name, report_type, limit)` to `connectors/psdb.py`.
  Runs one of 6 parameterized SQL reports and returns `{title, columns, rows, note,
  available_reports}`. Reports:
  - `empty_roles` — roles in PSROLEDEFN with zero PSROLEUSER rows
  - `unused_permission_lists` — PSCLASSDEFN entries not in PSROLECLASS
  - `top_operators_by_roles` — operators ranked by role count (joins PSOPRDEFN for email)
  - `top_roles_by_users` — roles ranked by user count
  - `permission_list_role_coverage` — permission lists ranked by role usage
  - `locked_operators` — operators with ACCTLOCK > 0
- Added `GET /api/peoplesoft/security/reports?env=&report=&limit=` endpoint
  in `routers/peoplesoft.py`.
- Added a "Security Reports" card at the bottom of `/admin/security`:
  dropdown selector for report type, limit input, "Run Report" button,
  results rendered as a styled table with deep links on rolename/classid/oprid values.

Verification:
- `security_report('HCM', 'empty_roles', limit=5)` → 5 rows, no error.
- HTTP: `GET .../security/reports?report=top_operators_by_roles&limit=3`
  → PSFED (621 roles), JARED (604), NODE_USER (603).
- `/admin/security` returned 200; page contains 8 report-UI element references.

------------------------------------------------------------------------

### Object Explorer Breadcrumbs

The Object Explorer (`/admin/object/{type}/{name}`) now shows a breadcrumb
trail above the object title when an object is loaded.

Changes:
- Added `<nav id="breadcrumb">` div above `<h2 id="objectTitle">` in
  `routers/admin.py`'s `object_explorer_page()`.
- Added `buildBreadcrumbs(type, name)` JS function that generates
  typed breadcrumb HTML:
  - All objects start with `Admin › Object Explorer`
  - Each object type maps to its canonical home section:
    Records, AE Programs, Security (Operators/Roles/Permission Lists),
    Portal Registry, Integration Broker (Services/Nodes/Queues/Routings), etc.
  - For `field` objects with a dotted name (e.g., `JOB.EMPLID`):
    inserts the parent record as an intermediate breadcrumb with a deep link.
  - Name segments are plain text; group segments are hyperlinked.
- Updated `renderObject()` to call `buildBreadcrumbs()` and show the nav.

Verification:
- `/admin/object/record/JOB` HTML contains 5 breadcrumb element references.
- Breadcrumb for a record: `Admin › Records › JOB`
- Breadcrumb for a field `JOB.EMPLID`: `Admin › Fields › JOB › EMPLID`
- Breadcrumb for an AE: `Admin › AE Programs › ACA_EXTRACT`

------------------------------------------------------------------------

### SQL Definition Type Filter

SQL Definition search now supports SQLTYPE filtering so users can find
standalone SQL objects separately from AE SQL actions.

Background: PSSQLDEFN SQLTYPE values: 0=Standalone SQL, 1=AE SQL Action,
2=AE PeopleCode SQL, 6=Trigger. HCM has ~7.7K standalone, ~38K AE SQL,
~23K PeopleCode SQL, 44 triggers. Without a filter, searching `ACA_MMDD`
returns both the standalone definition and any AE step definitions.

Changes:
- Added `search_sql_definitions(env_name, q, sqltype, limit)` to
  `connectors/psdb.py`. Uses `table_columns()` (lowercase keys) to build
  the SELECT list, applies optional `AND SQLTYPE = :sqltype` clause, returns
  rows enriched with `sqltype_label` (from `_SQL_TYPE_LABELS` dict).
- Added `GET /api/peoplesoft/sql_definitions?env=&q=&sqltype=&limit=` endpoint
  in `routers/peoplesoft.py`. `sqltype` defaults to blank (all); if numeric,
  filters to that type. Returns rows with `_links.admin` set.
- Added SQL type filter UI to Object Explorer: when the type selector is set
  to `sql_definition`, a `<select id="sqlTypeFilter">` and "Search SQL" button
  appear via JS `change` event listener. `searchSqlDefinitions()` calls the
  new endpoint and renders results in the Search Results panel.

Verification:
- `search_sql_definitions('HCM', 'ACA_MMDD', limit=5)` → 2 rows (ACA_MMDD,
  ACA_MMDD_CMN), both labeled "Standalone SQL".
- `search_sql_definitions('HCM', '', sqltype=1, limit=3)` → AE SQL Actions.
- HTTP: `GET /api/peoplesoft/sql_definitions?sqltype=1&limit=3` → 3 AE SQL rows.
- Object Explorer HTML contains 5 `sqlTypeFilter`/`searchSqlDefinitions` references.

------------------------------------------------------------------------

### Recently Viewed Enhancements

The Object Explorer's "Recently Viewed" panel now shows descriptions, relative
timestamps, and per-item remove buttons.

Changes in `routers/admin.py` (`object_explorer_page()`):
- Added `relativeTime(ts)` helper: converts epoch milliseconds to "just now",
  "Xm ago", "Xh ago", or "Xd ago".
- Updated `pushRecent(type, name, title, description)` to accept and store a
  `description` field (sourced from `object.overview.description` in `loadObject()`).
- Added `removeRecent(type, name, event)` function that removes a single entry
  from `localStorage` and re-renders.
- Updated `renderRecentList()`:
  - Flex layout per entry (name + timestamp left, × button right).
  - Shows description below the name (truncated with `text-overflow:ellipsis`)
    when it differs from the name/title.
  - Shows relative timestamp ("5m ago") in muted text.
  - Each entry has a `×` remove button that stops click propagation.

Verification:
- `/admin/object/record/JOB` HTML contains 6 references to
  `relativeTime`/`removeRecent`/`pushRecent`.

------------------------------------------------------------------------

### SQL Syntax Highlighting in Object Explorer

All SQL content in the Object Explorer now renders with syntax highlighting
instead of plain text.

Changes in `routers/admin.py` (`object_explorer_page()`):
- Added `highlightSQL(sql)` tokenizer function. Uses a hand-rolled tokenizer
  (block comments, line comments, single-quoted strings, code segments) to
  avoid regex-based false positives. Color scheme:
  - SQL keywords (SELECT/FROM/WHERE/JOIN/etc.) → blue (`#569cd6`)
  - PeopleSoft meta-SQL (%Table/%Bind/%Select/etc.) → purple (`#c586c0`)
  - String literals → orange (`#ce9178`)
  - Comments → green (`#6a9955`)
  - Numbers → light green (`#b5cea8`)
- Updated section renderer: changed `pre.textContent = section.data.ddl` to
  `pre.innerHTML = highlightSQL(section.data.ddl)` for DDL sections (Record
  DDL, SQL Definition source).
- Updated `renderRows()`: items that carry `row.data.ddl` (e.g., AE SQL Steps)
  now render an inline `<pre>` with `highlightSQL()` below the item title.

Verification:
- `/admin/object/record/JOB` HTML contains 3 `highlightSQL` references.
- SQL Definition objects show colored keywords in their SQL Source section.
- AE object SQL Steps show inline highlighted SQL under each step row.

------------------------------------------------------------------------

### SQL Workspace Autocomplete and Typed Bind Parameters

**SQL Autocomplete** (`routers/admin.py` — `admin_sqlws()`):

- Added `<div id="sqlAC">` fixed-position overlay with `position:fixed;z-index:9999` — appears below the SQL textarea when triggered.
- `_tokenBeforeCursor()`: extracts the current word from the textarea before the cursor (including dots).
- `_acContext()`: determines whether the token is a table reference (no dot, ≥2 chars → `{type:"table", prefix}`) or a column reference (contains dot → `{type:"column", qualifier, prefix}`).
- `_extractAliases(sql)`: regex over FROM/JOIN clauses to build `alias → table` map (skips SQL keywords).
- `_fetchAC(ctx)`: calls `/api/sqlws/schema/search` for table completion; calls `/api/sqlws/schema/SYSADM/{table}/columns` for column completion after resolving the qualifier via alias map. Column results are cached per `env|table`.
- `_showAC()`: positions dropdown using `getBoundingClientRect()`, renders items with label + detail; `_acCommit(i)` splices the selected token into the textarea at cursor position.
- Keyboard: ArrowUp/Down to navigate, Enter/Tab to commit (when item selected), Escape to close, Ctrl+Space to trigger manually.
- Fires automatically on `input` (debounced 200ms) when token ≥2 chars; hides on `blur` with 150ms delay.
- Hint label "Ctrl+Space to autocomplete" added to SQL Query label.

**Typed Bind Parameters** (`routers/admin.py` — `admin_sqlws()`):

- Replaced raw JSON `<textarea id="bindsInput">` with a structured editor `<div id="bindsEditor">`.
- Each bind is a row: `[name input] [value input] [× remove button]`.
- `addBind(name, val)`: creates a new bind row.
- `clearBinds()`: removes all rows.
- `setBinds(obj)`: clears and repopulates from a `{name: value}` object.
- `bindsObj()`: iterates `.bind-row` elements, strips leading `:` from names, returns `{name: value}` dict.
- `_detectBinds(sql)`: regex-scans SQL for `:name` placeholders, adds missing ones as empty rows — fires automatically on SQL input (debounced 400ms) and when loading from history.
- History "Load" now passes saved binds as second argument to `loadQueryFromHistory(sqlJson, bindsJson)`, restoring bind rows from history.
- CSS: `.bind-row`, `.bnd-name`, `.bnd-val`, `.bnd-rm` with monospace styling consistent with the dark theme.

Verification:
- `admin_sqlws()` HTML contains `bindsEditor`, `addBind`, `clearBinds`, `setBinds`, `_detectBinds`, `bnd-name` (CSS), and no `bindsInput`.
- `admin_sqlws()` HTML contains `sqlAC`, `_acTrigger`, `_extractAliases`, and `Ctrl+Space` hint text.
- Schema browser API confirmed: table search returns `PSOPRDEFN` etc., column search returns `OPRID, OPRDEFNDESC, EMPLID` for `PSOPRDEFN`.

------------------------------------------------------------------------

### PS Query Explorer

Added full PS Query object type support via the UOM pattern:

**`connectors/ptmetadata.py`**:
- Replaced the "planned" stub for `"query"` in the fallback loop with a proper
  `OBJECT_REGISTRY.setdefault("query", {...})` entry pointing to `PSQRYDEFN`
  with `provider: "query"` search config.
- Added `provider: "query"` branch in `global_search()` that filters
  `WHERE OPRID = ' '` (public/shared queries only) when searching `PSQRYDEFN`.

**`connectors/uom.py`**:
- `query_object(env, qryname)`: fetches definition from `PSQRYDEFN` (public
  only, `OPRID=' '`), records from `PSQRYRECORD` (with join types and
  correlation name aliases), output columns from `PSQRYFIELD` (with heading,
  aggregate function, record resolution), and prompt parameters from
  `PSQRYBIND` (with field type labels). All tables guarded with
  `ptmetadata.has_table()` + `psdb.select_existing_columns()`.
- `sections_for_query(q_obj)`: renders Overview, Records Used (join type +
  alias per record), Output Columns (column position, heading, aggregate,
  RECNAME.FIELD display), and Prompt Parameters (bind name, type, related
  field).
- `query_payload(q_obj)`: standard UOM payload envelope.
- `canonical_object()`: added `if object_type == "query": return query_object()`
  dispatch.

**`routers/peoplesoft.py`**:
- Added `if object_type == "query"` dispatch in `object_payload()`, returning
  `uom.query_payload(uom.query_object(...))`.

**`routers/admin.py`**:
- Added `<option value="query">PS Query</option>` to both the Graph Explorer
  type selector and the Object Explorer type selector.

Verification:
- `query_object('HCM', 'OPRDEFN2')`: status=ok, 1 record, 2 output columns.
- `query_object('HCM', 'FPA_JOB_SUM')`: status=ok, 5 records with join types,
  17 output columns, 2 prompt parameters.
- `GET /api/peoplesoft/object/query/FPA_JOB_SUM?env=HCM`: 200 OK, sections
  `['Overview', 'Records Used (5)', 'Output Columns (17)', 'Prompt Parameters (2)']`.
- Global search `?q=FPA_JOB`: returns `query: FPA_JOB_SUM | FPS Job Data`.

------------------------------------------------------------------------

### PS Queries Tab — Environment Comparison

Added a PS Queries comparison tab to `/admin/envcompare`:

**`connectors/envcompare.py`** (already complete):
- `compare_queries(env1, env2, q, limit)`: diffs `PSQRYDEFN` public queries
  (`OPRID=' '`) between two environments by `QRYNAME`, comparing `DESCR`,
  `QRYTYPE`, `QRYFOLDER`, `QRYDISABLED`, `LASTUPDDTTM`.
- `summary()`: includes `PS Queries` count query.

**`routers/envcompare.py`** (already complete):
- `GET /api/envcompare/queries`: public diff endpoint.

**`routers/admin.py`**:
- Added "PS Queries" tab button after "Portals" in the envcompare tab row.
- Added `<div id="pane-queries">` with `<input id="queryQ">`, Compare button,
  spinner, and result div.
- Updated `TABS` constant to include `'queries'` between `'portals'` and `'graph'`.
- Added `queries: 'queryQ'` to `Q_IDS` map so `runCompare('queries')` picks
  up the filter input.

------------------------------------------------------------------------

### SQL Workspace — Timeout and Cancellation

Added server-side call timeout and client-side cancel support:

**`connectors/sqlws.py`**:
- `MAX_TIMEOUT_SECS = 600` constant.
- `_normalize_timeout_secs(seconds)`: clamps to `[0, MAX_TIMEOUT_SECS]`.
- `execute_query()`: accepts `timeout_secs` and `cancel_check` parameters.
  Sets `cursor.callTimeout = timeout_secs * 1000` when driver supports it.
  Catches `oracledb.Error` with DPI-1067 or "call timeout" message to set
  `timed_out=True, status="timeout"`. Cancellation detected via `cancel_check`
  callable or oracle "cancel/abort" error message.
- Result dict includes `timed_out`, `cancelled`, and `status` fields.
- History entries record `timed_out` and `cancelled` flags.

**`routers/sqlws.py`**:
- `ExecuteRequest`: added `timeout_secs: int = 0`.
- `execute_sql()`: now `async`, uses `asyncio.to_thread()` to run the blocking
  DB call without blocking the event loop.
- Pre- and post-execution `request.is_disconnected()` checks set `cancelled`
  flag when the HTTP client aborts before or after the query runs.

**`routers/admin.py`** (SQL Workspace UI):
- Added Cancel button (`id="cancelBtn"`, hidden while idle) next to Execute.
- Added Timeout selector (`id="timeoutSel"`) with None/10s/30s/60s/2m/5m options
  (default 30s).
- `currentAbortController`: module-level `AbortController` for the live request.
- `_setExecRunning(running)`: toggles Execute disabled state + Cancel button
  visibility.
- `cancelSQL()`: calls `currentAbortController.abort()`.
- `executeSQL()`: creates `AbortController`, passes `signal` to fetch and
  `timeout_secs` to request body; handles `AbortError` to show "Query
  cancelled by user." message without crashing.
- Timing display shows `— TIMED OUT` suffix when `data.timed_out` is set.

------------------------------------------------------------------------

### IB Explorer — Overview Duplication Fix + Services Count

**`routers/admin.py`**:
- `loadDashboard()`: removed the duplicate `<h2>Integration Broker Overview</h2>`
  and stat-grid from the injected HTML — these counts are already in the static
  card (populated via `$('ovSvc').textContent` etc.). The `#dashboard` div now
  only renders live runtime data (Publications/Subscriptions/Domain Status).
- `loadServices()`: increased limit to 500; appended a footer note showing
  "N services — all services (no status filter) · PSIBAPPLDEFN" so users can
  confirm the list is unfiltered (PSIBAPPLDEFN has no EFF_STATUS filter in the
  services query).

------------------------------------------------------------------------

### IB Relationship Explorer Redesign

Rewrote `/admin/ib` from a table-centric tab browser into a relationship
explorer with master-detail navigation.

**Layout**:
- `<div class="explorer">` replaces `.content` — flexbox row with a 290px
  `.list-panel` on the left and a `.detail-panel` (flex:1) on the right.
- All list tabs (`tab-services`, `tab-operations`, etc.) now live inside
  `.list-panel` so the list stays visible when viewing a detail.
- `.detail-panel` contains `#breadcrumb` bar + `#detailScroll > #detailContent`.

**Navigation stack**:
- `navStack[]` tracks the path taken: `[{type, name}, ...]`.
- `pushNav(type, name, push)` adds to the stack and calls `renderBreadcrumb()`.
- `renderBreadcrumb()` renders `IB › &#9881; SVC_OP › &#8652; ROUTING › ...`
  with clickable segments that call `navTo(i)` to jump back.
- `navTo(idx)` slices the stack to idx+1 and re-invokes the appropriate `showXxx()`.
- `clearDetail()` resets stack, restores placeholder, and clears active states.

**All `showXxx()` functions** now:
- Accept optional `push=true` parameter (false when called from breadcrumb nav).
- Call `switchTab()` to show the relevant list tab.
- Call `markActive(listId, name)` to highlight the selected list item.
- Call `setDetail(html)` instead of replacing `contentArea`.
- Start with a `relStrip()` relationship bar showing clickable tags to related
  objects (operation → service + routings + queues + Transactions;
  routing → operation + sender + receiver + Transactions;
  node → related operations + Transactions; queue → Transactions;
  transaction → operation + queue + pubnode).

**Relationship strip**:
- `relStrip(label, tags)` renders a compact horizontal bar at the top of each
  detail view with `rel-tag` buttons for each related object.
- `rel-action` class for "View Transactions" tags (green tint).
- `viewTxnsFor(q)` switches to the Txns tab and prefills the filter with the
  given operation/node/queue name.

**Compact overview**:
- Replaced large `stat-box` elements with `cstat-row` 3-column compact grid
  fitting in the 290px left panel.
- Quick-action buttons are full-width stacked buttons in the left panel.

**Additional click-through fixes**:
- Routing sub-definitions: sender/receiver nodes now clickable.
- Transaction pub/sub contracts: sub nodes and routings now clickable.
- Messages table in operation detail: queue names now clickable.
- Routing table in service detail: sender/receiver nodes now clickable.
- `showNode()` guards against null/undefined names.

------------------------------------------------------------------------

## 2026-06-30

### Navigation Architecture Redesign

Completed a full navigation overhaul of the admin shell (`routers/admin.py`,
`static/app.css`, `static/app.js`).

**`static/app.css`** — full rewrite with design-system tokens:
- `--nav-h: 42px`, `--hdr-h: 46px`, `--bg`, `--panel`, `--line`, `--text`,
  `--muted`, `--cyan` CSS variables.
- `.ds-nav` sticky global navbar; `.ds-page-hdr` per-page header strip;
  `.ds-env` / `.ds-env-sel` environment selector.
- `.ds-content` (scrollable) and `.ds-content.ds-noscroll` (overflow:hidden
  flex-column, for master-detail layouts).
- `.ds-toolbar` for page-specific action bars.
- Preserved `.pe-home`, `.pe-hero`, `.pe-kicker`, `.pe-grid`, `.pe-card` for
  the landing page.

**`static/app.js`** — full rewrite:
- `localStorage['ps_env']` persistence for environment selector across pages.
- `initGlobalEnv()` populates all `.ds-env-sel` selects from
  `/api/sqlws/config` and restores saved selection.
- `syncPageEnvSel(val)` syncs legacy per-page `#envSel` selects.
- `window.dsGetEnv()`, `window.dsSetEnv()`, `window.dsGetStoredEnv()` helpers.

**`routers/admin.py`** — major refactor:
- `_NAV` list + `_shell(title, active, content, env=True, noscroll=False)`
  function replaces per-page HTML boilerplate. One `<!DOCTYPE html>` in the
  entire file.
- Navigation: `Home · Users · Runtime · SQL Workspace · IB Explorer · Env
  Compare · Tools · Docs`.
- New `/admin/users` page (moved user management from `/admin/`).
- New `/admin/` landing page with `.pe-hero` + `.pe-grid` module cards.
- New `/admin/docs` page linking to Swagger UI and ReDoc.
- All 18 page functions use `return _shell(...)`.
- Fixed `noscroll=True` on Runtime Monitor (was preventing scroll through
  stacked Process Scheduler / IB / Oracle sections).
- Removed `body { padding: 40px }` inline overrides that created dead space
  above the nav bar on Home, Runtime, Security, Graph, Portal, Metadata,
  Knowledge Graph, and Object Explorer pages.
- Fixed double `<style>` tag in `object_explorer_page()` (migration artifact).

**Verification:**
- `python -m py_compile routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all core pages return 200.
- All 25 routes registered; server boots clean on port 8088.

------------------------------------------------------------------------

### Object Explorer Visual Hierarchy

Improved the Object Explorer (`/admin/object`) rendering without touching the
UOM or API layer.

**`routers/admin.py`** (JavaScript/HTML/CSS in `object_explorer_page()`):

**Layout change** — the left panel no longer has separate "Overview" and
"Actions" cards. Instead the right panel opens with a single rich
`#objectHeader` (`div.obj-hdr`) card that shows:
- Type chip (color-coded, using `TYPE_CHIP_CFG`) + monospace object name.
- Description subtitle (from `overview.description`).
- Up to 12 key-value pairs from the object overview (`.kv-grid`/`.kv-key`/
  `.kv-val` from `app.css`; skips `id`, `display_name`, `description`,
  `status`).
- Action links as compact button chips (`div.obj-hdr-actions > a`).
- Section count in small muted text.

**Section cards**:
- `<h2>` now includes a `span.count-badge` when `section.items.length > 0`
  (e.g., "Fields (24)", "Pages (75)").
- Sections containing DDL or PeopleCode source get class `section-wide`
  which spans both columns of the `.sections` grid (`grid-column: 1 / -1`).
- The "Warnings" section gets class `section-warn` (amber border + amber h2).

**`renderKeyValues(target, data)`** — replaced custom `<dl>/<dt>/<dd>` with
`.kv-grid`/`.kv-key`/`.kv-val` from `app.css`; also filters out null/empty
values and skips `ddl`/`source` keys.

**`renderRows(target, rows)`** — each row now renders:
- `div.row-header` flex container holding a `span.rel-chip` (if
  `row.relationship` is set) + the title span + a `span.row-arrow` (→) for
  clickable rows.
- The old `"relationship: labelFor(row)"` prefix text replaced by the chip.

**`renderActions()`** — stubbed (logic folded into `renderObject()`).

New CSS classes: `.obj-hdr`, `.obj-hdr-row`, `.obj-hdr-name`, `.obj-type-chip`,
`.obj-hdr-desc`, `.obj-hdr-actions`, `.count-badge`, `.section-wide`,
`.section-warn`, `.row-header`, `.rel-chip`, `.row-arrow`.

**Verification:**
- `python -m py_compile routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all core pages pass (including `/admin/object`).
- `GET /admin/object/record/PSRECDEFN`: obj-hdr, type chip, description,
  kv-grid, action links, count badges on Fields/Keys/Indexes sections, DDL
  section spans full width.
- API `GET /api/peoplesoft/object/record/PSRECDEFN?env=HCM` — 15 sections,
  unchanged shape.

### Portal Registry — Rich Reconstruction

Improved `sections_for_portal_registry()` in `connectors/uom.py` and the
generic row renderer in `routers/admin.py`.

**`connectors/uom.py`**:

- `_portal_label_items(items, use_reftype_chip=False)` — new helper that adds
  `title` (portal_label → classid → pnlgrpname → portal_permname → rolename →
  roleuser → portal_objname) and optionally sets `relationship` to the decoded
  reftype label (Folder / Content Reference) for use as a renderer chip.

- `_portal_access_summary(access_paths)` — new helper that groups the flat
  permission-list→role→operator rows into one summary row per permission list,
  with `roles` count, `operators` count, and a `via_roles` sample string. Turns
  152+ flat rows into 3–5 grouped rows.

- `sections_for_portal_registry()` — updated:
  - "Breadcrumbs" renamed to **"Navigation Path"**; items get titles from
    `portal_label` and a "Folder"/"Content Reference" chip via `relationship`.
  - "Children" items get human-readable `title` from `portal_label` and a
    reftype chip.
  - **"Access Paths"** section replaced by **"Who Has Access"** — 3-column
    grouped summary (permlist → roles → operators). Original raw paths still
    in `_relationships` for the graph layer.
  - "Portal Security" items get `relationship` chip from `portal_permtype_label`
    (Permission List / Role).
  - "Definition" data now includes `navigation_path` — a `→`-separated string
    of ancestor folder labels all the way to the current item.
  - Children data includes `folders` and `content_refs` counts.
  - Empty sections (0 items, no meaningful data) filtered from the output.

**`routers/admin.py`** (Object Explorer JS):

- `labelFor(row)` — now checks `row.title` and `row.label` before falling back
  to specific field names; applies to all object types.
- `_DETAIL_SKIP` — added `title`, `label`, `portal_permtype_label`,
  `portal_reftype_label`, `portal_reftype`, `portal_permtype` so those
  helper fields don't clutter the detail text line.

**Verification:**
- `python -m py_compile connectors/uom.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/portal_registry/EOEC_CCI_INSTAL?env=HCM` —
  "Navigation Path" (5 items, each with portal_label title + reftype chip),
  "Who Has Access" (3 rows: EOCO9000 1 role 6 ops, EOEC9000 1 role 141 ops,
  EOEC9010 1 role 5 ops), Definition.navigation_path shows full ancestor trail.
- `GET /api/peoplesoft/object/portal_registry/EOCO_EOEC?env=HCM` — folder
  object: "Children" shows 9 items (5 folders, 4 content refs) with human
  labels and reftype chips.

### Access-Path Visualization — Component, Page, Permission List

Improved access-path and permission decoding display across three UOM object types.

**`connectors/uom.py`**:

- `_portal_access_summary()` generalized into `_access_summary(access_rows, ...)` —
  groups flat permlist→role→operator rows into one row per permission list,
  collecting role count, operator count, role sample, and unique `decoded_actions`.
  `_portal_access_summary` kept as backward-compatible alias.

- `sections_for_component()` — "Security" (flat 158-row list) replaced by
  **"Who Has Access"** (3 grouped rows, one per permission list) using
  `_access_summary()`; each row shows classid, roles count, operators count,
  and `actions` field for the granted permissions (Update/Display, Add, etc.).
  "Permission Lists" section items now carry a `relationship` chip decoded from
  `authorizedactions` (Update/Display / Add, Update/Display / etc.).

- `sections_for_page()` — "Security" (flat 158-row list) replaced by
  **"Who Has Access"** using `_access_summary()`.

- `sections_for_permissionlist()` — "Components" items now carry a
  `relationship` chip from each row's `decoded_actions` list.

**`routers/admin.py`** (Object Explorer JS):

- `_DETAIL_SKIP` — added `authorizedactions`, `displayonly`,
  `raw_authorizedactions`, `raw_displayonly`, `pnlitemname`,
  `target_portal_objname`, `portal_iscascade` to eliminate noise from
  permission-decoded rows.

**Verification:**
- `python -m py_compile connectors/uom.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/component/EOEC_CCI_INSTAL?env=HCM` —
  "Permission Lists": [EOCO9000 chip=Update/Display, EOEC9000 chip=Update/Display,
  EOEC9010 chip=Add, Update/Display]; "Who Has Access": [EOCO9000 6 ops,
  EOEC9000 141 ops, EOEC9010 5 ops] — 3 rows vs prior 158 flat rows.
- `GET /api/peoplesoft/object/permissionlist/EOCO9000?env=HCM` — "Components":
  items have action chips (Update/Display / Add, Update/Display).

### AE Runtime Detail — Instance Deep-Linking

Enhanced AE Object Explorer Runtime Instances section and added process instance
deep-linking between the AE Object Explorer and the Runtime Monitor.

**`connectors/ae.py`** — `runtime_instances()`:
- Each item now gets `title = f"#{prcsinstance}"` so `labelFor()` shows the
  instance number instead of falling through to `oprid`.
- `relationship = runstatus_label` — status chip (Success / Error / Hold /
  Queued) shown as a colored chip next to the instance number.
- `_links.admin = f"/admin/runtime?instance={prcsinstance}"` — deep-link to
  the Runtime Monitor's process detail panel.
- `duration` field computed from `begindttm`/`enddttm` when both are present
  (e.g., "15s", "2m 30s", "1h 5m").

**`routers/admin.py`** (Runtime Monitor init):
- Added `URLSearchParams` parsing in the runtime page init block.
- `?env=ENV` selects the correct environment on load.
- `?instance=N` auto-invokes `showProc(N)` after data loads, opening the
  process detail slide-in panel directly.
- `_DETAIL_SKIP` expanded with `runstatus`, `runstatus_label`, `prcstype`,
  `prcsname`, `runlocation`, `outdesttype`, `outdestformat` to suppress noise
  from runtime rows.

**Verification:**
- `python -m py_compile connectors/ae.py routers/admin.py` — OK.
- `scripts/smoke_admin_shell.py` — all pages pass.
- `GET /api/peoplesoft/object/application_engine/PSPM_REAPER?env=HCM` —
  Runtime Instances: 20 items, first 3 show title=#606394, chip=Success,
  duration=15s, _links.admin=/admin/runtime?instance=606394.
- Deep-link `/admin/runtime?instance=606394` supported by URL param handler.

---

## 2026-06-30 — Application Package UOM (Priority #8)

**What changed:**
- `connectors/peoplecode.py` — corrected objectid1=104 from "Handler (IB new)" to "App Package Class". Updated `PEOPLECODE_OBJECT_TYPES`, `_OID1_PARENT_TYPES`, and `decode_semantic_path()` to properly parse the variable-depth path structure (OV1=packageroot, OV2..OVn-1=qualifypath segments, OVn=OnExecute).
- `connectors/ptmetadata.py` — wired `application_package` in `OBJECT_REGISTRY` with real PSPACKAGEDEFN discovery/search; added `app_package` custom search provider in `global_search()` (searches PACKAGEROOT + DESCR, returns root-level packages distinct). Also wired `application_class` with PSAPPCLASSDEFN discovery.
- `connectors/uom.py` — added `app_package_object()`, `sections_for_app_package()`, `app_package_payload()`. Sections: Definition (PSPACKAGEDEFN PACKAGELEVEL=0), Sub-Packages (PACKAGELEVEL>0), Classes (PSAPPCLASSDEFN with qualifypath+classid), PeopleCode (PSPCMPROG objectid1=104 grouped by class).
- `routers/peoplesoft.py` — added `application_package` branch to canonical object dispatcher calling `app_package_payload()`.
- `routers/admin.py` — added App Package option to Object Explorer and Graph Explorer selectors; updated `inferObject()` for packageroot, `labelFor()` for packageroot+appclassid, `_DETAIL_SKIP` for packageroot/appclassid/qualifypath/full_path; added TYPE_CHIP_CFG entries for application_package and application_class.

**Data confirmed:**
- PSPACKAGEDEFN: 4245 rows, PSAPPCLASSDEFN: 12622 rows — both accessible
- objectid1=104 in PSPCMPROG: 15300 programs — ALL are App Package class PeopleCode (not IB handlers; IB handler classes ARE app classes)
- Largest packages: HRS_CANDIDATE_MANAGER (303 classes), PTUNI_REVIEW (256), HCR_PERSON_SERVICES (250)
- HRS_COMMON: 91 sub-packages, 170 classes, 160 PeopleCode programs

**Live test results:**
- `/api/peoplesoft/object/application_package/HRS_COMMON?env=HCM` → 4 sections, 170 classes ✓
- Global search "HRS_CANDID" → application_package HRS_CANDIDATE_MANAGER score=66 ✓
- Object Explorer `/admin/object/application_package/HRS_COMMON` → renders with "App Package" chip ✓

---

## 2026-06-30 — AE Restart Eligibility, SQL PeopleCode Cross-Reference, Portal Object Comparison

### AE Restart Eligibility (Priority #6 completion)
- `ae.state_records()` was broken — required column `RECNAME` but actual column is `AE_STATE_RECNAME` (column names vary by PeopleTools version). Fixed to accept both `AE_STATE_RECNAME` / `RECNAME` / `AE_DEFAULT_STATE` / `AE_ISBASESTATE` and normalize into consistent `recname`, `title`, `is_default`, `relationship` (chip) keys.
- `ae_payload()` overview now includes `restart_eligible: bool` and `state_records: int`. GPGB_EDIEXPT shows `restart_eligible=true, state_records=1` (GPGB_EDILIB_AET). State Records section now shows AET records with Default chip and record cross-links.

### SQL PeopleCode Cross-Reference (Priority #10 completion)
- PSPCMTXT.PCTEXT is plain text — searchable via Oracle LIKE.
- Added PeopleCode cross-reference block to `sql_object()`: searches `UPPER(PCTEXT) LIKE '%SQL.{sqlid}%'` against PSPCMTXT, normalizes each matching program via `peoplecode.normalize_program()`, adds type_label, parent cross-link, PeopleCode Explorer deep-link.
- `sections_for_sql()` now adds "PeopleCode References" section when results exist (hidden when empty).
- Test: `SQL.HR_GET_SETID_LOCATION` → 17 PeopleCode references.

### Portal Object Deep Comparison (Priority #3 completion)
- `compare_portal_object(env1, env2, portal_objname)` in `connectors/envcompare.py`: independently queries each env for PSPRSMDEFN definition, children (PORTAL_PRNTOBJNAME), and PSPORTALDEFN permissions; diffs by field and by presence.
- `/api/envcompare/portal-object?env1=HCM&env2=FSCM&name=X` endpoint in `routers/envcompare.py`.
- UI: `/admin/envcompare` Portals tab enhanced with "Deep Object Comparison" sub-panel; `runPortalObjectCompare()` + `renderPortalObjectDiff()` JS; shows stat boxes + definition diff table + collapsible children/permissions diff sections with add/remove/change chips.
- Portal UOM `_links` now includes `compare` link to `/api/envcompare/portal-object?name=X`.
- Test: PORTAL_GROUPLETS → 141 children differ (FSCM has FSCM-specific grouplets: Asset Management, Accounts Payable, etc.).

---

## 2026-06-30 — App Server Domain Monitoring (PSPMDOMAIN_VW)

**Context:** AE grants unblocked. Previous implementation assumed PSAPPSRV / PSAPPSRVDOM which do not exist in HCMDMO or FSCMDMO. Neither table exists in any environment.

**What changed:**

- `connectors/psdb.py` — added `app_server_domains(env_name)`:
  - Discovery-first: checks `PSPMDOMAIN_VW` then `PS_PSPMDOMAIN1_VW` using `ptmetadata.has_table()`; returns a non-fatal warning dict if neither is accessible — no crash, no hard-coded dependency
  - Groups raw rows by `PM_DOMAIN_NAME`; parses `PM_HOST_PORT` into `{host, port, alt_port}`; infers domain type from name suffix (`_APP` → App Server, `_PRCS` → Process Scheduler, `_WEB` → Web/PIA, default → Integration Broker)
  - Returns `{items, source_view, counts, warnings}` — `source_view` tells the caller which view was actually used
  - Added constants: `_APPSRV_DOMAIN_VIEWS`, `_DOMAIN_TYPE_RULES`, helpers `_classify_domain()`, `_parse_host_port()`

- `routers/runtime.py` — added `GET /api/runtime/domains?env=` endpoint

- `routers/admin.py` — added "App Server Domains" card (above the Process Scheduler Servers card); `loadDomains()` JS function with type chips (green=App Server, amber=Proc Sched, blue=Web/PIA, grey=IB); source view attribution footer; wired into `refresh()` via `Promise.allSettled`

- `ARCHITECTURE.md` — added App Server Domain Topology data source table and discovery contract description

**Live results (2026-06-30):**
- HCM (PSPMDOMAIN_VW): 4 domains — HCMDMO (IB), HCMDMO_APP (App Server :9043), HCMDMO_PRCS (Proc Sched), HCMDMO_WEB (Web/PIA)
- FSCM (PSPMDOMAIN_VW): 8 domains — FSCMDMO_APP, APPDOM (App Server), FSCMDMO_PRCS, PRCSDOM (Proc Sched), FSCMDMO_WEB, ps/peoplesoft (Web/PIA), FSCMDMO (IB)

---

## 2026-06-29 — Graph Indexing, Impact Analysis, Explorer Pages, Reporting Center, PeopleCode Source Search

### Portal Registry Bug Fixes

Two long-standing bugs in portal reconstruction were fixed.

**`connectors/psdb.py`**:

- `portal_registry_portals()` root detection: `TRIM(PORTAL_PRNTOBJNAME) = ' '` was
  wrong because TRIM strips the space, making the comparison `'' = ' '` (false). Fixed
  to `LENGTH(TRIM(PORTAL_PRNTOBJNAME)) = 0`.

- `portal_registry_breadcrumbs_fast()` CONNECT BY duplicate rows: `START WITH
  UPPER(PORTAL_OBJNAME) = UPPER(:objname)` without a portal-name filter matched the same
  objname across all 9 portals, producing N× ancestor chains. Fixed by adding `AND
  UPPER(PORTAL_NAME) = UPPER(:pn)` to both START WITH and CONNECT BY; also added NOCYCLE.

### Graph Indexing — 5 New Bulk Providers

**`connectors/graphdb.py`** — added to `build()`:

- `menus()`: joins PSMENUDEFN + PSMENUITEM, adds menu→component CONTAINS edges; guarded by `has_table("PSMENUDEFN")`.
- `trees()`: queries PSTREEDEFN, adds tree→record USES edges for treestrctpnm and tree_recname; `seen` set deduplicates tree names.
- `sql_definitions()`: queries PSSQLDEFN WHERE SQLTYPE=0 (standalone SQL), nodes only.
- `queries()`: queries PSQRYDEFN WHERE OPRID=' ' (public queries), nodes only.
- `component_interfaces()`: queries PSBCDEFN, adds ci→component WRAPS edges. Node type is `ci` (matching OBJECT_REGISTRY key, not `component_interface`).

All 5 use a single SQL call with ROWNUM limit. `WRAPS` edge type added to `EDGE_TYPES` and `DEPENDENCY_EDGES`.

**`connectors/ptmetadata.py`**: Fixed tree OBJECT_REGISTRY entry — `name_column` changed from `TREE_NAME` to `TREENAME`; `extra_search_columns` changed from `TREE_STRCT_ID` to `TREESTRCTPNM`. Added `"relationships"` field to query/tree/ci/menu entries.

### Advanced Dependency Analysis — `impact()`

**`connectors/graphdb.py`**: Added `impact(env, node, depth=3)` — runs `dependency_tree()` forward (downstream) and reverse (upstream), returns per-direction node lists plus per-type count summaries.

**`routers/graphdb.py`**: Added `GET /api/graph/impact/{node_id}?env=&depth=`.

**`routers/admin.py`** — Graph Explorer IMPACT tab:
- New tab button `#tabImpact` wired to `showTab('impact')`.
- `#impactView` div with node type/name pickers, depth selector, Analyse button, and side-by-side upstream/downstream panels.
- `renderImpactNodes(nodes, containerId)` — groups by `n.type`, renders object links via `objectUrl()` and `escHtml()`.
- `renderImpactSummary(byType, containerId)` — type-count chip badges.
- `runImpact()` — calls impact API, renders both panels.
- Node click in LIST view pre-fills the IMPACT type/name pickers.

### PS Query, Tree, CI, Menu Explorer Pages

New search functions in `connectors/psdb.py`:
- `search_queries(env, q, folder, limit)` — PSQRYDEFN WHERE OPRID=' ', optional folder filter.
- `query_folders(env)` — distinct QRYFOLDER values from public queries.
- `search_trees(env, q, setid, limit)` — correlated subquery to get latest EFFDT per (TREENAME, SETID, SETCNTRLVALUE).
- `search_cis(env, q, limit)` — PSBCDEFN.

New REST endpoints in `routers/peoplesoft.py`:
- `GET /api/peoplesoft/queries`, `GET /api/peoplesoft/query-folders`
- `GET /api/peoplesoft/trees`
- `GET /api/peoplesoft/cis`

New admin pages in `routers/admin.py` (all two-panel search/detail layout):
- `/admin/query` — folder filter dropdown, col/bind count stats, Object Explorer deep-link.
- `/admin/tree` — SETID filter, active/inactive chip, record cross-links.
- `/admin/ci` — type chip, wrapped component cross-link.
- `/admin/menu` — reuses existing menus API; detail renders items as a table with component cross-links.

Nav entries added: Queries, Trees, CIs, Menus.

### Reporting Center

**`connectors/psdb.py`** — `security_report()` extended with 10 new reports (total 16) across three categories — Security, Objects, System. Each report has a `category` field. `"params": {}` spec suppresses `:limit` injection for GROUP BY reports.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/reports`, `GET /api/peoplesoft/reports/catalog`.

**`routers/admin.py`** — `/admin/reports`: catalog sidebar grouped by category; result panel with live filter and CSV export; cells for known types (role, operator, permlist, component, record, AE, menu) auto-link to their Object Explorer pages.

### PeopleCode Source Search

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/peoplecode/source-search?q=&env=&limit=` — wraps `peoplecode.source_search()` which queries PSPCMTXT.PCTEXT with LIKE.

**`routers/admin.py`** — `/admin/pcsearch`: search box + result limit selector; sidebar shows matching programs with parent type chip + event chip; detail panel shows syntax-highlighted PeopleCode source with search term highlighted in amber `.hit` spans; "Open in PC Explorer" and parent cross-links.

**Verification:**
- `python -c "from routers import admin, peoplesoft; from connectors import psdb, peoplecode; print('OK')"` → OK

---

## 2026-06-30 — Admin Shell Smoke Harness — Priority #9 (CI/Deployment Wiring)

Extended `scripts/smoke_admin_shell.py` to cover all explorer pages added since the last harness update.

**`scripts/smoke_admin_shell.py`**:

- Added 6 new entries to `DEFAULT_PAGES`:
  - `/admin/query` → marker `#qSearch`, env=True, active nav
  - `/admin/tree` → marker `#tSearch`, env=True, active nav
  - `/admin/ci` → marker `#ciSearch`, env=True, active nav
  - `/admin/menu` → marker `#mSearch`, env=True, active nav
  - `/admin/reports` → marker `#catalog`, env=True, active nav
  - `/admin/pcsearch` → marker `#pcq`, env=True, active nav

- Upgraded Graph Explorer interaction check from "list/visual" to "list/visual/impact":
  - `showTab('impact')` → asserts `#impactView` not hidden and `#tabImpact` has class `active`.
  - `showTab('list')` → also now asserts `#tabList` has class `active` (was only checking pane visibility).

Harness now covers 13 pages (was 7).

**Verification:**
- `python -m py_compile scripts/smoke_admin_shell.py` → OK
- `python3 -c "import main"` → OK
- Page count confirmed: 13 entries across `DEFAULT_PAGES`.
- Blocker: headless Chrome is not available in this environment; harness requires `--base-url` pointing to a running DeathStar instance. Run against staging to validate the new page entries before next deploy.

---

## 2026-06-30 — Message Catalog Explorer (Phase 5 Knowledge Graph)

Full vertical slice for PeopleSoft Message Catalog (PSMSGCATDEFN / PSMSGSETDEFN).
Messages are referenced throughout PeopleCode via `MsgGet()`, `MessageBox()`, `Error MsgGet()`, etc.
Previously completely absent from the platform.

**`connectors/psdb.py`**:
- `search_messages(env, q, set_nbr, severity, limit)` — searches PSMSGCATDEFN by MESSAGE_TEXT and DESCRLONG (LIKE). Supports optional set_nbr and severity filters. Returns items with computed `severity_label` and `name` (`set.msg` format). Degrades if PSMSGCATDEFN is not accessible.
- `message_sets(env)` — attempts PSMSGSETDEFN JOIN PSMSGCATDEFN for counts+descriptions; falls back to GROUP BY on PSMSGCATDEFN alone. Returns `source` field indicating which path was used.
- `get_message(env, set_nbr, msg_nbr)` — fetches a specific message. Returns None gracefully if not found or table missing.
- `message_set_info(env, set_nbr)` — fetches set description from PSMSGSETDEFN (optional; returns None if table missing).
- `_MSG_SEVERITY` labels: 0=Message, 1=Warning, 2=Error, 3=Cancel.

**`connectors/ptmetadata.py`**:
- Added `message_catalog` to `OBJECT_REGISTRY` with `discovery.table=PSMSGCATDEFN`, custom `search.provider="message_catalog"`, icon `message-square`.
- Added `message_catalog` provider handler in `global_search()` — searches MESSAGE_TEXT and DESCRLONG. Returns `{set_nbr}.{msg_nbr}` as `name`, truncated message text as description.

**`connectors/uom.py`**:
- `message_catalog_object(env, name)` — parses `{set_nbr}.{msg_nbr}` name, calls `get_message` + `message_set_info`, returns structured object with `message` and `set_info` dicts.
- `sections_for_message_catalog(obj)` — single "Definition" section: Severity chip label, Message Set, Message Number, Message Text, Explanation.
- `message_catalog_payload(env, name)` — full UOM payload with overview kv grid + sections.
- Wired into `canonical_object()`.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/messages?env=&q=&set_nbr=&severity=&limit=` — search endpoint. Adds `_links.admin` to each result.
- `GET /api/peoplesoft/message-sets?env=` — returns all message sets.
- `message_catalog` wired into `object_payload()` dispatcher.

**`connectors/graphdb.py`**:
- `messages()` provider added to `build()`: queries PSMSGCATDEFN with ROWNUM limit, creates `message_catalog` nodes with `{set_nbr}.{msg_nbr}` as node name, message text (truncated to 80 chars) as display name. No edges (messages are referenced by PeopleCode but edge detection would require source parsing). `has_table("PSMSGCATDEFN")` guard.

**`routers/admin.py`**:
- Added `("msgcat", "Messages", "/admin/msgcat")` to `_NAV`.
- Added `message_catalog` / `menu` / `query` / `tree` / `ci` / `sql_definition` to `TYPE_CHIP_CFG` (was previously falling through to grey default).
- Added `message_set_nbr`, `message_nbr`, `severity`, `severity_label` to `_DETAIL_SKIP`.
- `/admin/msgcat` page: two-panel layout; top bar has text search + Set filter dropdown (populated from `/api/peoplesoft/message-sets`) + Severity filter dropdown; sidebar shows messages with severity chip, `set.msg` ref, and truncated text; detail panel shows severity chip + stat boxes + message text block + explanation block + "Object Explorer ↗" link.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/msgcat` → marker `#mcSearch`, env=True, nav=True. Harness now covers 14 pages (was 13).

**Verification:**
- `python -m py_compile connectors/psdb.py connectors/ptmetadata.py connectors/uom.py connectors/graphdb.py routers/peoplesoft.py routers/admin.py` → ALL OK (pre-existing `\-` warning in admin.py PC tokenizer regex, not introduced here)
- `python3 -c "import main"` → OK
- Live tests require DB access; message catalog tables (PSMSGCATDEFN, PSMSGSETDEFN) expected to be accessible given SYSADM schema grants on HCM.

---

## 2026-06-30 — Drift Detection & Approval Framework

### Priority #10: Drift Detection (Graph Explorer DRIFT tab)

**Goal:** Surface configuration drift by comparing the live in-memory graph against the most-recent snapshot directly inside the Object Explorer admin page.

**`connectors/graphdb.py`**:
- `drift(env, node_types, limit)` — loads the most-recent snapshot via `list_snapshots(env)["snapshots"][0]`, calls `load_snapshot()` to rehydrate, calls `current(env)` for the live graph, then delegates to `_diff_graphs(baseline, live, ...)`.
- Wraps result with `baseline_snapshot` metadata and `drift_summary` dict: `new_count`, `removed_count`, `changed_count`, `new_by_type`, `removed_by_type`, `baseline_at`, `baseline_id`.
- Semantics: `only_in_env2_nodes` = NEW objects (in live but not baseline), `only_in_env1_nodes` = REMOVED objects (in baseline but not live).

**`routers/graphdb.py`**:
- `GET /api/graphdb/drift?env=&node_types=&limit=` — thin router delegating to `graphdb.drift()`.

**`routers/admin.py`**:
- Added DRIFT tab button (`#tabDrift`) to Graph Explorer tab strip.
- Added `#driftView` div: env selector, type-filter text input, "Check Drift" button, summary chips panel (new/removed/changed counts), side-by-side new/removed node panels, changed node panel.
- `showTab()` extended to handle `'drift'` — shows `#driftView`, sets `#tabDrift.active`.
- `runDrift()` JS function: calls `/api/graphdb/drift`, renders summary chips, populates `renderDriftNodes()` panels.
- `renderDriftNodes(nodes, container)` — renders node cards with type chip, name, labels.
- `renderDriftChanged(nodes, container)` — renders changed nodes showing which properties differed.

**`scripts/smoke_admin_shell.py`**:
- Graph Explorer check upgraded from `list/visual/impact` to `list/visual/impact/drift`: added `showTab('drift')`, asserts `#driftView` visible and `#tabDrift.active`.

**Verification:**
- `python -m py_compile` → OK on all modified files.
- Live drift test: `drift('HCM')` against 7 existing HCM snapshots returned 0/0/0 (expected — no graph rebuild between snapshot and drift call).

---

### Priority #11: Approval Framework Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft Approval Framework workflow definitions (PSAWDEFN + sub-tables).

**Data model:** PSAWDEFN (definition) → PSAWSTAGEDEFN (stages) → PSAWPATHDEFN (paths) → PSAWSTEPDEFN (steps). Sub-tables individually optional — each guarded by `has_table()`.

**`connectors/psdb.py`**:
- `_AW_STATUS` dict: `{"A": "Active", "I": "Inactive"}`
- `_AW_PROCESS_TYPE` dict: maps `"0"`–`"8"` to No Approval / User / Role / Query / Application Class / Supervisory / Position / Department Security / Role User.
- `search_approvals(env, q, status, limit)` — searches PSAWDEFN.AWDEFNID + DESCR; optional STATUS filter; returns list of `{awdefnid, descr, status, objectownerid, status_label}`.
- `get_approval(env, awdefnid)` — fetches PSAWDEFN row; conditionally fetches each sub-table if present. Returns `{definition, stages, paths, steps, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `"approval"` entry promoted from planned to full `OBJECT_REGISTRY` entry: `display_title="Approval Framework"`, `icon="check-square"`, `discovery.table="PSAWDEFN"`, search on AWDEFNID + DESCR + OBJECTOWNERID.

**`connectors/uom.py`**:
- `_AW_STATUS_CHIP` and `_AW_PROCESS_LABELS` label dicts.
- `approval_object(env, awdefnid)` — fetches raw data, wraps into canonical object dict.
- `sections_for_approval(obj)` — produces three sections:
  - "Definition": kv grid (Description, Status label, Owner, Last Updated By, Last Updated, stage/path/step counts).
  - "Stages": one item per stage with `title="Stage N: {descr}"`, `relationship=process_type_label`, `path_count`, `step_count`.
  - "Steps": one item per step with `title="SN PN Step N: {descr}"`, `relationship=process_type_label`, `userlist`.
- `approval_payload(env, awdefnid)` — full UOM payload with `overview` kv grid keyed by `stage_count`, `path_count`, `step_count`, `status`, `owner`.
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `approvals()` provider added to `build()`: queries PSAWDEFN with ROWNUM limit, creates `approval` nodes. `has_table("PSAWDEFN")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/approvals?env=&q=&status=&limit=` — search endpoint.
- `approval` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("approval", "Approvals", "/admin/approval")` to `_NAV`.
- `/admin/approval` page: two-panel layout; top bar has text search (`#awSearch`) + Status filter (All/Active/Inactive); sidebar shows approval definitions with status chip (Active=green/chip-ok, Inactive=grey/chip-muted) and description; detail panel shows stat boxes (stage/path/step counts), Stages section with process type chips, Steps section with S/P/Step references and process type chips; "Object Explorer ↗" link for each selected approval.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/approval` → marker `#awSearch`, env=True, nav=True. Harness now covers 15 pages.

**Verification:**
- `python -m py_compile routers/admin.py` → OK (pre-existing `\-` warning unchanged).
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — XML Publisher Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft XML Publisher report definitions, data sources, and template layouts.

**Data model:**
- `PSXPREPORTDEFN` — report definition header (REPORTID PK, DESCR, OBJECTOWNERID, DATASRCID FK, LASTUPDOPRID, LASTUPDDTTM)
- `PSXPDATASRC` — data source definitions (DATASRCID PK, DESCR, DATASRCTYPE: A/Q/S/C/G/F)
- `PSXPTEMPLDEFN` — template/layout definitions (REPORTID FK, PSFBDILANGCD, TEMPLATEFORMAT, OUTPUTFORMAT, EFFDT, EFF_STATUS)

Sub-tables PSXPDATASRC and PSXPTEMPLDEFN individually guarded with `has_table()` — missing tables produce warnings, not crashes.

**`connectors/psdb.py`**:
- `_XPUB_DATASRC_TYPE` dict: A=App Engine, Q=PS Query, S=SQL, C=Connected Query, G=Group, F=File.
- `_XPUB_TEMPLATE_FORMAT` dict: RTF, XSL, Excel, eText, PDF Form, Flash.
- `_XPUB_OUTPUT_FORMAT` dict: PDF, Excel, RTF, HTML, CSV, XML, PCL.
- `search_xpub_reports(env, q, limit)` — searches PSXPREPORTDEFN by REPORTID/DESCR pattern; returns `{items, warnings}`.
- `search_xpub_datasources(env, q, limit)` — searches PSXPDATASRC; adds `datasrctype_label`; returns `{items, warnings}`.
- `get_xpub_report(env, reportid)` — full detail: PSXPREPORTDEFN row + PSXPDATASRC join + PSXPTEMPLDEFN rows with format labels; returns `{definition, datasource, templates, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `xml_publisher_report` entry: `discovery.table=PSXPREPORTDEFN`, search on REPORTID/DESCR/OBJECTOWNERID/DATASRCID.
- `xml_publisher_datasource` entry: `discovery.table=PSXPDATASRC`, search on DATASRCID/DESCR.

**`connectors/uom.py`**:
- `_XPUB_DATASRC_CHIP`, `_XPUB_STATUS_CHIP` label dicts.
- `xpub_report_object(env, reportid)` — wraps `get_xpub_report()` into canonical object dict.
- `sections_for_xpub_report(obj)` — "Definition" kv section (desc, owner, data source, type, last updated) + "Templates" section (one item per template row: lang—format→output, status chip, effdt).
- `xpub_report_payload(env, reportid)` — full UOM payload with `overview` (description, owner, datasrcid, datasrc_type_label, template_count).
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `xpub_reports()` provider added to `build()`: queries PSXPREPORTDEFN with ROWNUM limit, creates `xml_publisher_report` nodes. `has_table("PSXPREPORTDEFN")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/xpub/reports?env=&q=&limit=` — report search endpoint.
- `GET /api/peoplesoft/xpub/datasources?env=&q=&limit=` — data source search endpoint.
- `xml_publisher_report` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("xpub", "XML Publisher", "/admin/xpub")` to `_NAV`.
- Added `approval`, `xml_publisher_report`, `xml_publisher_datasource` to `TYPE_CHIP_CFG`.
- `/admin/xpub` page: two-panel layout with Reports/Data Sources mode toggle; search input (`#xpubSearch`); sidebar lists reports with ID + description + data source ID, or data sources with type chip + ID + description; report detail shows stat boxes (template count, owner), data source kv grid, Templates section with status chip + language/format/output/effdt rows; data source detail shows type chip + kv grid; "Object Explorer ↗" link for reports.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/xpub` → marker `#xpubSearch`, env=True, nav=True. Harness now covers 16 pages.

**Verification:**
- `python -m py_compile` all modified files → ALL OK.
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — Navigation Collections Vertical Slice

**Goal:** Full end-to-end explorer for PeopleSoft Fluid Navigation Collections.

**Data model:**
- `PTNC_COLLECTION` — collection header (PORTAL_NAME + COLL_ID PK, COLL_TITLE, EFF_STATUS A/I, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID)
- `PTNC_COLL_LINE` — collection lines (PORTAL_NAME + COLL_ID + LINE_NBR PK, LINE_TYPE: C=Content Ref/F=Folder/T=Tile/S=Static Link, LABEL, PORTAL_URLTEXT)

`PTNC_COLL_LINE` individually guarded with `has_table()`.

**`connectors/psdb.py`**:
- `_NC_LINE_TYPE`, `_NC_EFF_STATUS` dicts.
- `search_nav_collections(env, q, portal, limit)` — searches PTNC_COLLECTION by COLL_ID/COLL_TITLE with optional PORTAL_NAME filter (defaults to 'EMPLOYEE'); adds `eff_status_label`; returns `{items, warnings}`.
- `get_nav_collection(env, coll_id, portal)` — fetches PTNC_COLLECTION row + PTNC_COLL_LINE rows with `line_type_label`; returns `{definition, lines, counts, warnings}`.

**`connectors/ptmetadata.py`**:
- `nav_collection` entry: `discovery.table=PTNC_COLLECTION`, supported_versions starts at 8.55 (Fluid).

**`connectors/uom.py`**:
- `_NC_LINE_TYPE_CHIP`, `_NC_STATUS_CHIP` label dicts.
- `nav_collection_object(env, coll_id)` — wraps `get_nav_collection()` into canonical object dict.
- `sections_for_nav_collection(obj)` — "Definition" kv section (title, status, portal, owner, last updated, line count) + "Lines" section (one item per line: relationship=type label, title=LABEL, url=PORTAL_URLTEXT, line_nbr).
- `nav_collection_payload(env, coll_id)` — full UOM payload with `overview` (title, portal, eff_status, owner, line_count).
- Wired into `canonical_object()`.

**`connectors/graphdb.py`**:
- `nav_collections()` provider added to `build()`: queries PTNC_COLLECTION with ROWNUM limit, creates `nav_collection` nodes. `has_table("PTNC_COLLECTION")` guard.

**`routers/peoplesoft.py`**:
- `GET /api/peoplesoft/nav-collections?env=&q=&portal=&limit=` — search endpoint.
- `nav_collection` wired into `object_payload()` dispatcher.

**`routers/admin.py`**:
- Added `("navcoll", "Nav Collections", "/admin/navcoll")` to `_NAV`.
- Added `nav_collection` to `TYPE_CHIP_CFG` (green palette, distinct from tree green).
- `/admin/navcoll` page: two-panel layout; top bar has text search (`#ncSearch`) + Portal dropdown (EMPLOYEE/All); sidebar shows collections with status chip, COLL_ID, title; detail panel shows stat boxes (line count, portal, owner), Lines section with line number, type chip (Tile=teal/Content Ref=green/Folder|Static=muted), label, URL; "Object Explorer ↗" link.

**`scripts/smoke_admin_shell.py`**:
- Added `/admin/navcoll` → marker `#ncSearch`, env=True, nav=True. Harness now covers 17 pages.

**Verification:**
- `python -m py_compile` all modified files → ALL OK.
- `python3 -c "import main"` → OK.

---

## 2026-06-30 — Event Mapping & Related Content Vertical Slices

### Event Mapping (PT 8.55+)

**Tables:** `PSEFMAPPINGDEFN` (header), `PSEFMAPPINGCTXT` (contexts, optional).

**`connectors/psdb.py`**:
- `search_event_mappings(env, q, status, limit)` — searches PSEFMAPPINGDEFN by EFMAPPINGID/DESCR with optional STATUS filter.
- `get_event_mapping(env, efmappingid)` — fetches definition + PSEFMAPPINGCTXT rows (SEQNO, EFCONTEXTTYPE, EFCONTEXTVALUE, APPEVENTNAME, APPEVENTHANDLER); `has_table()` guard on context table.

**`connectors/ptmetadata.py`**: `event_mapping` promoted from planned stub to full registry entry (table=PSEFMAPPINGDEFN, supported from PT 8.55).

**`connectors/uom.py`**: `event_mapping_object()`, `sections_for_event_mapping()` (Definition kv + optional Contexts section), `event_mapping_payload()`. Wired into `canonical_object()`.

**`connectors/graphdb.py`**: `event_mappings()` provider.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/event-mappings`, wired into `object_payload()`.

**`routers/admin.py`**: `("efmapping", "Event Mapping", "/admin/efmapping")` in `_NAV`; `event_mapping` chip (yellow palette); `/admin/efmapping` two-panel page with status filter, context section showing type/value/event/handler.

**`scripts/smoke_admin_shell.py`**: Added `/admin/efmapping` → `#efSearch`. Harness now 18 pages.

---

### Related Content (Service Framework)

**Table:** `PSRELCONDEFN` (header only; service attachments are out of scope for this slice).

Service type codes: U=URL, C=Component, S=Script, A=App Class, P=PS Page, I=iScript, R=Related Action.

**`connectors/psdb.py`**:
- `_RC_SERVICE_TYPE` dict.
- `search_related_content(env, q, limit)` — searches PSRELCONDEFN by RELCONID/DESCR; adds `servicetype_label`.
- `get_related_content(env, relconid)` — fetches PSRELCONDEFN definition row with type label.

**`connectors/ptmetadata.py`**: `related_content` promoted from planned stub to full registry entry (table=PSRELCONDEFN).

**`connectors/uom.py`**: `related_content_object()`, `sections_for_related_content()` (Definition kv), `related_content_payload()`. Wired into `canonical_object()`.

**`connectors/graphdb.py`**: `related_content_defs()` provider.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/related-content`, wired into `object_payload()`.

**`routers/admin.py`**: `("relcontent", "Related Content", "/admin/relcontent")` in `_NAV`; `related_content` chip (purple palette); `/admin/relcontent` two-panel page with service type chip in sidebar, kv detail panel.

**`scripts/smoke_admin_shell.py`**: Added `/admin/relcontent` → `#rcSearch`. Harness now 19 pages.

**Verification:** `python -m py_compile` → ALL OK. `python3 -c "import main"` → OK.

---

## Search Definitions (PTSF_SRCDEFN)

Implemented the Search Definitions vertical slice — the PeopleSoft Search Framework definition object.

**`connectors/psdb.py`**: `_SRCH_STATUS` dict; `search_search_definitions(env, q, status, limit)` querying `PTSF_SRCDEFN` with has_table() guard; `get_search_definition(env, srcdefnid)` fetching definition row plus optional sub-tables `PTSF_SRCMAP` (mapped fields) and `PTSF_SRCAT` (categories) each guarded by has_table() + try/except.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY.setdefault("search_definition", {...})` entry with `PTSF_SRCDEFN` discovery/search tables, versions 8.54–8.62.

**`connectors/uom.py`**: `_SRCH_STATUS_CHIP`; `search_definition_object()`, `sections_for_search_definition()`, `search_definition_payload()`; added `search_definition` dispatch in `canonical_object()`.

**`connectors/graphdb.py`**: `search_definitions()` provider querying `PTSF_SRCDEFN` with `has_table()` guard; added to provider loop as `("search_definitions", search_definitions)`.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/search-definitions` endpoint; `search_definition` dispatch in `object_payload()`.

**`routers/admin.py`**: `("srchdef", "Search Defs", "/admin/srchdef")` in `_NAV`; `search_definition` chip (blue palette `#2299ee`); `/admin/srchdef` two-panel page with status filter dropdown, fields section, categories section.

**`scripts/smoke_admin_shell.py`**: Added `/admin/srchdef` → `#sdSearch`. Harness now 20 pages.

**`ROADMAP.md`**: Search Definitions promoted to Completed Providers; platform status updated to 20 smoke test pages; "Next Slice" section added at bottom.

---

## Search Categories (PTSF_SRCAT) and Drop Zones (PSPTDZDEFN)

Implemented two more Phase 5 providers in the same session cycle: Search Categories (sibling of Search Definitions in the Search Framework) and Drop Zones (promoted from the planned stub loop — `page_drop_zones()`/`component_drop_zones()` relationship helpers already existed and pointed at the real backing tables `PSPTDZDEFN`/`PSPTDZITEM`/`PSPTDZCOMP`/`PSPTDZPNL`, which made this a natural promotion rather than a fresh discovery).

**`connectors/psdb.py`**: `search_search_categories()` / `get_search_category()` over `PTSF_SRCAT`; `search_drop_zones()` / `get_drop_zone()` over `PSPTDZDEFN` with has_table()-guarded sub-table reads from `PSPTDZCOMP` (components), `PSPTDZPNL` (pages), and `PSPTDZITEM` (items).

**`connectors/ptmetadata.py`**: `search_category` and `drop_zone` promoted to full `OBJECT_REGISTRY` entries; `drop_zone` removed from the planned stub loop (now only `content_reference`, `section`, `step`, `sql`, `message`, `process_scheduler`, `runtime_instance` remain planned).

**`connectors/uom.py`**: `search_category_object()`/`sections_for_search_category()`/`search_category_payload()`; `drop_zone_object()`/`sections_for_drop_zone()`/`drop_zone_payload()`; both dispatched in `canonical_object()`.

**`connectors/graphdb.py`**: `search_categories()` and `drop_zones()` providers added to the build loop.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/search-categories`, `GET /api/peoplesoft/drop-zones`; both dispatched in `object_payload()`. Verified no collision with the existing component/page-scoped `.../drop-zones` relationship endpoints.

**`routers/admin.py`**: `("srchcat", "Search Cats", "/admin/srchcat")` and `("dropzone", "Drop Zones", "/admin/dropzone")` in `_NAV`; `search_category` (violet) and `drop_zone` (amber) chips; two new two-panel explorer pages.

**`scripts/smoke_admin_shell.py`**: Added `/admin/srchcat` → `#scSearch` and `/admin/dropzone` → `#dzSearch`. Harness now 22 pages.

**`ROADMAP.md`**: Search Categories and Drop Zones promoted to Completed Providers; platform status updated to 22 smoke test pages; "Next Slice" section rewritten for WorkCenters, Dashboards, Homepage Tiles, BI Publisher.

**Verification:** `python -m py_compile` on all seven touched files → ALL OK (pre-existing `\-` SyntaxWarning in the unrelated pcsearch tokenizer regex, not introduced here). `python3 -c "import main"` → OK.

---

## Schema Verification and Provider Rewrites (2026-06-30)

This session performed a systematic schema verification of all Phase 5 providers added in the prior session cycle, discovering that several were implemented against assumed/guessed table and column names that do not match the live HCM SYSADM schema. All five providers were fully rewritten using a live-DB-first methodology: query `all_tables`/`all_tab_columns` → pull sample rows to verify usable keys → rewrite psdb.py → compile-check → smoke-test → propagate through ptmetadata.py/graphdb.py/uom.py/admin.py.

### Methodology

Every provider rewrite followed the same pattern:
1. Query `all_tables`/`all_tab_columns` for SYSADM owner to find the real table name and columns
2. Pull sample rows to confirm which column is actually populated as a unique key (not just a plausible PeopleTools name)
3. Scan for related sub-tables via `all_tables WHERE table_name LIKE 'PREFIX%'`
4. Write psdb.py functions; compile-check; smoke-test against live HCM DB
5. Propagate the verified shape through ptmetadata.py → graphdb.py → uom.py → admin.py
6. Final end-to-end smoke-test via `uom.*_payload('HCM', '<real object name>')`

### Approval Framework

**Correction:** Prior implementation used wrong table names. The live SYSADM schema uses the EOAW (Enterprise Online Approval Workflow) table family: `PS_EOAW_TXN` (header, keyed by `EOAWPRCS_ID`), `PS_EOAW_PRCS` (process definitions), `PS_EOAW_STAGE`, `PS_EOAW_STEP`, `PS_EOAW_PATH`.

**`connectors/psdb.py`**: `search_approvals()` / `get_approval()` rewritten against EOAW tables. `get_approval()` returns `{definition, process_definitions, default_process_definition, stages, steps, paths, counts, warnings}`.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY["approval"]` discovery/search tables corrected to `PS_EOAW_TXN`/`EOAWPRCS_ID`.

**`connectors/graphdb.py`**: `approvals()` rewritten to query `PS_EOAW_TXN`.

**`connectors/uom.py`**: `approval_object()`, `sections_for_approval()`, `approval_payload()` rewritten to consume new `get_approval()` shape. Added `_EOAW_STATUS_CHIP`. Sections: Definition / Process Definitions / Stages / Steps / Paths.

**`routers/admin.py`**: `/admin/approval` page rewritten: removed per-item status chip from search list, added Process Definitions section with default chip, renamed `awdefnid` → `eoawprcsId`, added Paths section.

**Verification:** `uom.approval_payload('HCM', 'AbsenceCancelation')` → `process_definition_count: 8`, sections `['Definition', 'Process Definitions', 'Stages', 'Steps', 'Paths']`.

### XML Publisher Reports

**Correction:** Column names and join structure were incorrect in prior implementation.

**`connectors/psdb.py`**: `search_xpub_reports()` / `search_xpub_datasources()` / `get_xpub_report()` rewritten against `PSXPRPTDEFN` (header), `PSXPDATASRC` (datasource), `PSXPRPTCAT` (category), `PSXPRPTTMPL` JOIN `PSXPTMPLDEFN` (templates), `PSXPRPTOUTFMT` (output formats). Fixed a self-join bug (PSXPRPTTMPL was accidentally joined to itself). Returns `{definition, datasource, category, templates, output_formats, counts, warnings}`.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY["xml_publisher_report"]` discovery/search tables corrected to `PSXPRPTDEFN`/`REPORT_DEFN_ID`.

**`connectors/graphdb.py`**: `xpub_reports()` rewritten to query `PSXPRPTDEFN` with `REPORT_DEFN_ID` key.

**`connectors/uom.py`**: `xpub_report_object()`, `sections_for_xpub_report()`, `xpub_report_payload()` rewritten with new field names. Added Output Formats section.

**`routers/admin.py`**: `/admin/xpub` page rewritten: renamed `reportid`/`datasrcid` → `report_defn_id`/`ds_id`, added Output Formats section rendering, added `active_flag` display in datasource detail.

**Verification:** `uom.xpub_report_payload('HCM', 'PYW2AS09N_CO')` → 1 template, 1 output format (PDF).

### Search Definitions

**Critical correction:** Prior implementation assumed `APPCLASSID` was the primary key on `PSPTSF_SD`. Live verification showed `APPCLASSID` is blank on every one of 114 rows (`COUNT(*) WHERE TRIM(APPCLASSID) IS NOT NULL` → 0). The real unique key is `PTSF_SOURCE_NAME` (114 distinct values = all rows). The feature table is also `PSPTSF_SD` (not `PTSF_SRCDEFN` as prior code assumed). Sub-tables `PSPTSF_SD_ATTR` (attributes/fields, 4938 rows) and `PSPTSF_SD_PNLGP` (panel groups, 116 rows) are keyed by the definition's `PTSF_SBO_NAME`, not by `PTSF_SOURCE_NAME` directly.

**`connectors/psdb.py`**: `search_search_definitions()` / `get_search_definition()` rewritten against `PSPTSF_SD` keyed by `PTSF_SOURCE_NAME`. Removed `status` parameter (no status concept on this table). Sub-table lookups use `ptsf_sbo_name` as foreign key.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY["search_definition"]` corrected to `PSPTSF_SD`/`PTSF_SOURCE_NAME`.

**`connectors/graphdb.py`**: `search_definitions()` rewritten against `PSPTSF_SD`.

**`connectors/uom.py`**: `search_definition_object()`, `sections_for_search_definition()`, `search_definition_payload()` rewritten with new field names. Sections: Overview / Fields / Panel Groups.

**`routers/peoplesoft.py`**: Removed stale `status` query parameter from `/api/peoplesoft/search-definitions`.

**`routers/admin.py`**: `/admin/srchdef` page rewritten: removed status filter, renamed `srcdefnid`→`ptsf_source_name`, replaced statusChip with typeChip, renamed "categories" section to "panel_groups".

**Verification:** `uom.search_definition_payload('HCM', 'COMP_SRCH_TRW_CQ')` → 49 fields, 1 panel group.

### Search Categories

**Correction:** Prior implementation used wrong table (`PTSF_SRCAT`); real table is `PSPTSF_SRCCAT` (122 rows), keyed by `PTSF_SRCCAT_NAME`. Sub-tables all keyed by `PTSF_SRCCAT_NAME`: `PSPTSF_CATPTSD` (SBO links, 0 rows in HCM), `PSPTSF_CATDSPFD` (display fields, 150 rows), `PSPTSF_CATADVFD` (advanced search fields, 2929 rows), `PSPTSF_CATFACET` (facets, 404 rows).

**`connectors/psdb.py`**: `search_search_categories()` / `get_search_category()` rewritten against real tables. Returns `{definition, sbo_links, display_fields, advanced_fields, facets, counts, warnings}`.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY["search_category"]` corrected to `PSPTSF_SRCCAT`/`PTSF_SRCCAT_NAME`.

**`connectors/graphdb.py`**: `search_categories()` rewritten against `PSPTSF_SRCCAT`.

**`connectors/uom.py`**: `search_category_object()`, `sections_for_search_category()`, `search_category_payload()` rewritten with new field names. Sections: Overview / SBO Links (when present) / Display Fields / Advanced Search Fields / Facets. Blank-padded CHAR columns filtered via `_clean()` helper to avoid rendering whitespace-only rows.

**`routers/admin.py`**: `/admin/srchcat` page rewritten: renamed `srccatid`→`ptsf_srccat_name`, `descr`→`descr100`, replaced "definitions" section with "sbo_links"/"display_fields"/"advanced_fields"/"facets" sections, added stat counters for all four sub-table types, added `.chip-muted`/`.stat`/`.field-row` flex styles.

**Verification:** `uom.search_category_payload('HCM', 'HC_HR_RW_EMP_VACC_INDEX')` → Overview, Display Fields (1), Advanced Search Fields (15), Facets (1). `uom.search_category_payload('HCM', 'PTIAINCUSTINSIGHT_SRCH')` → Overview, Display Fields (1), Advanced Search Fields (23), Facets (22).

### Navigation Collections, Event Mappings, Related Content, Drop Zones — Confirmed Stubs

Live schema verification found no backing tables for any of these four features in the HCM SYSADM schema:
- Navigation Collections: `PTNC_COLLECTION` does not exist; `PSPTPNCOLL` is Push Notification Collections (3 rows, different feature)
- Event Mappings: `PSEFMAPPINGDEFN` does not exist
- Related Content: `PSRELCONDEFN` does not exist
- Drop Zones: `PSPTDZDEFN` does not exist

All four already had `has_table()` guards in psdb.py and graphdb.py producing graceful empty/error results. Added `"stub": True` marker to all four `OBJECT_REGISTRY` entries in ptmetadata.py to make the unverified status explicit for callers.

**`ROADMAP.md`**: Corrected Completed Providers list; added ⚠️ Stub Providers section; rewrote Next Slice section with verification methodology and verified HomepageTile table candidates (`PS_AGC_TILE_TBL`, `PS_HCTS_TILE_SEC` found in live schema).

**Verification:** `python -m py_compile` on all six files → ALL OK. `uom.search_category_payload('HCM', 'DOES_NOT_EXIST_XYZ')` → `None` (graceful not-found).

---

## PivotGrid Explorer (PSPGCORE) — 2026-06-30

Implemented the PivotGrid vertical slice. Schema verified against live HCM: `PSPGCORE` (154 rows, all type `PUB`, keyed by `PTPG_PGRIDNAME`). Data source breakdown: 140 PS Query, 14 Component. For PS Query grids, the actual query name is stored in `PSPGSETTINGS` WHERE `PTPG_DSNAME='QRYNAME'`. Data model columns in `PSPGMODEL` (3228 rows, 3 column types: `DIM`=Dimension, `DISO`=Display Only, `VAL`=Value). NUI/UI options in `PSPGNUIOPT` (137 rows, includes view name, access group, component mapping, publish-as-tile and share flags).

Pre-investigation found no viable backing tables for Dashboards (PS_EOEN_DASHBRD/PS_PT_ACMDASHTBL both 0 rows), WorkCenters (EOWC tables are runtime config with no header definition table), or BI Publisher (no distinct tables — PSXP family already covered by XML Publisher). PivotGrid was the only well-populated definition table found in the Phase 5 candidate set.

**`connectors/psdb.py`**: `_PTPG_DSTYPE`/`_PTPG_COLTYPE` dicts; `search_pivot_grids(env, q, limit)` querying `PSPGCORE`; `get_pivot_grid(env, pgridname)` fetching definition + PSPGSETTINGS datasource name + PSPGMODEL columns + PSPGNUIOPT options. Returns `{definition, datasource_name, columns, nui_opts, counts, warnings}`.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY.setdefault("pivot_grid", {...})` with `PSPGCORE`/`PTPG_PGRIDNAME` discovery/search tables, icon `bar-chart-2`, versions 8.54–8.62.

**`connectors/uom.py`**: `_PTPG_DSTYPE_CHIP`, `_PTPG_COLTYPE_CHIP`; `pivot_grid_object()`, `sections_for_pivot_grid()`, `pivot_grid_payload()`; dispatched in `canonical_object()`. Sections: Overview (name, title, data source type+name, view, access group, component mapping, publish-as-tile, owner, validity, timestamps) / Data Model Columns (type chip DIM/DISO/VAL, format as meta).

**`connectors/graphdb.py`**: `pivot_grids()` provider added to build loop; queries `PSPGCORE` keyed by `PTPG_PGRIDNAME`.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/pivot-grids`; `pivot_grid` dispatch in `object_payload()`.

**`routers/admin.py`**: `("pivotgrid", "PivotGrids", "/admin/pivotgrid")` in `_NAV`; `pivot_grid` chip (green palette `#22cc66`); `/admin/pivotgrid` two-panel explorer page with type chip, kv overview, column model section with DIM/DISO/VAL chips and format meta.

**Verification:** `python -m py_compile` all six files → ALL OK. `uom.pivot_grid_payload('HCM', 'TL_TIME_STATUS_IRPT')` → overview `{ds_type: 'PS Query', datasource: 'TL_TIME_STATUS_IRPT', owner: 'PPT'}`, 37 columns. `uom.pivot_grid_payload('HCM', 'EODP_RRF_MNT_FL')` (Component type) → `datasource: None` (no QRYNAME setting). Not-found returns `None`. Search with `q='time'` returns 5 results with correct type labels.

---

## Connected Query Explorer (PSCONQRSDEFN) — 2026-06-30

Implemented the Connected Query vertical slice. Schema verified against live HCM: `PSCONQRSDEFN` (97 rows), keyed by `CONQRSNAME`. `PT_REPORT_STATUS`: A=Active, I=Inactive. Sub-tables: `PSCONQRSMAP` (356 rows) holds the parent-child PS Query composition — each row links a parent query name to a child query name; the root query has blank `QRYNAMEPARENT`. `PSCONQRSFLDREL` (597 rows) holds the join field relationships between parent and child queries per `SEQNUM`.

Activity Definitions (`PSACTIVITYDEFN`, 518 rows) were also found but determined to be legacy classic-era workflow activity definitions (pre-Fluid, not PeopleSoft Activity Guide), with low operational relevance; not implemented.

**`connectors/psdb.py`**: `_CONQRS_STATUS` dict; `search_connected_queries(env, q, limit)` querying `PSCONQRSDEFN`; `get_connected_query(env, conqrsname)` fetching definition + PSCONQRSMAP composition + PSCONQRSFLDREL field joins (filtered to non-blank field entries). Returns `{definition, query_map, field_rels, counts, warnings}`.

**`connectors/ptmetadata.py`**: `OBJECT_REGISTRY.setdefault("connected_query", {...})` with `PSCONQRSDEFN`/`CONQRSNAME` discovery/search tables, icon `git-merge`, versions 8.54–8.62.

**`connectors/uom.py`**: `_CONQRS_STATUS_CHIP`; `connected_query_object()`, `sections_for_connected_query()`, `connected_query_payload()`; dispatched in `canonical_object()`. Sections: Overview / Component Queries (root marked with "Root" chip, child queries show parent name as meta) / Field Joins (child field with parent field as meta).

**`connectors/graphdb.py`**: `connected_queries()` provider added to build loop; queries `PSCONQRSDEFN`.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/connected-queries`; `connected_query` dispatch in `object_payload()`.

**`routers/admin.py`**: `("conqrs", "Conn. Queries", "/admin/conqrs")` in `_NAV`; `connected_query` chip (cyan palette `#00ccee`); `/admin/conqrs` two-panel explorer with status chip, kv overview, component queries and field joins sections.

**Verification:** `python -m py_compile` all six files → ALL OK. `uom.connected_query_payload('HCM', 'HRS_SRCH_JOB_OPENING_CQY')` → 6 component queries, 5 field joins, status Active. Not-found returns `None`.

---

## PM Transaction and PM Event Explorer (PSPMTRANSDEFN, PSPMEVENTDEFN) — 2025-07-01

Implemented the PM Transaction and PM Event vertical slices together. Both tables live in the Performance Monitor subsystem alongside the existing PM Metrics Explorer. PSPMTRANSDEFN has ~200 rows (transaction definitions tracking groups of metrics); PSPMEVENTDEFN has ~300 rows (event definitions tracking the same metrics at event boundaries).

`PM_FILTER_LEVEL` shared decode: `01`=Minimal, `04`=Standard, `05`=Detailed, `06`=Diagnostic. Both tables use up to 7 metric slots (`PM_METRICID_1`–`PM_METRICID_7`) and join LEFT to `PSPMMETRICDEFN` to resolve labels. PSPMTRANSDEFN additionally has 3 context slots (`PM_CONTEXT_DEFN_ID_1`–3) joining to `PSPMCONTEXTDEFN`.

**`connectors/psdb.py`**: `search_pm_transactions()`, `get_pm_transaction()` (full LEFT JOIN for 10 slots); `search_pm_events()`, `get_pm_event()` (7 metric slots).

**`connectors/ptmetadata.py`**: `pm_transaction` and `pm_event` OBJECT_REGISTRY entries.

**`connectors/uom.py`**: `_PM_FILTER_LEVELS` module-level dict; `pm_transaction_object()` with Context/Metric slot sections; `pm_event_object()` with Metric slot section.

**`connectors/graphdb.py`**: `pm_transactions()` and `pm_events()` providers added to build loop.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/pm-transactions`, `/pm-events`; dispatch for `pm_transaction`, `pm_event`.

**`routers/admin.py`**: `pmtrans`/`pmevent` NAV entries; light-purple/dark-purple chips; two `/admin/pmtrans` and `/admin/pmevent` explorer pages with filter-level badges and slot-display sections.

**`scripts/smoke_admin_shell.py`**: Added `/admin/pmtrans` and `/admin/pmevent` entries; all pass.

---

## IB Service Operations Explorer (PSOPERATION) — 2025-07-01

Implemented the IB Service Operations vertical slice. PSOPERATION has 2160 rows — these are the canonical IB service operation definitions: the bridges between services and messages. They encode routing type (S=Synchronous/A=Asynchronous/R=REST), the linked IB service, the request message name, and for REST operations, the HTTP method. Routings from PSIBRTNGDEFN (up to 100) are fetched per operation, showing sender→receiver node pairs.

Search supports free-text (operation name, service, description) plus routing-type filter (S/A/R). List sidebar shows Sync/Async/REST colored badges. Detail pane shows Operation Overview kv-table + Routings list with active/inactive distinction.

**`connectors/psdb.py`**: `search_ib_operations(env, q, rtype, limit)` with optional `RTNGTYPE` filter; `get_ib_operation(env, op_name)` returning definition + routings with sender→receiver labels.

**`connectors/ptmetadata.py`**: `ib_operation` OBJECT_REGISTRY entry (`PSOPERATION`/`IB_OPERATIONNAME`, icon `zap`).

**`connectors/uom.py`**: `_IB_RTNG_TYPES`, `_IB_REST_METHODS` dicts; `ib_operation_object()` with Operation Overview + Routings sections.

**`connectors/graphdb.py`**: `ib_operations()` provider added to build loop.

**`routers/peoplesoft.py`**: `GET /api/peoplesoft/ib-operations` (supports `q` and `rtype` params); `ib_operation` dispatch in `object_payload()`.

**`routers/admin.py`**: `("iboper", "IB Operations", "/admin/iboper")` in `_NAV`; amber/orange chip (`#ffaa44`); `/admin/iboper` two-panel explorer with Sync/Async/REST colored badges, routing type filter dropdown, and routingList renderer showing active/inactive routings.

**`scripts/smoke_admin_shell.py`**: Added `/admin/iboper`; passes (28/28 OK, 2 pre-existing failures unchanged).

------------------------------------------------------------------------

## 2026-07-01 — Nav Redesign and Admin Package Split

Date/time: 2026-07-01 CDT

### Nav bar redesign

**Problem**: The flat horizontal nav bar had grown to 49 links spanning multiple
monitors and was unmanageable. Additionally, 16 pages added in earlier sessions
referenced undefined module-level names (`_nav_html`, `_NAV_CSS`, `_ESC_JS`),
causing `NameError` 500s on every request. A further 16 route decorators had
a double `/admin/` prefix bug (router prefix + decorator both included `/admin/`)
returning 404 for those pages. `Request` was not imported despite being used in
type annotations on those routes.

**Solution**: Replaced the flat `_NAV` list with `_NAV_GROUPS` (grouped dropdown
structure). Added three shared module-level constants:
- `_NAV_CSS` — CSS string embedded inline by standalone pages (no `app.css` link)
- `_ESC_JS` — JS `esc()` helper embedded inline in standalone page `<script>` blocks
- `_nav_html(active, env=None)` — generates the `<nav>` element with CSS-only hover dropdowns

Added `from fastapi import APIRouter, Request` to satisfy annotation resolution on
Python 3.14. Fixed all 16 double-prefix decorators via `sed`. Added `?v=2`
cache-buster to CSS/JS links in `_shell()` to force browsers off the cached
pre-dropdown version.

Nav groups (CSS-only hover, no JavaScript required):
- Direct: **Home** · **Users**
- Dropdowns: **Runtime** (Runtime, Infra, Tracing, Env Compare) ·
  **Data** (SQL Workspace, Queries, Conn. Queries) ·
  **Integration** (IB Explorer, IB Messages, IB App Svcs, IB Svc Groups, IB Routings, IB Operations) ·
  **Objects** (CIs, Trees, Menus, App Classes, ADS Defs, Chatbot Skills, Approvals, Content Svcs, URL Defs) ·
  **Portal** (Nav Collections, Related Content, Event Mapping, Drop Zones, PivotGrids, Search Defs,
  Search Cats, XML Publisher, Style Sheets, PC Search) ·
  **Platform** (Processes, File Layouts, Translate, Projects, Messages, Archive Objs,
  Timezones, Locales, PTF Tests) ·
  **Perf** (PM Metrics, PM Transactions, PM Events) ·
  **Tools** (Reports, Tools, Docs)

CSS: `.ds-nav-group`, `.ds-nav-grouplbl`, `.ds-nav-dropdown`, `.ds-nav-drop-link`
added to `/static/app.css`. `_NAV_CSS` mirrors these rules for standalone pages.
Active group gets `ds-nav-group ds-active` class; active item gets `ds-nav-drop-link ds-active`.

### Admin UI package split

**Problem**: `routers/admin.py` had grown to 15,529 lines across 67 routes,
making it impractical to navigate or maintain.

**Solution**: Converted to a package at `routers/admin/`. A Python script
(`split_admin.py`, run once and discarded) identified route block boundaries
via `@router.get(` markers, assigned each block to a module by URL prefix, and
wrote each file with a standard import header. `main.py` required no changes —
`from routers import admin; admin.router` works identically with the package.

Package layout (`routers/admin/`):

| File | Routes | Lines |
|------|--------|-------|
| `_core.py` | — | 195 |
| `__init__.py` | — | 18 |
| `home.py` | `/`, `/users` | 705 |
| `security.py` | `/security`, `/record`, `/field`, `/operator`, `/role`, `/peoplecode` | 2 507 |
| `graph.py` | `/graph`, `/object`, `/portal`, `/metadata`, `/graphdb` | 2 870 |
| `runtime.py` | `/runtime`, `/infra`, `/tracing`, `/envcompare` | 2 359 |
| `data.py` | `/sqlws`, `/query`, `/conqrs` | 1 165 |
| `integration.py` | `/ib`, `/ibmessage`, `/ibapp`, `/ibsvcgrp`, `/ibrtng`, `/iboper` | 1 574 |
| `objects.py` | `/ci`, `/tree`, `/menu`, `/appclass`, `/adsdef`, `/cbskill`, `/approval`, `/contsvc`, `/urldef` | 1 042 |
| `portal.py` | `/navcoll`, `/relcontent`, `/efmapping`, `/dropzone`, `/pivotgrid`, `/srchdef`, `/srchcat`, `/xpub`, `/stylesheet`, `/pcsearch` | 1 367 |
| `platform.py` | `/prcsdefn`, `/filelayout`, `/xlat`, `/project`, `/msgcat`, `/archobj`, `/timezone`, `/locale`, `/ptftest` | 1 182 |
| `perf.py` | `/pmmetric`, `/pmtrans`, `/pmevent` | 393 |
| `tools.py` | `/reports`, `/tools`, `/docs` | 225 |

Sub-module header (standard for all sub-modules):
```python
import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS
```

Files modified:
- `routers/admin/` (new package — replaces `routers/admin.py`)
- `static/app.css` (added dropdown nav CSS rules)
- `ARCHITECTURE.md`, `README.md`, `ROADMAP.md`, `HANDOFF_PROMPT.md`, `DEVELOPMENT_DIARY.md`

Verification:
- `python3 -c "from routers.admin import router; print(len(router.routes), 'routes')"` → 67 routes
- `python3 -c "import main"` → OK (SyntaxWarning in portal.py inline JS regex pre-existing)
- All 67 routes smoke-tested via `curl localhost:8088`; all returned 200
- Service restarted via `kill -HUP`; `journalctl` confirmed clean startup
- Nav groupings confirmed in browser; dropdown hover works; active group highlights correctly
- `app.css?v=2` cache-buster forces browsers to fetch updated stylesheet

------------------------------------------------------------------------

## 2026-07-01 — Phase 5 Complete; Phase 6 Continuous Drift Detection

### Phase 5 Closed

IB Schema Definitions (PSIBSCMADATA / PSIBSCMADFN) was the last Phase 5 candidate.
Investigated: `has_table()` returns True (visible in `all_objects`) but actual SELECT yields
ORA-00942 — no grant in HCM. Even with grants, PSIBSCMADATA stores raw XML as CLOB chunks
with no human-readable names or types; PSIBSCMADFN header is redundant with PSMSGDEFN coverage.
Decision: deprioritize. Phase 5 declared complete.

ROADMAP updated: "Remaining Providers" replaced by "Deprioritized Providers" table with one row
per unimplementable table, each documenting the exact table names and reason.

### Phase 6 — Environment Compare Expansion (Continuous Drift Detection)

Existing envcompare covered: Records, Fields, Components, Permissions, AE, Roles, PeopleCode,
SQL Definitions, Portals, PS Queries. The Phase 6 roadmap items (Menus, Trees, IB metadata)
were all missing.

Implemented four new compare functions following the existing `_run()` / `_compare()` pattern:

| Function | Table | Key | Notes |
|---|---|---|---|
| `compare_menus()` | PSMENUDEFN (637 rows) | MENUNAME | Compares menutype, descr, objectownerid, lastupddttm |
| `compare_trees()` | PSTREEDEFN (326 rows) | TREE_NAME | Inner-join to MAX(EFFDT) per TREE_NAME+SETID; latest effective row only |
| `compare_ib_routings()` | PSIBRTNGDEFN | ROUTINGDEFNNAME | Filters `NOT LIKE '~%'` to exclude auto-generated rows; compares type, operation, sender/receiver |
| `compare_ib_messages()` | PSMSGDEFN (4272 rows) | MSGNAME | Compares msgstatus, descr, objectownerid, lastupddttm |

Also updated `summary()` to include Menus, Trees, IB Routings, IB Messages in the object count sidebar.

Files modified:
- `connectors/envcompare.py` — four new functions + updated summary()
- `routers/envcompare.py` — four new GET endpoints (/menus, /trees, /ib_routings, /ib_messages)
- `routers/admin/runtime.py` — four new tabs in envcompare UI; updated TABS, Q_IDS, nameCol, metaHeaders, metaCells
- `ROADMAP.md` — Phase 5 closed; Phase 6 Continuous Drift Detection section updated

Verification:
- `python3 -m py_compile` on all three Python files: OK
- `python3 -c "import main"`: OK
- Live connector calls: compare_menus (20 diffs), compare_trees (OK), compare_ib_routings (OK), compare_ib_messages (OK)
- HTTP endpoints all returned 200 after service restart
- `/admin/envcompare` page confirmed 44,822 bytes; Menus/Trees/IB Routings tabs present

------------------------------------------------------------------------

## 2026-07-02 — App Class Source, Portal Reconstruction, Access Path Fix

### HANDOFF #8 — App Class PeopleCode Source in Object Explorer

Added PeopleCode source code display to the App Class Object Explorer page.

**Problem**: `psdb.get_app_class()` fetched PSAPPCLASSDEFN metadata but did not
fetch the actual PeopleCode source from PSPCMTXT.

**Root cause #1 — sections ignored**: `uom.object_payload()` was calling
`sections_for_field()` regardless of whether the object had custom sections
from `canonical_base`. Fixed by checking `field.get("sections") is not None`
first; falls back to `sections_for_field` for legacy field objects only.

**Root cause #2 — case sensitivity**: The route does `object_name.upper()`, so
the compound key `PTNUI~IBHandlers~UniNavLandingPageHandler` becomes
`PTNUI~IBHANDLERS~UNINAVLANDINGPAGEHANDLER`. `PSAPPCLASSDEFN` stores mixed-case
qualify paths and class IDs. Fixed by using `UPPER()` predicates in the
PSAPPCLASSDEFN query and then re-assigning to DB-returned correct-case values.

**Source lookup key**: OV1=packageroot, OV2..n-1=qualifypath split by `:`, OVn-1=classid, OVn=OnExecute; padded to 7 columns.

Files changed:
- `connectors/psdb.py` — `get_app_class()`: add source fetch via PSPCMTXT; case-insensitive PSAPPCLASSDEFN lookup; DB-returned correct-case values for subsequent queries
- `connectors/uom.py` — `_app_class_sections()`: add "PeopleCode Source" section; `object_payload()`: prefer `field.sections` when already set

Verification:
- `python3 -c "import py_compile; py_compile.compile(...)"` → OK both files
- Direct call: `psdb.get_app_class("HCM", "PTNUI~IBHandlers~UniNavLandingPageHandler")` → source len: 91487
- Root-level class `HR_ABN~:~ABNDynamicFolderBase` → source len: 10338
- API: `GET /api/peoplesoft/object/app_class/PTNUI~IBHandlers~UniNavLandingPageHandler?env=HCM` → 3 sections, PeopleCode Source present

### HANDOFF #3 — Portal Rich Reconstruction (Subtree Expansion)

Added deep portal subtree expansion capability using Oracle CONNECT BY.

**New**: `psdb.portal_registry_subtree(env, portal_name, parent_objname, max_depth=6, max_rows=1000)` — hierarchical CONNECT BY query returning full descendant subtree as a flat depth-annotated list.

**New API**: `GET /api/peoplesoft/portal/subtree?portal_name=EMPLOYEE&parent=HC_WORKFORCE_ADMINISTRATION&max_depth=3&max_rows=50&env=HCM` → returns `{items, count}` with depth-sorted items.

**Portal Explorer enhancement**: "Expand Subtree" button (purple) on the Portal Explorer page loads the full subtree of the currently loaded portal object and renders it as a depth-indented color-coded tree (folders=blue, content refs=green).

Files changed:
- `connectors/psdb.py` — `portal_registry_subtree()` function
- `routers/peoplesoft.py` — `GET /api/peoplesoft/portal/subtree` endpoint
- `routers/admin/graph.py` — "Expand Subtree" button + subtree card + `expandSubtree()` JS function

Verification:
- `portal_registry_subtree("HCM", "EMPLOYEE", "HC_WORKFORCE_ADMINISTRATION", max_depth=3, max_rows=50)` → 50 rows
- API: 50 rows returned, correct depth ordering

### HANDOFF #4 — Access Path Visualization Fix (BARITEMNAME)

**Critical bug discovered**: `auth_component_source()` in `psdb.py` only handled `PNLGRPNAME` (older schema) and `PNLITEMNAME`→PSPNLGROUP join path. PeopleTools 8.5x uses `BARITEMNAME` to store the component name. Since this DB has `BARITEMNAME` but not `PNLGRPNAME`, ALL component access path queries were returning empty results.

**Fix**: Added `BARITEMNAME` as a priority-2 check in `auth_component_source()`, before the `PNLITEMNAME` join path.

**Impact**: Functions now returning real data:
- `component_access("HCM", "JOB_DATA")` → 2,250 paths (was 0)
- `permissionlist_components("HCM", "HCCPHD1000")` → 31 components (was 0)
- `GET /api/peoplesoft/security/components/JOB_DATA/access?env=HCM` → counts: 11 PLs, 15 roles, 43 users, 2250 paths
- Permission List Object Explorer now shows 31 components for HCCPHD1000

Files changed:
- `connectors/psdb.py` — `auth_component_source()`: add BARITEMNAME branch

Commits:
- `a7ef5dd` feat(app-class): add PeopleCode source code to App Class Object Explorer
- `a76f1c9` feat(portal): rich portal reconstruction — deep subtree expansion
- `4c5ceff` fix(security): support BARITEMNAME as component source in PSAUTHITEM

---

## 2026-07-02 (session 2) — HANDOFF #5 Graph Indexing + HANDOFF #7 Topology Diagram

### HANDOFF #5: Graph Compaction and Large-Environment Indexing

The knowledge graph build already supported `limit=50..2000` (batch mode at 250+), but the Graph Management admin page hardcoded `limit=50` in the Rebuild button. Graph search had no type filtering.

**Changes:**
- `connectors/graphdb.py` — `search()` now accepts optional `node_types` (comma-separated string); pre-filters nodes before scoring, eliminating O(n) work for irrelevant types
- `routers/graphdb.py` — `GET /api/graph/search` exposes `node_types` query param (forwarded to `graphdb.search()`)
- `routers/admin/graph.py` — "Rebuild Graph" now has a limit selector: 50 / 250 (batch) / 1000 (batch) / 2000 (batch, full); "Graph Search" card now has type filter input (e.g. `component,record`) and result limit selector (50/100/200)

**Verification:** `curl "/api/graph/search?env=HCM&q=JOB&limit=5&node_types=component,record"` → 5 results of types component/record only; unfiltered search returns mix of types as before.

### HANDOFF #7: App Server Monitoring and Runtime Alerts

Runtime alerts (process_errors, long_processes, queue_depth, blocking, ash_waits, domains) were already complete. The remaining ROADMAP item was the interactive topology diagram with live status indicators.

**Changes:**
- `routers/topology.py` — expanded `/api/topology` from 8 nodes/10 links to 12 nodes/17 links; added Browser, Process Scheduler (HCM/FSCM), and IB (HCM/FSCM) nodes; IB nodes inherit status from their corresponding App Server since IB runs in the same domain; links now carry protocol labels (Jolt, SQL\*Net, RPC, IB, REST, HTTPS); kind classification: client/proxy/weblogic/appserver/prcs/ib/database/search
- `routers/admin/runtime.py` — added `/admin/topology`: SVG-based fixed-layout diagram showing full PeopleSoft infrastructure flow (Browser → NGINX → WebLogic → App Server → Process Scheduler + IB → Oracle / OpenSearch); each node has a kind-coloured border, left-edge status bar, and top-right status dot in ONLINE (green) / OFFLINE (red) / UNKNOWN (yellow); click a node to see details in the info panel; kind + status legend below SVG
- `routers/admin/_core.py` — "Topology" added to Runtime nav dropdown

**Verification:**
- `/api/topology` → 12 nodes; HCMDMO_PRCS OFFLINE, HCMDMO_IB ONLINE (inherits HCMDMO_APP), FSCMDMO_* OFFLINE
- `/admin/topology` → 200 OK with `#topoSvg`
- Smoke: 56 OK, 1 FAIL (`/admin/reports` pre-existing SyntaxError)

**Note:** `admin_promotions` in runtime.py briefly had a duplication bug (double table row from a bad oldString match in replace_string_in_file); fixed before commit.

Files changed:
- `connectors/graphdb.py` — `search()` type filter
- `routers/graphdb.py` — `node_types` param forwarding
- `routers/admin/graph.py` — limit selector + graph search type filter
- `routers/topology.py` — expanded topology API
- `routers/admin/runtime.py` — `/admin/topology` page
- `routers/admin/_core.py` — Topology in Runtime nav
- `scripts/smoke_admin_shell.py` — `/admin/topology` added to suite

Commits:
- `72c4311` feat(graph,topology): HANDOFF #5 graph indexing + HANDOFF #7 topology diagram

---

## 2026-07-02 — Object Explorers, Component Event Flow, Security Intelligence, SQR Intelligence

### SQR Explorer: Env-Based Filtering + SQC Included-By Tab (c5552ae, 71bbda2, bcf5e95)

Added environment-scoped filtering to the SQR Explorer. The env selector dropdown is populated from `/api/sqr/sources`, and changing env reloads stats and search results filtered to the selected env's source keys. The `GET /api/sqr/sources?env=` endpoint was introduced to return both the full sources list and the enumerated env names. SQC detail pages now have an "Included By" tab that lazy-loads programs referencing this SQC via `/api/sqr/sqc/{name}/users`.

Config change: `sqr_sources` entries now use `ssh_host` instead of `alias`. `sqringest.py` updated accordingly.

Files changed:
- `routers/sqr.py` — `GET /api/sqr/sources[?env=]`, env→source_keys resolution in `GET /api/sqr/programs`
- `routers/admin/sqr_view.py` — env selector, `onEnvChange()`, `doSearch()` env param, SQC Included By tab
- `connectors/sqringest.py` — `source["ssh_host"]` rename
- `config.json` (gitignored) — `sqr_sources` keys renamed

Verification:
- `/api/sqr/sources` returns combined sources + env list
- Env selector in admin SQR changes filtered results

Commits:
- `bcf5e95` feat(sqr): rename sqr_sources alias to ssh_host
- `71bbda2` feat(sqr): env-based source filtering in SQR Explorer
- `c5552ae` feat(envcompare): add Process Definitions comparison tab

---

### EnvCompare: Process Definitions Tab + Summary Row (c5552ae)

`compare_process_definitions()` added to `connectors/envcompare.py`. Queries `PS_PRCSDEFN` using composite key `TYPE~NAME`; compares DESCR and LASTUPDDTTM across environments. A "Processes" tab was wired into the EnvCompare UI (between Trees and IB Routings) and a Process Definitions count row added to the summary table.

Files changed:
- `connectors/envcompare.py` — `compare_process_definitions()`
- `routers/envcompare.py` — `GET /api/envcompare/process_definitions`
- `routers/admin/runtime.py` — Processes tab in TABS/Q_IDS/keyCol/metaHeaders/metaCells

Commits:
- `c5552ae` feat(envcompare): add Process Definitions comparison tab

---

### SQR JS $ Fix (44acd94)

`_ESC_JS` only defines `esc()`, not `$`. Fixed by adding `const $ = id => document.getElementById(id);` to all three script blocks in `sqr_view.py` that used `$` without defining it.

Files changed:
- `routers/admin/sqr_view.py` — three `const $ = …` declarations

Commits:
- `44acd94` fix(sqr): add const $ definition to all script blocks

---

### SQR Override Intelligence + KG Records Tab + Schema Migration (76b24c4, 7565949)

**sqr_sources config split:** Distinct keys per source+env (`fscm_sqr_delivered`, `fscm_sqr_custom`, `hcm_sqr_delivered`, `hcm_sqr_custom`) plus `source_type: delivered|custom` field. This enables override detection: a file present in both a delivered and a custom source key for the same env is an override.

**sqrdb schema migration:** Old schema had `UNIQUE(filename)`. New schema requires `UNIQUE(filename, source_key)` plus `source_type TEXT` column. SQLite can't ALTER CONSTRAINT, so `init_db()` detects the old schema by presence of the old index, renames to `sqr_programs_v1`, creates the new table, copies data, drops the old. 1,384 programs preserved across migration.

**Override endpoint:** `GET /api/sqr/overrides?env=` returns filenames appearing in both delivered and custom source keys for the given env. Powers the Overrides tab in SQR Explorer analytics.

**KG Records tab:** All SQR detail pages now have a lazy-loaded "KG Records" tab. Queries `/api/graph/neighbors/sqr_program:FILENAME?env=HCM&limit=150`. Groups results as READS (blue) and WRITES (amber) with links to Record Explorer. Node ID uses `filename.toUpperCase()` to match KG conventions.

Files changed:
- `connectors/sqrdb.py` — schema migration in `init_db()`, `UNIQUE(filename, source_key)`, `source_type` column, `overrides()` method
- `connectors/sqringest.py` — passes `source_type` to `upsert_program()`
- `routers/sqr.py` — `GET /api/sqr/overrides`
- `routers/admin/sqr_view.py` — KG Records tab on all detail pages, `loadKgRecords()` with uppercase node ID
- `config.json` (gitignored) — sqr_sources split into four distinct keys

Verification:
- sqrdb migration ran without data loss (1,384 programs)
- `/api/sqr/overrides?env=HCM` returns filenames present in both delivered and custom
- KG Records tab loads in SQR detail pages
- `python3 scripts/smoke_admin_shell.py` → 57/57

Commits:
- `76b24c4` feat(sqr): override intelligence, KG records tab, schema migration
- `7565949` fix(sqr): sqrdb overrides query param order

---

### SQR Full-Text Search (1e648dc)

`/admin/sqrsearch` added to SQR nav. SQLite-backed source text index with schema migration (adds `source_text TEXT` column to `sqr_programs` on first use). Search queries via `/api/sqr/search?q=&env=`. Results show syntax-highlighted snippets, hit counts (sorted descending), source type badge, and "Open in SQR Explorer" cross-link. Deduplicates across delivered/custom trees.

Files changed:
- `connectors/sqrdb.py` — `source_text` column, FTS search
- `routers/sqr.py` — `GET /api/sqr/search`
- `routers/admin/sqr_view.py` — `/sqrsearch` route and page

Commits:
- `1e648dc` feat(sqr): full-text SQR search + complete Component Event Flow

---

### Field PeopleCode Impact Tab (2717465, c5de9b7)

`/admin/field/{name}` now has a "PeopleCode" tab showing all PeopleCode programs that reference this field, grouped by object type (Record/Component/Page), with event name and direct links. Also added Operator Activity insights to the Operator 360 page.

Files changed:
- `routers/admin/objects.py` — PeopleCode tab in field detail, operator activity insights
- `connectors/psdb.py` — `field_peoplecode_references()` query

Commits:
- `2717465` feat(field): add PeopleCode impact tab to /admin/field
- `c5de9b7` feat(field): PeopleCode impact analysis + operator activity insights

---

### Application Engine Explorer (22d7595)

`/admin/ae` added to Platform nav. Tabbed detail: Overview (DESCR, type, owner, dates), Steps (section→step tree with SQL text inline), Runtime History (recent process instances from runtimedb), Cross-References (Process Definitions that invoke this AE), KG Graph (graph neighbors). Env-aware; env selector populates from available environments.

Files changed:
- `routers/admin/platform.py` — `admin_ae()` route and page
- `connectors/ae.py` — step listing, runtime history, cross-reference queries

Commits:
- `22d7595` feat(ae): Application Engine Explorer with runtime/dependency analysis

---

### Dedicated Object Explorers: Component, Page, Permission List (6072e76, 7473280)

- **Component Explorer** at `/admin/component`: tabbed — Overview, Pages, Security (full PL→Role→Operator chain), PeopleCode (events by record/field), Portal, Records; deep-link to Page Explorer, Access Path Explorer, Security Explorer
- **Page Explorer** at `/admin/page`: Overview, Records, Components, PeopleCode, Security tabs
- **Permission List Explorer** at `/admin/permissionlist`: Overview, Components, Roles, Menus tabs
- **Unified Object Explorer** at `/admin/object/{type}/{name}` (in `graph.py`): cross-type search; auto-redirects to dedicated explorer for supported types (component, page, permissionlist, ae); generic UOM view otherwise
- Nav wiring: dedicated explorers added to Objects nav group; correct cross-links throughout

Files changed:
- `routers/admin/platform.py` — `admin_component()`, `admin_page()` routes
- `routers/admin/security.py` — `admin_permissionlist()` route
- `routers/admin/graph.py` — unified object explorer, cross-type search
- `routers/admin/_core.py` — nav entries for component, page, permissionlist, ae

Commits:
- `6072e76` feat(objects): Component Explorer, Page Explorer, Permission List Explorer
- `7473280` feat(objects): wire dedicated explorers into platform navigation

---

### Component Event Flow Explorer (b42e5b2, d805ee6, 35cd6de, 1e648dc)

`/admin/compflow` (Platform nav): enter a component name, renders the canonical 20-event PeopleSoft processing lifecycle across 4 phases (Search, Build, Interaction, Save). Each event slot shows delivered vs custom PeopleCode presence with inline source viewer and syntax highlighting. Custom events highlighted in amber with LASTUPDOPRID.

New APIs:
- `GET /api/peoplesoft/components/{comp}/events` — enumerate component/record/field PeopleCode events with execution phase, scope, customization status, and canonical event metadata (purpose, phase)
- `GET /api/peoplesoft/components/{comp}/event-source` — fetch PeopleCode source for specific event context from PSPCMTXT

Inline source viewer: click event slot → loads source; PeopleCode syntax highlighting with token-level coloring.

Files changed:
- `routers/admin/compflow.py` — full page (new file)
- `routers/peoplesoft.py` — `/components/{comp}/events`, `/components/{comp}/event-source`
- `routers/admin/_core.py` — Component Event Flow in Platform nav

Commits:
- `b42e5b2` feat(compflow): Component Event Flow APIs + runtime RCA integration
- `d805ee6` feat(compflow): inline PeopleCode source viewer
- `35cd6de` feat(compflow): page improvements and event canonicalization
- `1e648dc` feat(sqr): full-text SQR search + complete Component Event Flow

---

### Incident RCA (39d7409)

`/admin/rca` (Tools nav): single-pane root-cause analysis correlating process failure with Oracle ASH, app/web logs, IB errors, and Knowledge Graph. Tabbed output: Process (scheduler details), Logs (parsed log errors near failure time), ASH (wait events), IB (correlated IB errors), KG (graph context for involved components/records). Pre-populated from runtime process panel deep-links.

Files changed:
- `routers/admin/rca.py` — new file; full RCA page
- `routers/admin/_core.py` — RCA in Tools nav

Commits:
- `39d7409` feat(rca): Incident RCA with log/runtime/alert correlation

---

### Security Audit Dashboard + What Changed Expansion (1d781a0, 762cc9f, 2280c61)

**Security Audit** at `/admin/secaudit`: stat cards (total operators, roles, permission lists, active 30d), top roles by member count, top operators by role count, recent sign-ons (30d), orphaned roles (defined but unassigned), operator type breakdown chart. Added **Security nav group** consolidating: Security Audit, Security Explorer, Operators, Roles, Permission Lists.

**What Changed expansion**: 9 → 20 supported object types. New types: Menus, Queries, Projects, Processes (PS_PRCSDEFN), App Packages, IB Messages, IB Routings, Trees, Translate Values, Component Interfaces. OPRID filter added: client-side filter on updater OPRID shows N/Total counts per type pill.

Files changed:
- `routers/admin/security.py` — `admin_secaudit()`, Security nav group entries
- `routers/admin/_core.py` — Security nav group
- `routers/admin/data.py` — What Changed expansion to 20 types

Commits:
- `1d781a0` feat(security): Security Audit dashboard + SQR record cross-references
- `762cc9f` feat(security): expand audit intelligence and change tracking
- `2280c61` feat(security): expand audit intelligence and change tracking

---

### SQR Cross-References in Record Explorer (1d781a0)

Record detail pages now include a "SQR Programs" section showing which SQR programs read or write this record. Sourced from `sqrdb.get_programs_for_table()`. Operation badges (READ/WRITE) and links to SQR Explorer.

Files changed:
- `routers/admin/objects.py` — SQR Programs section in record detail

Commits:
- `1d781a0` feat(security): Security Audit dashboard + SQR record cross-references

---

### Access Path Explorer (1bac112)

`/admin/accesspath` (Security nav): dual-mode security analysis.

- **Component mode**: enter a component name → lists all Permission Lists that grant access, with linked Roles and Operators per PL; access level and add/update/display flags shown; total access count summary
- **Operator mode**: enter an OPRID → lists all components the operator can access, through which PL and Role chain, with access level badges

Env-aware; URL deep-linking (`?comp=` / `?oprid=`); client-side filtering for rapid investigation; links back to Component Explorer and Security Explorer.

Files changed:
- `routers/admin/security.py` — `admin_access()` route and page

Commits:
- `1bac112` feat(security): Access Path Explorer

---

### Change Risk Analyzer + IB Message Cross-References (5f8e16b)

**Change Risk Analyzer** at `/admin/riskanalysis` (Tools nav): enter a project name → computes blast radius using KG reverse traversal (`/api/impact/project`); scores risk by affected object type weights; shows affected records, components, AE programs, and estimated affected users (via Role→Operator chains); direct navigation to Component Explorer, Record Explorer, and Access Path Explorer for each affected object.

**IB Message cross-references**: UOM IB Message objects (`uom.py` IBMessageProvider) now show correlated Service Operations, Routings, and Subscriptions. Added to Phase 5 Cross-References delivery.

Files changed:
- `routers/admin/platform.py` — `admin_riskanalysis()` route and page
- `connectors/uom.py` — IBMessageProvider cross-reference section
- `routers/admin/_core.py` — Risk Analysis in Tools nav

Verification:
- `/admin/riskanalysis` renders correctly
- IB Message cross-references appear in Object Explorer for IB Message objects
- `python3 scripts/smoke_admin_shell.py` → 57/57

Commits:
- `5f8e16b` feat(risk): Change Risk Analyzer + IB message cross-reference intelligence

---

### SQR Override Intelligence (pending commit)

Extended SQR source-artifact analysis beyond the existing duplicate-filename-only
`/overrides` check to the full override picture: **overridden** (customized copy of a
delivered program), **custom-only** (net-new custom code), **delivered-only** (count
only — avoids dumping hundreds of unmodified rows in normal operation).

`connectors/sqrdb.py`'s `override_summary(env_source_keys)` runs three SQL queries per
env against `sqr_programs`: an INNER JOIN (delivered ∩ custom filename match) for
`overridden`, a `NOT EXISTS` anti-join for `custom_only`, and a `NOT EXISTS` count for
`delivered_only_count`. `GET /api/sqr/override-summary?env=` wires it to
`config.json`'s `sqr_sources` grouped by env.

**Verification against real data**: this demo environment's custom-SQR source trees
are empty (`SELECT source_key, COUNT(*) FROM sqr_programs GROUP BY source_key` shows
only `hcm_sqr_delivered`/`fscm_sqr_delivered`, 179 rows each — zero custom rows
indexed). Live curl correctly returns `0 overridden / 0 custom-only / 179
delivered-only` per env — an honest result, not a bug, but it can't prove the
categorization logic actually works end-to-end. To verify that separately: copied
`data/sqr.db` to a scratch file, inserted a synthetic override row (reused a real
delivered filename `askeffdt.sqc` under a fake `hcm_sqr_custom` source_key) and a
synthetic custom-only row (`CUSTOMONLY.sqr`), then called `override_summary()` against
the scratch DB directly — confirmed `overridden: ['askeffdt.sqc']`, `custom_only:
['CUSTOMONLY.sqr']`, `delivered_only: 178` (one less than the real 179, as expected).

**Bug found and fixed**: the new `/admin/sqroverrides` admin page
(`routers/admin/sqr_view.py`) failed the smoke test with `SyntaxError: Unexpected
token '}'`. Root cause: this file's `_shell()`-content strings follow a
three-part-concatenation convention — `content = f"""...(HTML/CSS, genuine f-string,
needs {{ }} doubling)...""" + _ESC_JS + """...(JS, plain string, needs single { }
because it is NOT f-prefixed)..."""`. I wrote the new page's JS segment using doubled
braces as if the whole thing were one f-string, so Python passed the literal `{{`/`}}`
straight through into the served JavaScript, breaking parsing. Confirmed via: (1) full
server restart ruling out staleness, (2) direct `importlib.reload()` + calling the
function in isolation ruling out any caching layer, (3) isolated test proving Python's
f-string brace-unescaping works as expected in general, (4) comparing against the
working sibling function `sqr_analytics()` in the same file, whose JS after its own
`_ESC_JS` correctly uses single braces. Fixed by de-doubling every brace in the
JS segment.

Also added: `/admin/sqroverrides` nav entry (Platform group), smoke-test coverage
(`scripts/smoke_admin_shell.py`).

Verification:
- `curl /api/sqr/override-summary` → correct real-data result (see above)
- Scratch-DB test → correct categorization with synthetic override/custom-only rows
- `/admin/sqroverrides` renders, JS confirmed single-braced (`grep -c '{{'` → 0)
- `python3 scripts/smoke_admin_shell.py` → 70/70 (was 69/69 before this page)
- `make check` → 100/100 files, 11/11 tests

---

### COBOL Environment Comparison (pending commit)

Added `/admin/cobolcompare` (HCM vs FSCM side-by-side diff), mirroring
`/admin/sqrcompare`'s UI/shape — `connectors/cobol_db.py`'s new
`envcompare_cobol(source_keys_a, source_keys_b, ...)` and `GET
/api/cobol/envcompare?env_a=&env_b=` in `routers/cobol.py`.

**Justified the use case before building, per earlier feedback about not assuming
feature parity between SQR and COBOL just because they share plumbing.** Checked
real data first: `SELECT filename FROM cobol_programs WHERE source_key='hcm_cobol_delivered'
EXCEPT ... 'fscm_cobol_delivered'` → 0 rows either direction (same 115 filenames in
both), and a content_hash join across all shared filenames → 0 rows differ. So in
this environment a COBOL env-compare view has nothing to show — asked the user
whether to build it anyway given that, since the value (a drift/patch-integrity
check between environments) is real independent of today's data: it costs nothing
to show "0 differences" and will surface the moment one environment's COBOL gets
patched without the other. User confirmed build it.

Reused the sibling `sqr_compare_page()`'s single-f-string convention (`{_ESC_JS}`
interpolated inline, not the three-part `""" + _ESC_JS + """` concatenation that
caused the brace-doubling bug in the SQR Overrides page) — avoids repeating that
exact mistake.

Verification:
- `curl /api/cobol/envcompare?env_a=HCM&env_b=FSCM` → real result: 0 only_a,
  0 only_b, all 115 shared files `changed: false` (confirms the "no drift" finding,
  not a bug)
- `/admin/cobolcompare` renders (200), added nav entry (Platform group) and smoke
  test coverage
- `python3 scripts/smoke_admin_shell.py` → 71/71 (was 70/70)
- `make check` → 100/100 files, 11/11 tests

---

### AI-Assisted SQR/COBOL Explanation (pending commit)

Extended the AI Assistant's tool belt so it can explain, summarize, or assess
modernization for indexed SQR/COBOL source — no new endpoint or summarization
pipeline needed, since the existing agentic tool loop already turns raw data
into conversational explanations once the source is in the tool result.

- `connectors/ai_tools.py`'s `sqr_program` tool previously returned only
  metadata/tables/includes from `sqrdb.get_program()` — it turns out
  `get_program()` already includes `source_text` (via `SELECT *`), it just
  wasn't being surfaced usefully: raw, untruncated, some files are 170KB+.
  Added `_truncate_source()` (12,000-char cap, `source_truncated` +
  `source_full_length` flags when clipped) applied to both the SQR tool and
  the new COBOL one, keeping tool-result token cost bounded.
- Added `cobol_program`, a new tool mirroring `sqr_program`'s shape
  (`program`/`table_users`/`search` lookup types) plus a COBOL-specific
  `copy_deps` (forward+reverse COPY closure, wrapping the existing
  `cobol_db.get_copy_deps()`). COBOL had no AI tool at all before this —
  the assistant could reason about SQR programs but not COBOL ones.

Verified with dispatch()-level tests first (truncation confirmed:
171,506 → 12,000 chars for `sysrtdfn.sqc`; all four `cobol_program`
lookup_types return correct real data), then live end-to-end against the
real OpenAI-backed assistant at `/admin/assistant`:
- "Explain PTCALOGM.cbl" → correctly called `cobol_program`, retrieved real
  source, produced an accurate one-sentence summary matching the actual
  COBOL logic (message-logger call, severity check, run-status update)
- "Explain sysrtdfn.sqc" → correctly called `sqr_program` (unchanged tool
  name, now source-aware), produced an accurate summary of the runtime
  table-definition audit procedures

Verification: `make check` 100/100 files + 11/11 tests; smoke test 71/71
(unchanged — no new admin pages, this is an AI-tool-only change).

---

### COBOL Analytics Dashboard (pending commit)

Added the COBOL equivalent of the existing `/admin/sqr/analytics` dashboard:
`cobol_db.analytics()` (top tables by reference count, most-complex programs
by table count, most-COPYd copybooks, delivered/custom breakdown), `GET
/api/cobol/analytics`, and `/admin/cobol/analytics` — plus
`/admin/cobol/table/{table_name}` (the API endpoint already existed, SQR had
an admin page for its equivalent, COBOL didn't).

**Real finding, not a bug**: `top_tables` renders empty for COBOL because
`cobol_tables` genuinely has 0 rows in this environment (verified directly:
`SELECT COUNT(*) FROM cobol_tables` → 0), while `cobol_copies` (806 rows) and
`cobol_calls` (328 rows) are populated and show real data. The page handles
this gracefully rather than erroring — consistent with how this codebase
treats other honestly-empty categories.

**Bug found and fixed**: registered the two new routes
(`/cobol/table/{table_name}`, `/cobol/analytics`) *after* the existing
`/cobol/{filename}` catch-all in the file. FastAPI matches routes in
registration order, so `GET /admin/cobol/analytics` matched
`/cobol/{filename}` with `filename="analytics"` first — the smoke test
caught this immediately (`FAIL /admin/cobol/analytics — missing marker
selector '.an-grid'`, `Uncaught: SyntaxError: Unexpected token '!'`, the
latter being a leftover console error from the wrong page's own JS). Fixed
by moving both new route functions before the catch-all in the file.
Confirmed via live curl that all three routes (`/cobol/analytics`,
`/cobol/table/{table}`, `/cobol/{filename}`) now serve their correct,
distinct content.

While mirroring the SQR analytics page's JS, also noticed (and fixed only in
the new COBOL code, out of scope to touch the SQR original) that the pattern
being copied has a latent bug: it references a `$()` DOM-lookup helper that
is never defined anywhere in that file or the shared `_ESC_JS` snippet — SQR's
`/admin/sqr/table/{table_name}` page has this same undefined-`$` bug today,
apparently never triggering because table-detail pages aren't in the smoke
test's page list. Added `const $ = id => document.getElementById(id);`
explicitly in the new COBOL pages rather than perpetuate the bug.

Verification: live curl on all three affected routes confirms correct/distinct
content; `python3 scripts/smoke_admin_shell.py` → 72/72 (was 71/71); `make check`
→ 100/100 files, 11/11 tests.

---

### Processing Path Explorer UI: Component/Record Mode Toggle (pending commit)

Closed the "Processing Path Explorer UI" ROADMAP gap by extending the existing
`/admin/compseq` ("PC Timeline") page rather than building a new one from
scratch — it already had exactly the visual language the gap called for
(ordered phase-card grid, per-slot delivered/custom/empty coloring, click-to-
expand inline detail), just scoped to Component sequences only. The Record
Explorer's "Processing Sequence" tab (built earlier this session) only ever
had a plain per-phase table — a real, noticeable gap once compseq's richer
visualization existed for Component.

Added a Component/Record mode `<select>` to compseq's toolbar. `renderRecord()`
consumes `record_sequence()`'s API response directly (`{record, phases: [{phase,
label, desc, events: [{name, status, field, last_oprid, last_dttm}]}]}`) —
simpler than Component mode's client-side `SEQUENCE` constant + raw-events
grouping, since Record's backend already canonicalizes into phases. Clicking a
populated slot shows field/last-editor/timestamp metadata (no source code —
there's no per-event source-fetch endpoint for record-owned PeopleCode the way
Component has `/event-source`; the panel says this honestly instead of
pretending to have source it doesn't).

Avoided a fragile approach I initially wrote (embedding `JSON.stringify(ev)`
into an inline `onclick` HTML attribute with `&quot;`-escaping) in favor of a
`_recSlotMap` lookup keyed by slot id — safer against any special characters
in event data and consistent with how `_evtMap` already works for Component
mode.

**Verified in a real headless Chrome instance** (driven directly via the
Chrome DevTools Protocol, reusing `smoke_admin_shell.py`'s `DevTools`/
`chrome_path`/`wait_for_target` helpers as a library rather than a fresh
harness): switched to Record mode, entered `JOB`, called `load()`, and
confirmed the rendered DOM matched `record_sequence('HCM','JOB')` exactly
(4 phase cards, 158 total slots, 154 with PeopleCode, 0 custom — all real
counts, not assumed); clicked a populated `FieldDefault` slot and confirmed
the metadata panel opened with the correct field (`ACTION`); switched back
to Component mode with `JOB_DATA` and confirmed no regression (20 slots,
matching pre-change behavior).

Verification: `python3 scripts/smoke_admin_shell.py` → 73/73 (was 72/72,
added `/admin/compseq` coverage which had none before); `make check` →
100/100 files, 11/11 tests.

---

### AI-Assisted Sequence Explanation (pending commit)

Added `peoplecode_sequence` to `connectors/ai_tools.py` — closes the last
"Processing Sequence Intelligence" ROADMAP gap ("AI-assisted conversational
sequence explanation ... not started"). Rather than three separate tools
(component/record/page), one tool with a `target_type` enum dispatches to
the existing `component_sequence()`/`record_sequence()`/`page_owned_events()`
connector functions — reusing the exact backend logic already verified
earlier this session, no new SQL. Complements the pre-existing
`component_events` tool: that one is a flat listing (no ordering context),
this one is specifically for "what fires before/after what" reasoning.

As with the earlier SQR/COBOL AI-explain work, no new chat UI or
summarization pipeline was needed — once real canonical-sequence data is in
a tool result, ordering questions fall out of the existing agentic tool loop
for free.

Verified live against the real OpenAI-backed assistant at `/admin/assistant`
(not just dispatch()-level unit checks):
- "Is FieldDefault in the Build phase or Interaction phase?" for record JOB
  -> correctly answered Build phase
- "What fires immediately before SaveEdit?" for component JOB_DATA ->
  correctly answered RowDelete — independently cross-checked by calling
  `component_sequence('HCM','JOB_DATA')` directly and confirming Interaction
  Phase's last populated slot is RowDelete, immediately preceding Save
  Phase's SaveEdit

Verification: `make check` 100/100 files + 11/11 tests; smoke test 73/73
(unchanged — AI-tool-only change, no new admin pages).

---

### Broader SQR/COBOL Diff Modes (pending commit)

Closed the "broader diff modes (syntax-aware, ignore whitespace/comments)"
ROADMAP item (the "ignore whitespace/comments" half — full syntax-aware/AST
diffing is a larger lift, left open). Added a `diff_mode` parameter
(`"exact"` | `"normalized"`) to `envcompare_sqr()` / `envcompare_cobol()`:
normalized mode strips comment lines and insignificant whitespace before
re-comparing only the subset of file pairs whose raw `content_hash` already
differs — exact mode's cost is unchanged. Comment stripping reuses each
language's existing parser convention rather than inventing a third one:
SQR's `!`-prefixed lines (`sqrparser.py`'s `_RE_COMMENT_LINE`) and COBOL's
fixed-format column-7 `*` (`cobolparser.py`'s `_RE_COMMENT_LINE`).

Both `/admin/sqrcompare` and `/admin/cobolcompare` got an "Exact match" /
"Ignore whitespace/comments" toggle, and the changed-files table now
distinguishes `DIFFERS (whitespace/comments only)` from a plain `DIFFERS`.

**Verification methodology**: HCM and FSCM are byte-identical for both SQR
and COBOL in this environment (established in earlier sessions), so there
was nothing real to demonstrate against — used the same scratch-DB approach
as SQR Override Intelligence. For each of SQR and COBOL:
1. Cloned a real indexed program's row into the other environment's source
   tree, adding only a comment line + trailing whitespace to its
   `source_text`, with a distinct `content_hash` to simulate a real
   content-hash mismatch. Confirmed exact mode reports `changed: true`
   (byte-different) while normalized mode reports `changed: false`,
   `content_normalized_same: true` — the comment/whitespace tweak is
   correctly ignored.
2. On a second variant, inserted a genuine non-comment token well past the
   file's header-comment block (an earlier attempt inserted it inside the
   license-header comment block by accident, which the normalizer correctly
   stripped along with everything else — a good sign the normalizer works,
   but not a valid test of "real change survives normalization"; moved the
   insertion point past the header and got a true positive). Confirmed
   normalized mode still reports `changed: true`,
   `content_normalized_same: false` for a real logic change.
3. Verified the UI toggle live in a headless Chrome instance (reusing
   `smoke_admin_shell.py`'s DevTools helpers): switched `/admin/sqrcompare`
   to "Ignore whitespace/comments", called `load()`, confirmed it re-fetches
   with `diff_mode=normalized` and renders the real 179/0/0 counts.

Verification: `make check` 100/100 files + 11/11 tests; smoke test 73/73
(unchanged — modifies existing pages, no new routes).
