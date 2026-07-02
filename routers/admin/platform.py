import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/msgcat", response_class=HTMLResponse)
def admin_msgcat():
    return _shell("Message Catalog", "msgcat", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:340px;min-width:240px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-ref{font-family:monospace;font-size:12px;color:#d7faff}
.item-text{font-size:11px;color:#aac;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00}
.chip-error{background:#2a0000;border:1px solid #ff4444;color:#ff6666}
.chip-crit{background:#1a0020;border:1px solid #aa44ff;color:#cc88ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.msg-text{background:#030d14;border:1px solid #1e3040;padding:12px 14px;font-size:12px;line-height:1.6;white-space:pre-wrap;word-break:break-word;margin:4px 0 12px}
.explain{background:#030d14;border:1px solid #1e304066;padding:10px 14px;font-size:11px;line-height:1.6;color:#aac;white-space:pre-wrap;word-break:break-word;margin-top:4px}
.muted{color:#556;font-style:italic}
a{color:#00e5ff;text-decoration:none} a:hover{text-decoration:underline}
</style>
<div class="topbar">
  <input id="mcSearch" type="text" placeholder="Search message text..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="mcSet" style="width:130px" onchange="doSearch()">
    <option value="">All Sets</option>
  </select>
  <select id="mcSeverity" style="width:110px" onchange="doSearch()">
    <option value="">All Severities</option>
    <option value="0">Message</option>
    <option value="1">Warning</option>
    <option value="2">Error</option>
    <option value="3">Cancel</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Messages</h2>
    <div id="list" class="muted">Search to load messages.</div>
  </div>
  <div class="content">
    <h2>Selected Message</h2>
    <div id="detail" class="muted">Select a message from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const SEV_CHIP = {'0':['chip-info','Message'],'1':['chip-warn','Warning'],'2':['chip-error','Error'],'3':['chip-crit','Cancel']};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function sevChip(sev) {
  const [cls, label] = SEV_CHIP[String(sev)] || ['chip-muted', 'Unknown'];
  return `<span class="chip ${cls}">${label}</span>`;
}

async function loadSets() {
  const d = await api(`/api/peoplesoft/message-sets?env=${ENV}`);
  if (!d) return;
  const sel = document.getElementById('mcSet');
  (d.items || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.message_set_nbr;
    const desc = s.descr ? ` — ${s.descr}` : '';
    const cnt = s.msg_count ? ` (${s.msg_count})` : '';
    opt.textContent = `Set ${s.message_set_nbr}${desc}${cnt}`;
    sel.appendChild(opt);
  });
}

async function doSearch() {
  const q = document.getElementById('mcSearch').value.trim();
  const setNbr = document.getElementById('mcSet').value;
  const sev = document.getElementById('mcSeverity').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (setNbr) params.set('set_nbr', setNbr);
  if (sev !== '') params.set('severity', sev);
  const d = await api(`/api/peoplesoft/messages?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading messages.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No messages found.</div>'; return; }
  list.innerHTML = items.map((m, i) =>
    `<div class="item" id="item-${i}" onclick="selectMsg(${i})" data-idx="${i}">
       <div class="item-ref">${sevChip(m.severity)}${esc(m.name)}</div>
       <div class="item-text">${esc((m.message_text||'').slice(0,80))}</div>
     </div>`
  ).join('');
  window._msgItems = items;
}

function selectMsg(idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const m = window._msgItems[idx];
  if (!m) return;
  const sev = String(m.severity || '0');
  const text = m.message_text || '';
  const explain = m.descrlong || '';
  const adminUrl = `/admin/object/message_catalog/${esc(m.name)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${sevChip(m.severity)}
      <span style="font-family:monospace;font-size:13px">${esc(m.name)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    <div class="stat"><b>${esc(m.message_set_nbr)}</b>Set</div>
    <div class="stat"><b>${esc(m.message_nbr)}</b>Msg #</div>
    ${text ? `<h2>Message Text</h2><div class="msg-text">${esc(text)}</div>` : ''}
    ${explain ? `<h2>Explanation</h2><div class="explain">${esc(explain)}</div>` : ''}
  `;
  document.getElementById('detail').innerHTML = html;
}

loadSets();
doSearch();
</script>""")


@router.get("/prcsdefn")
def admin_prcsdefn(request: Request, env: str = "HCM"):
    nav = _nav_html("prcsdefn", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Process Definitions</title>
{_NAV_CSS}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d11;color:#ccd;font-family:system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}}
.shell{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:300px;min-width:220px;border-right:1px solid #222;display:flex;flex-direction:column;overflow:hidden}}
.filters{{padding:10px;border-bottom:1px solid #1a1a22}}
.filters input,.filters select{{width:100%;background:#111;border:1px solid #333;color:#ccd;padding:5px 8px;border-radius:3px;font-size:12px;margin-bottom:6px}}
.list{{overflow-y:auto;flex:1;padding:4px 0}}
.item{{padding:7px 12px;cursor:pointer;border-left:3px solid transparent;transition:background .1s}}
.item:hover{{background:#151520}}
.item.sel{{background:#12121e;border-left-color:#aa66ff}}
.item-name{{font-family:monospace;font-size:12px;color:#aa66ff;font-weight:bold}}
.item-meta{{font-size:10px;color:#556;margin-top:2px}}
.item-descr{{font-size:11px;color:#889;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.detail{{flex:1;overflow-y:auto;padding:20px}}
.muted{{color:#445;font-size:12px;padding:20px}}
h2{{color:#aa66ff;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #1e1e2a}}
.kv-grid{{display:grid;grid-template-columns:140px 1fr;gap:4px 10px;font-size:12px;margin-bottom:10px}}
.kv-key{{color:#556;padding-top:1px}}
.kv-val{{color:#aab;font-family:monospace;word-break:break-all}}
.chip{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;margin:1px 3px 1px 0;white-space:nowrap}}
.chip-ok{{background:#0a1a0a;border:1px solid #22cc6644;color:#22cc66}}
.chip-info{{background:#001018;border:1px solid #00ccee44;color:#00ccee}}
.chip-muted{{background:#1a1a1a;border:1px solid #33333388;color:#778}}
.chip-purple{{background:#100a18;border:1px solid #aa66ff44;color:#aa66ff}}
.stat{{display:inline-block;margin-right:14px;font-size:11px;color:#556}}
.stat b{{color:#aa66ff;font-size:14px;margin-right:4px}}
.field-row{{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #1a1a22;font-size:12px}}
.type-badge{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;border:1px solid #aa66ff44;background:#100a18;color:#aa66ff;margin-right:6px}}
</style></head>
<body>
{nav}
<div class="shell">
  <div class="sidebar">
    <div class="filters">
      <input id="qInput" placeholder="Search name / description…" oninput="doSearch()">
      <select id="typeFilter" onchange="doSearch()">
        <option value="">All Types</option>
        <option value="Application Engine">Application Engine</option>
        <option value="SQR Report">SQR Report</option>
        <option value="XML Publisher">XML Publisher</option>
        <option value="COBOL SQL">COBOL SQL</option>
        <option value="SQR Process">SQR Process</option>
        <option value="SQR Report For WF Delivery">SQR/WF Delivery</option>
        <option value="Data Mover">Data Mover</option>
      </select>
    </div>
    <div class="list" id="list"></div>
  </div>
  <div class="detail" id="detail"><div class="muted">Select a process definition.</div></div>
</div>
<script>
const ENV = {repr(env)};
let _all = [], _sel = -1;

async function api(url) {{
  try {{ const r = await fetch(url); return r.ok ? r.json() : null; }} catch {{ return null; }}
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function chip(cls, label) {{ return `<span class="chip ${{cls}}">${{esc(label)}}</span>`; }}

function typeChip(t) {{
  const cls = {{
    'Application Engine':'chip-ok','SQR Report':'chip-info','XML Publisher':'chip-info',
    'COBOL SQL':'chip-muted','SQR Process':'chip-muted','Data Mover':'chip-muted',
    'SQR Report For WF Delivery':'chip-muted'
  }}[t] || 'chip-muted';
  return chip(cls, t);
}}

async function doSearch() {{
  const q = document.getElementById('qInput').value;
  const prcstype = document.getElementById('typeFilter').value;
  const data = await api(`/api/peoplesoft/process-definitions?env=${{ENV}}&q=${{encodeURIComponent(q)}}&prcstype=${{encodeURIComponent(prcstype)}}&limit=500`);
  _all = (data?.items || []);
  const list = document.getElementById('list');
  list.innerHTML = _all.map((it, i) => `
    <div class="item" id="item-${{i}}" onclick="selectItem(${{i}}, '${{encodeURIComponent(it._key)}}')">
      <div class="item-name">${{esc(it.prcsname)}}</div>
      <div class="item-meta">${{esc(it.prcstype)}}</div>
      <div class="item-descr">${{esc(it.descr||'')}}</div>
    </div>`).join('');
}}

async function selectItem(idx, key) {{
  _sel = idx;
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${{idx}}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/prcs_defn/${{key}}?env=${{ENV}}`);
  if (!d) {{ detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }}

  const uom = d._uom || {{}};
  const sections = d.sections || [];
  const ovSec = sections.find(s => s.id === 'overview');
  const pgSec = sections.find(s => s.id === 'run_cntl_pages');
  const grpSec = sections.find(s => s.id === 'prcs_groups');
  const counts = uom.counts || {{}};

  let html = `<div style="margin-bottom:12px">
    ${{typeChip(uom.prcstype||'')}}
    <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#aa66ff">${{esc(uom.prcsname||'')}}</span>
  </div>`;

  if (uom.title && uom.title !== uom.prcsname) {{
    html += `<div style="color:#889;font-size:13px;margin-bottom:12px">${{esc(uom.title)}}</div>`;
  }}

  const ovRows = (ovSec?.rows || []).filter(r => !['Type'].includes(r.label));
  if (ovRows.length) {{
    html += `<div class="kv-grid">`;
    for (const row of ovRows) {{
      const val = row.value ? esc(String(row.value)) :
        (row.chips||[]).map(c => chip(c.cls||'chip-info', c.label)).join('') || '';
      html += `<div class="kv-key">${{esc(row.label)}}</div><div class="kv-val">${{val}}</div>`;
    }}
    html += `</div>`;
  }}

  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${{counts.run_cntl_pages||0}}</b>Run Control Pages</span>`
    + `<span class="stat"><b>${{counts.prcs_groups||0}}</b>Process Groups</span>`
    + `</div>`;

  if (pgSec?.chips?.length) {{
    html += `<h2>Run Control Pages</h2>`;
    html += pgSec.chips.map(c => chip('chip-info', c.label)).join(' ');
  }}
  if (grpSec?.chips?.length) {{
    html += `<h2>Process Groups</h2>`;
    html += grpSec.chips.map(c => chip('chip-muted', c.label)).join(' ');
  }}

  if (!ovRows.length && !pgSec && !grpSec) {{
    html += `<div class="muted">No detail available.</div>`;
  }}

  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/filelayout")
def admin_filelayout(request: Request, env: str = "HCM"):
    nav = _nav_html("filelayout", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>File Layouts</title>
{_NAV_CSS}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d11;color:#ccd;font-family:system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}}
.shell{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:300px;min-width:220px;border-right:1px solid #222;display:flex;flex-direction:column;overflow:hidden}}
.filters{{padding:10px;border-bottom:1px solid #1a1a22}}
.filters input{{width:100%;background:#111;border:1px solid #333;color:#ccd;padding:5px 8px;border-radius:3px;font-size:12px}}
.list{{overflow-y:auto;flex:1;padding:4px 0}}
.item{{padding:7px 12px;cursor:pointer;border-left:3px solid transparent;transition:background .1s}}
.item:hover{{background:#151520}}
.item.sel{{background:#12121e;border-left-color:#44aaff}}
.item-name{{font-family:monospace;font-size:12px;color:#44aaff;font-weight:bold}}
.item-meta{{font-size:10px;color:#556;margin-top:2px}}
.item-descr{{font-size:11px;color:#889;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.detail{{flex:1;overflow-y:auto;padding:20px}}
.muted{{color:#445;font-size:12px;padding:20px}}
h2{{color:#44aaff;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #1e1e2a}}
.kv-grid{{display:grid;grid-template-columns:140px 1fr;gap:4px 10px;font-size:12px;margin-bottom:10px}}
.kv-key{{color:#556;padding-top:1px}}
.kv-val{{color:#aab;font-family:monospace;word-break:break-all}}
.chip{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;margin:1px 3px 1px 0;white-space:nowrap}}
.chip-ok{{background:#0a1a0a;border:1px solid #22cc6644;color:#22cc66}}
.chip-info{{background:#001018;border:1px solid #00ccee44;color:#00ccee}}
.chip-muted{{background:#1a1a1a;border:1px solid #33333388;color:#778}}
.chip-blue{{background:#0a1218;border:1px solid #44aaff44;color:#44aaff}}
.stat{{display:inline-block;margin-right:14px;font-size:11px;color:#556}}
.stat b{{color:#44aaff;font-size:14px;margin-right:4px}}
.field-row{{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #1a1a22;font-size:12px}}
.seg-header{{background:#0d1220;border:1px solid #1a2a3a;border-radius:3px;padding:6px 10px;margin:8px 0 4px;font-family:monospace;font-size:12px;color:#44aaff;font-weight:bold}}
.seg-meta{{color:#556;font-size:10px;margin-left:8px;font-weight:normal}}
</style></head>
<body>
{nav}
<div class="shell">
  <div class="sidebar">
    <div class="filters">
      <input id="qInput" placeholder="Search name / description…" oninput="doSearch()">
    </div>
    <div class="list" id="list"></div>
  </div>
  <div class="detail" id="detail"><div class="muted">Select a file layout.</div></div>
</div>
<script>
const ENV = {repr(env)};
let _all = [];

async function api(url) {{
  try {{ const r = await fetch(url); return r.ok ? r.json() : null; }} catch {{ return null; }}
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function chip(cls, label) {{ return `<span class="chip ${{cls}}">${{esc(label)}}</span>`; }}

function fmtChip(fmt) {{
  const cls = {{'Fixed Width':'chip-info','Delimited':'chip-ok','XML':'chip-ok'}}[fmt] || 'chip-muted';
  const map = {{'Fixed Width':'chip-info','Delimited':'chip-ok','XML':'chip-ok'}};
  return chip(map[fmt]||'chip-muted', fmt||'?');
}}

function fieldTypeLabel(t) {{
  return [,'Number','Date','Time','DateTime','','Image'][t] || 'Char';
}}

async function doSearch() {{
  const q = document.getElementById('qInput').value;
  const data = await api(`/api/peoplesoft/file-layouts?env=${{ENV}}&q=${{encodeURIComponent(q)}}&limit=500`);
  _all = (data?.items || []);
  const list = document.getElementById('list');
  list.innerHTML = _all.map((it, i) => `
    <div class="item" id="item-${{i}}" onclick="selectItem(${{i}}, '${{encodeURIComponent(it.flddefnname)}}')">
      <div class="item-name">${{esc(it.flddefnname)}}</div>
      <div class="item-meta">${{esc(it.fldformat_label||'')}}</div>
      <div class="item-descr">${{esc(it.descr||'')}}</div>
    </div>`).join('');
}}

async function selectItem(idx, name) {{
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${{idx}}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/file_layout/${{name}}?env=${{ENV}}`);
  if (!d) {{ detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }}

  const uom = d._uom || {{}};
  const sections = d.sections || [];
  const ovSec = sections.find(s => s.id === 'overview');
  const segSec = sections.find(s => s.id === 'segments');
  const fieldSecs = sections.filter(s => s.id.startsWith('fields_'));
  const counts = uom.counts || {{}};

  let html = `<div style="margin-bottom:12px">
    ${{fmtChip(uom.format)}}
    <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#44aaff">${{esc(uom.name||'')}}</span>
  </div>`;

  if (uom.title && uom.title !== uom.name) {{
    html += `<div style="color:#889;font-size:13px;margin-bottom:12px">${{esc(uom.title)}}</div>`;
  }}

  const ovRows = (ovSec?.rows || []).filter(r => r.label !== 'Format');
  if (ovRows.length) {{
    html += `<div class="kv-grid">`;
    for (const row of ovRows) {{
      const val = row.value ? esc(String(row.value)) :
        (row.chips||[]).map(c => chip(c.cls||'chip-info', c.label)).join('') || '';
      html += `<div class="kv-key">${{esc(row.label)}}</div><div class="kv-val">${{val}}</div>`;
    }}
    html += `</div>`;
  }}

  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${{counts.segments||0}}</b>Segments</span>`
    + `<span class="stat"><b>${{counts.fields||0}}</b>Fields</span>`
    + `</div>`;

  if (segSec?.items?.length) {{
    html += `<h2>Segments</h2>`;
    for (const seg of segSec.items) {{
      html += `<div class="seg-header">${{esc(seg.name)}}${{seg.meta ? `<span class="seg-meta">${{esc(seg.meta)}}</span>` : ''}}</div>`;
    }}
  }}

  for (const fsec of fieldSecs) {{
    if (fsec.items?.length) {{
      html += `<h2>${{esc(fsec.title)}}</h2>`;
      html += fsec.items.map(f =>
        `<div class="field-row">
           <span style="font-family:monospace;color:#aad;min-width:160px">${{esc(f.name)}}</span>
           ${{(f.chips||[]).map(c => chip(c.cls||'chip-muted', c.label)).join('')}}
           ${{f.meta ? `<span style="color:#445;font-size:10px">${{esc(f.meta)}}</span>` : ''}}
         </div>`
      ).join('');
    }}
  }}

  if (!ovRows.length && !segSec) {{
    html += `<div class="muted">No detail available.</div>`;
  }}

  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/xlat")
def admin_xlat(request: Request, env: str = "HCM"):
    nav = _nav_html("xlat", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Translate Values</title>
{_NAV_CSS}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d11;color:#ccd;font-family:system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}}
.shell{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:280px;min-width:200px;border-right:1px solid #222;display:flex;flex-direction:column;overflow:hidden}}
.filters{{padding:10px;border-bottom:1px solid #1a1a22}}
.filters input{{width:100%;background:#111;border:1px solid #333;color:#ccd;padding:5px 8px;border-radius:3px;font-size:12px}}
.list{{overflow-y:auto;flex:1;padding:4px 0}}
.item{{padding:7px 12px;cursor:pointer;border-left:3px solid transparent;transition:background .1s}}
.item:hover{{background:#151520}}
.item.sel{{background:#12121e;border-left-color:#ddcc00}}
.item-name{{font-family:monospace;font-size:12px;color:#ddcc00;font-weight:bold}}
.item-meta{{font-size:10px;color:#556;margin-top:2px}}
.detail{{flex:1;overflow-y:auto;padding:20px}}
.muted{{color:#445;font-size:12px;padding:20px}}
h2{{color:#ddcc00;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #1e1e2a}}
.chip{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;margin:1px 3px 1px 0;white-space:nowrap}}
.chip-ok{{background:#0a1a0a;border:1px solid #22cc6644;color:#22cc66}}
.chip-muted{{background:#1a1a1a;border:1px solid #33333388;color:#778}}
.stat{{display:inline-block;margin-right:14px;font-size:11px;color:#556}}
.stat b{{color:#ddcc00;font-size:14px;margin-right:4px}}
.val-row{{display:flex;align-items:baseline;gap:8px;padding:5px 0;border-bottom:1px solid #16161e;font-size:12px}}
.val-code{{font-family:monospace;color:#ddcc00;min-width:60px;font-weight:bold}}
.val-long{{color:#aab;flex:1}}
.val-short{{color:#667;font-size:10px;min-width:80px;text-align:right}}
.val-inactive{{opacity:0.45}}
</style></head>
<body>
{nav}
<div class="shell">
  <div class="sidebar">
    <div class="filters">
      <input id="qInput" placeholder="Search field name…" oninput="doSearch()">
    </div>
    <div class="list" id="list"></div>
  </div>
  <div class="detail" id="detail"><div class="muted">Select a field to see its translate values.</div></div>
</div>
<script>
const ENV = {repr(env)};
let _all = [];

async function api(url) {{
  try {{ const r = await fetch(url); return r.ok ? r.json() : null; }} catch {{ return null; }}
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function chip(cls, label) {{ return `<span class="chip ${{cls}}">${{esc(label)}}</span>`; }}

async function doSearch() {{
  const q = document.getElementById('qInput').value;
  const data = await api(`/api/peoplesoft/translate-fields?env=${{ENV}}&q=${{encodeURIComponent(q)}}&limit=500`);
  _all = (data?.items || []);
  const list = document.getElementById('list');
  list.innerHTML = _all.map((it, i) => `
    <div class="item" id="item-${{i}}" onclick="selectItem(${{i}}, '${{encodeURIComponent(it.fieldname)}}')">
      <div class="item-name">${{esc(it.fieldname)}}</div>
      <div class="item-meta">${{it.active_count||0}} active / ${{it.value_count||0}} total</div>
    </div>`).join('');
}}

async function selectItem(idx, name) {{
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${{idx}}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/xlat_field/${{name}}?env=${{ENV}}`);
  if (!d) {{ detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }}

  const uom = d._uom || {{}};
  const counts = uom.counts || {{}};
  const sections = d.sections || [];
  const activeSec = sections.find(s => s.id === 'active_values');
  const inactiveSec = sections.find(s => s.id === 'inactive_values');

  let html = `<div style="margin-bottom:12px">
    <span style="font-family:monospace;font-size:15px;font-weight:bold;color:#ddcc00">${{esc(uom.name||'')}}</span>
  </div>`;

  html += `<div style="margin:8px 0 14px">
    <span class="stat"><b>${{counts.active||0}}</b>Active</span>
    <span class="stat"><b>${{counts.inactive||0}}</b>Inactive</span>
    <span class="stat"><b>${{counts.total||0}}</b>Total</span>
  </div>`;

  function renderValueRows(items, inactive) {{
    return items.map(it =>
      `<div class="val-row${{inactive?' val-inactive':''}}">
         <span class="val-code">${{esc(it.name)}}</span>
         <span class="val-long">${{esc(it.meta||it.name)}}</span>
       </div>`
    ).join('');
  }}

  if (activeSec?.items?.length) {{
    html += `<h2>Active Values (${{activeSec.items.length}})</h2>`;
    html += renderValueRows(activeSec.items, false);
  }}
  if (inactiveSec?.items?.length) {{
    html += `<h2>Inactive Values (${{inactiveSec.items.length}})</h2>`;
    html += renderValueRows(inactiveSec.items, true);
  }}
  if (!activeSec && !inactiveSec) {{
    html += `<div class="muted">No translate values found.</div>`;
  }}

  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/project")
def admin_project(request: Request, env: str = "HCM"):
    nav = _nav_html("project", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>App Designer Projects</title>
{_NAV_CSS}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d0d11;color:#ccd;font-family:system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}}
.shell{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:300px;min-width:220px;border-right:1px solid #222;display:flex;flex-direction:column;overflow:hidden}}
.filters{{padding:10px;border-bottom:1px solid #1a1a22}}
.filters input{{width:100%;background:#111;border:1px solid #333;color:#ccd;padding:5px 8px;border-radius:3px;font-size:12px}}
.list{{overflow-y:auto;flex:1;padding:4px 0}}
.item{{padding:7px 12px;cursor:pointer;border-left:3px solid transparent;transition:background .1s}}
.item:hover{{background:#151520}}
.item.sel{{background:#12121e;border-left-color:#55ee55}}
.item-name{{font-family:monospace;font-size:12px;color:#55ee55;font-weight:bold}}
.item-meta{{font-size:10px;color:#556;margin-top:2px}}
.item-descr{{font-size:11px;color:#889;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.detail{{flex:1;overflow-y:auto;padding:20px}}
.muted{{color:#445;font-size:12px;padding:20px}}
h2{{color:#55ee55;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #1e1e2a}}
.kv-grid{{display:grid;grid-template-columns:140px 1fr;gap:4px 10px;font-size:12px;margin-bottom:10px}}
.kv-key{{color:#556;padding-top:1px}}
.kv-val{{color:#aab;font-family:monospace;word-break:break-all}}
.chip{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;margin:2px 4px 2px 0;white-space:nowrap}}
.chip-ok{{background:#0a1a0a;border:1px solid #22cc6644;color:#22cc66}}
.chip-info{{background:#001018;border:1px solid #00ccee44;color:#00ccee}}
.chip-muted{{background:#1a1a1a;border:1px solid #33333388;color:#778}}
.stat{{display:inline-block;margin-right:14px;font-size:11px;color:#556}}
.stat b{{color:#55ee55;font-size:14px;margin-right:4px}}
.field-row{{display:flex;align-items:center;gap:6px;padding:3px 0;border-bottom:1px solid #16161e;font-size:12px}}
.obj-name{{font-family:monospace;color:#aad;flex:1}}
.obj-meta{{color:#445;font-size:10px}}
</style></head>
<body>
{nav}
<div class="shell">
  <div class="sidebar">
    <div class="filters">
      <input id="qInput" placeholder="Search project name / description…" oninput="doSearch()">
    </div>
    <div class="list" id="list"></div>
  </div>
  <div class="detail" id="detail"><div class="muted">Select a project.</div></div>
</div>
<script>
const ENV = {repr(env)};
let _all = [];

async function api(url) {{
  try {{ const r = await fetch(url); return r.ok ? r.json() : null; }} catch {{ return null; }}
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function chip(cls, label) {{ return `<span class="chip ${{cls}}">${{esc(label)}}</span>`; }}

function fmtDate(d) {{
  if (!d) return '';
  return String(d).slice(0,10);
}}

async function doSearch() {{
  const q = document.getElementById('qInput').value;
  const data = await api(`/api/peoplesoft/projects?env=${{ENV}}&q=${{encodeURIComponent(q)}}&limit=500`);
  _all = (data?.items || []);
  const list = document.getElementById('list');
  list.innerHTML = _all.map((it, i) => `
    <div class="item" id="item-${{i}}" onclick="selectItem(${{i}}, '${{encodeURIComponent(it.projectname)}}')">
      <div class="item-name">${{esc(it.projectname)}}</div>
      <div class="item-meta">${{fmtDate(it.lastupddttm)}} · ${{esc(it.lastupdoprid||'')}} · ${{it.item_count||0}} objects</div>
      <div class="item-descr">${{esc(it.projectdescr||'')}}</div>
    </div>`).join('');
}}

async function selectItem(idx, name) {{
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${{idx}}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/project/${{name}}?env=${{ENV}}`);
  if (!d) {{ detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }}

  const uom = d._uom || {{}};
  const sections = d.sections || [];
  const ovSec = sections.find(s => s.id === 'overview');
  const tsSec = sections.find(s => s.id === 'type_summary');
  const objSecs = sections.filter(s => s.id.startsWith('objects_'));
  const counts = uom.counts || {{}};

  let html = `<div style="margin-bottom:12px">
    <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#55ee55">${{esc(uom.name||'')}}</span>
  </div>`;

  if (uom.title && uom.title !== uom.name) {{
    html += `<div style="color:#889;font-size:13px;margin-bottom:10px">${{esc(uom.title)}}</div>`;
  }}

  if (ovSec?.rows?.length) {{
    html += `<div class="kv-grid">`;
    for (const row of ovSec.rows) {{
      html += `<div class="kv-key">${{esc(row.label)}}</div><div class="kv-val">${{esc(String(row.value||''))}}</div>`;
    }}
    html += `</div>`;
  }}

  html += `<div style="margin:10px 0">
    <span class="stat"><b>${{counts.total_items||0}}</b>Objects</span>
    <span class="stat"><b>${{counts.types||0}}</b>Types</span>
  </div>`;

  if (tsSec?.chips?.length) {{
    html += `<h2>Object Types</h2><div style="margin-bottom:8px">`;
    html += tsSec.chips.map(c => chip(c.cls||'chip-muted', c.label)).join('');
    html += `</div>`;
  }}

  for (const sec of objSecs) {{
    if (sec.items?.length) {{
      html += `<h2>${{esc(sec.title)}}</h2>`;
      html += sec.items.map(it =>
        `<div class="field-row">
           <span class="obj-name">${{esc(it.name)}}</span>
           ${{it.meta ? `<span class="obj-meta">${{esc(it.meta)}}</span>` : ''}}
         </div>`
      ).join('');
      if (sec.items.length >= 100) {{
        html += `<div style="color:#556;font-size:10px;padding:4px 0">Showing first 100 of this type…</div>`;
      }}
    }}
  }}

  if (!ovSec && !tsSec && !objSecs.length) {{
    html += `<div class="muted">No items in project.</div>`;
  }}

  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/ptftest", response_class=HTMLResponse)
def admin_ptftest(request: Request, env: str = "HCM"):
    nav = _nav_html("ptftest", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>PTF Tests</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search test name or description…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <select id="tp" onchange="doSearch()"
      style="width:90px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 6px;border-radius:4px;font-size:12px">
      <option value="">All</option>
      <option value="S">Script</option>
      <option value="H">Shell</option>
      <option value="L">Library</option>
    </select>
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a PTF test to view its cases and commands.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

const TYPE_COLOR = {{S:'#ee8800', H:'#44aaff', L:'#aa66ff'}};
const TYPE_LABEL = {{S:'Script', H:'Shell', L:'Library'}};

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const tp = document.getElementById('tp').value;
  const url = `/api/peoplesoft/ptf-tests?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&ptf_type=${{encodeURIComponent(tp)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.pttst_name || '';
    const descr = (r.descr || '').trim().slice(0, 60);
    const tp2 = r.pttst_type || '';
    const tc = TYPE_COLOR[tp2] || '#778';
    const tl = TYPE_LABEL[tp2] || tp2;
    const cmds = r.cmd_count || 0;
    const folder = (r.pttst_parentfolder || '').split('\\\\').filter(Boolean).slice(-1)[0] || '';
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#ee8800;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        <span style="font-size:10px;font-weight:bold;color:${{tc}}">${{esc(tl)}}</span>
        ${{cmds ? `<span style="font-size:10px;color:#445">${{cmds}} cmds</span>` : ''}}
        ${{folder ? `<span style="font-size:10px;color:#334">${{esc(folder)}}</span>` : ''}}
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/ptf_test/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const caseSec = secs.find(s=>s.title?.includes('Cases'));
  const cmdSec = secs.find(s=>s.title?.includes('Command'));

  let html = `<h1 style="color:#ee8800;font-size:16px;margin:0 0 4px;font-family:monospace">${{esc(name)}}</h1>`;

  // Overview KV
  if (ovSec?.rows?.length) {{
    html += '<table style="border-collapse:collapse;margin-bottom:16px;font-size:13px">';
    ovSec.rows.forEach(row => {{
      if (!row.value || row.value === '—' || row.value === '0') return;
      html += `<tr><td style="color:#556;padding:2px 16px 2px 0;white-space:nowrap;vertical-align:top">${{esc(row.key)}}</td>
        <td style="color:#acd;word-break:break-word;max-width:500px">${{esc(String(row.value))}}</td></tr>`;
    }});
    html += '</table>';
  }}

  // Cases
  if (caseSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(caseSec.title)}}</h2>`;
    html += caseSec.items.map(c => {{
      const meta = c.meta ? `<span style="color:#445;font-size:11px;margin-left:10px">${{esc(c.meta)}}</span>` : '';
      return `<div style="padding:3px 8px;border-bottom:1px solid #0d1a2a;font-family:monospace;font-size:12px">
        <span style="color:#ee8800">${{esc(c.name)}}</span>${{meta}}
      </div>`;
    }}).join('');
  }}

  // Commands
  if (cmdSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:13px;margin:16px 0 6px">${{esc(cmdSec.title)}}</h2>`;
    html += '<div style="font-family:monospace;font-size:11px">';
    html += cmdSec.items.map(cmd => {{
      const meta = cmd.meta ? `<span style="color:#334;margin-left:10px;font-size:10px">${{esc(cmd.meta)}}</span>` : '';
      return `<div style="padding:2px 8px;border-bottom:1px solid #0d1520">
        <span style="color:#88a;min-width:160px;display:inline-block">${{esc(cmd.name)}}</span>${{meta}}
      </div>`;
    }}).join('');
    html += '</div>';
  }}

  if (!ovSec && !caseSec && !cmdSec) {{
    html += '<div class="muted">No detail available.</div>';
  }}
  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/archobj", response_class=HTMLResponse)
def admin_archobj(request: Request, env: str = "HCM"):
    nav = _nav_html("archobj", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Archive Objects</title>
<meta charset="utf-8">
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search archive object name or description…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select a Data Archive Object to view its source and history record mapping.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const url = `/api/peoplesoft/archive-objects?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.psarch_object || '';
    const descr = (r.descr || '').trim().slice(0, 60);
    const recs = r.record_count || 0;
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#aa66cc;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        ${{recs ? `<span style="font-size:10px;color:#445">${{recs}} records</span>` : ''}}
      </div>
      ${{descr ? `<div style="color:#445;font-size:10px;margin-top:1px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/archive_object/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENV)}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const recSec = secs.find(s=>s.title?.includes('Records'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  function itemList(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<div style="display:flex;flex-direction:column;gap:4px">` +
      sec.items.map(i=>{{
        const chips = (i.chips||[]).map(c=>`<span style="padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#1a0a2a;border:1px solid #334;color:#aa66cc">${{esc(c.label||c)}}</span>`).join(' ');
        return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #0d1520">
          <span style="font-family:monospace;font-size:11px;color:#c8d8e8">${{esc(i.name||'')}}</span>
          ${{chips}}
          ${{i.meta ? `<span style="font-size:10px;color:#445">${{esc(i.meta)}}</span>` : ''}}
        </div>`;
      }}).join('') + `</div>`;
  }}

  const ov = uom.overview || {{}};
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#aa66cc;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:16px">${{esc(uom.display_name||'')}}</div>
    <div style="margin-bottom:16px;font-size:12px;color:#778">
      Records: <b style="color:#aac">${{ov.record_count||0}}</b>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
    ${{recSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(recSec.title)}}</h3>${{itemList(recSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")






@router.get("/timezone", response_class=HTMLResponse)
def admin_timezone():
    return _shell("Timezone Explorer", "timezone", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#4499ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #4499ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #4499ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #4499ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #4499ee44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#4499ee}
button{background:#4499ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(68,153,238,.07);border-left-color:#4499ee55}
.item.sel{background:rgba(68,153,238,.12);border-left-color:#4499ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.kv-grid{display:grid;grid-template-columns:160px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search timezone code or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Timezones</h2>
    <div id="list" class="muted">Search to load timezones.</div>
  </div>
  <div class="content">
    <h2>Selected Timezone</h2>
    <div id="detail" class="muted">Select a timezone from the list.</div>
  </div>
</div>
<script>
const ENV = window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM');
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmtOffset(mins) {
  if (mins == null) return '\u2014';
  if (mins === 0) return 'UTC\u00b10';
  const sign = mins > 0 ? '+' : '-';
  const h = Math.floor(Math.abs(mins) / 60);
  const m = Math.abs(mins) % 60;
  return 'UTC' + sign + h + (m ? ':' + String(m).padStart(2, '0') : '');
}

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api('/api/peoplesoft/timezones?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No timezones found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    const meta = fmtOffset(r.utcoffset) + (r.observedst === 'Y' ? ' \u00b7 DST' : '') +
      (r.tzdescr ? ' \u2013 ' + esc((r.tzdescr||'').slice(0,45)) : '');
    return '<div class="item" id="tz-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.timezone) + '</div>' +
      '<div class="item-meta">' + meta + '</div>' +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectTz(+el.dataset.idx); });
  });
}

async function selectTz(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('tz-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api('/api/peoplesoft/object/timezone/' + encodeURIComponent(r.timezone) + '?env=' + ENV);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const ianaSec = sections.find(function(s) { return s.title && s.title.indexOf('IANA') >= 0; });
  const ov = d.overview || {};
  const offsetStr = fmtOffset(ov.utc_offset_minutes);

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  function chipList(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px">' +
      sec.items.map(function(c) {
        return '<span style="padding:2px 8px;border-radius:3px;font-size:11px;font-family:monospace;background:#0a1828;border:1px solid #1a3a5a;color:#7ab">' + esc(c.label||c) + '</span>';
      }).join('') + '</div>';
  }

  let html = '<h2 style="font-family:monospace;color:#4499ee;font-size:14px;margin:0 0 4px">' + esc(r.timezone) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">' + esc(d.display_name||'') + '</div>' +
    '<div style="margin-bottom:16px;font-size:12px;color:#778">Offset: <b style="color:#7ab;font-family:monospace">' +
    offsetStr + '</b>' + (ov.observes_dst ? ' \u00b7 <span style="color:#888">Observes DST</span>' : '') + '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (ianaSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(ianaSec.title) + '</h3>' + chipList(ianaSec);
  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/locale", response_class=HTMLResponse)
def admin_locale():
    return _shell("Locale Explorer", "locale", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#55cc55;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #55cc5533;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #55cc5522;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #55cc5522;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b0b;color:#d7faff;border:1px solid #55cc5544;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#55cc55}
button{background:#55cc55;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(85,204,85,.07);border-left-color:#55cc5555}
.item.sel{background:rgba(85,204,85,.12);border-left-color:#55cc55}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search locale code or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Locales</h2>
    <div id="list" class="muted">Search to load locales.</div>
  </div>
  <div class="content">
    <h2>Selected Locale</h2>
    <div id="detail" class="muted">Select a locale from the list.</div>
  </div>
</div>
<script>
const ENV = window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM');
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 250});
  if (q) params.set('q', q);
  const d = await api('/api/peoplesoft/locales?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No locales found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    return '<div class="item" id="lc-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.localecd) + '</div>' +
      '<div class="item-meta">' + esc((r.descr||'').slice(0,60)) + '</div>' +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectLocale(+el.dataset.idx); });
  });
}

async function selectLocale(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('lc-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api('/api/peoplesoft/object/locale/' + encodeURIComponent(r.localecd) + '?env=' + ENV);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec  = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const fmtSec = sections.find(function(s) { return s.title && s.title.indexOf('Format') >= 0; });

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8;font-family:monospace">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  let html = '<h2 style="font-family:monospace;color:#55cc55;font-size:14px;margin:0 0 4px">' + esc(r.localecd) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">' + esc(d.display_name||'') + '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec)  html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (fmtSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">Format Options</h3>' + kvTable(fmtSec);
  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/ae", response_class=HTMLResponse)
def admin_ae(request: Request, env: str = "HCM"):
    nav = _nav_html("ae", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>AE Programs</title>
<meta charset="utf-8">
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.list-item{{padding:6px 10px;border-radius:3px;cursor:pointer;margin-bottom:1px;border-bottom:1px solid #0d1520}}
.list-item:hover{{background:rgba(0,229,255,.06)}}
.list-item.sel{{background:rgba(0,229,255,.12);border-left:2px solid #00e5ff}}
.tab-row{{display:flex;gap:2px;margin-bottom:14px;border-bottom:1px solid #1a2a3a;padding-bottom:0}}
.tab{{padding:6px 14px;cursor:pointer;font-size:12px;color:#778;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab:hover{{color:#acd}}
.tab.on{{color:#00e5ff;border-bottom-color:#00e5ff}}
.pane{{display:none}}.pane.on{{display:block}}
.step-block{{margin-bottom:3px}}
.step-hdr{{display:flex;align-items:center;gap:6px;padding:5px 8px;background:#0a1520;border-radius:3px;cursor:pointer;border-left:2px solid transparent}}
.step-hdr:hover{{background:#0d1b2a;border-left-color:#00e5ff44}}
.step-body{{padding:6px 8px 6px 28px;background:#070f18;border-left:1px solid #1a2a3a;margin-bottom:2px;display:none}}
.step-body.open{{display:block}}
.chip-act{{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-weight:bold;font-family:monospace}}
.sec-hdr{{font-size:12px;font-weight:bold;color:#00e5ff;padding:8px 0 4px;margin-top:8px;border-bottom:1px solid #1a2a3a;margin-bottom:4px;font-family:monospace}}
.kv{{display:grid;grid-template-columns:160px 1fr;gap:2px 8px;font-size:12px;margin-bottom:12px}}
.kv-lbl{{color:#556;padding:2px 0}}
.kv-val{{color:#acd;font-family:monospace;word-break:break-all;padding:2px 0}}
.warn-box{{background:#1a0a00;border:1px solid #ff6a00;color:#ffa;padding:6px 10px;border-radius:3px;font-size:11px;margin-bottom:10px}}
pre.sql{{background:#030b14;border:1px solid #1a3a5a;padding:8px;border-radius:3px;font-size:11px;overflow-x:auto;color:#9bc;margin:6px 0 0;white-space:pre-wrap;word-break:break-all}}
.pc-link{{display:inline-block;padding:2px 8px;background:#1a0a2a;border:1px solid #aa66ff55;border-radius:3px;font-size:11px;color:#aa66ff;text-decoration:none}}
.pc-link:hover{{border-color:#aa66ff;color:#cc88ff}}
.call-link{{color:#ffaa22;font-family:monospace;font-size:11px;text-decoration:none}}
.call-link:hover{{color:#ffcc55;text-decoration:underline}}
table.plain{{border-collapse:collapse;font-size:12px;width:100%}}
table.plain th{{color:#445;font-weight:normal;text-align:left;padding:4px 12px 4px 0;border-bottom:1px solid #1a2a3a}}
table.plain td{{padding:4px 12px 4px 0;color:#acd;vertical-align:top;font-family:monospace;font-size:11px}}
table.plain tr:hover td{{background:#0a1520}}
.stat{{display:inline-block;padding:4px 12px;border:1px solid #1a3a5a;background:#050f18;border-radius:3px;margin:2px 4px 2px 0;font-size:11px}}
.stat b{{color:#00e5ff;font-size:15px;display:block}}
</style>
</head><body class="ds-body">
{nav}
<div style="display:grid;grid-template-columns:360px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:10px 8px;display:flex;flex-direction:column;gap:6px">
  <input id="q" placeholder="Search AE program or description…" oninput="doSearch()"
    style="background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px;width:100%">
  <div id="list" style="font-size:12px;flex:1"><div class="muted">Type to search AE programs.</div></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 24px">
  <div class="muted">Select an Application Engine program.</div>
</div>
</div>
<script>
{_ESC_JS}
const ENV = {repr(env)};
let _sel = null;

const ACT_COLOR = {{
  S:'#44aaff', P:'#aa66ff', C:'#ffaa22', L:'#667788', M:'#667788',
  D:'#22cc88', W:'#22cc88', U:'#22cc88', H:'#22cc88', X:'#22cc88', T:'#22cc88',
  A:'#99aacc', E:'#99aacc'
}};
const ACT_LABEL = {{
  S:'SQL', P:'PeopleCode', C:'Call', L:'Log', M:'Msg',
  D:'DoSel', W:'DoWhen', U:'DoUntil', H:'DoWhile', X:'DoSelX', T:'DoSelT',
  A:'Assign', E:'Exec'
}};

let _searchTimer = null;
function doSearch() {{
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(async () => {{
    const q = document.getElementById('q').value.trim();
    if (q.length < 2) {{ document.getElementById('list').innerHTML = '<div class="muted">Type 2+ chars to search.</div>'; return; }}
    document.getElementById('list').innerHTML = '<div class="muted">Searching…</div>';
    const data = await fetch(`/api/peoplesoft/ae?env=${{encodeURIComponent(ENV)}}&q=${{encodeURIComponent(q)}}&limit=200`)
      .then(r=>r.json()).catch(()=>({{items:[]}}));
    const items = data.items || [];
    if (!items.length) {{ document.getElementById('list').innerHTML = '<div class="muted">No programs found.</div>'; return; }}
    document.getElementById('list').innerHTML = items.map(r => {{
      const id = r.ae_applid || '';
      const desc = (r.descr || '').trim();
      const restart = r.ae_disable_restart === 'Y' ? ' <span style="color:#f90;font-size:9px">NO-RESTART</span>' : '';
      return `<div class="list-item${{_sel===id?' sel':''}}" onclick="loadProg(${{JSON.stringify(id)}})" data-id="${{esc(id)}}">
        <div style="font-family:monospace;font-size:12px;color:#44ddff">${{esc(id)}}${{restart}}</div>
        ${{desc?`<div style="font-size:10px;color:#445;margin-top:1px">${{esc(desc)}}</div>`:''}}
      </div>`;
    }}).join('');
  }}, 220);
}}

async function loadProg(id) {{
  _sel = id;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('sel', el.dataset.id === id));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const data = await fetch(`/api/peoplesoft/ae/${{encodeURIComponent(id)}}?env=${{encodeURIComponent(ENV)}}`)
    .then(r=>r.json()).catch(e=>({{error:String(e)}}));
  if (data.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(data.error)}}</div>`; return; }}
  detail.innerHTML = renderProg(id, data);
  document.querySelectorAll('.step-hdr').forEach(h => h.addEventListener('click', function() {{
    const body = this.nextElementSibling;
    if (body && body.classList.contains('step-body')) body.classList.toggle('open');
  }}));
}}

function renderProg(id, d) {{
  const rel = d._relationships || d.relationships || {{}};
  const steps = rel.steps || [];
  const sections = rel.sections || [];
  const stateRecs = rel.state_records || [];
  const procDefs = rel.process_definitions || [];
  const runs = rel.runtime_instances || [];
  const pcItems = rel.peoplecode || [];
  const warns = d.warnings || [];

  const warn_html = warns.map(w => {{
    const msg = typeof w === 'object' ? (w.detail || w.title || JSON.stringify(w)) : String(w);
    return `<div class="warn-box">${{esc(msg)}}</div>`;
  }}).join('');

  const sqlSteps  = steps.filter(s => s.ae_acttype === 'S').length;
  const pcSteps   = steps.filter(s => s.ae_acttype === 'P').length;
  const callSteps = steps.filter(s => s.ae_acttype === 'C').length;
  const statHtml = [['Sections',sections.length],['Steps',steps.length],['SQL',sqlSteps],
    ['PC',pcSteps],['Calls',callSteps],['State Recs',stateRecs.length],['Processes',procDefs.length],['Recent Runs',runs.length]]
    .map(([l,v]) => `<div class="stat"><b>${{v}}</b>${{l}}</div>`).join('');

  const raw = (d._metadata && d._metadata.raw) || {{}};
  const kvRows = [
    ['Last Updated', (String(raw.lastupddttm||'')).replace('T',' ').slice(0,19) || '—'],
    ['Updated By',   raw.lastupdoprid || '—'],
    ['Version',      raw.version != null ? String(raw.version) : '—'],
    ['Disable Restart', raw.ae_disable_restart==='Y' ? 'Yes' : 'No'],
  ];
  const kvHtml = `<div class="kv">${{kvRows.map(([k,v])=>`<div class="kv-lbl">${{esc(k)}}</div><div class="kv-val">${{esc(v)}}</div>`).join('')}}</div>`;
  const overviewHtml = `<div style="margin-bottom:16px">${{statHtml}}</div>${{kvHtml}}`;

  // Steps grouped by section
  const bySec = {{}};
  const secOrder = [];
  for (const st of steps) {{
    const sn = (st.ae_section||'').trim();
    if (!bySec[sn]) {{ bySec[sn]=[]; secOrder.push(sn); }}
    bySec[sn].push(st);
  }}
  const secMeta = {{}};
  for (const s of sections) secMeta[(s.ae_section||'').trim()] = s;

  let stepsHtml = '';
  for (const sn of secOrder) {{
    const si = secMeta[sn] || {{}};
    const secDesc = (si.descr||'').trim();
    const secType = si.section_type_label || '';
    const disabled = si.ae_disable==='Y' ? ' <span style="color:#f90;font-size:10px">[DISABLED]</span>' : '';
    stepsHtml += `<div class="sec-hdr">${{esc(sn)}}${{secType&&secType!=='Regular'
      ?` <span style="color:#778;font-size:10px;font-weight:normal">${{esc(secType)}}</span>`:''}}${{disabled}}${{secDesc
      ?` <span style="color:#445;font-size:10px;font-weight:normal"> — ${{esc(secDesc)}}</span>`:''}}\n</div>`;

    for (const st of bySec[sn]) {{
      const act = (st.ae_acttype||'').trim();
      const lbl = ACT_LABEL[act] || (st.action_type_label||'Step').split(' ')[0];
      const col = ACT_COLOR[act] || '#778';
      const stepName = (st.ae_step||'').trim();
      const desc = (st.descr||'').trim();
      const inactive = !st.is_active ? ' <span style="color:#f90;font-size:9px">INACTIVE</span>' : '';
      const commit = st.commits_after ? ' <span style="color:#22cc66;font-size:9px">COMMIT</span>' : '';

      let bodyParts = '';
      if (act === 'C') {{
        const ta = (st.ae_do_appl_id||'').trim();
        const ts = (st.ae_do_section||'').trim();
        if (ta || ts) {{
          const isSame = !ta || ta.toUpperCase()===id.toUpperCase();
          const lnk = isSame
            ? `<span class="call-link" style="cursor:pointer" onclick="event.stopPropagation();loadProg(${{JSON.stringify(isSame?id:ta)}})">${{esc(isSame?id:ta)}}.${{esc(ts)}}</span>`
            : `<a class="call-link" href="/admin/ae?q=${{encodeURIComponent(ta)}}&env=${{ENV}}" onclick="event.stopPropagation()">${{esc(ta)}}.${{esc(ts)}}</a>`;
          bodyParts += `<div style="margin-bottom:6px;color:#556;font-size:11px">→ ${{lnk}}</div>`;
        }}
      }}
      if (st.has_sql && st.sql_statements) {{
        for (const sql of st.sql_statements) {{
          const stype = sql.stmt_type ? `<span style="color:#445;font-size:10px;margin-right:4px">${{esc(sql.stmt_type)}}</span>` : '';
          bodyParts += `${{stype}}<pre class="sql">${{esc(sql.sql_text||'')}}</pre>`;
        }}
      }}
      if (st.has_peoplecode && st._links && st._links.peoplecode) {{
        bodyParts += `<a class="pc-link" href="${{esc(st._links.peoplecode)}}" onclick="event.stopPropagation()">View PeopleCode →</a>`;
      }}
      let meta = '';
      if (st.on_norows_label && st.on_norows_label!=='Continue') meta += `<span style="color:#445;font-size:10px">No rows: ${{esc(st.on_norows_label)}}</span> `;
      if (st.abend_action_label && st.abend_action_label!=='Abort') meta += `<span style="color:#445;font-size:10px">Abend: ${{esc(st.abend_action_label)}}</span>`;
      if (meta) bodyParts += `<div style="margin-top:4px">${{meta}}</div>`;

      const hasBody = !!bodyParts;
      const arrow = hasBody ? `<span style="color:#334;font-size:10px;margin-left:auto">▼</span>` : '';

      stepsHtml += `<div class="step-block">
<div class="step-hdr" style="border-left-color:${{col}}33">
  <span class="chip-act" style="background:${{col}}22;color:${{col}};border:1px solid ${{col}}44">${{lbl}}</span>
  <span style="font-family:monospace;font-size:12px;color:#c8d8e8">${{esc(stepName)}}</span>
  ${{inactive}}${{commit}}${{desc?`<span style="font-size:11px;color:#556">${{esc(desc)}}</span>`:''}}
  ${{arrow}}
</div>
${{hasBody?`<div class="step-body">${{bodyParts}}</div>`:''}}
</div>`;
    }}
  }}
  if (!stepsHtml) stepsHtml = '<div class="muted">No steps found.</div>';

  const stateHtml = stateRecs.length
    ? `<table class="plain"><thead><tr><th>Record</th><th>Default</th></tr></thead><tbody>` +
      stateRecs.map(r => {{
        const rn = (r.recname||r.ae_state_recname||'').trim();
        return `<tr><td><a href="/admin/record/${{encodeURIComponent(rn)}}?env=${{ENV}}" style="color:#44ddff">${{esc(rn)}}</a></td>
          <td>${{r.is_default?'<span style="color:#22cc66">✓</span>':''}}</td></tr>`;
      }}).join('') + '</tbody></table>'
    : '<div class="muted">No state records defined.</div>';

  const procsHtml = procDefs.length
    ? `<table class="plain"><thead><tr><th>Process Name</th><th>Type</th><th>Description</th></tr></thead><tbody>` +
      procDefs.map(p=>`<tr>
        <td style="color:#44ddff">${{esc((p.prcsname||'').trim())}}</td>
        <td style="color:#556">${{esc((p.prcstype||'').trim())}}</td>
        <td style="color:#acd">${{esc((p.descr||'').trim())}}</td></tr>`).join('') + '</tbody></table>'
    : '<div class="muted">No process definitions found.</div>';

  const SC={{'7':'#22cc66','8':'#ff4444','9':'#ff4444','5':'#ffaa22','6':'#ffaa22','2':'#00e5ff','3':'#00e5ff','4':'#44aaff','1':'#778','0':'#334'}};
  const SL={{'0':'New','1':'Pending','2':'Queued','3':'Initiated','4':'Processing','5':'Cancel','6':'Cancelled','7':'Success','8':'Error','9':'Sys Error','10':'Redirect','11':'Not Posted','12':'Blocked','13':'Hold','14':'Resend'}};
  const runsHtml = runs.length
    ? `<table class="plain"><thead><tr><th>Instance</th><th>Process</th><th>Requested</th><th>Ended</th><th>Status</th></tr></thead><tbody>` +
      runs.map(r=>{{
        const st=String(r.runstatus||'');
        return `<tr>
          <td style="color:#556">${{esc(String(r.prcsinstance||''))}}</td>
          <td style="color:#44ddff">${{esc((r.prcsname||'').trim())}}</td>
          <td style="color:#8ab">${{esc(String(r.rqstdttm||'')).replace('T',' ').slice(0,19)}}</td>
          <td style="color:#8ab">${{esc(String(r.enddttm||'')).replace('T',' ').slice(0,19)}}</td>
          <td><span style="color:${{SC[st]||'#778'}};font-weight:bold;font-size:11px">${{esc(SL[st]||st)}}</span></td></tr>`;
      }}).join('') + '</tbody></table>'
    : '<div class="muted">No recent runs found.</div>';

  const pcHtml = pcItems.length
    ? `<table class="plain"><thead><tr><th>Section</th><th>Step</th><th>Event</th><th>Updated</th><th></th></tr></thead><tbody>` +
      pcItems.map(p=>{{
        const lnk = p._links&&p._links.admin ? `<a class="pc-link" href="${{esc(p._links.admin)}}">View →</a>` : '';
        return `<tr>
          <td>${{esc((p.objectvalue2||'').trim())}}</td>
          <td>${{esc((p.objectvalue6||'').trim())}}</td>
          <td>${{esc((p.event_type||p.objectvalue7||'').trim())}}</td>
          <td style="color:#445">${{esc(String(p.lastupddttm||'')).replace('T',' ').slice(0,19)}}</td>
          <td>${{lnk}}</td></tr>`;
      }}).join('') + '</tbody></table>'
    : '<div class="muted">No PeopleCode programs found for this AE.</div>';

  return `<h1 style="font-family:monospace;color:#44ddff;font-size:15px;margin:0 0 4px">${{esc(id)}}</h1>
<div style="color:#445;font-size:12px;margin-bottom:12px">${{esc(d.description||'')}}</div>
${{warn_html}}
<div class="tab-row">
  <div class="tab on" onclick="setTab('ov',this)">Overview</div>
  <div class="tab" onclick="setTab('steps',this)">Steps (${{steps.length}})</div>
  <div class="tab" onclick="setTab('state',this)">State Records (${{stateRecs.length}})</div>
  <div class="tab" onclick="setTab('prcs',this)">Processes (${{procDefs.length}})</div>
  <div class="tab" onclick="setTab('runs',this)">Runtime (${{runs.length}})</div>
  <div class="tab" onclick="setTab('pc',this)">PeopleCode (${{pcItems.length}})</div>
</div>
<div id="pane-ov" class="pane on">${{overviewHtml}}</div>
<div id="pane-steps" class="pane">${{stepsHtml}}</div>
<div id="pane-state" class="pane">${{stateHtml}}</div>
<div id="pane-prcs" class="pane">${{procsHtml}}</div>
<div id="pane-runs" class="pane">${{runsHtml}}</div>
<div id="pane-pc" class="pane">${{pcHtml}}</div>`;
}}

function setTab(name, el) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('on'));
  el.classList.add('on');
  const pane = document.getElementById('pane-' + name);
  if (pane) pane.classList.add('on');
}}

(function() {{
  const params = new URLSearchParams(location.search);
  const q = params.get('q');
  if (q) {{ document.getElementById('q').value = q; doSearch(); }}
}})();
</script>
</body></html>""")

