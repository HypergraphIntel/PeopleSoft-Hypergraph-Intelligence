import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["DeathStar Admin"])

# ── Navigation items ───────────────────────────────────────────────────────
_NAV = [
    ("home",       "Home",          "/admin/"),
    ("runtime",    "Runtime",       "/admin/runtime"),
    ("infra",      "Infra",         "/admin/infra"),
    ("tracing",    "Tracing",       "/admin/tracing"),
    ("sqlws",      "SQL Workspace", "/admin/sqlws"),
    ("ib",         "IB Explorer",   "/admin/ib"),
    ("query",      "Queries",       "/admin/query"),
    ("tree",       "Trees",         "/admin/tree"),
    ("ci",         "CIs",           "/admin/ci"),
    ("menu",       "Menus",         "/admin/menu"),
    ("pcsearch",   "PC Search",     "/admin/pcsearch"),
    ("msgcat",     "Messages",      "/admin/msgcat"),
    ("approval",   "Approvals",     "/admin/approval"),
    ("xpub",       "XML Publisher", "/admin/xpub"),
    ("navcoll",    "Nav Collections", "/admin/navcoll"),
    ("efmapping",  "Event Mapping",   "/admin/efmapping"),
    ("relcontent", "Related Content", "/admin/relcontent"),
    ("srchdef",    "Search Defs",   "/admin/srchdef"),
    ("srchcat",    "Search Cats",   "/admin/srchcat"),
    ("dropzone",   "Drop Zones",    "/admin/dropzone"),
    ("reports",    "Reports",       "/admin/reports"),
    ("envcompare", "Env Compare",   "/admin/envcompare"),
    ("tools",      "Tools",         "/admin/tools"),
    ("docs",       "Docs",          "/admin/docs"),
    ("users",      "Users",         "/admin/users"),
]


def _shell(title: str, active: str, content: str, env: bool = True, noscroll: bool = False) -> str:
    """Render a complete HTML page with the standard two-level shell."""
    nav_links = ""
    for key, label, href in _NAV:
        cls = "ds-nav-link ds-active" if key == active else "ds-nav-link"
        nav_links += f'<a class="{cls}" href="{href}">{label}</a>'

    env_html = ""
    if env:
        env_html = (
            '<div class="ds-env">'
            '<span class="ds-env-lbl">Env</span>'
            '<select class="ds-env-sel" id="globalEnv"></select>'
            '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DeathStar — {title}</title>
<link rel="icon" type="image/svg+xml" href="/static/images/empire_logo_sith_cyan.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/static/images/favicon-32.png">
<link rel="apple-touch-icon" href="/static/images/apple-touch-icon.png">
<link rel="stylesheet" href="/static/app.css">
<script src="/static/app.js"></script>
</head>
<body>
<nav class="ds-nav">
    <a class="ds-brand" href="/admin/">
        <img
            src="/static/images/empire_logo_sith_cyan.svg"
            class="ds-brand-logo"
            alt="PeopleSoft Explorer">
        <span class="ds-brand-title">PeopleSoft Explorer</span>
    </a>
    {nav_links}
  </nav>
<div class="ds-page-hdr">
  <span class="ds-page-title">{title}</span>
  {env_html}
</div>
<div class="{'ds-content ds-noscroll' if noscroll else 'ds-content'}">
{content}
</div>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
def admin_home():
    return _shell("Home", "home", env=False, content="""\
<div class="pe-home">
  <div class="pe-hero">
    <p class="pe-kicker">DeathStar Platform</p>
    <h1>PeopleSoft Explorer</h1>
    <p>Unified diagnostic, development, security, and monitoring
    console for PeopleSoft environments.</p>
    <div class="pe-actions">
      <a href="/admin/runtime">Runtime Monitor</a>
      <a href="/admin/sqlws">SQL Workspace</a>
      <a href="/admin/ib">IB Explorer</a>
      <a href="/admin/envcompare">Env Compare</a>
    </div>
  </div>
  <div class="pe-grid">
    <div class="pe-card">
      <span>Identity &amp; Security</span>
      User management, operator search, role explorer, permission analysis.
      <div style="margin-top:8px;font-size:11px">
        <a href="/admin/users">Users</a> &middot;
        <a href="/admin/operator">Operators</a> &middot;
        <a href="/admin/role">Roles</a> &middot;
        <a href="/admin/security">Security Explorer</a>
      </div>
    </div>
    <div class="pe-card">
      <span>Object Exploration</span>
      Browse records, fields, components, pages, PeopleCode, and AE programs.
      <div style="margin-top:8px;font-size:11px">
        <a href="/admin/record">Records</a> &middot;
        <a href="/admin/field">Fields</a> &middot;
        <a href="/admin/peoplecode">PeopleCode</a> &middot;
        <a href="/admin/objects">Object Explorer</a>
      </div>
    </div>
    <div class="pe-card">
      <span>Integration &amp; Tracing</span>
      Integration Broker, transaction tracing, and process monitoring.
      <div style="margin-top:8px;font-size:11px">
        <a href="/admin/ib">IB Explorer</a> &middot;
        <a href="/admin/tracing">Transaction Tracing</a> &middot;
        <a href="/admin/runtime">Runtime Monitor</a>
      </div>
    </div>
    <div class="pe-card">
      <span>Analytics &amp; Tools</span>
      Knowledge Graph, SQL Workspace, environment comparison, platform tools.
      <div style="margin-top:8px;font-size:11px">
        <a href="/admin/sqlws">SQL Workspace</a> &middot;
        <a href="/admin/envcompare">Env Compare</a> &middot;
        <a href="/admin/tools">Tools</a> &middot;
        <a href="/admin/graph">Graph Explorer</a>
      </div>
    </div>
  </div>
</div>""")


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
            border: none;
            padding: 8px 14px;
            margin: 4px;
            cursor: pointer;
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
        lines.join('\n')
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


@router.get("/security", response_class=HTMLResponse)
def admin_security():
    return _shell("Security Explorer", "security", content="""\
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

        h2, h3 {
            color: #d7faff;
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
            grid-template-columns: repeat(4, minmax(220px, 1fr));
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

        .toolbar {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        button {
            background: #00e5ff;
            border: none;
            padding: 8px 14px;
            margin: 4px 0;
            cursor: pointer;
        }

        button.link-row {
            display: block;
            width: 100%;
            background: transparent;
            color: #d7faff;
            border: 1px solid #1e5b66;
            margin: 6px 0;
            text-align: left;
        }

        button.link-row:hover,
        button.link-row.active {
            border-color: #00e5ff;
            box-shadow: 0 0 10px rgba(0,229,255,.3);
        }

        input {
            padding: 8px;
            margin: 4px 0;
            background: #0b1b24;
            color: white;
            border: 1px solid #00e5ff;
        }

        .muted {
            color: #7faab2;
        }

        .item-title {
            color: #00e5ff;
            font-weight: bold;
        }

        .item-detail {
            display: block;
            margin-top: 4px;
            color: #b8dce2;
            font-size: 12px;
        }

        .status {
            margin-top: 12px;
            color: #7faab2;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }

        .metric {
            border: 1px solid #1e5b66;
            padding: 10px;
            background: rgba(5, 18, 28, .85);
        }

        @media (max-width: 1100px) {
            .grid {
                grid-template-columns: repeat(2, minmax(220px, 1fr));
            }
        }

        @media (max-width: 700px) {
            body {
                padding: 20px;
            }

            .grid {
                grid-template-columns: 1fr;
            }
        }
</style>
    <div class="card">
        <div class="toolbar">
            <input id="roleSearch" placeholder="Filter roles">
            <button onclick="loadRoles()">Load Roles</button>
            <input id="operatorSearch" placeholder="Analyze OPRID">
            <button onclick="analyzeOperator()">Analyze Operator</button>
            <input id="compareOprid" placeholder="Compare with OPRID">
            <button onclick="compareOperators()">Compare Operators</button>
            <input id="componentAccessSearch" placeholder="Component access">
            <button onclick="analyzeComponentAccess()">Who Has Access?</button>
            <button onclick="explainAccess()">Explain Access</button>
            <button onclick="explainPageAccess()">Explain Page</button>
            <button onclick="explainMenuAccess()">Explain Menu</button>
        </div>
        <div id="status" class="status">Loading roles...</div>
        <div id="accessSummary" class="muted">Search a role, operator, or component.</div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Roles</h2>
            <div id="roles"></div>
        </div>

        <div class="card">
            <h2>Permission Lists</h2>
            <div id="permissionlists" class="muted">Select a role.</div>
        </div>

        <div class="card">
            <h2>Menus</h2>
            <div id="menus" class="muted">Select a permission list.</div>
            <h2>Components</h2>
            <div id="components" class="muted">Select a permission list.</div>
        </div>

        <div class="card">
            <h2>Pages</h2>
            <div id="pages" class="muted">Select a component.</div>
        </div>
    </div>

<script>
const ENV = 'HCM';
const state = {
    role: null,
    classid: null,
    component: null
};

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

function clearPanel(id, message) {
    const el = document.getElementById(id);
    el.innerHTML = '';
    el.className = 'muted';
    el.textContent = message;
}

function label(row, keys) {
    for (const key of keys) {
        if (row[key] !== undefined && row[key] !== null && String(row[key]).trim() !== '') {
            return row[key];
        }
    }
    return '';
}

function detail(row, keys) {
    return keys
        .map(key => row[key])
        .filter(value => value !== undefined && value !== null && String(value).trim() !== '')
        .join(' | ');
}

function renderList(id, rows, emptyText, buildButton) {
    const el = document.getElementById(id);
    el.className = '';
    el.innerHTML = '';

    if (!rows.length) {
        el.className = 'muted';
        el.textContent = emptyText;
        return;
    }

    rows.forEach(row => el.appendChild(buildButton(row)));
}

function rowButton(title, subtitle, onclick, active) {
    const btn = document.createElement('button');
    btn.className = active ? 'link-row active' : 'link-row';
    btn.onclick = onclick;

    const titleEl = document.createElement('span');
    titleEl.className = 'item-title';
    titleEl.textContent = title || '(blank)';
    btn.appendChild(titleEl);

    if (subtitle) {
        const detailEl = document.createElement('span');
        detailEl.className = 'item-detail';
        detailEl.textContent = subtitle;
        btn.appendChild(detailEl);
    }

    return btn;
}

async function loadRoles() {
    const q = document.getElementById('roleSearch').value;
    setStatus('Loading roles...');
    clearPanel('permissionlists', 'Select a role.');
    clearPanel('menus', 'Select a permission list.');
    clearPanel('components', 'Select a permission list.');
    clearPanel('pages', 'Select a component.');
    state.role = null;
    state.classid = null;
    state.component = null;
    document.getElementById('accessSummary').className = 'muted';
    document.getElementById('accessSummary').textContent = 'Role browsing mode.';

    const roles = await api(`/api/peoplesoft/roles?env=${ENV}&q=${encodeURIComponent(q)}`);
    renderList('roles', roles, 'No roles found.', row => {
        const role = label(row, ['rolename']);
        const subtitle = detail(row, ['descr', 'rolestatus']);
        return rowButton(role, subtitle, () => selectRole(role), state.role === role);
    });
    setStatus(`Loaded ${roles.length} roles.`);
}

function renderSummary(title, counts) {
    const el = document.getElementById('accessSummary');
    el.className = '';
    el.innerHTML = '';

    const heading = document.createElement('h3');
    heading.textContent = title;
    el.appendChild(heading);

    const grid = document.createElement('div');
    grid.className = 'summary';

    Object.keys(counts).forEach(key => {
        const metric = document.createElement('div');
        metric.className = 'metric';
        metric.innerHTML = `
            <span class="item-title">${counts[key]}</span>
            <span class="item-detail">${key}</span>
        `;
        grid.appendChild(metric);
    });

    el.appendChild(grid);
}

async function analyzeOperator() {
    const oprid = document.getElementById('operatorSearch').value.trim();

    if (!oprid) {
        setStatus('Enter an OPRID.');
        return;
    }

    setStatus(`Analyzing operator ${oprid}...`);
    clearPanel('pages', 'Select a component.');
    state.role = null;
    state.classid = null;
    state.component = null;

    const data = await api(`/api/peoplesoft/security/operators/${encodeURIComponent(oprid)}?env=${ENV}`);
    renderSummary(`Operator ${data.operator.oprid}`, data.counts);

    renderList('roles', data.roles, 'No roles found.', row => {
        const role = label(row, ['rolename']);
        const subtitle = detail(row, ['dynamic_sw']);
        return rowButton(role, subtitle, () => selectRole(role), false);
    });

    renderList('permissionlists', data.permissionlists, 'No permission lists found.', row => {
        const classid = label(row, ['classid']);
        const subtitle = detail(row, ['rolename', 'roleclass_dynamic_sw']);
        return rowButton(classid, subtitle, () => selectPermissionList(classid), false);
    });

    renderList('menus', data.menus, 'No menus found.', row => {
        const menu = label(row, ['menuname']);
        const subtitle = detail(row, ['rolename', 'classid', 'barname', 'baritemname']);
        return rowButton(menu, subtitle, () => {}, false);
    });

    renderList('components', data.components, 'No components found.', row => {
        const component = label(row, ['pnlgrpname']);
        const subtitle = detail(row, ['rolename', 'classid', 'menuname', 'component_descr']);
        return rowButton(component, subtitle, () => selectComponent(component), false);
    });

    setStatus(`Operator ${data.operator.oprid}: ${data.counts.roles} roles, ${data.counts.components} components.`);
}

async function analyzeComponentAccess() {
    const component = document.getElementById('componentAccessSearch').value.trim();

    if (!component) {
        setStatus('Enter a component.');
        return;
    }

    setStatus(`Analyzing access for component ${component}...`);
    clearPanel('menus', 'Component access mode.');
    clearPanel('pages', 'Select the component below to view pages.');

    const data = await api(`/api/peoplesoft/security/components/${encodeURIComponent(component)}/access?env=${ENV}`);
    renderSummary(`Component ${data.component.pnlgrpname}`, data.counts);

    renderList('roles', data.roles.map(rolename => ({rolename})), 'No roles found.', row => {
        const role = label(row, ['rolename']);
        return rowButton(role, '', () => selectRole(role), false);
    });

    renderList('permissionlists', data.permissionlists.map(classid => ({classid})), 'No permission lists found.', row => {
        const classid = label(row, ['classid']);
        return rowButton(classid, '', () => selectPermissionList(classid), false);
    });

    renderList('components', [data.component], 'No component found.', row => {
        const componentName = label(row, ['pnlgrpname']);
        const subtitle = detail(row, ['descr', 'searchrecname', 'addsrchrecname']);
        return rowButton(componentName, subtitle, () => selectComponent(componentName), false);
    });

    setStatus(`Component ${data.component.pnlgrpname}: ${data.counts.users} users through ${data.counts.access_paths} access paths.`);
}

async function explainAccess() {
    const oprid = document.getElementById('operatorSearch').value.trim();
    const component = document.getElementById('componentAccessSearch').value.trim();

    if (!oprid || !component) {
        setStatus('Enter both an OPRID and a component.');
        return;
    }

    setStatus(`Explaining ${oprid} access to ${component}...`);
    clearPanel('menus', 'Access explanation mode.');
    clearPanel('pages', 'Select a component to view pages.');

    const data = await api(`/api/peoplesoft/security/explain?env=${ENV}&oprid=${encodeURIComponent(oprid)}&component=${encodeURIComponent(component)}`);
    renderSummary(data.explanation, data.counts);

    renderList('roles', data.operator_roles || [], 'No operator roles found.', row => {
        const role = label(row, ['rolename']);
        const subtitle = detail(row, ['descr', 'dynamic_sw']);
        return rowButton(role, subtitle, () => selectRole(role), false);
    });

    const plRows = data.has_access ? (data.grant_paths || []) : (data.component_permissionlists || []);
    renderList('permissionlists', plRows, 'No matching permission lists found.', row => {
        const classid = label(row, ['classid']);
        const subtitle = data.has_access
            ? detail(row, ['rolename', 'menuname', 'decoded_actions'])
            : detail(row, ['pnlgrpname', 'class_classdefndesc']);
        return rowButton(classid, subtitle, () => selectPermissionList(classid), false);
    });

    renderList('components', [data.component_row], 'No component found.', row => {
        const componentName = label(row, ['pnlgrpname']);
        const subtitle = detail(row, ['descr', 'searchrecname', 'addsrchrecname']);
        return rowButton(componentName, subtitle, () => selectComponent(componentName), false);
    });

    if (data.has_access) {
        renderList('menus', data.grant_paths || [], 'No access paths found.', row => {
            const title = `${label(row, ['rolename'])} → ${label(row, ['classid'])}`;
            const subtitle = detail(row, ['menuname', 'pnlitemname', 'decoded_actions']);
            return rowButton(title, subtitle, () => {}, false);
        });
    } else {
        renderList('menus', (data.operator_permissionlists || []).map(row => ({...row})), 'No operator permission lists found.', row => {
            const classid = label(row, ['classid']);
            const subtitle = detail(row, ['rolename']);
            return rowButton(classid, subtitle, () => selectPermissionList(classid), false);
        });
    }

    setStatus(data.explanation);
}

async function explainPageAccess() {
    const oprid = document.getElementById('operatorSearch').value.trim();
    const page = document.getElementById('componentAccessSearch').value.trim();

    if (!oprid || !page) {
        setStatus('Enter both an OPRID and a page name.');
        return;
    }

    setStatus(`Explaining ${oprid} access to page ${page}...`);
    clearPanel('menus', 'Page access explanation mode.');
    clearPanel('pages', 'Page explanation result.');

    const data = await api(`/api/peoplesoft/security/explain-page?env=${ENV}&oprid=${encodeURIComponent(oprid)}&page=${encodeURIComponent(page)}`);
    renderSummary(data.explanation, data.counts);

    renderList('components', data.components || [], 'No components found for page.', row => {
        const component = label(row, ['pnlgrpname']);
        const subtitle = detail(row, ['pnlname', 'market', 'itemnum']);
        return rowButton(component, subtitle, () => selectComponent(component), (data.matching_components || []).includes(component));
    });

    renderList('permissionlists', data.grant_paths || [], 'No grant paths found.', row => {
        const classid = label(row, ['classid']);
        const subtitle = detail(row, ['rolename', 'pnlgrpname', 'decoded_actions']);
        return rowButton(classid, subtitle, () => selectPermissionList(classid), false);
    });

    renderList('menus', data.grant_paths || [], 'No menu/action paths found.', row => {
        const title = `${label(row, ['rolename'])} → ${label(row, ['classid'])}`;
        const subtitle = detail(row, ['menuname', 'pnlitemname', 'pnlgrpname', 'decoded_actions']);
        return rowButton(title, subtitle, () => {}, false);
    });

    const pageRows = [data.page_row, ...(data.fields || []).slice(0, 30)];
    renderList('pages', pageRows, 'No page found.', row => {
        const pageName = label(row, ['pnlname']) || `${label(row, ['recname'])}.${label(row, ['fieldname'])}`;
        const flags = [];
        if (String(row.invisible || '0') === '1') flags.push('Invisible');
        if (String(row.displayonly || '0') === '1') flags.push('Display Only');
        const subtitle = detail(row, ['descr', 'pnltype', 'recname', 'fieldname', 'lbltext']) + (flags.length ? ` | ${flags.join(', ')}` : '');
        return rowButton(pageName, subtitle, () => {}, false);
    });

    setStatus(data.explanation);
}

async function explainMenuAccess() {
    const oprid = document.getElementById('operatorSearch').value.trim();
    const menu = document.getElementById('componentAccessSearch').value.trim();

    if (!oprid || !menu) {
        setStatus('Enter both an OPRID and a menu name.');
        return;
    }

    setStatus(`Explaining ${oprid} access to menu ${menu}...`);
    clearPanel('components', 'Menu access explanation mode.');
    clearPanel('pages', 'Select a component to view pages.');

    const data = await api(`/api/peoplesoft/security/explain-menu?env=${ENV}&oprid=${encodeURIComponent(oprid)}&menu=${encodeURIComponent(menu)}`);
    renderSummary(data.explanation, data.counts);

    renderList('menus', data.grant_paths || [], 'No menu grant paths found.', row => {
        const title = label(row, ['menuname']);
        const subtitle = detail(row, ['rolename', 'classid', 'barname', 'baritemname']);
        return rowButton(title, subtitle, () => {}, false);
    });

    renderList('permissionlists', data.grant_paths || [], 'No permission lists found.', row => {
        const classid = label(row, ['classid']);
        const subtitle = detail(row, ['rolename']);
        return rowButton(classid, subtitle, () => selectPermissionList(classid), false);
    });

    setStatus(data.explanation);
}

async function compareOperators() {
    const oprid1 = document.getElementById('operatorSearch').value.trim();
    const oprid2 = document.getElementById('compareOprid').value.trim();
    if (!oprid1 || !oprid2) {
        setStatus('Enter both an OPRID (Analyze field) and a comparison OPRID (Compare field).');
        return;
    }
    setStatus(`Comparing ${oprid1} vs ${oprid2}...`);

    const d = await api(`/api/peoplesoft/security/compare-operators?env=${ENV}&oprid1=${encodeURIComponent(oprid1)}&oprid2=${encodeURIComponent(oprid2)}`);
    const r = d.roles || {}, pl = d.permission_lists || {}, co = d.components || {};

    function diffSection(title, data, key1, key2) {
        const only1 = data[key1] || [], only2 = data[key2] || [], shared = data.shared || [], counts = data.counts || {};
        let html = `<div style="margin-bottom:12px"><b style="color:#00e5ff">${title}</b>`;
        html += ` <span class="subtitle">${counts.oprid1||0} vs ${counts.oprid2||0} (${counts.shared||0} shared)</span>`;
        if (only1.length) html += `<div style="margin-top:4px"><span class="role-chip" style="background:#2a1200;border:1px solid #ff8800;color:#ff8800">Only ${oprid1}</span> ${only1.slice(0,20).map(n=>`<a href="/admin/object/${title==='Roles'?'role':'permissionlist'}/${n}" style="color:#ff8800">${n}</a>`).join(', ')}${only1.length>20?` +${only1.length-20} more`:''}</div>`;
        if (only2.length) html += `<div style="margin-top:2px"><span class="role-chip" style="background:#001a2a;border:1px solid #44aaff;color:#44aaff">Only ${oprid2}</span> ${only2.slice(0,20).map(n=>`<a href="/admin/object/${title==='Roles'?'role':'permissionlist'}/${n}" style="color:#44aaff">${n}</a>`).join(', ')}${only2.length>20?` +${only2.length-20} more`:''}</div>`;
        if (!only1.length && !only2.length) html += ' <span style="color:#00cc66">&#x2714; Identical</span>';
        html += '</div>';
        return html;
    }

    let html = `<div style="border:1px solid #00e5ff22;padding:12px;background:rgba(0,20,30,.6);margin-top:8px">`;
    html += `<b style="font-size:13px">&#9878; Security Comparison: <a href="/admin/object/operator/${oprid1}">${oprid1}</a> vs <a href="/admin/object/operator/${oprid2}">${oprid2}</a></b>`;
    html += `<hr style="border-color:#00e5ff22;margin:8px 0">`;
    html += diffSection('Roles', r, 'only_in_oprid1', 'only_in_oprid2');
    html += diffSection('Permission Lists', pl, 'only_in_oprid1', 'only_in_oprid2');
    const compMsg = co.counts ? `${co.counts.oprid1||0} vs ${co.counts.oprid2||0} (${co.counts.shared||0} shared)` : '';
    html += `<div><b style="color:#00e5ff">Components</b> <span class="subtitle">${compMsg}</span>`;
    const onlyC1 = co.only_in_oprid1 || [], onlyC2 = co.only_in_oprid2 || [];
    if (onlyC1.length) html += `<div style="margin-top:4px"><span class="role-chip" style="background:#2a1200;border:1px solid #ff8800;color:#ff8800">Only ${oprid1}</span> ${onlyC1.slice(0,10).map(n=>`<a href="/admin/object/component/${n}" style="color:#ff8800">${n}</a>`).join(', ')}${onlyC1.length>10?` +${onlyC1.length-10} more`:''}</div>`;
    if (onlyC2.length) html += `<div style="margin-top:2px"><span class="role-chip" style="background:#001a2a;border:1px solid #44aaff;color:#44aaff">Only ${oprid2}</span> ${onlyC2.slice(0,10).map(n=>`<a href="/admin/object/component/${n}" style="color:#44aaff">${n}</a>`).join(', ')}${onlyC2.length>10?` +${onlyC2.length-10} more`:''}</div>`;
    if (!onlyC1.length && !onlyC2.length) html += ' <span style="color:#00cc66">&#x2714; Identical</span>';
    html += '</div></div>';

    document.getElementById('accessSummary').innerHTML = html;
    setStatus(`Compared ${oprid1} vs ${oprid2} — ${r.counts?.oprid1||0} vs ${r.counts?.oprid2||0} roles, ${pl.counts?.oprid1||0} vs ${pl.counts?.oprid2||0} permission lists.`);
}

async function selectRole(rolename) {
    state.role = rolename;
    state.classid = null;
    state.component = null;
    setStatus(`Loading permission lists for ${rolename}...`);
    clearPanel('menus', 'Select a permission list.');
    clearPanel('components', 'Select a permission list.');
    clearPanel('pages', 'Select a component.');

    const rows = await api(`/api/peoplesoft/roles/${encodeURIComponent(rolename)}/permissionlists?env=${ENV}`);
    renderList('permissionlists', rows, 'No permission lists found.', row => {
        const classid = label(row, ['classid']);
        const subtitle = detail(row, ['dynamic_sw']);
        return rowButton(classid, subtitle, () => selectPermissionList(classid), state.classid === classid);
    });
    setStatus(`Role ${rolename} has ${rows.length} permission lists.`);
}

async function selectPermissionList(classid) {
    state.classid = classid;
    state.component = null;
    setStatus(`Loading menus and components for ${classid}...`);
    clearPanel('pages', 'Select a component.');

    const [menus, components, pageGrants] = await Promise.all([
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/menus?env=${ENV}`),
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/components?env=${ENV}`),
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/page-grants?env=${ENV}`),
    ]);

    renderList('menus', menus, 'No menus found.', row => {
        const menu = label(row, ['menuname']);
        const subtitle = detail(row, ['barname', 'baritemname']);
        return rowButton(menu, subtitle, () => {}, false);
    });

    renderList('components', components, 'No components found.', row => {
        const component = label(row, ['pnlgrpname']);
        const subtitle = detail(row, ['menuname', 'component_descr', 'component_searchrecname', 'market']);
        return rowButton(component, subtitle, () => selectComponent(component), state.component === component);
    });

    renderPageGrantsForPL(pageGrants, classid);

    setStatus(`Permission list ${classid}: ${menus.length} menus, ${components.length} components, ${pageGrants.length} page grants.`);
}

function _actionChips(actions) {
    const COLOR = {Add:'#00cc66','Update/Display':'#00aaff','Update All':'#ffaa00','Correction':'#ff8800'};
    return (actions || []).map(a => {
        const c = COLOR[a] || '#8ab';
        return `<span style="background:${c}22;border:1px solid ${c};color:${c};border-radius:3px;padding:1px 5px;font-size:10px;margin-right:3px">${a}</span>`;
    }).join('');
}

function renderPageGrantsForPL(pageGrants, classid) {
    const el = document.getElementById('pages');
    el.className = '';
    if (!pageGrants || !pageGrants.length) {
        el.className = 'muted';
        el.textContent = 'No page-level grants found. Select a component for structural pages.';
        return;
    }

    // Group by baritemname (component)
    const groups = {};
    const order = [];
    for (const row of pageGrants) {
        const comp = row.baritemname || '';
        if (!groups[comp]) { groups[comp] = []; order.push(comp); }
        groups[comp].push(row);
    }

    let html = `<div style="font-size:10px;color:#8ab;margin-bottom:6px">${pageGrants.length} page grants across ${order.length} components for <b style="color:#ff8800">${classid}</b> — <a href="#" onclick="event.preventDefault();clearPageGrants()" style="color:#8ab">clear</a></div>`;
    for (const comp of order) {
        const pages = groups[comp];
        html += `<div style="margin-bottom:8px">
            <div style="font-size:11px;color:#00e5ff;font-weight:600;cursor:pointer" onclick="selectComponent('${comp.replace(/'/g,"\\'")}')">&#x25B8; ${comp} <span style="color:#8ab;font-weight:normal">(${pages.length})</span></div>
            <div style="padding-left:12px">`;
        for (const p of pages) {
            const chips = _actionChips(p.decoded_actions);
            const disp = p.displayonly ? `<span style="color:#ffaa00;font-size:10px">Display Only</span>` : '';
            html += `<div style="font-size:11px;padding:1px 0">${p.pnlitemname} ${chips}${disp}</div>`;
        }
        html += `</div></div>`;
    }
    el.innerHTML = html;
}

function clearPageGrants() {
    clearPanel('pages', 'Select a component.');
}

async function selectComponent(component) {
    state.component = component;
    setStatus(`Loading pages and page grants for ${component}...`);

    const [pages, pgGrants] = await Promise.all([
        api(`/api/peoplesoft/components/${encodeURIComponent(component)}/pages?env=${ENV}`),
        api(`/api/peoplesoft/components/${encodeURIComponent(component)}/page-grants?env=${ENV}`),
    ]);

    // Build permission-list map by pnlitemname for annotation
    const plByPage = {};
    for (const g of (pgGrants || [])) {
        const pg = g.pnlitemname || '';
        if (!plByPage[pg]) plByPage[pg] = [];
        plByPage[pg].push({classid: g.classid, decoded_actions: g.decoded_actions, displayonly: g.displayonly});
    }

    const el = document.getElementById('pages');
    el.className = '';
    el.innerHTML = '';

    if (!pages.length && !pgGrants.length) {
        el.className = 'muted';
        el.textContent = 'No pages found.';
        return;
    }

    if (pages.length) {
        const hdr = document.createElement('div');
        hdr.style.cssText = 'font-size:10px;color:#8ab;margin-bottom:6px';
        hdr.textContent = `${pages.length} structural pages`;
        el.appendChild(hdr);

        pages.forEach(row => {
            const page = row.pnlname || '';
            const grants = plByPage[page] || [];
            const subtitle = [row.itemnum, row.market, row.page_descr].filter(Boolean).join(' | ');
            const btn = rowButton(page, subtitle, () => {}, false);
            if (grants.length) {
                const gDiv = document.createElement('div');
                gDiv.style.cssText = 'font-size:10px;color:#8ab;padding:2px 8px 4px';
                gDiv.innerHTML = grants.slice(0, 5).map(g => {
                    const chips = _actionChips(g.decoded_actions);
                    return `<span style="color:#ff8800">${g.classid}</span> ${chips}`;
                }).join('  ') + (grants.length > 5 ? ` <span>+${grants.length - 5} more</span>` : '');
                btn.appendChild(gDiv);
            }
            el.appendChild(btn);
        });
    }

    if (pgGrants.length) {
        const pgsWithoutStruct = pgGrants.filter(g => !pages.some(p => p.pnlname === g.pnlitemname));
        if (pgsWithoutStruct.length) {
            const hdr = document.createElement('div');
            hdr.style.cssText = 'font-size:10px;color:#8ab;margin:8px 0 4px';
            hdr.textContent = `${pgsWithoutStruct.length} additional page grants (not in structural page list)`;
            el.appendChild(hdr);
            pgsWithoutStruct.forEach(g => {
                const btn = rowButton(g.pnlitemname, `${g.classid} | ${(g.decoded_actions||[]).join(', ')}`, () => {}, false);
                el.appendChild(btn);
            });
        }
    }

    setStatus(`Component ${component}: ${pages.length} pages, ${pgGrants.length} page grants.`);
}

document.getElementById('roleSearch').addEventListener('keydown', event => {
    if (event.key === 'Enter') {
        loadRoles();
    }
});

document.getElementById('operatorSearch').addEventListener('keydown', event => {
    if (event.key === 'Enter') {
        analyzeOperator();
    }
});

document.getElementById('componentAccessSearch').addEventListener('keydown', event => {
    if (event.key === 'Enter') {
        analyzeComponentAccess();
    }
});

loadRoles();
</script>

<div class="card" style="margin-top:24px">
    <h2>Security Reports</h2>
    <div class="toolbar">
        <select id="reportType" style="background:#0b1b24;color:white;border:1px solid #00e5ff;padding:8px">
            <option value="empty_roles">Roles with No Users</option>
            <option value="unused_permission_lists">Unused Permission Lists</option>
            <option value="top_operators_by_roles">Top Operators by Role Count</option>
            <option value="top_roles_by_users">Top Roles by User Count</option>
            <option value="permission_list_role_coverage">Permission Lists by Role Coverage</option>
            <option value="locked_operators">Locked Operator Accounts</option>
        </select>
        <input id="reportLimit" type="number" value="50" min="1" max="500" style="width:70px">
        <button onclick="loadReport()">Run Report</button>
    </div>
    <div id="reportNote" class="muted" style="margin-top:8px"></div>
    <div id="reportTable" style="margin-top:12px;overflow-x:auto"></div>
</div>

<script>
async function loadReport() {
    const rtype = document.getElementById('reportType').value;
    const limit = parseInt(document.getElementById('reportLimit').value) || 50;
    document.getElementById('reportNote').textContent = 'Loading...';
    document.getElementById('reportTable').innerHTML = '';
    try {
        const d = await api(`/api/peoplesoft/security/reports?env=${ENV}&report=${encodeURIComponent(rtype)}&limit=${limit}`);
        document.getElementById('reportNote').textContent = d.note || '';
        if (!d.rows || !d.rows.length) {
            document.getElementById('reportTable').innerHTML = '<p class="muted">No rows returned.</p>';
            return;
        }
        const cols = d.columns || Object.keys(d.rows[0]);
        let h = `<table style="border-collapse:collapse;width:100%;font-size:13px"><thead><tr>`;
        for (const c of cols) h += `<th style="border:1px solid #1e5b66;padding:6px 10px;color:#00e5ff;text-align:left">${c}</th>`;
        h += '</tr></thead><tbody>';
        for (const row of d.rows) {
            h += '<tr>';
            for (const c of cols) {
                const val = row[c] == null ? '' : String(row[c]);
                const isLink = (c === 'rolename' || c === 'roleuser') && val;
                const isPlLink = (c === 'classid') && val;
                const isOpLink = (c === 'oprid') && val;
                let cell = val;
                if (isLink) cell = `<a href="/admin/object/role/${encodeURIComponent(val)}">${val}</a>`;
                else if (isPlLink) cell = `<a href="/admin/object/permissionlist/${encodeURIComponent(val)}">${val}</a>`;
                else if (isOpLink) cell = `<a href="/admin/object/operator/${encodeURIComponent(val)}">${val}</a>`;
                h += `<td style="border:1px solid #1e5b66;padding:6px 10px">${cell}</td>`;
            }
            h += '</tr>';
        }
        h += '</tbody></table>';
        document.getElementById('reportTable').innerHTML = h;
    } catch (e) {
        document.getElementById('reportNote').textContent = 'Error: ' + e.message;
    }
}
</script>""")


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
            border: none;
            padding: 8px 14px;
            cursor: pointer;
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
            border: none;
            padding: 8px 14px;
            cursor: pointer;
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
            .layout, .sections {
                grid-template-columns: 1fr;
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

            <div id="sections" class="sections"></div>
        </div>
    </div>

<script>
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
    metaEl.style.display = object.sections.length ? '' : 'none';
    metaEl.textContent = `${object.sections.length} sections`;

    // Breadcrumbs
    const bc = document.getElementById('breadcrumb');
    bc.innerHTML = buildBreadcrumbs(object.type, object.name);
    bc.style.display = '';

    // ── Sections ───────────────────────────────────────────────────────────
    const sections = document.getElementById('sections');
    sections.innerHTML = '';

    object.sections.forEach(section => {
        const hasDDL = !!(section.data && section.data.ddl);
        const hasSrc = !!(section.data && section.data.source);
        const itemCount = (section.items || []).length;
        const dataKeys = Object.keys(section.data || {}).filter(k => k !== 'ddl' && k !== 'source' && !k.startsWith('_'));
        const hasData  = dataKeys.some(k => section.data[k] !== null && section.data[k] !== undefined && section.data[k] !== '' && section.data[k] !== ' ');
        const isEmpty  = !itemCount && !hasDDL && !hasSrc && !hasData;
        const isWarn   = section.name === 'Warnings';
        const isWide   = hasDDL || hasSrc;

        const card = document.createElement('div');
        let cls = 'card';
        if (isWide) cls += ' section-wide';
        if (isWarn) cls += ' section-warn';
        card.className = cls;

        // Section header with count badge
        const h = document.createElement('h2');
        h.style.cssText = 'display:flex;align-items:center;margin:0 0 8px';
        const nameSpan = document.createElement('span');
        nameSpan.textContent = section.name;
        h.appendChild(nameSpan);
        if (itemCount > 0) {
            const badge = document.createElement('span');
            badge.className = 'count-badge';
            badge.textContent = itemCount;
            h.appendChild(badge);
        }
        card.appendChild(h);

        if (hasData) {
            const dataDiv = document.createElement('div');
            renderKeyValues(dataDiv, section.data);
            card.appendChild(dataDiv);
        }

        if (hasDDL) {
            const pre = document.createElement('pre');
            pre.innerHTML = highlightSQL(section.data.ddl);
            card.appendChild(pre);
        }

        if (hasSrc) {
            const pre = document.createElement('pre');
            pre.innerHTML = highlightPeopleCode(section.data.source);
            card.appendChild(pre);
        }

        if (itemCount > 0) {
            const rowsDiv = document.createElement('div');
            renderRows(rowsDiv, section.items);
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
          <button onclick="removeRecent(${JSON.stringify(r.type)},${JSON.stringify(r.name)},event)"
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
        .replace("__OBJECT_TYPE__", json.dumps(object_type))
        .replace("__OBJECT_NAME__", json.dumps(object_name))
    )
    return html


@router.get("/object", response_class=HTMLResponse)
def admin_object_search():
    return object_explorer_page()


@router.get("/object/{object_type}/{object_name}", response_class=HTMLResponse)
def admin_object(object_type: str, object_name: str):
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
            border: none;
            padding: 8px 12px;
            cursor: pointer;
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
            ${topComp.map(r => `<div class="row clickable" onclick="window.location.href='/admin/object/component/${esc(r.component)}'">${esc(r.component)} <span class="muted">${r.ref_count} refs</span></div>`).join('')}</div>` : ''}
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
            border: none;
            padding: 8px 14px;
            cursor: pointer;
            margin-right: 8px;
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
            cursor: pointer;
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
            <input id="searchText" placeholder="Search graph nodes">
            <button onclick="searchGraph()">Search</button>
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
    setStatus('Building graph...');
    const data = await api(`/api/graph/build?env=${ENV}&limit=50&persist=true`);
    renderStats(data);
    setStatus('Graph build complete.');
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
    const target = document.getElementById('searchResults');

    if (!q) {
        target.className = 'muted';
        target.textContent = 'Enter search text.';
        return;
    }

    const rows = await api(`/api/graph/search?env=${ENV}&q=${encodeURIComponent(q)}`);
    target.innerHTML = '';
    target.className = '';

    if (!rows.length) {
        target.className = 'muted';
        target.textContent = 'No graph nodes found.';
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


@router.get("/runtime", response_class=HTMLResponse)
def admin_runtime():
    return _shell("Runtime Monitor", "runtime", noscroll=False, content="""\
<style>
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin-bottom:4px;}
h2{color:#00e5ff;border-bottom:1px solid #00e5ff33;padding-bottom:6px;font-size:13px;
   letter-spacing:2px;text-transform:uppercase;margin:20px 0 10px;}
.card{border:1px solid #00e5ff44;box-shadow:0 0 10px rgba(0,229,255,.2);
      padding:16px;margin-top:16px;background:rgba(0,20,30,.75);}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px;}
th{border-bottom:1px solid #00e5ff44;padding:5px 8px;text-align:left;color:#00e5ff;
   font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #1e3040;padding:5px 8px;}
tr:hover td{background:rgba(0,229,255,.04);}
.status-bar{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0;}
.chip{padding:5px 12px;border-radius:3px;font-size:12px;font-weight:bold;white-space:nowrap;}
.chip-active{background:#003040;border:1px solid #00e5ff;color:#00e5ff;}
.chip-error{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-success{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-muted{background:#141a20;border:1px solid #334;color:#778;}
.s-run{color:#00e5ff;} .s-que{color:#ffaa00;} .s-err{color:#ff4444;}
.s-ok{color:#00cc66;} .s-hold{color:#778;}
.alert-box{background:#2a0000;border:1px solid #ff4444;
           padding:8px 14px;color:#ff8888;margin:8px 0;font-size:12px;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;
       font-size:11px;color:#000;margin:2px;}
button.sec{background:transparent;border:1px solid #00e5ff33;color:#00e5ff;}
select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;
       padding:5px 8px;font-size:12px;}
 .ctrl{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;margin-bottom:12px;}
 .lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;
   display:block;margin-bottom:3px;}
.runtime-nav{font-size:12px;margin-bottom:16px;color:#445;}
.mono{font-family:monospace;}
.empty{color:#445;font-style:italic;padding:10px 0;font-size:12px;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.tab-row{display:flex;gap:0;margin:10px 0 0;border-bottom:1px solid #00e5ff22;}
.tab{padding:5px 14px;cursor:pointer;font-size:11px;color:#556;
     border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.sql-cell{font-family:monospace;font-size:10px;color:#9ab;max-width:360px;
          overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.pct-bar{display:inline-block;background:#0b2030;width:70px;height:8px;
         border-radius:2px;vertical-align:middle;overflow:hidden;}
.pct-fill{height:100%;background:#00e5ff;}
.ts{font-size:10px;color:#446;}
/* ── process detail panel ── */
#procPanel{position:fixed;top:0;right:-520px;width:520px;height:100%;
  background:#070e14;border-left:1px solid #00e5ff44;overflow-y:auto;
  padding:20px;transition:right .25s ease;z-index:1000;box-shadow:-4px 0 24px rgba(0,0,0,.6);}
#procPanel.open{right:0;}
#procPanel h2{color:#00e5ff;font-size:12px;letter-spacing:2px;text-transform:uppercase;
  border-bottom:1px solid #00e5ff33;padding-bottom:6px;margin:16px 0 8px;}
#procPanel .close-btn{float:right;background:transparent;border:none;color:#778;
  font-size:18px;cursor:pointer;padding:0;}
#procPanel .close-btn:hover{color:#fff;}
.p-field{display:flex;margin:4px 0;font-size:12px;}
.p-label{color:#445;min-width:130px;flex-shrink:0;font-size:11px;text-transform:uppercase;letter-spacing:.5px;}
.p-value{color:#d7faff;font-family:monospace;word-break:break-all;}
.p-value a{color:#00e5ff;text-decoration:none;} .p-value a:hover{text-decoration:underline;}
.timeline-bar{display:flex;height:6px;border-radius:3px;overflow:hidden;margin:10px 0;background:#0b1b24;}
.tl-seg{height:100%;}
.tl-queued{background:#ffaa00;}
.tl-init{background:#00e5ff;}
.tl-proc{background:#00cc66;}
.tl-done{background:#556677;}
.tl-err{background:#ff4444;}
.proc-badge{display:inline-block;padding:2px 10px;border-radius:2px;font-size:11px;font-weight:bold;margin-left:8px;}
.pb-run{background:#001828;border:1px solid #00e5ff;color:#00e5ff;}
.pb-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.pb-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.pb-hold{background:#1a1a00;border:1px solid #778;color:#778;}
.pb-que{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
  background:rgba(0,0,0,.5);z-index:999;}
.overlay.open{display:block;}
</style>
<div class="overlay" id="overlay" onclick="closeProc()"></div>
<div id="procPanel">
  <button class="close-btn" onclick="closeProc()">&#x2715;</button>
  <h1 style="font-size:14px;margin:0 0 4px;color:#00e5ff;">PROCESS DETAIL</h1>
  <div id="procPanelBody"></div>
</div>
<div class="ctrl">
  <div><span class="lbl">Environment</span><select id="envSel" onchange="refresh()"></select></div>
  <div><span class="lbl">Oracle DB</span><select id="dbSel" onchange="refresh()"></select></div>
  <div>
    <button onclick="refresh()">&#8635; Refresh</button>
    <button class="sec" id="arBtn" onclick="toggleAR()">Auto: ON</button>
    <span class="ts" id="lastTs"></span>
  </div>
</div>

<!-- ── Active Alerts ── -->
<div class="card" id="alertsCard">
  <h2>Active Alerts <span id="alertBadge"></span></h2>
  <div id="alertsArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── App Server Domains ── -->
<div class="card">
  <h2>App Server Domains</h2>
  <div id="domArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Process Scheduler Servers ── -->
<div class="card">
  <h2>Process Scheduler Servers</h2>
  <div id="srvArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Process Scheduler ── -->
<div class="card">
  <h2>Process Scheduler</h2>
  <div id="procBar" class="status-bar"></div>
  <div class="tab-row proc-tabs">
    <div class="tab on"  onclick="procTab('active')">Active / Queued</div>
    <div class="tab"     onclick="procTab('errors')">Errors</div>
    <div class="tab"     onclick="procTab('ae')">App Engine</div>
    <div class="tab"     onclick="procTab('all')">All Recent</div>
  </div>
  <div id="paneActive" class="pane on"><div id="tblActive"></div></div>
  <div id="paneErrors" class="pane"><div id="tblErrors"></div></div>
  <div id="paneAe"     class="pane"><div id="tblAe"></div></div>
  <div id="paneAll"    class="pane"><div id="tblAll"></div></div>
</div>

<!-- ── Integration Broker ── -->
<div class="card">
  <h2>Integration Broker</h2>
  <div id="ibArea"></div>
</div>

<!-- ── Oracle ── -->
<div class="card">
  <h2>Oracle DB &mdash; <span id="dbLabel"></span></h2>
  <div id="oraBar" class="status-bar"></div>
  <div id="blockAlert"></div>
  <div class="tab-row ora-tabs">
    <div class="tab on" onclick="oraTab('sessions')">Active Sessions</div>
    <div class="tab"    onclick="oraTab('blocking')">Blocking</div>
    <div class="tab"    onclick="oraTab('longops')">Long Ops</div>
    <div class="tab"    onclick="oraTab('topsql')">Top SQL</div>
  </div>
  <div id="paneSessions" class="pane on"><div id="tblSessions"></div></div>
  <div id="paneBlocking" class="pane"><div id="tblBlocking"></div></div>
  <div id="paneLongops"  class="pane"><div id="tblLongops"></div></div>
  <div id="paneTopsql"   class="pane"><div id="tblTopsql"></div></div>
</div>

<!-- ── Oracle ASH ── -->
<div class="card">
  <h2>Oracle Active Session History &mdash; <span id="ashLabel"></span></h2>
  <div id="ashBar" class="status-bar"></div>
  <div id="ashArea"><span class="muted" style="font-size:12px">Loading…</span></div>
</div>

<!-- ── Runtime Graph ── -->
<div class="card">
  <h2>Runtime Graph</h2>
  <div class="ctrl">
    <button onclick="loadRtGraph()">&#x2B58; Build Runtime Graph</button>
    <span id="graphStatus" class="ts"></span>
  </div>
  <div id="rtGraphArea" style="display:none;margin-top:10px;">
    <svg id="rtGraphSvg" width="100%" height="560"
         style="background:#030d16;border:1px solid #00e5ff22;display:block;cursor:grab;border-radius:3px;"></svg>
    <div id="rtGraphLegend" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;font-size:11px;"></div>
    <div id="rtGraphDetail" style="margin-top:6px;font-size:11px;color:#445;font-style:italic;min-height:18px;">
      Click a node to see details.
    </div>
  </div>
</div>

<script>
const RS = {
  '0':'s-err','1':'s-que','2':'s-run','3':'s-err',
  '4':'s-err','5':'s-hold','6':'s-que','7':'s-run',
  '8':'s-err','9':'s-ok'
};
let autoR = true, arTimer = null;
const INTERVAL = 30000;

const $ = id => document.getElementById(id);

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function chip(label, val, cls) {
  return `<div class="chip ${cls}">${label}: <b>${val}</b></div>`;
}

function empty(msg) { return `<div class="empty">${msg || 'No data.'}</div>`; }

function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// ── tab switching ──────────────────────────────────────
function procTab(name) {
  const tabs = document.querySelectorAll('.proc-tabs .tab');
  ['active','errors','ae','all'].forEach((n,i) => {
    if (tabs[i]) tabs[i].classList.toggle('on', n === name);
    const p = $(`pane${n.charAt(0).toUpperCase()+n.slice(1)}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

function oraTab(name) {
  const tabs = document.querySelectorAll('.ora-tabs .tab');
  ['sessions','blocking','longops','topsql'].forEach((n,i) => {
    if (tabs[i]) tabs[i].classList.toggle('on', n === name);
    const cap = n.charAt(0).toUpperCase()+n.slice(1);
    const p = $(`pane${cap}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

// ── process table ──────────────────────────────────────
function procTable(items) {
  if (!items || !items.length) return empty('No processes found.');
  const rows = items.map(r => {
    const cls = RS[r.runstatus] || '';
    const dt = (r.begindttm || '').replace('T',' ').substr(0,19);
    const tp = (r.prcstype||'').replace('Application Engine','AE').replace(/ (Process|Report)$/,'');
    return `<tr>
      <td><a class="mono" href="#" onclick="showProc(${r.prcsinstance});return false;">${r.prcsinstance}</a></td>
      <td class="mono" style="font-size:10px">${tp}</td>
      <td class="mono">${r.prcsname||''}</td>
      <td>${r.oprid||''}</td>
      <td class="mono" style="font-size:10px">${r.runcntlid||''}</td>
      <td style="font-size:10px">${r.serverbatch||''}</td>
      <td class="${cls}">${r.runstatus_label||r.runstatus}</td>
      <td class="ts">${dt}</td>
    </tr>`;
  }).join('');
  return `<table>
    <thead><tr>
      <th>Instance</th><th>Type</th><th>Program</th><th>Operator</th>
      <th>Run Control</th><th>Server</th><th>Status</th><th>Started</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ── IB rendering ───────────────────────────────────────
function renderIB(data) {
  const el = $('ibArea');
  if (!data) { el.innerHTML = empty('IB data unavailable.'); return; }
  const pub = data.ib?.published || [];
  const sub = data.ib?.subscribed || [];
  const warn = data.warnings || [];
  let html = '<div class="status-bar">';
  if (pub.length) {
    pub.forEach(r => {
      const label = r.status_label || `Pub ${r.pub_status}`;
      const cnt = r.cnt || 0;
      const cls = r.pub_status === '5' ? 'chip-error' : cnt > 0 ? 'chip-warn' : 'chip-muted';
      html += chip(label, cnt, cls);
    });
  } else {
    html += chip('Published', 0, 'chip-muted');
  }
  html += '<span style="color:#334;padding:0 6px">|</span>';
  if (sub.length) {
    sub.forEach(r => {
      const label = r.status_label || `Sub ${r.sub_status}`;
      const cnt = r.cnt || 0;
      const cls = r.sub_status === '5' ? 'chip-error' : cnt > 0 ? 'chip-warn' : 'chip-muted';
      html += chip(label, cnt, cls);
    });
  } else {
    html += chip('Subscribed', 0, 'chip-muted');
  }
  html += '</div>';
  warn.forEach(w => { html += `<div class="warn-msg">&#9888; ${w.message}</div>`; });
  el.innerHTML = html;
}

// ── Oracle rendering ───────────────────────────────────
function renderOraBar(counts) {
  let active=0, inactive=0, bg=0;
  counts.forEach(r => {
    if (r.type === 'BACKGROUND') bg += r.cnt;
    else if (r.status === 'ACTIVE') active += r.cnt;
    else inactive += r.cnt;
  });
  $('oraBar').innerHTML = [
    chip('Active', active, active>0 ? 'chip-active' : 'chip-muted'),
    chip('Inactive', inactive, 'chip-muted'),
    chip('Background', bg, 'chip-muted'),
  ].join('');
}

function renderBlocking(data) {
  const chains = data?.chains || [];
  const alertEl = $('blockAlert');
  const tblEl   = $('tblBlocking');
  if (!chains.length) {
    alertEl.innerHTML = '';
    if (tblEl) tblEl.innerHTML = empty('No blocking sessions detected.');
    return;
  }
  const waiterCount = chains.reduce((s,c) => s+(c.waiters?.length||0), 0);
  alertEl.innerHTML = `<div class="alert-box">
    &#9888; ${chains.length} blocking chain(s) &mdash; ${waiterCount} session(s) waiting
  </div>`;
  if (!tblEl) return;
  let html = '';
  chains.forEach(chain => {
    const b = chain.blocker || {};
    html += `<div style="margin:12px 0">
      <div style="color:#ff8888;font-size:11px;margin-bottom:4px">
        Blocker SID <b>${b.sid ?? chain.blocker_sid ?? '?'}</b>
        ${b.username ? `&mdash; ${b.username}` : ''}
        ${b.program  ? `(${(b.program||'').substr(0,30)})` : ''}
        ${b.event    ? `&mdash; event: ${b.event}` : ''}
      </div>
      <table><thead><tr>
        <th>Waiting SID</th><th>User</th><th>Program</th><th>Event</th><th>Wait (s)</th>
      </tr></thead><tbody>
      ${(chain.waiters||[]).map(w=>`<tr>
        <td class="mono">${w.sid}</td>
        <td>${w.username||''}</td>
        <td class="mono" style="font-size:10px">${(w.program||'').substr(0,30)}</td>
        <td style="font-size:10px">${w.event||''}</td>
        <td style="color:#ff4444">${w.seconds_in_wait??''}</td>
      </tr>`).join('')}
      </tbody></table>
    </div>`;
  });
  tblEl.innerHTML = html;
}

function renderSessions(items) {
  if (!items || !items.length) return empty('No active sessions.');
  return `<table><thead><tr>
    <th>SID</th><th>User</th><th>Program</th><th>Module</th>
    <th>Event</th><th>Wait (s)</th><th>SQL</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const wc = r.seconds_in_wait > 30 ? '#ff4444' : '#778';
    const prog = (r.program||'').replace(/@[\\w.]+$/,'').substr(0,22);
    return `<tr>
      <td class="mono">${r.sid}</td>
      <td>${r.username||''}</td>
      <td class="mono" style="font-size:10px">${prog}</td>
      <td style="font-size:10px">${r.module||''}</td>
      <td style="font-size:10px;color:#778">${r.event||''}</td>
      <td style="color:${wc}">${r.seconds_in_wait??''}</td>
      <td class="sql-cell" title="${(r.sql_text||'').replace(/"/g,'&quot;')}">${r.sql_text||''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

function renderLongops(items) {
  if (!items || !items.length) return empty('No long-running operations in progress.');
  return `<table><thead><tr>
    <th>SID</th><th>Operation</th><th>Target</th>
    <th>Progress</th><th>Elapsed (s)</th><th>Remaining (s)</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const pct = r.pct_done ?? 0;
    return `<tr>
      <td class="mono">${r.sid}</td>
      <td>${r.opname||''}</td>
      <td style="font-size:10px">${r.target||''}</td>
      <td>
        <span class="pct-bar"><span class="pct-fill" style="width:${pct}%"></span></span>
        &nbsp;${pct}%
      </td>
      <td>${r.elapsed_seconds??''}</td>
      <td style="color:#ffaa00">${r.time_remaining??''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

function renderTopSql(items) {
  if (!items || !items.length) return empty('No SQL statements in V$SQL cursor cache.');
  return `<table><thead><tr>
    <th>SQL ID</th><th>Schema</th><th>Execs</th>
    <th>Elapsed (s)</th><th>Elapsed/Exec</th><th>Buffer Gets</th><th>Last Active</th><th>SQL</th>
  </tr></thead><tbody>
  ${items.map(r => {
    const epx = r.elapsed_per_exec??0;
    const eColor = epx > 1 ? '#ff4444' : epx > 0.1 ? '#ffaa00' : 'inherit';
    return `<tr>
      <td class="mono" style="font-size:10px">${r.sql_id||''}</td>
      <td style="font-size:10px">${r.parsing_schema_name||''}</td>
      <td style="text-align:right">${r.executions??0}</td>
      <td style="text-align:right">${r.elapsed_secs??0}</td>
      <td style="text-align:right;color:${eColor}">${epx}</td>
      <td style="text-align:right">${r.buffer_gets??0}</td>
      <td class="ts">${r.last_active||''}</td>
      <td class="sql-cell" title="${(r.sql_text||'').replace(/"/g,'&quot;')}">${r.sql_text||''}</td>
    </tr>`;
  }).join('')}
  </tbody></table>`;
}

// ── data loaders ───────────────────────────────────────
async function loadStatus() {
  const env = $('envSel').value;
  const db  = $('dbSel').value;
  if (!env) return;
  try {
    const s = await api(`/api/runtime/status?env=${env}${db ? '&db='+db : ''}`);

    // Process summary bar
    const t = s.process_summary?.totals || {};
    $('procBar').innerHTML = [
      chip('Running', t.active||0,   t.active  > 0 ? 'chip-active'  : 'chip-muted'),
      chip('Error',   t.error||0,    t.error   > 0 ? 'chip-error'   : 'chip-muted'),
      chip('Success', t.success||0,  t.success > 0 ? 'chip-success' : 'chip-muted'),
      chip('Other',   t.other||0,    'chip-muted'),
      chip('Recent Total', t.total||0, 'chip-muted'),
    ].join('');

    // AE tab
    $('tblAe').innerHTML = procTable(s.ae_running?.items || []);

    // IB
    renderIB(s.ib_summary);

    // Oracle from status (if db was provided)
    if (db && s.oracle_sessions) renderOraBar(s.oracle_sessions.counts || []);
    if (db && s.blocking)        renderBlocking(s.blocking);
  } catch(e) {
    $('procBar').innerHTML = `<span class="warn-msg">Status error: ${e.message}</span>`;
  }
}

async function loadAlerts() {
  const env = $('envSel').value;
  const db  = $('dbSel').value;
  if (!env) { $('alertsArea').innerHTML = ''; $('alertBadge').innerHTML = ''; return; }
  try {
    const url = `/api/runtime/alerts?env=${encodeURIComponent(env)}${db ? '&db='+encodeURIComponent(db) : ''}`;
    const r = await api(url);
    const alerts = r.alerts || [];

    // Badge on card title
    const errCnt = r.error_count || 0;
    const warnCnt = r.warn_count || 0;
    let badge = '';
    if (errCnt) badge += `<span class="chip chip-error" style="font-size:10px;padding:2px 8px;margin-left:6px">${errCnt} error${errCnt>1?'s':''}</span>`;
    if (warnCnt) badge += `<span class="chip chip-warn" style="font-size:10px;padding:2px 8px;margin-left:6px">${warnCnt} warning${warnCnt>1?'s':''}</span>`;
    $('alertBadge').innerHTML = badge;
    $('alertsCard').style.borderColor = errCnt ? '#ff444466' : warnCnt ? '#ffaa0066' : '#00e5ff44';

    if (!alerts.length) {
      $('alertsArea').innerHTML = `<div class="empty" style="color:#00cc66">&#x2714; All clear — no active alerts</div>`;
      return;
    }

    let html = '';
    alerts.forEach(a => {
      const col = a.severity === 'error' ? '#ff4444' : '#ffaa00';
      const icon = a.severity === 'error' ? '&#x26A0;' : '&#x25B2;';
      const link = a.data?._links?.admin ? `<a href="${esc(a.data._links.admin)}" style="color:#00e5ff;font-size:10px;margin-left:8px">&#x2192; View</a>` : '';
      html += `<div class="alert-box" style="border-color:${col};color:${col};display:flex;align-items:flex-start;gap:8px;margin:4px 0">
        <span style="font-size:16px;line-height:1">${icon}</span>
        <div><span style="font-size:10px;opacity:.7;text-transform:uppercase;letter-spacing:1px">[${esc(a.code)}]</span>
          <span style="margin-left:6px">${esc(a.message)}</span>${link}</div>
      </div>`;
    });
    $('alertsArea').innerHTML = html;
  } catch(e) {
    $('alertsArea').innerHTML = `<span class="muted" style="font-size:12px">Alerts unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadDomains() {
  const env = $('envSel').value;
  if (!env) { $('domArea').innerHTML = '<span class="muted" style="font-size:12px">No environment selected.</span>'; return; }
  try {
    const d = await api(`/api/runtime/domains?env=${env}`);
    const items = d.items || [];
    const warnings = d.warnings || [];
    if (!items.length) {
      const wmsg = warnings.length ? warnings.map(w => esc(w.message||String(w))).join(' ') : 'No domain data found.';
      $('domArea').innerHTML = `<span class="muted" style="font-size:12px">${wmsg}</span>`;
      return;
    }
    const TYPE_CLS = {
      app_server:        'chip-success',
      process_scheduler: 'chip-warn',
      web:               'chip-info',
      ib:                'chip-muted',
    };
    let html = `<table><thead><tr>
      <th>Domain</th><th>Type</th><th>Host</th><th>Port</th><th>Listeners</th>
    </tr></thead><tbody>`;
    for (const dom of items) {
      const cls = TYPE_CLS[dom.domain_type] || 'chip-muted';
      const altPort = dom.alt_port ? ` / ${esc(dom.alt_port)}` : '';
      html += `<tr>
        <td class="mono">${esc(dom.domain_name)}</td>
        <td><span class="chip ${cls}" style="font-size:10px;padding:2px 8px;">${esc(dom.domain_type_label)}</span></td>
        <td class="mono" style="font-size:11px">${esc((dom.hosts||[]).join(', '))}</td>
        <td class="mono" style="font-size:11px">${esc(dom.primary_port||'—')}${altPort}</td>
        <td style="text-align:center;color:#8ab">${dom.listener_count}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    if (d.source_view) {
      html += `<div style="font-size:9px;color:#334;margin-top:4px;text-align:right;">Source: ${esc(d.source_view)}</div>`;
    }
    $('domArea').innerHTML = html;
  } catch(e) {
    $('domArea').innerHTML = `<span class="muted" style="font-size:12px">Domains unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadServers() {
  const env = $('envSel').value;
  if (!env) { $('srvArea').innerHTML = '<span class="muted" style="font-size:12px">No environment selected.</span>'; return; }
  try {
    const d = await api(`/api/runtime/servers?env=${env}`);
    const items = d.items || [];
    if (!items.length) {
      $('srvArea').innerHTML = '<span class="muted" style="font-size:12px">PSSERVERSTAT not accessible or no servers found.</span>';
      return;
    }
    const STATUS_CLS = { '3': 'chip-success', '2': 'chip-warn', '1': 'chip-muted', '5': 'chip-error' };
    let html = '<table><thead><tr><th>Server</th><th>Status</th><th>Host</th><th>AE Servers</th><th>Max CPU</th><th>Last Updated</th></tr></thead><tbody>';
    for (const s of items) {
      const cls = STATUS_CLS[String(s.serverstatus)] || 'chip-muted';
      const dt = (s.lastupddttm || '').replace('T',' ').substr(0,19);
      html += `<tr>
        <td class="mono">${esc(s.servername||'')}</td>
        <td><span class="chip ${cls}" style="font-size:10px;padding:2px 8px;">${esc(s.serverstatus_label||'')}</span></td>
        <td class="mono" style="font-size:11px">${esc(s.srvrhostname||'')}</td>
        <td style="text-align:center">${s.schdlraesrvcnt ?? '—'}</td>
        <td style="text-align:center">${s.maxcpu ?? '—'}</td>
        <td class="mono" style="font-size:10px">${dt}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    if (d.warnings && d.warnings.length) {
      html += d.warnings.map(w => `<div class="alert-box" style="margin-top:6px">${esc(w)}</div>`).join('');
    }
    $('srvArea').innerHTML = html;
  } catch(e) {
    $('srvArea').innerHTML = `<span class="muted" style="font-size:12px">Servers unavailable: ${esc(e.message)}</span>`;
  }
}

async function loadProcesses() {
  const env = $('envSel').value;
  if (!env) return;
  const [active, errors, all] = await Promise.allSettled([
    api(`/api/runtime/processes?env=${env}&status=1,2,6,7&limit=50`),
    api(`/api/runtime/processes?env=${env}&status=0,3,4,8&limit=50`),
    api(`/api/runtime/processes?env=${env}&limit=100`),
  ]);
  $('tblActive').innerHTML = procTable(active.value?.items || []);
  $('tblErrors').innerHTML = procTable(errors.value?.items || []);
  $('tblAll').innerHTML    = procTable(all.value?.items    || []);
}

async function loadOracle() {
  const db = $('dbSel').value;
  if (!db) {
    $('tblSessions').innerHTML = empty('Select an Oracle database above.');
    return;
  }
  $('dbLabel').textContent = db;

  const [sessions, counts, blocking, longops, topsql] = await Promise.allSettled([
    api(`/api/runtime/oracle?db=${db}&limit=50`),
    api(`/api/runtime/sessions?db=${db}`),
    api(`/api/runtime/blocking?db=${db}`),
    api(`/api/runtime/longops?db=${db}`),
    api(`/api/runtime/sql?db=${db}&limit=20`),
  ]);

  $('tblSessions').innerHTML = renderSessions(sessions.value?.items || []);
  if (counts.value) renderOraBar(counts.value.counts || []);
  renderBlocking(blocking.value || {chains:[]});
  $('tblLongops').innerHTML = renderLongops(longops.value?.items || []);
  $('tblTopsql').innerHTML  = renderTopSql(topsql.value?.items   || []);
}

const _WC_COLOR = {
  'CPU': '#00cc66', 'User I/O': '#00aaff', 'System I/O': '#0066cc',
  'Commit': '#ffaa00', 'Lock': '#ff4444', 'Concurrency': '#ff8800',
  'Network': '#aa66ff', 'Application': '#cc4466', 'Other': '#778',
  'Administrative': '#556', 'Configuration': '#445',
};

async function loadAsh() {
  const db = $('dbSel').value;
  if (!db) { $('ashArea').innerHTML = ''; $('ashBar').innerHTML = ''; return; }
  $('ashLabel').textContent = db;
  try {
    const [summary, topSql] = await Promise.all([
      api(`/api/runtime/ash?db=${encodeURIComponent(db)}&minutes=30`),
      api(`/api/runtime/ash/sql?db=${encodeURIComponent(db)}&minutes=30&limit=10`),
    ]);
    const wcs = summary.wait_classes || [];
    const total = summary.total_samples || 0;

    // Wait class chips
    let barHtml = wcs.map(wc => {
      const col = _WC_COLOR[wc.wait_class] || '#778';
      return `<div class="chip" style="border-color:${col}44;color:${col};background:${col}11">${esc(wc.wait_class)}: <b>${wc.pct}%</b> <span style="font-size:10px;opacity:.6">(${wc.samples})</span></div>`;
    }).join('');
    $('ashBar').innerHTML = barHtml || `<span class="muted" style="font-size:12px">No foreground ASH samples in last 30 minutes.</span>`;

    if (!total) { $('ashArea').innerHTML = ''; return; }

    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px;">`;

    // Top events
    html += `<div><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Top Wait Events</div>`;
    html += `<table><thead><tr><th>Event</th><th>Class</th><th></th><th>%</th></tr></thead><tbody>`;
    (summary.top_events || []).slice(0,8).forEach(ev => {
      const col = _WC_COLOR[ev.wait_class] || '#778';
      html += `<tr>
        <td class="mono" style="font-size:11px">${esc(ev.event)}</td>
        <td><span style="color:${col};font-size:10px">${esc(ev.wait_class)}</span></td>
        <td><div class="pct-bar"><div class="pct-fill" style="width:${Math.min(ev.pct,100).toFixed(0)}%;background:${col}"></div></div></td>
        <td style="font-size:10px;color:#9ab">${ev.pct}%</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;

    // Top SQL
    html += `<div><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Top SQL by Samples (≈ DB Time)</div>`;
    html += `<table><thead><tr><th>SQL ID</th><th>Samples</th><th>%</th><th>Text</th></tr></thead><tbody>`;
    (topSql.items || []).slice(0,8).forEach(s => {
      const txt = s.sql_text ? s.sql_text.substring(0,70) : '<span style="color:#445;font-style:italic">not in V$SQL</span>';
      html += `<tr>
        <td class="mono" style="font-size:10px;color:#00e5ff">${esc(s.sql_id)}</td>
        <td style="font-size:11px">${s.samples}</td>
        <td style="font-size:10px;color:#9ab">${s.pct}%</td>
        <td class="sql-cell">${s.sql_text ? esc(txt) : txt}</td>
      </tr>`;
    });
    html += `</tbody></table></div>`;
    html += `</div>`;

    // Top modules
    const mods = (summary.top_modules || []).filter(m => m.module !== '(unknown)').slice(0,6);
    if (mods.length) {
      html += `<div style="margin-top:10px"><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px">Top Processes</div>`;
      html += `<div style="display:flex;gap:6px;flex-wrap:wrap">`;
      mods.forEach(m => {
        html += `<div class="chip chip-muted" style="font-size:10px">${esc(m.module)} <span style="color:#00e5ff">${m.pct}%</span></div>`;
      });
      html += `</div></div>`;
    }

    html += `<div style="font-size:10px;color:#334;margin-top:10px">Source: V$ACTIVE_SESSION_HISTORY · Last 30 min · ${total} samples · Foreground sessions only</div>`;
    (summary.warnings||[]).concat(topSql.warnings||[]).forEach(w => {
      html += `<div class="warn-msg">${esc(w.message||String(w))}</div>`;
    });
    $('ashArea').innerHTML = html;
  } catch(e) {
    $('ashArea').innerHTML = `<span class="muted" style="font-size:12px">ASH unavailable: ${esc(e.message)}</span>`;
  }
}

function closeProc() {
  $('procPanel').classList.remove('open');
  $('overlay').classList.remove('open');
}

function _fmtDt(s) { return s ? s.replace('T',' ').substr(0,19) : '—'; }

function _procBadge(row) {
  const s = String(row.runstatus||'');
  const label = row.runstatus_label || `Status ${s}`;
  const cls = {'2':'pb-run','6':'pb-que','7':'pb-run','9':'pb-ok',
    '0':'pb-err','3':'pb-err','4':'pb-err','8':'pb-err','5':'pb-hold'}[s] || 'pb-hold';
  return `<span class="proc-badge ${cls}">${esc(label)}</span>`;
}

function _timelineBar(row) {
  const req = row.rqstdttm, beg = row.begindttm, end = row.enddttm;
  if (!req && !beg) return '';
  const t0 = req ? new Date(req) : new Date(beg);
  const t1 = end ? new Date(end) : new Date();
  const total = Math.max(t1 - t0, 1000);
  const segs = [];
  if (req && beg) {
    const wait = new Date(beg) - new Date(req);
    segs.push({cls:'tl-queued', pct: wait/total*100, label:'Queued'});
  }
  if (beg) {
    const run = (end ? new Date(end) : new Date()) - new Date(beg);
    const s = String(row.runstatus||'');
    const cls = ({'4':'tl-err','8':'tl-err','3':'tl-err','0':'tl-err'}[s]) ||
                ({'9':'tl-done'}[s]) || 'tl-proc';
    segs.push({cls, pct: run/total*100, label: row.runstatus_label||'Run'});
  }
  const bars = segs.map(s => `<div class="tl-seg ${s.cls}" style="width:${Math.max(s.pct,2).toFixed(1)}%" title="${s.label}"></div>`).join('');
  return `<div class="timeline-bar">${bars}</div>
  <div style="display:flex;gap:16px;font-size:10px;color:#445;margin-bottom:8px;">
    <span>Requested: ${_fmtDt(req)}</span>
    <span>Started: ${_fmtDt(beg)}</span>
    <span>Ended: ${_fmtDt(end)}</span>
  </div>`;
}

async function showProc(instance) {
  const env = $('envSel').value;
  $('procPanelBody').innerHTML = '<div style="color:#445;padding:20px 0">Loading&#8230;</div>';
  $('procPanel').classList.add('open');
  $('overlay').classList.add('open');
  try {
    const data = await api(`/api/runtime/process/${instance}?env=${env}`);
    if (!data.item) {
      $('procPanelBody').innerHTML = '<div class="warn-msg">Process not found.</div>';
      return;
    }
    const d = data.item;
    const warns = (data.warnings||[]).map(w => `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
    const aeLink = d.prcstype && d.prcstype.includes('Engine')
      ? `<a href="/admin/object/application_engine/${esc(d.prcsname)}" target="_blank">&#8599; AE Explorer</a>`
      : '';
    const traceLink = d.oprid
      ? `<a href="/admin/tracing?oprid=${esc(d.oprid)}&env=${esc(env)}" target="_blank">&#8599; Trace ${esc(d.oprid)}</a>`
      : '';
    const loc = {'1':'Client','2':'Server','3':'Default','4':'PS/nVision'}[String(d.runlocation||'')] || d.runlocation || '—';
    const orig = {'1':'Online','2':'Batch','3':'Default','4':'Daemon','5':'App Engine','6':'CI/IB'}[String(d.origination||'')] || d.origination || '—';
    const dist = {'0':'N/A','1':'Generated','2':'Posted','3':'Not Posted','4':'Content Deleted','5':'Distributed','6':'Error'}[String(d.diststatus||'')] || d.diststatus || '—';

    $('procPanelBody').innerHTML = `
${warns}
<div style="margin:8px 0 12px;">
  <span style="font-size:22px;font-weight:bold;color:#00e5ff;">#${esc(String(d.prcsinstance))}</span>
  ${_procBadge(d)}
</div>
${_timelineBar(d)}
<h2>Identity</h2>
<div class="p-field"><span class="p-label">Process Type</span><span class="p-value">${esc(d.prcstype||'—')}</span></div>
<div class="p-field"><span class="p-label">Program</span><span class="p-value">${esc(d.prcsname||'—')} ${aeLink}</span></div>
<div class="p-field"><span class="p-label">Operator</span><span class="p-value">${esc(d.oprid||'—')} ${traceLink}</span></div>
<div class="p-field"><span class="p-label">Run Control</span><span class="p-value">${esc(d.runcntlid||'—')}</span></div>
<div class="p-field"><span class="p-label">Server</span><span class="p-value">${esc(d.serverbatch||'—')}</span></div>
<div class="p-field"><span class="p-label">Run Location</span><span class="p-value">${esc(loc)}</span></div>
<div class="p-field"><span class="p-label">Origination</span><span class="p-value">${esc(orig)}</span></div>
<h2>Output</h2>
<div class="p-field"><span class="p-label">Dest Type</span><span class="p-value">${esc(d.outdest_label||d.outdesttype||'—')}</span></div>
${d.outdestformat ? `<div class="p-field"><span class="p-label">Format</span><span class="p-value">${esc(String(d.outdestformat))}</span></div>` : ''}
${d.outdest ? `<div class="p-field"><span class="p-label">Destination</span><span class="p-value" style="font-size:10px">${esc(d.outdest)}</span></div>` : ''}
<div class="p-field"><span class="p-label">Dist Status</span><span class="p-value">${esc(dist)}</span></div>
<h2>Job / Session</h2>
${d.jobinstance > 0 ? `<div class="p-field"><span class="p-label">Job Instance</span><span class="p-value">${esc(String(d.jobinstance))}</span></div>` : ''}
${d.jobname ? `<div class="p-field"><span class="p-label">Job Name</span><span class="p-value">${esc(d.jobname)}</span></div>` : ''}
${d.sessionidnum ? `<div class="p-field"><span class="p-label">Session ID</span><span class="p-value">${esc(String(d.sessionidnum))}</span></div>` : ''}
${d.prcsservername ? `<div class="p-field"><span class="p-label">Process Server</span><span class="p-value">${esc(d.prcsservername)}</span></div>` : ''}
<div id="procAshSection"><div style="color:#334;font-size:11px;margin-top:16px">Loading Oracle activity…</div></div>
`;
    // Async ASH enrichment — only for processes with a start time
    if (d.begindttm) {
      const db = $('dbSel').value;
      if (db) {
        loadProcAsh(instance, db, env, d.prcstype || '');
      } else {
        $('procAshSection').innerHTML = '<div style="color:#334;font-size:11px;margin-top:16px">Select Oracle DB above to see session activity.</div>';
      }
    } else {
      $('procAshSection').innerHTML = '';
    }
  } catch(e) {
    $('procPanelBody').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

async function loadProcAsh(instance, db, env, prcstype) {
  try {
    const r = await api(`/api/runtime/ash/process?db=${encodeURIComponent(db)}&env=${encodeURIComponent(env)}&instance=${instance}`);
    const total = r.total_samples || 0;
    if (!total) {
      $('procAshSection').innerHTML = `<h2>Oracle Activity (ASH)</h2><div style="color:#334;font-size:11px">No ASH samples found for this process run.<br><span style="color:#223">Source: ${esc(r.source||'V$ACTIVE_SESSION_HISTORY + DBA_HIST')}</span></div>`;
      return;
    }
    let html = `<h2>Oracle Activity (ASH) <span style="color:#9ab;font-size:10px;font-weight:normal">${total} samples · ${esc(r.source||'')}</span></h2>`;

    // Wait events
    html += `<div style="margin:4px 0 8px"><div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Wait Events</div>`;
    (r.events||[]).forEach(ev => {
      const col = _WC_COLOR[ev.wait_class] || '#778';
      const barW = Math.min(ev.pct, 100).toFixed(0);
      html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0;font-size:11px">
        <div class="pct-bar" style="width:60px"><div class="pct-fill" style="width:${barW}%;background:${col}"></div></div>
        <span style="color:${col};font-size:10px;min-width:28px">${ev.pct}%</span>
        <span style="color:#9ab">${esc(ev.event)}</span>
      </div>`;
    });
    html += '</div>';

    // Top SQL
    const sqls = (r.top_sql||[]).filter(s => s.sql_id);
    if (sqls.length) {
      html += `<div style="font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Top SQL</div>`;
      sqls.slice(0,5).forEach(s => {
        const txt = s.sql_text ? s.sql_text.substring(0,80) : '(not in V$SQL)';
        html += `<div style="margin:3px 0;font-size:10px">
          <span class="mono" style="color:#00e5ff">${esc(s.sql_id)}</span>
          <span style="color:#556;margin:0 4px">${s.samples} samples</span>
          <span style="color:#667">${esc(txt)}</span>
        </div>`;
      });
    }

    $('procAshSection').innerHTML = html;
  } catch(e) {
    $('procAshSection').innerHTML = `<div style="color:#334;font-size:11px;margin-top:8px">Oracle Activity unavailable: ${esc(e.message)}</div>`;
  }
}

async function refresh() {
  $('lastTs').textContent = 'Refreshing…';
  await Promise.allSettled([loadAlerts(), loadStatus(), loadDomains(), loadServers(), loadProcesses(), loadOracle(), loadAsh()]);
  $('lastTs').textContent = 'Last: ' + new Date().toLocaleTimeString();
  if (autoR) {
    clearTimeout(arTimer);
    arTimer = setTimeout(refresh, INTERVAL);
  }
}

function toggleAR() {
  autoR = !autoR;
  $('arBtn').textContent = `Auto: ${autoR ? 'ON' : 'OFF'}`;
  if (autoR) { arTimer = setTimeout(refresh, INTERVAL); }
  else { clearTimeout(arTimer); }
}

// ── Runtime Graph Visualization ─────────────────────────
const RT_COLORS = {
  environment:'#00e5ff', operator:'#4488ff', process:'#00cc66',
  application_engine:'#ff8800', oracle_session:'#ffdd00',
  oracle_database:'#ff4488', service_operation:'#aa44ff',
  process_server:'#44ffcc', sql_id:'#ff6644', ib_status:'#ff88ff',
};
function rtColor(t) { return RT_COLORS[t] || '#556677'; }

function rtForce(nodes, edges, w, h, ticks) {
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

function rtRender(svg, nodes, edges) {
  const ns = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';
  for (const e of edges) {
    const s = nodes[e.si], t = nodes[e.ti]; if(!s||!t) continue;
    const line = document.createElementNS(ns,'line');
    line.setAttribute('x1',s.x); line.setAttribute('y1',s.y);
    line.setAttribute('x2',t.x); line.setAttribute('y2',t.y);
    line.setAttribute('stroke','#1e3040'); line.setAttribute('stroke-width','1');
    svg.appendChild(line);
    if (e.rel) {
      const tx = document.createElementNS(ns,'text');
      tx.setAttribute('x',(s.x+t.x)/2); tx.setAttribute('y',(s.y+t.y)/2);
      tx.setAttribute('fill','#1e3848'); tx.setAttribute('font-size','7');
      tx.setAttribute('text-anchor','middle'); tx.textContent = e.rel;
      svg.appendChild(tx);
    }
  }
  for (const n of nodes) {
    const g = document.createElementNS(ns,'g');
    g.style.cursor = 'pointer';
    g.onclick = () => rtShowDetail(n);
    const r = n.type==='environment'?18:n.type==='oracle_database'?14:9;
    const c = document.createElementNS(ns,'circle');
    c.setAttribute('cx',n.x); c.setAttribute('cy',n.y); c.setAttribute('r',r);
    c.setAttribute('fill',rtColor(n.type)); c.setAttribute('fill-opacity','0.22');
    c.setAttribute('stroke',rtColor(n.type)); c.setAttribute('stroke-width','1.5');
    g.appendChild(c);
    const lbl = (n.label||n.id||'').replace(/^[^:]+:/,'');
    const tx = document.createElementNS(ns,'text');
    tx.setAttribute('x',n.x); tx.setAttribute('y',n.y+r+11);
    tx.setAttribute('fill',rtColor(n.type)); tx.setAttribute('font-size','9');
    tx.setAttribute('text-anchor','middle');
    tx.textContent = lbl.length>18?lbl.slice(0,16)+'…':lbl;
    g.appendChild(tx);
    svg.appendChild(g);
  }
}

function rtShowDetail(n) {
  const el = $('rtGraphDetail');
  const lbl = (n.label||n.id||'');
  el.innerHTML = `<b style="color:${rtColor(n.type)}">[${n.type}]</b> `+
    `<b style="color:#d7faff">${esc(lbl)}</b>`+
    (n._links&&n._links.admin ? ` <a href="${esc(n._links.admin)}" style="color:#00e5ff;font-size:10px;margin-left:6px;">&#x2197; open</a>` : '')+
    '<br>'+Object.entries(n.data||{}).slice(0,10)
      .map(([k,v])=>`<span style="color:#445">${esc(k)}:</span> <span style="color:#9ab">${esc(String(v??''))}</span>`)
      .join(' &nbsp; ');
}

async function loadRtGraph() {
  const env = $('envSel')?.value || 'HCM';
  $('graphStatus').textContent = 'Building graph…';
  $('rtGraphArea').style.display = 'none';
  try {
    const data = await api(`/api/runtime/graph?env=${encodeURIComponent(env)}&process_limit=60&session_limit=60`);
    const svg = $('rtGraphSvg');
    const w = svg.clientWidth || 900, h = parseInt(svg.getAttribute('height'))||560;
    const nodeMap = {};
    const nodes = (data.nodes||[]).map((n,i) => {
      nodeMap[n.id] = i;
      return {...n, x:24+Math.random()*(w-48), y:24+Math.random()*(h-48), fx:0, fy:0};
    });
    const edges = (data.edges||[]).map(e=>({
      si:nodeMap[e.source], ti:nodeMap[e.target], rel:e.relationship||''
    })).filter(e=>e.si!==undefined&&e.ti!==undefined);
    rtForce(nodes, edges, w, h, 350);
    rtRender(svg, nodes, edges);
    const types = [...new Set(nodes.map(n=>n.type))].sort();
    $('rtGraphLegend').innerHTML = types.map(t=>`<span style="color:${rtColor(t)};` +
      `background:#0a1820;border:1px solid ${rtColor(t)}44;padding:2px 8px;border-radius:2px;">` +
      `${t} <b>${nodes.filter(n=>n.type===t).length}</b></span>`).join('');
    $('rtGraphDetail').textContent = 'Click a node to see details.';
    $('rtGraphArea').style.display = 'block';
    $('graphStatus').textContent = `${nodes.length} nodes · ${edges.length} edges`;
  } catch(e) {
    $('graphStatus').textContent = 'Error: '+esc(e.message);
  }
}

// ── init ────────────────────────────────────────────────
(async () => {
  const cfg = await api('/api/runtime/config').catch(() => ({envs:[], dbs:[]}));
  $('envSel').innerHTML = cfg.envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('dbSel').innerHTML  = cfg.dbs.map(d  => `<option value="${d}">${d}</option>`).join('');
  const urlParams = new URLSearchParams(window.location.search);
  const envParam = urlParams.get('env');
  if (envParam) {
    const envOpt = $('envSel').querySelector(`option[value="${envParam}"]`);
    if (envOpt) envOpt.selected = true;
  }
  await refresh();
  arTimer = setTimeout(refresh, INTERVAL);
  const instParam = urlParams.get('instance');
  if (instParam) showProc(instParam);
})();
// Hide the top-right ENV control in the shared shell header (keep page-local ENV controls visible)
try {
  const hdrEnv = document.querySelector('.ds-page-hdr .ds-env');
  if (hdrEnv) { hdrEnv.style.display = 'none'; }
  else {
    const tbSel = document.querySelector('.topbar select#envSel');
    if (tbSel && tbSel.parentElement) tbSel.parentElement.style.display = 'none';
  }
} catch(e) {}
</script>""")


@router.get("/sqlws", response_class=HTMLResponse)
def admin_sqlws():
    return _shell("SQL Workspace", "sqlws", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;height:100vh;display:flex;flex-direction:column;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;
   border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px;}
nav{font-size:12px;color:#445;}
nav a{color:#00e5ff;text-decoration:none;} nav a:hover{text-decoration:underline;}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:280px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0;}
.editor-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.editor-panel{padding:12px;border-bottom:1px solid #00e5ff22;}
.results-panel{flex:1;overflow:auto;padding:12px;}
select,input[type=text],input[type=number]{background:#0b1b24;color:#d7faff;
  border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
textarea{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;
  font-family:monospace;font-size:12px;padding:8px;width:100%;resize:vertical;}
textarea:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{border-color:#00e5ff;background:#00e5ff11;}
button.danger{background:#ff4444;color:#fff;}
button.danger:hover{background:#ff6666;}
button.warn{background:#ffaa00;color:#000;}
.btn-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:8px;}
.ctrl-row{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin-top:8px;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:3px;}
.chip{display:inline-block;padding:2px 8px;border-radius:2px;font-size:11px;font-weight:bold;}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-block{background:#3a0000;border:1px solid #ff6600;color:#ff6600;}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
table{border-collapse:collapse;width:100%;font-size:11px;margin-top:4px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;
   font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;position:sticky;top:0;background:#050b12;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;max-width:320px;
   overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
td.wrap{white-space:normal;word-break:break-all;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:8px 0;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;margin:2px 0;}
.ok-msg{color:#00cc66;font-size:11px;margin:2px 0;}
.ts{font-size:10px;color:#446;}
.timing{font-size:11px;color:#667;margin:4px 0;}
.section-toggle{cursor:pointer;user-select:none;}
.section-toggle:hover{color:#00e5ff;}
.sql-preview{font-family:monospace;font-size:10px;color:#6ab;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;display:block;}
.pin-btn{font-size:10px;padding:1px 5px;}
.pagination{display:flex;gap:6px;align-items:center;margin-top:8px;}
.col-type{color:#445;font-size:10px;}
.schema-item{padding:4px 6px;cursor:pointer;border-radius:2px;font-size:11px;
  display:flex;justify-content:space-between;align-items:center;}
.schema-item:hover{background:#0b2030;}
.schema-item .obj-type{font-size:9px;color:#445;text-transform:uppercase;}
.schema-cols{display:none;padding:4px 0 4px 16px;}
.schema-cols.open{display:block;}
.schema-col{font-size:10px;color:#778;padding:1px 4px;font-family:monospace;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;margin:8px 0 0;}
.tab{padding:5px 12px;cursor:pointer;font-size:11px;color:#556;
     border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.bind-row{display:flex;gap:3px;align-items:center;margin-bottom:3px;}
.bnd-name{width:72px;font-family:monospace;font-size:11px;padding:2px 4px;
  background:#050b12;color:#9ab;border:1px solid #00e5ff33;}
.bnd-val{flex:1;min-width:0;font-family:monospace;font-size:11px;padding:2px 4px;
  background:#050b12;color:#d7faff;border:1px solid #00e5ff33;}
.bnd-rm{background:transparent;border:none;color:#445;cursor:pointer;padding:0 3px;font-size:13px;line-height:1;}
.bnd-rm:hover{color:#ff4444;}
#sqlAC{position:fixed;z-index:9999;background:#0b1b24;border:1px solid #00e5ff55;
  min-width:260px;max-width:480px;max-height:220px;overflow-y:auto;display:none;
  box-shadow:0 4px 16px #000a;}
.ac-item{padding:4px 10px;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;gap:8px;font-size:11px;}
.ac-item:hover,.ac-item.ac-sel{background:#0e2a3a;}
.ac-label{font-family:monospace;color:#d7faff;}
.ac-detail{color:#445;font-size:10px;text-align:right;}
.ac-type-col{color:#00e5ff44;font-size:9px;text-transform:uppercase;}
</style>

<div class="main">

<!-- ═══════════════════════════════════════════════════════ SIDEBAR ═══ -->
<div class="sidebar">

  <div class="tab-row">
    <div class="tab on" onclick="showTab('schema')">Schema</div>
    <div class="tab"    onclick="showTab('history')">History</div>
    <div class="tab"    onclick="showTab('pinned')">Pinned</div>
  </div>

  <!-- Schema browser -->
  <div id="pane-schema" class="pane on">
    <h2>Schema Browser</h2>
    <div style="display:flex;gap:4px;margin-bottom:4px;">
      <input id="schemaQ" type="text" placeholder="Search tables/records…" style="flex:1;" onkeydown="if(event.key==='Enter')searchSchema()">
      <button onclick="searchSchema()">Go</button>
    </div>
    <div style="display:flex;gap:4px;margin-bottom:8px;">
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('')">All</button>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('PS_')">PS_</button>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="schemaPrefix('SYSADM.')">SYSADM.</button>
    </div>
    <div id="schemaResults"><span class="empty">Type to search</span></div>
  </div>

  <!-- History -->
  <div id="pane-history" class="pane">
    <div style="display:flex;align-items:center;gap:4px;margin-bottom:6px;">
      <h2 style="margin:0;flex:1;">Query History</h2>
      <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="loadHistory()">Refresh</button>
    </div>
    <input id="historyQ" type="text" placeholder="Filter by SQL or env…" style="width:100%;margin-bottom:6px;" oninput="applyHistoryFilter()">
    <div id="historyList"><span class="empty">Loading…</span></div>
  </div>

  <!-- Pinned -->
  <div id="pane-pinned" class="pane">
    <h2>Pinned Queries <button class="sec" style="font-size:9px;padding:2px 6px;" onclick="loadPinned()">Refresh</button></h2>
    <div id="pinnedList"><span class="empty">No pinned queries</span></div>
  </div>

</div>
<!-- ══════════════════════════════════════════════════ EDITOR AREA ════ -->
<div class="editor-area">

  <div class="editor-panel">
    <div style="display:flex;gap:8px;align-items:flex-start;">
      <div style="flex:1;">
        <label class="lbl">SQL Query <span style="color:#445;font-size:9px;font-weight:normal;">Ctrl+Space to autocomplete</span></label>
        <textarea id="sqlInput" rows="8" placeholder="SELECT * FROM SYSADM.PSOPRDEFN FETCH FIRST 10 ROWS ONLY"></textarea>
      </div>
      <div id="sqlAC"></div>
      <div style="width:200px;display:flex;flex-direction:column;">
        <label class="lbl">Bind Parameters
          <button class="sec" onclick="addBind()" style="font-size:9px;padding:1px 5px;margin-left:4px;">+ Add</button>
          <button class="sec" onclick="clearBinds()" style="font-size:9px;padding:1px 5px;margin-left:2px;">Clear</button>
        </label>
        <div id="bindsEditor" style="flex:1;overflow-y:auto;min-height:60px;max-height:160px;
          border:1px solid #00e5ff44;padding:4px 6px;background:#0b1b24;"></div>
        <div class="muted" id="bindsHint" style="font-size:9px;color:#445;padding:2px 0;">
          Bind vars from SQL e.g. :oprid → "oprid"
        </div>
      </div>
    </div>

    <div class="ctrl-row">
      <div>
        <label class="lbl">Page</label>
        <input id="pageInput" type="number" value="1" min="1" style="width:60px;">
      </div>
      <div>
        <label class="lbl">Page Size</label>
        <input id="pageSizeInput" type="number" value="100" min="1" max="1000" style="width:70px;">
      </div>
      <div>
        <label class="lbl">Timeout (s)</label>
        <input id="timeoutInput" type="number" value="30" min="0" max="600" style="width:78px;">
      </div>
    </div>

    <div class="btn-row">
      <button id="validateBtn" onclick="validateSQL()">Validate</button>
      <button id="execBtn" onclick="executeSQL()">Execute</button>
      <button id="cancelBtn" class="sec" onclick="cancelSQL()" style="display:none;">&#9632; Cancel</button>
      <button id="explainBtn" class="sec" onclick="explainSQL()">Explain Plan</button>
      <button id="exportCsvBtn" class="sec" onclick="exportCSV()">Export CSV</button>
      <button id="exportJsonBtn" class="sec" onclick="exportJSON()">Export JSON</button>
      <button id="clearBtn" class="sec" onclick="clearResults()">Clear</button>
    </div>

    <div id="validationBox" style="margin-top:8px;display:none;"></div>
  </div>

  <div class="results-panel">
    <div id="timingBox" style="display:none;" class="timing"></div>
    <div id="warningBox"></div>
    <div id="resultsBox"></div>
    <div id="paginationBox" class="pagination" style="display:none;">
      <button class="sec" onclick="prevPage()" id="prevBtn">&#8592; Prev</button>
      <span id="pageLabel" style="font-size:11px;color:#667;"></span>
      <button class="sec" onclick="nextPage()" id="nextBtn">Next &#8594;</button>
    </div>
  </div>

</div>
</div>

<script>
// ── state ──────────────────────────────────────────────────────────────
let lastSQL   = '';
let lastBinds = {};
let currentPage = 1;
let lastPageSize = 100;
let lastResult = null;

// ── helpers ────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function env()      { return (window.dsGetEnv && window.dsGetEnv()) || 'HCM'; }
function sqlText()  { return $('sqlInput').value.trim(); }
function bindsObj() {
  const obj = {};
  document.querySelectorAll('#bindsEditor .bind-row').forEach(row => {
    const name = row.querySelector('.bnd-name').value.trim().replace(/^:/, '');
    const val  = row.querySelector('.bnd-val').value;
    if (name) obj[name] = val;
  });
  return obj;
}

function addBind(name, val) {
  const ed  = $('bindsEditor');
  const row = document.createElement('div');
  row.className = 'bind-row';
  row.innerHTML = `<input class="bnd-name" placeholder="name" value="${esc(name||'')}">` +
                  `<input class="bnd-val"  placeholder="value" value="${esc(val!=null?val:'')}">` +
                  `<button class="bnd-rm" onclick="this.parentElement.remove()" title="Remove">×</button>`;
  ed.appendChild(row);
  row.querySelector('.bnd-name').focus();
}

function clearBinds() {
  $('bindsEditor').innerHTML = '';
}

function setBinds(obj) {
  clearBinds();
  Object.entries(obj || {}).forEach(([k,v]) => addBind(k, v));
}

function showTab(name) {
  ['schema','history','pinned'].forEach(t => {
    document.querySelectorAll('.tab').forEach((el,i) => {
      if (['schema','history','pinned'][i] === t)
        el.classList.toggle('on', t === name);
    });
    $(`pane-${t}`).classList.toggle('on', t === name);
  });
  if (name === 'history') loadHistory();
  if (name === 'pinned')  loadPinned();
}

// tab selection uses index — re-wire correctly
document.querySelectorAll('.tab').forEach((el, i) => {
  const names = ['schema','history','pinned'];
  el.onclick = () => showTab(names[i]);
});

async function api(path, options={}) {
  const res = await fetch(path, options);
  if (res.status === 401) { window.location.reload(); return; }
  return res;
}

function setValidationBox(result) {
  const box = $('validationBox');
  box.style.display = 'block';
  if (result.allowed) {
    box.innerHTML = `<span class="chip chip-ok">&#10003; Allowed — ${esc(result.statement_type)}</span>`;
  } else {
    box.innerHTML = `<span class="chip chip-block">&#10007; Blocked — ${esc(result.blocked_reason)}</span>`;
  }
  (result.warnings || []).forEach(w => {
    box.innerHTML += `<div class="warn-msg">&#9888; ${esc(w)}</div>`;
  });
}

function setWarnings(warnings, errors) {
  const box = $('warningBox');
  box.innerHTML = '';
  (warnings || []).forEach(w => {
    box.innerHTML += `<div class="warn-msg">&#9888; ${esc(w)}</div>`;
  });
  (errors || []).forEach(e => {
    box.innerHTML += `<div class="err-msg">&#10007; ${esc(e)}</div>`;
  });
}

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function clearResults() {
  $('resultsBox').innerHTML = '';
  $('timingBox').style.display = 'none';
  $('warningBox').innerHTML = '';
  $('validationBox').style.display = 'none';
  $('paginationBox').style.display = 'none';
}

// ── validate ───────────────────────────────────────────────────────────
async function validateSQL() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const res = await api('/api/sqlws/validate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({sql}),
  });
  const data = await res.json();
  setValidationBox(data);
  $('warningBox').innerHTML = '';
}

// ── execute ────────────────────────────────────────────────────────────
let currentAbortController = null;

function _setExecRunning(running) {
  const buttons = ['validateBtn','execBtn','explainBtn','exportCsvBtn','exportJsonBtn','clearBtn'];
  buttons.forEach(id => { const el = $(id); if (el) el.disabled = running; });
  $('execBtn').disabled = running;
  $('cancelBtn').style.display = running ? 'inline-block' : 'none';
}

function getTimeoutSecs() {
  const raw = parseInt($('timeoutInput').value, 10);
  if (!Number.isFinite(raw)) return 0;
  return Math.max(0, Math.min(raw, 600));
}

function cancelSQL() {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
}

async function executeSQL(page) {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const binds      = bindsObj();
  const pageSize   = parseInt($('pageSizeInput').value) || 100;
  const timeoutSecs = getTimeoutSecs();
  page = page || parseInt($('pageInput').value) || 1;

  lastSQL = sql; lastBinds = binds; lastPageSize = pageSize; currentPage = page;
  $('pageInput').value = page;

  currentAbortController = new AbortController();
  _setExecRunning(true);

  let data;
  try {
    const res = await api('/api/sqlws/execute', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({env:env(), sql, binds, page, page_size:pageSize, timeout_secs:timeoutSecs}),
      signal: currentAbortController.signal,
    });
    if (!res.ok) {
      const text = await res.text();
      let msg = text;
      try {
        const errData = JSON.parse(text);
        msg = errData.error || (errData.warnings || []).join('; ') || text;
      } catch(e) {}
      throw new Error(msg || `HTTP ${res.status}`);
    }
    data = await res.json();
  } catch (e) {
    _setExecRunning(false);
    if (e.name === 'AbortError') {
      $('timingBox').style.display = 'block';
      $('timingBox').textContent = 'Query cancelled by user.';
      setWarnings([], ['Query cancelled by user.']);
      $('resultsBox').innerHTML = '<div class="empty">Execution cancelled.</div>';
      $('paginationBox').style.display = 'none';
    } else {
      setWarnings([], [`Request failed: ${e.message}`]);
    }
    return;
  } finally {
    currentAbortController = null;
  }
  _setExecRunning(false);
  lastResult = data;

  setValidationBox({
    allowed: !data.blocked,
    statement_type: data.statement_type,
    warnings: data.warnings || [],
    blocked_reason: data.blocked_reason,
  });

  const warns = (data.warnings || []).filter(w => !w.startsWith('Execution'));
  const errs  = data.error ? [data.error] : [];
  setWarnings(warns, errs);

  const timing = $('timingBox');
  timing.style.display = 'block';
  const statusSuffix = data.timed_out ? ' — TIMED OUT' : (data.cancelled ? ' — CANCELLED' : '');
  timing.textContent = `${data.row_count} rows · ${data.elapsed_ms} ms · Page ${data.page}${data.truncated ? ' (more rows available)' : ''}${statusSuffix}`;

  renderTable(data);
  renderPagination(data);
  loadHistory();
}

function renderTable(data) {
  const box = $('resultsBox');
  if (data.blocked) {
    box.innerHTML = `<div class="err-msg">&#10007; ${esc(data.blocked_reason)}</div>`;
    return;
  }
  if (!data.columns || data.columns.length === 0) {
    box.innerHTML = '<div class="empty">No columns returned.</div>';
    return;
  }
  if (data.rows.length === 0) {
    box.innerHTML = '<div class="empty">No rows returned.</div>';
    return;
  }

  let html = '<div style="overflow-x:auto;"><table><thead><tr>';
  data.columns.forEach(c => {
    html += `<th>${esc(c.name)}<br><span class="col-type">${esc(c.type)}</span></th>`;
  });
  html += '</tr></thead><tbody>';

  data.rows.forEach(row => {
    html += '<tr>';
    data.columns.forEach(c => {
      const v = row[c.name];
      const display = v === null ? '<span style="color:#334">NULL</span>' : esc(String(v));
      html += `<td class="mono">${display}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  box.innerHTML = html;
}

function renderPagination(data) {
  const box = $('paginationBox');
  if (!data.columns || data.columns.length === 0 || data.row_count === 0) {
    box.style.display = 'none';
    return;
  }
  box.style.display = 'flex';
  $('pageLabel').textContent = `Page ${data.page}${data.truncated ? '+' : ''}`;
  $('prevBtn').disabled = data.page <= 1;
  $('nextBtn').disabled = !data.truncated;
}

function prevPage() {
  if (currentPage > 1) executeSQL(currentPage - 1);
}
function nextPage() {
  executeSQL(currentPage + 1);
}

// ── explain ─────────────────────────────────────────────────────────────
async function explainSQL() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const binds = bindsObj();

  const res = await api('/api/sqlws/explain', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({env:env(), sql, binds}),
  });
  const data = await res.json();

  const warns = data.warnings || [];
  setWarnings(warns, []);

  const box = $('resultsBox');
  if (!data.allowed) {
    box.innerHTML = `<div class="err-msg">&#10007; ${esc(data.blocked_reason)}</div>`;
    return;
  }
  if (!data.plan || data.plan.length === 0) {
    box.innerHTML = '<div class="empty">No plan returned. ' + esc(warns.join(' ')) + '</div>';
    return;
  }

  let html = '<pre style="font-family:monospace;font-size:11px;color:#9ab;background:#0b1b24;padding:12px;overflow-x:auto;">';
  data.plan.forEach(line => { html += esc(line) + '\\n'; });
  html += '</pre>';
  $('timingBox').style.display = 'block';
  $('timingBox').textContent = `EXPLAIN PLAN · ${data.elapsed_ms} ms`;
  box.innerHTML = html;
  $('paginationBox').style.display = 'none';
}

// ── export ──────────────────────────────────────────────────────────────
async function exportCSV() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const body = JSON.stringify({env:env(), sql, binds:bindsObj(), page_size:1000});
  const res = await api('/api/sqlws/export/csv', {
    method:'POST', headers:{'Content-Type':'application/json'}, body
  });
  if (!res || !res.ok) { alert('Export failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sqlws_export.csv';
  a.click();
}

async function exportJSON() {
  const sql = sqlText();
  if (!sql) { alert('Enter a SQL query first.'); return; }
  const body = JSON.stringify({env:env(), sql, binds:bindsObj(), page_size:1000});
  const res = await api('/api/sqlws/export/json', {
    method:'POST', headers:{'Content-Type':'application/json'}, body
  });
  if (!res || !res.ok) { alert('Export failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sqlws_export.json';
  a.click();
}

// ── schema browser ─────────────────────────────────────────────────────
function schemaPrefix(p) {
  $('schemaQ').value = p;
  if (p) searchSchema();
  else $('schemaResults').innerHTML = '<span class="empty">Type to search</span>';
}

async function searchSchema() {
  const q = $('schemaQ').value.trim();
  if (!q) return;
  $('schemaResults').innerHTML = '<span class="empty">Searching…</span>';
  const res  = await api(`/api/sqlws/schema/search?env=${encodeURIComponent(env())}&q=${encodeURIComponent(q)}`);
  const data = await res.json();
  renderSchemaResults(data.results || [], data.warnings || []);
}

function renderSchemaResults(results, warnings) {
  const box = $('schemaResults');
  if (!results.length) { box.innerHTML = '<span class="empty">No results.</span>'; return; }

  let html = '';
  warnings.forEach(w => { html += `<div class="warn-msg">${esc(w)}</div>`; });

  results.forEach(obj => {
    const id = `sc_${btoa(obj.owner + '.' + obj.object_name).replace(/[^a-zA-Z0-9]/g,'')}`;
    const badge = obj.source === 'peoplesoft'
      ? `<span class="obj-type" style="color:#00cc66;">PS</span>`
      : `<span class="obj-type">${esc(obj.object_type)}</span>`;
    const link = obj.ps_recname
      ? `<a href="/admin/object/record/${esc(obj.ps_recname)}" style="color:#00e5ff;font-size:9px;" target="_blank">&#8599;</a>`
      : '';
    html += `
      <div class="schema-item" onclick="toggleSchemaItem('${id}','${esc(obj.owner)}','${esc(obj.object_name)}')">
        <span>
          <span style="font-family:monospace;">${esc(obj.owner)}.${esc(obj.object_name)}</span>
          ${link}
          ${obj.description ? `<br><span style="font-size:9px;color:#556;">${esc(obj.description)}</span>` : ''}
        </span>
        ${badge}
      </div>
      <div id="${id}" class="schema-cols"></div>`;
  });
  box.innerHTML = html;
}

async function toggleSchemaItem(id, owner, objName) {
  const el = document.getElementById(id);
  if (el.classList.contains('open')) { el.classList.remove('open'); return; }
  el.classList.add('open');
  el.innerHTML = '<span class="schema-col">Loading columns…</span>';
  const res  = await api(`/api/sqlws/schema/${encodeURIComponent(owner)}/${encodeURIComponent(objName)}/columns?env=${encodeURIComponent(env())}`);
  const data = await res.json();
  if (!data.columns || !data.columns.length) {
    el.innerHTML = '<span class="schema-col empty">No columns found.</span>';
    return;
  }
  el.innerHTML = data.columns.map(c =>
    `<div class="schema-col" onclick="insertColumnRef('${esc(owner)}.${esc(objName)}','${esc(c.column_name)}')" style="cursor:pointer;" title="Click to insert">
       <span style="color:#9ab;">${esc(c.column_name)}</span>
       <span style="color:#445;"> ${esc(c.data_type)}</span>
     </div>`
  ).join('');
}

function insertColumnRef(table, col) {
  const ta = $('sqlInput');
  const sel = ta.selectionStart;
  const txt = ta.value;
  ta.value = txt.slice(0, sel) + col + txt.slice(ta.selectionEnd);
  ta.focus();
  ta.selectionStart = ta.selectionEnd = sel + col.length;
}

// ── SQL Autocomplete ────────────────────────────────────────────────────
let _acItems = [];
let _acSel   = -1;
let _acTimer = null;
const _acColCache = {};

function _tokenBeforeCursor() {
  const ta  = $('sqlInput');
  const txt = ta.value.slice(0, ta.selectionStart);
  const m   = txt.match(/[\\w.]+$/);
  return m ? m[0] : '';
}

function _extractAliases(sql) {
  const map = {};
  const re = /(?:FROM|JOIN)\\s+(?:SYSADM\\.)?(\\w+)\\s+(?:AS\\s+)?(\\w+)/gi;
  let m;
  const KEYWORDS = new Set(['WHERE','ON','INNER','LEFT','RIGHT','OUTER','CROSS','FULL','FETCH','ORDER','GROUP','HAVING','SET','AND','OR']);
  while ((m = re.exec(sql)) !== null) {
    const tbl   = m[1].toUpperCase();
    const alias = m[2].toUpperCase();
    if (!KEYWORDS.has(alias)) {
      map[alias] = tbl;
      map[tbl]   = tbl;
    }
  }
  return map;
}

function _acContext() {
  const tok = _tokenBeforeCursor();
  if (!tok) return null;
  if (tok.includes('.')) {
    const dot  = tok.lastIndexOf('.');
    const pre  = tok.slice(0, dot);
    const suf  = tok.slice(dot + 1);
    const owner = pre.includes('.') ? pre.split('.').pop() : pre;
    return { type: 'column', qualifier: owner, prefix: suf, replaceLen: suf.length };
  }
  if (tok.length >= 2) return { type: 'table', prefix: tok, replaceLen: tok.length };
  return null;
}

async function _fetchAC(ctx) {
  if (!ctx) return [];
  if (ctx.type === 'table') {
    try {
      const res  = await fetch(`/api/sqlws/schema/search?env=${encodeURIComponent(env())}&q=${encodeURIComponent(ctx.prefix)}`);
      const data = await res.json();
      return (data.results || []).slice(0, 12).map(r => ({
        label: r.object_name,
        insert: r.object_name,
        detail: r.description || (r.source === 'peoplesoft' ? 'PS' : (r.object_type || '')),
      }));
    } catch(e) { return []; }
  }
  if (ctx.type === 'column') {
    const aliases = _extractAliases($('sqlInput').value);
    const tblName = aliases[ctx.qualifier.toUpperCase()] || ctx.qualifier.toUpperCase();
    const cacheKey = `${env()}|${tblName}`;
    if (!_acColCache[cacheKey]) {
      try {
        const res  = await fetch(`/api/sqlws/schema/SYSADM/${encodeURIComponent(tblName)}/columns?env=${encodeURIComponent(env())}`);
        const data = await res.json();
        _acColCache[cacheKey] = data.columns || [];
      } catch(e) { _acColCache[cacheKey] = []; }
    }
    const cols = _acColCache[cacheKey];
    const pfx  = ctx.prefix.toUpperCase();
    return cols
      .filter(c => !pfx || c.column_name.toUpperCase().startsWith(pfx))
      .slice(0, 16)
      .map(c => ({ label: c.column_name, insert: c.column_name, detail: c.data_type || '' }));
  }
  return [];
}

function _showAC(items, replaceLen) {
  const box = $('sqlAC');
  if (!items.length) { _hideAC(); return; }
  _acItems = items;
  _acSel   = -1;
  box.innerHTML = items.map((it, i) =>
    `<div class="ac-item" data-i="${i}" onmousedown="event.preventDefault();_acCommit(${i})">
      <span class="ac-label">${esc(it.label)}</span>
      <span class="ac-detail">${esc(it.detail)}</span>
    </div>`
  ).join('');
  const ta  = $('sqlInput');
  const r   = ta.getBoundingClientRect();
  box.style.left = r.left + 'px';
  box.style.top  = (r.bottom + 2) + 'px';
  box.style.display = 'block';
  box._replaceLen = replaceLen;
}

function _hideAC() {
  $('sqlAC').style.display = 'none';
  _acItems = [];
  _acSel   = -1;
}

function _acRenderSel() {
  document.querySelectorAll('#sqlAC .ac-item').forEach((el, i) => {
    el.classList.toggle('ac-sel', i === _acSel);
  });
}

function _acCommit(i) {
  const item = _acItems[i];
  if (!item) return;
  const ta  = $('sqlInput');
  const pos = ta.selectionStart;
  const txt = ta.value;
  const rl  = $('sqlAC')._replaceLen || 0;
  ta.value  = txt.slice(0, pos - rl) + item.insert + txt.slice(pos);
  ta.selectionStart = ta.selectionEnd = pos - rl + item.insert.length;
  ta.focus();
  _hideAC();
}

function _acTrigger() {
  clearTimeout(_acTimer);
  _acTimer = setTimeout(async () => {
    const ctx   = _acContext();
    const items = await _fetchAC(ctx);
    _showAC(items, ctx ? ctx.replaceLen : 0);
  }, 200);
}

(function _wireAC() {
  const ta = $('sqlInput');
  if (!ta) return;

  ta.addEventListener('keydown', e => {
    const box = $('sqlAC');
    if (box.style.display === 'none') {
      if (e.ctrlKey && e.key === ' ') { e.preventDefault(); _acTrigger(); }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      _acSel = Math.min(_acSel + 1, _acItems.length - 1);
      _acRenderSel();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      _acSel = Math.max(_acSel - 1, -1);
      _acRenderSel();
    } else if ((e.key === 'Enter' || e.key === 'Tab') && _acSel >= 0) {
      e.preventDefault();
      _acCommit(_acSel);
    } else if (e.key === 'Escape') {
      _hideAC();
    } else if (e.ctrlKey && e.key === ' ') {
      e.preventDefault();
      _acTrigger();
    }
  });

  ta.addEventListener('input', () => {
    const tok = _tokenBeforeCursor();
    if (!tok || tok.length < 2) { _hideAC(); return; }
    _acTrigger();
  });

  ta.addEventListener('blur', () => setTimeout(_hideAC, 150));
})();

// ── history ─────────────────────────────────────────────────────────────
let _historyItems = [];
let _pinnedItems  = [];
const _renderedHistoryItems = {};

async function loadHistory() {
  const res  = await api('/api/sqlws/history?limit=50');
  const data = await res.json();
  _historyItems = data.history || [];
  applyHistoryFilter();
}

function applyHistoryFilter() {
  const q = ($('historyQ') ? $('historyQ').value : '').toLowerCase().trim();
  const items = q
    ? _historyItems.filter(h =>
        (h.sql || '').toLowerCase().includes(q) ||
        (h.env || '').toLowerCase().includes(q))
    : _historyItems;
  renderHistoryList(items, 'historyList', false);
}

async function loadPinned() {
  const res  = await api('/api/sqlws/history?pinned=true&limit=50');
  const data = await res.json();
  _pinnedItems = data.history || [];
  renderHistoryList(_pinnedItems, 'pinnedList', true);
}

function renderHistoryList(items, targetId, pinnedView) {
  const box = $(targetId);
  if (!items.length) { box.innerHTML = '<span class="empty">None.</span>'; return; }
  _renderedHistoryItems[targetId] = items;
  box.innerHTML = items.map((item, idx) => {
    const ts    = (item.timestamp || '').replace('T',' ').slice(0,19);
    const status = item.status === 'success' ? '&#10003;'
                 : item.status === 'blocked' ? '&#9940;' : '&#10007;';
    const statusColor = item.status === 'success' ? '#00cc66'
                      : item.status === 'blocked' ? '#ff6600' : '#ff4444';
    const pinLabel = item.pinned ? '&#9733; Unpin' : '&#9734; Pin';
    const idArg = esc(item.id || '');
    const targetArg = esc(targetId);
    return `
      <div style="border-bottom:1px solid #0e2030;padding:5px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="ts">${esc(ts)}</span>
          <span style="color:${statusColor};font-size:10px;">${status} ${esc(item.env)}</span>
        </div>
        <div class="sql-preview" onclick="loadHistoryItem('${targetArg}',${idx})"
             title="${esc(item.sql)}" style="cursor:pointer;">${esc(item.sql)}</div>
        <div style="display:flex;gap:4px;margin-top:3px;flex-wrap:wrap;">
          <button class="sec pin-btn" onclick="togglePin('${idArg}',${!item.pinned})">${pinLabel}</button>
          <button class="sec pin-btn" onclick="deleteHistory('${idArg}')">Delete</button>
          <button class="sec pin-btn" onclick="loadHistoryItem('${targetArg}',${idx})">Load</button>
          ${item.elapsed_ms ? `<span class="ts">${item.elapsed_ms}ms</span>` : ''}
          ${item.row_count  ? `<span class="ts">${item.row_count}r</span>`   : ''}
        </div>
      </div>`;
  }).join('');
}

function loadHistoryItem(targetId, idx) {
  const item = (_renderedHistoryItems[targetId] || [])[idx];
  if (!item) return;
  loadQueryFromHistory(item.sql || '', item.binds || {});
}

function loadQueryFromHistory(sql, binds) {
  $('sqlInput').value = sql || '';
  setBinds(binds || {});
  _detectBinds(sql || '');
  $('sqlInput').focus();
}

function _detectBinds(sql) {
  const existing = new Set(
    [...document.querySelectorAll('#bindsEditor .bnd-name')].map(el => el.value.trim().replace(/^:/, ''))
  );
  const matches = (sql || '').match(/:([a-zA-Z_][a-zA-Z0-9_]*)/g) || [];
  matches.forEach(m => {
    const name = m.slice(1);
    if (!existing.has(name)) { addBind(name, ''); existing.add(name); }
  });
}

async function togglePin(id, pin) {
  await api(`/api/sqlws/history/${id}/pin?pinned=${pin}`, {method:'POST'});
  loadHistory();
  loadPinned();
}

async function deleteHistory(id) {
  if (!confirm('Delete this history entry?')) return;
  await api(`/api/sqlws/history/${id}`, {method:'DELETE'});
  loadHistory();
  loadPinned();
}

// ── init ────────────────────────────────────────────────────────────────
(async () => {
  const res = await api('/api/sqlws/config').catch(() => null);
  if (res && res.ok) {
    const cfg = await res.json();
    $('pageSizeInput').value = cfg.default_page_size || 100;
  }
  loadHistory();

  // Auto-detect bind vars when SQL changes (debounced)
  let _bindDetectTimer = null;
  $('sqlInput').addEventListener('input', () => {
    clearTimeout(_bindDetectTimer);
    _bindDetectTimer = setTimeout(() => _detectBinds($('sqlInput').value), 400);
  });
})();
</script>""")


@router.get("/ib", response_class=HTMLResponse)
@router.get("/ib/{section}", response_class=HTMLResponse)
@router.get("/ib/{section}/{name}", response_class=HTMLResponse)
def admin_ib(section: str = None, name: str = None):
    return _shell("IB Explorer", "ib", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
  .brand-logo{width:36px;height:36px;object-fit:contain;margin-right:8px;filter:drop-shadow(0 2px 6px rgba(0,0,0,.6));}
.main{display:flex;flex:1;overflow:hidden;flex-direction:column;min-height:0;}
/* master-detail layout */
.explorer{display:flex;flex:1;overflow:hidden;min-height:0;}
.list-panel{width:290px;min-width:200px;border-right:1px solid #00e5ff22;display:flex;flex-direction:column;overflow:hidden;flex-shrink:0;}
.detail-panel{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
.detail-scroll{flex:1;overflow-y:auto;padding:14px;}
/* breadcrumb */
.breadcrumb{padding:5px 12px;border-bottom:1px solid #00e5ff11;font-size:11px;display:flex;align-items:center;flex-wrap:wrap;gap:3px;min-height:28px;background:#03080f;}
.bc-link{color:#00e5ff88;cursor:pointer;font-size:10px;}
.bc-link:hover{color:#00e5ff;text-decoration:underline;}
.bc-sep{color:#223;font-size:10px;}
.bc-cur{color:#d7faff;font-size:10px;}
/* relationship strip */
.rel-strip{display:flex;flex-wrap:wrap;gap:6px;padding:6px 10px;border:1px solid #00e5ff11;background:#030c14;margin-bottom:10px;align-items:center;font-size:10px;}
.rel-strip-label{color:#334;text-transform:uppercase;letter-spacing:1px;margin-right:4px;}
.rel-tag{background:#001828;border:1px solid #00e5ff33;color:#00e5ff;padding:2px 8px;cursor:pointer;border-radius:2px;font-size:10px;}
.rel-tag:hover{background:#00e5ff22;}
.rel-tag.rel-action{background:#001800;border-color:#00cc6633;color:#00cc66;}
.rel-tag.rel-action:hover{background:#00cc6611;}
/* compact stats for overview panel */
.cstat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;padding:8px 0;}
.cstat{border:1px solid #00e5ff22;padding:5px 6px;text-align:center;background:rgba(0,20,30,.5);}
.cstat-num{font-size:16px;color:#00e5ff;font-weight:bold;line-height:1.2;}
.cstat-lbl{font-size:9px;color:#445;text-transform:uppercase;letter-spacing:0.5px;}
/* lists */
.list-area{overflow-y:auto;flex:1;min-height:0;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;overflow-x:auto;flex-shrink:0;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 10px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;border-color:#00e5ff;}
.tab{padding:7px 12px;cursor:pointer;font-size:10px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;letter-spacing:0.5px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.search-bar{padding:6px 8px;border-bottom:1px solid #00e5ff11;display:flex;gap:4px;}
.search-bar input{flex:1;min-width:0;font-size:11px;}
.list-item{padding:6px 10px;cursor:pointer;border-bottom:1px solid #0b1b24;font-size:11px;}
.list-item:hover{background:#0b2030;}
.list-item.active{background:#0b2030;border-left:2px solid #00e5ff;}
.item-name{font-family:monospace;color:#d7faff;}
.item-meta{font-size:10px;color:#445;margin-top:1px;}
.badge{display:inline-block;font-size:9px;padding:1px 5px;border-radius:2px;float:right;}
.bd-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.bd-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.bd-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.bd-mute{background:#141a20;border:1px solid #334;color:#556;}
.bd-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.chip{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;}
.ch-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.ch-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.ch-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.ch-mute{background:#141a20;border:1px solid #334;color:#556;}
.ch-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:2px 12px;font-size:11px;margin:8px 0;}
.kv-key{color:#667;text-transform:uppercase;font-size:10px;letter-spacing:1px;padding:3px 0;}
.kv-val{padding:3px 0;font-family:monospace;}
.card{border:1px solid #00e5ff22;padding:10px 14px;margin-bottom:10px;background:rgba(0,20,30,.6);}
.stat-grid{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0;}
.stat-box{border:1px solid #00e5ff33;padding:10px 16px;min-width:100px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:22px;color:#00e5ff;font-weight:bold;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.ts{font-size:10px;color:#446;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:2px;}
a.obj-link{color:#00e5ff;text-decoration:none;cursor:pointer;}
a.obj-link:hover{text-decoration:underline;}
.detail-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;height:60%;color:#223;font-size:13px;gap:8px;}
.detail-placeholder svg{opacity:.15;}
</style>

<div class="main">

<div class="tab-row">
  <div class="tab on" onclick="switchTab('overview')">Overview</div>
  <div class="tab" onclick="switchTab('services')">Services</div>
  <div class="tab" onclick="switchTab('operations')">Service Ops</div>
  <div class="tab" onclick="switchTab('routings')">Routings</div>
  <div class="tab" onclick="switchTab('nodes')">Nodes</div>
  <div class="tab" onclick="switchTab('queues')">Queues</div>
  <div class="tab" onclick="switchTab('txns')">Txns</div>
</div>

<div class="explorer">

  <!-- LEFT: list panel -->
  <div class="list-panel">

    <div id="tab-overview" style="display:flex;flex-direction:column;overflow-y:auto;padding:10px;">
      <div class="cstat-row">
        <div class="cstat"><div class="cstat-num" id="ovSvc">--</div><div class="cstat-lbl">Services</div></div>
        <div class="cstat"><div class="cstat-num" id="ovOps">--</div><div class="cstat-lbl">Ops</div></div>
        <div class="cstat"><div class="cstat-num" id="ovRtng">--</div><div class="cstat-lbl">Routings</div></div>
        <div class="cstat"><div class="cstat-num" id="ovNode">--</div><div class="cstat-lbl">Nodes</div></div>
        <div class="cstat"><div class="cstat-num" id="ovQueue">--</div><div class="cstat-lbl">Queues</div></div>
        <div class="cstat" style="grid-column:span 1;cursor:pointer;border-color:#00cc6633;" onclick="switchTab('txns')"><div class="cstat-num" style="font-size:11px;color:#00cc66;">&#9654;</div><div class="cstat-lbl">Txns</div></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;margin-top:8px;">
        <button style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('services')">&#127760; Browse Services</button>
        <button style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('operations')">&#9881; Browse Service Ops</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('routings')">&#8652; Routings</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('nodes')">&#128279; Nodes</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('queues')">&#11036; Queues</button>
        <button class="sec" style="width:100%;text-align:left;font-size:10px;" onclick="switchTab('txns')">&#8644; Transactions</button>
      </div>
      <div id="dashboard" style="margin-top:10px;"></div>
    </div>

    <div id="tab-services" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="svcQ" type="text" placeholder="Search services…" onkeydown="if(event.key==='Enter')loadServices()">
        <button onclick="loadServices()">Go</button>
      </div>
      <div class="list-area" id="svcList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-operations" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="opQ" type="text" placeholder="Search service ops…" onkeydown="if(event.key==='Enter')loadOperations()">
        <button onclick="loadOperations()">Go</button>
      </div>
      <div class="list-area" id="opList"><span class="empty" style="padding:8px;">Type to search</span></div>
    </div>

    <div id="tab-routings" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="rtngQ" type="text" placeholder="Search routings…" onkeydown="if(event.key==='Enter')loadRoutings()">
        <button onclick="loadRoutings()">Go</button>
      </div>
      <div class="list-area" id="rtngList"><span class="empty" style="padding:8px;">Type to search</span></div>
    </div>

    <div id="tab-nodes" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="nodeQ" type="text" placeholder="Search nodes…" onkeydown="if(event.key==='Enter')loadNodes()">
        <button onclick="loadNodes()">Go</button>
      </div>
      <div class="list-area" id="nodeList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-queues" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar">
        <input id="queueQ" type="text" placeholder="Search queues…" onkeydown="if(event.key==='Enter')loadQueues()">
        <button onclick="loadQueues()">Go</button>
      </div>
      <div class="list-area" id="queueList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

    <div id="tab-txns" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div class="search-bar" style="flex-direction:column;gap:4px;">
        <input id="txQ" type="text" placeholder="Operation / node / queue…" onkeydown="if(event.key==='Enter')loadTxns()">
        <div style="display:flex;gap:4px;">
          <select id="txStatus" style="flex:1;font-size:10px;">
            <option value="">All Status</option>
            <option value="1">New</option>
            <option value="2">Started</option>
            <option value="3">Done</option>
            <option value="4">Cancelled</option>
            <option value="5">Error</option>
            <option value="6">Retry</option>
            <option value="7">Timeout</option>
          </select>
          <button onclick="loadTxns()">Go</button>
        </div>
      </div>
      <div class="list-area" id="txList"><span class="empty" style="padding:8px;">Loading…</span></div>
    </div>

  </div><!-- .list-panel -->

  <!-- RIGHT: detail panel -->
  <div class="detail-panel" id="detailPanel">
    <div class="breadcrumb" id="breadcrumb"></div>
    <div class="detail-scroll" id="detailScroll">
      <div id="detailContent">
        <div class="detail-placeholder">
          <svg width="60" height="60" viewBox="0 0 60 60"><circle cx="30" cy="30" r="28" fill="none" stroke="#00e5ff" stroke-width="1.5"/><line x1="30" y1="10" x2="30" y2="50" stroke="#00e5ff" stroke-width="1"/><line x1="10" y1="30" x2="50" y2="30" stroke="#00e5ff" stroke-width="1"/></svg>
          <div>Select an object from the list to explore its relationships</div>
        </div>
      </div>
    </div>
  </div><!-- .detail-panel -->

</div><!-- .explorer -->

</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
let currentTab = 'overview';

function env() { return (window.dsGetEnv && window.dsGetEnv()) || 'HCM'; }

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path, opts) {
  const r = await fetch(path, opts || {});
  return r.json().catch(() => ({}));
}

// ─── nav stack (breadcrumbs) ───────────────────────────────────────────────
let navStack = [];
const NAV_ICONS = {service:'&#127760;',operation:'&#9881;',routing:'&#8652;',node:'&#128279;',queue:'&#11036;',txn:'&#8644;'};

function pushNav(type, name, push=true) {
  if (!push) return;
  // If clicking the same thing that's already at top of stack, skip
  if (navStack.length && navStack[navStack.length-1].type===type && navStack[navStack.length-1].name===name) {
    renderBreadcrumb(); return;
  }
  navStack.push({type, name});
  renderBreadcrumb();
}

function renderBreadcrumb() {
  const bc = $('breadcrumb');
  if (!navStack.length) { bc.innerHTML = '<span class="bc-cur" style="color:#334;">Select an object</span>'; return; }
  bc.innerHTML = '<span class="bc-link" onclick="navStack=[];clearDetail();">IB</span>'
    + navStack.map((n, i) => {
        const icon = NAV_ICONS[n.type] || '';
        const label = `${icon} ${esc(n.name)}`;
        return '<span class="bc-sep">›</span>'
          + (i < navStack.length-1
              ? `<span class="bc-link" onclick="navTo(${i})">${label}</span>`
              : `<span class="bc-cur">${label}</span>`);
      }).join('');
}

function navTo(idx) {
  const n = navStack[idx];
  navStack = navStack.slice(0, idx + 1);
  const fn = {service:showService,operation:showOperation,routing:showRouting,node:showNode,queue:showQueue,txn:showTxn}[n.type];
  if (fn) fn(n.name, false);
}

function clearDetail() {
  navStack = [];
  renderBreadcrumb();
  $('detailContent').innerHTML = '<div class="detail-placeholder"><div>Select an object from the list</div></div>';
  document.querySelectorAll('.list-item').forEach(el=>el.classList.remove('active'));
}

// Mark active item in list
function markActive(listId, name) {
  document.querySelectorAll(`#${listId} .list-item`).forEach(el => {
    el.classList.toggle('active', el.dataset.name === name);
  });
}

// ─── tabs ──────────────────────────────────────────────────────────────────
const TABS = ['overview','services','operations','routings','nodes','queues','txns'];
function switchTab(name) {
  currentTab = name;
  TABS.forEach(t => {
    const el = $(`tab-${t}`);
    if (el) el.style.display = t === name ? 'flex' : 'none';
  });
  document.querySelectorAll('.tab').forEach((el, i) => {
    el.classList.toggle('on', TABS[i] === name);
  });
  if (name === 'overview') loadDashboard();
  if (name === 'services' && !$('svcList').querySelector('.list-item')) loadServices();
  if (name === 'operations' && !$('opList').querySelector('.list-item')) loadOperations();
  if (name === 'routings' && !$('rtngList').querySelector('.list-item')) loadRoutings();
  if (name === 'nodes' && !$('nodeList').querySelector('.list-item')) loadNodes();
  if (name === 'queues' && !$('queueList').querySelector('.list-item')) loadQueues();
  if (name === 'txns') loadTxns();
}

// ─── list loaders ─────────────────────────────────────────────────────────
async function loadServices() {
  const q = $('svcQ').value;
  $('svcList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/services?env=${env()}&q=${encodeURIComponent(q)}&limit=500`);
  const items = d.items || [];
  renderList('svcList', items, item => {
    const b = bStatus(item.status_label);
    return `<div class="list-item" data-name="${esc(item.ptibapplname)}" onclick="showService('${item.ptibapplname}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name">${esc(item.ptibapplname)}</span>
      <div class="item-meta">${esc(item.descr || '')}</div>
    </div>`;
  });
  if (items.length) {
    const note = document.createElement('div');
    note.style.cssText = 'font-size:10px;color:#334;padding:4px 8px;border-top:1px solid #0b1b24;';
    note.textContent = `${items.length} service${items.length===1?'':'s'}${q ? ' matching' : ' total'} · PSIBAPPLDEFN`;
    $('svcList').appendChild(note);
  }
  warnBox(d.warnings);
}

async function loadOperations() {
  const q = $('opQ').value;
  $('opList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/operations?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('opList', d.items || [], item => {
    const routeBits = item.routing_count != null ? `${item.routing_count}r` : '';
    return `<div class="list-item" data-name="${esc(item.ib_operationname)}" onclick="showOperation('${item.ib_operationname}')">
      <span class="badge bd-info">${esc(item.service_kind || 'Op')}</span>
      <span class="item-name">${esc(item.ib_operationname)}</span>
      <div class="item-meta">${esc(item.ib_servicename || item.ptibapplname || '')}${routeBits ? ' · ' + routeBits : ''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadRoutings() {
  const q = $('rtngQ').value;
  $('rtngList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/routings?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('rtngList', d.items || [], item => {
    return `<div class="list-item" data-name="${esc(item.routingdefnname)}" onclick="showRouting('${item.routingdefnname}')">
      <span class="item-name">${esc(item.routingdefnname)}</span>
      <div class="item-meta">${esc(item.sendernodename||'*')} → ${esc(item.receivernodename||'*')}${item.eff_status_label?' · '+esc(item.eff_status_label):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadNodes() {
  const q = $('nodeQ').value;
  $('nodeList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/nodes?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('nodeList', d.items || [], item => {
    const b = bStatus(item.active_label);
    const localTag = item.is_local ? ' <span style="font-size:9px;color:#00e5ff;">[LOCAL]</span>' : '';
    return `<div class="list-item" data-name="${esc(item.msgnodename)}" onclick="showNode('${item.msgnodename}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name">${esc(item.msgnodename)}</span>${localTag}
      <div class="item-meta">${esc(item.node_type_label||'')}${item.toolsrel?' · '+esc(item.toolsrel):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadQueues() {
  const q = $('queueQ').value;
  $('queueList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  const d = await api(`/api/ib/queues?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
  renderList('queueList', d.items || [], item => {
    const b = bQueue(item.queuestatus_label);
    return `<div class="list-item" data-name="${esc(item.queuename)}" onclick="showQueue('${item.queuename}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name">${esc(item.queuename)}</span>
      <div class="item-meta">${esc(item.descr||'')}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

async function loadTxns() {
  const q  = $('txQ').value;
  const st = $('txStatus').value;
  $('txList').innerHTML = '<span class="empty" style="padding:8px;">Loading…</span>';
  let url = `/api/ib/transactions?env=${env()}&q=${encodeURIComponent(q)}&limit=100`;
  if (st) url += `&status=${st}`;
  const d = await api(url);
  renderList('txList', d.items || [], item => {
    const b = bTx(item.pubstatus_label);
    return `<div class="list-item" data-name="${esc(item.ibtransactionid)}" onclick="showTxn('${item.ibtransactionid}')">
      <span class="badge ${b.cls}">${b.text}</span>
      <span class="item-name mono" style="font-size:10px;">${esc((item.ibtransactionid||'').substring(0,26))}</span>
      <div class="item-meta">${esc(item.ib_operationname||'')}${item.queuename?' · '+esc(item.queuename):''}</div>
    </div>`;
  });
  warnBox(d.warnings);
}

function renderList(targetId, items, rowFn) {
  const box = $(targetId);
  if (!items.length) { box.innerHTML = '<span class="empty" style="padding:8px;">No results.</span>'; return; }
  box.innerHTML = items.map(rowFn).join('');
}

// ─── view transactions for a related object ────────────────────────────────
function viewTxnsFor(q) {
  $('txQ').value = q;
  $('txStatus').value = '';
  switchTab('txns');
  loadTxns();
}

// ─── relationship strip builder ────────────────────────────────────────────
function relStrip(label, tags) {
  if (!tags.length) return '';
  const tagsHtml = tags.map(t => `<span class="rel-tag${t.cls?' '+t.cls:''}" onclick="${t.action}">${t.icon||''}${esc(t.label)}</span>`).join('');
  return `<div class="rel-strip"><span class="rel-strip-label">${esc(label)}</span>${tagsHtml}</div>`;
}

// ─── detail views ──────────────────────────────────────────────────────────
function setDetail(html) {
  $('detailContent').innerHTML = html;
  $('detailScroll').scrollTop = 0;
}

async function showService(name, push=true) {
  pushNav('service', name, push);
  switchTab('services');
  markActive('svcList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/services/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const ops = it.service_operations || [];
  const opTags = ops.slice(0,8).map(op => ({label:op.ib_operationname, action:`showOperation('${op.ib_operationname}')`}));
  if (ops.length > 8) opTags.push({label:`+${ops.length-8} more`, action:`switchTab('operations')`});

  let h = relStrip('Operations', opTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#127760; ${esc(it.ptibapplname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card">
    <div class="kv-grid">
      ${kv('Status', chipStatus(it.status_label))}
      ${kv('Type', esc(it.service_kind || it.appltype_label))}
      ${kv('Service Name', esc(it.ib_servicename))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div>
  </div>`;

  if (ops.length) {
    h += `<h2>Service Operations (${ops.length})</h2><div class="card"><table><thead><tr>
      <th>Operation</th><th>Type</th><th>Method</th><th>Description</th>
    </tr></thead><tbody>`;
    ops.forEach(op => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showOperation('${op.ib_operationname}')">${esc(op.ib_operationname || '')}</a></td>
        <td>${esc(op.service_kind || '')}</td>
        <td>${esc(op.ib_restmethod || '')}</td><td>${esc(op.descr || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.operations||[]).length) {
    h += `<h2>Application Operations (${it.operations.length})</h2><div class="card"><table><thead><tr>
      <th>Operation</th><th>Status</th><th>Action</th><th>URI Template</th>
    </tr></thead><tbody>`;
    it.operations.forEach(op => {
      h += `<tr><td class="mono">${esc(op.ptibapplopr)}</td><td>${chipStatus(op.status_label)}</td>
        <td>${esc(op.ib_action||'')}</td><td class="mono" style="font-size:10px;">${esc(op.ib_uri_template||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.routings||[]).length) {
    h += `<h2>Routings (${it.routings.length})</h2><div class="card"><table><thead><tr>
      <th>Routing</th><th>From</th><th>To</th><th>Status</th>
    </tr></thead><tbody>`;
    it.routings.forEach(r => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.sendernodename}')">${esc(r.sendernodename||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.receivernodename}')">${esc(r.receivernodename||'')}</a></td>
        <td>${chipStatus(r.eff_status_label)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showOperation(name, push=true) {
  pushNav('operation', name, push);
  switchTab('operations');
  markActive('opList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/operations/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  // Build relationship strip
  const relTags = [];
  const svcName = it.ib_servicename || it.ptibapplname;
  if (svcName) relTags.push({label:`&#127760; ${svcName}`, action:`showService('${svcName}')`});
  (it.routings||[]).slice(0,3).forEach(r => {
    relTags.push({label:`&#8652; ${r.routingdefnname}`, action:`showRouting('${r.routingdefnname}')`});
  });
  (it.runtime_queues||[]).slice(0,2).forEach(q => {
    relTags.push({label:`&#11036; ${q.queuename}`, action:`showQueue('${q.queuename}')`});
  });
  relTags.push({label:'&#8644; Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#9881; ${esc(it.ib_operationname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Type', esc(it.service_kind))}
      ${svcName ? kv('Service', `<a class="obj-link" onclick="showService('${svcName}')">${esc(svcName)}</a>`) : ''}
      ${kv('Alias', esc(it.ib_aliasname))}
      ${kv('Default Version', esc(it.defaultver || it.versionname))}
      ${kv('REST Method', esc(it.ib_restmethod))}
      ${it.ib_restbase_url ? kv('REST Base URL', esc(it.ib_restbase_url)) : ''}
      ${kv('Routings', esc(it.routing_count))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.messages||[]).length) {
    h += `<h2>Messages (${it.messages.length})</h2><div class="card"><table><thead><tr>
      <th>Version</th><th>Request Msg</th><th>Response Msg</th><th>Queue</th>
    </tr></thead><tbody>`;
    it.messages.forEach(m => {
      const qname = m.queuename || '';
      h += `<tr><td class="mono">${esc(m.versionname || '')}</td>
        <td class="mono">${esc(m.ib_reqmsgname || m.msgname || '')}${m.inmsgversion ? ' v'+esc(m.inmsgversion) : ''}</td>
        <td class="mono">${esc(m.ib_respmsgname || '')}${m.outmsgversion ? ' v'+esc(m.outmsgversion) : ''}</td>
        <td class="mono">${qname ? `<a class="obj-link" onclick="showQueue('${qname}')">${esc(qname)}</a>` : ''}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.routings||[]).length) {
    h += `<h2>Routings (${it.routings.length})</h2><div class="card"><table><thead><tr>
      <th>Routing</th><th>Sender Node</th><th>Receiver Node</th><th>Status</th>
    </tr></thead><tbody>`;
    it.routings.forEach(r => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.sendernodename}')">${esc(r.sendernodename || '')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${r.receivernodename}')">${esc(r.receivernodename || '')}</a></td>
        <td>${chipStatus(r.eff_status_label)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.handlers||[]).length) {
    h += `<h2>Handlers (${it.handlers.length})</h2><div class="card"><table><thead><tr>
      <th>Handler</th><th>Type</th><th>Version</th><th>Status</th><th>Owner</th>
    </tr></thead><tbody>`;
    it.handlers.forEach(x => {
      h += `<tr><td class="mono">${esc(x.handlername || '')}</td><td>${esc(x.handlertype || '')}</td>
        <td class="mono">${esc(x.version || '')}</td><td>${chipStatus(x.active_label)}</td>
        <td>${esc(x.handlerowner || x.objectownerid || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.runtime_queues||[]).length) {
    h += `<h2>Runtime Queues (${it.runtime_queues.length})</h2><div class="card"><table><thead><tr>
      <th>Queue</th><th>Status</th><th>Count</th><th>Last Created</th>
    </tr></thead><tbody>`;
    it.runtime_queues.forEach(q => {
      h += `<tr><td class="mono"><a class="obj-link" onclick="showQueue('${q.queuename}')">${esc(q.queuename || '')}</a></td>
        <td>${chipTx(q.pubstatus_label)}</td><td>${esc(q.cnt)}</td><td class="ts">${esc(q.last_created || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.versions||[]).length) {
    h += `<h2>Versions (${it.versions.length})</h2><div class="card"><table><thead><tr>
      <th>Version</th><th>Status</th><th>Multi Queue</th><th>Description</th>
    </tr></thead><tbody>`;
    it.versions.forEach(v => {
      h += `<tr><td class="mono">${esc(v.versionname || v.version || '')}</td>
        <td>${chipStatus(v.active_label)}</td><td>${esc(v.ib_multiqueue || '')}</td>
        <td>${esc(v.descr || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.security||[]).length) {
    h += `<h2>Security (${it.security.length})</h2><div class="card"><table><thead><tr>
      <th>Service</th><th>Group</th><th>Security</th>
    </tr></thead><tbody>`;
    it.security.forEach(s => {
      h += `<tr><td class="mono">${esc(s.ib_servicename || '')}</td>
        <td class="mono">${esc(s.ib_intgroupname || '')}</td>
        <td>${esc(s.ib_servicesecurity || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showRouting(name, push=true) {
  pushNav('routing', name, push);
  switchTab('routings');
  markActive('rtngList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/routings/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const relTags = [];
  if (it.ib_operationname) relTags.push({label:`&#9881; ${it.ib_operationname}`, action:`showOperation('${it.ib_operationname}')`});
  if (it.sendernodename) relTags.push({label:`&#8594; ${it.sendernodename}`, action:`showNode('${it.sendernodename}')`});
  if (it.receivernodename) relTags.push({label:`&#8592; ${it.receivernodename}`, action:`showNode('${it.receivernodename}')`});
  relTags.push({label:'&#8644; Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#8652; ${esc(it.routingdefnname)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipStatus(it.eff_status_label))}
      ${kv('Type', esc(it.rtngtype_label))}
      ${kv('Service Operation', `<a class="obj-link" onclick="showOperation('${it.ib_operationname}')">${esc(it.ib_operationname)}</a>`)}
      ${kv('Sender Node', `<a class="obj-link" onclick="showNode('${it.sendernodename}')">${esc(it.sendernodename)}</a>`)}
      ${kv('Receiver Node', `<a class="obj-link" onclick="showNode('${it.receivernodename}')">${esc(it.receivernodename)}</a>`)}
      ${kv('REST Method', esc(it.ib_restmethod))}
      ${kv('Delivery Mode', esc(it.ib_deliverymode))}
      ${kv('Effective Date', esc(it.effdt))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.sub_definitions||[]).length) {
    h += `<h2>Sub-Definitions (${it.sub_definitions.length})</h2><div class="card"><table><thead><tr>
      <th>Seq</th><th>Direction</th><th>From Node</th><th>To Node</th><th>Type</th>
    </tr></thead><tbody>`;
    it.sub_definitions.forEach(s => {
      h += `<tr><td>${esc(s.seqnum)}</td><td>${esc(s.ib_direction)}</td>
        <td class="mono"><a class="obj-link" onclick="showNode('${s.sendernodename}')">${esc(s.sendernodename||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showNode('${s.receivernodename}')">${esc(s.receivernodename||'')}</a></td>
        <td>${esc(s.rtngtype)}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showNode(name, push=true) {
  if (!name || name === 'null' || name === 'undefined') return;
  pushNav('node', name, push);
  switchTab('nodes');
  markActive('nodeList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/nodes/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const allRoutings = [...(it.routings_as_sender||[]), ...(it.routings_as_receiver||[])];
  const uniqueOps = [...new Set(allRoutings.map(r=>r.ib_operationname).filter(Boolean))];
  const relTags = uniqueOps.slice(0,5).map(op => ({label:`&#9881; ${op}`, action:`showOperation('${op}')`}));
  relTags.push({label:'&#8644; Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`});

  let h = relStrip('Related Ops', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">
    &#128279; ${esc(it.msgnodename)}
    ${it.is_local ? '<span class="chip ch-info" style="font-size:9px;margin-left:6px;">LOCAL</span>' : ''}
    ${it.is_default ? '<span class="chip ch-info" style="font-size:9px;margin-left:4px;">DEFAULT</span>' : ''}
  </div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipActive(it.active_label))}
      ${kv('Node Type', esc(it.node_type_label))}
      ${kv('Tools Release', esc(it.toolsrel))}
      ${kv('App Release', esc(it.apmsgapprel))}
      ${it.ib_tgtlocation ? kv('Target Location', esc(it.ib_tgtlocation)) : ''}
      ${it.conngatewayid ? kv('Gateway ID', esc(it.conngatewayid)) : ''}
      ${it.networknodename ? kv('Network Node', esc(it.networknodename)) : ''}
      ${it.hubnodename ? kv('Hub Node', esc(it.hubnodename)) : ''}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  if ((it.routings_as_sender||[]).length) h += rtngTable('Sends Via Routings', it.routings_as_sender);
  if ((it.routings_as_receiver||[]).length) h += rtngTable('Receives Via Routings', it.routings_as_receiver);

  warnBox(d.warnings);
  setDetail(h);
}

function rtngTable(title, rows) {
  let h = `<h2>${esc(title)} (${rows.length})</h2><div class="card"><table><thead><tr>
    <th>Routing</th><th>Operation</th><th>From</th><th>To</th><th>Status</th>
  </tr></thead><tbody>`;
  rows.forEach(r => {
    h += `<tr>
      <td class="mono"><a class="obj-link" onclick="showRouting('${r.routingdefnname}')">${esc(r.routingdefnname)}</a></td>
      <td class="mono"><a class="obj-link" onclick="showOperation('${r.ib_operationname}')">${esc(r.ib_operationname||'')}</a></td>
      <td class="mono">${esc(r.sendernodename||'')}</td><td class="mono">${esc(r.receivernodename||'')}</td>
      <td>${chipStatus(r.eff_status_label)}</td></tr>`;
  });
  return h + '</tbody></table></div>';
}

async function showQueue(name, push=true) {
  pushNav('queue', name, push);
  switchTab('queues');
  markActive('queueList', name);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/queues/${encodeURIComponent(name)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found: ${esc(name)}</div>`); return; }

  const relTags = [{label:'&#8644; Transactions', cls:'rel-action', action:`viewTxnsFor('${name}')`}];

  let h = relStrip('Related', relTags);
  h += `<div style="font-size:14px;font-family:monospace;color:#00e5ff;margin-bottom:4px;">&#11036; ${esc(it.queuename)}</div>`;
  if (it.descr) h += `<div style="color:#9ab;margin-bottom:8px;font-size:11px;">${esc(it.descr)}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipQueue(it.queuestatus_label))}
      ${kv('Throughput', esc(it.thruput_label))}
      ${kv('Priority', esc(it.ptib_queue_pri))}
      ${kv('Archive', esc(it.archive))}
      ${kv('Owner', esc(it.objectownerid))}
      ${kv('Last Updated', esc(it.lastupddttm))}
    </div></div>`;

  const rt = it.runtime || {};
  if ((rt.pub_by_status||[]).length || (rt.sub_by_status||[]).length) {
    h += `<h2>Runtime Activity (24h)</h2><div class="card">`;
    if (rt.pub_by_status && rt.pub_by_status.length) {
      h += `<div style="margin-bottom:6px;"><span style="font-size:10px;color:#667;text-transform:uppercase;margin-right:6px;">Pub:</span>`;
      rt.pub_by_status.forEach(s => { h += `${chipTx(s.status_label)}&nbsp;<span class="mono" style="margin-right:8px;">${s.cnt}</span>`; });
      h += '</div>';
    }
    if (rt.sub_by_status && rt.sub_by_status.length) {
      h += `<div><span style="font-size:10px;color:#667;text-transform:uppercase;margin-right:6px;">Sub:</span>`;
      rt.sub_by_status.forEach(s => { h += `${chipTx(s.status_label)}&nbsp;<span class="mono" style="margin-right:8px;">${s.cnt}</span>`; });
      h += '</div>';
    }
    h += '</div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

async function showTxn(txid, push=true) {
  pushNav('txn', txid, push);
  switchTab('txns');
  markActive('txList', txid);
  setDetail('<span class="empty">Loading…</span>');
  const d = await api(`/api/ib/transactions/${encodeURIComponent(txid)}?env=${env()}`);
  const it = d.item;
  if (!it) { setDetail(`<div class="err-msg">Not found.</div>`); return; }

  const relTags = [];
  if (it.ib_operationname) relTags.push({label:`&#9881; ${it.ib_operationname}`, action:`showOperation('${it.ib_operationname}')`});
  if (it.queuename) relTags.push({label:`&#11036; ${it.queuename}`, action:`showQueue('${it.queuename}')`});
  if (it.pubnode) relTags.push({label:`&#128279; ${it.pubnode}`, action:`showNode('${it.pubnode}')`});

  let h = relStrip('Path', relTags);
  h += `<div style="font-family:monospace;color:#00e5ff;font-size:11px;margin-bottom:4px;">&#8644; ${esc((txid||'').substring(0,36))}</div>`;
  h += `<div class="card"><div class="kv-grid">
      ${kv('Status', chipTx(it.pubstatus_label))}
      ${kv('Operation', `<a class="obj-link" onclick="showOperation('${it.ib_operationname}')">${esc(it.ib_operationname)}</a>`)}
      ${kv('Queue', it.queuename ? `<a class="obj-link" onclick="showQueue('${it.queuename}')">${esc(it.queuename)}</a>` : '')}
      ${kv('Pub Node', it.pubnode ? `<a class="obj-link" onclick="showNode('${it.pubnode}')">${esc(it.pubnode)}</a>` : '')}
      ${it.destpubnode ? kv('Dest Node', esc(it.destpubnode)) : ''}
      ${kv('Publisher', esc(it.publisher))}
      ${kv('Created', esc(it.createdttm))}
      ${kv('Retry Count', esc(it.retrycount))}
      ${kv('Machine', esc(it.machinename))}
    </div>
    ${it.statusstring ? `<div class="warn-msg" style="margin-top:6px;">${esc(it.statusstring)}</div>` : ''}
  </div>`;

  if ((it.pub_contracts||[]).length) {
    h += `<h2>Publication Contracts (${it.pub_contracts.length})</h2><div class="card"><table><thead><tr>
      <th>Sub Node</th><th>Routing</th><th>Status</th><th>Retries</th><th>Updated</th>
    </tr></thead><tbody>`;
    it.pub_contracts.forEach(c => {
      h += `<tr>
        <td class="mono"><a class="obj-link" onclick="showNode('${c.subnode}')">${esc(c.subnode||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showRouting('${c.routingdefnname}')">${esc(c.routingdefnname||'')}</a></td>
        <td>${chipTx(c.pubconstatus_label)}</td><td>${esc(c.retrycount)}</td>
        <td class="ts">${esc(c.lastupddttm||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  if ((it.sub_contracts||[]).length) {
    h += `<h2>Subscription Contracts (${it.sub_contracts.length})</h2><div class="card"><table><thead><tr>
      <th>Action</th><th>Operation</th><th>Routing</th><th>Status</th><th>Proc Inst</th>
    </tr></thead><tbody>`;
    it.sub_contracts.forEach(c => {
      h += `<tr><td class="mono">${esc(c.actionname||'')}</td>
        <td class="mono"><a class="obj-link" onclick="showOperation('${c.ib_operationname}')">${esc(c.ib_operationname||'')}</a></td>
        <td class="mono"><a class="obj-link" onclick="showRouting('${c.routingdefnname}')">${esc(c.routingdefnname||'')}</a></td>
        <td>${chipTx(c.subconstatus_label)}</td>
        <td>${esc(c.process_instance||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  warnBox(d.warnings);
  setDetail(h);
}

// ─── dashboard ────────────────────────────────────────────────────────────
async function loadDashboard() {
  const dashboard = $('dashboard');
  if (!dashboard) return;
  const d = await api(`/api/ib/dashboard?env=${env()}`);
  let h = '';

  const configured = d.service_count != null || d.node_count != null;
  if (!configured) {
    h += `<div class="card"><div class="warn-msg">IB metadata tables are not accessible in this environment.
      The monitoring account may lack grants to PSIBAPPLDEFN, PSIBRTNGDEFN, PSMSGNODEDEFN and related tables.</div></div>`;
    (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">${esc(w.message||w)}</div>`; });
    dashboard.innerHTML = h;
    return;
  }

  $('ovSvc').textContent   = d.service_count != null ? d.service_count : '--';
  $('ovOps').textContent   = d.operation_count != null ? d.operation_count : '--';
  $('ovRtng').textContent  = d.routing_count != null ? d.routing_count : '--';
  $('ovNode').textContent  = d.node_count != null ? d.node_count : '--';
  $('ovQueue').textContent = d.queue_count != null ? d.queue_count : '--';

  if ((d.pub_by_status||[]).length) {
    h += `<h2>Publications — Last 24h</h2><div class="card" style="display:flex;gap:16px;flex-wrap:wrap;">`;
    d.pub_by_status.forEach(s => {
      h += `<div style="text-align:center;"><div class="stat-num" style="font-size:18px;">${esc(s.cnt)}</div><div>${chipTx(s.status_label)}</div></div>`;
    });
    h += '</div>';
  }

  if ((d.sub_by_status||[]).length) {
    h += `<h2>Subscriptions — Last 24h</h2><div class="card" style="display:flex;gap:16px;flex-wrap:wrap;">`;
    d.sub_by_status.forEach(s => {
      h += `<div style="text-align:center;"><div class="stat-num" style="font-size:18px;">${esc(s.cnt)}</div><div>${chipTx(s.status_label)}</div></div>`;
    });
    h += '</div>';
  }

  if ((d.domain_status||[]).length) {
    h += `<h2>Domain Status</h2><div class="card"><table><thead><tr>
      <th>Domain ID</th><th>Machine</th><th>Server Domain</th><th>Last Updated</th>
    </tr></thead><tbody>`;
    d.domain_status.forEach(ds => {
      h += `<tr><td class="mono">${esc(ds.ibdomainid||'')}</td><td>${esc(ds.machinename||'')}</td>
        <td>${esc(ds.serverdomainname||'')}</td><td class="ts">${esc(ds.lastupddttm||'')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }

  (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">${esc(w.message||w)}</div>`; });
  $('dashboard').innerHTML = h;
}

// ─── helpers ──────────────────────────────────────────────────────────────
function kv(label, val) {
  if (val == null || val === '') return '';
  return `<div class="kv-key">${esc(label)}</div><div class="kv-val">${val}</div>`;
}
function sBox(n, lbl) {
  return `<div class="stat-box"><div class="stat-num">${n != null ? n : '—'}</div><div class="stat-lbl">${esc(lbl)}</div></div>`;
}
function bStatus(l) { return l === 'Active' ? {cls:'bd-ok',text:l||''} : {cls:'bd-mute',text:l||''}; }
function bQueue(l)  { return l === 'Running' ? {cls:'bd-ok',text:l} : l === 'Halted' ? {cls:'bd-err',text:l} : {cls:'bd-warn',text:l||''}; }
function bTx(l)     { return (l==='Error'||l==='Timeout') ? {cls:'bd-err',text:l} : l==='Done' ? {cls:'bd-ok',text:l} : {cls:'bd-mute',text:l||''}; }
function chipStatus(l) { const c=l==='Active'?'ch-ok':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipActive(l) { const c=l==='Active'?'ch-ok':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipQueue(l)  { const c=l==='Running'?'ch-ok':l==='Halted'?'ch-err':'ch-warn'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function chipTx(l)     { const c=(l==='Error'||l==='Timeout')?'ch-err':l==='Done'?'ch-ok':l==='Started'?'ch-warn':'ch-mute'; return `<span class="chip ${c}">${esc(l||'')}</span>`; }
function warnBox(ws) {
  if (!ws||!ws.length) return;
  const box = document.querySelector('#detailContent .warn-container') || (() => {
    const el = document.createElement('div');
    el.className = 'warn-container';
    $('detailContent').appendChild(el);
    return el;
  })();
  box.innerHTML = ws.map(w => `<div class="warn-msg">${esc(w.message||w)}</div>`).join('');
}

// ─── init ─────────────────────────────────────────────────────────────────
function reload() {
  const dashboard = $('dashboard');
  if (dashboard) dashboard.innerHTML = '';
  clearDetail();
  loadDashboard();
  loadServices();
  loadOperations();
  loadNodes();
  loadQueues();
}

(async () => {
  renderBreadcrumb();

  await Promise.all([loadDashboard(), loadServices(), loadNodes(), loadQueues()]);

  // Deep-link: /admin/ib?tab=services&show=MY_SERVICE  (from Object Explorer global search)
  const params = new URLSearchParams(location.search);
  const deepTab  = params.get('tab');
  const deepShow = params.get('show');
  if (deepTab && deepShow) {
    switchTab(deepTab);
    const tabShowMap = {
      services: showService, operations: showOperation, routings: showRouting,
      nodes: showNode, queues: showQueue, txns: showTxn,
    };
    const fn = tabShowMap[deepTab];
    if (fn) fn(deepShow);
  } else {
    switchTab('overview');
  }
})();
</script>""")


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


@router.get("/envcompare", response_class=HTMLResponse)
def admin_envcompare():
    return _shell("Environment Comparison", "envcompare", noscroll=True, env=False, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;min-height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:220px;border-right:1px solid #00e5ff22;padding:10px;overflow-y:auto;}
.content{flex:1;overflow:auto;padding:14px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button:disabled{opacity:.4;cursor:default;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;margin-bottom:10px;}
.tab{padding:7px 13px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.stat-grid{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;}
.stat-box{border:1px solid #00e5ff22;padding:8px 14px;min-width:110px;text-align:center;background:rgba(0,20,30,.5);cursor:pointer;}
.stat-box:hover{border-color:#00e5ff66;}
.stat-box.active{border-color:#00e5ff;background:rgba(0,229,255,.07);}
.stat-num{font-size:20px;font-weight:bold;}
.stat-lbl{font-size:10px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.n-only1{color:#ff9900;}
.n-changed{color:#ffdd55;}
.n-only2{color:#55aaff;}
.n-same{color:#00cc66;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.card{border:1px solid #00e5ff22;padding:10px 14px;margin-bottom:10px;background:rgba(0,20,30,.5);}
.section-head{font-size:11px;font-weight:bold;padding:5px 0 4px;border-bottom:1px solid #0a2030;margin-bottom:4px;display:flex;align-items:center;gap:8px;cursor:pointer;}
.section-head:hover{color:#00e5ff;}
.toggle{font-size:10px;color:#556;}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;}
.chip-add{background:#001e00;border:1px solid #00cc66;color:#00cc66;}
.chip-del{background:#200000;border:1px solid #ff6600;color:#ff9900;}
.chip-chg{background:#1a1400;border:1px solid #ffdd55;color:#ffdd55;}
.chip-same{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.diff-row{background:#12181f;border-left:3px solid #ffdd55;padding:3px 8px;margin:1px 0;font-size:11px;}
.diff-col{color:#667;font-size:10px;text-transform:uppercase;letter-spacing:1px;}
.diff-v1{color:#ff9900;}
.diff-v2{color:#55aaff;}
.ctrl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;}
.env-label{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;}
a.obj-link{color:#00e5ff;text-decoration:none;cursor:pointer;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.spinner{display:none;color:#00e5ff;font-size:11px;margin-left:8px;}
.spinner.on{display:inline;}
</style>

<div class="main">

<!-- ═══════════════════════════════════════════════════════════ SIDEBAR -->
<div class="sidebar">
  <h2>Environments</h2>
  <div style="margin-bottom:8px;">
    <span class="env-label">Left</span>
    <select id="env1Sel" onchange="loadSummary()" style="width:100%;margin-top:2px;"></select>
  </div>
  <div style="margin-bottom:12px;">
    <span class="env-label">Right</span>
    <select id="env2Sel" onchange="loadSummary()" style="width:100%;margin-top:2px;"></select>
  </div>

  <h2>Object Counts</h2>
  <div id="summaryTable"><span class="empty">Loading…</span></div>
</div>

<!-- ═══════════════════════════════════════════════════════ CONTENT AREA -->
<div class="content">
  <div class="tab-row">
    <div class="tab on"  onclick="switchTab('records')">Records</div>
    <div class="tab"     onclick="switchTab('fields')">Fields</div>
    <div class="tab"     onclick="switchTab('components')">Components</div>
    <div class="tab"     onclick="switchTab('permissions')">Permissions</div>
    <div class="tab"     onclick="switchTab('ae')">AE Programs</div>
    <div class="tab"     onclick="switchTab('roles')">Roles</div>
    <div class="tab"     onclick="switchTab('peoplecode')">PeopleCode</div>
    <div class="tab"     onclick="switchTab('sql_definitions')">SQL Defs</div>
    <div class="tab"     onclick="switchTab('portals')">Portals</div>
    <div class="tab"     onclick="switchTab('queries')">PS Queries</div>
    <div class="tab"     onclick="switchTab('graph')">Graph</div>
  </div>

  <!-- Records tab -->
  <div id="pane-records" class="pane on">
    <div class="ctrl">
      <input id="recQ" type="text" placeholder="Search records…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('records')">
      <button onclick="runCompare('records')">Compare</button>
      <span class="spinner" id="spin-records">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-records"></div>
  </div>

  <!-- Fields tab -->
  <div id="pane-fields" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="fieldRec" type="text" placeholder="Record name (e.g. PSRECDEFN)" style="width:220px;" onkeydown="if(event.key==='Enter')runFieldCompare()">
      <button onclick="runFieldCompare()">Compare Fields</button>
      <span class="spinner" id="spin-fields">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-fields"></div>
  </div>

  <!-- Components tab -->
  <div id="pane-components" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="compQ" type="text" placeholder="Search components…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('components')">
      <button onclick="runCompare('components')">Compare</button>
      <span class="spinner" id="spin-components">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-components"></div>
  </div>

  <!-- Permissions tab -->
  <div id="pane-permissions" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="permQ" type="text" placeholder="Search permission lists…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('permissions')">
      <button onclick="runCompare('permissions')">Compare</button>
      <span class="spinner" id="spin-permissions">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-permissions"></div>
  </div>

  <!-- AE tab -->
  <div id="pane-ae" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="aeQ" type="text" placeholder="Search AE programs…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('ae')">
      <button onclick="runCompare('ae')">Compare</button>
      <span class="spinner" id="spin-ae">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-ae"></div>
  </div>

  <!-- Roles tab -->
  <div id="pane-roles" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="roleQ" type="text" placeholder="Search roles…" style="width:220px;" onkeydown="if(event.key==='Enter')runCompare('roles')">
      <button onclick="runCompare('roles')">Compare</button>
      <span class="spinner" id="spin-roles">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-roles"></div>
  </div>

  <!-- PeopleCode tab -->
  <div id="pane-peoplecode" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="pcQ" type="text" placeholder="Filter by parent object (e.g. JOB, GDP_SELECT_PRCS)…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('peoplecode')">
      <button onclick="runCompare('peoplecode')">Compare Catalog</button>
      <span class="spinner" id="spin-peoplecode">&#9679;&#9679;&#9679;</span>
    </div>
    <div class="warn-msg" style="margin-bottom:6px;">Key = objectid1|ov1|ov2|ov3|ov4|ov5 &nbsp;&middot;&nbsp; Compare col = lastupddttm &nbsp;&middot;&nbsp; Capped at 500 programs — use the filter to scope by record/component name.</div>
    <div id="res-peoplecode"></div>
    <hr style="border-color:#1a2a3a;margin:18px 0">
    <div style="font-size:11px;color:#8ab;margin-bottom:8px;font-weight:bold;letter-spacing:.05em;">DEEP SOURCE DIFF</div>
    <div class="ctrl">
      <input id="pcRefInput" type="text" placeholder="Reference (e.g. JOB.EMPLID.FieldEdit.0 or JOB.FieldFormula.0)…" style="width:420px;" onkeydown="if(event.key==='Enter')runPcSourceDiff()">
      <button onclick="runPcSourceDiff()">Diff Source</button>
      <span class="spinner" id="spin-pc-diff">&#9679;&#9679;&#9679;</span>
    </div>
    <div style="font-size:10px;color:#445;margin-bottom:6px;">Format: OV1.OV2.OV3.Event.PROGSEQ — e.g. <code>JOB.FieldFormula.0</code> or <code>GBL_JOB_DATA.W.JOB.FieldEdit.0</code></div>
    <div id="res-pc-diff"></div>
  </div>

  <!-- SQL Definitions tab -->
  <div id="pane-sql_definitions" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="sqlQ" type="text" placeholder="Search SQL ID or owner…" style="width:260px;" onkeydown="if(event.key==='Enter')runCompare('sql_definitions')">
      <button onclick="runCompare('sql_definitions')">Compare</button>
      <span class="spinner" id="spin-sql_definitions">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-sql_definitions"></div>
  </div>

  <!-- Portals tab -->
  <div id="pane-portals" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="portalQ" type="text" placeholder="Search portal object name or label…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('portals')">
      <button onclick="runCompare('portals')">Compare Catalog</button>
      <span class="spinner" id="spin-portals">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-portals"></div>
    <hr style="border-color:#1a2a3a;margin:18px 0">
    <div style="font-size:11px;color:#8ab;margin-bottom:8px;font-weight:bold;letter-spacing:.05em;">DEEP OBJECT COMPARISON</div>
    <div class="ctrl">
      <input id="portalObjName" type="text" placeholder="Portal object name (e.g. PORTAL_GROUPLETS)…" style="width:340px;" onkeydown="if(event.key==='Enter')runPortalObjectCompare()">
      <button onclick="runPortalObjectCompare()">Deep Compare</button>
      <span class="spinner" id="spin-portal-obj">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-portal-obj"></div>
  </div>

  <!-- PS Queries tab -->
  <div id="pane-queries" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="queryQ" type="text" placeholder="Search public PS Query name or description…" style="width:300px;" onkeydown="if(event.key==='Enter')runCompare('queries')">
      <button onclick="runCompare('queries')">Compare</button>
      <span class="spinner" id="spin-queries">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-queries"></div>
  </div>

  <!-- Graph tab -->
  <div id="pane-graph" class="pane" style="display:none;">
    <div class="ctrl">
      <input id="graphTypes" type="text" placeholder="Node types, e.g. record,component,service_operation" style="width:360px;" onkeydown="if(event.key==='Enter')runGraphCompare()">
      <button onclick="runGraphCompare()">Compare Graph Snapshots</button>
      <a class="obj-link" href="/admin/graphdb" target="_blank">Open Graph Admin ↗</a>
      <span class="spinner" id="spin-graph">&#9679;&#9679;&#9679;</span>
    </div>
    <div id="res-graph"></div>
  </div>

</div><!-- .content -->
</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
const TABS = ['records','fields','components','permissions','ae','roles','peoplecode','sql_definitions','portals','queries','graph'];
let currentTab = 'records';

function env1() { return $('env1Sel').value || 'HCM'; }
function env2() { return $('env2Sel').value || 'FSCM'; }

function esc(s) {
  if (s == null) return '—';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path) {
  const r = await fetch(path);
  return r.json().catch(() => ({}));
}

function switchTab(name) {
  currentTab = name;
  TABS.forEach(t => {
    $(`pane-${t}`).style.display = t === name ? 'block' : 'none';
  });
  document.querySelectorAll('.tab').forEach((el, i) => {
    el.classList.toggle('on', TABS[i] === name);
  });
}

// ─── Summary sidebar ──────────────────────────────────────────────────────────
async function loadSummary() {
  $('summaryTable').innerHTML = '<span class="empty">Loading…</span>';
  const d = await api(`/api/envcompare/summary?env1=${env1()}&env2=${env2()}`);
  if (!d.counts) { $('summaryTable').innerHTML = '<div class="err-msg">Error loading summary.</div>'; return; }

  let h = `<table>
    <thead><tr><th>Type</th><th style="text-align:right">${esc(env1())}</th><th style="text-align:right">${esc(env2())}</th><th style="text-align:right">Δ</th></tr></thead>
    <tbody>`;
  d.counts.forEach(row => {
    const delta = row.delta;
    const dcls = delta === 0 ? 'color:#00cc66' : (delta > 0 ? 'color:#ff9900' : 'color:#55aaff');
    const dsign = delta > 0 ? `+${delta}` : (delta < 0 ? String(delta) : '=');
    h += `<tr>
      <td style="font-size:10px;">${esc(row.type)}</td>
      <td style="text-align:right;font-family:monospace;">${row.env1_count != null ? row.env1_count : '—'}</td>
      <td style="text-align:right;font-family:monospace;">${row.env2_count != null ? row.env2_count : '—'}</td>
      <td style="text-align:right;font-family:monospace;${dcls}">${delta != null ? dsign : '—'}</td>
    </tr>`;
  });
  h += '</tbody></table>';
  (d.warnings || []).forEach(w => { h += `<div class="warn-msg" style="margin-top:4px;">${esc(w.message||w)}</div>`; });
  $('summaryTable').innerHTML = h;
}

// ─── Generic compare (records / components / permissions / ae / roles) ────────
const Q_IDS = {
  records: 'recQ', components: 'compQ', permissions: 'permQ', ae: 'aeQ', roles: 'roleQ',
  peoplecode: 'pcQ', sql_definitions: 'sqlQ', portals: 'portalQ', queries: 'queryQ',
};

async function runCompare(type) {
  const qId = Q_IDS[type];
  const q = qId ? $(qId).value : '';
  const spinId = `spin-${type}`;
  $(spinId).classList.add('on');
  $(`res-${type}`).innerHTML = '';

  const url = `/api/envcompare/${type}?env1=${env1()}&env2=${env2()}&q=${encodeURIComponent(q)}&limit=500`;
  const d = await api(url);
  $(spinId).classList.remove('on');

  if (d.warnings && d.warnings.some(w => w.severity === 'error')) {
    let h = '';
    d.warnings.forEach(w => { h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message)}</div>`; });
    $(`res-${type}`).innerHTML = h;
    return;
  }

  renderDiff(`res-${type}`, d, type);
}

async function runFieldCompare() {
  const rec = $('fieldRec').value.trim().toUpperCase();
  if (!rec) { $('res-fields').innerHTML = '<div class="warn-msg">Enter a record name.</div>'; return; }
  $('spin-fields').classList.add('on');
  $('res-fields').innerHTML = '';

  const d = await api(`/api/envcompare/fields?env1=${env1()}&env2=${env2()}&record=${encodeURIComponent(rec)}`);
  $('spin-fields').classList.remove('on');

  if (d.warnings && d.warnings.some(w => w.severity === 'error')) {
    let h = '';
    d.warnings.forEach(w => { h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message)}</div>`; });
    $('res-fields').innerHTML = h;
    return;
  }

  renderDiff('res-fields', d, 'fields');
}

async function runGraphCompare() {
  $('spin-graph').classList.add('on');
  $('res-graph').innerHTML = '';
  const types = $('graphTypes').value.trim();
  const d = await api(`/api/envcompare/graph?env1=${env1()}&env2=${env2()}&node_types=${encodeURIComponent(types)}&limit=250`);
  $('spin-graph').classList.remove('on');
  renderGraphDiff(d);
}

async function runPortalObjectCompare() {
  const name = ($('portalObjName').value || '').trim().toUpperCase();
  if (!name) return;
  $('spin-portal-obj').classList.add('on');
  $('res-portal-obj').innerHTML = '';
  try {
    const d = await api(`/api/envcompare/portal-object?env1=${env1()}&env2=${env2()}&name=${encodeURIComponent(name)}`);
    $('spin-portal-obj').classList.remove('on');
    renderPortalObjectDiff(d);
  } catch(e) {
    $('spin-portal-obj').classList.remove('on');
    $('res-portal-obj').innerHTML = `<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderPortalObjectDiff(d) {
  const e1 = d.env1, e2 = d.env2;
  const sum = d.summary || {};
  let h = '';
  (d.warnings || []).forEach(w => {
    h += `<div class="warn-msg">${esc(w.message||String(w))}</div>`;
  });
  // Existence
  const ex1 = d.exists_in_env1, ex2 = d.exists_in_env2;
  const lu1 = (d.last_updated||{})[e1] || '—';
  const lu2 = (d.last_updated||{})[e2] || '—';
  h += `<div class="stat-grid">
    ${sBox(sum.definition_changes||0, 'Definition Changes', sum.definition_changes?'n-changed':'n-same')}
    ${sBox(sum.children_changes||0, 'Children Changes', sum.children_changes?'n-changed':'n-same')}
    ${sBox(sum.permissions_changes||0, 'Permission Changes', sum.permissions_changes?'n-changed':'n-same')}
  </div>`;
  h += `<table><thead><tr><th>Attribute</th><th>${esc(e1)}</th><th>${esc(e2)}</th></tr></thead><tbody>
    <tr><td>Exists</td><td>${ex1?'✓':'✗'}</td><td>${ex2?'✓':'✗'}</td></tr>
    <tr><td>Last Updated</td><td class="mono">${esc(lu1)}</td><td class="mono">${esc(lu2)}</td></tr>
  </tbody></table>`;
  if ((d.definition_diffs||[]).length) {
    const rows = d.definition_diffs.map(df =>
      `<tr><td class="mono">${esc(df.field)}</td>
       <td class="diff-v1 mono">${esc(df[e1]||'—')}</td>
       <td class="diff-v2 mono">${esc(df[e2]||'—')}</td></tr>`
    ).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">Definition Differences (${d.definition_diffs.length})</span>`,
      rows, ['Field', e1, e2], 'pod-defn', true
    );
  }
  if ((d.children_diffs||[]).length) {
    const rows = d.children_diffs.map(cd => {
      const cls = cd.status.startsWith('only_in_'+e1)?'chip-del':cd.status.startsWith('only_in_'+e2)?'chip-add':'chip-chg';
      const lbl = cd.portal_label || cd[e1] || cd[e2] || '';
      const link = `<a href="/admin/object/portal_registry/${esc(cd.portal_objname)}" target="_blank" style="color:#00e5ff44;font-size:9px;">↗</a>`;
      return `<tr><td class="mono">${esc(cd.portal_objname)} ${link}</td>
        <td>${esc(lbl)}</td>
        <td><span class="chip ${cls}">${esc(cd.status.replace(/_/g,' '))}</span></td></tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip ${d.children_diffs.length?'chip-chg':'chip-add'}">Children Differences (${d.children_diffs.length})</span>`,
      rows, ['Object Name', 'Label', 'Status'], 'pod-children', true
    );
  }
  if ((d.permissions_diffs||[]).length) {
    const rows = d.permissions_diffs.map(pd => {
      const cls = pd.status.startsWith('only_in_'+e1)?'chip-del':pd.status.startsWith('only_in_'+e2)?'chip-add':'chip-chg';
      return `<tr><td class="mono">${esc(pd.classid)}</td>
        <td>${esc(pd[e1]||'—')}</td><td>${esc(pd[e2]||'—')}</td>
        <td><span class="chip ${cls}">${esc(pd.status.replace(/_/g,' '))}</span></td></tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">Permission Differences (${d.permissions_diffs.length})</span>`,
      rows, ['Permission List', e1, e2, 'Status'], 'pod-perms', true
    );
  }
  if (sum.total_changes === 0) {
    h += `<div style="color:#00aa66;padding:12px;font-size:12px;">&#10003; Identical in both environments.</div>`;
  }
  $('res-portal-obj').innerHTML = h;
}

// ─── PeopleCode Deep Source Diff ──────────────────────────────────────────────
async function runPcSourceDiff() {
  const ref = ($('pcRefInput').value || '').trim();
  if (!ref) return;
  $('spin-pc-diff').classList.add('on');
  $('res-pc-diff').innerHTML = '';
  try {
    const d = await api(`/api/envcompare/peoplecode-source?env1=${env1()}&env2=${env2()}&ref=${encodeURIComponent(ref)}`);
    $('spin-pc-diff').classList.remove('on');
    renderPcSourceDiff(d);
  } catch(e) {
    $('spin-pc-diff').classList.remove('on');
    $('res-pc-diff').innerHTML = `<div class="err-msg">${esc(String(e))}</div>`;
  }
}

function renderPcSourceDiff(d) {
  let h = '';
  // stat boxes
  const ex1 = d.exists_in_env1, ex2 = d.exists_in_env2;
  h += `<div style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0">`;
  h += `<div class="stat-box"><div class="stat-n">${d.line_count_env1}</div><div class="stat-l">${esc(d.env1)} lines</div></div>`;
  h += `<div class="stat-box"><div class="stat-n">${d.line_count_env2}</div><div class="stat-l">${esc(d.env2)} lines</div></div>`;
  if (d.identical) {
    h += `<div class="stat-box" style="border-color:#00cc6644"><div class="stat-n" style="color:#00cc66">&#x2714;</div><div class="stat-l">Identical</div></div>`;
  } else {
    h += `<div class="stat-box" style="border-color:#00aaff44"><div class="stat-n" style="color:#00aaff">+${d.added_lines}</div><div class="stat-l">Added</div></div>`;
    h += `<div class="stat-box" style="border-color:#ff444444"><div class="stat-n" style="color:#ff4444">-${d.removed_lines}</div><div class="stat-l">Removed</div></div>`;
  }
  if (!ex1) h += `<div class="stat-box" style="border-color:#ff440044"><div class="stat-n" style="color:#ff4444">&#x2715;</div><div class="stat-l">Not in ${esc(d.env1)}</div></div>`;
  if (!ex2) h += `<div class="stat-box" style="border-color:#ff440044"><div class="stat-n" style="color:#ff4444">&#x2715;</div><div class="stat-l">Not in ${esc(d.env2)}</div></div>`;
  h += `</div>`;

  // warnings
  (d.warnings||[]).forEach(w => { h += `<div class="warn-msg">&#9888; ${esc(w.message||String(w))}</div>`; });

  if (d.identical) {
    h += `<div style="color:#00cc66;font-size:12px;margin:10px 0">Source is identical in both environments.</div>`;
    $('res-pc-diff').innerHTML = h;
    return;
  }

  if (!d.diff) {
    $('res-pc-diff').innerHTML = h;
    return;
  }

  // Unified diff rendered with line-level coloring
  h += `<div style="font-size:10px;font-family:monospace;background:#050e16;border:1px solid #1a2a3a;padding:10px;margin-top:8px;overflow-x:auto;max-height:600px;overflow-y:auto;white-space:pre;">`;
  d.diff.split('\n').forEach(line => {
    let col = '#9ab', bg = 'transparent';
    if (line.startsWith('+++') || line.startsWith('---')) { col = '#668'; bg = '#0a1520'; }
    else if (line.startsWith('@@'))  { col = '#00aaff'; bg = '#001828'; }
    else if (line.startsWith('+'))   { col = '#00cc66'; bg = '#002210'; }
    else if (line.startsWith('-'))   { col = '#ff4444'; bg = '#200808'; }
    else { col = '#566'; }
    h += `<div style="color:${col};background:${bg};padding:0 4px;min-height:14px">${esc(line) || '&nbsp;'}</div>`;
  });
  h += `</div>`;
  h += `<div style="font-size:10px;color:#334;margin-top:6px">Reference: ${esc(d.reference)} &nbsp;·&nbsp; Source: SYSADM.PSPCMTXT</div>`;
  $('res-pc-diff').innerHTML = h;
}

// ─── Diff renderer ────────────────────────────────────────────────────────────
function explorerLink(type, name) {
  const map = {
    records:     `/admin/record/${encodeURIComponent(name)}`,
    roles:       `/admin/role/${encodeURIComponent(name)}`,
    permissions: `/admin/object/permissionlist/${encodeURIComponent(name)}`,
    queries:     `/admin/object/query/${encodeURIComponent(name)}`,
  };
  if (!map[type]) return '';
  return ` <a href="${map[type]}" target="_blank" style="font-size:9px;color:#00e5ff44;text-decoration:none;" title="Open in Explorer">↗</a>`;
}

function renderDiff(targetId, d, type) {
  const only1 = d.only_in_env1 || [];
  const only2 = d.only_in_env2 || [];
  const changed = d.changed || [];
  const identical = d.identical_count || 0;
  const total = only1.length + only2.length + changed.length + identical;
  const sectionPrefix = targetId.replace(/[^a-zA-Z0-9_-]/g, '_');
  const sectionId = key => `${sectionPrefix}-${key}`;

  const nameKey = nameCol(type);

  let h = '';

  // Warnings.
  (d.warnings || []).forEach(w => {
    h += `<div class="${w.severity==='error'?'err-msg':'warn-msg'}">${esc(w.message||w)}</div>`;
  });

  // Stat summary.
  h += `<div class="stat-grid">
    ${sBox(only1.length, 'Only in ' + esc(env1()), 'n-only1', sectionId('only1'))}
    ${sBox(changed.length, 'Changed', 'n-changed', sectionId('changed'))}
    ${sBox(only2.length, 'Only in ' + esc(env2()), 'n-only2', sectionId('only2'))}
    ${sBox(identical, 'Identical', 'n-same', sectionId('same'))}
  </div>`;

  // Only in env1.
  if (only1.length) {
    h += collapsibleSection(
      `<span class="chip chip-del">&#8722; Only in ${esc(env1())} (${only1.length})</span>`,
      only1.map(r => `<tr><td class="mono">${esc(r[nameKey])}${explorerLink(type, r[nameKey])}</td>${metaCells(r, type)}</tr>`).join(''),
      metaHeaders(type), sectionId('only1'), true
    );
  }

  // Changed.
  if (changed.length) {
    const rows = changed.map(c => {
      const diffs = c.diffs.map(df =>
        `<div class="diff-row"><span class="diff-col">${esc(df.col)}</span>&nbsp;
          <span class="diff-v1">${esc(df.env1)}</span>
          <span style="color:#334;"> → </span>
          <span class="diff-v2">${esc(df.env2)}</span></div>`
      ).join('');
      return `<tr onclick="toggleDetail(this)" style="cursor:pointer;">
        <td class="mono">${esc(c.name)}${explorerLink(type, c.name)}</td>
        <td colspan="99"><span style="color:#ffdd55;font-size:10px;">▶ ${c.diffs.length} diff${c.diffs.length>1?'s':''}</span>
          <div class="detail" style="display:none;margin-top:4px;">${diffs}</div>
        </td>
      </tr>`;
    }).join('');
    h += collapsibleSection(
      `<span class="chip chip-chg">&#9650; Changed (${changed.length})</span>`,
      rows, ['Name','Differences'], sectionId('changed'), true
    );
  }

  // Only in env2.
  if (only2.length) {
    h += collapsibleSection(
      `<span class="chip chip-add">&#43; Only in ${esc(env2())} (${only2.length})</span>`,
      only2.map(r => `<tr><td class="mono">${esc(r[nameKey])}${explorerLink(type, r[nameKey])}</td>${metaCells(r, type)}</tr>`).join(''),
      metaHeaders(type), sectionId('only2'), true
    );
  }

  if (!h.includes('<tr>') && !h.includes('warn') && !h.includes('err')) {
    h += `<div class="empty" style="padding:16px;">No results. Try a different search filter.</div>`;
  } else if (total === identical && identical > 0) {
    h += `<div class="card" style="color:#00cc66;font-size:12px;">&#10003; All ${identical} objects are identical across both environments.</div>`;
  }

  $(targetId).innerHTML = h;
}

function renderGraphDiff(d) {
  const s = d.summary || {};
  let h = '';

  (d.warnings || []).forEach(w => {
    h += `<div class="warn-msg">${esc(w.message || w)}
      <div style="margin-top:4px;">
        <a class="obj-link" href="/api/graph/build?env=${encodeURIComponent(env1())}&limit=50&persist=true" target="_blank">Build ${esc(env1())} graph</a>
        &nbsp;·&nbsp;
        <a class="obj-link" href="/api/graph/build?env=${encodeURIComponent(env2())}&limit=50&persist=true" target="_blank">Build ${esc(env2())} graph</a>
      </div>
    </div>`;
  });

  h += `<div class="card">
    <div style="font-size:11px;color:#667;margin-bottom:8px;">
      Snapshot: ${esc(d.snapshot?.env1_built_at || 'not built')} ↔ ${esc(d.snapshot?.env2_built_at || 'not built')}
    </div>
    <div class="stat-grid">
      ${sBox(s.only_in_env1_nodes || 0, 'Nodes only in ' + esc(env1()), 'n-only1')}
      ${sBox(s.changed_nodes || 0, 'Changed Nodes', 'n-changed')}
      ${sBox(s.only_in_env2_nodes || 0, 'Nodes only in ' + esc(env2()), 'n-only2')}
      ${sBox(s.only_in_env1_edges || 0, 'Edges only in ' + esc(env1()), 'n-only1')}
      ${sBox(s.changed_edges || 0, 'Changed Edges', 'n-changed')}
      ${sBox(s.only_in_env2_edges || 0, 'Edges only in ' + esc(env2()), 'n-only2')}
    </div>
  </div>`;

  h += graphNodeSection(`Only in ${esc(env1())} Nodes`, d.only_in_env1_nodes || [], 'g-only1');
  h += graphChangedNodeSection(d.changed_nodes || [], 'g-changed');
  h += graphNodeSection(`Only in ${esc(env2())} Nodes`, d.only_in_env2_nodes || [], 'g-only2');
  h += graphEdgeSection(`Only in ${esc(env1())} Edges`, d.only_in_env1_edges || [], 'g-edge1');
  h += graphEdgeSection(`Changed Edges`, d.changed_edges || [], 'g-edge-changed', true);
  h += graphEdgeSection(`Only in ${esc(env2())} Edges`, d.only_in_env2_edges || [], 'g-edge2');

  $('res-graph').innerHTML = h;
}

function graphNodeSection(title, nodes, id) {
  if (!nodes.length) return '';
  const rows = nodes.map(n => `<tr>
    <td class="mono"><a class="obj-link" href="${esc(n.canonical_url || '#')}" target="_blank">${esc(n.id)}</a></td>
    <td>${esc(n.type)}</td>
    <td>${esc(n.display_name || n.name)}</td>
  </tr>`).join('');
  return collapsibleSection(`<span class="chip chip-del">${title} (${nodes.length})</span>`, rows, ['ID','Type','Name'], id, false);
}

function graphChangedNodeSection(items, id) {
  if (!items.length) return '';
  const rows = items.map(item => {
    const diffs = (item.diffs || []).map(df => `<div class="diff-row">
      <span class="diff-col">${esc(df.field)}</span>
      <span class="diff-v1">${esc(shortJson(df.env1))}</span>
      <span style="color:#334;"> → </span>
      <span class="diff-v2">${esc(shortJson(df.env2))}</span>
    </div>`).join('');
    return `<tr onclick="toggleDetail(this)" style="cursor:pointer;">
      <td class="mono"><a class="obj-link" href="${esc(item.env1?.canonical_url || item.env2?.canonical_url || '#')}" target="_blank">${esc(item.id)}</a></td>
      <td>${esc(item.env1?.type || item.env2?.type)}</td>
      <td><span style="color:#ffdd55;">▶ ${item.diffs?.length || 0} diff(s)</span><div class="detail" style="display:none;margin-top:4px;">${diffs}</div></td>
    </tr>`;
  }).join('');
  return collapsibleSection(`<span class="chip chip-chg">Changed Nodes (${items.length})</span>`, rows, ['ID','Type','Differences'], id, false);
}

function graphEdgeSection(title, edges, id, changed=false) {
  if (!edges.length) return '';
  const rows = edges.map(item => {
    const e = changed ? (item.env1 || item.env2 || {}) : item;
    return `<tr>
      <td class="mono">${esc(e.source || item.id)}</td>
      <td>${esc(e.type || '')}</td>
      <td class="mono">${esc(e.target || '')}</td>
    </tr>`;
  }).join('');
  return collapsibleSection(`<span class="chip ${changed ? 'chip-chg' : 'chip-del'}">${title} (${edges.length})</span>`, rows, ['Source','Type','Target'], id, false);
}

function shortJson(value) {
  if (value == null) return '';
  const s = typeof value === 'string' ? value : JSON.stringify(value);
  return s.length > 180 ? s.substring(0, 180) + '…' : s;
}

function collapsibleSection(header, rows, headers, id, open) {
  const thHtml = Array.isArray(headers)
    ? headers.map(h => `<th>${esc(h)}</th>`).join('')
    : '';
  return `<div class="card" style="margin-bottom:8px;">
    <div class="section-head" data-section-id="sec-${id}" role="button" tabindex="0" aria-expanded="${open ? 'true' : 'false'}">
      ${header}
      <span class="toggle">${open ? '▾' : '▸'}</span>
    </div>
    <div id="sec-${id}" style="${open ? '' : 'display:none'}">
      <table><thead><tr>${thHtml}</tr></thead><tbody>${rows}</tbody></table>
    </div>
  </div>`;
}

function toggleSection(id, head) {
  const el = $(id);
  if (!el) return;
  const resolvedHead = head || document.querySelector(`[data-section-id="${id}"]`);
  const tog = resolvedHead ? resolvedHead.querySelector('.toggle') : null;
  const hidden = getComputedStyle(el).display === 'none';
  el.style.display = hidden ? 'block' : 'none';
  if (tog) tog.textContent = hidden ? '▾' : '▸';
  if (resolvedHead) resolvedHead.setAttribute('aria-expanded', hidden ? 'true' : 'false');
}

function toggleSectionById(sectionKey) {
  const id = sectionKey && sectionKey.startsWith('sec-') ? sectionKey : `sec-${sectionKey}`;
  toggleSection(id);
}

function toggleDetail(tr) {
  const detail = tr.querySelector('.detail');
  if (!detail) return;
  const arrow = tr.querySelector('span[style]');
  if (detail.style.display === 'none') {
    detail.style.display = '';
    if (arrow) arrow.textContent = arrow.textContent.replace('▶','▼');
  } else {
    detail.style.display = 'none';
    if (arrow) arrow.textContent = arrow.textContent.replace('▼','▶');
  }
}

document.addEventListener('click', event => {
  const head = event.target.closest('.section-head[data-section-id]');
  if (!head || event.target.closest('a,button,input,select,textarea')) return;
  toggleSection(head.dataset.sectionId, head);
});

document.addEventListener('keydown', event => {
  if (event.key !== 'Enter' && event.key !== ' ') return;
  const head = event.target.closest('.section-head[data-section-id]');
  if (!head) return;
  event.preventDefault();
  toggleSection(head.dataset.sectionId, head);
});

function sBox(n, label, cls, targetSectionId) {
  const sectionId = targetSectionId || '';
  const click = sectionId ? ` onclick="toggleSectionById('${sectionId}')"` : '';
  return `<div class="stat-box" title="${sectionId ? 'Click to expand/collapse section' : ''}"${click}>
    <div class="stat-num ${cls}">${n}</div>
    <div class="stat-lbl">${label}</div>
  </div>`;
}

// ─── Per-type helpers ─────────────────────────────────────────────────────────
function nameCol(type) {
  const map = {
    records: 'recname',
    fields: 'fieldname',
    components: 'pnlgrpname',
    permissions: 'classid',
    ae: 'ae_applid',
    roles: 'rolename',
    queries: 'qryname',
  };
  return map[type] || 'name';
}

function metaHeaders(type) {
  const map = {
    records:     ['Name', 'Type', 'Fields', 'Description'],
    fields:      ['Name', 'Seq', 'Type', 'Length'],
    components:  ['Name', 'Search Rec', 'Add Rec', 'Actions'],
    permissions: ['Name', 'Description'],
    ae:          ['Name', 'Status', 'Description'],
    roles:       ['Name', 'Description'],
    queries:     ['Name', 'Type', 'Folder', 'Disabled', 'Valid'],
  };
  return map[type] || ['Name'];
}

function metaCells(r, type) {
  switch(type) {
    case 'records':
      return `<td>${esc(r.rectype_label||r.rectype)}</td><td>${esc(r.field_count)}</td><td>${esc(r.recdescr)}</td>`;
    case 'fields':
      return `<td>${esc(r.fieldnum)}</td><td>${esc(r.fieldtype_label||r.fieldtype)}</td><td>${esc(r.fieldlen)}</td>`;
    case 'components':
      return `<td class="mono">${esc(r.searchrecname)}</td><td class="mono">${esc(r.addrecname)}</td><td>${esc(r.actions)}</td>`;
    case 'permissions':
      return `<td>${esc(r.descr)}</td>`;
    case 'ae':
      return `<td>${esc(r.ae_status)}</td><td>${esc(r.descr)}</td>`;
    case 'roles':
      return `<td>${esc(r.descr)}</td>`;
    case 'queries':
      return `<td>${esc(r.qrytype)}</td><td>${esc(r.qryfolder)}</td><td>${esc(r.qrydisabled)}</td><td>${esc(r.qryvalid)}</td>`;
    default:
      return '';
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  const d = await api('/api/envcompare/config');
  const envs = d.envs || ['HCM', 'FSCM'];
  $('env1Sel').innerHTML = envs.map((e,i) => `<option value="${e}"${i===0?' selected':''}>${e}</option>`).join('');
  $('env2Sel').innerHTML = envs.map((e,i) => `<option value="${e}"${i===1||envs.length===1?' selected':''}>${e}</option>`).join('');
  // If only one env, pick it for both (will show all-identical).
  loadSummary();
})();
</script>""")


@router.get("/tracing", response_class=HTMLResponse)
def admin_tracing():
    return _shell("Transaction Tracing", "runtime", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:230px;border-right:1px solid #00e5ff22;display:flex;flex-direction:column;overflow:hidden;}
.sidebar-body{overflow-y:auto;flex:1;padding:8px;}
.content{flex:1;overflow:auto;padding:14px;}
select,input[type=text],input[type=number]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button:disabled{opacity:.4;cursor:default;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;}
.ctrl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:10px;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;}
.stat-grid{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;}
.stat-box{border:1px solid #00e5ff22;padding:6px 12px;min-width:90px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:18px;font-weight:bold;color:#00e5ff;}
.stat-lbl{font-size:9px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.s-err{color:#ff4444;}
.s-warn{color:#ffaa00;}
.s-proc{color:#00e5ff;}
.s-sess{color:#00cc66;}
.s-ib{color:#ffaa00;}
/* Timeline */
.timeline{position:relative;padding-left:28px;}
.timeline::before{content:'';position:absolute;left:10px;top:0;bottom:0;width:1px;background:#0a2030;}
.tl-event{position:relative;margin-bottom:6px;}
.tl-dot{position:absolute;left:-22px;top:6px;width:10px;height:10px;border-radius:50%;border:2px solid;}
.tl-card{border:1px solid #0a2030;padding:7px 10px;background:#06121a;cursor:pointer;transition:border-color .1s;}
.tl-card:hover{border-color:#00e5ff33;}
.tl-card.open{border-color:#00e5ff44;background:#081820;}
.tl-type{font-size:9px;text-transform:uppercase;letter-spacing:1px;font-weight:bold;margin-bottom:2px;}
.tl-title{font-size:12px;color:#d7faff;}
.tl-sub{font-size:10px;color:#556;margin-top:1px;}
.tl-ts{font-size:10px;color:#334;float:right;font-family:monospace;}
.tl-detail{display:none;margin-top:6px;border-top:1px solid #0a2030;padding-top:6px;}
.tl-card.open .tl-detail{display:block;}
.kv-grid{display:grid;grid-template-columns:130px 1fr;gap:1px 10px;font-size:10px;}
.kv-key{color:#556;text-transform:uppercase;letter-spacing:1px;padding:2px 0;}
.kv-val{padding:2px 0;font-family:monospace;word-break:break-all;}
.sql-block{background:#040d14;border:1px solid #0a2030;padding:6px 8px;font-family:monospace;font-size:10px;color:#9ab;margin-top:4px;white-space:pre-wrap;word-break:break-all;max-height:150px;overflow:auto;}
.empty{color:#445;font-style:italic;font-size:12px;padding:10px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-err{background:#3a0000;border:1px solid #ff4444;color:#ff4444;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.side-item{padding:6px 8px;cursor:pointer;border-bottom:1px solid #081520;font-size:11px;}
.side-item:hover{background:#0b2030;}
.side-item.active{background:#0b2030;border-left:2px solid #00e5ff;}
.side-badge{float:right;font-size:9px;padding:1px 5px;border-radius:2px;background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.spin{display:none;color:#00e5ff;font-size:11px;margin-left:6px;}
.spin.on{display:inline;}
a.obj-link{color:#00e5ff;text-decoration:none;font-size:10px;}
a.obj-link:hover{text-decoration:underline;}
#opridInput{width:160px;}
#hoursInput{width:55px;}
#opridSuggest{position:absolute;z-index:100;background:#0b1b24;border:1px solid #00e5ff44;max-height:200px;overflow-y:auto;width:200px;display:none;}
#opridSuggest .sug-item{padding:5px 10px;cursor:pointer;font-size:11px;}
#opridSuggest .sug-item:hover{background:#0b2030;}
.suggest-wrap{position:relative;display:inline-block;}
</style>

<div class="ds-toolbar">
  <span class="lbl">Env</span>
  <select id="envSel" style="width:70px;"></select>
  <span class="lbl">DB</span>
  <select id="dbSel" style="width:80px;"></select>
  <span class="lbl">OPRID</span>
  <div class="suggest-wrap" style="position:relative;">
    <input id="opridInput" type="text" placeholder="JSMITH" autocomplete="off"
           oninput="suggestOprids()" onkeydown="handleKey(event)">
    <div id="opridSuggest"></div>
  </div>
  <span class="lbl">Hours</span>
  <input id="hoursInput" type="number" value="24" min="1" max="720" style="width:60px;">
  <button id="traceBtn" onclick="runTrace()">Trace</button>
  <span class="spin" id="spin">&#9679;&#9679;&#9679;</span>
</div>

<div class="main">

<!-- ═══════════════════════════════════════════════════════════ SIDEBAR -->
<div class="sidebar">
  <div style="padding:8px;border-bottom:1px solid #00e5ff11;">
    <h2 style="margin:0 0 6px;">Recent Activity</h2>
    <select id="sideEnvSel" style="width:100%;font-size:11px;" onchange="loadActive()"></select>
  </div>
  <div class="sidebar-body" id="activeList">
    <span class="empty">Loading…</span>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════ CONTENT AREA -->
<div class="content" id="contentArea">
  <div id="placeholder" style="padding:20px 0;">
    <div style="color:#334;font-size:13px;margin-bottom:8px;">Enter an OPRID above to trace their activity.</div>
    <div style="color:#223;font-size:11px;line-height:1.8;">
      The trace will correlate:<br>
      &nbsp;&#9654; Login / logout history (PSACCESSLOG)<br>
      &nbsp;&#9881; Process Scheduler runs (PSPRCSRQST)<br>
      &nbsp;&#9670; Active Oracle sessions (V$SESSION · CLIENT_IDENTIFIER)<br>
      &nbsp;&#8644; Integration Broker transactions (PSAPMSGPUBHDR · when accessible)
    </div>
  </div>
</div>

</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
let suggestTimer = null;
let currentOprid = null;

function env()   { return $('envSel').value   || 'HCM'; }
function db()    { return $('dbSel').value    || ''; }
function hours() { return parseInt($('hoursInput').value) || 24; }

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path) {
  const r = await fetch(path);
  return r.json().catch(() => ({}));
}

// ─── Autocomplete ──────────────────────────────────────────────────────────
function suggestOprids() {
  clearTimeout(suggestTimer);
  const q = $('opridInput').value.trim();
  if (!q) { $('opridSuggest').style.display = 'none'; return; }
  suggestTimer = setTimeout(async () => {
    const d = await api(`/api/tracing/operators?env=${env()}&q=${encodeURIComponent(q)}`);
    const items = d.items || [];
    if (!items.length) { $('opridSuggest').style.display = 'none'; return; }
    $('opridSuggest').innerHTML = items.map(it =>
      `<div class="sug-item" onclick="selectOprid('${esc(it.oprid)}')">
        <strong>${esc(it.oprid)}</strong>
        ${it.oprdefndesc ? `<span style="color:#556;"> — ${esc(it.oprdefndesc)}</span>` : ''}
        ${it.emailid ? `<br><span style="color:#334;font-size:10px;">${esc(it.emailid)}</span>` : ''}
      </div>`
    ).join('');
    $('opridSuggest').style.display = 'block';
  }, 200);
}

function selectOprid(oprid) {
  $('opridInput').value = oprid;
  $('opridSuggest').style.display = 'none';
  runTrace();
}

function handleKey(e) {
  if (e.key === 'Enter') { $('opridSuggest').style.display = 'none'; runTrace(); }
  if (e.key === 'Escape') $('opridSuggest').style.display = 'none';
}

document.addEventListener('click', e => {
  if (!e.target.closest('.suggest-wrap')) $('opridSuggest').style.display = 'none';
});

// ─── Recent active operators (sidebar) ────────────────────────────────────
async function loadActive() {
  const e = $('sideEnvSel').value || 'HCM';
  $('activeList').innerHTML = '<span class="empty">Loading…</span>';
  const d = await api(`/api/tracing/active?env=${e}&limit=30`);
  const items = d.items || [];
  if (!items.length) {
    $('activeList').innerHTML = '<span class="empty" style="padding:8px;">No recent activity.</span>';
    (d.warnings||[]).forEach(w => {
      $('activeList').innerHTML += `<div class="warn-msg">${esc(w.message||w)}</div>`;
    });
    return;
  }
  $('activeList').innerHTML = items.map(it => {
    const badge = it.is_active
      ? '<span class="side-badge" style="background:#002800;border-color:#00cc66;color:#00cc66;">ACTIVE</span>'
      : `<span class="side-badge">${it.session_count}</span>`;
    const sub = it.last_login ? it.last_login.replace('T',' ').substring(0,16) : '';
    return `<div class="side-item" onclick="quickTrace('${esc(it.oprid)}')">
      ${badge}
      <strong style="font-family:monospace;font-size:11px;">${esc(it.oprid)}</strong>
      <div style="font-size:10px;color:#334;">${sub}</div>
    </div>`;
  }).join('');
}

function quickTrace(oprid) {
  $('opridInput').value = oprid;
  document.querySelectorAll('.side-item').forEach(el => el.classList.remove('active'));
  event.currentTarget.classList.add('active');
  runTrace();
}

// ─── Main trace ────────────────────────────────────────────────────────────
async function runTrace() {
  const oprid = $('opridInput').value.trim();
  if (!oprid) return;
  currentOprid = oprid;
  $('spin').classList.add('on');
  $('traceBtn').disabled = true;
  $('contentArea').innerHTML = `<div style="color:#334;padding:10px;">Tracing ${esc(oprid)}…</div>`;

  let url = `/api/tracing/trace?env=${env()}&oprid=${encodeURIComponent(oprid)}&hours=${hours()}`;
  const dbv = db();
  if (dbv) url += `&db=${encodeURIComponent(dbv)}`;

  const d = await api(url);
  $('spin').classList.remove('on');
  $('traceBtn').disabled = false;

  renderTrace(d);
}

function renderTrace(d) {
  const oprid   = d.oprid || '?';
  const summary = d.summary || {};
  const events  = d.timeline || [];
  const warns   = d.warnings || [];

  let h = `<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;">
    <span style="font-family:monospace;font-size:15px;color:#00e5ff;">${esc(oprid)}</span>
    <span style="font-size:10px;color:#556;">last ${d.hours_back}h · ${esc(d.env)}</span>
  </div>`;

  // Warnings.
  warns.forEach(w => {
    if (w.severity === 'error') {
      h += `<div class="err-msg">${esc(w.message||w)}</div>`;
    } else {
      h += `<div class="warn-msg">${esc(w.message||w)}</div>`;
    }
  });

  // Summary stats.
  h += `<div class="stat-grid">
    ${sBox(summary.login_count, 'Logins', 's-sess')}
    ${sBox(summary.process_count, 'Processes', 's-proc')}
    ${sBox(summary.error_count, 'Errors', 's-err')}
    ${sBox(summary.oracle_count, 'Oracle Sessions', '')}
    ${sBox(summary.ib_count, 'IB Txns', 's-ib')}
  </div>`;

  if (!events.length) {
    h += `<div class="empty">No activity found for ${esc(oprid)} in the last ${d.hours_back} hours.</div>`;
    $('contentArea').innerHTML = h;
    return;
  }

  // Filter bar.
  h += `<div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;font-size:11px;">
    <button class="sec" style="font-size:10px;" onclick="filterEvents('all')">All</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('login')">Logins</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('process')">Processes</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('oracle')">Oracle</button>
    <button class="sec" style="font-size:10px;" onclick="filterEvents('ib')">IB</button>
    <button class="sec" style="font-size:10px;float:right;" onclick="expandAll()">Expand All</button>
    <button class="sec" style="font-size:10px;" onclick="collapseAll()">Collapse</button>
  </div>`;

  // Timeline.
  h += '<div class="timeline" id="timeline">';
  events.forEach((ev, i) => {
    const meta    = ev.meta || {};
    const color   = meta.color || '#556';
    const typeKey = ev.type || 'info';
    const tsStr   = (ev.ts || '').replace('T', ' ').substring(0, 19);
    const statusCls = ev.status === 'error' ? 'chip-err' : ev.status === 'warn' ? 'chip-warn' : ev.status === 'ok' ? 'chip-ok' : 'chip-info';

    h += `<div class="tl-event" data-type="${esc(typeKey)}">
      <div class="tl-dot" style="border-color:${color};background:${color}33;"></div>
      <div class="tl-card" onclick="toggleEvent(this)">
        <div>
          <span class="tl-ts">${esc(tsStr)}</span>
          <span class="tl-type" style="color:${color};">${esc(meta.label || typeKey)}</span>
        </div>
        <div class="tl-title">${esc(ev.title)}</div>
        ${ev.subtitle ? `<div class="tl-sub">${esc(ev.subtitle)}</div>` : ''}
        <div class="tl-detail">${buildDetail(ev)}</div>
      </div>
    </div>`;
  });
  h += '</div>';

  $('contentArea').innerHTML = h;
}

function buildDetail(ev) {
  const d = ev.detail || {};
  const type = ev.type;
  let h = '<div class="kv-grid">';

  if (type === 'login' || type === 'logout') {
    h += kv('OPRID', d.oprid) + kv('Login', d.logindttm) + kv('Logout', d.logoutdttm || '— (active)') + kv('DB', d.connectdbbname) + kv('Tools', d.toolsrel);
  } else if (type === 'process') {
    h += kv('Instance', d.prcsinstance) + kv('Type', d.prcstype) + kv('Program', d.prcsname)
       + kv('Run Control', d.runcntlid) + kv('Status', d.runstatus_label) + kv('Server', d.serverbatch)
       + kv('Start', d.begindttm) + kv('End', d.enddttm);
  } else if (type === 'oracle') {
    h += kv('SID/Serial', `${d.sid}/${d.serial_num}`) + kv('Username', d.username) + kv('Status', d.status)
       + kv('Program', d.program) + kv('Module', d.module) + kv('Action', d.action)
       + kv('Machine', d.machine) + kv('Logon', d.logon_time) + kv('Wait', `${d.seconds_in_wait || 0}s · ${d.event || ''}`)
       + kv('CLIENT_ID', d.client_identifier);
    if (d.sql_text) {
      h += `</div><div class="sql-block">${esc(d.sql_text)}</div><div class="kv-grid">`;
    }
  } else if (type === 'ib') {
    h += kv('Txn ID', d.ibtransactionid) + kv('Operation', d.ib_operationname) + kv('Queue', d.queuename)
       + kv('Pub Node', d.pubnode) + kv('Status', d.pubstatus) + kv('Created', d.createdttm);
  }

  h += '</div>';
  if ((ev.links || []).length) {
    h += '<div style="margin-top:4px;">';
    ev.links.forEach(l => { h += `<a class="obj-link" href="${esc(l.url)}">${esc(l.label)}</a>&nbsp; `; });
    h += '</div>';
  }
  return h;
}

function kv(label, val) {
  if (val == null || val === '') return '';
  return `<div class="kv-key">${esc(label)}</div><div class="kv-val">${esc(String(val))}</div>`;
}

function sBox(n, label, cls) {
  return `<div class="stat-box"><div class="stat-num ${cls}">${n != null ? n : 0}</div><div class="stat-lbl">${esc(label)}</div></div>`;
}

function toggleEvent(card) {
  card.classList.toggle('open');
}

function filterEvents(type) {
  document.querySelectorAll('.tl-event').forEach(el => {
    el.style.display = (type === 'all' || el.dataset.type === type) ? '' : 'none';
  });
}

function expandAll() {
  document.querySelectorAll('.tl-card').forEach(c => c.classList.add('open'));
}
function collapseAll() {
  document.querySelectorAll('.tl-card').forEach(c => c.classList.remove('open'));
}

// ─── Init ─────────────────────────────────────────────────────────────────
(async () => {
  const cfg = await api('/api/tracing/config');
  const envs = cfg.envs || ['HCM'];
  const dbs  = cfg.dbs  || [];
  $('envSel').innerHTML = envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('sideEnvSel').innerHTML = envs.map(e => `<option value="${e}">${e}</option>`).join('');
  $('dbSel').innerHTML = `<option value="">— (no Oracle)</option>` + dbs.map(d => `<option value="${d}">${d}</option>`).join('');
  if (dbs.length) $('dbSel').value = dbs[0];

  // Pre-fill from URL params: ?oprid=VP1&env=FSCM
  const params = new URLSearchParams(window.location.search);
  const opParam  = params.get('oprid');
  const envParam = params.get('env');
  if (envParam && envs.includes(envParam.toUpperCase())) {
    $('envSel').value = envParam.toUpperCase();
    $('sideEnvSel').value = envParam.toUpperCase();
  }
  if (opParam) {
    $('opridInput').value = opParam;
    runTrace();
  } else {
    loadActive();
  }
})();
</script>""")


@router.get("/record", response_class=HTMLResponse)
@router.get("/record/{recname}", response_class=HTMLResponse)
def admin_record(recname: str = None):
    return _shell("Record Explorer", "objects", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;display:flex;flex-direction:column;height:100vh;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:4px;margin:12px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;}
nav a:hover{text-decoration:underline;}
.topbar{padding:10px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:240px;border-right:1px solid #00e5ff22;display:flex;flex-direction:column;overflow:hidden;}
.search-bar{padding:8px;border-bottom:1px solid #00e5ff11;display:flex;gap:4px;}
.search-bar input{flex:1;min-width:0;}
.list-area{overflow-y:auto;flex:1;}
.content{flex:1;overflow:auto;padding:14px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
select:focus,input:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:4px 10px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button:hover{background:#33eeff;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
button.sec:hover{background:#00e5ff11;}
.tab-row{display:flex;gap:0;border-bottom:1px solid #00e5ff22;margin-bottom:10px;overflow-x:auto;}
.tab{padding:7px 12px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.list-item{padding:6px 10px;cursor:pointer;border-bottom:1px solid #0b1b24;font-size:11px;}
.list-item:hover{background:#0b2030;}
.list-item.active{background:#0b2030;border-left:2px solid #00e5ff;}
.item-name{font-family:monospace;color:#d7faff;}
.item-meta{font-size:10px;color:#445;margin-top:1px;}
.badge{display:inline-block;font-size:9px;padding:1px 5px;border-radius:2px;float:right;}
.bd-table{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.bd-view{background:#180030;border:1px solid #aa55ff;color:#aa55ff;}
.bd-work{background:#181800;border:1px solid #aaaa00;color:#aaaa00;}
.bd-sub{background:#002018;border:1px solid #00aaaa;color:#00aaaa;}
.bd-temp{background:#1a0a00;border:1px solid #ff8800;color:#ff8800;}
table{border-collapse:collapse;width:100%;font-size:11px;}
th{border-bottom:1px solid #00e5ff33;padding:4px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;white-space:nowrap;}
td{border-bottom:1px solid #0e2030;padding:4px 8px;vertical-align:top;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;font-size:11px;}
.empty{color:#445;font-style:italic;font-size:12px;padding:8px 0;}
.warn-msg{color:#ffaa00;font-size:11px;padding:3px 8px;background:#1a1000;border-left:2px solid #ffaa00;margin:2px 0;}
.err-msg{color:#ff6666;font-size:11px;padding:3px 8px;background:#1a0000;border-left:2px solid #ff4444;margin:2px 0;}
.card{border:1px solid #00e5ff22;padding:10px 14px;margin-bottom:10px;background:rgba(0,20,30,.5);}
.kv-grid{display:grid;grid-template-columns:150px 1fr;gap:2px 12px;font-size:11px;margin:8px 0;}
.kv-key{color:#667;text-transform:uppercase;font-size:10px;letter-spacing:1px;padding:3px 0;}
.kv-val{padding:3px 0;font-family:monospace;}
.stat-grid{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;}
.stat-box{border:1px solid #00e5ff22;padding:6px 12px;min-width:90px;text-align:center;background:rgba(0,20,30,.5);}
.stat-num{font-size:18px;font-weight:bold;color:#00e5ff;}
.stat-lbl{font-size:9px;color:#445;text-transform:uppercase;letter-spacing:1px;}
.chip{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10px;font-weight:bold;}
.chip-table{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.chip-view{background:#180030;border:1px solid #aa55ff;color:#aa55ff;}
.chip-work{background:#181800;border:1px solid #aaaa00;color:#aaaa00;}
.chip-sub{background:#002018;border:1px solid #00aaaa;color:#00aaaa;}
.chip-temp{background:#1a0a00;border:1px solid #ff8800;color:#ff8800;}
.key-badge{display:inline-block;font-size:9px;padding:1px 4px;border-radius:2px;margin-right:2px;}
.key-pk{background:#002818;border:1px solid #00aa66;color:#00aa66;}
.key-search{background:#281800;border:1px solid #aa7700;color:#aa7700;}
.key-dup{background:#001828;border:1px solid #0077aa;color:#0077aa;}
.code-block{background:#040d14;border:1px solid #0a2030;padding:8px;font-family:monospace;font-size:10px;color:#9ab;white-space:pre-wrap;word-break:break-all;max-height:300px;overflow:auto;margin:4px 0;}
a.obj-link{color:#00e5ff;text-decoration:none;font-family:monospace;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.spin{display:none;color:#00e5ff;font-size:11px;margin-left:6px;}
.spin.on{display:inline;}
.rec-header{font-size:16px;font-family:monospace;color:#00e5ff;margin-bottom:4px;}
</style>

<div class="main">

<!-- ═══════════════════════════════════════════════════════════ SIDEBAR -->
<div class="sidebar">
  <div class="search-bar">
    <input id="recQ" type="text" placeholder="Search records…" onkeydown="if(event.key==='Enter')searchRecords()">
    <button onclick="searchRecords()">Go</button>
  </div>
  <div class="list-area" id="recList">
    <span class="empty" style="padding:8px;">Search for a record above.</span>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════ CONTENT AREA -->
<div class="content" id="contentArea">
  <div style="color:#334;padding:10px 0;font-size:12px;">
    Search for a record, or navigate from the Object Explorer.<br><br>
    Examples: <span class="mono" onclick="loadRecord('PSRECDEFN')" style="cursor:pointer;color:#00e5ff;">PSRECDEFN</span> &nbsp;
    <span class="mono" onclick="loadRecord('PSOPRDEFN')" style="cursor:pointer;color:#00e5ff;">PSOPRDEFN</span> &nbsp;
    <span class="mono" onclick="loadRecord('PSROLEDEFN')" style="cursor:pointer;color:#00e5ff;">PSROLEDEFN</span>
  </div>
</div>

</div><!-- .main -->

<script>
const $ = id => document.getElementById(id);
let currentRec = null;

function env() { return $('envSel').value || 'HCM'; }

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function api(path) {
  const r = await fetch(path);
  return r.json().catch(() => ({}));
}

function clearRecord() { currentRec = null; }

// ─── Search ────────────────────────────────────────────────────────────────
async function searchRecords() {
  const q = $('recQ').value.trim();
  $('recList').innerHTML = '<span class="empty" style="padding:8px;">Searching…</span>';
  const d = await api(`/api/record/search?env=${env()}&q=${encodeURIComponent(q)}`);
  const items = d.items || [];
  if (!items.length) {
    $('recList').innerHTML = '<span class="empty" style="padding:8px;">No results.</span>';
    return;
  }
  $('recList').innerHTML = items.map(r => {
    const badge = recBadge(r.rectype_label || r.rectype);
    return `<div class="list-item" onclick="loadRecord('${esc(r.recname)}')">
      <span class="badge ${badge.cls}">${badge.text}</span>
      <span class="item-name">${esc(r.recname)}</span>
      <div class="item-meta">${esc(r.recdescr || '')}</div>
    </div>`;
  }).join('');
}

// ─── Record detail ─────────────────────────────────────────────────────────
async function loadRecord(recname) {
  currentRec = recname.toUpperCase();
  $('contentArea').innerHTML = `<div style="color:#334;padding:6px;">Loading ${esc(recname)}…</div>`;

  // Mark active in list.
  document.querySelectorAll('.list-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.list-item').forEach(el => {
    if (el.querySelector('.item-name')?.textContent === recname.toUpperCase())
      el.classList.add('active');
  });

  const d = await api(`/api/record/${encodeURIComponent(recname)}?env=${env()}`);
  const item = d.item;
  if (!item) {
    $('contentArea').innerHTML = `<div class="err-msg">Record not found: ${esc(recname)}</div>`;
    return;
  }

  const chip = recChip(item.rectype_label);
  const sqltbl = item.sqltablename && item.sqltablename.trim() ? item.sqltablename.trim() : null;

  let h = `
  <div class="rec-header">${esc(item.recname)} ${chip}</div>
  ${item.recdescr ? `<div style="color:#9ab;font-size:12px;margin-bottom:10px;">${esc(item.recdescr)}</div>` : ''}

  <div class="tab-row">
    <div class="tab on"   onclick="switchTab('overview')">Overview</div>
    <div class="tab"      onclick="switchTab('fields');loadTab('fields')">Fields</div>
    <div class="tab"      onclick="switchTab('keys');loadTab('keys')">Keys</div>
    <div class="tab"      onclick="switchTab('indexes');loadTab('indexes')">Indexes</div>
    <div class="tab"      onclick="switchTab('related');loadTab('related')">Related</div>
    <div class="tab"      onclick="switchTab('components');loadTab('components')">Components</div>
    <div class="tab"      onclick="switchTab('pages');loadTab('pages')">Pages</div>
    <div class="tab"      onclick="switchTab('ddl');loadTab('ddl')">DDL</div>
    <div class="tab"      onclick="switchTab('data');loadTab('data')">Data</div>
  </div>

  <!-- Overview tab -->
  <div id="pane-overview" class="pane on">
    <div class="card">
      <div class="kv-grid">
        ${kv('Record Name', item.recname)}
        ${kv('Type', item.rectype_label)}
        ${item.sqltablename && item.sqltablename.trim() ? kv('SQL Table Name', item.sqltablename.trim()) : ''}
        ${item.parentrecname && item.parentrecname.trim() ? kv('Parent Record', `<a class="obj-link" onclick="loadRecord('${esc(item.parentrecname.trim())}')">${esc(item.parentrecname.trim())}</a>`) : ''}
        ${kv('Field Count', item.fieldcount ?? '—')}
        ${kv('Key Count', item.keycount ?? '—')}
        ${item.setcntrlfld && item.setcntrlfld.trim() ? kv('SetID Control Field', item.setcntrlfld.trim()) : ''}
        ${kv('Owner', item.objectownerid)}
        ${kv('Last Updated', item.lastupddttm)}
        ${kv('Updated By', item.lastupdoprid)}
      </div>
    </div>
    <div id="overview-storage"></div>
    <div id="overview-children"></div>
  </div>

  <div id="pane-fields"     class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-keys"       class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-indexes"    class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-related"    class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-components" class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-pages"      class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-ddl"        class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-data"       class="pane"><span class="empty">Loading…</span></div>
  `;

  $('contentArea').innerHTML = h;

  // Eagerly load storage stats and children into the overview.
  loadStorageInto('overview-storage', recname);
  loadChildrenInto('overview-children', recname);
}

function switchTab(name) {
  const tabs = ['overview','fields','keys','indexes','related','components','pages','ddl','data'];
  tabs.forEach(t => {
    const p = $(`pane-${t}`); if (p) p.className = 'pane' + (t === name ? ' on' : '');
  });
  document.querySelectorAll('.tab').forEach((el, i) => {
    el.classList.toggle('on', tabs[i] === name);
  });
}

const _loaded = {};
async function loadTab(name) {
  switchTab(name);
  if (_loaded[currentRec + '/' + name]) return;
  _loaded[currentRec + '/' + name] = true;
  const pane = $(`pane-${name}`);

  if (name === 'fields') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/fields?env=${env()}`);
    pane.innerHTML = renderFields(d.items || []);
  } else if (name === 'keys') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/keys?env=${env()}`);
    pane.innerHTML = renderKeys(d.items || []);
  } else if (name === 'indexes') {
    const [idxR, keyR] = await Promise.all([
      api(`/api/record/${encodeURIComponent(currentRec)}/indexes?env=${env()}`),
      api(`/api/record/${encodeURIComponent(currentRec)}/keys?env=${env()}`)
    ]);
    pane.innerHTML = renderIndexes(idxR.items || [], keyR.items || []);
  } else if (name === 'related') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/related?env=${env()}`);
    pane.innerHTML = renderRelated(d);
  } else if (name === 'components') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/components?env=${env()}`);
    pane.innerHTML = renderComponents(d.items || []);
  } else if (name === 'pages') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/pages?env=${env()}`);
    pane.innerHTML = renderPages(d.items || []);
  } else if (name === 'ddl') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/ddl?env=${env()}`);
    pane.innerHTML = renderDDL(d);
  } else if (name === 'data') {
    pane.innerHTML = renderDataPane();
    loadData(currentRec);
  }
}

// ─── Tab renderers ─────────────────────────────────────────────────────────
function renderFields(items) {
  if (!items.length) return '<div class="empty">No fields found.</div>';
  return `<table><thead><tr>
    <th>#</th><th>Field Name</th><th>Type</th><th>Len</th><th>Dec</th><th>Flags</th><th>Prompt</th>
  </tr></thead><tbody>` + items.map(f => {
    const flags = [];
    const ue = parseInt(f.useedit || 0);
    if (ue & 1)  flags.push('<span class="key-badge key-pk">Req</span>');
    if (ue & 2)  flags.push('<span class="key-badge key-search">Xlat</span>');
    if (ue & 16) flags.push('<span class="key-badge key-dup">Prompt</span>');
    return `<tr>
      <td style="color:#445;">${esc(f.fieldnum)}</td>
      <td class="mono">
        <a class="obj-link" href="/admin/object/field/${esc(currentRec)}.${esc(f.fieldname)}">${esc(f.fieldname)}</a>
        <a href="/admin/field?field=${esc(f.fieldname)}" title="Cross-record usage" style="color:#556;font-size:9px;margin-left:4px;text-decoration:none;">&#8648;</a>
      </td>
      <td>${esc(f.fieldtype_label || f.fieldtype)}</td>
      <td>${esc(f.fieldlen)}</td>
      <td>${esc(f.decimalpos || '')}</td>
      <td>${flags.join(' ')}</td>
      <td class="mono" style="font-size:10px;">${esc(f.defrecname || '')}${f.deffieldname ? '.' + esc(f.deffieldname) : ''}</td>
    </tr>`;
  }).join('') + '</tbody></table>';
}

function renderKeys(items) {
  if (!items.length) return '<div class="empty">No key fields (PSKEYDEFN not accessible in this environment).</div>';
  const IDX_LABEL = {'_':'PK','0':'Search','A':'Alt A','B':'Alt B','C':'Alt C','D':'Alt D'};
  return `<table><thead><tr>
    <th>Index</th><th>Pos</th><th>Field</th><th>Order</th>
  </tr></thead><tbody>` + items.map(k => {
    const lbl = IDX_LABEL[k.indexid] ?? `Idx ${k.indexid}`;
    const ord = k.ascdesc === 1 ? 'Asc' : k.ascdesc === 0 ? 'Desc' : '';
    return `<tr>
      <td style="color:#00e5ff;font-family:monospace;">${esc(lbl)}</td>
      <td style="color:#445;">${esc(k.keyposn)}</td>
      <td class="mono">${esc(k.fieldname)}</td>
      <td style="color:#667;">${ord}</td>
    </tr>`;
  }).join('') + '</tbody></table>';
}

function renderIndexes(indexes, keys) {
  if (!indexes.length && !keys.length) return '<div class="empty">No indexes found (PSINDEXDEFN/PSKEYDEFN not accessible in this environment).</div>';
  const IDX_LABEL = {'_':'Primary Key (PK)','0':'Primary Search','A':'Alt Search A','B':'Alt Search B','C':'Alt Search C'};
  // group keys by indexid
  const keysByIdx = {};
  (keys || []).forEach(k => { (keysByIdx[k.indexid] = keysByIdx[k.indexid] || []).push(k); });
  let h = '';
  indexes.forEach(idx => {
    const id = idx.indexid ?? '?';
    const label = IDX_LABEL[id] ?? (id >= 'A' && id <= 'Z' ? `Alt Search ${id}` : `Index ${id}`);
    const fields = (keysByIdx[id] || []).sort((a,b) => (a.keyposn||0)-(b.keyposn||0));
    const uniq = idx.uniqueflag ? '<span class="chip chip-table" style="margin-left:6px;">Unique</span>' : '';
    const inactive = !idx.activeflag ? '<span class="chip chip-temp" style="margin-left:4px;">Inactive</span>' : '';
    const custord = idx.custkeyorder ? '<span class="chip chip-work" style="margin-left:4px;">Custom Order</span>' : '';
    const fieldStr = fields.length
      ? fields.map(f => `${esc(f.fieldname)}${f.ascdesc === 0 ? '<span style="color:#667;"> ▼</span>' : ''}`).join(', ')
      : '<em style="color:#445;">No field composition (fetch keys tab first)</em>';
    h += `<div class="card" style="margin-bottom:8px;">
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:5px;">
        <strong style="font-size:12px;color:#00e5ff;">${label}</strong>
        <span style="color:#334;font-size:10px;font-family:monospace;">[${esc(id)}]</span>
        ${uniq}${inactive}${custord}
      </div>
      <div style="font-family:monospace;font-size:11px;color:#9ab;">${fieldStr}</div>
    </div>`;
  });
  // Any key-only indexes (no PSINDEXDEFN row)
  Object.keys(keysByIdx).filter(id => !indexes.find(i => (i.indexid ?? '?') === id)).forEach(id => {
    const fields = keysByIdx[id].sort((a,b) => (a.keyposn||0)-(b.keyposn||0));
    h += `<div class="card" style="margin-bottom:8px;">
      <strong style="font-size:12px;color:#00e5ff;">Index ${esc(id)}</strong>
      <div style="font-family:monospace;font-size:11px;color:#9ab;margin-top:4px;">${fields.map(f=>esc(f.fieldname)).join(', ')}</div>
    </div>`;
  });
  return h || '<div class="empty">No indexes found.</div>';
}

function renderRelated(d) {
  let h = '';
  if (d.parent) {
    h += '<h2>Parent Record</h2><div class="card">' +
      recRow(d.parent, () => loadRecord(d.parent.recname)) + '</div>';
  }
  if (d.lang) {
    h += '<h2>Language Variant</h2><div class="card">' +
      recRow(d.lang, () => loadRecord(d.lang.recname)) + '</div>';
  }
  if (d.audit) {
    h += '<h2>Audit Record</h2><div class="card">' +
      recRow(d.audit, () => loadRecord(d.audit.recname)) + '</div>';
  }
  if ((d.views || []).length) {
    h += `<h2>Related Views (${d.views.length})</h2><div class="card"><table><thead><tr>
      <th>Record Name</th><th>Type</th><th>Description</th>
    </tr></thead><tbody>`;
    d.views.forEach(v => {
      const chip = recChip(psRecTypeLabel(v.rectype));
      h += `<tr><td class="mono"><a class="obj-link" onclick="loadRecord('${esc(v.recname)}')">${esc(v.recname)}</a></td>
        <td>${chip}</td><td>${esc(v.recdescr || '')}</td></tr>`;
    });
    h += '</tbody></table></div>';
  }
  if (!h) h = '<div class="empty">No related records found.</div>';
  return h;
}

function renderComponents(items) {
  if (!items.length) return '<div class="empty">No components use this record as search or add record.</div>';
  return `<table><thead><tr>
    <th>Component</th><th>Search Record</th><th>Add Record</th><th>Description</th><th>Market</th>
  </tr></thead><tbody>` + items.map(c => `<tr>
    <td class="mono"><a class="obj-link" href="/admin/object/component/${esc(c.pnlgrpname)}">${esc(c.pnlgrpname)}</a></td>
    <td class="mono">${esc(c.searchrecname || '')}</td>
    <td class="mono">${esc(c.addsrchrecname || '')}</td>
    <td>${esc(c.descr || '')}</td>
    <td>${esc(c.market || '')}</td>
  </tr>`).join('') + '</tbody></table>';
}

function renderPages(items) {
  if (!items.length) return '<div class="empty">No pages reference this record\'s fields.</div>';
  // Deduplicate by page name.
  const seen = new Set();
  const unique = items.filter(r => { const k = r.pnlname; if (seen.has(k)) return false; seen.add(k); return true; });
  return `<table><thead><tr><th>Page</th></tr></thead><tbody>` +
    unique.map(p => `<tr><td class="mono">
      <a class="obj-link" href="/admin/object/page/${esc(p.pnlname)}">${esc(p.pnlname)}</a>
    </td></tr>`).join('') + '</tbody></table>';
}

function renderDDL(d) {
  const ddl = d.ddl || d.sql || '';
  if (!ddl) return '<div class="empty">DDL not available (may be a view or derived record).</div>';
  return `<div class="code-block">${esc(ddl)}</div>`;
}

function renderDataPane() {
  return `<div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
      <span id="rowCountBadge" style="font-size:11px;color:#556;">Loading row count…</span>
      <button class="sec" onclick="loadSample()" style="font-size:10px;">Sample 20 Rows</button>
      <a class="obj-link" id="sqlwsLink" style="margin-left:auto;display:none;" href="/admin/sqlws">Open in SQL Workspace &#8594;</a>
    </div>
    <div id="sampleData"><span class="empty">Click "Sample 20 Rows" to load data.</span></div>
  </div>`;
}

async function loadData(recname) {
  const d = await api(`/api/record/${encodeURIComponent(recname)}/count?env=${env()}`);
  const badge = $('rowCountBadge');
  if (badge) {
    const n = d.row_count ?? d.count ?? '?';
    badge.textContent = `${n.toLocaleString()} rows`;
    badge.style.color = '#00e5ff';
  }
  const link = $('sqlwsLink');
  if (link) {
    const tbl = `PS_${recname}`;
    link.href = `/admin/sqlws`;
    link.style.display = 'inline';
    link.title = `SELECT * FROM SYSADM.${tbl}`;
  }
}

async function loadSample() {
  const d = await api(`/api/record/${encodeURIComponent(currentRec)}/sample?env=${env()}&limit=20`);
  const pane = $('sampleData');
  if (!pane) return;
  const rows = d.rows || d.items || [];
  if (!rows.length) { pane.innerHTML = '<div class="empty">No data returned.</div>'; return; }
  const cols = Object.keys(rows[0]);
  pane.innerHTML = `<div style="overflow-x:auto;"><table><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>` +
    rows.map(r => `<tr>${cols.map(c => `<td class="mono">${esc(r[c])}</td>`).join('')}</tr>`).join('') +
    '</tbody></table></div>';
}

// ─── Eager overview sub-sections ──────────────────────────────────────────
async function loadStorageInto(targetId, recname) {
  const d = await api(`/api/record/${encodeURIComponent(recname)}/storage?env=${env()}`);
  const target = $(targetId);
  if (!target) return;
  const item = d.item;
  if (!item) return;
  target.innerHTML = `<h2>Oracle Storage</h2><div class="card">
    <div class="stat-grid">
      ${sBox(item.num_rows != null ? Number(item.num_rows).toLocaleString() : '—', 'Est. Rows')}
      ${sBox(item.blocks != null ? item.blocks : '—', 'Blocks')}
      ${sBox(item.avg_row_len != null ? item.avg_row_len + ' B' : '—', 'Avg Row')}
    </div>
    <div class="kv-grid">
      ${kv('Table Name', item.table_name)}
      ${kv('Partitioned', item.partitioned)}
      ${kv('Compression', item.compression)}
      ${kv('Last Analyzed', item.last_analyzed)}
    </div>
  </div>`;
}

async function loadChildrenInto(targetId, recname) {
  const d = await api(`/api/record/${encodeURIComponent(recname)}/children?env=${env()}`);
  const target = $(targetId);
  if (!target) return;
  const items = d.items || [];
  if (!items.length) return;
  target.innerHTML = `<h2>Child Records (${items.length})</h2><div class="card"><table><thead><tr>
    <th>Record Name</th><th>Type</th><th>Description</th>
  </tr></thead><tbody>` +
    items.map(c => `<tr>
      <td class="mono"><a class="obj-link" onclick="loadRecord('${esc(c.recname)}')">${esc(c.recname)}</a></td>
      <td>${recChip(c.rectype_label || psRecTypeLabel(c.rectype))}</td>
      <td>${esc(c.recdescr || '')}</td>
    </tr>`).join('') +
  '</tbody></table></div>';
}

// ─── Helpers ───────────────────────────────────────────────────────────────
function kv(label, val) {
  if (val == null || val === '' || val === ' ') return '';
  return `<div class="kv-key">${esc(label)}</div><div class="kv-val">${val}</div>`;
}
function sBox(n, label) {
  return `<div class="stat-box"><div class="stat-num">${n != null ? n : '—'}</div><div class="stat-lbl">${esc(label)}</div></div>`;
}

function psRecTypeLabel(rt) {
  const map = {0:'SQL Table',1:'SQL View',2:'Derived/Work',3:'SubRecord',5:'Dynamic View',6:'Query View',7:'Temporary Table'};
  return map[parseInt(rt)] || String(rt ?? '');
}

function recBadge(label) {
  const map = {
    'SQL Table':      {cls:'bd-table',text:'T'},
    'SQL View':       {cls:'bd-view',text:'V'},
    'Derived/Work':   {cls:'bd-work',text:'D'},
    'SubRecord':      {cls:'bd-sub',text:'S'},
    'Dynamic View':   {cls:'bd-view',text:'DV'},
    'Query View':     {cls:'bd-view',text:'QV'},
    'Temporary Table':{cls:'bd-temp',text:'TMP'},
  };
  return map[label] || {cls:'bd-table',text:String(label||'?').substring(0,3)};
}

function recChip(label) {
  const map = {
    'SQL Table':'chip-table','SQL View':'chip-view','Derived/Work':'chip-work',
    'SubRecord':'chip-sub','Dynamic View':'chip-view','Query View':'chip-view',
    'Temporary Table':'chip-temp',
  };
  const cls = map[label] || 'chip-table';
  return `<span class="chip ${cls}">${esc(label||'')}</span>`;
}

function recRow(rec, onclick) {
  if (!rec) return '';
  return `<span class="mono" style="cursor:pointer;" onclick="loadRecord('${esc(rec.recname)}')">${esc(rec.recname)}</span>
    <span style="color:#556;font-size:10px;margin-left:8px;">${esc(rec.recdescr || '')}</span>`;
}

// ─── Init ─────────────────────────────────────────────────────────────────
(async () => {
  const envs = ['HCM','FSCM'];
  try {
    const d = await (await fetch('/api/envcompare/config')).json();
    if (d.envs) envs.splice(0, envs.length, ...d.envs);
  } catch(e) {}
  $('envSel').innerHTML = envs.map(e => `<option value="${e}">${e}</option>`).join('');

  // If URL has a record name, load it.
  const path = window.location.pathname;
  const match = path.match(/\\/admin\\/record\\/([^/]+)$/);
  if (match) loadRecord(decodeURIComponent(match[1]));
})();
</script>""")


@router.get("/field", response_class=HTMLResponse)
def admin_field():
    return _shell("Field Explorer", "objects", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;height:100vh;display:flex;flex-direction:column;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px;}
nav{font-size:12px;color:#445;}
nav a{color:#00e5ff;text-decoration:none;} nav a:hover{text-decoration:underline;}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:280px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0;}
.content{flex:1;overflow:auto;padding:16px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
input:focus,select:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:3px;}
.chip{display:inline-block;padding:2px 8px;border-radius:2px;font-size:11px;font-weight:bold;}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66;}
.chip-muted{background:#141a20;border:1px solid #334;color:#778;}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff;}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00;}
.chip-def{background:#001830;border:1px solid #00e5ff55;color:#00ccdd;font-size:10px;padding:2px 7px;}
.chip-len{background:#0d1a10;border:1px solid #33664422;color:#558866;font-size:10px;padding:2px 7px;}
.field-item{padding:6px 8px;cursor:pointer;border-radius:2px;display:flex;justify-content:space-between;align-items:center;}
.field-item:hover{background:rgba(0,229,255,.07);}
.field-item.sel{background:rgba(0,229,255,.12);border-left:2px solid #00e5ff;}
.field-name{font-family:monospace;font-size:12px;color:#d7faff;}
.field-cnt{font-size:10px;color:#445;min-width:30px;text-align:right;}
.field-type{font-size:10px;color:#667;padding-left:6px;}
table{border-collapse:collapse;width:100%;font-size:12px;}
th{border-bottom:1px solid #00e5ff33;padding:5px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #1e3040;padding:5px 8px;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;}
.empty{color:#445;font-style:italic;padding:16px 0;font-size:12px;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.tab-row{display:flex;gap:0;margin:10px 0 0;border-bottom:1px solid #00e5ff22;}
.tab{padding:5px 14px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
.rec-badge{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;border:1px solid #00e5ff33;color:#8ab;margin-left:4px;}
.flag-key{color:#ffaa00;font-size:10px;font-weight:bold;}
.flag-req{color:#ff8888;font-size:10px;}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin:12px 0;}
.stat-box{background:#0b1b24;border:1px solid #00e5ff22;padding:10px;border-radius:2px;}
.stat-box .sv{font-size:22px;font-weight:bold;color:#00e5ff;line-height:1;}
.stat-box .sl{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
a.obj-link{color:#00e5ff;text-decoration:none;font-family:monospace;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.search-row{display:flex;gap:6px;margin-bottom:8px;}
.search-row input{flex:1;}
</style>
<div class="main">
  <!-- Sidebar -->
  <div class="sidebar">
    <h2>Field Search</h2>
    <div class="search-row">
      <input type="text" id="searchInput" placeholder="Field name…" oninput="debSearch()" onkeydown="if(event.key==='Enter')doSearch()">
      <button class="sec" onclick="doSearch()" style="font-size:10px;">Go</button>
    </div>
    <div id="searchCount" style="font-size:10px;color:#445;margin-bottom:6px;"></div>
    <div id="fieldList"><div class="empty">Enter a field name to search.</div></div>
  </div>
  <!-- Content -->
  <div class="content">
    <div id="placeholder" style="padding:40px 0;text-align:center;">
      <div style="font-size:40px;margin-bottom:12px;opacity:.3;">&#8801;</div>
      <div style="color:#445;font-size:13px;">Select a field from the sidebar.</div>
      <div style="color:#334;font-size:11px;margin-top:6px;">Searches PSRECFIELD — 521k+ field-record relationships.</div>
    </div>
    <div id="fieldContent" style="display:none;">
      <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:12px;">
        <span id="fieldTitle" style="font-size:20px;font-weight:bold;color:#00e5ff;font-family:monospace;"></span>
        <span id="fieldTypeChip"></span>
        <span id="fieldLenChip"></span>
        <a id="fieldObjLink" href="#" style="margin-left:auto;font-size:11px;color:#00e5ff;text-decoration:none;">Object Page &#8599;</a>
      </div>
      <div class="stat-grid" id="statGrid"></div>
      <div class="tab-row">
        <div class="tab on" onclick="setTab('records')">Records</div>
        <div class="tab"    onclick="setTab('keyed')">Keyed Usage</div>
        <div class="tab"    onclick="setTab('rectype')">By Type</div>
      </div>
      <div id="paneRecords" class="pane on"><div id="tblRecords"></div></div>
      <div id="paneKeyed"   class="pane"><div id="tblKeyed"></div></div>
      <div id="paneRectype" class="pane"><div id="tblRectype"></div></div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
function env() { return $('envSel').value || 'HCM'; }
let debTimer = null;
function debSearch() { clearTimeout(debTimer); debTimer = setTimeout(doSearch, 200); }
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}
function empty(msg) { return `<div class="empty">${msg || 'No data.'}</div>`; }

const FTYPE = {0:'Char',1:'Long Char',2:'Number',3:'Signed Num',4:'Date',5:'Time',6:'DateTime',8:'Image',9:'ImgRef'};
const RTYPE = {0:'SQL Table',1:'SQL View',2:'Derived/Work',3:'SubRecord',5:'Dynamic View',6:'Query View',7:'Temp Table'};
let currentField = null;
let allRecords = [];

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function doSearch() {
  const q = $('searchInput').value.trim();
  if (!q) { $('fieldList').innerHTML = '<div class="empty">Enter a field name to search.</div>'; return; }
  $('fieldList').innerHTML = '<div class="empty">Searching…</div>';
  $('searchCount').textContent = '';
  try {
    const d = await api(`/api/field/search?env=${env()}&q=${encodeURIComponent(q)}&limit=150`);
    const items = d.items || [];
    $('searchCount').textContent = `${items.length} field${items.length===1?'':'s'}`;
    if (!items.length) { $('fieldList').innerHTML = '<div class="empty">No fields found.</div>'; return; }
    $('fieldList').innerHTML = items.map(it => {
      const ft = FTYPE[it.db_fieldtype] || '';
      return `<div class="field-item" id="fi_${esc(it.fieldname)}" onclick="loadField('${esc(it.fieldname)}', this)">
        <div>
          <span class="field-name">${esc(it.fieldname)}</span>
          ${ft ? `<span class="field-type">${ft}</span>` : ''}
        </div>
        <span class="field-cnt">${(it.record_count||0).toLocaleString()}</span>
      </div>`;
    }).join('');
  } catch(e) {
    $('fieldList').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

function clearField() {
  $('placeholder').style.display = '';
  $('fieldContent').style.display = 'none';
  currentField = null;
  allRecords = [];
}

async function loadField(name, el) {
  if (el) {
    document.querySelectorAll('.field-item').forEach(e => e.classList.remove('sel'));
    el.classList.add('sel');
  }
  currentField = name;
  $('placeholder').style.display = 'none';
  $('fieldContent').style.display = '';
  $('fieldTitle').textContent = name;
  $('fieldTypeChip').textContent = '';
  $('fieldLenChip').textContent = '';
  $('statGrid').innerHTML = '<div style="color:#445;font-size:11px;">Loading…</div>';
  $('tblRecords').innerHTML = '<div class="empty">Loading…</div>';
  $('tblKeyed').innerHTML = '';
  $('tblRectype').innerHTML = '';
  $('fieldObjLink').href = `/admin/object/field/${encodeURIComponent(name)}`;

  // Load definition + records in parallel
  const [defRes, recRes] = await Promise.allSettled([
    api(`/api/field/${encodeURIComponent(name)}/definition?env=${env()}`),
    api(`/api/field/${encodeURIComponent(name)}/records?env=${env()}`)
  ]);

  if (defRes.status === 'fulfilled') {
    const item = defRes.value.item || {};
    const ft = item.field_type;
    if (ft !== null && ft !== undefined) {
      $('fieldTypeChip').className = 'chip chip-def';
      $('fieldTypeChip').textContent = FTYPE[ft] || `Type ${ft}`;
    }
    const len = item.length;
    if (len !== null && len !== undefined && len !== '') {
      $('fieldLenChip').className = 'chip chip-len';
      $('fieldLenChip').textContent = `Len ${len}`;
    }
  }

  if (recRes.status === 'fulfilled') {
    const d = recRes.value;
    allRecords = d.items || [];
    (d.warnings||[]).forEach(w => $('tblRecords').innerHTML += `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`);
    renderStats(allRecords);
    renderRecords(allRecords);
    renderKeyed(allRecords);
    renderByType(allRecords);
  } else {
    $('tblRecords').innerHTML = `<div class="warn-msg">Error: ${esc(recRes.reason?.message)}</div>`;
    $('statGrid').innerHTML = '';
  }
}

function renderStats(rows) {
  const total = rows.length;
  const keyed = rows.filter(r => r.is_key).length;
  const views = rows.filter(r => [1,5,6].includes(r.rectype)).length;
  const tables = rows.filter(r => r.rectype === 0).length;
  $('statGrid').innerHTML = [
    {v: total, l: 'Records Using Field'},
    {v: tables, l: 'SQL Tables'},
    {v: views, l: 'Views'},
    {v: keyed, l: 'Used as Key'},
  ].map(s => `<div class="stat-box"><div class="sv">${s.v.toLocaleString()}</div><div class="sl">${s.l}</div></div>`).join('');
}

function recRow(r) {
  const rt = r.rectype_label || '';
  const flags = [
    r.is_key ? '<span class="flag-key">KEY</span>' : '',
    r.is_search_key ? '<span class="flag-key">SRCH</span>' : '',
    r.is_required ? '<span class="flag-req">REQ</span>' : '',
  ].filter(Boolean).join(' ');
  return `<tr>
    <td><a class="obj-link" href="/admin/record/${esc(r.recname)}">${esc(r.recname)}</a></td>
    <td style="font-size:10px;color:#667;">${esc(r.recdescr||'')}</td>
    <td style="font-size:10px;"><span class="rec-badge">${esc(rt)}</span></td>
    <td style="font-size:10px;text-align:center;">${r.fieldnum||''}</td>
    <td>${flags}</td>
  </tr>`;
}

function recTable(rows, emptyMsg) {
  if (!rows.length) return empty(emptyMsg||'None.');
  return `<table><thead><tr>
    <th>Record</th><th>Description</th><th>Type</th><th>Fld#</th><th>Flags</th>
  </tr></thead><tbody>${rows.map(recRow).join('')}</tbody></table>`;
}

function renderRecords(rows) {
  $('tblRecords').innerHTML = recTable(rows, 'No records use this field.');
}

function renderKeyed(rows) {
  const keyed = rows.filter(r => r.is_key || r.is_search_key);
  $('tblKeyed').innerHTML = keyed.length
    ? recTable(keyed, 'Field is not used as a key in any record.')
    : '<div class="empty">This field is not used as a key in any record.</div>';
}

function renderByType(rows) {
  const groups = {};
  rows.forEach(r => {
    const k = r.rectype_label || 'Unknown';
    if (!groups[k]) groups[k] = [];
    groups[k].push(r);
  });
  const order = ['SQL Table','SQL View','Dynamic View','Query View','SubRecord','Derived/Work','Temporary Table'];
  const keys = [...new Set([...order, ...Object.keys(groups)])].filter(k => groups[k]);
  $('tblRectype').innerHTML = keys.map(k => {
    const cnt = groups[k].length;
    return `<details style="margin-bottom:6px;">
      <summary style="cursor:pointer;padding:4px 0;font-size:11px;color:#8ab;">
        ${esc(k)} <span style="color:#00e5ff;font-weight:bold;">${cnt}</span>
      </summary>
      ${recTable(groups[k])}
    </details>`;
  }).join('');
}

function setTab(name) {
  ['records','keyed','rectype'].forEach(n => {
    const tab = document.querySelector(`.tab[onclick*="${n}"]`);
    if (tab) tab.classList.toggle('on', n === name);
    const p = $(`pane${n.charAt(0).toUpperCase()+n.slice(1)}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

(async () => {
  try {
    const cfg = await api('/api/runtime/config').catch(() => ({envs:['HCM','FSCM']}));
    $('envSel').innerHTML = (cfg.envs||['HCM','FSCM']).map(e => `<option value="${e}">${e}</option>`).join('');
  } catch(e) {
    $('envSel').innerHTML = '<option value="HCM">HCM</option>';
  }
  // Check URL for pre-seeded field
  const params = new URLSearchParams(window.location.search);
  const fParam = params.get('field');
  if (fParam) {
    $('searchInput').value = fParam;
    await doSearch();
    const item = document.getElementById(`fi_${fParam}`);
    if (item) loadField(fParam, item);
    else loadField(fParam, null);
  }
})();
</script>""")


@router.get("/operator", response_class=HTMLResponse)
@router.get("/operator/{oprid_val:path}", response_class=HTMLResponse)
def admin_operator(oprid_val: str = None):
    return _shell("Operator Explorer", "security", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;height:100vh;display:flex;flex-direction:column;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;} nav a:hover{text-decoration:underline;}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:280px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0;}
.content{flex:1;overflow:auto;padding:16px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
input:focus,select:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:3px;}
.op-item{padding:6px 8px;cursor:pointer;border-radius:2px;}
.op-item:hover{background:rgba(0,229,255,.07);}
.op-item.sel{background:rgba(0,229,255,.12);border-left:2px solid #00e5ff;}
.op-id{font-family:monospace;font-size:12px;color:#d7faff;}
.op-name{font-size:10px;color:#556;margin-top:1px;}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin:12px 0;}
.stat-box{background:#0b1b24;border:1px solid #00e5ff22;padding:10px;border-radius:2px;}
.stat-box .sv{font-size:22px;font-weight:bold;color:#00e5ff;line-height:1;}
.stat-box .sl{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
table{border-collapse:collapse;width:100%;font-size:12px;}
th{border-bottom:1px solid #00e5ff33;padding:5px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #1e3040;padding:5px 8px;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;}
.empty{color:#445;font-style:italic;padding:16px 0;font-size:12px;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.tab-row{display:flex;gap:0;margin:10px 0 0;border-bottom:1px solid #00e5ff22;}
.tab{padding:5px 14px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
a.obj-link{color:#00e5ff;text-decoration:none;font-family:monospace;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.badge{display:inline-block;padding:2px 8px;border-radius:2px;font-size:10px;font-weight:bold;border:1px solid;}
.b-active{border-color:#00cc66;color:#00cc66;background:#002800;}
.b-locked{border-color:#ff4444;color:#ff4444;background:#3a0000;}
.kv{display:flex;margin:4px 0;font-size:12px;}
.kl{color:#445;min-width:160px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;flex-shrink:0;}
.kv-val{color:#d7faff;font-family:monospace;word-break:break-all;}
.search-row{display:flex;gap:6px;margin-bottom:8px;}
.search-row input{flex:1;}
</style>
<div class="main">
  <div class="sidebar">
    <h2>Operator Search</h2>
    <div class="search-row">
      <input type="text" id="searchInput" placeholder="OPRID, name, or email…" oninput="debSearch()" onkeydown="if(event.key==='Enter')doSearch()">
      <button class="sec" onclick="doSearch()" style="font-size:10px;">Go</button>
    </div>
    <div style="font-size:10px;color:#445;margin-bottom:6px;" id="searchCount"></div>
    <div id="opList"><div class="empty">Enter a search term or leave blank to list all operators.</div></div>
  </div>
  <div class="content">
    <div id="placeholder" style="padding:40px 0;text-align:center;">
      <div style="font-size:40px;margin-bottom:12px;opacity:.3;">&#9786;</div>
      <div style="color:#445;font-size:13px;">Select an operator from the sidebar.</div>
      <div style="color:#334;font-size:11px;margin-top:6px;">141 operators in HCM.</div>
    </div>
    <div id="opContent" style="display:none;">
      <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
        <span id="opTitle" style="font-size:20px;font-weight:bold;color:#00e5ff;font-family:monospace;"></span>
        <span id="opBadge"></span>
        <a id="traceLink" href="#" style="font-size:11px;color:#00e5ff;text-decoration:none;">&#9654; Trace</a>
        <a id="objLink"   href="#" style="font-size:11px;color:#00e5ff;text-decoration:none;">Object Page &#8599;</a>
      </div>
      <div id="opName" style="color:#8ab;font-size:13px;margin-bottom:12px;"></div>
      <div class="stat-grid" id="statGrid"></div>
      <div class="tab-row">
        <div class="tab on" onclick="setTab('overview')">Overview</div>
        <div class="tab"    onclick="setTab('roles')">Roles</div>
      </div>
      <div id="paneOverview" class="pane on"><div id="tblOverview"></div></div>
      <div id="paneRoles"    class="pane"><div id="tblRoles"></div></div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
function env() { return $('envSel').value || 'HCM'; }
let debTimer = null;
function debSearch() { clearTimeout(debTimer); debTimer = setTimeout(doSearch, 200); }
function esc(s) { const d = document.createElement('div'); d.textContent = String(s??''); return d.innerHTML; }
function empty(msg) { return `<div class="empty">${msg||'No data.'}</div>`; }
let currentOp = null;

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function doSearch() {
  const q = $('searchInput').value.trim();
  $('opList').innerHTML = '<div class="empty">Searching…</div>';
  $('searchCount').textContent = '';
  try {
    const d = await api(`/api/operator/search?env=${env()}&q=${encodeURIComponent(q)}&limit=150`);
    const items = d.items || [];
    $('searchCount').textContent = `${items.length} operator${items.length===1?'':'s'}`;
    if (!items.length) { $('opList').innerHTML = '<div class="empty">No operators found.</div>'; return; }
    $('opList').innerHTML = items.map(it => {
      const locked = it.acctlock ? ' style="color:#ff4444;"' : '';
      return `<div class="op-item" id="oi_${esc(it.oprid)}" onclick="loadOp('${esc(it.oprid).replace(/'/g,"\\'")}', this)">
        <div class="op-id"${locked}>${esc(it.oprid)}${it.acctlock ? ' &#128274;' : ''}</div>
        ${it.oprdefndesc ? `<div class="op-name">${esc(it.oprdefndesc)}</div>` : ''}
      </div>`;
    }).join('');
  } catch(e) {
    $('opList').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

function clearOp() {
  $('placeholder').style.display = '';
  $('opContent').style.display = 'none';
  currentOp = null;
}

async function loadOp(oprid, el) {
  if (el) {
    document.querySelectorAll('.op-item').forEach(e => e.classList.remove('sel'));
    el.classList.add('sel');
  }
  currentOp = oprid;
  $('placeholder').style.display = 'none';
  $('opContent').style.display = '';
  $('opTitle').textContent = oprid;
  $('opName').textContent = '';
  $('opBadge').innerHTML = '';
  $('statGrid').innerHTML = '<div style="color:#445;font-size:11px;">Loading…</div>';
  $('tblOverview').innerHTML = '<div class="empty">Loading…</div>';
  $('tblRoles').innerHTML = '<div class="empty">Loading…</div>';
  $('traceLink').href = `/admin/tracing?oprid=${encodeURIComponent(oprid)}&env=${env()}`;
  $('objLink').href   = `/admin/object/operator/${encodeURIComponent(oprid)}`;
  history.replaceState(null, '', `/admin/operator/${encodeURIComponent(oprid)}`);

  try {
    const [det, roles] = await Promise.allSettled([
      api(`/api/operator/${encodeURIComponent(oprid)}?env=${env()}`),
      api(`/api/operator/${encodeURIComponent(oprid)}/roles?env=${env()}`),
    ]);

    const d = det.status === 'fulfilled'   ? det.value   : {item: null, warnings: [{message: det.reason?.message}]};
    const r = roles.status === 'fulfilled' ? roles.value : {items: [], warnings: [{message: roles.reason?.message}]};

    const item = d.item || {};
    $('opName').textContent = item.oprdefndesc || '';

    const locked = item.acctlock;
    $('opBadge').innerHTML = `<span class="badge ${locked ? 'b-locked' : 'b-active'}">${esc(item.acctlock_label || (locked ? 'Locked' : 'Active'))}</span>`;

    const roleCount = (r.items || []).length;
    $('statGrid').innerHTML = [
      {v: roleCount,               l: 'Roles Assigned'},
      {v: item.failedlogins || 0,  l: 'Failed Logins'},
    ].map(s => `<div class="stat-box"><div class="sv">${s.v}</div><div class="sl">${s.l}</div></div>`).join('');

    renderOverview(item, d.warnings || []);
    renderRoles(r.items || [], r.warnings || []);
  } catch(e) {
    $('tblOverview').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
    $('statGrid').innerHTML = '';
  }
}

function renderOverview(item, warns) {
  let h = warns.filter(w=>w.message).map(w=>`<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
  if (!item || !item.oprid) { $('tblOverview').innerHTML = h+'<div class="empty">Operator not found.</div>'; return; }
  const dt = s => s ? s.replace('T',' ').substr(0,19) : '—';
  h += `
  <h2>Identity</h2>
  <div class="kv"><span class="kl">OPRID</span><span class="kv-val">${esc(item.oprid)}</span></div>
  <div class="kv"><span class="kl">Name</span><span class="kv-val">${esc(item.oprdefndesc||'—')}</span></div>
  ${item.emplid ? `<div class="kv"><span class="kl">Employee ID</span><span class="kv-val">${esc(item.emplid)}</span></div>` : ''}
  ${item.emailid ? `<div class="kv"><span class="kl">Email</span><span class="kv-val">${esc(item.emailid)}</span></div>` : ''}
  <div class="kv"><span class="kl">Status</span><span class="kv-val">${esc(item.acctlock_label||'—')}</span></div>
  ${item.oprtype_label ? `<div class="kv"><span class="kl">Type</span><span class="kv-val">${esc(item.oprtype_label)}</span></div>` : ''}
  ${item.language_cd ? `<div class="kv"><span class="kl">Language</span><span class="kv-val">${esc(item.language_cd)}</span></div>` : ''}
  ${item.currency_cd ? `<div class="kv"><span class="kl">Currency</span><span class="kv-val">${esc(item.currency_cd)}</span></div>` : ''}
  <h2>Security</h2>
  <div class="kv"><span class="kl">Permission List</span><span class="kv-val">${item.oprclass ? `<a class="obj-link" href="/admin/object/permissionlist/${esc(item.oprclass)}">${esc(item.oprclass)}</a>` : '—'}</span></div>
  <div class="kv"><span class="kl">Row Security</span><span class="kv-val">${esc(item.rowsecclass||'—')}</span></div>
  <div class="kv"><span class="kl">Process Profile</span><span class="kv-val">${esc(item.prcsprflcls||'—')}</span></div>
  <div class="kv"><span class="kl">Failed Logins</span><span class="kv-val">${esc(item.failedlogins??'—')}</span></div>
  ${item.ptacctlockdate ? `<div class="kv"><span class="kl">Lock Date</span><span class="kv-val">${esc(dt(item.ptacctlockdate))}</span></div>` : ''}
  ${item.ptacctneverlock ? `<div class="kv"><span class="kl">Never Lock</span><span class="kv-val">${esc(item.ptacctneverlock)}</span></div>` : ''}
  <div class="kv"><span class="kl">Allow Switch User</span><span class="kv-val">${item.ptallowswitchuser==='Y'?'<span style="color:#00cc66;">Yes</span>':'No'}</span></div>
  <h2>Activity</h2>
  <div class="kv"><span class="kl">Last Sign-On</span><span class="kv-val">${esc(dt(item.lastsignondttm))}</span></div>
  <div class="kv"><span class="kl">Last Password Change</span><span class="kv-val">${esc(dt(item.lastpswdchange))}</span></div>
  <div class="kv"><span class="kl">Password Expiry</span><span class="kv-val">${esc(dt(item.expent))}</span></div>
  <div class="kv"><span class="kl">Last Updated</span><span class="kv-val">${esc(dt(item.lastupddttm))}</span></div>
  <div class="kv"><span class="kl">Updated By</span><span class="kv-val">${esc(item.lastupdoprid||'—')}</span></div>`;
  $('tblOverview').innerHTML = h;
}

function renderRoles(items, warns) {
  let h = warns.filter(w=>w.message).map(w=>`<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
  if (!items.length) { $('tblRoles').innerHTML = h+'<div class="empty">No roles found.</div>'; return; }
  const rows = items.map(r => `<tr>
    <td class="mono"><a class="obj-link" href="/admin/role/${encodeURIComponent(r.rolename)}">${esc(r.rolename)}</a></td>
    <td style="font-size:10px;color:#556;">${esc(r.descr||'')}</td>
    <td style="font-size:10px;">${r.dynamic_sw==='Y'?'<span style="color:#ffaa00;">Dynamic</span>':'Static'}</td>
    <td style="font-size:10px;color:#445;">${esc(r.rolestatus_label||'')}</td>
  </tr>`).join('');
  $('tblRoles').innerHTML = h+`<table><thead><tr>
    <th>Role</th><th>Description</th><th>Assignment</th><th>Status</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function setTab(name) {
  ['overview','roles'].forEach(n => {
    const tab = document.querySelector(`.tab[onclick*="${n}"]`);
    if (tab) tab.classList.toggle('on', n === name);
    const cap = n.charAt(0).toUpperCase()+n.slice(1);
    const p = $(`pane${cap}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

(async () => {
  try {
    const cfg = await api('/api/runtime/config').catch(()=>({envs:['HCM','FSCM']}));
    $('envSel').innerHTML = (cfg.envs||['HCM','FSCM']).map(e=>`<option value="${e}">${e}</option>`).join('');
  } catch(e) { $('envSel').innerHTML='<option value="HCM">HCM</option>'; }

  doSearch();

  const pathMatch = window.location.pathname.match(/\\/admin\\/operator\\/(.+)$/);
  const opParam   = new URLSearchParams(window.location.search).get('oprid') || (pathMatch ? decodeURIComponent(pathMatch[1]) : null);
  if (opParam) {
    $('searchInput').value = opParam;
    await doSearch();
    const el = document.getElementById(`oi_${opParam}`);
    loadOp(opParam, el||null);
  }
})();
</script>""")


@router.get("/role", response_class=HTMLResponse)
@router.get("/role/{rolename:path}", response_class=HTMLResponse)
def admin_role(rolename: str = None):
    return _shell("Role Explorer", "security", noscroll=True, content="""\
<style>
*{box-sizing:border-box;}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;padding:0;height:100vh;display:flex;flex-direction:column;}
h1{color:#00e5ff;text-shadow:0 0 12px #00e5ff;letter-spacing:4px;margin:0;font-size:18px;}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px;}
nav a{color:#00e5ff;text-decoration:none;font-size:12px;} nav a:hover{text-decoration:underline;}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.main{display:flex;flex:1;overflow:hidden;}
.sidebar{width:280px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0;}
.content{flex:1;overflow:auto;padding:16px;}
select,input[type=text]{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:4px 8px;font-size:12px;}
input:focus,select:focus{outline:none;border-color:#00e5ff;}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold;}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff;}
.lbl{font-size:10px;color:#667;text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:3px;}
.role-item{padding:6px 8px;cursor:pointer;border-radius:2px;display:flex;justify-content:space-between;align-items:center;gap:4px;}
.role-item:hover{background:rgba(0,229,255,.07);}
.role-item.sel{background:rgba(0,229,255,.12);border-left:2px solid #00e5ff;}
.role-name{font-family:monospace;font-size:11px;color:#d7faff;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.role-descr{font-size:9px;color:#445;margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.role-cnt{font-size:10px;color:#00e5ff;font-weight:bold;min-width:24px;text-align:right;flex-shrink:0;}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin:12px 0;}
.stat-box{background:#0b1b24;border:1px solid #00e5ff22;padding:10px;border-radius:2px;}
.stat-box .sv{font-size:22px;font-weight:bold;color:#00e5ff;line-height:1;}
.stat-box .sl{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
table{border-collapse:collapse;width:100%;font-size:12px;}
th{border-bottom:1px solid #00e5ff33;padding:5px 8px;text-align:left;color:#00e5ff;font-size:10px;text-transform:uppercase;letter-spacing:1px;}
td{border-bottom:1px solid #1e3040;padding:5px 8px;}
tr:hover td{background:rgba(0,229,255,.04);}
.mono{font-family:monospace;}
.empty{color:#445;font-style:italic;padding:16px 0;font-size:12px;}
.warn-msg{color:#ffaa00;font-size:11px;margin:2px 0;}
.tab-row{display:flex;gap:0;margin:10px 0 0;border-bottom:1px solid #00e5ff22;}
.tab{padding:5px 14px;cursor:pointer;font-size:11px;color:#556;border-bottom:2px solid transparent;margin-bottom:-1px;}
.tab.on{color:#00e5ff;border-bottom-color:#00e5ff;}
.pane{display:none;} .pane.on{display:block;}
a.obj-link{color:#00e5ff;text-decoration:none;font-family:monospace;font-size:11px;}
a.obj-link:hover{text-decoration:underline;}
.badge{display:inline-block;padding:2px 8px;border-radius:2px;font-size:10px;font-weight:bold;border:1px solid;}
.b-active{border-color:#00cc66;color:#00cc66;background:#002800;}
.b-inactive{border-color:#556;color:#556;background:#1a1a1a;}
.b-query{border-color:#ffaa00;color:#ffaa00;background:#2a1800;}
.b-general{border-color:#00e5ff44;color:#8ab;background:#001830;}
.kv{display:flex;margin:4px 0;font-size:12px;}
.kl{color:#445;min-width:160px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;}
.kv-val{color:#d7faff;font-family:monospace;word-break:break-all;}
.flag-on{color:#00cc66;font-size:10px;} .flag-off{color:#334;font-size:10px;}
.search-row{display:flex;gap:6px;margin-bottom:8px;}
.search-row input{flex:1;}
.count-tag{font-size:10px;color:#445;margin-bottom:6px;}
</style>
<div class="main">
  <!-- Sidebar -->
  <div class="sidebar">
    <h2>Role Search</h2>
    <div class="search-row">
      <input type="text" id="searchInput" placeholder="Role name or description…" oninput="debSearch()" onkeydown="if(event.key==='Enter')doSearch()">
      <button class="sec" onclick="doSearch()" style="font-size:10px;">Go</button>
    </div>
    <div class="count-tag" id="searchCount"></div>
    <div id="roleList"><div class="empty">Enter a role name to search.<br>Leave blank to list all roles.</div></div>
  </div>
  <!-- Content -->
  <div class="content">
    <div id="placeholder" style="padding:40px 0;text-align:center;">
      <div style="font-size:40px;margin-bottom:12px;opacity:.3;">&#9632;</div>
      <div style="color:#445;font-size:13px;">Select a role from the sidebar.</div>
      <div style="color:#334;font-size:11px;margin-top:6px;">853 roles · 6,088 assignments in HCM.</div>
    </div>
    <div id="roleContent" style="display:none;">
      <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
        <span id="roleTitle" style="font-size:20px;font-weight:bold;color:#00e5ff;font-family:monospace;max-width:100%;word-break:break-word;"></span>
        <span id="roleStatusBadge"></span>
        <span id="roleTypeBadge"></span>
        <a id="roleObjLink" href="#" style="margin-left:auto;font-size:11px;color:#00e5ff;text-decoration:none;">Object Page &#8599;</a>
      </div>
      <div id="roleDescr" style="color:#8ab;font-size:12px;margin-bottom:12px;"></div>
      <div class="stat-grid" id="statGrid"></div>
      <div class="tab-row">
        <div class="tab on" onclick="setTab('overview')">Overview</div>
        <div class="tab"    onclick="setTab('members')">Members</div>
        <div class="tab"    onclick="setTab('permlists')">Permission Lists</div>
      </div>
      <div id="paneOverview"  class="pane on"><div id="tblOverview"></div></div>
      <div id="paneMembers"   class="pane"><div id="tblMembers"></div></div>
      <div id="panePermlists" class="pane"><div id="tblPermlists"></div></div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
function env() { return $('envSel').value || 'HCM'; }
let debTimer = null;
function debSearch() { clearTimeout(debTimer); debTimer = setTimeout(doSearch, 200); }
function esc(s) {
  const d = document.createElement('div'); d.textContent = String(s ?? ''); return d.innerHTML;
}
function empty(msg) { return `<div class="empty">${msg||'No data.'}</div>`; }

let currentRole = null;

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function doSearch() {
  const q = $('searchInput').value.trim();
  $('roleList').innerHTML = '<div class="empty">Searching…</div>';
  $('searchCount').textContent = '';
  try {
    const d = await api(`/api/role/search?env=${env()}&q=${encodeURIComponent(q)}&limit=200`);
    const items = d.items || [];
    $('searchCount').textContent = `${items.length} role${items.length===1?'':'s'}`;
    if (!items.length) { $('roleList').innerHTML = '<div class="empty">No roles found.</div>'; return; }
    $('roleList').innerHTML = items.map(it => `
      <div class="role-item" id="ri_${esc(it.rolename)}" onclick="loadRole('${esc(it.rolename).replace(/'/g,"\\\'")}', this)">
        <div style="min-width:0;overflow:hidden;">
          <div class="role-name">${esc(it.rolename)}</div>
          ${it.descr ? `<div class="role-descr">${esc(it.descr)}</div>` : ''}
        </div>
        ${it.member_count != null ? `<span class="role-cnt">${it.member_count}</span>` : ''}
      </div>`).join('');
  } catch(e) {
    $('roleList').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

function clearRole() {
  $('placeholder').style.display = '';
  $('roleContent').style.display = 'none';
  currentRole = null;
}

async function loadRole(name, el) {
  if (el) {
    document.querySelectorAll('.role-item').forEach(e => e.classList.remove('sel'));
    el.classList.add('sel');
  }
  currentRole = name;
  $('placeholder').style.display = 'none';
  $('roleContent').style.display = '';
  $('roleTitle').textContent = name;
  $('roleDescr').textContent = '';
  $('roleStatusBadge').textContent = '';
  $('roleTypeBadge').textContent = '';
  $('statGrid').innerHTML = '<div style="color:#445;font-size:11px;">Loading…</div>';
  $('tblOverview').innerHTML = '<div class="empty">Loading…</div>';
  $('tblMembers').innerHTML = '<div class="empty">Loading…</div>';
  $('tblPermlists').innerHTML = '<div class="empty">Loading…</div>';
  $('roleObjLink').href = `/admin/object/role/${encodeURIComponent(name)}`;
  history.replaceState(null, '', `/admin/role/${encodeURIComponent(name)}`);

  try {
    const [det, mem, perm] = await Promise.allSettled([
      api(`/api/role/${encodeURIComponent(name)}?env=${env()}`),
      api(`/api/role/${encodeURIComponent(name)}/members?env=${env()}`),
      api(`/api/role/${encodeURIComponent(name)}/permissionlists?env=${env()}`),
    ]);

    const d = det.status === 'fulfilled' ? det.value : {item: null, warnings: [{message: det.reason?.message}]};
    const m = mem.status === 'fulfilled' ? mem.value : {items: [], warnings: [{message: mem.reason?.message}]};
    const p = perm.status === 'fulfilled' ? perm.value : {items: [], warnings: [{message: perm.reason?.message}]};

    const item = d.item || {};

    $('roleDescr').textContent = item.descr || '';
    $('roleStatusBadge').innerHTML = item.rolestatus_label
      ? `<span class="badge b-${item.rolestatus_label.toLowerCase()}">${esc(item.rolestatus_label)}</span>`
      : '';
    $('roleTypeBadge').innerHTML = item.roletype_label
      ? `<span class="badge ${item.roletype_label.includes('Query') || item.roletype_label.includes('PeopleCode') ? 'b-query' : 'b-general'}">${esc(item.roletype_label)}</span>`
      : '';

    const memberCount = (m.items || []).length;
    $('statGrid').innerHTML = [
      {v: memberCount, l: 'Members (Users)'},
      {v: (p.items || []).length || '—', l: 'Permission Lists'},
    ].map(s => `<div class="stat-box"><div class="sv">${s.v}</div><div class="sl">${s.l}</div></div>`).join('');

    renderOverview(item, d.warnings || []);
    renderMembers(m.items || [], m.warnings || []);
    renderPermlists(p.items || [], p.warnings || []);
  } catch(e) {
    $('tblOverview').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
    $('statGrid').innerHTML = '';
  }
}

function renderOverview(item, warns) {
  let h = warns.map(w => `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
  if (!item || !item.rolename) { $('tblOverview').innerHTML = h + '<div class="empty">Role not found.</div>'; return; }

  const yn = v => v === 'Y' ? '<span class="flag-on">&#10003; Yes</span>' : '<span class="flag-off">No</span>';
  const on = v => v === 'Y' ? '<span class="flag-on">&#10003; On</span>' : '<span class="flag-off">Off</span>';

  h += `
    <h2>Identity</h2>
    <div class="kv"><span class="kl">Role Name</span><span class="kv-val">${esc(item.rolename)}</span></div>
    <div class="kv"><span class="kl">Description</span><span class="kv-val">${esc(item.descr||'—')}</span></div>
    <div class="kv"><span class="kl">Type</span><span class="kv-val">${esc(item.roletype_label||'—')}</span></div>
    <div class="kv"><span class="kl">Status</span><span class="kv-val">${esc(item.rolestatus_label||'—')}</span></div>
    <div class="kv"><span class="kl">Last Updated</span><span class="kv-val">${esc((item.lastupddttm||'').replace('T',' ').substr(0,19)||'—')}</span></div>
    <div class="kv"><span class="kl">Updated By</span><span class="kv-val">${esc(item.lastupdoprid||'—')}</span></div>`;

  if (item.roletype_label?.includes('Query') && item.qryname) {
    h += `
    <h2>Dynamic Membership Rule</h2>
    <div class="kv"><span class="kl">Query Name</span><span class="kv-val">${esc(item.qryname)}</span></div>
    ${item.qryname_sec ? `<div class="kv"><span class="kl">Security Query</span><span class="kv-val">${esc(item.qryname_sec)}</span></div>` : ''}
    <div class="kv"><span class="kl">Query Rule Active</span><span class="kv-val">${on(item.role_query_rule_on)}</span></div>`;
  }

  if (item.recname || item.fieldname) {
    h += `
    <h2>Dynamic Rule — Record/Field</h2>
    <div class="kv"><span class="kl">Record</span><span class="kv-val"><a class="obj-link" href="/admin/record/${esc(item.recname)}">${esc(item.recname||'—')}</a></span></div>
    <div class="kv"><span class="kl">Field</span><span class="kv-val">${esc(item.fieldname||'—')}</span></div>`;
  }

  if (item.pc_function_name) {
    h += `
    <h2>PeopleCode Rule</h2>
    <div class="kv"><span class="kl">Function</span><span class="kv-val">${esc(item.pc_function_name)}</span></div>
    <div class="kv"><span class="kl">Event Type</span><span class="kv-val">${esc(item.pc_event_type||'—')}</span></div>
    <div class="kv"><span class="kl">PeopleCode Rule Active</span><span class="kv-val">${on(item.role_pcode_rule_on)}</span></div>`;
  }

  h += `
    <h2>Permissions</h2>
    <div class="kv"><span class="kl">Allow Notifications</span><span class="kv-val">${yn(item.allownotify)}</span></div>
    <div class="kv"><span class="kl">Allow Lookup</span><span class="kv-val">${yn(item.allowlookup)}</span></div>
    <div class="kv"><span class="kl">LDAP Rule Active</span><span class="kv-val">${on(item.ldap_rule_on)}</span></div>`;

  if (item.descrlong) {
    h += `<h2>Description</h2><div style="font-size:12px;color:#8ab;line-height:1.6;white-space:pre-wrap;">${esc(item.descrlong)}</div>`;
  }

  $('tblOverview').innerHTML = h;
}

function renderMembers(items, warns) {
  let h = warns.filter(w => w.message).map(w => `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
  if (!items.length) {
    $('tblMembers').innerHTML = h + '<div class="empty">No members (this role may be assigned dynamically via query, or no users have been assigned).</div>';
    return;
  }
  const rows = items.map(r => `<tr>
    <td class="mono"><a class="obj-link" href="/admin/tracing?oprid=${esc(r.roleuser)}&env=${esc(env())}">${esc(r.roleuser)}</a></td>
    <td style="font-size:10px;">${r.dynamic_sw === 'Y' ? '<span style="color:#ffaa00;">Dynamic</span>' : 'Static'}</td>
    <td><a class="obj-link" href="/admin/object/operator/${esc(r.roleuser)}" style="font-size:10px;">Profile &#8599;</a></td>
  </tr>`).join('');
  $('tblMembers').innerHTML = h + `<table><thead><tr>
    <th>User (OPRID)</th><th>Assignment Type</th><th>Links</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderPermlists(items, warns) {
  let h = warns.filter(w => w.message).map(w => `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`).join('');
  if (!items.length) {
    $('tblPermlists').innerHTML = h + '<div class="empty">No permission lists found (PSROLECLASS not accessible, or role has no permission lists).</div>';
    return;
  }
  const rows = items.map(r => `<tr>
    <td class="mono"><a class="obj-link" href="/admin/object/permissionlist/${esc(r.classid)}">${esc(r.classid)}</a></td>
    <td style="font-size:10px;">${r.dynamic_sw === 'Y' ? '<span style="color:#ffaa00;">Dynamic</span>' : 'Static'}</td>
  </tr>`).join('');
  $('tblPermlists').innerHTML = h + `<table><thead><tr>
    <th>Permission List</th><th>Type</th>
  </tr></thead><tbody>${rows}</tbody></table>`;
}

function setTab(name) {
  ['overview','members','permlists'].forEach(n => {
    const tab = document.querySelector(`.tab[onclick*="${n}"]`);
    if (tab) tab.classList.toggle('on', n === name);
    const cap = n.charAt(0).toUpperCase() + n.slice(1);
    const p = $(`pane${cap}`);
    if (p) p.classList.toggle('on', n === name);
  });
}

(async () => {
  try {
    const cfg = await api('/api/runtime/config').catch(() => ({envs:['HCM','FSCM']}));
    $('envSel').innerHTML = (cfg.envs||['HCM','FSCM']).map(e => `<option value="${e}">${e}</option>`).join('');
  } catch(e) {
    $('envSel').innerHTML = '<option value="HCM">HCM</option>';
  }

  // Pre-load all roles in sidebar on start
  doSearch();

  // URL param: /admin/role/ROLENAME
  const params = new URLSearchParams(window.location.search);
  const rParam = params.get('role');
  const pathMatch = window.location.pathname.match(/\\/admin\\/role\\/(.+)$/);
  const roleName = rParam || (pathMatch ? decodeURIComponent(pathMatch[1]) : null);
  if (roleName) {
    $('searchInput').value = roleName;
    await doSearch();
    const el = document.getElementById(`ri_${roleName}`);
    loadRole(roleName, el || null);
  }
})();
</script>""")


@router.get("/peoplecode", response_class=HTMLResponse)
@router.get("/peoplecode/{reference:path}", response_class=HTMLResponse)
def admin_peoplecode(reference: str = None):
    return _shell("PeopleCode Explorer", "objects", noscroll=True, content="""\
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#ccc;font-family:monospace;font-size:13px}
nav{padding:8px 16px;background:#111;border-bottom:1px solid #222;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
nav a{color:#7bf;text-decoration:none;font-size:12px}
nav a:hover{color:#fff}
.topbar{display:flex;gap:8px;padding:12px 16px;background:#111;border-bottom:1px solid #222;align-items:center;flex-wrap:wrap}
.topbar input,.topbar select{background:#1a1a1a;border:1px solid #333;color:#ccc;padding:5px 8px;font-family:monospace;font-size:12px;border-radius:3px}
.topbar input[type=text]{width:280px}
.topbar button{background:#1a3a5a;border:1px solid #336;color:#8cf;padding:5px 14px;cursor:pointer;border-radius:3px;font-size:12px}
.topbar button:hover{background:#2a4a7a}
.chip-row{display:flex;gap:6px;flex-wrap:wrap;padding:8px 16px;background:#111;border-bottom:1px solid #222}
.type-chip{padding:3px 9px;border-radius:10px;font-size:11px;cursor:pointer;border:1px solid;opacity:0.5;transition:opacity .15s}
.type-chip.on{opacity:1}
.layout{display:flex;flex:1;min-height:0;}
.sidebar{width:400px;min-width:280px;border-right:1px solid #222;overflow-y:auto;flex-shrink:0}
.detail-pane{flex:1;overflow-y:auto;padding:16px}
.result-item{padding:8px 12px;border-bottom:1px solid #1a1a1a;cursor:pointer;display:flex;flex-direction:column;gap:3px}
.result-item:hover{background:#151515}
.result-item.selected{background:#1a2a3a}
.result-name{font-size:12px;color:#e0e0e0;font-family:monospace}
.result-detail{font-size:11px;color:#556;display:flex;gap:8px;align-items:center}
.type-badge{padding:1px 6px;border-radius:8px;font-size:10px;border:1px solid}
.event-badge{color:#aaa;font-size:10px}
.parent-badge{color:#888;font-size:10px}
.muted{color:#444;padding:16px;font-size:11px}
.stat{color:#667;font-size:11px;padding:4px 12px}
.obj-card{background:#111;border:1px solid #222;border-radius:4px;padding:16px;margin-bottom:12px}
.obj-card h3{color:#8ab;font-size:13px;margin-bottom:10px}
.kl{color:#667;font-size:11px;width:130px;display:inline-block}
.kv{padding:3px 0}
.kv-val{color:#ccc}
.kv-val a{color:#7bf;text-decoration:none}
.kv-val a:hover{color:#fff}
.ref{font-size:11px;color:#556;font-family:monospace;word-break:break-all}
pre{background:#0a0a0a;border:1px solid #222;padding:12px;border-radius:3px;overflow-x:auto;font-size:11px;line-height:1.5;white-space:pre-wrap}
</style>
<div class="ds-toolbar">
  <select id="envSel"></select>
  <input type="text" id="searchQ" placeholder="Search PeopleCode (name, event, object)..." oninput="schedSearch()" style="flex:1;">
  <button onclick="doSearch()">Search</button>
  <span id="resultCount" class="stat"></span>
</div>

<div class="chip-row" id="typeChips"></div>

<div class="layout">
  <div class="sidebar">
    <div id="results"><div class="muted">Enter a search term to find PeopleCode programs.</div></div>
  </div>
  <div class="detail-pane" id="detail">
    <div class="muted">Select a PeopleCode program to view details.</div>
  </div>
</div>

<script>
const TYPE_COLORS = {
  'Record':              {bg:'#001830', border:'#00e5ff44', color:'#8ab'},
  'Component':           {bg:'#1a1800', border:'#aaaa00',   color:'#aaaa00'},
  'Application Engine':  {bg:'#0d1a00', border:'#44aa00',   color:'#88cc55'},
  'Handler':             {bg:'#001a14', border:'#00cc88',    color:'#00cc88'},
  'Subscription':        {bg:'#1a0030', border:'#cc66ff',    color:'#cc66ff'},
  'Component Interface': {bg:'#1a0010', border:'#ff4488',    color:'#ff88aa'},
  'Menu':                {bg:'#1a1000', border:'#cc8800',    color:'#ccaa55'},
  'Application Package': {bg:'#001a18', border:'#00aaaa',    color:'#00aaaa'},
};

let _allTypes = new Set();
let _activeTypes = new Set();
let _searchTimer = null;
let _items = [];
let _selectedRef = null;
let _pcOffset = 0;
let _pcHasMore = false;
const _PC_LIMIT = 500;

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function api(url) { return fetch(url).then(r => r.json()); }
function env() { return document.getElementById('envSel').value; }

function schedSearch() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(doSearch, 350);
}

function buildTypeChips() {
  const row = document.getElementById('typeChips');
  row.innerHTML = '';
  [..._allTypes].sort().forEach(t => {
    const cfg = TYPE_COLORS[t] || {bg:'#111', border:'#555', color:'#aaa'};
    const chip = document.createElement('span');
    chip.className = 'type-chip' + (_activeTypes.has(t) ? ' on' : '');
    chip.style.cssText = `background:${cfg.bg};border-color:${cfg.border};color:${cfg.color}`;
    chip.textContent = t;
    chip.onclick = () => toggleType(t);
    row.appendChild(chip);
  });
}

function toggleType(t) {
  if (_activeTypes.has(t)) _activeTypes.delete(t);
  else _activeTypes.add(t);
  buildTypeChips();
  renderResults();
}

function renderResults() {
  const results = document.getElementById('results');
  const filtered = _activeTypes.size > 0
    ? _items.filter(i => _activeTypes.has(i.object_type_label))
    : _items;

  const moreNote = _pcHasMore ? ` (+more)` : '';
  document.getElementById('resultCount').textContent =
    `${filtered.length} / ${_items.length} programs${moreNote}`;

  if (!filtered.length) {
    results.innerHTML = '<div class="muted">No results.</div>';
    return;
  }

  let html = filtered.map(item => {
    const cfg = TYPE_COLORS[item.object_type_label] || {bg:'#111', border:'#555', color:'#aaa'};
    const isSelected = item.encoded_reference === _selectedRef;
    return `<div class="result-item${isSelected ? ' selected' : ''}" onclick="loadPC(${JSON.stringify(item.encoded_reference)})">
      <div class="result-name">${esc(item.reference || item.objectvalue1)}</div>
      <div class="result-detail">
        <span class="type-badge" style="background:${cfg.bg};border-color:${cfg.border};color:${cfg.color}">${esc(item.object_type_label)}</span>
        ${item.event_label || item.event ? `<span class="event-badge">${esc(item.event_label || item.event)}</span>` : ''}
        ${item.parent_name ? `<span class="parent-badge">→ ${esc(item.parent_name)}</span>` : ''}
      </div>
    </div>`;
  }).join('');

  if (_pcHasMore && _activeTypes.size === 0) {
    html += `<div style="padding:8px;text-align:center">
      <button onclick="loadMorePC()" style="font-size:11px;padding:4px 12px">Load more (offset ${_pcOffset})…</button>
    </div>`;
  }

  results.innerHTML = html;
}

async function doSearch() {
  const q = document.getElementById('searchQ').value.trim();
  if (!q) {
    document.getElementById('results').innerHTML = '<div class="muted">Enter a search term.</div>';
    document.getElementById('resultCount').textContent = '';
    _items = []; _pcOffset = 0; _pcHasMore = false;
    return;
  }
  document.getElementById('results').innerHTML = '<div class="muted">Searching...</div>';
  _pcOffset = 0;

  const data = await api(`/api/peoplesoft/peoplecode?env=${env()}&q=${encodeURIComponent(q)}&limit=${_PC_LIMIT}&offset=0`).catch(() => ({items:[], has_more: false}));
  _items = data.items || [];
  _pcHasMore = data.has_more || false;
  _pcOffset = _items.length;

  _allTypes = new Set(_items.map(i => i.object_type_label).filter(Boolean));
  _activeTypes = new Set();
  buildTypeChips();
  renderResults();
}

async function loadMorePC() {
  const q = document.getElementById('searchQ').value.trim();
  const data = await api(`/api/peoplesoft/peoplecode?env=${env()}&q=${encodeURIComponent(q)}&limit=${_PC_LIMIT}&offset=${_pcOffset}`).catch(() => ({items:[], has_more: false}));
  const newItems = data.items || [];
  _pcHasMore = data.has_more || false;
  _pcOffset += newItems.length;
  _items = [..._items, ...newItems];
  newItems.forEach(i => { if (i.object_type_label) _allTypes.add(i.object_type_label); });
  buildTypeChips();
  renderResults();
}

async function loadPC(encodedRef) {
  _selectedRef = encodedRef;
  renderResults();

  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  // Update URL
  history.replaceState(null, '', `/admin/peoplecode/${encodeURIComponent(encodedRef)}`);

  const data = await api(`/api/peoplesoft/object/peoplecode/${encodeURIComponent(encodedRef)}?env=${env()}`).catch(e => null);
  if (!data) {
    detail.innerHTML = '<div class="muted">Failed to load.</div>';
    return;
  }

  const uom = data._uom || {};
  const raw = uom._metadata?.raw || {};
  const rels = uom._relationships || {};
  const cfg = TYPE_COLORS[raw.object_type_label] || {bg:'#111', border:'#555', color:'#aaa'};

  let h = `<div class="obj-card">
    <h3>
      <span class="type-badge" style="background:${cfg.bg};border-color:${cfg.border};color:${cfg.color};margin-right:6px">${esc(raw.object_type_label)}</span>
      ${esc(raw.reference || uom.name)}
    </h3>
    <div class="ref">${esc(raw.reference || '')}</div>
    <div style="margin-top:10px">
      <div class="kv"><span class="kl">Event</span><span class="kv-val">${esc(raw.event_label || raw.event || '—')}</span></div>
      <div class="kv"><span class="kl">Scope</span><span class="kv-val">${esc(raw.event_scope || '—')}</span></div>
      <div class="kv"><span class="kl">Subtype</span><span class="kv-val">${esc(raw.subtype || '—')}</span></div>
      <div class="kv"><span class="kl">Path</span><span class="kv-val">${esc(raw.semantic_path_text || '—')}</span></div>
      <div class="kv"><span class="kl">Parent Type</span><span class="kv-val">${esc(raw.parent_type || '—')}</span></div>
      <div class="kv"><span class="kl">Parent</span><span class="kv-val">${raw.parent_name && raw.parent_type
        ? `<a href="/admin/object/${esc(raw.parent_type)}/${encodeURIComponent(raw.parent_name)}">${esc(raw.parent_name)}</a>`
        : esc(raw.parent_name || '—')}</span></div>
      <div class="kv"><span class="kl">Last Updated</span><span class="kv-val">${esc(raw.lastupddttm || '—')}</span></div>
      <div class="kv"><span class="kl">Updated By</span><span class="kv-val">${esc(raw.lastupdoprid || '—')}</span></div>
    </div>
    <div style="margin-top:10px">
      <a href="/admin/object/peoplecode/${encodeURIComponent(encodedRef)}" style="color:#7bf;font-size:11px">Open in Object Explorer →</a>
    </div>
  </div>`;

  // Source
  const src = raw.source;
  if (src) {
    h += `<div class="obj-card"><h3>Source</h3><pre>${highlightPeopleCode(src)}</pre></div>`;
  } else {
    h += `<div class="obj-card"><h3>Source</h3><div class="muted">Source not available (PSPCMTXT may not be accessible or this program has no text).</div></div>`;
  }

  // References
  const refs = rels.references || {};
  const refItems = Object.entries(refs).flatMap(([type, names]) =>
    names.map(n => ({type, name: n}))
  );
  if (refItems.length) {
    h += `<div class="obj-card"><h3>References (${refItems.length})</h3>`;
    refItems.forEach(r => {
      const url = `/admin/object/${encodeURIComponent(r.type)}/${encodeURIComponent(r.name)}`;
      h += `<div class="kv"><span class="kl">${esc(r.type)}</span><span class="kv-val"><a href="${esc(url)}">${esc(r.name)}</a></span></div>`;
    });
    h += '</div>';
  }

  // Calls
  const calls = rels.calls || [];
  if (calls.length) {
    h += `<div class="obj-card"><h3>Calls (${calls.length})</h3>`;
    calls.forEach(c => { h += `<div class="kv"><span class="kl">${esc(c.name)}</span><span class="kv-val">${esc(c.count)}</span></div>`; });
    h += '</div>';
  }

  detail.innerHTML = h;
}

function highlightPeopleCode(source) {
    if (!source) return '';
    function esc2(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    const KEYWORDS = /\\b(If|Else|ElseIf|End-If|For|End-For|While|End-While|Break|Return|Function|End-Function|Local|Global|Component|import|class|method|property|get|set|End-class|try|catch|End-try|throw|CreateObject|GetLevel0|GetRowset|CreateRowset|CreateRecord|CreateArray|CreateSQL|GetSQL|SQLExec|MessageBox|WinMessage|Error|Warning|CallAppEngine|Transfer|DoModal|DoSaveNow|CommitWork|RetrieveFile|PutFile)\\b/g;
    const BUILTINS = /\\b(SQLExec|CreateSQL|GetSQL|CallAppEngine|Transfer|DoModal|CreateRecord|GetRecord|GetField|GetComponent|GetRowset|GetLevel0|MessageBox|WinMessage|CommitWork|Error|Warning|CreateObject|CreateArray|CreateRowset|Substring|Len|Left|Right|Upper|Lower|NumberToString|StringToNumber|Char|Code|Find|DateAdd|DateDiff|Date|Time|DateTime|Today|Now|IsDate|IsNumber|MsgGet|MsgGetText)\\b/g;
    const parts = [];
    let i = 0;
    while (i < source.length) {
      if (source.startsWith('/*', i)) {
        const e = source.indexOf('*/', i+2); const en = e<0?source.length:e+2;
        parts.push(`<span style="color:#6a9955">${esc2(source.slice(i,en))}</span>`); i=en;
      } else if (source[i] === '"') {
        let j=i+1; while(j<source.length&&source[j]!=='"')j++;
        parts.push(`<span style="color:#ce9178">${esc2(source.slice(i,j+1))}</span>`); i=j+1;
      } else {
        let j=i+1; while(j<source.length&&source[j]!=='"'&&!source.startsWith('/*',j))j++;
        let chunk = esc2(source.slice(i,j));
        chunk = chunk.replace(KEYWORDS, m=>`<span style="color:#569cd6">${m}</span>`);
        chunk = chunk.replace(BUILTINS, m=>`<span style="color:#dcdcaa">${m}</span>`);
        chunk = chunk.replace(/\\b(\\d+(\\.\\d+)?)\\b/g, m=>`<span style="color:#b5cea8">${m}</span>`);
        parts.push(chunk); i=j;
      }
    }
    return parts.join('');
}

(async () => {
  // Env selector
  const cfg = await api('/api/peoplesoft/summary').catch(() => null);
  if (cfg?.environments) {
    document.getElementById('envSel').innerHTML = cfg.environments
      .map(e => `<option value="${e}">${e}</option>`).join('');
  }

  // URL param: /admin/peoplecode/REFERENCE
  const params = new URLSearchParams(window.location.search);
  const pathMatch = window.location.pathname.match(/\\/admin\\/peoplecode\\/(.+)$/);
  const initRef = params.get('ref') || (pathMatch ? decodeURIComponent(pathMatch[1]) : null);
  const initQ = params.get('q') || '';

  if (initQ) {
    document.getElementById('searchQ').value = initQ;
    await doSearch();
  }
  if (initRef) {
    await loadPC(initRef);
  }
})();
</script>""")


@router.get("/infra", response_class=HTMLResponse)
def admin_infra():
    return _shell("Infrastructure", "infra", content="""
<div class="ds-page-header">
  <div class="ds-page-title">Infrastructure</div>
  <div class="ds-page-subtitle">Host metrics, services, containers, and Oracle health</div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">

  <div class="card">
    <h2>Host Metrics <button onclick="loadHost()" style="float:right;font-size:11px">Refresh</button></h2>
    <div id="hostMetrics" style="font-size:12px;color:#6c7086">Loading...</div>
  </div>

  <div class="card">
    <h2>Services <button onclick="loadServices()" style="float:right;font-size:11px">Refresh</button></h2>
    <table id="servicesTable" style="font-size:12px;width:100%">
      <thead><tr><th>Service</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="serviceRows"></tbody>
    </table>
    <div style="margin-top:8px">
      <button onclick="reloadNginx()" style="font-size:11px;background:#313244">Reload NGINX Config</button>
    </div>
  </div>

  <div class="card">
    <h2>Containers <button onclick="loadContainers()" style="float:right;font-size:11px">Refresh</button></h2>
    <table id="containersTable" style="font-size:12px;width:100%">
      <thead><tr><th>Name</th><th>Image</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody id="containerRows"></tbody>
    </table>
  </div>

  <div class="card">
    <h2>Oracle Health <button onclick="loadOracleHealth()" style="float:right;font-size:11px">Refresh</button></h2>
    <div id="oracleHealth" style="font-size:12px;color:#6c7086">Loading...</div>
  </div>

</div>

<div class="card" style="margin-top:16px">
  <h2>Container Logs
    <select id="containerLogName" style="font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
      <option value="authelia">authelia</option>
    </select>
    <input id="containerLogLines" type="number" value="50" min="10" max="500" style="width:60px;font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
    <button onclick="loadContainerLogs()" style="font-size:11px">Load</button>
  </h2>
  <pre id="containerLogOutput" style="font-size:11px;max-height:300px;overflow:auto;background:#0d0d14;padding:8px;border-radius:4px;color:#a6e3a1">Select a container and click Load.</pre>
</div>

<div class="card" style="margin-top:16px">
  <h2>Journal Log
    <input id="journalUnits" value="nginx,deathstar-api" style="font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px;width:220px">
    <input id="journalLines" type="number" value="80" min="10" max="500" style="width:60px;font-size:11px;background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;padding:2px 4px">
    <button onclick="loadJournal()" style="font-size:11px">Load</button>
  </h2>
  <pre id="journalOutput" style="font-size:11px;max-height:300px;overflow:auto;background:#0d0d14;padding:8px;border-radius:4px;color:#cdd6f4">Click Load to fetch journal entries.</pre>
</div>

<script>
async function api(path, opts = {}) {
    const res = await fetch(path, opts);
    if (!res.ok) { const t = await res.text(); console.error(path, t); return null; }
    return res.json();
}

function fmtBytes(b) {
    if (b == null) return '?';
    const gb = b / 1073741824;
    return gb >= 1 ? gb.toFixed(1) + ' GB' : (b / 1048576).toFixed(0) + ' MB';
}

async function loadHost() {
    const d = await api('/api/metrics/host');
    if (!d) return;
    const mem = d.memory || {};
    const disk = d.disk || {};
    const load = d.loadavg || [0, 0, 0];
    const boot = d.boot_time ? new Date(d.boot_time * 1000).toLocaleString() : '?';
    document.getElementById('hostMetrics').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div><b>CPU</b>: ${d.cpu_percent?.toFixed(1)}%</div>
          <div><b>Load</b>: ${load.map(l => l.toFixed(2)).join(' / ')}</div>
          <div><b>Memory</b>: ${fmtBytes(mem.used)} / ${fmtBytes(mem.total)} (${mem.percent?.toFixed(1)}%)</div>
          <div><b>Disk /</b>: ${fmtBytes(disk.used)} / ${fmtBytes(disk.total)} (${disk.percent?.toFixed(1)}%)</div>
          <div style="grid-column:1/-1"><b>Boot time</b>: ${boot}</div>
        </div>`;
}

async function loadServices() {
    const rows = await api('/api/system/services');
    const tbody = document.getElementById('serviceRows');
    if (!tbody || !rows) return;
    tbody.innerHTML = '';
    rows.forEach(r => {
        const chip = r.active
            ? '<span class="chip" style="background:#a6e3a1;color:#1e1e2e">active</span>'
            : '<span class="chip" style="background:#f38ba8;color:#1e1e2e">inactive</span>';
        const btn = r.restartable
            ? `<button onclick="restartService('${r.unit}')" style="font-size:10px;background:#313244">Restart</button>`
            : '<span style="color:#6c7086;font-size:10px">—</span>';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.name}</td><td>${chip}</td><td>${btn}</td>`;
        tbody.appendChild(tr);
    });
}

async function restartService(unit) {
    if (!confirm(`Restart ${unit}?`)) return;
    const d = await api(`/api/system/service/${encodeURIComponent(unit)}/restart`, { method: 'POST' });
    alert(d ? `${unit}: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
    await loadServices();
}

async function reloadNginx() {
    if (!confirm('Reload NGINX config?')) return;
    const d = await api('/api/system/nginx/reload', { method: 'POST' });
    alert(d ? `NGINX reload: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
}

async function loadContainers() {
    const d = await api('/api/system/containers');
    const tbody = document.getElementById('containerRows');
    if (!tbody || !d) return;
    tbody.innerHTML = '';

    // Update log selector
    const sel = document.getElementById('containerLogName');
    const existing = new Set([...sel.options].map(o => o.value));

    (d.containers || []).forEach(c => {
        if (!existing.has(c.name)) {
            const opt = document.createElement('option');
            opt.value = c.name; opt.textContent = c.name;
            sel.appendChild(opt);
        }
        const chip = c.running
            ? '<span class="chip" style="background:#a6e3a1;color:#1e1e2e">running</span>'
            : '<span class="chip" style="background:#f38ba8;color:#1e1e2e">stopped</span>';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${c.name}</td><td style="font-size:10px;color:#6c7086">${(c.image||'').split('/').pop()}</td><td>${chip}</td>
            <td><button onclick="restartContainer('${c.name}')" style="font-size:10px;background:#313244">Restart</button></td>`;
        tbody.appendChild(tr);
    });
    if (!d.containers?.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="color:#6c7086;font-style:italic">No containers</td></tr>';
    }
}

async function restartContainer(name) {
    if (!confirm(`Restart container ${name}?`)) return;
    const d = await api(`/api/system/containers/${encodeURIComponent(name)}/restart`, { method: 'POST' });
    alert(d ? `${name}: ${d.status}${d.stderr ? '\\n' + d.stderr : ''}` : 'Request failed');
    await loadContainers();
}

async function loadOracleHealth() {
    const d = await api('/api/oracle/health');
    if (!d) { document.getElementById('oracleHealth').textContent = 'Failed to load'; return; }
    const items = [];
    if (d.instances) items.push(`<b>Instances:</b> ${d.instances.length}`);
    if (d.tablespace_ok != null) items.push(`<b>Tablespace OK:</b> ${d.tablespace_ok}`);
    if (d.status) items.push(`<b>Status:</b> ${d.status}`);
    if (d.warnings?.length) items.push(`<b>Warnings:</b> ${d.warnings.join(', ')}`);

    // Also fetch listener
    const listener = await api('/api/oracle/listener');
    if (listener) items.push(`<b>Listener:</b> ${listener.status || JSON.stringify(listener)}`);

    document.getElementById('oracleHealth').innerHTML = items.join('<br>') || JSON.stringify(d, null, 2);
}

async function loadContainerLogs() {
    const name = document.getElementById('containerLogName').value;
    const lines = document.getElementById('containerLogLines').value || 50;
    const d = await api(`/api/system/containers/${encodeURIComponent(name)}/logs?lines=${lines}`);
    const pre = document.getElementById('containerLogOutput');
    if (!d) { pre.textContent = 'Failed'; return; }
    pre.textContent = (d.lines || []).join('\\n') || '(no output)';
    pre.scrollTop = pre.scrollHeight;
}

async function loadJournal() {
    const units = document.getElementById('journalUnits').value;
    const lines = document.getElementById('journalLines').value || 80;
    const d = await api(`/api/logs/journal?units=${encodeURIComponent(units)}&lines=${lines}`);
    const pre = document.getElementById('journalOutput');
    if (!d) { pre.textContent = 'Failed'; return; }
    pre.textContent = (d.lines || []).join('\\n') || '(no output)';
    pre.scrollTop = pre.scrollHeight;
}

(async function() {
    await Promise.all([loadHost(), loadServices(), loadContainers(), loadOracleHealth()]);
})();
</script>""")


@router.get("/query", response_class=HTMLResponse)
def admin_query():
    return _shell("PS Query Explorer", "query", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="qSearch" type="text" placeholder="Search query name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="qFolder" style="width:160px"><option value="">All Folders</option></select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Queries</h2>
    <div id="list" class="muted">Search to load queries.</div>
  </div>
  <div class="content">
    <h2>Selected Query</h2>
    <div id="detail" class="muted">Select a query from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return res.json();
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function loadFolders() {
  const folders = await api(`/api/peoplesoft/query-folders?env=${ENV}`);
  if (!folders) return;
  const sel = document.getElementById('qFolder');
  folders.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f; opt.textContent = f;
    sel.appendChild(opt);
  });
}

async function doSearch() {
  const q = document.getElementById('qSearch').value.trim();
  const folder = document.getElementById('qFolder').value;
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a query.</span>';

  const rows = await api(`/api/peoplesoft/queries?env=${ENV}&q=${encodeURIComponent(q)}&folder=${encodeURIComponent(folder)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading queries.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';

  if (!rows.length) { list.innerHTML = '<span class="muted">No queries found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const folder_label = r.qryfolder && r.qryfolder.trim() ? r.qryfolder.trim() : '';
    const disabled = r.qrydisabled && r.qrydisabled !== '0' && r.qrydisabled !== 0;
    div.innerHTML = `
      <div class="item-name">${esc(r.qryname)} ${disabled ? '<span class="chip chip-warn">DISABLED</span>' : ''}</div>
      <div class="item-meta">${folder_label ? '<span class="chip chip-muted">'+esc(folder_label)+'</span> ' : ''}${r.descr ? esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:3px">
        ${r.selcount !== undefined ? '<span class="chip chip-info">'+r.selcount+' cols</span> ' : ''}
        ${r.bndcount !== undefined ? '<span class="chip chip-muted">'+r.bndcount+' binds</span>' : ''}
      </div>`;
    div.onclick = () => { selectQuery(r, div); };
    list.appendChild(div);
  });
}

function selectQuery(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const disabled = r.qrydisabled && r.qrydisabled !== '0' && r.qrydisabled !== 0;
  const folder = r.qryfolder && r.qryfolder.trim() ? r.qryfolder.trim() : '—';
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.qryname)}</span>
      ${disabled ? ' <span class="chip chip-warn">DISABLED</span>' : ' <span class="chip chip-ok">ENABLED</span>'}
      <a href="/admin/object/query/${encodeURIComponent(r.qryname)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.descr ? `<div style="color:#8ab;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="margin-bottom:10px">
      <span class="stat"><b>${esc(folder)}</b>Folder</span>
      ${r.selcount !== undefined ? `<span class="stat"><b>${r.selcount}</b>Output Cols</span>` : ''}
      ${r.bndcount !== undefined ? `<span class="stat"><b>${r.bndcount}</b>Bind Params</span>` : ''}
      ${r.expcount !== undefined ? `<span class="stat"><b>${r.expcount}</b>Expressions</span>` : ''}
    </div>
    ${r.lastupdoprid ? `<div style="font-size:11px;color:#445">Last updated by ${esc(r.lastupdoprid)}</div>` : ''}`;
}

(async function() {
  await loadFolders();
  await doSearch();
})();
</script>""")


@router.get("/tree", response_class=HTMLResponse)
def admin_tree():
    return _shell("Tree Explorer", "tree", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="tSearch" type="text" placeholder="Search tree name or description..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <input id="tSetid" type="text" placeholder="SETID filter..." style="width:120px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Trees</h2>
    <div id="list" class="muted">Search to load trees.</div>
  </div>
  <div class="content">
    <h2>Selected Tree</h2>
    <div id="detail" class="muted">Select a tree from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return res.json();
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('tSearch').value.trim();
  const setid = document.getElementById('tSetid').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a tree.</span>';

  const rows = await api(`/api/peoplesoft/trees?env=${ENV}&q=${encodeURIComponent(q)}&setid=${encodeURIComponent(setid)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading trees.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';
  if (!rows.length) { list.innerHTML = '<span class="muted">No trees found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const active = (r.eff_status || '').toUpperCase() === 'A';
    div.innerHTML = `
      <div class="item-name">${esc(r.treename)} <span class="chip ${active ? 'chip-ok' : 'chip-warn'}">${active ? 'ACTIVE' : 'INACTIVE'}</span></div>
      <div class="item-meta">${r.setid ? '<span class="chip chip-muted">'+esc(r.setid)+'</span> ' : ''}${r.descr ? esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:2px">${r.treestrctpnm ? esc(r.treestrctpnm) : ''}</div>`;
    div.onclick = () => selectTree(r, div);
    list.appendChild(div);
  });
}

function selectTree(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const active = (r.eff_status || '').toUpperCase() === 'A';
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.treename)}</span>
      <span class="chip ${active ? 'chip-ok' : 'chip-warn'}" style="margin-left:8px">${active ? 'ACTIVE' : 'INACTIVE'}</span>
      <a href="/admin/object/tree/${encodeURIComponent(r.treename)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.descr ? `<div style="color:#8ab;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="margin-bottom:10px">
      <span class="stat"><b>${esc(r.setid || '—')}</b>SETID</span>
      <span class="stat"><b>${esc(r.setcntrlvalue || '—')}</b>Set Control</span>
    </div>
    <div style="font-size:12px">
      ${r.treestrctpnm && r.treestrctpnm.trim() ? `<div style="margin-bottom:6px">Structure Record: <a href="/admin/object/record/${encodeURIComponent(r.treestrctpnm.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.treestrctpnm.trim())} &#x2197;</a></div>` : ''}
      ${r.tree_recname && r.tree_recname.trim() ? `<div>Leaf Record: <a href="/admin/object/record/${encodeURIComponent(r.tree_recname.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.tree_recname.trim())} &#x2197;</a></div>` : ''}
    </div>`;
}

doSearch();
</script>""")


@router.get("/ci", response_class=HTMLResponse)
def admin_ci():
    return _shell("Component Interface Explorer", "ci", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="ciSearch" type="text" placeholder="Search component interface name or description..." style="width:300px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Component Interfaces</h2>
    <div id="list" class="muted">Search to load CIs.</div>
  </div>
  <div class="content">
    <h2>Selected CI</h2>
    <div id="detail" class="muted">Select a component interface from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return res.json();
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

const CI_TYPE = {'0':'Standard', '1':'Find-only', '2':'Read-only'};

async function doSearch() {
  const q = document.getElementById('ciSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML = '<span class="muted">Select a CI.</span>';

  const rows = await api(`/api/peoplesoft/cis?env=${ENV}&q=${encodeURIComponent(q)}&limit=200`);
  if (!rows) { list.innerHTML = '<span class="muted">Error loading CIs.</span>'; return; }

  document.getElementById('stats').textContent = `${rows.length} result${rows.length===1?'':'s'}`;
  list.innerHTML = '';
  if (!rows.length) { list.innerHTML = '<span class="muted">No CIs found.</span>'; return; }

  rows.forEach(r => {
    const div = document.createElement('div');
    div.className = 'item';
    const typeLabel = CI_TYPE[String(r.bctype)] || ('Type '+r.bctype);
    div.innerHTML = `
      <div class="item-name">${esc(r.bcname)}</div>
      <div class="item-meta"><span class="chip chip-muted">${esc(typeLabel)}</span>${r.descr ? ' '+esc(r.descr) : ''}</div>
      <div class="item-meta" style="margin-top:2px">${r.pnlgrpname && r.pnlgrpname.trim() ? '&#x2192; '+esc(r.pnlgrpname.trim()) : ''}</div>`;
    div.onclick = () => selectCi(r, div);
    list.appendChild(div);
  });
}

function selectCi(r, el) {
  document.querySelectorAll('.item').forEach(i => i.classList.remove('sel'));
  if (el) el.classList.add('sel');
  const d = document.getElementById('detail');
  const typeLabel = CI_TYPE[String(r.bctype)] || ('Type '+r.bctype);
  d.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:16px;font-family:monospace;color:#d7faff">${esc(r.bcname)}</span>
      <span class="chip chip-info" style="margin-left:8px">${esc(typeLabel)}</span>
      <a href="/admin/object/ci/${encodeURIComponent(r.bcname)}?env=${ENV}" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a>
    </div>
    ${r.bcdisplayname && r.bcdisplayname.trim() ? `<div style="color:#8ab;font-size:13px;margin-bottom:4px">${esc(r.bcdisplayname.trim())}</div>` : ''}
    ${r.descr ? `<div style="color:#667;font-size:12px;margin-bottom:10px">${esc(r.descr)}</div>` : ''}
    <div style="font-size:12px;margin-top:8px">
      ${r.pnlgrpname && r.pnlgrpname.trim()
        ? `<div style="margin-bottom:6px">Wrapped Component: <a href="/admin/object/component/${encodeURIComponent(r.pnlgrpname.trim())}?env=${ENV}" style="color:#00e5ff">${esc(r.pnlgrpname.trim())} &#x2197;</a></div>`
        : ''}
      ${r.objectownerid && r.objectownerid.trim() ? `<div style="color:#445;margin-bottom:4px">Owner: ${esc(r.objectownerid.trim())}</div>` : ''}
      ${r.lastupddttm ? `<div style="color:#445;font-size:11px">Last updated: ${esc(String(r.lastupddttm))}</div>` : ''}
    </div>`;
}

doSearch();
</script>""")


@router.get("/menu", response_class=HTMLResponse)
def admin_menu():
    return _shell("Menu Explorer", "menu", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.item-row{padding:5px 6px;font-size:11px;border-bottom:1px solid #0d1a22}
.item-row:hover{background:#0a1820}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="mSearch" type="text" placeholder="Search menu name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Menus</h2>
    <div id="list" class="muted">Search to load menus.</div>
  </div>
  <div class="content">
    <h2>Menu Items</h2>
    <div id="detail" class="muted">Select a menu to see its items.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const MENU_TYPE = {'0':'Standard','1':'Pop-up'};
async function api(path) { const r=await fetch(path); return r.ok?r.json():null; }
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
async function doSearch() {
  const q=document.getElementById('mSearch').value.trim();
  const list=document.getElementById('list');
  list.innerHTML='<span class="muted">Loading...</span>';
  document.getElementById('detail').innerHTML='<span class="muted">Select a menu.</span>';
  const rows=await api('/api/peoplesoft/menus?env='+ENV+'&q='+encodeURIComponent(q));
  if(!rows){list.innerHTML='<span class="muted">Error.</span>';return;}
  document.getElementById('stats').textContent=rows.length+' result'+(rows.length===1?'':'s');
  list.innerHTML='';
  if(!rows.length){list.innerHTML='<span class="muted">No menus found.</span>';return;}
  rows.forEach(r=>{
    const div=document.createElement('div');div.className='item';
    const tl=MENU_TYPE[String(r.menutype)]||('Type '+r.menutype);
    div.innerHTML='<div class="item-name">'+esc(r.menuname)+' <span class="chip chip-muted">'+esc(tl)+'</span></div>'
      +'<div class="item-meta">'+(r.descr?esc(r.descr):'')+'</div>';
    div.onclick=()=>selectMenu(r,div);list.appendChild(div);});
}
async function selectMenu(r,el){
  document.querySelectorAll('.item').forEach(i=>i.classList.remove('sel'));
  if(el)el.classList.add('sel');
  const d=document.getElementById('detail');
  d.innerHTML='<span class="muted">Loading items...</span>';
  const items=await api('/api/peoplesoft/menus/'+encodeURIComponent(r.menuname)+'/items?env='+ENV);
  const tl=MENU_TYPE[String(r.menutype)]||('Type '+r.menutype);
  const hdr='<div style="margin-bottom:12px"><span style="font-size:16px;font-family:monospace;color:#d7faff">'+esc(r.menuname)+'</span>'
    +' <span class="chip chip-info">'+esc(tl)+'</span>'
    +' <a href="/admin/object/menu/'+encodeURIComponent(r.menuname)+'?env='+ENV+'" style="margin-left:12px;font-size:11px;color:#00e5ff">Open in Object Explorer &#x2197;</a></div>'
    +(r.descr?'<div style="color:#8ab;font-size:12px;margin-bottom:10px">'+esc(r.descr)+'</div>':'');
  if(!items||!items.length){d.innerHTML=hdr+'<span class="muted">No items found.</span>';return;}
  let table='<table style="width:100%;border-collapse:collapse;font-size:11px">'
    +'<thead><tr style="color:#00e5ff;border-bottom:1px solid #1e3040">'
    +'<th style="text-align:left;padding:4px 6px">Bar</th><th style="text-align:left;padding:4px 6px">Item</th>'
    +'<th style="text-align:left;padding:4px 6px">Label</th><th style="text-align:left;padding:4px 6px">Component</th>'
    +'</tr></thead><tbody>';
  items.forEach(i=>{
    const comp=(i.pnlgrpname||'').trim();
    table+='<tr class="item-row">'
      +'<td style="padding:4px 6px;color:#445">'+esc(i.barname||'')+'</td>'
      +'<td style="padding:4px 6px;font-family:monospace">'+esc(i.itemname||'')+'</td>'
      +'<td style="padding:4px 6px;color:#8ab">'+esc(i.itemlabel||i.barlabel||'')+'</td>'
      +'<td style="padding:4px 6px">'+(comp?'<a href="/admin/object/component/'+encodeURIComponent(comp)+'?env='+ENV+'" style="color:#00e5ff">'+esc(comp)+'</a>':'')+'</td>'
      +'</tr>';});
  table+='</tbody></table>';
  d.innerHTML=hdr+table;
}
doSearch();
</script>""")


@router.get("/approval", response_class=HTMLResponse)
def admin_approval():
    return _shell("Approval Framework Explorer", "approval", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.stage-row{padding:8px 10px;border-left:3px solid #00e5ff44;margin-bottom:6px;background:#030d14}
.stage-title{font-family:monospace;font-size:12px;color:#d7faff}
.stage-meta{font-size:10px;color:#556;margin-top:2px}
.step-row{padding:5px 10px;border-bottom:1px solid #0d1a22;font-size:11px}
.step-row:hover{background:#0a1820}
a{color:#00e5ff;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="awSearch" type="text" placeholder="Search workflow name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="awStatus" onchange="doSearch()" style="width:110px">
    <option value="">All Status</option>
    <option value="A">Active</option>
    <option value="I">Inactive</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Approval Definitions</h2>
    <div id="list" class="muted">Search to load approval definitions.</div>
  </div>
  <div class="content">
    <h2>Selected Workflow</h2>
    <div id="detail" class="muted">Select an approval workflow from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const STATUS_LABELS = {'A':['chip-ok','Active'], 'I':['chip-muted','Inactive']};
const PT_LABELS = {'0':'No Approval','1':'User','2':'Role','3':'Query','4':'App Class','5':'Supervisory','6':'Position','7':'Dept Security','8':'Role User'};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  const [cls, label] = STATUS_LABELS[String(s||'').trim()] || ['chip-muted', s||'?'];
  return `<span class="chip ${cls}">${label}</span>`;
}
function ptChip(pt) {
  const label = PT_LABELS[String(pt||'')] || String(pt||'');
  return label ? `<span class="chip chip-info">${esc(label)}</span>` : '';
}

async function doSearch() {
  const q = document.getElementById('awSearch').value.trim();
  const status = document.getElementById('awStatus').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (status) params.set('status', status);
  const d = await api(`/api/peoplesoft/approvals?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading approvals.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No approval definitions found.</div>'; return; }
  list.innerHTML = items.map((a, i) =>
    `<div class="item" id="item-${i}" onclick="selectApproval('${esc(a.awdefnid)}', ${i})">
       <div class="item-name">${statusChip(a.status)}${esc(a.awdefnid)}</div>
       <div class="item-meta">${esc((a.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
  window._awItems = items;
}

async function selectApproval(awdefnid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/approval/${encodeURIComponent(awdefnid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/approval/${esc(awdefnid)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold">${esc(awdefnid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.stage_count||0}</b>Stages</div>
      <div class="stat"><b>${ov.path_count||0}</b>Paths</div>
      <div class="stat"><b>${ov.step_count||0}</b>Steps</div>
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const stages = (d.sections||[]).find(s => s.name === 'Stages');
  if (stages && stages.items && stages.items.length) {
    html += '<h2>Stages</h2>';
    html += stages.items.map(s => `
      <div class="stage-row">
        <div class="stage-title">${s.relationship ? `<span class="chip chip-info">${esc(s.relationship)}</span>` : ''}${esc(s.title||'')}</div>
        <div class="stage-meta">${s.path_count||0} path${(s.path_count||0)!==1?'s':''} · ${s.step_count||0} step${(s.step_count||0)!==1?'s':''}</div>
      </div>`).join('');
  }

  const steps = (d.sections||[]).find(s => s.name === 'Steps');
  if (steps && steps.items && steps.items.length) {
    html += '<h2>Steps</h2><div style="border:1px solid #1e3040">';
    html += steps.items.map(st => `
      <div class="step-row">
        ${st.relationship ? `<span class="chip chip-info" style="font-size:10px">${esc(st.relationship)}</span>` : ''}
        <span style="font-family:monospace;font-size:11px">${esc(st.title||'')}</span>
        ${st.userlist ? `<span style="font-size:10px;color:#556;margin-left:8px">List: ${esc(st.userlist)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/efmapping", response_class=HTMLResponse)
def admin_efmapping():
    return _shell("Event Mapping Explorer", "efmapping", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#ddcc00;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #ddcc0033;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #ddcc0022;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #ddcc0022;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #ddcc0044;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#ddcc00}
button{background:#ddcc00;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(221,204,0,.07);border-left-color:#ddcc0055}
.item.sel{background:rgba(221,204,0,.12);border-left-color:#ddcc00}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#1a1800;border:1px solid #ddcc0044;color:#ddcc00}
.stat{display:inline-block;padding:4px 12px;border:1px solid #ddcc0033;background:#1a1800;font-size:11px;margin:2px}
.stat b{color:#ddcc00;font-size:16px;display:block}
.ctx-row{padding:6px 10px;border-bottom:1px solid #1a1800;font-size:11px}
.ctx-row:hover{background:#120e00}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#ddcc00;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="efSearch" type="text" placeholder="Search mapping ID or description..." style="width:270px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="efStatus" onchange="doSearch()" style="width:110px">
    <option value="">All Status</option>
    <option value="A">Active</option>
    <option value="I">Inactive</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Event Mappings</h2>
    <div id="list" class="muted">Search to load event mappings.</div>
  </div>
  <div class="content">
    <h2>Selected Mapping</h2>
    <div id="detail" class="muted">Select an event mapping from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s==='A') return '<span class="chip chip-ok">Active</span>';
  if (s==='I') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}

async function doSearch() {
  const q = document.getElementById('efSearch').value.trim();
  const status = document.getElementById('efStatus').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (status) params.set('status', status);
  const d = await api(`/api/peoplesoft/event-mappings?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No event mappings found.</div>'; return; }
  list.innerHTML = items.map((m, i) =>
    `<div class="item" id="item-${i}" onclick="selectMapping('${esc(m.efmappingid)}', ${i})">
       <div class="item-name">${statusChip(m.status)}${esc(m.efmappingid)}</div>
       <div class="item-meta">${esc((m.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectMapping(efmappingid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/event_mapping/${encodeURIComponent(efmappingid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/event_mapping/${esc(efmappingid)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#ddcc00">${esc(efmappingid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.context_count||0}</b>Contexts</div>
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const ctxSection = (d.sections||[]).find(s => s.name === 'Contexts');
  if (ctxSection && ctxSection.items && ctxSection.items.length) {
    html += '<h2>Contexts</h2><div style="border:1px solid #1a1800">';
    html += ctxSection.items.map(c => `
      <div class="ctx-row">
        ${c.relationship ? `<span class="chip chip-info">${esc(c.relationship)}</span>` : ''}
        <span style="font-family:monospace">${esc(c.title||'')}</span>
        ${c.event ? `<span style="color:#556;font-size:10px;margin-left:8px">Event: ${esc(c.event)}</span>` : ''}
        ${c.handler ? `<span style="color:#334;font-size:10px;margin-left:6px">→ ${esc(c.handler)}</span>` : ''}
      </div>`).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/relcontent", response_class=HTMLResponse)
def admin_relcontent():
    return _shell("Related Content Explorer", "relcontent", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#9944ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #9944ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #9944ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #9944ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #9944ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#9944ff}
button{background:#9944ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(153,68,255,.07);border-left-color:#9944ff55}
.item.sel{background:rgba(153,68,255,.12);border-left-color:#9944ff}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#0a0018;border:1px solid #9944ff44;color:#9944ff}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#9944ff;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="rcSearch" type="text" placeholder="Search related content ID or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Related Content Services</h2>
    <div id="list" class="muted">Search to load related content services.</div>
  </div>
  <div class="content">
    <h2>Selected Service</h2>
    <div id="detail" class="muted">Select a service from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const SVC_LABELS = {U:'URL',C:'Component',S:'Script',A:'App Class',P:'PS Page',I:'iScript',R:'Related Action'};
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s==='A') return '<span class="chip chip-ok">Active</span>';
  if (s==='I') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}
function svcChip(t) {
  const label = SVC_LABELS[String(t||'')] || String(t||'');
  return label ? `<span class="chip chip-info">${esc(label)}</span>` : '';
}

async function doSearch() {
  const q = document.getElementById('rcSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/related-content?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No related content services found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectService('${esc(r.relconid)}', ${i})">
       <div class="item-name">${statusChip(r.status)}${svcChip(r.servicetype)}${esc(r.relconid)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectService(relconid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/related_content/${encodeURIComponent(relconid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/related_content/${esc(relconid)}`;
  const defnSection = (d.sections||[]).find(s => s.name === 'Definition');
  const kv = defnSection?.data || {};
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      ${svcChip(ov.servicetype)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#9944ff">${esc(relconid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.description ? `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>` : ''}
    <div class="kv-grid">`;
  for (const [k, v] of Object.entries(kv)) {
    if (k !== 'Description' && k !== 'Status') {
      html += `<div class="kv-key">${esc(k)}</div><div class="kv-val">${esc(String(v||''))}</div>`;
    }
  }
  html += `</div>`;
  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/navcoll", response_class=HTMLResponse)
def admin_navcoll():
    return _shell("Navigation Collections", "navcoll", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00bb66;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00bb6633;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00bb6622;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #00bb6622;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00bb6644;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00bb66}
button{background:#00bb66;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,187,102,.07);border-left-color:#00bb6655}
.item.sel{background:rgba(0,187,102,.12);border-left-color:#00bb66}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001a14;border:1px solid #00bb6644;color:#00bb66}
.chip-tile{background:#001a14;border:1px solid #00ddaa44;color:#00ddaa}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00bb6633;background:#001a14;font-size:11px;margin:2px}
.stat b{color:#00bb66;font-size:16px;display:block}
.line-row{padding:6px 10px;border-bottom:1px solid #001a14;font-size:11px;display:flex;gap:8px;align-items:baseline}
.line-row:hover{background:#041208}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#00bb66;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="ncSearch" type="text" placeholder="Search collection ID or title..." style="width:270px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="ncPortal" style="width:120px" onchange="doSearch()">
    <option value="EMPLOYEE">EMPLOYEE</option>
    <option value="">All Portals</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Collections</h2>
    <div id="list" class="muted">Search to load navigation collections.</div>
  </div>
  <div class="content">
    <h2>Selected Collection</h2>
    <div id="detail" class="muted">Select a collection from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const LINE_TYPE_CHIP = {
  C: ['chip-info',  'Content Ref'],
  F: ['chip-muted', 'Folder'],
  T: ['chip-tile',  'Tile'],
  S: ['chip-muted', 'Static'],
};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s === 'A' || s === 'Active') return '<span class="chip chip-ok">Active</span>';
  if (s === 'I' || s === 'Inactive') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}
function lineTypeChip(lt) {
  const [cls, label] = LINE_TYPE_CHIP[String(lt||'')] || ['chip-muted', lt||'?'];
  return `<span class="chip ${cls}">${esc(label)}</span>`;
}

async function doSearch() {
  const q = document.getElementById('ncSearch').value.trim();
  const portal = document.getElementById('ncPortal').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (portal) params.set('portal', portal);
  const d = await api(`/api/peoplesoft/nav-collections?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading collections.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No navigation collections found.</div>'; return; }
  list.innerHTML = items.map((c, i) =>
    `<div class="item" id="item-${i}" onclick="selectCollection('${esc(c.coll_id)}', ${i})">
       <div class="item-name">${statusChip(c.eff_status)}${esc(c.coll_id)}</div>
       <div class="item-meta">${esc((c.coll_title||'').slice(0,60))}${c.portal_name ? ` · ${esc(c.portal_name)}` : ''}</div>
     </div>`
  ).join('');
  window._ncItems = items;
}

async function selectCollection(collId, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const portal = document.getElementById('ncPortal').value || 'EMPLOYEE';
  const d = await api(`/api/peoplesoft/object/nav_collection/${encodeURIComponent(collId)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading collection.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/nav_collection/${esc(collId)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.eff_status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#00bb66">${esc(collId)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    ${ov.title ? `<div style="color:#aac;font-size:13px;margin-bottom:10px">${esc(ov.title)}</div>` : ''}
    <div style="margin-bottom:12px">
      <div class="stat"><b>${ov.line_count||0}</b>Lines</div>
      ${ov.portal ? `<div class="stat"><b>${esc(ov.portal)}</b>Portal</div>` : ''}
      ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
    </div>`;

  const linesSection = (d.sections||[]).find(s => s.name === 'Lines');
  if (linesSection && linesSection.items && linesSection.items.length) {
    html += '<h2>Lines</h2><div style="border:1px solid #001a14">';
    html += linesSection.items.map(ln => {
      const nbr = ln.line_nbr !== undefined ? `<span style="color:#334;font-size:10px;min-width:28px;text-align:right">${ln.line_nbr}.</span>` : '';
      const rel = String(ln.relationship || '');
      const chipCls = rel === 'Tile' ? 'chip-tile' : rel === 'Content Ref' ? 'chip-info' : 'chip-muted';
      const relChip = rel ? `<span class="chip ${chipCls}">${esc(rel)}</span>` : '';
      const urlPart = ln.url ? `<span style="font-size:10px;color:#334;margin-left:6px;font-family:monospace">${esc(ln.url.slice(0,60))}</span>` : '';
      return `<div class="line-row">${nbr}${relChip}${esc(ln.title||'')}${urlPart}</div>`;
    }).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/xpub", response_class=HTMLResponse)
def admin_xpub():
    return _shell("XML Publisher Explorer", "xpub", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#cc44aa;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #cc44aa33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #cc44aa22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #cc44aa22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #cc44aa44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#cc44aa}
button{background:#cc44aa;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
button.sec{background:#1a0a18;border:1px solid #cc44aa44;color:#cc44aa}
button.sec.active{background:#cc44aa22;border-color:#cc44aa;color:#fff}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(204,68,170,.07);border-left-color:#cc44aa55}
.item.sel{background:rgba(204,68,170,.12);border-left-color:#cc44aa}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#1a0818;border:1px solid #cc44aa44;color:#cc44aa}
.chip-ds{background:#180814;border:1px solid #aa336644;color:#aa6688}
.stat{display:inline-block;padding:4px 12px;border:1px solid #cc44aa33;background:#1a0818;font-size:11px;margin:2px}
.stat b{color:#cc44aa;font-size:16px;display:block}
.tmpl-row{padding:6px 10px;border-bottom:1px solid #1a0818;font-size:11px;display:flex;gap:8px;align-items:center}
.tmpl-row:hover{background:#130810}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
a{color:#cc44aa;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
.tab-strip{display:flex;gap:6px;margin-bottom:10px}
</style>
<div class="topbar">
  <div class="tab-strip" id="modeTabs">
    <button class="sec active" id="modeReports"   onclick="switchMode('reports')">Reports</button>
    <button class="sec"        id="modeDatasources" onclick="switchMode('datasources')">Data Sources</button>
  </div>
  <input id="xpubSearch" type="text" placeholder="Search report ID or description..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2 id="sidebarTitle">Reports</h2>
    <div id="list" class="muted">Search to load XML Publisher objects.</div>
  </div>
  <div class="content">
    <h2>Selected Object</h2>
    <div id="detail" class="muted">Select an item from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
let _mode = 'reports';

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function dsChip(type) {
  const labels = {A:'App Engine',Q:'PS Query',S:'SQL',C:'Connected Query',G:'Group',F:'File'};
  const label = labels[String(type||'')] || String(type||'');
  return label ? `<span class="chip chip-ds">${esc(label)}</span>` : '';
}

function switchMode(mode) {
  _mode = mode;
  document.getElementById('modeReports').classList.toggle('active', mode==='reports');
  document.getElementById('modeDatasources').classList.toggle('active', mode==='datasources');
  document.getElementById('sidebarTitle').textContent = mode === 'reports' ? 'Reports' : 'Data Sources';
  document.getElementById('xpubSearch').placeholder = mode === 'reports'
    ? 'Search report ID or description...'
    : 'Search data source ID or description...';
  document.getElementById('detail').innerHTML = '<div class="muted">Select an item from the list.</div>';
  doSearch();
}

async function doSearch() {
  const q = document.getElementById('xpubSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const url = _mode === 'reports'
    ? `/api/peoplesoft/xpub/reports?${params}`
    : `/api/peoplesoft/xpub/datasources?${params}`;
  const d = await api(url);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No results found.</div>'; return; }
  if (_mode === 'reports') {
    list.innerHTML = items.map((r, i) =>
      `<div class="item" id="item-${i}" onclick="selectReport('${esc(r.reportid)}', ${i})">
         <div class="item-name">${esc(r.reportid)}</div>
         <div class="item-meta">${esc((r.descr||'').slice(0,55))}${r.datasrcid ? ` · DS: ${esc(r.datasrcid)}` : ''}</div>
       </div>`
    ).join('');
  } else {
    list.innerHTML = items.map((r, i) =>
      `<div class="item" id="item-${i}" onclick="selectDatasource('${esc(r.datasrcid)}', ${i})">
         <div class="item-name">${dsChip(r.datasrctype)}${esc(r.datasrcid)}</div>
         <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
       </div>`
    ).join('');
  }
  window._xpubItems = items;
}

async function selectReport(reportid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/xml_publisher_report/${encodeURIComponent(reportid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading report.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/xml_publisher_report/${esc(reportid)}`;
  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#cc44aa">${esc(reportid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (ov.description) html += `<div style="color:#aac;font-size:12px;margin-bottom:10px">${esc(ov.description)}</div>`;

  html += `<div style="margin-bottom:12px">
    <div class="stat"><b>${ov.template_count||0}</b>Templates</div>
    ${ov.owner ? `<div class="stat"><b>${esc(ov.owner)}</b>Owner</div>` : ''}
  </div>`;

  if (ov.datasrcid) {
    html += `<div class="kv-grid" style="margin-bottom:12px">
      <div class="kv-key">Data Source</div><div class="kv-val">${esc(ov.datasrcid)}</div>`;
    if (ov.datasrc_descr) {
      html += `<div class="kv-key">DS Description</div><div class="kv-val">${esc(ov.datasrc_descr)}</div>`;
    }
    if (ov.datasrc_type_label) {
      html += `<div class="kv-key">DS Type</div><div class="kv-val">${dsChip(ov.datasrc_type)}${esc(ov.datasrc_type_label)}</div>`;
    }
    html += `</div>`;
  }

  const tmplSection = (d.sections||[]).find(s => s.name === 'Templates');
  if (tmplSection && tmplSection.items && tmplSection.items.length) {
    html += '<h2>Templates / Layouts</h2><div style="border:1px solid #1a0818">';
    html += tmplSection.items.map(t => {
      const statusCls = t.relationship === 'Active' ? 'chip-ok' : 'chip-muted';
      return `<div class="tmpl-row">
        <span class="chip ${statusCls}">${esc(t.relationship||'')}</span>
        <span style="font-family:monospace;flex:1">${esc(t.title||'')}</span>
        ${t.effdt ? `<span style="font-size:10px;color:#556">${esc(t.effdt)}</span>` : ''}
      </div>`;
    }).join('');
    html += '</div>';
  }

  detail.innerHTML = html;
}

async function selectDatasource(datasrcid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  const item = window._xpubItems ? window._xpubItems[idx] : null;
  if (!item) { detail.innerHTML = '<div class="muted">No data.</div>'; return; }
  detail.innerHTML = `
    <div style="margin-bottom:12px">
      ${dsChip(item.datasrctype)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#aa3366">${esc(datasrcid)}</span>
    </div>
    <div class="kv-grid">
      <div class="kv-key">Description</div><div class="kv-val">${esc(item.descr||'—')}</div>
      <div class="kv-key">Type</div><div class="kv-val">${esc(item.datasrctype_label||item.datasrctype||'—')}</div>
    </div>`;
}

doSearch();
</script>""")


@router.get("/msgcat", response_class=HTMLResponse)
def admin_msgcat():
    return _shell("Message Catalog", "msgcat", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:340px;min-width:240px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-ref{font-family:monospace;font-size:12px;color:#d7faff}
.item-text{font-size:11px;color:#aac;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-info{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-warn{background:#2a1800;border:1px solid #ffaa00;color:#ffaa00}
.chip-error{background:#2a0000;border:1px solid #ff4444;color:#ff6666}
.chip-crit{background:#1a0020;border:1px solid #aa44ff;color:#cc88ff}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.stat{display:inline-block;padding:4px 12px;border:1px solid #00e5ff33;background:#001830;font-size:11px;margin:2px}
.stat b{color:#00e5ff;font-size:16px;display:block}
.msg-text{background:#030d14;border:1px solid #1e3040;padding:12px 14px;font-size:12px;line-height:1.6;white-space:pre-wrap;word-break:break-word;margin:4px 0 12px}
.explain{background:#030d14;border:1px solid #1e304066;padding:10px 14px;font-size:11px;line-height:1.6;color:#aac;white-space:pre-wrap;word-break:break-word;margin-top:4px}
.muted{color:#556;font-style:italic}
a{color:#00e5ff;text-decoration:none} a:hover{text-decoration:underline}
</style>
<div class="topbar">
  <input id="mcSearch" type="text" placeholder="Search message text..." style="width:260px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="mcSet" style="width:130px" onchange="doSearch()">
    <option value="">All Sets</option>
  </select>
  <select id="mcSeverity" style="width:110px" onchange="doSearch()">
    <option value="">All Severities</option>
    <option value="0">Message</option>
    <option value="1">Warning</option>
    <option value="2">Error</option>
    <option value="3">Cancel</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Messages</h2>
    <div id="list" class="muted">Search to load messages.</div>
  </div>
  <div class="content">
    <h2>Selected Message</h2>
    <div id="detail" class="muted">Select a message from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
const SEV_CHIP = {'0':['chip-info','Message'],'1':['chip-warn','Warning'],'2':['chip-error','Error'],'3':['chip-crit','Cancel']};

async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function sevChip(sev) {
  const [cls, label] = SEV_CHIP[String(sev)] || ['chip-muted', 'Unknown'];
  return `<span class="chip ${cls}">${label}</span>`;
}

async function loadSets() {
  const d = await api(`/api/peoplesoft/message-sets?env=${ENV}`);
  if (!d) return;
  const sel = document.getElementById('mcSet');
  (d.items || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.message_set_nbr;
    const desc = s.descr ? ` — ${s.descr}` : '';
    const cnt = s.msg_count ? ` (${s.msg_count})` : '';
    opt.textContent = `Set ${s.message_set_nbr}${desc}${cnt}`;
    sel.appendChild(opt);
  });
}

async function doSearch() {
  const q = document.getElementById('mcSearch').value.trim();
  const setNbr = document.getElementById('mcSet').value;
  const sev = document.getElementById('mcSeverity').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (setNbr) params.set('set_nbr', setNbr);
  if (sev !== '') params.set('severity', sev);
  const d = await api(`/api/peoplesoft/messages?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading messages.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No messages found.</div>'; return; }
  list.innerHTML = items.map((m, i) =>
    `<div class="item" id="item-${i}" onclick="selectMsg(${i})" data-idx="${i}">
       <div class="item-ref">${sevChip(m.severity)}${esc(m.name)}</div>
       <div class="item-text">${esc((m.message_text||'').slice(0,80))}</div>
     </div>`
  ).join('');
  window._msgItems = items;
}

function selectMsg(idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const m = window._msgItems[idx];
  if (!m) return;
  const sev = String(m.severity || '0');
  const text = m.message_text || '';
  const explain = m.descrlong || '';
  const adminUrl = `/admin/object/message_catalog/${esc(m.name)}`;
  let html = `
    <div style="margin-bottom:12px">
      ${sevChip(m.severity)}
      <span style="font-family:monospace;font-size:13px">${esc(m.name)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>
    <div class="stat"><b>${esc(m.message_set_nbr)}</b>Set</div>
    <div class="stat"><b>${esc(m.message_nbr)}</b>Msg #</div>
    ${text ? `<h2>Message Text</h2><div class="msg-text">${esc(text)}</div>` : ''}
    ${explain ? `<h2>Explanation</h2><div class="explain">${esc(explain)}</div>` : ''}
  `;
  document.getElementById('detail').innerHTML = html;
}

loadSets();
doSearch();
</script>""")


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


@router.get("/pcsearch", response_class=HTMLResponse)
def admin_pcsearch():
    return _shell("PeopleCode Source Search", "pcsearch", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#00e5ff;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #00e5ff33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #00e5ff22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:240px;border-right:1px solid #00e5ff22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#00e5ff}
button{background:#00e5ff;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
button.sec{background:transparent;border:1px solid #00e5ff44;color:#00e5ff}
select{background:#0b1b24;color:#d7faff;border:1px solid #00e5ff44;padding:5px 8px;font-size:12px}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(0,229,255,.07);border-left-color:#00e5ff55}
.item.sel{background:rgba(0,229,255,.12);border-left-color:#00e5ff}
.item-ref{font-family:monospace;font-size:11px;color:#d7faff}
.item-parent{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold}
.chip-type{background:#001830;border:1px solid #00e5ff44;color:#00e5ff}
.chip-event{background:#0d1a00;border:1px solid #44aa4444;color:#66cc66}
pre{background:#030d14;border:1px solid #1e3040;padding:12px;font-family:monospace;font-size:11px;white-space:pre-wrap;word-break:break-word;line-height:1.5;overflow-x:auto;max-height:500px}
.hit{background:#2a1c00;color:#ffcc44}
.kw{color:#569cd6}.str{color:#ce9178}.cmt{color:#6a9955}.builtin{color:#dcdcaa}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="pcq" type="text" placeholder="Search in PeopleCode source... (e.g. EMPLMT_SRCH_ALL, CreateSQL, %UpdateStats)" style="width:320px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="limitSel">
    <option value="50">50 results</option>
    <option value="100" selected>100 results</option>
    <option value="200">200 results</option>
    <option value="500">500 results</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#445;margin-left:6px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Matching Programs</h2>
    <div id="list" class="muted">Enter a search term and press Search.</div>
  </div>
  <div class="content">
    <h2>Source Preview</h2>
    <div id="detail" class="muted">Select a program to view source with matches highlighted.</div>
  </div>
</div>
<script>
const ENV=localStorage.getItem('dsEnv')||'HCM';
const PC_KW=['If','Then','Else','End-If','For','End-For','While','End-While','Repeat','Until','Return','Break','Continue','Local','Global','Component','Function','End-Function','Method','End-Method','class','Extends','Implements','import','Array','String','Integer','Number','Date','DateTime','Boolean','Object','Any','Exception','Try','Catch','End-Try','Throw','CreateObject','GetLevel0','GetRecord','GetField','GetPage','GetGrid','GetRow','GetComponent','Step','DoWhile','DoUntil'];
const PC_BUILTIN=['MessageBox','SQLExec','CreateSQL','Close','Fetch','Insert','Update','Delete','IsNull','None','Null','True','False','All','And','Or','Not','As','Of','Property','Get','Set','Value','Name','Type','CreateRecord','CreateMessage','CreateRowset','CreateArray','GetRowset','GetMessage','%This','%Super','%CurrentTimeIn','%Date','%DateTime','%Time','%EmployeeId','%OperatorId','%MenuName','%Component','%Page','%Action','%Mode','%Panel','%PanelGroup','%UpdateStats','%SelectAll','%Insert','%Update','%Delete','%SelectByKey','%SelectByKeyEffdt','%DateAdd','%DateTimeAdd','%DateTimeDiff','%DateDiff','%Substring','%NumToChar','%CharToNum','%DateOut','%TimeOut','%Round','%Truncate','%Abs','%Sign','%Mod','%Upper','%Lower','%Rtrim','%Ltrim','%Replace','%Len','%Value','%like','%contains','%starts'];

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
async function api(p){const r=await fetch(p);return r.ok?r.json():null;}

function highlightPC(src,q){
  // tokenize and highlight PeopleCode source with match highlighting
  let h='',i=0;const s=src;
  while(i<s.length){
    if(s[i]==='/' && s[i+1]==='*'){const e=s.indexOf('*/',i+2);const end=e<0?s.length:e+2;h+='<span class="cmt">'+esc(s.slice(i,end))+'</span>';i=end;continue;}
    if(s[i]==='"'){let j=i+1;while(j<s.length&&s[j]!=='"')j++;h+='<span class="str">'+esc(s.slice(i,j+1))+'</span>';i=j+1;continue;}
    // word
    if(/[A-Za-z%_]/.test(s[i])){let j=i;while(j<s.length&&/[A-Za-z0-9_.%\-]/.test(s[j]))j++;const w=s.slice(i,j);
      if(PC_KW.includes(w))h+='<span class="kw">'+esc(w)+'</span>';
      else if(PC_BUILTIN.includes(w))h+='<span class="builtin">'+esc(w)+'</span>';
      else if(q&&w.toUpperCase()===q.toUpperCase())h+='<span class="hit">'+esc(w)+'</span>';
      else h+=esc(w);i=j;continue;}
    // check for match at any position (non-word chars)
    if(q&&s.slice(i).toUpperCase().startsWith(q.toUpperCase())){h+='<span class="hit">'+esc(s.slice(i,i+q.length))+'</span>';i+=q.length;continue;}
    h+=esc(s[i]);i++;}
  return h;
}

let _results=[];
async function doSearch(){
  const q=document.getElementById('pcq').value.trim();
  const lim=document.getElementById('limitSel').value;
  if(!q){return;}
  const list=document.getElementById('list');
  list.innerHTML='<span class="muted">Searching...</span>';
  document.getElementById('detail').innerHTML='<span class="muted">Select a result.</span>';
  document.getElementById('stats').textContent='';
  const data=await api('/api/peoplesoft/peoplecode/source-search?q='+encodeURIComponent(q)+'&env='+ENV+'&limit='+lim);
  if(!data){list.innerHTML='<span class="muted">Error.</span>';return;}
  _results=data.items||[];
  document.getElementById('stats').textContent=_results.length+(data.warnings&&data.warnings.length?' ('+data.warnings[0].message+')':' programs matched');
  list.innerHTML='';
  if(!_results.length){list.innerHTML='<span class="muted">No PeopleCode programs match "'+esc(q)+'".</span>';return;}
  _results.forEach((r,idx)=>{
    const div=document.createElement('div');div.className='item';
    const ptype=r.parent_type||'';const pname=r.parent_name||'';
    div.innerHTML='<div class="item-ref">'+esc(r.reference||r.encoded_reference||'')+'</div>'
      +'<div class="item-parent">'+(ptype?'<span class="chip chip-type">'+esc(ptype.toUpperCase())+'</span> ':'')+(pname?esc(pname):'')+' <span class="chip chip-event">'+esc(r.event_name||r.objectvalue7||'')+'</span></div>';
    div.onclick=()=>showSource(r,q,div);
    list.appendChild(div);
  });
}

function showSource(r,q,el){
  document.querySelectorAll('.item').forEach(i=>i.classList.remove('sel'));
  if(el)el.classList.add('sel');
  const src=r.source||'(source not loaded)';
  const d=document.getElementById('detail');
  const ref=r.reference||r.encoded_reference||'';
  const ptype=r.parent_type||'';const pname=r.parent_name||'';
  d.innerHTML='<div style="margin-bottom:10px">'
    +'<span style="font-family:monospace;font-size:13px;color:#d7faff">'+esc(ref)+'</span>'
    +' <a href="/admin/object/peoplecode/'+encodeURIComponent(r.encoded_reference||ref)+'?env='+ENV+'" style="font-size:11px;color:#00e5ff;margin-left:10px">Open in PC Explorer &#x2197;</a>'
    +(ptype&&pname?' <a href="/admin/object/'+encodeURIComponent(ptype)+'/'+encodeURIComponent(pname)+'?env='+ENV+'" style="font-size:11px;color:#00e5ff;margin-left:10px">&#x2192; '+esc(pname)+' &#x2197;</a>':'')
    +'</div>'
    +'<pre>'+highlightPC(src,q)+'</pre>';
  // scroll first match into view
  setTimeout(()=>{const hit=d.querySelector('.hit');if(hit)hit.scrollIntoView({block:'center',behavior:'smooth'});},50);
}
</script>""")


@router.get("/srchdef", response_class=HTMLResponse)
def admin_srchdef():
    return _shell("Search Definition Explorer", "srchdef", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#2299ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #2299ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #2299ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #2299ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input,select{background:#0b1b24;color:#d7faff;border:1px solid #2299ee44;padding:5px 8px;font-size:12px}
input:focus,select:focus{outline:none;border-color:#2299ee}
button{background:#2299ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(34,153,238,.07);border-left-color:#2299ee55}
.item.sel{background:rgba(34,153,238,.12);border-left-color:#2299ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-ok{background:#002800;border:1px solid #00cc66;color:#00cc66}
.chip-muted{background:#141a20;border:1px solid #334;color:#778}
.chip-info{background:#001020;border:1px solid #2299ee44;color:#2299ee}
.stat{display:inline-block;padding:4px 12px;border:1px solid #2299ee33;background:#001020;font-size:11px;margin:2px}
.stat b{color:#2299ee;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right;padding-top:2px}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #001020;font-size:11px;display:flex;gap:8px;align-items:baseline}
.field-row:hover{background:#020c14}
a{color:#2299ee;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="sdSearch" type="text" placeholder="Search definition ID or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <select id="sdStatus" onchange="doSearch()">
    <option value="">All Statuses</option>
    <option value="A">Active</option>
    <option value="I">Inactive</option>
  </select>
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Search Definitions</h2>
    <div id="list" class="muted">Search to load search definitions.</div>
  </div>
  <div class="content">
    <h2>Selected Definition</h2>
    <div id="detail" class="muted">Select a definition from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function statusChip(s) {
  if (s==='A'||s==='Active') return '<span class="chip chip-ok">Active</span>';
  if (s==='I'||s==='Inactive') return '<span class="chip chip-muted">Inactive</span>';
  return '';
}

async function doSearch() {
  const q = document.getElementById('sdSearch').value.trim();
  const status = document.getElementById('sdStatus').value;
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  if (status) params.set('status', status);
  const d = await api(`/api/peoplesoft/search-definitions?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No search definitions found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectDef('${esc(r.srcdefnid)}', ${i})">
       <div class="item-name">${statusChip(r.status)}${esc(r.srcdefnid)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectDef(srcdefnid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/search_definition/${encodeURIComponent(srcdefnid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const ov = d.overview || {};
  const adminUrl = `/admin/object/search_definition/${esc(srcdefnid)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const fieldsSec = sections.find(s => s.id === 'fields');
  const catsSec = sections.find(s => s.id === 'categories');

  let html = `
    <div style="margin-bottom:12px">
      ${statusChip(ov.status)}
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#2299ee">${esc(srcdefnid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      if (row.label !== 'Status') {
        html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
      }
    }
    html += `</div>`;
  }

  const counts = d._uom?._raw?.counts || {};
  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${counts.fields||0}</b>Fields</span>`
    + `<span class="stat"><b>${counts.categories||0}</b>Categories</span>`
    + `</div>`;

  if (fieldsSec && (fieldsSec.items||[]).length) {
    html += `<h2>${esc(fieldsSec.title)}</h2>`;
    html += fieldsSec.items.map(f =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#d7faff">${esc(f.name)}</span>
         ${(f.chips||[]).map(c=>`<span class="chip chip-info">${esc(c.label)}</span>`).join('')}
         ${f.meta ? `<span style="color:#556;font-size:10px">${esc(f.meta)}</span>` : ''}
       </div>`
    ).join('');
  }

  if (catsSec && (catsSec.items||[]).length) {
    html += `<h2>${esc(catsSec.title)}</h2>`;
    html += catsSec.items.map(c =>
      `<div class="field-row">
         <span style="font-family:monospace;color:#d7faff">${esc(c.name)}</span>
         ${c.meta ? `<span style="color:#aac;font-size:11px">${esc(c.meta)}</span>` : ''}
       </div>`
    ).join('');
  }

  if (!rows.length && !fieldsSec && !catsSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/srchcat", response_class=HTMLResponse)
def admin_srchcat():
    return _shell("Search Category Explorer", "srchcat", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#7744ee;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #7744ee33;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #7744ee22;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #7744ee22;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #7744ee44;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#7744ee}
button{background:#7744ee;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#fff;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(119,68,238,.07);border-left-color:#7744ee55}
.item.sel{background:rgba(119,68,238,.12);border-left-color:#7744ee}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.chip{display:inline-block;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:bold;margin-right:3px}
.chip-info{background:#10001a;border:1px solid #7744ee44;color:#7744ee}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #10001a;font-size:11px}
a{color:#7744ee;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="scSearch" type="text" placeholder="Search category ID or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Search Categories</h2>
    <div id="list" class="muted">Search to load search categories.</div>
  </div>
  <div class="content">
    <h2>Selected Category</h2>
    <div id="detail" class="muted">Select a category from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('scSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/search-categories?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No search categories found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectCat('${esc(r.srccatid)}', ${i})">
       <div class="item-name">${esc(r.srccatid)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectCat(srccatid, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/search_category/${encodeURIComponent(srccatid)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const adminUrl = `/admin/object/search_category/${esc(srccatid)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const defnSec = sections.find(s => s.id === 'definitions');

  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#7744ee">${esc(srccatid)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  if (defnSec && (defnSec.items||[]).length) {
    html += `<h2>${esc(defnSec.title)}</h2>`;
    html += defnSec.items.map(it =>
      `<div class="field-row"><span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span></div>`
    ).join('');
  }

  if (!rows.length && !defnSec) {
    html += `<div class="muted">No detail available.</div>`;
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")


@router.get("/dropzone", response_class=HTMLResponse)
def admin_dropzone():
    return _shell("Drop Zone Explorer", "dropzone", noscroll=True, content="""\
<style>
*{box-sizing:border-box}
body{background:#050b12;color:#d7faff;font-family:Arial,sans-serif;margin:0;height:100vh;display:flex;flex-direction:column}
h2{color:#ee8800;font-size:11px;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #ee880033;padding-bottom:5px;margin:14px 0 8px}
.topbar{padding:12px 16px;border-bottom:1px solid #ee880022;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:320px;min-width:220px;border-right:1px solid #ee880022;overflow-y:auto;padding:12px;flex-shrink:0}
.content{flex:1;overflow:auto;padding:16px}
input{background:#0b1b24;color:#d7faff;border:1px solid #ee880044;padding:5px 8px;font-size:12px}
input:focus{outline:none;border-color:#ee8800}
button{background:#ee8800;border:none;padding:5px 12px;cursor:pointer;font-size:11px;color:#000;font-weight:bold}
.item{padding:7px 8px;cursor:pointer;border-radius:2px;border-left:2px solid transparent}
.item:hover{background:rgba(238,136,0,.07);border-left-color:#ee880055}
.item.sel{background:rgba(238,136,0,.12);border-left-color:#ee8800}
.item-name{font-family:monospace;font-size:12px;color:#d7faff}
.item-meta{font-size:10px;color:#556;margin-top:2px}
.stat{display:inline-block;padding:4px 12px;border:1px solid #ee880033;background:#1a1000;font-size:11px;margin:2px}
.stat b{color:#ee8800;font-size:16px;display:block}
.kv-grid{display:grid;grid-template-columns:140px 1fr;gap:3px 12px;font-size:12px;margin-bottom:10px}
.kv-key{color:#556;text-align:right}
.kv-val{color:#d7faff;font-family:monospace}
.field-row{padding:5px 10px;border-bottom:1px solid #1a1000;font-size:11px}
a{color:#ee8800;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#556;font-style:italic}
</style>
<div class="topbar">
  <input id="dzSearch" type="text" placeholder="Search drop zone name or description..." style="width:280px"
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
  <span id="stats" style="font-size:11px;color:#556;margin-left:8px"></span>
</div>
<div class="main">
  <div class="sidebar">
    <h2>Drop Zones</h2>
    <div id="list" class="muted">Search to load drop zones.</div>
  </div>
  <div class="content">
    <h2>Selected Drop Zone</h2>
    <div id="detail" class="muted">Select a drop zone from the list.</div>
  </div>
</div>
<script>
const ENV = localStorage.getItem('dsEnv') || 'HCM';
async function api(path) { const r = await fetch(path); return r.ok ? r.json() : null; }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function doSearch() {
  const q = document.getElementById('dzSearch').value.trim();
  const list = document.getElementById('list');
  list.innerHTML = '<div class="muted">Loading...</div>';
  const params = new URLSearchParams({env: ENV, limit: 200});
  if (q) params.set('q', q);
  const d = await api(`/api/peoplesoft/drop-zones?${params}`);
  if (!d) { list.innerHTML = '<div class="muted">Error loading data.</div>'; return; }
  const items = d.items || [];
  document.getElementById('stats').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;
  if (!items.length) { list.innerHTML = '<div class="muted">No drop zones found.</div>'; return; }
  list.innerHTML = items.map((r, i) =>
    `<div class="item" id="item-${i}" onclick="selectDz('${esc(r.dzname)}', ${i})">
       <div class="item-name">${esc(r.dzname)}</div>
       <div class="item-meta">${esc((r.descr||'').slice(0,60))}</div>
     </div>`
  ).join('');
}

async function selectDz(dzname, idx) {
  document.querySelectorAll('.item').forEach(el => el.classList.remove('sel'));
  const el = document.getElementById(`item-${idx}`);
  if (el) el.classList.add('sel');
  const detail = document.getElementById('detail');
  detail.innerHTML = '<div class="muted">Loading...</div>';

  const d = await api(`/api/peoplesoft/object/drop_zone/${encodeURIComponent(dzname)}?env=${ENV}`);
  if (!d) { detail.innerHTML = '<div class="muted">Error loading detail.</div>'; return; }

  const adminUrl = `/admin/object/drop_zone/${esc(dzname)}`;
  const sections = d.sections || [];
  const overviewSec = sections.find(s => s.id === 'overview') || {};
  const rows = overviewSec.rows || [];
  const compSec = sections.find(s => s.id === 'components');
  const pageSec = sections.find(s => s.id === 'pages');
  const itemSec = sections.find(s => s.id === 'items');

  let html = `
    <div style="margin-bottom:12px">
      <span style="font-family:monospace;font-size:14px;font-weight:bold;color:#ee8800">${esc(dzname)}</span>
      &nbsp;<a href="${adminUrl}" target="_blank" style="font-size:11px">Object Explorer ↗</a>
    </div>`;

  if (rows.length) {
    html += `<div class="kv-grid">`;
    for (const row of rows) {
      html += `<div class="kv-key">${esc(row.label)}</div><div class="kv-val">${esc(String(row.value||''))}</div>`;
    }
    html += `</div>`;
  }

  html += `<div style="margin:10px 0">`
    + `<span class="stat"><b>${(compSec?.items||[]).length}</b>Components</span>`
    + `<span class="stat"><b>${(pageSec?.items||[]).length}</b>Pages</span>`
    + `<span class="stat"><b>${(itemSec?.items||[]).length}</b>Items</span>`
    + `</div>`;

  for (const sec of [compSec, pageSec, itemSec]) {
    if (sec && (sec.items||[]).length) {
      html += `<h2>${esc(sec.title)}</h2>`;
      html += sec.items.map(it =>
        `<div class="field-row">
           <span style="font-family:monospace;color:#d7faff">${esc(it.name)}</span>
           ${it.meta ? `<span style="color:#556;font-size:10px;margin-left:8px">${esc(it.meta)}</span>` : ''}
         </div>`
      ).join('');
    }
  }

  detail.innerHTML = html;
}

doSearch();
</script>""")
