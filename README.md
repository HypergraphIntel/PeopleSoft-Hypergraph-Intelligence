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
-   A foundation for AI-assisted PeopleSoft troubleshooting

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
├── PHASE2.md                       # Phase planning notes
├── config/
│   └── role_mapping.yml            # PeopleSoft role → Authelia group mapping
├── connectors/
│   ├── ae.py                       # Application Engine metadata/runtime helpers
│   ├── alerts.py                   # Runtime alert checks
│   ├── envcompare.py               # Cross-environment comparison logic
│   ├── execution.py                # Oracle execution/runtime queries
│   ├── graphdb.py                  # Knowledge graph store and dependency graph logic
│   ├── ib.py                       # Integration Broker metadata/runtime discovery
│   ├── nginx.py                    # nginx log/status helpers
│   ├── oracle.py                   # Oracle connectivity helpers
│   ├── peoplecode.py               # PeopleCode decoding/source helpers
│   ├── peoplesoft.py               # PeopleSoft environment helpers
│   ├── psdb.py                     # Core PeopleSoft DB metadata access
│   ├── ptmetadata.py               # PeopleTools/version-aware metadata discovery
│   ├── scheduler.py                # Background graph snapshot scheduling
│   ├── sqlws.py                    # SQL Workspace backend helpers
│   ├── system.py                   # Host/service/container/log management
│   ├── tracing.py                  # Transaction tracing helpers
│   └── uom.py                      # Unified Object Model providers
├── routers/
│   ├── admin/                      # Admin UI package (split 2026-07-01)
│   │   ├── __init__.py             #   Re-exports router; triggers sub-module imports
│   │   ├── _core.py                #   Shared: router obj, nav groups, _shell, _nav_html, CSS/JS
│   │   ├── home.py                 #   /, /users
│   │   ├── security.py             #   /security, /record, /field, /operator, /role, /peoplecode
│   │   ├── graph.py                #   /graph, /object, /portal, /metadata, /graphdb
│   │   ├── runtime.py              #   /runtime, /infra, /tracing, /envcompare
│   │   ├── data.py                 #   /sqlws, /query, /conqrs
│   │   ├── integration.py          #   /ib, /ibmessage, /ibapp, /ibsvcgrp, /ibrtng, /iboper
│   │   ├── objects.py              #   /ci, /tree, /menu, /appclass, /adsdef, /cbskill, /approval, /contsvc, /urldef
│   │   ├── portal.py               #   /navcoll, /relcontent, /efmapping, /dropzone, /pivotgrid, /srchdef, /srchcat, /xpub, /stylesheet, /pcsearch
│   │   ├── platform.py             #   /prcsdefn, /filelayout, /xlat, /project, /msgcat, /archobj, /timezone, /locale, /ptftest
│   │   ├── perf.py                 #   /pmmetric, /pmtrans, /pmevent
│   │   └── tools.py                #   /reports, /tools, /docs
│   ├── authelia_admin.py           # Authelia user/group administration
│   ├── envcompare.py               # Environment comparison API
│   ├── field.py                    # Field metadata API
│   ├── graphdb.py                  # Knowledge graph API
│   ├── health.py                   # Health/status API
│   ├── ib.py                       # Integration Broker API
│   ├── identity.py                 # PeopleSoft → Authelia identity workflow
│   ├── live.py                     # Live event stream API
│   ├── metadata.py                 # Metadata/version/relationship APIs
│   ├── nginx.py                    # nginx API
│   ├── operator.py                 # Operator/OPRID API
│   ├── oracle.py                   # Oracle connectivity API
│   ├── peoplesoft.py               # PeopleSoft environment API
│   ├── record.py                   # Record metadata API
│   ├── role.py                     # Role/security API
│   ├── runtime.py                  # Runtime Monitor, ASH, domains, alerts
│   ├── sqlws.py                    # SQL Workspace API
│   ├── system.py                   # Infrastructure/service/container API
│   ├── topology.py                 # Environment topology API
│   └── tracing.py                  # Transaction tracing API
├── data/
│   ├── knowledge_graph_HCM.json    # Generated graph snapshot/cache
│   └── knowledge_graph_FSCM.json   # Generated graph snapshot/cache
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
-   Optional access to nginx logs
-   Optional SSH/SFTP access to remote PeopleSoft tiers

### Python Requirements

Install dependencies:

``` bash
pip install -r requirements.txt
```

Typical dependencies include:

``` text
fastapi
uvicorn
oracledb
pydantic
python-dotenv
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

Create:

``` text
/opt/deathstar-api/config.json
```

Populate it with your Oracle environments, log sources, and nginx log
locations.

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
GET /api/envcompare/peoplecode?env1=HCM&env2=FSCM&q=
GET /api/envcompare/peoplecode-source?env1=HCM&env2=FSCM&ref={encoded_ref}
GET /api/envcompare/sql_definitions?env1=HCM&env2=FSCM&q=
GET /api/envcompare/queries?env1=HCM&env2=FSCM&q=
GET /api/envcompare/portals?env1=HCM&env2=FSCM&q=
GET /api/envcompare/portal-object?env1=HCM&env2=FSCM&name={PORTAL_OBJNAME}
GET /api/envcompare/graph?env1=HCM&env2=FSCM
```

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

-   ARCHITECTURE.md
-   ROADMAP.md
-   DEVELOPMENT_DIARY.md

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
