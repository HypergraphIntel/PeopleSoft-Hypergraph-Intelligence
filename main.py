from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from connectors import scheduler
from routers import health
from routers import nginx
from routers import system
from routers import topology
from routers import oracle
from routers import peoplesoft
from routers import live
from routers import authelia_admin
from routers import admin
from routers import identity
from routers import metadata
from routers import graphdb
from routers import runtime
from routers import sqlws
from routers import ib
from routers import envcompare
from routers import drift
from routers import impact_api
from routers import promotions
from routers import assistant
from routers import tracing
from routers import record
from routers import field
from routers import role
from routers import operator
from routers import logs as logs_api
from routers.admin import logs as admin_logs

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="DeathStar Operations API", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _inject_frontend_shell(html: str) -> str:
    if "/static/app.css" not in html:
        html = html.replace(
            "</head>",
            '    <link rel="stylesheet" href="/static/app.css">\n</head>',
            1,
        )
    if "/static/app.js" not in html:
        html = html.replace(
            "</body>",
            '    <script src="/static/app.js" defer></script>\n</body>',
            1,
        )
    return html


@app.middleware("http")
async def frontend_shell_middleware(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")

    if "text/html" not in content_type:
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    text = body.decode("utf-8")
    text = _inject_frontend_shell(text)
    headers = dict(response.headers)
    headers.pop("content-length", None)
    headers.pop("content-encoding", None)

    return Response(
        content=text,
        status_code=response.status_code,
        headers=headers,
        media_type="text/html",
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/images/favicon-32.png")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(health.router)
app.include_router(nginx.router)
app.include_router(system.router)
app.include_router(topology.router)
app.include_router(oracle.router)
app.include_router(peoplesoft.router)
app.include_router(live.router)
app.include_router(authelia_admin.router)
app.include_router(admin.router)
app.include_router(identity.router)
app.include_router(metadata.router)
app.include_router(graphdb.router)
app.include_router(runtime.router)
app.include_router(sqlws.router)
app.include_router(ib.router)
app.include_router(envcompare.router)
app.include_router(drift.router)
app.include_router(impact_api.router)
app.include_router(promotions.router)
app.include_router(assistant.router)
app.include_router(tracing.router)
app.include_router(record.router)
app.include_router(field.router)
app.include_router(role.router)
app.include_router(operator.router)
app.include_router(logs_api.router)
app.include_router(admin_logs.router)
