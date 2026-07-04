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
const LINKS={rolename:n=>'/admin/role/'+n,roleuser:n=>'/admin/operator/'+n,
  oprid:n=>'/admin/operator/'+n,classid:n=>'/admin/permissionlist/'+n,
  pnlgrpname:n=>'/admin/component?name='+encodeURIComponent(n),recname:n=>'/admin/record/'+n,
  ae_applid:n=>'/admin/ae?q='+encodeURIComponent(n),menuname:n=>'/admin/object/menu/'+n};
async function loadCatalog(){
  const cat=await api('/api/peoplesoft/reports/catalog?env='+ENV);
  if(!cat){document.getElementById('catalog').textContent='Failed.';return;}
  const by={};cat.forEach(r=>{by[r.category]=by[r.category]||[];by[r.category].push(r);});
  let h='';['security','objects','system'].forEach(c=>{
    if(!by[c]||!by[c].length)return;
    h+='<div class="cat-label">'+c+'</div>';
    by[c].forEach(r=>{h+='<button class="report-btn" id="rb_'+esc(r.key)+'" data-key="'+esc(r.key)+'" data-title="'+esc(r.title)+'" onclick="runReport(this.dataset.key,this.dataset.title)" title="'+esc(r.title)+'"><div class="report-btn-title">'+esc(r.title)+'</div></button>';});
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
function exportCsv(){if(!_allRows.length)return;const q=document.getElementById('rowFilter').value.toLowerCase();const rows=q?_allRows.filter(r=>_cols.some(c=>String(r[c]||'').toLowerCase().includes(q))):_allRows;const lines=[_cols.join(',')].concat(rows.map(r=>_cols.map(c=>JSON.stringify(r[c]??'')).join(',')));const blob=new Blob([lines.join('\\n')],{type:'text/csv'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(_key||'report')+'_'+ENV+'.csv';a.click();}
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
function esc(s){return String(s==null?'\u2014':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function riskCls(label){
  const m={None:'risk-low',Low:'risk-low',Medium:'risk-medium',High:'risk-high',Critical:'risk-critical'};
  return m[label]||'';
}

// --- Risk Assessment ---
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
    h+='<div class="empty">No drift detected \u2014 environments are in sync.</div>';
  }
  $('riskResult').innerHTML=h;
}

// --- Project Impact ---
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
    h+='<div class="empty">No downstream KG impact found. The graph may not cover this project\\'s objects yet \u2014 use the Tools page to rebuild the graph with higher coverage.</div>';
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


_EXAMPLE_PROMPTS = [
    "Where is employee termination implemented?",
    "Which AE programs touch the JOB record?",
    "Who has access to the JOB_DATA component in HCM?",
    "What PeopleCode fires on the PERSONAL_DATA record?",
    "Show me the SQL definition HR_GET_SETID",
    "What does the GPUS_TAX_CALC AE program do?",
    "What components depend on the EMPLOYMENT record?",
    "Compare object counts between HCM and FSCM",
    "Show me active user sessions",
    "How many users are currently using HCM?",
]


@router.get("/assistant", response_class=HTMLResponse)
def admin_assistant():
    examples_js = json.dumps(_EXAMPLE_PROMPTS)
    return _shell("AI Assistant", "assistant", env=False, noscroll=True, content=f"""\
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{{box-sizing:border-box;}}
.chat-layout{{display:flex;height:calc(100vh - 90px);gap:0;}}
.chat-sidebar{{width:220px;flex-shrink:0;border-right:1px solid rgba(0,229,255,.15);
  padding:12px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;}}
.sidebar-head{{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#445;margin-bottom:4px;}}
.example-btn{{background:none;border:1px solid rgba(0,229,255,.15);color:#7faab2;
  font-size:10px;padding:6px 8px;cursor:pointer;text-align:left;line-height:1.4;
  transition:border-color .15s,color .15s;}}
.example-btn:hover{{border-color:rgba(0,229,255,.4);color:#d7faff;}}
.provider-badge{{margin-top:auto;padding:8px;border:1px solid rgba(0,229,255,.12);
  font-size:10px;color:#445;line-height:1.6;}}
.provider-name{{color:#00e5ff;font-weight:bold;}}
.chat-main{{flex:1;display:flex;flex-direction:column;min-width:0;}}
.chat-messages{{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;}}
.msg{{display:flex;flex-direction:column;gap:4px;max-width:92%;}}
.msg-user{{align-self:flex-end;}}
.msg-assistant{{align-self:flex-start;width:100%;max-width:100%;}}
.msg-bubble{{padding:10px 14px;font-size:12px;line-height:1.6;border-radius:2px;}}
.msg-user .msg-bubble{{background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.25);color:#d7faff;}}
.msg-assistant .msg-bubble{{background:rgba(10,26,36,.8);border:1px solid rgba(0,229,255,.1);color:#c8e8f0;}}
.msg-assistant .msg-bubble p{{margin:0 0 6px;}}
.msg-assistant .msg-bubble ul,.msg-assistant .msg-bubble ol{{margin:4px 0 6px;padding-left:18px;}}
.msg-assistant .msg-bubble li{{margin:2px 0;}}
.msg-assistant .msg-bubble strong{{color:#d7faff;}}
.msg-assistant .msg-bubble code{{background:#0b2030;border:1px solid #00e5ff22;padding:1px 4px;font-size:11px;}}
.msg-assistant .msg-bubble pre{{background:#060f18;border:1px solid #00e5ff22;padding:8px;overflow-x:auto;}}
.msg-assistant .msg-bubble pre code{{background:none;border:none;padding:0;}}
.msg-assistant .msg-bubble h1,.msg-assistant .msg-bubble h2,.msg-assistant .msg-bubble h3{{color:#00e5ff;font-size:12px;margin:8px 0 4px;text-transform:uppercase;letter-spacing:1px;}}
.tool-block{{border:1px solid rgba(0,229,255,.12);background:#060f18;margin:4px 0;}}
.tool-head{{display:flex;align-items:center;gap:8px;padding:5px 10px;cursor:pointer;
  user-select:none;font-size:10px;color:#445;}}
.tool-head:hover{{color:#7faab2;}}
.tool-name{{color:#00e5ff;font-family:monospace;font-size:11px;}}
.tool-body{{display:none;padding:8px 10px;border-top:1px solid rgba(0,229,255,.08);}}
.tool-body.open{{display:block;}}
.tool-json{{font-family:monospace;font-size:10px;color:#7faab2;white-space:pre-wrap;
  max-height:200px;overflow-y:auto;}}
.tool-table{{width:100%;border-collapse:collapse;font-size:10px;margin-top:4px;}}
.tool-table th{{color:#445;text-transform:uppercase;letter-spacing:.8px;font-size:9px;
  border-bottom:1px solid #0a2030;padding:3px 6px;text-align:left;}}
.tool-table td{{padding:3px 6px;border-bottom:1px solid #06111a;color:#7faab2;vertical-align:top;}}
.tool-table tr:hover td{{background:#060f18;}}
.tool-table td.msg-cell{{color:#c8e8f0;max-width:500px;word-break:break-word;}}
.tool-table td.err-cell{{color:#ff8888;}}
.tool-table td.warn-cell{{color:#ffcc66;}}
.tool-table td.ts-cell{{color:#445;white-space:nowrap;font-family:monospace;}}
.tool-table td.cnt-cell{{color:#00e5ff;font-weight:bold;text-align:right;}}
.tool-summary{{font-size:10px;color:#445;padding:4px 0 2px;}}
.tool-note{{color:#ffaa00;font-size:10px;padding:4px 0;font-style:italic;}}
.thinking{{color:#445;font-size:11px;font-style:italic;padding:6px 14px;}}
.chat-input-bar{{padding:12px 16px;border-top:1px solid rgba(0,229,255,.15);
  display:flex;gap:8px;align-items:flex-end;}}
textarea#chatInput{{flex:1;background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;
  padding:8px 10px;font-size:12px;resize:none;min-height:42px;max-height:140px;
  font-family:inherit;line-height:1.5;}}
textarea#chatInput:focus{{outline:none;border-color:rgba(0,229,255,.6);}}
#sendBtn{{background:#00e5ff;border:none;padding:8px 18px;cursor:pointer;
  font-size:12px;color:#000;font-weight:bold;height:42px;flex-shrink:0;}}
#sendBtn:hover{{background:#33eeff;}}
#sendBtn:disabled{{background:#0a2030;color:#334;cursor:default;}}
.err-bubble{{background:#1a0000;border:1px solid #ff4444;color:#ff6666;
  padding:8px 12px;font-size:11px;}}
/* Object link style — cyan dotted underline */
a.obj-link{{color:#00e5ff;text-decoration:none;border-bottom:1px dotted rgba(0,229,255,.5);
  cursor:pointer;transition:border-bottom-style .1s;}}
a.obj-link:hover{{border-bottom-style:solid;}}
/* SQL Proxy masked-token reveal chip — the AI only ever sees the masked form */
.token-chip{{display:inline-block;font-family:monospace;font-size:11px;padding:1px 6px;
  border-radius:3px;background:rgba(255,180,0,.12);border:1px solid rgba(255,180,0,.4);
  color:#ffb400;cursor:pointer;user-select:none;}}
.token-chip:hover{{background:rgba(255,180,0,.22);}}
.token-chip-revealed{{background:rgba(0,204,102,.12);border-color:rgba(0,204,102,.4);color:#00cc66;}}
</style>

<div class="chat-layout">

  <!-- Sidebar: examples + provider badge -->
  <div class="chat-sidebar">
    <div class="sidebar-head">Example questions</div>
    <div id="exampleList"></div>
    <div class="provider-badge" id="providerBadge">Loading provider…</div>
  </div>

  <!-- Main chat area -->
  <div class="chat-main">
    <div class="chat-messages" id="chatMessages"></div>
    <div class="chat-input-bar">
      <textarea id="chatInput" rows="1" placeholder="Ask anything about your PeopleSoft environments…"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();sendMessage();}}"></textarea>
      <button id="sendBtn" onclick="sendMessage()">Send</button>
    </div>
  </div>

</div>
<script>
const EXAMPLES = {examples_js};
const chatMessages = document.getElementById('chatMessages');
const chatInput    = document.getElementById('chatInput');
const sendBtn      = document.getElementById('sendBtn');
let conversationHistory = [];

// Configure marked for safe inline rendering
if (typeof marked !== 'undefined') {{
  marked.setOptions({{ breaks: true, gfm: true }});
}}
function renderMarkdown(text) {{
  if (typeof marked !== 'undefined') return marked.parse(text);
  // Minimal fallback if CDN unavailable (avoid backslash escapes in f-string)
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/[*][*](.+?)[*][*]/g,'<strong>$1</strong>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .split(String.fromCharCode(10)).join('<br>');
}}

// ── Tool result rendering ─────────────────────────────────────────────────────

function esc(s) {{
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function toolSummary(tool, input, result) {{
  if (!result) return '';
  switch(tool) {{
    case 'log_errors':
      return `${{result.count || 0}} error group(s)`;
    case 'log_search':
      const wa = (result.web||[]).length + (result.app||[]).length;
      return `${{wa}} entries`;
    case 'session_log_chain':
      return `${{(result.web||[]).length}} web · ${{(result.app||[]).length}} app`;
    case 'active_sessions':
      return `${{(result.recently_active||[]).length}} active · ${{(result.recent_users||[]).length}} recent`;
    case 'search_objects':
      return `${{result.count || 0}} result(s)`;
    case 'environment_health': {{
      const v = result.verdict || '';
      return v || `${{(result.checks||[]).length}} checks`;
    }}
    case 'ib_diagnostics':
      return `${{(result.nodes||[]).length}} nodes · ${{(result.failed_transactions||[]).length}} failed txn(s)`;
    case 'process_scheduler_health': {{
      const srvs = result.scheduler_servers || [];
      const online = srvs.filter(s => s.status === 'ONLINE').length;
      return `${{online}}/${{srvs.length}} servers online`;
    }}
    default:
      return '';
  }}
}}

function renderToolResult(tool, input, result) {{
  if (!result) return '<div class="tool-note">No result</div>';
  if (result.error) return `<div class="tool-note" style="color:#ff6666">${{esc(result.error)}}</div>`;
  if (result.note && !result.groups && !result.web && !result.app) {{
    return `<div class="tool-note">${{esc(result.note)}}</div>`;
  }}

  let h = '';

  // ── log_errors ──────────────────────────────────────────────────────────────
  if (tool === 'log_errors') {{
    const groups = result.groups || [];
    if (!groups.length) return `<div class="tool-note">${{esc(result.note || 'No errors found')}}</div>`;
    h += `<div class="tool-summary">${{esc(result.count)}} error group(s) in ${{esc(result.env)}}</div>`;
    h += '<table class="tool-table"><thead><tr>'
       + '<th>#</th><th>Source</th><th>Error Code</th><th>Object</th>'
       + '<th>Users</th><th>Last Seen</th><th>Recent Message</th></tr></thead><tbody>';
    for (const g of groups) {{
      const sample = (g.sample_messages || [])[0];
      const msg = sample ? (sample.message || '').slice(0, 120) : '';
      const levelCls = (sample && sample.level === 'ERROR') ? 'err-cell' : (sample && sample.level === 'WARNING') ? 'warn-cell' : '';
      h += `<tr>
        <td class="cnt-cell">${{esc(g.cnt)}}</td>
        <td>${{esc((g.source_name || sample?.source_name || ''))}}</td>
        <td style="font-family:monospace;color:#ffaa00">${{esc(g.error_code || '—')}}</td>
        <td style="color:#00e5ff">${{esc(g.object_ref || '—')}}</td>
        <td>${{esc(g.oprids_sample || '')}}</td>
        <td class="ts-cell">${{esc((g.last_seen||'').slice(0,16))}}</td>
        <td class="msg-cell ${{levelCls}}">${{esc(msg)}}</td>
      </tr>`;
      // Show remaining sample messages as sub-rows
      for (const sm of (g.sample_messages || []).slice(1)) {{
        const smMsg = (sm.message || '').slice(0, 120);
        h += `<tr style="opacity:.6"><td colspan="6" style="padding-left:24px;font-size:9px;color:#334">${{esc(sm.ts||'').slice(0,16)}} · ${{esc(sm.oprid||'')}}</td>`
           + `<td class="msg-cell">${{esc(smMsg)}}</td></tr>`;
      }}
    }}
    h += '</tbody></table>';
    return h;
  }}

  // ── log_search ──────────────────────────────────────────────────────────────
  if (tool === 'log_search') {{
    const rows = [...(result.web||[]), ...(result.app||[])].sort((a,b) => (b.ts||'') < (a.ts||'') ? -1 : 1);
    if (!rows.length) return `<div class="tool-note">${{esc(result.note || 'No log entries found')}}</div>`;
    h += `<div class="tool-summary">${{rows.length}} entries</div>`;
    h += '<table class="tool-table"><thead><tr><th>Time</th><th>Level</th><th>Source</th><th>OPRID</th><th>Message</th></tr></thead><tbody>';
    for (const r of rows.slice(0, 50)) {{
      const lev = (r.level || '').toUpperCase();
      const levCls = lev === 'ERROR' || lev === 'SEVERE' ? 'err-cell' : lev === 'WARNING' || lev === 'WARN' ? 'warn-cell' : '';
      h += `<tr>
        <td class="ts-cell">${{esc((r.ts||'').slice(0,16))}}</td>
        <td class="${{levCls}}">${{esc(lev || r.status || '')}}</td>
        <td style="font-size:9px">${{esc(r.source_name||'')}}</td>
        <td style="color:#00e5ff">${{esc(r.oprid||'')}}</td>
        <td class="msg-cell">${{esc((r.message||r.url||r.raw||'').slice(0,140))}}</td>
      </tr>`;
    }}
    if (rows.length > 50) h += `<tr><td colspan="5" class="tool-note">… ${{rows.length - 50}} more rows</td></tr>`;
    h += '</tbody></table>';
    return h;
  }}

  // ── session_log_chain ───────────────────────────────────────────────────────
  if (tool === 'session_log_chain') {{
    const all = [
      ...(result.web||[]).map(r => ({{...r, _tier:'web'}})),
      ...(result.app||[]).map(r => ({{...r, _tier:'app'}})),
    ].sort((a,b) => (b.ts||'') < (a.ts||'') ? -1 : 1);
    if (!all.length) return `<div class="tool-note">${{esc(result.note || 'No entries found')}}</div>`;
    h += `<div class="tool-summary">Session chain for ${{esc(result.oprid)}} · ${{all.length}} entries</div>`;
    h += '<table class="tool-table"><thead><tr><th>Time</th><th>Tier</th><th>Level</th><th>Message</th></tr></thead><tbody>';
    for (const r of all.slice(0, 60)) {{
      const lev = (r.level || '').toUpperCase();
      const levCls = lev === 'ERROR' || lev === 'SEVERE' ? 'err-cell' : lev === 'WARNING' ? 'warn-cell' : '';
      h += `<tr>
        <td class="ts-cell">${{esc((r.ts||'').slice(0,16))}}</td>
        <td style="color:#556;font-size:9px">${{r._tier === 'web' ? 'WEB' : 'APP'}}</td>
        <td class="${{levCls}}">${{esc(lev)}}</td>
        <td class="msg-cell ${{levCls}}">${{esc((r.message||r.url||r.raw||'').slice(0,160))}}</td>
      </tr>`;
    }}
    h += '</tbody></table>';
    return h;
  }}

  // ── active_sessions ─────────────────────────────────────────────────────────
  if (tool === 'active_sessions') {{
    const active  = result.recently_active || [];
    const recent  = result.recent_users    || [];
    if (active.length) {{
      h += `<div class="tool-summary" style="color:#00cc66">${{active.length}} user(s) active now</div>`;
      h += '<table class="tool-table"><thead><tr><th>OPRID</th><th>Last Request</th><th>Page</th></tr></thead><tbody>';
      for (const u of active) {{
        h += `<tr>
          <td style="color:#00cc66;font-weight:bold">${{esc(u.oprid)}}</td>
          <td class="ts-cell">${{esc((u.logindttm||u.last_login||'').slice(0,16))}}</td>
          <td style="font-size:9px">${{esc(u.pnlgrpname||'')}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (recent.length) {{
      h += `<div class="tool-summary" style="margin-top:6px">${{recent.length}} recent user(s)</div>`;
      h += '<table class="tool-table"><thead><tr><th>OPRID</th><th>Sessions</th><th>Last Seen</th></tr></thead><tbody>';
      for (const u of recent.slice(0,20)) {{
        h += `<tr>
          <td style="color:#7faab2">${{esc(u.oprid)}}</td>
          <td class="cnt-cell">${{esc(u.session_count)}}</td>
          <td class="ts-cell">${{esc((u.last_login||'').slice(0,16))}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (!active.length && !recent.length) return '<div class="tool-note">No active sessions</div>';
    return h;
  }}

  // ── search_objects ───────────────────────────────────────────────────────────
  if (tool === 'search_objects') {{
    const results = result.results || [];
    if (!results.length) return '<div class="tool-note">No objects found</div>';
    h += '<table class="tool-table"><thead><tr><th>Name</th><th>Type</th><th>Description</th></tr></thead><tbody>';
    for (const r of results.slice(0,20)) {{
      h += `<tr>
        <td style="color:#00e5ff;font-family:monospace">${{esc(r.name||r.id)}}</td>
        <td style="color:#556">${{esc(r.type||'')}}</td>
        <td class="msg-cell">${{esc((r.descr||r.description||r.label||'').slice(0,80))}}</td>
      </tr>`;
    }}
    h += '</tbody></table>';
    return h;
  }}

  // ── environment_health ──────────────────────────────────────────────────────
  if (tool === 'environment_health') {{
    const checks = result.checks || [];
    const verdict = result.verdict || '';
    const verdictColor = verdict.includes('OFFLINE') ? '#ff4444'
                       : verdict.includes('DEGRADED') || verdict.includes('UNHEALTHY') ? '#ffaa00'
                       : '#00cc66';
    h += `<div class="tool-summary" style="color:${{verdictColor}};font-weight:bold">${{esc(verdict)}}</div>`;
    if (checks.length) {{
      h += '<table class="tool-table"><thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead><tbody>';
      for (const c of checks) {{
        const sc = c.status === 'UP' || c.status === 'OK' ? '#00cc66'
                 : c.status === 'DOWN' || c.status === 'ERROR' ? '#ff4444'
                 : c.status === 'SPIKE' || c.status === 'DEGRADED' ? '#ff8800'
                 : '#ffaa00';
        h += `<tr>
          <td style="font-family:monospace;color:#7faab2">${{esc(c.name)}}</td>
          <td style="color:${{sc}};font-weight:bold">${{esc(c.status)}}</td>
          <td class="msg-cell">${{esc(c.detail||'')}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (result.active_users && result.active_users.length) {{
      h += `<div class="tool-note" style="margin-top:4px">Active users: ${{esc(result.active_users.join(', '))}}</div>`;
    }}
    if (result.recommendation) {{
      h += `<div class="tool-note" style="color:#ffaa00;margin-top:4px">⚠ ${{esc(result.recommendation)}}</div>`;
    }}
    return h;
  }}

  // ── ib_diagnostics ──────────────────────────────────────────────────────────
  if (tool === 'ib_diagnostics') {{
    const nodes = result.nodes || [];
    const domains = result.domains || [];
    const txns = result.failed_transactions || [];
    if (nodes.length) {{
      h += `<div class="tool-summary">IB Nodes (${{nodes.length}})</div>`;
      h += '<table class="tool-table"><thead><tr><th>Node</th><th>Active</th><th>Type</th><th>Local</th><th>URL</th></tr></thead><tbody>';
      for (const n of nodes) {{
        const ac = (n.active||'').toLowerCase();
        const acColor = ac === 'active' || ac === 'yes' || ac === '1' ? '#00cc66' : '#ff6666';
        h += `<tr>
          <td style="color:#00e5ff;font-family:monospace">${{esc(n.name||'')}}</td>
          <td style="color:${{acColor}}">${{esc(n.active||'')}}</td>
          <td style="font-size:9px">${{esc(n.type||'')}}</td>
          <td style="color:#556">${{esc(n.local||'')}}</td>
          <td class="msg-cell" style="font-size:9px">${{esc((n.target_url||'').slice(0,60))}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (domains.length) {{
      h += `<div class="tool-summary" style="margin-top:6px">IB Domains</div>`;
      h += '<table class="tool-table"><thead><tr><th>Domain</th><th>Status</th><th>Detail</th></tr></thead><tbody>';
      for (const d of domains) {{
        h += `<tr>
          <td style="color:#7faab2">${{esc(d.msgnodename||d.ibnodename||d.domain_name||JSON.stringify(d))}}</td>
          <td>${{esc(d.domain_status||'')}}</td>
          <td class="msg-cell" style="font-size:9px">${{esc(d.status_description||d.remarks||'')}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (txns.length) {{
      h += `<div class="tool-summary" style="margin-top:6px;color:#ff8800">${{txns.length}} Failed Transaction(s)</div>`;
      h += '<table class="tool-table"><thead><tr><th>Operation</th><th>Pub→Sub</th><th>Status</th><th>Error</th></tr></thead><tbody>';
      for (const t2 of txns.slice(0, 15)) {{
        h += `<tr>
          <td style="font-family:monospace;font-size:9px">${{esc(t2.operation||'')}}</td>
          <td style="font-size:9px">${{esc(t2.pub_node||'')}} → ${{esc(t2.sub_node||'')}}</td>
          <td style="color:#ff6666">${{esc(String(t2.status||''))}}</td>
          <td class="msg-cell err-cell">${{esc((t2.error||'').slice(0,120))}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (!nodes.length && !domains.length && !txns.length) return '<div class="tool-note">No IB data returned</div>';
    return h;
  }}

  // ── process_scheduler_health ─────────────────────────────────────────────────
  if (tool === 'process_scheduler_health') {{
    const counts = result.status_counts || {{}};
    const servers = result.scheduler_servers || [];
    const failures = result.recent_failures || [];
    if (result.verdict) {{
      const vc = result.verdict.includes('OFFLINE') ? '#ff4444' : '#ffaa00';
      h += `<div class="tool-summary" style="color:${{vc}};font-weight:bold">${{esc(result.verdict)}}</div>`;
    }}
    if (Object.keys(counts).length) {{
      h += '<table class="tool-table"><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>';
      for (const [st, cnt] of Object.entries(counts)) {{
        const sc = st === 'Error' ? 'err-cell' : st === 'Cancelled' || st === 'Hold' ? 'warn-cell' : '';
        h += `<tr><td class="${{sc}}">${{esc(st)}}</td><td class="cnt-cell">${{esc(cnt)}}</td></tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (servers.length) {{
      h += `<div class="tool-summary" style="margin-top:6px">Scheduler Servers</div>`;
      h += '<table class="tool-table"><thead><tr><th>Server</th><th>Status</th><th>Last Seen</th><th>Workers</th></tr></thead><tbody>';
      for (const s of servers) {{
        const sc2 = s.status === 'ONLINE' ? '#00cc66' : s.status === 'STALE' ? '#ffaa00' : '#ff4444';
        const ago = s.minutes_ago != null ? `${{s.minutes_ago}}m ago` : s.last_seen || '';
        h += `<tr>
          <td style="font-family:monospace">${{esc(s.name||'')}}</td>
          <td style="color:${{sc2}};font-weight:bold">${{esc(s.status||'')}}</td>
          <td class="ts-cell">${{esc(ago)}}</td>
          <td class="cnt-cell">${{esc(s.workers||'')}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (failures.length) {{
      h += `<div class="tool-summary" style="margin-top:6px;color:#ff8800">${{failures.length}} Recent Failure(s)</div>`;
      h += '<table class="tool-table"><thead><tr><th>Instance</th><th>Process</th><th>OPRID</th><th>End Time</th></tr></thead><tbody>';
      for (const f of failures.slice(0,10)) {{
        h += `<tr>
          <td class="cnt-cell">${{esc(f.prcsinstance||'')}}</td>
          <td style="font-family:monospace;font-size:9px">${{esc(f.prcsname||'')}}</td>
          <td style="color:#00e5ff">${{esc(f.oprid||'')}}</td>
          <td class="ts-cell">${{esc(String(f.enddttm||f.begindttm||'').slice(0,16))}}</td>
        </tr>`;
      }}
      h += '</tbody></table>';
    }}
    if (!Object.keys(counts).length && !servers.length) return '<div class="tool-note">No scheduler data returned</div>';
    return h;
  }}

  // ── fallback: collapsible JSON ───────────────────────────────────────────────
  return `<div class="tool-json">${{esc(JSON.stringify({{input, result}}, null, 2))}}</div>`;
}}

// ── Link map builder — extracts named objects from tool_log ──────────────────
function buildLinkMap(toolLog) {{
  const links = {{}};  // name → {{url, title}}

  // Object-type → URL path segment mapping
  const typeToPath = {{
    'record':              (n,e) => `/admin/record/${{n}}?env=${{e}}`,
    'component':           (n,e) => `/admin/component?name=${{n}}&env=${{e}}`,
    'page':                (n,e) => `/admin/page?name=${{n}}&env=${{e}}`,
    'application_engine':  (n,e) => `/admin/ae?q=${{n}}&env=${{e}}`,
    'sql_definition':      (n,e) => `/admin/object/sql_definition/${{n}}?env=${{e}}`,
    'peoplecode':          (n,e) => `/admin/peoplecode/${{n}}?env=${{e}}`,
    'field':               (n,e) => `/admin/field/${{n}}?env=${{e}}`,
    'menu':                (n,e) => `/admin/menu/${{n}}?env=${{e}}`,
    'role':                (n,e) => `/admin/role/${{n}}`,
    'permissionlist':      (n,e) => `/admin/permissionlist/${{n}}?env=${{e}}`,
    'query':               (n,e) => `/admin/query?name=${{n}}&env=${{e}}`,
  }};

  function addObj(name, type, env) {{
    if (!name || name.length < 2) return;
    const fn = typeToPath[type];
    if (fn) links[name] = {{ url: fn(name, env || 'HCM'), title: type.replace('_',' ') }};
  }}
  function addRecord(name, env) {{
    if (!name || name.length < 2) return;
    links[name] = {{ url: `/admin/record/${{name}}?env=${{env||'HCM'}}`, title: 'Record' }};
  }}
  function addComponent(name, env) {{
    if (!name || name.length < 2) return;
    links[name] = {{ url: `/admin/component?name=${{name}}&env=${{env||'HCM'}}`, title: 'Component' }};
  }}
  function addRole(name) {{
    if (!name || name.length < 2) return;
    links[name] = {{ url: `/admin/role/${{name}}`, title: 'Role / Permission List' }};
  }}
  function addOprid(oprid, env) {{
    if (!oprid || oprid.length < 1) return;
    links[oprid] = {{ url: `/admin/tracing?oprid=${{encodeURIComponent(oprid)}}&env=${{env||'HCM'}}`, title: 'Transaction Tracing' }};
  }}

  if (!toolLog) return links;

  for (const t of toolLog) {{
    const env = (t.input && t.input.env) || 'HCM';
    const res = t.result || {{}};

    switch (t.tool) {{
      case 'active_sessions':
        for (const u of [...(res.recent_users||[]), ...(res.currently_active||[])]) {{
          addOprid(u.oprid, env);
          if (u.oprclass) addRole(u.oprclass);
        }}
        break;

      case 'search_objects':
        for (const r of (res.results||[])) {{
          if (r.name && r.type) addObj(r.name, r.type, env);
        }}
        break;

      case 'record_usage':
        if (t.input && t.input.record) addRecord(t.input.record, env);
        for (const c of (res.components||[]))               addComponent(c, env);
        for (const c of (res.search_record_components||[])) addComponent(c, env);
        for (const r of (res.records_inheriting_fields||[])) addRecord(r, env);
        for (const ae of (res.ae_state_programs||[]))        addObj(ae, 'application_engine', env);
        break;

      case 'who_has_access':
        if (t.input && t.input.component) addComponent(t.input.component, env);
        for (const g of (res.access_grants||[])) {{
          if (g.classid) addRole(g.classid);
        }}
        break;

      case 'graph_impact':
      case 'graph_dependencies': {{
        const summary = res.impact_summary || res.dependency_summary || {{}};
        for (const [type, names] of Object.entries(summary)) {{
          for (const n of (names||[])) addObj(n, type, env);
        }}
        break;
      }}

      case 'ae_steps':
        if (t.input && t.input.ae_name) addObj(t.input.ae_name, 'application_engine', env);
        break;

      case 'sql_lookup':
        if (t.input && t.input.sqlid) addObj(t.input.sqlid, 'sql_definition', env);
        break;

      case 'peoplecode_search':
        for (const r of (res.results||[])) {{
          const prog = r.programname || r.program_name || r.objectvalue1;
          if (prog) addObj(prog, 'peoplecode', env);
          // recname often present in result rows
          if (r.recname) addRecord(r.recname, env);
        }}
        break;

      case 'project_impact':
        if (t.input && t.input.project) {{
          links[t.input.project] = {{ url: `/admin/project?name=${{t.input.project}}&env=${{env}}`, title: 'Project' }};
        }}
        for (const obj of (res.top_impacted_objects||[])) {{
          if (obj.name && obj.type) addObj(obj.name, obj.type, env);
        }}
        break;

      case 'log_errors':
        for (const g of (res.groups||[])) {{
          for (const sm of (g.sample_messages||[])) {{
            if (sm.oprid) addOprid(sm.oprid, env);
          }}
          if (g.oprids_sample) {{
            String(g.oprids_sample).split(',').forEach(op => addOprid(op.trim(), env));
          }}
        }}
        break;

      case 'log_search':
        for (const r of [...(res.web||[]), ...(res.app||[])]) {{
          if (r.oprid) addOprid(r.oprid, env);
          if (r.component) addComponent(r.component, env);
        }}
        break;

      case 'session_log_chain':
        if (t.input && t.input.oprid) addOprid(t.input.oprid, env);
        for (const r of [...(res.web||[]), ...(res.app||[])]) {{
          if (r.component) addComponent(r.component, env);
        }}
        break;

      case 'environment_health':
        for (const u of (res.active_users||[])) addOprid(u, env);
        break;

      case 'ib_diagnostics':
        for (const n of (res.nodes||[])) {{
          if (n.name) links[n.name] = {{ url: `/admin/ib/node/${{n.name}}?env=${{env}}`, title: 'IB Node' }};
        }}
        for (const tx of (res.failed_transactions||[])) {{
          if (tx.pub_node) links[tx.pub_node] = {{ url: `/admin/ib/node/${{tx.pub_node}}?env=${{env}}`, title: 'IB Node' }};
          if (tx.sub_node) links[tx.sub_node] = {{ url: `/admin/ib/node/${{tx.sub_node}}?env=${{env}}`, title: 'IB Node' }};
        }}
        break;

      case 'process_scheduler_health':
        for (const f of (res.recent_failures||[])) {{
          if (f.oprid) addOprid(f.oprid, env);
        }}
        break;
    }}
  }}
  return links;
}}

// ── Text-node walker — wraps matched names in <a> tags ───────────────────────
function applyLinks(rootEl, linkMap) {{
  const names = Object.keys(linkMap);
  if (!names.length) return;

  // Sort longest first so JOB_DATA matches before JOB
  names.sort((a,b) => b.length - a.length);

  // PeopleSoft names are pure [A-Z0-9_$] — no regex escaping needed.
  // Use lookaround to avoid partial matches (e.g. JOB inside JOB_DATA).
  const pattern = new RegExp('(?<![A-Z0-9_$])(' + names.join('|') + ')(?![A-Z0-9_$])', 'g');

  // Walk text nodes, skip inside <a>, <code>, <pre>
  const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, {{
    acceptNode(node) {{
      const p = node.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (p.closest('a,code,pre')) return NodeFilter.FILTER_REJECT;
      if (!node.textContent.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }}
  }});

  const nodes = [];
  let n;
  while ((n = walker.nextNode())) nodes.push(n);

  for (const textNode of nodes) {{
    const text = textNode.textContent;
    pattern.lastIndex = 0;
    if (!pattern.test(text)) continue;
    pattern.lastIndex = 0;

    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = pattern.exec(text)) !== null) {{
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const info = linkMap[m[1]];
      const a = document.createElement('a');
      a.className = 'obj-link';
      a.href = info.url;
      a.target = '_blank';
      a.title = info.title;
      a.textContent = m[1];
      frag.appendChild(a);
      last = m.index + m[1].length;
    }}
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    textNode.parentNode.replaceChild(frag, textNode);
  }}
}}

// ── SQL Proxy: masked-token reveal chips ─────────────────────────────────────
// The AI only ever sees masked tokens like EMP_9a41c2f0 (connectors/sqlmask.py);
// this turns any such token appearing in a chat response into a clickable chip
// a human can decode back to the real value via /api/sql-proxy/reveal — the AI
// itself has no path to that endpoint.
const TOKEN_PATTERN = /\\b(EMP|USER|PERSON|EMAIL|PHONE|ADDR|SSN|DOB|ACCT|DEPT|VENDOR|STUDENT|CUSTOMER|POS)_([0-9a-f]{{8}})\\b/g;

function applyTokenReveal(rootEl) {{
  const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, {{
    acceptNode(node) {{
      const p = node.parentElement;
      if (!p) return NodeFilter.FILTER_REJECT;
      if (p.closest('.token-chip')) return NodeFilter.FILTER_REJECT;
      if (!node.textContent) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }}
  }});
  const nodes = [];
  let n;
  while ((n = walker.nextNode())) nodes.push(n);

  for (const textNode of nodes) {{
    const text = textNode.textContent;
    TOKEN_PATTERN.lastIndex = 0;
    if (!TOKEN_PATTERN.test(text)) continue;
    TOKEN_PATTERN.lastIndex = 0;

    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = TOKEN_PATTERN.exec(text)) !== null) {{
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const chip = document.createElement('span');
      chip.className = 'token-chip';
      const tokenText = m[0];
      chip.textContent = tokenText;
      chip.title = 'Click to reveal (masked from AI)';
      chip.onclick = () => revealToken(chip, tokenText);
      frag.appendChild(chip);
      last = m.index + m[0].length;
    }}
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    textNode.parentNode.replaceChild(frag, textNode);
  }}
}}

async function revealToken(chipEl, token) {{
  if (chipEl.dataset.revealed) {{
    chipEl.classList.toggle('token-chip-open');
    return;
  }}
  chipEl.textContent = 'decoding…';
  try {{
    const r = await fetch('/api/sql-proxy/reveal', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{token}}),
    }});
    if (!r.ok) {{ chipEl.textContent = token + ' (not found)'; return; }}
    const d = await r.json();
    chipEl.textContent = d.real_value;
    chipEl.title = `${{token}} — revealed`;
    chipEl.dataset.revealed = '1';
    chipEl.classList.add('token-chip-revealed', 'token-chip-open');
  }} catch(e) {{
    chipEl.textContent = token + ' (error)';
  }}
}}

// ── Examples ──────────────────────────────────────────────────────────────────
const el = document.getElementById('exampleList');
EXAMPLES.forEach(ex => {{
  const b = document.createElement('button');
  b.className = 'example-btn';
  b.textContent = ex;
  b.onclick = () => {{ chatInput.value = ex; chatInput.focus(); }};
  el.appendChild(b);
}});

// ── Provider badge ────────────────────────────────────────────────────────────
(async () => {{
  try {{
    const r = await fetch('/api/assistant/status');
    const d = await r.json();
    const p = d.active_provider || '?';
    const pCfg = d[p] || {{}};
    const model = pCfg.model || '';
    const keyOk = pCfg.api_key !== 'missing';
    const badge = document.getElementById('providerBadge');
    badge.innerHTML = `<span class="provider-name">${{p.toUpperCase()}}</span><br>
      Model: ${{model}}<br>
      Key: ${{keyOk ? '&#10003; configured' : '<span style="color:#ff6666">&#10005; missing</span>'}}`;
  }} catch(e) {{
    document.getElementById('providerBadge').textContent = 'Provider unknown';
  }}
}})();

// ── Chat ──────────────────────────────────────────────────────────────────────
function appendMsg(role, content, toolLog) {{
  const wrap = document.createElement('div');
  wrap.className = `msg msg-${{role}}`;

  if (toolLog && toolLog.length) {{
    toolLog.forEach(t => {{
      const blk  = document.createElement('div');
      blk.className = 'tool-block';
      const head = document.createElement('div');
      head.className = 'tool-head';
      const summary = toolSummary(t.tool, t.input, t.result);
      head.innerHTML = `<span>&#9654;</span><span class="tool-name">${{t.tool}}</span>`
        + (summary ? `<span style="margin-left:8px;color:#556;font-size:9px">${{summary}}</span>` : '')
        + `<span style="margin-left:auto;font-size:9px;color:#334">expand</span>`;
      const body = document.createElement('div');
      body.className = 'tool-body';
      body.innerHTML = renderToolResult(t.tool, t.input, t.result);
      head.onclick = () => body.classList.toggle('open');
      blk.appendChild(head);
      blk.appendChild(body);
      wrap.appendChild(blk);
    }});
  }}

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (role === 'assistant' && content) {{
    bubble.innerHTML = renderMarkdown(content);
    // Build link map from what the AI actually fetched, then annotate the text
    const linkMap = buildLinkMap(toolLog);
    if (Object.keys(linkMap).length) applyLinks(bubble, linkMap);
    applyTokenReveal(bubble);
  }} else {{
    bubble.textContent = content;
  }}

  wrap.appendChild(bubble);
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}}

function appendThinking() {{
  const d = document.createElement('div');
  d.className = 'thinking';
  d.id = 'thinking';
  d.textContent = 'Thinking…';
  chatMessages.appendChild(d);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}}

function removeThinking() {{
  const t = document.getElementById('thinking');
  if (t) t.remove();
}}

async function sendMessage() {{
  const text = (chatInput.value || '').trim();
  if (!text) return;
  chatInput.value = '';
  sendBtn.disabled = true;

  appendMsg('user', text, null);
  conversationHistory.push({{ role: 'user', content: text }});
  appendThinking();

  try {{
    const r = await fetch('/api/assistant/chat', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ messages: conversationHistory, stream: false }}),
    }});
    removeThinking();
    if (!r.ok) {{
      const e = await r.json();
      const d = document.createElement('div');
      d.className = 'err-bubble';
      d.textContent = e.detail || 'Request failed';
      chatMessages.appendChild(d);
    }} else {{
      const d = await r.json();
      appendMsg('assistant', d.content, d.tool_log);
      conversationHistory.push({{ role: 'assistant', content: d.content }});
    }}
  }} catch(e) {{
    removeThinking();
    const d = document.createElement('div');
    d.className = 'err-bubble';
    d.textContent = String(e);
    chatMessages.appendChild(d);
  }}

  sendBtn.disabled = false;
  chatInput.focus();
}}

chatInput.addEventListener('input', () => {{
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
}});
</script>""")

