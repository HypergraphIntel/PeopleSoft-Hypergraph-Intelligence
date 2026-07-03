"""
COBOL Explorer — admin UI.

Routes:
  GET /admin/cobol            — list/search all indexed programs & copybooks
  GET /admin/cobol/{filename} — program/copybook detail (tables, COPY deps, calls, source)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from routers.admin._core import _shell, _ESC_JS

router = APIRouter(prefix="/admin", tags=["DeathStar Admin"])


@router.get("/cobol", response_class=HTMLResponse)
def cobol_index():
    content = """
<style>
.cbl-toolbar{display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.cbl-search{flex:1;min-width:220px;background:#0a1520;border:1px solid #1a3a4a;
  color:#d7faff;padding:6px 10px;border-radius:4px;font-size:13px}
.cbl-search:focus{outline:none;border-color:#00e5ff}
.cbl-filter{background:#0a1520;border:1px solid #1a3a4a;color:#d7faff;
  padding:6px 10px;border-radius:4px;font-size:13px}
.cbl-btn{padding:5px 14px;border:1px solid rgba(0,229,255,.4);border-radius:4px;
  background:rgba(0,229,255,.07);color:#00e5ff;font-size:12px;cursor:pointer}
.cbl-btn:hover{background:rgba(0,229,255,.15)}
.cbl-btn.green{border-color:rgba(0,255,150,.4);background:rgba(0,255,150,.07);color:#0f9}
.cbl-stats{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.cbl-stat{background:#0a1520;border:1px solid #1a3a4a;border-radius:6px;padding:8px 16px;min-width:120px}
.cbl-stat-val{font-size:22px;font-weight:700;color:#00e5ff}
.cbl-stat-lbl{font-size:10px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px}
.cbl-tbl{width:100%;border-collapse:collapse;font-size:12px}
.cbl-tbl th{text-align:left;padding:6px 10px;border-bottom:1px solid #1a3a4a;
  color:#7faab2;text-transform:uppercase;letter-spacing:.5px;font-weight:600;font-size:10px}
.cbl-tbl td{padding:5px 10px;border-bottom:1px solid #0e2030}
.cbl-tbl tr:hover td{background:#0a1f2e}
.cbl-tbl a{color:#00e5ff;text-decoration:none}
.cbl-tbl a:hover{text-decoration:underline}
.cbl-pg{display:flex;gap:8px;margin-top:12px;align-items:center;font-size:12px;color:#7faab2}
.cbl-pg button{padding:3px 10px;border:1px solid #1a3a4a;background:#0a1520;
  color:#7faab2;border-radius:3px;cursor:pointer;font-size:12px}
.cbl-pg button:hover:not(:disabled){color:#00e5ff;border-color:#00e5ff}
.cbl-pg button:disabled{opacity:.3}
.ingest-bar{background:#0a1520;border:1px solid #1a3a4a;border-radius:6px;
  padding:10px 14px;margin-bottom:16px;font-size:12px;color:#7faab2}
.compiled-y{color:#0f9}.compiled-n{color:#4a6a7a}
</style>

<div class="ingest-bar" id="ingestBar" style="display:none"></div>

<div class="cbl-stats" id="statsRow">
  <div class="cbl-stat"><div class="cbl-stat-val" id="sTot">&mdash;</div><div class="cbl-stat-lbl">Indexed Files</div></div>
  <div class="cbl-stat"><div class="cbl-stat-val" id="sProg">&mdash;</div><div class="cbl-stat-lbl">Programs</div></div>
  <div class="cbl-stat"><div class="cbl-stat-val" id="sCopy">&mdash;</div><div class="cbl-stat-lbl">Copybooks</div></div>
  <div class="cbl-stat"><div class="cbl-stat-val" id="sTbl">&mdash;</div><div class="cbl-stat-lbl">PS_ Tables</div></div>
  <div class="cbl-stat"><div class="cbl-stat-val" id="sTs" style="font-size:11px;color:#7faab2">&mdash;</div><div class="cbl-stat-lbl">Last indexed</div></div>
</div>

<div class="cbl-toolbar">
  <input class="cbl-search" id="searchBox" placeholder="Search programs, copybooks, descriptions…" oninput="debounceSearch()">
  <select class="cbl-filter" id="envFilter" onchange="onEnvChange()">
    <option value="">All environments</option>
  </select>
  <select class="cbl-filter" id="typeFilter" onchange="doSearch(1)">
    <option value="">All types</option>
    <option value="program">Programs only</option>
    <option value="copybook">Copybooks only</option>
  </select>
  <button class="cbl-btn" onclick="doSearch(1)">Search</button>
  <button class="cbl-btn green" id="ingestBtn" onclick="triggerIngest()">Re-index</button>
  <a class="cbl-btn" href="/admin/cobol/analytics" style="text-decoration:none;padding:5px 14px">Analytics</a>
</div>

<div id="resultsArea">
  <div style="color:#7faab2;padding:24px;text-align:center">Loading&hellip;</div>
</div>
<div class="cbl-pg" id="pgBar" style="display:none">
  <button id="pgPrev" onclick="doSearch(_page-1)">&larr; Prev</button>
  <span id="pgInfo"></span>
  <button id="pgNext" onclick="doSearch(_page+1)">Next &rarr;</button>
</div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
let _page = 1, _debTimer = null;

async function loadEnvs() {
  try {
    const r = await fetch('/api/cobol/sources');
    const d = await r.json();
    const sel = $('envFilter');
    (d.envs || []).forEach(e => {
      const opt = document.createElement('option');
      opt.value = e; opt.textContent = e;
      sel.appendChild(opt);
    });
  } catch(e) {}
}

function onEnvChange() { doSearch(1); }

async function loadStats() {
  try {
    const r = await fetch('/api/cobol/stats');
    const d = await r.json();
    $('sTs').textContent = d.last_indexed ? d.last_indexed.replace('T',' ').replace('Z','') : 'Not indexed';
    $('sTot').textContent = d.total ?? '—';
    $('sProg').textContent = d.programs ?? '—';
    $('sCopy').textContent = d.copybooks ?? '—';
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
  let url = `/api/cobol/programs?page=${_page}&per_page=50`;
  if (q)   url += `&q=${encodeURIComponent(q)}`;
  if (t)   url += `&type=${t}`;
  if (env) url += `&env=${encodeURIComponent(env)}`;

  $('resultsArea').innerHTML = '<div style="color:#7faab2;padding:16px">Loading&hellip;</div>';
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
    $('resultsArea').innerHTML = '<div style="color:#7faab2;padding:24px;text-align:center">No programs found. Try re-indexing.</div>';
    $('pgBar').style.display = 'none';
    return;
  }

  let html = `<table class="cbl-tbl"><thead><tr>
    <th>Filename</th><th>Member</th><th>Type</th><th>Description</th>
    <th style="text-align:right">Tables</th><th style="text-align:right">Copies</th>
    <th style="text-align:right">Calls</th><th>Compiled</th>
  </tr></thead><tbody>`;

  for (const r of rows) {
    const badge = r.file_type === 'program'
      ? '<span style="color:#0f9;font-size:10px;font-weight:700">PROGRAM</span>'
      : '<span style="color:#fa0;font-size:10px;font-weight:700">COPYBOOK</span>';
    html += `<tr>
      <td><a href="/admin/cobol/${esc(r.filename)}">${esc(r.filename)}</a></td>
      <td style="color:#aac;font-family:monospace">${esc(r.member_name || '—')}</td>
      <td>${badge}</td>
      <td style="color:#aac">${esc(r.description || '—')}</td>
      <td style="text-align:right;color:${r.table_count>0?'#0af':'#4a6a7a'}">${r.table_count}</td>
      <td style="text-align:right;color:${r.copy_count>0?'#fa0':'#4a6a7a'}">${r.copy_count}</td>
      <td style="text-align:right;color:${r.call_count>0?'#a0f':'#4a6a7a'}">${r.call_count}</td>
      <td class="${r.compiled?'compiled-y':'compiled-n'}">${r.compiled?'✓':'—'}</td>
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
  $('ingestBar').innerHTML = '<span style="color:#fa0">⏳ Indexing COBOL library — this may take a minute. Many delivered .cbl files are owner-only and will be skipped as permission-denied, which is expected.</span>';

  try {
    await fetch('/api/cobol/ingest', { method: 'POST' });
    pollIngest();
  } catch(e) {
    $('ingestBar').innerHTML = `<span style="color:#f55">Error: ${esc(String(e))}</span>`;
    btn.disabled = false;
    btn.textContent = 'Re-index';
  }
}

async function pollIngest() {
  const r = await fetch('/api/cobol/ingest/status');
  const d = await r.json();
  if (d.running) { setTimeout(pollIngest, 2000); return; }
  const btn = $('ingestBtn');
  btn.disabled = false;
  btn.textContent = 'Re-index';
  if (d.last && d.last.status === 'ok') {
    const results = d.last.results || [];
    const total = results.reduce((s,r) => s + (r.indexed||0), 0);
    const denied = results.reduce((s,r) => s + (r.denied||0), 0);
    const errs  = results.reduce((s,r) => s + (r.errors||0), 0);
    $('ingestBar').innerHTML = `<span style="color:#0f9">✓ Indexed ${total} files (${denied} permission-denied, ${errs} other errors) — refreshing…</span>`;
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
    return HTMLResponse(_shell("COBOL Explorer", "cobol", content))


@router.get("/cobol/table/{table_name}", response_class=HTMLResponse)
def cobol_table_detail(table_name: str):
    tbl_upper = table_name.upper()
    content = f"""
<style>
.cbl-tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.cbl-tbl th{{text-align:left;padding:6px 10px;border-bottom:1px solid #1a3a4a;
  color:#7faab2;text-transform:uppercase;font-size:10px;font-weight:600;letter-spacing:.5px}}
.cbl-tbl td{{padding:5px 10px;border-bottom:1px solid #0e2030}}
.cbl-tbl tr:hover td{{background:#0a1f2e}}
.cbl-tbl a{{color:#00e5ff;text-decoration:none}}
.cbl-tbl a:hover{{text-decoration:underline}}
.op-badge{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;
  font-weight:700;margin:1px;vertical-align:middle}}
.op-SELECT{{background:#0af2;color:#0af}}
.op-UPDATE{{background:#fa02;color:#fa0}}
.op-INSERT{{background:#0f92;color:#0f9}}
.op-DELETE{{background:#f552;color:#f55}}
</style>

<a href="/admin/cobol" style="color:#7faab2;font-size:12px;text-decoration:none;
  margin-bottom:14px;display:inline-block">← COBOL Explorer</a>
<h2 style="margin:8px 0 16px;color:#d7faff;font-size:16px">
  PS_ Table: <span style="color:#00e5ff">{tbl_upper}</span>
</h2>
<div id="tableContent"><div style="color:#7faab2;padding:24px">Loading…</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
async function load() {
  const r = await fetch('/api/cobol/table/' + encodeURIComponent(""" + f'"{tbl_upper}"' + """));
  const d = await r.json();
  const progs = d.programs || [];
  if (!progs.length) {
    $('tableContent').innerHTML = '<div style="color:#7faab2;padding:24px">No COBOL programs reference this table.</div>';
    return;
  }
  let html = `<p style="color:#7faab2;font-size:12px;margin-bottom:12px">${progs.length} program(s) reference this table</p>
  <table class="cbl-tbl"><thead><tr>
    <th>Filename</th><th>Type</th><th>Description</th><th>Operations</th>
  </tr></thead><tbody>`;
  for (const p of progs) {
    const ops = (p.operations||'').split(',').filter(Boolean).map(o =>
      `<span class="op-badge op-${esc(o)}">${esc(o)}</span>`).join('');
    const ftBadge = p.file_type === 'program'
      ? '<span style="color:#0f9;font-size:10px;font-weight:700">PROG</span>'
      : '<span style="color:#fa0;font-size:10px;font-weight:700">COPY</span>';
    html += `<tr>
      <td><a href="/admin/cobol/${esc(p.filename)}">${esc(p.filename)}</a></td>
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
    return HTMLResponse(_shell(f"COBOL — {tbl_upper}", "cobol", content))


@router.get("/cobol/analytics", response_class=HTMLResponse)
def cobol_analytics_page():
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
</style>

<a href="/admin/cobol" style="color:#7faab2;font-size:12px;text-decoration:none;margin-bottom:14px;display:inline-block">← COBOL Explorer</a>
<div class="stat-row" id="statRow">
  <div class="stat-box"><div class="stat-val" id="sTot">—</div><div class="stat-lbl">Files</div></div>
  <div class="stat-box"><div class="stat-val" id="sTbl">—</div><div class="stat-lbl">PS_ Tables</div></div>
  <div class="stat-box"><div class="stat-val" id="sRef">—</div><div class="stat-lbl">Table Refs</div></div>
  <div class="stat-box"><div class="stat-val" id="sCopy">—</div><div class="stat-lbl">COPY Refs</div></div>
</div>

<div id="analyticsContent"><div style="color:#7faab2;padding:24px">Loading analytics…</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);
async function load() {
  const [statsRes, anRes] = await Promise.all([
    fetch('/api/cobol/stats'),
    fetch('/api/cobol/analytics'),
  ]);
  const stats = await statsRes.json();
  const an = await anRes.json();

  $('sTot').textContent = stats.total ?? '—';
  $('sTbl').textContent = stats.distinct_ps_tables ?? '—';
  $('sRef').textContent = stats.total_table_refs ?? '—';
  $('sCopy').textContent = stats.total_copies ?? '—';

  renderAnalytics(an);
}

function barPct(val, max) {
  const pct = max > 0 ? Math.round(val / max * 100) : 0;
  return `<div class="bar-wrap"><div class="bar-fill" style="width:${pct}%"></div></div>`;
}

function renderAnalytics(an) {
  const topTbls = an.top_tables || [];
  const topProgs = an.top_programs || [];
  const topCopies = an.top_copies || [];
  const typeBreak = an.type_breakdown || [];

  const maxTbl = topTbls.length ? topTbls[0].program_count : 1;
  const maxProg = topProgs.length ? topProgs[0].table_count : 1;
  const maxCopy = topCopies.length ? topCopies[0].user_count : 1;

  let tblRows = topTbls.map(t => `<tr>
    <td><a href="/admin/cobol/table/${esc(t.table_name)}">${esc(t.table_name)}</a></td>
    <td style="text-align:right;color:#0af">${t.program_count}</td>
    <td style="text-align:right;color:#fa0">${t.program_type_count}</td>
    <td style="width:80px">${barPct(t.program_count, maxTbl)}</td>
  </tr>`).join('');

  let progRows = topProgs.map(p => `<tr>
    <td><a href="/admin/cobol/${esc(p.filename)}">${esc(p.filename)}</a></td>
    <td style="color:#7faab2;font-size:11px;max-width:180px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${esc(p.description||'—')}</td>
    <td style="text-align:right;color:#0af">${p.table_count}</td>
    <td style="text-align:right;color:#fa0">${p.copy_count}</td>
    <td style="text-align:right;color:#7faab2">${p.call_count}</td>
    <td style="width:60px">${barPct(p.table_count, maxProg)}</td>
  </tr>`).join('');

  let copyRows = topCopies.map(c => `<tr>
    <td style="font-family:monospace">${esc(c.copy_name)}</td>
    <td style="text-align:right;color:#0af">${c.user_count}</td>
    <td style="width:80px">${barPct(c.user_count, maxCopy)}</td>
  </tr>`).join('');

  const totalFiles = typeBreak.reduce((s,r) => s + r.cnt, 0) || 1;
  let typeRows = typeBreak.map(r => `<tr>
    <td style="color:#d7faff">${esc(r.typ||'—')}</td>
    <td style="text-align:right;color:#0f9">${r.program_cnt}</td>
    <td style="text-align:right;color:#fa0">${r.copybook_cnt}</td>
    <td style="text-align:right;color:#0af">${r.cnt}</td>
    <td style="width:80px">${barPct(r.cnt, totalFiles)}</td>
  </tr>`).join('');

  $('analyticsContent').innerHTML = `
  <div class="an-grid">
    <div class="an-card" style="grid-column:1/-1">
      <h3>Top 30 PS_ Tables by Reference Count</h3>
      <table class="an-tbl"><thead><tr>
        <th>Table</th><th style="text-align:right">Programs</th>
        <th style="text-align:right">Programs (excl. copybooks)</th><th>Density</th>
      </tr></thead><tbody>${tblRows}</tbody></table>
    </div>
    <div class="an-card" style="grid-column:1/-1">
      <h3>Top 20 Most Complex COBOL Programs (by Table Count)</h3>
      <table class="an-tbl"><thead><tr>
        <th>Filename</th><th>Description</th>
        <th style="text-align:right">Tables</th>
        <th style="text-align:right">COPY</th>
        <th style="text-align:right">CALL</th><th>Complexity</th>
      </tr></thead><tbody>${progRows}</tbody></table>
    </div>
    <div class="an-card">
      <h3>Top 20 Most-COPYd Copybooks</h3>
      <table class="an-tbl"><thead><tr>
        <th>Copybook</th><th style="text-align:right">Users</th><th>Usage</th>
      </tr></thead><tbody>${copyRows}</tbody></table>
    </div>
    <div class="an-card">
      <h3>Delivered vs Custom Breakdown</h3>
      <table class="an-tbl"><thead><tr>
        <th>Source Type</th><th style="text-align:right">Programs</th>
        <th style="text-align:right">Copybooks</th>
        <th style="text-align:right">Total</th><th>Share</th>
      </tr></thead><tbody>${typeRows}</tbody></table>
    </div>
  </div>`;
}

load();
</script>
"""
    return HTMLResponse(_shell("COBOL Analytics", "cobol", content))


@router.get("/cobol/{filename}", response_class=HTMLResponse)
def cobol_detail(filename: str):
    content = f"""
<style>
.cbl-detail-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:900px){{.cbl-detail-grid{{grid-template-columns:1fr}}}}
.cbl-card{{background:#0a1520;border:1px solid #1a3a4a;border-radius:8px;padding:16px}}
.cbl-card h3{{margin:0 0 12px;color:#00e5ff;font-size:13px;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px}}
.cbl-meta{{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:12px}}
.cbl-meta-lbl{{color:#7faab2;white-space:nowrap}}
.cbl-meta-val{{color:#d7faff}}
.cbl-list{{list-style:none;padding:0;margin:0;max-height:320px;overflow-y:auto}}
.cbl-list li{{padding:4px 0;border-bottom:1px solid #0e2030;font-size:12px;color:#aac}}
.cbl-list li:last-child{{border:none}}
.cbl-list a{{color:#00e5ff;text-decoration:none}}
.cbl-list a:hover{{text-decoration:underline}}
.op-badge{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;
  font-weight:700;margin-left:4px;vertical-align:middle}}
.op-SELECT{{background:#0af2;color:#0af}}
.op-UPDATE{{background:#fa02;color:#fa0}}
.op-INSERT{{background:#0f92;color:#0f9}}
.op-DELETE{{background:#f552;color:#f55}}
.back-link{{color:#7faab2;font-size:12px;text-decoration:none;margin-bottom:14px;display:inline-block}}
.back-link:hover{{color:#00e5ff}}
.cbl-hdr{{margin-bottom:16px}}
.cbl-title{{font-size:18px;font-weight:700;color:#d7faff;font-family:monospace}}
.cbl-desc{{font-size:13px;color:#7faab2;margin-top:4px}}
.tab-row{{display:flex;gap:4px;border-bottom:1px solid #1a3a4a;margin-bottom:16px}}
.tab{{padding:6px 16px;font-size:12px;color:#7faab2;cursor:pointer;border-bottom:2px solid transparent;
  border-radius:4px 4px 0 0;user-select:none}}
.tab:hover{{color:#00e5ff}}
.tab.on{{color:#00e5ff;border-bottom-color:#00e5ff;font-weight:600}}
.src-inner{{font-family:monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;word-break:break-word;
  background:#020c14;border:1px solid #0d1b24;border-radius:3px;padding:10px 14px;
  max-height:calc(100vh - 340px);overflow-y:auto}}
</style>

<a class="back-link" href="/admin/cobol">&larr; COBOL Explorer</a>
<div id="detailContent"><div style="color:#7faab2;padding:24px">Loading&hellip;</div></div>

<script>
""" + _ESC_JS + """
const $ = id => document.getElementById(id);

function esc2(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

async function loadDetail() {{
  try {{
    const r = await fetch('/api/cobol/program/' + encodeURIComponent({filename!r}));
    if (!r.ok) {{
      $('detailContent').innerHTML = '<div style="color:#f55;padding:24px">Not found in index. Try re-indexing from <a href="/admin/cobol" style="color:#0af">COBOL Explorer</a>.</div>';
      return;
    }}
    const d = await r.json();
    render(d);
  }} catch(e) {{
    $('detailContent').innerHTML = `<div style="color:#f55;padding:24px">Error: ${{esc(String(e))}}</div>`;
  }}
}}

function opBadges(ops) {{
  return (ops||'').split(',').filter(Boolean).map(o => `<span class="op-badge op-${{esc(o)}}">${{esc(o)}}</span>`).join('');
}}

function render(d) {{
  const badge = d.file_type === 'program'
    ? '<span style="color:#0f9;font-weight:700;font-size:11px">PROGRAM</span>'
    : '<span style="color:#fa0;font-weight:700;font-size:11px">COPYBOOK</span>';

  let tables = (d.tables && d.tables.length)
    ? d.tables.map(t => `<li><a href="/admin/cobol?q=${{encodeURIComponent(t.table_name)}}">${{esc(t.table_name)}}</a>${{opBadges(t.operations)}}</li>`).join('')
    : '<li style="color:#4a6a7a">No PS_ tables referenced (EXEC SQL)</li>';

  let copies = (d.copies && d.copies.length)
    ? d.copies.map(c => `<li><a href="/admin/cobol/${{encodeURIComponent(c)}}.cbl">${{esc(c)}}</a></li>`).join('')
    : '<li style="color:#4a6a7a">No COPY dependencies</li>';

  let calls = (d.calls && d.calls.length)
    ? d.calls.map(c => `<li><a href="/admin/cobol/${{encodeURIComponent(c)}}.cbl">${{esc(c)}}</a></li>`).join('')
    : '<li style="color:#4a6a7a">No static CALL targets</li>';

  $('detailContent').innerHTML = `
    <div class="cbl-hdr">
      <div class="cbl-title">${{esc(d.filename)}} ${{badge}}</div>
      <div class="cbl-desc">${{esc(d.description || 'No description available')}}</div>
    </div>

    <div class="tab-row">
      <div class="tab on" onclick="switchTab('overview')">Overview</div>
      <div class="tab" onclick="switchTab('deps')">Dependency Graph</div>
      <div class="tab" onclick="switchTab('src')">Source</div>
    </div>

    <div id="paneOverview">
      <div class="cbl-card" style="margin-bottom:16px">
        <h3>Metadata</h3>
        <div class="cbl-meta">
          <span class="cbl-meta-lbl">Member</span><span class="cbl-meta-val">${{esc(d.member_name||'—')}}</span>
          <span class="cbl-meta-lbl">Source</span><span class="cbl-meta-val">${{esc(d.source_key||'—')}} (${{esc(d.source_type||'—')}})</span>
          <span class="cbl-meta-lbl">Compiled</span><span class="cbl-meta-val">${{d.compiled ? '✓ binary present' : '— not found in cblbin'}}</span>
          <span class="cbl-meta-lbl">Indexed</span><span class="cbl-meta-val">${{esc((d.indexed_at||'—').replace('T',' ').replace('Z',''))}}</span>
        </div>
      </div>
      <div class="cbl-detail-grid">
        <div class="cbl-card">
          <h3>PS_ Tables Referenced (${{d.tables ? d.tables.length : 0}})</h3>
          <ul class="cbl-list">${{tables}}</ul>
        </div>
        <div class="cbl-card">
          <h3>COPY Dependencies (${{d.copies ? d.copies.length : 0}})</h3>
          <ul class="cbl-list">${{copies}}</ul>
        </div>
        <div class="cbl-card" style="grid-column:1/-1">
          <h3>Static CALL Targets (${{d.calls ? d.calls.length : 0}})</h3>
          <ul class="cbl-list" style="columns:3;column-gap:20px;max-height:280px">${{calls}}</ul>
        </div>
      </div>
    </div>

    <div id="paneDeps" style="display:none">
      <div class="cbl-card">
        <h3>COPY Dependency Graph</h3>
        <div id="depsContent" style="color:#7faab2;font-size:12px;padding:8px">Loading&hellip;</div>
      </div>
    </div>

    <div id="paneSrc" style="display:none">
      <div class="cbl-card">
        <h3>Source</h3>
        <div class="src-inner" id="srcContent">Loading&hellip;</div>
      </div>
    </div>
  `;
}}

let _depsLoaded = false, _srcLoaded = false;

async function switchTab(tab) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  event.target.classList.add('on');
  document.getElementById('paneOverview').style.display = tab === 'overview' ? '' : 'none';
  document.getElementById('paneDeps').style.display = tab === 'deps' ? '' : 'none';
  document.getElementById('paneSrc').style.display = tab === 'src' ? '' : 'none';

  if (tab === 'deps' && !_depsLoaded) {{
    _depsLoaded = true;
    try {{
      const r = await fetch('/api/cobol/deps/' + encodeURIComponent({filename!r}));
      const d = await r.json();
      let html = '';
      html += `<div style="margin-bottom:16px"><b style="color:#00e5ff">Direct COPY (${{d.direct_copies.length}})</b><ul class="cbl-list">` +
        (d.direct_copies.length ? d.direct_copies.map(c => `<li><a href="/admin/cobol/${{encodeURIComponent(c)}}.cbl">${{esc(c)}}</a></li>`).join('') : '<li style="color:#4a6a7a">None</li>') + '</ul></div>';
      html += `<div style="margin-bottom:16px"><b style="color:#fa0">Transitive COPY closure (${{d.all_copies.length}})</b><ul class="cbl-list">` +
        (d.all_copies.length ? d.all_copies.map(c => `<li>${{esc(c)}}</li>`).join('') : '<li style="color:#4a6a7a">None</li>') + '</ul></div>';
      html += `<div style="margin-bottom:16px"><b style="color:#0f9">Used By — Direct (${{d.used_by_direct.length}})</b><ul class="cbl-list">` +
        (d.used_by_direct.length ? d.used_by_direct.map(u => `<li><a href="/admin/cobol/${{encodeURIComponent(u.fn)}}">${{esc(u.fn)}}</a></li>`).join('') : '<li style="color:#4a6a7a">Not COPY\\'d by any indexed program</li>') + '</ul></div>';
      html += `<div><b style="color:#0f9">Used By — Transitive (${{d.used_by_all.length}})</b><ul class="cbl-list">` +
        (d.used_by_all.length ? d.used_by_all.map(u => `<li>${{esc(u)}}</li>`).join('') : '<li style="color:#4a6a7a">None</li>') + '</ul></div>';
      document.getElementById('depsContent').innerHTML = html;
    }} catch(e) {{
      document.getElementById('depsContent').innerHTML = `<span style="color:#f55">Error: ${{esc(String(e))}}</span>`;
    }}
  }}

  if (tab === 'src' && !_srcLoaded) {{
    _srcLoaded = true;
    try {{
      const r = await fetch('/api/cobol/program/' + encodeURIComponent({filename!r}) + '/source');
      if (!r.ok) {{
        const err = await r.json().catch(() => ({{}}));
        document.getElementById('srcContent').innerHTML = `<span style="color:#fa0">${{esc(err.detail || 'Could not load source (permission denied is common for delivered COBOL on this filesystem).')}}</span>`;
        return;
      }}
      const d = await r.json();
      document.getElementById('srcContent').textContent = d.source || '';
    }} catch(e) {{
      document.getElementById('srcContent').innerHTML = `<span style="color:#f55">Error: ${{esc(String(e))}}</span>`;
    }}
  }}
}}

loadDetail();
</script>
"""
    return HTMLResponse(_shell(f"COBOL: {filename}", "cobol", content))


@router.get("/cobolcompare", response_class=HTMLResponse)
def cobol_compare_page():
    """COBOL environment side-by-side comparison (e.g. HCM vs FSCM)."""
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
a{{color:#00e5ff;text-decoration:none}}a:hover{{text-decoration:underline}}
#status{{font-size:11px;color:#445;margin-left:auto}}
</style>

<div class="cmp-toolbar">
  <a href="/admin/cobol" style="color:#7faab2;font-size:12px;text-decoration:none">&larr; COBOL Explorer</a>
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

function renderSingle(rows, env, emptyMsg){{
  if(!rows.length) return `<div class="empty">${{emptyMsg}}</div>`;
  return `<table><thead><tr>
    <th>File</th><th>Type</th><th>PS_ Tables</th><th>Description</th>
  </tr></thead><tbody>`+
  rows.map(r=>`<tr>
    <td><a href="/admin/cobol/${{encodeURIComponent(r.filename)}}">${{esc(r.filename)}}</a></td>
    <td>${{esc(r.file_type||'')}}</td>
    <td style="color:#00e5ff">${{r.table_count||0}}</td>
    <td style="color:#7faab2">${{esc(r.description||'')}}</td>
  </tr>`).join('')+'</tbody></table>';
}}

function renderChanged(rows, labelA, labelB){{
  if(!rows.length) return '<div class="empty">No differences found between environments.</div>';
  return `<table><thead><tr>
    <th>File</th><th>Type</th>
    <th>Tables (${{esc(labelA)}})</th><th>Tables (${{esc(labelB)}})</th>
    <th>COPY (${{esc(labelA)}})</th><th>COPY (${{esc(labelB)}})</th>
    <th>CALL (${{esc(labelA)}})</th><th>CALL (${{esc(labelB)}})</th>
    <th>Content Hash</th>
  </tr></thead><tbody>`+
  rows.filter(r=>r.changed).map(r=>{{
    const tDiff=r.table_count_a!==r.table_count_b;
    const cDiff=r.copy_count_a!==r.copy_count_b;
    const kDiff=r.call_count_a!==r.call_count_b;
    const hDiff=r.content_hash_a&&r.content_hash_b&&r.content_hash_a!==r.content_hash_b;
    let hashLabel = hDiff?'DIFFERS':(r.content_hash_a?'SAME':'—');
    if (hDiff && r.content_normalized_same === true) hashLabel = 'DIFFERS (whitespace/comments only)';
    return `<tr>
      <td><a href="/admin/cobol/${{encodeURIComponent(r.filename)}}">${{esc(r.filename)}}</a></td>
      <td>${{esc(r.file_type||'')}}</td>
      <td class="${{tDiff?'diff-val':'same-val'}}">${{r.table_count_a||0}}</td>
      <td class="${{tDiff?'diff-val':'same-val'}}">${{r.table_count_b||0}}</td>
      <td class="${{cDiff?'diff-val':'same-val'}}">${{r.copy_count_a||0}}</td>
      <td class="${{cDiff?'diff-val':'same-val'}}">${{r.copy_count_b||0}}</td>
      <td class="${{kDiff?'diff-val':'same-val'}}">${{r.call_count_a||0}}</td>
      <td class="${{kDiff?'diff-val':'same-val'}}">${{r.call_count_b||0}}</td>
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
  const data=await fetch(`/api/cobol/envcompare?env_a=${{encodeURIComponent(envA)}}&env_b=${{encodeURIComponent(envB)}}&diff_mode=${{diffMode}}`).then(r=>r.json()).catch(e=>({{error:String(e)}}));
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
    return HTMLResponse(_shell("COBOL Environment Comparison", "cobolcompare", content=content))
