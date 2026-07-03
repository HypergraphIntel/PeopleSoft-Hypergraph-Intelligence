"""
SQR Source Artifact Explorer — admin UI.

Routes:
  GET /admin/sqr            — list/search all programs
  GET /admin/sqr/{filename} — program detail (tables, includes, procedures)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from routers.admin._core import _shell, _ESC_JS

router = APIRouter(prefix="/admin", tags=["DeathStar Admin"])


def _badge(text: str, color: str = "#0af") -> str:
    return (f'<span style="display:inline-block;padding:1px 7px;border-radius:10px;'
            f'font-size:10px;font-weight:700;background:{color}22;color:{color};'
            f'border:1px solid {color}44">{text}</span>')


@router.get("/sqr/analytics", response_class=HTMLResponse)
def sqr_analytics():
    content = """
<style>
.an-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
@media(max-width:900px){.an-grid{grid-template-columns:1fr}}
.an-card{background:#0a1520;border:1px solid #1a3a4a;border-radius:8px;padding:16px}
.an-card h3{margin:0 0 12px;color:#00e5ff;font-size:13px;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px}
.an-tbl{width:100%;border-collapse:collapse;font-size:12px}
.an-tbl th{text-align:left;padding:4px 8px;border-bottom:1px solid #1a3a4a;
  color:#7faab2;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.an-tbl td{padding:4px 8px;border-bottom:1px solid #0e2030}
.an-tbl tr:hover td{background:#0a1f2e}
.an-tbl a{color:#00e5ff;text-decoration:none}
.an-tbl a:hover{text-decoration:underline}
.bar-wrap{width:100%;background:#0e2030;border-radius:2px;height:6px;margin-top:2px}
.bar-fill{height:6px;border-radius:2px;background:#00e5ff}
.stat-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.stat-box{background:#0a1520;border:1px solid #1a3a4a;border-radius:6px;padding:8px 16px;min-width:110px}
.stat-val{font-size:22px;font-weight:700;color:#00e5ff}
.stat-lbl{font-size:10px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px}
.rel-chip{display:inline-block;padding:1px 6px;border-radius:10px;font-size:9px;font-weight:700;
  margin-left:3px;vertical-align:middle}
</style>

<a href="/admin/sqr" style="color:#7faab2;font-size:12px;text-decoration:none;margin-bottom:14px;display:inline-block">← SQR Explorer</a>
<div class="stat-row" id="statRow">
  <div class="stat-box"><div class="stat-val" id="sTot">—</div><div class="stat-lbl">Programs</div></div>
  <div class="stat-box"><div class="stat-val" id="sTbl">—</div><div class="stat-lbl">PS_ Tables</div></div>
  <div class="stat-box"><div class="stat-val" id="sRef">—</div><div class="stat-lbl">Table Refs</div></div>
  <div class="stat-box"><div class="stat-val" id="sInc">—</div><div class="stat-lbl">Includes</div></div>
</div>

<div id="analyticsContent"><div style="color:#7faab2;padding:24px">Loading analytics…</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
async function load() {
  const [statsRes, anRes] = await Promise.all([
    fetch('/api/sqr/stats'),
    fetch('/api/sqr/analytics'),
  ]);
  const stats = await statsRes.json();
  const an = await anRes.json();

  $('sTot').textContent = stats.programs ?? '—';
  $('sTbl').textContent = stats.distinct_ps_tables ?? '—';
  $('sRef').textContent = stats.total_table_refs ?? '—';
  $('sInc').textContent = stats.total_includes ?? '—';

  renderAnalytics(an);
}

function barPct(val, max) {
  const pct = max > 0 ? Math.round(val / max * 100) : 0;
  return `<div class="bar-wrap"><div class="bar-fill" style="width:${pct}%"></div></div>`;
}

function renderAnalytics(an) {
  const topTbls = an.top_tables || [];
  const topProgs = an.top_programs || [];
  const topIncs = an.top_includes || [];
  const relBreak = an.release_breakdown || [];

  const maxTbl = topTbls.length ? topTbls[0].program_count : 1;
  const maxProg = topProgs.length ? topProgs[0].table_count : 1;
  const maxInc = topIncs.length ? topIncs[0].user_count : 1;

  let tblRows = topTbls.map(t => `<tr>
    <td><a href="/admin/sqr/table/${esc(t.table_name)}">${esc(t.table_name)}</a></td>
    <td style="text-align:right;color:#0af">${t.program_count}</td>
    <td style="text-align:right;color:#fa0">${t.sqr_count}</td>
    <td style="width:80px">${barPct(t.program_count, maxTbl)}</td>
  </tr>`).join('');

  let progRows = topProgs.map(p => `<tr>
    <td><a href="/admin/sqr/${esc(p.filename)}">${esc(p.filename)}</a></td>
    <td style="color:#7faab2;font-size:11px;max-width:180px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${esc(p.description||'—')}</td>
    <td style="text-align:right;color:#0af">${p.table_count}</td>
    <td style="text-align:right;color:#fa0">${p.include_count}</td>
    <td style="text-align:right;color:#7faab2">${p.proc_count}</td>
    <td style="width:60px">${barPct(p.table_count, maxProg)}</td>
  </tr>`).join('');

  let incRows = topIncs.map(i => `<tr>
    <td><a href="/admin/sqr/${esc(i.include_file)}">${esc(i.include_file)}</a></td>
    <td style="text-align:right;color:#0af">${i.user_count}</td>
    <td style="width:80px">${barPct(i.user_count, maxInc)}</td>
  </tr>`).join('');

  const totalProgs = relBreak.reduce((s,r) => s + r.cnt, 0) || 1;
  let relRows = relBreak.map(r => `<tr>
    <td style="color:#d7faff">${esc(r.rel)}</td>
    <td style="text-align:right;color:#0f9">${r.sqr_cnt}</td>
    <td style="text-align:right;color:#fa0">${r.sqc_cnt}</td>
    <td style="text-align:right;color:#0af">${r.cnt}</td>
    <td style="width:80px">${barPct(r.cnt, totalProgs)}</td>
  </tr>`).join('');

  $('analyticsContent').innerHTML = `
  <div class="an-grid">
    <div class="an-card" style="grid-column:1/-1">
      <h3>Top 30 PS_ Tables by Reference Count</h3>
      <table class="an-tbl"><thead><tr>
        <th>Table</th><th style="text-align:right">Programs</th>
        <th style="text-align:right">SQR</th><th>Density</th>
      </tr></thead><tbody>${tblRows}</tbody></table>
    </div>
    <div class="an-card" style="grid-column:1/-1">
      <h3>Top 20 Most Complex SQR Programs (by Table Count)</h3>
      <table class="an-tbl"><thead><tr>
        <th>Filename</th><th>Description</th>
        <th style="text-align:right">Tables</th>
        <th style="text-align:right">Includes</th>
        <th style="text-align:right">Procs</th><th>Complexity</th>
      </tr></thead><tbody>${progRows}</tbody></table>
    </div>
    <div class="an-card">
      <h3>Top 20 Most-Included SQC Files</h3>
      <table class="an-tbl"><thead><tr>
        <th>SQC File</th><th style="text-align:right">Users</th><th>Usage</th>
      </tr></thead><tbody>${incRows}</tbody></table>
    </div>
    <div class="an-card">
      <h3>Release Breakdown</h3>
      <table class="an-tbl"><thead><tr>
        <th>Release</th><th style="text-align:right">SQR</th>
        <th style="text-align:right">SQC</th>
        <th style="text-align:right">Total</th><th>Share</th>
      </tr></thead><tbody>${relRows}</tbody></table>
    </div>
  </div>`;
}

load();
</script>
"""
    return HTMLResponse(_shell("SQR Analytics", "sqr", content))


@router.get("/sqr", response_class=HTMLResponse)
def sqr_index():
    content = """
<style>
.sqr-toolbar{display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.sqr-search{flex:1;min-width:220px;background:#0a1520;border:1px solid #1a3a4a;
  color:#d7faff;padding:6px 10px;border-radius:4px;font-size:13px}
.sqr-search:focus{outline:none;border-color:#00e5ff}
.sqr-filter{background:#0a1520;border:1px solid #1a3a4a;color:#d7faff;
  padding:6px 10px;border-radius:4px;font-size:13px}
.sqr-btn{padding:5px 14px;border:1px solid rgba(0,229,255,.4);border-radius:4px;
  background:rgba(0,229,255,.07);color:#00e5ff;font-size:12px;cursor:pointer}
.sqr-btn:hover{background:rgba(0,229,255,.15)}
.sqr-btn.green{border-color:rgba(0,255,150,.4);background:rgba(0,255,150,.07);color:#0f9}
.sqr-stats{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.sqr-stat{background:#0a1520;border:1px solid #1a3a4a;border-radius:6px;padding:8px 16px;min-width:120px}
.sqr-stat-val{font-size:22px;font-weight:700;color:#00e5ff}
.sqr-stat-lbl{font-size:10px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px}
.sqr-tbl{width:100%;border-collapse:collapse;font-size:12px}
.sqr-tbl th{text-align:left;padding:6px 10px;border-bottom:1px solid #1a3a4a;
  color:#7faab2;text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-size:10px}
.sqr-tbl td{padding:5px 10px;border-bottom:1px solid #0e2030}
.sqr-tbl tr:hover td{background:#0a1f2e}
.sqr-tbl a{color:#00e5ff;text-decoration:none}
.sqr-tbl a:hover{text-decoration:underline}
.sqr-pg{display:flex;gap:8px;margin-top:12px;align-items:center;font-size:12px;color:#7faab2}
.sqr-pg button{padding:3px 10px;border:1px solid #1a3a4a;background:#0a1520;
  color:#7faab2;border-radius:3px;cursor:pointer;font-size:12px}
.sqr-pg button:hover:not(:disabled){color:#00e5ff;border-color:#00e5ff}
.sqr-pg button:disabled{opacity:.3}
.ingest-bar{background:#0a1520;border:1px solid #1a3a4a;border-radius:6px;
  padding:10px 14px;margin-bottom:16px;font-size:12px;color:#7faab2}
</style>

<div class="ingest-bar" id="ingestBar" style="display:none"></div>

<div class="sqr-stats" id="statsRow">
  <div class="sqr-stat"><div class="sqr-stat-val" id="sTot">—</div><div class="sqr-stat-lbl">Programs</div></div>
  <div class="sqr-stat"><div class="sqr-stat-val" id="sSqr">—</div><div class="sqr-stat-lbl">SQR files</div></div>
  <div class="sqr-stat"><div class="sqr-stat-val" id="sSqc">—</div><div class="sqr-stat-lbl">SQC files</div></div>
  <div class="sqr-stat"><div class="sqr-stat-val" id="sTbl">—</div><div class="sqr-stat-lbl">PS_ Tables</div></div>
  <div class="sqr-stat"><div class="sqr-stat-val" id="sTs" style="font-size:11px;color:#7faab2">—</div><div class="sqr-stat-lbl">Last indexed</div></div>
</div>

<div class="sqr-toolbar">
  <input class="sqr-search" id="searchBox" placeholder="Search programs, descriptions…" oninput="debounceSearch()">
  <select class="sqr-filter" id="envFilter" onchange="onEnvChange()">
    <option value="">All environments</option>
  </select>
  <select class="sqr-filter" id="typeFilter" onchange="doSearch(1)">
    <option value="">All types</option>
    <option value="sqr">SQR only</option>
    <option value="sqc">SQC only</option>
  </select>
  <button class="sqr-btn" onclick="doSearch(1)">Search</button>
  <a class="sqr-btn" href="/admin/sqr/analytics" style="text-decoration:none;padding:5px 14px">Analytics</a>
  <button class="sqr-btn green" id="ingestBtn" onclick="triggerIngest()">Re-index</button>
</div>

<div id="resultsArea">
  <div style="color:#7faab2;padding:24px;text-align:center">Loading…</div>
</div>
<div class="sqr-pg" id="pgBar" style="display:none">
  <button id="pgPrev" onclick="doSearch(_page-1)">← Prev</button>
  <span id="pgInfo"></span>
  <button id="pgNext" onclick="doSearch(_page+1)">Next →</button>
</div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
let _page = 1, _debTimer = null;

async function loadEnvs() {
  try {
    const r = await fetch('/api/sqr/sources');
    const d = await r.json();
    const sel = $('envFilter');
    (d.envs || []).forEach(e => {
      const opt = document.createElement('option');
      opt.value = e;
      opt.textContent = e;
      sel.appendChild(opt);
    });
  } catch(e) {}
}

function onEnvChange() {
  loadStats();
  doSearch(1);
}

async function loadStats() {
  try {
    const env = $('envFilter').value;
    const envParam = env ? `&env=${encodeURIComponent(env)}` : '';
    // global last-indexed timestamp always comes from /stats
    const r = await fetch('/api/sqr/stats');
    const d = await r.json();
    $('sTs').textContent = d.last_indexed ? d.last_indexed.replace('T',' ').replace('Z','') : 'Not indexed';
    // counts are env-aware
    const r2 = await fetch(`/api/sqr/programs?type=sqr&per_page=1${envParam}`);
    const d2 = await r2.json();
    const r3 = await fetch(`/api/sqr/programs?type=sqc&per_page=1${envParam}`);
    const d3 = await r3.json();
    $('sSqr').textContent = d2.total ?? '—';
    $('sSqc').textContent = d3.total ?? '—';
    $('sTot').textContent = ((d2.total||0) + (d3.total||0)) || '—';
    $('sTbl').textContent = d.distinct_ps_tables ?? '—';
  } catch(e) {}
}

function debounceSearch() {
  clearTimeout(_debTimer);
  _debTimer = setTimeout(() => doSearch(1), 320);
}

async function doSearch(page) {
  _page = page || 1;
  const q = $('searchBox').value.trim();
  const t = $('typeFilter').value;
  const env = $('envFilter').value;
  let url = `/api/sqr/programs?page=${_page}&per_page=50`;
  if (q)   url += `&q=${encodeURIComponent(q)}`;
  if (t)   url += `&type=${t}`;
  if (env) url += `&env=${encodeURIComponent(env)}`;

  $('resultsArea').innerHTML = '<div style="color:#7faab2;padding:16px">Loading…</div>';
  try {
    const r = await fetch(url);
    const d = await r.json();
    renderResults(d);
  } catch(e) {
    $('resultsArea').innerHTML = `<div style="color:#f55;padding:16px">Error: ${esc(String(e))}</div>`;
  }
}

function renderResults(d) {
  const rows = d.results || [];
  if (!rows.length) {
    $('resultsArea').innerHTML = '<div style="color:#7faab2;padding:24px;text-align:center">No programs found</div>';
    $('pgBar').style.display = 'none';
    return;
  }

  let html = `<table class="sqr-tbl"><thead><tr>
    <th>Filename</th><th>Type</th><th>Description</th>
    <th style="text-align:right">Tables</th><th style="text-align:right">Includes</th><th style="text-align:right">Procs</th>
  </tr></thead><tbody>`;

  for (const r of rows) {
    const badge = r.file_type === 'sqr'
      ? '<span style="color:#0f9;font-size:10px;font-weight:700">SQR</span>'
      : '<span style="color:#fa0;font-size:10px;font-weight:700">SQC</span>';
    html += `<tr>
      <td><a href="/admin/sqr/${esc(r.filename)}">${esc(r.filename)}</a></td>
      <td>${badge}</td>
      <td style="color:#aac">${esc(r.description || '—')}</td>
      <td style="text-align:right;color:${r.table_count>0?'#0af':'#4a6a7a'}">${r.table_count}</td>
      <td style="text-align:right;color:${r.include_count>0?'#fa0':'#4a6a7a'}">${r.include_count}</td>
      <td style="text-align:right;color:#4a6a7a">${r.proc_count}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  $('resultsArea').innerHTML = html;

  const totalPages = Math.ceil(d.total / d.per_page);
  $('pgInfo').textContent = `Page ${_page} of ${totalPages} (${d.total} total)`;
  $('pgPrev').disabled = _page <= 1;
  $('pgNext').disabled = _page >= totalPages;
  $('pgBar').style.display = 'flex';
}

async function triggerIngest() {
  const btn = $('ingestBtn');
  btn.disabled = true;
  btn.textContent = 'Indexing…';
  $('ingestBar').style.display = '';
  $('ingestBar').innerHTML = '<span style="color:#fa0">⏳ Indexing SQR library — this may take 30-60 seconds…</span>';

  try {
    await fetch('/api/sqr/ingest', { method: 'POST' });
    pollIngest();
  } catch(e) {
    $('ingestBar').innerHTML = `<span style="color:#f55">Error: ${esc(String(e))}</span>`;
    btn.disabled = false;
    btn.textContent = 'Re-index';
  }
}

async function pollIngest() {
  const r = await fetch('/api/sqr/ingest/status');
  const d = await r.json();
  if (d.running) {
    setTimeout(pollIngest, 2000);
    return;
  }
  const btn = $('ingestBtn');
  btn.disabled = false;
  btn.textContent = 'Re-index';
  if (d.last && d.last.status === 'ok') {
    const results = d.last.results || [];
    const total = results.reduce((s,r) => s + (r.indexed||0), 0);
    const errs  = results.reduce((s,r) => s + (r.errors||0), 0);
    $('ingestBar').innerHTML = `<span style="color:#0f9">✓ Indexed ${total} files${errs ? ` (${errs} errors)` : ''} — refreshing…</span>`;
    setTimeout(() => { loadStats(); doSearch(1); $('ingestBar').style.display='none'; }, 1000);
  } else {
    $('ingestBar').innerHTML = `<span style="color:#f55">Ingest error: ${esc((d.last||{}).error||'unknown')}</span>`;
  }
}

loadEnvs();
loadStats();
doSearch(1);
</script>
"""
    return HTMLResponse(_shell("SQR Explorer", "sqr", content))


@router.get("/sqr/{filename}", response_class=HTMLResponse)
def sqr_detail(filename: str):
    content = f"""
<style>
.sqr-detail-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:900px){{.sqr-detail-grid{{grid-template-columns:1fr}}}}
.sqr-card{{background:#0a1520;border:1px solid #1a3a4a;border-radius:8px;padding:16px}}
.sqr-card h3{{margin:0 0 12px;color:#00e5ff;font-size:13px;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px}}
.sqr-meta{{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:12px}}
.sqr-meta-lbl{{color:#7faab2;white-space:nowrap}}
.sqr-meta-val{{color:#d7faff}}
.sqr-list{{list-style:none;padding:0;margin:0;max-height:320px;overflow-y:auto}}
.sqr-list li{{padding:4px 0;border-bottom:1px solid #0e2030;font-size:12px;color:#aac}}
.sqr-list li:last-child{{border:none}}
.sqr-list a{{color:#00e5ff;text-decoration:none}}
.sqr-list a:hover{{text-decoration:underline}}
.op-badge{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;
  font-weight:700;margin-left:4px;vertical-align:middle}}
.op-SELECT{{background:#0af2;color:#0af}}
.op-UPDATE{{background:#fa02;color:#fa0}}
.op-INSERT{{background:#0f92;color:#0f9}}
.op-DELETE{{background:#f552;color:#f55}}
.op-CREATE{{background:#a0f2;color:#a0f}}
.back-link{{color:#7faab2;font-size:12px;text-decoration:none;margin-bottom:14px;display:inline-block}}
.back-link:hover{{color:#00e5ff}}
.sqr-hdr{{margin-bottom:16px}}
.sqr-title{{font-size:18px;font-weight:700;color:#d7faff}}
.sqr-desc{{font-size:13px;color:#7faab2;margin-top:4px}}
.tab-row{{display:flex;gap:4px;border-bottom:1px solid #1a3a4a;margin-bottom:0}}
.tab{{padding:6px 16px;font-size:12px;color:#7faab2;cursor:pointer;border-bottom:2px solid transparent;
  border-radius:4px 4px 0 0;user-select:none}}
.tab:hover{{color:#00e5ff}}
.tab.on{{color:#00e5ff;border-bottom-color:#00e5ff;font-weight:600}}
</style>

<a class="back-link" href="/admin/sqr">← SQR Explorer</a>
<div id="detailContent"><div style="color:#7faab2;padding:24px">Loading…</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
async function loadDetail() {
  try {
    const r = await fetch('/api/sqr/program/' + encodeURIComponent(""" + f'"{filename}"' + """));
    if (!r.ok) {
      $('detailContent').innerHTML = '<div style="color:#f55;padding:24px">Program not found in index. Try re-indexing from <a href="/admin/sqr" style="color:#0af">SQR Explorer</a>.</div>';
      return;
    }
    const d = await r.json();
    render(d);
  } catch(e) {
    $('detailContent').innerHTML = `<div style="color:#f55;padding:24px">Error: ${esc(String(e))}</div>`;
  }
}

function opBadges(ops) {
  return (ops||'').split(',').filter(Boolean).map(o =>
    `<span class="op-badge op-${esc(o)}">${esc(o)}</span>`
  ).join('');
}

function render(d) {
  const isSquc = d.file_type === 'sqc';
  const ftBadge = d.file_type === 'sqr'
    ? '<span style="color:#0f9;font-weight:700;font-size:11px">SQR</span>'
    : '<span style="color:#fa0;font-weight:700;font-size:11px">SQC</span>';

  let tables = '';
  if (d.tables && d.tables.length) {
    tables = d.tables.map(t =>
      `<li><a href="/admin/sqr?q=${encodeURIComponent(t.table_name)}"
         onclick="event.preventDefault();window.location='/admin/sqr/table/${encodeURIComponent(t.table_name)}'"
         >${esc(t.table_name)}</a>${opBadges(t.operations)}</li>`
    ).join('');
  } else {
    tables = '<li style="color:#4a6a7a">No PS_ tables referenced</li>';
  }

  let includes = '';
  if (d.includes && d.includes.length) {
    includes = d.includes.map(inc =>
      `<li><a href="/admin/sqr/${encodeURIComponent(inc)}">${esc(inc)}</a></li>`
    ).join('');
  } else {
    includes = '<li style="color:#4a6a7a">No #include dependencies</li>';
  }

  let procs = '';
  if (d.procedures && d.procedures.length) {
    procs = d.procedures.map(p => `<li>${esc(p)}</li>`).join('');
  } else {
    procs = '<li style="color:#4a6a7a">No procedures defined</li>';
  }

  $('detailContent').innerHTML = `
    <div class="sqr-hdr">
      <div class="sqr-title">${esc(d.filename)} ${ftBadge}</div>
      <div class="sqr-desc">${esc(d.description || 'No description')}</div>
    </div>

    <div class="tab-row" style="margin-bottom:16px">
      <div class="tab on" onclick="switchTab('meta')">Overview</div>
      ${d.includes && d.includes.length ? `<div class="tab" onclick="switchTab('tree')">Include Tree</div>` : ''}
      <div class="tab" onclick="switchTab('src')">Source</div>
      <div class="tab" onclick="switchTab('records')">KG Records</div>
      ${isSquc ? `<div class="tab" onclick="switchTab('inclby')">Included By <span id="inclByBadge" style="font-size:10px;opacity:.7"></span></div>` : ''}
    </div>

    <div id="paneTree" style="display:none">
      <div class="sqr-card">
        <h3>SQC Include Tree</h3>
        <div id="treeContent" style="color:#7faab2;font-size:12px;padding:8px">Loading…</div>
      </div>
    </div>

    <div id="paneIncludedBy" style="display:none">
      <div class="sqr-card">
        <h3>Programs Including This SQC <span id="inclByCount" style="font-size:11px;font-weight:400;color:#7faab2"></span></h3>
        <div id="inclByContent" style="color:#7faab2;font-size:12px;padding:8px">Loading\u2026</div>
      </div>
    </div>

    <div id="paneOverview">
      <div class="sqr-card" style="margin-bottom:16px">
        <h3>Metadata</h3>
        <div class="sqr-meta">
          <span class="sqr-meta-lbl">Program</span><span class="sqr-meta-val">${esc(d.program_name||'—')}</span>
          <span class="sqr-meta-lbl">Release</span><span class="sqr-meta-val">${esc(d.release||'—')}</span>
          <span class="sqr-meta-lbl">Revision</span><span class="sqr-meta-val">${esc(d.revision||'—')}</span>
          <span class="sqr-meta-lbl">Date</span><span class="sqr-meta-val">${esc(d.sqr_date||'—')}</span>
          <span class="sqr-meta-lbl">Indexed</span><span class="sqr-meta-val">${esc((d.indexed_at||'—').replace('T',' ').replace('Z',''))}</span>
        </div>
      </div>
      <div class="sqr-detail-grid">
        <div class="sqr-card">
          <h3>PS_ Tables Referenced (${d.tables ? d.tables.length : 0})</h3>
          <ul class="sqr-list">${tables}</ul>
        </div>
        <div class="sqr-card">
          <h3>#Include Dependencies (${d.includes ? d.includes.length : 0})</h3>
          <ul class="sqr-list">${includes}</ul>
        </div>
        <div class="sqr-card" style="grid-column:1/-1">
          <h3>Procedures (${d.procedures ? d.procedures.length : 0})</h3>
          <ul class="sqr-list" style="columns:3;column-gap:20px;max-height:280px">${procs}</ul>
        </div>
      </div>
    </div>

    <div id="paneSrc" style="display:none">
      <div class="sqr-card">
        <h3 style="display:flex;align-items:center;gap:10px">
          Source
          <span id="srcInfo" style="font-size:10px;color:#7faab2;font-weight:400;text-transform:none"></span>
        </h3>
        <div id="srcContent" style="color:#7faab2;font-size:12px;padding:8px">Loading source…</div>
      </div>
    </div>

    <div id="paneRecords" style="display:none">
      <div class="sqr-card">
        <h3>Records Referenced <span id="kgRecBadge" style="font-size:10px;font-weight:400;color:#7faab2"></span></h3>
        <div id="kgRecContent" style="color:#7faab2;font-size:12px;padding:8px">Loading…</div>
      </div>
    </div>
  `;
  // lazy-load source when tab opened
  _detail = d;
}

let _detail = null, _srcLoaded = false, _inclByLoaded = false, _treeLoaded = false, _kgRecLoaded = false;

function switchTab(tab) {
  document.querySelectorAll('.tab-row .tab').forEach(t => {
    const m = (t.getAttribute('onclick')||'').match(/switchTab\('(\w+)'\)/);
    if (m) t.classList.toggle('on', m[1] === tab);
  });
  $('paneOverview').style.display = tab === 'meta'   ? '' : 'none';
  const pt = $('paneTree');    if (pt) pt.style.display = tab === 'tree'    ? '' : 'none';
  $('paneSrc').style.display      = tab === 'src'    ? '' : 'none';
  const ip = $('paneIncludedBy'); if (ip) ip.style.display = tab === 'inclby'  ? '' : 'none';
  const rp = $('paneRecords');   if (rp) rp.style.display = tab === 'records' ? '' : 'none';
  if (tab === 'src'     && !_srcLoaded)    loadSource();
  if (tab === 'inclby'  && !_inclByLoaded) loadInclBy();
  if (tab === 'tree'    && !_treeLoaded)   loadTree();
  if (tab === 'records' && !_kgRecLoaded)  loadKgRecords();
}

async function loadSource() {
  _srcLoaded = true;
  try {
    const r = await fetch('/api/sqr/program/' + encodeURIComponent(""" + f'"{filename}"' + """) + '/source');
    if (!r.ok) {
      $('srcContent').innerHTML = '<span style="color:#f55">Could not load source — file may not be accessible from the server</span>';
      return;
    }
    const d = await r.json();
    const trunc = d.truncated ? ` (truncated at ${Math.round(d.size/1024)}KB)` : ` (${Math.round(d.size/1024)} KB)`;
    $('srcInfo').textContent = trunc;
    $('srcContent').innerHTML = `<pre style="margin:0;font-size:11px;line-height:1.5;overflow-x:auto;white-space:pre-wrap">${highlightSQR(d.source)}</pre>`;
  } catch(e) {
    $('srcContent').innerHTML = `<span style="color:#f55">Error: ${esc(String(e))}</span>`;
  }
}

async function loadKgRecords() {
  _kgRecLoaded = true;
  const fn = (_detail && _detail.filename || '').toUpperCase();
  if (!fn) { $('kgRecContent').innerHTML = '<span style="color:#4a6a7a">No program loaded</span>'; return; }
  const nodeId = 'sqr_program:' + fn;
  try {
    const r = await fetch('/api/graph/neighbors/' + encodeURIComponent(nodeId) + '?env=HCM&limit=150');
    const d = await r.json();
    const edges = (d.edges || []).filter(e => e.type === 'READS' || e.type === 'WRITES');
    $('kgRecBadge').textContent = edges.length ? '(' + edges.length + ' from KG)' : '(KG)';
    if (!edges.length) {
      $('kgRecContent').innerHTML = '<div style="color:#4a6a7a;padding:8px">No record edges in Knowledge Graph for this program. Rebuild the graph to index SQR \u2192 record edges.</div>';
      return;
    }
    const nodeMap = {};
    (d.nodes || []).forEach(n => { nodeMap[n.id] = n; });
    const reads  = edges.filter(e => e.type === 'READS');
    const writes = edges.filter(e => e.type === 'WRITES');
    function renderGroup(title, color, grpEdges) {
      if (!grpEdges.length) return '';
      const items = grpEdges.map(e => {
        const node = nodeMap[e.target] || {};
        const recName = (e.target || '').replace('record:', '');
        const url = node.canonical_url || ('/admin/object/record/' + encodeURIComponent(recName));
        return `<li><a href="${esc(url)}" target="_blank">${esc(recName)}</a></li>`;
      }).join('');
      return `<div style="margin-bottom:14px">
        <div style="font-size:10px;font-weight:700;color:${color};letter-spacing:.05em;margin-bottom:6px">${title} (${grpEdges.length})</div>
        <ul class="sqr-list">${items}</ul></div>`;
    }
    $('kgRecContent').innerHTML = renderGroup('READS', '#0af', reads) + renderGroup('WRITES', '#fa0', writes);
  } catch(e) {
    $('kgRecContent').innerHTML = `<div style="color:#f55;padding:8px">Error: ${esc(String(e))}</div>`;
  }
}

async function loadInclBy() {
  _inclByLoaded = true;
  try {
    const r = await fetch('/api/sqr/sqc/' + encodeURIComponent(""" + f'"{filename}"' + """) + '/users');
    if (!r.ok) { $('inclByContent').innerHTML = '<span style="color:#f55">Could not load inclusion data</span>'; return; }
    const d = await r.json();
    const progs = d.programs || [];
    $('inclByCount').textContent = '(' + progs.length + ')';
    const badge = $('inclByBadge'); if (badge) badge.textContent = progs.length;
    if (!progs.length) {
      $('inclByContent').innerHTML = '<span style="color:#4a6a7a">No programs in the index include this SQC</span>';
      return;
    }
    $('inclByContent').innerHTML = `<ul class="sqr-list" style="max-height:520px">${
      progs.map(p =>
        `<li><a href="/admin/sqr/${encodeURIComponent(p.filename)}">${esc(p.program_name)}</a>` +
        (p.description ? ` <span style="color:#556;font-size:10px">— ${esc(p.description.slice(0,90))}</span>` : '') +
        '</li>'
      ).join('')
    }</ul>`;
  } catch(e) {
    $('inclByContent').innerHTML = `<span style="color:#f55">Error: ${esc(String(e))}</span>`;
  }
}

function toggleTree(uid) {
  const el = document.getElementById(uid);
  const ch = document.getElementById('ch_' + uid);
  if (!el) return;
  const hidden = el.style.display === 'none';
  el.style.display = hidden ? '' : 'none';
  if (ch) ch.textContent = hidden ? '▼' : '▶';
}

function renderNode(node, depth) {
  const hasKids = node.children && node.children.length;
  const uid = 'tn_' + Math.random().toString(36).slice(2);
  let nameHtml;
  if (node.cyclic) {
    nameHtml = `<span style="color:#ff6699">${esc(node.filename)}</span>` +
      `<span style="margin-left:6px;font-size:9px;background:#ff66992a;color:#ff6699;padding:1px 5px;border-radius:3px">CYCLIC</span>`;
  } else if (!node.indexed) {
    nameHtml = `<span style="color:#7faab2">${esc(node.filename)}</span>` +
      `<span style="margin-left:6px;font-size:9px;color:#fa0;opacity:.7">not indexed</span>`;
  } else {
    nameHtml = `<a href="/admin/sqr/${encodeURIComponent(node.filename)}" style="color:#0af;text-decoration:none">${esc(node.filename)}</a>`;
  }
  let chevron, childrenHtml = '';
  if (hasKids && !node.cyclic) {
    chevron = `<span id="ch_${uid}" onclick="toggleTree('${uid}')" style="cursor:pointer;color:#00e5ff;font-size:10px;user-select:none;margin-right:4px;display:inline-block;width:12px">▼</span>`;
    childrenHtml = `<div id="${uid}" style="margin-left:20px;border-left:1px solid rgba(0,229,255,.12);padding-left:8px;margin-top:2px">` +
      node.children.map(c => renderNode(c, depth+1)).join('') + `</div>`;
  } else {
    chevron = `<span style="display:inline-block;width:16px;margin-right:4px"></span>`;
  }
  return `<div style="padding:2px 0">${chevron}${nameHtml}${childrenHtml}</div>`;
}

async function loadTree() {
  _treeLoaded = true;
  const tc = $('treeContent');
  try {
    const r = await fetch('/api/sqr/program/' + encodeURIComponent(""" + f'"{filename}"' + """) + '/tree');
    if (!r.ok) { tc.innerHTML = '<span style="color:#f55">Could not load include tree</span>'; return; }
    const d = await r.json();
    if (!d.children || !d.children.length) {
      tc.innerHTML = '<span style="color:#4a6a7a">No #include dependencies</span>';
      return;
    }
    tc.innerHTML = d.children.map(c => renderNode(c, 0)).join('');
  } catch(e) {
    tc.innerHTML = `<span style="color:#f55">Error: ${esc(String(e))}</span>`;
  }
}

function highlightSQR(src) {
  const lines = src.split('\\n');
  return lines.map(line => {
    // comment lines
    if (/^\\s*!/.test(line)) return `<span style="color:#5a8a5a">${esc(line)}</span>`;
    // preprocessor #include / #define
    if (/^\\s*#/.test(line)) return `<span style="color:#c97bdb">${esc(line)}</span>`;
    // begin/end section headers
    if (/^\\s*(begin-|end-)/i.test(line)) return `<span style="color:#00e5ff;font-weight:700">${esc(line)}</span>`;
    // SQL keywords
    const sqlKw = line.replace(
      /\\b(SELECT|FROM|WHERE|JOIN|LEFT|INNER|OUTER|AND|OR|ORDER BY|GROUP BY|HAVING|INSERT INTO|UPDATE|DELETE FROM|SET|INTO|VALUES|AS|ON|NOT|IN|EXISTS|DISTINCT|COUNT|SUM|MAX|MIN|NVL|SYSDATE|ROWNUM)\\b/gi,
      '<span style="color:#fa0;font-weight:600">$1</span>'
    );
    // SQR keywords (do, let, print, etc.)
    return sqlKw.replace(
      /\\b(do|gosub|let|print|move|add|subtract|multiply|divide|clear|string|numeric|date|array|if|else|end-if|while|end-while|evaluate|when|when-other|end-evaluate|break|exit|return|call|begin|end)\\b/gi,
      '<span style="color:#7af">$1</span>'
    );
  }).join('\\n');
}

loadDetail();
</script>
"""
    return HTMLResponse(_shell(f"SQR — {filename}", "sqr", content))


@router.get("/sqr/table/{table_name}", response_class=HTMLResponse)
def sqr_table_detail(table_name: str):
    tbl_upper = table_name.upper()
    content = f"""
<style>
.sqr-tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.sqr-tbl th{{text-align:left;padding:6px 10px;border-bottom:1px solid #1a3a4a;
  color:#7faab2;text-transform:uppercase;font-size:10px;font-weight:600;letter-spacing:.5px}}
.sqr-tbl td{{padding:5px 10px;border-bottom:1px solid #0e2030}}
.sqr-tbl tr:hover td{{background:#0a1f2e}}
.sqr-tbl a{{color:#00e5ff;text-decoration:none}}
.sqr-tbl a:hover{{text-decoration:underline}}
.op-badge{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;
  font-weight:700;margin:1px;vertical-align:middle}}
.op-SELECT{{background:#0af2;color:#0af}}
.op-UPDATE{{background:#fa02;color:#fa0}}
.op-INSERT{{background:#0f92;color:#0f9}}
.op-DELETE{{background:#f552;color:#f55}}
.op-CREATE{{background:#a0f2;color:#a0f}}
</style>

<a href="/admin/sqr" style="color:#7faab2;font-size:12px;text-decoration:none;
  margin-bottom:14px;display:inline-block">← SQR Explorer</a>
<h2 style="margin:8px 0 16px;color:#d7faff;font-size:16px">
  PS_ Table: <span style="color:#00e5ff">{tbl_upper}</span>
</h2>
<div id="tableContent"><div style="color:#7faab2;padding:24px">Loading…</div></div>

<script>
""" + _ESC_JS + """
async function load() {
  const r = await fetch('/api/sqr/table/' + encodeURIComponent(""" + f'"{tbl_upper}"' + """));
  const d = await r.json();
  const progs = d.programs || [];
  if (!progs.length) {
    $('tableContent').innerHTML = '<div style="color:#7faab2;padding:24px">No SQR programs reference this table.</div>';
    return;
  }
  let html = `<p style="color:#7faab2;font-size:12px;margin-bottom:12px">${progs.length} program(s) reference this table</p>
  <table class="sqr-tbl"><thead><tr>
    <th>Filename</th><th>Type</th><th>Description</th><th>Operations</th>
  </tr></thead><tbody>`;
  for (const p of progs) {
    const ops = (p.operations||'').split(',').filter(Boolean).map(o =>
      `<span class="op-badge op-${esc(o)}">${esc(o)}</span>`).join('');
    const ftBadge = p.file_type === 'sqr'
      ? '<span style="color:#0f9;font-size:10px;font-weight:700">SQR</span>'
      : '<span style="color:#fa0;font-size:10px;font-weight:700">SQC</span>';
    html += `<tr>
      <td><a href="/admin/sqr/${esc(p.filename)}">${esc(p.filename)}</a></td>
      <td>${ftBadge}</td>
      <td style="color:#aac">${esc(p.description||'—')}</td>
      <td>${ops}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  $('tableContent').innerHTML = html;
}
load();
</script>
"""
    return HTMLResponse(_shell(f"SQR — {tbl_upper}", "sqr", content))


# ── SQR Source Search ────────────────────────────────────────────────────────

_SQR_KW = (
    "'BEGIN-PROGRAM','END-PROGRAM','BEGIN-PROCEDURE','END-PROCEDURE',"
    "'BEGIN-HEADING','END-HEADING','BEGIN-FOOTING','END-FOOTING',"
    "'BEGIN-REPORT','END-REPORT','BEGIN-SELECT','END-SELECT',"
    "'BEGIN-SQL','END-SQL','BEGIN-SETUP','END-SETUP',"
    "'LET','DO','IF','ELSE','ELSEIF','END-IF','WHILE','END-WHILE',"
    "'EVALUATE','WHEN','WHEN-OTHER','END-EVALUATE',"
    "'CALL','PRINT','DISPLAY','MOVE','ADD','SUBTRACT','MULTIPLY','DIVIDE',"
    "'STRING','UNSTRING','CONCAT','TRIM','UPPER-CASE','LOWER-CASE',"
    "'OPEN','READ','CLOSE','WRITE','NEXT-LISTING','NEW-PAGE',"
    "'FROM','WHERE','AND','OR','NOT','IN','BETWEEN','ORDER BY','GROUP BY',"
    "'SELECT','INSERT','UPDATE','DELETE','COMMIT','ROLLBACK',"
    "'#include','#define','#ifdef','#endif','#else',"
    "'INPUT','SHOW','ASK','POSITION'"
)


@router.get("/sqrsearch", response_class=HTMLResponse)
def sqr_search_page(q: str = ""):
    preload = q.strip()
    return _shell("SQR Source Search", "sqrsearch", noscroll=True, content=f"""
<style>
*{{box-sizing:border-box}}
.ds-content{{display:flex;flex-direction:column;overflow:hidden;height:calc(100vh - 88px)}}
.topbar{{padding:10px 16px;border-bottom:1px solid #22aa6622;display:flex;align-items:center;gap:10px;flex-wrap:wrap;flex-shrink:0}}
input[type=text]{{background:#0b1b24;color:#d7faff;border:1px solid #22aa6644;padding:5px 10px;font-size:12px;border-radius:3px}}
input[type=text]:focus{{outline:none;border-color:#22aa66}}
button{{background:#22aa66;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
button:hover{{background:#33cc77}}
button.sec{{background:transparent;border:1px solid #22aa6644;color:#22aa66}}
button.sec.on{{background:rgba(34,170,102,.15);border-color:#22aa66}}
button.sec:hover{{border-color:#22aa66;background:rgba(34,170,102,.1)}}
select{{background:#0b1b24;color:#d7faff;border:1px solid #22aa6644;padding:5px 8px;font-size:12px;border-radius:3px}}
.split{{display:flex;flex:1;overflow:hidden}}
.sidebar{{width:340px;min-width:220px;border-right:1px solid #22aa6622;overflow-y:auto;flex-shrink:0}}
.content{{flex:1;overflow:auto;padding:0}}
.hint{{font-size:10px;color:#445}}
.empty{{color:#445;font-size:12px;padding:24px;text-align:center}}
.hit-item{{padding:8px 12px;border-bottom:1px solid #0d1b24;cursor:pointer;border-left:3px solid transparent}}
.hit-item:hover{{background:rgba(34,170,102,.06);border-left-color:#22aa6644}}
.hit-item.sel{{background:rgba(34,170,102,.1);border-left-color:#22aa66}}
.hit-name{{font-family:monospace;font-size:12px;color:#22aa66;font-weight:bold}}
.hit-meta{{font-size:10px;color:#556;margin-top:2px}}
.hit-count{{display:inline-block;padding:0 6px;border-radius:8px;font-size:10px;font-weight:bold;
  background:rgba(34,170,102,.15);color:#22aa66;border:1px solid rgba(34,170,102,.3);margin-left:6px}}
.src-wrap{{padding:0}}
.src-hdr{{padding:10px 16px;border-bottom:1px solid #22aa6622;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.src-hdr-name{{font-family:monospace;font-size:14px;color:#22aa66;font-weight:bold}}
.src-hdr-meta{{font-size:11px;color:#556}}
.snippets{{padding:12px 16px;border-bottom:1px solid #0d1b24}}
.snip-lbl{{font-size:10px;color:#445;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}}
.snip-block{{font-family:monospace;font-size:11px;background:#020c14;border:1px solid #0d1b24;
  border-radius:3px;padding:6px 10px;margin-bottom:6px;line-height:1.5;white-space:pre}}
.snip-lineno{{color:#334;user-select:none;display:inline-block;width:36px;text-align:right;margin-right:8px}}
.snip-match{{background:#1a3300;color:#88ff44}}
.src-full{{padding:12px 16px}}
.src-full-hdr{{font-size:10px;color:#445;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;
  display:flex;align-items:center;justify-content:space-between}}
.src-inner{{font-family:monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;word-break:break-word;
  background:#020c14;border:1px solid #0d1b24;border-radius:3px;padding:10px 14px;
  max-height:calc(100vh - 340px);overflow-y:auto}}
.kw{{color:#569cd6}}.str{{color:#ce9178}}.cmt{{color:#6a9955}}.hit{{background:#1a3300;color:#88ff44}}
.status-bar{{font-size:10px;color:#445;padding:4px 12px;flex-shrink:0;border-top:1px solid #0d1b24}}
</style>

<div class="topbar">
  <input id="qInp" type="text" placeholder="Search SQR/SQC source… (2+ chars)" style="width:320px"
         value="{preload}" onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">&#128269; Search</button>
  <select id="typeFilter" onchange="doSearch()">
    <option value="">All types</option>
    <option value="sqr">SQR only</option>
    <option value="sqc">SQC only</option>
  </select>
  <span class="hint" id="statusTxt"></span>
</div>
<div class="split">
  <div class="sidebar" id="sidebar"><div class="empty">Enter a search term to find SQR/SQC programs.</div></div>
  <div class="content" id="content"><div class="empty">Select a result to view source with highlights.</div></div>
</div>
<div class="status-bar" id="statusBar"></div>

<script>
const SQR_KW=[{_SQR_KW}];

function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}

function highlightSQR(src, q){{
  const qLo=q.toLowerCase();
  let out='',i=0;
  while(i<src.length){{
    // Comment: !
    if(src[i]==='!'){{const nl=src.indexOf('\\n',i);const end=nl<0?src.length:nl;out+='<span class="cmt">'+esc(src.slice(i,end))+'</span>';i=end;continue;}}
    // Comment: /*
    if(src[i]==='/'&&src[i+1]==='*'){{const e=src.indexOf('*/',i+2);const end=e<0?src.length:e+2;out+='<span class="cmt">'+esc(src.slice(i,end))+'</span>';i=end;continue;}}
    // String
    if(src[i]==="'"){{let j=i+1;while(j<src.length&&src[j]!=="'")j++;out+='<span class="str">'+esc(src.slice(i,j+1))+'</span>';i=j+1;continue;}}
    // Word
    if(/[A-Za-z#_%$]/.test(src[i])){{
      let j=i;while(j<src.length&&/[A-Za-z0-9_\-#%$.]/.test(src[j]))j++;
      const w=src.slice(i,j);
      const wu=w.toUpperCase();
      if(qLo&&wu.toLowerCase().includes(qLo))out+='<span class="hit">'+esc(w)+'</span>';
      else if(SQR_KW.includes(wu))out+='<span class="kw">'+esc(w)+'</span>';
      else out+=esc(w);
      i=j;continue;
    }}
    out+=esc(src[i]);i++;
  }}
  return out;
}}

let _curQ='';
let _hits=[];
let _srcCache={{}};

async function doSearch(){{
  const q=document.getElementById('qInp').value.trim();
  const type=document.getElementById('typeFilter').value;
  if(!q||q.length<2){{
    document.getElementById('sidebar').innerHTML='<div class="empty">Enter 2+ characters.</div>';
    document.getElementById('content').innerHTML='<div class="empty">Select a result to view source.</div>';
    return;
  }}
  _curQ=q;
  _srcCache={{}};
  document.getElementById('sidebar').innerHTML='<div class="empty" style="color:#334">Searching…</div>';
  document.getElementById('statusTxt').textContent='';
  const params=new URLSearchParams({{q, limit:100}});
  if(type)params.set('type',type);
  try{{
    const d=await fetch('/api/sqr/search?'+params).then(r=>r.json());
    if(d.warning){{
      document.getElementById('sidebar').innerHTML=
        `<div style="padding:12px;color:#ffaa00;font-size:11px;border:1px solid #ffaa0022;background:#1a0e00;margin:10px;border-radius:3px">&#9888; ${{esc(d.warning)}}</div>`;
      document.getElementById('statusTxt').textContent=d.warning;
      return;
    }}
    _hits=d.hits||[];
    document.getElementById('statusTxt').textContent=
      `${{_hits.length}} file${{_hits.length!==1?'s':''}} matched`+(d.has_more?' (showing first 100)':'')+
      ` — ${{d.indexed||0}} files indexed`;
    renderSidebar(_hits, q);
    if(_hits.length)selectHit(0);
  }}catch(e){{
    document.getElementById('sidebar').innerHTML=`<div class="empty">Error: ${{esc(String(e))}}</div>`;
  }}
}}

function renderSidebar(hits, q){{
  if(!hits.length){{document.getElementById('sidebar').innerHTML='<div class="empty">No matches found.</div>';return;}}
  const side=document.getElementById('sidebar');
  side.innerHTML=hits.map((h,i)=>
    `<div class="hit-item" id="hi-${{i}}" onclick="selectHit(${{i}})">
      <div class="hit-name">${{esc(h.filename)}}<span class="hit-count">${{h.total_hits}} match${{h.total_hits!==1?'es':''}}</span></div>
      <div class="hit-meta">${{esc((h.description||'').slice(0,55))||'&nbsp;'}}</div>
    </div>`
  ).join('');
}}

async function selectHit(idx){{
  document.querySelectorAll('.hit-item').forEach((el,i)=>el.classList.toggle('sel',i===idx));
  const h=_hits[idx];if(!h)return;
  const content=document.getElementById('content');

  // Show snippets immediately
  let html=`<div class="src-wrap">
    <div class="src-hdr">
      <span class="src-hdr-name">${{esc(h.filename)}}</span>
      <span class="src-hdr-meta">${{esc(h.file_type?.toUpperCase()||'')}}</span>
      <a href="/admin/sqr/${{encodeURIComponent(h.filename)}}" target="_blank"
         style="color:#22aa66;font-size:11px">Open in SQR Explorer &#x2197;</a>
    </div>`;

  if((h.snippets||[]).length){{
    html+=`<div class="snippets"><div class="snip-lbl">Matching lines</div>`;
    for(const sn of h.snippets){{
      html+='<div class="snip-block">';
      sn.context.forEach((ln,ci)=>{{
        const lineNo=sn.line_no-(sn.match_offset||0)+ci;
        const isMatch=ci===(sn.match_offset||0);
        const escaped=esc(ln);
        const highlighted=isMatch
          ?escaped.replace(new RegExp(esc(_curQ).replace(/[.*+?^${{}}()|[\]\\\\]/g,'\\\\$&'),'gi'),m=>`<span class="snip-match">${{m}}</span>`)
          :escaped;
        html+=`<span class="snip-lineno">${{lineNo}}</span>${{isMatch?'<span class="snip-match-line">'+highlighted+'</span>':highlighted}}\\n`;
      }});
      html+='</div>';
    }}
    html+='</div>';
  }}

  html+=`<div class="src-full">
    <div class="src-full-hdr">
      <span>Full Source</span>
      <span style="color:#22aa66;font-size:10px">${{h.total_hits}} match${{h.total_hits!==1?'es':''}}</span>
    </div>
    <div class="src-inner" id="src-body">Loading source…</div>
  </div></div>`;
  content.innerHTML=html;

  // Load full source
  if(_srcCache[h.filename]){{
    document.getElementById('src-body').innerHTML=_srcCache[h.filename];
    return;
  }}
  try{{
    const d=await fetch(`/api/sqr/program/${{encodeURIComponent(h.filename)}}/source`).then(r=>r.json());
    const src=d.source||d.content||'';
    const highlighted=highlightSQR(src,_curQ);
    _srcCache[h.filename]=highlighted;
    const el=document.getElementById('src-body');
    if(el)el.innerHTML=highlighted;
  }}catch(e){{
    const el=document.getElementById('src-body');
    if(el)el.innerHTML=`<span style="color:#445">Could not load source: ${{esc(String(e))}}</span>`;
  }}
}}

{f"document.addEventListener('DOMContentLoaded',()=>doSearch());" if preload else ""}
window.onEnvChange=()=>{{}};
</script>
""")


# ── helpers ───────────────────────────────────────────────────────────────────

def _esc_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


# ── SQR Include Dependency Graph ──────────────────────────────────────────────

@router.get("/sqrdeps", response_class=HTMLResponse)
def sqr_deps_page(q: str = ""):
    """SQR Include Dependency Graph — visualize the SQC include tree."""
    preload = q.strip()
    content = f"""
<style>
*{{box-sizing:border-box}}
.ds-toolbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.ds-input{{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 10px;font-size:12px;border-radius:3px;width:300px}}
.ds-input:focus{{outline:none;border-color:#00e5ff}}
.ds-btn{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
.ds-btn:hover{{background:#33eeff}}
.ds-btn.sec{{background:transparent;border:1px solid #00e5ff44;color:#00e5ff}}
.ds-btn.sec:hover{{border-color:#00e5ff;background:rgba(0,229,255,.08)}}
.main-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px 16px}}
@media(max-width:900px){{.main-grid{{grid-template-columns:1fr}}}}
.panel{{background:#06121a;border:1px solid #00e5ff1a;border-radius:6px;display:flex;flex-direction:column;overflow:hidden}}
.panel-hdr{{padding:8px 14px;border-bottom:1px solid #00e5ff1a;font-size:11px;font-weight:bold;color:#00e5ff;text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:8px}}
.panel-body{{flex:1;overflow:auto;padding:10px 14px;max-height:420px}}
.tree-node{{margin:0;padding:0;list-style:none}}
.tree-toggle{{cursor:pointer;user-select:none;font-size:11px;color:#00e5ff;margin-right:4px;display:inline-block;width:12px;text-align:center}}
.tree-file{{font-family:monospace;font-size:12px;color:#d7faff}}
.tree-file.sqr{{color:#00e5ff}}
.tree-file.sqc{{color:#7fe0a0}}
.tree-file.unindexed{{color:#334;font-style:italic}}
.tree-file.cyclic{{color:#ff8800}}
.tree-children{{margin-left:16px;border-left:1px solid #00e5ff18;padding-left:8px}}
.empty{{color:#334;font-size:12px;padding:20px}}
.badge{{display:inline-block;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700;margin-left:4px}}
.badge.sqr{{background:#00e5ff18;color:#00e5ff;border:1px solid #00e5ff33}}
.badge.sqc{{background:#7fe0a018;color:#7fe0a0;border:1px solid #7fe0a033}}
.badge.num{{background:#0a1f2e;color:#7faab2;border:1px solid #1a3a4a}}
.meta-bar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 16px 0;font-size:12px}}
.meta-item{{color:#556}}.meta-val{{color:#d7faff;font-family:monospace}}
.used-row{{padding:3px 0;font-size:12px;font-family:monospace;color:#d7faff}}
.used-row a{{color:#00e5ff;text-decoration:none}}
.used-row a:hover{{text-decoration:underline}}
.used-row .ft{{font-size:10px;color:#445;margin-left:4px}}
#status{{font-size:11px;color:#445;margin-left:auto}}
.graph-panel{{background:#06121a;border:1px solid #00e5ff1a;border-radius:6px;overflow:hidden;margin:0 16px 14px}}
.graph-hdr{{padding:8px 14px;border-bottom:1px solid #00e5ff1a;font-size:11px;font-weight:bold;color:#00e5ff;text-transform:uppercase;letter-spacing:.05em}}
canvas{{display:block;background:#030d14}}
</style>

<div class="ds-toolbar">
  <a href="/admin/sqr" style="color:#7faab2;font-size:12px;text-decoration:none">← SQR Explorer</a>
  <input class="ds-input" id="searchInput" placeholder="Enter filename (e.g. battimes.sqr or setenv.sqc)"
         value="{_esc_attr(preload)}" onkeydown="if(event.key==='Enter')load()">
  <button class="ds-btn" onclick="load()">Analyze</button>
  <span id="status"></span>
</div>

<div id="metaBar" class="meta-bar" style="display:none"></div>
<div id="graphWrap" style="display:none">
  <div class="graph-panel">
    <div class="graph-hdr">Include Graph</div>
    <canvas id="graphCanvas" height="260"></canvas>
  </div>
</div>
<div class="main-grid" id="mainGrid" style="display:none">
  <div class="panel">
    <div class="panel-hdr"><span>Includes (forward tree)</span><span class="badge num" id="fwdCount">0</span></div>
    <div class="panel-body" id="fwdPanel"><div class="empty">No data yet</div></div>
  </div>
  <div class="panel">
    <div class="panel-hdr"><span>Included By (reverse)</span><span class="badge num" id="revCount">0</span></div>
    <div class="panel-body" id="revPanel"><div class="empty">No data yet</div></div>
  </div>
</div>

<script>
{_ESC_JS}
const $ = id => document.getElementById(id);
function fileExt(f){{return (f||'').split('.').pop().toLowerCase()}}
function fileClass(f,indexed,cyclic){{
  if(cyclic) return 'cyclic';
  if(!indexed) return 'unindexed';
  return fileExt(f)==='sqr'?'sqr':'sqc';
}}
function buildTreeHTML(nodes){{
  if(!nodes||!nodes.length) return '';
  let html='<ul class="tree-node">';
  for(const n of nodes){{
    const hasKids=n.children&&n.children.length>0;
    const cls=fileClass(n.filename,n.indexed!==false,n.cycle||n.cyclic);
    const toggle=hasKids?`<span class="tree-toggle" onclick="toggleNode(this)">&#9656;</span>`
                        :`<span class="tree-toggle" style="opacity:0">·</span>`;
    const link=(n.indexed!==false&&!n.cycle&&!n.cyclic)
      ?`<a href="/admin/sqrdeps?q=${{encodeURIComponent(n.filename)}}" style="color:inherit;text-decoration:none">${{esc(n.filename)}}</a>`
      :esc(n.filename);
    const note=(n.cycle||n.cyclic)?' <span style="color:#ff8800;font-size:10px">[cyclic]</span>'
              :(!n.indexed&&n.indexed!==undefined?' <span style="color:#334;font-size:10px">[not indexed]</span>':'');
    const kids=hasKids?`<div class="tree-children" style="display:none">${{buildTreeHTML(n.children)}}</div>`:'';
    html+=`<li style="padding:2px 0">${{toggle}}<span class="tree-file ${{cls}}">${{link}}</span>${{note}}${{kids}}</li>`;
  }}
  return html+'</ul>';
}}
function toggleNode(el){{
  const li=el.closest('li');
  const kids=li.querySelector('.tree-children');
  if(!kids) return;
  const open=kids.style.display!=='none';
  kids.style.display=open?'none':'block';
  el.innerHTML=open?'&#9656;':'&#9662;';
}}
function buildRevHTML(rows){{
  if(!rows||!rows.length) return '<div class="empty">Nothing includes this file.</div>';
  return rows.map(r=>{{
    const fn=r.fn||r.filename||r;
    const ext=fileExt(fn);
    return `<div class="used-row"><a href="/admin/sqrdeps?q=${{encodeURIComponent(fn)}}">${{esc(fn)}}</a><span class="ft badge ${{ext}}">${{ext.toUpperCase()}}</span></div>`;
  }}).join('');
}}

let _simFrame=null;
function drawGraph(filename,direct_includes,used_by_direct){{
  const canvas=$('graphCanvas');
  if(!canvas) return;
  canvas.width=canvas.parentElement.clientWidth||800;
  const W=canvas.width,H=260;
  const ctx=canvas.getContext('2d');
  const nodeMap={{}};
  const edges=[];
  function addNode(id,type){{if(!nodeMap[id])nodeMap[id]={{id,type,x:W/2+(Math.random()-.5)*200,y:H/2+(Math.random()-.5)*80,vx:0,vy:0}};}}
  addNode(filename,'root');
  for(const inc of (direct_includes||[])){{addNode(inc,'inc');edges.push({{s:filename,d:inc}});}}
  for(const u of (used_by_direct||[])){{const fn=u.fn||u.filename||u;addNode(fn,'user');edges.push({{s:fn,d:filename}});}}
  const nodes=Object.values(nodeMap);
  if(nodes.length<2){{$('graphWrap').style.display='none';return;}}
  $('graphWrap').style.display='block';
  let frame=0;
  function tick(){{
    for(const n of nodes){{n.vx*=0.85;n.vy*=0.85;}}
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){{
      const a=nodes[i],b=nodes[j];let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1;
      const f=1200/(d*d);a.vx-=f*dx/d;a.vy-=f*dy/d;b.vx+=f*dx/d;b.vy+=f*dy/d;
    }}
    for(const e of edges){{
      const a=nodeMap[e.s],b=nodeMap[e.d];if(!a||!b) continue;
      const dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)||1,ideal=120,f=(d-ideal)*0.04;
      a.vx+=f*dx/d;a.vy+=f*dy/d;b.vx-=f*dx/d;b.vy-=f*dy/d;
    }}
    for(const n of nodes){{n.vx+=(W/2-n.x)*0.005;n.vy+=(H/2-n.y)*0.005;n.x=Math.max(60,Math.min(W-60,n.x+n.vx));n.y=Math.max(20,Math.min(H-20,n.y+n.vy));}}
  }}
  function render(){{
    for(let i=0;i<6;i++) tick();
    ctx.clearRect(0,0,W,H);
    ctx.strokeStyle='#00e5ff22';ctx.lineWidth=1;
    for(const e of edges){{
      const a=nodeMap[e.s],b=nodeMap[e.d];if(!a||!b) continue;
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
      const ang=Math.atan2(b.y-a.y,b.x-a.x),r=14;
      const tx=b.x-r*Math.cos(ang),ty=b.y-r*Math.sin(ang);
      ctx.beginPath();ctx.moveTo(tx,ty);ctx.lineTo(tx-8*Math.cos(ang-.4),ty-8*Math.sin(ang-.4));
      ctx.lineTo(tx-8*Math.cos(ang+.4),ty-8*Math.sin(ang+.4));ctx.closePath();
      ctx.fillStyle='#00e5ff33';ctx.fill();
    }}
    for(const n of nodes){{
      const col=n.type==='root'?'#00e5ff':n.type==='inc'?'#7fe0a0':'#ff8844';
      const r=n.type==='root'?14:10;
      ctx.beginPath();ctx.arc(n.x,n.y,r,0,Math.PI*2);
      ctx.fillStyle=col+'22';ctx.fill();ctx.strokeStyle=col;ctx.lineWidth=n.type==='root'?2:1.5;ctx.stroke();
      ctx.fillStyle=col;ctx.font=`${{n.type==='root'?11:10}}px monospace`;ctx.textAlign='center';ctx.textBaseline='middle';
      const lbl=n.id.length>16?n.id.slice(0,15)+'…':n.id;ctx.fillText(lbl,n.x,n.y+r+10);
    }}
    if(++frame<120) requestAnimationFrame(render);
  }}
  render();
}}

async function load(){{
  const fn=($('searchInput').value||'').trim();
  if(!fn){{$('status').textContent='Enter a filename first.';return;}}
  $('status').textContent='Loading…';
  $('mainGrid').style.display='none';
  $('metaBar').style.display='none';
  $('graphWrap').style.display='none';
  const data=await fetch(`/api/sqr/deps/${{encodeURIComponent(fn)}}`).then(r=>r.json()).catch(e=>({{error:String(e)}}));
  $('status').textContent='';
  if(data.error){{$('status').textContent='Error: '+data.error;return;}}
  const m=data.meta||{{}};
  const ext=fileExt(data.filename);
  $('metaBar').innerHTML=`
    <span class="badge ${{ext}}">${{ext.toUpperCase()}}</span>
    <span class="meta-item">File: <span class="meta-val">${{esc(data.filename)}}</span></span>
    ${{m.description?`<span class="meta-item">Desc: <span class="meta-val">${{esc(m.description)}}</span></span>`:''}}
    <span class="meta-item">Direct includes: <span class="meta-val">${{(data.direct_includes||[]).length}}</span></span>
    <span class="meta-item">Total deps: <span class="meta-val">${{(data.all_includes||[]).length}}</span></span>
    <span class="meta-item">Used by (direct): <span class="meta-val">${{(data.used_by_direct||[]).length}}</span></span>
    <span class="meta-item">Used by (all): <span class="meta-val">${{(data.used_by_all||[]).length}}</span></span>
    ${{!data.meta?'<span style="color:#ff8800;font-size:11px">&#x26A0; Not in index</span>':''}}
  `;
  $('metaBar').style.display='flex';
  $('fwdPanel').innerHTML=buildTreeHTML(data.include_tree||[])||'<div class="empty">No includes.</div>';
  $('fwdCount').textContent=(data.all_includes||[]).length;
  const revDirect=data.used_by_direct||[];
  const revAll=data.used_by_all||[];
  let revHtml='';
  if(revAll.length){{
    if(revDirect.length){{
      revHtml+=`<div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Direct (${{revDirect.length}})</div>`;
      revHtml+=buildRevHTML(revDirect);
    }}
    const indirect=revAll.filter(fn=>!revDirect.find(d=>(d.fn||d.filename||d)===fn));
    if(indirect.length){{
      revHtml+=`<div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:.05em;margin:10px 0 6px">Indirect (${{indirect.length}})</div>`;
      revHtml+=indirect.map(fn=>{{
        const ext2=fileExt(fn);
        return `<div class="used-row"><a href="/admin/sqrdeps?q=${{encodeURIComponent(fn)}}">${{esc(fn)}}</a><span class="ft badge ${{ext2}}">${{ext2.toUpperCase()}}</span></div>`;
      }}).join('');
    }}
  }} else revHtml='<div class="empty">No programs include this file.</div>';
  $('revPanel').innerHTML=revHtml;
  $('revCount').textContent=revAll.length;
  $('mainGrid').style.display='grid';
  drawGraph(data.filename,data.direct_includes,data.used_by_direct);
}}

{"document.addEventListener('DOMContentLoaded',()=>load());" if preload else ""}
window.onEnvChange=()=>{{}};
</script>
"""
    return _shell("SQR Dependency Graph", "sqrdeps", content=content)


# ── SQR Environment Comparison ────────────────────────────────────────────────

@router.get("/sqrcompare", response_class=HTMLResponse)
def sqr_compare_page():
    """SQR environment side-by-side comparison (e.g. HCM vs FSCM)."""
    content = f"""
<style>
*{{box-sizing:border-box}}
.cmp-toolbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.cmp-sel{{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px;border-radius:3px}}
.cmp-btn{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
.cmp-btn:hover{{background:#33eeff}}
.stat-row{{display:flex;gap:10px;flex-wrap:wrap;padding:12px 16px}}
.stat-card{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:8px 16px;min-width:110px}}
.stat-num{{font-size:20px;font-weight:bold;font-family:monospace}}
.stat-lbl{{font-size:10px;color:#445;margin-top:2px}}
.stat-card.only-a .stat-num{{color:#ff8844}}
.stat-card.only-b .stat-num{{color:#44aaff}}
.stat-card.changed .stat-num{{color:#ffcc44}}
.stat-card.same .stat-num{{color:#00cc66}}
.tabs{{display:flex;gap:0;padding:0 16px;border-bottom:1px solid #00e5ff22}}
.tab{{padding:7px 16px;cursor:pointer;font-size:12px;color:#445;border-bottom:2px solid transparent}}
.tab.active{{color:#00e5ff;border-bottom-color:#00e5ff}}
.tab-content{{display:none;padding:10px 16px}}
.tab-content.active{{display:block}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:5px 10px;border-bottom:1px solid #00e5ff22;color:#445;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
td{{padding:5px 10px;border-bottom:1px solid #0a1c28;font-family:monospace;font-size:11px}}
tr:hover td{{background:#0a161e}}
.empty{{padding:24px;text-align:center;color:#334;font-size:12px}}
.diff-val{{color:#ffcc44}}
.same-val{{color:#445}}
.ft-sqr{{color:#00e5ff}}.ft-sqc{{color:#7fe0a0}}
a{{color:#00e5ff;text-decoration:none}}a:hover{{text-decoration:underline}}
#status{{font-size:11px;color:#445;margin-left:auto}}
</style>

<div class="cmp-toolbar">
  <a href="/admin/sqr" style="color:#7faab2;font-size:12px;text-decoration:none">← SQR Explorer</a>
  <select class="cmp-sel" id="envA"><option>HCM</option><option>FSCM</option></select>
  <span style="color:#445;font-size:12px">vs</span>
  <select class="cmp-sel" id="envB"><option>FSCM</option><option>HCM</option></select>
  <select class="cmp-sel" id="diffMode" title="Exact = raw byte comparison. Normalized = ignore comment lines and whitespace-only differences.">
    <option value="exact">Exact match</option>
    <option value="normalized">Ignore whitespace/comments</option>
  </select>
  <button class="cmp-btn" onclick="load()">Compare</button>
  <span id="status"></span>
</div>

<div class="stat-row" id="statRow" style="display:none"></div>

<div class="tabs" id="tabBar" style="display:none">
  <div class="tab active" onclick="switchTab('changed',this)">Changed</div>
  <div class="tab" onclick="switchTab('onlyA',this)" id="tabOnlyA">Only in A</div>
  <div class="tab" onclick="switchTab('onlyB',this)" id="tabOnlyB">Only in B</div>
  <div class="tab" onclick="switchTab('same',this)">Identical</div>
</div>
<div id="tab-changed" class="tab-content active"></div>
<div id="tab-onlyA"   class="tab-content"></div>
<div id="tab-onlyB"   class="tab-content"></div>
<div id="tab-same"    class="tab-content"></div>

<script>
{_ESC_JS}
const $ = id => document.getElementById(id);

function switchTab(name, el){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  $('tab-'+name).classList.add('active');
}}

function ftClass(ft){{return ft==='sqr'?'ft-sqr':'ft-sqc';}}

function renderSingle(rows, env, emptyMsg){{
  if(!rows.length) return `<div class="empty">${{emptyMsg}}</div>`;
  return `<table><thead><tr>
    <th>File</th><th>Type</th><th>PS_ Tables</th><th>Description</th>
  </tr></thead><tbody>`+
  rows.map(r=>`<tr>
    <td><a href="/admin/sqr/${{encodeURIComponent(r.filename)}}">${{esc(r.filename)}}</a></td>
    <td><span class="${{ftClass(r.file_type)}}">${{esc(r.file_type||'')}}</span></td>
    <td style="color:#00e5ff">${{r.table_count||0}}</td>
    <td style="color:#7faab2">${{esc(r.description||'')}}</td>
  </tr>`).join('')+'</tbody></table>';
}}

function renderChanged(rows, labelA, labelB){{
  if(!rows.length) return '<div class="empty">No differences found between environments.</div>';
  return `<table><thead><tr>
    <th>File</th><th>Type</th>
    <th>Tables (${{esc(labelA)}})</th><th>Tables (${{esc(labelB)}})</th>
    <th>Includes (${{esc(labelA)}})</th><th>Includes (${{esc(labelB)}})</th>
    <th>Content Hash</th>
  </tr></thead><tbody>`+
  rows.filter(r=>r.changed).map(r=>{{
    const tDiff=r.table_count_a!==r.table_count_b;
    const iDiff=r.include_count_a!==r.include_count_b;
    const hDiff=r.content_hash_a&&r.content_hash_b&&r.content_hash_a!==r.content_hash_b;
    let hashLabel = hDiff?'DIFFERS':(r.content_hash_a?'SAME':'—');
    if (hDiff && r.content_normalized_same === true) hashLabel = 'DIFFERS (whitespace/comments only)';
    return `<tr>
      <td><a href="/admin/sqr/${{encodeURIComponent(r.filename)}}">${{esc(r.filename)}}</a></td>
      <td><span class="${{ftClass(r.file_type)}}">${{esc(r.file_type||'')}}</span></td>
      <td class="${{tDiff?'diff-val':'same-val'}}">${{r.table_count_a||0}}</td>
      <td class="${{tDiff?'diff-val':'same-val'}}">${{r.table_count_b||0}}</td>
      <td class="${{iDiff?'diff-val':'same-val'}}">${{r.include_count_a||0}}</td>
      <td class="${{iDiff?'diff-val':'same-val'}}">${{r.include_count_b||0}}</td>
      <td style="font-size:10px;color:${{hDiff?'#ffcc44':'#445'}}">${{hashLabel}}</td>
    </tr>`;
  }}).join('')+'</tbody></table>';
}}

async function load(){{
  const envA=$('envA').value, envB=$('envB').value;
  const diffMode=$('diffMode').value;
  if(envA===envB){{$('status').textContent='Select different environments.';return;}}
  $('status').textContent='Loading…';
  $('statRow').style.display='none';
  $('tabBar').style.display='none';
  const data=await fetch(`/api/sqr/envcompare?env_a=${{encodeURIComponent(envA)}}&env_b=${{encodeURIComponent(envB)}}&diff_mode=${{diffMode}}`).then(r=>r.json()).catch(e=>({{error:String(e)}}));
  $('status').textContent='';
  if(data.error){{$('status').textContent='Error: '+data.error;return;}}
  const c=data.counts||{{}};
  $('statRow').innerHTML=`
    <div class="stat-card"><div class="stat-num">${{c.total_a||0}}</div><div class="stat-lbl">${{esc(data.label_a)}} total</div></div>
    <div class="stat-card"><div class="stat-num">${{c.total_b||0}}</div><div class="stat-lbl">${{esc(data.label_b)}} total</div></div>
    <div class="stat-card changed"><div class="stat-num">${{c.changed||0}}</div><div class="stat-lbl">Changed</div></div>
    <div class="stat-card same"><div class="stat-num">${{c.identical||0}}</div><div class="stat-lbl">Identical</div></div>
    <div class="stat-card only-a"><div class="stat-num">${{c.only_a||0}}</div><div class="stat-lbl">Only in ${{esc(data.label_a)}}</div></div>
    <div class="stat-card only-b"><div class="stat-num">${{c.only_b||0}}</div><div class="stat-lbl">Only in ${{esc(data.label_b)}}</div></div>
  `;
  $('statRow').style.display='flex';
  $('tabOnlyA').textContent=`Only in ${{data.label_a}} (${{c.only_a||0}})`;
  $('tabOnlyB').textContent=`Only in ${{data.label_b}} (${{c.only_b||0}})`;
  $('tab-changed').innerHTML=renderChanged(data.in_both||[],data.label_a,data.label_b);
  $('tab-onlyA').innerHTML=renderSingle(data.only_a||[],data.label_a,`No files exist only in ${{data.label_a}}.`);
  $('tab-onlyB').innerHTML=renderSingle(data.only_b||[],data.label_b,`No files exist only in ${{data.label_b}}.`);
  $('tab-same').innerHTML=renderSingle((data.in_both||[]).filter(r=>!r.changed),'',' All shared files have differences.');
  $('tabBar').style.display='flex';
}}

document.addEventListener('DOMContentLoaded',()=>load());
window.onEnvChange=()=>{{}};
</script>
"""
    return _shell("SQR Environment Comparison", "sqrcompare", content=content)


@router.get("/sqroverrides", response_class=HTMLResponse)
def sqr_overrides_page():
    """SQR Override Intelligence: delivered-only / custom-only / overridden
    categorization per environment, beyond the plain duplicate-filename check."""
    content = f"""
<style>
*{{box-sizing:border-box}}
.ov-toolbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.ov-sel{{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px;border-radius:3px}}
.ov-btn{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
.ov-btn:hover{{background:#33eeff}}
.stat-row{{display:flex;gap:10px;flex-wrap:wrap;padding:12px 16px}}
.stat-card{{background:#0a161e;border:1px solid #00e5ff22;border-radius:4px;padding:8px 16px;min-width:140px}}
.stat-num{{font-size:20px;font-weight:bold;font-family:monospace}}
.stat-lbl{{font-size:10px;color:#445;margin-top:2px}}
.stat-card.overridden .stat-num{{color:#ffcc44}}
.stat-card.custom-only .stat-num{{color:#44aaff}}
.stat-card.delivered-only .stat-num{{color:#556}}
.tabs{{display:flex;gap:0;padding:0 16px;border-bottom:1px solid #00e5ff22}}
.tab{{padding:7px 16px;cursor:pointer;font-size:12px;color:#445;border-bottom:2px solid transparent}}
.tab.active{{color:#00e5ff;border-bottom-color:#00e5ff}}
.tab-content{{display:none;padding:10px 16px}}
.tab-content.active{{display:block}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:5px 10px;border-bottom:1px solid #00e5ff22;color:#445;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
td{{padding:5px 10px;border-bottom:1px solid #0a1c28;font-family:monospace;font-size:11px}}
tr:hover td{{background:#0a161e}}
.empty{{padding:24px;text-align:center;color:#334;font-size:12px}}
.note{{padding:10px 16px;font-size:11px;color:#556;border-bottom:1px solid #0a1c28}}
a{{color:#00e5ff;text-decoration:none}}a:hover{{text-decoration:underline}}
#status{{font-size:11px;color:#445;margin-left:auto}}
</style>

<div class="ov-toolbar">
  <a href="/admin/sqr" style="color:#7faab2;font-size:12px;text-decoration:none">&larr; SQR Explorer</a>
  <select class="ov-sel" id="envSel"><option value="">All environments</option></select>
  <button class="ov-btn" onclick="load()">Analyze</button>
  <span id="status"></span>
</div>

<div class="note">
  <b style="color:#7faab2">overridden</b> = filename in both delivered and custom trees (a genuine customization) &middot;
  <b style="color:#7faab2">custom-only</b> = filename in custom but not delivered (new custom program, or a former override whose delivered baseline was later removed &mdash; a single snapshot can't tell these apart) &middot;
  <b style="color:#7faab2">delivered-only</b> = shown as a count only, not a browsable list (can be tens of thousands of rows)
</div>

<div id="body"><div class="empty">Select an environment (or leave blank for all) and click Analyze.</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);

async function loadEnvs() {
  try {
    const r = await fetch('/api/sqr/sources');
    const d = await r.json();
    const sel = $('envSel');
    (d.envs || []).forEach(e => {
      const opt = document.createElement('option');
      opt.value = e; opt.textContent = e;
      sel.appendChild(opt);
    });
  } catch(e) {}
}

async function load() {
  const env = $('envSel').value;
  $('status').textContent = 'Loading…';
  $('body').innerHTML = '<div class="empty">Loading…</div>';
  try {
    const url = '/api/sqr/override-summary' + (env ? `?env=${encodeURIComponent(env)}` : '');
    const r = await fetch(url);
    const data = await r.json();
    $('status').textContent = '';
    render(data);
  } catch(e) {
    $('status').textContent = '';
    $('body').innerHTML = `<div class="empty">Error: ${esc(String(e))}</div>`;
  }
}

function renderList(items, cols) {
  if (!items.length) return '<div class="empty">None found.</div>';
  const header = cols.map(c => `<th>${esc(c.label)}</th>`).join('');
  const rows = items.map(it => `<tr>${cols.map(c => `<td>${esc(it[c.key] ?? '—')}</td>`).join('')}</tr>`).join('');
  return `<table><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`;
}

function render(data) {
  const envs = Object.keys(data);
  if (!envs.length) {
    $('body').innerHTML = '<div class="empty">No delivered+custom source pairs configured for this environment.</div>';
    return;
  }

  let html = '';
  envs.forEach(env => {
    const d = data[env];
    const c = d.counts || {};
    html += `<h2 style="padding:12px 16px 0;margin:0;color:#00e5ff;font-size:13px">${esc(env)}</h2>`;
    html += `<div class="stat-row">
      <div class="stat-card overridden"><div class="stat-num">${c.overridden||0}</div><div class="stat-lbl">Overridden</div></div>
      <div class="stat-card custom-only"><div class="stat-num">${c.custom_only||0}</div><div class="stat-lbl">Custom-Only</div></div>
      <div class="stat-card delivered-only"><div class="stat-num">${c.delivered_only||0}</div><div class="stat-lbl">Delivered-Only (count)</div></div>
    </div>`;
    const uid = env.replace(/[^A-Za-z0-9]/g, '');
    html += `<div class="tabs" id="tabs-${uid}">
      <div class="tab active" onclick="switchOvTab('${uid}','overridden')">Overridden (${c.overridden||0})</div>
      <div class="tab" onclick="switchOvTab('${uid}','customonly')">Custom-Only (${c.custom_only||0})</div>
    </div>`;
    html += `<div id="tab-${uid}-overridden" class="tab-content active">
      ${renderList(d.overridden||[], [
        {key:'filename',label:'Filename'}, {key:'file_type',label:'Type'},
        {key:'description',label:'Description'},
        {key:'delivered_key',label:'Delivered Source'}, {key:'custom_key',label:'Custom Source'},
      ])}
    </div>`;
    html += `<div id="tab-${uid}-customonly" class="tab-content">
      ${renderList(d.custom_only||[], [
        {key:'filename',label:'Filename'}, {key:'file_type',label:'Type'},
        {key:'description',label:'Description'}, {key:'custom_key',label:'Custom Source'},
      ])}
    </div>`;
  });
  $('body').innerHTML = html;
}

function switchOvTab(uid, which) {
  const tabsBar = document.getElementById('tabs-' + uid);
  if (tabsBar) tabsBar.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const overridden = document.getElementById(`tab-${uid}-overridden`);
  const customOnly = document.getElementById(`tab-${uid}-customonly`);
  if (overridden) overridden.classList.toggle('active', which === 'overridden');
  if (customOnly) customOnly.classList.toggle('active', which === 'customonly');
  if (tabsBar) {
    const idx = which === 'overridden' ? 0 : 1;
    const tabs = tabsBar.querySelectorAll('.tab');
    if (tabs[idx]) tabs[idx].classList.add('active');
  }
}

loadEnvs();
window.onEnvChange=()=>{};
</script>
"""
    return _shell("SQR Override Intelligence", "sqroverrides", content=content)

