# PeopleSoft Hypergraph Intelligence - PHI

PeopleSoft Hypergraph Intelligence is a read-only observability and exploration
platform for PeopleSoft environments.

It is designed to help administrators and developers inspect PeopleSoft
metadata, Integration Broker configuration, transaction activity, logs,
nginx traffic, Oracle connectivity, and environment topology from a
single API-driven interface.

The project is intentionally built around **read-only access** wherever
possible.

------------------------------------------------------------------------

## Goals

PeopleSoft Hypergraph Intelligence provides:

-   Environment-aware PeopleSoft inspection
-   Oracle-backed metadata queries
-   Integration Broker discovery, including services, service operations,
    routings, nodes, queues, handlers, security, and message relationships
-   Transaction tracing
-   Knowledge graph generation
-   Log exploration
-   nginx / reverse proxy visibility
-   Multi-environment support for HCM, FSCM, and future PeopleSoft
    pillars
-   AI-assisted PeopleSoft troubleshooting (Claude / OpenAI / Ollama, 21+ tools)
-   Filesystem source artifact intelligence (SQR, SQC, COBOL/copybook) alongside
    database metadata
-   A Plugin SDK for adding custom object/graph/runtime providers, health checks,
    config-driven ingest sources, and admin pages without editing core files

------------------------------------------------------------------------

## Project Structure

```text
PeopleSoft-Hypergraph-Intelligence/
├── main.py                         # FastAPI app, router registration, static frontend mount
├── requirements.txt                # Python dependencies
├── LICENSE                         # Apache-2.0 license
├── README.md                       # Project install/run overview
├── ARCHITECTURE.md                 # System architecture and design contracts
├── ROADMAP.md                      # Current status and remaining work
├── DEVELOPMENT_DIARY.md            # Chronological engineering journal
├── HANDOFF_PROMPT.md               # AI-agent handoff instructions
├── PLUGINS.md                      # Plugin SDK: extension points, loading, worked example
├── PHASE2.md                       # Historical planning notes (superseded by Phase 8, implemented)
├── config/
│   └── role_mapping.yml            # PeopleSoft role → Authelia group mapping
├── plugins/
│   └── example_hello.py            # Worked Plugin SDK example (all six extension points)
├── connectors/
│   ├── ae.py                       # Application Engine metadata/runtime helpers
│   ├── ai.py                       # AI provider abstraction (AIProvider ABC + get_provider factory)
│   ├── ai_claude.py                # Anthropic Claude provider implementation
│   ├── ai_openai.py                # OpenAI provider implementation
│   ├── ai_ollama.py                # Ollama local inference provider implementation
│   ├── ai_tools.py                 # AI tool definitions and dispatch (wraps existing connectors)
│   ├── alerts.py                   # Runtime alert checks
│   ├── appsrvproc.py               # SSH `ps`-based live Tuxedo/App Server process tracking
│   ├── cobolparser.py              # COBOL/copybook parser (program vs copybook, COPY/CALL, EXEC SQL)
│   ├── cobol_db.py                 # SQLite COBOL index (data/cobol.db)
│   ├── cobolingest.py              # SSH-based COBOL filesystem indexer
│   ├── driftdb.py                  # SQLite drift snapshot store (data/drift.db)
│   ├── envcompare.py               # Cross-environment comparison logic
│   ├── execution.py                # Oracle execution/runtime queries
│   ├── graphdb.py                  # Knowledge graph store and dependency graph logic
│   ├── graphshape.py               # Shared graph payload annotations and edge type aliases
│   ├── ib.py                       # Integration Broker metadata/runtime discovery
│   ├── impact.py                   # Impact forecasting: project KG traversal + env risk scoring
│   ├── incidentdb.py                # SQLite incident record + RCA snapshot store (data/incidents.db)
│   ├── logdb.py                    # SQLite log store (data/logs.db): web, app, error tables
│   ├── logingest.py                # Log ingestion orchestrator: SSH→parse→store per source
│   ├── logparser.py                # Line parsers: pia_access, pia_error, appsrv, tuxedo, apache, f5, igw, prcs_ae
│   ├── nginx.py                    # nginx log/status helpers
│   ├── oracle.py                   # Oracle connectivity helpers
│   ├── peoplecode.py               # PeopleCode decoding/source helpers; canonical processing sequence
│   ├── peoplesoft.py               # PeopleSoft environment helpers
│   ├── plugins.py                  # Plugin SDK registries (object/graph/runtime providers, health checks, source types, nav/routers)
│   ├── pluginloader.py             # Discovers and loads plugins/*.py at startup, per-plugin isolation
│   ├── promotiondb.py              # SQLite promotion event log (data/promotions.db)
│   ├── psdb.py                     # Core PeopleSoft DB metadata access
│   ├── ptmetadata.py               # PeopleTools/version-aware metadata discovery
│   ├── runtimedb.py                 # SQLite runtime metrics history (data/runtime.db)
│   ├── scheduler.py                # Background scheduler: graph snapshots, runtime snapshots, log ingest
│   ├── sqlws.py                    # SQL Workspace backend helpers
│   ├── sqrdb.py                    # SQLite SQR/SQC index (data/sqr.db)
│   ├── sqringest.py                # SSH-based SQR filesystem indexer
│   ├── sqrparser.py                # Pure SQR/SQC parser (tables, includes, procedures)
│   ├── sshclient.py                # Paramiko SSH/SFTP wrapper with per-host connection pooling
│   ├── system.py                   # Host/service/container/log management
│   ├── tracing.py                  # Transaction tracing helpers
│   └── uom.py                      # Unified Object Model providers
├── routers/
│   ├── admin/                      # Admin UI package
│   │   ├── __init__.py             #   Re-exports router; triggers sub-module imports
│   │   ├── _core.py                #   Shared: router obj, nav groups, _shell, CSS/JS
│   │   ├── home.py                 #   /admin/, /admin/users
│   │   ├── logs.py                 #   /admin/logs, /admin/log_errors, /admin/log_viewer, /admin/log_session, /admin/igw, /admin/prcs-ae
│   │   ├── security.py             #   /admin/security, /record, /field, /operator, /role, /peoplecode, /secaudit, /access
│   │   ├── graph.py                #   /admin/graph, /object, /portal, /metadata, /graphdb
│   │   ├── runtime.py              #   /admin/runtime, /infra, /tracing, /envcompare, /drift, /promotions, /topology
│   │   ├── data.py                 #   /admin/sqlws, /query, /conqrs
│   │   ├── integration.py          #   /admin/ib, /ibmessage, /ibapp, /ibsvcgrp, /ibrtng, /iboper
│   │   ├── objects.py              #   /admin/ci, /tree, /menu, /appclass, /adsdef, /cbskill, /approval, /contsvc, /urldef
│   │   ├── portal.py               #   /admin/navcoll, /relcontent, /efmapping, /dropzone, /pivotgrid, /srchdef, /srchcat, /xpub, /stylesheet, /pcsearch
│   │   ├── platform.py             #   /admin/prcsdefn, /filelayout, /xlat, /project, /msgcat, /archobj, /timezone, /locale, /ptftest, /ae, /component, /page, /riskanalysis
│   │   ├── perf.py                 #   /admin/pmmetric, /pmtrans, /pmevent
│   │   ├── compflow.py             #   /admin/compflow (Component Event Flow), /admin/compseq (PC Timeline; Component/Record mode toggle)
│   │   ├── rca.py                  #   /admin/rca (Incident RCA)
│   │   ├── incidents.py            #   /admin/incidents (list + detail/replay)
│   │   ├── sqr_view.py             #   /admin/sqr, /sqrsearch, /sqrdeps, /sqrcompare (+ diff-mode toggle), /sqroverrides
│   │   ├── cobol_view.py           #   /admin/cobol (list + detail, Process Runs tab), /cobolcompare, /cobol/analytics, /cobol/table/{name}
│   │   └── tools.py                #   /admin/reports, /tools, /impact, /assistant, /docs
│   ├── assistant.py                # AI Assistant API (/api/assistant/*)
│   ├── authelia_admin.py           # Authelia user/group administration
│   ├── cobol.py                    # COBOL Source Artifact Intelligence API (/api/cobol/*)
│   ├── drift.py                    # Drift snapshot/alert API (/api/drift/*)
│   ├── envcompare.py               # Environment comparison API
│   ├── field.py                    # Field metadata API
│   ├── graphdb.py                  # Knowledge graph API
│   ├── health.py                   # Health/status API
│   ├── ib.py                       # Integration Broker API
│   ├── identity.py                 # PeopleSoft → Authelia identity workflow
│   ├── impact_api.py               # Impact forecasting API (/api/impact/*)
│   ├── incident.py                 # Incident recording API (/api/incidents/*)
│   ├── live.py                     # Live event stream API
│   ├── logs.py                     # Log Intelligence REST API (/api/logs/*)
│   ├── metadata.py                 # Metadata/version/relationship APIs
│   ├── nginx.py                    # nginx API
│   ├── operator.py                 # Operator/OPRID API
│   ├── oracle.py                   # Oracle connectivity API
│   ├── peoplesoft.py               # PeopleSoft environment API
│   ├── plugin_sources.py           # Plugin SDK config-driven source API (/api/plugins/sources/*)
│   ├── promotions.py               # Promotion event log API (/api/promotions/*)
│   ├── record.py                   # Record metadata API
│   ├── role.py                     # Role/security API
│   ├── runtime.py                  # Runtime Monitor, ASH, domains, alerts, app server processes, plugin providers/health checks, AE process trace
│   ├── sqlws.py                    # SQL Workspace API
│   ├── sqr.py                      # SQR Source Artifact Intelligence API (/api/sqr/*)
│   ├── system.py                   # Infrastructure/service/container API
│   ├── topology.py                 # Environment topology API
│   └── tracing.py                  # Transaction tracing API
├── data/
│   ├── knowledge_graph_HCM.json    # Generated graph snapshot/cache
│   ├── knowledge_graph_FSCM.json   # Generated graph snapshot/cache
│   ├── drift.db                    # SQLite: scheduled drift snapshots and alerts
│   ├── logs.db                     # SQLite: ingested web/app log entries and errors
│   ├── promotions.db               # SQLite: manual promotion event log
│   ├── runtime.db                  # SQLite: runtime metrics history
│   ├── incidents.db                # SQLite: incident records + RCA snapshots
│   ├── sqr.db                      # SQLite: SQR/SQC source index
│   └── cobol.db                    # SQLite: COBOL source index
├── logs/
│   ├── identity_audit.jsonl        # Identity workflow audit trail
│   └── provision_requests.json     # Provision request state
├── static/
│   ├── index.html                  # Landing page
│   ├── app.css                     # Shared frontend shell styles
│   ├── app.js                      # Shared frontend shell behavior
│   └── images/                     # Logo/favicon/static image assets
└── tests/
    └── ...                         # Test coverage
```

------------------------------------------------------------------------

## Requirements

### System Requirements

-   Linux server
-   Python 3.11+
-   Oracle Instant Client
-   Network access to PeopleSoft Oracle databases
-   SSH access to web/app server hosts (for Phase 8 log ingestion)

### Python Requirements

Install dependencies:

``` bash
pip install -r requirements.txt
```

Core dependencies (see `requirements.txt` for the authoritative list):

``` text
fastapi
uvicorn
oracledb
pydantic
requests
jinja2
python-multipart
PyYAML
paramiko       # SSH/SFTP for remote log/SQR/COBOL ingestion
```

AI provider dependencies (install only the providers you use):

``` bash
pip install anthropic   # Claude (Anthropic)
pip install openai      # OpenAI / Azure OpenAI
# Ollama requires no Python package — it uses a local REST API
```

------------------------------------------------------------------------

## Oracle Client Setup

Install Oracle Instant Client.

``` bash
export LD_LIBRARY_PATH=/opt/oracle/instantclient_19_28:$LD_LIBRARY_PATH
export PATH=/opt/oracle/instantclient_19_28:$PATH
```

------------------------------------------------------------------------

## Configuration

All configuration lives in a single file: `/opt/deathstar-api/config.json`.

The file has five top-level sections:

| Section | Purpose |
|---------|---------|
| `oracle` | Raw Oracle database connections (used by non-PS queries) |
| `peoplesoft` | PeopleSoft environment connections (used for all metadata queries) |
| `ai` | AI provider selection and API keys |
| `ssh_hosts` | Reusable SSH connection profiles for remote log access |
| `log_sources` | Log files to ingest (web/app server logs per environment) |

---

### oracle

Low-level Oracle connections. Used for queries that do not require a PS environment context.

``` json
"oracle": {
  "databases": [
    {
      "name":     "HRDMO",
      "host":     "192.168.1.10",
      "port":     1521,
      "service":  "HRDMO",
      "user":     "DEATHSTAR_MON",
      "password": "changeme"
    }
  ]
}
```

---

### peoplesoft

PeopleSoft environment connections. Each entry becomes a named environment
(e.g. `HCM`, `FSCM`) used in the UI and API `?env=` parameters.

``` json
"peoplesoft": {
  "environments": [
    {
      "name":     "HCM",
      "service":  "HRDMO",
      "host":     "192.168.1.10",
      "port":     1521,
      "user":     "DEATHSTAR_MON",
      "password": "changeme"
    },
    {
      "name":     "FSCM",
      "service":  "FSCMDMO",
      "host":     "192.168.1.10",
      "port":     1521,
      "user":     "DEATHSTAR_MON",
      "password": "changeme"
    }
  ]
}
```

---

### ai

Controls the Engineering Assistant at `/admin/assistant`.

``` json
"ai": {
  "provider": "openai",
  "claude": {
    "api_key": "sk-ant-...",
    "model":   "claude-sonnet-4-6"
  },
  "openai": {
    "api_key": "sk-...",
    "model":   "gpt-4o"
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "model":    "llama3.1"
  }
}
```

| Field | Description |
|-------|-------------|
| `provider` | Active provider: `claude`, `openai`, or `ollama` |
| `claude.api_key` | Anthropic API key |
| `claude.model` | Recommended: `claude-sonnet-4-6` |
| `openai.api_key` | OpenAI API key |
| `openai.model` | Recommended: `gpt-4o` |
| `ollama.base_url` | Ollama server URL — default `http://localhost:11434` |
| `ollama.model` | e.g. `llama3.1`, `mistral`, `qwen2.5` |

Only the `provider` field is required. Unused provider sections are ignored at runtime.

**Environment variable overrides** take precedence over config.json values:

``` bash
export CLAUDE_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export OLLAMA_BASE_URL="http://localhost:11434"
```

**Ollama** works in air-gapped environments with no external API key:

``` bash
ollama pull llama3.1
# then set "provider": "ollama" in config.json
```

Check which provider is active (no secrets exposed):

``` bash
curl http://localhost:8088/api/assistant/status
```

---

### ssh_hosts

Defines reusable SSH connection profiles for remote log ingestion.
Each key is an alias referenced in `log_sources[].ssh_host`.

``` json
"ssh_hosts": {
  "webserver1": {
    "host":     "10.0.0.10",
    "port":     22,
    "username": "psadm1",
    "key_path": "~/.ssh/id_rsa",
    "password": null
  },
  "appserver1": {
    "host":     "10.0.0.11",
    "port":     22,
    "username": "psadm1",
    "key_path": "~/.ssh/id_rsa",
    "password": null
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `host` | yes | Hostname or IP of the remote server |
| `port` | no | SSH port (default: 22) |
| `username` | yes | SSH login username |
| `key_path` | no | Path to private key — supports `~` expansion. Recommended over password. |
| `password` | no | Password auth — use only if key auth is unavailable |

Use the special alias `"local"` in `log_sources[].ssh_host` to read files
directly from disk without SSH (for logs on the same host as the platform).

---

### log_sources

Defines which log files to ingest. Each entry is one log file glob pattern
on one host. The scheduler ingests all enabled sources every 60 seconds,
reading only new bytes since the last run (byte-offset tracking per file).

``` json
"log_sources": [
  {
    "name":     "WEB1_ACCESS",
    "type":     "pia_access",
    "env":      "HCM",
    "ssh_host": "webserver1",
    "path":     "/opt/oracle/psft/pt/webserv/HCM/servers/PIA/logs/PIA_access*.log",
    "enabled":  true
  },
  {
    "name":     "WEB1_ERROR",
    "type":     "pia_error",
    "env":      "HCM",
    "ssh_host": "webserver1",
    "path":     "/opt/oracle/psft/pt/webserv/HCM/servers/PIA/logs/PIA_stderr*.log",
    "enabled":  true
  },
  {
    "name":     "APP1",
    "type":     "appsrv",
    "env":      "HCM",
    "ssh_host": "appserver1",
    "path":     "/opt/oracle/psft/cfg/appserv/HCM/LOGS/APPSRV_*.LOG",
    "enabled":  true
  },
  {
    "name":     "APP1_TUX",
    "type":     "tuxedo",
    "env":      "HCM",
    "ssh_host": "appserver1",
    "path":     "/opt/oracle/psft/cfg/appserv/HCM/LOGS/TUXLOG.*",
    "enabled":  true
  },
  {
    "name":     "PROXY1",
    "type":     "apache_access",
    "env":      "HCM",
    "ssh_host": "webserver1",
    "path":     "/etc/nginx/logs/access.log",
    "enabled":  true
  }
]
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Unique source identifier shown in the UI and used for offset tracking |
| `type` | yes | Log format (see table below) |
| `env` | yes | PeopleSoft environment this source belongs to (`HCM`, `FSCM`, etc.) |
| `ssh_host` | yes | SSH host alias from `ssh_hosts`, or `"local"` for local files |
| `path` | yes | Absolute path or glob pattern on the remote host. Glob patterns (e.g. `APPSRV_*.LOG`) resolve to all matching files; each is tracked independently. |
| `enabled` | no | Set to `false` to skip without removing the entry (default: `true`) |

**Supported log types:**

| Type | Source | Description |
|------|--------|-------------|
| `pia_access` | WebLogic PIA | NCSA extended access log — extracts OPRID, component, page, status, duration |
| `pia_error` | WebLogic PIA | stderr/error log — extracts ORA- codes, OPRID |
| `appsrv` | Tuxedo App Server | `APPSRV_MMDD.LOG` — extracts OPRID, ORA- codes, object refs |
| `tuxedo` | Tuxedo ULOG | `TUXLOG.MMDDYY` / `ULOG.MMDDYY` — domain-level events and errors |
| `apache_access` | Apache / nginx | Combined access log (standard NCSA) |
| `apache_error` | Apache / nginx | Error log |
| `f5_access` | F5 LTM | HSL iRule access log (NCSA combined format) |
| `prcs_ae` | Process Scheduler (AESRV) | Tuxedo AESRV log — applid, process instance, error detection (configured in `log_sources`, same as other types) |
| `igw_error_log` | Integration Gateway | `errorLog.html` — HTML block parser; configured separately in `config.json`'s `igw_log_sources` array, not `log_sources` |

**Multiple web/app servers:** Add one entry per server. Give each a unique `name`
and point to its own `ssh_host` alias.

``` json
{ "name": "WEB2_ACCESS", "type": "pia_access", "env": "HCM", "ssh_host": "webserver2", "path": "...", "enabled": true },
{ "name": "APP2",        "type": "appsrv",     "env": "HCM", "ssh_host": "appserver2", "path": "...", "enabled": true }
```

**Checking ingestion status:**

``` bash
curl http://localhost:8088/api/logs/sources
```

Or visit `/admin/logs` in the UI. The page shows each source, when it was
last ingested, how many files are being tracked, and any errors.

**Triggering an immediate ingest** (useful after adding a new source):

``` bash
curl -X POST http://localhost:8088/api/logs/ingest
```

------------------------------------------------------------------------

## Database Permissions

Recommended monitoring account:

``` sql
GRANT CREATE SESSION TO deathstar_mon;
GRANT SELECT ANY TABLE TO deathstar_mon;
GRANT SELECT ANY DICTIONARY TO deathstar_mon;
GRANT SELECT_CATALOG_ROLE TO deathstar_mon;
```

------------------------------------------------------------------------

## Installation

``` bash
git clone https://github.com/NoodleSploder/peoplesoft-explorer.git deathstar-api
cd deathstar-api

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Running

``` bash
uvicorn main:app --host 0.0.0.0 --port 8088
```

Browse to:

``` text
http://localhost:8088/
```

The root route redirects to `/static/index.html`, which loads the shared
PeopleSoft Hypergraph Intelligence frontend shell and sticky navigation
banner. API documentation remains available at `/docs`.

------------------------------------------------------------------------

## Running as a Service

Create:

``` text
/etc/systemd/system/deathstar-api.service
```

Use an appropriate systemd service pointing to:

``` text
/opt/deathstar-api/.venv/bin/uvicorn
```

Then:

``` bash
sudo systemctl daemon-reload
sudo systemctl enable deathstar-api
sudo systemctl start deathstar-api
```

------------------------------------------------------------------------

## Common Endpoints

The full live endpoint catalog is available at:

```text
GET /docs
GET /openapi.json
```

### Frontend

```text
GET /                         # Redirects to /static/index.html
GET /static/index.html        # Main frontend shell
GET /static/app.css           # Shared styles
GET /static/app.js            # Shared frontend behavior
```

### Health and Status

```text
GET /api/health
```

### Knowledge Graph

```text
GET    /api/graph/build?env=HCM
GET    /api/graph/stats?env=HCM
GET    /api/graph/search?env=HCM&q=JOB
GET    /api/graph/node/{node_id}?env=HCM
GET    /api/graph/neighbors/{node_id}?env=HCM&direction=both&depth=1
GET    /api/graph/path?env=HCM&source={source_id}&target={target_id}
GET    /api/graph/dependencies/{node_id}?env=HCM&depth=3
GET    /api/graph/reverse-dependencies/{node_id}?env=HCM&depth=3
GET    /api/graph/impact/{node_id}?env=HCM&depth=3
GET    /api/graph/export?env=HCM&format=json
GET    /api/graph/components?env=HCM
GET    /api/graph/cycles?env=HCM
GET    /api/graph/topological-order?env=HCM
GET    /api/graph/diff?env1=HCM&env2=FSCM
GET    /api/graph/snapshots
GET    /api/graph/snapshots/schedule
POST   /api/graph/snapshots?env=HCM
POST   /api/graph/snapshots/prune
GET    /api/graph/snapshots/{snapshot_id}
DELETE /api/graph/snapshots/{snapshot_id}
POST   /api/graph/clear?env=HCM
POST   /api/graph/compact?env=HCM
```

### Environment Compare

```text
GET /api/envcompare/config
GET /api/envcompare/summary?env1=HCM&env2=FSCM
GET /api/envcompare/records?env1=HCM&env2=FSCM&q=
GET /api/envcompare/fields?env1=HCM&env2=FSCM&record=JOB
GET /api/envcompare/components?env1=HCM&env2=FSCM&q=
GET /api/envcompare/permissions?env1=HCM&env2=FSCM&q=
GET /api/envcompare/roles?env1=HCM&env2=FSCM&q=
GET /api/envcompare/ae?env1=HCM&env2=FSCM&q=
GET /api/envcompare/ae-body?env1=HCM&env2=FSCM&ae_applid=GPUS_TAX_CALC
GET /api/envcompare/peoplecode?env1=HCM&env2=FSCM&q=
GET /api/envcompare/peoplecode-source?env1=HCM&env2=FSCM&ref={encoded_ref}
GET /api/envcompare/sql_definitions?env1=HCM&env2=FSCM&q=
GET /api/envcompare/queries?env1=HCM&env2=FSCM&q=
GET /api/envcompare/portals?env1=HCM&env2=FSCM&q=
GET /api/envcompare/portal-object?env1=HCM&env2=FSCM&name={PORTAL_OBJNAME}
GET /api/envcompare/menus?env1=HCM&env2=FSCM&q=
GET /api/envcompare/trees?env1=HCM&env2=FSCM&q=
GET /api/envcompare/ib_routings?env1=HCM&env2=FSCM&q=
GET /api/envcompare/ib_messages?env1=HCM&env2=FSCM&q=
GET /api/envcompare/ci?env1=HCM&env2=FSCM&q=
GET /api/envcompare/graph?env1=HCM&env2=FSCM
```

### Drift Detection

Scheduled snapshots run automatically after each graph build cycle. Use the
`POST /snapshot` endpoint to trigger manually.

```text
POST /api/drift/snapshot?env1=HCM&env2=FSCM
GET  /api/drift/latest?env1=HCM&env2=FSCM
GET  /api/drift/history?env1=HCM&env2=FSCM&days=30
GET  /api/drift/alerts?env1=HCM&env2=FSCM
GET  /api/drift/alerts?env1=HCM&env2=FSCM&include_resolved=true
```

### Impact Forecasting

```text
GET /api/impact/project?env=HCM&project=MY_PROJECT
GET /api/impact/risk?env1=HCM&env2=FSCM
```

`/api/impact/risk` is KG-independent — it uses the latest drift snapshot to
score deployment risk by object type without requiring a built knowledge graph.

### Promotion History

Phase 1 is a manual event log. Auto-detection from PSPROJECTDEFN is planned
for Phase 2 when promotion-chain DB connections are available.

```text
POST   /api/promotions
GET    /api/promotions?pillar=HCM&project=MY_PROJECT&env=TST
GET    /api/promotions/timeline?pillar=HCM&project=MY_PROJECT
GET    /api/promotions/summary?pillar=HCM
DELETE /api/promotions/{id}
```

Example POST body:

``` json
{
  "pillar":       "HCM",
  "project":      "GPIT_HR92_OBJECTS",
  "from_env":     "DV",
  "to_env":       "TST",
  "promoted_at":  "2026-07-01",
  "promoted_by":  "jsmith",
  "ticket_ref":   "JIRA-1234",
  "notes":        "Initial promotion for Q3 patch"
}
```

### AI Assistant

```text
GET  /api/assistant/status
POST /api/assistant/chat
```

Chat request body:

``` json
{
  "messages": [
    {"role": "user", "content": "Which AE programs touch the JOB record?"}
  ],
  "stream": false
}
```

Set `"stream": true` to receive a Server-Sent Events stream with `tool_start`,
`tool_result`, `content`, and `done` events.

The assistant has access to 21 tools backed by live PeopleSoft Hypergraph Intelligence connectors:

| Tool | Purpose |
|------|---------|
| `search_objects` | Find PS objects by name across all types |
| `peoplecode_search` | Full-text search through PeopleCode source |
| `graph_dependencies` | What does this object depend on? |
| `graph_impact` | What depends on this object? (blast radius) |
| `who_has_access` | Roles and permission lists that grant access to a component |
| `ae_steps` | List sections and steps of an AE program |
| `sql_lookup` | Retrieve a SQL definition by name |
| `envcompare_summary` | Object count comparison between two environments |
| `project_impact` | Downstream risk of promoting a project |
| `active_sessions` | Currently active user sessions (PSACCESSLOG) |
| `record_usage` | All components, pages, and AE programs using a record |
| `log_search` | Search ingested web/app log entries by user, component, time |
| `log_errors` | Grouped error summary from ingested logs |
| `session_log_chain` | Full web→app log chain for a user in a time window |
| `environment_health` | Overall health snapshot for an environment |
| `ib_diagnostics` | Integration Broker queue/routing diagnostics |
| `process_scheduler_health` | Process Scheduler queue/error health |
| `component_events` | Canonical processing-sequence events for a component (search/build/interaction/save phases) |
| `sqr_program` | Look up an SQR/SQC program's tables, includes, dependencies, and (if indexed) source for explain/summarize questions |
| `cobol_program` | Look up a COBOL program/copybook's tables, COPY deps, calls, and (if indexed) source |
| `peoplecode_sequence` | Canonical ordered processing sequence for a component, record, or page — for "what fires before X" ordering questions |

### Log Intelligence

```text
GET  /api/logs/sources                          # List all log sources with ingest status
GET  /api/logs/web?env=HCM&oprid=GUACUSER       # Query web access entries
GET  /api/logs/app?env=HCM&errors_only=true     # Query app server entries
GET  /api/logs/errors?env=HCM&summary=true      # Error surface grouped by code + object
GET  /api/logs/errors?env=HCM&error_code=ORA-00942  # Filter to a specific error
GET  /api/logs/session/{oprid}?start=...&end=...    # Web+app chain for one user
POST /api/logs/search?q=ORA-00942&env=HCM       # Full-text search across web+app entries
POST /api/logs/ingest                            # Trigger immediate ingest (non-blocking)
```

Query parameters for `/api/logs/web`:

| Parameter | Description |
|-----------|-------------|
| `env` | Filter to a specific environment (e.g. `HCM`) |
| `oprid` | Filter to a specific user OPRID |
| `component` | Filter to a specific PS component name |
| `status` | Filter by HTTP status code (e.g. `500`) |
| `errors_only` | `true` to return only error entries (status ≥ 500) |
| `start` / `end` | ISO datetime range (e.g. `2026-07-01T08:00:00`) |
| `limit` | Max rows (default 200, max 2000) |

Query parameters for `/api/logs/app`:

| Parameter | Description |
|-----------|-------------|
| `env` | Environment filter |
| `oprid` | OPRID filter |
| `object_ref` | Filter by extracted PS object name |
| `level` | Log level filter: `ERROR`, `INFO`, `WARN` |
| `errors_only` | `true` to return only error entries |
| `start` / `end` | ISO datetime range |
| `limit` | Max rows |

### Integration Broker

```text
GET /api/ib/dashboard?env=HCM
GET /api/ib/services?env=HCM&q=
GET /api/ib/services/{applname}?env=HCM
GET /api/ib/services/{applname}/operations?env=HCM
GET /api/ib/operations?env=HCM&q=
GET /api/ib/operations/{opname}?env=HCM
GET /api/ib/routings?env=HCM&q=
GET /api/ib/routings/{rtngname}?env=HCM
GET /api/ib/nodes?env=HCM&q=
GET /api/ib/nodes/{nodename}?env=HCM
GET /api/ib/queues?env=HCM&q=
```

### Identity and Provisioning

```text
GET    /api/identity/compare/{oprid}?env=HCM
POST   /api/identity/sync/{oprid}?env=HCM
POST   /api/identity/provision/{oprid}?env=HCM
POST   /api/identity/bulk-provision?env=HCM
GET    /api/identity/requests
POST   /api/identity/requests?env=HCM
POST   /api/identity/requests/{req_id}/approve?env=HCM
POST   /api/identity/requests/{req_id}/reject
DELETE /api/identity/requests/{req_id}
GET    /api/identity/status?env=HCM
POST   /api/identity/sync-all?env=HCM
GET    /api/identity/audit?limit=100
```

### Runtime Monitor

```text
GET /api/runtime/domains?env=HCM
GET /api/runtime/alerts?env=HCM&db=HRDMO
GET /api/runtime/ash?db=HRDMO&minutes=30
GET /api/runtime/ash/sql?db=HRDMO&minutes=30
GET /api/runtime/appserver-processes?env=HCM   # Live Tuxedo/App Server process list via SSH ps
GET /api/runtime/plugins                        # List registered plugin runtime providers
GET /api/runtime/plugins/{name}?env=HCM         # Fetch a specific plugin provider's status
```

### SQR Source Artifact Intelligence

```text
GET  /api/sqr/stats
GET  /api/sqr/sources?env=HCM
GET  /api/sqr/programs?q=&type=sqr|sqc&env=HCM&page=1&per_page=50
GET  /api/sqr/program/{filename}
GET  /api/sqr/program/{filename}/source
GET  /api/sqr/table/{table_name}
GET  /api/sqr/sqc/{sqc_name}/users
GET  /api/sqr/deps/{filename}                   # Include dependency graph (forward + reverse)
GET  /api/sqr/envcompare?env_a=HCM&env_b=FSCM   # Side-by-side environment comparison
GET  /api/sqr/search?q=&type=&source_key=       # Full-text source search
GET  /api/sqr/overrides?env=HCM                 # Filenames present in both delivered and custom
POST /api/sqr/ingest                             # Trigger re-index (background)
GET  /api/sqr/ingest/status
```

### COBOL Source Artifact Intelligence

```text
GET  /api/cobol/stats
GET  /api/cobol/sources?env=HCM
GET  /api/cobol/programs?q=&type=program|copybook&env=HCM&page=1&per_page=50
GET  /api/cobol/program/{filename}
GET  /api/cobol/program/{filename}/source
GET  /api/cobol/table/{table_name}
GET  /api/cobol/deps/{filename}                 # COPY dependency graph (forward + reverse)
GET  /api/cobol/search?q=&type=&source_key=
POST /api/cobol/ingest
GET  /api/cobol/ingest/status
```

### Incident Recording

```text
POST   /api/incidents                    # Create incident (optionally capture RCA snapshot)
GET    /api/incidents?state=open|resolved&env=
GET    /api/incidents/{id}               # Get incident + all captured snapshots
PATCH  /api/incidents/{id}
DELETE /api/incidents/{id}
GET    /api/incidents/{id}/snapshot      # Re-run RCA and attach a fresh snapshot
```

### Transaction Tracing

```text
GET /api/tracing/config
GET /api/tracing/operators?env=HCM&q=
GET /api/tracing/active?env=HCM&limit=30
```

### Live Events

```text
GET /api/live/events
```

### SQL Workspace, Metadata, Object Explorer, Infrastructure

Additional APIs are exposed through the registered routers for:

```text
/api/sqlws/*
/api/metadata/*
/api/admin/*
/api/system/*
/api/nginx/*
/api/oracle/*
/api/peoplesoft/*
/api/topology/*
/api/record/*
/api/field/*
/api/role/*
/api/operator/*
/api/authelia/*
```

------------------------------------------------------------------------

## Log Intelligence

Phase 8 adds continuous ingestion, storage, and AI analysis of PeopleSoft
web server and application server logs.

### How it works

1. The background scheduler reads each enabled log source every 60 seconds
   via SSH/SFTP (or directly from disk for `"local"` sources).
2. Only new bytes since the last ingest are fetched — files are never re-read
   from the beginning.
3. Lines are parsed by format (PIA, APPSRV, Tuxedo, nginx, F5) and stored
   in `data/logs.db` (SQLite).
4. Errors (ORA- codes, HTTP 5xx, fatal messages) are extracted and stored
   separately in the `log_errors` table, deduplicated by `(source, ts, raw)`.

### Quick start

1. Fill in real SSH hosts in `config.json → ssh_hosts`
2. Add log source entries in `config.json → log_sources` with `"enabled": true`
3. Restart the server (or POST to `/api/logs/ingest` to trigger immediately)
4. Visit `/admin/logs` to see source status and ingest results

### Admin UI pages

| URL | Purpose |
|-----|---------|
| `/admin/logs` | Source overview — status, last ingest time, file count, errors |
| `/admin/log_errors` | Error surface — grouped by error code + object, sorted by frequency |
| `/admin/log_viewer` | Raw log browser — filter by user, component, level, time range |
| `/admin/log_session` | Session chain — correlates web + app logs for one OPRID |

### Asking the AI about logs

Once log sources are ingesting, the assistant at `/admin/assistant` can answer:

- "What errors are we seeing in HCM?" → uses `log_errors`
- "What was GUACUSER doing between 9am and 10am?" → uses `session_log_chain`
- "Are there any ORA-00942 errors?" → uses `log_errors`
- "Show me 500 errors in the web logs for the JOB_DATA component" → uses `log_search`
- "What objects are responsible for the most errors?" → uses `log_errors`

The AI also links error codes directly to PS metadata tools (`peoplecode_search`,
`record_usage`, `sql_lookup`) to suggest a diagnosis or further troubleshooting steps.

### Session chain correlation

The session chain (`/admin/log_session`) correlates web and app log entries
for a single OPRID by timestamp. It shows:

- Every component/page the user accessed (from web access logs)
- Everything the app server logged for them simultaneously (ORA- errors, PC errors, state record loads)
- A link directly to Transaction Tracing for the same OPRID

This is the fastest path from "a user is having a problem" to understanding exactly
what failed and what object is responsible.

------------------------------------------------------------------------

## Knowledge Graph

Build:

``` bash
curl "http://127.0.0.1:8088/api/graph/build?env=HCM"
```

Output:

``` text
/opt/deathstar-api/data/
```

------------------------------------------------------------------------

## Plugin SDK

Add custom object providers, Knowledge Graph builders, runtime status providers,
health checks, config-driven ingest sources, and admin dashboard pages without
editing any core file. Drop a Python module into `plugins/` (e.g.
`plugins/my_plugin.py`) exposing a `register(sdk)` function; it's discovered and
loaded automatically at startup, with per-plugin failure isolation — a broken plugin
is logged and skipped, never crashes the server or other plugins.

```python
def register(sdk):
    sdk.register_object_provider("my_type", my_object_fn, my_payload_fn, registry_meta={...})
    sdk.register_graph_provider("my_provider", my_graph_loader)
    sdk.register_runtime_provider("my_status", my_fetch_fn, label="My Status")
    sdk.register_health_check("my_check", my_check_fn, label="My Health Check")
    sdk.register_source_type("my_source", "my_sources", my_ingest_fn, status_fn=my_status_fn)
    sdk.register_nav_entry("My Group", "my_page", "My Page", "/admin/plugin/my-page")
    sdk.register_router(my_fastapi_router)
```

See `PLUGINS.md` for the full walkthrough of all six extension points and
`plugins/example_hello.py` for a complete worked example.

------------------------------------------------------------------------

## nginx Reverse Proxy

``` nginx
location /api/ {
    proxy_pass http://127.0.0.1:8088/api/;
}
```

------------------------------------------------------------------------

## Security

-   Use read-only Oracle accounts.
-   Protect config.json.
-   Place authentication in front of the API.
-   Avoid exposing the API directly to the Internet.

------------------------------------------------------------------------

## Development Workflow

Always keep the following synchronized:

-   ARCHITECTURE.md — design rules, subsystem boundaries, provider contracts
-   ROADMAP.md — current status and remaining work only
-   DEVELOPMENT_DIARY.md — dated narrative: what changed, why, how it was verified
-   PLUGINS.md — Plugin SDK docs; update when `connectors/plugins.py`'s registries change

------------------------------------------------------------------------

## Troubleshooting

View service logs:

``` bash
journalctl -u deathstar-api -f
```

Run manually:

``` bash
uvicorn main:app --reload
```

------------------------------------------------------------------------

## License

Apache-2.0 for permissive use with explicit patent protections

------------------------------------------------------------------------

## Disclaimer

PeopleSoft Hypergraph Intelligence is an independent administration and diagnostics
platform and is not affiliated with Oracle.
