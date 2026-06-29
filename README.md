# PeopleSoft Explorer

PeopleSoft Explorer is a read-only observability and exploration
platform for PeopleSoft environments.

It is designed to help administrators and developers inspect PeopleSoft
metadata, Integration Broker configuration, transaction activity, logs,
nginx traffic, Oracle connectivity, and environment topology from a
single API-driven interface.

The project is intentionally built around **read-only access** wherever
possible.

------------------------------------------------------------------------

## Goals

PeopleSoft Explorer provides:

-   Environment-aware PeopleSoft inspection
-   Oracle-backed metadata queries
-   Integration Broker discovery
-   Transaction tracing
-   Knowledge graph generation
-   Log exploration
-   nginx / reverse proxy visibility
-   Multi-environment support for HCM, FSCM, and future PeopleSoft
    pillars
-   A foundation for AI-assisted PeopleSoft troubleshooting

------------------------------------------------------------------------

## Project Structure

``` text
deathstar-api/
├── main.py
├── config.json
├── connectors/
│   ├── oracle.py
│   ├── execution.py
│   ├── ib.py
│   ├── tracing.py
│   ├── nginx.py
│   └── system.py
├── routers/
│   ├── graph.py
│   ├── ib.py
│   ├── tracing.py
│   ├── live.py
│   └── ...
├── data/
│   ├── knowledge_graph_HCM.json
│   └── knowledge_graph_FSCM.json
├── static/
├── requirements.txt
├── ARCHITECTURE.md
├── ROADMAP.md
└── DEVELOPMENT_DIARY.md
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
http://localhost:8088/docs
```

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

``` text
GET /docs

GET /api/graph/build?env=HCM
GET /api/graph/build?env=FSCM

GET /api/tracing/config
GET /api/tracing/operators
GET /api/tracing/active

GET /api/live/events

GET /api/ib/nodes
GET /api/ib/services
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

PeopleSoft Explorer is an independent administration and diagnostics
platform and is not affiliated with Oracle.