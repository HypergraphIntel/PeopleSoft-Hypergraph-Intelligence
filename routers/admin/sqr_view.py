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
let _page = 1, _debTimer = null;

async function loadStats() {
  try {
    const r = await fetch('/api/sqr/stats');
    const d = await r.json();
    $('sTot').textContent = d.programs ?? '—';
    $('sTbl').textContent = d.distinct_ps_tables ?? '—';
    $('sTs').textContent  = d.last_indexed ? d.last_indexed.replace('T',' ').replace('Z','') : 'Not indexed';
    // count sqr vs sqc
    const r2 = await fetch('/api/sqr/programs?type=sqr&per_page=1');
    const d2 = await r2.json();
    $('sSqr').textContent = d2.total ?? '—';
    $('sSqc').textContent = (d.programs - (d2.total||0)) || '—';
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
  let url = `/api/sqr/programs?page=${_page}&per_page=50`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  if (t) url += `&type=${t}`;

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
      <div class="tab" onclick="switchTab('src')">Source</div>
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
  `;
  // lazy-load source when tab opened
  _detail = d;
}

let _detail = null, _srcLoaded = false;

function switchTab(tab) {
  document.querySelectorAll('.tab-row .tab').forEach((t,i) => {
    t.classList.toggle('on', (tab==='meta'&&i===0)||(tab==='src'&&i===1));
  });
  $('paneOverview').style.display = tab === 'meta' ? '' : 'none';
  $('paneSrc').style.display      = tab === 'src'  ? '' : 'none';
  if (tab === 'src' && !_srcLoaded) loadSource();
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
