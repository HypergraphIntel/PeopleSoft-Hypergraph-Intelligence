"""
Admin UI for Phase 8 Log Intelligence.

/admin/logs           — sources overview + quick stats
/admin/log_errors     — error surface grouped by error_code + object_ref
/admin/log_viewer     — web / app log viewer with filters
/admin/log_session    — session chain (web→app) for a specific OPRID
/admin/igw            — Integration Gateway error analytics
/admin/prcs-ae        — PRCS AE server log analytics
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from typing import Optional

import html as _html

from routers.admin._core import _shell, _ESC_JS

def _esc(s: str) -> str:
    return _html.escape(str(s or ""), quote=True)

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

        enabled = bool(s["enabled"])
        status_dot = (
            '<span style="color:#00e5ff" title="enabled">●</span>' if enabled
            else '<span style="color:#555" title="disabled">●</span>'
        )
        error_msg = s.get("error_msg") or ""
        if error_msg:
            error_badge = (
                f'<span style="color:#ff6b6b;font-size:11px" title="{error_msg}">'
                f'{error_msg[:80]}{"…" if len(error_msg) > 80 else ""}</span>'
            )
        else:
            error_badge = ""

        file_count_html = (
            f'<span style="color:#00e5ff;font-weight:600">{file_count}</span>'
            if file_count > 0
            else f'<span style="color:#555" title="No files tracked yet — check path and SSH access">0</span>'
        )

        rows_html += f"""
        <tr>
          <td>{status_dot} <strong>{s['name']}</strong></td>
          <td><code>{s['type']}</code></td>
          <td>{s['env']}</td>
          <td>{s['ssh_host']}</td>
          <td style="font-size:11px;color:#7faab2;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
              title="{s['path']}">{s['path']}</td>
          <td style="text-align:center">{file_count_html}</td>
          <td style="font-size:11px;color:#7faab2;white-space:nowrap">{s.get('last_ingest') or '—'}</td>
          <td style="max-width:300px">{error_badge}</td>
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
  <a class="ql-btn" href="/admin/igw" style="color:#ff9f43;border-color:rgba(255,159,67,.35)">IGW Errors</a>
  <a class="ql-btn" href="/admin/prcs-ae" style="color:#00cc66;border-color:rgba(0,204,102,.35)">PRCS AE Logs</a>
  <a class="ql-btn" href="/admin/log_viewer">Log Viewer</a>
  <a class="ql-btn" href="/admin/log_session">Session Chain</a>
  <button class="ql-btn" onclick="triggerIngest()" id="ingest-btn">Trigger Ingest Now</button>
  <button class="ql-btn" onclick="reExtract()" id="reextract-btn" style="color:#ffd700;border-color:rgba(255,215,0,.3)">Re-extract Errors</button>
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
function reExtract() {{
  var btn = document.getElementById('reextract-btn');
  btn.textContent = 'Running…';
  btn.disabled = true;
  fetch('/api/logs/re-extract', {{method:'POST'}}).then(r => r.json()).then(function(d) {{
    btn.textContent = 'Re-extracted ✓ (' + (d.updated||0) + ' updated)';
    setTimeout(function(){{ btn.textContent='Re-extract Errors'; btn.disabled=false; }}, 4000);
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


# ---------------------------------------------------------------------------
# /admin/igw  — Integration Gateway error analytics
# ---------------------------------------------------------------------------

_IGW_EC_COLORS = {
    "HTTP_404": "#ffd700",
    "HTTP_503": "#ff6b6b",
    "HTTP_500": "#ff6b6b",
    "IB_EXT_APP":     "#ff6b6b",
    "IB_GFW":         "#ff9f43",
    "IB_LISTEN":      "#ff9f43",
    "IB_HTTP_TC":     "#ffd700",
    "IB_EXT_CONTACT": "#ffd700",
}

def _igw_ec_color(code: str) -> str:
    if not code:
        return "#7faab2"
    for prefix, color in _IGW_EC_COLORS.items():
        if code.startswith(prefix):
            return color
    return "#7faab2"


@router.get("/igw", response_class=HTMLResponse)
def igw_view(request: Request, env: Optional[str] = None):
    db = _logdb()

    import json
    cfg_path = __import__("pathlib").Path(__file__).parent.parent.parent / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text())
        envs = [e["name"] for e in cfg.get("peoplesoft", {}).get("environments", [])]
    except Exception:
        envs = []

    s = db.igw_summary(env=env)
    total   = s["total"]
    ops     = s["by_operation"]
    nodes   = s["by_node"]
    codes   = s["by_error_code"]
    recent  = s["recent"]
    first_s = (s["first_seen"] or "")[:19]
    last_s  = (s["last_seen"]  or "")[:19]

    env_opts = "".join(
        f'<option value="{e}" {"selected" if e == env else ""}>{e}</option>'
        for e in envs
    )

    # ── Stat cards ────────────────────────────────────────────────────────────
    unique_ops   = len(ops)
    unique_nodes = len(nodes)
    http_404     = next((c["count"] for c in codes if c["code"] == "HTTP_404"), 0)
    http_other   = sum(c["count"] for c in codes if (c["code"] or "").startswith("HTTP_") and c["code"] != "HTTP_404")

    def stat(val, label, color="#00e5ff", border_color=None):
        bc = border_color or "rgba(0,229,255,.2)"
        return (
            f'<div style="background:rgba(0,229,255,.05);border:1px solid {bc};'
            f'border-radius:6px;padding:12px 20px;min-width:110px">'
            f'<div style="font-size:24px;font-weight:700;color:{color}">{val}</div>'
            f'<div style="font-size:11px;color:#7faab2;margin-top:2px">{label}</div></div>'
        )

    stats_html = "".join([
        stat(total,        "IGW Errors",        "#ff6b6b", "rgba(255,107,107,.3)"),
        stat(unique_ops,   "IB Operations",     "#ff9f43", "rgba(255,159,67,.3)"),
        stat(unique_nodes, "Requesting Nodes",  "#ffd700", "rgba(255,215,0,.3)"),
        stat(http_404,     "HTTP 404 Errors",   "#ff6b6b", "rgba(255,107,107,.2)") if http_404 else "",
        stat(http_other,   "Other HTTP Errors", "#ffd700", "rgba(255,215,0,.2)")   if http_other else "",
    ])

    # ── Error code chips ──────────────────────────────────────────────────────
    ec_chips = ""
    for c_item in codes:
        code  = c_item["code"] or "—"
        count = c_item["count"]
        color = _igw_ec_color(code)
        ec_chips += (
            f'<div style="display:inline-flex;align-items:center;gap:6px;'
            f'background:rgba(0,0,0,.3);border:1px solid {color}40;'
            f'border-radius:4px;padding:5px 10px;margin:3px">'
            f'<span style="color:{color};font-weight:600;font-size:12px">{code}</span>'
            f'<span style="color:#7faab2;font-size:11px">×{count}</span></div>'
        )

    # ── IB operation breakdown table ──────────────────────────────────────────
    op_rows = ""
    max_op_count = ops[0][1] if ops else 1
    for op_name, op_count in ops:
        pct = int(op_count / max_op_count * 100)
        op_link = (
            f'<a href="/admin/object/ib_service_operation/{op_name}?env={env or ""}" '
            f'style="color:#ff9f43;font-family:monospace" target="_blank">{op_name}</a>'
        )
        bar = (
            f'<div style="height:6px;border-radius:3px;width:{pct}%;'
            f'background:rgba(255,159,67,.5);margin-top:4px"></div>'
        )
        op_rows += (
            f'<tr>'
            f'<td>{op_link}</td>'
            f'<td style="text-align:right;font-weight:700;color:#ffd700">{op_count}</td>'
            f'<td><div style="min-width:80px">{bar}</div></td>'
            f'</tr>'
        )
    if not op_rows:
        op_rows = '<tr><td colspan="3" style="color:#555;text-align:center;padding:16px">No operations found — check raw field format</td></tr>'

    # ── Requesting node breakdown table ───────────────────────────────────────
    node_rows = ""
    for node_name, node_count in nodes:
        node_link = (
            f'<a href="/admin/ib/node/{node_name}?env={env or ""}" '
            f'style="color:#00e5ff;font-family:monospace">{node_name}</a>'
        )
        ai_q = f"Diagnose IB node {node_name} errors in gateway log for env {env or 'HCM'}"
        node_rows += (
            f'<tr>'
            f'<td>{node_link}</td>'
            f'<td style="text-align:right;font-weight:700;color:#ffd700">{node_count}</td>'
            f'<td>'
            f'<a href="/admin/assistant?q={ai_q}" class="ql-btn" '
            f'style="font-size:11px;padding:3px 8px" target="_blank">Ask AI</a>'
            f'</td></tr>'
        )
    if not node_rows:
        node_rows = '<tr><td colspan="3" style="color:#555;text-align:center;padding:16px">No nodes found</td></tr>'

    # ── Recent entries table ──────────────────────────────────────────────────
    recent_rows = ""
    for entry in recent[:30]:
        ts   = (entry["ts"] or "")[:19]
        desc = entry["description"] or "—"
        excp = entry["exception"] or "—"
        op   = entry["operation"] or "—"
        node = entry["node"] or "—"
        env_ = entry["env"] or ""
        op_link = (
            f'<a href="/admin/object/ib_service_operation/{op}?env={env_}" '
            f'style="color:#ff9f43;font-family:monospace;font-size:11px" target="_blank">{op}</a>'
            if op != "—" else "—"
        )
        node_link = (
            f'<a href="/admin/ib/node/{node}?env={env_}" '
            f'style="color:#00e5ff;font-family:monospace;font-size:11px">{node}</a>'
            if node != "—" else "—"
        )
        desc_short = desc[:80] + ("…" if len(desc) > 80 else "")
        recent_rows += (
            f'<tr>'
            f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{ts}</td>'
            f'<td>{op_link}</td>'
            f'<td>{node_link}</td>'
            f'<td style="font-size:11px;color:#ff9f43" title="{_esc(desc)}">{desc_short}</td>'
            f'</tr>'
        )
    if not recent_rows:
        recent_rows = '<tr><td colspan="4" style="color:#555;text-align:center;padding:24px">No IGW entries found.</td></tr>'

    # ── Ask AI prompt ──────────────────────────────────────────────────────────
    top_op   = ops[0][0]   if ops   else "unknown"
    top_node = nodes[0][0] if nodes else "unknown"
    ai_q = (
        f"Analyze IGW errors in {env or 'HCM'}: {total} errors total. "
        f"Top operation: {top_op}. Top requesting node: {top_node}. "
        f"HTTP 404 count: {http_404}. Check ib_diagnostics and explain what is failing."
    )

    date_range_html = ""
    if first_s and last_s:
        date_range_html = f'<span style="color:#7faab2;font-size:12px">{first_s} → {last_s}</span>'

    content = f"""
<style>
.ig-table{{width:100%;border-collapse:collapse;font-size:13px}}
.ig-table th{{text-align:left;padding:7px 10px;border-bottom:1px solid rgba(255,159,67,.25);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.ig-table td{{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}}
.ig-table tr:hover td{{background:rgba(255,159,67,.04)}}
.ig-section{{background:rgba(0,0,0,.25);border:1px solid rgba(255,159,67,.15);
  border-radius:6px;padding:16px 20px;margin-bottom:18px}}
.ig-section h4{{color:#ff9f43;font-size:13px;margin:0 0 12px 0;letter-spacing:.3px}}
.ql-btn{{padding:6px 12px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;
  text-decoration:none;display:inline-block;cursor:pointer}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}}}
</style>

<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <h3 style="color:#ff9f43;margin:0;font-size:15px">IGW Error Analytics</h3>
  <select id="env-sel" onchange="applyEnv()"
    style="background:rgba(0,20,30,.88);border:1px solid rgba(255,159,67,.3);
      color:#d7faff;font-size:12px;padding:4px 8px;border-radius:4px">
    <option value="">All Envs</option>{env_opts}
  </select>
  {date_range_html}
  <div style="margin-left:auto;display:flex;gap:8px">
    <a href="/admin/logs" class="ql-btn" style="font-size:12px">← Sources</a>
    <a href="/admin/log_errors" class="ql-btn" style="font-size:12px">Error Surface</a>
    <a href="/admin/assistant?q={_esc(ai_q)}" class="ql-btn"
       style="font-size:12px;background:rgba(255,159,67,.1);border-color:rgba(255,159,67,.4);color:#ff9f43"
       target="_blank">Ask AI</a>
  </div>
</div>

<p style="color:#7faab2;font-size:12px;margin:0 0 14px 0">
  Integration Gateway errors from <code>errorLog.html</code> — gateway-level IB operation failures,
  target connector errors, and node connectivity issues. Cross-links to IB Explorer and AI assistant.
</p>

<!-- Stat cards -->
<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">
  {stats_html}
</div>

<!-- Error codes -->
<div class="ig-section" style="margin-bottom:18px">
  <h4>Error Codes</h4>
  <div>{ec_chips}</div>
</div>

<!-- Operations + Nodes side-by-side -->
<div class="grid2">
  <div class="ig-section">
    <h4>By IB Operation</h4>
    <table class="ig-table">
      <thead><tr><th>Operation</th><th style="text-align:right">Count</th><th>Relative</th></tr></thead>
      <tbody>{op_rows}</tbody>
    </table>
  </div>
  <div class="ig-section">
    <h4>By Requesting Node</h4>
    <table class="ig-table">
      <thead><tr><th>Node</th><th style="text-align:right">Count</th><th>Actions</th></tr></thead>
      <tbody>{node_rows}</tbody>
    </table>
  </div>
</div>

<!-- Recent entries -->
<div class="ig-section">
  <h4>Recent Errors <span style="color:#7faab2;font-weight:400;font-size:11px">(last 30)</span></h4>
  <table class="ig-table">
    <thead><tr><th>Time</th><th>Operation</th><th>Node</th><th>Description</th></tr></thead>
    <tbody>{recent_rows}</tbody>
  </table>
</div>

<script>
function applyEnv() {{
  var e = document.getElementById('env-sel').value;
  window.location = '/admin/igw' + (e ? '?env=' + e : '');
}}
</script>
"""
    return HTMLResponse(_shell("IGW Errors", "igw", content))


# ---------------------------------------------------------------------------
# /admin/prcs-ae  — PRCS AE server log analytics
# ---------------------------------------------------------------------------

@router.get("/prcs-ae", response_class=HTMLResponse)
def prcs_ae_view(request: Request, env: Optional[str] = None):
    db = _logdb()

    import json
    cfg_path = __import__("pathlib").Path(__file__).parent.parent.parent / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text())
        envs = [e["name"] for e in cfg.get("peoplesoft", {}).get("environments", [])]
    except Exception:
        envs = []

    s = db.prcs_ae_summary(env=env)
    total        = s["total"]
    error_count  = s["error_count"]
    by_program   = s["by_program"]
    recent_errs  = s["recent_errors"]
    first_s      = (s["first_seen"] or "")[:19]
    last_s       = (s["last_seen"]  or "")[:19]

    env_opts = "".join(
        f'<option value="{e}" {"selected" if e == env else ""}>{e}</option>'
        for e in envs
    )

    def stat(val, label, color="#00e5ff", border_color=None):
        bc = border_color or "rgba(0,229,255,.2)"
        return (
            f'<div style="background:rgba(0,229,255,.05);border:1px solid {bc};'
            f'border-radius:6px;padding:12px 20px;min-width:110px">'
            f'<div style="font-size:24px;font-weight:700;color:{color}">{val}</div>'
            f'<div style="font-size:11px;color:#7faab2;margin-top:2px">{label}</div></div>'
        )

    unique_programs = len(by_program)
    failed_programs = sum(1 for p in by_program if p["error_count"] > 0)
    stats_html = "".join([
        stat(total,           "Total Entries",     "#00e5ff", "rgba(0,229,255,.2)"),
        stat(unique_programs, "AE Programs",       "#00cc66", "rgba(0,204,102,.3)"),
        stat(error_count,     "Errors",            "#ff6b6b", "rgba(255,107,107,.3)") if error_count else
        stat(0,               "Errors",            "#00cc66", "rgba(0,204,102,.2)"),
        stat(failed_programs, "Failed Programs",   "#ff9f43", "rgba(255,159,67,.3)") if failed_programs else "",
    ])

    # Program breakdown table
    max_runs = max((p["run_count"] for p in by_program), default=1)
    prog_rows = ""
    for p in by_program:
        ae = p["ae_applid"] or "—"
        err_c = p["error_count"] or 0
        run_c = p["run_count"]
        pct = int(run_c / max_runs * 100)
        err_pct = int(err_c / run_c * 100) if run_c else 0
        ae_link = (
            f'<a href="/admin/object/application_engine/{_esc(ae)}?env={_esc(env or "")}" '
            f'style="color:#00e5ff;font-family:monospace" target="_blank">{_esc(ae)}</a>'
            if ae != "—" else "—"
        )
        err_color = "#ff4444" if err_c > 0 else "#00cc66"
        err_badge = (
            f'<span style="color:{err_color};font-weight:700">{err_c}</span>'
            f'<span style="color:#445;font-size:10px"> ({err_pct}%)</span>'
        ) if err_c else '<span style="color:#00cc66">0</span>'
        bar = (
            f'<div style="display:flex;height:6px;border-radius:3px;overflow:hidden;'
            f'background:#0b2030;width:100%;max-width:120px">'
            f'<div style="width:{pct - err_pct}%;background:rgba(0,204,102,.5)"></div>'
            f'<div style="width:{err_pct}%;background:rgba(255,100,100,.7)"></div>'
            f'</div>'
        )
        first = (p["first_seen"] or "")[:10]
        last  = (p["last_seen"]  or "")[:10]
        prog_rows += (
            f'<tr>'
            f'<td>{ae_link}</td>'
            f'<td style="text-align:right;font-weight:700;color:#ffd700">{run_c}</td>'
            f'<td style="text-align:right">{err_badge}</td>'
            f'<td><div style="min-width:80px">{bar}</div></td>'
            f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{first}</td>'
            f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{last}</td>'
            f'</tr>'
        )
    if not prog_rows:
        prog_rows = '<tr><td colspan="6" style="color:#555;text-align:center;padding:16px">No PRCS AE entries found.</td></tr>'

    # Recent errors table
    err_rows = ""
    for entry in recent_errs:
        ts    = (entry["ts"] or "")[:19]
        ae    = entry["ae_applid"] or None
        msg   = (entry["message"] or "")[:100] + ("…" if len(entry["message"] or "") > 100 else "")
        inst  = entry.get("process_instance")
        ae_link = (
            f'<a href="/admin/object/application_engine/{_esc(ae)}?env={_esc(env or "")}" '
            f'style="color:#00e5ff;font-family:monospace;font-size:11px" target="_blank">{_esc(ae)}</a>'
            if ae else '<span style="color:#445">—</span>'
        )
        inst_link = (
            f'<a href="/admin/runtime?instance={inst}" style="color:#ffd700;font-family:monospace;font-size:11px">'
            f'#{inst}</a>'
            if inst else "—"
        )
        err_rows += (
            f'<tr>'
            f'<td style="font-size:11px;color:#7faab2;white-space:nowrap">{_esc(ts)}</td>'
            f'<td>{ae_link}</td>'
            f'<td style="font-size:11px;color:#ff9f43">{_esc(msg)}</td>'
            f'<td>{inst_link}</td>'
            f'</tr>'
        )
    if not err_rows:
        err_rows = '<tr><td colspan="4" style="color:#555;text-align:center;padding:16px">No errors recorded.</td></tr>'

    date_range_html = ""
    if first_s and last_s:
        date_range_html = f'<span style="color:#7faab2;font-size:12px">{first_s} → {last_s}</span>'

    top_prog = by_program[0]["ae_applid"] if by_program else "unknown"
    ai_q = (
        f"Analyze PRCS AE server logs for {env or 'HCM'}: "
        f"{total} total entries, {error_count} errors. "
        f"Most active AE: {top_prog}. "
        f"Failed programs: {failed_programs}. Explain what is failing and why."
    )

    content = f"""
<style>
.pa-table{{width:100%;border-collapse:collapse;font-size:13px}}
.pa-table th{{text-align:left;padding:7px 10px;border-bottom:1px solid rgba(0,229,255,.2);
  color:#7faab2;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.pa-table td{{padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}}
.pa-table tr:hover td{{background:rgba(0,229,255,.04)}}
.pa-section{{background:rgba(0,0,0,.25);border:1px solid rgba(0,229,255,.15);
  border-radius:6px;padding:16px 20px;margin-bottom:18px}}
.pa-section h4{{color:#00e5ff;font-size:13px;margin:0 0 12px 0;letter-spacing:.3px}}
.ql-btn{{padding:6px 12px;border-radius:4px;background:rgba(0,229,255,.08);
  border:1px solid rgba(0,229,255,.25);color:#00e5ff;font-size:12px;
  text-decoration:none;display:inline-block;cursor:pointer}}
.ql-btn:hover{{background:rgba(0,229,255,.15)}}
</style>

<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">
  <h3 style="color:#00e5ff;margin:0;font-size:15px">PRCS AE Log Analytics</h3>
  <select id="env-sel" onchange="applyEnv()"
    style="background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.3);
      color:#d7faff;font-size:12px;padding:4px 8px;border-radius:4px">
    <option value="">All Envs</option>{env_opts}
  </select>
  {date_range_html}
  <div style="margin-left:auto;display:flex;gap:8px">
    <a href="/admin/logs" class="ql-btn" style="font-size:12px">← Sources</a>
    <a href="/admin/runtime" class="ql-btn" style="font-size:12px">Runtime Monitor</a>
    <a href="/admin/assistant?q={_esc(ai_q)}" class="ql-btn"
       style="font-size:12px;background:rgba(0,229,255,.1);border-color:rgba(0,229,255,.4)"
       target="_blank">Ask AI</a>
  </div>
</div>

<p style="color:#7faab2;font-size:12px;margin:0 0 14px 0">
  Process Scheduler AE Server log entries — start, step execution, completion, and failure events
  per Application Engine program. Click a process instance to open Runtime Monitor with the Exec Log tab.
</p>

<!-- Stat cards -->
<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">
  {stats_html}
</div>

<!-- Program breakdown -->
<div class="pa-section">
  <h4>By AE Program</h4>
  <table class="pa-table">
    <thead><tr>
      <th>AE Program</th>
      <th style="text-align:right">Entries</th>
      <th style="text-align:right">Errors</th>
      <th>Error Rate</th>
      <th>First Seen</th>
      <th>Last Seen</th>
    </tr></thead>
    <tbody>{prog_rows}</tbody>
  </table>
</div>

<!-- Recent errors -->
<div class="pa-section">
  <h4>Recent Errors <span style="color:#7faab2;font-weight:400;font-size:11px">(last 20)</span></h4>
  <table class="pa-table">
    <thead><tr><th>Timestamp</th><th>AE Program</th><th>Message</th><th>Instance</th></tr></thead>
    <tbody>{err_rows}</tbody>
  </table>
</div>

<script>
function applyEnv() {{
  var e = document.getElementById('env-sel').value;
  window.location = '/admin/prcs-ae' + (e ? '?env=' + e : '');
}}
</script>
"""
    return HTMLResponse(_shell("PRCS AE Logs", "prcs_ae", content))
