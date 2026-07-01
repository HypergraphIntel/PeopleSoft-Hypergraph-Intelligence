from connectors import graphshape, psdb, ptmetadata

AE_ACTION_TYPES = {
    "S": "SQL",
    "P": "PeopleCode",
    "C": "Call Section",
    "L": "Log Message",
    "D": "Do Select",
    "W": "Do When",
    "U": "Do Until",
    "H": "Do While",
    "M": "Message",
    "X": "Do Select (Extended)",
    "T": "Do Select (Temp Table)",
    "A": "Assign",
    "E": "Declare/Execute",
}

AE_SECTION_TYPES = {
    "": "Regular",
    "0": "Regular",
    "1": "Function",
    "C": "Critical",
}


def safe_ae_query(env, table_name, col_candidates, where_clause, params, required_cols=None, order_by=None):
    """Query an AE table safely; return (rows, warning_or_None)."""
    if not ptmetadata.has_table(env, table_name):
        return [], ptmetadata.warning(
            f"{table_name.lower()}_unavailable",
            f"Table SYSADM.{table_name} is not accessible.",
            detail={"table": table_name, "hint": "Missing Oracle grant or table does not exist"},
        )

    try:
        available = psdb.table_columns(env, table_name)
        required = set(c.lower() for c in (required_cols or []))
        selected = [col for col in col_candidates if col.lower() in available]

        missing_required = required - {c.lower() for c in selected}
        if missing_required:
            return [], ptmetadata.warning(
                f"{table_name.lower()}_columns_missing",
                f"Required columns missing from {table_name}: {', '.join(missing_required)}",
            )

        if not selected:
            return [], ptmetadata.warning(
                f"{table_name.lower()}_empty",
                f"No queryable columns found in {table_name}.",
            )

        order = f"ORDER BY {order_by}" if order_by else ""
        rows = psdb.query(env, f"""
            SELECT {", ".join(selected)}
              FROM SYSADM.{table_name}
             WHERE {where_clause}
             {order}
        """, params)

        return rows, None
    except Exception as exc:
        return [], ptmetadata.warning(f"{table_name.lower()}_query_failed", str(exc))


def programs(env, q="", limit=100):
    """Search Application Engine programs."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"

    candidates = ["AE_APPLID", "DESCR", "LASTUPDDTTM", "LASTUPDOPRID", "AE_DISABLE_RESTART", "VERSION"]

    if not ptmetadata.has_table(env, "PSAEAPPLDEFN"):
        return {
            "items": [],
            "warnings": [ptmetadata.warning(
                "psaeappldefn_unavailable",
                "SYSADM.PSAEAPPLDEFN is not accessible. Missing grant.",
            )],
        }

    try:
        available = psdb.table_columns(env, "PSAEAPPLDEFN")
        selected = [col for col in candidates if col.lower() in available]

        if not selected or "ae_applid" not in {c.lower() for c in selected}:
            return {"items": [], "warnings": [ptmetadata.warning("psaeappldefn_schema", "AE_APPLID not found in PSAEAPPLDEFN")]}

        predicates = ["upper(ae_applid) like :pattern"]
        if "descr" in {c.lower() for c in selected}:
            predicates.append("upper(descr) like :pattern")

        rows = psdb.query(env, f"""
            SELECT {", ".join(selected)}
              FROM SYSADM.PSAEAPPLDEFN
             WHERE {" OR ".join(predicates)}
             ORDER BY ae_applid
             FETCH FIRST {limit} ROWS ONLY
        """, {"pattern": pattern})

        return {"items": rows, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [ptmetadata.warning("ae_programs_failed", str(exc))]}


def program(env, ae_applid):
    """Get AE program definition."""
    ae_applid = ae_applid.upper()

    rows, err = safe_ae_query(
        env,
        "PSAEAPPLDEFN",
        ["AE_APPLID", "DESCR", "LASTUPDDTTM", "LASTUPDOPRID", "AE_DISABLE_RESTART", "VERSION"],
        "ae_applid = :ae_applid",
        {"ae_applid": ae_applid},
        required_cols=["AE_APPLID"],
    )

    return {"item": rows[0] if rows else None, "warnings": [err] if err else []}


def sections(env, ae_applid):
    """Get sections for an AE program."""
    ae_applid = ae_applid.upper()

    rows, err = safe_ae_query(
        env,
        "PSAESECTDEFN",
        ["AE_APPLID", "AE_SECTION", "DESCR", "AE_PARALLEL", "AE_SECTIONTYPE", "AE_DISABLE", "LASTUPDDTTM", "LASTUPDOPRID"],
        "ae_applid = :ae_applid",
        {"ae_applid": ae_applid},
        required_cols=["AE_APPLID", "AE_SECTION"],
        order_by="ae_section",
    )

    enriched = []
    for row in rows:
        item = dict(row)
        sect_type = str(item.get("ae_sectiontype") or "").strip()
        item["section_type_label"] = AE_SECTION_TYPES.get(sect_type, f"Type {sect_type}")
        enriched.append(item)

    return {"items": enriched, "warnings": [err] if err else []}


def steps(env, ae_applid, ae_section=None):
    """Get steps for an AE program, optionally filtered by section."""
    ae_applid = ae_applid.upper()

    where = "ae_applid = :ae_applid"
    params = {"ae_applid": ae_applid}

    if ae_section:
        where += " AND ae_section = :ae_section"
        params["ae_section"] = ae_section.upper()

    rows, err = safe_ae_query(
        env,
        "PSAESTEPDEFN",
        ["AE_APPLID", "AE_SECTION", "AE_STEP", "DESCR", "AE_ACTTYPE",
         "AE_STEP_ONABEND", "AE_ONABEND_SECTION", "LASTUPDDTTM", "LASTUPDOPRID"],
        where,
        params,
        required_cols=["AE_APPLID", "AE_SECTION", "AE_STEP"],
        order_by="ae_section, ae_step",
    )

    enriched = []
    for row in rows:
        item = dict(row)
        act = str(item.get("ae_acttype") or "").strip()
        item["action_type_label"] = AE_ACTION_TYPES.get(act, f"Type '{act}'")
        enriched.append(item)

    return {"items": enriched, "warnings": [err] if err else []}


def ae_sql_step_text(env, ae_applid):
    """Return a dict mapping (section, step, stmt_type) -> sql_text for SQL-bearing AE steps.

    Queries PSAESTMTDEFN for the program's step-to-SQLID mapping, then
    batch-fetches actual SQL text from PSSQLTEXTDEFN (SQLTYPE=1).
    Returns ({key: text}, [warnings]).
    """
    ae_applid = ae_applid.upper()

    if not ptmetadata.has_table(env, "PSAESTMTDEFN"):
        return {}, [ptmetadata.warning(
            "psaestmtdefn_unavailable",
            "SYSADM.PSAESTMTDEFN is not accessible — AE step SQL text unavailable.",
        )]

    if not ptmetadata.has_table(env, "PSSQLTEXTDEFN"):
        return {}, [ptmetadata.warning(
            "pssqltextdefn_unavailable",
            "SYSADM.PSSQLTEXTDEFN is not accessible — AE step SQL text unavailable.",
        )]

    available = psdb.table_columns(env, "PSAESTMTDEFN")
    needed = {"ae_applid", "ae_section", "ae_step", "ae_stmt_type", "sqlid", "dbtype", "effdt", "market"}
    if not needed.issubset(available):
        return {}, []

    try:
        stmt_rows = psdb.query(env, """
            SELECT AE_SECTION, AE_STEP, AE_STMT_TYPE, TRIM(SQLID) AS SQLID
              FROM SYSADM.PSAESTMTDEFN
             WHERE AE_APPLID = :applid
               AND DBTYPE    = :dbtype
               AND MARKET    = :market
               AND EFFDT = (
                   SELECT MAX(E.EFFDT) FROM SYSADM.PSAESTMTDEFN E
                    WHERE E.AE_APPLID  = PSAESTMTDEFN.AE_APPLID
                      AND E.AE_SECTION = PSAESTMTDEFN.AE_SECTION
                      AND E.AE_STEP    = PSAESTMTDEFN.AE_STEP
                      AND E.DBTYPE     = PSAESTMTDEFN.DBTYPE
                      AND E.MARKET     = PSAESTMTDEFN.MARKET)
             ORDER BY AE_SECTION, AE_STEP
        """, {"applid": ae_applid, "dbtype": " ", "market": "GBL"})
    except Exception as exc:
        return {}, [ptmetadata.warning("psaestmtdefn_query_error",
                                       f"Could not query PSAESTMTDEFN: {exc}")]

    # Collect SQLIDs; skip rows with no SQL text reference
    # Key is (section, step) — multiple stmt_types per step are collected as a list
    step_stmts: dict = {}  # (section, step) -> [{stmt_type, sqlid}, ...]
    sqlids = []
    for r in stmt_rows:
        sid = str(r.get("sqlid") or "").strip()
        if not sid:
            continue
        key = (
            str(r.get("ae_section") or "").strip(),
            str(r.get("ae_step") or "").strip(),
        )
        step_stmts.setdefault(key, []).append({
            "stmt_type": str(r.get("ae_stmt_type") or "").strip(),
            "sqlid": sid,
        })
        sqlids.append(sid)

    if not sqlids:
        return {}, []

    # Batch-fetch SQL text chunks, preferring Oracle DBTYPE='7' over Generic ' '
    try:
        in_list = ", ".join(f"'{s.replace(chr(39), chr(39)+chr(39))}'" for s in sqlids)
        text_rows = psdb.query(env, f"""
            SELECT SQLID, SEQNUM, DBTYPE, SQLTEXT
              FROM SYSADM.PSSQLTEXTDEFN
             WHERE SQLID IN ({in_list})
               AND SQLTYPE = 1
               AND DBTYPE  IN (chr(32), '7')
               AND EFFDT = (
                   SELECT MAX(E.EFFDT) FROM SYSADM.PSSQLTEXTDEFN E
                    WHERE E.SQLID   = PSSQLTEXTDEFN.SQLID
                      AND E.SQLTYPE = PSSQLTEXTDEFN.SQLTYPE
                      AND E.DBTYPE  = PSSQLTEXTDEFN.DBTYPE)
             ORDER BY SQLID, DBTYPE DESC, SEQNUM
        """, {})
    except Exception as exc:
        return {}, [ptmetadata.warning("pssqltextdefn_query_error",
                                       f"Could not fetch AE SQL text: {exc}")]

    # Concatenate chunks per SQLID; Oracle variant (DBTYPE='7') wins over Generic
    from collections import defaultdict
    chunks_by_sid: dict = defaultdict(lambda: {"7": [], " ": []})
    for r in text_rows:
        sid = str(r.get("sqlid") or "").strip()
        db = str(r.get("dbtype") or " ")
        chunks_by_sid[sid][db].append(str(r.get("sqltext") or ""))

    sqlid_text = {}
    for sid, variants in chunks_by_sid.items():
        text = "".join(variants["7"]) if variants["7"] else "".join(variants[" "])
        if text.strip():
            sqlid_text[sid] = text

    # Build step-keyed result: (section, step) -> list of {stmt_type, sql_text}
    result: dict = {}
    for key, stmts in step_stmts.items():
        entries = []
        for st in stmts:
            text = sqlid_text.get(st["sqlid"])
            if text:
                entries.append({"stmt_type": st["stmt_type"], "sql_text": text})
        if entries:
            result[key] = entries

    return result, []


def state_records(env, ae_applid):
    """Get state records for an AE program from PSAEAPPLSTATE."""
    ae_applid = ae_applid.upper()

    # Column name varies by PeopleTools version: AE_STATE_RECNAME (newer) or RECNAME (older)
    rows, err = safe_ae_query(
        env,
        "PSAEAPPLSTATE",
        ["AE_APPLID", "AE_STATE_RECNAME", "RECNAME", "AE_DEFAULT_STATE", "AE_ISBASESTATE"],
        "ae_applid = :ae_applid",
        {"ae_applid": ae_applid},
        required_cols=["AE_APPLID"],
        order_by="1",
    )

    linked = []
    for row in rows:
        item = dict(row)
        # Normalize: prefer AE_STATE_RECNAME, fall back to RECNAME
        recname = (
            str(item.get("ae_state_recname") or item.get("recname") or "").strip() or None
        )
        is_default = str(item.get("ae_default_state") or item.get("ae_isbasestate") or "").strip()
        if recname:
            item["recname"] = recname
            item["title"] = recname
            item["is_default"] = is_default in ("Y", "1", "T")
            if is_default in ("Y", "1", "T"):
                item["relationship"] = "Default"
            item.setdefault("_links", {})["admin"] = f"/admin/object/record/{recname}"
        linked.append(item)

    return {"items": linked, "warnings": [err] if err else []}


def temp_tables(env, ae_applid):
    """Get temp table assignments for an AE program."""
    ae_applid = ae_applid.upper()

    rows, err = safe_ae_query(
        env,
        "PSPRCSRQST",
        ["PRCSINSTANCE", "PRCSNAME", "PRCSTYPE"],
        "1=0",  # just probe schema existence
        {},
    )
    _ = rows  # discard

    # Try PSAETEMPRECDEFN first
    rows2, err2 = safe_ae_query(
        env,
        "PSAETEMPRECDEFN",
        ["AE_APPLID", "RECNAME", "AE_TMPTBLCNT", "AE_TMPTBLUSE"],
        "ae_applid = :ae_applid",
        {"ae_applid": ae_applid},
        required_cols=["AE_APPLID", "RECNAME"],
        order_by="ae_tmptblcnt, recname",
    )

    if rows2 or err2 is None:
        linked = []
        for row in rows2:
            item = dict(row)
            recname = item.get("recname")
            if recname:
                item.setdefault("_links", {})["admin"] = f"/admin/object/record/{recname}"
            linked.append(item)
        return {"items": linked, "warnings": [err2] if err2 else []}

    # Fallback: look for temp table steps in PSAESTEPDEFN
    step_rows, step_err = safe_ae_query(
        env,
        "PSAESTEPDEFN",
        ["AE_APPLID", "AE_SECTION", "AE_STEP", "AE_ACTTYPE"],
        "ae_applid = :ae_applid AND ae_acttype IN ('T', 'D')",
        {"ae_applid": ae_applid},
        order_by="ae_section, ae_step",
    )

    return {"items": step_rows, "warnings": [w for w in [err2, step_err] if w]}


def sql_actions(env, ae_applid):
    """Get SQL action content for an AE program via PSSQLDDEFN/PSSQLTEXTDEFN."""
    ae_applid = ae_applid.upper()

    # SQL actions reference SQL definitions stored in PSSQLDDEFN
    rows, err = safe_ae_query(
        env,
        "PSSQLDDEFN",
        ["SQLID", "SQLTYPE", "DESCR", "LASTUPDDTTM", "LASTUPDOPRID"],
        "upper(sqlid) like :pattern",
        {"pattern": f"%{ae_applid}%"},
        required_cols=["SQLID"],
        order_by="sqlid",
    )

    if not rows and err:
        return {"items": [], "warnings": [err]}

    linked = []
    for row in rows:
        item = dict(row)
        sql_id = item.get("sqlid")
        if sql_id:
            item.setdefault("_links", {})["admin"] = f"/admin/object/sql_definition/{sql_id}"
        linked.append(item)

    return {"items": linked, "warnings": [err] if err else []}


def ae_peoplecode(env, ae_applid):
    """Get PeopleCode programs attached to AE steps."""
    ae_applid = ae_applid.upper()

    # Search PSPCMPROG for any row referencing this AE by name in a value column.
    # AEs with PeopleCode steps may appear here with OV1=ae_applid.
    if not ptmetadata.has_table(env, "PSPCMPROG"):
        return {"items": [], "warnings": [ptmetadata.warning(
            "pspcmprog_unavailable",
            "SYSADM.PSPCMPROG not accessible. Cannot retrieve AE PeopleCode metadata.",
        )]}

    try:
        # AE PeopleCode is objectid1=66, OV1=applid, OV2=section, OV6=step, OV7=event
        columns = psdb.select_existing_columns(
            env, "PSPCMPROG",
            ["OBJECTID1", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4",
             "OBJECTVALUE5", "OBJECTVALUE6", "OBJECTVALUE7", "PROGSEQ",
             "LASTUPDDTTM", "LASTUPDOPRID"],
            required=["OBJECTVALUE1"],
        )
        rows = psdb.query(env, f"""
            SELECT {", ".join(columns)}
              FROM SYSADM.PSPCMPROG
             WHERE OBJECTID1 = 66
               AND upper(OBJECTVALUE1) = upper(:ae_applid)
             ORDER BY OBJECTVALUE2, OBJECTVALUE6
             FETCH FIRST 200 ROWS ONLY
        """, {"ae_applid": ae_applid})

        return {"items": rows, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [ptmetadata.warning("ae_peoplecode_failed", str(exc))]}


def process_definitions(env, ae_applid):
    """Get process scheduler definitions that run this AE."""
    ae_applid = ae_applid.upper()

    rows, err = safe_ae_query(
        env,
        "PSPROCESSDEFN",
        ["PRCSTYPE", "PRCSNAME", "DESCR", "PRCSCATEGORY", "JOBNAME",
         "SERVERNAMERUN", "PRIORITY", "LASTUPDDTTM", "LASTUPDOPRID"],
        "upper(prcsname) = :ae_applid OR upper(jobname) = :ae_applid",
        {"ae_applid": ae_applid},
        required_cols=["PRCSNAME"],
        order_by="prcsname",
    )

    return {"items": rows, "warnings": [err] if err else []}


def runtime_instances(env, ae_applid, limit=20):
    """Get recent process scheduler requests for this AE."""
    ae_applid = ae_applid.upper()
    limit = max(1, min(int(limit), 100))

    rows, err = safe_ae_query(
        env,
        "PSPRCSRQST",
        ["PRCSINSTANCE", "OPRID", "PRCSTYPE", "PRCSNAME", "RUNSTATUS",
         "BEGINDTTM", "ENDDTTM", "RUNCNTLID", "SERVERNAMERUN", "RUNLOCATION",
         "OUTDESTTYPE", "OUTDESTFORMAT"],
        f"upper(prcsname) = :ae_applid AND upper(prcstype) LIKE '%ENGINE%' ORDER BY prcsinstance DESC FETCH FIRST {limit} ROWS ONLY",
        {"ae_applid": ae_applid},
        required_cols=["PRCSINSTANCE", "PRCSNAME"],
    )

    # Decode run status codes
    run_status_labels = {
        "0": "Cancel", "1": "Pending", "2": "Processing", "3": "Cancelled",
        "4": "Error", "5": "Hold", "6": "Queued", "7": "Initiated", "8": "No Success",
        "9": "Success", "10": "Distributing", "11": "Generated", "12": "Posted",
        "13": "Not Posted", "14": "Content Deleted",
    }

    enriched = []
    for row in rows:
        item = dict(row)
        status_code = str(item.get("runstatus") or "")
        status_label = run_status_labels.get(status_code, f"Status {status_code}")
        item["runstatus_label"] = status_label
        item["relationship"] = status_label

        prcsinstance = item.get("prcsinstance")
        if prcsinstance:
            item["title"] = f"#{prcsinstance}"
            item.setdefault("_links", {})["admin"] = f"/admin/runtime?instance={prcsinstance}"

        if item.get("oprid"):
            item.setdefault("_links", {})["operator"] = f"/admin/object/operator/{item['oprid']}"

        begin = item.get("begindttm")
        end = item.get("enddttm")
        if begin and end:
            try:
                from datetime import datetime
                fmt = "%Y-%m-%dT%H:%M:%S"
                b = datetime.fromisoformat(str(begin)[:19])
                e = datetime.fromisoformat(str(end)[:19])
                secs = int((e - b).total_seconds())
                if secs < 60:
                    item["duration"] = f"{secs}s"
                elif secs < 3600:
                    item["duration"] = f"{secs // 60}m {secs % 60}s"
                else:
                    item["duration"] = f"{secs // 3600}h {(secs % 3600) // 60}m"
            except Exception:
                pass

        enriched.append(item)

    return {"items": enriched, "warnings": [err] if err else []}


def program_graph(env, ae_applid):
    """Build a graph of an AE program's key relationships."""
    ae_applid = ae_applid.upper()
    nodes = {}
    edges = []

    def add(node_type, name, data=None):
        nid = f"{node_type}:{name.upper()}"
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "type": node_type,
                "name": name.upper(),
                "label": name.upper(),
                "data": data or {},
                "_links": {"admin": f"/admin/object/{node_type}/{name.upper()}"},
            }
        return nid

    def link(src_type, src_name, tgt_type, tgt_name, rel):
        s = add(src_type, src_name)
        t = add(tgt_type, tgt_name)
        edges.append({"source": s, "target": t, "relationship": rel})

    add("application_engine", ae_applid)

    sect_result = sections(env, ae_applid)
    for sect in sect_result["items"]:
        sect_name = sect.get("ae_section")
        if sect_name:
            link("application_engine", ae_applid, "section", f"{ae_applid}.{sect_name}", "CONTAINS")

    state_result = state_records(env, ae_applid)
    for state in state_result["items"]:
        recname = state.get("recname")
        if recname:
            link("application_engine", ae_applid, "record", recname, "USES")

    step_result = steps(env, ae_applid)
    for step in step_result["items"]:
        act = str(step.get("ae_acttype") or "").strip()
        if act == "P":
            sect = step.get("ae_section", "")
            step_name = step.get("ae_step", "")
            ref = f"{ae_applid}.{sect}.{step_name}"
            link("application_engine", ae_applid, "peoplecode", ref, "CONTAINS")
        elif act == "C":
            onabend_sect = step.get("ae_onabend_section")
            if onabend_sect:
                link("application_engine", ae_applid, "section", f"{ae_applid}.{onabend_sect}", "CALLS")

    proc_result = process_definitions(env, ae_applid)
    for proc in proc_result["items"]:
        prcsname = proc.get("prcsname")
        if prcsname:
            link("process_scheduler", ae_applid, "process", prcsname, "SCHEDULED_AS")

    return graphshape.annotate_graph({
        "root": f"application_engine:{ae_applid}",
        "nodes": list(nodes.values()),
        "edges": edges,
    }, "application_engine", "domain_ae", "application-engine dependency graph")
