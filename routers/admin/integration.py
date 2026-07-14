import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/ib", response_class=HTMLResponse)
@router.get("/ib/{section}", response_class=HTMLResponse)
@router.get("/ib/{section}/{name}", response_class=HTMLResponse)
def admin_ib(section: str = None, name: str = None):
    return _shell("IB Explorer", "ib", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
  .brand-logo{width:36px;height:36px;object-fit:contain;margin-right:8px;filter:drop-shadow(0 2px 6px rgba(0,0,0,.6));}
.main{display:flex;flex:1;overflow:hidden;flex-direction:column;min-height:0;}
/* master-detail layout */
.explorer{display:flex;flex:1;overflow:hidden;min-height:0;}
.list-panel{width:290px;min-width:200px;border-right:1px solid #00e5ff22;display:flex;flex-direction:column;overflow:hidden;flex-shrink:0;}
.detail-panel{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
.detail-scroll{flex:1;overflow-y:auto;padding:14px;}
/* breadcrumb */
.breadcrumb{padding:5px 12px;border-bottom:1px solid #00e5ff11;font-size:11px;display:flex;align-items:center;flex-wrap:wrap;gap:3px;min-height:28px;background:#03080f;}
.bc-link{color:#00e5ff88;cursor:pointer;font-size:10px;}
.bc-link:hover{color:#00e5ff;text-decoration:underline;}
.bc-sep{color:#223;font-size:10px;}
.bc-cur{color:#d7faff;font-size:10px;}
/* relationship strip */
.rel-strip{display:flex;flex-wrap:wrap;gap:6px;padding:6px 10px;border:1px solid #00e5ff11;background:#030c14;margin-bottom:10px;align-items:center;font-size:10px;}
.rel-strip-label{color:#334;text-transform:uppercase;letter-spacing:1px;margin-right:4px;}
.rel-tag{background:#001828;border:1px solid #00e5ff33;color:#00e5ff;padding:2px 8px;cursor:pointer;border-radius:2px;font-size:10px;}
.rel-tag:hover{background:#00e5ff22;}
.rel-tag.rel-action{background:#001800;border-color:#00cc6633;color:#00cc66;}
.rel-tag.rel-action:hover{background:#00cc6611;}
/* compact stats for overview panel */
.cstat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;padding:8px 0;}
.cstat{border:1px solid #00e5ff22;padding:5px 6px;text-align:center;background:rgba(0,20,30,.5);}
.cstat-num{font-size:16px;color:#00e5ff;font-weight:bold;line-height:1.2;}
.cstat-lbl{font-size:9px;color:#445;text-transform:uppercase;letter-spacing:0.5px;}
/* lists */
.list-area{overflow-y:auto;flex:1;min-height:0;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;overflow-x:auto;flex-shrink:0;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 10px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;border-color:#00e5ff;}
.tab{padding:7px 12px;cursor:pointer;font-size:10px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;letter-spacing:0.5px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.search-bar{padding:6px 8px;border-bottom:1px solid #00e5ff11;display:flex;gap:4px;}
.search-bar input{flex:1;min-width:0;font-size:11px;}
.list-item{padding:6px 10px;cursor:pointer;border-bottom:1px solid #0b1b24;font-size:11px;}
.list-item:hover{background:#0b2030;}
.list-item.active{background:#0b2030;border-left:2px solid #00e5ff;}
.item-name{font-family:monospace;color:#d7faff;}
.item-meta{font-size:10px;color:#445;margin-top:1px;}
.badge{display:inline-block;font-size:9px;padding:1px 5px;border-radius:2px;float:right;}
.bd-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.bd-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.bd-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.bd-mute{background:#141a20;border:1px solid #334;color:#556;}
.bd-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.chip{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;}
.ch-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.ch-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.ch-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.ch-mute{background:#141a20;border:1px solid #334;color:#556;}
.ch-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:2px 12px;font-size:11px;margin:8px 0;}
.kv-key{color:#667;text-transform:uppercase;font-size:10px;letter-spacing:1px;padding:3px 0;}
.kv-val{padding:3px 0;font-family:monospace;}
.card{border:1px solid #00e5ff22;padding:10px 14px;margin-bottom:10px;background:rgba(0,20,30,.6);}
.stat-grid{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0;}
.stat-box{border:1px solid #00e5ff33;padding:10px 16px;min-width:100px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:22px;color:#00e5ff;font-weight:bold;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.ts{font-size:10px;color:#446;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:2px;}
a.obj-link{color:#00e5ff;text-decoration:none;cursor:pointer;}
a.obj-link:hover{text-decoration:underline;}
.detail-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;height:60%;color:#223;font-size:13px;gap:8px;}
.detail-placeholder svg{opacity:.15;}
</style>

<div class="main">

<div class="tab-row">
  <div class="tab on" onclick="switchTab('overview')">Overview</div>
  <div class="tab" onclick="switchTab('services')">Services</div>
  <div class="tab" onclick="switchTab('operations')">Service Ops</div>
  <div class="tab" onclick="switchTab('routings')">Routings</div>
  <div class="tab" onclick="switchTab('nodes')">Nodes</div>
  <div class="tab" onclick="switchTab('queues')">Queues</div>
  <div class="tab" onclick="switchTab('txns')">Txns</div>
</div>

<div class="explorer">

  <!-- LEFT: list panel -->
  <div class="list-panel">

    <div id="tab-overview" style="display:flex;flex-direction:column;overflow-y:auto;padding:10px;">
      <div class="cstat-row">
        <div class="cstat"><div class="cstat-num" id="ovSvc">--</div><div class="cstat-lbl">Services</div></div>
        <div class="cstat"><div class="cstat-num" id="ovOps">--</div><div class="cstat-lbl">Ops</div></div>
        <div class="cstat"><div class="cstat-num" id="ovRtng">--</div><div class="cstat-lbl">Routings</div></div>
        <div class="cstat"><div class="cstat-num" id="ovNode">--</div><div class="cstat-lbl">Nodes</div></div>
        <div class="cstat"><div class="cstat-num" id="ovQueue">--</div><div class="cstat-lbl">Queues</div></div>
        <div class="cstat" style="grid-column:span 1;cursor:pointer;border-color:#00cc6633;" onclick="switchTab('txns')"><div class="cstat-num" style="font-size:11px;color:#00cc66;">&#9654;</div><div class="cstat-lbl">Txns</div></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;margin-top:8px;">
        <button style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('services')">&#127760; Browse Services</button>
        <button style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('operations')">&#9881; Browse Service Ops</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('routings')">&#8652; Routings</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('nodes')">&#128279; Nodes</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('queues')">&#11036; Queues</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('txns')">&#8644; Transactions</button>
      </div>
      <div id="dashboard" style="margin-top:10px;"></div>
    </div>

    <div id="tab-services" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="svcQ" type="text" placeholder="Search services…" onkeydown="if(event.key==='Enter')loadServices()">
        <button onclick="loadServices()">Go</button>
      </div>
      <div class="list-area" id="svcList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-operations" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="opQ" type="text" placeholder="Search service ops…" onkeydown="if(event.key==='Enter')loadOperations()">
        <button onclick="loadOperations()">Go</button>
      </div>
      <div class="list-area" id="opList"><span class="empty" style="padding:8px;">Type to search</span></div>
    </div>

    <div id="tab-routings" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="rtngQ" type="text" placeholder="Search routings…" onkeydown="if(event.key==='Enter')loadRoutings()">
        <button onclick="loadRoutings()">Go</button>
      </div>
      <div class="list-area" id="rtngList"><span class="empty" style="padding:8px;">Type to search</span></div>
    </div>

    <div id="tab-nodes" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="nodeQ" type="text" placeholder="Search nodes…" onkeydown="if(event.key==='Enter')loadNodes()">
        <button onclick="loadNodes()">Go</button>
      </div>
      <div class="list-area" id="nodeList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-queues" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="queueQ" type="text" placeholder="Search queues…" onkeydown="if(event.key==='Enter')loadQueues()">
        <button onclick="loadQueues()">Go</button>
      </div>
      <div class="list-area" id="queueList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-txns" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar" style="flex-direction:column;gap:4px;">
        <input id="txQ" type="text" placeholder="Operation / node / queue…" onkeydown="if(event.key==='Enter')loadTxns()">
        <div style="display:flex;gap:4px;">
          <select id="txStatus" style="flex:1;font-size:10px;">
            <option value="">All Status</option>
            <option value="1">New</option>
            <option value="2">Started</option>
            <option value="3">Done</option>
            <option value="4">Cancelled</option>
            <option value="5">Error</option>
            <option value="6">Retry</option>
            <option value="7">Timeout</option>
          </select>
          <button onclick="loadTxns()">Go</button>
        </div>
      </div>
      <div class="list-area" id="txList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

  </div><!-- .list-panel -->

  <!-- RIGHT: detail panel -->
  <div class="detail-panel" id="detailPanel">
    <div class="breadcrumb" id="breadcrumb"></div>
    <div class="detail-scroll" id="detailScroll">
      <div id="detailContent">
        <div class="detail-placeholder">
          <svg width="60" height="60" viewBox="0 0 60 60"><circle cx="30" cy="30" r="28" fill="none" stroke="#00e5ff" stroke-width="1.5"/><line x1="30" y1="10" x2="30" y2="50" stroke="#00e5ff" stroke-width="1"/><line x1="10" y1="30" x2="50" y2="30" stroke="#00e5ff" stroke-width="1"/></svg>
          <div>Select an object from the list to explore its relationships</div>
        </div>
      </div>
    </div>
  </div><!-- .detail-panel -->

</div><!-- .explorer -->

</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
let currentTab = 'overview';

function env() { return (window.dsGetEnv && window.dsGetEnv()) || 'HCM'; }

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path, opts) {
  const r = await fetch(path, opts || {});
  return r.json().catch(() => ({}));
}

// ─── nav stack (breadcrumbs) ───────────────────────────────────────────────
let navStack = [];
const NAV_ICONS = {service:'&#127760;',operation:'&#9881;',routing:'&#8652;',node:'&#128279;',queue:'&#11036;',txn:'&#8644;'};

// Rough IB parent→child depth order, used to keep the breadcrumb reading
// as a lineage rather than a raw click history. A Service Operation
// genuinely is a child of a Service, a Routing follows from an Operation,
// etc. — Transactions is always the deepest/leaf type since everything
// can drill into it.
const NAV_TYPE_RANK = {service:1, operation:2, routing:3, node:4, queue:5, txn:6};

function pushNav(type, name, push=true) {
  if (!push) return;
  // If clicking the same thing that's already at top of stack, skip
  if (navStack.length && navStack[navStack.length-1].type===type && navStack[navStack.length-1].name===name) {
    renderBreadcrumb(); return;
  }
  // Jumping to a related object (a "Related" chip, not necessarily a
  // strict drill-down) shouldn't just tack onto the raw click path — drop
  // anything already on the stack that isn't a plausible ancestor of the
  // new node (same or deeper rank), then append. A jump to a deeper type
  // extends the existing lineage; a jump to a shallower/sibling type
  // starts a new branch from whatever ancestors still apply.
  const rank = NAV_TYPE_RANK[type] || 99;
  navStack = navStack.filter(n => (NAV_TYPE_RANK[n.type] || 99) < rank);
  navStack.push({type, name});
  renderBreadcrumb();
}

function renderBreadcrumb() {
  const bc = $('breadcrumb');
  if (!navStack.length) { bc.innerHTML = '<span class="bc-cur" style="color:#334;">Select an object</span>'; return; }
  bc.innerHTML = '<span class="bc-link" onclick="navStack=[];clearDetail();">IB</span>'
    + navStack.map((n, i) => {
        const icon = NAV_ICONS[n.type] || '';
        const label = `${icon} ${esc(n.name)}`;
        return '<span class="bc-sep">›</span>'
          + (i < navStack.length-1
              ? `<span class="bc-link" onclick="navTo(${i})">${label}</span>`
              : `<span class="bc-cur">${label}</span>`);
      }).join('');
}

function navTo(idx) {
  const n = navStack[idx];
  navStack = navStack.slice(0, idx + 1);
  const fn = {service:showService,operation:showOperation,routing:showRouting,node:showNode,queue:showQueue,txn:showTxn}[n.type];
  if (fn) fn(n.name, false);
}

function clearDetail() {
  navStack = [];
  renderBreadcrumb();
  $('detailContent').innerHTML = '<div class="detail-placeholder"><div>Select an object from the list</div></div>';
  document.querySelectorAll('.list-item').forEach(el=>el.classList.remove('active'));
}

// Mark active item in list
function markActive(listId, name) {
  document.querySelectorAll(`#${listId} .list-item`).forEach(el => {
    el.classList.toggle('active', el.dataset.name === name);
  });
}

// ─── tabs ──────────────────────────────────────────────────────────────────
const TABS = ['overview','services','operations','routings','nodes','queues','txns'];
function switchTab(name) {
  currentTab = name;
  TABS.forEach(t => {
    const el = $(`tab-${t}`);
    if (el) el.style.display = t === name ? 'flex' : 'none';
  });
  document.querySelectorAll('.tab').forEach((el, i) => {
    el.classList.toggle('on', TABS[i] === name);
  });
  if (name === 'overview') loadDashboard();
  if (name === 'services' && !$('svcList').querySelector('.list-item')) loadServices();
  if (name === 'operations' && !$('opList').querySelector('.list-item')) loadOperations();
  if (name === 'routings' && !$('rtngList').querySelector('.list-item')) loadRoutings();
  if (name === 'nodes' && !$('nodeList').querySelector('.list-item')) loadNodes();
  if (name === 'queues' && !$('queueList').querySelector('.list-item')) loadQueues();
  if (name === 'txns') loadTxns();
}

// ─── list loaders ─────────────────────────────────────────────────────────
async function loadServices() {
  const q = $('svcQ').value;
  $('svcList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/services?env=${env()}&q=${encodeURIComponent(q)}&limit=500`);
  const items = d.items || [];
  renderList('svcList', items, item => {
    const b = bStatus(item.status_label);
    const kindCls = item.service_kind === 'REST' ? 'bd-info' : 'bd-mute';
    const kindText = item.service_kind === 'REST' ? 'REST' : 'STD';
    return `<div class="list-item" data-name="${esc(item.ptibapplname)}" onclick="showService('${item.ptibapplname}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="badge ${kindCls}">${kindText}</span>
      <span class="item-name">${esc(item.ptibapplname)}</span>
      <div class="item-meta">${esc(item.descr || '')}</div>
    </div>`;
  });
  if (items.length) {
    const note = document.createElement('div');
    note.style.cssText = 'font-size:10px;color:#334;padding:4px 8px;border-top:1px solid #0b1b24;';
    note.textContent = `${items.length} service${items.length===1?'':'s'}${q ? ' matching' : ' total'} · PSIBAPPLDEFN`;
    $('svcList').appendChild(note);
  }
  warnBox(d.warnings);
}

async function loadOperations() {
  const q = $('opQ').value;
  $('opList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/operations?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('opList', d.items || [], item => {
    const routeBits = item.routing_count != null ? `${item.routing_count}r` : '';
    return `<div class="list-item" data-name="${esc(item.ib_operationname)}" onclick="showOperation('${item.ib_operationname}')">
      <span class="badge bd-info">${esc(item.service_kind || 'Op')}</span>
      <span class="item-name">${esc(item.ib_operationname)}</span>
      <div class="item-meta">${esc(item.ib_servicename || item.ptibapplname || '')}${routeBits ? ' · ' + routeBits : ''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadRoutings() {
  const q = $('rtngQ').value;
  $('rtngList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/routings?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('rtngList', d.items || [], item => {
    return `<div class="list-item" data-name="${esc(item.routingdefnname)}" onclick="showRouting('${item.routingdefnname}')">
      <span class="item-name">${esc(item.routingdefnname)}</span>
      <div class="item-meta">${esc(item.sendernodename||'*')} → ${esc(item.receivernodename||'*')}${item.eff_status_label?' · '+esc(item.eff_status_label):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadNodes() {
  const q = $('nodeQ').value;
  $('nodeList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/nodes?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('nodeList', d.items || [], item => {
    const b = bStatus(item.active_label);
    const localTag = item.is_local ? ' <span style="font-size:9px;color:#00e5ff;">[LOCAL]</span>' : '';
    return `<div class="list-item" data-name="${esc(item.msgnodename)}" onclick="showNode('${item.msgnodename}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name">${esc(item.msgnodename)}</span>${localTag}
      <div class="item-meta">${esc(item.node_type_label||'')}${item.toolsrel?' · '+esc(item.toolsrel):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadQueues() {
  const q = $('queueQ').value;
  $('queueList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/queues?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('queueList', d.items || [], item => {
    const b = bQueue(item.queuestatus_label);
    return `<div class="list-item" data-name="${esc(item.queuename)}" onclick="showQueue('${item.queuename}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name">${esc(item.queuename)}</span>
      <div class="item-meta">${esc(item.descr||'')}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadTxns() {
  const q  = $('txQ').value;
  const st = $('txStatus').value;
  $('txList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  let url = `/api/ib/transactions?env=${env()}&q=${encodeURIComponent(q)}&limit=100`;
  if (st) url += `&status=${st}`;
  const d = await api(url);
  renderList('txList', d.items || [], item => {
    const b = bTx(item.pubstatus_label);
    return `<div class="list-item" data-name="${esc(item.ibtransactionid)}" onclick="showTxn('${item.ibtransactionid}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name mono" style="font-size:10px;">${esc((item.ibtransactionid||'').substring(0,26))}</span>
      <div class="item-meta">${esc(item.ib_operationname||'')}${item.queuename?' · '+esc(item.queuename):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

function renderList(targetId, items, rowFn) {
  const box = $(targetId);
  if (!items.length) { box.innerHTML = '<span class="empty" style="padding:8px;">No results.</span>'; return; }
  box.innerHTML = items.map(rowFn).join('');
}

// ─── view transactions for a related object ────────────────────────────────
function viewTxnsFor(q) {
  $('txQ').value = q;
  $('txStatus').value = '';
  switchTab('txns');
  loadTxns();
}

// ─── relationship strip builder ────────────────────────────────────────────
function relStrip(label, tags) {
  if (!tags.length) return '';
  const tagsHtml = tags.map(t => `<span class="rel-tag${t.cls?' '+t.cls:''}" onclick="${t.action}">${t.icon||''}${esc(t.label)}</span>`).join('');
  return `<div class="rel-strip"><span class="rel-strip-label">${esc(label)}</span>${tagsHtml}</div>`;
}

// ─── detail views ──────────────────────────────────────────────────────────
function setDetail(html) {
  $('detailContent').innerHTML = html;
  $('detailScroll').scrollTop = 0;
}

async function showService(name, push=true) {
  pushNav('service', name, push);
  switchTab('services');
  markActive('svcList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/services/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const ops = it.service_operations || [];
  const opTags = ops.slice(0,8).map(op => ({label:op.ib_operationname, action:`showOperation('${op.ib_operationname}')`}));
  if (ops.length > 8) opTags.push({label:`+${ops.length-8} more`, action:`switchTab('operations')`});

  let h = relStrip('Operations', opTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#127760; ${esc(it.ptibapplname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card">
    <div class="kv-grid">
      ${kv('Status', chipStatus(it.status_label))}
      ${kv('Type', chipKind(it.service_kind || it.appltype_label))}
      ${kv('Service Name', esc(it.ib_servicename))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div>
  </div>`;

  if (ops.length) {
    h += `<h2>Service Operations (${ops.length})</h2><div class="card"><table><thead><tr>
      <th>Operation</th><th>Type</th><th>Method</th><th>Description</th>
    </tr></thead><tbody>`;
    ops.forEach(op => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showOperation('${op.ib_operationname}')">${esc(op.ib_operationname || '')}</a></td>
        <td>${esc(op.service_kind || '')}</td>
        <td>${esc(op.ib_restmethod || '')}</td><td>${esc(op.descr || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.operations||[]).length) {
    h += `<h2>Application Operations (${it.operations.length})</h2><div class="card"><table><thead><tr>
      <th>Operation</th><th>Status</th><th>Action</th><th>URI Template</th>
    </tr></thead><tbody>`;
    it.operations.forEach(op => {
      h += `<tr><td class="mono">${esc(op.ptibapplopr)}</td><td>${chipStatus(op.status_label)}</td>
        <td>${esc(op.ib_action||'')}</td><td class="mono" style="font-size:10px;">${esc(op.ib_uri_template||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.routings||[]).length) {
    h += `<h2>Routings (${it.routings.length})</h2><div class="card"><table><thead><tr>
      <th>Routing</th><th>From</th><th>To</th><th>Status</th>
    </tr></thead><tbody>`;
    it.routings.forEach(r => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.sendernodename}')">${esc(r.sendernodename||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.receivernodename}')">${esc(r.receivernodename||'')}</a></td>
        <td>${chipStatus(r.eff_status_label)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showOperation(name, push=true) {
  pushNav('operation', name, push);
  switchTab('operations');
  markActive('opList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/operations/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  // Build relationship strip
  const relTags = [];
  const svcName = it.ib_servicename || it.ptibapplname;
  if (svcName) relTags.push({icon:'&#127760; ', label:`${svcName}`, action:`showService('${svcName}')`});
  (it.routings||[]).slice(0,3).forEach(r => {
    relTags.push({icon:'&#8652; ', label:`${r.routingdefnname}`, action:`showRouting('${r.routingdefnname}')`});
  });
  (it.runtime_queues||[]).slice(0,2).forEach(q => {
    relTags.push({icon:'&#11036; ', label:`${q.queuename}`, action:`showQueue('${q.queuename}')`});
  });
  relTags.push({icon:'&#8644; ', label:'Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#9881; ${esc(it.ib_operationname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Type', esc(it.service_kind))}
      ${svcName ? kv('Service', `<a class="obj-link" onclick="showService('${svcName}')">${esc(svcName)}</a>`) : ''}
      ${kv('Alias', esc(it.ib_aliasname))}
      ${kv('Default Version', esc(it.defaultver || it.versionname))}
      ${kv('REST Method', esc(it.ib_restmethod))}
      ${it.ib_restbase_url ? kv('REST Base URL', esc(it.ib_restbase_url)) : ''}
      ${kv('Routings', esc(it.routing_count))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.messages||[]).length) {
    h += `<h2>Messages (${it.messages.length})</h2><div class="card"><table><thead><tr>
      <th>Version</th><th>Request Msg</th><th>Response Msg</th><th>Queue</th>
    </tr></thead><tbody>`;
    it.messages.forEach(m => {
      const qname = m.queuename || '';
      h += `<tr><td class="mono">${esc(m.versionname || '')}</td>
        <td class="mono">${esc(m.ib_reqmsgname || m.msgname || '')}${m.inmsgversion ? ' v'+esc(m.inmsgversion) : ''}</td>
        <td class="mono">${esc(m.ib_respmsgname || '')}${m.outmsgversion ? ' v'+esc(m.outmsgversion) : ''}</td>
        <td class="mono">${qname ? `<a class="obj-link" onclick="showQueue('${qname}')">${esc(qname)}</a>` : ''}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.routings||[]).length) {
    h += `<h2>Routings (${it.routings.length})</h2><div class="card"><table><thead><tr>
      <th>Routing</th><th>Sender Node</th><th>Receiver Node</th><th>Status</th>
    </tr></thead><tbody>`;
    it.routings.forEach(r => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.sendernodename}')">${esc(r.sendernodename || '')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.receivernodename}')">${esc(r.receivernodename || '')}</a></td>
        <td>${chipStatus(r.eff_status_label)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.handlers||[]).length) {
    h += `<h2>Handlers (${it.handlers.length})</h2><div class="card"><table><thead><tr>
      <th>Handler</th><th>Type</th><th>Version</th><th>Status</th><th>Owner</th>
    </tr></thead><tbody>`;
    it.handlers.forEach(x => {
      h += `<tr><td class="mono">${esc(x.handlername || '')}</td><td>${esc(x.handlertype || '')}</td>
        <td class="mono">${esc(x.version || '')}</td><td>${chipStatus(x.active_label)}</td>
        <td>${esc(x.handlerowner || x.objectownerid || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.runtime_queues||[]).length) {
    h += `<h2>Runtime Queues (${it.runtime_queues.length})</h2><div class="card"><table><thead><tr>
      <th>Queue</th><th>Status</th><th>Count</th><th>Last Created</th>
    </tr></thead><tbody>`;
    it.runtime_queues.forEach(q => {
      h += `<tr><td class="mono"><a class="obj-link" onclick="showQueue('${q.queuename}')">${esc(q.queuename || '')}</a></td>
        <td>${chipTx(q.pubstatus_label)}</td><td>${esc(q.cnt)}</td><td class="ts">${esc(q.last_created || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.versions||[]).length) {
    h += `<h2>Versions (${it.versions.length})</h2><div class="card"><table><thead><tr>
      <th>Version</th><th>Status</th><th>Multi Queue</th><th>Description</th>
    </tr></thead><tbody>`;
    it.versions.forEach(v => {
      h += `<tr><td class="mono">${esc(v.versionname || v.version || '')}</td>
        <td>${chipStatus(v.active_label)}</td><td>${esc(v.ib_multiqueue || '')}</td>
        <td>${esc(v.descr || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.security||[]).length) {
    h += `<h2>Security (${it.security.length})</h2><div class="card"><table><thead><tr>
      <th>Service</th><th>Group</th><th>Security</th>
    </tr></thead><tbody>`;
    it.security.forEach(s => {
      h += `<tr><td class="mono">${esc(s.ib_servicename || '')}</td>
        <td class="mono">${esc(s.ib_intgroupname || '')}</td>
        <td>${esc(s.ib_servicesecurity || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showRouting(name, push=true) {
  pushNav('routing', name, push);
  switchTab('routings');
  markActive('rtngList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/routings/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const relTags = [];
  if (it.ib_operationname) relTags.push({icon:'&#9881; ', label:`${it.ib_operationname}`, action:`showOperation('${it.ib_operationname}')`});
  if (it.sendernodename) relTags.push({icon:'&#8594; ', label:`${it.sendernodename}`, action:`showNode('${it.sendernodename}')`});
  if (it.receivernodename) relTags.push({icon:'&#8592; ', label:`${it.receivernodename}`, action:`showNode('${it.receivernodename}')`});
  relTags.push({icon:'&#8644; ', label:'Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#8652; ${esc(it.routingdefnname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipStatus(it.eff_status_label))}
      ${kv('Type', esc(it.rtngtype_label))}
      ${kv('Service Operation', `<a class="obj-link" onclick="showOperation('${it.ib_operationname}')">${esc(it.ib_operationname)}</a>`)}
      ${kv('Sender Node', `<a class="obj-link" onclick="showNode('${it.sendernodename}')">${esc(it.sendernodename)}</a>`)}
      ${kv('Receiver Node', `<a class="obj-link" onclick="showNode('${it.receivernodename}')">${esc(it.receivernodename)}</a>`)}
      ${kv('REST Method', esc(it.ib_restmethod))}
      ${kv('Delivery Mode', esc(it.ib_deliverymode))}
      ${kv('Effective Date', esc(it.effdt))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.sub_definitions||[]).length) {
    h += `<h2>Sub-Definitions (${it.sub_definitions.length})</h2><div class="card"><table><thead><tr>
      <th>Seq</th><th>Direction</th><th>From Node</th><th>To Node</th><th>Type</th>
    </tr></thead><tbody>`;
    it.sub_definitions.forEach(s => {
      h += `<tr><td>${esc(s.seqnum)}</td><td>${esc(s.ib_direction)}</td>
        <td class="mono"><a class="obj-link" onclick="showNode('${s.sendernodename}')">${esc(s.sendernodename||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${s.receivernodename}')">${esc(s.receivernodename||'')}</a></td>
        <td>${esc(s.rtngtype)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showNode(name, push=true) {
  if (!name || name === 'null' || name === 'undefined') return;
  pushNav('node', name, push);
  switchTab('nodes');
  markActive('nodeList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/nodes/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const allRoutings = [...(it.routings_as_sender||[]), ...(it.routings_as_receiver||[])];
  const uniqueOps = [...new Set(allRoutings.map(r=>r.ib_operationname).filter(Boolean))];
  const relTags = uniqueOps.slice(0,5).map(op => ({icon:'&#9881; ', label:`${op}`, action:`showOperation('${op}')`}));
  relTags.push({icon:'&#8644; ', label:'Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related Ops', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">
    &#128279; ${esc(it.msgnodename)}
    ${it.is_local ? '<span class="chip ch-info" style="font-size:9px;margin-left:6px;">LOCAL</span>' : ''}
    ${it.is_default ? '<span class="chip ch-info" style="font-size:9px;margin-left:4px;">DEFAULT</span>' : ''}
  </div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipActive(it.active_label))}
      ${kv('Node Type', esc(it.node_type_label))}
      ${kv('Tools Release', esc(it.toolsrel))}
      ${kv('App Release', esc(it.apmsgapprel))}
      ${it.ib_tgtlocation ? kv('Target Location', esc(it.ib_tgtlocation)) : ''}
      ${it.conngatewayid ? kv('Gateway ID', esc(it.conngatewayid)) : ''}
      ${it.networknodename ? kv('Network Node', esc(it.networknodename)) : ''}
      ${it.hubnodename ? kv('Hub Node', esc(it.hubnodename)) : ''}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.routings_as_sender||[]).length) h += rtngTable('Sends Via Routings', it.routings_as_sender);
  if ((it.routings_as_receiver||[]).length) h += rtngTable('Receives Via Routings', it.routings_as_receiver);

  warnBox(d.warnings);
  setDetail(h);
}

function rtngTable(title, rows) {
  let h = `<h2>${esc(title)} (${rows.length})</h2><div class="card"><table><thead><tr>
    <th>Routing</th><th>Operation</th><th>From</th><th>To</th><th>Status</th>
  </tr></thead><tbody>`;
  rows.forEach(r => {
    h += `<tr>
      <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
      <td class="mono"><a class="obj-link" onclick="showOperation('${r.ib_operationname}')">${esc(r.ib_operationname||'')}</a></td>
      <td class="mono">${esc(r.sendernodename||'')}</td><td class="mono">${esc(r.receivernodename||'')}</td>
      <td>${chipStatus(r.eff_status_label)}</td></tr>`;
  });
  return h + '</tbody></table></div>';
}

async function showQueue(name, push=true) {
  pushNav('queue', name, push);
  switchTab('queues');
  markActive('queueList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/queues/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const relTags = [{icon:'&#8644; ', label:'Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`}];

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#11036; ${esc(it.queuename)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipQueue(it.queuestatus_label))}
      ${kv('Throughput', esc(it.thruput_label))}
      ${kv('Priority', esc(it.ptib_queue_pri))}
      ${kv('Archive', esc(it.archive))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  const rt = it.runtime || {};
  if ((rt.pub_by_status||[]).length || (rt.sub_by_status||[]).length) {
    h += `<h2>Runtime Activity (24h)</h2><div class="card">`;
    if (rt.pub_by_status && rt.pub_by_status.length) {
      h += `<div style="margin-bottom:6px;"><span style="font-size:10px;color:#667;text-transform:uppercase;margin-right:6px;">Pub:</span>`;
      rt.pub_by_status.forEach(s => { h += `${chipTx(s.status_label)}&nbsp;<span class="mono" style="margin-right:8px;">${s.cnt}</span>`; });
      h += '</div>';
    }
    if (rt.sub_by_status && rt.sub_by_status.length) {
      h += `<div><span style="font-size:10px;color:#667;text-transform:uppercase;margin-right:6px;">Sub:</span>`;
      rt.sub_by_status.forEach(s => { h += `${chipTx(s.status_label)}&nbsp;<span class="mono" style="margin-right:8px;">${s.cnt}</span>`; });
      h += '</div>';
    }
    h += '</div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showTxn(txid, push=true) {
  pushNav('txn', txid, push);
  switchTab('txns');
  markActive('txList', txid);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/transactions/${encodeURIComponent(txid)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found.</div>`); return; }

  const relTags = [];
  if (it.ib_operationname) relTags.push({icon:'&#9881; ', label:`${it.ib_operationname}`, action:`showOperation('${it.ib_operationname}')`});
  if (it.queuename) relTags.push({icon:'&#11036; ', label:`${it.queuename}`, action:`showQueue('${it.queuename}')`});
  if (it.pubnode) relTags.push({icon:'&#128279; ', label:`${it.pubnode}`, action:`showNode('${it.pubnode}')`});

  let h = relStrip('Path', relTags);
  h += `<div style="font-family:monospace;color:#00e5ff;font-size:11px;margin-bottom:4px;">&#8644; ${esc((txid||'').substring(0,36))}</div>`;

  h += `<h2>Operation Instance</h2><div class="card"><div class="kv-grid">
      ${kv('Status', chipTx(it.pubstatus_label))}
      ${kv('Operation', `<a class="obj-link" onclick="showOperation('${it.ib_operationname}')">${esc(it.ib_operationname)}</a>`)}
      ${kv('Queue', it.queuename ? `<a class="obj-link" onclick="showQueue('${it.queuename}')">${esc(it.queuename)}</a>` : '')}
      ${kv('Pub Node', it.pubnode ? `<a class="obj-link" onclick="showNode('${it.pubnode}')">${esc(it.pubnode)}</a>` : '')}
      ${it.destpubnode ? kv('Dest Node', esc(it.destpubnode)) : ''}
      ${kv('Publisher', esc(it.publisher))}
      ${kv('Created', esc(it.createdttm))}
      ${kv('Retry Count', esc(it.retrycount))}
      ${kv('Machine', esc(it.machinename))}
    </div>
    ${it.statusstring ? `<div class="warn-msg" style="margin-top:6px;">${esc(it.statusstring)}</div>` : ''}
  </div>`;

  h += `<h2>Publication Transaction${(it.pub_contracts||[]).length === 1 ? '' : 's'} (${(it.pub_contracts||[]).length})</h2>`;
  if ((it.pub_contracts||[]).length) {
    h += `<div class="card"><table><thead><tr>
      <th>Sub Node</th><th>Routing</th><th>Status</th><th>Retries</th><th>Updated</th>
    </tr></thead><tbody>`;
    it.pub_contracts.forEach(c => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showNode('${c.subnode}')">${esc(c.subnode||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showRouting('${c.routingdefnname}')">${esc(c.routingdefnname||'')}</a></td>
        <td>${chipTx(c.pubconstatus_label)}</td><td>${esc(c.retrycount)}</td>
        <td class="ts">${esc(c.lastupddttm||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  } else {
    h += `<div class="card"><span class="empty">None for this transaction.</span></div>`;
  }

  h += `<h2>Subscription Transaction${(it.sub_contracts||[]).length === 1 ? '' : 's'} (${(it.sub_contracts||[]).length})</h2>`;
  if ((it.sub_contracts||[]).length) {
    h += `<div class="card"><table><thead><tr>
      <th>Sub Txn ID</th><th>Action</th><th>Operation</th><th>Routing</th><th>Status</th><th>Proc Inst</th>
    </tr></thead><tbody>`;
    it.sub_contracts.forEach(c => {
      h += `<tr><td class="mono" style="font-size:10px;">${esc((c.ibtransactionid||'').substring(0,36))}</td>
        <td class="mono">${esc(c.actionname||'')}</td>
        <td class="mono"><a class="obj-link" onclick="showOperation('${c.ib_operationname}')">${esc(c.ib_operationname||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showRouting('${c.routingdefnname}')">${esc(c.routingdefnname||'')}</a></td>
        <td>${chipTx(c.subconstatus_label)}</td>
        <td>${esc(c.process_instance||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  } else {
    h += `<div class="card"><span class="empty">None for this transaction.</span></div>`;
  }

  h += `<h2>Request Message Body</h2>`;
  if (it.request_body && it.request_body.content) {
    h += `<div class="card"><div style="font-size:11px;color:#888;margin-bottom:4px;">${it.request_body.segments} segment(s), decompressed</div>
      <pre style="white-space:pre-wrap;word-break:break-all;font-size:11px;max-height:400px;overflow:auto;margin:0;">${esc(it.request_body.content)}</pre></div>`;
  } else {
    h += `<div class="card"><span class="empty">No message body available for this transaction.</span></div>`;
  }

  if ((it.errors||[]).length) {
    h += `<h2>IB Errors (${it.errors.length})</h2><div class="card"><table><thead><tr>
      <th>Time</th><th>Message</th><th>Severity</th><th>Params</th>
    </tr></thead><tbody>`;
    it.errors.forEach(e => {
      h += `<tr><td class="ts">${esc(e.errortimestamp||'')}</td>
        <td>${esc(e.message_text || `Msg Set ${e.message_set_nbr}, Msg ${e.message_nbr}`)}</td>
        <td>${esc(e.msg_severity||'')}</td>
        <td class="mono">${esc((e.params||[]).join(', '))}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

// ─── dashboard ────────────────────────────────────────────────────────────
async function loadDashboard() {
  const dashboard = $('dashboard');
  if (!dashboard) return;
  const d = await api(`/api/ib/dashboard?env=${env()}`);
  let h = '';

  const configured = d.service_count != null || d.node_count != null;
  if (!configured) {
    h += `<div class="card"><div class="warn-msg">IB metadata tables are not accessible in this environment.
      The monitoring account may lack grants to PSIBAPPLDEFN, PSIBRTNGDEFN, PSMSGNODEDEFN and related tables.</div></div>`;
    (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">${esc(w.message||w)}</div>`; });
    dashboard.innerHTML = h;
    return;
  }

  $('ovSvc').textContent   = d.service_count != null ? d.service_count : '--';
  $('ovOps').textContent   = d.operation_count != null ? d.operation_count : '--';
  $('ovRtng').textContent  = d.routing_count != null ? d.routing_count : '--';
  $('ovNode').textContent  = d.node_count != null ? d.node_count : '--';
  $('ovQueue').textContent = d.queue_count != null ? d.queue_count : '--';

  if ((d.pub_by_status||[]).length) {
    h += `<h2>Publications — Last 24h</h2><div class="card" style="display:flex;gap:16px;flex-wrap:wrap;">`;
    d.pub_by_status.forEach(s => {
      h += `<div style="text-align:center;"><div class="stat-num" style="font-size:18px;">${esc(s.cnt)}</div><div>${chipTx(s.status_label)}</div></div>`;
    });
    h += '</div>';
  }

  if ((d.sub_by_status||[]).length) {
    h += `<h2>Subscriptions — Last 24h</h2><div class="card" style="display:flex;gap:16px;flex-wrap:wrap;">`;
    d.sub_by_status.forEach(s => {
      h += `<div style="text-align:center;"><div class="stat-num" style="font-size:18px;">${esc(s.cnt)}</div><div>${chipTx(s.status_label)}</div></div>`;
    });
    h += '</div>';
  }

  if ((d.domain_status||[]).length) {
    h += `<h2>Domain Status</h2><div class="card"><table><thead><tr>
      <th>Domain ID</th><th>Machine</th><th>Server Domain</th><th>Last Updated</th>
    </tr></thead><tbody>`;
    d.domain_status.forEach(ds => {
      h += `<tr><td class="mono">${esc(ds.ibdomainid||'')}</td><td>${esc(ds.machinename||'')}</td>
        <td>${esc(ds.serverdomainname||'')}</td><td class="ts">${esc(ds.lastupddttm||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">${esc(w.message||w)}</div>`; });
  $('dashboard').innerHTML = h;
}

// ─── helpers ──────────────────────────────────────────────────────────────
function kv(label, val) {
  if (val == null || val === '') return '';
  return `<div class="kv-key">${esc(label)}</div><div class="kv-val">${val}</div>`;
}
function sBox(n, lbl) {
  return `<div class="stat-box"><div class="stat-num">${n != null ? n : '—'}</div><div class="stat-lbl">${esc(lbl)}</div></div>`;
}
function bStatus(l) { return l === 'Active' ? {cls:'bd-ok',text:l||''} : {cls:'bd-mute',text:l||''}; }
function bQueue(l)  { return l === 'Running' ? {cls:'bd-ok',text:l} : l === 'Halted' ? {cls:'bd-err',text:l} : {cls:'bd-warn',text:l||''}; }
function bTx(l)     { return (l==='Error'||l==='Timeout') ? {cls:'bd-err',text:l} : l==='Done' ? {cls:'bd-ok',text:l} : {cls:'bd-mute',text:l||''}; }
function chipStatus(l) { const c=l==='Active'?'ch-ok':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipKind(k)   { const c=k==='REST'?'ch-info':'ch-mute'; return `<span class="chip ${c}">${esc(k==='REST'?'REST':'STD')}</span>`; }
function chipActive(l) { const c=l==='Active'?'ch-ok':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipQueue(l)  { const c=l==='Running'?'ch-ok':l==='Halted'?'ch-err':'ch-warn'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipTx(l)     { const c=(l==='Error'||l==='Timeout')?'ch-err':l==='Done'?'ch-ok':l==='Started'?'ch-warn':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function warnBox(ws) {
  if (!ws||!ws.length) return;
  const box = document.querySelector('#detailContent .warn-container') || (() => {
    const el = document.createElement('div');
    el.className = 'warn-container';
    $('detailContent').appendChild(el);
    return el;
  })();
  box.innerHTML = ws.map(w => `<div class="warn-msg">${esc(w.message||w)}</div>`).join('');
}

// ─── init ─────────────────────────────────────────────────────────────────
function reload() {
  const dashboard = $('dashboard');
  if (dashboard) dashboard.innerHTML = '';
  clearDetail();
  loadDashboard();
  loadServices();
  loadOperations();
  loadNodes();
  loadQueues();
}

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event — this page
// previously defined neither, so switching environments silently left every
// panel (Overview counts, open object detail, tab contents) stuck on
// whatever env was active at initial page load.
window.onEnvChange = reload;
document.addEventListener('deathstar:envchange', reload);

(async () => {
  renderBreadcrumb();

  await Promise.all([loadDashboard(), loadServices(), loadNodes(), loadQueues()]);

  // Deep-link: /admin/ib?tab=services&show=MY_SERVICE  (from Object Explorer global search)
  const params = new URLSearchParams(location.search);
  const deepTab  = params.get('tab');
  const deepShow = params.get('show');
  if (deepTab && deepShow) {
    switchTab(deepTab);
    const tabShowMap = {
      services: showService, operations: showOperation, routings: showRouting,
      nodes: showNode, queues: showQueue, txns: showTxn,
    };
    const fn = tabShowMap[deepTab];
    if (fn) fn(deepShow);
  } else {
    switchTab('overview');
  }
})();
</script>""")


@router.get("/ibmessage")
def admin_ibmessage(request: Request):
    nav = _nav_html("ibmessage", '<select class="ds-env-sel" id="globalEnv" style="background:transparent;color:#00e5ff;border:1px solid rgba(0,229,255,.3);border-radius:3px;font-size:11px;padding:2px 6px"></select>')
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="/static/app.js?v=2"></script><title>IB Messages</title>
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
.item.sel{{background:#12121e;border-left-color:#cc44ff}}
.item-name{{font-family:monospace;font-size:12px;color:#cc44ff;font-weight:bold}}
.item-meta{{font-size:10px;color:#556;margin-top:2px}}
.item-descr{{font-size:11px;color:#889;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.detail{{flex:1;overflow-y:auto;padding:20px}}
.muted{{color:#445;font-size:12px;padding:20px}}
h2{{color:#cc44ff;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #1e1e2a}}
.kv-grid{{display:grid;grid-template-columns:140px 1fr;gap:4px 10px;font-size:12px;margin-bottom:10px}}
.kv-key{{color:#556;padding-top:1px}}
.kv-val{{color:#aab;font-family:monospace;word-break:break-all}}
.chip{{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;margin:1px 3px 1px 0;white-space:nowrap}}
.chip-ok{{background:#0a1a0a;border:1px solid #22cc6644;color:#22cc66}}
.chip-info{{background:#001018;border:1px solid #00ccee44;color:#00ccee}}
.chip-muted{{background:#1a1a1a;border:1px solid #33333388;color:#778}}
.chip-purple{{background:#180a1a;border:1px solid #cc44ff44;color:#cc44ff}}
.stat{{display:inline-block;margin-right:14px;font-size:11px;color:#556}}
.stat b{{color:#cc44ff;font-size:14px;margin-right:4px}}
.field-row{{display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid #1a1a22;font-size:12px}}
</style></head>
<body>
{nav}
<div class="shell">
  <div class="sidebar">
    <div class="filters">
      <input id="qInput" placeholder="Search message name / description…" oninput="doSearch()">
    </div>
    <div class="list" id="list"></div>
  </div>
  <div class="detail" id="detail"><div class="muted">Select an IB message definition.</div></div>
</div>
<script>
function ENVVAL() {{ return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HRDMO'); }}
let _all = [];

async function api(url) {{
  try {{ const r = await fetch(url); return r.ok ? r.json() : null; }} catch {{ return null; }}
}}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function chip(cls, label) {{ return `<span class="chip ${{cls}}">${{esc(label)}}</span>`; }}

function statusChip(s) {{
  return s === 'Active' ? chip('chip-ok', 'Active') : chip('chip-muted', s||'?');
}}

async function doSearch() {{
  const q = document.getElementById('qInput').value;
  const data = await api(`/api/peoplesoft/ib-messages?env=${{ENVVAL()}}&q=${{encodeURIComponent(q)}}&limit=500`);
  _all = (data?.items || []);
  const list = document.getElementById('list');
  list.innerHTML = _all.map((it, i) => `
    <div class="item" id="item-${{i}}" onclick="selectItem(${{i}}, '${{encodeURIComponent(it.msgname)}}')">
      <div class="item-name">${{esc(it.msgname)}}</div>
      <div class="item-meta">${{esc((it.chnlname||'').trim()||'No Queue')}} · ${{esc(it.msgstatus_label||'')}}</div>
      <div class="item-descr">${{esc(it.descr||'')}}</div>
    </div>`).join('');
}}

async function selectItem(idx, name) {{
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${{idx}}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/message/${{name}}?env=${{ENVVAL()}}`);
  if (!d) {{ detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }}

  const uom = d._uom || {{}};
  const sections = d.sections || [];
  const ovSec = sections.find(s => s.id === 'overview');
  const verSec = sections.find(s => s.id === 'versions');
  const recSec = sections.find(s => s.id === 'schema_records');
  const counts = uom.counts || {{}};

  let html = `<div style="margin-bottom:12px">
    ${{statusChip(uom.status_label)}}
    <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#cc44ff">${{esc(uom.name||'')}}</span>
  </div>`;
  if (uom.title && uom.title !== uom.name) {{
    html += `<div style="color:#889;font-size:13px;margin-bottom:12px">${{esc(uom.title)}}</div>`;
  }}

  const ovRows = (ovSec?.rows || []).filter(r => r.label !== 'Status');
  if (ovRows.length) {{
    html += `<div class="kv-grid">`;
    for (const row of ovRows) {{
      const val = row.value ? esc(String(row.value)) :
        (row.chips||[]).map(c => chip(c.cls||'chip-info', c.label)).join('') || '';
      html += `<div class="kv-key">${{esc(row.label)}}</div><div class="kv-val">${{val}}</div>`;
    }}
    html += `</div>`;
  }}

  html += `<div style="margin:10px 0">
    <span class="stat"><b>${{counts.versions||0}}</b>Versions</span>
    <span class="stat"><b>${{counts.schema_records||0}}</b>Schema Records</span>
  </div>`;

  if (verSec?.items?.length) {{
    html += `<h2>Versions</h2>`;
    html += verSec.items.map(it =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#cc44ff;min-width:100px">${{esc(it.name)}}</span>
         ${{(it.chips||[]).map(c => chip(c.cls||'chip-muted', c.label)).join('')}}
       </div>`
    ).join('');
  }}
  if (recSec?.items?.length) {{
    html += `<h2>Schema Records (${{recSec.items.length}})</h2>`;
    html += recSec.items.map(it =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#aad;min-width:180px">${{esc(it.name)}}</span>
         ${{it.meta ? `<span style="color:#445;font-size:10px">${{esc(it.meta)}}</span>` : ''}}
       </div>`
    ).join('');
  }}

  if (!ovRows.length && !verSec && !recSec) {{
    html += `<div class="muted">No detail available.</div>`;
  }}
  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/ibapp", response_class=HTMLResponse)
def admin_ibapp(request: Request):
    nav = _nav_html("ibapp", '<select class="ds-env-sel" id="globalEnv" style="background:transparent;color:#00e5ff;border:1px solid rgba(0,229,255,.3);border-radius:3px;font-size:11px;padding:2px 6px"></select>')
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>IB Application Services</title>
<meta charset="utf-8">
<script src="/static/app.js?v=2"></script>
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:10px">
    <input id="q" placeholder="Search applications…" oninput="doSearch()"
      style="width:100%;box-sizing:border-box;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
  </div>
  <div id="list" style="font-size:13px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select an IB Application Service to view its REST endpoints and operations.</div>
</div>
</div>
<script>
{_ESC_JS}
function ENVVAL() {{ return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HRDMO'); }}
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const url = `/api/peoplesoft/ib-applications?env=${{encodeURIComponent(ENVVAL())}}&q=${{encodeURIComponent(q)}}&limit=100`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.ptibapplname || '';
    const grp = (r.ptib_appsrvgrp || '').trim();
    const opCnt = r.op_count || 0;
    const status = (r.status || '').trim();
    const statusDot = status === 'A' ? '🟢' : '🔴';
    const descr = (r.descr || '').trim().slice(0, 80);
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:7px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #111">
      <div style="font-weight:bold;color:#00ddcc;font-family:monospace">${{esc(name)}} ${{statusDot}}</div>
      ${{grp ? `<div style="color:#778;font-size:11px">${{esc(grp)}} · ${{opCnt}} ops</div>` : ''}}
      ${{descr ? `<div style="color:#667;font-size:11px;margin-top:2px">${{esc(descr)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

const METHOD_COLOR = {{GET:'#22cc66',POST:'#4499ff',PUT:'#ddaa22',DELETE:'#ff5555',PATCH:'#ff8822'}};

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/ib_application/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENVVAL())}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const opSec = secs.find(s=>s.title?.includes('Operations'));
  const epSec = secs.find(s=>s.title?.includes('Endpoints'));
  const stSec = secs.find(s=>s.title?.includes('Response States'));

  let html = `<h1 style="color:#00ddcc;font-size:18px;margin:0 0 4px">${{esc(uom.display_name || name)}}</h1>`;

  // Overview KV
  if (ovSec?.rows?.length) {{
    html += '<table style="border-collapse:collapse;margin-bottom:16px;font-size:13px">';
    ovSec.rows.forEach(row => {{
      if (!row.value || row.value === '—') return;
      html += `<tr><td style="color:#556;padding:2px 16px 2px 0;white-space:nowrap;vertical-align:top">${{esc(row.key)}}</td>
        <td style="color:#acd;font-family:monospace;word-break:break-all">${{esc(String(row.value))}}</td></tr>`;
    }});
    html += '</table>';
  }}

  // Operations
  if (opSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:14px;margin:16px 0 8px">${{esc(opSec.title)}}</h2>`;
    html += opSec.items.map(op => {{
      const chips = (op.chips||[]).map(ch => {{
        const c = METHOD_COLOR[ch.label] || '#778';
        return `<span style="display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#001;border:1px solid ${{c}}44;color:${{c}};margin-right:4px">${{esc(ch.label)}}</span>`;
      }}).join('');
      const meta = op.meta ? `<div style="color:#445;font-size:11px;font-family:monospace;margin-top:3px">${{esc(op.meta)}}</div>` : '';
      return `<div style="padding:6px 10px;border-left:2px solid #1a3a4a;margin-bottom:6px">
        <div style="font-family:monospace;color:#78c;font-size:13px">${{chips}}${{esc(op.name)}}</div>
        ${{meta}}
      </div>`;
    }}).join('');
  }}

  // Endpoints (detailed)
  if (epSec?.items?.length) {{
    html += `<h2 style="color:#aab;font-size:14px;margin:16px 0 8px">${{esc(epSec.title)}}</h2>`;
    html += '<div style="font-family:monospace;font-size:12px">';
    html += epSec.items.map(ep => {{
      const method = ep.chips?.[0]?.label || '';
      const mc = METHOD_COLOR[method] || '#778';
      const meta = ep.meta ? `<span style="color:#445;margin-left:12px;font-family:sans-serif;font-size:11px">${{esc(ep.meta)}}</span>` : '';
      return `<div style="padding:3px 8px;border-bottom:1px solid #0d1a2a">
        <span style="display:inline-block;min-width:52px;color:${{mc}};font-weight:bold">${{esc(method)}}</span>
        <span style="color:#8ac">${{esc(ep.name)}}</span>${{meta}}
      </div>`;
    }}).join('');
    html += '</div>';
  }}

  if (!ovSec && !opSec && !epSec) {{
    html += '<div class="muted">No detail available.</div>';
  }}

  detail.innerHTML = html;
}}

doSearch();
</script>
</body></html>""")


@router.get("/ibsvcgrp", response_class=HTMLResponse)
def admin_ibsvcgrp(request: Request):
    nav = _nav_html("ibsvcgrp", '<select class="ds-env-sel" id="globalEnv" style="background:transparent;color:#00e5ff;border:1px solid rgba(0,229,255,.3);border-radius:3px;font-size:11px;padding:2px 6px"></select>')
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>IB Service Groups</title>
<meta charset="utf-8">
<script src="/static/app.js?v=2"></script>
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:340px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search group name or description…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select an IB Service Group to view its member service operations.</div>
</div>
</div>
<script>
{_ESC_JS}
function ENVVAL() {{ return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HRDMO'); }}
let selected = null;

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const url = `/api/peoplesoft/ib-service-groups?env=${{encodeURIComponent(ENVVAL())}}&q=${{encodeURIComponent(q)}}&limit=200`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.ib_intgroupname || '';
    const descr = (r.descr || '').trim().slice(0, 60);
    const cnt = r.service_count || 0;
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520">
      <div style="font-weight:bold;color:#00ccdd;font-family:monospace;font-size:11px">${{esc(name)}}</div>
      <div style="display:flex;gap:8px;margin-top:2px;align-items:center">
        ${{cnt ? `<span style="font-size:10px;color:#445">${{cnt}} services</span>` : ''}}
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
  const url = `/api/peoplesoft/object/ib_service_group/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENVVAL())}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const svcSec = secs.find(s=>s.title?.includes('Services'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap;vertical-align:top">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  function itemList(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<div style="display:flex;flex-direction:column;gap:4px">` +
      sec.items.map(i=>{{
        const chips = (i.chips||[]).map(c=>`<span style="padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#1a1a2a;border:1px solid #334;color:#aac">${{esc(c.label||c)}}</span>`).join(' ');
        return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #0d1520">
          <span style="font-family:monospace;font-size:11px;color:#00ccdd">${{esc(i.name||'')}}</span>
          ${{chips}}
          ${{i.meta ? `<span style="font-size:10px;color:#445">${{esc(i.meta)}}</span>` : ''}}
        </div>`;
      }}).join('') + `</div>`;
  }}

  const ov = uom.overview || {{}};
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#00ccdd;font-size:14px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="font-size:12px;color:#556;margin-bottom:16px">${{esc(uom.display_name||'')}}</div>
    <div style="display:flex;gap:12px;margin-bottom:16px;font-size:12px;color:#778">
      <span>Services: <b style="color:#aac">${{ov.service_count||0}}</b></span>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>${{kvTable(ovSec)}}` : ''}}
    ${{svcSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(svcSec.title)}}</h3>${{itemList(svcSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")


@router.get("/ibrtng", response_class=HTMLResponse)
def admin_ibrtng(request: Request):
    nav = _nav_html("ibrtng", '<select class="ds-env-sel" id="globalEnv" style="background:transparent;color:#00e5ff;border:1px solid rgba(0,229,255,.3);border-radius:3px;font-size:11px;padding:2px 6px"></select>')
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>IB Routings</title>
<meta charset="utf-8">
<script src="/static/app.js?v=2"></script>
{_NAV_CSS}
</head><body class="ds-body">
{nav}
<div class="ds-main" style="display:grid;grid-template-columns:380px 1fr;gap:0;height:calc(100vh - 48px)">
<div style="border-right:1px solid #1a2a3a;overflow-y:auto;padding:12px 8px">
  <div style="margin-bottom:6px;display:flex;gap:6px">
    <input id="q" placeholder="Search name, operation, or node…" oninput="doSearch()"
      style="flex:1;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 10px;border-radius:4px;font-size:13px">
    <select id="rt" onchange="doSearch()"
      style="width:80px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 6px;border-radius:4px;font-size:12px">
      <option value="">All</option>
      <option value="S">Sync</option>
      <option value="A">Async</option>
      <option value="R">REST</option>
    </select>
    <select id="st" onchange="doSearch()"
      style="width:70px;background:#0a1520;border:1px solid #1a3a5a;color:#c8d8e8;padding:6px 6px;border-radius:4px;font-size:12px">
      <option value="">All</option>
      <option value="A">Active</option>
      <option value="I">Inactive</option>
    </select>
  </div>
  <div id="list" style="font-size:12px"></div>
</div>
<div id="detail" style="overflow-y:auto;padding:20px 28px;color:#c8d8e8">
  <div class="muted">Select an IB Routing to view its node connections and handlers.</div>
</div>
</div>
<script>
{_ESC_JS}
function ENVVAL() {{ return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HRDMO'); }}
let selected = null;

const TYPE_COLOR = {{S:'#44aaff', A:'#ffaa44', R:'#44ff88', X:'#778'}};
const TYPE_LABEL = {{S:'Sync', A:'Async', R:'REST', X:'Internal'}};

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  const rt = document.getElementById('rt').value;
  const st = document.getElementById('st').value;
  const url = `/api/peoplesoft/ib-routings?env=${{encodeURIComponent(ENVVAL())}}&q=${{encodeURIComponent(q)}}&rtng_type=${{encodeURIComponent(rt)}}&status=${{encodeURIComponent(st)}}&limit=300`;
  const data = await fetch(url).then(r=>r.json()).catch(()=>[]);
  const list = document.getElementById('list');
  if (!data.length) {{ list.innerHTML = '<div class="muted">No results.</div>'; return; }}
  list.innerHTML = data.map(r => {{
    const name = r.routingdefnname || '';
    const op = (r.ib_operationname || '').trim();
    const sender = (r.sendernodename || '').trim();
    const rcvr = (r.receivernodename || '').trim();
    const rt2 = r.rtngtype || '';
    const tc = TYPE_COLOR[rt2] || '#778';
    const tl = TYPE_LABEL[rt2] || rt2;
    const active = r.eff_status === 'A';
    return `<div class="list-item${{selected===name?' selected':''}}" onclick="loadDetail('${{esc(name)}}')"
      style="padding:6px 10px;border-radius:4px;cursor:pointer;margin-bottom:2px;border-bottom:1px solid #0d1520;${{active?'':'opacity:0.5'}}">
      <div style="font-weight:bold;color:#4488ff;font-family:monospace;font-size:10px">${{esc(name)}}</div>
      <div style="display:flex;gap:6px;margin-top:2px;align-items:center">
        <span style="font-size:10px;font-weight:bold;color:${{tc}}">${{esc(tl)}}</span>
        <span style="font-size:10px;color:#445">${{esc(op)}}</span>
      </div>
      <div style="font-size:10px;color:#334;font-family:monospace;margin-top:1px">${{esc(sender)}} → ${{esc(rcvr)}}</div>
    </div>`;
  }}).join('');
}}

async function loadDetail(name) {{
  selected = name;
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('selected', el.innerText.trim().startsWith(name)));
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading…</div>';
  const url = `/api/peoplesoft/object/ib_routing/${{encodeURIComponent(name)}}?env=${{encodeURIComponent(ENVVAL())}}`;
  const payload = await fetch(url).then(r=>r.json()).catch(e=>{{return {{error:String(e)}}}});
  if (payload.error) {{ detail.innerHTML = `<div style="color:#f66">${{esc(payload.error)}}</div>`; return; }}

  const uom = payload;
  const secs = uom.sections || [];
  const ovSec = secs.find(s=>s.title?.includes('Overview'));
  const aliasSec = secs.find(s=>s.title?.includes('Alias'));

  function kvTable(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">` +
      sec.items.map(i=>`<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap;vertical-align:top">${{esc(i.label)}}</td>
        <td style="padding:4px 0;color:#c8d8e8;font-family:monospace">${{esc(String(i.value||''))}}</td></tr>`).join('') +
      `</table>`;
  }}

  function itemList(sec) {{
    if (!sec || !sec.items?.length) return '';
    return `<div style="display:flex;flex-direction:column;gap:4px">` +
      sec.items.map(i=>{{
        const chips = (i.chips||[]).map(c=>`<span style="padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:#1a1a2a;border:1px solid #334;color:#aac">${{esc(c.label||c)}}</span>`).join(' ');
        return `<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #0d1520">
          <span style="font-family:monospace;font-size:11px;color:#c8d8e8">${{esc(i.name||'')}}</span>
          ${{chips}}
          ${{i.meta ? `<span style="font-size:10px;color:#445">${{esc(i.meta)}}</span>` : ''}}
        </div>`;
      }}).join('') + `</div>`;
  }}

  const ov = uom.overview || {{}};
  const statusColor = uom.status === 'active' ? '#44ee88' : '#ee8844';
  detail.innerHTML = `
    <h2 style="font-family:monospace;color:#4488ff;font-size:13px;margin:0 0 4px">${{esc(name)}}</h2>
    <div style="display:flex;gap:12px;margin-bottom:16px;font-size:12px;color:#778">
      <span>Type: <b style="color:#aac">${{esc(ov.routing_type||'')}}</b></span>
      <span style="color:${{statusColor}}">${{uom.status||''}}</span>
    </div>
    ${{uom.warnings?.length ? `<div style="color:#f90;font-size:11px;margin-bottom:12px">${{uom.warnings.map(w=>esc(w)).join('<br>')}}</div>` : ''}}
    ${{ovSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Routing Detail</h3>${{kvTable(ovSec)}}` : ''}}
    ${{aliasSec ? `<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">${{esc(aliasSec.title)}}</h3>${{itemList(aliasSec)}}` : ''}}
  `;
}}

doSearch();
</script>
</body></html>""")


@router.get("/iboper", response_class=HTMLResponse)
def admin_iboper():
    return _shell("IB Service Operations Explorer", "iboper", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#ffaa44;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #ffaa4433;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #ffaa4422;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:340px;min-width:240px;border-right:1px solid #ffaa4422;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#181008;color:#d7faff;border:1px solid #ffaa4444;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#ffaa44}
button{background:#cc8833;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(255,170,68,.07);border-left-color:#ffaa4455}
.item.sel{background:rgba(255,170,68,.12);border-left-color:#ffaa44}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.muted{color:#556;font-style:italic}
.badge-sync{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
            background:#001820;border:1px solid #0099cc55;color:#44bbdd;margin-left:5px}
.badge-async{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
             background:#182000;border:1px solid #88cc0055;color:#99dd44;margin-left:5px}
.badge-rest{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
            background:#180a00;border:1px solid #ff660055;color:#ff9944;margin-left:5px}
.badge-other{display:inline-block;padding:1px 5px;border-radius:2px;font-size:10px;font-family:monospace;
             background:#181818;border:1px solid #55555555;color:#778;margin-left:5px}
</style>
<div class="topbar">
  <input id="q" type="text" placeholder="Search operation name, service, or description..." style="width:310px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="rtype" onchange="doSearch()">
    <option value="">All Types</option>
    <option value="S">Synchronous</option>
    <option value="A">Asynchronous</option>
    <option value="R">REST</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>IB Operations</h2>
    <div id="list" class="muted">Search to load operations.</div>
  </div>
  <div class="content">
    <h2>Selected Operation</h2>
    <div id="detail" class="muted">Select an operation from the list.</div>
  </div>
</div>
<script>
const ENV = window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM');
let _rows = [];
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function rtypeBadge(rt, rm) {
  if (rt === 'S') return '<span class="badge-sync">Sync</span>';
  if (rt === 'A') return '<span class="badge-async">Async</span>';
  if (rt === 'R') return '<span class="badge-rest">REST</span>';
  const m = (rm || '').trim();
  if (m) return '<span class="badge-rest">' + esc(m) + '</span>';
  return rt ? '<span class="badge-other">' + esc(rt) + '</span>' : '';
}

async function doSearch() {
  const q = document.getElementById('q').value.trim();
  const rtype = document.getElementById('rtype').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading\u2026</div>';
  const params = new URLSearchParams({env: ENV, limit: 100});
  if (q) params.set('q', q);
  if (rtype) params.set('rtype', rtype);
  const d = await api('/api/peoplesoft/ib-operations?' + params);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  _rows = Array.isArray(d) ? d : (d.items || []);
  document.getElementById('stats').textContent = _rows.length + ' result' + (_rows.length !== 1 ? 's' : '');
  if (!_rows.length) { list.innerHTML = '<div class="muted">No operations found.</div>'; return; }
  list.innerHTML = _rows.map(function(r, i) {
    const svc = (r.ib_servicename || '').trim();
    const descr = (r.descr || '').trim();
    let meta = '';
    if (svc && svc !== r.ib_operationname) meta += esc(svc);
    if (descr && descr !== r.ib_operationname) meta += (meta ? ' \u00b7 ' : '') + esc(descr.slice(0,55));
    return '<div class="item" id="op-' + i + '" data-idx="' + i + '">' +
      '<div class="item-name">' + esc(r.ib_operationname) + rtypeBadge(r.rtngtype, r.ib_restmethod) + '</div>' +
      (meta ? '<div class="item-meta">' + meta + '</div>' : '') +
      '</div>';
  }).join('');
  list.querySelectorAll('.item').forEach(function(el) {
    el.addEventListener('click', function() { selectOp(+el.dataset.idx); });
  });
}

async function selectOp(idx) {
  const r = _rows[idx];
  if (!r) return;
  document.querySelectorAll('.item').forEach(function(el) { el.classList.remove('sel'); });
  const el = document.getElementById('op-' + idx);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading\u2026</div>';

  const d = await api('/api/peoplesoft/object/ib_operation/' + encodeURIComponent(r.ib_operationname) + '?env=' + ENV);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const sections = d.sections || [];
  const ovSec  = sections.find(function(s) { return s.title && s.title.indexOf('Overview') >= 0; });
  const rtnSec = sections.find(function(s) { return s.title && s.title.indexOf('Routing') >= 0; });

  function kvTable(sec) {
    if (!sec || !sec.items || !sec.items.length) return '';
    return '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:12px">' +
      sec.items.map(function(item) {
        return '<tr><td style="padding:4px 12px 4px 0;color:#778;white-space:nowrap">' + esc(item.label) + '</td>' +
          '<td style="padding:4px 0;color:#c8d8e8;font-family:monospace;word-break:break-word">' + esc(String(item.value||'')) + '</td></tr>';
      }).join('') + '</table>';
  }

  function routingList(sec) {
    if (!sec || !sec.items || !sec.items.length) {
      return '<div class="muted" style="font-size:12px">No routings defined.</div>';
    }
    return '<div style="margin-bottom:16px">' +
      sec.items.map(function(it) {
        const inactive = it.status === 'inactive';
        return '<div style="padding:5px 0;border-bottom:1px solid #181008;font-size:12px;display:flex;gap:10px;align-items:baseline">' +
          '<span style="font-family:monospace;min-width:220px;color:' + (inactive ? '#445' : '#ffaa44') + '">' + esc(it.label||it.id||'') + '</span>' +
          (inactive ? '<span style="font-size:10px;color:#445">(inactive)</span>' : '') +
          '<span style="color:#778;font-size:11px">' + esc(it.value||'') + '</span>' +
          '</div>';
      }).join('') + '</div>';
  }

  const ov = d.overview || {};
  let html = '<h2 style="font-family:monospace;color:#ffaa44;font-size:14px;margin:0 0 4px">' + esc(r.ib_operationname) + '</h2>' +
    '<div style="font-size:12px;color:#556;margin-bottom:16px">' +
    rtypeBadge(ov.rtng_type, ov.rest_method) +
    (ov.service && ov.service !== r.ib_operationname ? ' Service: <span style="color:#c8d8e8;font-family:monospace">' + esc(ov.service) + '</span>' : '') +
    '</div>';
  if (d.warnings && d.warnings.length) {
    html += '<div style="color:#f90;font-size:11px;margin-bottom:12px">' + d.warnings.map(esc).join('<br>') + '</div>';
  }
  if (ovSec)  html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:0 0 6px">Overview</h3>' + kvTable(ovSec);
  if (rtnSec) html += '<h3 style="font-size:11px;color:#556;text-transform:uppercase;margin:12px 0 6px">' + esc(rtnSec.title) + '</h3>' + routingList(rtnSec);
  detail.innerHTML = html;
}

doSearch();
</script>""")
