from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell


@router.get("/compflow", response_class=HTMLResponse)
def admin_compflow(request: Request, env: str = "HCM", comp: str = ""):
    preload = comp.upper()
    return _shell("Component Event Flow", "compflow", content=f"""
<style>
*{{box-sizing:border-box}}
body{{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0}}
.topbar{{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
input{{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 10px;font-size:12px;border-radius:3px}}
input:focus{{outline:none;border-color:#00e5ff}}
button{{background:#00e5ff;border:none;padding:5px 14px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;border-radius:3px}}
button:hover{{background:#33eeff}}
.hint{{font-size:10px;color:#556}}
#result{{padding:16px}}
.phase-block{{margin-bottom:16px}}
.phase-hdr{{font-size:10px;letter-spacing:2px;text-transform:uppercase;padding:5px 10px;font-weight:bold;
  display:flex;align-items:center;justify-content:space-between}}
.phase-body{{overflow:hidden}}
.col-hdr{{display:grid;grid-template-columns:140px 170px 170px 90px;background:#0a161e;
  border:1px solid #00e5ff22;border-bottom:none}}
.event-row{{display:grid;grid-template-columns:140px 170px 170px 90px;border-bottom:1px solid #0d1b24}}
.event-row:last-child{{border-bottom:none}}
.event-row:hover{{background:rgba(255,255,255,.03)}}
.er-cell{{padding:5px 10px;font-size:11px;font-family:monospace;border-right:1px solid #0d1b24}}
.er-cell:last-child{{border-right:none}}
.col-hdr .er-cell{{font-size:10px;color:#445;font-family:Arial,sans-serif;font-weight:bold;letter-spacing:.4px;text-transform:uppercase;padding:3px 10px}}
.er-event{{color:#00e5ff;font-weight:bold}}
.er-scope{{font-size:10px;color:#556;font-family:Arial}}
.er-rec{{color:#88ff44}}
.er-field{{color:#ffcc44}}
.empty{{color:#445;font-size:12px;padding:24px;text-align:center}}
.warn{{color:#ffaa00;font-size:11px;padding:7px 12px;border:1px solid #ffaa0033;background:#1a0e00;border-radius:3px;margin-bottom:10px}}
.comp-hdr{{display:flex;align-items:baseline;gap:12px;margin-bottom:14px;flex-wrap:wrap}}
.comp-name{{font-size:16px;color:#00e5ff;font-family:monospace;font-weight:bold}}
.comp-meta{{font-size:11px;color:#556}}
.badge{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:10px;font-weight:bold;margin-left:6px;vertical-align:middle}}
.ac-wrap{{position:relative}}
#suggestions{{position:absolute;top:100%;left:0;z-index:999;background:#0b1b24;
  border:1px solid #00e5ff44;min-width:300px;max-height:200px;overflow-y:auto;
  border-radius:0 0 3px 3px;box-shadow:0 8px 24px rgba(0,0,0,.5)}}
.sug-item{{padding:5px 10px;font-size:12px;font-family:monospace;cursor:pointer;color:#d7faff}}
.sug-item:hover,.sug-item.hl{{background:rgba(0,229,255,.1);color:#00e5ff}}
.phase-search{{border:1px solid #ffaa0033;border-radius:3px}}
.phase-build{{border:1px solid #00e5ff33;border-radius:3px}}
.phase-interaction{{border:1px solid #88ff4433;border-radius:3px}}
.phase-save{{border:1px solid #ff669933;border-radius:3px}}
.phase-other{{border:1px solid #33333366;border-radius:3px}}
</style>

<div class="topbar">
  <div class="ac-wrap">
    <input id="compInp" placeholder="Component name (e.g. JOB_DATA)" style="width:280px"
           oninput="onInput(this.value)" onkeydown="onKey(event)" value="{preload}">
    <div id="suggestions"></div>
  </div>
  <button onclick="load()">&#9654; Load</button>
  <span class="hint">Events shown in canonical PeopleSoft processing sequence order</span>
</div>

<div id="result"><div class="empty">Enter a component name to view its PeopleCode event flow.</div></div>

<script>
let _sugIdx = -1, _sugTimer = null;

function esc(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
function onInput(v) {{
  clearTimeout(_sugTimer);
  _sugTimer = setTimeout(() => fetchSuggestions(v), 180);
}}
function onKey(e) {{
  const box = document.getElementById('suggestions');
  const items = [...box.querySelectorAll('.sug-item')];
  if (e.key==='ArrowDown') {{ _sugIdx=Math.min(_sugIdx+1,items.length-1); hlSug(items); e.preventDefault(); }}
  else if (e.key==='ArrowUp') {{ _sugIdx=Math.max(_sugIdx-1,0); hlSug(items); e.preventDefault(); }}
  else if (e.key==='Enter') {{
    if (_sugIdx>=0&&items[_sugIdx]) selectSug(items[_sugIdx].dataset.name);
    else {{ load(); box.innerHTML=''; }}
  }} else if (e.key==='Escape') {{ box.innerHTML=''; _sugIdx=-1; }}
}}
function hlSug(items) {{
  items.forEach((el,i)=>el.classList.toggle('hl',i===_sugIdx));
}}
function selectSug(name) {{
  document.getElementById('compInp').value=name;
  document.getElementById('suggestions').innerHTML='';
  _sugIdx=-1; load();
}}
async function fetchSuggestions(q) {{
  if (q.length<2) {{ document.getElementById('suggestions').innerHTML=''; return; }}
  const env = window.dsGetEnv ? window.dsGetEnv() : 'HCM';
  try {{
    const d = await fetch(`/api/peoplesoft/${{env}}/component/search?q=${{encodeURIComponent(q)}}&limit=25`).then(r=>r.json());
    const box = document.getElementById('suggestions');
    const res = d.results||[];
    box.innerHTML = res.map(r=>
      `<div class="sug-item" data-name="${{esc(r.pnlgrpname)}}" onclick="selectSug('${{esc(r.pnlgrpname)}}')">`+
      `<b>${{esc(r.pnlgrpname)}}</b> <span style="color:#445;font-size:10px">${{esc(r.descr||'')}}</span></div>`
    ).join('');
    _sugIdx=-1;
  }} catch(e) {{ /* ignore */ }}
}}
async function load() {{
  document.getElementById('suggestions').innerHTML='';
  const comp = document.getElementById('compInp').value.trim().toUpperCase();
  if (!comp) return;
  const env = window.dsGetEnv ? window.dsGetEnv() : 'HCM';
  document.getElementById('result').innerHTML='<div class="empty" style="color:#334">Loading…</div>';
  try {{
    const d = await fetch(`/api/peoplesoft/${{env}}/component/${{encodeURIComponent(comp)}}/events`).then(r=>r.json());
    renderFlow(d);
  }} catch(err) {{
    document.getElementById('result').innerHTML=`<div class="warn">Error: ${{esc(String(err))}}</div>`;
  }}
}}

const PHASE_ORDER = ['search','build','interaction','save','other'];
const PHASE_LABEL = {{search:'Search Phase',build:'Component Build',interaction:'User Interaction',save:'Save Phase',other:'Other'}};
const PHASE_COLOR = {{
  search:     ['#ffaa00','#ffaa0033'],
  build:      ['#00e5ff','#00e5ff33'],
  interaction:['#88ff44','#88ff4433'],
  save:       ['#ff6699','#ff669933'],
  other:      ['#778',   '#33333355'],
}};

function renderFlow(d) {{
  const el = document.getElementById('result');
  if (!d) {{ el.innerHTML='<div class="empty">No data.</div>'; return; }}
  const events = d.events||[];
  const warns = d.warnings||[];
  let html='';

  const records = new Set(events.filter(e=>e.record).map(e=>e.record)).size;
  html += `<div class="comp-hdr">
    <span class="comp-name">${{esc(d.component||'')}}</span>
    <span class="comp-meta">${{events.length}} event handler${{events.length!==1?'s':''}}
      &middot; ${{records}} record${{records!==1?'s':''}}</span>
  </div>`;

  if (warns.length) html+=warns.map(w=>`<div class="warn">&#9888; ${{esc(w)}}</div>`).join('');
  if (!events.length) {{ el.innerHTML=html+'<div class="empty">No PeopleCode events found for this component.</div>'; return; }}

  const byPhase={{}};
  for (const e of events) {{ const p=e.phase||'other'; (byPhase[p]=byPhase[p]||[]).push(e); }}

  for (const pk of PHASE_ORDER) {{
    const rows=byPhase[pk]; if(!rows?.length) continue;
    const [clr,bdr]=PHASE_COLOR[pk]||PHASE_COLOR.other;
    html+=`<div class="phase-block phase-${{pk}}">
      <div class="phase-hdr" style="color:${{clr}}">
        <span>${{PHASE_LABEL[pk]||pk}}</span>
        <span class="badge" style="background:${{bdr}};color:${{clr}}">${{rows.length}}</span>
      </div>
      <div class="col-hdr">
        <div class="er-cell">Event</div><div class="er-cell">Record</div>
        <div class="er-cell">Field</div><div class="er-cell">Scope</div>
      </div>
      <div class="phase-body">`;
    for (const e of rows) {{
      const recHtml = e.record
        ? `<a href="/admin/record/${{esc(e.record)}}" target="_blank" style="color:#88ff44;text-decoration:none">${{esc(e.record)}}</a>`
        : '<span style="color:#223">—</span>';
      html+=`<div class="event-row">
        <div class="er-cell er-event">${{esc(e.event)}}</div>
        <div class="er-cell er-rec">${{recHtml}}</div>
        <div class="er-cell er-field">${{e.field?esc(e.field):'<span style="color:#223">—</span>'}}</div>
        <div class="er-cell"><span class="er-scope">${{esc(e.scope)}}</span></div>
      </div>`;
    }}
    html+='</div></div>';
  }}
  el.innerHTML=html;
}}

window.onEnvChange = () => {{
  const comp = document.getElementById('compInp').value.trim();
  if (comp) load();
}};

{f"document.addEventListener('DOMContentLoaded', () => load());" if preload else ""}
</script>
""")
