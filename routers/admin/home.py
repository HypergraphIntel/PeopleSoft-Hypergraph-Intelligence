import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS


@router.get("/", response_class=HTMLResponse)
def admin_home():
    return _shell("Home", "home", env=False, noscroll=False, content="""\
<style>
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;}
h2{color:#00e5ff;font-size:12px;letter-spacing:2px;text-transform:uppercase;
   border-bottom:1px solid #00e5ff22;padding-bottom:6px;margin:0 0 10px;}
.dash-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;max-width:1100px;}
@media(max-width:700px){.dash-grid{grid-template-columns:1fr;}}
.dash-card{background:rgba(0,20,30,.75);border:1px solid #00e5ff33;
  box-shadow:0 0 10px rgba(0,229,255,.1);padding:14px 18px;border-radius:4px;}
.dash-card.alert-card{border-color:rgba(255,107,107,.3);}
.stat-row{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0;}
.stat{display:flex;flex-direction:column;}
.stat-val{font-size:22px;font-weight:700;color:#00e5ff;}
.stat-val.red{color:#ff4444;}
.stat-val.green{color:#00cc66;}
.stat-val.orange{color:#ff9f43;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:.5px;margin-top:1px;}
.alert-item{display:flex;gap:8px;align-items:flex-start;padding:5px 0;
  border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;}
.alert-item:last-child{border-bottom:none;}
.sev-error{color:#ff4444;font-weight:700;font-size:10px;min-width:38px;}
.sev-warn{color:#ff9f43;font-weight:700;font-size:10px;min-width:38px;}
.src-row{display:flex;justify-content:space-between;align-items:center;
  padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;}
.src-row:last-child{border-bottom:none;}
.src-ok{color:#00cc66;font-size:10px;}
.src-err{color:#ff4444;font-size:10px;}
.ql-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
.ql{padding:5px 12px;border-radius:3px;background:rgba(0,229,255,.07);
  border:1px solid rgba(0,229,255,.2);color:#00e5ff;font-size:11px;
  text-decoration:none;white-space:nowrap;}
.ql:hover{background:rgba(0,229,255,.15);}
.ql.orange{border-color:rgba(255,159,67,.3);color:#ff9f43;background:rgba(255,159,67,.07);}
.ql.green{border-color:rgba(0,204,102,.3);color:#00cc66;background:rgba(0,204,102,.07);}
.ql.red{border-color:rgba(255,107,107,.3);color:#ff6b6b;background:rgba(255,107,107,.07);}
.ql.purple{border-color:rgba(180,100,255,.3);color:#c97fff;background:rgba(180,100,255,.07);}
.mini-spark{display:block;overflow:visible;}
.spark-row{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;}
.spark-tile{display:flex;flex-direction:column;gap:2px;}
.spark-lbl{font-size:10px;color:#334;text-transform:uppercase;letter-spacing:.5px;}
.spark-val{font-size:14px;font-weight:700;}
.muted{color:#334;}
.ts-label{font-size:11px;color:#334;}
</style>

<div class="pe-home" style="max-width:1100px;margin:0 auto;padding:16px">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
  <div>
    <div style="font-size:10px;color:#445;letter-spacing:2px;text-transform:uppercase">DeathStar Platform</div>
    <h1 style="color:#00e5ff;font-size:20px;margin:2px 0;text-shadow:0 0 12px #00e5ff44;letter-spacing:3px">
      PeopleSoft Hypergraph Intelligence
    </h1>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <select id="envSel" onchange="loadDash()"
      style="background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.3);
             color:#d7faff;font-size:12px;padding:5px 10px;border-radius:4px">
    </select>
    <span class="ts-label" id="lastTs">Loading…</span>
  </div>
</div>

<div class="dash-grid">

  <!-- Active Alerts -->
  <div class="dash-card alert-card" id="alertCard">
    <h2>Active Alerts <span id="alertBadge" style="font-weight:normal;font-size:11px"></span></h2>
    <div id="alertBody"><span class="muted" style="font-size:12px">Loading…</span></div>
    <div class="ql-row">
      <a class="ql" href="/admin/runtime">Runtime Monitor</a>
      <a class="ql orange" href="/admin/igw">IGW Errors</a>
      <a class="ql green" href="/admin/prcs-ae">PRCS AE</a>
    </div>
  </div>

  <!-- Runtime Health -->
  <div class="dash-card">
    <h2>Runtime Health</h2>
    <div id="runtimeBody"><span class="muted" style="font-size:12px">Loading…</span></div>
    <div class="ql-row">
      <a class="ql" href="/admin/runtime">Monitor</a>
      <a class="ql orange" href="/admin/runtime">Process Errors</a>
    </div>
  </div>

  <!-- Log Health -->
  <div class="dash-card">
    <h2>Log Intelligence</h2>
    <div id="logBody"><span class="muted" style="font-size:12px">Loading…</span></div>
    <div class="ql-row">
      <a class="ql" href="/admin/logs">Sources</a>
      <a class="ql red" href="/admin/log_errors">Errors</a>
      <a class="ql orange" href="/admin/igw">IGW</a>
      <a class="ql green" href="/admin/prcs-ae">PRCS AE</a>
    </div>
  </div>

  <!-- Drift + Trend -->
  <div class="dash-card">
    <h2>Environment &amp; Trends</h2>
    <div id="driftBody"><span class="muted" style="font-size:12px">Loading…</span></div>
    <div id="sparkBody" style="margin-top:12px"></div>
    <div class="ql-row">
      <a class="ql" href="/admin/drift">Drift History</a>
      <a class="ql" href="/admin/envcompare">Env Compare</a>
      <a class="ql purple" href="/admin/assistant">Ask AI</a>
    </div>
  </div>

</div><!-- /dash-grid -->

<!-- Quick Navigation -->
<div style="margin-top:14px;background:rgba(0,20,30,.5);border:1px solid #00e5ff22;
            border-radius:4px;padding:12px 18px">
  <div style="font-size:10px;color:#334;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">Quick Navigation</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px">
    <a class="ql orange" href="/admin/whatchanged">What Changed</a>
    <a class="ql" href="/admin/objects">Object Search</a>
    <a class="ql" href="/admin/component">Components</a>
    <a class="ql" href="/admin/page">Pages</a>
    <a class="ql" href="/admin/record">Records</a>
    <a class="ql" href="/admin/ae">AE Programs</a>
    <a class="ql" href="/admin/peoplecode">PeopleCode</a>
    <a class="ql" href="/admin/graph">Graph Explorer</a>
    <a class="ql" href="/admin/ib">IB Explorer</a>
    <a class="ql" href="/admin/tracing">Tracing</a>
    <a class="ql" href="/admin/sqlws">SQL Workspace</a>
    <a class="ql" href="/admin/secaudit">Security Audit</a>
    <a class="ql" href="/admin/access">Access Path</a>
    <a class="ql" href="/admin/riskanalysis">Risk Analyzer</a>
    <a class="ql" href="/admin/compflow">Event Flow</a>
    <a class="ql" href="/admin/compseq">PC Timeline</a>
    <a class="ql" href="/admin/sqrsearch">SQR Search</a>
    <a class="ql" href="/admin/impact">Impact</a>
    <a class="ql" href="/admin/topology">Topology</a>
    <a class="ql" href="/admin/log_viewer">Log Viewer</a>
    <a class="ql" href="/admin/users">Users</a>
    <a class="ql purple" href="/admin/assistant">AI Assistant</a>
  </div>
</div>
</div><!-- /max-width -->

<script>
const $ = id => document.getElementById(id);
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

function _sparkline(vals, color, w=100, h=28) {
  if (!vals.length) return '';
  const min = Math.min(...vals), max = Math.max(...vals, min + 1);
  const range = max - min || 1;
  const pts = vals.map((v, i) => {
    const x = ((i / Math.max(vals.length - 1, 1)) * (w - 4) + 2).toFixed(1);
    const y = (h - 2 - ((v - min) / range) * (h - 6)).toFixed(1);
    return `${x},${y}`;
  }).join(' ');
  const lp = pts.split(' ').at(-1).split(',');
  return `<svg class="mini-spark" width="${w}" height="${h}">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" opacity=".9"/>
    <circle cx="${lp[0]}" cy="${lp[1]}" r="2.5" fill="${color}"/>
  </svg>`;
}

async function loadAlerts(env) {
  try {
    const d = await api(`/api/runtime/alerts?env=${encodeURIComponent(env)}`);
    const alerts = d.alerts || [];
    $('alertBadge').textContent = alerts.length ? `· ${alerts.length} active` : '· All Clear';
    $('alertBadge').style.color = d.error_count > 0 ? '#ff4444' : d.warn_count > 0 ? '#ff9f43' : '#00cc66';
    if (!alerts.length) {
      $('alertBody').innerHTML = '<div style="color:#00cc66;font-size:13px">✓ No active alerts</div>';
      return;
    }
    $('alertBody').innerHTML = alerts.slice(0, 6).map(a => `
      <div class="alert-item">
        <span class="${a.severity === 'error' ? 'sev-error' : 'sev-warn'}">${a.severity.toUpperCase()}</span>
        <span>${esc(a.message)}</span>
        ${a.data?._links?.admin ? `<a href="${a.data._links.admin}" style="color:#00e5ff;font-size:10px;margin-left:auto;white-space:nowrap">→</a>` : ''}
      </div>`).join('');
  } catch(e) {
    $('alertBody').innerHTML = `<span class="muted" style="font-size:12px">Alerts unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadRuntime(env) {
  try {
    const d = await api(`/api/runtime/status?env=${encodeURIComponent(env)}`);
    const ps = d.process_summary?.totals || {};
    const ae = d.ae_running?.count ?? 0;
    const ib = d.ib_summary?.ib || {};
    const ibPend = Object.values(ib).flat()
      .filter(r => (r.pubstatus ?? r.subconstatus ?? 4) !== 4)
      .reduce((s, r) => s + (r.cnt || 0), 0);

    const statColor = (v, badIfPos) => v > 0 ? (badIfPos ? 'red' : 'green') : 'muted';
    $('runtimeBody').innerHTML = `
      <div class="stat-row">
        <div class="stat"><span class="stat-val">${ps.total ?? '—'}</span><span class="stat-lbl">Processes</span></div>
        <div class="stat"><span class="stat-val ${statColor(ps.active,false)}">${ps.active ?? 0}</span><span class="stat-lbl">Active</span></div>
        <div class="stat"><span class="stat-val ${statColor(ps.error,true)}">${ps.error ?? 0}</span><span class="stat-lbl">Errors</span></div>
        <div class="stat"><span class="stat-val ${statColor(ae,false)}">${ae}</span><span class="stat-lbl">AE Running</span></div>
        <div class="stat"><span class="stat-val ${statColor(ibPend,true)}">${ibPend}</span><span class="stat-lbl">IB Pending</span></div>
      </div>
      ${d.warnings?.length ? `<div style="font-size:11px;color:#334;margin-top:4px">${esc(d.warnings[0]?.message||'')}</div>` : ''}`;
  } catch(e) {
    $('runtimeBody').innerHTML = `<span class="muted" style="font-size:12px">Unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadLog(env) {
  try {
    const [srcs, ae, igw] = await Promise.allSettled([
      api('/api/logs/sources'),
      api(`/api/logs/prcs-ae-summary?env=${encodeURIComponent(env)}`),
      api(`/api/logs/igw-summary?env=${encodeURIComponent(env)}`),
    ]);

    const sources = srcs.value || [];
    const lastIngest = sources.reduce((latest, s) => {
      const t = s.last_ingest || '';
      return t > latest ? t : latest;
    }, '');
    const srcErrors = sources.filter(s => s.last_error).length;
    const aed = ae.value || {};
    const igwd = igw.value || {};

    $('logBody').innerHTML = `
      <div class="stat-row">
        <div class="stat">
          <span class="stat-val">${sources.length}</span>
          <span class="stat-lbl">Log Sources</span>
        </div>
        <div class="stat">
          <span class="stat-val ${srcErrors > 0 ? 'red' : 'green'}">${srcErrors > 0 ? srcErrors : '✓'}</span>
          <span class="stat-lbl">Source Errors</span>
        </div>
        <div class="stat">
          <span class="stat-val ${(aed.error_count||0) > 0 ? 'orange' : 'green'}">${aed.error_count ?? 0}</span>
          <span class="stat-lbl">PRCS AE Errors</span>
        </div>
        <div class="stat">
          <span class="stat-val ${(igwd.total||0) > 0 ? 'orange' : 'green'}">${igwd.total ?? 0}</span>
          <span class="stat-lbl">IGW Errors</span>
        </div>
      </div>
      <div style="font-size:11px;color:#334;margin-top:4px">
        Last ingest: ${lastIngest ? lastIngest.replace('T',' ').substring(0,16) : '—'}
      </div>`;
  } catch(e) {
    $('logBody').innerHTML = `<span class="muted" style="font-size:12px">Unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadDriftAndTrends(env) {
  try {
    // Drift
    const driftP = api('/api/drift/latest?env1=HCM&env2=FSCM').catch(() => null);
    const histP  = api(`/api/runtime/history?env=${encodeURIComponent(env)}&hours=6`).catch(() => ({snapshots:[]}));
    const [driftD, histD] = await Promise.all([driftP, histP]);

    // Drift section
    let driftHtml = '';
    if (driftD) {
      const alerts = (driftD.alerts || []).filter(a => !a.resolved_at);
      driftHtml = `<div style="font-size:12px;color:#9ab">
        Drift vs FSCM: <span style="color:${alerts.length ? '#ff9f43':'#00cc66'}">${alerts.length} alert${alerts.length===1?'':'s'}</span>
      </div>`;
      if (alerts.length) {
        driftHtml += alerts.slice(0,2).map(a =>
          `<div style="font-size:11px;color:#ff9f43;margin-top:2px">⚠ ${esc(a.message||a.alert_type||'')}</div>`
        ).join('');
      }
    } else {
      driftHtml = '<div style="font-size:12px;color:#334">Drift data unavailable</div>';
    }
    $('driftBody').innerHTML = driftHtml;

    // Sparklines from runtime history
    const snaps = (histD.snapshots || []);
    if (snaps.length < 2) {
      $('sparkBody').innerHTML = '<div style="font-size:11px;color:#334">Not enough history yet — check back in a few minutes.</div>';
      return;
    }
    const metrics = [
      {key:'process_active', label:'Active', color:'#00e5ff'},
      {key:'process_error',  label:'Errors', color:'#ff4444'},
      {key:'ib_pending',     label:'IB',     color:'#ffdd55'},
      {key:'alert_count',    label:'Alerts', color:'#ff6b6b'},
    ];
    let sparkHtml = '<div class="spark-row">';
    metrics.forEach(m => {
      const vals = snaps.map(s => s[m.key] ?? 0);
      const cur  = vals.at(-1) ?? 0;
      sparkHtml += `<div class="spark-tile">
        <span class="spark-lbl">${m.label}</span>
        <span class="spark-val" style="color:${m.color}">${cur}</span>
        ${_sparkline(vals, m.color)}
      </div>`;
    });
    sparkHtml += '</div><div style="font-size:10px;color:#223;margin-top:4px">${snaps.length} pts · 6h trend</div>';
    $('sparkBody').innerHTML = sparkHtml.replace('${snaps.length}', snaps.length);
  } catch(e) {
    $('driftBody').innerHTML = `<span class="muted" style="font-size:12px">Unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadDash() {
  const env = $('envSel').value || 'HCM';
  $('lastTs').textContent = 'Loading…';
  await Promise.allSettled([
    loadAlerts(env),
    loadRuntime(env),
    loadLog(env),
    loadDriftAndTrends(env),
  ]);
  $('lastTs').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

(async () => {
  try {
    const cfg = await api('/api/runtime/config');
    $('envSel').innerHTML = (cfg.envs || ['HCM']).map(e =>
      `<option value="${esc(e)}">${esc(e)}</option>`
    ).join('');
  } catch {
    $('envSel').innerHTML = '<option value="HCM">HCM</option>';
  }
  await loadDash();
  setInterval(loadDash, 60000);
})();
</script>""")


@router.get("/users", response_class=HTMLResponse)
def admin_users():
    return _shell("User Management", "users", content="""\
<div style="padding:24px">
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

        .card {
            border: 1px solid #00e5ff;
            box-shadow: 0 0 12px rgba(0,229,255,.4);
            padding: 20px;
            margin-top: 20px;
            max-width: 900px;
            background: rgba(0, 20, 30, .75);
        }

        button {
            background: #00e5ff;
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 14px;
            margin: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 16px;
        }

        th, td {
            border-bottom: 1px solid #1e5b66;
            padding: 8px;
            text-align: left;
        }

        input {
            padding: 8px;
            margin: 4px;
            background: #0b1b24;
            color: white;
            border: 1px solid #00e5ff;
        }

        a {
            color: #00e5ff;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }
</style>
    <div class="card">
        <h2>Authelia Users</h2>

	<button onclick="syncAllIdentities()">Sync All</button>

        <div>
            <h3>PeopleSoft Lookup</h3>
            <input id="opridSearch" placeholder="Search OPRID">
            <button onclick="searchOprids()">Search PeopleSoft</button>
            <div id="opridResults"></div>
            <hr>

            <input id="username" placeholder="Username / OPRID">
            <input id="password" placeholder="Password" type="password">
            <input id="displayname" placeholder="Display Name">
            <input id="email" placeholder="Email">
            <div id="groupCheckboxes"></div>
            <button onclick="createUser()">Create User</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Username</th>
                    <th>Display Name</th>
                    <th>Email</th>
                    <th>Groups</th>
                    <th>Disabled</th>
                    <th>Identity Status</th>
                    <th>MFA</th>
                    <th>Last Seen</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="users"></tbody>
        </table>
    </div>

    <div class="card">
        <h2>Provision Requests</h2>
        <button onclick="loadProvisionRequests()">Refresh</button>
        <label style="margin-left:12px;font-size:12px">
            <select id="reqStatusFilter" onchange="loadProvisionRequests()" style="font-size:12px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px;">
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
            </select>
        </label>
        <table style="margin-top:8px">
            <thead>
                <tr>
                    <th>OPRID</th>
                    <th>Display Name</th>
                    <th>Reason</th>
                    <th>Requested By</th>
                    <th>Created</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="provisionRequestRows"></tbody>
        </table>
    </div>

    <div class="card">
        <h2>Identity Audit Log</h2>
        <button onclick="loadAudit()">Refresh Audit</button>

        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Target</th>
                    <th>Detail</th>
                </tr>
            </thead>
            <tbody id="auditRows"></tbody>
        </table>

        <h2 style="margin-top:24px">Authelia Authentication Log</h2>
        <button onclick="loadAuthLogs()">Refresh</button>
        <label style="margin-left:12px;font-size:12px"><input type="checkbox" id="failedOnly" onchange="loadAuthLogs()"> Failed only</label>
        <table style="margin-top:8px">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Username</th>
                    <th>Result</th>
                    <th>Factor</th>
                    <th>IP</th>
                </tr>
            </thead>
            <tbody id="authLogRows"></tbody>
        </table>
    </div>

<script>
async function api(path, options = {}) {
    const res = await fetch(path, options);

    if (res.status === 401) {
        window.location.reload();
        return;
    }

    if (!res.ok) {
        const msg = await res.text();
        alert(msg);
        throw new Error(msg);
    }

    return res.json();
}

async function loadGroups() {
    const groups = await api('/authelia/groups');
    const box = document.getElementById('groupCheckboxes');
    box.innerHTML = '';

    groups.forEach(g => {
        const label = document.createElement('label');
        label.style.marginRight = '16px';
        label.innerHTML = `
            <input type="checkbox" class="group-check" value="${g}">
            ${g}
        `;
        box.appendChild(label);
    });
}

function selectedGroups() {
    return Array.from(document.querySelectorAll('.group-check:checked'))
        .map(x => x.value);
}

async function loadUsers() {
    const [users, statuses, mfaStatuses] = await Promise.all([
        api('/authelia/users'),
        api('/api/identity/status?env=HCM'),
        api('/authelia/mfa/status').catch(() => []),
    ]);

    const statusMap = {};
    statuses.forEach(s => statusMap[s.username] = s);
    const mfaMap = {};
    mfaStatuses.forEach(m => mfaMap[m.username] = m);

    const tbody = document.getElementById('users');
    tbody.innerHTML = '';

    users.forEach(u => {
        const s = statusMap[u.username] || {};
        const m = mfaMap[u.username] || {};
        let statusText = 'Unknown';

        if (s.error) {
            statusText = 'Error';
        } else if (s.in_sync) {
            statusText = 'In Sync';
        } else if (s.peoplesoft_exists === false) {
            statusText = 'Missing in PeopleSoft';
        } else {
            statusText = 'Out of Sync';
        }

        // MFA chips
        const mfaChips = [];
        if (m.totp_configured) mfaChips.push(`<span style="background:#00332211;border:1px solid #00cc66;color:#00cc66;padding:1px 6px;font-size:10px;border-radius:2px">TOTP</span>`);
        if (m.webauthn_count > 0) mfaChips.push(`<span style="background:#00112211;border:1px solid #00aaff;color:#00aaff;padding:1px 6px;font-size:10px;border-radius:2px">WebAuthn×${m.webauthn_count}</span>`);
        if (!mfaChips.length) mfaChips.push(`<span style="color:#445;font-size:10px">none</span>`);
        const mfaHtml = mfaChips.join(' ');

        const lastSeen = m.last_seen ? m.last_seen.replace('T', ' ').substring(0, 16) : '—';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.username}</td>
            <td>${u.displayname || ''}</td>
            <td>${u.email || ''}</td>
            <td>${(u.groups || []).join(', ')}</td>
            <td>${u.disabled}</td>
            <td>${statusText}</td>
            <td>${mfaHtml}</td>
            <td style="font-size:10px;color:#8ab">${lastSeen}</td>
            <td>
                <button onclick="compareIdentity('${u.username}')">Compare</button>
                <button onclick="syncIdentity('${u.username}')">Sync</button>
                <button onclick="toggleUser('${u.username}', ${!u.disabled})">
                    ${u.disabled ? 'Enable' : 'Disable'}
                </button>
                <button onclick="resetPassword('${u.username}')">Reset Password</button>
                ${m.totp_configured || m.webauthn_count > 0 ? `<button onclick="revokeMFA('${u.username}')" style="background:#ff4400">Revoke MFA</button>` : ''}
                <button onclick="deleteUser('${u.username}')">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function revokeMFA(username) {
    if (!confirm(`Revoke ALL MFA (TOTP + WebAuthn) for ${username}? They will need to re-register on next login.`)) return;
    await api(`/authelia/mfa/${username}`, {method: 'DELETE'});
    alert(`MFA revoked for ${username}.`);
    await loadUsers();
}

async function loadAuthLogs() {
    const failedOnly = document.getElementById('failedOnly') && document.getElementById('failedOnly').checked;
    const url = `/authelia/logs?limit=50${failedOnly ? '&failed_only=true' : ''}`;
    const data = await api(url).catch(() => ({logs: []}));
    const tbody = document.getElementById('authLogRows');
    if (!tbody) return;
    tbody.innerHTML = '';
    (data.logs || []).forEach(r => {
        const tr = document.createElement('tr');
        const status = r.successful ? `<span style="color:#00cc66">✓</span>` : `<span style="color:#ff4400">✗</span>`;
        const mfaBadge = r.auth_type === '2FA' ? `<span style="color:#00aaff;font-size:10px">2FA</span>` : `<span style="color:#445;font-size:10px">1FA</span>`;
        tr.innerHTML = `<td>${r.time ? r.time.substring(0, 16) : ''}</td><td>${r.username}</td><td>${status}</td><td>${mfaBadge}</td><td style="font-size:10px;color:#8ab">${r.remote_ip || ''}</td>`;
        tbody.appendChild(tr);
    });
}

async function createUser() {
    await api('/authelia/users', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            displayname: document.getElementById('displayname').value,
            email: document.getElementById('email').value,
            groups: selectedGroups()
        })
    });

    await loadUsers();
}

async function toggleUser(username, disabled) {
    await api(`/authelia/users/${username}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({disabled})
    });

    await loadUsers();
}

async function resetPassword(username) {
    const password = prompt(`New password for ${username}:`);
    if (!password) return;

    await api(`/authelia/users/${username}/reset-password`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password})
    });

    alert('Password reset.');
}

async function deleteUser(username) {
    if (!confirm(`Delete ${username}?`)) return;

    await api(`/authelia/users/${username}`, {
        method: 'DELETE'
    });

    await loadUsers();
}

async function init() {
    await loadGroups();
    await loadUsers();
    await Promise.all([loadAudit(), loadAuthLogs(), loadProvisionRequests()]);
}

function selectOprid(r) {
    document.getElementById('username').value = r.oprid;
    document.getElementById('displayname').value = r.oprdefndesc || r.oprid;
    document.getElementById('email').value = `${r.oprid.toLowerCase()}@deathstar.chickenkiller.com`;

    const hcm = document.querySelector('.group-check[value="hcm"]');
    if (hcm) hcm.checked = true;
}

async function compareIdentity(username) {
    const data = await api(`/api/identity/compare/${username}?env=HCM`);
    alert(JSON.stringify(data, null, 2));
}

async function syncIdentity(username) {
    if (!confirm(`Sync ${username} from PeopleSoft roles?`)) return;

    const data = await api(`/api/identity/sync/${username}?env=HCM`, {
        method: 'POST'
    });

    alert(
        `Synced ${data.oprid}\n` +
        `Groups: ${(data.groups.current || []).join(', ')}\n` +
        `Disabled: ${data.disabled.new}`
    );
    await loadUsers();
}

async function provisionIdentity(oprid) {
    const password = prompt(`Initial password for ${oprid}:`);
    if (!password) return;

    const data = await api(`/api/identity/provision/${oprid}?env=HCM`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password})
    });

    alert(
        `Provisioned ${data.oprid}\n` +
        `Groups: ${(data.groups || []).join(', ')}\n` +
        `Disabled: ${data.disabled}`
    );

    await loadUsers();
}

async function searchOprids() {
    const q = document.getElementById('opridSearch').value;
    const rows = await api(`/api/peoplesoft/oprids?env=HCM&q=${encodeURIComponent(q)}`);

    const div = document.getElementById('opridResults');
    div.innerHTML = '';

    if (!rows || rows.length === 0) {
        div.textContent = 'No results.';
        return;
    }

    // Bulk action bar
    const bar = document.createElement('div');
    bar.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:6px;padding:6px;background:#1e1e2e;border-radius:4px;';

    const selAllCb = document.createElement('input');
    selAllCb.type = 'checkbox';
    selAllCb.title = 'Select All';

    const selAllLabel = document.createElement('label');
    selAllLabel.textContent = `Select All (${rows.length})`;
    selAllLabel.style.cursor = 'pointer';
    selAllLabel.onclick = () => selAllCb.click();

    const countSpan = document.createElement('span');
    countSpan.id = 'opridSelCount';
    countSpan.textContent = '0 selected';

    const bulkBtn = document.createElement('button');
    bulkBtn.textContent = 'Provision Selected';
    bulkBtn.disabled = true;
    bulkBtn.onclick = bulkProvisionSelected;

    selAllCb.onchange = () => {
        div.querySelectorAll('.oprid-checkbox').forEach(cb => { cb.checked = selAllCb.checked; });
        updateBulkBar(bulkBtn, countSpan);
    };

    bar.appendChild(selAllCb);
    bar.appendChild(selAllLabel);
    bar.appendChild(countSpan);
    bar.appendChild(bulkBtn);
    div.appendChild(bar);

    rows.forEach(r => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:2px 0;';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'oprid-checkbox';
        cb.dataset.oprid = r.oprid;
        cb.onchange = () => {
            if (!cb.checked) selAllCb.checked = false;
            updateBulkBar(bulkBtn, countSpan);
        };

        const select = document.createElement('button');
        select.textContent = 'Select';
        select.onclick = () => selectOprid(r);

        const provision = document.createElement('button');
        provision.textContent = 'Provision';
        provision.onclick = () => provisionIdentity(r.oprid);

        const request = document.createElement('button');
        request.textContent = 'Request';
        request.style.cssText = 'background:#555;';
        request.onclick = () => requestProvision(r.oprid);

        const label = document.createElement('span');
        label.textContent = `${r.oprid} - ${r.oprdefndesc || ''} - locked=${r.acctlock}`;

        row.appendChild(cb);
        row.appendChild(select);
        row.appendChild(provision);
        row.appendChild(request);
        row.appendChild(label);

        div.appendChild(row);
    });
}

function updateBulkBar(btn, countSpan) {
    const checked = document.querySelectorAll('#opridResults .oprid-checkbox:checked');
    countSpan.textContent = `${checked.length} selected`;
    btn.disabled = checked.length === 0;
}

async function bulkProvisionSelected() {
    const checked = [...document.querySelectorAll('#opridResults .oprid-checkbox:checked')];
    const oprids = checked.map(cb => cb.dataset.oprid);
    if (oprids.length === 0) return;

    if (!confirm(`Provision ${oprids.length} PeopleSoft user(s) into Authelia?\n\n${oprids.join(', ')}`)) return;

    const data = await api('/api/identity/bulk-provision?env=HCM', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oprids })
    });

    const lines = (data.results || []).map(r => {
        if (r.status === 'provisioned') return `OK ${r.oprid}: provisioned (pw: ${r.temp_password})`;
        if (r.status === 'already_exists') return `-- ${r.oprid}: already exists`;
        return `ERR ${r.oprid}: ${r.status} ${r.error || ''}`;
    });

    alert(
        `Bulk Provision: ${data.provisioned} provisioned, ${data.skipped} skipped, ${data.errors} errors\n\n` +
        lines.join('\\n')
    );

    await loadUsers();
}

async function requestProvision(oprid) {
    const reason = prompt(`Request provisioning for ${oprid}?\n\nReason (optional):`);
    if (reason === null) return;  // cancelled

    const data = await api('/api/identity/requests?env=HCM', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oprid, reason, requested_by: 'admin' })
    });

    if (data.status === 'error') {
        alert(`Error: ${data.message}`);
        return;
    }

    alert(`Provision request created for ${oprid} (ID: ${data.id})`);
    await loadProvisionRequests();
}

async function loadProvisionRequests() {
    const filter = document.getElementById('reqStatusFilter')?.value || '';
    const url = `/api/identity/requests${filter ? `?status=${filter}` : ''}`;
    const rows = await api(url);
    const tbody = document.getElementById('provisionRequestRows');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!rows || rows.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="7" style="color:#6c7086;font-style:italic">No requests</td>';
        tbody.appendChild(tr);
        return;
    }

    rows.forEach(r => {
        const tr = document.createElement('tr');

        const statusChip = {
            pending: '<span class="chip" style="background:#fab387;color:#1e1e2e">Pending</span>',
            approved: '<span class="chip" style="background:#a6e3a1;color:#1e1e2e">Approved</span>',
            rejected: '<span class="chip" style="background:#f38ba8;color:#1e1e2e">Rejected</span>',
        }[r.status] || r.status;

        const created = r.created_at ? new Date(r.created_at).toLocaleString() : '';

        let actions = '';
        if (r.status === 'pending') {
            actions = `<button onclick="approveRequest('${r.id}')">Approve</button>
                       <button onclick="rejectRequest('${r.id}')" style="background:#555;margin-left:4px">Reject</button>
                       <button onclick="cancelRequest('${r.id}')" style="background:#333;margin-left:4px">Cancel</button>`;
        } else if (r.status === 'approved' && r.temp_password) {
            actions = `<span style="font-size:11px;color:#89b4fa">pw: ${r.temp_password}</span>`;
        } else if (r.status === 'rejected' && r.reject_reason) {
            actions = `<span style="font-size:11px;color:#f38ba8">${r.reject_reason}</span>`;
        }

        tr.innerHTML = `
            <td>${r.oprid}</td>
            <td>${r.ps_displayname || ''}</td>
            <td>${r.reason || ''}</td>
            <td>${r.requested_by || ''}</td>
            <td style="font-size:11px">${created}</td>
            <td>${statusChip}</td>
            <td>${actions}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function approveRequest(reqId) {
    if (!confirm('Approve this provision request? The user will be provisioned into Authelia.')) return;
    const data = await api(`/api/identity/requests/${reqId}/approve?env=HCM`, { method: 'POST' });
    if (data.temp_password) {
        alert(`Approved and provisioned.\nOPRID: ${data.oprid}\nTemp password: ${data.temp_password}\nGroups: ${(data.groups || []).join(', ')}`);
    } else {
        alert(`Approved: ${data.note || JSON.stringify(data)}`);
    }
    await Promise.all([loadProvisionRequests(), loadUsers()]);
}

async function rejectRequest(reqId) {
    const reason = prompt('Reason for rejection (optional):');
    if (reason === null) return;
    await api(`/api/identity/requests/${reqId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
    });
    await loadProvisionRequests();
}

async function cancelRequest(reqId) {
    if (!confirm('Cancel this provision request?')) return;
    await api(`/api/identity/requests/${reqId}`, { method: 'DELETE' });
    await loadProvisionRequests();
}

async function syncAllIdentities() {
    if (!confirm('Sync all Authelia users from PeopleSoft?')) return;

    const data = await api('/api/identity/sync-all?env=HCM', {
        method: 'POST'
    });

    alert(`Sync complete. Processed ${data.count} users.`);
    await loadUsers();
}

async function loadAudit() {
    const rows = await api('/api/identity/audit?limit=50');
    const tbody = document.getElementById('auditRows');
    tbody.innerHTML = '';

    rows.reverse().forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${e.timestamp}</td>
            <td>${e.action}</td>
            <td>${e.target}</td>
            <td><pre>${JSON.stringify(e.detail, null, 2)}</pre></td>
        `;
        tbody.appendChild(tr);
    });
}


init();
</script>
</div>""")


