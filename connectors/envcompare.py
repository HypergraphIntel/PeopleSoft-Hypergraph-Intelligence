"""
Environment comparison connector.
Queries the same PeopleSoft metadata in two named environments and diffs the results.
All comparisons are grant-aware; errors per-environment are captured as warnings.
"""

import difflib

from connectors import psdb

# ── PeopleSoft decode tables ───────────────────────────────────────────────────

RECTYPE_LABELS = {
    0: "SQL Table",
    1: "SQL View",
    2: "Derived/Work",
    3: "SubRecord",
    5: "Dynamic View",
    6: "Query View",
    7: "Temporary Table",
}

FIELDTYPE_LABELS = {
    0: "Char",
    1: "Long Char",
    2: "Number",
    3: "Signed Number",
    4: "Date",
    5: "Time",
    6: "DateTime",
    8: "Image",
    9: "ImageRef",
}


def _label(mapping, val, default="?"):
    if val is None:
        return default
    try:
        return mapping.get(int(val), str(val))
    except (TypeError, ValueError):
        return str(val)


# ── Core diff engine ───────────────────────────────────────────────────────────

def _compare(env1_rows, env2_rows, key_col, compare_cols):
    """
    Diff two query result-sets.  Returns:
      only_in_env1  — rows present only in env1
      only_in_env2  — rows present only in env2
      changed       — rows in both with at least one differing compare_col
      identical_count — count of rows that match on all compare_cols
    """
    e1 = {str(r.get(key_col, "") or "").strip(): r for r in env1_rows}
    e2 = {str(r.get(key_col, "") or "").strip(): r for r in env2_rows}
    all_keys = sorted(set(e1) | set(e2))

    only1, only2, changed = [], [], []
    identical = 0

    for k in all_keys:
        if k not in e2:
            only1.append(e1[k])
        elif k not in e1:
            only2.append(e2[k])
        else:
            diffs = []
            for col in compare_cols:
                v1 = str(e1[k].get(col) or "").strip()
                v2 = str(e2[k].get(col) or "").strip()
                if v1 != v2:
                    diffs.append({"col": col, "env1": v1, "env2": v2})
            if diffs:
                changed.append({"name": k, "env1": e1[k], "env2": e2[k], "diffs": diffs})
            else:
                identical += 1

    return {
        "only_in_env1": only1,
        "only_in_env2": only2,
        "changed": changed,
        "identical_count": identical,
    }


def _run(env, sql, params):
    """Run a query, return (rows, warning_or_None)."""
    try:
        return psdb.query(env, sql, params), None
    except Exception as exc:
        return [], {"code": f"{env.upper()}_ERROR", "message": f"{env}: {exc}", "severity": "error"}


# ── Public comparison functions ────────────────────────────────────────────────

def compare_records(env1, env2, q="", limit=500):
    """Diff PSRECDEFN (record catalog) between two environments."""
    sql = """
        SELECT r.RECNAME,
               r.RECTYPE,
               r.RECDESCR,
               COUNT(f.FIELDNUM) AS field_count
        FROM SYSADM.PSRECDEFN r
        LEFT JOIN SYSADM.PSRECFIELD f ON r.RECNAME = f.RECNAME
        WHERE (:q IS NULL OR UPPER(r.RECNAME) LIKE :q OR UPPER(r.RECDESCR) LIKE :q)
        GROUP BY r.RECNAME, r.RECTYPE, r.RECDESCR
        ORDER BY r.RECNAME
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    # Decode rectype for display.
    for r in rows1 + rows2:
        r["rectype_label"] = _label(RECTYPE_LABELS, r.get("rectype"))

    diff = _compare(rows1, rows2, "recname", ["rectype", "field_count"])
    diff.update({"env1": env1, "env2": env2, "object_type": "record",
                 "query": q, "warnings": warnings})
    return diff


def compare_field_definitions(env1, env2, q="", limit=500):
    """
    Diff PSDBFIELD — the standalone PeopleTools Field object type —
    between two environments. A Field is its own metadata definition
    independent of which records use it; this is NOT the same thing as
    compare_fields() below, which diffs PSRECFIELD (a record's *usage* of
    fields, i.e. Record.Fields) — a legitimately different, record-scoped
    object type that was previously mislabeled as "Fields" in the UI.

    PSDBFIELD does not carry a DESCR column in every PeopleTools version
    (confirmed live: ORA-00904 when assumed present) — check per env like
    compare_components()/compare_permissions() do for their own
    version-dependent columns, rather than assuming.

    Matches FIELDNAME *exactly* (case-insensitive), not by substring —
    unlike Records/Components/etc., a field name is a precise identifier,
    not free text; substring matching on "EMPLID" pulled in 186 unrelated
    fields (EMPLID_SRCH, NEW_EMPLID, ...) instead of the single field the
    user was actually looking up. DESCR is still substring-matched, for
    discovering fields by description text when the exact name isn't known.
    """
    q_name = q.strip().upper() if q else None
    q_descr_pattern = f"%{q_name}%" if q_name else None
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSDBFIELD")
        has_descr = "descr" in cols
        descr_sel = "DESCR" if has_descr else "NULL AS DESCR"
        # oracledb requires the params dict to exactly match the bind
        # placeholders present in THIS SQL string — a stray unused key
        # (e.g. :qpat when the has_descr=False branch never references
        # it) raises DPY-4008, so params are built per-branch, not shared.
        if has_descr:
            q_clause = "(:qname IS NULL OR UPPER(FIELDNAME) = :qname OR UPPER(DESCR) LIKE :qpat)"
            params = {"qname": q_name, "qpat": q_descr_pattern}
        else:
            q_clause = "(:qname IS NULL OR UPPER(FIELDNAME) = :qname)"
            params = {"qname": q_name}
        sql = f"""
            SELECT FIELDNAME,
                   FIELDTYPE,
                   LENGTH AS FIELDLEN,
                   DECIMALPOS,
                   {descr_sel}
            FROM SYSADM.PSDBFIELD
            WHERE {q_clause}
            ORDER BY FIELDNAME
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows

    for r in rows1 + rows2:
        r["fieldtype_label"] = _label(FIELDTYPE_LABELS, r.get("fieldtype"))

    diff = _compare(rows1, rows2, "fieldname", ["fieldtype", "fieldlen", "decimalpos", "descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "field_definition",
                 "query": q, "warnings": warnings})
    return diff


def compare_fields(env1, env2, record_name):
    """Diff PSRECFIELD (a record's field usage/structure — "Record.Fields",
    NOT the standalone Field object type; see compare_field_definitions()
    above for that) for a specific record across two environments.

    FIELDTYPE/LENGTH/DECIMALPOS live in PSDBFIELD, not PSRECFIELD — join when accessible.
    """
    params = {"recname": record_name.upper()}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        if psdb.table_columns(env, "PSDBFIELD"):
            sql = """
                SELECT rf.FIELDNAME,
                       rf.FIELDNUM,
                       rf.USEEDIT,
                       rf.DEFRECNAME,
                       rf.DEFFIELDNAME,
                       fd.FIELDTYPE,
                       fd.LENGTH      AS FIELDLEN,
                       fd.DECIMALPOS
                FROM SYSADM.PSRECFIELD rf
                LEFT JOIN SYSADM.PSDBFIELD fd ON fd.FIELDNAME = rf.FIELDNAME
                WHERE rf.RECNAME = :recname
                ORDER BY rf.FIELDNUM
            """
        else:
            sql = """
                SELECT FIELDNAME,
                       FIELDNUM,
                       USEEDIT,
                       DEFRECNAME,
                       DEFFIELDNAME,
                       NULL AS FIELDTYPE,
                       NULL AS FIELDLEN,
                       NULL AS DECIMALPOS
                FROM SYSADM.PSRECFIELD
                WHERE RECNAME = :recname
                ORDER BY FIELDNUM
            """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    for r in rows1 + rows2:
        r["fieldtype_label"] = _label(FIELDTYPE_LABELS, r.get("fieldtype"))

    compare_cols = ["fieldtype", "fieldlen", "decimalpos", "useedit", "defrecname", "deffieldname"]
    diff = _compare(rows1, rows2, "fieldname", compare_cols)
    diff.update({"env1": env1, "env2": env2, "object_type": "field",
                 "record_name": record_name.upper(), "warnings": warnings})
    return diff


def compare_components(env1, env2, q="", limit=500):
    """Diff PSPNLGRPDEFN (component catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSPNLGRPDEFN")
        addsrch = "ADDSRCHRECNAME" if "addsrchrecname" in cols else "NULL AS ADDSRCHRECNAME"
        actions = "ACTIONS" if "actions" in cols else "NULL AS ACTIONS"
        sql = f"""
            SELECT PNLGRPNAME,
                   SEARCHRECNAME,
                   {addsrch},
                   DESCR,
                   {actions}
            FROM SYSADM.PSPNLGRPDEFN
            WHERE MARKET = 'GBL'
              AND (:q IS NULL OR UPPER(PNLGRPNAME) LIKE :q OR UPPER(DESCR) LIKE :q)
            ORDER BY PNLGRPNAME
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "pnlgrpname", ["searchrecname", "addsrchrecname", "actions"])
    diff.update({"env1": env1, "env2": env2, "object_type": "component",
                 "query": q, "warnings": warnings})
    return diff


def compare_permissions(env1, env2, q="", limit=500):
    """Diff PSCLASSDEFN (permission list catalog) between two environments.

    PSCLASSDEFN uses DESCR in older PeopleTools and CLASSDEFNDESC in newer — check per env.
    """
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSCLASSDEFN")
        descr_col = next(
            (c for c in ("DESCR", "CLASSDEFNDESC") if c.lower() in cols),
            None,
        )
        if descr_col:
            descr_sel = descr_col
            descr_filter = f"OR UPPER({descr_col}) LIKE :q"
        else:
            descr_sel = "NULL AS DESCR"
            descr_filter = ""
        sql = f"""
            SELECT CLASSID, {descr_sel} AS DESCR
            FROM SYSADM.PSCLASSDEFN
            WHERE (:q IS NULL OR UPPER(CLASSID) LIKE :q {descr_filter})
            ORDER BY CLASSID
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "classid", ["descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "permission",
                 "query": q, "warnings": warnings})
    return diff


def compare_ae(env1, env2, q="", limit=500):
    """Diff PSAEAPPLDEFN (Application Engine program catalog) between two environments.

    AE_STATUS does not exist in PSAEAPPLDEFN; use DESCR + LASTUPDDTTM, guard per env.
    """
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSAEAPPLDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT AE_APPLID, {descr_col}, {ts_col}
            FROM SYSADM.PSAEAPPLDEFN
            WHERE (:q IS NULL OR UPPER(AE_APPLID) LIKE :q {descr_filter})
            ORDER BY AE_APPLID
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "ae_applid", ["descr", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ae",
                 "query": q, "warnings": warnings})
    return diff


def compare_roles(env1, env2, q="", limit=500):
    """Diff PSROLEDEFN (role catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSROLEDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        sql = f"""
            SELECT ROLENAME, {descr_col}
            FROM SYSADM.PSROLEDEFN
            WHERE (:q IS NULL OR UPPER(ROLENAME) LIKE :q {descr_filter})
            ORDER BY ROLENAME
            FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "rolename", ["descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "role",
                 "query": q, "warnings": warnings})
    return diff


def compare_peoplecode(env1, env2, q="", limit=500):
    """Diff PSPCMPROG (PeopleCode program catalog) between two environments.

    Groups by the logical program identity (OBJECTID1 + OBJECTVALUE1..5) so that
    multi-row programs (multiple PROGSEQ rows per event) appear as a single entry.
    Comparing LASTUPDDTTM (MAX per program) reveals which programs changed.
    Filter by q to scope the comparison to a specific parent object (e.g. record name).
    """
    sql = """
        SELECT OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
               OBJECTVALUE4, OBJECTVALUE5,
               MAX(LASTUPDDTTM) AS LASTUPDDTTM
          FROM SYSADM.PSPCMPROG
         WHERE (:q IS NULL OR UPPER(OBJECTVALUE1) LIKE :q OR UPPER(OBJECTVALUE2) LIKE :q)
         GROUP BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3,
                  OBJECTVALUE4, OBJECTVALUE5
         ORDER BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3
         FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    def _pc_key(row):
        return "|".join([
            str(row.get("objectid1") or ""),
            str(row.get("objectvalue1") or "").strip(),
            str(row.get("objectvalue2") or "").strip(),
            str(row.get("objectvalue3") or "").strip(),
            str(row.get("objectvalue4") or "").strip(),
            str(row.get("objectvalue5") or "").strip(),
        ])

    for r in rows1:
        r["_key"] = _pc_key(r)
    for r in rows2:
        r["_key"] = _pc_key(r)

    diff = _compare(rows1, rows2, "_key", ["lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "peoplecode",
                 "query": q, "warnings": warnings})
    return diff


def compare_sql_definitions(env1, env2, q="", limit=500):
    """Diff PSSQLDEFN (SQL object catalog) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSSQLDEFN")
        owner_col = "OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        owner_filter = "OR UPPER(OBJECTOWNERID) LIKE :q" if "objectownerid" in cols else ""
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT SQLID, SQLTYPE, {owner_col}, {ts_col}
              FROM SYSADM.PSSQLDEFN
             WHERE (:q IS NULL OR UPPER(SQLID) LIKE :q {owner_filter})
             ORDER BY SQLTYPE, SQLID
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "sqlid", ["sqltype", "objectownerid", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "sql_definitions",
                 "query": q, "warnings": warnings})
    return diff


def compare_portals(env1, env2, q="", limit=500):
    """Diff PSPRSMDEFN (Portal Registry content references) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSPRSMDEFN")
        label_col = "PORTAL_LABEL" if "portal_label" in cols else "NULL AS PORTAL_LABEL"
        label_filter = "OR UPPER(PORTAL_LABEL) LIKE :q" if "portal_label" in cols else ""
        prnt_col = "PORTAL_PRNTOBJNAME" if "portal_prntobjname" in cols else "NULL AS PORTAL_PRNTOBJNAME"
        type_col = "PORTAL_OBJTYPE" if "portal_objtype" in cols else "NULL AS PORTAL_OBJTYPE"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT PORTAL_OBJNAME, PORTAL_NAME, {label_col},
                   {prnt_col}, {type_col}, {ts_col}
              FROM SYSADM.PSPRSMDEFN
             WHERE (:q IS NULL OR UPPER(PORTAL_OBJNAME) LIKE :q {label_filter})
             ORDER BY PORTAL_OBJNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "portal_objname",
                    ["portal_label", "portal_prntobjname", "portal_objtype", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "portals",
                 "query": q, "warnings": warnings})
    return diff


def compare_queries(env1, env2, q="", limit=500):
    """Diff PSQRYDEFN (public PS Queries, OPRID=' ') between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSQRYDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        folder_col = "QRYFOLDER" if "qryfolder" in cols else "NULL AS QRYFOLDER"
        disabled_col = "QRYDISABLED" if "qrydisabled" in cols else "NULL AS QRYDISABLED"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT QRYNAME, {descr_col}, QRYTYPE, {folder_col}, {disabled_col}, {ts_col}
              FROM SYSADM.PSQRYDEFN
             WHERE OPRID = ' '
               AND (:q IS NULL OR UPPER(QRYNAME) LIKE :q {descr_filter})
             ORDER BY QRYNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "qryname",
                    ["descr", "qrytype", "qryfolder", "qrydisabled", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "queries",
                 "query": q, "warnings": warnings})
    return diff


def compare_menus(env1, env2, q="", limit=500):
    """Diff PSMENUDEFN (Menu definitions) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSMENUDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        owner_col = "OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        menutype_col = "MENUTYPE" if "menutype" in cols else "NULL AS MENUTYPE"
        sql = f"""
            SELECT MENUNAME, {menutype_col}, {descr_col}, {owner_col}, {ts_col}
              FROM SYSADM.PSMENUDEFN
             WHERE (:q IS NULL OR UPPER(MENUNAME) LIKE :q {descr_filter})
             ORDER BY MENUNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "menuname",
                    ["menutype", "descr", "objectownerid", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "menus",
                 "query": q, "warnings": warnings})
    return diff


def compare_trees(env1, env2, q="", limit=500):
    """Diff PSTREEDEFN (Tree definitions, latest effective row per tree) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSTREEDEFN")
        eff_col = "t.EFF_STATUS" if "eff_status" in cols else "NULL AS EFF_STATUS"
        descr_col = "t.DESCR" if "descr" in cols else "NULL AS DESCR"
        ts_col = "t.LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        setid_col = "t.SETID" if "setid" in cols else "NULL AS SETID"
        sql = f"""
            SELECT t.TREE_NAME, {setid_col}, t.EFFDT,
                   {eff_col}, {descr_col}, {ts_col}
              FROM SYSADM.PSTREEDEFN t
              INNER JOIN (
                SELECT TREE_NAME, SETID, MAX(EFFDT) AS EFFDT
                  FROM SYSADM.PSTREEDEFN
                 GROUP BY TREE_NAME, SETID
              ) latest ON t.TREE_NAME = latest.TREE_NAME
                      AND t.SETID     = latest.SETID
                      AND t.EFFDT     = latest.EFFDT
             WHERE (:q IS NULL OR UPPER(t.TREE_NAME) LIKE :q)
             ORDER BY t.TREE_NAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "tree_name",
                    ["eff_status", "descr", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "trees",
                 "query": q, "warnings": warnings})
    return diff


def compare_process_definitions(env1, env2, q="", limit=500):
    """Diff PS_PRCSDEFN (Process Scheduler definitions) between two environments.

    Compares across all process types: Application Engine, SQR Report,
    SQR Process, XML Publisher, COBOL SQL, Data Mover, etc.
    """
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PS_PRCSDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT PRCSTYPE, PRCSNAME, {descr_col}, {ts_col}
              FROM SYSADM.PS_PRCSDEFN
             WHERE (:q IS NULL
                    OR UPPER(PRCSNAME) LIKE :q
                    OR UPPER(PRCSTYPE) LIKE :q)
             ORDER BY PRCSTYPE, PRCSNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        # Composite key: type~name  (same convention as KG)
        for r in rows:
            r["_key"] = f"{r.get('prcstype', '')}~{r.get('prcsname', '')}".upper()
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "_key", ["descr", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "process_definitions",
                 "query": q, "warnings": warnings})
    return diff


def compare_ib_routings(env1, env2, q="", limit=500):
    """Diff PSIBRTNGDEFN (IB Routing definitions, named only) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSIBRTNGDEFN")
        rtngtype_col = "RTNGTYPE" if "rtngtype" in cols else "NULL AS RTNGTYPE"
        op_col = "IB_OPERATIONNAME" if "ib_operationname" in cols else "NULL AS IB_OPERATIONNAME"
        sender_col = "SENDERNODENAME" if "sendernodename" in cols else "NULL AS SENDERNODENAME"
        rcvr_col = "RECEIVERNODENAME" if "receivernodename" in cols else "NULL AS RECEIVERNODENAME"
        status_col = "EFF_STATUS" if "eff_status" in cols else "NULL AS EFF_STATUS"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT ROUTINGDEFNNAME, {rtngtype_col}, {op_col},
                   {sender_col}, {rcvr_col}, {status_col}, {ts_col}
              FROM SYSADM.PSIBRTNGDEFN
             WHERE ROUTINGDEFNNAME NOT LIKE '~%'
               AND (:q IS NULL OR UPPER(ROUTINGDEFNNAME) LIKE :q
                    OR UPPER({op_col}) LIKE :q)
             ORDER BY ROUTINGDEFNNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "routingdefnname",
                    ["rtngtype", "ib_operationname", "sendernodename",
                     "receivernodename", "eff_status", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ib_routings",
                 "query": q, "warnings": warnings})
    return diff


def compare_ib_messages(env1, env2, q="", limit=500):
    """Diff PSMSGDEFN (IB Message definitions) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSMSGDEFN")
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        status_col = "MSGSTATUS" if "msgstatus" in cols else "NULL AS MSGSTATUS"
        owner_col = "OBJECTOWNERID" if "objectownerid" in cols else "NULL AS OBJECTOWNERID"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT MSGNAME, {status_col}, {descr_col}, {owner_col}, {ts_col}
              FROM SYSADM.PSMSGDEFN
             WHERE (:q IS NULL OR UPPER(MSGNAME) LIKE :q {descr_filter})
             ORDER BY MSGNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "msgname",
                    ["msgstatus", "descr", "objectownerid", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ib_messages",
                 "query": q, "warnings": warnings})
    return diff


def compare_ci(env1, env2, q="", limit=500):
    """Diff PSBCDEFN (Component Interface definitions) between two environments."""
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}
    warnings = []
    all_rows = []

    for env in (env1, env2):
        cols = psdb.table_columns(env, "PSBCDEFN")
        if not cols:
            all_rows.append([])
            warnings.append({"code": f"{env.upper()}_NO_TABLE",
                             "message": f"{env}: PSBCDEFN not accessible", "severity": "error"})
            continue
        descr_col = "DESCR" if "descr" in cols else "NULL AS DESCR"
        descr_filter = "OR UPPER(DESCR) LIKE :q" if "descr" in cols else ""
        type_col = "BCTYPE" if "bctype" in cols else "NULL AS BCTYPE"
        if "bcpgname" in cols:
            pnlgrp_col = "BCPGNAME AS PNLGRPNAME"
        elif "pnlgrpname" in cols:
            pnlgrp_col = "PNLGRPNAME"
        else:
            pnlgrp_col = "NULL AS PNLGRPNAME"
        ts_col = "LASTUPDDTTM" if "lastupddttm" in cols else "NULL AS LASTUPDDTTM"
        sql = f"""
            SELECT BCNAME, {type_col}, {descr_col}, {pnlgrp_col}, {ts_col}
              FROM SYSADM.PSBCDEFN
             WHERE (:q IS NULL OR UPPER(BCNAME) LIKE :q {descr_filter})
             ORDER BY BCNAME
             FETCH FIRST {int(limit)} ROWS ONLY
        """
        rows, w = _run(env, sql, params)
        all_rows.append(rows)
        if w:
            warnings.append(w)

    rows1, rows2 = all_rows
    diff = _compare(rows1, rows2, "bcname",
                    ["bctype", "descr", "pnlgrpname", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ci",
                 "query": q, "warnings": warnings})
    return diff


def compare_ae_body(env1, env2, ae_applid):
    """
    Step-level diff of an AE program between two environments.
    Compares PSAESTEPDEFN rows (section+step composite key), and for SQL steps
    fetches and diffs the SQL text from PSAESTMTDEFN + PSSQLTEXTDEFN.
    Returns a structured diff with per-step detail.
    """
    ae_applid = ae_applid.strip().upper()
    warnings = []

    def _fetch_steps(env):
        try:
            return psdb.query(env, """
                SELECT AE_SECTION, AE_STEP, AE_ACTIVE_STATUS, AE_ABEND_ACTION, DESCR
                  FROM SYSADM.PSAESTEPDEFN
                 WHERE AE_APPLID = :applid
                   AND DBTYPE    = ' '
                   AND MARKET    = 'GBL'
                   AND EFFDT = (
                       SELECT MAX(e.EFFDT) FROM SYSADM.PSAESTEPDEFN e
                        WHERE e.AE_APPLID  = PSAESTEPDEFN.AE_APPLID
                          AND e.AE_SECTION = PSAESTEPDEFN.AE_SECTION
                          AND e.AE_STEP    = PSAESTEPDEFN.AE_STEP
                          AND e.DBTYPE     = PSAESTEPDEFN.DBTYPE
                          AND e.MARKET     = PSAESTEPDEFN.MARKET)
                 ORDER BY AE_SECTION, AE_STEP
            """, {"applid": ae_applid}), None
        except Exception as exc:
            return [], f"{env}: {exc}"

    def _fetch_sql_texts(env):
        """Return dict keyed by (section, step) -> full sql_text (chunks concatenated by seqnum)."""
        try:
            stmt_rows = psdb.query(env, """
                SELECT s.AE_SECTION, s.AE_STEP, TRIM(s.SQLID) AS SQLID
                  FROM SYSADM.PSAESTMTDEFN s
                 WHERE s.AE_APPLID = :applid
                   AND s.DBTYPE    = ' '
                   AND s.MARKET    = 'GBL'
                   AND s.EFFDT = (
                       SELECT MAX(e.EFFDT) FROM SYSADM.PSAESTMTDEFN e
                        WHERE e.AE_APPLID  = s.AE_APPLID
                          AND e.AE_SECTION = s.AE_SECTION
                          AND e.AE_STEP    = s.AE_STEP
                          AND e.DBTYPE     = s.DBTYPE
                          AND e.MARKET     = s.MARKET)
                 ORDER BY s.AE_SECTION, s.AE_STEP
            """, {"applid": ae_applid})
        except Exception:
            return {}

        sqlids = {str(r.get("sqlid") or "").strip() for r in stmt_rows
                  if str(r.get("sqlid") or "").strip()}
        if not sqlids:
            return {}

        try:
            text_rows = psdb.query(env, f"""
                SELECT SQLID, SEQNUM, SQLTEXT
                  FROM SYSADM.PSSQLTEXTDEFN
                 WHERE SQLTYPE = 1
                   AND SQLID IN ({','.join(':id'+str(i) for i in range(len(sqlids)))})
                 ORDER BY SQLID, SEQNUM
            """, {f"id{i}": sid for i, sid in enumerate(sqlids)})
        except Exception:
            return {}

        # Concatenate chunks per SQLID ordered by SEQNUM
        sqlid_chunks: dict = {}
        for r in text_rows:
            sid = str(r.get("sqlid") or "").strip()
            sqlid_chunks.setdefault(sid, []).append(str(r.get("sqltext") or ""))
        sqlid_to_text = {sid: "".join(chunks) for sid, chunks in sqlid_chunks.items()}

        result = {}
        for r in stmt_rows:
            sid = str(r.get("sqlid") or "").strip()
            if sid and sid in sqlid_to_text:
                key = (str(r.get("ae_section") or "").strip(),
                       str(r.get("ae_step") or "").strip())
                result[key] = sqlid_to_text[sid]
        return result

    steps1, err1 = _fetch_steps(env1)
    steps2, err2 = _fetch_steps(env2)
    if err1:
        warnings.append({"code": f"{env1.upper()}_STEP_ERR", "message": err1, "severity": "error"})
    if err2:
        warnings.append({"code": f"{env2.upper()}_STEP_ERR", "message": err2, "severity": "error"})

    sql1 = _fetch_sql_texts(env1)
    sql2 = _fetch_sql_texts(env2)

    def _step_key(r):
        return f"{str(r.get('ae_section') or '').strip()}.{str(r.get('ae_step') or '').strip()}"

    map1 = {_step_key(r): r for r in steps1}
    map2 = {_step_key(r): r for r in steps2}
    all_keys = sorted(set(map1) | set(map2))

    only_in_env1, only_in_env2, changed, identical = [], [], [], []

    for key in all_keys:
        sect, _, step = key.partition(".")
        in1 = key in map1
        in2 = key in map2
        if in1 and not in2:
            only_in_env1.append({"step_key": key, **map1[key]})
        elif in2 and not in1:
            only_in_env2.append({"step_key": key, **map2[key]})
        else:
            r1, r2 = map1[key], map2[key]
            step_tuple = (sect.strip(), step.strip())
            txt1 = sql1.get(step_tuple, "")
            txt2 = sql2.get(step_tuple, "")
            sql_changed = txt1 != txt2
            meta_changed = (str(r1.get("ae_active_status") or "") != str(r2.get("ae_active_status") or "") or
                            str(r1.get("ae_abend_action") or "") != str(r2.get("ae_abend_action") or ""))
            if sql_changed or meta_changed:
                diff_lines = list(difflib.unified_diff(
                    txt1.splitlines(), txt2.splitlines(),
                    fromfile=f"{env1}/{key}", tofile=f"{env2}/{key}", lineterm="",
                )) if sql_changed else []
                changed.append({
                    "step_key": key,
                    "ae_section": sect.strip(),
                    "ae_step": step.strip(),
                    "sql_changed": sql_changed,
                    "meta_changed": meta_changed,
                    "env1_status": r1.get("ae_active_status"),
                    "env2_status": r2.get("ae_active_status"),
                    "diff": "\n".join(diff_lines) if diff_lines else "",
                })
            else:
                identical.append(key)

    return {
        "env1": env1, "env2": env2,
        "ae_applid": ae_applid,
        "only_in_env1": only_in_env1,
        "only_in_env2": only_in_env2,
        "changed": changed,
        "identical_count": len(identical),
        "total_steps": len(all_keys),
        "warnings": warnings,
    }


def summary(env1, env2):
    """
    Quick catalog-count comparison across key object types.
    Returns a list of {type, env1_count, env2_count, delta} rows.
    """
    queries = [
        ("Records",          "SELECT COUNT(*) AS n FROM SYSADM.PSRECDEFN"),
        ("Fields",           "SELECT COUNT(*) AS n FROM SYSADM.PSDBFIELD"),
        ("Record Fields",    "SELECT COUNT(*) AS n FROM SYSADM.PSRECFIELD"),
        ("Components",       "SELECT COUNT(*) AS n FROM SYSADM.PSPNLGRPDEFN WHERE MARKET='GBL'"),
        ("Pages",            "SELECT COUNT(*) AS n FROM SYSADM.PSPNLDEFN"),
        ("Permission Lists", "SELECT COUNT(*) AS n FROM SYSADM.PSCLASSDEFN"),
        ("Roles",            "SELECT COUNT(*) AS n FROM SYSADM.PSROLEDEFN"),
        ("AE Programs",      "SELECT COUNT(*) AS n FROM SYSADM.PSAEAPPLDEFN"),
        ("PeopleCode Progs", "SELECT COUNT(DISTINCT OBJECTVALUE1||'|'||OBJECTVALUE2||'|'||OBJECTVALUE3) AS n FROM SYSADM.PSPCMPROG"),
        ("SQL Definitions",  "SELECT COUNT(*) AS n FROM SYSADM.PSSQLDEFN"),
        ("Portal Entries",   "SELECT COUNT(*) AS n FROM SYSADM.PSPRSMDEFN"),
        ("PS Queries",       "SELECT COUNT(*) AS n FROM SYSADM.PSQRYDEFN WHERE OPRID = ' '"),
        ("Menus",            "SELECT COUNT(*) AS n FROM SYSADM.PSMENUDEFN"),
        ("Trees",            "SELECT COUNT(*) AS n FROM SYSADM.PSTREEDEFN"),
        ("IB Routings",      "SELECT COUNT(*) AS n FROM SYSADM.PSIBRTNGDEFN WHERE ROUTINGDEFNNAME NOT LIKE '~%'"),
        ("IB Messages",      "SELECT COUNT(*) AS n FROM SYSADM.PSMSGDEFN"),
        ("Comp. Interfaces", "SELECT COUNT(*) AS n FROM SYSADM.PSBCDEFN"),
        ("Process Defs",     "SELECT COUNT(*) AS n FROM SYSADM.PS_PRCSDEFN"),
        ("Operators",        "SELECT COUNT(*) AS n FROM SYSADM.PSOPRDEFN"),
        ("Translate Values", "SELECT COUNT(*) AS n FROM SYSADM.PSXLATITEM"),
        ("IB Nodes",         "SELECT COUNT(*) AS n FROM SYSADM.PSMSGNODEDEFN"),
        ("Style Sheets",     "SELECT COUNT(*) AS n FROM SYSADM.PSSTYLEDEFN"),
        ("URL Definitions",  "SELECT COUNT(*) AS n FROM SYSADM.PSURLDEFN"),
        ("App. Packages",    "SELECT COUNT(*) AS n FROM SYSADM.PSPACKAGEDEFN"),
        ("Approval Framework", "SELECT COUNT(*) AS n FROM SYSADM.PS_EOAW_PRCS"),
        ("Message Catalog",   "SELECT COUNT(*) AS n FROM SYSADM.PSMSGCATDEFN"),
        ("Search Definitions", "SELECT COUNT(*) AS n FROM SYSADM.PSPTSF_SD"),
        ("Search Categories", "SELECT COUNT(*) AS n FROM SYSADM.PSPTSF_SRCCAT"),
        ("Pivot Grids",       "SELECT COUNT(*) AS n FROM SYSADM.PSPGCORE"),
        ("Connected Queries", "SELECT COUNT(*) AS n FROM SYSADM.PSCONQRSDEFN"),
        ("File Layouts",      "SELECT COUNT(*) AS n FROM SYSADM.PSFLDDEFN"),
        ("App Designer Projects", "SELECT COUNT(*) AS n FROM SYSADM.PSPROJECTDEFN"),
        ("IB Applications",   "SELECT COUNT(*) AS n FROM SYSADM.PSIBAPPLDEFN"),
        ("IB Service Groups", "SELECT COUNT(*) AS n FROM SYSADM.PSIBGROUPDEFN"),
        ("Application Classes", "SELECT COUNT(*) AS n FROM SYSADM.PSAPPCLASSDEFN"),
        ("Content Services",  "SELECT COUNT(*) AS n FROM SYSADM.PSPTCSSRVDEFN"),
        ("PTF Tests",         "SELECT COUNT(*) AS n FROM SYSADM.PSPTTSTDEFN"),
        ("ADS Definitions",   "SELECT COUNT(*) AS n FROM SYSADM.PSADSDEFN"),
        ("Chatbot Skills",    "SELECT COUNT(*) AS n FROM SYSADM.PSCBAPPLDEFN"),
        ("Archive Objects",   "SELECT COUNT(*) AS n FROM SYSADM.PSARCHOBJDEFN"),
        ("Timezones",         "SELECT COUNT(*) AS n FROM SYSADM.PSTIMEZONE"),
        ("Locales",           "SELECT COUNT(*) AS n FROM SYSADM.PSLOCALEDEFN"),
        ("PM Metrics",        "SELECT COUNT(*) AS n FROM SYSADM.PSPMMETRICDEFN"),
        ("PM Transactions",   "SELECT COUNT(*) AS n FROM SYSADM.PSPMTRANSDEFN"),
        ("PM Events",         "SELECT COUNT(*) AS n FROM SYSADM.PSPMEVENTDEFN"),
        ("IB Operations",     "SELECT COUNT(*) AS n FROM SYSADM.PSOPERATION"),
    ]
    rows = []
    warnings = []
    for label, sql in queries:
        c1 = c2 = None
        try:
            r = psdb.query(env1, sql)
            c1 = r[0]["n"] if r else 0
        except Exception as e:
            warnings.append({"code": "ENV1_COUNT_ERR", "message": f"{env1}/{label}: {e}", "severity": "warning"})
        try:
            r = psdb.query(env2, sql)
            c2 = r[0]["n"] if r else 0
        except Exception as e:
            warnings.append({"code": "ENV2_COUNT_ERR", "message": f"{env2}/{label}: {e}", "severity": "warning"})
        rows.append({
            "type": label,
            "env1_count": c1,
            "env2_count": c2,
            "delta": (c1 - c2) if (c1 is not None and c2 is not None) else None,
        })
    return {"env1": env1, "env2": env2, "counts": rows, "warnings": warnings}


def compare_portal_object(env1, env2, portal_objname):
    """
    Deep diff of a specific Portal Registry object across two environments.
    Compares: definition fields, permissions, children set.
    """
    from connectors import psdb

    portal_objname = portal_objname.strip().upper()
    warnings = []
    result = {"env1": env1, "env2": env2, "portal_objname": portal_objname}

    def _fetch_defn(env):
        try:
            cols = psdb.table_columns(env, "PSPRSMDEFN")
            want = ["PORTAL_OBJNAME", "PORTAL_NAME", "PORTAL_REFTYPE", "PORTAL_LABEL",
                    "PORTAL_URLTEXT", "PORTAL_URI_SEG1", "PORTAL_URI_SEG2", "PORTAL_URI_SEG3",
                    "PORTAL_PRNTOBJNAME", "DESCR254", "LASTUPDDTTM", "LASTUPDOPRID",
                    "PORTAL_SECTYPE", "PORTAL_HIDE"]
            sel = [c for c in want if c.lower() in cols]
            if not sel:
                return None
            rows = psdb.query(env, f"""
                SELECT {', '.join(sel)}
                  FROM SYSADM.PSPRSMDEFN
                 WHERE PORTAL_OBJNAME = :name
                 FETCH FIRST 1 ROWS ONLY
            """, {"name": portal_objname})
            return rows[0] if rows else None
        except Exception as exc:
            warnings.append({"code": "defn_error", "env": env, "message": str(exc), "severity": "warning"})
            return None

    def _fetch_children(env):
        try:
            rows = psdb.query(env, """
                SELECT PORTAL_OBJNAME, PORTAL_LABEL, PORTAL_REFTYPE
                  FROM SYSADM.PSPRSMDEFN
                 WHERE PORTAL_PRNTOBJNAME = :name
                 ORDER BY PORTAL_OBJNAME
            """, {"name": portal_objname})
            return {str(r.get("portal_objname") or "").strip(): dict(r) for r in rows}
        except Exception as exc:
            warnings.append({"code": "children_error", "env": env, "message": str(exc), "severity": "warning"})
            return {}

    def _fetch_permissions(env):
        try:
            rows = psdb.query(env, """
                SELECT CLASSID, PORTAL_PERMTYPE
                  FROM SYSADM.PSPORTALDEFN
                 WHERE PORTAL_OBJNAME = :name
                 ORDER BY CLASSID
            """, {"name": portal_objname})
            return {str(r.get("classid") or "").strip(): str(r.get("portal_permtype") or "").strip() for r in rows}
        except Exception:
            return {}

    defn1 = _fetch_defn(env1)
    defn2 = _fetch_defn(env2)

    # Definition field diff
    defn_diff = []
    compare_fields = ["portal_reftype", "portal_label", "portal_urltext",
                      "portal_uri_seg1", "portal_uri_seg2", "portal_uri_seg3",
                      "portal_prntobjname", "descr254", "portal_sectype", "portal_hide"]
    for field in compare_fields:
        v1 = str(defn1.get(field) or "").strip() if defn1 else None
        v2 = str(defn2.get(field) or "").strip() if defn2 else None
        if v1 != v2:
            defn_diff.append({"field": field, env1: v1, env2: v2})

    # Children diff
    children1 = _fetch_children(env1)
    children2 = _fetch_children(env2)
    all_children = sorted(set(children1) | set(children2))
    children_diff = []
    for child in all_children:
        in1 = child in children1
        in2 = child in children2
        if not (in1 and in2):
            children_diff.append({
                "portal_objname": child,
                "status": f"only_in_{env1}" if in1 else f"only_in_{env2}",
                "portal_label": (children1.get(child) or children2.get(child) or {}).get("portal_label"),
            })
        else:
            # Both have it — check if label differs
            l1 = str(children1[child].get("portal_label") or "").strip()
            l2 = str(children2[child].get("portal_label") or "").strip()
            if l1 != l2:
                children_diff.append({
                    "portal_objname": child,
                    "status": "label_differs",
                    env1: l1,
                    env2: l2,
                })

    # Permissions diff
    perms1 = _fetch_permissions(env1)
    perms2 = _fetch_permissions(env2)
    all_perms = sorted(set(perms1) | set(perms2))
    perms_diff = []
    for classid in all_perms:
        in1 = classid in perms1
        in2 = classid in perms2
        if not (in1 and in2):
            perms_diff.append({
                "classid": classid,
                "status": f"only_in_{env1}" if in1 else f"only_in_{env2}",
            })
        elif perms1[classid] != perms2[classid]:
            perms_diff.append({
                "classid": classid,
                "status": "type_differs",
                env1: perms1[classid],
                env2: perms2[classid],
            })

    ts1 = str(defn1.get("lastupddttm") or "") if defn1 else None
    ts2 = str(defn2.get("lastupddttm") or "") if defn2 else None

    result.update({
        "exists_in_env1": defn1 is not None,
        "exists_in_env2": defn2 is not None,
        "last_updated": {env1: ts1, env2: ts2},
        "definition_diffs": defn_diff,
        "children_diffs": children_diff,
        "permissions_diffs": perms_diff,
        "summary": {
            "definition_changes": len(defn_diff),
            "children_changes": len(children_diff),
            "permissions_changes": len(perms_diff),
            "total_changes": len(defn_diff) + len(children_diff) + len(perms_diff),
        },
        "warnings": warnings,
    })
    return result


# ── PeopleCode Deep Source Diff ───────────────────────────────────────────────

def _fetch_full_pc_source(env, ov1, ov2, ov3):
    """Fetch full PeopleCode source from PSPCMTXT for OV1.OV2.OV3, concatenating all PROGSEQ chunks."""
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env, "PSPCMTXT"):
        return None, [{"code": "PSPCMTXT_UNAVAILABLE", "message": f"PSPCMTXT not accessible in {env}", "severity": "warn"}]
    try:
        rows = psdb.query(env, """
            SELECT PCTEXT
              FROM sysadm.PSPCMTXT
             WHERE UPPER(OBJECTVALUE1) = :ov1
               AND UPPER(OBJECTVALUE2) = :ov2
               AND UPPER(OBJECTVALUE3) = :ov3
             ORDER BY PROGSEQ
        """, {"ov1": ov1.upper(), "ov2": ov2.upper(), "ov3": ov3.upper()})
        if not rows:
            return None, warnings
        source = "".join(str(r.get("pctext") or "") for r in rows).rstrip()
        return source, warnings
    except Exception as exc:
        return None, [{"code": "PSPCMTXT_ERR", "message": str(exc), "severity": "warn"}]


def _parse_pc_reference(reference):
    """Parse a PeopleCode reference string into (ov1, ov2, ov3) components.

    Accepts:
      OV1.OV2.EVENT           — 3 parts (Record: rec.field.event)
      OV1.OV2.OV3.EVENT       — 4 parts (Component: cmpnt.mkt.rec.event)
      OV1.OV2.EVENT.PROGSEQ   — strips numeric suffix
      OV1.OV2.OV3.EVENT.PROGSEQ

    Returns (ov1, ov2, ov3) for PSPCMTXT WHERE clause.
    """
    from urllib.parse import unquote
    ref = unquote(reference).upper().strip()
    parts = ref.split(".")
    # Strip trailing numeric (PROGSEQ)
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    if len(parts) >= 4:
        return parts[0], parts[1], parts[2], ".".join(parts[3:])
    if len(parts) == 3:
        return parts[0], parts[1], parts[2], None
    if len(parts) == 2:
        return parts[0], parts[1], None, None
    return (parts[0] if parts else ""), None, None, None


def compare_peoplecode_source(env1, env2, reference):
    """Fetch and unified-diff the FULL PeopleCode source for a program across two environments.

    Accepts references like:
      PTPG_WORKREC.FUNCLIB.FieldFormula   (Record PeopleCode — fetches all PROGSEQ chunks)
      GBL_JOB_DATA.W.JOB.FieldEdit        (Component PeopleCode)
    Optional PROGSEQ suffix (e.g. .0) is stripped.
    Source is fetched directly from PSPCMTXT, concatenating all chunks.
    """
    from urllib.parse import unquote
    ref_upper = unquote(reference).upper().strip()

    # Parse into OV components
    parts = ref_upper.split(".")
    if parts and parts[-1].isdigit():
        parts = parts[:-1]  # strip PROGSEQ

    warnings = []
    if len(parts) < 3:
        return {
            "env1": env1, "env2": env2, "reference": ref_upper,
            "exists_in_env1": False, "exists_in_env2": False,
            "identical": True, "diff": "",
            "line_count_env1": 0, "line_count_env2": 0,
            "added_lines": 0, "removed_lines": 0,
            "warnings": [{"code": "INVALID_REFERENCE",
                          "message": f"Reference must have at least 3 parts (OV1.OV2.EVENT): {ref_upper}",
                          "severity": "warn"}],
        }

    ov1, ov2, ov3 = parts[0], parts[1], ".".join(parts[2:])

    src1, w1 = _fetch_full_pc_source(env1, ov1, ov2, ov3)
    src2, w2 = _fetch_full_pc_source(env2, ov1, ov2, ov3)
    warnings.extend(w1 + w2)

    src1 = (src1 or "").rstrip()
    src2 = (src2 or "").rstrip()

    lines1 = (src1 + "\n").splitlines(keepends=True) if src1 else []
    lines2 = (src2 + "\n").splitlines(keepends=True) if src2 else []

    diff_lines = list(difflib.unified_diff(
        lines1, lines2,
        fromfile=f"{env1}",
        tofile=f"{env2}",
        lineterm="\n",
        n=4,
    ))

    added   = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

    return {
        "env1": env1,
        "env2": env2,
        "reference": ref_upper,
        "ov1": ov1,
        "ov2": ov2,
        "ov3": ov3,
        "exists_in_env1": bool(src1),
        "exists_in_env2": bool(src2),
        "line_count_env1": len(lines1),
        "line_count_env2": len(lines2),
        "identical": src1 == src2,
        "added_lines": added,
        "removed_lines": removed,
        "diff": "".join(diff_lines),
        "warnings": warnings,
    }
