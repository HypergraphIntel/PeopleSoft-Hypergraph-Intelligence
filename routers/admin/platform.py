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

  // AE deep link for Application Engine processes
  if ((uom.prcstype||'').trim() === 'Application Engine') {{
    const aeId = (uom.prcsname||'').trim();
    if (aeId) {{
      html += `<div style="margin-top:14px;padding-top:10px;border-top:1px solid #1a2a3a">
        <a href="/admin/ae?q=${{encodeURIComponent(aeId)}}&env=${{ENV}}" style="color:#22cc88;font-size:12px">Open in AE Explorer &#x2197;</a>
      </div>`;
    }}
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



@router.get("/component", response_class=HTMLResponse)
def admin_component(request: Request, env: str = "HCM"):
    nav = _nav_html("component", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Component Explorer</title>
<meta charset="utf-8">
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.list-item{{padding:6px 10px;border-radius:3px;cursor:pointer;margin-bottom:1px;border-bottom:1px solid #0d1520}}
.list-item:hover{{background:rgba(68,170,255,.06)}}
.list-item.sel{{background:rgba(68,170,255,.12);border-left:2px solid #44aaff}}
.tab-row{{display:flex;gap:2px;margin-bottom:14px;border-bottom:1px solid #1a2a3a;padding-bottom:0}}
.tab{{padding:6px 14px;cursor:pointer;font-size:12px;color:#778;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab:hover{{color:#acd}}
.tab.on{{color:#44aaff;border-bottom-color:#44aaff}}
.pane{{display:none}}.pane.on{{display:block}}
.kv{{display:grid;grid-template-columns:180px 1fr;gap:2px 8px;font-size:12px;margin-bottom:12px}}
.kv-lbl{{color:#556;padding:2px 0}}
.kv-val{{color:#acd;font-family:monospace;word-break:break-all;padding:2px 0}}
.stat-row{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.stat-pill{{background:rgba(68,170,255,.08);border:1px solid rgba(68,170,255,.25);border-radius:4px;padding:6px 14px;text-align:center}}
.stat-num{{font-size:20px;font-weight:bold;color:#44aaff;display:block}}
.stat-lbl{{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:.5px}}
.page-row{{display:flex;align-items:center;padding:5px 6px;border-bottom:1px solid #0d1520;font-size:12px}}
.page-row:hover{{background:rgba(68,170,255,.05)}}
.page-badge{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:2px;margin-right:4px;font-family:monospace}}
.sec-card{{background:#0a1520;border:1px solid rgba(68,170,255,.18);border-radius:4px;padding:10px 14px;margin-bottom:8px}}
.sec-card-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.sec-pl{{font-family:monospace;font-size:13px;color:#44aaff;font-weight:bold}}
.sec-roles{{font-size:11px;color:#8aabb8;margin-top:4px}}
.action-chip{{display:inline-block;font-size:10px;padding:1px 6px;border-radius:2px;margin-right:3px;background:rgba(68,170,255,.15);color:#44aaff;border:1px solid rgba(68,170,255,.3)}}
.action-chip.corr{{background:rgba(255,68,68,.12);color:#ff8888;border-color:rgba(255,68,68,.3)}}
.action-chip.upd{{background:rgba(34,204,136,.12);color:#44cc88;border-color:rgba(34,204,136,.3)}}
.pc-group{{margin-bottom:16px}}
.pc-group-hdr{{font-size:11px;font-weight:bold;color:#556;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #1a2a3a}}
.pc-row{{display:flex;align-items:center;gap:6px;padding:4px 6px;border-radius:3px;font-size:12px}}
.pc-row:hover{{background:rgba(170,102,255,.06)}}
.event-chip{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:2px;font-family:monospace;font-weight:bold}}
.portal-row{{padding:8px 10px;border-bottom:1px solid #0d1520;font-size:12px}}
.breadcrumb{{color:#556;font-size:11px;margin-bottom:3px}}
.rec-row{{display:flex;align-items:center;padding:4px 6px;border-bottom:1px solid #0d1520;font-size:12px}}
.rec-row:hover{{background:rgba(0,229,255,.04)}}
</style>
</head>
<body>
{nav}
<div style="display:grid;grid-template-columns:280px 1fr;height:calc(100vh - 42px)">
  <!-- LEFT RAIL -->
  <div style="border-right:1px solid #1a2a3a;display:flex;flex-direction:column;overflow:hidden">
    <div style="padding:10px;border-bottom:1px solid #1a2a3a">
      <div style="font-size:11px;color:#44aaff;font-weight:bold;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Component Explorer</div>
      <input id="q" type="text" placeholder="Search components..." autocomplete="off"
        style="width:100%;background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 8px;border-radius:3px;font-size:12px;outline:none">
      <div id="rail-status" style="font-size:11px;color:#446;margin-top:5px">&nbsp;</div>
    </div>
    <div id="rail-list" style="overflow-y:auto;flex:1;padding:4px"></div>
  </div>
  <!-- RIGHT PANEL -->
  <div id="detail-panel" style="overflow-y:auto;padding:20px">
    <div class="muted" style="margin-top:40px;text-align:center">Search for a component to explore its structure, security, and PeopleCode.</div>
  </div>
</div>
<script>
{_ESC_JS}
const ENV = "{env}";

async function api(url) {{
  try {{
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  }} catch(e) {{ return null; }}
}}

function fmt(s) {{
  if (!s) return '';
  if (s.includes('T')) {{
    const d = new Date(s);
    return isNaN(d) ? s : d.toLocaleDateString('en-AU', {{year:'numeric',month:'short',day:'numeric'}});
  }}
  return s;
}}

let debounce;
document.getElementById('q').addEventListener('input', () => {{
  clearTimeout(debounce);
  debounce = setTimeout(doSearch, 220);
}});
document.getElementById('q').addEventListener('keydown', e => {{
  if (e.key === 'Enter') {{ clearTimeout(debounce); doSearch(); }}
}});

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  document.getElementById('rail-status').textContent = 'Searching...';
  const rows = await api(`/api/peoplesoft/components?env=${{ENV}}&q=${{encodeURIComponent(q)}}&limit=80`);
  const list = document.getElementById('rail-list');
  if (!rows || !rows.length) {{
    list.innerHTML = '<div class="muted" style="padding:12px">No components found.</div>';
    document.getElementById('rail-status').textContent = '0 results';
    return;
  }}
  document.getElementById('rail-status').textContent = rows.length + ' result' + (rows.length===1?'':'s');
  list.innerHTML = rows.map(r => {{
    const name = r.pnlgrpname || '';
    const desc = r.descr || '';
    return `<div class="list-item" onclick="loadComponent(${{JSON.stringify(name)}})" data-name="${{esc(name)}}">
      <div style="font-family:monospace;font-size:12px;color:#c8d8e8">${{esc(name)}}</div>
      ${{desc ? `<div style="font-size:11px;color:#556;margin-top:1px">${{esc(desc)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadComponent(name) {{
  // highlight selected
  document.querySelectorAll('.list-item').forEach(el => {{
    el.classList.toggle('sel', el.dataset.name === name);
  }});
  const panel = document.getElementById('detail-panel');
  panel.innerHTML = '<div class="muted" style="margin-top:40px;text-align:center">Loading...</div>';

  // update URL
  history.replaceState(null,'',`/admin/component?q=${{encodeURIComponent(document.getElementById('q').value.trim())}}&name=${{encodeURIComponent(name)}}&env=${{ENV}}`);

  const d = await api(`/api/peoplesoft/object/component/${{encodeURIComponent(name)}}?env=${{ENV}}`);
  if (!d) {{
    panel.innerHTML = '<div style="color:#f88;padding:20px">Failed to load component data.</div>';
    return;
  }}
  renderComponent(d, name, panel);
}}

// Colour map for PC events
const EV_COLOR = {{
  'FieldChange':'#44aaff','FieldDefault':'#22bb88','FieldEdit':'#ffaa22',
  'FieldFormula':'#aa66ff','RowInit':'#5588cc','RowInsert':'#44cc88',
  'RowSelect':'#6688aa','RowDelete':'#ff6644','PreBuild':'#ffdd44',
  'PostBuild':'#ffcc33','Activate':'#22ccff','SaveEdit':'#ff8844',
  'SavePreChange':'#cc44aa','SavePostChange':'#aa44cc','WorkflowEnabled':'#778899',
  'SearchSave':'#44aadd','SearchInit':'#3399cc',
}};

function eventChip(ev) {{
  const c = EV_COLOR[ev] || '#667788';
  return `<span class="event-chip" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}44">${{esc(ev)}}</span>`;
}}

function actionChips(actions) {{
  if (!actions) return '';
  return actions.split(',').map(a => {{
    a = a.trim();
    const isCorr = a.toLowerCase().includes('correction');
    const isUpd  = a.toLowerCase().includes('update');
    return `<span class="action-chip${{isCorr?' corr':isUpd?' upd':''}}">${{esc(a)}}</span>`;
  }}).join('');
}}

function renderComponent(d, name, panel) {{
  const ov = d.overview || {{}};
  const secs = d.sections || [];
  const byName = {{}};
  secs.forEach(s => {{ if(s.name) byName[s.name] = s; }});

  // --- OVERVIEW TAB ---
  const pages_count = ov.pages || 0;
  const pl_count = ov.permissionlists || 0;
  const op_count = ov.operators || 0;
  const role_count = ov.roles || 0;
  const pc_count = ov.peoplecode || 0;
  const rec_count = ov.page_records || 0;
  const portal_count = ov.portal_refs || 0;
  const searchrec = (ov.searchrecname||'').trim();
  const addsrec   = (ov.addsrchrecname||'').trim();

  const ovHtml = `
    <div class="stat-row">
      <div class="stat-pill"><span class="stat-num">${{pages_count}}</span><span class="stat-lbl">Pages</span></div>
      <div class="stat-pill"><span class="stat-num">${{pl_count}}</span><span class="stat-lbl">Perm Lists</span></div>
      <div class="stat-pill"><span class="stat-num">${{role_count}}</span><span class="stat-lbl">Roles</span></div>
      <div class="stat-pill"><span class="stat-num">${{op_count}}</span><span class="stat-lbl">Operators</span></div>
      <div class="stat-pill"><span class="stat-num">${{pc_count}}</span><span class="stat-lbl">PC Events</span></div>
      <div class="stat-pill"><span class="stat-num">${{rec_count}}</span><span class="stat-lbl">Records</span></div>
      ${{portal_count ? `<div class="stat-pill"><span class="stat-num">${{portal_count}}</span><span class="stat-lbl">Portal Refs</span></div>` : ''}}
    </div>
    <div class="kv">
      <span class="kv-lbl">Component</span><span class="kv-val">${{esc(ov.pnlgrpname||name)}}</span>
      ${{ov.description||ov.descr ? `<span class="kv-lbl">Description</span><span class="kv-val" style="color:#c8d8e8">${{esc(ov.description||ov.descr)}}</span>` : ''}}
      <span class="kv-lbl">Market</span><span class="kv-val">${{esc(ov.market||'')}}</span>
      ${{searchrec ? `<span class="kv-lbl">Search Record</span><span class="kv-val"><a href="/admin/object/record/${{encodeURIComponent(searchrec)}}?env=${{ENV}}" style="color:#44aaff">${{esc(searchrec)}}</a></span>` : ''}}
      ${{addsrec && addsrec !== searchrec ? `<span class="kv-lbl">Add Search Rec</span><span class="kv-val"><a href="/admin/object/record/${{encodeURIComponent(addsrec)}}?env=${{ENV}}" style="color:#44aaff">${{esc(addsrec)}}</a></span>` : ''}}
      <span class="kv-lbl">Version</span><span class="kv-val">${{ov.version||''}}</span>
      <span class="kv-lbl">Last Updated</span><span class="kv-val">${{fmt(ov.lastupddttm||'')}}</span>
      <span class="kv-lbl">Updated By</span><span class="kv-val">${{esc(ov.lastupdoprid||'')}}</span>
    </div>
    <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap">
      <a href="/admin/compflow?component=${{encodeURIComponent(name)}}&env=${{ENV}}" style="color:#44aaff;font-size:12px">Event Flow &#x2197;</a>
      <a href="/admin/object/component/${{encodeURIComponent(name)}}?env=${{ENV}}" style="color:#44aaff;font-size:12px">Full Object View &#x2197;</a>
    </div>`;

  // --- PAGES TAB ---
  const pagesItems = (byName['Pages'] || {{}}).items || [];
  let pagesHtml = '';
  if (!pagesItems.length) {{
    pagesHtml = '<div class="muted">No pages found.</div>';
  }} else {{
    const BADGE = {{ 'Standard':'#44aaff','Subpage':'#667788','SecondaryPage':'#aa66ff','PopupPage':'#ffaa22','Header':'#556677','Footer':'#556677' }};
    pagesHtml = pagesItems.map(p => {{
      const lvl = p.level || 0;
      const rel = p.relationship || 'Standard';
      const col = BADGE[rel] || '#556677';
      const pnl = p.pnlname || '';
      const ttl = p.name || pnl;
      const rec = p.recname ? ` <span style="color:#446;font-size:10px">&#x2192; ${{esc(p.recname)}}</span>` : '';
      const link = pnl ? `/admin/page?name=${{encodeURIComponent(pnl)}}&env=${{ENV}}` : '#';
      return `<div class="page-row" style="padding-left:${{6+lvl*20}}px">
        <span class="page-badge" style="background:${{col}}22;color:${{col}};border:1px solid ${{col}}44">${{esc(rel)}}</span>
        <a href="${{link}}" style="color:#c8d8e8;font-family:monospace;font-size:12px;text-decoration:none" onmouseover="this.style.color='#44aaff'" onmouseout="this.style.color='#c8d8e8'">${{esc(pnl)}}</a>
        ${{ttl !== pnl ? `<span style="color:#556;margin-left:6px">${{esc(ttl)}}</span>` : ''}}
        ${{rec}}
      </div>`;
    }}).join('');
  }}

  // --- SECURITY TAB ---
  const whoItems = (byName['Who Has Access'] || {{}}).items || [];
  let secHtml = '';
  if (!whoItems.length) {{
    secHtml = '<div class="muted">No access data found.</div>';
  }} else {{
    const secData = byName['Who Has Access'] || {{}};
    const totPL = secData.data && secData.data.permissionlists || whoItems.length;
    const totRoles = secData.data && secData.data.roles || 0;
    const totOps = secData.data && secData.data.operators || 0;
    secHtml = `<div style="margin-bottom:12px;font-size:12px;color:#556">
      ${{totPL}} permission list(s) · ${{totRoles}} role(s) · ${{totOps}} operator(s) with access
    </div>`;
    secHtml += whoItems.map(pl => {{
      const via = pl.via_roles ? `<div class="sec-roles">Via roles: ${{esc(pl.via_roles)}}</div>` : '';
      const ops = pl.operators ? `<div style="font-size:11px;color:#446;margin-top:2px">${{pl.operators}} operator(s) directly assigned</div>` : '';
      const acts = actionChips(pl.actions);
      return `<div class="sec-card">
        <div class="sec-card-hdr">
          <a href="/admin/permissionlist/${{encodeURIComponent(pl.classid)}}?env=${{ENV}}" class="sec-pl">${{esc(pl.classid)}}</a>
          <div>${{acts}}</div>
        </div>
        ${{via}}${{ops}}
      </div>`;
    }}).join('');
  }}

  // --- PEOPLECODE TAB ---
  const pcItems = (byName['PeopleCode'] || {{}}).items || [];
  let pcHtml = '';
  if (!pcItems.length) {{
    pcHtml = '<div class="muted">No PeopleCode events found on this component.</div>';
  }} else {{
    // Group by event_scope
    const groups = {{}};
    pcItems.forEach(pc => {{
      const scope = pc.event_scope || 'other';
      (groups[scope] = groups[scope] || []).push(pc);
    }});
    const SCOPE_LABEL = {{
      'component': 'Component Events',
      'component_record': 'Component Record Events',
      'component_record_field': 'Component Record Field Events',
    }};
    const ORDER = ['component','component_record','component_record_field','other'];
    ORDER.forEach(scope => {{
      if (!groups[scope]) return;
      const lbl = SCOPE_LABEL[scope] || scope;
      const rows = groups[scope].map(pc => {{
        const path = (pc.semantic_path || []).slice(2); // drop component + market
        const pathHtml = path.map(p => `<span style="color:#445;margin:0 2px">›</span><span style="color:#8aabb8;font-family:monospace">${{esc(p.name)}}</span>`).join('');
        const ref = pc.encoded_reference || pc.reference || '';
        const lnk = ref ? `/admin/object/peoplecode/${{encodeURIComponent(ref)}}?env=${{ENV}}` : '#';
        return `<div class="pc-row">
          ${{eventChip(pc.event||pc.event_label||'?')}}
          <span style="color:#556;font-size:10px">${{pathHtml}}</span>
          <a href="${{lnk}}" style="color:#aa66ff;font-size:11px;margin-left:auto">View &#x2197;</a>
        </div>`;
      }}).join('');
      pcHtml += `<div class="pc-group"><div class="pc-group-hdr">${{lbl}} (${{groups[scope].length}})</div>${{rows}}</div>`;
    }});
  }}

  // --- PORTAL TAB ---
  const portalItems = (byName['Portal Registry'] || {{}}).items || [];
  let portalHtml = '';
  if (!portalItems.length) {{
    portalHtml = '<div class="muted">No portal registry entries.</div>';
  }} else {{
    portalHtml = portalItems.map(p => {{
      const path = p.nav_path || p.relationship || '';
      const lbl  = p.portal_label || '';
      const url  = p.portal_urltext || '';
      const portal = p.portal_name || '';
      const objname = p.portal_objname || '';
      const lnk = objname ? `/admin/object/portal_registry/${{encodeURIComponent(objname)}}?env=${{ENV}}` : '#';
      return `<div class="portal-row">
        <div class="breadcrumb">${{esc(portal)}} › ${{esc(path)}}</div>
        <div style="display:flex;align-items:center;gap:8px">
          ${{lbl ? `<span style="color:#c8d8e8">${{esc(lbl)}}</span>` : '<span style="color:#446">unlabeled</span>'}}
          ${{url ? `<code style="font-size:10px;color:#446">${{esc(url)}}</code>` : ''}}
          <a href="${{lnk}}" style="color:#44aaff;font-size:11px;margin-left:auto">Detail &#x2197;</a>
        </div>
      </div>`;
    }}).join('');
  }}

  // --- RECORDS TAB ---
  const recItems = (byName['Records Used By Pages'] || {{}}).items || [];
  let recHtml = '';
  if (!recItems.length) {{
    recHtml = '<div class="muted">No records found.</div>';
  }} else {{
    const shown = recItems.slice(0, 200);
    recHtml = `<div style="font-size:11px;color:#446;margin-bottom:8px">${{recItems.length}} record(s) used by pages${{recItems.length > 200 ? ' (showing first 200)' : ''}}</div>`;
    recHtml += shown.map(r => {{
      const rn = r.recname || r.name || '';
      const desc = r.descr || r.description || '';
      const rtype = r.rectype_label || '';
      const lnk = rn ? `/admin/object/record/${{encodeURIComponent(rn)}}?env=${{ENV}}` : '#';
      return `<div class="rec-row">
        <a href="${{lnk}}" style="color:#00e5ff;font-family:monospace;font-size:12px;flex:0 0 220px;text-decoration:none" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${{esc(rn)}}</a>
        ${{rtype ? `<span style="font-size:10px;color:#446;margin-right:8px">${{esc(rtype)}}</span>` : ''}}
        <span style="color:#556;font-size:11px">${{esc(desc)}}</span>
      </div>`;
    }}).join('');
  }}

  // --- BUILD PAGE ---
  panel.innerHTML = `
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <h1 style="margin:0;font-family:monospace;font-size:20px;color:#44aaff">${{esc(name)}}</h1>
      ${{ov.description || ov.descr ? `<span style="color:#778;font-size:14px">${{esc(ov.description||ov.descr)}}</span>` : ''}}
    </div>
    <div class="tab-row">
      <div class="tab on" onclick="setTab('overview',this)">Overview</div>
      <div class="tab" onclick="setTab('pages',this)">Pages (${{pages_count}})</div>
      <div class="tab" onclick="setTab('security',this)">Security (${{whoItems.length}} PLs)</div>
      <div class="tab" onclick="setTab('peoplecode',this)">PeopleCode (${{pcItems.length}})</div>
      <div class="tab" onclick="setTab('portal',this)">Portal (${{portalItems.length}})</div>
      <div class="tab" onclick="setTab('records',this)">Records (${{recItems.length}})</div>
    </div>
    <div id="pane-overview" class="pane on">${{ovHtml}}</div>
    <div id="pane-pages"    class="pane">${{pagesHtml}}</div>
    <div id="pane-security" class="pane">${{secHtml}}</div>
    <div id="pane-peoplecode" class="pane">${{pcHtml}}</div>
    <div id="pane-portal"   class="pane">${{portalHtml}}</div>
    <div id="pane-records"  class="pane">${{recHtml}}</div>`;
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
  const name = params.get('name');
  if (q) {{
    document.getElementById('q').value = q;
    doSearch().then(() => {{
      if (name) loadComponent(name);
    }});
  }} else if (name) {{
    loadComponent(name);
  }}
}})();
</script>
</body></html>""")


@router.get("/page", response_class=HTMLResponse)
def admin_page(request: Request, env: str = "HCM"):
    nav = _nav_html("page", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Page Explorer</title>
<meta charset="utf-8">
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.list-item{{padding:6px 10px;border-radius:3px;cursor:pointer;margin-bottom:1px;border-bottom:1px solid #0d1520}}
.list-item:hover{{background:rgba(136,136,255,.06)}}
.list-item.sel{{background:rgba(136,136,255,.12);border-left:2px solid #8888ff}}
.tab-row{{display:flex;gap:2px;margin-bottom:14px;border-bottom:1px solid #1a2a3a;padding-bottom:0}}
.tab{{padding:6px 14px;cursor:pointer;font-size:12px;color:#778;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab:hover{{color:#acd}}.tab.on{{color:#8888ff;border-bottom-color:#8888ff}}
.pane{{display:none}}.pane.on{{display:block}}
.kv{{display:grid;grid-template-columns:160px 1fr;gap:2px 8px;font-size:12px;margin-bottom:12px}}
.kv-lbl{{color:#556;padding:2px 0}}.kv-val{{color:#acd;font-family:monospace;word-break:break-all;padding:2px 0}}
.stat-row{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.stat-pill{{background:rgba(136,136,255,.08);border:1px solid rgba(136,136,255,.25);border-radius:4px;padding:6px 14px;text-align:center}}
.stat-num{{font-size:20px;font-weight:bold;color:#8888ff;display:block}}
.stat-lbl{{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:.5px}}
.rec-row{{display:flex;align-items:center;gap:8px;padding:5px 6px;border-bottom:1px solid #0d1520;font-size:12px}}
.rec-row:hover{{background:rgba(0,229,255,.04)}}
.scroll-badge{{display:inline-block;font-size:9px;padding:1px 4px;border-radius:2px;background:rgba(136,136,255,.15);color:#8888ff;border:1px solid rgba(136,136,255,.3);font-family:monospace}}
.comp-row{{display:flex;align-items:center;padding:6px 8px;border-bottom:1px solid #0d1520;font-size:12px}}
.comp-row:hover{{background:rgba(68,170,255,.05)}}
.pc-group{{margin-bottom:14px}}
.pc-group-hdr{{font-size:11px;font-weight:bold;color:#556;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;padding-bottom:3px;border-bottom:1px solid #1a2a3a}}
.pc-row{{display:flex;align-items:center;gap:6px;padding:3px 6px;border-radius:3px;font-size:11px}}
.pc-row:hover{{background:rgba(170,102,255,.06)}}
.event-chip{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:2px;font-family:monospace;font-weight:bold}}
.sec-card{{background:#0a1520;border:1px solid rgba(136,136,255,.18);border-radius:4px;padding:8px 12px;margin-bottom:6px}}
.action-chip{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:2px;margin-right:3px;background:rgba(68,170,255,.12);color:#44aaff;border:1px solid rgba(68,170,255,.25)}}
</style>
</head><body>
{nav}
<div style="display:grid;grid-template-columns:280px 1fr;height:calc(100vh - 42px)">
  <!-- RAIL -->
  <div style="border-right:1px solid #1a2a3a;display:flex;flex-direction:column;overflow:hidden">
    <div style="padding:10px;border-bottom:1px solid #1a2a3a">
      <div style="font-size:11px;color:#8888ff;font-weight:bold;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Page Explorer</div>
      <input id="q" type="text" placeholder="Search pages..." autocomplete="off"
        style="width:100%;background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 8px;border-radius:3px;font-size:12px;outline:none">
      <div id="rail-status" style="font-size:11px;color:#446;margin-top:5px">&nbsp;</div>
    </div>
    <div id="rail-list" style="overflow-y:auto;flex:1;padding:4px"></div>
  </div>
  <!-- DETAIL -->
  <div id="detail-panel" style="overflow-y:auto;padding:20px">
    <div class="muted" style="margin-top:40px;text-align:center">Search for a page to explore its records, components, and PeopleCode.</div>
  </div>
</div>
<script>
{_ESC_JS}
const ENV = "{env}";

async function api(url) {{
  try {{ const r = await fetch(url); if (!r.ok) return null; return await r.json(); }} catch(e) {{ return null; }}
}}
function fmt(s) {{
  if (!s) return '';
  const d = new Date(s);
  return isNaN(d) ? s : d.toLocaleDateString('en-AU', {{year:'numeric',month:'short',day:'numeric'}});
}}

const PNLTYPE = {{0:'Standard',1:'Subpage',2:'Secondary',3:'Summary',4:'Child'}};

let debounce;
document.getElementById('q').addEventListener('input', () => {{ clearTimeout(debounce); debounce = setTimeout(doSearch, 220); }});
document.getElementById('q').addEventListener('keydown', e => {{ if (e.key==='Enter') {{ clearTimeout(debounce); doSearch(); }} }});

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  document.getElementById('rail-status').textContent = 'Searching...';
  const rows = await api(`/api/peoplesoft/pages?env=${{ENV}}&q=${{encodeURIComponent(q)}}&limit=100`);
  const list = document.getElementById('rail-list');
  if (!rows || !rows.length) {{
    list.innerHTML = '<div class="muted" style="padding:12px">No pages found.</div>';
    document.getElementById('rail-status').textContent = '0 results';
    return;
  }}
  document.getElementById('rail-status').textContent = rows.length + ' result' + (rows.length===1?'':'s');
  list.innerHTML = rows.map(r => {{
    const name = r.pnlname || '';
    const desc = r.descr || '';
    const typeLbl = PNLTYPE[r.pnltype] || '';
    return `<div class="list-item" onclick="loadPage(${{JSON.stringify(name)}})" data-name="${{esc(name)}}">
      <div style="display:flex;align-items:center;gap:6px">
        <span style="font-family:monospace;font-size:12px;color:#c8d8e8">${{esc(name)}}</span>
        ${{typeLbl && typeLbl !== 'Standard' ? `<span style="font-size:9px;color:#556">${{esc(typeLbl)}}</span>` : ''}}
      </div>
      ${{desc && desc.trim() ? `<div style="font-size:11px;color:#556;margin-top:1px">${{esc(desc.trim())}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadPage(name) {{
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('sel', el.dataset.name === name));
  const panel = document.getElementById('detail-panel');
  panel.innerHTML = '<div class="muted" style="margin-top:40px;text-align:center">Loading...</div>';
  history.replaceState(null, '', `/admin/page?q=${{encodeURIComponent(document.getElementById('q').value.trim())}}&name=${{encodeURIComponent(name)}}&env=${{ENV}}`);

  const d = await api(`/api/peoplesoft/object/page/${{encodeURIComponent(name)}}?env=${{ENV}}`);
  if (!d) {{ panel.innerHTML = '<div style="color:#f88;padding:20px">Failed to load page data.</div>'; return; }}
  renderPage(d, name, panel);
}}

const EV_COLOR = {{
  'FieldChange':'#44aaff','FieldDefault':'#22bb88','FieldEdit':'#ffaa22','FieldFormula':'#aa66ff',
  'RowInit':'#5588cc','RowInsert':'#44cc88','RowSelect':'#6688aa','RowDelete':'#ff6644',
  'PreBuild':'#ffdd44','PostBuild':'#ffcc33','Activate':'#22ccff',
  'SaveEdit':'#ff8844','SavePreChange':'#cc44aa','SavePostChange':'#aa44cc',
}};
function evChip(ev) {{
  const c = EV_COLOR[ev] || '#667788';
  return `<span class="event-chip" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}44">${{esc(ev)}}</span>`;
}}

function renderPage(d, name, panel) {{
  const ov = d.overview || {{}};
  const secs = d.sections || [];
  const by = {{}};
  secs.forEach(s => {{ if (s.name) by[s.name] = s; }});

  const recItems  = (by['Records']     || {{}}).items || [];
  const compItems = (by['Components']  || {{}}).items || [];
  const pcItems   = (by['PeopleCode']  || {{}}).items || [];
  const whoItems  = (by['Who Has Access'] || {{}}).items || [];
  const subItems  = (by['Subpages']    || {{}}).items || [];
  const xferCount = ((by['Transfers']  || {{}}).data || {{}}).count || 0;

  // Overview
  const ovHtml = `
    <div class="stat-row">
      <div class="stat-pill"><span class="stat-num">${{ov.fields||0}}</span><span class="stat-lbl">Fields</span></div>
      <div class="stat-pill"><span class="stat-num">${{recItems.length}}</span><span class="stat-lbl">Records</span></div>
      <div class="stat-pill"><span class="stat-num">${{compItems.length}}</span><span class="stat-lbl">Components</span></div>
      <div class="stat-pill"><span class="stat-num">${{pcItems.length}}</span><span class="stat-lbl">PC Events</span></div>
      <div class="stat-pill"><span class="stat-num">${{ov.permissionlists||0}}</span><span class="stat-lbl">Perm Lists</span></div>
      ${{subItems.length ? `<div class="stat-pill"><span class="stat-num">${{subItems.length}}</span><span class="stat-lbl">Subpages</span></div>` : ''}}
      ${{xferCount ? `<div class="stat-pill"><span class="stat-num">${{xferCount}}</span><span class="stat-lbl">Transfers</span></div>` : ''}}
    </div>
    <div class="kv">
      <span class="kv-lbl">Page</span><span class="kv-val">${{esc(ov.pnlname||name)}}</span>
      ${{ov.descr && ov.descr.trim() ? `<span class="kv-lbl">Description</span><span class="kv-val" style="color:#c8d8e8">${{esc(ov.descr.trim())}}</span>` : ''}}
      <span class="kv-lbl">Type</span><span class="kv-val">${{esc(PNLTYPE[ov.pnltype]||'Standard')}}</span>
      <span class="kv-lbl">Version</span><span class="kv-val">${{ov.version||''}}</span>
      <span class="kv-lbl">Last Updated</span><span class="kv-val">${{fmt(ov.lastupddttm||'')}}</span>
      <span class="kv-lbl">Updated By</span><span class="kv-val">${{esc(ov.lastupdoprid||'')}}</span>
    </div>
    ${{subItems.length ? `<div style="margin-top:8px"><div style="font-size:11px;color:#556;margin-bottom:6px;font-weight:bold;text-transform:uppercase;letter-spacing:.5px">Subpages</div>${{subItems.map(s=>`<span style="font-family:monospace;font-size:11px;margin-right:10px"><a href="/admin/page?name=${{encodeURIComponent(s.pnlname||'')}}&env=${{ENV}}" style="color:#8888ff;text-decoration:none">${{esc(s.pnlname||'')}}</a></span>`).join('')}}</div>` : ''}}
    <div style="margin-top:12px">
      <a href="/admin/object/page/${{encodeURIComponent(name)}}?env=${{ENV}}" style="color:#8888ff;font-size:12px">Full Object View &#x2197;</a>
    </div>`;

  // Records tab
  const recsHtml = recItems.length ? (() => {{
    const real = recItems.filter(r => r.recname && r.recname.trim());
    return `<div style="font-size:11px;color:#446;margin-bottom:8px">${{real.length}} record(s) referenced on this page</div>`
      + real.map(r => {{
        const rn = r.recname.trim();
        const fc = r.field_count || 0;
        const usage = (r.usage || []).join(', ');
        return `<div class="rec-row">
          <a href="/admin/record/${{encodeURIComponent(rn)}}?env=${{ENV}}" style="color:#00e5ff;font-family:monospace;font-size:12px;flex:0 0 220px;text-decoration:none" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${{esc(rn)}}</a>
          <span style="color:#556;font-size:11px;flex:1">${{esc(usage)}}</span>
          <span class="scroll-badge">${{fc}} field${{fc===1?'':'s'}}</span>
        </div>`;
      }}).join('');
  }})() : '<div class="muted">No records found.</div>';

  // Components tab
  const compsHtml = compItems.length ? compItems.map(c => {{
    const cn = c.pnlgrpname || '';
    const mk = c.market || '';
    return `<div class="comp-row">
      <a href="/admin/component?name=${{encodeURIComponent(cn)}}&env=${{ENV}}" style="color:#44aaff;font-family:monospace;font-size:12px;flex:1;text-decoration:none" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${{esc(cn)}}</a>
      ${{mk ? `<span style="font-size:11px;color:#446">${{esc(mk)}}</span>` : ''}}
    </div>`;
  }}).join('') : '<div class="muted">No components reference this page.</div>';

  // PeopleCode tab — group by source component
  let pcHtml = '';
  if (!pcItems.length) {{
    pcHtml = '<div class="muted">No PeopleCode events on this page.</div>';
  }} else {{
    const groups = {{}};
    pcItems.forEach(pc => {{
      const comp = pc._source_component || pc.objectvalue1 || 'unknown';
      (groups[comp] = groups[comp] || []).push(pc);
    }});
    pcHtml = Object.entries(groups).map(([comp, pcs]) => {{
      const rows = pcs.slice(0, 30).map(pc => {{
        const ref = pc.encoded_reference || pc.reference || '';
        const lnk = ref ? `/admin/object/peoplecode/${{encodeURIComponent(ref)}}?env=${{ENV}}` : '#';
        const pathParts = (pc.semantic_path || []).slice(2);
        const pathHtml = pathParts.map(p => `<span style="color:#445;margin:0 2px">›</span><span style="color:#8aabb8;font-family:monospace">${{esc(p.name)}}</span>`).join('');
        return `<div class="pc-row">
          ${{evChip(pc.event||'?')}}
          <span style="color:#556;font-size:10px">${{pathHtml}}</span>
          <a href="${{lnk}}" style="color:#aa66ff;font-size:10px;margin-left:auto">View &#x2197;</a>
        </div>`;
      }}).join('');
      const extra = pcs.length > 30 ? `<div style="color:#446;font-size:10px;padding:3px 6px">+${{pcs.length-30}} more</div>` : '';
      return `<div class="pc-group">
        <div class="pc-group-hdr">
          <a href="/admin/component?name=${{encodeURIComponent(comp)}}&env=${{ENV}}" style="color:#acd;text-decoration:none">${{esc(comp)}}</a>
          <span style="margin-left:4px;color:#446">(${{pcs.length}} event${{pcs.length===1?'':'s'}})</span>
        </div>
        ${{rows}}${{extra}}
      </div>`;
    }}).join('');
  }}

  // Security tab
  const secHtml = whoItems.length ? (() => {{
    const wdata = (by['Who Has Access'] || {{}}).data || {{}};
    return `<div style="margin-bottom:12px;font-size:12px;color:#556">
      ${{wdata.permissionlists||whoItems.length}} permission list(s) · ${{wdata.roles||0}} role(s) · ${{wdata.operators||0}} operator(s) with access to this page
    </div>` + whoItems.map(pl => {{
      const via = pl.via_roles ? `<div style="font-size:11px;color:#8aabb8;margin-top:4px">Via: ${{esc(pl.via_roles)}}</div>` : '';
      const acts = (pl.actions||'').split(',').map(a => `<span class="action-chip">${{esc(a.trim())}}</span>`).join('');
      return `<div class="sec-card">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <a href="/admin/permissionlist/${{encodeURIComponent(pl.classid)}}?env=${{ENV}}" style="color:#ff9900;font-family:monospace;font-size:13px;font-weight:bold;text-decoration:none">${{esc(pl.classid)}}</a>
          <div>${{acts}}</div>
        </div>
        ${{via}}
      </div>`;
    }}).join('');
  }})() : '<div class="muted">No access data found.</div>';

  panel.innerHTML = `
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <h1 style="margin:0;font-family:monospace;font-size:20px;color:#8888ff">${{esc(name)}}</h1>
      ${{ov.descr && ov.descr.trim() ? `<span style="color:#778;font-size:14px">${{esc(ov.descr.trim())}}</span>` : ''}}
    </div>
    <div class="tab-row">
      <div class="tab on" onclick="setTab('overview',this)">Overview</div>
      <div class="tab" onclick="setTab('records',this)">Records (${{recItems.filter(r=>r.recname&&r.recname.trim()).length}})</div>
      <div class="tab" onclick="setTab('components',this)">Components (${{compItems.length}})</div>
      <div class="tab" onclick="setTab('peoplecode',this)">PeopleCode (${{pcItems.length}})</div>
      <div class="tab" onclick="setTab('pageowned',this,'${{esc(name)}}')">Page-Owned PeopleCode</div>
      <div class="tab" onclick="setTab('security',this)">Security (${{whoItems.length}} PLs)</div>
    </div>
    <div id="pane-overview"   class="pane on">${{ovHtml}}</div>
    <div id="pane-records"    class="pane">${{recsHtml}}</div>
    <div id="pane-components" class="pane">${{compsHtml}}</div>
    <div id="pane-peoplecode" class="pane">${{pcHtml}}</div>
    <div id="pane-pageowned"  class="pane"><span class="muted">Loading…</span></div>
    <div id="pane-security"   class="pane">${{secHtml}}</div>`;
}}

let _pageOwnedLoaded = null;
function setTab(name, el, pageName) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('on'));
  el.classList.add('on');
  const pane = document.getElementById('pane-' + name);
  if (pane) pane.classList.add('on');
  if (name === 'pageowned' && pageName && _pageOwnedLoaded !== pageName) {{
    _pageOwnedLoaded = pageName;
    api(`/api/peoplesoft/pages/${{encodeURIComponent(pageName)}}/owned-events?env=${{ENV}}`).then(d => {{
      const events = (d && d.events) || [];
      if (!events.length) {{
        pane.innerHTML = `<div class="muted">No Page-Owned PeopleCode (OBJECTID1=8, e.g. Page Activate) on <span style="font-family:monospace">${{esc(pageName)}}</span>.<br><span style="font-size:10px">This is a distinct, real PeopleTools category independent of Component-level PeopleCode (the PeopleCode tab above) — most pages have none; this environment has zero rows in this category.</span></div>`;
        return;
      }}
      pane.innerHTML = events.map(e => {{
        const modBadge = e.modified ? `<span style="color:#ffaa00;font-size:10px">&#9998; ${{esc(e.last_oprid)}}</span>` : '<span style="color:#556;font-size:10px">delivered</span>';
        return `<div class="pc-row"><span style="font-family:monospace;color:#8888ff;font-weight:bold">${{esc(e.event)}}</span> ${{modBadge}}</div>`;
      }}).join('');
    }}).catch(() => {{ pane.innerHTML = '<div class="muted">Failed to load page-owned events.</div>'; }});
  }}
}}

(function() {{
  const params = new URLSearchParams(location.search);
  const q = params.get('q');
  const name = params.get('name');
  if (q) {{
    document.getElementById('q').value = q;
    doSearch().then(() => {{ if (name) loadPage(name); }});
  }} else if (name) {{
    loadPage(name);
  }}
}})();
</script>
</body></html>""")


@router.get("/whatchanged", response_class=HTMLResponse)
def admin_whatchanged(request: Request, env: str = "HCM"):
    nav = _nav_html("whatchanged", env)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>What Changed</title>
<meta charset="utf-8">
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.toolbar{{padding:14px 20px;border-bottom:1px solid #1a2a3a;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#060d16}}
.quick-btn{{padding:4px 12px;border-radius:3px;cursor:pointer;font-size:12px;border:1px solid #1a2a3a;background:rgba(0,229,255,.05);color:#7faab2;transition:all .15s}}
.quick-btn:hover,.quick-btn.on{{background:rgba(0,229,255,.12);border-color:rgba(0,229,255,.3);color:#00e5ff}}
input[type=date]{{background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:4px 8px;border-radius:3px;font-size:12px}}
.run-btn{{padding:5px 16px;border-radius:3px;background:#00e5ff;color:#000;font-weight:bold;font-size:12px;border:none;cursor:pointer}}
.run-btn:hover{{background:#33eeff}}
.content{{padding:20px;max-width:1200px}}
.summary-bar{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}}
.type-pill{{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:3px;cursor:pointer;font-size:12px;border:1px solid transparent;transition:all .15s}}
.type-pill:hover{{filter:brightness(1.2)}}
.type-pill.off{{opacity:.4}}
.type-pill .cnt{{font-size:16px;font-weight:bold}}
.section{{margin-bottom:16px;border:1px solid #1a2a3a;border-radius:4px;overflow:hidden}}
.sec-hdr{{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;background:#0a1520}}
.sec-hdr:hover{{background:#0d1b2a}}
.sec-body{{display:none}}
.sec-body.open{{display:block}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{padding:5px 10px;text-align:left;color:#556;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1a2a3a;background:#070f18}}
td{{padding:5px 10px;border-bottom:1px solid #0d1520}}
tr:hover td{{background:rgba(0,229,255,.03)}}
.name-link{{color:#00e5ff;font-family:monospace;text-decoration:none}}
.name-link:hover{{text-decoration:underline}}
.dt{{color:#446;font-size:11px;white-space:nowrap}}
.op{{color:#667;font-size:11px}}
.desc{{color:#8aabb8;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.err{{color:#f88;font-size:11px;padding:8px 12px}}
#status{{font-size:12px;color:#446}}
</style>
</head><body>
{nav}
<div class="toolbar">
  <span style="font-size:13px;font-weight:bold;color:#00e5ff;letter-spacing:.5px">What Changed</span>
  <span style="color:#1a2a3a">|</span>
  <span style="font-size:11px;color:#446">Since:</span>
  <span class="quick-btn on" data-days="7" onclick="setQuick(this,7)">7 days</span>
  <span class="quick-btn" data-days="14" onclick="setQuick(this,14)">14 days</span>
  <span class="quick-btn" data-days="30" onclick="setQuick(this,30)">30 days</span>
  <span class="quick-btn" data-days="90" onclick="setQuick(this,90)">90 days</span>
  <input type="date" id="sinceDate" onchange="clearQuick()">
  <button class="run-btn" onclick="runAll()">Search</button>
  <span style="color:#1a2a3a">|</span>
  <span style="font-size:11px;color:#446">OPRID:</span>
  <input type="text" id="oprFilter" placeholder="Filter by…" oninput="applyOprFilter(this.value)"
    style="background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:4px 8px;border-radius:3px;font-size:12px;width:130px">
  <span id="status"></span>
  <div style="margin-left:auto;display:flex;align-items:center;gap:6px">
    <span style="font-size:11px;color:#446">Env:</span>
    <span style="font-size:12px;color:#00e5ff;font-weight:bold">{env}</span>
  </div>
</div>
<div class="content" id="content">
  <div class="muted" style="text-align:center;margin-top:40px">Select a time range and click Search to see what changed in {env}.</div>
</div>
<script>
{_ESC_JS}
const ENV = "{env}";

// Object type config — sql aliases must be N/D/DT/OP (Oracle uppercases them)
const TS = `TO_TIMESTAMP(:since, 'YYYY-MM-DD HH24:MI:SS')`;
const TYPES = [
  {{ id:'record',     label:'Records',     color:'#00e5ff', sql:`SELECT recname n, recdescr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSRECDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                               link: n => `/admin/record/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'component',  label:'Components',  color:'#44aaff', sql:`SELECT pnlgrpname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSPNLGRPDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                          link: n => `/admin/component?name=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'page',       label:'Pages',       color:'#8888ff', sql:`SELECT pnlname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSPNLDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                link: n => `/admin/page?name=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'ae',         label:'AE Programs', color:'#22cc88', sql:`SELECT ae_applid n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSAEAPPLDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                           link: n => `/admin/ae?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'field',      label:'Fields',      color:'#22ddcc', sql:`SELECT fieldname n, '' d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSDBFIELD WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                  link: n => `/admin/field/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'peoplecode', label:'PeopleCode',  color:'#aa66ff', sql:`SELECT objectvalue1||'.'||objectvalue2||'.'||objectvalue3||'.'||objectvalue4||'.'||objectvalue5 n, '' d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSPCMPROG WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`, link: n => `/admin/peoplecode/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'sql',        label:'SQL Defs',    color:'#4488ff', sql:`SELECT sqlid n, '' d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSSQLDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                      link: n => `/admin/object/sql_definition/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'permlist',   label:'Perm Lists',  color:'#ff9900', sql:`SELECT classid n, classdefndesc d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSCLASSDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                       link: n => `/admin/permissionlist/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'role',       label:'Roles',       color:'#ffaa22', sql:`SELECT rolename n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSROLEDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                               link: n => `/admin/role/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'menu',       label:'Menus',       color:'#cc8800', sql:`SELECT menuname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSMENUDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                link: n => `/admin/menu?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'query',      label:'Queries',     color:'#00bbdd', sql:`SELECT qryname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSQRYDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                  link: n => `/admin/query?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'project',    label:'Projects',    color:'#55ee55', sql:`SELECT projectname n, descrlong d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSPROJECTDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                     link: n => `/admin/object/project/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'prcsdefn',   label:'Processes',   color:'#bb77ff', sql:`SELECT prcsname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PS_PRCSDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                               link: n => `/admin/prcsdefn?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'package',    label:'App Packages',color:'#cc44ee', sql:`SELECT packageroot n, '' d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSPACKAGEDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                             link: n => `/admin/object/application_package/${{encodeURIComponent(n)}}?env=${{ENV}}` }},
  {{ id:'ibmsg',      label:'IB Messages', color:'#dd44aa', sql:`SELECT msgname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSMSGDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                  link: n => `/admin/ibmessage?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'ibrtng',     label:'IB Routings', color:'#00aabb', sql:`SELECT routingdefnname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSIBRTNGDEFN WHERE routingdefnname NOT LIKE '~%' AND lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                    link: n => `/admin/ibrtng?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'tree',       label:'Trees',       color:'#00bb66', sql:`SELECT tree_name n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSTREEDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                               link: n => `/admin/tree?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'xlat',       label:'Translate',   color:'#ddcc00', sql:`SELECT fieldname n, MAX(xlatlongname) d, MAX(lastupddttm) dt, MAX(lastupdoprid) op FROM SYSADM.PSXLATITEM WHERE lastupddttm >= ${{TS}} GROUP BY fieldname ORDER BY MAX(lastupddttm) DESC`,                link: n => `/admin/xlat?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
  {{ id:'ci',         label:'Comp Intfs',  color:'#00cccc', sql:`SELECT bcname n, descr d, lastupddttm dt, lastupdoprid op FROM SYSADM.PSBCDEFN WHERE lastupddttm >= ${{TS}} ORDER BY lastupddttm DESC`,                                                                    link: n => `/admin/ci?q=${{encodeURIComponent(n)}}&env=${{ENV}}` }},
];

let activeTypes = new Set(TYPES.map(t => t.id));
let results = {{}};
let currentSince = '';
let oprFilter = '';

function applyOprFilter(val) {{
  oprFilter = (val || '').trim().toUpperCase();
  if (currentSince) renderResults(currentSince);
}}

function isoDate(daysAgo) {{
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0,10);
}}

function sinceDate() {{
  return document.getElementById('sinceDate').value || isoDate(7);
}}

function setQuick(el, days) {{
  document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('on'));
  el.classList.add('on');
  document.getElementById('sinceDate').value = isoDate(days);
}}
function clearQuick() {{
  document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('on'));
}}

async function execSQL(sql, since) {{
  try {{
    const r = await fetch('/api/sqlws/execute', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        env: ENV,
        sql: sql,
        binds: {{since: since + ' 00:00:00'}},
        max_rows: 500,
        timeout_secs: 30
      }})
    }});
    if (!r.ok) return null;
    const d = await r.json();
    return d.rows || d.data || null;
  }} catch(e) {{ return null; }}
}}

function fmtDt(s) {{
  if (!s) return '';
  const d = new Date(s);
  if (isNaN(d)) return String(s).slice(0,16);
  return d.toLocaleDateString('en-AU', {{day:'2-digit',month:'short',year:'numeric'}}) + ' ' + d.toTimeString().slice(0,5);
}}

async function runAll() {{
  const since = sinceDate();
  const content = document.getElementById('content');
  const status = document.getElementById('status');
  status.textContent = 'Querying…';
  content.innerHTML = '<div class="muted" style="text-align:center;margin-top:30px">Loading changes since ' + esc(since) + '…</div>';

  results = {{}};
  currentSince = since;
  const promises = TYPES.map(async t => {{
    const rows = await execSQL(t.sql, since);
    results[t.id] = rows;
  }});
  await Promise.all(promises);

  renderResults(since);
}}

function renderResults(since) {{
  const status = document.getElementById('status');
  const content = document.getElementById('content');

  function filterRows(id) {{
    const raw = results[id] || [];
    if (!oprFilter) return raw;
    return raw.filter(r => (r.OP || r.op || '').trim().toUpperCase().includes(oprFilter));
  }}
  const total = TYPES.reduce((s,t) => s + filterRows(t.id).length, 0);
  const typesWithData = TYPES.filter(t => (results[t.id] || []).length > 0);

  const rawTotal = TYPES.reduce((s,t) => s + (results[t.id] ? results[t.id].length : 0), 0);
  if (rawTotal === 0) {{
    status.textContent = 'No changes found since ' + since;
    content.innerHTML = '<div class="muted" style="text-align:center;margin-top:40px">No changes found since ' + esc(since) + '.</div>';
    return;
  }}
  if (total === 0 && oprFilter) {{
    status.textContent = 'No results matching OPRID "' + oprFilter + '"';
    content.innerHTML = '<div class="muted" style="text-align:center;margin-top:40px">No changes by OPRID matching "' + esc(oprFilter) + '" since ' + esc(since) + '.</div>';
    return;
  }}

  status.textContent = `${{total}} change${{total===1?'':'s'}} across ${{typesWithData.length}} object type${{typesWithData.length===1?'':'s'}} since ${{since}}`;

  const oprMsg = oprFilter ? (' filtered by OPRID "' + oprFilter + '"') : '';
  // Summary pills
  let html = '<div class="summary-bar">';
  TYPES.forEach(t => {{
    const raw = results[t.id] || [];
    if (!raw.length) return;
    const rows = filterRows(t.id);
    const on = activeTypes.has(t.id);
    const cntLabel = oprFilter && rows.length !== raw.length ? `${{rows.length}}/${{raw.length}}` : rows.length;
    html += `<div class="type-pill${{on?'':' off'}}" style="background:${{t.color}}18;border-color:${{t.color}}44;color:${{t.color}}"
      onclick="toggleType('${{t.id}}',this)">
      <span class="cnt">${{cntLabel}}</span>
      <span>${{esc(t.label)}}</span>
    </div>`;
  }});
  html += '</div>';
  if (oprFilter) html += '<div style="font-size:11px;color:#7faab2;margin-bottom:10px">Showing rows where OPRID contains "' + esc(oprFilter) + '"</div>';

  // Sections
  TYPES.forEach(t => {{
    const raw = results[t.id] || [];
    if (!raw.length) return;
    const rows = filterRows(t.id);
    if (!rows.length) return;
    const on = activeTypes.has(t.id);
    const rawLen = raw.length;
    const rowsHtml = rows.map(r => {{
      const name = (r.N || r.n || r[0] || '').trim();
      const desc = (r.D || r.d || r[1] || '').trim();
      const dt   = r.DT || r.dt || r[2] || '';
      const op   = (r.OP || r.op || r[3] || '').trim();
      const href = t.link(name);
      return `<tr>
        <td><a class="name-link" href="${{esc(href)}}">${{esc(name)}}</a></td>
        <td class="desc">${{esc(desc)}}</td>
        <td class="dt">${{esc(fmtDt(dt))}}</td>
        <td class="op">${{esc(op)}}</td>
      </tr>`;
    }}).join('');

    html += `<div class="section" id="sec-${{t.id}}" style="display:${{on?'block':'none'}}">
      <div class="sec-hdr" onclick="toggleSec('${{t.id}}')">
        <span style="color:#778;font-size:10px">&#x25B6;</span>
        <span style="color:${{t.color}};font-weight:bold;font-size:12px">${{esc(t.label)}}</span>
        <span style="color:#556;font-size:11px">(${{rows.length}}${{oprFilter&&rows.length!==rawLen?'/'+rawLen:''}})${{rawLen===500?' <span style="color:#f90;font-size:10px">⚠ truncated at 500</span>':''}}</span>
      </div>
      <div class="sec-body open" id="body-${{t.id}}">
        <table>
          <thead><tr><th>Name</th><th>Description</th><th>Changed</th><th>By</th></tr></thead>
          <tbody>${{rowsHtml}}</tbody>
        </table>
      </div>
    </div>`;
  }});

  content.innerHTML = html;
}}

function toggleType(id, el) {{
  if (activeTypes.has(id)) {{ activeTypes.delete(id); el.classList.add('off'); }}
  else {{ activeTypes.add(id); el.classList.remove('off'); }}
  const sec = document.getElementById('sec-' + id);
  if (sec) sec.style.display = activeTypes.has(id) ? 'block' : 'none';
}}

function toggleSec(id) {{
  const body = document.getElementById('body-' + id);
  const hdr  = document.getElementById('sec-' + id)?.querySelector('.sec-hdr span');
  if (!body) return;
  body.classList.toggle('open');
  if (hdr) hdr.textContent = body.classList.contains('open') ? '▼' : '▶';
}}

// Initialise with 7-day default
document.getElementById('sinceDate').value = isoDate(7);

// Auto-run on load
runAll();
</script>
</body></html>""")


@router.get("/riskanalysis", response_class=HTMLResponse)
def admin_riskanalysis():
    return _shell("Change Risk Analyzer", "riskanalysis", content="""
<style>
.ra-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  padding:12px 16px;background:rgba(0,20,40,.6);border-bottom:1px solid #1a2a3a}
.ra-inp{background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 10px;
  border-radius:4px;font-size:13px;width:280px}
.ra-inp:focus{outline:none;border-color:#00e5ff80}
.ra-btn{padding:6px 16px;border-radius:4px;border:1px solid #00e5ff60;
  background:rgba(0,229,255,.1);color:#00e5ff;font-size:12px;cursor:pointer}
.ra-btn:hover{background:rgba(0,229,255,.2)}
.ra-body{padding:16px;overflow:auto;height:calc(100vh - 100px)}
.ra-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.ra-card{background:rgba(0,10,20,.6);border:1px solid #1a2a3a;border-radius:6px;padding:14px}
.ra-card-title{font-size:11px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.ra-stat{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.ra-num{font-size:28px;font-weight:700;color:#00e5ff;min-width:60px}
.ra-label{font-size:12px;color:#7faab2}
.ra-risk{display:inline-block;padding:3px 12px;border-radius:10px;font-size:11px;font-weight:600;letter-spacing:.5px}
.ra-risk.low{background:rgba(0,200,100,.15);border:1px solid #00c86440;color:#00e080}
.ra-risk.med{background:rgba(255,180,0,.15);border:1px solid #ffb40040;color:#ffd040}
.ra-risk.high{background:rgba(255,80,80,.15);border:1px solid #ff505040;color:#ff8080}
.ra-risk.crit{background:rgba(255,40,40,.25);border:1px solid #ff282840;color:#ff5050}
.ra-section{margin-bottom:16px}
.ra-sec-hdr{font-size:11px;color:#00e5ff;text-transform:uppercase;letter-spacing:.5px;
  padding:6px 0;border-bottom:1px solid #1a2a3a;margin-bottom:8px;
  display:flex;align-items:center;gap:8px}
.ra-tbl{width:100%;border-collapse:collapse;font-size:12px}
.ra-tbl th{background:#0a1828;color:#7faab2;padding:5px 8px;text-align:left;
  border-bottom:1px solid #1a2a3a;font-weight:500}
.ra-tbl td{padding:4px 8px;border-bottom:1px solid #0d1a28;vertical-align:middle}
.ra-tbl tr:hover td{background:rgba(0,229,255,.03)}
.ra-link{color:#00e5ff;text-decoration:none;font-size:11px}
.ra-link:hover{text-decoration:underline}
.ra-pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;margin:1px;
  background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.25);color:#7faab2}
.ra-bar{height:4px;background:#1a2a3a;border-radius:2px;margin-top:3px}
.ra-bar-fill{height:100%;border-radius:2px;background:#00e5ff;transition:width .4s}
.ra-none{color:#4a5a6a;font-size:12px;padding:20px;text-align:center}
.ra-warn{background:rgba(255,180,0,.1);border:1px solid #ffc00040;border-radius:4px;
  color:#ffc44d;font-size:11px;padding:8px 12px;margin-bottom:10px}
.ra-progress{font-size:11px;color:#7faab2}
</style>

<div class="ra-toolbar">
  <input class="ra-inp" id="projInput" placeholder="Project name e.g. PATCH862"
    onkeydown="if(event.key==='Enter')analyze()">
  <button class="ra-btn" onclick="analyze()">Analyze Risk</button>
  <span id="raStatus" class="ra-progress"></span>
</div>

<div class="ra-body" id="raBody">
  <div class="ra-none">Enter a PeopleSoft project name (from PSPROJECTDEFN) to analyze its deployment risk</div>
</div>

<script>
const TYPE_LABEL = {
  0:'Record', 2:'Page', 4:'Component', 5:'CI', 6:'Menu', 7:'App Engine', 8:'App Package',
  9:'Field', 10:'PS Query', 25:'SQL Def', 26:'Role', 27:'Perm List', 30:'AE SQL Step',
  33:'Process Def', 34:'Process Job', 43:'AE Activity', 44:'PeopleCode', 46:'Related Content',
  48:'Portal Registry', 49:'IB Handler', 51:'IB Routing', 55:'Classic Menu', 58:'Tree',
  74:'PS Query', 104:'App Class', 106:'Msg Catalog Set'
};

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function pick(r,...ks){for(const k of ks){const v=r[k]??r[k.toLowerCase()]??r[k.toUpperCase()];if(v!=null)return v;}return ''}

let _env=()=>(document.getElementById('globalEnv')||{}).value||'HCM';

async function sqlx(sql){
  const r=await fetch('/api/sqlws/execute',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({sql,env:_env(),binds:{},max_rows:500})});
  const d=await r.json();
  return d.rows||[];
}

function setStatus(msg){document.getElementById('raStatus').textContent=msg}

async function analyze(){
  const proj=(document.getElementById('projInput').value||'').trim().toUpperCase();
  if(!proj)return;
  setStatus('Loading project items…');
  const body=document.getElementById('raBody');
  body.innerHTML='<div class="ra-none">Analyzing…</div>';

  // Step 1: Load project definition
  const defnRows=await sqlx(`SELECT PROJECTNAME, DESCRLONG, LASTUPDDTTM, LASTUPDOPRID FROM SYSADM.PSPROJECTDEFN WHERE PROJECTNAME='${proj}'`);
  if(!defnRows.length){body.innerHTML='<div class="ra-none">Project not found: '+esc(proj)+'</div>';setStatus('');return;}
  const defn=defnRows[0];

  // Step 2: Load items grouped by type
  setStatus('Loading items…');
  const itemRows=await sqlx(`SELECT OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3, OBJECTVALUE4, UPGRADEACTION FROM SYSADM.PSPROJECTITEM WHERE PROJECTNAME='${proj}' ORDER BY OBJECTTYPE, OBJECTVALUE1`);

  // Group by type
  const byType={};
  for(const r of itemRows){
    const t=parseInt(pick(r,'OBJECTTYPE','objecttype')||0);
    if(!byType[t])byType[t]=[];
    byType[t].push(r);
  }
  const totalItems=itemRows.length;
  const typeCount=Object.keys(byType).length;

  // Extract key collections
  const records=(byType[0]||[]).map(r=>((pick(r,'OBJECTVALUE1','objectvalue1')||'').trim().toUpperCase())).filter(n=>n&&n!==' ');
  const components=(byType[4]||[]).map(r=>((pick(r,'OBJECTVALUE1','objectvalue1')||'').trim().toUpperCase())).filter(n=>n&&n!==' ');
  const aeprograms=(byType[7]||[]).map(r=>((pick(r,'OBJECTVALUE1','objectvalue1')||'').trim().toUpperCase())).filter(n=>n&&n!==' ');
  const pages=(byType[2]||[]).map(r=>((pick(r,'OBJECTVALUE1','objectvalue1')||'').trim().toUpperCase())).filter(n=>n&&n!==' ');

  // Step 3: Component security impact via dedicated bulk endpoint
  let userCount=0;
  let roleCount=0;
  let plCount=0;
  if(components.length){
    setStatus('Analyzing component access (this may take a moment)…');
    const compParam=components.slice(0,20).join(',');
    try{
      const sr=await fetch('/api/peoplesoft/security/bulk-component-access?components='+encodeURIComponent(compParam)+'&env='+_env());
      const sd=await sr.json();
      userCount=sd.user_count||0;
      roleCount=sd.role_count||0;
      plCount=sd.pl_count||0;
    }catch(e){/* skip */}
  }

  // Step 6: Compute risk score
  const risk=computeRisk(totalItems,records.length,components.length,userCount,aeprograms.length);

  setStatus('');

  // Render
  body.innerHTML=renderPage(proj,defn,{
    totalItems,typeCount,byType,records,components,aeprograms,pages,
    userCount,roleCount,plCount,sqrImpact,aeImpact,risk
  });
}

function computeRisk(total,recs,comps,users,ae){
  let score=0;
  if(recs>20)score+=30; else if(recs>5)score+=15; else if(recs>0)score+=5;
  if(comps>10)score+=25; else if(comps>3)score+=12; else if(comps>0)score+=5;
  if(users>100)score+=30; else if(users>20)score+=15; else if(users>0)score+=8;
  if(ae>5)score+=15; else if(ae>0)score+=8;
  if(total>500)score+=10; else if(total>100)score+=5;
  return score;
}

function riskLabel(score){
  if(score>=70)return['crit','CRITICAL'];
  if(score>=45)return['high','HIGH'];
  if(score>=20)return['med','MEDIUM'];
  return['low','LOW'];
}

function renderPage(proj,defn,d){
  const {totalItems,typeCount,byType,records,components,aeprograms,pages,
         userCount,roleCount,plCount,risk}=d;
  const [rCls,rLbl]=riskLabel(risk);
  const descr=((pick(defn,'DESCRLONG','descrlong')||'').split('\\n')[0]||'').trim().slice(0,120);
  const updby=(pick(defn,'LASTUPDOPRID','lastupdoprid')||'').trim();
  const upddt=(pick(defn,'LASTUPDDTTM','lastupddttm')||'').toString().slice(0,16);

  const statCards=`<div class="ra-grid">
    <div class="ra-card">
      <div class="ra-card-title">Project</div>
      <div style="font-size:14px;color:#c8d8e8;margin-bottom:6px">${esc(proj)}</div>
      ${descr?'<div style="font-size:11px;color:#7faab2;margin-bottom:6px">'+esc(descr)+'</div>':''}
      <div style="font-size:11px;color:#4a6a8a">${updby?'Last updated by '+esc(updby)+' ':''} ${upddt}</div>
    </div>
    <div class="ra-card">
      <div class="ra-card-title">Risk Assessment</div>
      <div style="margin-bottom:10px"><span class="ra-risk ${rCls}">${rLbl} RISK</span>
        <span style="font-size:11px;color:#4a6a8a;margin-left:8px">score: ${risk}/100</span></div>
      <div class="ra-bar"><div class="ra-bar-fill" style="width:${Math.min(risk,100)}%;background:${rCls==='crit'?'#ff5050':rCls==='high'?'#ff8040':rCls==='med'?'#ffd040':'#00e080'}"></div></div>
    </div>
  </div>
  <div class="ra-grid">
    <div class="ra-card">
      <div class="ra-card-title">Objects in Project</div>
      <div class="ra-stat"><span class="ra-num">${totalItems}</span><div class="ra-label">Total objects<br><span style="font-size:10px">${typeCount} distinct types</span></div></div>
      <div style="font-size:11px;color:#7faab2">
        ${records.length?'<span class="ra-pill">'+records.length+' Records</span>':''}
        ${components.length?'<span class="ra-pill">'+components.length+' Components</span>':''}
        ${aeprograms.length?'<span class="ra-pill">'+aeprograms.length+' AE Programs</span>':''}
        ${pages.length?'<span class="ra-pill">'+pages.length+' Pages</span>':''}
      </div>
    </div>
    <div class="ra-card">
      <div class="ra-card-title">Affected Users</div>
      <div class="ra-stat"><span class="ra-num">${userCount}</span>
        <div class="ra-label">Operators with access<br>to modified components</div></div>
      <div style="font-size:11px;color:#7faab2">
        ${roleCount?'<span class="ra-pill">'+roleCount+' Roles</span>':''}
        ${plCount?'<span class="ra-pill">'+plCount+' Perm Lists</span>':''}
        ${!components.length?'<span style="color:#4a6a8a">No components in project</span>':''}
      </div>
    </div>
  </div>`;

  // Object type breakdown
  let typeRows='';
  const sortedTypes=Object.entries(byType).sort((a,b)=>b[1].length-a[1].length);
  for(const [t,items] of sortedTypes){
    const lbl=TYPE_LABEL[parseInt(t)]||'Type '+t;
    const pct=Math.round((items.length/totalItems)*100);
    typeRows+=`<tr><td style="color:#c8d8e8">${esc(lbl)}</td>
      <td style="text-align:right;color:#00e5ff;font-weight:600">${items.length}</td>
      <td style="width:120px"><div class="ra-bar"><div class="ra-bar-fill" style="width:${pct}%"></div></div></td>
      <td style="font-size:10px;color:#4a6a8a;text-align:right">${pct}%</td></tr>`;
  }

  // Records table
  let recTable='';
  if(records.length){
    recTable=`<div class="ra-section">
      <div class="ra-sec-hdr">Records (${records.length})<span style="color:#4a6a8a;font-size:10px">SQL tables modified by this project</span></div>
      <table class="ra-tbl"><thead><tr><th>Record Name</th><th>View in Explorer</th></tr></thead><tbody>`;
    for(const r of records.slice(0,50)){
      recTable+=`<tr><td style="color:#c8d8e8">${esc(r)}</td>
        <td><a class="ra-link" href="/admin/object/record/${esc(r)}">Record Explorer →</a></td></tr>`;
    }
    if(records.length>50)recTable+=`<tr><td colspan="2" style="color:#4a6a8a;font-size:11px">… and ${records.length-50} more</td></tr>`;
    recTable+='</tbody></table></div>';
  }

  // Components table
  let compTable='';
  if(components.length){
    compTable=`<div class="ra-section">
      <div class="ra-sec-hdr">Components (${components.length})<span style="color:#4a6a8a;font-size:10px">End-user screens modified by this project</span></div>
      <table class="ra-tbl"><thead><tr><th>Component</th><th>Access Path</th><th>View</th></tr></thead><tbody>`;
    for(const c of components.slice(0,30)){
      compTable+=`<tr><td style="color:#c8d8e8">${esc(c)}</td>
        <td><a class="ra-link" href="/admin/access?comp=${esc(c)}">Who has access →</a></td>
        <td><a class="ra-link" href="/admin/object/component/${esc(c)}">Explorer →</a></td></tr>`;
    }
    if(components.length>30)compTable+=`<tr><td colspan="3" style="color:#4a6a8a;font-size:11px">… and ${components.length-30} more</td></tr>`;
    compTable+='</tbody></table></div>';
  }

  // AE Programs
  let aeTable='';
  if(aeprograms.length){
    aeTable=`<div class="ra-section">
      <div class="ra-sec-hdr">App Engine Programs (${aeprograms.length})<span style="color:#4a6a8a;font-size:10px">Batch programs modified by this project</span></div>
      <table class="ra-tbl"><thead><tr><th>AE Program</th><th>View</th></tr></thead><tbody>`;
    for(const ae of aeprograms.slice(0,20)){
      aeTable+=`<tr><td style="color:#c8d8e8">${esc(ae)}</td>
        <td><a class="ra-link" href="/admin/object/application_engine/${esc(ae)}">AE Explorer →</a></td></tr>`;
    }
    if(aeprograms.length>20)aeTable+=`<tr><td colspan="2" style="color:#4a6a8a;font-size:11px">… and ${aeprograms.length-20} more</td></tr>`;
    aeTable+='</tbody></table></div>';
  }

  return `${statCards}
  <div class="ra-section">
    <div class="ra-sec-hdr">Object Type Breakdown</div>
    <table class="ra-tbl"><thead><tr><th>Type</th><th style="text-align:right">Count</th><th>Share</th><th></th></tr></thead>
    <tbody>${typeRows}</tbody></table>
  </div>
  ${recTable}${compTable}${aeTable}`;
}

if(typeof window!=='undefined'){
  window.onEnvChange=function(){
    const v=(document.getElementById('projInput').value||'').trim();
    if(v)analyze();
  };
  document.addEventListener('DOMContentLoaded',()=>{
    const p=new URLSearchParams(location.search).get('proj');
    if(p){document.getElementById('projInput').value=p;analyze();}
  });
}
</script>""")
