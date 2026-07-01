import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/runtime", response_class=HTMLResponse)
def admin_runtime():
    return _shell("Runtime Monitor", "runtime", noscroll=False, content="""\
<style>
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin-bottom:4px;}
h2{color:#00e5ff;border-bottom:1px solid #00e5ff33;padding-bottom:6px;font-size:13px;
   letter-spacing:2px;text-transform:uppercase;margin:20px 0 10px;}
.card{border:1px solid #00e5ff44;box-shadow:0 0 10px rgba(0,229,255,.2);
      padding:16px;margin-top:16px;background:rgba(0,20,30,.75);}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px;}
th{border-bottom:1px solid #00e5ff44;padding:5px 8px;text-align:left;color:#00e5ff;
   font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #1e3040;padding:5px 8px;}
tr:hover td{background:rgba(0,229,255,.04);}
.status-bar{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0;}
.chip{padding:5px 12px;border-radius:3px;font-size:12px;font-weight:bold;white-space:nowrap;}
.chip-active{background:#003040;border:1px solid #00e5ff;color:#00e5ff;}
.chip-error{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-success{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-muted{background:#141a20;border:1px solid #334;color:#778;}
.s-run{color:#00e5ff;} .s-que{color:#ffaa00;} .s-err{color:#ff4444;}
.s-ok{color:#00cc66;} .s-hold{color:#778;}
.alert-box{background:#2a0000;border:1px solid #ff4444;
           padding:8px 14px;color:#ff8888;margin:8px 0;font-size:12px;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;
       font-size:11px;color:#000;margin:2px;}
button.sec{background:transparent;border:1px solid #00e5ff33;color:#00e5ff;}
select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;
       padding:5px 8px;font-size:12px;}
 .ctrl{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;margin-bottom:12px;}
 .lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;
   display:block;margin-bottom:3px;}
.runtime-nav{font-size:12px;margin-bottom:16px;color:#445;}
.mono{font-family:monospace;}
.empty{color:#445;font-style:italic;padding:10px 0;font-size:12px;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.tab-row{display:flex;gap:0;margin:10px 0 0;border-bottom:1px solid #00e5ff22;}
.tab{padding:5px 14px;cursor:pointer;font-size:11px;color:#556;
     border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.sql-cell{font-family:monospace;font-size:10px;color:#9ab;max-width:360px;
          overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.pct-bar{display:inline-block;background:#0b2030;width:70px;height:8px;
         border-radius:2px;vertical-align:middle;overflow:hidden;}
.pct-fill{height:100%;background:#00e5ff;}
.ts{font-size:10px;color:#446;}
/* ── process detail panel ── */
#procPanel{position:fixed;top:0;right:-520px;width:520px;height:100%;
  background:#070e14;border-left:1px solid #00e5ff44;overflow-y:auto;
  padding:20px;transition:right .25s ease;z-index:1000;box-shadow:-4px 0 24px rgba(0,0,0,.6);}
#procPanel.open{right:0;}
#procPanel h2{color:#00e5ff;font-size:12px;letter-spacing:2px;text-transform:uppercase;
  border-bottom:1px solid #00e5ff33;padding-bottom:6px;margin:16px 0 8px;}
#procPanel .close-btn{float:right;background:transparent;border:none;color:#778;
  font-size:18px;cursor:pointer;padding:0;}
#procPanel .close-btn:hover{color:#fff;}
.p-field{display:flex;margin:4px 0;font-size:12px;}
.p-label{color:#445;min-width:130px;flex-shrink:0;font-size:11px;text-transform:uppercase;letter-spacing:.5px;}
.p-value{color:#d7faff;font-family:monospace;word-break:break-all;}
.p-value a{color:#00e5ff;text-decoration:none;} .p-value a:hover{text-decoration:underline;}
.timeline-bar{display:flex;height:6px;border-radius:3px;overflow:hidden;margin:10px 0;background:#0b1b24;}
.tl-seg{height:100%;}
.tl-queued{background:#ffaa00;}
.tl-init{background:#00e5ff;}
.tl-proc{background:#00cc66;}
.tl-done{background:#556677;}
.tl-err{background:#ff4444;}
.proc-badge{display:inline-block;padding:2px 10px;border-radius:2px;font-size:11px;font-weight:bold;margin-left:8px;}
.pb-run{background:#001828;border:1px solid #00e5ff;color:#00e5ff;}
.pb-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.pb-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.pb-hold{background:#1a1a00;border:1px solid #778;color:#778;}
.pb-que{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.5);z-index:999;}
.overlay.open{display:block;}
</style>
<div class="overlay" id="overlay" onclick="closeProc()"></div>
<div id="procPanel">
  <button class="close-btn" onclick="closeProc()">&#x2715;</button>
  <h1 style="font-size:14px;margin:0 0 4px;color:#00e5ff;">PROCESS DETAIL</h1>
  <div id="procPanelBody"></div>
</div>
<div class="ctrl">
  <div><span class="lbl">Environment</span><select id="envSel" onchange="refresh()"></select></div>
  <div><span class="lbl">Oracle DB</span><select id="dbSel" onchange="refresh()"></select></div>
  <div>
    <button onclick="refresh()">&#8635; Refresh</button>
    <button class="sec" id="arBtn" onclick="toggleAR()">Auto: ON</button>
    <span class="ts" id="lastTs"></span>
  </div>
</div>

<!-- ── Active Alerts ── -->
<div class="card" id="alertsCard">
  <h2>Active Alerts <span id="alertBadge"></span></h2>
  <div id="alertsArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── App Server Domains ── -->
<div class="card">
  <h2>App Server Domains</h2>
  <div id="domArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Process Scheduler Servers ── -->
<div class="card">
  <h2>Process Scheduler Servers</h2>
  <div id="srvArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Process Scheduler ── -->
<div class="card">
  <h2>Process Scheduler</h2>
  <div id="procBar" class="status-bar"></div>
  <div class="tab-row proc-tabs">
    <div class="tab on"  onclick="procTab('active')">Active / Queued</div>
    <div class="tab"     onclick="procTab('errors')">Errors</div>
    <div class="tab"     onclick="procTab('ae')">App Engine</div>
    <div class="tab"     onclick="procTab('all')">All Recent</div>
  </div>
  <div id="paneActive" class="pane on"><div id="tblActive"></div></div>
  <div id="paneErrors" class="pane"><div id="tblErrors"></div></div>
  <div id="paneAe"     class="pane"><div id="tblAe"></div></div>
  <div id="paneAll"    class="pane"><div id="tblAll"></div></div>
</div>

<!-- ── Integration Broker ── -->
<div class="card">
  <h2>Integration Broker</h2>
  <div id="ibArea"></div>
</div>

<!-- ── Oracle ── -->
<div class="card">
  <h2>Oracle DB &mdash; <span id="dbLabel"></span></h2>
  <div id="oraBar" class="status-bar"></div>
  <div id="blockAlert"></div>
  <div class="tab-row ora-tabs">
    <div class="tab on" onclick="oraTab('sessions')">Active Sessions</div>
    <div class="tab"    onclick="oraTab('blocking')">Blocking</div>
    <div class="tab"    onclick="oraTab('longops')">Long Ops</div>
    <div class="tab"    onclick="oraTab('topsql')">Top SQL</div>
  </div>
  <div id="paneSessions" class="pane on"><div id="tblSessions"></div></div>
  <div id="paneBlocking" class="pane"><div id="tblBlocking"></div></div>
  <div id="paneLongops"  class="pane"><div id="tblLongops"></div></div>
  <div id="paneTopsql"   class="pane"><div id="tblTopsql"></div></div>
</div>

<!-- ── Oracle ASH ── -->
<div class="card">
  <h2>Oracle Active Session History &mdash; <span id="ashLabel"></span></h2>
  <div id="ashBar" class="status-bar"></div>
  <div id="ashArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Runtime Graph ── -->
<div class="card">
  <h2>Runtime Graph</h2>
  <div class="ctrl">
    <button onclick="loadRtGraph()">&#x2B58; Build Runtime Graph</button>
    <span id="graphStatus" class="ts"></span>
  </div>
  <div id="rtGraphArea" style="display:none;margin-top:10px;">
    <svg id="rtGraphSvg" width="100%" height="560"
         style="background:#030d16;border:1px solid #00e5ff22;display:block;cursor:grab;border-radius:3px;"></svg>
    <div id="rtGraphLegend" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;font-size:11px;"></div>
    <div id="rtGraphDetail" style="margin-top:6px;font-size:11px;color:#445;font-style:italic;min-height:18px;">
      Click a node to see details.
    </div>
  </div>
</div>

<script>
const RS = {
  '0':'s-err','1':'s-que','2':'s-run','3':'s-err',
  '4':'s-err','5':'s-hold','6':'s-que','7':'s-run',
  '8':'s-err','9':'s-ok'
};
let autoR = true, arTimer = null;
const INTERVAL = 30000;

const $ = id => document.getElementById(id);

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function chip(label, val, cls) {
  return `<div class="chip ${cls}">${label}: <b>${val}</b></div>`;
}

function empty(msg) { return `<div class="empty">${msg || 'No data.'}</div>`; }

function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// ── tab switching ──────────────────────────────────────
function procTab(name) {
  const tabs = document.querySelectorAll('.proc-tabs .tab');
  ['active','errors','ae','all'].forEach((n,i) => {
    if (tabs[i]) tabs[i].classList.toggle('on', n === name);
    const p = $(`pane${n.charAt(0).toUpperCase()+n.slice(1)}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

function oraTab(name) {
  const tabs = document.querySelectorAll('.ora-tabs .tab');
  ['sessions','blocking','longops','topsql'].forEach((n,i) => {
    if (tabs[i]) tabs[i].classList.toggle('on', n === name);
    const cap = n.charAt(0).toUpperCase()+n.slice(1);
    const p = $(`pane${cap}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

// ── process table ──────────────────────────────────────
function procTable(items) {
  if (!items || !items.length) return empty('No processes found.');
  const rows = items.map(r => {
    const cls = RS[r.runstatus] || '';
    const dt = (r.begindttm || '').replace('T',' ').substr(0,19);
    const tp = (r.prcstype||'').replace('Application Engine','AE').replace(/ (Process|Report)$/,'');
    return `<tr>
      <td><a class="mono" href="#" onclick="showProc(${r.prcsinstance});return false;">${r.prcsinstance}</a></td>
      <td class="mono" style="font-size:10px">${tp}</td>
      <td class="mono">${r.prcsname||''}</td>
      <td>${r.oprid||''}</td>
      <td class="mono" style="font-size:10px">${r.runcntlid||''}</td>
      <td style="font-size:10px">${r.serverbatch||''}</td>
      <td class="${cls}">${r.runstatus_label||r.runstatus}</td>
      <td class="ts">${dt}</td>
    </tr>`;
  }).join('');
  return `<table>
    <thead><tr>
      <th>Instance</th><th>Type</th><th>Program</th><th>Operator</th>
      <th>Run Control</th><th>Server</th><th>Status</th><th>Started</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ── IB rendering ───────────────────────────────────────
function renderIB(data) {
  const el = $('ibArea');
  if (!data) { el.innerHTML = empty('IB data unavailable.'); return; }
  const pub = data.ib?.published || [];
  const sub = data.ib?.subscribed || [];
  const warn = data.warnings || [];
  let html = '<div class="status-bar">';
  if (pub.length) {
    pub.forEach(r => {
      const label = r.status_label || `Pub ${r.pub_status}`;
      const cnt = r.cnt || 0;
      const cls = r.pub_status === '5' ? 'chip-error' : cnt > 0 ? 'chip-warn' : 'chip-muted';
      html += chip(label, cnt, cls);
    });
  } else {
    html += chip('Published', 0, 'chip-muted');
  }
  html += '<span style="color:#334;padding:0 6px">|</span>';
  if (sub.length) {
    sub.forEach(r => {
      const label = r.status_label || `Sub ${r.sub_status}`;
      const cnt = r.cnt || 0;
      const cls = r.sub_status === '5' ? 'chip-error' : cnt > 0 ? 'chip-warn' : 'chip-muted';
      html += chip(label, cnt, cls);
    });
  } else {
    html += chip('Subscribed', 0, 'chip-muted');
  }
  html += '</div>';
  warn.forEach(w => { html += `<div class="warn-msg">&#9888; ${w.message}</div>`; });
  el.innerHTML = html;
}

// ── Oracle rendering ───────────────────────────────────
function renderOraBar(counts) {
  let active=0, inactive=0, bg=0;
  counts.forEach(r => {
    if (r.type === 'BACKGROUND') bg += r.cnt;
    else if (r.status === 'ACTIVE') active += r.cnt;
    else inactive += r.cnt;
  });
  $('oraBar').innerHTML = [
    chip('Active', active, active>0 ? 'chip-active' : 'chip-muted'),
    chip('Inactive', inactive, 'chip-muted'),
    chip('Background', bg, 'chip-muted'),
  ].join('');
}

function renderBlocking(data) {
  const chains = data?.chains || [];
  const alertEl = $('blockAlert');
  const tblEl   = $('tblBlocking');
  if (!chains.length) {
    alertEl.innerHTML = '';
    if (tblEl) tblEl.innerHTML = empty('No blocking sessions detected.');
    return;
  }
  const waiterCount = chains.reduce((s,c) => s+(c.waiters?.length||0), 0);
  alertEl.innerHTML = `<div class="alert-box">
    &#9888; ${chains.length} blocking chain(s) &mdash; ${waiterCount} session(s) waiting
  </div>`;
  if (!tblEl) return;
  let html = '';
  chains.forEach(chain => {
    const b = chain.blocker || {};
    html += `<div style="margin:12px 0">
      <div style="color:#ff8888;font-size:11px;margin-bottom:4px">
        Blocker SID <b>${b.sid ?? chain.blocker_sid ?? '?'}</b>
        ${b.username ? `&mdash; ${b.username}` : ''}
        ${b.program  ? `(${(b.program||'').substr(0,30)})` : ''}
        ${b.event    ? `&mdash; event: ${b.event}` : ''}
      </div>
      <table><thead><tr>
        <th>Waiting SID</th><th>User</th><th>Program</th><th>Event</th><th>Wait (s)</th>
      </tr></thead><tbody>
      ${(chain.waiters||[]).map(w=>`<tr>
        <td class="mono">${w.sid}</td>
        <td>${w.username||''}</td>
        <td class="mono" style="font-size:10px">${(w.program||'').substr(0,30)}</td>
        <td style="font-size:10px">${w.event||''}</td>
        <td style="color:#ff4444">${w.seconds_in_wait??''}</td>
      </tr>`).join('')}
      </tbody></table>
    </div>`;
  });
  tblEl.innerHTML = html;
}

function renderSessions(items) {
  if (!items || !items.length) return empty('No active sessions.');
  return `<table><thead><tr>
    <th>SID</th><th>User</th><th>Program</th><th>Module</th>
    <th>Event</th><th>Wait (s)</th><th>SQL</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const wc = r.seconds_in_wait > 30 ? '#ff4444' : '#778';
    const prog = (r.program||'').replace(/@[\\w.]+$/,'').substr(0,22);
    return `<tr>
      <td class="mono">${r.sid}</td>
      <td>${r.username||''}</td>
      <td class="mono" style="font-size:10px">${prog}</td>
      <td style="font-size:10px">${r.module||''}</td>
      <td style="font-size:10px;color:#778">${r.event||''}</td>
      <td style="color:${wc}">${r.seconds_in_wait??''}</td>
      <td class="sql-cell" title="${(r.sql_text||'').replace(/"/g,'&quot;')}">${r.sql_text||''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

function renderLongops(items) {
  if (!items || !items.length) return empty('No long-running operations in progress.');
  return `<table><thead><tr>
    <th>SID</th><th>Operation</th><th>Target</th>
    <th>Progress</th><th>Elapsed (s)</th><th>Remaining (s)</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const pct = r.pct_done ?? 0;
    return `<tr>
      <td class="mono">${r.sid}</td>
      <td>${r.opname||''}</td>
      <td style="font-size:10px">${r.target||''}</td>
      <td>
        <span class="pct-bar"><span class="pct-fill" style="width:${pct}%"></span></span>
        &nbsp;${pct}%
      </td>
      <td>${r.elapsed_seconds??''}</td>
      <td style="color:#ffaa00">${r.time_remaining??''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

function renderTopSql(items) {
  if (!items || !items.length) return empty('No SQL statements in V$SQL cursor cache.');
  return `<table><thead><tr>
    <th>SQL ID</th><th>Schema</th><th>Execs</th>
    <th>Elapsed (s)</th><th>Elapsed/Exec</th><th>Buffer Gets</th><th>Last Active</th><th>SQL</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const epx = r.elapsed_per_exec??0;
    const eColor = epx > 1 ? '#ff4444' : epx > 0.1 ? '#ffaa00' : 'inherit';
    return `<tr>
      <td class="mono" style="font-size:10px">${r.sql_id||''}</td>
      <td style="font-size:10px">${r.parsing_schema_name||''}</td>
      <td style="text-align:right">${r.executions??0}</td>
      <td style="text-align:right">${r.elapsed_secs??0}</td>
      <td style="text-align:right;color:${eColor}">${epx}</td>
      <td style="text-align:right">${r.buffer_gets??0}</td>
      <td class="ts">${r.last_active||''}</td>
      <td class="sql-cell" title="${(r.sql_text||'').replace(/"/g,'&quot;')}">${r.sql_text||''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

// ── data loaders ───────────────────────────────────────
async function loadStatus() {
  const env = $('envSel').value;
  const db  = $('dbSel').value;
  if (!env) return;
  try {
    const s = await api(`/api/runtime/status?env=${env}${db ? '&db='+db : ''}`);

    // Process summary bar
    const t = s.process_summary?.totals || {};
    $('procBar').innerHTML = [
      chip('Running', t.active||0,   t.active  > 0 ? 'chip-active'  : 'chip-muted'),
      chip('Error',   t.error||0,    t.error   > 0 ? 'chip-error'   : 'chip-muted'),
      chip('Success', t.success||0,  t.success > 0 ? 'chip-success' : 'chip-muted'),
      chip('Other',   t.other||0,    'chip-muted'),
      chip('Recent Total', t.total||0, 'chip-muted'),
    ].join('');

    // AE tab
    $('tblAe').innerHTML = procTable(s.ae_running?.items || []);

    // IB
    renderIB(s.ib_summary);

    // Oracle from status (if db was provided)
    if (db && s.oracle_sessions) renderOraBar(s.oracle_sessions.counts || []);
    if (db && s.blocking)        renderBlocking(s.blocking);
  } catch(e) {
    $('procBar').innerHTML = `<span class="warn-msg">Status error: ${e.message}</span>`;
  }
}

async function loadAlerts() {
  const env = $('envSel').value;
  const db  = $('dbSel').value;
  if (!env) { $('alertsArea').innerHTML = ''; $('alertBadge').innerHTML = ''; return; }
  try {
    const url = `/api/runtime/alerts?env=${encodeURIComponent(env)}${db ? '&db='+encodeURIComponent(db) : ''}`;
    const r = await api(url);
    const alerts = r.alerts || [];

    // Badge on card title
    const errCnt = r.error_count || 0;
    const warnCnt = r.warn_count || 0;
    let badge = '';
    if (errCnt) badge += `<span class="chip chip-error" style="font-size:10px;padding:2px 8px;margin-left:6px">${errCnt} error${errCnt>1?'s':''}</span>`;
    if (warnCnt) badge += `<span class="chip chip-warn" style="font-size:10px;padding:2px 8px;margin-left:6px">${warnCnt} warning${warnCnt>1?'s':''}</span>`;
    $('alertBadge').innerHTML = badge;
    $('alertsCard').style.borderColor = errCnt ? '#ff444466' : warnCnt ? '#ffaa0066' : '#00e5ff44';

    if (!alerts.length) {
      $('alertsArea').innerHTML = `<div class="empty" style="color:#00cc66">&#x2714; All clear — no active alerts</div>`;
      return;
    }

    let html = '';
    alerts.forEach(a => {
      const col = a.severity === 'error' ? '#ff4444' : '#ffaa00';
      const icon = a.severity === 'error' ? '&#x26A0;' : '&#x25B2;';
      const link = a.data?._links?.admin ? `<a href="${esc(a.data._links.admin)}" style="color:#00e5ff;font-size:10px;margin-left:8px">&#x2192; View</a>` : '';
      html += `<div class="alert-box" style="border-color:${col};color:${col};display:flex;align-items:flex-start;gap:8px;margin:4px 0">
        <span style="font-size:16px;line-height:1">${icon}</span>
        <div><span style="font-size:10px;opacity:.7;text-transform:uppercase;letter-spacing:1px">[${esc(a.code)}]</span>
          <span style="margin-left:6px">${esc(a.message)}</span>${link}</div>
      </div>`;
    });
    $('alertsArea').innerHTML = html;
  } catch(e) {
    $('alertsArea').innerHTML = `<span class="muted" style="font-size:12px">Alerts unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadDomains() {
  const env = $('envSel').value;
  if (!env) { $('domArea').innerHTML = '<span class="muted" style="font-size:12px">No environment selected.</span>'; return; }
  try {
    const d = await api(`/api/runtime/domains?env=${env}`);
    const items = d.items || [];
    const warnings = d.warnings || [];
    if (!items.length) {
      const wmsg = warnings.length ? warnings.map(w => esc(w.message||String(w))).join(' ') : 'No domain data found.';
      $('domArea').innerHTML = `<span class="muted" style="font-size:12px">${wmsg}</span>`;
      return;
    }
    const TYPE_CLS = {
      app_server:        'chip-success',
      process_scheduler: 'chip-warn',
      web:               'chip-info',
      ib:                'chip-muted',
    };
    let html = `<table><thead><tr>
      <th>Domain</th><th>Type</th><th>Host</th><th>Port</th><th>Listeners</th>
    </tr></thead><tbody>`;
    for (const dom of items) {
      const cls = TYPE_CLS[dom.domain_type] || 'chip-muted';
      const altPort = dom.alt_port ? ` / ${esc(dom.alt_port)}` : '';
      html += `<tr>
        <td class="mono">${esc(dom.domain_name)}</td>
        <td><span class="chip ${cls}" style="font-size:10px;padding:2px 8px;">${esc(dom.domain_type_label)}</span></td>
        <td class="mono" style="font-size:11px">${esc((dom.hosts||[]).join(', '))}</td>
        <td class="mono" style="font-size:11px">${esc(dom.primary_port||'—')}${altPort}</td>
        <td style="text-align:center;color:#8ab">${dom.listener_count}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    if (d.source_view) {
      html += `<div style="font-size:9px;color:#334;margin-top:4px;text-align:right;">Source: ${esc(d.source_view)}</div>`;
    }
    $('domArea').innerHTML = html;
  } catch(e) {
    $('domArea').innerHTML = `<span class="muted" style="font-size:12px">Domains unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadServers() {
  const env = $('envSel').value;
  if (!env) { $('srvArea').innerHTML = '<span class="muted" style="font-size:12px">No environment selected.</span>'; return; }
  try {
    const d = await api(`/api/runtime/servers?env=${env}`);
    const items = d.items || [];
    if (!items.length) {
      $('srvArea').innerHTML = '<span class="muted" style="font-size:12px">PSSERVERSTAT not accessible or no servers found.</span>';
      return;
    }
    const STATUS_CLS = { '3': 'chip-success', '2': 'chip-warn', '1': 'chip-muted', '5': 'chip-error' };
    let html = '<table><thead><tr><th>Server</th><th>Status</th><th>Host</th><th>AE Servers</th><th>Max CPU</th><th>Last Updated</th></tr></thead><tbody>';
    for (const s of items) {
      const cls = STATUS_CLS[String(s.serverstatus)] || 'chip-muted';
      const dt = (s.lastupddttm || '').replace('T',' ').substr(0,19);
      html += `<tr>
        <td class="mono">${esc(s.servername||'')}</td>
        <td><span class="chip ${cls}" style="font-size:10px;padding:2px 8px;">${esc(s.serverstatus_label||'')}</span></td>
        <td class="mono" style="font-size:11px">${esc(s.srvrhostname||'')}</td>
        <td style="text-align:center">${s.schdlraesrvcnt ?? '—'}</td>
        <td style="text-align:center">${s.maxcpu ?? '—'}</td>
        <td class="mono" style="font-size:10px">${dt}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    if (d.warnings && d.warnings.length) {
      html += d.warnings.map(w => `<div class="alert-box" style="margin-top:6px">${esc(w)}</div>`).join('');
    }
    $('srvArea').innerHTML = html;
  } catch(e) {
    $('srvArea').innerHTML = `<span class="muted" style="font-size:12px">Servers unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadProcesses() {
  const env = $('envSel').value;
  if (!env) return;
  const [active, errors, all] = await Promise.allSettled([
    api(`/api/runtime/processes?env=${env}&status=1,2,6,7&limit=50`),
    api(`/api/runtime/processes?env=${env}&status=0,3,4,8&limit=50`),
    api(`/api/runtime/processes?env=${env}&limit=100`),
  ]);
  $('tblActive').innerHTML = procTable(active.value?.items || []);
  $('tblErrors').innerHTML = procTable(errors.value?.items || []);
  $('tblAll').innerHTML    = procTable(all.value?.items    || []);
}

async function loadOracle() {
  const db = $('dbSel').value;
  if (!db) {
    $('tblSessions').innerHTML = empty('Select an Oracle database above.');
    return;
  }
  $('dbLabel').textContent = db;

  const [sessions, counts, blocking, longops, topsql] = await Promise.allSettled([
    api(`/api/runtime/oracle?db=${db}&limit=50`),
    api(`/api/runtime/sessions?db=${db}`),
    api(`/api/runtime/blocking?db=${db}`),
    api(`/api/runtime/longops?db=${db}`),
    api(`/api/runtime/sql?db=${db}&limit=20`),
  ]);

  $('tblSessions').innerHTML = renderSessions(sessions.value?.items || []);
  if (counts.value) renderOraBar(counts.value.counts || []);
  renderBlocking(blocking.value || {chains:[]});
  $('tblLongops').innerHTML = renderLongops(longops.value?.items || []);
  $('tblTopsql').innerHTML  = renderTopSql(topsql.value?.items   || []);
}

const _WC_COLOR = {
  'CPU': '#00cc66', 'User I/O': '#00aaff', 'System I/O': '#0066cc',
  'Commit': '#ffaa00', 'Lock': '#ff4444', 'Concurrency': '#ff8800',
  'Network': '#aa66ff', 'Application': '#cc4466', 'Other': '#778',
  'Administrative': '#556', 'Configuration': '#445',
};

async function loadAsh() {
  const db = $('dbSel').value;
  if (!db) { $('ashArea').innerHTML = ''; $('ashBar').innerHTML = ''; return; }
  $('ashLabel').textContent = db;
  try {
    const [summary, topSql] = await Promise.all([
      api(`/api/runtime/ash?db=${encodeURIComponent(db)}&minutes=30`),
      api(`/api/runtime/ash/sql?db=${encodeURIComponent(db)}&minutes=30&limit=10`),
    ]);
    const wcs = summary.wait_classes || [];
    const total = summary.total_samples || 0;

    // Wait class chips
    let barHtml = wcs.map(wc => {
      const col = _WC_COLOR[wc.wait_class] || '#778';
      return `<div class="chip" style="border-color:${col}44;color:${col};background:${col}11">${esc(wc.wait_class)}: <b>${wc.pct}%</b> <span style="font-size:10px;opacity:.6">(${wc.samples})</span></div>`;
    }).join('');
    $('ashBar').innerHTML = barHtml || `<span class="muted" style="font-size:12px">No foreground ASH samples in last 30 minutes.</span>`;

    if (!total) { $('ashArea').innerHTML = ''; return; }

    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px;">`;

    // Top events
    html += `<div><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Top Wait Events</div>`;
    html += `<table><thead><tr><th>Event</th><th>Class</th><th></th><th>%</th></tr></thead><tbody>`;
    (summary.top_events || []).slice(0,8).forEach(ev => {
      const col = _WC_COLOR[ev.wait_class] || '#778';
      html += `<tr>
        <td class="mono" style="font-size:11px">${esc(ev.event)}</td>
        <td><span style="color:${col};font-size:10px">${esc(ev.wait_class)}</span></td>
        <td><div class="pct-bar"><div class="pct-fill" style="width:${Math.min(ev.pct,100).toFixed(0)}%;background:${col}"></div></div></td>
        <td style="font-size:10px;color:#9ab">${ev.pct}%</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;

    // Top SQL
    html += `<div><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Top SQL by Samples (≈ DB Time)</div>`;
    html += `<table><thead><tr><th>SQL ID</th><th>Samples</th><th>%</th><th>Text</th></tr></thead><tbody>`;
    (topSql.items || []).slice(0,8).forEach(s => {
      const txt = s.sql_text ? s.sql_text.substring(0,70) : '<span style="color:#445;font-style:italic">not in V$SQL</span>';
      html += `<tr>
        <td class="mono" style="font-size:10px;color:#00e5ff">${esc(s.sql_id)}</td>
        <td style="font-size:11px">${s.samples}</td>
        <td style="font-size:10px;color:#9ab">${s.pct}%</td>
        <td class="sql-cell">${s.sql_text ? esc(txt) : txt}</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;
    html += `</div>`;

    // Top modules
    const mods = (summary.top_modules || []).filter(m => m.module !== '(unknown)').slice(0,6);
    if (mods.length) {
      html += `<div style="margin-top:10px"><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px">Top Processes</div>`;
      html += `<div style="display:flex;gap:6px;flex-wrap:wrap">`;
      mods.forEach(m => {
        html += `<div class="chip chip-muted" style="font-size:10px">${esc(m.module)} <span style="color:#00e5ff">${m.pct}%</span></div>`;
      });
      html += `</div></div>`;
    }

    html += `<div style="font-size:10px;color:#334;margin-top:10px">Source: V$ACTIVE_SESSION_HISTORY · Last 30 min · ${total} samples · Foreground sessions only</div>`;
    (summary.warnings||[]).concat(topSql.warnings||[]).forEach(w => {
      html += `<div class="warn-msg">${esc(w.message||String(w))}</div>`;
    });
    $('ashArea').innerHTML = html;
  } catch(e) {
    $('ashArea').innerHTML = `<span class="muted" style="font-size:12px">ASH unavailable: ${esc(e.message)}</span>`;
  }
}

function closeProc() {
  $('procPanel').classList.remove('open');
  $('overlay').classList.remove('open');
}

function _fmtDt(s) { return s ? s.replace('T',' ').substr(0,19) : '—'; }

function _procBadge(row) {
  const s = String(row.runstatus||'');
  const label = row.runstatus_label || `Status ${s}`;
  const cls = {'2':'pb-run','6':'pb-que','7':'pb-run','9':'pb-ok',
    '0':'pb-err','3':'pb-err','4':'pb-err','8':'pb-err','5':'pb-hold'}[s] || 'pb-hold';
  return `<span class="proc-badge ${cls}">${esc(label)}</span>`;
}

function _timelineBar(row) {
  const req = row.rqstdttm, beg = row.begindttm, end = row.enddttm;
  if (!req && !beg) return '';
  const t0 = req ? new Date(req) : new Date(beg);
  const t1 = end ? new Date(end) : new Date();
  const total = Math.max(t1 - t0, 1000);
  const segs = [];
  if (req && beg) {
    const wait = new Date(beg) - new Date(req);
    segs.push({cls:'tl-queued', pct: wait/total*100, label:'Queued'});
  }
  if (beg) {
    const run = (end ? new Date(end) : new Date()) - new Date(beg);
    const s = String(row.runstatus||'');
    const cls = ({'4':'tl-err','8':'tl-err','3':'tl-err','0':'tl-err'}[s]) ||
                ({'9':'tl-done'}[s]) || 'tl-proc';
    segs.push({cls, pct: run/total*100, label: row.runstatus_label||'Run'});
  }
  const bars = segs.map(s => `<div class="tl-seg ${s.cls}" style="width:${Math.max(s.pct,2).toFixed(1)}%" title="${s.label}"></div>`).join('');
  return `<div class="timeline-bar">${bars}</div>
  <div style="display:flex;gap:16px;font-size:10px;color:#445;margin-bottom:8px;">
    <span>Requested: ${_fmtDt(req)}</span>
    <span>Started: ${_fmtDt(beg)}</span>
    <span>Ended: ${_fmtDt(end)}</span>
  </div>`;
}

async function showProc(instance) {
  const env = $('envSel').value;
  $('procPanelBody').innerHTML = '<div style="color:#445;padding:20px 0">Loading&#8230;</div>';
  $('procPanel').classList.add('open');
  $('overlay').classList.add('open');
  try {
    const data = await api(`/api/runtime/process/${instance}?env=${env}`);
    if (!data.item) {
      $('procPanelBody').innerHTML = '<div class="warn-msg">Process not found.</div>';
      return;
    }
    const d = data.item;
    const warns = (data.warnings||[]).map(w => `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
    const aeLink = d.prcstype && d.prcstype.includes('Engine')
      ? `<a href="/admin/object/application_engine/${esc(d.prcsname)}" target="_blank">&#8599; AE Explorer</a>`
      : '';
    const traceLink = d.oprid
      ? `<a href="/admin/tracing?oprid=${esc(d.oprid)}&env=${esc(env)}" target="_blank">&#8599; Trace ${esc(d.oprid)}</a>`
      : '';
    const loc = {'1':'Client','2':'Server','3':'Default','4':'PS/nVision'}[String(d.runlocation||'')] || d.runlocation || '—';
    const orig = {'1':'Online','2':'Batch','3':'Default','4':'Daemon','5':'App Engine','6':'CI/IB'}[String(d.origination||'')] || d.origination || '—';
    const dist = {'0':'N/A','1':'Generated','2':'Posted','3':'Not Posted','4':'Content Deleted','5':'Distributed','6':'Error'}[String(d.diststatus||'')] || d.diststatus || '—';

    $('procPanelBody').innerHTML = `
${warns}
<div style="margin:8px 0 12px;">
  <span style="font-size:22px;font-weight:bold;color:#00e5ff;">#${esc(String(d.prcsinstance))}</span>
  ${_procBadge(d)}
</div>
${_timelineBar(d)}
<h2>Identity</h2>
<div class="p-field"><span class="p-label">Process Type</span><span class="p-value">${esc(d.prcstype||'—')}</span></div>
<div class="p-field"><span class="p-label">Program</span><span class="p-value">${esc(d.prcsname||'—')} ${aeLink}</span></div>
<div class="p-field"><span class="p-label">Operator</span><span class="p-value">${esc(d.oprid||'—')} ${traceLink}</span></div>
<div class="p-field"><span class="p-label">Run Control</span><span class="p-value">${esc(d.runcntlid||'—')}</span></div>
<div class="p-field"><span class="p-label">Server</span><span class="p-value">${esc(d.serverbatch||'—')}</span></div>
<div class="p-field"><span class="p-label">Run Location</span><span class="p-value">${esc(loc)}</span></div>
<div class="p-field"><span class="p-label">Origination</span><span class="p-value">${esc(orig)}</span></div>
<h2>Output</h2>
<div class="p-field"><span class="p-label">Dest Type</span><span class="p-value">${esc(d.outdest_label||d.outdesttype||'—')}</span></div>
${d.outdestformat ? `<div class="p-field"><span class="p-label">Format</span><span class="p-value">${esc(String(d.outdestformat))}</span></div>` : ''}
${d.outdest ? `<div class="p-field"><span class="p-label">Destination</span><span class="p-value" style="font-size:10px">${esc(d.outdest)}</span></div>` : ''}
<div class="p-field"><span class="p-label">Dist Status</span><span class="p-value">${esc(dist)}</span></div>
<h2>Job / Session</h2>
${d.jobinstance > 0 ? `<div class="p-field"><span class="p-label">Job Instance</span><span class="p-value">${esc(String(d.jobinstance))}</span></div>` : ''}
${d.jobname ? `<div class="p-field"><span class="p-label">Job Name</span><span class="p-value">${esc(d.jobname)}</span></div>` : ''}
${d.sessionidnum ? `<div class="p-field"><span class="p-label">Session ID</span><span class="p-value">${esc(String(d.sessionidnum))}</span></div>` : ''}
${d.prcsservername ? `<div class="p-field"><span class="p-label">Process Server</span><span class="p-value">${esc(d.prcsservername)}</span></div>` : ''}
<div id="procAshSection"><div style="color:#334;font-size:11px;margin-top:16px">Loading Oracle activity…</div></div>
`;
    // Async ASH enrichment — only for processes with a start time
    if (d.begindttm) {
      const db = $('dbSel').value;
      if (db) {
        loadProcAsh(instance, db, env, d.prcstype || '');
      } else {
        $('procAshSection').innerHTML = '<div style="color:#334;font-size:11px;margin-top:16px">Select Oracle DB above to see session activity.</div>';
      }
    } else {
      $('procAshSection').innerHTML = '';
    }
  } catch(e) {
    $('procPanelBody').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

async function loadProcAsh(instance, db, env, prcstype) {
  try {
    const r = await api(`/api/runtime/ash/process?db=${encodeURIComponent(db)}&env=${encodeURIComponent(env)}&instance=${instance}`);
    const total = r.total_samples || 0;
    if (!total) {
      $('procAshSection').innerHTML = `<h2>Oracle Activity (ASH)</h2><div style="color:#334;font-size:11px">No ASH samples found for this process run.<br><span style="color:#223">Source: ${esc(r.source||'V$ACTIVE_SESSION_HISTORY + DBA_HIST')}</span></div>`;
      return;
    }
    let html = `<h2>Oracle Activity (ASH) <span style="color:#9ab;font-size:10px;font-weight:normal">${total} samples · ${esc(r.source||'')}</span></h2>`;

    // Wait events
    html += `<div style="margin:4px 0 8px"><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Wait Events</div>`;
    (r.events||[]).forEach(ev => {
      const col = _WC_COLOR[ev.wait_class] || '#778';
      const barW = Math.min(ev.pct, 100).toFixed(0);
      html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;font-size:11px">
        <div class="pct-bar" style="width:60px"><div class="pct-fill" style="width:${barW}%;background:${col}"></div></div>
        <span style="color:${col};font-size:10px;min-width:28px">${ev.pct}%</span>
        <span style="color:#9ab">${esc(ev.event)}</span>
      </div>`;
    });
    html += '</div>';

    // Top SQL
    const sqls = (r.top_sql||[]).filter(s => s.sql_id);
    if (sqls.length) {
      html += `<div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Top SQL</div>`;
      sqls.slice(0,5).forEach(s => {
        const txt = s.sql_text ? s.sql_text.substring(0,80) : '(not in V$SQL)';
        html += `<div style="margin:3px 0;font-size:10px">
          <span class="mono" style="color:#00e5ff">${esc(s.sql_id)}</span>
          <span style="color:#556;margin:0 4px">${s.samples} samples</span>
          <span style="color:#667">${esc(txt)}</span>
        </div>`;
      });
    }

    $('procAshSection').innerHTML = html;
  } catch(e) {
    $('procAshSection').innerHTML = `<div style="color:#334;font-size:11px;margin-top:8px">Oracle Activity unavailable: ${esc(e.message)}</div>`;
  }
}

async function refresh() {
  $('lastTs').textContent = 'Refreshing…';
  await Promise.allSettled([loadAlerts(), loadStatus(), loadDomains(), loadServers(), loadProcesses(), loadOracle(), loadAsh()]);
  $('lastTs').textContent = 'Last: ' + new Date().toLocaleTimeString();
  if (autoR) {
    clearTimeout(arTimer);
    arTimer = setTimeout(refresh, INTERVAL);
  }
}

function toggleAR() {
  autoR = !autoR;
  $('arBtn').textContent = `Auto: ${autoR ? 'ON' : 'OFF'}`;
  if (autoR) { arTimer = setTimeout(refresh, INTERVAL); }
  else { clearTimeout(arTimer); }
}

// ── Runtime Graph Visualization ─────────────────────────
const RT_COLORS = {
  environment:'#00e5ff', operator:'#4488ff', process:'#00cc66',
  application_engine:'#ff8800', oracle_session:'#ffdd00',
  oracle_database:'#ff4488', service_operation:'#aa44ff',
  process_server:'#44ffcc', sql_id:'#ff6644', ib_status:'#ff88ff',
};
function rtColor(t) { return RT_COLORS[t] || '#556677'; }

function rtForce(nodes, edges, w, h, ticks) {
  const k = Math.sqrt((w * h) / Math.max(nodes.length, 1));
  for (let t = 0; t < ticks; t++) {
    for (let i = 0; i < nodes.length; i++) { nodes[i].fx = 0; nodes[i].fy = 0; }
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i+1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
        const d2 = dx*dx + dy*dy || 0.001;
        const f = k*k / d2;
        nodes[i].fx += dx*f; nodes[i].fy += dy*f;
        nodes[j].fx -= dx*f; nodes[j].fy -= dy*f;
      }
    }
    for (const e of edges) {
      const s = nodes[e.si], tgt = nodes[e.ti];
      if (!s || !tgt) continue;
      const dx = tgt.x-s.x, dy = tgt.y-s.y, d = Math.sqrt(dx*dx+dy*dy)||1;
      const f = d*d/(k*3), fx = dx/d*f, fy = dy/d*f;
      s.fx += fx; s.fy += fy; tgt.fx -= fx; tgt.fy -= fy;
    }
    const temp = k*(1-t/ticks);
    for (const n of nodes) {
      n.fx += (w/2-n.x)*0.012; n.fy += (h/2-n.y)*0.012;
      const d = Math.sqrt(n.fx*n.fx+n.fy*n.fy)||1;
      n.x += n.fx/d*Math.min(d,temp); n.y += n.fy/d*Math.min(d,temp);
      n.x = Math.max(24,Math.min(w-24,n.x)); n.y = Math.max(24,Math.min(h-24,n.y));
    }
  }
}

function rtRender(svg, nodes, edges) {
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';
  for (const e of edges) {
    const s = nodes[e.si], t = nodes[e.ti]; if(!s||!t) continue;
    const line = document.createElementNS(ns,'line');
    line.setAttribute('x1',s.x); line.setAttribute('y1',s.y);
    line.setAttribute('x2',t.x); line.setAttribute('y2',t.y);
    line.setAttribute('stroke','#1e3040'); line.setAttribute('stroke-width','1');
    svg.appendChild(line);
    if (e.rel) {
      const tx = document.createElementNS(ns,'text');
      tx.setAttribute('x',(s.x+t.x)/2); tx.setAttribute('y',(s.y+t.y)/2);
      tx.setAttribute('fill','#1e3848'); tx.setAttribute('font-size','7');
      tx.setAttribute('text-anchor','middle'); tx.textContent = e.rel;
      svg.appendChild(tx);
    }
  }
  for (const n of nodes) {
    const g = document.createElementNS(ns,'g');
    g.style.cursor = 'pointer';
    g.onclick = () => rtShowDetail(n);
    const r = n.type==='environment'?18:n.type==='oracle_database'?14:9;
    const c = document.createElementNS(ns,'circle');
    c.setAttribute('cx',n.x); c.setAttribute('cy',n.y); c.setAttribute('r',r);
    c.setAttribute('fill',rtColor(n.type)); c.setAttribute('fill-opacity','0.22');
    c.setAttribute('stroke',rtColor(n.type)); c.setAttribute('stroke-width','1.5');
    g.appendChild(c);
    const lbl = (n.label||n.id||'').replace(/^[^:]+:/,'');
    const tx = document.createElementNS(ns,'text');
    tx.setAttribute('x',n.x); tx.setAttribute('y',n.y+r+11);
    tx.setAttribute('fill',rtColor(n.type)); tx.setAttribute('font-size','9');
    tx.setAttribute('text-anchor','middle');
    tx.textContent = lbl.length>18?lbl.slice(0,16)+'…':lbl;
    g.appendChild(tx);
    svg.appendChild(g);
  }
}

function rtShowDetail(n) {
  const el = $('rtGraphDetail');
  const lbl = (n.label||n.id||'');
  el.innerHTML = `<b style="color:${rtColor(n.type)}">[${n.type}]</b> `+
    `<b style="color:#d7faff">${esc(lbl)}</b>`+
    (n._links&&n._links.admin ? ` <a href="${esc(n._links.admin)}" style="color:#00e5ff;font-size:10px;margin-left:6px;">&#x2197; open</a>` : '')+
    '<br>'+Object.entries(n.data||{}).slice(0,10)
      .map(([k,v])=>`<span style="color:#445">${esc(k)}:</span> <span style="color:#9ab">${esc(String(v??''))}</span>`)
      .join(' &nbsp; ');
}

async function loadRtGraph() {
  const env = $('envSel')?.value || 'HCM';
  $('graphStatus').textContent = 'Building graph…';
  $('rtGraphArea').style.display = 'none';
  try {
    const data = await api(`/api/runtime/graph?env=${encodeURIComponent(env)}&process_limit=60&session_limit=60`);
    const svg = $('rtGraphSvg');
    const w = svg.clientWidth || 900, h = parseInt(svg.getAttribute('height'))||560;
    const nodeMap = {};
    const nodes = (data.nodes||[]).map((n,i) => {
      nodeMap[n.id] = i;
      return {...n, x:24+Math.random()*(w-48), y:24+Math.random()*(h-48), fx:0, fy:0};
    });
    const edges = (data.edges||[]).map(e=>({
      si:nodeMap[e.source], ti:nodeMap[e.target], rel:e.relationship||''
    })).filter(e=>e.si!==undefined&&e.ti!==undefined);
    rtForce(nodes, edges, w, h, 350);
    rtRender(svg, nodes, edges);
    const types = [...new Set(nodes.map(n=>n.type))].sort();
    $('rtGraphLegend').innerHTML = types.map(t=>`<span style="color:${rtColor(t)};` +
      `background:#0a1820;border:1px solid ${rtColor(t)}44;padding:2px 8px;border-radius:2px;">` +
      `${t} <b>${nodes.filter(n=>n.type===t).length}</b></span>`).join('');
    $('rtGraphDetail').textContent = 'Click a node to see details.';
    $('rtGraphArea').style.display = 'block';
    $('graphStatus').textContent = `${nodes.length} nodes · ${edges.length} edges`;
  } catch(e) {
    $('graphStatus').textContent = 'Error: '+esc(e.message);
  }
}

// ── init ────────────────────────────────────────────────
(async () => {
  const cfg = await api('/api/runtime/config').catch(() => ({envs:[], dbs:[]}));
  $('envSel').innerHTML = cfg.envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('dbSel').innerHTML  = cfg.dbs.map(d  => `<option value="${d}">${d}</option>`).join('');
  const urlParams = new URLSearchParams(window.location.search);
  const envParam = urlParams.get('env');
  if (envParam) {
    const envOpt = $('envSel').querySelector(`option[value="${envParam}"]`);
    if (envOpt) envOpt.selected = true;
  }
  await refresh();
  arTimer = setTimeout(refresh, INTERVAL);
  const instParam = urlParams.get('instance');
  if (instParam) showProc(instParam);
})();
// Hide the top-right ENV control in the shared shell header (keep page-local ENV controls visible)
try {
  const hdrEnv = document.querySelector('.ds-page-hdr .ds-env');
  if (hdrEnv) { hdrEnv.style.display = 'none'; }
  else {
    const tbSel = document.querySelector('.topbar select#envSel');
    if (tbSel && tbSel.parentElement) tbSel.parentElement.style.display = 'none';
  }
} catch(e) {}
</script>""")


@router.get("/envcompare", response_class=HTMLResponse)
def admin_envcompare():
    return _shell("Environment Comparison", "envcompare", noscroll=True, env=False, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;min-height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:220px;border-right:1px solid #00e5ff22;padding:10px;overflow-y:auto;}
.content{flex:1;overflow:auto;padding:14px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button:disabled{opacity:.4;cursor:default;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;margin-bottom:10px;}
.tab{padding:7px 13px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.stat-grid{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;}
.stat-box{border:1px solid #00e5ff22;padding:8px 14px;min-width:110px;text-align:center;background:rgba(0,20,30,.5);cursor:pointer;}
.stat-box:hover{border-color:#00e5ff66;}
.stat-box.active{border-color:#00e5ff;background:rgba(0,229,255,.07);}
.stat-num{font-size:20px;font-weight:bold;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.n-only1{color:#ff9900;}
.n-changed{color:#ffdd55;}
.n-only2{color:#55aaff;}
.n-same{color:#00cc66;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.card{border:1px solid #00e5ff22;padding:10px 14px;margin-bottom:10px;background:rgba(0,20,30,.5);}
.section-head{font-size:11px;font-weight:bold;padding:5px 0 4px;border-bottom:1px solid #0a2030;margin-bottom:4px;display:flex;align-items:center;gap:8px;cursor:pointer;}
.section-head:hover{color:#00e5ff;}
.toggle{font-size:10px;color:#556;}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;}
.chip-add{background:#001e00;border:1px solid #00cc66;color:#00cc66;}
.chip-del{background:#200000;border:1px solid #ff6600;color:#ff9900;}
.chip-chg{background:#1a1400;border:1px solid #ffdd55;color:#ffdd55;}
.chip-same{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.diff-row{background:#12181f;border-left:3px solid #ffdd55;padding:3px 8px;margin:1px 0;font-size:11px;}
.diff-col{color:#667;font-size:10px;text-transform:uppercase;letter-spacing:1px;}
.diff-v1{color:#ff9900;}
.diff-v2{color:#55aaff;}
.ctrl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;}
.env-label{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;}
a.obj-link{color:#00e5ff;text-decoration:none;cursor:pointer;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.spinner{display:none;color:#00e5ff;font-size:11px;margin-left:8px;}
.spinner.on{display:inline;}
</style>

<div class="main">

<!-- ═══════════════════════════════════════════════════════════ SIDEBAR -->
<div class="sidebar">
  <h2>Environments</h2>
  <div style="margin-bottom:8px;">
    <span class="env-label">Left</span>
    <select id="env1Sel" onchange="loadSummary()" style="width:100%;margin-top:2px;"></select>
  </div>
  <div style="margin-bottom:12px;">
    <span class="env-label">Right</span>
    <select id="env2Sel" onchange="loadSummary()" style="width:100%;margin-top:2px;"></select>
  </div>

  <h2>Object Counts</h2>
  <div id="summaryTable"><span class="empty">Loading…</span></div>
</div>

<!-- ═══════════════════════════════════════════════════════ CONTENT AREA -->
<div class="content">
  <div class="tab-row">
    <div class="tab on"  onclick="switchTab('records')">Records</div>
    <div class="tab"     onclick="switchTab('fields')">Fields</div>
    <div class="tab"     onclick="switchTab('components')">Components</div>
    <div class="tab"     onclick="switchTab('permissions')">Permissions</div>
    <div class="tab"     onclick="switchTab('ae')">AE Programs</div>
    <div class="tab"     onclick="switchTab('roles')">Roles</div>
    <div class="tab"     onclick="switchTab('peoplecode')">PeopleCode</div>
    <div class="tab"     onclick="switchTab('sql_definitions')">SQL Defs</div>
    <div class="tab"     onclick="switchTab('portals')">Portals</div>
    <div class="tab"     onclick="switchTab('queries')">PS Queries</div>
    <div class="tab"     onclick="switchTab('menus')">Menus</div>
    <div class="tab"     onclick="switchTab('trees')">Trees</div>
    <div class="tab"     onclick="switchTab('ib_routings')">IB Routings</div>
    <div class="tab"     onclick="switchTab('ib_messages')">IB Messages</div>
    <div class="tab"     onclick="switchTab('graph')">Graph</div>
  </div>

  <!-- Records tab -->
  <div id="pane-records" class="pane on">
    <div class="ctrl">
      <input id="recQ" type="text" placeholder="Search records…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('records')">
      <button onclick="runCompare('records')">Compare</button>
      <span class="spinner" id="spin-records">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-records"></div>
  </div>

  <!-- Fields tab -->
  <div id="pane-fields" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="fieldRec" type="text" placeholder="Record name (e.g. PSRECDEFN)" style="width:220px;" onkeydown="if(event.key==='Enter')runFieldCompare()">
      <button onclick="runFieldCompare()">Compare Fields</button>
      <span class="spinner" id="spin-fields">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-fields"></div>
  </div>

  <!-- Components tab -->
  <div id="pane-components" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="compQ" type="text" placeholder="Search components…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('components')">
      <button onclick="runCompare('components')">Compare</button>
      <span class="spinner" id="spin-components">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-components"></div>
  </div>

  <!-- Permissions tab -->
  <div id="pane-permissions" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="permQ" type="text" placeholder="Search permission lists…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('permissions')">
      <button onclick="runCompare('permissions')">Compare</button>
      <span class="spinner" id="spin-permissions">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-permissions"></div>
  </div>

  <!-- AE tab -->
  <div id="pane-ae" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="aeQ" type="text" placeholder="Search AE programs…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('ae')">
      <button onclick="runCompare('ae')">Compare</button>
      <span class="spinner" id="spin-ae">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-ae"></div>
  </div>

  <!-- Roles tab -->
  <div id="pane-roles" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="roleQ" type="text" placeholder="Search roles…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('roles')">
      <button onclick="runCompare('roles')">Compare</button>
      <span class="spinner" id="spin-roles">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-roles"></div>
  </div>

  <!-- PeopleCode tab -->
  <div id="pane-peoplecode" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="pcQ" type="text" placeholder="Filter by parent object (e.g. JOB, GDP_SELECT_PRCS)…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('peoplecode')">
      <button onclick="runCompare('peoplecode')">Compare Catalog</button>
      <span class="spinner" id="spin-peoplecode">&#9679;&#9679;&#9679;</span>
    </div>
    <div class="warn-msg" style="margin-bottom:6px;">Key = objectid1|ov1|ov2|ov3|ov4|ov5 &nbsp;&middot;&nbsp; Compare col = lastupddttm &nbsp;&middot;&nbsp; Capped at 500 programs — use the filter to scope by record/component name.</div>
    <div id="res-peoplecode"></div>
    <hr style="border-color:#1a2a3a;margin:18px 0">
    <div style="font-size:11px;color:#8ab;margin-bottom:8px;font-weight:bold;letter-spacing:.05em;">DEEP SOURCE DIFF</div>
    <div class="ctrl">
      <input id="pcRefInput" type="text" placeholder="Reference (e.g. JOB.EMPLID.FieldEdit.0 or JOB.FieldFormula.0)…" style="width:420px;" onkeydown="if(event.key==='Enter')runPcSourceDiff()">
      <button onclick="runPcSourceDiff()">Diff Source</button>
      <span class="spinner" id="spin-pc-diff">&#9679;&#9679;&#9679;</span>
    </div>
    <div style="font-size:10px;color:#445;margin-bottom:6px;">Format: OV1.OV2.OV3.Event.PROGSEQ — e.g. <code>JOB.FieldFormula.0</code> or <code>GBL_JOB_DATA.W.JOB.FieldEdit.0</code></div>
    <div id="res-pc-diff"></div>
  </div>

  <!-- SQL Definitions tab -->
  <div id="pane-sql_definitions" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="sqlQ" type="text" placeholder="Search SQL ID or owner…" style="width:260px;" onkeydown="if(event.key==='Enter')runCompare('sql_definitions')">
      <button onclick="runCompare('sql_definitions')">Compare</button>
      <span class="spinner" id="spin-sql_definitions">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-sql_definitions"></div>
  </div>

  <!-- Portals tab -->
  <div id="pane-portals" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="portalQ" type="text" placeholder="Search portal object name or label…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('portals')">
      <button onclick="runCompare('portals')">Compare Catalog</button>
      <span class="spinner" id="spin-portals">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-portals"></div>
    <hr style="border-color:#1a2a3a;margin:18px 0">
    <div style="font-size:11px;color:#8ab;margin-bottom:8px;font-weight:bold;letter-spacing:.05em;">DEEP OBJECT COMPARISON</div>
    <div class="ctrl">
      <input id="portalObjName" type="text" placeholder="Portal object name (e.g. PORTAL_GROUPLETS)…" style="width:340px;" onkeydown="if(event.key==='Enter')runPortalObjectCompare()">
      <button onclick="runPortalObjectCompare()">Deep Compare</button>
      <span class="spinner" id="spin-portal-obj">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-portal-obj"></div>
  </div>

  <!-- PS Queries tab -->
  <div id="pane-queries" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="queryQ" type="text" placeholder="Search public PS Query name or description…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('queries')">
      <button onclick="runCompare('queries')">Compare</button>
      <span class="spinner" id="spin-queries">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-queries"></div>
  </div>

  <!-- Menus tab -->
  <div id="pane-menus" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="menuQ" type="text" placeholder="Search menus…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('menus')">
      <button onclick="runCompare('menus')">Compare</button>
      <span class="spinner" id="spin-menus">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-menus"></div>
  </div>

  <!-- Trees tab -->
  <div id="pane-trees" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="treeQ" type="text" placeholder="Search trees…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('trees')">
      <button onclick="runCompare('trees')">Compare</button>
      <span class="spinner" id="spin-trees">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-trees"></div>
  </div>

  <!-- IB Routings tab -->
  <div id="pane-ib_routings" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="ibrtngQ" type="text" placeholder="Search routing name or operation…" style="width:280px;" onkeydown="if(event.key==='Enter')runCompare('ib_routings')">
      <button onclick="runCompare('ib_routings')">Compare</button>
      <span class="spinner" id="spin-ib_routings">&#9679;&#9679;&#9679;</span>
    </div>
    <div class="warn-msg" style="margin-bottom:6px;">Named routings only — auto-generated (~GENERATED~, ~GEN~UPG~) excluded.</div>
    <div id="res-ib_routings"></div>
  </div>

  <!-- IB Messages tab -->
  <div id="pane-ib_messages" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="ibmsgQ" type="text" placeholder="Search message name or description…" style="width:280px;" onkeydown="if(event.key==='Enter')runCompare('ib_messages')">
      <button onclick="runCompare('ib_messages')">Compare</button>
      <span class="spinner" id="spin-ib_messages">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-ib_messages"></div>
  </div>

  <!-- Graph tab -->
  <div id="pane-graph" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="graphTypes" type="text" placeholder="Node types, e.g. record,component,service_operation" style="width:360px;" onkeydown="if(event.key==='Enter')runGraphCompare()">
      <button onclick="runGraphCompare()">Compare Graph Snapshots</button>
      <a class="obj-link" href="/admin/graphdb" target="_blank">Open Graph Admin ↗</a>
      <span class="spinner" id="spin-graph">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-graph"></div>
  </div>

</div><!-- .content -->
</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
const TABS = ['records','fields','components','permissions','ae','roles','peoplecode','sql_definitions','portals','queries','menus','trees','ib_routings','ib_messages','graph'];
let currentTab = 'records';

function env1() { return $('env1Sel').value || 'HCM'; }
function env2() { return $('env2Sel').value || 'FSCM'; }

function esc(s) {
  if (s == null) return '—';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path) {
  const r = await fetch(path);
  return r.json().catch(() => ({}));
}

function switchTab(name) {
  currentTab = name;
  TABS.forEach(t => {
    $(`pane-${t}`).style.display = t === name ? 'block' : 'none';
  });
  document.querySelectorAll('.tab').forEach((el, i) => {
    el.classList.toggle('on', TABS[i] === name);
  });
}

// ─── Summary sidebar ──────────────────────────────────────────────────────────
async function loadSummary() {
  $('summaryTable').innerHTML = '<span class="empty">Loading…</span>';
  const d = await api(`/api/envcompare/summary?env1=${env1()}&env2=${env2()}`);
  if (!d.counts) { $('summaryTable').innerHTML = '<div class="err-msg">Error loading summary.</div>'; return; }

  let h = `<table>
    <thead><tr><th>Type</th><th style="text-align:right">${esc(env1())}</th><th style="text-align:right">${esc(env2())}</th><th style="text-align:right">Δ</th></tr></thead>
    <tbody>`;
  d.counts.forEach(row => {
    const delta = row.delta;
    const dcls = delta === 0 ? 'color:#00cc66' : (delta > 0 ? 'color:#ff9900' : 'color:#55aaff');
    const dsign = delta > 0 ? `+${delta}` : (delta < 0 ? String(delta) : '=');
    h += `<tr>
      <td style="font-size:10px;">${esc(row.type)}</td>
      <td style="text-align:right;font-family:monospace;">${row.env1_count != null ? row.env1_count : '—'}</td>
      <td style="text-align:right;font-family:monospace;">${row.env2_count != null ? row.env2_count : '—'}</td>
      <td style="text-align:right;font-family:monospace;${dcls}">${delta != null ? dsign : '—'}</td>
    </tr>`;
  });
  h += '</tbody></table>';
  (d.warnings || []).forEach(w => { h += `<div class="warn-msg" style="margin-top:4px;">${esc(w.message||w)}</div>`; });
  $('summaryTable').innerHTML = h;
}

// ─── Generic compare (records / components / permissions / ae / roles) ────────
const Q_IDS = {
  records: 'recQ', components: 'compQ', permissions: 'permQ', ae: 'aeQ', roles: 'roleQ',
  peoplecode: 'pcQ', sql_definitions: 'sqlQ', portals: 'portalQ', queries: 'queryQ',
  menus: 'menuQ', trees: 'treeQ', ib_routings: 'ibrtngQ', ib_messages: 'ibmsgQ',
};

async function runCompare(type) {
  const qId = Q_IDS[type];
  const q = qId ? $(qId).value : '';
  const spinId = `spin-${type}`;
  $(spinId).classList.add('on');
  $(`res-${type}`).innerHTML = '';

  const url = `/api/envcompare/${type}?env1=${env1()}&env2=${env2()}&q=${encodeURIComponent(q)}&limit=500`;
  const d = await api(url);
  $(spinId).classList.remove('on');

  if (d.warnings && d.warnings.some(w => w.severity === 'error')) {
    let h = '';
    d.warnings.forEach(w => { h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message)}</div>`; });
    $(`res-${type}`).innerHTML = h;
    return;
  }

  renderDiff(`res-${type}`, d, type);
}

async function runFieldCompare() {
  const rec = $('fieldRec').value.trim().toUpperCase();
  if (!rec) { $('res-fields').innerHTML = '<div class="warn-msg">Enter a record name.</div>'; return; }
  $('spin-fields').classList.add('on');
  $('res-fields').innerHTML = '';

  const d = await api(`/api/envcompare/fields?env1=${env1()}&env2=${env2()}&record=${encodeURIComponent(rec)}`);
  $('spin-fields').classList.remove('on');

  if (d.warnings && d.warnings.some(w => w.severity === 'error')) {
    let h = '';
    d.warnings.forEach(w => { h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message)}</div>`; });
    $('res-fields').innerHTML = h;
    return;
  }

  renderDiff('res-fields', d, 'fields');
}

async function runGraphCompare() {
  $('spin-graph').classList.add('on');
  $('res-graph').innerHTML = '';
  const types = $('graphTypes').value.trim();
  const d = await api(`/api/envcompare/graph?env1=${env1()}&env2=${env2()}&node_types=${encodeURIComponent(types)}&limit=250`);
  $('spin-graph').classList.remove('on');
  renderGraphDiff(d);
}

async function runPortalObjectCompare() {
  const name = ($('portalObjName').value || '').trim().toUpperCase();
  if (!name) return;
  $('spin-portal-obj').classList.add('on');
  $('res-portal-obj').innerHTML = '';
  try {
    const d = await api(`/api/envcompare/portal-object?env1=${env1()}&env2=${env2()}&name=${encodeURIComponent(name)}`);
    $('spin-portal-obj').classList.remove('on');
    renderPortalObjectDiff(d);
  } catch(e) {
    $('spin-portal-obj').classList.remove('on');
    $('res-portal-obj').innerHTML = `<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderPortalObjectDiff(d) {
  const e1 = d.env1, e2 = d.env2;
  const sum = d.summary || {};
  let h = '';
  (d.warnings || []).forEach(w => {
    h += `<div class="warn-msg">${esc(w.message||String(w))}</div>`;
  });
  // Existence
  const ex1 = d.exists_in_env1, ex2 = d.exists_in_env2;
  const lu1 = (d.last_updated||{})[e1] || '—';
  const lu2 = (d.last_updated||{})[e2] || '—';
  h += `<div class="stat-grid">
    ${sBox(sum.definition_changes||0, 'Definition Changes', sum.definition_changes?'n-changed':'n-same')}
    ${sBox(sum.children_changes||0, 'Children Changes', sum.children_changes?'n-changed':'n-same')}
    ${sBox(sum.permissions_changes||0, 'Permission Changes', sum.permissions_changes?'n-changed':'n-same')}
  </div>`;
  h += `<table><thead><tr><th>Attribute</th><th>${esc(e1)}</th><th>${esc(e2)}</th></tr></thead><tbody>
    <tr><td>Exists</td><td>${ex1?'✓':'✗'}</td><td>${ex2?'✓':'✗'}</td></tr>
    <tr><td>Last Updated</td><td class="mono">${esc(lu1)}</td><td class="mono">${esc(lu2)}</td></tr>
  </tbody></table>`;
  if ((d.definition_diffs||[]).length) {
    const rows = d.definition_diffs.map(df =>
      `<tr><td class="mono">${esc(df.field)}</td>
       <td class="diff-v1 mono">${esc(df[e1]||'—')}</td>
       <td class="diff-v2 mono">${esc(df[e2]||'—')}</td></tr>`
    ).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">Definition Differences (${d.definition_diffs.length})</span>`,
      rows, ['Field', e1, e2], 'pod-defn', true
    );
  }
  if ((d.children_diffs||[]).length) {
    const rows = d.children_diffs.map(cd => {
      const cls = cd.status.startsWith('only_in_'+e1)?'chip-del':cd.status.startsWith('only_in_'+e2)?'chip-add':'chip-chg';
      const lbl = cd.portal_label || cd[e1] || cd[e2] || '';
      const link = `<a href="/admin/object/portal_registry/${esc(cd.portal_objname)}" target="_blank" style="color:#00e5ff44;font-size:9px;">↗</a>`;
      return `<tr><td class="mono">${esc(cd.portal_objname)} ${link}</td>
        <td>${esc(lbl)}</td>
        <td><span class="chip ${cls}">${esc(cd.status.replace(/_/g,' '))}</span></td></tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip ${d.children_diffs.length?'chip-chg':'chip-add'}">Children Differences (${d.children_diffs.length})</span>`,
      rows, ['Object Name', 'Label', 'Status'], 'pod-children', true
    );
  }
  if ((d.permissions_diffs||[]).length) {
    const rows = d.permissions_diffs.map(pd => {
      const cls = pd.status.startsWith('only_in_'+e1)?'chip-del':pd.status.startsWith('only_in_'+e2)?'chip-add':'chip-chg';
      return `<tr><td class="mono">${esc(pd.classid)}</td>
        <td>${esc(pd[e1]||'—')}</td><td>${esc(pd[e2]||'—')}</td>
        <td><span class="chip ${cls}">${esc(pd.status.replace(/_/g,' '))}</span></td></tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">Permission Differences (${d.permissions_diffs.length})</span>`,
      rows, ['Permission List', e1, e2, 'Status'], 'pod-perms', true
    );
  }
  if (sum.total_changes === 0) {
    h += `<div style="color:#00aa66;padding:12px;font-size:12px;">&#10003; Identical in both environments.</div>`;
  }
  $('res-portal-obj').innerHTML = h;
}

// ─── PeopleCode Deep Source Diff ──────────────────────────────────────────────
async function runPcSourceDiff() {
  const ref = ($('pcRefInput').value || '').trim();
  if (!ref) return;
  $('spin-pc-diff').classList.add('on');
  $('res-pc-diff').innerHTML = '';
  try {
    const d = await api(`/api/envcompare/peoplecode-source?env1=${env1()}&env2=${env2()}&ref=${encodeURIComponent(ref)}`);
    $('spin-pc-diff').classList.remove('on');
    renderPcSourceDiff(d);
  } catch(e) {
    $('spin-pc-diff').classList.remove('on');
    $('res-pc-diff').innerHTML = `<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderPcSourceDiff(d) {
  let h = '';
  // stat boxes
  const ex1 = d.exists_in_env1, ex2 = d.exists_in_env2;
  h += `<div style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0">`;
  h += `<div class="stat-box"><div class="stat-n">${d.line_count_env1}</div><div class="stat-l">${esc(d.env1)} lines</div></div>`;
  h += `<div class="stat-box"><div class="stat-n">${d.line_count_env2}</div><div class="stat-l">${esc(d.env2)} lines</div></div>`;
  if (d.identical) {
    h += `<div class="stat-box" style="border-color:#00cc6644"><div class="stat-n" style="color:#00cc66">&#x2714;</div><div class="stat-l">Identical</div></div>`;
  } else {
    h += `<div class="stat-box" style="border-color:#00aaff44"><div class="stat-n" style="color:#00aaff">+${d.added_lines}</div><div class="stat-l">Added</div></div>`;
    h += `<div class="stat-box" style="border-color:#ff444444"><div class="stat-n" style="color:#ff4444">-${d.removed_lines}</div><div class="stat-l">Removed</div></div>`;
  }
  if (!ex1) h += `<div class="stat-box" style="border-color:#ff440044"><div class="stat-n" style="color:#ff4444">&#x2715;</div><div class="stat-l">Not in ${esc(d.env1)}</div></div>`;
  if (!ex2) h += `<div class="stat-box" style="border-color:#ff440044"><div class="stat-n" style="color:#ff4444">&#x2715;</div><div class="stat-l">Not in ${esc(d.env2)}</div></div>`;
  h += `</div>`;

  // warnings
  (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">&#9888; ${esc(w.message||String(w))}</div>`; });

  if (d.identical) {
    h += `<div style="color:#00cc66;font-size:12px;margin:10px 0">Source is identical in both environments.</div>`;
    $('res-pc-diff').innerHTML = h;
    return;
  }

  if (!d.diff) {
    $('res-pc-diff').innerHTML = h;
    return;
  }

  // Unified diff rendered with line-level coloring
  h += `<div style="font-size:10px;font-family:monospace;background:#050e16;border:1px solid #1a2a3a;padding:10px;margin-top:8px;overflow-x:auto;max-height:600px;overflow-y:auto;white-space:pre;">`;
  d.diff.split('\n').forEach(line => {
    let col = '#9ab', bg = 'transparent';
    if (line.startsWith('+++') || line.startsWith('---')) { col = '#668'; bg = '#0a1520'; }
    else if (line.startsWith('@@'))  { col = '#00aaff'; bg = '#001828'; }
    else if (line.startsWith('+'))   { col = '#00cc66'; bg = '#002210'; }
    else if (line.startsWith('-'))   { col = '#ff4444'; bg = '#200808'; }
    else { col = '#566'; }
    h += `<div style="color:${col};background:${bg};padding:0 4px;min-height:14px">${esc(line) || '&nbsp;'}</div>`;
  });
  h += `</div>`;
  h += `<div style="font-size:10px;color:#334;margin-top:6px">Reference: ${esc(d.reference)} &nbsp;·&nbsp; Source: SYSADM.PSPCMTXT</div>`;
  $('res-pc-diff').innerHTML = h;
}

// ─── Diff renderer ────────────────────────────────────────────────────────────
function explorerLink(type, name) {
  const map = {
    records:     `/admin/record/${encodeURIComponent(name)}`,
    roles:       `/admin/role/${encodeURIComponent(name)}`,
    permissions: `/admin/object/permissionlist/${encodeURIComponent(name)}`,
    queries:     `/admin/object/query/${encodeURIComponent(name)}`,
  };
  if (!map[type]) return '';
  return ` <a href="${map[type]}" target="_blank" style="font-size:9px;color:#00e5ff44;text-decoration:none;" title="Open in Explorer">↗</a>`;
}

function renderDiff(targetId, d, type) {
  const only1 = d.only_in_env1 || [];
  const only2 = d.only_in_env2 || [];
  const changed = d.changed || [];
  const identical = d.identical_count || 0;
  const total = only1.length + only2.length + changed.length + identical;
  const sectionPrefix = targetId.replace(/[^a-zA-Z0-9_-]/g, '_');
  const sectionId = key => `${sectionPrefix}-${key}`;

  const nameKey = nameCol(type);

  let h = '';

  // Warnings.
  (d.warnings || []).forEach(w => {
    h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message||w)}</div>`;
  });

  // Stat summary.
  h += `<div class="stat-grid">
    ${sBox(only1.length, 'Only in ' + esc(env1()), 'n-only1', sectionId('only1'))}
    ${sBox(changed.length, 'Changed', 'n-changed', sectionId('changed'))}
    ${sBox(only2.length, 'Only in ' + esc(env2()), 'n-only2', sectionId('only2'))}
    ${sBox(identical, 'Identical', 'n-same', sectionId('same'))}
  </div>`;

  // Only in env1.
  if (only1.length) {
    h += collapsibleSection(
      `<span class="chip chip-del">&#8722; Only in ${esc(env1())} (${only1.length})</span>`,
      only1.map(r => `<tr><td class="mono">${esc(r[nameKey])}${explorerLink(type, r[nameKey])}</td>${metaCells(r, type)}</tr>`).join(''),
      metaHeaders(type), sectionId('only1'), true
    );
  }

  // Changed.
  if (changed.length) {
    const rows = changed.map(c => {
      const diffs = c.diffs.map(df =>
        `<div class="diff-row"><span class="diff-col">${esc(df.col)}</span>&nbsp;
          <span class="diff-v1">${esc(df.env1)}</span>
          <span style="color:#334;"> → </span>
          <span class="diff-v2">${esc(df.env2)}</span></div>`
      ).join('');
      return `<tr onclick="toggleDetail(this)" style="cursor:pointer;">
        <td class="mono">${esc(c.name)}${explorerLink(type, c.name)}</td>
        <td colspan="99"><span style="color:#ffdd55;font-size:10px;">▶ ${c.diffs.length} diff${c.diffs.length>1?'s':''}</span>
          <div class="detail" style="display:none;margin-top:4px;">${diffs}</div>
        </td>
      </tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">&#9650; Changed (${changed.length})</span>`,
      rows, ['Name','Differences'], sectionId('changed'), true
    );
  }

  // Only in env2.
  if (only2.length) {
    h += collapsibleSection(
      `<span class="chip chip-add">&#43; Only in ${esc(env2())} (${only2.length})</span>`,
      only2.map(r => `<tr><td class="mono">${esc(r[nameKey])}${explorerLink(type, r[nameKey])}</td>${metaCells(r, type)}</tr>`).join(''),
      metaHeaders(type), sectionId('only2'), true
    );
  }

  if (!h.includes('<tr>') && !h.includes('warn') && !h.includes('err')) {
    h += `<div class="empty" style="padding:16px;">No results. Try a different search filter.</div>`;
  } else if (total === identical && identical > 0) {
    h += `<div class="card" style="color:#00cc66;font-size:12px;">&#10003; All ${identical} objects are identical across both environments.</div>`;
  }

  $(targetId).innerHTML = h;
}

function renderGraphDiff(d) {
  const s = d.summary || {};
  let h = '';

  (d.warnings || []).forEach(w => {
    h += `<div class="warn-msg">${esc(w.message || w)}
      <div style="margin-top:4px;">
        <a class="obj-link" href="/api/graph/build?env=${encodeURIComponent(env1())}&limit=50&persist=true" target="_blank">Build ${esc(env1())} graph</a>
        &nbsp;·&nbsp;
        <a class="obj-link" href="/api/graph/build?env=${encodeURIComponent(env2())}&limit=50&persist=true" target="_blank">Build ${esc(env2())} graph</a>
      </div>
    </div>`;
  });

  h += `<div class="card">
    <div style="font-size:11px;color:#667;margin-bottom:8px;">
      Snapshot: ${esc(d.snapshot?.env1_built_at || 'not built')} ↔ ${esc(d.snapshot?.env2_built_at || 'not built')}
    </div>
    <div class="stat-grid">
      ${sBox(s.only_in_env1_nodes || 0, 'Nodes only in ' + esc(env1()), 'n-only1')}
      ${sBox(s.changed_nodes || 0, 'Changed Nodes', 'n-changed')}
      ${sBox(s.only_in_env2_nodes || 0, 'Nodes only in ' + esc(env2()), 'n-only2')}
      ${sBox(s.only_in_env1_edges || 0, 'Edges only in ' + esc(env1()), 'n-only1')}
      ${sBox(s.changed_edges || 0, 'Changed Edges', 'n-changed')}
      ${sBox(s.only_in_env2_edges || 0, 'Edges only in ' + esc(env2()), 'n-only2')}
    </div>
  </div>`;

  h += graphNodeSection(`Only in ${esc(env1())} Nodes`, d.only_in_env1_nodes || [], 'g-only1');
  h += graphChangedNodeSection(d.changed_nodes || [], 'g-changed');
  h += graphNodeSection(`Only in ${esc(env2())} Nodes`, d.only_in_env2_nodes || [], 'g-only2');
  h += graphEdgeSection(`Only in ${esc(env1())} Edges`, d.only_in_env1_edges || [], 'g-edge1');
  h += graphEdgeSection(`Changed Edges`, d.changed_edges || [], 'g-edge-changed', true);
  h += graphEdgeSection(`Only in ${esc(env2())} Edges`, d.only_in_env2_edges || [], 'g-edge2');

  $('res-graph').innerHTML = h;
}

function graphNodeSection(title, nodes, id) {
  if (!nodes.length) return '';
  const rows = nodes.map(n => `<tr>
    <td class="mono"><a class="obj-link" href="${esc(n.canonical_url || '#')}" target="_blank">${esc(n.id)}</a></td>
    <td>${esc(n.type)}</td>
    <td>${esc(n.display_name || n.name)}</td>
  </tr>`).join('');
  return collapsibleSection(`<span class="chip chip-del">${title} (${nodes.length})</span>`, rows, ['ID','Type','Name'], id, false);
}

function graphChangedNodeSection(items, id) {
  if (!items.length) return '';
  const rows = items.map(item => {
    const diffs = (item.diffs || []).map(df => `<div class="diff-row">
      <span class="diff-col">${esc(df.field)}</span>
      <span class="diff-v1">${esc(shortJson(df.env1))}</span>
      <span style="color:#334;"> → </span>
      <span class="diff-v2">${esc(shortJson(df.env2))}</span>
    </div>`).join('');
    return `<tr onclick="toggleDetail(this)" style="cursor:pointer;">
      <td class="mono"><a class="obj-link" href="${esc(item.env1?.canonical_url || item.env2?.canonical_url || '#')}" target="_blank">${esc(item.id)}</a></td>
      <td>${esc(item.env1?.type || item.env2?.type)}</td>
      <td><span style="color:#ffdd55;">▶ ${item.diffs?.length || 0} diff(s)</span><div class="detail" style="display:none;margin-top:4px;">${diffs}</div></td>
    </tr>`;
  }).join('');
  return collapsibleSection(`<span class="chip chip-chg">Changed Nodes (${items.length})</span>`, rows, ['ID','Type','Differences'], id, false);
}

function graphEdgeSection(title, edges, id, changed=false) {
  if (!edges.length) return '';
  const rows = edges.map(item => {
    const e = changed ? (item.env1 || item.env2 || {}) : item;
    return `<tr>
      <td class="mono">${esc(e.source || item.id)}</td>
      <td>${esc(e.type || '')}</td>
      <td class="mono">${esc(e.target || '')}</td>
    </tr>`;
  }).join('');
  return collapsibleSection(`<span class="chip ${changed ? 'chip-chg' : 'chip-del'}">${title} (${edges.length})</span>`, rows, ['Source','Type','Target'], id, false);
}

function shortJson(value) {
  if (value == null) return '';
  const s = typeof value === 'string' ? value : JSON.stringify(value);
  return s.length > 180 ? s.substring(0, 180) + '…' : s;
}

function collapsibleSection(header, rows, headers, id, open) {
  const thHtml = Array.isArray(headers)
    ? headers.map(h => `<th>${esc(h)}</th>`).join('')
    : '';
  return `<div class="card" style="margin-bottom:8px;">
    <div class="section-head" data-section-id="sec-${id}" role="button" tabindex="0" aria-expanded="${open ? 'true' : 'false'}">
      ${header}
      <span class="toggle">${open ? '▾' : '▸'}</span>
    </div>
    <div id="sec-${id}" style="${open ? '' : 'display:none'}">
      <table><thead><tr>${thHtml}</tr></thead><tbody>${rows}</tbody></table>
    </div>
  </div>`;
}

function toggleSection(id, head) {
  const el = $(id);
  if (!el) return;
  const resolvedHead = head || document.querySelector(`[data-section-id="${id}"]`);
  const tog = resolvedHead ? resolvedHead.querySelector('.toggle') : null;
  const hidden = getComputedStyle(el).display === 'none';
  el.style.display = hidden ? 'block' : 'none';
  if (tog) tog.textContent = hidden ? '▾' : '▸';
  if (resolvedHead) resolvedHead.setAttribute('aria-expanded', hidden ? 'true' : 'false');
}

function toggleSectionById(sectionKey) {
  const id = sectionKey && sectionKey.startsWith('sec-') ? sectionKey : `sec-${sectionKey}`;
  toggleSection(id);
}

function toggleDetail(tr) {
  const detail = tr.querySelector('.detail');
  if (!detail) return;
  const arrow = tr.querySelector('span[style]');
  if (detail.style.display === 'none') {
    detail.style.display = '';
    if (arrow) arrow.textContent = arrow.textContent.replace('▶','▼');
  } else {
    detail.style.display = 'none';
    if (arrow) arrow.textContent = arrow.textContent.replace('▼','▶');
  }
}

document.addEventListener('click', event => {
  const head = event.target.closest('.section-head[data-section-id]');
  if (!head || event.target.closest('a,button,input,select,textarea')) return;
  toggleSection(head.dataset.sectionId, head);
});

document.addEventListener('keydown', event => {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  const head = event.target.closest('.section-head[data-section-id]');
  if (!head) return;
  event.preventDefault();
  toggleSection(head.dataset.sectionId, head);
});

function sBox(n, label, cls, targetSectionId) {
  const sectionId = targetSectionId || '';
  const click = sectionId ? ` onclick="toggleSectionById('${sectionId}')"` : '';
  return `<div class="stat-box" title="${sectionId ? 'Click to expand/collapse section' : ''}"${click}>
    <div class="stat-num ${cls}">${n}</div>
    <div class="stat-lbl">${label}</div>
  </div>`;
}

// ─── Per-type helpers ─────────────────────────────────────────────────────────
function nameCol(type) {
  const map = {
    records: 'recname',
    fields: 'fieldname',
    components: 'pnlgrpname',
    permissions: 'classid',
    ae: 'ae_applid',
    roles: 'rolename',
    queries: 'qryname',
    menus: 'menuname',
    trees: 'tree_name',
    ib_routings: 'routingdefnname',
    ib_messages: 'msgname',
  };
  return map[type] || 'name';
}

function metaHeaders(type) {
  const map = {
    records:      ['Name', 'Type', 'Fields', 'Description'],
    fields:       ['Name', 'Seq', 'Type', 'Length'],
    components:   ['Name', 'Search Rec', 'Add Rec', 'Actions'],
    permissions:  ['Name', 'Description'],
    ae:           ['Name', 'Status', 'Description'],
    roles:        ['Name', 'Description'],
    queries:      ['Name', 'Type', 'Folder', 'Disabled', 'Valid'],
    menus:        ['Name', 'Type', 'Description', 'Owner'],
    trees:        ['Name', 'SetID', 'Status', 'Description'],
    ib_routings:  ['Name', 'Type', 'Operation', 'Sender', 'Receiver'],
    ib_messages:  ['Name', 'Status', 'Description', 'Owner'],
  };
  return map[type] || ['Name'];
}

function metaCells(r, type) {
  switch(type) {
    case 'records':
      return `<td>${esc(r.rectype_label||r.rectype)}</td><td>${esc(r.field_count)}</td><td>${esc(r.recdescr)}</td>`;
    case 'fields':
      return `<td>${esc(r.fieldnum)}</td><td>${esc(r.fieldtype_label||r.fieldtype)}</td><td>${esc(r.fieldlen)}</td>`;
    case 'components':
      return `<td class="mono">${esc(r.searchrecname)}</td><td class="mono">${esc(r.addrecname)}</td><td>${esc(r.actions)}</td>`;
    case 'permissions':
      return `<td>${esc(r.descr)}</td>`;
    case 'ae':
      return `<td>${esc(r.ae_status)}</td><td>${esc(r.descr)}</td>`;
    case 'roles':
      return `<td>${esc(r.descr)}</td>`;
    case 'queries':
      return `<td>${esc(r.qrytype)}</td><td>${esc(r.qryfolder)}</td><td>${esc(r.qrydisabled)}</td><td>${esc(r.qryvalid)}</td>`;
    case 'menus':
      return `<td>${esc(r.menutype)}</td><td>${esc(r.descr)}</td><td>${esc(r.objectownerid)}</td>`;
    case 'trees':
      return `<td class="mono">${esc(r.setid)}</td><td>${esc(r.eff_status)}</td><td>${esc(r.descr)}</td>`;
    case 'ib_routings':
      return `<td>${esc(r.rtngtype)}</td><td class="mono">${esc(r.ib_operationname)}</td><td class="mono">${esc(r.sendernodename)}</td><td class="mono">${esc(r.receivernodename)}</td>`;
    case 'ib_messages':
      return `<td>${esc(r.msgstatus)}</td><td>${esc(r.descr)}</td><td>${esc(r.objectownerid)}</td>`;
    default:
      return '';
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  const d = await api('/api/envcompare/config');
  const envs = d.envs || ['HCM', 'FSCM'];
  $('env1Sel').innerHTML = envs.map((e,i) => `<option value="${e}"${i===0?' selected':''}>${e}</option>`).join('');
  $('env2Sel').innerHTML = envs.map((e,i) => `<option value="${e}"${i===1||envs.length===1?' selected':''}>${e}</option>`).join('');
  // If only one env, pick it for both (will show all-identical).
  loadSummary();
})();
</script>""")


@router.get("/tracing", response_class=HTMLResponse)
def admin_tracing():
    return _shell("Transaction Tracing", "runtime", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:230px;border-right:1px solid #00e5ff22;display:flex;flex-direction:column;overflow:hidden;}
.sidebar-body{overflow-y:auto;flex:1;padding:8px;}
.content{flex:1;overflow:auto;padding:14px;}
select,input[type=text],input[type=number]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button:disabled{opacity:.4;cursor:default;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;}
.ctrl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:10px;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;}
.stat-grid{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;}
.stat-box{border:1px solid #00e5ff22;padding:6px 12px;min-width:90px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:18px;font-weight:bold;color:#00e5ff;}
.stat-lbl{font-size:9px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.s-err{color:#ff4444;}
.s-warn{color:#ffaa00;}
.s-proc{color:#00e5ff;}
.s-sess{color:#00cc66;}
.s-ib{color:#ffaa00;}
/* Timeline */
.timeline{position:relative;padding-left:28px;}
.timeline::before{content:'';position:absolute;left:10px;top:0;bottom:0;width:1px;background:#0a2030;}
.tl-event{position:relative;margin-bottom:6px;}
.tl-dot{position:absolute;left:-22px;top:6px;width:10px;height:10px;border-radius:50%;border:2px solid;}
.tl-card{border:1px solid #0a2030;padding:7px 10px;background:#06121a;cursor:pointer;transition:border-color .1s;}
.tl-card:hover{border-color:#00e5ff33;}
.tl-card.open{border-color:#00e5ff44;background:#081820;}
.tl-type{font-size:9px;text-transform:uppercase;letter-spacing:1px;font-weight:bold;margin-bottom:2px;}
.tl-title{font-size:12px;color:#d7faff;}
.tl-sub{font-size:10px;color:#556;margin-top:1px;}
.tl-ts{font-size:10px;color:#334;float:right;font-family:monospace;}
.tl-detail{display:none;margin-top:6px;border-top:1px solid #0a2030;padding-top:6px;}
.tl-card.open .tl-detail{display:block;}
.kv-grid{display:grid;grid-template-columns:130px 1fr;gap:1px 10px;font-size:10px;}
.kv-key{color:#556;text-transform:uppercase;letter-spacing:1px;padding:2px 0;}
.kv-val{padding:2px 0;font-family:monospace;word-break:break-all;}
.sql-block{background:#040d14;border:1px solid #0a2030;padding:6px 8px;font-family:monospace;font-size:10px;color:#9ab;margin-top:4px;white-space:pre-wrap;word-break:break-all;max-height:150px;overflow:auto;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.side-item{padding:6px 8px;cursor:pointer;border-bottom:1px solid #081520;font-size:11px;}
.side-item:hover{background:#0b2030;}
.side-item.active{background:#0b2030;border-left:2px solid #00e5ff;}
.side-badge{float:right;font-size:9px;padding:1px 5px;border-radius:2px;background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.spin{display:none;color:#00e5ff;font-size:11px;margin-left:6px;}
.spin.on{display:inline;}
a.obj-link{color:#00e5ff;text-decoration:none;font-size:10px;}
a.obj-link:hover{text-decoration:underline;}
#opridInput{width:160px;}
#hoursInput{width:55px;}
#opridSuggest{position:absolute;z-index:100;background:#0b1b24;border:1px solid #00e5ff44;max-height:200px;overflow-y:auto;width:200px;display:none;}
#opridSuggest .sug-item{padding:5px 10px;cursor:pointer;font-size:11px;}
#opridSuggest .sug-item:hover{background:#0b2030;}
.suggest-wrap{position:relative;display:inline-block;}
</style>

<div class="ds-toolbar">
  <span class="lbl">Env</span>
  <select id="envSel" style="width:70px;"></select>
  <span class="lbl">DB</span>
  <select id="dbSel" style="width:80px;"></select>
  <span class="lbl">OPRID</span>
  <div class="suggest-wrap" style="position:relative;">
    <input id="opridInput" type="text" placeholder="JSMITH" autocomplete="off"
           oninput="suggestOprids()" onkeydown="handleKey(event)">
    <div id="opridSuggest"></div>
  </div>
  <span class="lbl">Hours</span>
  <input id="hoursInput" type="number" value="24" min="1" max="720" style="width:60px;">
  <button id="traceBtn" onclick="runTrace()">Trace</button>
  <span class="spin" id="spin">&#9679;&#9679;&#9679;</span>
</div>

<div class="main">

<!-- ═══════════════════════════════════════════════════════════ SIDEBAR -->
<div class="sidebar">
  <div style="padding:8px;border-bottom:1px solid #00e5ff11;">
    <h2 style="margin:0 0 6px;">Recent Activity</h2>
    <select id="sideEnvSel" style="width:100%;font-size:11px;" onchange="loadActive()"></select>
  </div>
  <div class="sidebar-body" id="activeList">
    <span class="empty">Loading…</span>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════ CONTENT AREA -->
<div class="content" id="contentArea">
  <div id="placeholder" style="padding:20px 0;">
    <div style="color:#334;font-size:13px;margin-bottom:8px;">Enter an OPRID above to trace their activity.</div>
    <div style="color:#223;font-size:11px;line-height:1.8;">
      The trace will correlate:<br>
      &nbsp;&#9654; Login / logout history (PSACCESSLOG)<br>
      &nbsp;&#9881; Process Scheduler runs (PSPRCSRQST)<br>
      &nbsp;&#9670; Active Oracle sessions (V$SESSION · CLIENT_IDENTIFIER)<br>
      &nbsp;&#8644; Integration Broker transactions (PSAPMSGPUBHDR · when accessible)
    </div>
  </div>
</div>

</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
let suggestTimer = null;
let currentOprid = null;

function env()   { return $('envSel').value   || 'HCM'; }
function db()    { return $('dbSel').value    || ''; }
function hours() { return parseInt($('hoursInput').value) || 24; }

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path) {
  const r = await fetch(path);
  return r.json().catch(() => ({}));
}

// ─── Autocomplete ──────────────────────────────────────────────────────────
function suggestOprids() {
  clearTimeout(suggestTimer);
  const q = $('opridInput').value.trim();
  if (!q) { $('opridSuggest').style.display = 'none'; return; }
  suggestTimer = setTimeout(async () => {
    const d = await api(`/api/tracing/operators?env=${env()}&q=${encodeURIComponent(q)}`);
    const items = d.items || [];
    if (!items.length) { $('opridSuggest').style.display = 'none'; return; }
    $('opridSuggest').innerHTML = items.map(it =>
      `<div class="sug-item" onclick="selectOprid('${esc(it.oprid)}')">
        <strong>${esc(it.oprid)}</strong>
        ${it.oprdefndesc ? `<span style="color:#556;"> — ${esc(it.oprdefndesc)}</span>` : ''}
        ${it.emailid ? `<br><span style="color:#334;font-size:10px;">${esc(it.emailid)}</span>` : ''}
      </div>`
    ).join('');
    $('opridSuggest').style.display = 'block';
  }, 200);
}

function selectOprid(oprid) {
  $('opridInput').value = oprid;
  $('opridSuggest').style.display = 'none';
  runTrace();
}

function handleKey(e) {
  if (e.key === 'Enter') { $('opridSuggest').style.display = 'none'; runTrace(); }
  if (e.key === 'Escape') $('opridSuggest').style.display = 'none';
}

document.addEventListener('click', e => {
  if (!e.target.closest('.suggest-wrap')) $('opridSuggest').style.display = 'none';
});

// ─── Recent active operators (sidebar) ────────────────────────────────────
async function loadActive() {
  const e = $('sideEnvSel').value || 'HCM';
  $('activeList').innerHTML = '<span class="empty">Loading…</span>';
  const d = await api(`/api/tracing/active?env=${e}&limit=30`);
  const items = d.items || [];
  if (!items.length) {
    $('activeList').innerHTML = '<span class="empty" style="padding:8px;">No recent activity.</span>';
    (d.warnings||[]).forEach(w => {
      $('activeList').innerHTML += `<div class="warn-msg">${esc(w.message||w)}</div>`;
    });
    return;
  }
  $('activeList').innerHTML = items.map(it => {
    const badge = it.is_active
      ? '<span class="side-badge" style="background:#002800;border-color:#00cc66;color:#00cc66;">ACTIVE</span>'
      : `<span class="side-badge">${it.session_count}</span>`;
    const sub = it.last_login ? it.last_login.replace('T',' ').substring(0,16) : '';
    return `<div class="side-item" onclick="quickTrace('${esc(it.oprid)}')">
      ${badge}
      <strong style="font-family:monospace;font-size:11px;">${esc(it.oprid)}</strong>
      <div style="font-size:10px;color:#334;">${sub}</div>
    </div>`;
  }).join('');
}

function quickTrace(oprid) {
  $('opridInput').value = oprid;
  document.querySelectorAll('.side-item').forEach(el => el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  runTrace();
}

// ─── Main trace ────────────────────────────────────────────────────────────
async function runTrace() {
  const oprid = $('opridInput').value.trim();
  if (!oprid) return;
  currentOprid = oprid;
  $('spin').classList.add('on');
  $('traceBtn').disabled = true;
  $('contentArea').innerHTML = `<div style="color:#334;padding:10px;">Tracing ${esc(oprid)}…</div>`;

  let url = `/api/tracing/trace?env=${env()}&oprid=${encodeURIComponent(oprid)}&hours=${hours()}`;
  const dbv = db();
  if (dbv) url += `&db=${encodeURIComponent(dbv)}`;

  const d = await api(url);
  $('spin').classList.remove('on');
  $('traceBtn').disabled = false;

  renderTrace(d);
}

function renderTrace(d) {
  const oprid   = d.oprid || '?';
  const summary = d.summary || {};
  const events  = d.timeline || [];
  const warns   = d.warnings || [];

  let h = `<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;">
    <span style="font-family:monospace;font-size:15px;color:#00e5ff;">${esc(oprid)}</span>
    <span style="font-size:10px;color:#556;">last ${d.hours_back}h · ${esc(d.env)}</span>
  </div>`;

  // Warnings.
  warns.forEach(w => {
    if (w.severity === 'error') {
      h += `<div class="err-msg">${esc(w.message||w)}</div>`;
    } else {
      h += `<div class="warn-msg">${esc(w.message||w)}</div>`;
    }
  });

  // Summary stats.
  h += `<div class="stat-grid">
    ${sBox(summary.login_count, 'Logins', 's-sess')}
    ${sBox(summary.process_count, 'Processes', 's-proc')}
    ${sBox(summary.error_count, 'Errors', 's-err')}
    ${sBox(summary.oracle_count, 'Oracle Sessions', '')}
    ${sBox(summary.ib_count, 'IB Txns', 's-ib')}
  </div>`;

  if (!events.length) {
    h += `<div class="empty">No activity found for ${esc(oprid)} in the last ${d.hours_back} hours.</div>`;
    $('contentArea').innerHTML = h;
    return;
  }

  // Filter bar.
  h += `<div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;font-size:11px;">
    <button class="sec" style="font-size:10px;" onclick="filterEvents('all')">All</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('login')">Logins</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('process')">Processes</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('oracle')">Oracle</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('ib')">IB</button>
    <button class="sec" style="font-size:10px;float:right;" onclick="expandAll()">Expand All</button>
    <button class="sec" style="font-size:10px;" onclick="collapseAll()">Collapse</button>
  </div>`;

  // Timeline.
  h += '<div class="timeline" id="timeline">';
  events.forEach((ev, i) => {
    const meta    = ev.meta || {};
    const color   = meta.color || '#556';
    const typeKey = ev.type || 'info';
    const tsStr   = (ev.ts || '').replace('T', ' ').substring(0, 19);
    const statusCls = ev.status === 'error' ? 'chip-err' : ev.status === 'warn' ? 'chip-warn' : ev.status === 'ok' ? 'chip-ok' : 'chip-info';

    h += `<div class="tl-event" data-type="${esc(typeKey)}">
      <div class="tl-dot" style="border-color:${color};background:${color}33;"></div>
      <div class="tl-card" onclick="toggleEvent(this)">
        <div>
          <span class="tl-ts">${esc(tsStr)}</span>
          <span class="tl-type" style="color:${color};">${esc(meta.label || typeKey)}</span>
        </div>
        <div class="tl-title">${esc(ev.title)}</div>
        ${ev.subtitle ? `<div class="tl-sub">${esc(ev.subtitle)}</div>` : ''}
        <div class="tl-detail">${buildDetail(ev)}</div>
      </div>
    </div>`;
  });
  h += '</div>';

  $('contentArea').innerHTML = h;
}

function buildDetail(ev) {
  const d = ev.detail || {};
  const type = ev.type;
  let h = '<div class="kv-grid">';

  if (type === 'login' || type === 'logout') {
    h += kv('OPRID', d.oprid) + kv('Login', d.logindttm) + kv('Logout', d.logoutdttm || '— (active)') + kv('DB', d.connectdbbname) + kv('Tools', d.toolsrel);
  } else if (type === 'process') {
    h += kv('Instance', d.prcsinstance) + kv('Type', d.prcstype) + kv('Program', d.prcsname)
       + kv('Run Control', d.runcntlid) + kv('Status', d.runstatus_label) + kv('Server', d.serverbatch)
       + kv('Start', d.begindttm) + kv('End', d.enddttm);
  } else if (type === 'oracle') {
    h += kv('SID/Serial', `${d.sid}/${d.serial_num}`) + kv('Username', d.username) + kv('Status', d.status)
       + kv('Program', d.program) + kv('Module', d.module) + kv('Action', d.action)
       + kv('Machine', d.machine) + kv('Logon', d.logon_time) + kv('Wait', `${d.seconds_in_wait || 0}s · ${d.event || ''}`)
       + kv('CLIENT_ID', d.client_identifier);
    if (d.sql_text) {
      h += `</div><div class="sql-block">${esc(d.sql_text)}</div><div class="kv-grid">`;
    }
  } else if (type === 'ib') {
    h += kv('Txn ID', d.ibtransactionid) + kv('Operation', d.ib_operationname) + kv('Queue', d.queuename)
       + kv('Pub Node', d.pubnode) + kv('Status', d.pubstatus) + kv('Created', d.createdttm);
  }

  h += '</div>';
  if ((ev.links || []).length) {
    h += '<div style="margin-top:4px;">';
    ev.links.forEach(l => { h += `<a class="obj-link" href="${esc(l.url)}">${esc(l.label)}</a>&nbsp; `; });
    h += '</div>';
  }
  return h;
}

function kv(label, val) {
  if (val == null || val === '') return '';
  return `<div class="kv-key">${esc(label)}</div><div class="kv-val">${esc(String(val))}</div>`;
}

function sBox(n, label, cls) {
  return `<div class="stat-box"><div class="stat-num ${cls}">${n != null ? n : 0}</div><div class="stat-lbl">${esc(label)}</div></div>`;
}

function toggleEvent(card) {
  card.classList.toggle('open');
}

function filterEvents(type) {
  document.querySelectorAll('.tl-event').forEach(el => {
    el.style.display = (type === 'all' || el.dataset.type === type) ? '' : 'none';
  });
}

function expandAll() {
  document.querySelectorAll('.tl-card').forEach(c => c.classList.add('open'));
}
function collapseAll() {
  document.querySelectorAll('.tl-card').forEach(c => c.classList.remove('open'));
}

// ─── Init ─────────────────────────────────────────────────────────────────
(async () => {
  const cfg = await api('/api/tracing/config');
  const envs = cfg.envs || ['HCM'];
  const dbs  = cfg.dbs  || [];
  $('envSel').innerHTML = envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('sideEnvSel').innerHTML = envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('dbSel').innerHTML = `<option value="">— (no Oracle)</option>` + dbs.map(d => `<option value="${d}">${d}</option>`).join('');
  if (dbs.length) $('dbSel').value = dbs[0];

  // Pre-fill from URL params: ?oprid=VP1&env=FSCM
  const params = new URLSearchParams(window.location.search);
  const opParam  = params.get('oprid');
  const envParam = params.get('env');
  if (envParam && envs.includes(envParam.toUpperCase())) {
    $('envSel').value = envParam.toUpperCase();
    $('sideEnvSel').value = envParam.toUpperCase();
  }
  if (opParam) {
    $('opridInput').value = opParam;
    runTrace();
  } else {
    loadActive();
  }
})();
</script>""")


@router.get("/infra", response_class=HTMLResponse)
def admin_infra():
    return _shell("Infrastructure", "infra", content="""
<div class="ds-page-header">
  <div class="ds-page-title">Infrastructure</div>
  <div class="ds-page-subtitle">Host metrics, services, containers, and Oracle health</div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">

  <div class="card">
    <h2>Host Metrics <button onclick="loadHost()" style="float:right;font-size:11px">Refresh</button></h2>
    <div id="hostMetrics" style="font-size:12px;color:#6c7086">Loading...</div>
  </div>

  <div class="card">
    <h2>Services <button onclick="loadServices()" style="float:right;font-size:11px">Refresh</button></h2>
    <table id="servicesTable" style="font-size:12px;width:100%">
      <thead><tr><th>Service</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="serviceRows"></tbody>
    </table>
    <div style="margin-top:8px">
      <button onclick="reloadNginx()" style="font-size:11px;background:#313244">Reload NGINX Config</button>
    </div>
  </div>

  <div class="card">
    <h2>Containers <button onclick="loadContainers()" style="float:right;font-size:11px">Refresh</button></h2>
    <table id="containersTable" style="font-size:12px;width:100%">
      <thead><tr><th>Name</th><th>Image</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="containerRows"></tbody>
    </table>
  </div>

  <div class="card">
    <h2>Oracle Health <button onclick="loadOracleHealth()" style="float:right;font-size:11px">Refresh</button></h2>
    <div id="oracleHealth" style="font-size:12px;color:#6c7086">Loading...</div>
  </div>

</div>

<div class="card" style="margin-top:16px">
  <h2>Container Logs
    <select id="containerLogName" style="font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
      <option value="authelia">authelia</option>
    </select>
    <input id="containerLogLines" type="number" value="50" min="10" max="500" style="width:60px;font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
    <button onclick="loadContainerLogs()" style="font-size:11px">Load</button>
  </h2>
  <pre id="containerLogOutput" style="font-size:11px;max-height:300px;overflow:auto;background:#0d0d14;padding:8px;border-radius:4px;color:#a6e3a1">Select a container and click Load.</pre>
</div>

<div class="card" style="margin-top:16px">
  <h2>Journal Log
    <input id="journalUnits" value="nginx,deathstar-api" style="font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px;width:220px">
    <input id="journalLines" type="number" value="80" min="10" max="500" style="width:60px;font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
    <button onclick="loadJournal()" style="font-size:11px">Load</button>
  </h2>
  <pre id="journalOutput" style="font-size:11px;max-height:300px;overflow:auto;background:#0d0d14;padding:8px;border-radius:4px;color:#cdd6f4">Click Load to fetch journal entries.</pre>
</div>

<script>
async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    if (!res.ok) { const t = await res.text(); console.error(path, t); return null; }
    return res.json();
}

function fmtBytes(b) {
    if (b == null) return '?';
    const gb = b / 1073741824;
    return gb >= 1 ? gb.toFixed(1) + ' GB' : (b / 1048576).toFixed(0) + ' MB';
}

async function loadHost() {
    const d = await api('/api/metrics/host');
    if (!d) return;
    const mem = d.memory || {};
    const disk = d.disk || {};
    const load = d.loadavg || [0, 0, 0];
    const boot = d.boot_time ? new Date(d.boot_time * 1000).toLocaleString() : '?';
    document.getElementById('hostMetrics').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div><b>CPU</b>: ${d.cpu_percent?.toFixed(1)}%</div>
          <div><b>Load</b>: ${load.map(l => l.toFixed(2)).join(' / ')}</div>
          <div><b>Memory</b>: ${fmtBytes(mem.used)} / ${fmtBytes(mem.total)} (${mem.percent?.toFixed(1)}%)</div>
          <div><b>Disk /</b>: ${fmtBytes(disk.used)} / ${fmtBytes(disk.total)} (${disk.percent?.toFixed(1)}%)</div>
          <div style="grid-column:1/-1"><b>Boot time</b>: ${boot}</div>
        </div>`;
}

async function loadServices() {
    const rows = await api('/api/system/services');
    const tbody = document.getElementById('serviceRows');
    if (!tbody || !rows) return;
    tbody.innerHTML = '';
    rows.forEach(r => {
        const chip = r.active
            ? '<span class="chip" style="background:#a6e3a1;color:#1e1e2e">active</span>'
            : '<span class="chip" style="background:#f38ba8;color:#1e1e2e">inactive</span>';
        const btn = r.restartable
            ? `<button onclick="restartService('${r.unit}')" style="font-size:10px;background:#313244">Restart</button>`
            : '<span style="color:#6c7086;font-size:10px">—</span>';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.name}</td><td>${chip}</td><td>${btn}</td>`;
        tbody.appendChild(tr);
    });
}

async function restartService(unit) {
    if (!confirm(`Restart ${unit}?`)) return;
    const d = await api(`/api/system/service/${encodeURIComponent(unit)}/restart`, { method: 'POST' });
    alert(d ? `${unit}: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
    await loadServices();
}

async function reloadNginx() {
    if (!confirm('Reload NGINX config?')) return;
    const d = await api('/api/system/nginx/reload', { method: 'POST' });
    alert(d ? `NGINX reload: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
}

async function loadContainers() {
    const d = await api('/api/system/containers');
    const tbody = document.getElementById('containerRows');
    if (!tbody || !d) return;
    tbody.innerHTML = '';

    // Update log selector
    const sel = document.getElementById('containerLogName');
    const existing = new Set([...sel.options].map(o => o.value));

    (d.containers || []).forEach(c => {
        if (!existing.has(c.name)) {
            const opt = document.createElement('option');
            opt.value = c.name; opt.textContent = c.name;
            sel.appendChild(opt);
        }
        const chip = c.running
            ? '<span class="chip" style="background:#a6e3a1;color:#1e1e2e">running</span>'
            : '<span class="chip" style="background:#f38ba8;color:#1e1e2e">stopped</span>';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${c.name}</td><td style="font-size:10px;color:#6c7086">${(c.image||'').split('/').pop()}</td><td>${chip}</td>
            <td><button onclick="restartContainer('${c.name}')" style="font-size:10px;background:#313244">Restart</button></td>`;
        tbody.appendChild(tr);
    });
    if (!d.containers?.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="color:#6c7086;font-style:italic">No containers</td></tr>';
    }
}

async function restartContainer(name) {
    if (!confirm(`Restart container ${name}?`)) return;
    const d = await api(`/api/system/containers/${encodeURIComponent(name)}/restart`, { method: 'POST' });
    alert(d ? `${name}: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
    await loadContainers();
}

async function loadOracleHealth() {
    const d = await api('/api/oracle/health');
    if (!d) { document.getElementById('oracleHealth').textContent = 'Failed to load'; return; }
    const items = [];
    if (d.instances) items.push(`<b>Instances:</b> ${d.instances.length}`);
    if (d.tablespace_ok != null) items.push(`<b>Tablespace OK:</b> ${d.tablespace_ok}`);
    if (d.status) items.push(`<b>Status:</b> ${d.status}`);
    if (d.warnings?.length) items.push(`<b>Warnings:</b> ${d.warnings.join(', ')}`);

    // Also fetch listener
    const listener = await api('/api/oracle/listener');
    if (listener) items.push(`<b>Listener:</b> ${listener.status || JSON.stringify(listener)}`);

    document.getElementById('oracleHealth').innerHTML = items.join('<br>') || JSON.stringify(d, null, 2);
}

async function loadContainerLogs() {
    const name = document.getElementById('containerLogName').value;
    const lines = document.getElementById('containerLogLines').value || 50;
    const d = await api(`/api/system/containers/${encodeURIComponent(name)}/logs?lines=${lines}`);
    const pre = document.getElementById('containerLogOutput');
    if (!d) { pre.textContent = 'Failed'; return; }
    pre.textContent = (d.lines || []).join('\\n') || '(no output)';
    pre.scrollTop = pre.scrollHeight;
}

async function loadJournal() {
    const units = document.getElementById('journalUnits').value;
    const lines = document.getElementById('journalLines').value || 80;
    const d = await api(`/api/logs/journal?units=${encodeURIComponent(units)}&lines=${lines}`);
    const pre = document.getElementById('journalOutput');
    if (!d) { pre.textContent = 'Failed'; return; }
    pre.textContent = (d.lines || []).join('\\n') || '(no output)';
    pre.scrollTop = pre.scrollHeight;
}

(async function() {
    await Promise.all([loadHost(), loadServices(), loadContainers(), loadOracleHealth()]);
})();
</script>""")


