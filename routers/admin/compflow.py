from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell

_PC_KW = ("'If','Then','Else','End-If','For','End-For','While','End-While','Repeat',"
          "'Until','Return','Break','Continue','Local','Global','Component','Function',"
          "'End-Function','Method','End-Method','class','Extends','Implements','import',"
          "'Array','String','Integer','Number','Date','DateTime','Boolean','Object','Any',"
          "'Exception','Try','Catch','End-Try','Throw','CreateObject','GetLevel0','GetRecord',"
          "'GetField','GetPage','GetGrid','GetRow','GetComponent','Step','DoWhile','DoUntil'")

_PC_BUILTIN = ("'MessageBox','SQLExec','CreateSQL','Close','Fetch','Insert','Update','Delete',"
               "'IsNull','None','Null','True','False','All','And','Or','Not','As','Of',"
               "'Property','Get','Set','Value','Name','Type','CreateRecord','CreateMessage',"
               "'CreateRowset','CreateArray','GetRowset','GetMessage',"
               "'%This','%Super','%CurrentTimeIn','%Date','%DateTime','%Time',"
               "'%EmployeeId','%OperatorId','%MenuName','%Component','%Page','%Action',"
               "'%Mode','%Panel','%PanelGroup','%UpdateStats','%SelectAll','%Insert',"
               "'%Update','%Delete','%SelectByKey','%SelectByKeyEffdt','%DateAdd',"
               "'%DateTimeAdd','%DateTimeDiff','%DateDiff','%Substring','%NumToChar',"
               "'%CharToNum','%DateOut','%TimeOut','%Round','%Truncate','%Abs','%Sign',"
               "'%Mod','%Upper','%Lower','%Rtrim','%Ltrim','%Replace','%Len','%Value',"
               "'%like','%contains','%starts'")


@router.get("/compflow", response_class=HTMLResponse)
def admin_compflow(request: Request, env: str = "HCM", comp: str = ""):
    preload = (comp or request.query_params.get("component") or "").upper()
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
.col-hdr{{display:grid;grid-template-columns:140px 170px 170px 90px 28px;background:#0a161e;
  border:1px solid #00e5ff22;border-bottom:none}}
.event-row{{display:grid;grid-template-columns:140px 170px 170px 90px 28px;border-bottom:1px solid #0d1b24;cursor:pointer}}
.event-row:last-child{{border-bottom:none}}
.event-row:hover{{background:rgba(255,255,255,.04)}}
.event-row.open{{background:rgba(0,229,255,.05)}}
.er-cell{{padding:5px 10px;font-size:11px;font-family:monospace;border-right:1px solid #0d1b24}}
.er-cell:last-child{{border-right:none}}
.col-hdr .er-cell{{font-size:10px;color:#445;font-family:Arial,sans-serif;font-weight:bold;letter-spacing:.4px;text-transform:uppercase;padding:3px 10px}}
.er-event{{color:#00e5ff;font-weight:bold}}
.er-scope{{font-size:10px;color:#556;font-family:Arial}}
.er-rec{{color:#88ff44}}
.er-field{{color:#ffcc44}}
.er-toggle{{display:flex;align-items:center;justify-content:center;font-size:12px;color:#334;user-select:none}}
.event-row:hover .er-toggle{{color:#00e5ff}}
.event-row.open .er-toggle{{color:#00e5ff;transform:rotate(90deg)}}
.src-row{{display:none;border-bottom:1px solid #0d1b24;background:#020a10}}
.src-row.open{{display:block}}
.src-inner{{padding:10px 14px;font-family:monospace;font-size:11px;line-height:1.5;
  max-height:380px;overflow-y:auto;white-space:pre-wrap;word-break:break-word}}
.src-loading{{color:#334;font-size:11px;padding:10px 14px}}
.src-none{{color:#334;font-size:11px;padding:10px 14px;font-style:italic}}
.kw{{color:#569cd6}}.str{{color:#ce9178}}.cmt{{color:#6a9955}}.builtin{{color:#dcdcaa}}.hit{{background:#2a1c00;color:#ffcc44}}
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
.owner-badge{{font-size:10px;font-family:Arial;font-weight:600;padding:1px 7px;border-radius:10px;vertical-align:middle;margin-left:8px}}
.owner-custom{{color:#fa0;background:rgba(255,170,0,.14);border:1px solid rgba(255,170,0,.3)}}
.owner-delivered{{color:#7faab2;background:rgba(0,100,120,.18);border:1px solid rgba(0,100,120,.3)}}
.mod-badge{{font-size:9px;font-family:Arial;color:#ffcc44;background:rgba(255,204,68,.1);
  padding:0 4px;border-radius:2px;display:inline-block;margin-top:2px}}
</style>

<div class="topbar">
  <div class="ac-wrap">
    <input id="compInp" placeholder="Component name (e.g. JOB_DATA)" style="width:280px"
           oninput="onInput(this.value)" onkeydown="onKey(event)" value="{preload}">
    <div id="suggestions"></div>
  </div>
  <button onclick="load()">&#9654; Load</button>
  <span class="hint">Click any event row to view its PeopleCode source inline</span>
</div>

<div id="result"><div class="empty">Enter a component name to view its PeopleCode event flow.</div></div>

<script>
const PC_KW=[{_PC_KW}];
const PC_BUILTIN=[{_PC_BUILTIN}];

function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}}

function highlightPC(src){{
  let h='',i=0;const s=src;
  while(i<s.length){{
    if(s[i]==='/'&&s[i+1]==='*'){{const e=s.indexOf('*/',i+2);const end=e<0?s.length:e+2;h+='<span class="cmt">'+esc(s.slice(i,end))+'</span>';i=end;continue;}}
    if(s[i]==='"'){{let j=i+1;while(j<s.length&&s[j]!=='"')j++;h+='<span class="str">'+esc(s.slice(i,j+1))+'</span>';i=j+1;continue;}}
    if(/[A-Za-z%_]/.test(s[i])){{let j=i;while(j<s.length&&/[A-Za-z0-9_.%\\-]/.test(s[j]))j++;const w=s.slice(i,j);
      if(PC_KW.includes(w))h+='<span class="kw">'+esc(w)+'</span>';
      else if(PC_BUILTIN.includes(w))h+='<span class="builtin">'+esc(w)+'</span>';
      else h+=esc(w);i=j;continue;}}
    h+=esc(s[i]);i++;}}
  return h;
}}

let _sugIdx=-1,_sugTimer=null,_curComp='';
let _pfcConfigs=[];

function onInput(v){{clearTimeout(_sugTimer);_sugTimer=setTimeout(()=>fetchSuggestions(v),180);}}
function onKey(e){{
  const box=document.getElementById('suggestions');
  const items=[...box.querySelectorAll('.sug-item')];
  if(e.key==='ArrowDown'){{_sugIdx=Math.min(_sugIdx+1,items.length-1);hlSug(items);e.preventDefault();}}
  else if(e.key==='ArrowUp'){{_sugIdx=Math.max(_sugIdx-1,0);hlSug(items);e.preventDefault();}}
  else if(e.key==='Enter'){{
    if(_sugIdx>=0&&items[_sugIdx])selectSug(items[_sugIdx].dataset.name);
    else{{load();box.innerHTML='';}}
  }}else if(e.key==='Escape'){{box.innerHTML='';_sugIdx=-1;}}
}}
function hlSug(items){{items.forEach((el,i)=>el.classList.toggle('hl',i===_sugIdx));}}
function selectSug(name){{document.getElementById('compInp').value=name;document.getElementById('suggestions').innerHTML='';_sugIdx=-1;load();}}

async function fetchSuggestions(q){{
  if(q.length<2){{document.getElementById('suggestions').innerHTML='';return;}}
  const env=window.dsGetEnv?window.dsGetEnv():'HCM';
  try{{
    const d=await fetch(`/api/peoplesoft/components?env=${{env}}&q=${{encodeURIComponent(q)}}&limit=25`).then(r=>r.json());
    const box=document.getElementById('suggestions');
    const items=Array.isArray(d)?d:(d.results||[]);
    box.innerHTML=items.map(r=>
      `<div class="sug-item" data-name="${{esc(r.pnlgrpname)}}" onclick="selectSug('${{esc(r.pnlgrpname)}}')">`+
      `<b>${{esc(r.pnlgrpname)}}</b> <span style="color:#445;font-size:10px">${{esc(r.descr||'')}}</span></div>`
    ).join('');
    _sugIdx=-1;
  }}catch(e){{}}
}}

async function load(){{
  document.getElementById('suggestions').innerHTML='';
  const comp=document.getElementById('compInp').value.trim().toUpperCase();
  if(!comp)return;
  _curComp=comp;
  const env=window.dsGetEnv?window.dsGetEnv():'HCM';
  document.getElementById('result').innerHTML='<div class="empty" style="color:#334">Loading…</div>';
  try{{
    const [d, obj]=await Promise.all([
      fetch(`/api/peoplesoft/components/${{encodeURIComponent(comp)}}/events?env=${{env}}`).then(r=>r.json()),
      fetch(`/api/peoplesoft/object/component/${{encodeURIComponent(comp)}}?env=${{env}}`).then(r=>r.ok?r.json():null).catch(()=>null),
    ]);
    const pfcSection=(obj?.sections||[]).find(s=>s.name==='Page Field Configurations');
    _pfcConfigs=pfcSection?.items||[];
    renderFlow(d);
  }}catch(err){{
    document.getElementById('result').innerHTML=`<div class="warn">Error: ${{esc(String(err))}}</div>`;
  }}
}}

const PHASE_ORDER=['search','build','interaction','save','other'];
const PHASE_LABEL={{search:'Search Phase',build:'Component Build',interaction:'User Interaction',save:'Save Phase',other:'Other'}};
const PHASE_COLOR={{
  search:['#ffaa00','#ffaa0033'],build:['#00e5ff','#00e5ff33'],
  interaction:['#88ff44','#88ff4433'],save:['#ff6699','#ff669933'],other:['#778','#33333355'],
}};

let _srcCache={{}};

async function toggleSrc(rowId, comp, event, record, field){{
  const row=document.getElementById(rowId);
  const srcRow=document.getElementById(rowId+'_src');
  if(!row||!srcRow)return;

  const isOpen=row.classList.contains('open');
  if(isOpen){{row.classList.remove('open');srcRow.classList.remove('open');return;}}

  row.classList.add('open');
  srcRow.classList.add('open');

  const cacheKey=`${{comp}}|${{event}}|${{record}}|${{field}}`;
  if(_srcCache[cacheKey]!==undefined){{srcRow.innerHTML=_srcCache[cacheKey];return;}}

  srcRow.innerHTML='<div class="src-loading">Loading PeopleCode source…</div>';
  const env=window.dsGetEnv?window.dsGetEnv():'HCM';
  const url=`/api/peoplesoft/components/${{encodeURIComponent(comp)}}/event-source`+
    `?env=${{env}}&event=${{encodeURIComponent(event)}}&record=${{encodeURIComponent(record)}}&field=${{encodeURIComponent(field)}}`;
  try{{
    const d=await fetch(url).then(r=>r.json());
    let html;
    if(d.source){{
      html=`<div class="src-inner">${{highlightPC(d.source)}}</div>`;
    }}else{{
      const warns=d.warnings||[];
      html=`<div class="src-none">No source available${{warns.length?' — '+esc(warns[0].message||warns[0]):''}}</div>`;
    }}
    _srcCache[cacheKey]=html;
    srcRow.innerHTML=html;
  }}catch(e){{
    const err=`<div class="src-none">Error fetching source: ${{esc(String(e))}}</div>`;
    _srcCache[cacheKey]=err;
    srcRow.innerHTML=err;
  }}
}}

let _rowSeq=0;
function renderFlow(d){{
  const el=document.getElementById('result');
  if(!d){{el.innerHTML='<div class="empty">No data.</div>';return;}}
  const events=d.events||[];
  const warns=d.warnings||[];
  _srcCache={{}};
  let html='';

  const records=new Set(events.filter(e=>e.record).map(e=>e.record)).size;
  const modCount=events.filter(e=>e.modified).length;
  const modNote=modCount?` &middot; <span style="color:#ffcc44;font-weight:600">${{modCount}} user-modified</span>`:'';
  const compOwner=(d.component_owner||'').trim();
  const ownerBadge=compOwner
    ?`<span class="owner-badge owner-delivered">${{esc(compOwner)}}</span>`
    :`<span class="owner-badge owner-custom">CUSTOM</span>`;
  html+=`<div class="comp-hdr">
    <span class="comp-name">${{esc(d.component||'')}}</span>${{ownerBadge}}
    <span class="comp-meta">${{events.length}} event handler${{events.length!==1?'s':''}} &middot; ${{records}} record${{records!==1?'s':''}}${{modNote}}</span>
  </div>`;

  if(_pfcConfigs.length){{
    html+=`<div style="border:1px solid #ffaa2244;background:#1a120022;padding:8px 12px;margin-bottom:10px;font-size:11px">
      <span style="color:#ffaa22;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-size:10px">
        &#9888; ${{_pfcConfigs.length}} Enabled Page Field Configuration${{_pfcConfigs.length!==1?'s':''}}
      </span>
      ${{_pfcConfigs.map(c=>{{
        const link=(c._links&&c._links.admin)||'#';
        return `<div style="margin-top:4px">
          <a href="${{link}}?env=${{window.dsGetEnv?window.dsGetEnv():'HCM'}}" style="color:#ffaa22;font-family:monospace;text-decoration:none">${{esc(c.config_name)}}</a>
          <span style="color:#556;margin-left:6px">${{esc(c.descr||'')}} (${{esc(c.config_type)}})</span>
        </div>`;
      }}).join('')}}
      <div style="color:#556;margin-top:4px;font-style:italic">
        Field visibility/label/required/mask behavior below may be altered at runtime by these configurations.
      </div>
    </div>`;
  }}

  if(warns.length)html+=warns.map(w=>`<div class="warn">&#9888; ${{esc(w)}}</div>`).join('');
  if(!events.length){{el.innerHTML=html+'<div class="empty">No PeopleCode events found for this component.</div>';return;}}

  const byPhase={{}};
  for(const e of events){{const p=e.phase||'other';(byPhase[p]=byPhase[p]||[]).push(e);}}

  for(const pk of PHASE_ORDER){{
    const rows=byPhase[pk];if(!rows?.length)continue;
    const[clr,bdr]=PHASE_COLOR[pk]||PHASE_COLOR.other;
    html+=`<div class="phase-block phase-${{pk}}">
      <div class="phase-hdr" style="color:${{clr}}">
        <span>${{PHASE_LABEL[pk]||pk}}</span>
        <span class="badge" style="background:${{bdr}};color:${{clr}}">${{rows.length}}</span>
      </div>
      <div class="col-hdr">
        <div class="er-cell">Event</div><div class="er-cell">Record</div>
        <div class="er-cell">Field</div><div class="er-cell">Scope</div>
        <div class="er-cell"></div>
      </div>
      <div class="phase-body" style="border:1px solid ${{bdr}};border-top:none">`;

    for(const e of rows){{
      const rid='er'+(_rowSeq++);
      const comp=d.component||'';
      const recHtml=e.record
        ?`<a href="/admin/record/${{esc(e.record)}}" target="_blank" style="color:#88ff44;text-decoration:none" onclick="event.stopPropagation()">${{esc(e.record)}}</a>`
        :'<span style="color:#223">—</span>';
      const fldHtml=e.field?esc(e.field):'<span style="color:#223">—</span>';
      const modBadge=e.modified
        ?`<span class="mod-badge">mod: ${{esc(e.last_oprid)}}</span>`:'';
      const rowTitle=e.modified
        ?`title="Modified by ${{esc(e.last_oprid)}}${{e.last_dttm?' on '+esc(String(e.last_dttm).substring(0,10)):''}}"`
        :'title="Click to view PeopleCode source"';
      html+=`<div class="event-row" id="${{rid}}"
        onclick="toggleSrc('${{rid}}','${{esc(comp)}}','${{esc(e.event)}}','${{esc(e.record||'')}}','${{esc(e.field||'')}}')"
        ${{rowTitle}}>
        <div class="er-cell er-event" style="display:flex;flex-direction:column;justify-content:center"><span>${{esc(e.event)}}</span>${{modBadge}}</div>
        <div class="er-cell er-rec">${{recHtml}}</div>
        <div class="er-cell er-field">${{fldHtml}}</div>
        <div class="er-cell"><span class="er-scope">${{esc(e.scope)}}</span></div>
        <div class="er-cell er-toggle">&#9658;</div>
      </div>
      <div class="src-row" id="${{rid}}_src"></div>`;
    }}
    html+='</div></div>';
  }}
  el.innerHTML=html;
}}

window.onEnvChange=()=>{{const comp=document.getElementById('compInp').value.trim();if(comp)load();}};
{f"document.addEventListener('DOMContentLoaded', () => load());" if preload else ""}
</script>
""")


@router.get("/compseq", response_class=HTMLResponse)
def admin_compseq(request: Request, env: str = "HCM", comp: str = ""):
    preload = bool(comp)
    return _shell("PC Timeline", "compseq", content=f"""
<style>
.cs-bar{{display:flex;align-items:center;gap:10px;padding:14px 20px;border-bottom:1px solid #1a2a3a;
  background:#060d16;flex-wrap:wrap}}
.cs-inp{{background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 12px;
  border-radius:4px;font-size:13px;width:300px;font-family:monospace}}
.cs-inp:focus{{outline:none;border-color:#00e5ff55}}
.cs-btn{{padding:6px 18px;border-radius:4px;background:#00e5ff;color:#000;
  font-weight:bold;font-size:12px;border:none;cursor:pointer}}
.cs-btn:hover{{background:#33eeff}}
.cs-body{{padding:18px 20px}}
.cs-phases{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.cs-phase{{background:rgba(0,20,30,.6);border:1px solid #1a2a3a;border-radius:6px;overflow:hidden}}
.cs-phase-hdr{{padding:8px 12px;font-size:11px;font-weight:700;letter-spacing:.5px;
  text-transform:uppercase;border-bottom:1px solid #1a2a3a}}
.cs-phase-search .cs-phase-hdr{{color:#88ccff;background:rgba(0,100,200,.12)}}
.cs-phase-build  .cs-phase-hdr{{color:#44ddaa;background:rgba(0,160,100,.10)}}
.cs-phase-inter  .cs-phase-hdr{{color:#ffaa44;background:rgba(200,100,0,.10)}}
.cs-phase-save   .cs-phase-hdr{{color:#ff6666;background:rgba(200,40,40,.12)}}
.cs-slot{{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.04);cursor:default}}
.cs-slot:last-child{{border-bottom:none}}
.cs-slot.has-pc{{cursor:pointer}}
.cs-slot.has-pc:hover{{background:rgba(0,229,255,.05)}}
.cs-evt-name{{font-size:12px;font-weight:600;font-family:monospace}}
.cs-slot.no-pc .cs-evt-name{{color:#2a3a4a}}
.cs-slot.has-pc.delivered .cs-evt-name{{color:#00e5ff}}
.cs-slot.has-pc.custom   .cs-evt-name{{color:#ffb400}}
.cs-evt-meta{{font-size:10px;color:#446;margin-top:2px}}
.cs-slot.has-pc.custom .cs-evt-meta{{color:#7a5a00}}
.cs-badge{{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:600;
  margin-left:6px;vertical-align:middle}}
.cs-badge-cnt{{background:rgba(0,229,255,.15);color:#00e5ff}}
.cs-badge-custom{{background:rgba(255,180,0,.15);color:#ffb400}}
.cs-badge-scope{{background:rgba(255,255,255,.07);color:#7faab2}}
.cs-src{{display:none;padding:10px 12px;background:#020a12;border-top:1px solid #1a2a3a;
  font-size:12px;line-height:1.6}}
.cs-src.open{{display:block}}
.cs-src pre{{margin:0;overflow-x:auto;font-size:11px;color:#8ab;white-space:pre-wrap;word-break:break-word}}
.cs-prog-hdr{{font-size:11px;color:#556;margin-bottom:6px;border-bottom:1px solid #1a2a3a;
  padding-bottom:4px}}
.cs-spinner{{color:#446;font-size:12px;font-style:italic}}
.cs-stats{{display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap}}
.cs-stat{{background:rgba(0,20,30,.6);border:1px solid #1a2a3a;border-radius:4px;
  padding:10px 16px;text-align:center}}
.cs-stat-val{{font-size:22px;font-weight:700;color:#00e5ff;line-height:1}}
.cs-stat-lbl{{font-size:10px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px}}
.cs-owner{{font-size:11px;color:#446;margin-bottom:14px}}
.cs-legend{{display:flex;gap:12px;font-size:11px;margin-bottom:16px;flex-wrap:wrap}}
.cs-legend-item{{display:flex;align-items:center;gap:5px}}
.cs-dot{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
.cs-no-data{{color:#446;font-style:italic;font-size:13px;margin-top:30px;text-align:center}}
</style>

<div class="cs-bar">
  <span style="font-size:13px;font-weight:700;color:#00e5ff;letter-spacing:.5px">PC Timeline</span>
  <span style="color:#1a2a3a">|</span>
  <select id="modeSel" class="cs-inp" style="width:130px" onchange="onModeChange()">
    <option value="component">Component</option>
    <option value="record">Record</option>
  </select>
  <input id="compInp" class="cs-inp" placeholder="Component name…"
    value="{comp}" oninput="onInput(this.value)" onkeydown="if(event.key==='Enter')load()">
  <button class="cs-btn" onclick="load()">Analyse</button>
  <span id="status" class="cs-spinner"></span>
</div>
<div class="cs-body" id="body">
  <div class="cs-no-data" id="placeholder">Enter a component name to see its PeopleCode processing timeline.</div>
</div>

<script>
const ENV = () => document.getElementById('globalEnv')?.value || '{env}';

// Canonical PeopleSoft processing sequence
const SEQUENCE = [
  {{
    id: 'search', label: 'Search Phase', cls: 'cs-phase-search',
    desc: 'Executes before the component search dialog opens',
    events: [
      {{ name:'SearchInit',    scope:'Component',    note:'Initialise search page' }},
      {{ name:'SearchSave',    scope:'Component',    note:'Validate search criteria' }},
      {{ name:'SearchDefault', scope:'Record/Field', note:'Default search keys' }},
    ]
  }},
  {{
    id: 'build', label: 'Build Phase', cls: 'cs-phase-build',
    desc: 'Executes when the component buffer is loaded',
    events: [
      {{ name:'PreBuild',     scope:'Component',    note:'Before buffers loaded' }},
      {{ name:'FieldDefault', scope:'Record/Field', note:'Default field values' }},
      {{ name:'FieldFormula', scope:'Record/Field', note:'Derived / formula fields' }},
      {{ name:'RowInit',      scope:'Record/Field', note:'Initialise each row' }},
      {{ name:'PostBuild',    scope:'Component',    note:'After buffers loaded' }},
      {{ name:'Activate',     scope:'Component',    note:'Page activation' }},
      {{ name:'RowSelect',    scope:'Record/Field', note:'Filter rows on select' }},
    ]
  }},
  {{
    id: 'inter', label: 'Interaction Phase', cls: 'cs-phase-inter',
    desc: 'Executes during user interaction (field changes, row actions)',
    events: [
      {{ name:'FieldEdit',    scope:'Record/Field', note:'Validate field value' }},
      {{ name:'FieldChange',  scope:'Record/Field', note:'React to field change' }},
      {{ name:'PrePopup',     scope:'Record/Field', note:'Before popup menu' }},
      {{ name:'ItemSelected', scope:'Record/Field', note:'List item selected' }},
      {{ name:'RowInsert',    scope:'Record',       note:'Row inserted' }},
      {{ name:'RowDelete',    scope:'Record',       note:'Row deleted' }},
    ]
  }},
  {{
    id: 'save', label: 'Save Phase', cls: 'cs-phase-save',
    desc: 'Executes during the save cycle',
    events: [
      {{ name:'SaveEdit',       scope:'Record/Field', note:'Validate before save' }},
      {{ name:'SavePreChange',  scope:'Record/Field', note:'Before DB write' }},
      {{ name:'Workflow',       scope:'Component',    note:'Workflow/notification' }},
      {{ name:'SavePostChange', scope:'Record/Field', note:'After DB write' }},
    ]
  }},
];

let _evtMap = {{}};  // event name → array of matching rows from API
let _recSlotMap = {{}};  // record-mode slot id → event data

function mode() {{ return document.getElementById('modeSel').value; }}

function onModeChange() {{
  const inp = document.getElementById('compInp');
  inp.placeholder = mode() === 'record' ? 'Record name…' : 'Component name…';
  document.getElementById('body').innerHTML =
    '<div class="cs-no-data" id="placeholder">Enter a ' + mode() + ' name to see its PeopleCode processing timeline.</div>';
}}

function onInput(v) {{
  if (!v.trim()) {{
    document.getElementById('body').innerHTML =
      '<div class="cs-no-data" id="placeholder">Enter a ' + mode() + ' name to see its PeopleCode processing timeline.</div>';
  }}
}}

async function load() {{
  const name = document.getElementById('compInp').value.trim().toUpperCase();
  if (!name) return;
  const st = document.getElementById('status');
  st.textContent = 'Loading…';
  document.getElementById('body').innerHTML = '<div class="cs-spinner" style="margin:30px 0">Querying…</div>';
  try {{
    if (mode() === 'record') {{
      const r = await fetch('/api/peoplesoft/records/' + encodeURIComponent(name) + '/sequence?env=' + ENV());
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      st.textContent = '';
      renderRecord(name, d);
    }} else {{
      const r = await fetch('/api/peoplesoft/components/' + encodeURIComponent(name) + '/events?env=' + ENV());
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      st.textContent = '';
      render(name, d);
    }}
  }} catch(e) {{
    st.textContent = '';
    document.getElementById('body').innerHTML = '<div class="cs-no-data">Error: ' + esc(String(e)) + '</div>';
  }}
}}

function esc(s){{return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}}

function render(comp, d) {{
  const events = d.events || [];
  const owner = d.owner || '';

  // Build lookup: event name → rows
  _evtMap = {{}};
  events.forEach(e => {{
    (_evtMap[e.event] = _evtMap[e.event] || []).push(e);
  }});

  // Stats
  const totalSlots = SEQUENCE.reduce((s,ph) => s + ph.events.length, 0);
  const activeEvents = new Set(events.map(e => e.event));
  const customRows = events.filter(e => e.modified);
  const customEvents = new Set(customRows.map(e => e.event));

  let html = '<div class="cs-stats">';
  html += `<div class="cs-stat"><div class="cs-stat-val">${{totalSlots}}</div><div class="cs-stat-lbl">Total Slots</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#00e5ff">${{activeEvents.size}}</div><div class="cs-stat-lbl">With PeopleCode</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#ffb400">${{customEvents.size}}</div><div class="cs-stat-lbl">Custom Events</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#4a9a4a">${{activeEvents.size - customEvents.size}}</div><div class="cs-stat-lbl">Delivered Events</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#888">${{totalSlots - activeEvents.size}}</div><div class="cs-stat-lbl">Empty Slots</div></div>`;
  html += '</div>';

  if (owner) html += `<div class="cs-owner">Owner: <span style="color:#7faab2">${{esc(owner)}}</span></div>`;

  html += '<div class="cs-legend">';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#00e5ff"></div><span style="color:#7faab2">Delivered PeopleCode</span></div>';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#ffb400"></div><span style="color:#7faab2">Custom PeopleCode</span></div>';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#1a2a3a"></div><span style="color:#3a4a5a">No PeopleCode</span></div>';
  html += '</div>';

  html += '<div class="cs-phases">';
  SEQUENCE.forEach(phase => {{
    html += `<div class="cs-phase ${{phase.cls}}">`;
    html += `<div class="cs-phase-hdr">${{phase.label}}</div>`;
    phase.events.forEach(ev => {{
      const rows = _evtMap[ev.name] || [];
      const hasPC = rows.length > 0;
      const isCustom = rows.some(r => r.modified);
      const stateCls = !hasPC ? 'no-pc' : (isCustom ? 'has-pc custom' : 'has-pc delivered');
      const id = 'slot_' + ev.name;

      let meta = `<div class="cs-evt-meta">${{esc(ev.scope)}} · ${{esc(ev.note)}}`;
      if (hasPC) {{
        // Summarise programs
        const scopes = [...new Set(rows.map(r => r.scope))];
        const recs = [...new Set(rows.filter(r => r.record).map(r => r.record))];
        meta += ` · ${{rows.length}} program${{rows.length===1?'':'s'}}`;
        if (recs.length) meta += ` (${{recs.slice(0,3).map(r => '<span style="color:#4a8a9a">'+esc(r)+'</span>').join(', ')}}${{recs.length>3?'…':''}})`;
      }}
      meta += '</div>';

      let badges = '';
      if (hasPC) {{
        badges += `<span class="cs-badge cs-badge-cnt">${{rows.length}}</span>`;
        if (isCustom) badges += `<span class="cs-badge cs-badge-custom">custom</span>`;
      }}

      const onclick = hasPC ? `onclick="toggleSlot('${{ev.name}}','${{esc(comp)}}')"` : '';
      html += `<div class="cs-slot ${{stateCls}}" id="${{id}}" ${{onclick}}>
        <div class="cs-evt-name">${{esc(ev.name)}}${{badges}}</div>
        ${{meta}}
      </div>
      <div class="cs-src" id="${{id}}_src"></div>`;
    }});
    html += '</div>';
  }});
  html += '</div>';

  document.getElementById('body').innerHTML = html;
}}

function renderRecord(rec, d) {{
  const phases = d.phases || [];
  if (!phases.length) {{
    document.getElementById('body').innerHTML =
      `<div class="cs-no-data">No canonical Record Field PeopleCode events on <span style="color:#7faab2">${{esc(rec)}}</span>.<br>
       <span style="font-size:10px;color:#334">Shows only genuinely record-owned PeopleCode (OBJECTID1=1), independent of any component.</span></div>`;
    return;
  }}

  const allEvents = phases.flatMap(ph => ph.events);
  const totalSlots = allEvents.length;
  const withPC = allEvents.filter(e => e.status !== 'empty');
  const customEvents = allEvents.filter(e => e.status === 'custom');
  _recSlotMap = {{}};

  let html = '<div class="cs-stats">';
  html += `<div class="cs-stat"><div class="cs-stat-val">${{totalSlots}}</div><div class="cs-stat-lbl">Total Slots</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#00e5ff">${{withPC.length}}</div><div class="cs-stat-lbl">With PeopleCode</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#ffb400">${{customEvents.length}}</div><div class="cs-stat-lbl">Custom Events</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#4a9a4a">${{withPC.length - customEvents.length}}</div><div class="cs-stat-lbl">Delivered Events</div></div>`;
  html += `<div class="cs-stat"><div class="cs-stat-val" style="color:#888">${{totalSlots - withPC.length}}</div><div class="cs-stat-lbl">Empty Slots</div></div>`;
  html += '</div>';

  html += '<div class="cs-legend">';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#00e5ff"></div><span style="color:#7faab2">Delivered PeopleCode</span></div>';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#ffb400"></div><span style="color:#7faab2">Custom PeopleCode</span></div>';
  html += '<div class="cs-legend-item"><div class="cs-dot" style="background:#1a2a3a"></div><span style="color:#3a4a5a">No PeopleCode</span></div>';
  html += '</div>';

  const phaseCls = {{search:'cs-phase-search', build:'cs-phase-build', interaction:'cs-phase-inter', save:'cs-phase-save'}};

  html += '<div class="cs-phases">';
  phases.forEach(ph => {{
    const cls = phaseCls[ph.phase] || 'cs-phase-build';
    html += `<div class="cs-phase ${{cls}}">`;
    html += `<div class="cs-phase-hdr">${{esc(ph.label)}}</div>`;
    ph.events.forEach((ev, idx) => {{
      const hasPC = ev.status !== 'empty';
      const isCustom = ev.status === 'custom';
      const stateCls = !hasPC ? 'no-pc' : (isCustom ? 'has-pc custom' : 'has-pc delivered');
      const id = 'rslot_' + ph.phase + '_' + idx;

      let meta = `<div class="cs-evt-meta">${{esc(ev.note||'')}}`;
      if (ev.field) meta += ` · field ${{esc(ev.field)}}`;
      if (hasPC && ev.last_oprid) meta += ` · ${{esc(ev.last_oprid)}}`;
      meta += '</div>';

      let badges = '';
      if (isCustom) badges += `<span class="cs-badge cs-badge-custom">custom</span>`;

      if (hasPC) _recSlotMap[id] = ev;
      const onclick = hasPC ? `onclick="toggleRecordSlot('${{id}}')"` : '';
      html += `<div class="cs-slot ${{stateCls}}" id="${{id}}" ${{onclick}}>
        <div class="cs-evt-name">${{esc(ev.name)}}${{badges}}</div>
        ${{meta}}
      </div>
      <div class="cs-src" id="${{id}}_src"></div>`;
    }});
    html += '</div>';
  }});
  html += '</div>';

  document.getElementById('body').innerHTML = html;
}}

function toggleRecordSlot(id) {{
  const srcEl = document.getElementById(id + '_src');
  const ev = _recSlotMap[id];
  if (!srcEl || !ev) return;
  if (srcEl.classList.contains('open')) {{
    srcEl.classList.remove('open');
    return;
  }}
  srcEl.classList.add('open');
  const recName = document.getElementById('compInp').value.trim().toUpperCase();
  let hdr = esc(ev.name);
  if (ev.field) hdr += ` · field ${{esc(ev.field)}}`;
  if (ev.status === 'custom') hdr += ` <span style="color:#ffb400;font-size:10px">● custom (${{esc(ev.last_oprid||'')}} @ ${{esc(ev.last_dttm||'')}})</span>`;
  srcEl.innerHTML = `<div class="cs-prog-hdr">${{hdr}}</div>
    <pre style="color:#556">Record-owned PeopleCode source viewing isn't wired up yet — this
shows the metadata this platform indexes today (field, last editor, timestamp).
See the <a href="/admin/object/record/${{esc(recName)}}" style="color:#00e5ff">Record Explorer</a> for full record detail.</pre>`;
}}

async function toggleSlot(evtName, comp) {{
  const srcEl = document.getElementById('slot_' + evtName + '_src');
  if (!srcEl) return;
  if (srcEl.classList.contains('open')) {{
    srcEl.classList.remove('open');
    return;
  }}
  const rows = _evtMap[evtName] || [];
  if (!rows.length) return;

  srcEl.classList.add('open');
  srcEl.innerHTML = '<span class="cs-spinner">Loading source…</span>';

  // Fetch source for each program row (up to 6)
  const toFetch = rows.slice(0, 6);
  const parts = [];
  for (const row of toFetch) {{
    const params = new URLSearchParams({{env: ENV(), event: evtName,
      record: row.record || '', field: row.field || ''}});
    try {{
      const r = await fetch('/api/peoplesoft/components/' + encodeURIComponent(comp)
        + '/event-source?' + params);
      const d = r.ok ? await r.json() : null;
      const src = d?.source || '';
      let hdr = `${{esc(evtName)}}`;
      if (row.scope !== 'Component') hdr += ` · ${{esc(row.record||'')}}`;
      if (row.field) hdr += `.${{esc(row.field)}}`;
      if (row.modified) hdr += ` <span style="color:#ffb400;font-size:10px">● custom (${{esc(row.lastupdoprid)}})</span>`;
      parts.push(`<div class="cs-prog-hdr">${{hdr}}</div>
        <pre>${{src ? highlightPC(src) : '<span style="color:#446">Source unavailable</span>'}}</pre>`);
    }} catch(e) {{
      parts.push(`<div class="cs-prog-hdr">${{esc(evtName)}}</div><pre style="color:#446">Error loading source</pre>`);
    }}
  }}
  if (rows.length > 6) parts.push(`<div class="cs-prog-hdr" style="color:#446">… ${{rows.length - 6}} more programs not shown</div>`);
  srcEl.innerHTML = parts.join('<hr style="border-color:#1a2a3a;margin:10px 0">');
}}

function highlightPC(src) {{
  const KW = 'If|Else|End-If|For|End-For|While|End-While|Evaluate|When|When-Other|End-Evaluate|Function|Return|End-Function|Local|Global|Component|Exists|All|None|Error|Warning|MessageBox|SQLExec|CreateSQL|GetRecord|CreateRecord|CreateObject|ObjectDoMethod|Fetch|Close|UpdateValue|InsertRow|DeleteRow|FlushBulkInserts|CommitWork|RollbackWork|DoSave|DoSaveNow|Transfer|TransferPage|WinMessage|Hide|UnHide|Gray|UnGray|Enable|Disable|SetDefault|ClearDefault|SetLabel|PeopleCode|End-'.split('|');
  let h = esc(src);
  h = h.replace(/\/\*[\s\S]*?\*\//g, m => `<span style="color:#4a6a4a">${{m}}</span>`);
  h = h.replace(/&amp;[A-Za-z_][A-Za-z0-9_]*/g, m => `<span style="color:#88ddff">${{m}}</span>`);
  h = h.replace(/"[^"]*"/g, m => `<span style="color:#ccbb88">${{m}}</span>`);
  KW.forEach(kw => {{
    h = h.replace(new RegExp('\\b' + kw.replace(/-/g,'\\-') + '\\b', 'g'),
      `<span style="color:#aa88ff">${{kw}}</span>`);
  }});
  return h;
}}

window.onEnvChange = () => {{
  const comp = document.getElementById('compInp').value.trim();
  if (comp) load();
}};
{f"document.addEventListener('DOMContentLoaded', () => load());" if preload else ""}
</script>
""")
