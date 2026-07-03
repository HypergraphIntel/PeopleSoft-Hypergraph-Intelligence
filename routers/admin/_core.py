import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["DeathStar Admin"])

# ── Navigation groups (dropdown nav) ──────────────────────────────────────
# Each entry: (group_label, items)
# group_label=None → direct link,  items=[("key","Label","/href")]
# group_label=str  → dropdown,     items=[("key","Label","/href"), ...]
_NAV_GROUPS = [
    (None, [("home", "Home", "/admin/")]),
    ("Runtime", [
        ("runtime",    "Runtime",       "/admin/runtime"),
        ("infra",      "Infra",         "/admin/infra"),
        ("topology",   "Topology",      "/admin/topology"),
        ("tracing",    "Tracing",       "/admin/tracing"),
        ("envcompare", "Env Compare",   "/admin/envcompare"),
        ("drift",       "Drift History",  "/admin/drift"),
        ("promotions",  "Promotions",     "/admin/promotions"),
        ("logs",        "Logs",           "/admin/logs"),
        ("log_errors",  "Log Errors",     "/admin/log_errors"),
        ("igw",         "IGW Errors",     "/admin/igw"),
        ("prcs_ae",     "PRCS AE Logs",   "/admin/prcs-ae"),
        ("rca",         "Incident RCA",   "/admin/rca"),
    ]),
    ("Data", [
        ("sqlws",  "SQL Workspace",  "/admin/sqlws"),
        ("query",  "Queries",        "/admin/query"),
        ("conqrs", "Conn. Queries",  "/admin/conqrs"),
    ]),
    ("Integration", [
        ("ib",        "IB Explorer",   "/admin/ib"),
        ("ibmessage", "IB Messages",   "/admin/ibmessage"),
        ("ibapp",     "IB App Svcs",   "/admin/ibapp"),
        ("ibsvcgrp",  "IB Svc Groups", "/admin/ibsvcgrp"),
        ("ibrtng",    "IB Routings",   "/admin/ibrtng"),
        ("iboper",    "IB Operations", "/admin/iboper"),
    ]),
    ("Security", [
        ("secaudit",       "Security Audit",  "/admin/secaudit"),
        ("security",       "Security",        "/admin/security"),
        ("operator",       "Operators",       "/admin/operator"),
        ("role",           "Roles",           "/admin/role"),
        ("permissionlist", "Perm Lists",      "/admin/permissionlist"),
    ]),
    ("Objects", [
        ("objects",        "Object Search",   "/admin/objects"),
        ("component",      "Components",      "/admin/component"),
        ("page",           "Pages",           "/admin/page"),
        ("ci",             "CIs",             "/admin/ci"),
        ("tree",     "Trees",          "/admin/tree"),
        ("menu",     "Menus",          "/admin/menu"),
        ("appclass", "App Classes",    "/admin/appclass"),
        ("adsdef",   "ADS Defs",       "/admin/adsdef"),
        ("cbskill",  "Chatbot Skills", "/admin/cbskill"),
        ("approval", "Approvals",      "/admin/approval"),
        ("contsvc",  "Content Svcs",   "/admin/contsvc"),
        ("urldef",   "URL Defs",       "/admin/urldef"),
    ]),
    ("Portal", [
        ("navcoll",    "Nav Collections", "/admin/navcoll"),
        ("relcontent", "Related Content", "/admin/relcontent"),
        ("efmapping",  "Event Mapping",   "/admin/efmapping"),
        ("dropzone",   "Drop Zones",      "/admin/dropzone"),
        ("pivotgrid",  "PivotGrids",      "/admin/pivotgrid"),
        ("srchdef",    "Search Defs",     "/admin/srchdef"),
        ("srchcat",    "Search Cats",     "/admin/srchcat"),
        ("xpub",       "XML Publisher",   "/admin/xpub"),
        ("stylesheet", "Style Sheets",    "/admin/stylesheet"),
        ("pcsearch",   "PC Search",       "/admin/pcsearch"),
    ]),
    ("Platform", [
        ("whatchanged","What Changed", "/admin/whatchanged"),
        ("prcsdefn",   "Processes",    "/admin/prcsdefn"),
        ("ae",         "AE Programs",  "/admin/ae"),
        ("filelayout", "File Layouts", "/admin/filelayout"),
        ("xlat",       "Translate",    "/admin/xlat"),
        ("project",    "Projects",     "/admin/project"),
        ("msgcat",     "Messages",     "/admin/msgcat"),
        ("archobj",    "Archive Objs", "/admin/archobj"),
        ("timezone",   "Timezones",    "/admin/timezone"),
        ("locale",     "Locales",      "/admin/locale"),
        ("ptftest",    "PTF Tests",    "/admin/ptftest"),
        ("sqr",        "SQR Explorer",  "/admin/sqr"),
        ("sqrsearch",  "SQR Search",    "/admin/sqrsearch"),
        ("compflow",   "Comp Event Flow", "/admin/compflow"),
    ]),
    ("Perf", [
        ("pmmetric", "PM Metrics",      "/admin/pmmetric"),
        ("pmtrans",  "PM Transactions", "/admin/pmtrans"),
        ("pmevent",  "PM Events",       "/admin/pmevent"),
    ]),
    ("Tools", [
        ("reports", "Reports",    "/admin/reports"),
        ("tools",   "Tools",      "/admin/tools"),
        ("impact",     "Impact",     "/admin/impact"),
        ("assistant",  "Assistant",  "/admin/assistant"),
        ("docs",       "Docs",       "/admin/docs"),
    ]),
    (None, [("users", "Users", "/admin/users")]),
]

# CSS block embedded inline in standalone pages (no app.css available).
_NAV_CSS = (
    "<style>"
    "nav.ds-nav{position:sticky;top:0;z-index:9999;display:flex;align-items:center;"
    "gap:2px;height:42px;padding:0 14px;background:rgba(3,8,18,.97);"
    "border-bottom:1px solid rgba(0,229,255,.25);box-shadow:0 4px 16px rgba(0,0,0,.4);"
    "flex-shrink:0}"
    ".ds-brand{display:flex;align-items:center;gap:8px;color:#00e5ff;font-weight:700;"
    "font-size:13px;letter-spacing:.5px;text-decoration:none;white-space:nowrap;"
    "margin-right:10px}"
    ".ds-brand:hover{text-decoration:none;color:#00e5ff}"
    ".ds-brand-logo{width:24px;height:24px;display:block;flex:0 0 24px;object-fit:contain;"
    "filter:drop-shadow(0 0 6px rgba(0,229,255,.55))}"
    ".ds-brand-title{color:#00e5ff}"
    ".ds-nav-link{color:#7faab2;font-size:12px;padding:5px 9px;border-radius:4px;"
    "text-decoration:none;border:1px solid transparent;white-space:nowrap;"
    "transition:color .15s,border-color .15s}"
    ".ds-nav-link:hover,.ds-nav-link.ds-active{color:#00e5ff;"
    "border-color:rgba(0,229,255,.3);text-decoration:none}"
    ".ds-nav-group{position:relative;display:flex;align-items:center}"
    ".ds-nav-grouplbl{color:#7faab2;font-size:12px;padding:5px 9px;border-radius:4px;"
    "border:1px solid transparent;white-space:nowrap;cursor:default;"
    "transition:color .15s,border-color .15s;user-select:none;line-height:1}"
    ".ds-nav-group:hover>.ds-nav-grouplbl,.ds-nav-group.ds-active>.ds-nav-grouplbl"
    "{color:#00e5ff;border-color:rgba(0,229,255,.3)}"
    ".ds-nav-dropdown{display:none;position:absolute;top:calc(100% + 1px);left:0;"
    "background:rgba(3,8,18,.98);border:1px solid rgba(0,229,255,.25);border-radius:4px;"
    "min-width:160px;padding:4px 0;z-index:10000;flex-direction:column;"
    "box-shadow:0 8px 24px rgba(0,0,0,.5)}"
    ".ds-nav-group:hover>.ds-nav-dropdown{display:flex}"
    ".ds-nav-drop-link{color:#7faab2;font-size:12px;padding:6px 14px;text-decoration:none;"
    "white-space:nowrap;transition:color .15s,background .15s}"
    ".ds-nav-drop-link:hover,.ds-nav-drop-link.ds-active{color:#00e5ff;"
    "background:rgba(0,229,255,.07);text-decoration:none}"
    ".ds-env{display:flex;align-items:center;gap:6px;margin-left:auto}"
    ".ds-env-lbl{font-size:11px;color:#7faab2}"
    ".ds-env-sel{background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.25);"
    "color:#d7faff;font-size:12px;padding:3px 8px;border-radius:4px}"
    "</style>"
)


def _nav_html(active: str, env: str = None) -> str:
    links = ""
    for group_label, items in _NAV_GROUPS:
        if group_label is None:
            key, label, href = items[0]
            cls = "ds-nav-link ds-active" if key == active else "ds-nav-link"
            links += f'<a class="{cls}" href="{href}">{label}</a>'
        else:
            group_active = any(item[0] == active for item in items)
            gcls = "ds-nav-group ds-active" if group_active else "ds-nav-group"
            drops = ""
            for key, label, href in items:
                dcls = "ds-nav-drop-link ds-active" if key == active else "ds-nav-drop-link"
                drops += f'<a class="{dcls}" href="{href}">{label}</a>'
            links += (f'<div class="{gcls}">'
                      f'<span class="ds-nav-grouplbl">{group_label} &#9660;</span>'
                      f'<div class="ds-nav-dropdown">{drops}</div>'
                      f'</div>')
    right = (
        f'<span style="margin-left:auto;font-size:11px;color:#7faab2;'
        f'background:rgba(0,229,255,.06);border:1px solid rgba(0,229,255,.18);'
        f'border-radius:3px;padding:2px 8px">{env}</span>'
        if env else '<span style="margin-left:auto"></span>'
    )
    return (f'<nav class="ds-nav">'
            f'<a class="ds-brand" href="/admin/">'
            f'<img src="/static/images/empire_logo_sith_cyan.svg"'
            f' class="ds-brand-logo" alt="PeopleSoft Hypergraph Intelligence">'
            f'<span class="ds-brand-title">PeopleSoft Hypergraph Intelligence</span>'
            f'</a>'
            f'{links}'
            f'{right}'
            f'</nav>')

# JS helper embedded in standalone page <script> blocks (no app.js available).
_ESC_JS = "function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}"


def _shell(title: str, active: str, content: str, env: bool = True, noscroll: bool = False) -> str:
    """Render a complete HTML page with the standard grouped-dropdown shell."""
    nav = _nav_html(active)

    env_html = ""
    if env:
        env_html = (
            '<div class="ds-env">'
            '<span class="ds-env-lbl">Env</span>'
            '<select class="ds-env-sel" id="globalEnv"></select>'
            '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DeathStar — {title}</title>
<link rel="icon" type="image/svg+xml" href="/static/images/empire_logo_sith_cyan.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/static/images/favicon-32.png">
<link rel="apple-touch-icon" href="/static/images/apple-touch-icon.png">
<link rel="stylesheet" href="/static/app.css?v=2">
<script src="/static/app.js?v=2"></script>
</head>
<body>
{nav}
<div class="ds-page-hdr">
  <span class="ds-page-title">{title}</span>
  {env_html}
</div>
<div class="{'ds-content ds-noscroll' if noscroll else 'ds-content'}">
{content}
</div>
</body>
</html>"""


