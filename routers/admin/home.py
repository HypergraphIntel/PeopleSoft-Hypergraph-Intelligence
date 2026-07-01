import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

@router.get("/", response_class=HTMLResponse)
def admin_home():
    return _shell("Home", "home", env=False, content="""\
<div class="pe-home">
  <div class="pe-hero">
    <p class="pe-kicker">DeathStar Platform</p>
    <h1>PeopleSoft Hypergraph Intelligence</h1>
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


