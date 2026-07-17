import json
from fastapi import Request
from fastapi.responses import HTMLResponse
from ._core import router, _shell, _nav_html, _NAV_CSS, _ESC_JS

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
            color: #000;
            font-weight: bold;
            border: none;
            padding: 8px 14px;
            margin: 4px 0;
            cursor: pointer;
        }

        button:hover {
            background: #33eeff;
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
function ENV_VAL() { return window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM'); }
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

    const roles = await api(`/api/peoplesoft/roles?env=${ENV_VAL()}&q=${encodeURIComponent(q)}`);
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

    const data = await api(`/api/peoplesoft/security/operators/${encodeURIComponent(oprid)}?env=${ENV_VAL()}`);
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

    const data = await api(`/api/peoplesoft/security/components/${encodeURIComponent(component)}/access?env=${ENV_VAL()}`);
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

    const data = await api(`/api/peoplesoft/security/explain?env=${ENV_VAL()}&oprid=${encodeURIComponent(oprid)}&component=${encodeURIComponent(component)}`);
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

    const data = await api(`/api/peoplesoft/security/explain-page?env=${ENV_VAL()}&oprid=${encodeURIComponent(oprid)}&page=${encodeURIComponent(page)}`);
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

    const data = await api(`/api/peoplesoft/security/explain-menu?env=${ENV_VAL()}&oprid=${encodeURIComponent(oprid)}&menu=${encodeURIComponent(menu)}`);
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

    const d = await api(`/api/peoplesoft/security/compare-operators?env=${ENV_VAL()}&oprid1=${encodeURIComponent(oprid1)}&oprid2=${encodeURIComponent(oprid2)}`);
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

    const rows = await api(`/api/peoplesoft/roles/${encodeURIComponent(rolename)}/permissionlists?env=${ENV_VAL()}`);
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
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/menus?env=${ENV_VAL()}`),
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/components?env=${ENV_VAL()}`),
        api(`/api/peoplesoft/permissionlists/${encodeURIComponent(classid)}/page-grants?env=${ENV_VAL()}`),
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
        api(`/api/peoplesoft/components/${encodeURIComponent(component)}/pages?env=${ENV_VAL()}`),
        api(`/api/peoplesoft/components/${encodeURIComponent(component)}/page-grants?env=${ENV_VAL()}`),
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

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event — this page
// only read ENV_VAL() lazily per-request, so no explicit reload wiring was
// needed for in-flight actions, but the role list itself needs a refresh
// when the environment changes since it was loaded for the old one.
window.onEnvChange = loadRoles;
document.addEventListener('deathstar:envchange', loadRoles);

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

function env() { return (document.getElementById('globalEnv') || {}).value || 'HCM'; }

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
    <div class="tab"      onclick="switchTab('sqr');loadTab('sqr')">SQR Programs</div>
    <div class="tab"      onclick="switchTab('pc');loadTab('pc')">PeopleCode</div>
    <div class="tab"      onclick="switchTab('sequence');loadTab('sequence')">Processing Sequence</div>
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
    <div id="overview-pc-summary"></div>
  </div>

  <div id="pane-fields"     class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-keys"       class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-indexes"    class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-related"    class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-components" class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-pages"      class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-sqr"        class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-pc"         class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-sequence"   class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-ddl"        class="pane"><span class="empty">Loading…</span></div>
  <div id="pane-data"       class="pane"><span class="empty">Loading…</span></div>
  `;

  $('contentArea').innerHTML = h;

  // Eagerly load storage stats and children into the overview.
  loadStorageInto('overview-storage', recname);
  loadChildrenInto('overview-children', recname);
  // Background: load PC summary chip
  api(`/api/record/${encodeURIComponent(recname)}/peoplecode?env=${env()}`).then(pc => {
    const el = $('overview-pc-summary');
    if (!el) return;
    const total = pc.total || 0;
    if (!total) return;
    const rowCnt   = (pc.row_events   || []).length;
    const fieldCnt = (pc.field_events || []).length;
    el.innerHTML = `<div style="margin-top:10px;padding:8px 12px;background:#030d14;border:1px solid #00e5ff22;border-radius:2px;font-size:11px">
      <span style="color:#00e5ff;font-weight:bold">${total}</span>
      <span style="color:#445"> record-level PeopleCode program${total===1?'':'s'} —</span>
      <span style="color:#44bbff"> ${rowCnt} row-level</span><span style="color:#445">,</span>
      <span style="color:#00e5ff"> ${fieldCnt} field-level</span>
      <span style="color:#334;margin-left:8px;font-size:10px">(see <a onclick="switchTab('pc');loadTab('pc')" style="color:#00e5ff;cursor:pointer">PeopleCode tab</a>)</span>
    </div>`;
  }).catch(() => {});
}

function switchTab(name) {
  const tabs = ['overview','fields','keys','indexes','related','components','pages','sqr','pc','sequence','ddl','data'];
  tabs.forEach(t => {
    const p = $(`pane-${t}`); if (p) p.className = 'pane' + (t === name ? ' on' : '');
  });
  document.querySelectorAll('.tab-row .tab').forEach(el => {
    const m = (el.getAttribute('onclick')||'').match(/switchTab\('(\w+)'\)/);
    if (m) el.classList.toggle('on', m[1] === name);
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
  } else if (name === 'sqr') {
    const tbl = 'PS_' + currentRec;
    const d = await api(`/api/sqr/table/${encodeURIComponent(tbl)}`);
    pane.innerHTML = renderSQR(d.programs || [], tbl);
  } else if (name === 'pc') {
    const d = await api(`/api/record/${encodeURIComponent(currentRec)}/peoplecode?env=${env()}`);
    pane.innerHTML = renderRecordPC(d);
  } else if (name === 'sequence') {
    const d = await api(`/api/peoplesoft/records/${encodeURIComponent(currentRec)}/sequence?env=${env()}`);
    pane.innerHTML = renderRecordSequence(d);
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
    <td class="mono"><a class="obj-link" href="/admin/component?name=${esc(c.pnlgrpname)}&env=${env()}">${esc(c.pnlgrpname)}</a></td>
    <td class="mono">${esc(c.searchrecname || '')}</td>
    <td class="mono">${esc(c.addsrchrecname || '')}</td>
    <td>${esc(c.descr || '')}</td>
    <td>${esc(c.market || '')}</td>
  </tr>`).join('') + '</tbody></table>';
}

function renderPages(items) {
  if (!items.length) return '<div class="empty">No pages reference this record\\'s fields.</div>';
  // Deduplicate by page name.
  const seen = new Set();
  const unique = items.filter(r => { const k = r.pnlname; if (seen.has(k)) return false; seen.add(k); return true; });
  return `<table><thead><tr><th>Page</th></tr></thead><tbody>` +
    unique.map(p => `<tr><td class="mono">
      <a class="obj-link" href="/admin/page?name=${esc(p.pnlname)}&env=${env()}">${esc(p.pnlname)}</a>
    </td></tr>`).join('') + '</tbody></table>';
}

function renderSQR(programs, tblName) {
  if (!programs.length) return `<div class="empty">No indexed SQR programs reference <span class="mono">${esc(tblName)}</span>.<br><span style="color:#445;font-size:10px">Index SQR programs from <a href="/admin/sqr" style="color:#00e5ff">SQR Explorer</a> to populate this view.</span></div>`;
  const OP_COLOR = {SELECT:'#0af',UPDATE:'#fa0',INSERT:'#0f9',DELETE:'#f55',CREATE:'#a0f'};
  return `<div style="font-size:11px;color:#7faab2;margin-bottom:8px">${programs.length} SQR program${programs.length!==1?'s':''} reference <span class="mono" style="color:#d7faff">${esc(tblName)}</span></div>` +
    `<table><thead><tr><th>Program</th><th>Type</th><th>Description</th><th>Operations</th></tr></thead><tbody>` +
    programs.map(p => {
      const ops = (p.operations||'').split(',').filter(Boolean).map(op =>
        `<span style="font-size:9px;font-weight:700;padding:1px 4px;border-radius:2px;margin:1px;display:inline-block;color:${OP_COLOR[op]||'#888'};background:${OP_COLOR[op]||'#888'}22">${esc(op)}</span>`
      ).join('');
      const ftColor = p.file_type === 'sqr' ? '#0f9' : '#fa0';
      return `<tr>
        <td class="mono"><a class="obj-link" href="/admin/sqr/${encodeURIComponent(p.filename)}">${esc(p.filename)}</a></td>
        <td><span style="font-size:9px;font-weight:700;color:${ftColor}">${esc((p.file_type||'').toUpperCase())}</span></td>
        <td style="font-size:11px;color:#9ab">${esc(p.description||'—')}</td>
        <td>${ops}</td>
      </tr>`;
    }).join('') + '</tbody></table>';
}

const _RPC_EV_COLOR = {
  FieldChange:'#00e5ff',FieldEdit:'#ffaa00',FieldDefault:'#a070ff',FieldFormula:'#00cc66',
  RowInit:'#44bbff',RowInsert:'#44bbff',RowDelete:'#ff6666',
  SaveEdit:'#ffcc00',SavePreChange:'#ffcc00',SavePostChange:'#ffcc00',
};

function renderRecordPC(d) {
  const warn = d.warning || d.error || '';
  if (warn) return `<div class="warn-msg">&#9888; ${esc(warn)}</div>`;
  const rowEvts   = d.row_events   || [];
  const fieldEvts = d.field_events || [];
  if (!rowEvts.length && !fieldEvts.length)
    return `<div class="empty">No record-level PeopleCode programs on <span class="mono">${esc(d.recname||currentRec)}</span>.<br><span style="color:#445;font-size:10px">Record-level PC (OBJECTID1=1) fires independent of component. Component-level PC is shown on the <a href="/admin/compflow" style="color:#00e5ff">Comp Event Flow</a> page.</span></div>`;

  let html = `<div style="font-size:10px;color:#445;margin-bottom:10px">
    ${rowEvts.length} row-level event${rowEvts.length===1?'':'s'} · ${fieldEvts.length} field-level event${fieldEvts.length===1?'':'s'}
    <span style="color:#334;margin-left:8px">· OBJECTID1=1 — fires at record/field definition level, all components ·
    see <a onclick="switchTab('sequence');loadTab('sequence')" style="color:#00e5ff;cursor:pointer">Processing Sequence tab</a> for canonical ordering</span>
  </div>`;

  // Row-level events (no field name)
  if (rowEvts.length) {
    html += `<h2>Row-Level Events</h2>
      <table style="width:100%;border-collapse:collapse;font-size:11px">
      <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
        <th style="text-align:left;padding:3px 6px">Event</th>
        <th style="text-align:left;padding:3px 6px">Last Updated By</th>
        <th style="text-align:left;padding:3px 6px">Modified</th>
      </tr></thead><tbody>`;
    rowEvts.forEach(e => {
      const col = _RPC_EV_COLOR[e.event_type] || '#8ab';
      const modBadge = e.modified ? `<span style="color:#ffaa00;font-size:10px">&#9998; ${esc(e.last_oprid)}</span>` : '';
      html += `<tr style="border-bottom:1px solid #08101a">
        <td style="padding:3px 6px;color:${col};font-weight:bold">${esc(e.event_type)}</td>
        <td style="padding:3px 6px;color:#445;font-size:10px">${esc(e.last_oprid||'—')}</td>
        <td style="padding:3px 6px">${modBadge}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }

  // Field-level events — group by event type
  if (fieldEvts.length) {
    html += `<h2 style="margin-top:16px">Field-Level Events</h2>`;
    const byEvt = {};
    fieldEvts.forEach(e => { (byEvt[e.event_type]||(byEvt[e.event_type]=[])).push(e); });
    const evtOrder = ['FieldChange','FieldEdit','FieldDefault','FieldFormula','SearchInit','SearchSave'];
    const keys = [...new Set([...evtOrder.filter(k=>byEvt[k]), ...Object.keys(byEvt)])];
    keys.forEach(evt => {
      const entries = byEvt[evt];
      const col = _RPC_EV_COLOR[evt] || '#8ab';
      html += `<details open style="margin-bottom:10px">
        <summary style="cursor:pointer;font-size:11px;color:${col};padding:3px 0;letter-spacing:.5px">
          ${esc(evt)} <span style="color:#445;font-weight:normal">(${entries.length})</span>
        </summary>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;font-size:11px">
        <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
          <th style="text-align:left;padding:3px 6px">Field</th>
          <th style="text-align:left;padding:3px 6px">Last Updated By</th>
          <th style="text-align:left;padding:3px 6px">Modified</th>
        </tr></thead><tbody>`;
      entries.forEach(e => {
        const modBadge = e.modified ? `<span style="color:#ffaa00;font-size:10px">&#9998; ${esc(e.last_oprid)}</span>` : '';
        html += `<tr style="border-bottom:1px solid #08101a">
          <td style="padding:3px 6px">
            <a class="obj-link" href="/admin/field?field=${encodeURIComponent(e.field)}">${esc(e.field)}</a>
          </td>
          <td style="padding:3px 6px;color:#445;font-size:10px">${esc(e.last_oprid||'—')}</td>
          <td style="padding:3px 6px">${modBadge}</td>
        </tr>`;
      });
      html += `</tbody></table></details>`;
    });
  }
  return html;
}

const _SEQ_STATUS_COLOR = { empty: '#334', delivered: '#00e5ff', custom: '#ffaa00' };

function renderRecordSequence(d) {
  const phases = d.phases || [];
  if (!phases.length)
    return `<div class="empty">No canonical Record Field PeopleCode events on <span class="mono">${esc(d.record||currentRec)}</span>.<br><span style="color:#445;font-size:10px">This shows only genuinely record-owned PeopleCode (OBJECTID1=1), independent of any component — not Component-scoped PeopleCode (see the <a href="/admin/compflow" style="color:#00e5ff">Comp Event Flow</a> page for that).</span></div>`;

  const totalSlots = phases.reduce((s, ph) => s + ph.events.length, 0);
  const present = phases.reduce((s, ph) => s + ph.events.filter(e => e.status !== 'empty').length, 0);
  let html = `<div style="font-size:10px;color:#445;margin-bottom:12px">
    ${present}/${totalSlots} canonical slots have PeopleCode ·
    <span style="color:#334">record-owned only (OBJECTID1=1) — Component-only events (PreBuild/PostBuild/Activate/Workflow/SearchInit/SearchSave) don't apply here</span>
  </div>`;

  phases.forEach(ph => {
    html += `<h2>${esc(ph.label)} <span style="color:#445;font-weight:normal;text-transform:none;letter-spacing:0">— ${esc(ph.desc)}</span></h2>`;
    html += `<table style="width:100%;border-collapse:collapse;font-size:11px;margin-bottom:14px">
      <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
        <th style="text-align:left;padding:3px 6px">Event</th>
        <th style="text-align:left;padding:3px 6px">Purpose</th>
        <th style="text-align:left;padding:3px 6px">Field</th>
        <th style="text-align:left;padding:3px 6px">Status</th>
        <th style="text-align:left;padding:3px 6px">Last Updated By</th>
      </tr></thead><tbody>`;
    ph.events.forEach(e => {
      const col = _SEQ_STATUS_COLOR[e.status] || '#8ab';
      html += `<tr style="border-bottom:1px solid #08101a">
        <td style="padding:3px 6px;color:${col};font-weight:bold">${esc(e.name)}</td>
        <td style="padding:3px 6px;color:#556;font-size:10px">${esc(e.note||'')}</td>
        <td style="padding:3px 6px">${e.field ? esc(e.field) : '<span style="color:#334">—</span>'}</td>
        <td style="padding:3px 6px;color:${col}">${esc(e.status)}</td>
        <td style="padding:3px 6px;color:#445;font-size:10px">${e.last_oprid ? esc(e.last_oprid) : '—'}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  });
  return html;
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
  // If URL has a record name, load it.
  const path = window.location.pathname;
  const match = path.match(/\\/admin\\/record\\/([^/]+)$/);
  if (match) loadRecord(decodeURIComponent(match[1]));

  window.addEventListener('deathstar:envchange', () => {
    if (currentRec) loadRecord(currentRec);
  });
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
        <div class="tab"    onclick="setTab('pc')">PeopleCode</div>
      </div>
      <div id="paneRecords" class="pane on"><div id="tblRecords"></div></div>
      <div id="paneKeyed"   class="pane"><div id="tblKeyed"></div></div>
      <div id="paneRectype" class="pane"><div id="tblRectype"></div></div>
      <div id="panePc"      class="pane"><div id="tblPc"><span class="empty">Loading…</span></div></div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
function env() { return (document.getElementById('globalEnv') || {}).value || 'HCM'; }
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
  _pcLoaded = false;
  _pcData = null;
  $('placeholder').style.display = 'none';
  $('fieldContent').style.display = '';
  $('fieldTitle').textContent = name;
  $('fieldTypeChip').textContent = '';
  $('fieldLenChip').textContent = '';
  $('statGrid').innerHTML = '<div style="color:#445;font-size:11px;">Loading…</div>';
  $('tblRecords').innerHTML = '<div class="empty">Loading…</div>';
  $('tblKeyed').innerHTML = '';
  $('tblRectype').innerHTML = '';
  $('tblPc').innerHTML = '<span class="empty">Loading…</span>';
  $('fieldObjLink').href = `/admin/object/field/${encodeURIComponent(name)}`;

  // Load definition + records in parallel; kick off PC count in background
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

  let pcCount = null;
  if (recRes.status === 'fulfilled') {
    const d = recRes.value;
    allRecords = d.items || [];
    (d.warnings||[]).forEach(w => $('tblRecords').innerHTML += `<div class="warn-msg">&#9888; ${esc(w.message)}</div>`);
    renderStats(allRecords, null);
    renderRecords(allRecords);
    renderKeyed(allRecords);
    renderByType(allRecords);
  } else {
    $('tblRecords').innerHTML = `<div class="warn-msg">Error: ${esc(recRes.reason?.message)}</div>`;
    $('statGrid').innerHTML = '';
  }

  // Background: load PC count to update stat grid (non-blocking)
  _pcData = null;
  api(`/api/field/${encodeURIComponent(name)}/peoplecode?env=${env()}`).then(pcData => {
    if (currentField !== name) return;
    _pcData = pcData;
    renderStats(allRecords, pcData.total_handlers || 0);
    if (_pcLoaded) renderPC(pcData);
  }).catch(() => {});
}

function renderStats(rows, pcCount) {
  const total = rows.length;
  const keyed = rows.filter(r => r.is_key).length;
  const views = rows.filter(r => [1,5,6].includes(r.rectype)).length;
  const tables = rows.filter(r => r.rectype === 0).length;
  const stats = [
    {v: total,  l: 'Records Using Field'},
    {v: tables, l: 'SQL Tables'},
    {v: views,  l: 'Views'},
    {v: keyed,  l: 'Used as Key'},
  ];
  if (pcCount !== null && pcCount !== undefined) {
    stats.push({v: pcCount, l: 'PC Handlers'});
  }
  $('statGrid').innerHTML = stats.map(s =>
    `<div class="stat-box"><div class="sv">${s.v.toLocaleString()}</div><div class="sl">${s.l}</div></div>`
  ).join('');
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

let _pcLoaded = false;
let _pcData = null;

function setTab(name) {
  ['records','keyed','rectype','pc'].forEach(n => {
    const tab = document.querySelector(`.tab[onclick*="'${n}'"]`);
    if (tab) tab.classList.toggle('on', n === name);
    const p = $(`pane${n.charAt(0).toUpperCase()+n.slice(1)}`);
    if (p) p.classList.toggle('on', n === name);
  });
  if (name === 'pc' && !_pcLoaded) loadPCTab();
}

async function loadPCTab() {
  _pcLoaded = true;
  if (!currentField) return;
  if (_pcData) { renderPC(_pcData); return; }
  $('tblPc').innerHTML = '<div class="empty">Loading PeopleCode handlers…</div>';
  try {
    const d = await api(`/api/field/${encodeURIComponent(currentField)}/peoplecode?env=${env()}`);
    _pcData = d;
    renderPC(d);
  } catch(e) {
    $('tblPc').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

const _EV_COLOR = {
  FieldChange:'#00e5ff', FieldEdit:'#ffaa00', FieldFormula:'#00cc66',
  FieldDefault:'#a070ff', SearchInit:'#ff88aa', SearchSave:'#ff88aa',
  RowInit:'#44bbff', RowInsert:'#44bbff', RowDelete:'#ff6666',
  SaveEdit:'#ffcc00', SavePreChange:'#ffcc00', SavePostChange:'#ffcc00',
};

function renderPC(d) {
  const comp = d.component_handlers || [];
  const rec  = d.record_handlers   || [];
  if (!comp.length && !rec.length) {
    $('tblPc').innerHTML = `<div class="empty">No PeopleCode programs found for field <b>${esc(d.fieldname||currentField)}</b>.</div>`;
    return;
  }
  let html = `<div style="font-size:10px;color:#445;margin-bottom:10px;">
    ${comp.length} component handler${comp.length===1?'':'s'} · ${rec.length} record-level handler${rec.length===1?'':'s'}
  </div>`;

  // Group component handlers by event_type
  if (comp.length) {
    html += `<h2>Component PeopleCode</h2>`;
    const byEvt = {};
    comp.forEach(h => { (byEvt[h.event_type]||(byEvt[h.event_type]=[])).push(h); });
    const evtOrder = ['FieldChange','FieldEdit','FieldDefault','FieldFormula','RowInit','RowInsert','RowDelete','SearchInit','SearchSave','SaveEdit','SavePreChange','SavePostChange'];
    const evtKeys = [...new Set([...evtOrder.filter(e=>byEvt[e]), ...Object.keys(byEvt)])];
    evtKeys.forEach(evt => {
      const handlers = byEvt[evt];
      const col = _EV_COLOR[evt] || '#8ab';
      html += `<details open style="margin-bottom:10px;">
        <summary style="cursor:pointer;font-size:11px;color:${col};padding:3px 0;letter-spacing:.5px;">
          ${esc(evt)} <span style="color:#445;font-weight:normal;">(${handlers.length})</span>
        </summary>
        <table style="width:100%;border-collapse:collapse;margin-top:4px;font-size:11px;">
          <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
            <th style="text-align:left;padding:3px 6px">Component</th>
            <th style="text-align:left;padding:3px 6px">Record</th>
            <th style="text-align:left;padding:3px 6px">Mkt</th>
          </tr></thead><tbody>`;
      handlers.forEach(h => {
        html += `<tr style="border-bottom:1px solid #08101a">
          <td style="padding:3px 6px">
            <a class="obj-link" href="/admin/compflow?comp=${encodeURIComponent(h.component)}">${esc(h.component)}</a>
          </td>
          <td style="padding:3px 6px">
            <a class="obj-link" href="/admin/record/${esc(h.recname)}">${esc(h.recname)}</a>
          </td>
          <td style="padding:3px 6px;color:#445;font-size:10px">${esc(h.market||'GBL')}</td>
        </tr>`;
      });
      html += `</tbody></table></details>`;
    });
  }

  // Record-level handlers
  if (rec.length) {
    html += `<h2>Record PeopleCode</h2>
      <table style="width:100%;border-collapse:collapse;font-size:11px;">
        <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
          <th style="text-align:left;padding:3px 6px">Record</th>
          <th style="text-align:left;padding:3px 6px">Event</th>
        </tr></thead><tbody>`;
    rec.forEach(h => {
      const col = _EV_COLOR[h.event_type] || '#8ab';
      html += `<tr style="border-bottom:1px solid #08101a">
        <td style="padding:3px 6px">
          <a class="obj-link" href="/admin/record/${esc(h.recname)}">${esc(h.recname)}</a>
        </td>
        <td style="padding:3px 6px;color:${col}">${esc(h.event_type)}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
  }
  $('tblPc').innerHTML = html;
}

(async () => {
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

  window.addEventListener('deathstar:envchange', () => {
    if ($('searchInput').value.trim()) doSearch();
    if (currentField) loadField(currentField, null);
  });
})();
</script>""")


@router.get("/operator", response_class=HTMLResponse)
@router.get("/operator/{oprid_val:path}", response_class=HTMLResponse)
def admin_operator(oprid_val: str = None):
    return _shell("Operator Explorer", "operator", noscroll=True, content="""\
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
        <div class="tab"    onclick="setTab('activity')">Activity</div>
        <div class="tab"    onclick="setTab('prcs')">Processes</div>
      </div>
      <div id="paneOverview" class="pane on"><div id="tblOverview"></div></div>
      <div id="paneRoles"    class="pane"><div id="tblRoles"></div></div>
      <div id="paneActivity" class="pane"><div id="tblActivity"><span class="empty">Loading…</span></div></div>
      <div id="panePrcs"     class="pane"><div id="tblPrcs"><span class="empty">Loading…</span></div></div>
    </div>
  </div>
</div>
<script>
const $ = id => document.getElementById(id);
function env() { return (document.getElementById('globalEnv') || {}).value || 'HCM'; }
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
  _actLoaded = false;
  _prcsLoaded = false;
  $('tblOverview').innerHTML = '<div class="empty">Loading…</div>';
  $('tblRoles').innerHTML = '<div class="empty">Loading…</div>';
  $('tblActivity').innerHTML = '<span class="empty">Loading…</span>';
  $('tblPrcs').innerHTML = '<span class="empty">Loading…</span>';
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
  <div class="kv"><span class="kl">Permission List</span><span class="kv-val">${item.oprclass ? `<a class="obj-link" href="/admin/permissionlist/${esc(item.oprclass)}?env=${env()}">${esc(item.oprclass)}</a>` : '—'}</span></div>
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

let _actLoaded = false, _prcsLoaded = false;

function setTab(name) {
  ['overview','roles','activity','prcs'].forEach(n => {
    const tab = document.querySelector(`.tab[onclick*="'${n}'"]`);
    if (tab) tab.classList.toggle('on', n === name);
    const cap = n.charAt(0).toUpperCase()+n.slice(1);
    const p = $(`pane${cap}`);
    if (p) p.classList.toggle('on', n === name);
  });
  if (name === 'activity' && !_actLoaded)  loadActivityTab();
  if (name === 'prcs'     && !_prcsLoaded) loadPrcsTab();
}

async function loadActivityTab() {
  _actLoaded = true;
  if (!currentOp) return;
  $('tblActivity').innerHTML = '<div class="empty">Loading activity…</div>';
  try {
    const d = await api(`/api/operator/${encodeURIComponent(currentOp)}/activity?env=${env()}&hours=48&limit=200`);
    renderActivity(d);
  } catch(e) {
    $('tblActivity').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

async function loadPrcsTab() {
  _prcsLoaded = true;
  if (!currentOp) return;
  $('tblPrcs').innerHTML = '<div class="empty">Loading processes…</div>';
  try {
    const d = await api(`/api/operator/${encodeURIComponent(currentOp)}/processes?env=${env()}&days=30&limit=200`);
    renderProcesses(d);
  } catch(e) {
    $('tblPrcs').innerHTML = `<div class="warn-msg">Error: ${esc(e.message)}</div>`;
  }
}

function renderActivity(d) {
  const items = d.items || [];
  const warn  = d.warning || d.error || '';
  if (warn && !items.length) {
    $('tblActivity').innerHTML = `<div class="warn-msg">&#9888; ${esc(warn)}</div>`;
    return;
  }
  if (!items.length) {
    $('tblActivity').innerHTML = `<div class="empty">No access log entries found in the last 48 hours.</div>`;
    return;
  }
  const hasPages = d.has_page_tracking;
  let html = `<div style="font-size:10px;color:#445;margin-bottom:8px">${items.length} entries · last 48h
    ${!hasPages ? '<span style="color:#334;margin-left:8px">· PSACCESSLOG in this environment does not capture page-level detail</span>' : ''}
  </div>
    <table style="width:100%;border-collapse:collapse;font-size:11px">
    <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
      <th style="text-align:left;padding:3px 6px">Login Time</th>
      <th style="text-align:left;padding:3px 6px">Logout Time</th>
      ${hasPages ? '<th style="text-align:left;padding:3px 6px">Component</th><th style="text-align:left;padding:3px 6px">Menu</th>' : ''}
      <th style="text-align:left;padding:3px 6px">IP</th>
      <th style="text-align:left;padding:3px 6px">Type</th>
    </tr></thead><tbody>`;
  items.forEach(it => {
    const ts    = (it.ts||'').replace('T',' ').substring(0,19);
    const tsOut = (it.ts_out||'').replace('T',' ').substring(0,19);
    const compLink = it.component
      ? `<a class="obj-link" href="/admin/compflow?comp=${encodeURIComponent(it.component)}">${esc(it.component)}</a>`
      : '—';
    const stCol = it.signon_type === 1 ? '#00cc66' : it.signon_type === 0 ? '#445' : '#556';
    const stLbl = it.signon_type === 1 ? 'SSO' : it.signon_type === 0 ? 'Svc' : (it.signon_type ?? '');
    html += `<tr style="border-bottom:1px solid #08101a">
      <td class="mono" style="padding:3px 6px;color:#334;font-size:10px;white-space:nowrap">${esc(ts)}</td>
      <td class="mono" style="padding:3px 6px;color:#223;font-size:10px;white-space:nowrap">${esc(tsOut||'—')}</td>
      ${hasPages ? `<td style="padding:3px 6px">${compLink}</td><td style="padding:3px 6px;color:#556;font-size:10px">${esc(it.menu||'—')}</td>` : ''}
      <td style="padding:3px 6px;color:#445;font-size:10px">${esc(it.ipaddress||'—')}</td>
      <td style="padding:3px 6px;color:${stCol};font-size:10px">${esc(String(stLbl))}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  $('tblActivity').innerHTML = html;
}

const _PRCS_STATUS_COLOR = {
  'Success':'#00cc66','Error':'#ff4444','Processing':'#ffaa00',
  'Queued':'#00e5ff','Cancel':'#ff8855','Scheduled':'#88aaff',
  'Blocked':'#ff8800','Initiated':'#66ddff',
};

function renderProcesses(d) {
  const items = d.items || [];
  const warn  = d.warning || d.error || '';
  if (warn && !items.length) {
    $('tblPrcs').innerHTML = `<div class="warn-msg">&#9888; ${esc(warn)}</div>`;
    return;
  }
  if (!items.length) {
    $('tblPrcs').innerHTML = `<div class="empty">No process submissions in the last 30 days.</div>`;
    return;
  }
  let html = `<div style="font-size:10px;color:#445;margin-bottom:8px">${items.length} submissions · last 30d</div>
    <table style="width:100%;border-collapse:collapse;font-size:11px">
    <thead><tr style="color:#445;border-bottom:1px solid #0a2030">
      <th style="text-align:left;padding:3px 6px">Instance</th>
      <th style="text-align:left;padding:3px 6px">Process</th>
      <th style="text-align:left;padding:3px 6px">Type</th>
      <th style="text-align:left;padding:3px 6px">Run Control</th>
      <th style="text-align:left;padding:3px 6px">Run Time</th>
      <th style="text-align:left;padding:3px 6px">Status</th>
    </tr></thead><tbody>`;
  items.forEach(it => {
    const ts = (it.run_dt||'').replace('T',' ').substring(0,16);
    const col = _PRCS_STATUS_COLOR[it.status_label] || '#778';
    html += `<tr style="border-bottom:1px solid #08101a">
      <td style="padding:3px 6px;font-size:10px;color:#445">${esc(String(it.instance||''))}</td>
      <td style="padding:3px 6px">
        <a class="obj-link" href="/admin/object/ae_program/${encodeURIComponent(it.prcsname)}" title="${esc(it.prcstype)}">${esc(it.prcsname)}</a>
      </td>
      <td style="padding:3px 6px;color:#556;font-size:10px">${esc(it.prcstype||'')}</td>
      <td style="padding:3px 6px;color:#667;font-size:10px">${esc(it.runcntlid||'—')}</td>
      <td class="mono" style="padding:3px 6px;color:#334;font-size:10px;white-space:nowrap">${esc(ts)}</td>
      <td style="padding:3px 6px;color:${col};font-size:10px;font-weight:bold">${esc(it.status_label||it.runstatus||'—')}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  $('tblPrcs').innerHTML = html;
}

(async () => {
  doSearch();

  const pathMatch = window.location.pathname.match(/\/admin\/operator\/(.+)$/);
  const opParam   = new URLSearchParams(window.location.search).get('oprid') || (pathMatch ? decodeURIComponent(pathMatch[1]) : null);
  if (opParam) {
    $('searchInput').value = opParam;
    await doSearch();
    const el = document.getElementById(`oi_${opParam}`);
    loadOp(opParam, el||null);
  }

  window.addEventListener('deathstar:envchange', doSearch);
})();
</script>""")


@router.get("/role", response_class=HTMLResponse)
@router.get("/role/{rolename:path}", response_class=HTMLResponse)
def admin_role(rolename: str = None):
    return _shell("Role Explorer", "role", noscroll=True, content="""\
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
function env() { return (document.getElementById('globalEnv') || {}).value || 'HCM'; }
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
    <td class="mono"><a class="obj-link" href="/admin/permissionlist/${esc(r.classid)}?env=${env()}">${esc(r.classid)}</a></td>
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

  window.addEventListener('deathstar:envchange', doSearch);
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
    return `<div class="result-item${isSelected ? ' selected' : ''}" data-ref="${esc(item.encoded_reference)}" onclick="loadPC(this.dataset.ref)">
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
      .map(e => `<option value="${e.environment}">${e.environment}</option>`).join('');
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




@router.get("/permissionlist", response_class=HTMLResponse)
@router.get("/permissionlist/{classid_val:path}", response_class=HTMLResponse)
def admin_permissionlist(classid_val: str = None):
    from ._core import _NAV_CSS, _ESC_JS, _nav_html
    nav = _nav_html("permissionlist")
    INIT_CLASSID = json.dumps(classid_val or "")
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Permission List Explorer</title>
<meta charset="utf-8">
<link rel="stylesheet" href="/static/app.css?v=2">
<script src="/static/app.js?v=2"></script>
{_NAV_CSS}
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050b12;color:#c8d8e8;font-family:Arial,sans-serif}}
.muted{{color:#446;font-style:italic;font-size:12px}}
.list-item{{padding:6px 10px;border-radius:3px;cursor:pointer;margin-bottom:1px;border-bottom:1px solid #0d1520}}
.list-item:hover{{background:rgba(255,153,0,.06)}}
.list-item.sel{{background:rgba(255,153,0,.12);border-left:2px solid #ff9900}}
.tab-row{{display:flex;gap:2px;margin-bottom:14px;border-bottom:1px solid #1a2a3a}}
.tab{{padding:6px 14px;cursor:pointer;font-size:12px;color:#778;border-bottom:2px solid transparent;margin-bottom:-1px}}
.tab:hover{{color:#acd}}.tab.on{{color:#ff9900;border-bottom-color:#ff9900}}
.pane{{display:none}}.pane.on{{display:block}}
.kv{{display:grid;grid-template-columns:180px 1fr;gap:2px 8px;font-size:12px;margin-bottom:12px}}
.kv-lbl{{color:#556;padding:2px 0}}.kv-val{{color:#acd;font-family:monospace;word-break:break-all;padding:2px 0}}
.stat-row{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.stat-pill{{background:rgba(255,153,0,.08);border:1px solid rgba(255,153,0,.25);border-radius:4px;padding:6px 14px;text-align:center}}
.stat-num{{font-size:20px;font-weight:bold;color:#ff9900;display:block}}
.stat-lbl{{font-size:10px;color:#556;text-transform:uppercase;letter-spacing:.5px}}
.comp-block{{background:#0a1520;border:1px solid rgba(255,153,0,.15);border-radius:4px;margin-bottom:6px}}
.comp-hdr{{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer}}
.comp-hdr:hover{{background:rgba(255,153,0,.05)}}
.comp-body{{padding:4px 12px 8px 24px;display:none}}
.comp-body.open{{display:block}}
.pg-row{{display:flex;align-items:center;gap:6px;padding:3px 6px;font-size:12px;border-bottom:1px solid #0d1520}}
.pg-row:last-child{{border-bottom:none}}
.action-badge{{display:inline-block;font-size:10px;padding:1px 5px;border-radius:2px;margin-right:3px}}
.role-row{{display:flex;align-items:center;padding:7px 10px;border-bottom:1px solid #0d1520;font-size:13px}}
.role-row:hover{{background:rgba(255,170,34,.05)}}
.menu-row{{padding:6px 10px;border-bottom:1px solid #0d1520;font-size:12px}}
.menu-row:hover{{background:rgba(0,229,255,.04)}}
</style>
</head><body>
{nav}
<div class="ds-page-hdr">
  <span class="ds-page-title">Permission List Explorer</span>
  <div class="ds-env">
    <span class="ds-env-lbl">Env</span>
    <select class="ds-env-sel" id="globalEnv"></select>
  </div>
</div>
<div style="display:grid;grid-template-columns:280px 1fr;height:calc(100vh - 90px)">
  <!-- RAIL -->
  <div style="border-right:1px solid #1a2a3a;display:flex;flex-direction:column;overflow:hidden">
    <div style="padding:10px;border-bottom:1px solid #1a2a3a">
      <div style="font-size:11px;color:#ff9900;font-weight:bold;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">Permission Lists</div>
      <input id="q" type="text" placeholder="Search permission lists..." autocomplete="off"
        style="width:100%;background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 8px;border-radius:3px;font-size:12px;outline:none">
      <div id="rail-status" style="font-size:11px;color:#446;margin-top:5px">&nbsp;</div>
    </div>
    <div id="rail-list" style="overflow-y:auto;flex:1;padding:4px"></div>
  </div>
  <!-- DETAIL -->
  <div id="detail-panel" style="overflow-y:auto;padding:20px">
    <div class="muted" style="margin-top:40px;text-align:center">Search for a permission list to explore its components and roles.</div>
  </div>
</div>
<script>
{_ESC_JS}
function ENV_VAL() {{ return window.dsGetEnv ? window.dsGetEnv() : ((new URLSearchParams(location.search).get('env')) || 'HCM'); }}

async function api(url) {{
  try {{ const r = await fetch(url); if (!r.ok) return null; return await r.json(); }} catch(e) {{ return null; }}
}}
function fmt(s) {{
  if (!s) return '';
  const d = new Date(s);
  return isNaN(d) ? s : d.toLocaleDateString('en-AU', {{year:'numeric',month:'short',day:'numeric'}});
}}

let debounce;
document.getElementById('q').addEventListener('input', () => {{ clearTimeout(debounce); debounce = setTimeout(doSearch, 220); }});
document.getElementById('q').addEventListener('keydown', e => {{ if (e.key==='Enter') {{ clearTimeout(debounce); doSearch(); }} }});

async function doSearch() {{
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  document.getElementById('rail-status').textContent = 'Searching...';
  const rows = await api(`/api/peoplesoft/permissionlists?env=${{ENV_VAL()}}&q=${{encodeURIComponent(q)}}&limit=100`);
  const list = document.getElementById('rail-list');
  if (!rows || !rows.length) {{
    list.innerHTML = '<div class="muted" style="padding:12px">No permission lists found.</div>';
    document.getElementById('rail-status').textContent = '0 results';
    return;
  }}
  document.getElementById('rail-status').textContent = rows.length + ' result' + (rows.length===1?'':'s');
  list.innerHTML = rows.map(r => {{
    const id = r.classid || '';
    const desc = r.classdefndesc || '';
    return `<div class="list-item" onclick="loadPL(this.dataset.id)" data-id="${{esc(id)}}">
      <div style="font-family:monospace;font-size:12px;color:#c8d8e8">${{esc(id)}}</div>
      ${{desc ? `<div style="font-size:11px;color:#556;margin-top:1px">${{esc(desc)}}</div>` : ''}}
    </div>`;
  }}).join('');
}}

async function loadPL(classid) {{
  document.querySelectorAll('.list-item').forEach(el => el.classList.toggle('sel', el.dataset.id === classid));
  const panel = document.getElementById('detail-panel');
  panel.innerHTML = '<div class="muted" style="margin-top:40px;text-align:center">Loading...</div>';
  history.replaceState(null, '', `/admin/permissionlist/${{encodeURIComponent(classid)}}?env=${{ENV_VAL()}}`);

  const d = await api(`/api/peoplesoft/object/permissionlist/${{encodeURIComponent(classid)}}?env=${{ENV_VAL()}}`);
  if (!d) {{ panel.innerHTML = '<div style="color:#f88;padding:20px">Failed to load data.</div>'; return; }}
  renderPL(d, classid, panel);
}}

function renderPL(d, classid, panel) {{
  const ov = d.overview || {{}};
  const secs = d.sections || [];
  const by = {{}};
  secs.forEach(s => {{ if (s.name) by[s.name] = s; }});

  const def = (by['Definition'] || {{}}).data || {{}};
  const roles     = (by['Roles']      || {{}}).items || [];
  const menus     = (by['Menus']      || {{}}).items || [];
  const comps     = (by['Components'] || {{}}).items || [];
  const pgGrants  = (by['Page Grants']|| {{}}).items || [];

  // Overview
  const ovHtml = `
    <div class="stat-row">
      <div class="stat-pill"><span class="stat-num">${{roles.length}}</span><span class="stat-lbl">Roles</span></div>
      <div class="stat-pill"><span class="stat-num">${{(by['Components']||{{}}).data?.count || new Set(comps.map(c=>c.pnlgrpname)).size}}</span><span class="stat-lbl">Components</span></div>
      <div class="stat-pill"><span class="stat-num">${{menus.length}}</span><span class="stat-lbl">Menus</span></div>
      <div class="stat-pill"><span class="stat-num">${{pgGrants.filter(p=>p.level===1).length}}</span><span class="stat-lbl">Page Grants</span></div>
    </div>
    <div class="kv">
      <span class="kv-lbl">Permission List</span><span class="kv-val">${{esc(classid)}}</span>
      ${{def.description||def.descr ? `<span class="kv-lbl">Description</span><span class="kv-val" style="color:#c8d8e8">${{esc(def.description||def.classdefndesc||def.descr||'')}}</span>` : ''}}
      ${{def.timeout_minutes != null ? `<span class="kv-lbl">Session Timeout</span><span class="kv-val">${{def.timeout_minutes}} min</span>` : ''}}
      ${{def.version != null ? `<span class="kv-lbl">Version</span><span class="kv-val">${{def.version}}</span>` : ''}}
      <span class="kv-lbl">Last Updated</span><span class="kv-val">${{fmt(def.lastupddttm||ov.lastupddttm||'')}}</span>
      <span class="kv-lbl">Updated By</span><span class="kv-val">${{esc(def.lastupdoprid||ov.lastupdoprid||'')}}</span>
    </div>`;

  // Components tab — use Page Grants (hierarchical) if available, else flat comps
  let compHtml = '';
  let blocks = null;
  if (!pgGrants.length && !comps.length) {{
    compHtml = '<div class="muted">No component grants found.</div>';
  }} else if (pgGrants.length) {{
    // pgGrants: level=0 → component header, level=1 → page row
    let curComp = null;
    blocks = [];
    let pages = [];
    pgGrants.forEach(pg => {{
      if (pg.level === 0) {{
        if (curComp) blocks.push({{comp: curComp, pages}});
        curComp = pg;
        pages = [];
      }} else {{
        pages.push(pg);
      }}
    }});
    if (curComp) blocks.push({{comp: curComp, pages}});

    compHtml = blocks.map((b, idx) => {{
      const cname = b.comp.pnlgrpname || b.comp.name || '';
      const cdesc = b.comp.component_descr || '';
      const pgRows = b.pages.map(pg => {{
        const rel = pg.relationship || '';
        const isCorr = rel.toLowerCase().includes('correction');
        const isUpd  = rel.toLowerCase().includes('update');
        const ac = `<span class="action-badge" style="background:rgba(${{isCorr?'255,68,68':isUpd?'34,204,136':'68,170,255'}},.15);color:${{isCorr?'#ff8888':isUpd?'#44cc88':'#44aaff'}};border:1px solid rgba(${{isCorr?'255,68,68':isUpd?'34,204,136':'68,170,255'}},.3)">${{esc(rel)}}</span>`;
        return `<div class="pg-row">
          <span style="font-family:monospace;color:#8aabb8">${{esc(pg.pnlname||pg.name||'')}}</span>
          <span style="margin-left:auto">${{ac}}</span>
        </div>`;
      }}).join('');
      const uid = 'cb'+idx;
      return `<div class="comp-block">
        <div class="comp-hdr" onclick="toggleBlock('${{uid}}')">
          <span style="color:#778;font-size:11px">&#x25B6;</span>
          <a href="/admin/component?name=${{encodeURIComponent(cname)}}&env=${{ENV_VAL()}}" style="color:#44aaff;font-family:monospace;font-size:13px;text-decoration:none" onclick="event.stopPropagation()">${{esc(cname)}}</a>
          ${{cdesc ? `<span style="color:#556;font-size:11px">${{esc(cdesc)}}</span>` : ''}}
          <span style="margin-left:auto;color:#446;font-size:11px">${{b.pages.length}} page(s)</span>
        </div>
        <div class="comp-body" id="${{uid}}">${{pgRows}}</div>
      </div>`;
    }}).join('');
  }} else {{
    // flat comps
    const seen = new Set();
    compHtml = comps.filter(c => {{ const k = c.pnlgrpname; if (seen.has(k)) return false; seen.add(k); return true; }}).map(c => {{
      const cname = c.pnlgrpname || '';
      return `<div style="padding:5px 8px;border-bottom:1px solid #0d1520;font-size:12px">
        <a href="/admin/component?name=${{encodeURIComponent(cname)}}&env=${{ENV_VAL()}}" style="color:#44aaff;font-family:monospace">${{esc(cname)}}</a>
        <span style="color:#556;margin-left:8px">${{esc(c.component_descr||'')}}</span>
      </div>`;
    }}).join('');
  }}

  // Roles tab
  const rolesHtml = roles.length ? roles.map(r => {{
    const rn = r.rolename || '';
    return `<div class="role-row">
      <a href="/admin/role/${{encodeURIComponent(rn)}}?env=${{ENV_VAL()}}" style="color:#ffaa22;font-size:13px;text-decoration:none" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${{esc(rn)}}</a>
    </div>`;
  }}).join('') : '<div class="muted">No roles assigned.</div>';

  // Menus tab
  const menusHtml = menus.length ? menus.map(m => {{
    const mn = m.menuname || m.name || '';
    const mi = m.baritemname || '';
    return `<div class="menu-row">
      <a href="/admin/object/menu/${{encodeURIComponent(mn)}}?env=${{ENV_VAL()}}" style="color:#00e5ff;font-family:monospace;font-size:12px;text-decoration:none" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${{esc(mn)}}</a>
      ${{mi ? `<span style="color:#446;margin-left:8px;font-size:11px">${{esc(mi)}}</span>` : ''}}
    </div>`;
  }}).join('') : '<div class="muted">No menus found.</div>';

  panel.innerHTML = `
    <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:16px;flex-wrap:wrap">
      <h1 style="margin:0;font-family:monospace;font-size:20px;color:#ff9900">${{esc(classid)}}</h1>
      ${{def.description||def.classdefndesc ? `<span style="color:#778;font-size:14px">${{esc(def.description||def.classdefndesc||'')}}</span>` : ''}}
    </div>
    <div class="tab-row">
      <div class="tab on" onclick="setTab('overview',this)">Overview</div>
      <div class="tab" onclick="setTab('components',this)">Components (${{blocks ? blocks.length : new Set(comps.map(c=>c.pnlgrpname)).size}})</div>
      <div class="tab" onclick="setTab('roles',this)">Roles (${{roles.length}})</div>
      <div class="tab" onclick="setTab('menus',this)">Menus (${{menus.length}})</div>
    </div>
    <div id="pane-overview"    class="pane on">${{ovHtml}}</div>
    <div id="pane-components"  class="pane">${{compHtml}}</div>
    <div id="pane-roles"       class="pane">${{rolesHtml}}</div>
    <div id="pane-menus"       class="pane">${{menusHtml}}</div>`;
}}

function setTab(name, el) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('on'));
  el.classList.add('on');
  const pane = document.getElementById('pane-' + name);
  if (pane) pane.classList.add('on');
}}

function toggleBlock(uid) {{
  const body = document.getElementById(uid);
  if (!body) return;
  const hdr = body.previousElementSibling;
  const arrow = hdr && hdr.querySelector('span');
  body.classList.toggle('open');
  if (arrow) arrow.textContent = body.classList.contains('open') ? '▼' : '▶';
}}

(function() {{
  const params = new URLSearchParams(location.search);
  const q = params.get('q');
  const initId = {INIT_CLASSID};
  if (initId) {{
    if (q) {{ document.getElementById('q').value = q; doSearch(); }}
    loadPL(initId);
  }} else if (q) {{
    document.getElementById('q').value = q;
    doSearch();
  }}
}})();

// The global shell's ENV selector (app.js) calls window.onEnvChange(v) when
// present and always dispatches a 'deathstar:envchange' event — this page
// only read ENV from the URL once at load, so switching environments
// silently left the prior env's rail list and detail panel on screen.
function reload() {{
  document.getElementById('detail-panel').innerHTML =
    '<div class="muted" style="margin-top:40px;text-align:center">Search for a permission list to explore its components and roles.</div>';
  doSearch();
}}
window.onEnvChange = reload;
document.addEventListener('deathstar:envchange', reload);
</script>
</body></html>""")


@router.get("/secaudit", response_class=HTMLResponse)
def admin_secaudit():
    return _shell("Security Audit", "secaudit", content="""
<style>
.sa-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.sa-card{background:rgba(0,20,30,.7);border:1px solid rgba(0,229,255,.18);border-radius:6px;
  padding:16px 20px;display:flex;flex-direction:column;gap:4px}
.sa-card-val{font-size:28px;font-weight:700;color:#00e5ff;line-height:1}
.sa-card-lbl{font-size:11px;color:#7faab2;text-transform:uppercase;letter-spacing:.5px}
.sa-panels{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.sa-panel{background:rgba(0,20,30,.7);border:1px solid rgba(0,229,255,.18);border-radius:6px;
  padding:14px 16px;overflow:hidden}
.sa-panel-hdr{font-size:12px;font-weight:600;color:#00e5ff;letter-spacing:.3px;
  margin-bottom:10px;text-transform:uppercase}
.sa-tbl{width:100%;border-collapse:collapse;font-size:12px}
.sa-tbl th{text-align:left;padding:5px 8px;color:#7faab2;font-weight:500;
  border-bottom:1px solid rgba(0,229,255,.12)}
.sa-tbl td{padding:5px 8px;color:#d7faff;border-bottom:1px solid rgba(0,229,255,.06)}
.sa-tbl tr:last-child td{border-bottom:none}
.sa-tbl tr:hover td{background:rgba(0,229,255,.05)}
.sa-link{color:#00e5ff;text-decoration:none}.sa-link:hover{text-decoration:underline}
.sa-bar-wrap{display:flex;align-items:center;gap:8px}
.sa-bar{height:8px;border-radius:4px;background:#00e5ff;flex-shrink:0;min-width:3px}
.sa-badge{background:rgba(0,229,255,.14);color:#00e5ff;border-radius:3px;
  padding:1px 7px;font-size:11px;font-weight:600;white-space:nowrap}
.sa-full{grid-column:1/-1}
.sa-env-bar{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.sa-env-sel{background:rgba(0,20,30,.88);border:1px solid rgba(0,229,255,.25);
  color:#d7faff;font-size:12px;padding:3px 8px;border-radius:4px}
.sa-btn{background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.3);
  color:#00e5ff;font-size:12px;padding:4px 14px;border-radius:4px;cursor:pointer}
.sa-btn:hover{background:rgba(0,229,255,.2)}
.sa-spinner{color:#7faab2;font-size:12px;font-style:italic}
.sa-orphan-count{font-size:16px;font-weight:700;color:#ffb400}
.sa-oprtype{font-size:10px;color:#7faab2;background:rgba(255,255,255,.06);
  border-radius:3px;padding:1px 6px;display:inline-block}
</style>

<div class="sa-env-bar">
  <button class="sa-btn" onclick="loadAll()">Refresh</button>
  <span id="status" class="sa-spinner" style="margin-left:8px"></span>
</div>

<div class="sa-grid" id="cards">
  <div class="sa-card"><div class="sa-card-val" id="c-ops">—</div>
    <div class="sa-card-lbl">Total Operators</div></div>
  <div class="sa-card"><div class="sa-card-val" id="c-roles">—</div>
    <div class="sa-card-lbl">Total Roles</div></div>
  <div class="sa-card"><div class="sa-card-val" id="c-pls">—</div>
    <div class="sa-card-lbl">Permission Lists</div></div>
  <div class="sa-card"><div class="sa-card-val" id="c-recent">—</div>
    <div class="sa-card-lbl">Active (30d)</div></div>
</div>

<div class="sa-panels">
  <div class="sa-panel">
    <div class="sa-panel-hdr">Top Roles by Member Count</div>
    <div id="top-roles"><span class="sa-spinner">Loading…</span></div>
  </div>
  <div class="sa-panel">
    <div class="sa-panel-hdr">Top Operators by Role Count</div>
    <div id="top-ops"><span class="sa-spinner">Loading…</span></div>
  </div>
  <div class="sa-panel">
    <div class="sa-panel-hdr">Recent Sign-ons (Last 30 Days)</div>
    <div id="recent-signon"><span class="sa-spinner">Loading…</span></div>
  </div>
  <div class="sa-panel">
    <div class="sa-panel-hdr">Orphaned Roles
      <span style="font-size:11px;font-weight:400;color:#7faab2">(no members)</span></div>
    <div id="orphan-roles"><span class="sa-spinner">Loading…</span></div>
  </div>
  <div class="sa-panel sa-full">
    <div class="sa-panel-hdr">Operator Type Breakdown</div>
    <div id="oprtype"><span class="sa-spinner">Loading…</span></div>
  </div>
</div>

<script>
const OPRTYPE_LABELS = {
  '':'Unspecified','0':'PeopleSoft User','1':'SPS User',
  'N':'Network User','S':'Service Account','G':'Guest',
};
function fmtDate(s) {
  if (!s) return '—';
  const m = String(s).match(/(\\d{4})[-/](\\d{2})[-/](\\d{2})/);
  return m ? m[1]+'-'+m[2]+'-'+m[3] : String(s).substring(0,16);
}
function pick(row, ...keys) {
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== null) return row[k];
  }
  return '';
}
async function runSql(sql) {
  const env = window.dsGetEnv ? window.dsGetEnv() : (localStorage.getItem('ps_env') || 'HCM');
  const r = await fetch('/api/sqlws/execute', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sql, env, limit:200})
  });
  if (!r.ok) throw new Error(await r.text());
  const d = await r.json();
  return d.rows || [];
}

async function loadStats() {
  const [opsR, rolesR, plsR, recentR] = await Promise.all([
    runSql('SELECT COUNT(*) AS N FROM SYSADM.PSOPRDEFN'),
    runSql('SELECT COUNT(*) AS N FROM SYSADM.PSROLEDEFN'),
    runSql('SELECT COUNT(*) AS N FROM SYSADM.PSCLASSDEFN'),
    runSql('SELECT COUNT(*) AS N FROM SYSADM.PSOPRDEFN WHERE LASTSIGNONDTTM > SYSDATE - 30'),
  ]);
  document.getElementById('c-ops').textContent    = pick(opsR[0]||{},    'N','n') || '—';
  document.getElementById('c-roles').textContent  = pick(rolesR[0]||{},  'N','n') || '—';
  document.getElementById('c-pls').textContent    = pick(plsR[0]||{},    'N','n') || '—';
  document.getElementById('c-recent').textContent = pick(recentR[0]||{}, 'N','n') || '—';
}

async function loadTopRoles() {
  const rows = await runSql(
    'SELECT r.ROLENAME, r.DESCR, COUNT(u.OPRID) AS MEMBER_COUNT ' +
    'FROM SYSADM.PSROLEDEFN r ' +
    'LEFT JOIN SYSADM.PSROLEUSER u ON u.ROLENAME=r.ROLENAME ' +
    'GROUP BY r.ROLENAME, r.DESCR ORDER BY MEMBER_COUNT DESC FETCH FIRST 20 ROWS ONLY'
  );
  if (!rows.length) { document.getElementById('top-roles').innerHTML='<span class="sa-spinner">No data</span>'; return; }
  const max = Math.max(...rows.map(r=>+pick(r,'MEMBER_COUNT','member_count')||0));
  let h='<table class="sa-tbl"><thead><tr><th>Role</th><th>Members</th></tr></thead><tbody>';
  rows.forEach(r=>{
    const n=+pick(r,'MEMBER_COUNT','member_count')||0;
    const pct=max>0?Math.round(n/max*80):0;
    const name=pick(r,'ROLENAME','rolename');
    const desc=pick(r,'DESCR','descr');
    h+=`<tr><td><a class="sa-link" href="/admin/role/${encodeURIComponent(name)}">${name}</a>`+
      `<span style="color:#4a7a8a;font-size:11px;margin-left:6px">${desc}</span></td>`+
      `<td><div class="sa-bar-wrap"><div class="sa-bar" style="width:${pct}px"></div>`+
      `<span class="sa-badge">${n}</span></div></td></tr>`;
  });
  document.getElementById('top-roles').innerHTML=h+'</tbody></table>';
}

async function loadTopOps() {
  const rows = await runSql(
    'SELECT u.OPRID, o.OPRDEFNDESC, COUNT(*) AS ROLE_COUNT ' +
    'FROM SYSADM.PSROLEUSER u ' +
    'JOIN SYSADM.PSOPRDEFN o ON o.OPRID=u.OPRID ' +
    'GROUP BY u.OPRID, o.OPRDEFNDESC ORDER BY ROLE_COUNT DESC FETCH FIRST 20 ROWS ONLY'
  );
  if (!rows.length) { document.getElementById('top-ops').innerHTML='<span class="sa-spinner">No data</span>'; return; }
  const max = Math.max(...rows.map(r=>+pick(r,'ROLE_COUNT','role_count')||0));
  let h='<table class="sa-tbl"><thead><tr><th>Operator</th><th>Roles</th></tr></thead><tbody>';
  rows.forEach(r=>{
    const n=+pick(r,'ROLE_COUNT','role_count')||0;
    const pct=max>0?Math.round(n/max*80):0;
    const oprid=pick(r,'OPRID','oprid');
    const desc=pick(r,'OPRDEFNDESC','oprdefndesc');
    h+=`<tr><td><a class="sa-link" href="/admin/operator/${encodeURIComponent(oprid)}">${oprid}</a>`+
      `<span style="color:#4a7a8a;font-size:11px;margin-left:6px">${desc}</span></td>`+
      `<td><div class="sa-bar-wrap"><div class="sa-bar" style="width:${pct}px"></div>`+
      `<span class="sa-badge">${n}</span></div></td></tr>`;
  });
  document.getElementById('top-ops').innerHTML=h+'</tbody></table>';
}

async function loadRecentSignons() {
  const rows = await runSql(
    'SELECT OPRID, OPRDEFNDESC, LASTSIGNONDTTM FROM SYSADM.PSOPRDEFN ' +
    'WHERE LASTSIGNONDTTM > SYSDATE - 30 ORDER BY LASTSIGNONDTTM DESC FETCH FIRST 25 ROWS ONLY'
  );
  const el=document.getElementById('recent-signon');
  if (!rows.length) { el.innerHTML='<span class="sa-spinner">No sign-ons in last 30 days</span>'; return; }
  let h='<table class="sa-tbl"><thead><tr><th>Operator</th><th>Last Sign-on</th></tr></thead><tbody>';
  rows.forEach(r=>{
    const oprid=pick(r,'OPRID','oprid');
    const desc=pick(r,'OPRDEFNDESC','oprdefndesc');
    const dt=pick(r,'LASTSIGNONDTTM','lastsignondttm');
    h+=`<tr><td><a class="sa-link" href="/admin/operator/${encodeURIComponent(oprid)}">${oprid}</a>`+
      `<span style="color:#4a7a8a;font-size:11px;margin-left:6px">${desc}</span></td>`+
      `<td style="color:#7faab2;white-space:nowrap">${fmtDate(dt)}</td></tr>`;
  });
  el.innerHTML=h+'</tbody></table>';
}

async function loadOrphanRoles() {
  const rows = await runSql(
    'SELECT r.ROLENAME, r.DESCR, r.LASTUPDDTTM FROM SYSADM.PSROLEDEFN r ' +
    'WHERE NOT EXISTS (SELECT 1 FROM SYSADM.PSROLEUSER u WHERE u.ROLENAME=r.ROLENAME) ' +
    'ORDER BY r.ROLENAME FETCH FIRST 50 ROWS ONLY'
  );
  const el=document.getElementById('orphan-roles');
  if (!rows.length) {
    el.innerHTML='<span style="color:#4a9a4a;font-size:13px">&#x2713; No orphaned roles found</span>';
    return;
  }
  let h=`<div style="margin-bottom:8px"><span class="sa-orphan-count">${rows.length}</span>`+
    `<span style="font-size:12px;color:#7faab2;margin-left:6px">roles with no members</span></div>`;
  h+='<table class="sa-tbl"><thead><tr><th>Role</th><th>Last Updated</th></tr></thead><tbody>';
  rows.forEach(r=>{
    const name=pick(r,'ROLENAME','rolename');
    const desc=pick(r,'DESCR','descr');
    const dt=pick(r,'LASTUPDDTTM','lastupddttm');
    h+=`<tr><td><a class="sa-link" href="/admin/role/${encodeURIComponent(name)}">${name}</a>`+
      `<span style="color:#4a7a8a;font-size:11px;margin-left:6px">${desc}</span></td>`+
      `<td style="color:#7faab2;font-size:11px">${fmtDate(dt)}</td></tr>`;
  });
  el.innerHTML=h+'</tbody></table>';
}

async function loadOprTypes() {
  const rows = await runSql(
    'SELECT OPRTYPE, COUNT(*) AS N FROM SYSADM.PSOPRDEFN GROUP BY OPRTYPE ORDER BY N DESC'
  );
  if (!rows.length) { document.getElementById('oprtype').innerHTML='<span class="sa-spinner">No data</span>'; return; }
  const total=rows.reduce((s,r)=>s+(+pick(r,'N','n')||0),0);
  const max=Math.max(...rows.map(r=>+pick(r,'N','n')||0));
  let h='<table class="sa-tbl"><thead><tr><th>Type</th><th>Label</th><th>Count</th><th>Share</th></tr></thead><tbody>';
  rows.forEach(r=>{
    const t=String(pick(r,'OPRTYPE','oprtype'));
    const n=+pick(r,'N','n')||0;
    const lbl=OPRTYPE_LABELS[t]||('Type '+t);
    const pct=total>0?Math.round(n/total*100):0;
    const bw=max>0?Math.round(n/max*120):0;
    h+=`<tr><td><span class="sa-oprtype">${t||'(blank)'}</span></td><td>${lbl}</td>`+
      `<td><span class="sa-badge">${n}</span></td>`+
      `<td><div class="sa-bar-wrap"><div class="sa-bar" style="width:${bw}px"></div>`+
      `<span style="font-size:11px;color:#7faab2">${pct}%</span></div></td></tr>`;
  });
  document.getElementById('oprtype').innerHTML=h+'</tbody></table>';
}

async function loadAll() {
  const st=document.getElementById('status');
  st.textContent='Loading…';
  try {
    await Promise.all([
      loadStats(),loadTopRoles(),loadTopOps(),
      loadRecentSignons(),loadOrphanRoles(),loadOprTypes(),
    ]);
    st.textContent='';
  } catch(e) {
    st.textContent='Error: '+e.message;
  }
}

window.onEnvChange = loadAll;
document.addEventListener('deathstar:envchange', loadAll);
loadAll();
</script>""")


@router.get("/access", response_class=HTMLResponse)
def admin_access():
    return _shell("Access Path", "access", content="""
<style>
.ap-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  padding:12px 16px;background:rgba(0,20,40,.6);border-bottom:1px solid #1a2a3a;margin-bottom:0}
.ap-mode-btn{padding:5px 14px;border-radius:4px;font-size:12px;cursor:pointer;border:1px solid;
  background:transparent;transition:.15s}
.ap-mode-btn.active{background:rgba(0,229,255,.15);border-color:#00e5ff;color:#00e5ff}
.ap-mode-btn:not(.active){border-color:#2a3a4a;color:#7faab2}
.ap-inp{background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:6px 10px;
  border-radius:4px;font-size:13px;width:260px}
.ap-inp:focus{outline:none;border-color:#00e5ff80}
.ap-btn{padding:6px 16px;border-radius:4px;border:1px solid #00e5ff60;background:rgba(0,229,255,.1);
  color:#00e5ff;font-size:12px;cursor:pointer}
.ap-btn:hover{background:rgba(0,229,255,.2)}
.ap-stats{display:flex;gap:12px;flex-wrap:wrap;padding:10px 16px;
  border-bottom:1px solid #1a2a3a;background:rgba(0,10,20,.4)}
.ap-stat{background:rgba(0,229,255,.06);border:1px solid rgba(0,229,255,.18);
  border-radius:4px;padding:6px 14px;font-size:12px;color:#7faab2}
.ap-stat b{font-size:18px;color:#00e5ff;display:block}
.ap-body{padding:16px;overflow:auto;height:calc(100vh - 195px)}
.ap-filter{background:#0a1520;border:1px solid #1a2a3a;color:#c8d8e8;padding:4px 8px;
  border-radius:3px;font-size:12px;width:200px;margin-bottom:10px}
.ap-tbl{width:100%;border-collapse:collapse;font-size:12px}
.ap-tbl th{background:#0a1828;color:#7faab2;padding:6px 10px;text-align:left;
  border-bottom:1px solid #1a2a3a;position:sticky;top:0}
.ap-tbl td{padding:5px 10px;border-bottom:1px solid #0d1a28;vertical-align:top}
.ap-tbl tr:hover td{background:rgba(0,229,255,.04)}
.ap-link{color:#00e5ff;text-decoration:none;font-size:11px}
.ap-link:hover{text-decoration:underline}
.ap-pill{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;margin:1px}
.ap-pill.d{background:rgba(0,150,255,.15);border:1px solid #0096ff40;color:#5bc8ff}
.ap-pill.u{background:rgba(0,255,150,.12);border:1px solid #00ff9640;color:#5fffa8}
.ap-pill.a{background:rgba(255,200,0,.12);border:1px solid #ffc80040;color:#ffd84d}
.ap-none{color:#4a5a6a;font-size:12px;padding:20px;text-align:center}
.ap-path{color:#4a6a8a;font-size:11px}
.ap-path span{color:#7faab2}
.ap-section{margin-bottom:6px;color:#00e5ff;font-size:11px;font-weight:600;
  letter-spacing:.5px;padding:4px 0;border-bottom:1px solid #1a2a3a;text-transform:uppercase}
.ap-warn{background:rgba(255,180,0,.1);border:1px solid #ffc00040;border-radius:4px;
  color:#ffc44d;font-size:11px;padding:8px 12px;margin-bottom:10px}
</style>

<div class="ap-toolbar">
  <button class="ap-mode-btn active" id="modeComp" onclick="setMode('comp')">Component → Who Has Access</button>
  <button class="ap-mode-btn" id="modeOpr" onclick="setMode('opr')">Operator → What Can They Access</button>
  <span id="modeInputs" style="display:flex;align-items:center;gap:8px">
    <input class="ap-inp" id="compInput" placeholder="Component name e.g. JOB_DATA" onkeydown="if(event.key==='Enter')run()">
  </span>
  <button class="ap-btn" onclick="run()">Search</button>
  <span id="apStatus" style="font-size:11px;color:#7faab2"></span>
</div>

<div id="apStats" class="ap-stats" style="display:none"></div>

<div class="ap-body" id="apBody">
  <div class="ap-none">Enter a component name or OPRID above and click Search</div>
</div>

<script>
let _mode = 'comp';
let _env = () => (document.getElementById('globalEnv') || {}).value || 'HCM';
let _raw = [];

function setMode(m) {
  _mode = m;
  document.getElementById('modeComp').className = 'ap-mode-btn' + (m==='comp'?' active':'');
  document.getElementById('modeOpr').className = 'ap-mode-btn' + (m==='opr'?' active':'');
  const inp = document.getElementById('compInput');
  inp.placeholder = m === 'comp' ? 'Component name e.g. JOB_DATA' : 'OPRID e.g. PS';
  inp.value = '';
  document.getElementById('apStats').style.display = 'none';
  document.getElementById('apBody').innerHTML = '<div class="ap-none">Enter a ' + (m==='comp'?'component name':'operator OPRID') + ' above and click Search</div>';
}

async function run() {
  const val = document.getElementById('compInput').value.trim().toUpperCase();
  if (!val) return;
  const st = document.getElementById('apStatus');
  st.textContent = 'Loading…';
  const env = _env();
  try {
    if (_mode === 'comp') {
      const r = await fetch('/api/peoplesoft/security/components/' + encodeURIComponent(val) + '/access?env=' + env);
      const d = await r.json();
      renderComp(d, val);
    } else {
      const r = await fetch('/api/peoplesoft/security/operators/' + encodeURIComponent(val) + '/components?env=' + env);
      const d = await r.json();
      renderOpr(d, val, env);
    }
    st.textContent = '';
  } catch(e) {
    st.textContent = 'Error: ' + e.message;
  }
}

function pick(row, ...keys) {
  for (const k of keys) {
    const v = row[k] ?? row[k.toLowerCase()] ?? row[k.toUpperCase()];
    if (v != null) return v;
  }
  return '';
}

function accessPill(row) {
  const cd = (pick(row,'ACCESSCD','accesscd')||'').toUpperCase();
  const disp = (pick(row,'DISPLAYONLY','displayonly')||'0').toString();
  const auth = pick(row,'AUTHORIZEDACTIONS','authorizedactions');
  let type = 'u'; let label = 'Update';
  if (cd === 'D' || disp === '1') { type='d'; label='Display'; }
  else if (cd === 'A') { type='a'; label='Add'; }
  else if (auth) {
    const bits = parseInt(auth,10)||0;
    if ((bits & 1) && (bits & 2)) { type='u'; label='Full'; }
    else if (bits & 1) { type='d'; label='Display'; }
    else if (bits & 2) { type='u'; label='Update'; }
    else if (bits & 4) { type='a'; label='Add'; }
  }
  return '<span class="ap-pill ' + type + '">' + label + '</span>';
}

function renderComp(d, comp) {
  const st = document.getElementById('apStats');
  const cnt = d.counts || {};
  st.style.display = 'flex';
  st.innerHTML = '<div class="ap-stat"><b>' + (cnt.users||0) + '</b>Operators</div>' +
    '<div class="ap-stat"><b>' + (cnt.roles||0) + '</b>Roles</div>' +
    '<div class="ap-stat"><b>' + (cnt.permissionlists||0) + '</b>Permission Lists</div>' +
    '<div class="ap-stat"><b>' + (cnt.access_paths||0) + '</b>Access Paths</div>';

  const body = document.getElementById('apBody');
  if (!d.access || !d.access.length) {
    body.innerHTML = '<div class="ap-none">No access grants found for component ' + esc(comp) + '</div>';
    return;
  }

  const warn = (d.warnings||[]).length ? '<div class="ap-warn">⚠ ' + d.warnings.join('; ') + '</div>' : '';

  // Group by operator
  const byOpr = {};
  for (const row of d.access) {
    const op = (pick(row,'ROLEUSER','roleuser')||'').toUpperCase();
    if (!op) continue;
    if (!byOpr[op]) byOpr[op] = [];
    byOpr[op].push(row);
  }
  const oprids = Object.keys(byOpr).sort();

  // Filter input
  const filterHtml = '<input class="ap-filter" id="aprFilter" placeholder="Filter operators…" oninput="filterComp(this.value)">';

  let html = warn + filterHtml + '<div id="aprList">';
  for (const op of oprids) {
    const rows = byOpr[op];
    const paths = rows.map(r => {
      const pl = esc(pick(r,'CLASSID','classid')||'');
      const role = esc(pick(r,'ROLENAME','rolename')||'');
      return '<span class="ap-path">' + esc(op) + ' → <span>' + role + '</span> → <span>' + pl + '</span> → <span>' + esc(comp) + '</span></span> ' + accessPill(r);
    }).join('<br>');
    html += '<div class="ap-opr-row" data-opr="' + esc(op) + '" style="padding:8px 0;border-bottom:1px solid #0d1a28">' +
      '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
      '<a class="ap-link" href="/admin/object/operator/' + esc(op) + '">' + esc(op) + '</a>' +
      '</div>' + paths + '</div>';
  }
  html += '</div>';
  body.innerHTML = html;
  _raw = d.access;
}

function filterComp(val) {
  val = (val||'').toUpperCase();
  document.querySelectorAll('.ap-opr-row').forEach(el => {
    el.style.display = !val || el.dataset.opr.includes(val) ? '' : 'none';
  });
}

function renderOpr(rows, oprid, env) {
  const st = document.getElementById('apStats');

  if (!rows || !rows.length) {
    st.style.display = 'none';
    document.getElementById('apBody').innerHTML = '<div class="ap-none">No component access found for operator ' + esc(oprid) + '</div>';
    return;
  }

  // Distinct counts
  const comps = new Set(rows.map(r => (pick(r,'PNLGRPNAME','pnlgrpname')||'').toUpperCase()).filter(Boolean));
  const roles = new Set(rows.map(r => pick(r,'ROLENAME','rolename')).filter(Boolean));
  const pls = new Set(rows.map(r => pick(r,'CLASSID','classid')).filter(Boolean));

  st.style.display = 'flex';
  st.innerHTML = '<div class="ap-stat"><b>' + comps.size + '</b>Components</div>' +
    '<div class="ap-stat"><b>' + roles.size + '</b>Roles</div>' +
    '<div class="ap-stat"><b>' + pls.size + '</b>Permission Lists</div>' +
    '<div class="ap-stat"><b>' + rows.length + '</b>Access Paths</div>';

  // Deduplicate to component level — pick first row per component, track unique paths
  const byComp = {};
  for (const row of rows) {
    const c = (pick(row,'PNLGRPNAME','pnlgrpname')||'').toUpperCase();
    if (!c) continue;
    if (!byComp[c]) byComp[c] = [];
    byComp[c].push(row);
  }
  const compList = Object.keys(byComp).sort();

  const filterHtml = '<input class="ap-filter" id="aprFilterC" placeholder="Filter components…" oninput="filterOpr(this.value)">';

  const warn = '';
  let html = warn + filterHtml;
  html += '<table class="ap-tbl"><thead><tr>' +
    '<th>Component</th><th>Description</th><th>Access</th><th>Via Role / PL</th></tr></thead><tbody id="aprTbody">';

  for (const c of compList) {
    const pathRows = byComp[c];
    // Collect unique role+pl combos
    const via = [...new Set(pathRows.map(r => {
      const role = pick(r,'ROLENAME','rolename')||'';
      const pl = pick(r,'CLASSID','classid')||'';
      return esc(role) + ' / ' + esc(pl);
    }))].join('<br>');
    const descr = esc(pick(pathRows[0],'COMPONENT_DESCR','component_descr')||'');
    const pill = accessPill(pathRows[0]);
    html += '<tr class="ap-comp-row" data-comp="' + esc(c) + '">' +
      '<td><a class="ap-link" href="/admin/object/component/' + esc(c) + '">' + esc(c) + '</a></td>' +
      '<td style="color:#7faab2">' + descr + '</td>' +
      '<td>' + pill + '</td>' +
      '<td style="font-size:11px;color:#4a6a8a">' + via + '</td></tr>';
  }
  html += '</tbody></table>';
  document.getElementById('apBody').innerHTML = html;
}

function filterOpr(val) {
  val = (val||'').toUpperCase();
  document.querySelectorAll('.ap-comp-row').forEach(el => {
    el.style.display = !val || el.dataset.comp.includes(val) ? '' : 'none';
  });
}

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(location.search);
  const comp = params.get('comp');
  const opr = params.get('opr');
  if (comp) {
    setMode('comp');
    document.getElementById('compInput').value = comp;
    run();
  } else if (opr) {
    setMode('opr');
    document.getElementById('compInput').value = opr;
    run();
  }
});

if (typeof window !== 'undefined') {
  window.onEnvChange = function(env) {
    const val = document.getElementById('compInput').value.trim();
    if (val) run();
  };
}
</script>""")
