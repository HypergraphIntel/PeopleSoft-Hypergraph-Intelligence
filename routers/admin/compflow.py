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
    const d=await fetch(`/api/peoplesoft/${{env}}/component/search?q=${{encodeURIComponent(q)}}&limit=25`).then(r=>r.json());
    const box=document.getElementById('suggestions');
    box.innerHTML=(d.results||[]).map(r=>
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
    const d=await fetch(`/api/peoplesoft/${{env}}/component/${{encodeURIComponent(comp)}}/events`).then(r=>r.json());
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
  const url=`/api/peoplesoft/${{env}}/component/${{encodeURIComponent(comp)}}/event-source`+
    `?event=${{encodeURIComponent(event)}}&record=${{encodeURIComponent(record)}}&field=${{encodeURIComponent(field)}}`;
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
  html+=`<div class="comp-hdr">
    <span class="comp-name">${{esc(d.component||'')}}</span>
    <span class="comp-meta">${{events.length}} event handler${{events.length!==1?'s':''}} &middot; ${{records}} record${{records!==1?'s':''}}</span>
  </div>`;

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
      html+=`<div class="event-row" id="${{rid}}"
        onclick="toggleSrc('${{rid}}','${{esc(comp)}}','${{esc(e.event)}}','${{esc(e.record||'')}}','${{esc(e.field||'')}}')"
        title="Click to view PeopleCode source">
        <div class="er-cell er-event">${{esc(e.event)}}</div>
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
