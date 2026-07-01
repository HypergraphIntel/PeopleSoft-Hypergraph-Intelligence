import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/tools", response_class=HTMLResponse)
def admin_tools():
    return _shell("Tools", "tools", env=False, content="""\
<style>
.tools-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;padding:20px;}
.tool-card{border:1px solid rgba(0,229,255,.2);background:rgba(0,20,30,.7);padding:0;}
.tool-card-head{padding:12px 16px;border-bottom:1px solid rgba(0,229,255,.1);display:flex;align-items:center;gap:10px;}
.tool-card-icon{font-size:20px;}
.tool-card-title{font-size:12px;font-weight:700;letter-spacing:1px;color:var(--cyan,#00e5ff);text-transform:uppercase;}
.tool-card-body{padding:14px 16px;}
.tool-card-body p{font-size:11px;color:#7faab2;line-height:1.55;margin:0 0 12px;}
.tool-link{display:block;padding:7px 10px;border:1px solid rgba(0,229,255,.2);color:#00e5ff;
           font-size:11px;margin-bottom:6px;text-decoration:none;background:rgba(0,229,255,.04);}
.tool-link:hover{background:rgba(0,229,255,.12);border-color:rgba(0,229,255,.5);}
.tool-link-ext::after{content:" ↗";opacity:.6;}
.build-row{display:flex;gap:6px;margin-top:8px;}
#buildStatus{font-size:11px;color:#7faab2;padding:4px 0;}
</style>

<div class="tools-grid">

  <!-- Tracing Config -->
  <div class="tool-card">
    <div class="tool-card-head">
      <span class="tool-card-icon">&#9881;</span>
      <span class="tool-card-title">Tracing Config</span>
    </div>
    <div class="tool-card-body">
      <p>View and update the active request tracing configuration. Controls which operations are traced and at what verbosity.</p>
      <a class="tool-link tool-link-ext" href="/api/tracing/config" target="_blank">View Tracing Config (JSON)</a>
      <a class="tool-link" href="/admin/tracing">&#9741; Transaction Tracing</a>
    </div>
  </div>

  <!-- Live Events -->
  <div class="tool-card">
    <div class="tool-card-head">
      <span class="tool-card-icon">&#9670;</span>
      <span class="tool-card-title">Live Events</span>
    </div>
    <div class="tool-card-body">
      <p>Server-sent event stream of real-time system events. Connect from a browser or curl to watch events as they happen.</p>
      <a class="tool-link tool-link-ext" href="/api/live/events" target="_blank">Open Live Event Stream</a>
    </div>
  </div>

  <!-- IB Nodes -->
  <div class="tool-card">
    <div class="tool-card-head">
      <span class="tool-card-icon">&#128279;</span>
      <span class="tool-card-title">IB Nodes</span>
    </div>
    <div class="tool-card-body">
      <p>Raw JSON listing of all Integration Broker nodes discovered across connected environments.</p>
      <a class="tool-link tool-link-ext" href="/api/ib/nodes" target="_blank">View IB Nodes (JSON)</a>
      <a class="tool-link" href="/admin/ib">&#127760; IB Explorer</a>
    </div>
  </div>

  <!-- Knowledge Graph Build -->
  <div class="tool-card">
    <div class="tool-card-head">
      <span class="tool-card-icon">&#9672;</span>
      <span class="tool-card-title">Knowledge Graph</span>
    </div>
    <div class="tool-card-body">
      <p>Trigger a full rebuild of the in-memory PeopleSoft knowledge graph for HCM or FSCM. Rebuilds are incremental when a prior graph exists.</p>
      <div class="build-row">
        <button onclick="buildGraph('HCM')">Build HCM Graph</button>
        <button onclick="buildGraph('FSCM')">Build FSCM Graph</button>
      </div>
      <div id="buildStatus"></div>
      <a class="tool-link" href="/admin/graphdb" style="margin-top:10px;">&#9672; Knowledge Graph Explorer</a>
    </div>
  </div>

  <!-- API Docs -->
  <div class="tool-card">
    <div class="tool-card-head">
      <span class="tool-card-icon">&#128218;</span>
      <span class="tool-card-title">API Docs</span>
    </div>
    <div class="tool-card-body">
      <p>Interactive Swagger UI for all DeathStar REST endpoints. Try out queries directly from the browser.</p>
      <a class="tool-link tool-link-ext" href="/docs" target="_blank">Open Swagger UI</a>
      <a class="tool-link tool-link-ext" href="/redoc" target="_blank">ReDoc Reference</a>
    </div>
  </div>

</div>

<script>
async function buildGraph(env) {
    const el = document.getElementById('buildStatus');
    el.textContent = `Building ${env} graph…`;
    try {
        const r = await fetch(`/api/graph/build?env=${encodeURIComponent(env)}`);
        const d = await r.json();
        el.textContent = `${env}: ${d.status || 'done'} — ${d.nodes ?? '?'} nodes, ${d.edges ?? '?'} edges`;
    } catch (e) {
        el.textContent = `Error: ${e.message}`;
    }
}
</script>""")

@router.get("/docs", response_class=HTMLResponse)
def admin_docs():
    return _shell("Documentation", "docs", env=False, content="""\
<div style="padding:32px;max-width:800px">
  <h2>API Reference</h2>
  <p style="color:var(--muted);font-size:12px;margin:6px 0 16px">Interactive OpenAPI documentation.</p>
  <div class="pe-actions">
    <a href="/docs" target="_blank">Swagger UI</a>
    <a href="/redoc" target="_blank">ReDoc</a>
  </div>
  <h2 style="margin-top:32px">Platform Reference</h2>
  <div class="pe-grid" style="margin-top:8px">
    <div class="pe-card">
      <span>Build Vertically</span>
      Every module follows: connector &rarr; API &rarr; UOM &rarr; graph &rarr; UI &rarr; search &rarr; navigation.
    </div>
    <div class="pe-card">
      <span>Safety Rules</span>
      Never crash on missing Oracle grants. Use ptmetadata.has_table() and return warnings. Keep SQL in connectors, routers thin.
    </div>
  </div>
</div>""")


@router.get("/reports", response_class=HTMLResponse)
def admin_reports():
    return _shell("Reports", "reports", content="""\
<style>
*{box-sizing:border-box}
.card{border:1px solid #00e5ff;box-shadow:0 0 12px rgba(0,229,255,.2);padding:16px;margin-bottom:16px;background:rgba(0,20,30,.75)}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:0 0 12px}
.report-btn{background:#0a1820;border:1px solid #00e5ff33;padding:10px 14px;cursor:pointer;text-align:left;color:#d7faff;font-size:12px;width:100%;margin-bottom:4px;transition:border-color .15s}
.report-btn:hover,.report-btn.active{border-color:#00e5ff;background:#0d2030}
.report-btn-title{color:#00e5ff;font-weight:bold;font-size:11px}
.cat-label{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#445;margin:14px 0 6px;border-top:1px solid #1e3040;padding-top:10px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:#00e5ff;text-align:left;padding:6px 8px;border-bottom:1px solid #1e3040;white-space:nowrap;font-size:11px}
td{padding:5px 8px;border-bottom:1px solid #0d1a22;vertical-align:top;font-size:11px}
tr:hover td{background:#0a1820}
a{color:#00e5ff;text-decoration:none} a:hover{text-decoration:underline}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;padding:5px 12px;cursor:pointer;font-size:11px}
.muted{color:#556;font-style:italic}
</style>
<div style="display:flex;gap:20px;align-items:flex-start">
  <div style="width:260px;flex-shrink:0">
    <div class="card">
      <h2>Report Catalog</h2>
      <div id="catalog" class="muted">Loading...</div>
    </div>
  </div>
  <div style="flex:1;min-width:0">
    <div id="reportPanel" class="card" style="display:none">
      <h2 id="reportTitle">Report</h2>
      <div id="reportNote" style="font-size:11px;color:#445;margin-bottom:10px"></div>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
        <input id="rowFilter" type="text" placeholder="Filter results..." style="width:220px" oninput="filterRows()">
        <span id="rowCount" style="font-size:11px;color:#445"></span>
        <button class="sec" onclick="exportCsv()" style="margin-left:auto">Export CSV</button>
      </div>
      <div id="reportTable"></div>
    </div>
    <div id="emptyState" class="card" style="color:#445;text-align:center;padding:40px">
      Select a report from the catalog.
    </div>
  </div>
</div>
<script>
const ENV=localStorage.getItem('dsEnv')||'HCM';
let _key=null,_allRows=[],_cols=[];
async function api(p){const r=await fetch(p);return r.ok?r.json():null;}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
const LINKS={rolename:n=>'/admin/object/role/'+n,roleuser:n=>'/admin/object/operator/'+n,
  oprid:n=>'/admin/object/operator/'+n,classid:n=>'/admin/object/permissionlist/'+n,
  pnlgrpname:n=>'/admin/object/component/'+n,recname:n=>'/admin/object/record/'+n,
  ae_applid:n=>'/admin/object/application_engine/'+n,menuname:n=>'/admin/object/menu/'+n};
async function loadCatalog(){
  const cat=await api('/api/peoplesoft/reports/catalog?env='+ENV);
  if(!cat){document.getElementById('catalog').textContent='Failed.';return;}
  const by={};cat.forEach(r=>{by[r.category]=by[r.category]||[];by[r.category].push(r);});
  let h='';['security','objects','system'].forEach(c=>{
    if(!by[c]||!by[c].length)return;
    h+='<div class="cat-label">'+c+'</div>';
    by[c].forEach(r=>{h+='<button class="report-btn" id="rb_'+esc(r.key)+'" onclick="runReport(\''+esc(r.key)+'\',\''+esc(r.title)+'\')" title="'+esc(r.title)+'"><div class="report-btn-title">'+esc(r.title)+'</div></button>';});
  });
  document.getElementById('catalog').innerHTML=h;
}
async function runReport(key,title){
  document.querySelectorAll('.report-btn').forEach(b=>b.classList.remove('active'));
  const btn=document.getElementById('rb_'+key);if(btn)btn.classList.add('active');
  document.getElementById('reportPanel').style.display='';
  document.getElementById('emptyState').style.display='none';
  document.getElementById('reportTitle').textContent=title+' — '+ENV;
  document.getElementById('reportTable').innerHTML='<span class="muted">Running...</span>';
  document.getElementById('rowFilter').value='';_key=key;
  const data=await api('/api/peoplesoft/reports?report='+encodeURIComponent(key)+'&env='+ENV+'&limit=500');
  if(!data){document.getElementById('reportTable').innerHTML='<span class="muted">Error.</span>';return;}
  document.getElementById('reportNote').textContent=data.note||'';
  _allRows=data.rows||[];_cols=data.columns||[];
  document.getElementById('rowCount').textContent=_allRows.length+' rows';
  renderTable(_allRows);
}
function renderTable(rows){
  if(!rows.length){document.getElementById('reportTable').innerHTML='<span class="muted">No rows returned.</span>';return;}
  let h='<table><thead><tr>'+_cols.map(c=>'<th>'+esc(c.toUpperCase().replace(/_/g,' '))+'</th>').join('')+'</tr></thead><tbody>';
  rows.forEach(r=>{h+='<tr>'+_cols.map(c=>{const v=r[c],s=v===null||v===undefined?'':String(v);const lf=LINKS[c];return'<td>'+(lf&&s.trim()?'<a href="'+esc(lf(s.trim()))+'?env='+ENV+'">'+esc(s)+'</a>':esc(s))+'</td>';}).join('')+'</tr>';});
  h+='</tbody></table>';document.getElementById('reportTable').innerHTML=h;
}
function filterRows(){const q=document.getElementById('rowFilter').value.toLowerCase();const f=q?_allRows.filter(r=>_cols.some(c=>String(r[c]||'').toLowerCase().includes(q))):_allRows;document.getElementById('rowCount').textContent=f.length+'/'+_allRows.length+' rows';renderTable(f);}
function exportCsv(){if(!_allRows.length)return;const q=document.getElementById('rowFilter').value.toLowerCase();const rows=q?_allRows.filter(r=>_cols.some(c=>String(r[c]||'').toLowerCase().includes(q))):_allRows;const lines=[_cols.join(',')].concat(rows.map(r=>_cols.map(c=>JSON.stringify(r[c]??'')).join(',')));const blob=new Blob([lines.join('\n')],{type:'text/csv'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(_key||'report')+'_'+ENV+'.csv';a.click();}
loadCatalog();
</script>""")


@router.get("/impact", response_class=HTMLResponse)
def admin_impact():
    return _shell("Impact Forecasting", "impact", noscroll=False, content="""\
<style>
*{box-sizing:border-box;}
.ctrl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
input[type=text]{width:300px;}
button{background:#00e5ff;border:none;padding:4px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
.section-head{font-size:11px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;color:#00e5ff;
              margin:18px 0 8px;border-bottom:1px solid #00e5ff22;padding-bottom:4px;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;
   font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #0e2030;padding:5px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.risk-low{color:#00cc66;font-weight:bold;}
.risk-medium{color:#ffdd55;font-weight:bold;}
.risk-high{color:#ff9900;font-weight:bold;}
.risk-critical{color:#ff4444;font-weight:bold;}
.stat-grid{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;}
.stat-box{border:1px solid #00e5ff22;padding:10px 16px;min-width:120px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:22px;font-weight:bold;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.bar-bg{background:#0a1a24;border-radius:2px;height:6px;width:120px;display:inline-block;vertical-align:middle;}
.bar-fill{height:100%;background:#00e5ff;border-radius:2px;}
.spinner{display:none;color:#00e5ff;font-size:11px;margin-left:8px;}
.spinner.on{display:inline;}
</style>
<div style="padding:16px;">

<!-- ── Environment Risk Assessment ─────────────────────────────────────── -->
<div class="section-head" style="margin-top:0">Environment Risk Assessment</div>
<div class="ctrl">
  <label style="font-size:11px;color:#7faab2">Env 1</label>
  <select id="riskEnv1"><option>HCM</option><option>FSCM</option></select>
  <label style="font-size:11px;color:#7faab2">Env 2</label>
  <select id="riskEnv2"><option value="FSCM">FSCM</option><option>HCM</option></select>
  <button onclick="runRisk()">Assess Risk</button>
  <span class="spinner" id="riskSpinner">&#9679;&#9679;&#9679;</span>
</div>
<div id="riskResult"></div>

<!-- ── Project Impact Analysis ─────────────────────────────────────────── -->
<div class="section-head">Project Impact Analysis (KG-based)</div>
<div class="ctrl">
  <label style="font-size:11px;color:#7faab2">Env</label>
  <select id="impEnv"><option>HCM</option><option>FSCM</option></select>
  <input id="impProject" type="text" placeholder="Project name (e.g. GPIT_HR92_OBJECTS)" onkeydown="if(event.key==='Enter')runImpact()">
  <button onclick="runImpact()">Analyze Impact</button>
  <span class="spinner" id="impSpinner">&#9679;&#9679;&#9679;</span>
</div>
<div id="impResult"></div>
</div>
<script>
const $ = id => document.getElementById(id);
function esc(s){return String(s==null?'—':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function riskCls(label){
  const m={None:'risk-low',Low:'risk-low',Medium:'risk-medium',High:'risk-high',Critical:'risk-critical'};
  return m[label]||'';
}

// ── Risk Assessment ────────────────────────────────────────────────────────
async function runRisk(){
  const e1=$('riskEnv1').value, e2=$('riskEnv2').value;
  $('riskSpinner').classList.add('on');
  $('riskResult').innerHTML='';
  try{
    const r=await fetch(`/api/impact/risk?env1=${e1}&env2=${e2}`);
    const d=await r.json();
    $('riskSpinner').classList.remove('on');
    renderRisk(d);
  }catch(e){
    $('riskSpinner').classList.remove('on');
    $('riskResult').innerHTML=`<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderRisk(d){
  if(d.error){$('riskResult').innerHTML=`<div class="err-msg">${esc(d.error)}</div>`;return;}
  const rc=riskCls(d.risk_label);
  let h=`<div class="stat-grid">
    <div class="stat-box"><div class="stat-num ${rc}">${esc(d.risk_label)}</div><div class="stat-lbl">Overall Risk</div></div>
    <div class="stat-box"><div class="stat-num">${d.risk_score}</div><div class="stat-lbl">Risk Score</div></div>
    <div class="stat-box"><div class="stat-num">${(d.type_risks||[]).filter(r=>r.contribution>0).length}</div><div class="stat-lbl">Drifted Types</div></div>
    <div class="stat-box"><div class="stat-num" style="font-size:14px">${esc(d.data_source||'')}</div><div class="stat-lbl">Data Source</div></div>
  </div>`;

  const rows=(d.type_risks||[]).filter(r=>r.contribution>0);
  if(rows.length){
    const maxC=Math.max(...rows.map(r=>r.contribution),1);
    h+='<table><tr><th>Object Type</th><th>Drift Level</th><th style="text-align:right">Delta</th><th style="text-align:right">Weight</th><th>Risk Contribution</th></tr>';
    rows.forEach(r=>{
      const pct=Math.round((r.contribution/maxC)*100);
      const dc=r.drift_level==='Major'?'risk-critical':r.drift_level==='Significant'?'risk-high':r.drift_level==='Moderate'?'risk-medium':'';
      const sign=r.delta>0?'+':'';
      h+=`<tr>
        <td>${esc(r.type)}</td>
        <td><span class="${dc}">${esc(r.drift_level)}</span></td>
        <td style="text-align:right;font-family:monospace">${sign}${r.delta.toLocaleString()}</td>
        <td style="text-align:right">${r.weight}&times;</td>
        <td><div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div> ${r.contribution}</td>
      </tr>`;
    });
    h+='</table>';
  } else {
    h+='<div class="empty">No drift detected — environments are in sync.</div>';
  }
  $('riskResult').innerHTML=h;
}

// ── Project Impact ─────────────────────────────────────────────────────────
async function runImpact(){
  const env=$('impEnv').value;
  const proj=($('impProject').value||'').trim().toUpperCase();
  if(!proj)return;
  $('impSpinner').classList.add('on');
  $('impResult').innerHTML='';
  try{
    const r=await fetch(`/api/impact/project?env=${env}&project=${encodeURIComponent(proj)}`);
    const d=await r.json();
    $('impSpinner').classList.remove('on');
    renderImpact(d);
  }catch(e){
    $('impSpinner').classList.remove('on');
    $('impResult').innerHTML=`<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderImpact(d){
  if(d.error){
    $('impResult').innerHTML=`<div class="err-msg">${esc(d.error)}</div>`;return;
  }
  let h='';
  (d.warnings||[]).forEach(w=>{h+=`<div class="warn-msg">&#9888; ${esc(w)}</div>`;});

  const riskCl=riskCls(d.risk_label);
  h+=`<div class="stat-grid">
    <div class="stat-box"><div class="stat-num">${(d.total_items||0).toLocaleString()}</div><div class="stat-lbl">Project Items</div></div>
    <div class="stat-box"><div class="stat-num">${(d.traversed_count||0).toLocaleString()}</div><div class="stat-lbl">KG Nodes Analyzed</div></div>
    <div class="stat-box"><div class="stat-num">${(d.total_affected_nodes||0).toLocaleString()}</div><div class="stat-lbl">Downstream Affected</div></div>
    <div class="stat-box"><div class="stat-num ${riskCl}">${esc(d.risk_label||'?')}</div><div class="stat-lbl">KG Risk Level</div></div>
  </div>`;

  if(d.graph_built_at){
    h+=`<div style="font-size:10px;color:#445;margin-bottom:8px">Knowledge graph built: ${esc(d.graph_built_at.substring(0,19))}</div>`;
  }

  // Affected node types
  const affected=d.affected_summary||[];
  if(affected.length){
    const maxCount=Math.max(...affected.map(a=>a.count),1);
    h+='<div class="section-head">Downstream Impact by Type</div>';
    h+='<table><tr><th>Node Type</th><th style="text-align:right">Affected</th><th>Distribution</th></tr>';
    affected.forEach(a=>{
      const pct=Math.round((a.count/maxCount)*100);
      h+=`<tr>
        <td>${esc(a.label||a.type)}</td>
        <td style="text-align:right;font-family:monospace">${a.count.toLocaleString()}</td>
        <td><div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div></td>
      </tr>`;
    });
    h+='</table>';
  } else {
    h+='<div class="empty">No downstream KG impact found. The graph may not cover this project\'s objects yet — use the Tools page to rebuild the graph with higher coverage.</div>';
  }

  // Top impacted objects
  const top=d.top_impacted_objects||[];
  if(top.length){
    h+='<div class="section-head">Most Impactful Project Objects</div>';
    h+='<table><tr><th>Object</th><th>Type</th><th style="text-align:right">Downstream Nodes</th></tr>';
    top.slice(0,30).forEach(o=>{
      h+=`<tr>
        <td class="mono">${esc(o.name)}</td>
        <td>${esc(o.kg_type)}</td>
        <td style="text-align:right">${o.affected_count.toLocaleString()}</td>
      </tr>`;
    });
    h+='</table>';
  }

  // Project item breakdown
  const breakdown=d.item_breakdown||[];
  if(breakdown.length){
    h+='<div class="section-head">Project Contents</div>';
    h+='<table><tr><th>Object Type</th><th style="text-align:right">Count</th><th>KG Coverage</th></tr>';
    breakdown.forEach(b=>{
      const mapped=b.mapped_to_kg?'<span style="color:#00cc66">&#10003; mapped</span>':'<span style="color:#334">not mapped</span>';
      h+=`<tr><td>${esc(b.label)}</td><td style="text-align:right">${(b.count||0).toLocaleString()}</td><td>${mapped}</td></tr>`;
    });
    h+='</table>';
  }

  $('impResult').innerHTML=h;
}

// Auto-load risk on page open
runRisk();
</script>""")

