"""
Admin UI for Phase 8 Log Intelligence.

/admin/logs           — sources overview + quick stats
/admin/log_errors     — error surface grouped by error_code + object_ref
/admin/log_viewer     — web / app log viewer with filters
/admin/log_session    — session chain (web→app) for a specific OPRID
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from typing import Optional

from routers.admin._core import _shell, _ESC_JS

router = APIRouter(prefix="/admin", tags=["Logs UI"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _logdb():
    from connectors import logdb
    logdb.init_db()
    return logdb


# ---------------------------------------------------------------------------
# /admin/logs  — source overview
# ---------------------------------------------------------------------------

@router.get("/logs", response_class=HTMLResponse)
def logs_overview(request: Request):
    db = _logdb()
    sources = db.get_sources(enabled_only=False)

    rows_html = ""
    for s in sources:
        offsets = s.get("offsets", "{}")
        try:
            import json
            off = json.loads(offsets) if isinstance(offsets, str) else offsets
            file_count = len(off)
        except Exception:
            file_count = 0

        status_dot = (
            '<span style="color:#00e5ff">●</span>' if s["enabled"]
            else '<span style="color:#555">●</span>'
        )
        error_badge = (
            f'<span style="color:#ff6b6b;font-size:11px">{s["error_msg"][:60]}</span>'
            if s.get("error_msg") else ""
        )
        rows_html += f"""
        <tr>
          <td>{status_dot} {s['name']}</td>
          <td><code>{s['type']}</code></td>
          <td>{s['env']}</td>
          <td>{s['ssh_host']}</td>
          <td style="font-size:11px;color:#7faab2;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
              title="{s['path']}">{s['path']}</td>
          <td style="text-align:center">{file_count}</td>
          <td style="font-size:11px;color:#7faab2">{s.get('last_ingest') or '—'}</td>
          <td>{error_badge}</td>
        </tr>"""

    if not sources:
        rows_html = '<tr><td colspan="8" style="color:#555;text-align:center;padding:24px">No log sources configured. Add entries to config.json → log_sources</td></tr>'

    content = f"""
<style>
.log-table{{width:100%;border-collapse:collapse;font-size:13px}}
.log-table th{{text-align:left;padding:8px 10px;border-bottom:1px solid rgba(0,229,255,.2);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.log-table td{{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}}
.log-table tr:hover td{{background:rgba(0,229,255,.04)}}
.ql-nav{{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}}
.ql-btn{{padding:7px 14px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;text-decoration:none}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
</style>

<div class="ql-nav">
  <a class="ql-btn" href="/admin/log_errors">Error Surface</a>
  <a class="ql-btn" href="/admin/log_viewer">Log Viewer</a>
  <a class="ql-btn" href="/admin/log_session">Session Chain</a>
  <button class="ql-btn" onclick="triggerIngest()" id="ingest-btn">Trigger Ingest Now</button>
</div>

<h3 style="color:#d7faff;margin:0 0 12px 0;font-size:14px">Log Sources</h3>
<p style="color:#7faab2;font-size:12px;margin:0 0 14px 0">
  Configure sources in <code>config.json → log_sources</code>.
  The ingest scheduler runs every 60 seconds and only reads new bytes since last run.
</p>

<table class="log-table">
  <thead>
    <tr>
      <th>Name</th><th>Type</th><th>Env</th><th>SSH Host</th><th>Path</th>
      <th>Files tracked</th><th>Last Ingest</th><th>Error</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<script>
function triggerIngest() {{
  var btn = document.getElementById('ingest-btn');
  btn.textContent = 'Ingesting…';
  btn.disabled = true;
  fetch('/api/logs/ingest', {{method:'POST'}}).then(r => r.json()).then(function(d) {{
    btn.textContent = 'Ingest started ✓';
    setTimeout(function(){{ btn.textContent='Trigger Ingest Now'; btn.disabled=false; }}, 3000);
  }}).catch(function(e){{ btn.textContent='Error'; btn.disabled=false; }});
}}
</script>
"""
    return HTMLResponse(_shell("Logs", "logs", content))


# ---------------------------------------------------------------------------
# /admin/log_errors  — error surface
# ---------------------------------------------------------------------------

@router.get("/log_errors", response_class=HTMLResponse)
def log_errors_view(request: Request, env: Optional[str] = None):
    db = _logdb()

    # get configured envs for the filter dropdown
    import json
    cfg_path = __import__("pathlib").Path(__file__).parent.parent.parent / "config.json"
    try:
        envs = [e["name"] for e in json.loads(cfg_path.read_text()).get("peoplesoft", {}).get("environments", [])]
    except Exception:
        envs = []

    groups = db.error_summary(env=env, limit=100)

    env_opts = "".join(
        f'<option value="{e}" {"selected" if e==env else ""}>{e}</option>'
        for e in envs
    )
    env_filter = f"""
    <select id="env-sel" onchange="applyEnv()" style="background:rgba(0,20,30,.88);border:1px solid
      rgba(0,229,255,.25);color:#d7faff;font-size:12px;padding:4px 8px;border-radius:4px">
      <option value="">All Envs</option>{env_opts}
    </select>"""

    rows_html = ""
    for g in groups:
        ec = g["error_code"] or "—"
        obj = g["object_ref"] or "—"
        obj_link = (
            f'<a href="/admin/record/{obj}?env={env or ""}" '
            f'style="color:#00e5ff" target="_blank">{obj}</a>'
            if g["object_ref"] else "—"
        )
        oprids = (g.get("oprids_sample") or "").split(",")[:3]
        oprid_links = " ".join(
            f'<a href="/admin/tracing?oprid={o}&env={env or ""}" style="color:#00e5ff;font-size:11px" target="_blank">{o}</a>'
            for o in oprids if o.strip()
        )
        rows_html += f"""
        <tr>
          <td style="color:#ff6b6b;font-weight:600">{ec}</td>
          <td>{obj_link}</td>
          <td>{g['env']}</td>
          <td style="text-align:center;font-weight:700;color:#ffd700">{g['cnt']}</td>
          <td style="font-size:11px;color:#7faab2">{g['first_seen']}</td>
          <td style="font-size:11px;color:#7faab2">{g['last_seen']}</td>
          <td style="text-align:center">{g['unique_users']}</td>
          <td style="font-size:11px">{oprid_links}</td>
          <td>
            <a href="/admin/assistant?q=Diagnose+{ec}+on+object+{obj or 'unknown'}&env={g['env']}"
               class="ql-btn" style="font-size:11px;padding:3px 8px" target="_blank">Ask AI</a>
            <a href="/admin/log_viewer?error_code={ec}&env={g['env']}"
               class="ql-btn" style="font-size:11px;padding:3px 8px">View Logs</a>
          </td>
        </tr>"""

    if not groups:
        rows_html = '<tr><td colspan="9" style="color:#555;text-align:center;padding:24px">No errors recorded yet. Configure log sources and wait for ingestion.</td></tr>'

    content = f"""
<style>
.log-table{{width:100%;border-collapse:collapse;font-size:13px}}
.log-table th{{text-align:left;padding:8px 10px;border-bottom:1px solid rgba(0,229,255,.2);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.log-table td{{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}}
.log-table tr:hover td{{background:rgba(0,229,255,.04)}}
.ql-btn{{padding:7px 14px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;text-decoration:none;
  display:inline-block;cursor:pointer}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
</style>

<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <h3 style="color:#d7faff;margin:0;font-size:14px">Error Surface</h3>
  {env_filter}
  <a class="ql-btn" href="/admin/logs" style="font-size:12px;padding:5px 12px">← Sources</a>
  <a class="ql-btn" href="/admin/log_viewer" style="font-size:12px;padding:5px 12px">Log Viewer</a>
</div>
<p style="color:#7faab2;font-size:12px;margin:0 0 14px 0">
  Grouped by error code + object. Click <strong style="color:#00e5ff">Ask AI</strong> to send the error to the assistant for diagnosis.
</p>

<table class="log-table">
  <thead>
    <tr>
      <th>Error Code</th><th>Object</th><th>Env</th><th>Count</th>
      <th>First Seen</th><th>Last Seen</th><th>Users</th><th>Sample Users</th><th>Actions</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<script>
function applyEnv() {{
  var e = document.getElementById('env-sel').value;
  window.location = '/admin/log_errors' + (e ? '?env=' + e : '');
}}
</script>
"""
    return HTMLResponse(_shell("Log Errors", "log_errors", content))


# ---------------------------------------------------------------------------
# /admin/log_viewer  — raw log browser
# ---------------------------------------------------------------------------

@router.get("/log_viewer", response_class=HTMLResponse)
def log_viewer(
    request: Request,
    env: Optional[str] = None,
    tier: str = "web",
    oprid: Optional[str] = None,
    component: Optional[str] = None,
    error_code: Optional[str] = None,
    errors_only: bool = False,
    limit: int = 200,
):
    db = _logdb()

    import json
    cfg_path = __import__("pathlib").Path(__file__).parent.parent.parent / "config.json"
    try:
        envs = [e["name"] for e in json.loads(cfg_path.read_text()).get("peoplesoft", {}).get("environments", [])]
    except Exception:
        envs = []

    # Fetch rows
    if tier == "app":
        rows = db.query_app(env=env, oprid=oprid, errors_only=errors_only, limit=limit)
    elif tier == "errors":
        rows = db.query_errors(env=env, error_code=error_code, oprid=oprid, limit=limit)
    else:
        rows = db.query_web(env=env, oprid=oprid, component=component,
                            errors_only=errors_only, limit=limit)

    # Build table
    if tier == "web":
        headers = ["Timestamp", "OPRID", "Method", "Status", "Component", "Page", "MS", "IP"]
        def row_cells(r):
            status = r.get("status") or 0
            sc = "color:#ff6b6b" if status >= 500 else ("color:#ffd700" if status >= 400 else "color:#7faab2")
            oprid_v = r.get("oprid") or "—"
            oprid_link = (
                f'<a href="/admin/tracing?oprid={oprid_v}&env={r.get("env","")}" '
                f'style="color:#00e5ff" target="_blank">{oprid_v}</a>'
                if oprid_v != "—" else "—"
            )
            comp = r.get("component") or "—"
            comp_link = (
                f'<a href="/admin/object/component/{comp}?env={r.get("env","")}" '
                f'style="color:#00e5ff" target="_blank">{comp}</a>'
                if comp != "—" else "—"
            )
            return (
                f'<td style="font-size:11px;color:#7faab2">{r.get("ts","")[:19]}</td>'
                f'<td>{oprid_link}</td>'
                f'<td style="font-size:11px">{r.get("method","")}</td>'
                f'<td style="{sc};font-weight:600">{status}</td>'
                f'<td>{comp_link}</td>'
                f'<td style="font-size:11px;color:#7faab2">{r.get("page") or "—"}</td>'
                f'<td style="font-size:11px;color:#7faab2">{r.get("ms") or "—"}</td>'
                f'<td style="font-size:11px;color:#555">{r.get("ip") or "—"}</td>'
            )
    elif tier == "app":
        headers = ["Timestamp", "Level", "OPRID", "Object", "Message"]
        def row_cells(r):
            level = r.get("level") or "INFO"
            lc = "color:#ff6b6b" if level == "ERROR" else "color:#ffd700" if level == "WARN" else "color:#7faab2"
            oprid_v = r.get("oprid") or "—"
            oprid_link = (
                f'<a href="/admin/tracing?oprid={oprid_v}&env={r.get("env","")}" '
                f'style="color:#00e5ff" target="_blank">{oprid_v}</a>'
                if oprid_v != "—" else "—"
            )
            obj = r.get("object_ref") or "—"
            return (
                f'<td style="font-size:11px;color:#7faab2">{r.get("ts","")[:19]}</td>'
                f'<td style="{lc};font-weight:600;font-size:11px">{level}</td>'
                f'<td>{oprid_link}</td>'
                f'<td style="font-size:11px;color:#00e5ff">{obj}</td>'
                f'<td style="font-size:11px;color:#d7faff;max-width:500px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap" title="{r.get("message","")}">'
                f'{(r.get("message") or "")[:200]}</td>'
            )
    else:  # errors
        headers = ["Timestamp", "Code", "Object", "OPRID", "Level", "Message"]
        def row_cells(r):
            ec = r.get("error_code") or "—"
            obj = r.get("object_ref") or "—"
            oprid_v = r.get("oprid") or "—"
            return (
                f'<td style="font-size:11px;color:#7faab2">{r.get("ts","")[:19]}</td>'
                f'<td style="color:#ff6b6b;font-weight:600">{ec}</td>'
                f'<td style="color:#00e5ff">{obj}</td>'
                f'<td style="color:#00e5ff">{oprid_v}</td>'
                f'<td style="font-size:11px">{r.get("level","")}</td>'
                f'<td style="font-size:11px;color:#d7faff;max-width:400px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap" title="{r.get("message","")}">'
                f'{(r.get("message") or "")[:200]}</td>'
            )

    thead = "".join(f'<th>{h}</th>' for h in headers)
    tbody = ""
    for r in rows:
        tbody += f'<tr>{row_cells(r)}</tr>'
    if not tbody:
        tbody = f'<tr><td colspan="{len(headers)}" style="color:#555;text-align:center;padding:24px">No entries found.</td></tr>'

    env_opts = "".join(
        f'<option value="{e}" {"selected" if e==env else ""}>{e}</option>'
        for e in envs
    )

    tier_opts = "".join(
        f'<option value="{t}" {"selected" if t==tier else ""}>{l}</option>'
        for t, l in [("web","Web Access"),("app","App Server"),("errors","Errors")]
    )

    content = f"""
<style>
.log-table{{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}}
.log-table th{{text-align:left;padding:7px 8px;border-bottom:1px solid rgba(0,229,255,.2);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.log-table td{{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.03);vertical-align:middle}}
.log-table tr:hover td{{background:rgba(0,229,255,.04)}}
.lv-filter{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}}
.lv-inp{{background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.25);color:#d7faff;
  font-size:12px;padding:4px 8px;border-radius:4px}}
.ql-btn{{padding:6px 12px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;text-decoration:none;cursor:pointer}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
</style>

<div class="lv-filter">
  <a class="ql-btn" href="/admin/logs" style="font-size:12px;padding:4px 10px">← Sources</a>
  <select class="lv-inp" id="f-tier"><option value="">Tier</option>{tier_opts}</select>
  <select class="lv-inp" id="f-env"><option value="">All Envs</option>{env_opts}</select>
  <input class="lv-inp" id="f-oprid" placeholder="OPRID" value="{oprid or ''}" style="width:120px">
  <input class="lv-inp" id="f-component" placeholder="Component" value="{component or ''}" style="width:150px">
  <input class="lv-inp" id="f-errcode" placeholder="Error Code" value="{error_code or ''}" style="width:120px">
  <label style="color:#7faab2;font-size:12px">
    <input type="checkbox" id="f-erronly" {"checked" if errors_only else ""}> Errors only
  </label>
  <select class="lv-inp" id="f-limit">
    {"".join(f'<option value="{n}" {"selected" if n==limit else ""}>{n} rows</option>' for n in [100,200,500,1000])}
  </select>
  <button class="ql-btn" onclick="applyFilter()">Apply</button>
</div>

<div style="color:#7faab2;font-size:11px;margin-bottom:8px">{len(rows)} rows</div>
<div style="overflow-x:auto">
<table class="log-table">
  <thead><tr>{thead}</tr></thead>
  <tbody>{tbody}</tbody>
</table>
</div>

<script>
function applyFilter() {{
  var p = new URLSearchParams();
  var t = document.getElementById('f-tier').value;
  if(t) p.set('tier', t);
  var e = document.getElementById('f-env').value;
  if(e) p.set('env', e);
  var o = document.getElementById('f-oprid').value.trim();
  if(o) p.set('oprid', o);
  var c = document.getElementById('f-component').value.trim();
  if(c) p.set('component', c);
  var ec = document.getElementById('f-errcode').value.trim();
  if(ec) p.set('error_code', ec);
  if(document.getElementById('f-erronly').checked) p.set('errors_only', '1');
  var lim = document.getElementById('f-limit').value;
  if(lim) p.set('limit', lim);
  window.location = '/admin/log_viewer?' + p.toString();
}}
</script>
"""
    return HTMLResponse(_shell("Log Viewer", "log_viewer", content))


# ---------------------------------------------------------------------------
# /admin/log_session  — session chain (OPRID + time window)
# ---------------------------------------------------------------------------

@router.get("/log_session", response_class=HTMLResponse)
def log_session_view(
    request: Request,
    oprid: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    env: Optional[str] = None,
):
    chain = None
    if oprid:
        db = _logdb()
        from datetime import datetime, timedelta
        if not start:
            start = (datetime.utcnow() - timedelta(hours=8)).isoformat(timespec="seconds")
        if not end:
            end = datetime.utcnow().isoformat(timespec="seconds")
        chain = db.session_chain(oprid.upper(), start, end)

    web_rows = chain["web"] if chain else []
    app_rows = chain["app"] if chain else []

    def web_table(rows):
        if not rows:
            return '<p style="color:#555;font-size:12px">No web entries in this window.</p>'
        cells = ""
        for r in rows:
            status = r.get("status") or 0
            sc = "color:#ff6b6b" if status >= 500 else ("color:#ffd700" if status >= 400 else "color:#7faab2")
            comp = r.get("component") or "—"
            comp_link = (
                f'<a href="/admin/object/component/{comp}?env={r.get("env","")}" '
                f'style="color:#00e5ff" target="_blank">{comp}</a>'
                if comp != "—" else "—"
            )
            cells += (
                f'<tr>'
                f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{r.get("ts","")[:19]}</td>'
                f'<td style="{sc};font-weight:600">{status}</td>'
                f'<td style="font-size:11px">{r.get("method","")}</td>'
                f'<td>{comp_link}</td>'
                f'<td style="font-size:11px;color:#7faab2">{r.get("page") or "—"}</td>'
                f'<td style="font-size:11px;color:#7faab2">{r.get("ms") or "—"} ms</td>'
                f'</tr>'
            )
        return (
            f'<table class="log-table"><thead><tr>'
            f'<th>Time</th><th>Status</th><th>Method</th>'
            f'<th>Component</th><th>Page</th><th>Duration</th>'
            f'</tr></thead><tbody>{cells}</tbody></table>'
        )

    def app_table(rows):
        if not rows:
            return '<p style="color:#555;font-size:12px">No app server entries in this window.</p>'
        cells = ""
        for r in rows:
            level = r.get("level") or "INFO"
            lc = "color:#ff6b6b" if level == "ERROR" else "color:#ffd700" if level == "WARN" else "color:#7faab2"
            cells += (
                f'<tr>'
                f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{r.get("ts","")[:19]}</td>'
                f'<td style="{lc};font-size:11px;font-weight:600">{level}</td>'
                f'<td style="font-size:11px;color:#00e5ff">{r.get("object_ref") or "—"}</td>'
                f'<td style="font-size:11px;color:#d7faff;max-width:600px;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap" title="{r.get("message","")}">'
                f'{(r.get("message") or "")[:300]}</td>'
                f'</tr>'
            )
        return (
            f'<table class="log-table"><thead><tr>'
            f'<th>Time</th><th>Level</th><th>Object</th><th>Message</th>'
            f'</tr></thead><tbody>{cells}</tbody></table>'
        )

    oprid_val = oprid or ""
    start_val = start or ""
    end_val   = end or ""

    summary_html = ""
    if chain:
        errors = [r for r in app_rows if r.get("is_error")]
        summary_html = f"""
        <div style="display:flex;gap:24px;margin-bottom:18px;flex-wrap:wrap">
          <div class="stat-card"><div class="stat-val">{len(web_rows)}</div><div class="stat-lbl">Web Requests</div></div>
          <div class="stat-card"><div class="stat-val">{len(app_rows)}</div><div class="stat-lbl">App Entries</div></div>
          <div class="stat-card" style="border-color:rgba(255,107,107,.3)">
            <div class="stat-val" style="color:#ff6b6b">{len(errors)}</div>
            <div class="stat-lbl">Errors</div>
          </div>
          <div style="display:flex;align-items:center">
            <a href="/admin/tracing?oprid={oprid_val}&env={env or ''}"
               style="color:#00e5ff;font-size:13px" target="_blank">
              → Open Transaction Tracing for {oprid_val}
            </a>
          </div>
        </div>"""

    content = f"""
<style>
.log-table{{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}}
.log-table th{{text-align:left;padding:7px 8px;border-bottom:1px solid rgba(0,229,255,.2);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.log-table td{{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.03);vertical-align:middle}}
.log-table tr:hover td{{background:rgba(0,229,255,.04)}}
.lv-inp{{background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.25);color:#d7faff;
  font-size:12px;padding:4px 8px;border-radius:4px}}
.ql-btn{{padding:6px 12px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;text-decoration:none;cursor:pointer}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
.stat-card{{background:rgba(0,229,255,.05);border:1px solid rgba(0,229,255,.2);border-radius:6px;
  padding:12px 20px;min-width:100px}}
.stat-val{{font-size:24px;font-weight:700;color:#00e5ff}}
.stat-lbl{{font-size:11px;color:#7faab2;margin-top:2px}}
.chain-section{{margin-bottom:28px}}
.chain-section h4{{color:#d7faff;font-size:13px;margin:0 0 10px 0;
  border-bottom:1px solid rgba(0,229,255,.15);padding-bottom:6px}}
</style>

<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:16px">
  <a class="ql-btn" href="/admin/logs">← Sources</a>
  <input class="lv-inp" id="f-oprid" placeholder="OPRID" value="{oprid_val}" style="width:130px">
  <input class="lv-inp" id="f-start" type="datetime-local" value="{start_val.replace('T','T') if start_val else ''}">
  <input class="lv-inp" id="f-end"   type="datetime-local" value="{end_val.replace('T','T') if end_val else ''}">
  <button class="ql-btn" onclick="applyChain()">Load Chain</button>
</div>

{summary_html}

{'<div class="chain-section"><h4>Web Tier — Access Log</h4>' + web_table(web_rows) + '</div>' if chain else ''}
{'<div class="chain-section"><h4>App Tier — Application Server Log</h4>' + app_table(app_rows) + '</div>' if chain else ''}
{'<p style="color:#555;font-size:13px;text-align:center;margin-top:40px">Enter an OPRID and time window to view the session chain.</p>' if not chain else ''}

<script>
function applyChain() {{
  var o = document.getElementById('f-oprid').value.trim();
  if(!o) return;
  var p = new URLSearchParams({{oprid: o}});
  var s = document.getElementById('f-start').value;
  if(s) p.set('start', s.replace('T',' '));
  var e = document.getElementById('f-end').value;
  if(e) p.set('end', e.replace('T',' '));
  window.location = '/admin/log_session?' + p.toString();
}}
</script>
"""
    return HTMLResponse(_shell("Session Chain", "log_session", content))
