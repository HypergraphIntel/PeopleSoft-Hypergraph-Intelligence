/* DeathStar shared frontend — env selector persistence + sync */

(function () {
    'use strict';

    const LS_KEY = 'ps_env';

    function getStoredEnv() {
        try { return localStorage.getItem(LS_KEY) || ''; } catch (_) { return ''; }
    }
    function setStoredEnv(val) {
        try { localStorage.setItem(LS_KEY, val); } catch (_) {}
    }

    function emitEnvChange(val) {
        try {
            window.dispatchEvent(new CustomEvent('deathstar:envchange', {
                detail: { env: val }
            }));
        } catch (_) {}
    }

    /* Sync per-page legacy #envSel (if present) to the chosen value and
       fire its change event so the page JS reacts. */
    function syncPageEnvSel(val) {
        const ps = document.getElementById('envSel');
        if (ps && ps.value !== val) {
            ps.value = val;
            ps.dispatchEvent(new Event('change'));
        }
    }

    /* Populate all .ds-env-sel selects from /api/sqlws/config, then restore
       the saved selection and sync any legacy #envSel on the page. */
    function initGlobalEnv() {
        const selects = document.querySelectorAll('.ds-env-sel');
        const saved = getStoredEnv();

        /* Always seed legacy #envSel if already rendered with options */
        const ps = document.getElementById('envSel');
        if (ps && saved) {
            if (ps.querySelector('option[value="' + saved + '"]')) ps.value = saved;
        }

        if (!selects.length) return;

        fetch('/api/sqlws/config')
            .then(r => r.json())
            .then(data => {
                /* config returns either envs[] (flat) or environments[] (objects) */
                const raw = data.envs || data.environments || [];
                const envs = raw.map(e => (typeof e === 'string' ? e : (e.name || e)));
                selects.forEach(sel => {
                    const cur = sel.value || saved;
                    sel.innerHTML = '';
                    envs.forEach(e => {
                        const o = document.createElement('option');
                        o.value = o.textContent = e;
                        if (e === cur) o.selected = true;
                        sel.appendChild(o);
                    });
                    if (!sel.value && saved) sel.value = saved;

                    sel.addEventListener('change', () => {
                        const v = sel.value;
                        setStoredEnv(v);
                        /* sync sibling .ds-env-sel selects */
                        document.querySelectorAll('.ds-env-sel').forEach(s => {
                            if (s !== sel) s.value = v;
                        });
                        /* sync legacy page #envSel */
                        syncPageEnvSel(v);
                        /* call page hook if defined */
                        if (typeof window.onEnvChange === 'function') window.onEnvChange(v);
                        emitEnvChange(v);
                    });
                });

                /* After populating, seed legacy #envSel */
                const chosen = selects[0] && selects[0].value;
                if (chosen) {
                    syncPageEnvSel(chosen);
                    emitEnvChange(chosen);
                }
            })
            .catch(() => {
                /* config fetch failed — restore saved value if options exist */
                selects.forEach(sel => {
                    if (saved && sel.querySelector('option[value="' + saved + '"]')) {
                        sel.value = saved;
                    }
                });
                if (saved) {
                    syncPageEnvSel(saved);
                    emitEnvChange(saved);
                }
            });
    }

    document.addEventListener('DOMContentLoaded', initGlobalEnv);

    /* Expose helpers for pages */
    window.dsGetEnv = function () {
        const sel = document.querySelector('.ds-env-sel');
        return sel ? sel.value : getStoredEnv();
    };
    window.dsSetEnv = setStoredEnv;
    window.dsGetStoredEnv = getStoredEnv;
})();
