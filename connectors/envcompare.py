"""
Environment comparison connector.
Queries the same PeopleSoft metadata in two named environments and diffs the results.
All comparisons are grant-aware; errors per-environment are captured as warnings.
"""

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


def compare_fields(env1, env2, record_name):
    """Diff PSRECFIELD (field definitions) for a specific record across two environments."""
    sql = """
        SELECT f.FIELDNAME,
               f.FIELDNUM,
               f.FIELDTYPE,
               f.FIELDLEN,
               f.DECIMALPOS,
               f.USEEDIT,
               f.DEFRECNAME,
               f.DEFFIELDNAME
        FROM SYSADM.PSRECFIELD f
        WHERE f.RECNAME = :recname
        ORDER BY f.FIELDNUM
    """
    params = {"recname": record_name.upper()}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    for r in rows1 + rows2:
        r["fieldtype_label"] = _label(FIELDTYPE_LABELS, r.get("fieldtype"))

    compare_cols = ["fieldtype", "fieldlen", "decimalpos", "useedit", "defrecname", "deffieldname"]
    diff = _compare(rows1, rows2, "fieldname", compare_cols)
    diff.update({"env1": env1, "env2": env2, "object_type": "field",
                 "record_name": record_name.upper(), "warnings": warnings})
    return diff


def compare_components(env1, env2, q="", limit=500):
    """Diff PSPNLGRPDEFN (component catalog) between two environments."""
    sql = """
        SELECT PNLGRPNAME,
               SEARCHRECNAME,
               ADDRECNAME,
               DESCR,
               ACTIONS
        FROM SYSADM.PSPNLGRPDEFN
        WHERE MARKET = 'GBL'
          AND (:q IS NULL OR UPPER(PNLGRPNAME) LIKE :q OR UPPER(DESCR) LIKE :q)
        ORDER BY PNLGRPNAME
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "pnlgrpname", ["searchrecname", "addrecname", "actions"])
    diff.update({"env1": env1, "env2": env2, "object_type": "component",
                 "query": q, "warnings": warnings})
    return diff


def compare_permissions(env1, env2, q="", limit=500):
    """Diff PSCLASSDEFN (permission list catalog) between two environments."""
    sql = """
        SELECT CLASSID, DESCR
        FROM SYSADM.PSCLASSDEFN
        WHERE (:q IS NULL OR UPPER(CLASSID) LIKE :q OR UPPER(DESCR) LIKE :q)
        ORDER BY CLASSID
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "classid", ["descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "permission",
                 "query": q, "warnings": warnings})
    return diff


def compare_ae(env1, env2, q="", limit=500):
    """Diff PSAEAPPLDEFN (Application Engine program catalog) between two environments."""
    sql = """
        SELECT AE_APPLID, DESCR, AE_STATUS
        FROM SYSADM.PSAEAPPLDEFN
        WHERE (:q IS NULL OR UPPER(AE_APPLID) LIKE :q OR UPPER(DESCR) LIKE :q)
        ORDER BY AE_APPLID
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "ae_applid", ["ae_status", "descr"])
    diff.update({"env1": env1, "env2": env2, "object_type": "ae",
                 "query": q, "warnings": warnings})
    return diff


def compare_roles(env1, env2, q="", limit=500):
    """Diff PSROLEDEFN (role catalog) between two environments."""
    sql = """
        SELECT ROLENAME, DESCR
        FROM SYSADM.PSROLEDEFN
        WHERE (:q IS NULL OR UPPER(ROLENAME) LIKE :q OR UPPER(DESCR) LIKE :q)
        ORDER BY ROLENAME
        FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

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
    sql = """
        SELECT SQLID, SQLTYPE, OBJECTOWNERID, LASTUPDOPRID, LASTUPDDTTM
          FROM SYSADM.PSSQLDEFN
         WHERE (:q IS NULL OR UPPER(SQLID) LIKE :q OR UPPER(OBJECTOWNERID) LIKE :q)
         ORDER BY SQLTYPE, SQLID
         FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "sqlid", ["sqltype", "objectownerid", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "sql_definitions",
                 "query": q, "warnings": warnings})
    return diff


def compare_portals(env1, env2, q="", limit=500):
    """Diff PSPRSMDEFN (Portal Registry content references) between two environments."""
    sql = """
        SELECT PORTAL_OBJNAME, PORTAL_NAME, PORTAL_LABEL,
               PORTAL_PRNTOBJNAME, PORTAL_OBJTYPE,
               LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSPRSMDEFN
         WHERE (:q IS NULL OR UPPER(PORTAL_OBJNAME) LIKE :q OR UPPER(PORTAL_LABEL) LIKE :q)
         ORDER BY PORTAL_OBJNAME
         FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "portal_objname",
                    ["portal_label", "portal_prntobjname", "portal_objtype", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "portals",
                 "query": q, "warnings": warnings})
    return diff


def compare_queries(env1, env2, q="", limit=500):
    """Diff PSQRYDEFN (public PS Queries, OPRID=' ') between two environments."""
    sql = """
        SELECT QRYNAME, DESCR, QRYTYPE, QRYFOLDER,
               QRYDISABLED, QRYVALID,
               LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSQRYDEFN
         WHERE OPRID = ' '
           AND (:q IS NULL OR UPPER(QRYNAME) LIKE :q OR UPPER(DESCR) LIKE :q)
         ORDER BY QRYNAME
         FETCH FIRST {limit} ROWS ONLY
    """.format(limit=int(limit))
    pattern = f"%{q.upper()}%" if q else None
    params = {"q": pattern}

    rows1, w1 = _run(env1, sql, params)
    rows2, w2 = _run(env2, sql, params)
    warnings = [w for w in [w1, w2] if w]

    diff = _compare(rows1, rows2, "qryname",
                    ["descr", "qrytype", "qryfolder", "qrydisabled", "lastupddttm"])
    diff.update({"env1": env1, "env2": env2, "object_type": "queries",
                 "query": q, "warnings": warnings})
    return diff


def summary(env1, env2):
    """
    Quick catalog-count comparison across key object types.
    Returns a list of {type, env1_count, env2_count, delta} rows.
    """
    queries = [
        ("Records",          "SELECT COUNT(*) AS n FROM SYSADM.PSRECDEFN"),
        ("Fields",           "SELECT COUNT(*) AS n FROM SYSADM.PSRECFIELD"),
        ("Components",       "SELECT COUNT(*) AS n FROM SYSADM.PSPNLGRPDEFN WHERE MARKET='GBL'"),
        ("Pages",            "SELECT COUNT(*) AS n FROM SYSADM.PSPNLDEFN"),
        ("Permission Lists", "SELECT COUNT(*) AS n FROM SYSADM.PSCLASSDEFN"),
        ("Roles",            "SELECT COUNT(*) AS n FROM SYSADM.PSROLEDEFN"),
        ("AE Programs",      "SELECT COUNT(*) AS n FROM SYSADM.PSAEAPPLDEFN"),
        ("PeopleCode Progs", "SELECT COUNT(DISTINCT OBJECTVALUE1||'|'||OBJECTVALUE2||'|'||OBJECTVALUE3) AS n FROM SYSADM.PSPCMPROG"),
        ("SQL Definitions",  "SELECT COUNT(*) AS n FROM SYSADM.PSSQLDEFN"),
        ("Portal Entries",   "SELECT COUNT(*) AS n FROM SYSADM.PSPRSMDEFN"),
        ("PS Queries",       "SELECT COUNT(*) AS n FROM SYSADM.PSQRYDEFN WHERE OPRID = ' '"),
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
