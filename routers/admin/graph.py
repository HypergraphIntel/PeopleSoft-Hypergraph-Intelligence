import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/graph", response_class=HTMLResponse)
def admin_graph():
    return _shell("Graph Explorer", "graphdb", content="""\
    <style>
        body {
            background: #050b12;
            color: #d7faff;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #00e5ff;
            text-shadow: 0 0 12px #00e5ff;
            letter-spacing: 4px;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.4);
            padding: 20px;
            margin-top: 20px;
            background: rgba(0, 20, 30, .75);
        }

        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        input, select {
            padding: 8px;
            background: #0b1b24;
            color: white;
            border: 1px solid #00e5ff;
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 14px;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
        }

        .graph {
            display: grid;
            grid-template-columns: minmax(260px, 1fr) minmax(260px, 1fr);
            gap: 16px;
        }

        .node, .edge {
            border: 1px solid #1e5b66;
            padding: 10px;
            margin: 8px 0;
            background: rgba(5, 18, 28, .85);
        }

        .node {
            cursor: pointer;
        }

        .node:hover {
            border-color: #00e5ff;
            box-shadow: 0 0 10px rgba(0,229,255,.3);
        }

        .title {
            color: #00e5ff;
            font-weight: bold;
        }

        .detail {
            display: block;
            color: #b8dce2;
            font-size: 12px;
            margin-top: 4px;
        }

        .muted {
            color: #7faab2;
        }

        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: #b8dce2;
        }

        @media (max-width: 800px) {
            body {
                padding: 20px;
            }

            .graph {
                grid-template-columns: 1fr;
            }
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-top: 16px;
        }

        .tab-btn {
            background: #0b1b24;
            border: 1px solid #1e5b66;
            color: #7faab2;
            padding: 6px 18px;
            cursor: pointer;
            letter-spacing: 1px;
            font-size: 12px;
        }

        .tab-btn.active {
            background: #00e5ff;
            border-color: #00e5ff;
            color: #050b12;
            font-weight: bold;
        }

        #kgLegend {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
            font-size: 11px;
        }

        #kgDetail {
            margin-top: 10px;
            padding: 10px;
            border: 1px solid #1e3040;
            background: #030d14;
            font-size: 12px;
            min-height: 36px;
        }
</style>
    <div class="card">
        <div class="toolbar">
            <select id="objectType">
                <option value="operator">Operator</option>
                <option value="role">Role</option>
                <option value="permissionlist">Permission List</option>
                <option value="component">Component</option>
                <option value="page">Page</option>
                <option value="record">Record</option>
                <option value="field">Field</option>
                <option value="portal_registry">Portal Registry</option>
                <option value="application_engine">Application Engine</option>
                <option value="peoplecode">PeopleCode</option>
                <option value="service_operation">IB Service</option>
                <option value="node">IB Node</option>
                <option value="queue">IB Queue</option>
                <option value="routing">IB Routing</option>
                <option value="sql_definition">SQL Definition</option>
                <option value="query">PS Query</option>
                <option value="tree">Tree</option>
                <option value="ci">Component Interface</option>
                <option value="application_package">App Package</option>
                <option value="eocc_config">Page Field Config</option>
            </select>
            <input id="objectName" placeholder="Object name">
            <button onclick="loadGraph()">Explore</button>
        </div>
        <div id="status" class="muted">Enter an object and explore its relationships.</div>
    </div>

    <div class="tabs">
        <button class="tab-btn active" id="tabList" onclick="showTab('list')">LIST</button>
        <button class="tab-btn" id="tabVisual" onclick="showTab('visual')">VISUAL</button>
        <button class="tab-btn" id="tabImpact" onclick="showTab('impact')">IMPACT</button>
        <button class="tab-btn" id="tabDrift" onclick="showTab('drift')">DRIFT</button>
    </div>

    <div id="listView">
        <div class="graph">
            <div class="card">
                <h2>Nodes</h2>
                <div id="nodes" class="muted">No graph loaded.</div>
            </div>

            <div class="card">
                <h2>Edges</h2>
                <div id="edges" class="muted">No graph loaded.</div>
            </div>
        </div>

        <div class="card">
            <h2>Selected Node</h2>
            <pre id="details">Select a node.</pre>
        </div>
    </div>

    <div id="visualView" style="display:none">
        <div class="card" style="padding:12px">
            <svg id="kgSvg" width="100%" height="580" style="display:block;background:#030d14;border:1px solid #1e3040"></svg>
            <div id="kgLegend"></div>
            <div id="kgDetail" class="muted">Load a graph then switch to Visual to explore.</div>
        </div>
    </div>

    <div id="impactView" style="display:none">
        <div class="card">
            <h2>Impact Analysis</h2>
            <p class="muted" style="margin:0 0 12px">Analyse what a node depends on (downstream) and what depends on it (upstream impact).</p>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <select id="impactNodeType" style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px">
                    <option value="">-- type --</option>
                    <option value="operator">operator</option>
                    <option value="role">role</option>
                    <option value="permissionlist">permissionlist</option>
                    <option value="component">component</option>
                    <option value="page">page</option>
                    <option value="record">record</option>
                    <option value="field">field</option>
                    <option value="peoplecode">peoplecode</option>
                    <option value="application_engine">application_engine</option>
                    <option value="menu">menu</option>
                    <option value="tree">tree</option>
                    <option value="sql_definition">sql_definition</option>
                    <option value="query">query</option>
                    <option value="ci">ci</option>
                </select>
                <input id="impactNodeName" type="text" placeholder="Object name..." style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px;width:260px">
                <select id="impactDepth" style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px">
                    <option value="1">depth 1</option>
                    <option value="2">depth 2</option>
                    <option value="3" selected>depth 3</option>
                    <option value="4">depth 4</option>
                    <option value="5">depth 5</option>
                </select>
                <button onclick="runImpact()" style="background:#00e5ff;color:#000;border:none;padding:8px 18px;cursor:pointer;font-size:12px;font-weight:bold">Analyse</button>
            </div>
            <div id="impactStatus" class="muted" style="margin-top:8px"></div>
        </div>

        <div class="graph" id="impactPanels" style="display:none">
            <div class="card">
                <h2>Upstream (Impact)</h2>
                <p class="muted" style="margin:0 0 8px;font-size:11px">Objects that depend on this node — changes here ripple upward.</p>
                <div id="impactSummaryReverse" style="margin-bottom:10px"></div>
                <div id="impactReverse"></div>
            </div>
            <div class="card">
                <h2>Downstream (Dependencies)</h2>
                <p class="muted" style="margin:0 0 8px;font-size:11px">Objects this node depends on — what breaks if they change.</p>
                <div id="impactSummaryForward" style="margin-bottom:10px"></div>
                <div id="impactForward"></div>
            </div>
        </div>
    </div>

    <div id="driftView" style="display:none">
        <div class="card">
            <h2>Configuration Drift</h2>
            <p class="muted" style="margin:0 0 12px">Compare the current live graph against the most recent snapshot to detect what was added, removed, or changed.</p>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <label style="font-size:12px;color:#aac">Environment:</label>
                <select id="driftEnv" style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px">
                    <option value="HCM">HCM</option>
                    <option value="FSCM">FSCM</option>
                </select>
                <label style="font-size:12px;color:#aac">Filter type:</label>
                <input id="driftTypes" type="text" placeholder="record,component,... (blank=all)"
                    style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px;width:220px">
                <button onclick="runDrift()" style="background:#00e5ff;color:#000;border:none;padding:8px 18px;cursor:pointer;font-size:12px;font-weight:bold">Check Drift</button>
            </div>
            <div id="driftStatus" class="muted" style="margin-top:8px"></div>
        </div>

        <div id="driftResults" style="display:none">
            <div class="graph">
                <div class="card">
                    <h2>Summary</h2>
                    <div id="driftSummary"></div>
                </div>
                <div class="card">
                    <h2>Baseline</h2>
                    <div id="driftBaseline" class="muted"></div>
                </div>
            </div>

            <div class="graph">
                <div class="card">
                    <h2 style="color:#44cc66">New Objects <span id="driftNewCount" style="font-size:10px;color:#44cc66;margin-left:6px"></span></h2>
                    <p class="muted" style="margin:0 0 8px;font-size:11px">Objects present in the current graph but not in the baseline snapshot.</p>
                    <div id="driftNew"></div>
                </div>
                <div class="card">
                    <h2 style="color:#ff6666">Removed Objects <span id="driftRemovedCount" style="font-size:10px;color:#ff6666;margin-left:6px"></span></h2>
                    <p class="muted" style="margin:0 0 8px;font-size:11px">Objects in the baseline snapshot that are no longer in the current graph.</p>
                    <div id="driftRemoved"></div>
                </div>
            </div>

            <div class="card">
                <h2 style="color:#ffaa00">Changed Objects <span id="driftChangedCount" style="font-size:10px;color:#ffaa00;margin-left:6px"></span></h2>
                <p class="muted" style="margin:0 0 8px;font-size:11px">Objects present in both but with metadata changes (display name, etc.).</p>
                <div id="driftChanged"></div>
            </div>
        </div>
    </div>

<script>
const ENV = 'HCM';

async function api(path) {
    const res = await fetch(path);

    if (res.status === 401) {
        window.location.reload();
        return;
    }

    if (!res.ok) {
        const msg = await res.text();
        setStatus(msg);
        throw new Error(msg);
    }

    return res.json();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function setObject(type, name) {
    document.getElementById('objectType').value = type;
    document.getElementById('objectName').value = name;
    loadGraph();
}

function objectUrl(type, name) {
    return `/admin/object/${encodeURIComponent(type)}/${encodeURIComponent(name)}`;
}

function nodeTitle(node) {
    return `${node.type}: ${node.name}`;
}

function renderGraph(graph) {
    const nodes = document.getElementById('nodes');
    const edges = document.getElementById('edges');
    nodes.className = '';
    edges.className = '';
    nodes.innerHTML = '';
    edges.innerHTML = '';

    if (!graph.nodes.length) {
        nodes.className = 'muted';
        nodes.textContent = 'No nodes returned.';
    }

    graph.nodes.forEach(node => {
        const div = document.createElement('div');
        div.className = 'node';
        div.onclick = () => {
            document.getElementById('details').textContent = JSON.stringify(node, null, 2);
            const typeEl = document.getElementById('impactNodeType');
            const nameEl = document.getElementById('impactNodeName');
            if (typeEl && nameEl) { typeEl.value = node.type || ''; nameEl.value = node.name || ''; }
            window.location.href = objectUrl(node.type, node.name);
        };

        const title = document.createElement('span');
        title.className = 'title';
        title.textContent = nodeTitle(node);
        div.appendChild(title);

        const detail = document.createElement('span');
        detail.className = 'detail';
        detail.textContent = Object.keys(node.data || {}).slice(0, 5).map(k => `${k}=${node.data[k]}`).join(' | ');
        div.appendChild(detail);

        nodes.appendChild(div);
    });

    if (!graph.edges.length) {
        edges.className = 'muted';
        edges.textContent = 'No edges returned.';
    }

    graph.edges.forEach(edge => {
        const div = document.createElement('div');
        div.className = 'edge';
        div.innerHTML = `
            <span class="title">${edge.relationship}</span>
            <span class="detail">${edge.source} -> ${edge.target}</span>
        `;
        edges.appendChild(div);
    });

    kgRenderForce(graph);
}

async function loadGraph() {
    const type = document.getElementById('objectType').value;
    const name = document.getElementById('objectName').value.trim();
    const normalizedType = type;

    if (!name) {
        setStatus('Enter an object name.');
        return;
    }

    try {
        setStatus(`Loading ${normalizedType}:${name}...`);
        const graph = await api(`/api/peoplesoft/graph/${encodeURIComponent(normalizedType)}/${encodeURIComponent(name)}?env=${ENV}`);
        renderGraph(graph);
        setStatus(`Loaded ${graph.nodes.length} nodes and ${graph.edges.length} edges.`);
    } catch (err) {
        setStatus(`Graph load failed: ${err.message || err}`);
    }
}

document.getElementById('objectName').addEventListener('keydown', event => {
    if (event.key === 'Enter') {
        loadGraph();
    }
});

// ── Knowledge Graph Force Visualization ─────────────────
const KG_COLORS = {
  operator:'#4488ff', role:'#00cc66', permissionlist:'#ff8800',
  component:'#00e5ff', page:'#44ffcc', record:'#ffdd00', field:'#ff88ff',
  portal_registry:'#aa44ff', application_engine:'#ff4488', peoplecode:'#ff6644',
  service_operation:'#88ccff', node:'#ff88aa', queue:'#88ff44',
  routing:'#cc88ff', process:'#55ff88', process_server:'#ffaa44',
};
function kgColor(t) { return KG_COLORS[t] || '#556677'; }

function kgForce(nodes, edges, w, h, ticks) {
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

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _kgNodes = [], _kgEdges = [], _kgFocalId = '';

function kgDrawSvg() {
  const svg = document.getElementById('kgSvg');
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';
  const w = svg.clientWidth || 900, h = parseInt(svg.getAttribute('height')) || 580;
  for (const e of _kgEdges) {
    const s = _kgNodes[e.si], t = _kgNodes[e.ti]; if (!s||!t) continue;
    const line = document.createElementNS(ns,'line');
    line.setAttribute('x1',s.x); line.setAttribute('y1',s.y);
    line.setAttribute('x2',t.x); line.setAttribute('y2',t.y);
    line.setAttribute('stroke','#1e3040'); line.setAttribute('stroke-width','1');
    svg.appendChild(line);
    if (e.rel) {
      const tx = document.createElementNS(ns,'text');
      tx.setAttribute('x',(s.x+t.x)/2); tx.setAttribute('y',(s.y+t.y)/2-2);
      tx.setAttribute('fill','#2a4050'); tx.setAttribute('font-size','7');
      tx.setAttribute('text-anchor','middle'); tx.textContent = e.rel;
      svg.appendChild(tx);
    }
  }
  for (const n of _kgNodes) {
    const g = document.createElementNS(ns,'g');
    g.style.cursor = 'pointer';
    g.onclick = () => kgShowDetail(n);
    const focal = n.id === _kgFocalId;
    const r = focal ? 16 : 9;
    const c = document.createElementNS(ns,'circle');
    c.setAttribute('cx',n.x); c.setAttribute('cy',n.y); c.setAttribute('r',r);
    c.setAttribute('fill',kgColor(n.type));
    c.setAttribute('fill-opacity', focal ? '0.5' : '0.22');
    c.setAttribute('stroke',kgColor(n.type));
    c.setAttribute('stroke-width', focal ? '2.5' : '1.5');
    g.appendChild(c);
    const lbl = (n.label || n.name || n.id || '');
    const tx = document.createElementNS(ns,'text');
    tx.setAttribute('x',n.x); tx.setAttribute('y',n.y+r+11);
    tx.setAttribute('fill',kgColor(n.type)); tx.setAttribute('font-size','9');
    tx.setAttribute('text-anchor','middle');
    tx.textContent = lbl.length>20 ? lbl.slice(0,18)+'…' : lbl;
    g.appendChild(tx);
    svg.appendChild(g);
  }
}

function kgShowDetail(n) {
  const el = document.getElementById('kgDetail');
  const lbl = n.label || n.name || n.id || '';
  const href = objectUrl(n.type, n.name || n.id);
  el.className = '';
  el.innerHTML = `<b style="color:${kgColor(n.type)}">[${n.type}]</b> `+
    `<b style="color:#d7faff">${escHtml(lbl)}</b>`+
    ` <a href="${escHtml(href)}" style="color:#00e5ff;font-size:10px;margin-left:6px;">&#x2197; explore</a>`+
    '<br>'+Object.entries(n.data||{}).slice(0,12)
      .map(([k,v])=>`<span style="color:#445566">${escHtml(k)}:</span> <span style="color:#9ab">${escHtml(String(v??''))}</span>`)
      .join(' &nbsp; ');
}

function kgRenderForce(graph) {
  const svg = document.getElementById('kgSvg');
  const w = svg.clientWidth || 900, h = parseInt(svg.getAttribute('height')) || 580;
  const nodeMap = {};
  _kgFocalId = ((graph.nodes||[])[0]||{}).id || '';
  _kgNodes = (graph.nodes||[]).map((n,i) => {
    nodeMap[n.id] = i;
    return {...n, x:24+Math.random()*(w-48), y:24+Math.random()*(h-48), fx:0, fy:0};
  });
  _kgEdges = (graph.edges||[]).map(e=>({
    si:nodeMap[e.source], ti:nodeMap[e.target], rel:e.relationship||''
  })).filter(e=>e.si!==undefined&&e.ti!==undefined);
  kgForce(_kgNodes, _kgEdges, w, h, 400);
  if (_activeTab === 'visual') kgDrawSvg();
  const types = [...new Set(_kgNodes.map(n=>n.type))].sort();
  document.getElementById('kgLegend').innerHTML = types.map(t =>
    `<span style="color:${kgColor(t)};background:#0a1820;border:1px solid ${kgColor(t)}44;padding:2px 8px;border-radius:2px;">`+
    `${t} <b>${_kgNodes.filter(n=>n.type===t).length}</b></span>`
  ).join('');
  document.getElementById('kgDetail').className = 'muted';
  document.getElementById('kgDetail').textContent = 'Click a node to see details.';
}

let _activeTab = 'list';
function showTab(name) {
  _activeTab = name;
  document.getElementById('listView').style.display    = name==='list'   ? '' : 'none';
  document.getElementById('visualView').style.display  = name==='visual' ? '' : 'none';
  document.getElementById('impactView').style.display  = name==='impact' ? '' : 'none';
  document.getElementById('driftView').style.display   = name==='drift'  ? '' : 'none';
  document.getElementById('tabList').classList.toggle('active',   name==='list');
  document.getElementById('tabVisual').classList.toggle('active', name==='visual');
  document.getElementById('tabImpact').classList.toggle('active', name==='impact');
  document.getElementById('tabDrift').classList.toggle('active',  name==='drift');
  if (name==='visual' && _kgNodes.length) kgDrawSvg();
}

async function runDrift() {
  const driftEnv   = document.getElementById('driftEnv').value;
  const driftTypes = document.getElementById('driftTypes').value.trim();
  const status     = document.getElementById('driftStatus');
  document.getElementById('driftResults').style.display = 'none';
  status.textContent = 'Loading drift report…';

  const params = new URLSearchParams({env: driftEnv, limit: 500});
  if (driftTypes) params.set('node_types', driftTypes);

  let d;
  try { d = await api(`/api/graph/drift?${params}`); }
  catch(e) { status.textContent = `Error: ${e.message}`; return; }

  if (d.error) {
    status.textContent = d.message || d.error;
    return;
  }

  const ds = d.drift_summary || {};
  status.textContent = '';

  // Summary chips
  const chipHtml = (n, label, color) =>
    `<span style="display:inline-block;padding:4px 12px;border:1px solid ${color}44;background:#030d14;color:${color};font-size:12px;margin:2px;font-weight:bold">${n} ${label}</span>`;
  document.getElementById('driftSummary').innerHTML =
    chipHtml(ds.new_count||0,     'new',     '#44cc66') +
    chipHtml(ds.removed_count||0, 'removed', '#ff6666') +
    chipHtml(ds.changed_count||0, 'changed', '#ffaa00');

  // Baseline info
  const bl = d.baseline_snapshot || {};
  document.getElementById('driftBaseline').innerHTML =
    `<span style="font-size:11px;color:#aac">ID:</span> <code style="font-size:11px">${escHtml(bl.id||'?')}</code><br>` +
    `<span style="font-size:11px;color:#aac">Created:</span> <span style="font-size:11px">${escHtml((bl.created_at||'?').replace('T',' ').slice(0,19))}</span>` +
    (bl.note ? `<br><span style="font-size:11px;color:#aac">Note:</span> <span style="font-size:11px">${escHtml(bl.note)}</span>` : '');

  // New nodes
  document.getElementById('driftNewCount').textContent = `(${ds.new_count||0})`;
  renderDriftNodes(d.only_in_env2_nodes || [], 'driftNew', '#44cc66');

  // Removed nodes
  document.getElementById('driftRemovedCount').textContent = `(${ds.removed_count||0})`;
  renderDriftNodes(d.only_in_env1_nodes || [], 'driftRemoved', '#ff6666');

  // Changed nodes
  document.getElementById('driftChangedCount').textContent = `(${ds.changed_count||0})`;
  renderDriftChanged(d.changed_nodes || [], 'driftChanged');

  document.getElementById('driftResults').style.display = '';
}

function renderDriftNodes(nodes, containerId, color) {
  const el = document.getElementById(containerId);
  if (!nodes.length) { el.innerHTML = '<span class="muted">None.</span>'; return; }
  const byType = {};
  nodes.forEach(n => { const t = n.type||'?'; byType[t] = byType[t]||[]; byType[t].push(n); });
  el.innerHTML = Object.keys(byType).sort().map(t => {
    const items = byType[t].map(n => {
      const href = objectUrl(n.type, n.name || n.id.split(':').slice(1).join(':'));
      const label = escHtml(n.display_name || n.name || n.id);
      return href
        ? `<a href="${href}" target="_blank" style="color:${color};font-size:11px;display:block;padding:1px 0;font-family:monospace">${label}</a>`
        : `<span style="color:${color};font-size:11px;display:block;padding:1px 0;font-family:monospace">${label}</span>`;
    }).join('');
    return `<div style="margin-bottom:10px">
      <div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#556;border-bottom:1px solid #1e3040;padding-bottom:3px;margin-bottom:4px">${escHtml(t)} (${byType[t].length})</div>
      ${items}
    </div>`;
  }).join('');
}

function renderDriftChanged(nodes, containerId) {
  const el = document.getElementById(containerId);
  if (!nodes.length) { el.innerHTML = '<span class="muted">None.</span>'; return; }
  el.innerHTML = nodes.slice(0, 200).map(item => {
    const n = item.env2 || item.env1 || {};
    const href = objectUrl(n.type, n.name || (item.id||'').split(':').slice(1).join(':'));
    const label = escHtml(n.display_name || n.name || item.id || '');
    const typeLabel = escHtml(n.type || '?');
    const diffs = (item.diffs || []).map(d =>
      `<span style="font-size:10px;color:#aac">${escHtml(d.field)}: </span>` +
      `<span style="font-size:10px;color:#ff8888;text-decoration:line-through">${escHtml(String(d.env1||''))}</span> → ` +
      `<span style="font-size:10px;color:#88ff88">${escHtml(String(d.env2||''))}</span>`
    ).join('<br>');
    const nameHtml = href
      ? `<a href="${href}" target="_blank" style="color:#ffaa00;font-family:monospace;font-size:12px">${label}</a>`
      : `<span style="color:#ffaa00;font-family:monospace;font-size:12px">${label}</span>`;
    return `<div style="padding:6px 0;border-bottom:1px solid #0d1a22">
      <span style="font-size:10px;color:#556;margin-right:6px">${typeLabel}</span>${nameHtml}
      <div style="margin-top:3px;padding-left:8px">${diffs}</div>
    </div>`;
  }).join('');
}

function renderImpactNodes(nodes, containerId) {
  const el = document.getElementById(containerId);
  if (!nodes || !nodes.length) { el.innerHTML = '<span class="muted">None found.</span>'; return; }
  const byType = {};
  nodes.forEach(n => { byType[n.type] = byType[n.type] || []; byType[n.type].push(n); });
  el.innerHTML = Object.keys(byType).sort().map(t => {
    const items = byType[t].map(n => {
      const href = objectUrl(n.type, n.name || n.id);
      const label = escHtml(n.display_name || n.name || n.id);
      return `<a href="${escHtml(href)}" style="display:inline-block;margin:2px 3px;padding:3px 7px;border-radius:2px;font-size:11px;border:1px solid #1e3040;background:#0a1820;color:#cdd6f4;text-decoration:none" onmouseenter="this.style.borderColor='#00e5ff'" onmouseleave="this.style.borderColor='#1e3040'">${label}</a>`;
    }).join('');
    return `<div style="margin-bottom:8px"><span style="color:#89b4fa;font-size:10px;display:block;margin-bottom:3px">[${escHtml(t.toUpperCase())}]</span>${items}</div>`;
  }).join('');
}

function renderImpactSummary(byType, containerId) {
  const el = document.getElementById(containerId);
  if (!byType || !Object.keys(byType).length) { el.innerHTML = ''; return; }
  el.innerHTML = Object.entries(byType).map(([t,c]) =>
    `<span style="background:#0a1820;border:1px solid #1e304044;padding:2px 7px;border-radius:2px;font-size:11px;margin:2px 3px;display:inline-block"><span style="color:#89b4fa">${escHtml(t)}</span> <b style="color:#d7faff">${c}</b></span>`
  ).join('');
}

async function runImpact() {
  const type = document.getElementById('impactNodeType').value;
  const name = document.getElementById('impactNodeName').value.trim().toUpperCase();
  const depth = document.getElementById('impactDepth').value;
  const status = document.getElementById('impactStatus');
  if (!type || !name) { status.textContent = 'Enter a node type and name.'; return; }

  const nodeId = `${type}:${name}`;
  status.textContent = 'Analysing...';
  document.getElementById('impactPanels').style.display = 'none';

  const data = await api(`/api/graph/impact/${encodeURIComponent(nodeId)}?env=${ENV}&depth=${depth}`);
  if (!data || !data.found) { status.textContent = `Node not found in graph: ${nodeId}. Build or rebuild the graph first.`; return; }

  status.textContent = `Found: [${type}] ${name} — ${data.summary.total_upstream} upstream, ${data.summary.total_downstream} downstream`;
  document.getElementById('impactPanels').style.display = '';

  renderImpactSummary(data.summary.reverse_by_type, 'impactSummaryReverse');
  renderImpactSummary(data.summary.forward_by_type, 'impactSummaryForward');
  renderImpactNodes(data.reverse_deps.nodes, 'impactReverse');
  renderImpactNodes(data.forward_deps.nodes, 'impactForward');
}
</script>""")


def object_explorer_page(object_type="", object_name=""):
    html = _shell("Object Explorer", "objects", content="""\
<style>
        body {
            background: #050b12;
            color: #d7faff;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #00e5ff;
            text-shadow: 0 0 12px #00e5ff;
            letter-spacing: 4px;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.4);
            padding: 20px;
            margin-top: 20px;
            background: rgba(0, 20, 30, .75);
        }

        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        .layout {
            display: grid;
            grid-template-columns: minmax(280px, 360px) 1fr;
            gap: 18px;
            align-items: start;
        }

        .object-shell {
            display: grid;
            grid-template-columns: minmax(190px, 240px) 1fr;
            gap: 16px;
            align-items: start;
        }

        .object-rail {
            position: sticky;
            top: 82px;
            border: 1px solid rgba(0,229,255,.24);
            background: rgba(0, 14, 22, .88);
            box-shadow: 0 0 10px rgba(0,229,255,.12);
            padding: 12px;
            margin-top: 16px;
        }

        .object-rail-title {
            color: #00e5ff;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin: 0 0 10px;
        }

        .object-rail-summary {
            display: grid;
            gap: 6px;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(0,229,255,.14);
        }

        .summary-pill {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            padding: 6px 8px;
            border: 1px solid rgba(0,229,255,.16);
            background: rgba(0,229,255,.04);
            color: #7faab2;
            font-size: 11px;
        }

        .summary-pill strong {
            color: #d7faff;
        }

        .section-nav {
            display: grid;
            gap: 5px;
        }

        .section-link {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            padding: 6px 8px;
            border-left: 2px solid rgba(0,229,255,.22);
            color: #7faab2;
            font-size: 12px;
            text-decoration: none;
            background: rgba(0,229,255,.025);
        }

        .section-link:hover {
            border-left-color: #00e5ff;
            background: rgba(0,229,255,.08);
            text-decoration: none;
        }

        .section-link.warn {
            border-left-color: #ffaa00;
            color: #ffaa00;
        }

        .section-link.graph {
            border-left-color: #aa66ff;
            color: #cba6ff;
        }

        .section-link.security {
            border-left-color: #ff5577;
            color: #ff9aaa;
        }

        .section-link.empty {
            opacity: .55;
        }

        .section-count {
            flex-shrink: 0;
            min-width: 18px;
            text-align: center;
            padding: 1px 6px;
            border: 1px solid rgba(0,229,255,.16);
            border-radius: 10px;
            color: #7faab2;
            font-size: 10px;
        }

        .sections {
            display: grid;
            grid-template-columns: repeat(2, minmax(260px, 1fr));
            gap: 16px;
        }

        input, select {
            padding: 8px;
            background: #0b1b24;
            color: white;
            border: 1px solid #00e5ff;
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 14px;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
        }

        .result, .row {
            border: 1px solid #1e5b66;
            padding: 10px;
            margin: 8px 0;
            background: rgba(5, 18, 28, .85);
        }

        .result, .clickable {
            cursor: pointer;
        }

        .result:hover, .clickable:hover {
            border-color: #00e5ff;
            box-shadow: 0 0 10px rgba(0,229,255,.3);
        }

        .title {
            color: #00e5ff;
            font-weight: bold;
        }

        .detail {
            display: block;
            color: #b8dce2;
            font-size: 12px;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }

        .muted {
            color: #7faab2;
        }

        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: #b8dce2;
        }

        dl {
            display: grid;
            grid-template-columns: minmax(120px, 180px) 1fr;
            gap: 8px 12px;
        }

        dt {
            color: #7faab2;
        }

        dd {
            margin: 0;
            overflow-wrap: anywhere;
        }

        /* ── Object header ──────────────────────────────────────────── */
        .obj-hdr {
            border: 1px solid rgba(0,229,255,.4);
            background: rgba(0,20,35,.95);
            padding: 14px 18px 12px;
            margin-top: 20px;
            box-shadow: 0 0 20px rgba(0,229,255,.12);
        }
        .obj-hdr-row { display:flex; align-items:center; gap:8px; margin-bottom:3px; }
        .obj-hdr-name { font-family:monospace; font-size:17px; font-weight:bold; color:#d7faff; letter-spacing:.5px; }
        .obj-type-chip { font-size:9px; font-weight:bold; padding:2px 6px; border-radius:2px; white-space:nowrap; flex-shrink:0; }
        .obj-hdr-desc { color:#7faab2; font-size:12px; margin:2px 0 6px; }
        .obj-hdr-actions { display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; padding-top:8px; border-top:1px solid rgba(0,229,255,.1); }
        .obj-hdr-actions a {
            font-size:11px; padding:3px 10px;
            border:1px solid rgba(0,229,255,.3); border-radius:3px;
            color:#00e5ff; white-space:nowrap; text-decoration:none;
        }
        .obj-hdr-actions a:hover { background:rgba(0,229,255,.1); }

        /* ── Section improvements ────────────────────────────────────── */
        .count-badge {
            font-size:9px; font-weight:bold; padding:1px 6px; border-radius:10px;
            background:rgba(0,229,255,.08); border:1px solid rgba(0,229,255,.2);
            color:#7faab2; margin-left:7px; vertical-align:middle;
        }
        .section-wide { grid-column: 1 / -1; }
        .section-warn { border-color:#ffaa00 !important; box-shadow:0 0 8px rgba(255,170,0,.15) !important; }
        .section-warn h2 { color:#ffaa00 !important; }
        .section-graph { border-color:#aa66ff66 !important; box-shadow:0 0 8px rgba(170,102,255,.12) !important; }
        .section-graph h2 { color:#cba6ff !important; }
        .section-security { border-color:#ff557766 !important; box-shadow:0 0 8px rgba(255,85,119,.12) !important; }
        .section-security h2 { color:#ff9aaa !important; }
        .section-empty { opacity:.76; }
        .section-summary {
            display:flex;
            flex-wrap:wrap;
            gap:6px;
            margin:0 0 10px;
        }
        .section-summary span {
            font-size:10px;
            color:#7faab2;
            border:1px solid rgba(0,229,255,.14);
            background:rgba(0,229,255,.035);
            padding:2px 7px;
            border-radius:10px;
        }
        .section-meta { font-size:10px; color:#446; margin-top:4px; }

        /* ── Row improvements ────────────────────────────────────────── */
        .row { display:flex; flex-direction:column; position:relative; padding-right:20px; }
        .row-header { display:flex; align-items:baseline; gap:6px; flex-wrap:nowrap; overflow:hidden; }
        .rel-chip {
            font-size:9px; font-weight:bold; padding:1px 5px; border-radius:2px;
            background:rgba(0,229,255,.07); border:1px solid rgba(0,229,255,.2);
            color:#7faab2; white-space:nowrap; flex-shrink:0;
        }
        .row-arrow {
            position:absolute; right:8px; top:8px;
            color:rgba(0,229,255,.35); font-size:11px; pointer-events:none;
        }

        @media (max-width: 1000px) {
            .layout, .object-shell, .sections {
                grid-template-columns: 1fr;
            }
            .object-rail {
                position: static;
            }
        }
</style>
    <div class="card">
        <div class="toolbar">
            <input id="globalSearch" placeholder="Search PeopleSoft objects">
            <button onclick="globalSearch()">Search</button>
            <select id="objectType">
                <option value="operator">Operator</option>
                <option value="role">Role</option>
                <option value="permissionlist">Permission List</option>
                <option value="component">Component</option>
                <option value="page">Page</option>
                <option value="record">Record</option>
                <option value="field">Field</option>
                <option value="portal_registry">Portal Registry</option>
                <option value="application_engine">Application Engine</option>
                <option value="peoplecode">PeopleCode</option>
                <option value="service_operation">IB Service</option>
                <option value="node">IB Node</option>
                <option value="queue">IB Queue</option>
                <option value="routing">IB Routing</option>
                <option value="sql_definition">SQL Definition</option>
                <option value="query">PS Query</option>
                <option value="tree">Tree</option>
                <option value="ci">Component Interface</option>
                <option value="application_package">App Package</option>
                <option value="eocc_config">Page Field Config</option>
            </select>
            <input id="objectName" placeholder="Object name">
            <button onclick="openTypedObject()">Open</button>
            <select id="sqlTypeFilter" style="display:none;background:#0b1b24;color:white;border:1px solid #00e5ff;padding:8px">
                <option value="">All SQL types</option>
                <option value="0">Standalone SQL (0)</option>
                <option value="1">AE SQL Action (1)</option>
                <option value="2">AE PeopleCode SQL (2)</option>
                <option value="6">Trigger (6)</option>
            </select>
            <button id="sqlSearchBtn" onclick="searchSqlDefinitions()" style="display:none">Search SQL</button>
        </div>
        <div id="status" class="muted">Search for an object or open a known type/name.</div>
    </div>

    <div class="layout">
        <div>
            <div class="card">
                <h2>Search Results</h2>
                <div id="results" class="muted">No search run.</div>
            </div>

            <div class="card">
                <h2 style="display:flex;justify-content:space-between;align-items:center;">
                  Recently Viewed
                  <button onclick="clearRecent()" style="font-size:10px;padding:2px 8px;background:transparent;border:1px solid #00e5ff33;color:#445;cursor:pointer;">Clear</button>
                </h2>
                <div id="recentList" class="muted">No objects viewed yet.</div>
            </div>

        </div>

        <div>
            <div class="obj-hdr" id="objectHeader">
                <nav id="breadcrumb" style="font-size:11px;color:#446;margin-bottom:8px;display:none"></nav>
                <div class="obj-hdr-row">
                    <span id="objectTypeChip" class="obj-type-chip" style="display:none"></span>
                    <span id="objectTitle" class="obj-hdr-name">Object Explorer</span>
                </div>
                <div id="objectDesc" class="obj-hdr-desc" style="display:none"></div>
                <div id="overview" style="margin:8px 0 4px"></div>
                <div id="actions" class="obj-hdr-actions" style="display:none"></div>
                <div id="objectMeta" class="muted" style="font-size:11px;margin-top:6px">Load an object to view canonical sections.</div>
            </div>

            <div class="object-shell">
                <aside id="sectionRail" class="object-rail" style="display:none"></aside>
                <div id="sections" class="sections"></div>
            </div>
        </div>
    </div>

<script>
__ESC_JS__
const ENV = 'HCM';
const INITIAL_TYPE = __OBJECT_TYPE__;
const INITIAL_NAME = __OBJECT_NAME__;

async function api(path) {
    const res = await fetch(path);

    if (res.status === 401) {
        window.location.reload();
        return;
    }

    if (!res.ok) {
        const msg = await res.text();
        setStatus(msg);
        throw new Error(msg);
    }

    return res.json();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function objectUrl(type, name) {
    if (type === 'operator')          return `/admin/operator/${encodeURIComponent(name)}`;
    if (type === 'role')              return `/admin/role/${encodeURIComponent(name)}`;
    if (type === 'record')            return `/admin/record/${encodeURIComponent(name)}`;
    if (type === 'service_operation') return `/admin/object/service_operation/${encodeURIComponent(name)}`;
    if (type === 'node')              return `/admin/object/node/${encodeURIComponent(name)}`;
    if (type === 'queue')             return `/admin/object/queue/${encodeURIComponent(name)}`;
    if (type === 'routing')           return `/admin/object/routing/${encodeURIComponent(name)}`;
    return `/admin/object/${encodeURIComponent(type)}/${encodeURIComponent(name)}`;
}

function inferObject(row) {
    if (row._links && row._links.admin) {
        return row._links.admin;
    }
    if (row._links && row._links.peoplecode) {
        return row._links.peoplecode;
    }

    if (row.recname && row.fieldname) return objectUrl('field', `${row.recname}.${row.fieldname}`);
    if (row.oprid) return objectUrl('operator', row.oprid);
    if (row.roleuser) return objectUrl('operator', row.roleuser);
    if (row.rolename) return objectUrl('role', row.rolename);
    if (row.classid) return objectUrl('permissionlist', row.classid);
    if (row.pnlgrpname) return objectUrl('component', row.pnlgrpname);
    if (row.pnlname) return objectUrl('page', row.pnlname);
    if (row.recname) return objectUrl('record', row.recname);
    if (row.searchrecname) return objectUrl('record', row.searchrecname);
    if (row.addsrchrecname) return objectUrl('record', row.addsrchrecname);
    if (row.ptibapplname) return objectUrl('service_operation', row.ptibapplname);
    if (row.ib_operationname) return objectUrl('service_operation', row.ib_operationname);
    if (row.routingdefnname) return objectUrl('routing', row.routingdefnname);
    if (row.msgnodename) return objectUrl('node', row.msgnodename);
    if (row.queuename) return objectUrl('queue', row.queuename);
    if (row.portal_objname) return objectUrl('portal_registry', row.portal_objname);
    if (row.tree_name) return objectUrl('tree', row.tree_name);
    if (row.bcname) return objectUrl('ci', row.bcname);
    if (row.packageroot) return objectUrl('application_package', row.packageroot);
    return null;
}

function labelFor(row) {
    return row.title || row.label ||
        row.name || row.oprid || row.roleuser || row.rolename || row.classid ||
        row.pnlgrpname || row.pnlname || row.recname || row.fieldname || row.portal_objname || row.menuname ||
        row.reference || row.ae_step || row.ae_section || row.ae_applid ||
        row.routingdefnname || row.msgnodename || row.queuename || row.ptibapplname ||
        row.ib_operationname || row.ae_step || row.tree_name || row.tree_node || row.tree_branch || row.range_from ||
        row.bcname || row.bcitemname ||
        row.packageroot || row.appclassid ||
        row.objectvalue1 || '(item)';
}

const _DETAIL_SKIP = new Set([
    '_links','title','label','name','reference','oprid','roleuser','rolename','classid','pnlgrpname','pnlname',
    'recname','fieldname','portal_objname','menuname','routingdefnname','msgnodename','queuename','ptibapplname',
    'ib_operationname','ae_step','ae_section','ae_applid','tree_name','tree_node','tree_branch','range_from',
    'bcname','bcitemname','objectvalue1','packageroot','appclassid','qualifypath','full_path',
    'has_peoplecode','encoded_reference','source','progseq','objectid1',
    'portal_permtype_label','portal_reftype_label','portal_reftype','portal_permtype',
    'authorizedactions','displayonly','raw_authorizedactions','raw_displayonly',
    'pnlitemname','target_portal_objname','portal_iscascade',
    'runstatus','runstatus_label','prcstype','prcsname','runlocation','outdesttype','outdestformat',
    'nav_path','nav_parent_label','nav_grandparent_label','nav_gpar_objname',
    'message_set_nbr','message_nbr','severity','severity_label',
]);

function detailFor(row) {
    const skip = row.relationship ? _DETAIL_SKIP : new Set([..._DETAIL_SKIP, 'relationship']);
    return Object.keys(row)
        .filter(key => !key.startsWith('_') && !skip.has(key) && row[key] !== null && row[key] !== undefined && row[key] !== '' && row[key] !== ' ')
        .slice(0, 5)
        .map(key => `${key}=${row[key]}`)
        .join(' | ');
}

function highlightPeopleCode(source) {
    if (!source) return '';
    function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    const tokens = [];
    let pos = 0;
    while (pos < source.length) {
        if (source.startsWith('/*', pos)) {
            const end = source.indexOf('*/', pos + 2);
            const closePos = end === -1 ? source.length : end + 2;
            tokens.push({type:'comment', text: source.slice(pos, closePos)});
            pos = closePos;
        } else if (source[pos] === '"') {
            let i = pos + 1;
            while (i < source.length && source[i] !== '"') i++;
            tokens.push({type:'string', text: source.slice(pos, i + 1)});
            pos = i + 1;
        } else {
            let i = pos + 1;
            while (i < source.length && source[i] !== '/' && source[i] !== '"') i++;
            tokens.push({type:'code', text: source.slice(pos, i)});
            pos = i;
        }
    }

    const KW  = /\\b(If|Else|ElseIf|End-If|For|End-For|While|End-While|Evaluate|When|When-Other|End-Evaluate|Function|End-Function|Return|Local|Global|Component|Object|Constant|CreateObject|import|class|method|property|get|set|readonly|abstract|extends|Array|of|As|By|Step|Break|Continue|try|catch|throw|end-try)\\b/g;
    const BIN = /\\b(SQLExec|CreateSQL|GetSQL|CreateRecord|GetRecord|GetField|GetRowset|GetLevel0|GetComponent|CallAppEngine|Transfer|DoSave|DoModal|CommitWork|RollbackWork|MessageBox|WinMessage|Error|Warning|CreateMessage|GetMessage|CreateObject)\\b/g;
    const NUM = /\\b\\d+(\\.\\d+)?\\b/g;

    function colorCode(text) {
        let h = esc(text);
        h = h.replace(KW,  m => `<span style="color:#569cd6">${m}</span>`);
        h = h.replace(BIN, m => `<span style="color:#dcdcaa">${m}</span>`);
        h = h.replace(NUM, m => `<span style="color:#b5cea8">${m}</span>`);
        return h;
    }

    return tokens.map(t => {
        if (t.type === 'comment') return `<span style="color:#6a9955">${esc(t.text)}</span>`;
        if (t.type === 'string')  return `<span style="color:#ce9178">${esc(t.text)}</span>`;
        return colorCode(t.text);
    }).join('');
}

function highlightSQL(sql) {
    if (!sql) return '';
    function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    // Tokenize: single-quoted strings, line comments (--), block comments (/* */), rest
    const tokens = [];
    let pos = 0;
    while (pos < sql.length) {
        if (sql.startsWith('/*', pos)) {
            const end = sql.indexOf('*/', pos + 2);
            const closePos = end === -1 ? sql.length : end + 2;
            tokens.push({type:'comment', text: sql.slice(pos, closePos)});
            pos = closePos;
        } else if (sql.startsWith('--', pos)) {
            const end = sql.indexOf('\\n', pos);
            const closePos = end === -1 ? sql.length : end;
            tokens.push({type:'comment', text: sql.slice(pos, closePos)});
            pos = closePos;
        } else if (sql[pos] === "'") {
            let i = pos + 1;
            while (i < sql.length) {
                if (sql[i] === "'" && sql[i+1] === "'") { i += 2; continue; }
                if (sql[i] === "'") { i++; break; }
                i++;
            }
            tokens.push({type:'string', text: sql.slice(pos, i)});
            pos = i;
        } else {
            let i = pos + 1;
            while (i < sql.length && sql[i] !== '/' && sql[i] !== '-' && sql[i] !== "'") i++;
            tokens.push({type:'code', text: sql.slice(pos, i)});
            pos = i;
        }
    }

    const KW = /\\b(SELECT|FROM|WHERE|AND|OR|NOT|IN|LIKE|ORDER|BY|GROUP|HAVING|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|DISTINCT|UNION|ALL|CASE|WHEN|THEN|ELSE|END|IS|NULL|EXISTS|BETWEEN|INTO|VALUES|INSERT|UPDATE|SET|DELETE|CREATE|ALTER|DROP|TABLE|VIEW|INDEX|WITH|OVER|PARTITION|ROWNUM|FETCH|ROWS|ONLY|COUNT|SUM|MAX|MIN|AVG|NVL|NVL2|COALESCE|TRIM|UPPER|LOWER|TO_DATE|TO_CHAR|DECODE|SUBSTR|LENGTH|INSTR|REPLACE|SYSDATE|TRUNC|ROUND|MOD|NEXT_VAL|CONNECT|LEVEL|PRIOR|START|ROWID|CONSTRAINT|PRIMARY|KEY|UNIQUE|FOREIGN|REFERENCES|DEFAULT|NOT)\\b/gi;
    const META = /(%Table|%Bind|%Select|%SelectAll|%SelectInit|%UpdateStats|%Insert|%Delete|%DateAdd|%DateDiff|%DateOut|%SQL|%Current|%Truncate|%TruncateTable|%Execute|%List|%CurrentDateIn|%EffDtCheck|%OPERATOR|%ParmList|%TextIn|%DateTimeIn|%TimeIn)\\b/g;
    const NUM = /\\b\\d+(\\.\\d+)?\\b/g;

    function colorCode(text) {
        const h = esc(text);
        return h
            .replace(KW,   m => `<span style="color:#569cd6">${m}</span>`)
            .replace(META, m => `<span style="color:#c586c0">${m}</span>`)
            .replace(NUM,  m => `<span style="color:#b5cea8">${m}</span>`);
    }

    return tokens.map(t => {
        if (t.type === 'comment') return `<span style="color:#6a9955">${esc(t.text)}</span>`;
        if (t.type === 'string')  return `<span style="color:#ce9178">${esc(t.text)}</span>`;
        return colorCode(t.text);
    }).join('');
}

function renderKeyValues(target, data) {
    target.innerHTML = '';
    const keys = Object.keys(data || {}).filter(k =>
        !k.startsWith('_') && k !== 'ddl' && k !== 'source' &&
        data[k] !== null && data[k] !== undefined && data[k] !== '' && data[k] !== ' '
    );
    if (!keys.length) return;
    const grid = document.createElement('div');
    grid.className = 'kv-grid';
    keys.forEach(key => {
        const kEl = document.createElement('div');
        kEl.className = 'kv-key';
        kEl.textContent = key.replace(/_/g, ' ');
        const vEl = document.createElement('div');
        vEl.className = 'kv-val';
        const value = data[key];
        const url = typeof value === 'string' ? inferObject({[key]: value}) : null;
        if (url) {
            const a = document.createElement('a');
            a.href = url; a.textContent = value;
            vEl.appendChild(a);
        } else {
            vEl.textContent = typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');
        }
        grid.appendChild(kEl);
        grid.appendChild(vEl);
    });
    target.appendChild(grid);
}

function renderRows(target, rows) {
    target.innerHTML = '';
    if (!rows.length) {
        target.className = 'muted';
        target.textContent = 'No items.';
        return;
    }
    target.className = '';
    rows.forEach(row => {
        const div = document.createElement('div');
        const url = inferObject(row);
        div.className = url ? 'row clickable' : 'row';
        if (row.level !== undefined && row.level !== null) {
            div.style.marginLeft = `${Math.min(Number(row.level) || 0, 4) * 18}px`;
        }
        if (url) div.onclick = () => window.location.href = url;

        const hdr = document.createElement('div');
        hdr.className = 'row-header';

        if (row.relationship) {
            const chip = document.createElement('span');
            chip.className = 'rel-chip';
            chip.textContent = row.relationship;
            hdr.appendChild(chip);
        }

        const title = document.createElement('span');
        title.className = 'title';
        title.textContent = labelFor(row);
        hdr.appendChild(title);

        if (url) {
            const arrow = document.createElement('span');
            arrow.className = 'row-arrow';
            arrow.textContent = '→';
            hdr.appendChild(arrow);
        }

        div.appendChild(hdr);

        const detailText = detailFor(row);
        if (detailText) {
            const detail = document.createElement('span');
            detail.className = 'detail';
            detail.textContent = detailText;
            div.appendChild(detail);
        }

        if (row.data && row.data.ddl) {
            const pre = document.createElement('pre');
            pre.style.cssText = 'margin:6px 0 0;padding:6px;background:#050c14;border:1px solid #1e3344;font-size:11px';
            pre.innerHTML = highlightSQL(row.data.ddl);
            div.appendChild(pre);
        }

        target.appendChild(div);
    });
}

function renderActions(object) { /* folded into renderObject */ }

function buildBreadcrumbs(type, name) {
    const crumb = (label, href) => href
        ? `<a href="${href}" style="color:#7faab2">${label}</a>`
        : `<span style="color:#d7faff">${label}</span>`;
    const sep = ' <span style="color:#1e5b66">›</span> ';

    const adminLink = crumb('Admin', '/admin/');
    const objLink   = crumb('Object Explorer', '/admin/search');

    const TYPE_TRAILS = {
        record:             ['Records', '/admin/search'],
        field:              ['Fields',  null],
        component:          ['Components', '/admin/search'],
        page:               ['Pages', null],
        application_engine: ['AE Programs', '/admin/ae'],
        sql_definition:     ['SQL Definitions', null],
        tree:               ['Trees', null],
        ci:                 ['Component Interfaces', null],
        peoplecode:         ['PeopleCode', null],
        operator:           ['Security', '/admin/security'],
        role:               ['Security', '/admin/security'],
        permission_list:    ['Security', '/admin/security'],
        permissionlist:     ['Security', '/admin/security'],
        portal_registry:    ['Portal Registry', '/admin/portal'],
        service_operation:  ['Integration Broker', '/admin/ib'],
        node:               ['Integration Broker', '/admin/ib'],
        queue:              ['Integration Broker', '/admin/ib'],
        routing:            ['Integration Broker', '/admin/ib'],
    };

    const SECOND_CRUMB = {
        operator:       'Operators',
        role:           'Roles',
        permission_list:'Permission Lists',
        permissionlist: 'Permission Lists',
        service_operation: 'Services',
        node:           'Nodes',
        queue:          'Queues',
        routing:        'Routings',
    };

    const trail = TYPE_TRAILS[type];
    if (!trail) return adminLink + sep + objLink + sep + crumb(name, null);

    const [groupLabel, groupHref] = trail;
    let parts = [adminLink, crumb(groupLabel, groupHref)];

    const second = SECOND_CRUMB[type];
    if (second) parts.push(crumb(second, null));

    // For field names like "JOB.EMPLID", show parent record as intermediate breadcrumb
    if (type === 'field' && name.includes('.')) {
        const [rec, fld] = name.split('.', 2);
        parts.push(crumb(rec, `/admin/object/record/${encodeURIComponent(rec)}`));
        parts.push(crumb(fld, null));
    } else {
        parts.push(crumb(name, null));
    }

    return parts.join(sep);
}

function sectionTitle(section) {
    return section.name || section.title || section.id || 'Section';
}

function sectionData(section) {
    return section.data || {};
}

function sectionItems(section) {
    return section.items || section.rows || [];
}

function isPresentValue(value) {
    return value !== null && value !== undefined && value !== '' && value !== ' ';
}

function sectionFacts(section) {
    const data = sectionData(section);
    const items = sectionItems(section);
    const hasDDL = !!data.ddl;
    const hasSrc = !!data.source;
    const dataKeys = Object.keys(data).filter(k => k !== 'ddl' && k !== 'source' && !k.startsWith('_'));
    const hasData = dataKeys.some(k => isPresentValue(data[k]));
    const dataCount = dataKeys.filter(k => isPresentValue(data[k])).length;
    const explicitCount = Number(section.count || section.total || section.total_count || 0) || 0;
    const count = items.length || explicitCount || dataCount || (hasDDL || hasSrc ? 1 : 0);
    return {
        items,
        data,
        dataKeys,
        hasDDL,
        hasSrc,
        hasData,
        dataCount,
        count,
        empty: !items.length && !hasDDL && !hasSrc && !hasData
    };
}

function sectionKind(title) {
    const t = String(title || '').toLowerCase();
    if (t.includes('warning') || t.includes('error')) return 'warn';
    if (t.includes('graph') || t.includes('edge') || t.includes('node')) return 'graph';
    if (t.includes('security') || t.includes('access') || t.includes('permission') || t.includes('role')) return 'security';
    return 'normal';
}

function sectionId(index, title) {
    const slug = String(title || 'section').toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'section';
    return `section-${index}-${slug}`;
}

function oeEscHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function renderSectionRail(object, sections, sectionInfos) {
    const rail = document.getElementById('sectionRail');
    if (!sections.length) {
        rail.innerHTML = '';
        rail.style.display = 'none';
        return;
    }

    const warnCount = sectionInfos.filter(info => info.kind === 'warn').length;
    const totalItems = sectionInfos.reduce((sum, info) => sum + (info.facts.items || []).length, 0);
    const graphInfo = sectionInfos.find(info => info.kind === 'graph');
    const graphCount = graphInfo ? graphInfo.facts.count : 0;

    const summary = [
        ['Sections', sections.length],
        ['Rows', totalItems],
    ];
    if (warnCount) summary.push(['Warnings', warnCount]);
    if (graphCount) summary.push(['Graph', graphCount]);

    const summaryHtml = summary.map(([label, value]) =>
        `<div class="summary-pill"><span>${oeEscHtml(label)}</span><strong>${oeEscHtml(value)}</strong></div>`
    ).join('');

    const linksHtml = sectionInfos.map(info => {
        const classes = ['section-link', info.kind];
        if (info.facts.empty) classes.push('empty');
        const count = info.facts.count ? `<span class="section-count">${oeEscHtml(info.facts.count)}</span>` : '';
        return `<a class="${classes.join(' ')}" href="#${oeEscHtml(info.id)}"><span>${oeEscHtml(info.title)}</span>${count}</a>`;
    }).join('');

    rail.innerHTML = `
        <div class="object-rail-title">Object Map</div>
        <div class="object-rail-summary">${summaryHtml}</div>
        <nav class="section-nav">${linksHtml}</nav>
    `;
    rail.style.display = '';
}

function renderSectionSummary(card, section, facts, kind) {
    const bits = [];
    if (facts.items.length) bits.push(`${facts.items.length} item${facts.items.length === 1 ? '' : 's'}`);
    if (facts.dataCount) bits.push(`${facts.dataCount} field${facts.dataCount === 1 ? '' : 's'}`);
    if (facts.hasDDL) bits.push('DDL');
    if (facts.hasSrc) bits.push('source');
    if (kind === 'warn') bits.push('attention');
    if (!bits.length) return;

    const div = document.createElement('div');
    div.className = 'section-summary';
    bits.forEach(bit => {
        const span = document.createElement('span');
        span.textContent = bit;
        div.appendChild(span);
    });
    card.appendChild(div);
}

function renderObject(object) {
    // ── Object header ──────────────────────────────────────────────────────
    const chip = document.getElementById('objectTypeChip');
    const c = TYPE_CHIP_CFG[object.type] || {label: object.type, bg:'#111', border:'#334', color:'#778'};
    chip.textContent = (c.label || object.type).toUpperCase();
    chip.style.cssText = `background:${c.bg};border:1px solid ${c.border};color:${c.color}`;
    chip.style.display = '';

    document.getElementById('objectTitle').textContent = object.name;

    const desc = (object.overview || {}).description || object.description || '';
    const descEl = document.getElementById('objectDesc');
    descEl.textContent = desc;
    descEl.style.display = desc ? '' : 'none';

    // Overview key-values — skip meta/noise keys, cap at 12
    const OV_SKIP = new Set(['id','display_name','description','status']);
    const ovKeys = Object.keys(object.overview || {})
        .filter(k => !OV_SKIP.has(k) && !k.startsWith('_') && object.overview[k] !== null &&
                     object.overview[k] !== undefined && object.overview[k] !== '' && object.overview[k] !== ' ')
        .slice(0, 12);
    const ovData = {};
    ovKeys.forEach(k => ovData[k] = object.overview[k]);
    renderKeyValues(document.getElementById('overview'), ovData);

    // Action links
    const actEl = document.getElementById('actions');
    actEl.innerHTML = '';
    const linkKeys = Object.keys(object._links || {}).filter(k => k !== 'self');
    linkKeys.forEach(name => {
        const a = document.createElement('a');
        a.href = object._links[name];
        a.textContent = name;
        actEl.appendChild(a);
    });
    actEl.style.display = linkKeys.length ? '' : 'none';

    const metaEl = document.getElementById('objectMeta');
    const objectSections = object.sections || [];
    metaEl.style.display = objectSections.length ? '' : 'none';
    metaEl.textContent = `${objectSections.length} sections`;

    // Breadcrumbs
    const bc = document.getElementById('breadcrumb');
    bc.innerHTML = buildBreadcrumbs(object.type, object.name);
    bc.style.display = '';

    // ── Sections ───────────────────────────────────────────────────────────
    const sections = document.getElementById('sections');
    sections.innerHTML = '';

    const sectionInfos = objectSections.map((section, index) => {
        const title = sectionTitle(section);
        return {
            section,
            title,
            id: sectionId(index, title),
            kind: sectionKind(title),
            facts: sectionFacts(section),
        };
    });
    renderSectionRail(object, objectSections, sectionInfos);

    sectionInfos.forEach(info => {
        const section = info.section;
        const facts = info.facts;
        const hasDDL = facts.hasDDL;
        const hasSrc = facts.hasSrc;
        const itemCount = facts.items.length;
        const hasData = facts.hasData;
        const isEmpty = facts.empty;
        const isWarn = info.kind === 'warn';
        const isGraph = info.kind === 'graph';
        const isSecurity = info.kind === 'security';
        const isWide = hasDDL || hasSrc || isGraph;

        const card = document.createElement('div');
        let cls = 'card';
        if (isWide) cls += ' section-wide';
        if (isWarn) cls += ' section-warn';
        if (isGraph) cls += ' section-graph';
        if (isSecurity) cls += ' section-security';
        if (isEmpty) cls += ' section-empty';
        card.className = cls;
        card.id = info.id;

        // Section header with count badge
        const h = document.createElement('h2');
        h.style.cssText = 'display:flex;align-items:center;margin:0 0 8px';
        const nameSpan = document.createElement('span');
        nameSpan.textContent = info.title;
        h.appendChild(nameSpan);
        if (facts.count > 0) {
            const badge = document.createElement('span');
            badge.className = 'count-badge';
            badge.textContent = facts.count;
            h.appendChild(badge);
        }
        card.appendChild(h);
        renderSectionSummary(card, section, facts, info.kind);

        if (hasData) {
            const dataDiv = document.createElement('div');
            renderKeyValues(dataDiv, facts.data);
            card.appendChild(dataDiv);
        }

        if (hasDDL) {
            const pre = document.createElement('pre');
            pre.innerHTML = highlightSQL(facts.data.ddl);
            card.appendChild(pre);
        }

        if (hasSrc) {
            const pre = document.createElement('pre');
            pre.innerHTML = highlightPeopleCode(facts.data.source);
            card.appendChild(pre);
        }

        if (itemCount > 0) {
            const rowsDiv = document.createElement('div');
            renderRows(rowsDiv, facts.items);
            card.appendChild(rowsDiv);
        } else if (isEmpty) {
            const empty = document.createElement('div');
            empty.className = 'muted';
            empty.textContent = 'No data.';
            card.appendChild(empty);
        }

        sections.appendChild(card);
    });
}

const RECENT_KEY = 'ds_recent_objects';
const RECENT_MAX = 12;

const TYPE_CHIP_CFG = {
    operator:           {label:'Operator',     bg:'#001830',border:'#00e5ff44',color:'#00e5ff'},
    role:               {label:'Role',          bg:'#180030',border:'#aa55ff',  color:'#aa55ff'},
    record:             {label:'Record',        bg:'#001830',border:'#00e5ff22',color:'#8ab'},
    field:              {label:'Field',         bg:'#0d1a0d',border:'#00aa6644',color:'#00aa66'},
    component:          {label:'Component',     bg:'#1a1800',border:'#aaaa00',  color:'#aaaa00'},
    page:               {label:'Page',          bg:'#001a18',border:'#00aaaa',  color:'#00aaaa'},
    permissionlist:     {label:'Perm List',     bg:'#1a0000',border:'#ff4444',  color:'#ff8888'},
    application_engine: {label:'App Engine',    bg:'#1a0a00',border:'#ff8800',  color:'#ff8800'},
    peoplecode:         {label:'PeopleCode',    bg:'#001018',border:'#0088cc',  color:'#55aaff'},
    service_operation:  {label:'IB Service',    bg:'#001a14',border:'#00cc8844',color:'#00cc88'},
    node:               {label:'IB Node',       bg:'#1a1800',border:'#ccaa0044',color:'#ccaa00'},
    queue:              {label:'IB Queue',       bg:'#180018',border:'#cc66ff44',color:'#cc66ff'},
    routing:            {label:'IB Routing',    bg:'#001818',border:'#00aabb44',color:'#00aabb'},
    application_package:{label:'App Package',   bg:'#180a1a',border:'#cc44ff44',color:'#cc44ff'},
    application_class:  {label:'App Class',     bg:'#12081a',border:'#aa33ee44',color:'#aa33ee'},
    app_class:          {label:'App Class',     bg:'#12081a',border:'#aa33ee44',color:'#aa33ee'},
    message_catalog:    {label:'Message',       bg:'#0a1800',border:'#66cc2244',color:'#88dd44'},
    menu:               {label:'Menu',          bg:'#1a1200',border:'#cc880044',color:'#cc8800'},
    query:              {label:'PS Query',      bg:'#001820',border:'#0099bb44',color:'#00bbdd'},
    tree:               {label:'Tree',          bg:'#001a0a',border:'#00bb6644',color:'#00bb66'},
    ci:                 {label:'CI',            bg:'#001a1a',border:'#00aaaa44',color:'#00cccc'},
    sql_definition:         {label:'SQL Def',       bg:'#1a1200',border:'#ddaa0044',color:'#ddaa00'},
    approval:               {label:'Approval',      bg:'#001814',border:'#00cc8844',color:'#00cc88'},
    xml_publisher_report:   {label:'XPub Report',   bg:'#1a0a18',border:'#cc44aa44',color:'#cc44aa'},
    xml_publisher_datasource:{label:'XPub DataSrc', bg:'#180814',border:'#aa336644',color:'#aa3366'},
    nav_collection:         {label:'Nav Coll',      bg:'#001a10',border:'#00bb6644',color:'#00bb66'},
    event_mapping:          {label:'Event Map',     bg:'#1a1400',border:'#ddcc0044',color:'#ddcc00'},
    related_content:        {label:'Related Cont',  bg:'#0a001a',border:'#9944ff44',color:'#9944ff'},
    search_definition:      {label:'Search Def',    bg:'#001820',border:'#2299ee44',color:'#2299ee'},
    search_category:        {label:'Search Cat',    bg:'#10001a',border:'#7744ee44',color:'#7744ee'},
    drop_zone:               {label:'Drop Zone',     bg:'#1a1000',border:'#ee880044',color:'#ee8800'},
    pivot_grid:              {label:'PivotGrid',     bg:'#0a1a10',border:'#22cc6644',color:'#22cc66'},
    connected_query:         {label:'Conn. Query',   bg:'#001018',border:'#00ccee44',color:'#00ccee'},
    prcs_defn:               {label:'Process Def',   bg:'#100a18',border:'#aa66ff44',color:'#aa66ff'},
    file_layout:             {label:'File Layout',   bg:'#0a1218',border:'#44aaff44',color:'#44aaff'},
    xlat_field:              {label:'Translate',      bg:'#100f00',border:'#ddcc0044',color:'#ddcc00'},
    project:                 {label:'Project',        bg:'#0a100a',border:'#55ee5544',color:'#55ee55'},
    message:                 {label:'IB Message',     bg:'#180a1a',border:'#cc44ff44',color:'#cc44ff'},
    ib_application:          {label:'IB App Svc',     bg:'#001818',border:'#00ddcc44',color:'#00ddcc'},
    content_service:         {label:'Content Svc',    bg:'#101810',border:'#44ee8844',color:'#44ee88'},
    ptf_test:                {label:'PTF Test',       bg:'#181008',border:'#ee880044',color:'#ee8800'},
    ads_definition:          {label:'ADS Def',        bg:'#0a0a18',border:'#6688ff44',color:'#6688ff'},
    ib_service_group:        {label:'IB Svc Group',   bg:'#0a1818',border:'#00ccdd44',color:'#00ccdd'},
    url_definition:          {label:'URL Def',         bg:'#0a1208',border:'#55dd3344',color:'#55dd33'},
    chatbot_skill:           {label:'Chatbot Skill',   bg:'#180818',border:'#dd44ff44',color:'#dd44ff'},
    ib_routing:              {label:'IB Routing',      bg:'#0a1020',border:'#4488ff44',color:'#4488ff'},
    style_sheet:             {label:'Style Sheet',     bg:'#181208',border:'#ffcc4444',color:'#ffcc44'},
    archive_object:          {label:'Archive Object',  bg:'#100a18',border:'#aa66cc44',color:'#aa66cc'},
    timezone:                {label:'Timezone',         bg:'#001828',border:'#0066cc44',color:'#4499ee'},
    locale:                  {label:'Locale',           bg:'#081808',border:'#22aa4444',color:'#55cc55'},
    pm_metric:               {label:'PM Metric',        bg:'#0d0d18',border:'#7766ee44',color:'#9988ff'},
    pm_transaction:          {label:'PM Transaction',   bg:'#100d18',border:'#9966ff44',color:'#bb99ff'},
    pm_event:                {label:'PM Event',         bg:'#0d0d18',border:'#6655dd44',color:'#8877ee'},
    ib_operation:            {label:'IB Operation',     bg:'#181008',border:'#ff880044',color:'#ffaa44'},
};

function typeChipHtml(type) {
    const c = TYPE_CHIP_CFG[type] || {label: type, bg:'#111', border:'#334', color:'#778'};
    return `<span style="display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;background:${c.bg};border:1px solid ${c.border};color:${c.color};margin-right:6px;white-space:nowrap;">${c.label}</span>`;
}

function loadRecent() {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch(e) { return []; }
}
function saveRecent(list) { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); }

function relativeTime(ts) {
    const sec = Math.floor((Date.now() - ts) / 1000);
    if (sec < 60)   return 'just now';
    if (sec < 3600) return `${Math.floor(sec/60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec/3600)}h ago`;
    return `${Math.floor(sec/86400)}d ago`;
}

function pushRecent(type, name, title, description) {
    const list = loadRecent().filter(r => !(r.type === type && r.name === name));
    list.unshift({type, name, title: title || name, description: description || '', ts: Date.now()});
    saveRecent(list.slice(0, RECENT_MAX));
    renderRecentList();
}

function removeRecent(type, name, event) {
    event.stopPropagation();
    saveRecent(loadRecent().filter(r => !(r.type === type && r.name === name)));
    renderRecentList();
}

function renderRecentList() {
    const el = document.getElementById('recentList');
    const list = loadRecent();
    if (!list.length) { el.className = 'muted'; el.textContent = 'No objects viewed yet.'; return; }
    el.className = '';
    el.innerHTML = list.map((r, i) => {
        const url = objectUrl(r.type, r.name);
        const ago = r.ts ? relativeTime(r.ts) : '';
        const desc = r.description && r.description !== r.name && r.description !== r.title
            ? `<span style="display:block;color:#667;font-size:10px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px">${r.description}</span>`
            : '';
        return `<div class="result" style="padding:6px 8px;margin:3px 0;display:flex;justify-content:space-between;align-items:flex-start;" onclick="window.location.href='${url}'">
          <div style="overflow:hidden;flex:1">
            <div style="display:flex;align-items:center;gap:6px">
              ${typeChipHtml(r.type)}
              <span style="font-family:monospace;font-size:12px">${r.name}</span>
              ${ago ? `<span style="color:#446;font-size:10px">${ago}</span>` : ''}
            </div>
            ${desc}
          </div>
          <button data-type="${esc(r.type)}" data-name="${esc(r.name)}" onclick="removeRecent(this.dataset.type,this.dataset.name,event)"
                  style="background:transparent;border:none;color:#334;cursor:pointer;font-size:14px;padding:0 2px;line-height:1;flex-shrink:0" title="Remove">×</button>
        </div>`;
    }).join('');
}

function clearRecent() { saveRecent([]); renderRecentList(); }

async function loadObject(type, name, options = {}) {
    if (!type || !name) return;

    document.getElementById('objectType').value = type;
    document.getElementById('objectName').value = name;
    setStatus(`Loading ${type}:${name}...`);

    try {
        const object = await api(`/api/peoplesoft/object/${encodeURIComponent(type)}/${encodeURIComponent(name)}?env=${ENV}`);
        renderObject(object);
        const desc = (object.overview || {}).description || object.description || '';
        pushRecent(object.type, object.name, object.title || object.name, desc);

        if (options.updateUrl) {
            const url = objectUrl(object.type, object.name);
            if (window.location.pathname + window.location.search !== url) {
                history.pushState({type: object.type, name: object.name}, '', url);
            }
        }

        setStatus(`Loaded ${object.type}:${object.name}.`);
    } catch (err) {
        setStatus(`Object load failed: ${err.message || err}`);
    }
}

async function globalSearch() {
    const q = document.getElementById('globalSearch').value.trim();

    if (!q) {
        setStatus('Enter search text.');
        return;
    }

    setStatus(`Searching for ${q}...`);
    const rows = await api(`/api/peoplesoft/search?env=${ENV}&q=${encodeURIComponent(q)}`);
    const results = document.getElementById('results');
    results.innerHTML = '';
    results.className = '';

    if (!rows.length) {
        results.className = 'muted';
        results.textContent = 'No results.';
        return;
    }

    const valid = rows.filter(r => !r.error && r.name);
    valid.forEach(row => {
        const url = (row._links && row._links.admin) ? row._links.admin : objectUrl(row.type, row.name);
        const chipHtml = typeChipHtml(row.type);
        const div = document.createElement('div');
        div.className = 'result';
        div.onclick = () => window.location.href = url;
        div.innerHTML = `<span class="title">${chipHtml}<span style="font-family:monospace;">${row.name}</span></span>`
            + (row.description ? `<span class="detail">${row.description}</span>` : '');
        results.appendChild(div);
    });

    const errCount = rows.length - valid.length;
    setStatus(`Found ${valid.length} object${valid.length===1?'':'s'}${errCount > 0 ? ` (${errCount} types not accessible in ${ENV})` : ''}.`);
}

function openTypedObject() {
    const type = document.getElementById('objectType').value;
    const name = document.getElementById('objectName').value.trim();

    if (!name) {
        setStatus('Enter an object name.');
        return;
    }

    const url = objectUrl(type, name);
    if (url.startsWith('/admin/object/')) {
        loadObject(type, name, {updateUrl: true});
    } else {
        window.location.href = url;
    }
}

window.addEventListener('popstate', () => {
    const match = window.location.pathname.match(/^\\/admin\\/object\\/([^/]+)\\/(.+)$/);
    if (match) {
        loadObject(decodeURIComponent(match[1]), decodeURIComponent(match[2]), {updateUrl: false});
    }
});

document.getElementById('globalSearch').addEventListener('keydown', event => {
    if (event.key === 'Enter') globalSearch();
});

document.getElementById('objectName').addEventListener('keydown', event => {
    if (event.key === 'Enter') openTypedObject();
});

// Show/hide SQL type filter based on selected object type
document.getElementById('objectType').addEventListener('change', () => {
    const isSql = document.getElementById('objectType').value === 'sql_definition';
    document.getElementById('sqlTypeFilter').style.display = isSql ? '' : 'none';
    document.getElementById('sqlSearchBtn').style.display  = isSql ? '' : 'none';
});

async function searchSqlDefinitions() {
    const q       = document.getElementById('objectName').value.trim();
    const sqltype = document.getElementById('sqlTypeFilter').value;
    setStatus('Searching SQL Definitions...');
    const params = new URLSearchParams({env: ENV, q, limit: 50});
    if (sqltype !== '') params.set('sqltype', sqltype);
    const rows = await api(`/api/peoplesoft/sql_definitions?${params}`);
    const results = document.getElementById('results');
    if (!rows.length) {
        results.className = 'muted';
        results.textContent = 'No SQL definitions found.';
        setStatus('No results.');
        return;
    }
    results.className = '';
    results.innerHTML = rows.map(row => {
        const sid  = row.sqlid || '';
        const lbl  = row.sqltype_label || '';
        const own  = row.objectownerid || '';
        const url  = (row._links || {}).admin || '';
        return `<div class="result" onclick="window.location.href='${url}'">
            <span class="title">${sid}</span>
            <span class="detail">${lbl}${own ? ' · ' + own : ''}</span>
        </div>`;
    }).join('');
    setStatus(`${rows.length} SQL definition(s) found.`);
}

renderRecentList();

if (INITIAL_TYPE && INITIAL_NAME) {
    loadObject(INITIAL_TYPE, INITIAL_NAME, {updateUrl: false});
}
</script>
""")
    html = (
        html
        .replace("__ESC_JS__", _ESC_JS)
        .replace("__OBJECT_TYPE__", json.dumps(object_type))
        .replace("__OBJECT_NAME__", json.dumps(object_name))
    )
    return html


@router.get("/object", response_class=HTMLResponse)
def admin_object_search():
    return object_explorer_page()


@router.get("/object/{object_type}/{object_name}", response_class=HTMLResponse)
def admin_object(object_type: str, object_name: str, env: str = "HCM"):
    from fastapi.responses import RedirectResponse
    if object_type == "sqr_program":
        filename = object_name.lower()
        if not (filename.endswith(".sqr") or filename.endswith(".sqc")):
            filename += ".sqr"
        return RedirectResponse(f"/admin/sqr/{filename}", status_code=302)
    if object_type == "cobol_program":
        filename = object_name.lower()
        if not filename.endswith(".cbl"):
            filename += ".cbl"
        return RedirectResponse(f"/admin/cobol/{filename}", status_code=302)
    if object_type == "component":
        return RedirectResponse(f"/admin/component?name={object_name}&env={env}", status_code=302)
    if object_type == "page":
        return RedirectResponse(f"/admin/page?name={object_name}&env={env}", status_code=302)
    if object_type == "permissionlist":
        return RedirectResponse(f"/admin/permissionlist/{object_name}?env={env}", status_code=302)
    if object_type == "application_engine":
        return RedirectResponse(f"/admin/ae?q={object_name}&env={env}", status_code=302)
    return object_explorer_page(object_type, object_name)


@router.get("/portal", response_class=HTMLResponse)
def admin_portal():
    return _shell("Portal Explorer", "objects", content="""\
    <style>
        body {
            background: #050b12;
            color: #d7faff;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #00e5ff;
            text-shadow: 0 0 12px #00e5ff;
            letter-spacing: 3px;
            margin-bottom: 10px;
        }

        h2 {
            color: #00e5ff;
            margin: 0 0 12px;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.35);
            padding: 16px;
            background: rgba(0, 20, 30, .75);
        }

        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
            margin-top: 18px;
        }

        .layout {
            display: grid;
            grid-template-columns: minmax(280px, 360px) 1fr;
            gap: 16px;
            align-items: start;
            margin-top: 16px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(240px, 1fr));
            gap: 16px;
        }

        input {
            padding: 8px;
            background: #0b1b24;
            color: white;
            border: 1px solid #00e5ff;
            min-width: 220px;
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 12px;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
        }

        .muted {
            color: #7faab2;
        }

        .row {
            border: 1px solid #1e5b66;
            padding: 10px;
            margin: 8px 0;
            background: rgba(5, 18, 28, .85);
            overflow-wrap: anywhere;
        }

        .clickable {
            cursor: pointer;
        }

        .clickable:hover {
            border-color: #00e5ff;
            box-shadow: 0 0 10px rgba(0,229,255,.25);
        }

        .title {
            color: #00e5ff;
            font-weight: bold;
            font-family: monospace;
        }

        .detail {
            display: block;
            color: #b8dce2;
            font-size: 12px;
            margin-top: 4px;
        }

        .crumbs {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            font-size: 12px;
        }

        .crumb {
            border: 1px solid #1e5b66;
            padding: 4px 6px;
            background: rgba(5,18,28,.85);
        }

        .counts {
            display: grid;
            grid-template-columns: repeat(3, minmax(90px, 1fr));
            gap: 8px;
        }

        .count {
            border: 1px solid #1e5b66;
            padding: 10px;
            background: rgba(5,18,28,.85);
        }

        .num {
            display: block;
            color: #00e5ff;
            font-size: 22px;
            font-weight: bold;
        }

        @media (max-width: 1000px) {
            .layout, .grid {
                grid-template-columns: 1fr;
            }
        }
</style>
    <div class="card toolbar">
        <input id="searchText" placeholder="Search content references">
        <button onclick="searchPortal()">Search</button>
        <input id="portalName" placeholder="PORTAL_OBJNAME">
        <button onclick="loadPortal()">Open</button>
        <input id="oprid" placeholder="Explain OPRID">
        <button onclick="explainPortal()">Explain Access</button>
        <select id="portalSelect" onchange="switchPortal()" style="background:#0b1b24;color:#d7faff;border:1px solid #00e5ff;padding:7px;font-size:12px">
            <option value="">-- Portal Tree --</option>
        </select>
        <button onclick="showAnalysis()">Analyse</button>
        <button onclick="expandSubtree()" style="background:#8844cc">Expand Subtree</button>
    </div>

    <div id="status" class="muted" style="margin-top:12px;">Search or open a Portal Registry content reference.</div>

    <div class="layout">
        <div class="card">
            <h2>
                <span id="leftPanelTitle">Search Results</span>
                <button id="btnTreeMode" onclick="toggleTreeMode()" style="float:right;font-size:10px;padding:4px 8px;background:#1e5b66">Tree</button>
            </h2>
            <div id="results" class="muted">No search run.</div>
            <div id="treePanel" style="display:none;max-height:600px;overflow-y:auto"></div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Definition</h2>
                <div id="definition" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Counts</h2>
                <div id="counts" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Breadcrumbs</h2>
                <div id="breadcrumbs" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Target Components</h2>
                <div id="targets" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Children</h2>
                <div id="children" class="muted">No content reference loaded.</div>
            </div>

            <div class="card" id="subtreeCard" style="display:none">
                <h2>Subtree <span id="subtreeCount" class="muted" style="font-size:11px"></span></h2>
                <div id="subtreePanel" style="max-height:420px;overflow-y:auto;font-size:11px;font-family:monospace"></div>
            </div>

            <div class="card">
                <h2>Portal Security</h2>
                <div id="security" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Access Paths</h2>
                <div id="accessPaths" class="muted">No content reference loaded.</div>
            </div>

            <div class="card">
                <h2>Explain Result</h2>
                <div id="explain" class="muted">No explanation run.</div>
            </div>

            <div class="card" id="analysisCard" style="display:none">
                <h2>Portal Analysis</h2>
                <div id="analysisContent" class="muted">No analysis run.</div>
            </div>
        </div>
    </div>

<script>
const ENV = 'HCM';
let currentPortal = '';
let treeMode = false;
let currentTreePortal = '';
let portalRootMap = {};

function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

async function api(path) {
    const res = await fetch(path);
    if (!res.ok) {
        const text = await res.text();
        setStatus(text || `Request failed with ${res.status}`);
        throw new Error(text);
    }
    return res.json();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function section(payload, name) {
    return (payload.sections || []).find(s => s.name === name) || {items: [], data: {}};
}

function firstValue(obj, keys) {
    for (const key of keys) {
        if (obj && obj[key] !== undefined && obj[key] !== null && String(obj[key]).trim() !== '') {
            return obj[key];
        }
    }
    return '';
}

function rowHtml(row, titleKeys, detailKeys, url) {
    const title = firstValue(row, titleKeys) || '(item)';
    const details = detailKeys
        .map(key => row[key] !== undefined && row[key] !== null && String(row[key]).trim() !== '' ? `${key}=${row[key]}` : '')
        .filter(Boolean)
        .join(' | ');
    const cls = url ? 'row clickable' : 'row';
    const click = url ? ` onclick="window.location.href='${url}'"` : '';
    return `<div class="${cls}"${click}><span class="title">${esc(title)}</span>${details ? `<span class="detail">${esc(details)}</span>` : ''}</div>`;
}

function adminUrl(type, name) {
    return `/admin/object/${encodeURIComponent(type)}/${encodeURIComponent(name)}`;
}

async function initPortalTree() {
    const portals = await api(`/api/peoplesoft/portal/portals?env=${ENV}`);
    if (!portals) return;
    const sel = document.getElementById('portalSelect');
    portals.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.portal_name;
        opt.textContent = `${p.portal_name} (${p.total} entries)`;
        sel.appendChild(opt);
        if (p.root_objname) portalRootMap[p.portal_name] = p.root_objname;
    });
}

function switchPortal() {
    const pn = document.getElementById('portalSelect').value;
    if (!pn) return;
    currentTreePortal = pn;
    if (!treeMode) toggleTreeMode();
    else renderTree(pn, portalRootMap[pn] || 'PORTAL_ROOT_OBJECT');
}

function toggleTreeMode() {
    treeMode = !treeMode;
    document.getElementById('results').style.display = treeMode ? 'none' : '';
    document.getElementById('treePanel').style.display = treeMode ? '' : 'none';
    document.getElementById('leftPanelTitle').textContent = treeMode ? 'Portal Tree' : 'Search Results';
    document.getElementById('btnTreeMode').textContent = treeMode ? 'Search' : 'Tree';
    if (treeMode && currentTreePortal) {
        renderTree(currentTreePortal, portalRootMap[currentTreePortal] || 'PORTAL_ROOT_OBJECT');
    }
}

async function renderTree(portalName, parentObjname, containerEl, depth = 0) {
    const panel = containerEl || document.getElementById('treePanel');
    if (depth === 0) panel.innerHTML = '<span class="muted">Loading...</span>';

    const rows = await api(`/api/peoplesoft/portal/folders?portal_name=${encodeURIComponent(portalName)}&parent=${encodeURIComponent(parentObjname)}&env=${ENV}`);
    if (!rows) { panel.innerHTML = '<span class="muted">Failed to load.</span>'; return; }
    if (depth === 0) panel.innerHTML = '';

    rows.forEach(r => {
        const isFolder = r.portal_reftype === 'F';
        const indent = depth * 14;
        const item = document.createElement('div');
        item.style.cssText = `padding:3px 4px 3px ${indent + 4}px;cursor:pointer;font-size:12px;border-bottom:1px solid #0d1a22;`;
        item.innerHTML = `<span style="color:${isFolder ? '#89b4fa' : '#cdd6f4'}">${isFolder ? '▶ ' : '• '}</span><span class="title" style="font-size:11px">${esc(r.portal_label || r.portal_objname)}</span> <span class="muted" style="font-size:10px">${esc(r.portal_objname)}</span>`;

        if (isFolder) {
            let expanded = false;
            let childContainer = null;
            item.onclick = async () => {
                if (!expanded) {
                    expanded = true;
                    item.querySelector('span:first-child').textContent = '▼ ';
                    childContainer = document.createElement('div');
                    item.after(childContainer);
                    await renderTree(portalName, r.portal_objname, childContainer, depth + 1);
                } else {
                    expanded = false;
                    item.querySelector('span:first-child').textContent = '▶ ';
                    if (childContainer) { childContainer.remove(); childContainer = null; }
                }
            };
        } else {
            item.onclick = () => loadPortal(r.portal_objname);
        }

        item.onmouseenter = () => item.style.background = '#0d1a22';
        item.onmouseleave = () => item.style.background = '';
        panel.appendChild(item);
    });

    if (rows.length === 0 && depth > 0) {
        const empty = document.createElement('div');
        empty.style.cssText = `padding:2px 4px 2px ${(depth + 1) * 14}px;font-size:11px;color:#6c7086;font-style:italic`;
        empty.textContent = '(empty)';
        panel.appendChild(empty);
    }
}

async function showAnalysis() {
    const pn = currentTreePortal || document.getElementById('portalSelect').value || 'EMPLOYEE';
    if (!pn) { alert('Select a portal first.'); return; }
    setStatus(`Analysing ${pn}...`);
    const d = await api(`/api/peoplesoft/portal/analysis?portal_name=${encodeURIComponent(pn)}&env=${ENV}`);
    if (!d) return;

    const card = document.getElementById('analysisCard');
    card.style.display = '';
    const counts = d.counts || {};
    const topComp = (d.top_components || []).slice(0, 10);

    document.getElementById('analysisContent').innerHTML = `
        <div style="margin-bottom:8px;font-size:12px">
            <b>Portal:</b> ${esc(pn)} &nbsp;
            <b>Folders:</b> ${counts['F'] || 0} &nbsp;
            <b>Content Refs:</b> ${counts['C'] || 0} &nbsp;
            <b>Orphans:</b> ${d.orphan_count || 0} &nbsp;
            <b>Empty Folders:</b> ${d.empty_folder_count || 0}
        </div>
        ${d.orphan_count > 0 ? `<details style="font-size:11px"><summary style="cursor:pointer;color:#f9e2af">Orphaned entries (${d.orphan_count})</summary>
            ${(d.orphans || []).map(r => `<div class="row">${esc(r.portal_objname)} → missing parent: ${esc(r.portal_prntobjname)}</div>`).join('')}</details>` : ''}
        ${d.empty_folder_count > 0 ? `<details style="font-size:11px"><summary style="cursor:pointer;color:#6c7086">Empty folders (${d.empty_folder_count})</summary>
            ${(d.empty_folders || []).map(r => `<div class="row">${esc(r.portal_label || r.portal_objname)}</div>`).join('')}</details>` : ''}
        ${topComp.length ? `<div style="font-size:11px;margin-top:8px"><b>Top Components:</b>
            ${topComp.map(r => `<div class="row clickable" onclick="window.location.href='/admin/component?name=${esc(r.component)}'">${esc(r.component)} <span class="muted">${r.ref_count} refs</span></div>`).join('')}</div>` : ''}
    `;
    setStatus(`Analysis complete for ${pn}.`);
}

async function searchPortal() {
    const q = document.getElementById('searchText').value.trim();
    if (!q) {
        setStatus('Enter portal search text.');
        return;
    }
    setStatus(`Searching for ${q}...`);
    const rows = await api(`/api/peoplesoft/search?env=${ENV}&q=${encodeURIComponent(q)}&limit=30`);
    const portals = rows.filter(row => row.type === 'portal_registry');
    const target = document.getElementById('results');
    if (!portals.length) {
        target.className = 'muted';
        target.textContent = 'No Portal Registry matches.';
        setStatus('No Portal Registry matches.');
        return;
    }
    target.className = '';
    target.innerHTML = portals.map(row =>
        rowHtml(row, ['name'], ['description'], `/admin/portal?portal=${encodeURIComponent(row.name)}`)
    ).join('');
    setStatus(`Found ${portals.length} Portal Registry object${portals.length === 1 ? '' : 's'}.`);
}

async function loadPortal(name) {
    const portal = (name || document.getElementById('portalName').value || '').trim();
    if (!portal) {
        setStatus('Enter PORTAL_OBJNAME.');
        return;
    }

    currentPortal = portal.toUpperCase();
    document.getElementById('portalName').value = currentPortal;
    document.getElementById('objectLink').href = adminUrl('portal_registry', currentPortal);
    setStatus(`Loading ${currentPortal}...`);

    const payload = await api(`/api/peoplesoft/object/portal_registry/${encodeURIComponent(currentPortal)}?env=${ENV}`);
    const overview = payload.overview || {};
    const def = section(payload, 'Definition').data || {};
    const crumbs = section(payload, 'Breadcrumbs').items || [];
    const children = section(payload, 'Children').items || [];
    const targets = section(payload, 'Target Components').items || [];
    const grants = section(payload, 'Portal Security').items || [];
    const paths = section(payload, 'Access Paths').items || [];

    document.getElementById('definition').innerHTML =
        rowHtml(def, ['portal_label', 'portal_objname'], ['portal_name', 'reference_type_label', 'uri', 'url', 'owner', 'lastupdoprid']);

    document.getElementById('counts').innerHTML = `
        <div class="counts">
            <div class="count"><span class="num">${esc(overview.children || 0)}</span>Children</div>
            <div class="count"><span class="num">${esc(overview.permissions || 0)}</span>Grants</div>
            <div class="count"><span class="num">${esc(overview.access_paths || 0)}</span>Access Paths</div>
            <div class="count"><span class="num">${esc(overview.permissionlists || 0)}</span>Permission Lists</div>
            <div class="count"><span class="num">${esc(overview.roles || 0)}</span>Roles</div>
            <div class="count"><span class="num">${esc(overview.operators || 0)}</span>Operators</div>
        </div>`;

    document.getElementById('breadcrumbs').innerHTML = crumbs.length
        ? `<div class="crumbs">${crumbs.map(row => `<span class="crumb"><a href="/admin/portal?portal=${encodeURIComponent(row.portal_objname)}">${esc(row.portal_label || row.portal_objname)}</a></span>`).join('')}</div>`
        : '<span class="muted">No breadcrumbs.</span>';

    document.getElementById('targets').innerHTML = targets.length
        ? targets.map(row => rowHtml(row, ['pnlgrpname'], ['descr', 'menu', 'market'], adminUrl('component', row.pnlgrpname))).join('')
        : '<span class="muted">No component target inferred.</span>';

    document.getElementById('children').innerHTML = children.length
        ? children.slice(0, 80).map(row => rowHtml(row, ['portal_label', 'portal_objname'], ['portal_reftype_label', 'portal_urltext'], `/admin/portal?portal=${encodeURIComponent(row.portal_objname)}`)).join('')
        : '<span class="muted">No children.</span>';

    document.getElementById('security').innerHTML = grants.length
        ? grants.map(row => rowHtml(row, ['portal_permname'], ['portal_permtype_label', 'portal_iscascade', 'inherited_from'], row.classid ? adminUrl('permissionlist', row.classid) : (row.rolename ? adminUrl('role', row.rolename) : null))).join('')
        : '<span class="muted">No portal grants.</span>';

    document.getElementById('accessPaths').innerHTML = paths.length
        ? paths.slice(0, 80).map(row => rowHtml(row, ['roleuser'], ['rolename', 'classid', 'path_type'], row.roleuser ? adminUrl('operator', row.roleuser) : null)).join('')
        : '<span class="muted">No expanded access paths.</span>';

    setStatus(`Loaded ${currentPortal}.`);
}

async function explainPortal() {
    const oprid = document.getElementById('oprid').value.trim();
    const portal = currentPortal || document.getElementById('portalName').value.trim();
    if (!oprid || !portal) {
        setStatus('Enter an OPRID and load a portal object.');
        return;
    }

    setStatus(`Explaining ${oprid} -> ${portal}...`);
    const result = await api(`/api/peoplesoft/security/explain-portal?env=${ENV}&oprid=${encodeURIComponent(oprid)}&portal=${encodeURIComponent(portal)}`);
    const target = document.getElementById('explain');
    const grants = result.grant_paths || [];
    target.className = '';
    target.innerHTML = `
        <div class="row">
            <span class="title">${result.has_access ? 'ACCESS GRANTED' : 'NO ACCESS'}</span>
            <span class="detail">${esc(result.oprid)} -> ${esc(result.portal_objname)} | matching grants=${grants.length}</span>
        </div>
        ${grants.length ? grants.map(row => rowHtml(row, ['portal_permname'], ['matched_by', 'portal_permtype_label', 'classid', 'rolename'])).join('') : ''}
    `;
    setStatus(`Explain complete: ${result.has_access ? 'access granted' : 'no access'}.`);
}

async function expandSubtree() {
    const portal = currentPortal || document.getElementById('portalName').value.trim();
    const portalName = currentTreePortal || document.getElementById('portalSelect').value || 'EMPLOYEE';
    if (!portal) {
        setStatus('Load a portal object first, then click Expand Subtree.');
        return;
    }
    setStatus(`Expanding subtree of ${portal}...`);
    const d = await api(`/api/peoplesoft/portal/subtree?env=${ENV}&portal_name=${encodeURIComponent(portalName)}&parent=${encodeURIComponent(portal)}&max_depth=6&max_rows=500`);
    if (!d) return;
    const items = d.items || [];
    const card = document.getElementById('subtreeCard');
    const panel = document.getElementById('subtreePanel');
    const countEl = document.getElementById('subtreeCount');
    card.style.display = '';
    countEl.textContent = `(${items.length} items)`;
    if (!items.length) {
        panel.innerHTML = '<span class="muted">No descendants found.</span>';
        setStatus('No subtree items found.');
        return;
    }
    const typeColor = {'F': '#89b4fa', 'C': '#a6e3a1'};
    panel.innerHTML = items.map(r => {
        const depth = Number(r.depth || 1);
        const indent = (depth - 1) * 14;
        const color = typeColor[String(r.portal_reftype||'').toUpperCase()] || '#cdd6f4';
        const label = esc(r.portal_label || r.portal_objname || '');
        const name = esc(r.portal_objname || '');
        const prefix = String(r.portal_reftype||'').toUpperCase() === 'F' ? '▶ ' : '• ';
        const url = String(r.portal_reftype||'').toUpperCase() === 'F'
            ? `/admin/portal?portal=${encodeURIComponent(r.portal_objname)}`
            : `/admin/portal?portal=${encodeURIComponent(r.portal_objname)}`;
        return `<div style="padding:2px 4px 2px ${indent+4}px;border-bottom:1px solid #0d1a22;cursor:pointer"
                     onclick="loadPortal('${name}')"
                     onmouseenter="this.style.background='#0d1a22'" onmouseleave="this.style.background=''">
                    <span style="color:${color}">${prefix}</span><span style="color:${color}">${label}</span>
                    <span style="color:#445;margin-left:6px;font-size:10px">${name}</span>
                </div>`;
    }).join('');
    setStatus(`Loaded subtree: ${items.length} descendants of ${portal}.`);
}

document.getElementById('searchText').addEventListener('keydown', event => {
    if (event.key === 'Enter') searchPortal();
});
document.getElementById('portalName').addEventListener('keydown', event => {
    if (event.key === 'Enter') loadPortal();
});
document.getElementById('oprid').addEventListener('keydown', event => {
    if (event.key === 'Enter') explainPortal();
});

(async function() {
    await initPortalTree();
    const params = new URLSearchParams(window.location.search);
    if (params.get('portal')) {
        loadPortal(params.get('portal'));
    }
    if (params.get('tree')) {
        const pn = params.get('tree');
        document.getElementById('portalSelect').value = pn;
        currentTreePortal = pn;
        toggleTreeMode();
    }
})();
</script>""")


@router.get("/metadata", response_class=HTMLResponse)
def admin_metadata():
    return _shell("Metadata Engine", "objects", content="""\
    <style>
        body {
            background: #050b12;
            color: #d7faff;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #00e5ff;
            text-shadow: 0 0 12px #00e5ff;
            letter-spacing: 4px;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(300px, 1fr));
            gap: 16px;
            align-items: start;
        }

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.4);
            padding: 20px;
            margin-top: 20px;
            background: rgba(0, 20, 30, .75);
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 14px;
            cursor: pointer;
            margin-right: 8px;
        }

        button:hover {
            background: #33eeff;
        }

        .row {
            border: 1px solid #1e5b66;
            padding: 10px;
            margin: 8px 0;
            background: rgba(5, 18, 28, .85);
        }

        .ok {
            color: #9ef7bd;
        }

        .warn {
            color: #ffd27d;
        }

        .bad {
            color: #ff8f8f;
        }

        .title {
            color: #00e5ff;
            font-weight: bold;
        }

        .detail {
            display: block;
            color: #b8dce2;
            font-size: 12px;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }

        .muted {
            color: #7faab2;
        }

        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: #b8dce2;
        }

        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
</style>
    <div class="card">
        <button onclick="loadMetadata()">Refresh</button>
        <button onclick="clearCache()">Clear Cache</button>
        <span id="status" class="muted">Loading metadata diagnostics...</span>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Version</h2>
            <div id="version" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Cache</h2>
            <div id="cache" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Capabilities</h2>
            <div id="capabilities" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Warnings</h2>
            <div id="warnings" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Object Types</h2>
            <div id="objectTypes" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Discovery</h2>
            <pre id="discovery">Loading...</pre>
        </div>
    </div>

<script>
const ENV = 'HCM';

async function api(path, options = {}) {
    const res = await fetch(path, options);

    if (res.status === 401) {
        window.location.reload();
        return;
    }

    if (!res.ok) {
        const msg = await res.text();
        setStatus(msg);
        throw new Error(msg);
    }

    return res.json();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function row(title, detail, cls = '') {
    const div = document.createElement('div');
    div.className = 'row';
    div.innerHTML = `
        <span class="title ${cls}">${title}</span>
        <span class="detail">${detail || ''}</span>
    `;
    return div;
}

function renderVersion(data) {
    const el = document.getElementById('version');
    el.innerHTML = '';
    el.appendChild(row('Oracle', data.oracle_version || 'Unavailable'));
    el.appendChild(row('PeopleTools', data.peopletools_version || 'Unavailable'));
    el.appendChild(row('Schema', JSON.stringify(data.schema || {})));
    el.appendChild(row('Adapter', `${data.version_adapter.adapter_key}: ${data.version_adapter.adapter.notes}`));
}

function renderCache(data) {
    const el = document.getElementById('cache');
    el.innerHTML = '';
    el.appendChild(row('TTL', `${data.ttl_seconds} seconds`));
    el.appendChild(row('Entries', data.entries.length));
    data.entries.forEach(entry => {
        el.appendChild(row(entry.key, `age=${entry.age_seconds}s expires=${entry.expires_in_seconds}s`));
    });
}

function renderCapabilities(data) {
    const el = document.getElementById('capabilities');
    el.innerHTML = '';
    data.capabilities.forEach(cap => {
        const cls = cap.supported ? 'ok' : 'bad';
        const detail = `table=${cap.table || 'n/a'} name_column=${cap.name_column || 'n/a'} page=${cap.object_page || 'n/a'}`;
        el.appendChild(row(`${cap.type}: ${cap.supported ? 'available' : 'missing'}`, detail, cls));
    });
}

function renderWarnings(warnings) {
    const el = document.getElementById('warnings');
    el.innerHTML = '';

    if (!warnings.length) {
        el.className = 'muted';
        el.textContent = 'No warnings.';
        return;
    }

    el.className = '';
    warnings.forEach(w => {
        el.appendChild(row(w.code || 'warning', w.message || JSON.stringify(w), 'warn'));
    });
}

function renderObjectTypes(data) {
    const el = document.getElementById('objectTypes');
    el.innerHTML = '';
    Object.keys(data).sort().forEach(type => {
        const item = data[type];
        el.appendChild(row(type, `${item.display_title} | ${item.graph_node_type} | ${item.object_page}`));
    });
}

async function clearCache() {
    await api('/api/metadata/cache/clear', {method: 'POST'});
    await loadMetadata();
}

async function loadMetadata() {
    setStatus('Loading metadata diagnostics...');
    const [version, capabilities, cache, objectTypes, discovery] = await Promise.all([
        api(`/api/metadata/version?env=${ENV}`),
        api(`/api/metadata/capabilities?env=${ENV}`),
        api('/api/metadata/cache'),
        api('/api/metadata/object-types'),
        api(`/api/metadata/discovery?env=${ENV}`)
    ]);

    renderVersion(version);
    renderCapabilities(capabilities);
    renderCache(cache);
    renderObjectTypes(objectTypes);
    renderWarnings([...(version.warnings || []), ...(capabilities.warnings || []), ...(discovery.warnings || [])]);
    document.getElementById('discovery').textContent = JSON.stringify(discovery, null, 2);
    setStatus('Metadata diagnostics loaded.');
}

loadMetadata();
</script>""")


@router.get("/graphdb", response_class=HTMLResponse)
def admin_graphdb():
    return _shell("Knowledge Graph", "graphdb", content="""\
    <style>
        body {
            background: #050b12;
            color: #d7faff;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        h1 {
            color: #00e5ff;
            text-shadow: 0 0 12px #00e5ff;
            letter-spacing: 4px;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        button, select, input {
            padding: 8px 12px;
            margin: 4px;
            border: 1px solid #00e5ff;
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
        }

        select, input {
            background: #0b1b24;
            color: white;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(300px, 1fr));
            gap: 16px;
            align-items: start;
        }

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.4);
            padding: 20px;
            margin-top: 20px;
            background: rgba(0, 20, 30, .75);
        }

        .row {
            border: 1px solid #1e5b66;
            padding: 10px;
            margin: 8px 0;
            background: rgba(5, 18, 28, .85);
        }

        .title {
            color: #00e5ff;
            font-weight: bold;
        }

        .detail {
            display: block;
            color: #b8dce2;
            font-size: 12px;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }

        .ok {
            color: #9ef7bd;
        }

        .warn {
            color: #ffd27d;
        }

        .muted {
            color: #7faab2;
        }

        pre {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: #b8dce2;
        }

        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
</style>
    <div class="card">
        <button onclick="buildGraph()">Rebuild Graph</button>
        <select id="buildLimit" title="Object limit per provider">
            <option value="50">limit: 50</option>
            <option value="250">limit: 250 (batch)</option>
            <option value="1000">limit: 1000 (batch)</option>
            <option value="2000">limit: 2000 (batch, full)</option>
        </select>
        <button onclick="clearGraph()">Clear Graph</button>
        <button onclick="compactGraph()">Compact</button>
        <button onclick="loadStats()">Refresh</button>
        <select id="exportFormat">
            <option value="json">JSON</option>
            <option value="graphml">GraphML</option>
            <option value="dot">DOT</option>
        </select>
        <button onclick="exportGraph()">Export</button>
        <span id="status" class="muted">Loading graph status...</span>
    </div>

    <div class="card">
        <h2>Snapshots</h2>
        <input id="snapshotName" placeholder="Snapshot name">
        <input id="snapshotNote" placeholder="Note" style="min-width:280px;">
        <button onclick="createSnapshot()">Create Snapshot</button>
        <button onclick="loadSnapshots()">Refresh Snapshots</button>
        <br>
        <select id="snapshotLeft" style="min-width:260px;"></select>
        <select id="snapshotRight" style="min-width:260px;"></select>
        <input id="snapshotTypes" placeholder="Node types filter" style="min-width:220px;">
        <button onclick="compareSnapshots()">Compare Snapshots</button>
        <div id="snapshots" class="muted">Loading snapshots...</div>
        <div id="snapshotDiff" class="muted">Select two snapshots to compare.</div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Stats</h2>
            <div id="stats" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Object Counts</h2>
            <div id="counts" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Providers</h2>
            <div id="providers" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Health</h2>
            <div id="health" class="muted">Loading...</div>
        </div>

        <div class="card">
            <h2>Graph Search</h2>
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
                <input id="searchText" placeholder="Search graph nodes" style="min-width:180px">
                <input id="searchTypeFilter" placeholder="type filter (e.g. component,record)" style="min-width:220px" title="Comma-separated node types to restrict search">
                <select id="searchLimit" title="Max results">
                    <option value="50">50 results</option>
                    <option value="100">100 results</option>
                    <option value="200">200 results</option>
                </select>
                <button onclick="searchGraph()">Search</button>
            </div>
            <div id="searchResults" class="muted">No search run.</div>
        </div>

        <div class="card">
            <h2>Raw Snapshot</h2>
            <pre id="raw">Loading...</pre>
        </div>
    </div>

<script>
const ENV = 'HCM';

async function api(path, options = {}) {
    const res = await fetch(path, options);

    if (res.status === 401) {
        window.location.reload();
        return;
    }

    if (!res.ok) {
        const msg = await res.text();
        setStatus(msg);
        throw new Error(msg);
    }

    return res.json();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function row(title, detail, cls = '') {
    const div = document.createElement('div');
    div.className = 'row';
    div.innerHTML = `<span class="title ${cls}">${title}</span><span class="detail">${detail || ''}</span>`;
    return div;
}

function renderStats(data) {
    const stats = document.getElementById('stats');
    stats.innerHTML = '';
    stats.className = '';
    stats.appendChild(row('Nodes', data.node_count));
    stats.appendChild(row('Edges', data.edge_count));
    stats.appendChild(row('Health', data.graph_health, data.graph_health === 'ok' ? 'ok' : 'warn'));
    stats.appendChild(row('Built At', data.built_at || 'Not built'));
    stats.appendChild(row('Build Time', `${data.build_seconds || 0}s`));
    stats.appendChild(row('Cache', JSON.stringify(data.cache_status || {})));

    const counts = document.getElementById('counts');
    counts.innerHTML = '';
    counts.className = '';
    Object.keys(data.object_counts || {}).sort().forEach(type => {
        counts.appendChild(row(type, data.object_counts[type]));
    });
    if (!counts.innerHTML) {
        counts.className = 'muted';
        counts.textContent = 'No object counts yet.';
    }

    const providers = document.getElementById('providers');
    providers.innerHTML = '';
    providers.className = '';
    (data.providers || []).forEach(provider => {
        providers.appendChild(row(provider.name, `${provider.status} | items=${provider.items} | ${provider.seconds}s ${provider.warning || ''}`, provider.status === 'ok' ? 'ok' : 'warn'));
    });
    if (!providers.innerHTML) {
        providers.className = 'muted';
        providers.textContent = 'No providers have run.';
    }

    const health = document.getElementById('health');
    health.innerHTML = '';
    health.className = '';
    health.appendChild(row('Warnings', data.warning_count));
    health.appendChild(row('Disconnected', data.disconnected_count, data.disconnected_count ? 'warn' : 'ok'));
    health.appendChild(row('Orphaned', data.orphaned_count, data.orphaned_count ? 'warn' : 'ok'));
    (data.warnings || []).slice(0, 20).forEach(w => {
        health.appendChild(row(w.code || 'warning', w.message || JSON.stringify(w), 'warn'));
    });

    document.getElementById('raw').textContent = JSON.stringify(data, null, 2);
}

async function loadStats() {
    setStatus('Loading graph stats...');
    const data = await api(`/api/graph/stats?env=${ENV}`);
    renderStats(data);
    setStatus('Graph stats loaded.');
}

async function buildGraph() {
    const limit = document.getElementById('buildLimit').value || '50';
    setStatus(`Building graph (limit=${limit})…`);
    const data = await api(`/api/graph/build?env=${ENV}&limit=${limit}&persist=true`);
    renderStats(data);
    setStatus(`Graph build complete (limit=${limit}).`);
}

async function clearGraph() {
    setStatus('Clearing graph...');
    const data = await api(`/api/graph/clear?env=${ENV}`, {method: 'POST'});
    renderStats(data);
    setStatus('Graph cleared.');
}

async function compactGraph() {
    setStatus('Compacting graph...');
    const data = await api(`/api/graph/compact?env=${ENV}`, {method: 'POST'});
    const msg = data.status === 'already_clean'
        ? `Graph already clean (${data.edges_after} edges, ${data.node_count} nodes).`
        : `Compacted: removed ${data.edges_removed} duplicate edges. ${data.edges_after} edges remaining.`;
    setStatus(msg);
    renderStats(await api(`/api/graph/stats?env=${ENV}`));
}

async function createSnapshot() {
    const name = document.getElementById('snapshotName').value.trim();
    const note = document.getElementById('snapshotNote').value.trim();
    setStatus('Creating graph snapshot...');
    const snap = await api(`/api/graph/snapshots?env=${ENV}&name=${encodeURIComponent(name)}&note=${encodeURIComponent(note)}`, {method: 'POST'});
    setStatus(`Snapshot created: ${snap.id}`);
    await loadSnapshots();
}

async function loadSnapshots() {
    const el = document.getElementById('snapshots');
    const left = document.getElementById('snapshotLeft');
    const right = document.getElementById('snapshotRight');
    el.innerHTML = '';
    el.className = '';
    const data = await api(`/api/graph/snapshots?env=${ENV}`);
    const snaps = data.snapshots || [];
    left.innerHTML = snaps.map(s => `<option value="${s.id}">${s.name} · ${s.created_at}</option>`).join('');
    right.innerHTML = snaps.map(s => `<option value="${s.id}">${s.name} · ${s.created_at}</option>`).join('');
    if (snaps.length > 1) {
        right.selectedIndex = 1;
    }
    if (!snaps.length) {
        el.className = 'muted';
        el.textContent = 'No snapshots yet.';
        return;
    }
    snaps.forEach(s => {
        const div = row(
            `${s.name} (${s.node_count} nodes / ${s.edge_count} edges)`,
            `${s.id} | created=${s.created_at || 'unknown'} | built=${s.built_at || 'not built'} | ${s.note || ''}`
        );
        const links = document.createElement('div');
        links.className = 'detail';
        links.innerHTML = `<a href="/api/graph/snapshots/${encodeURIComponent(s.id)}" target="_blank">Open JSON</a>
            &nbsp;·&nbsp; <a href="#" data-id="${s.id}">Delete</a>`;
        links.querySelector('a[data-id]').onclick = async event => {
            event.preventDefault();
            await deleteSnapshot(s.id);
        };
        div.appendChild(links);
        el.appendChild(div);
    });
}

async function compareSnapshots() {
    const left = document.getElementById('snapshotLeft').value;
    const right = document.getElementById('snapshotRight').value;
    const types = document.getElementById('snapshotTypes').value.trim();
    const target = document.getElementById('snapshotDiff');
    if (!left || !right) {
        target.className = 'muted';
        target.textContent = 'Create or select two snapshots first.';
        return;
    }
    setStatus('Comparing snapshots...');
    const data = await api(`/api/graph/snapshot-diff?snapshot1=${encodeURIComponent(left)}&snapshot2=${encodeURIComponent(right)}&node_types=${encodeURIComponent(types)}&limit=25`);
    const s = data.summary || {};
    target.className = '';
    target.innerHTML = '';
    [
        ['Nodes only left', s.only_in_env1_nodes || 0],
        ['Changed nodes', s.changed_nodes || 0],
        ['Nodes only right', s.only_in_env2_nodes || 0],
        ['Edges only left', s.only_in_env1_edges || 0],
        ['Changed edges', s.changed_edges || 0],
        ['Edges only right', s.only_in_env2_edges || 0],
    ].forEach(([title, detail]) => target.appendChild(row(title, detail)));
    [...(data.only_in_env1_nodes || []), ...(data.only_in_env2_nodes || [])].slice(0, 12).forEach(node => {
        target.appendChild(row(`${node.type}: ${node.name}`, node.id));
    });
    setStatus('Snapshot comparison complete.');
}

async function deleteSnapshot(id) {
    setStatus(`Deleting snapshot ${id}...`);
    await api(`/api/graph/snapshots/${encodeURIComponent(id)}`, {method: 'DELETE'});
    setStatus(`Snapshot deleted: ${id}`);
    await loadSnapshots();
}

function exportGraph() {
    const format = document.getElementById('exportFormat').value;
    window.location.href = `/api/graph/export?env=${ENV}&format=${encodeURIComponent(format)}`;
}

async function searchGraph() {
    const q = document.getElementById('searchText').value.trim();
    const typeFilter = document.getElementById('searchTypeFilter').value.trim();
    const limit = document.getElementById('searchLimit').value || '50';
    const target = document.getElementById('searchResults');

    if (!q) {
        target.className = 'muted';
        target.textContent = 'Enter search text.';
        return;
    }

    const params = new URLSearchParams({env: ENV, q, limit});
    if (typeFilter) params.set('node_types', typeFilter);
    const rows = await api(`/api/graph/search?${params}`);
    target.innerHTML = '';
    target.className = '';

    if (!rows.length) {
        target.className = 'muted';
        target.textContent = typeFilter
            ? `No graph nodes found matching '${q}' in types: ${typeFilter}.`
            : 'No graph nodes found.';
        return;
    }

    rows.forEach(node => {
        const div = row(`${node.type}: ${node.name}`, node.id);
        div.onclick = () => window.location.href = node.canonical_url;
        target.appendChild(div);
    });
}

document.getElementById('searchText').addEventListener('keydown', event => {
    if (event.key === 'Enter') searchGraph();
});

loadStats();
loadSnapshots();
</script>""")
