import json
from pathlib import Path
import re
import oracledb

CONFIG = Path("/opt/deathstar-api/config.json")
IDENTIFIER_RE = re.compile(r"^[A-Z][A-Z0-9_$#]*$")


def load_envs():
    data = json.loads(CONFIG.read_text())
    return data["peoplesoft"]["environments"]


def dsn(env):
    return f'{env["host"]}:{env["port"]}/{env["service"]}'

def query(env_name, sql, params=None):
    env = next(e for e in load_envs()
               if e["name"].upper() == env_name.upper())
    return query_env(env, sql, params)

def _clean_value(v):
    """Convert Oracle-specific types to JSON-safe Python primitives."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "read"):
        return v.read()
    return str(v)


def query_env(env, sql, params=None):
    conn = oracledb.connect(
        user=env["user"],
        password=env["password"],
        dsn=dsn(env)
    )
    cur = conn.cursor()
    cur.execute(sql, params or {})
    cols = [c[0].lower() for c in cur.description]
    rows = [dict(zip(cols, (_clean_value(v) for v in row))) for row in cur.fetchall()]
    conn.close()
    return rows


def safe_identifier(value):
    identifier = value.upper().strip().replace('"', '')

    if not IDENTIFIER_RE.fullmatch(identifier):
        raise ValueError(f"Invalid Oracle identifier: {value}")

    return identifier


def table_columns(env_name, table_name, owner="SYSADM"):
    sql = """
        select column_name
        from all_tab_columns
        where owner = upper(:owner)
          and table_name = upper(:table_name)
        order by column_id
    """

    rows = query(env_name, sql, {
        "owner": owner,
        "table_name": table_name,
    })

    return {row["column_name"].lower() for row in rows}


def existing_columns(env_name, table_name, candidates, owner="SYSADM"):
    available = table_columns(env_name, table_name, owner)
    return [col for col in candidates if col.lower() in available]


def select_existing_columns(env_name, table_name, candidates, required=None, owner="SYSADM"):
    required = required or []
    columns = []
    seen = set()

    for col in required + candidates:
        key = col.lower()
        if key not in seen:
            seen.add(key)
            columns.append(col)

    selected = existing_columns(env_name, table_name, columns, owner)

    if not selected:
        return columns

    missing_required = [
        col for col in required
        if col.lower() not in {selected_col.lower() for selected_col in selected}
    ]

    if missing_required:
        raise ValueError(
            f"{table_name} is missing required column(s): {', '.join(missing_required)}"
        )

    return selected


def table_count(env_name, table_name):
    env = next(e for e in load_envs() if e["name"].upper() == env_name.upper())
    table_name = safe_identifier(table_name)
    sql = f"select count(*) as row_count from SYSADM.{table_name}"
    return {
        "environment": env["name"],
        "table": table_name,
        "rows": query_env(env, sql)[0]["row_count"]
    }

def search_objects(env_name, q, owner="SYSADM"):
    sql = """
        select owner, object_name, object_type
        from all_objects
        where upper(owner) = upper(:owner)
          and object_type in ('TABLE', 'VIEW')
          and upper(object_name) like upper(:pattern)
        order by object_type, object_name
    """
    return query(env_name, sql, {
        "owner": owner,
        "pattern": f"%{q}%"
    })


def object_columns(env_name, object_name, owner="SYSADM"):
    sql = """
        select
            owner,
            table_name,
            column_id,
            column_name,
            data_type,
            data_length,
            nullable
        from all_tab_columns
        where upper(owner) = upper(:owner)
          and upper(table_name) = upper(:object_name)
        order by column_id
    """
    return query(env_name, sql, {
        "owner": owner,
        "object_name": object_name
    })


def sample_rows(env_name, object_name, owner="SYSADM", limit=20):
    # object/owner are validated to simple identifiers before interpolation
    safe_owner = safe_identifier(owner)
    safe_object = safe_identifier(object_name)
    limit = max(1, min(int(limit), 100))

    sql = f"""
        select *
        from {safe_owner}.{safe_object}
        fetch first {limit} rows only
    """
    return query(env_name, sql)


def object_count(env_name, object_name, owner="SYSADM"):
    safe_owner = safe_identifier(owner)
    safe_object = safe_identifier(object_name)

    sql = f"""
        select count(*) as row_count
        from {safe_owner}.{safe_object}
    """
    rows = query(env_name, sql)
    return {
        "environment": env_name.upper(),
        "owner": safe_owner,
        "object_name": safe_object,
        "row_count": rows[0]["row_count"]
    }


def search_records(env_name, q):
    sql = """
        select
            recname,
            rectype,
            recdescr,
            fieldcount,
            indexcount,
            sqltablename,
            parentrecname,
            qrysecrecname,
            version
        from sysadm.psrecdefn
        where upper(recname) like upper(:pattern)
           or upper(recdescr) like upper(:pattern)
           or upper(sqltablename) like upper(:pattern)
        order by recname
    """
    return query(env_name, sql, {"pattern": f"%{q.upper()}%"})


def record_fields(env_name, recname):
    sql = """
        select
            recname,
            fieldnum,
            fieldname,
            defrecname,
            deffieldname,
            edittable,
            useedit,
            useedit2,
            subrecord,
            setcntrlfld,
            label_id,
            lastupddttm,
            lastupdoprid
        from sysadm.psrecfield
        where upper(recname) = upper(:recname)
        order by fieldnum
    """
    return query(env_name, sql, {"recname": recname.upper()})


def field_labels_batch(env_name, fieldnames):
    """Return {fieldname: {longname, shortname}} for the given field list.

    Uses PSDBFLDLABL WHERE DEFAULT_LABEL=1 when available; falls back to an
    empty dict so callers always get a mapping they can safely .get() against.
    """
    if not fieldnames or not table_columns(env_name, "PSDBFLDLABL"):
        return {}
    upper_names = [f.strip().upper() for f in fieldnames if f and f.strip()]
    if not upper_names:
        return {}
    # Oracle IN clause — safe because names are uppercased identifiers, no SQL injection risk
    in_list = ", ".join(f"'{n}'" for n in upper_names)
    try:
        rows = query(env_name, f"""
            SELECT FIELDNAME, LONGNAME, SHORTNAME
              FROM SYSADM.PSDBFLDLABL
             WHERE FIELDNAME IN ({in_list})
               AND DEFAULT_LABEL = 1
        """, {})
        return {
            str(r.get("fieldname") or "").strip(): {
                "longname": str(r.get("longname") or "").strip(),
                "shortname": str(r.get("shortname") or "").strip(),
            }
            for r in rows
        }
    except Exception:
        return {}


def resolve_field_reference(env_name, field_ref):
    field_ref = field_ref.upper().strip()

    if "." not in field_ref:
        return {
            "input": field_ref,
            "recname": None,
            "fieldname": field_ref,
            "canonical_name": field_ref,
            "resolved": False,
            "warning": "Field reference must be RECORD.FIELD",
        }

    recname, fieldname = [part.strip() for part in field_ref.split(".", 1)]
    candidates = [recname]

    if recname.startswith("PS_"):
        candidates.append(recname[3:])
    else:
        candidates.append(f"PS_{recname}")

    seen = set()
    candidates = [candidate for candidate in candidates if not (candidate in seen or seen.add(candidate))]

    for candidate in candidates:
        rows = query(env_name, """
            select recname, fieldname
              from sysadm.psrecfield
             where recname = upper(:recname)
               and fieldname = upper(:fieldname)
             fetch first 1 rows only
        """, {"recname": candidate, "fieldname": fieldname})

        if rows:
            record = rows[0]["recname"]
            field = rows[0]["fieldname"]
            return {
                "input": field_ref,
                "recname": record,
                "fieldname": field,
                "canonical_name": f"{record}.{field}",
                "resolved": True,
            }

    return {
        "input": field_ref,
        "recname": recname,
        "fieldname": fieldname,
        "canonical_name": f"{recname}.{fieldname}",
        "resolved": False,
        "warning": "Field not found on record",
    }


def fields(env_name, q="", limit=100):
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"
    try:
        rec_columns = select_existing_columns(
            env_name,
            "PSRECFIELD",
            ["FIELDNUM", "LABEL_ID", "USEEDIT", "USEEDIT2", "EDITTABLE", "SUBRECORD"],
            required=["RECNAME", "FIELDNAME"],
        )
        field_columns = select_existing_columns(
            env_name,
            "PSDBFIELD",
            ["DESCR", "LONGNAME", "SHORTNAME", "FIELDTYPE", "LENGTH", "DECIMALPOS", "FORMAT"],
            required=["FIELDNAME"],
        )

        selected = [
            f"rf.{col} as {col.lower()}"
            for col in rec_columns
        ]
        selected.extend(
            f"df.{col} as db_{col.lower()}"
            for col in field_columns
            if col.upper() != "FIELDNAME"
        )

        sql = f"""
            select {", ".join(selected)}
              from sysadm.psrecfield rf
              left join sysadm.psdbfield df
                on df.fieldname = rf.fieldname
             where upper(rf.fieldname) like :pattern
                or upper(rf.recname || '.' || rf.fieldname) like :pattern
             order by
               case
                 when upper(rf.recname || '.' || rf.fieldname) = upper(:exact) then 0
                 when upper(rf.fieldname) = upper(:exact) then 1
                 else 2
               end,
               rf.fieldname,
               rf.recname
             fetch first {limit} rows only
        """

        return query(env_name, sql, {"pattern": pattern, "exact": q.upper()})
    except Exception:
        columns = select_existing_columns(
            env_name,
            "PSRECFIELD",
            ["FIELDNUM", "LABEL_ID", "USEEDIT", "USEEDIT2", "EDITTABLE", "SUBRECORD"],
            required=["RECNAME", "FIELDNAME"],
        )

        sql = f"""
            select {", ".join(columns)}
              from sysadm.psrecfield
             where upper(fieldname) like :pattern
                or upper(recname || '.' || fieldname) like :pattern
             order by
               case
                 when upper(recname || '.' || fieldname) = upper(:exact) then 0
                 when upper(fieldname) = upper(:exact) then 1
                 else 2
               end,
               fieldname,
               recname
             fetch first {limit} rows only
        """

        return query(env_name, sql, {"pattern": pattern, "exact": q.upper()})


def field_definition(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    recname = resolved["recname"]
    fieldname = resolved["fieldname"]

    if not resolved["resolved"]:
        # No record context — still attempt a PSDBFIELD-only type/length lookup
        db_type_info = {}
        if table_columns(env_name, "PSDBFIELD"):
            db_rows = query(env_name, """
                select fieldtype as db_fieldtype, length as db_length
                  from sysadm.psdbfield
                 where fieldname = upper(:fn)
                 fetch first 1 rows only
            """, {"fn": fieldname})
            if db_rows:
                db_type_info = {
                    "field_type": db_rows[0].get("db_fieldtype"),
                    "length": db_rows[0].get("db_length"),
                }
        return {
            **resolved,
            **db_type_info,
            "warnings": [resolved.get("warning")] if resolved.get("warning") else [],
        }

    rec_columns = select_existing_columns(
        env_name,
        "PSRECFIELD",
        [
            "FIELDNUM",
            "DEFRECNAME",
            "DEFFIELDNAME",
            "EDITTABLE",
            "USEEDIT",
            "USEEDIT2",
            "SUBRECORD",
            "SETCNTRLFLD",
            "LABEL_ID",
            "LASTUPDDTTM",
            "LASTUPDOPRID",
        ],
        required=["RECNAME", "FIELDNAME"],
    )
    db_columns = select_existing_columns(
        env_name,
        "PSDBFIELD",
        [
            "DESCR",
            "LONGNAME",
            "SHORTNAME",
            "FIELDTYPE",
            "LENGTH",
            "DECIMALPOS",
            "FORMAT",
            "XLATFLG",
            "CURRCTLFLD",
            "LANGUAGE_CD",
            "DEFAULT_VALUE",
        ],
        required=["FIELDNAME"],
    )

    selected = [f"rf.{col} as {col.lower()}" for col in rec_columns]
    selected.extend(
        f"df.{col} as db_{col.lower()}"
        for col in db_columns
        if col.upper() != "FIELDNAME"
    )

    rows = query(env_name, f"""
        select {", ".join(selected)}
          from sysadm.psrecfield rf
          left join sysadm.psdbfield df
            on df.fieldname = rf.fieldname
         where rf.recname = upper(:recname)
           and rf.fieldname = upper(:fieldname)
    """, {"recname": recname, "fieldname": fieldname})

    row = rows[0] if rows else {}
    keys = record_keys(env_name, recname)
    key_positions = [
        key for key in keys
        if key.get("fieldname") == fieldname
    ]
    key_index_ids = {key.get("indexid") for key in key_positions}
    useedit = int(row.get("useedit") or 0)
    useedit2 = int(row.get("useedit2") or 0)

    row.update({
        **resolved,
        "description": row.get("db_descr"),
        "long_name": row.get("db_longname"),
        "short_name": row.get("db_shortname"),
        "field_type": row.get("db_fieldtype"),
        "length": row.get("db_length"),
        "decimal_positions": row.get("db_decimalpos"),
        "format": row.get("db_format"),
        "xlat": row.get("db_xlatflg"),
        "default_value": row.get("db_default_value"),
        "currency_control": row.get("db_currctlfld"),
        "language_sensitivity": row.get("db_language_cd"),
        "key": bool(key_positions),
        "search_key": "0" in key_index_ids,
        "alternate_search_key": "1" in key_index_ids,
        "duplicate_order_key": "2" in key_index_ids,
        "required": bool(useedit & 1),
        "prompt_table": row.get("edittable"),
        "edit_table": row.get("edittable"),
        "translate_table": "XLATTABLE" if str(row.get("db_xlatflg") or "").upper() in ("Y", "1", "T") else None,
        "warnings": [],
    })

    return row


def field_records(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    fieldname = resolved["fieldname"]

    columns = select_existing_columns(
        env_name,
        "PSRECFIELD",
        ["FIELDNUM", "LABEL_ID", "USEEDIT", "EDITTABLE"],
        required=["RECNAME", "FIELDNAME"],
    )

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psrecfield
         where fieldname = upper(:fieldname)
         order by recname
    """

    return query(env_name, sql, {"fieldname": fieldname})


def field_pages(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    recname = resolved["recname"]
    fieldname = resolved["fieldname"]

    columns = select_existing_columns(
        env_name,
        "PSPNLFIELD",
        ["RECNAME", "FIELDNUM", "LBLTEXT", "LEVELNUM", "OCCURSLEVEL", "REQUIRED", "INVISIBLE", "DISPLAYONLY", "PROMPTTABLE"],
        required=["PNLNAME", "FIELDNAME"],
    )

    predicate = "fieldname = upper(:fieldname)"
    params = {"fieldname": fieldname}

    if recname and resolved["resolved"]:
        predicate += " and recname = upper(:recname)"
        params["recname"] = recname

    order_columns = ["pnlname"]
    if "FIELDNUM" in columns:
        order_columns.append("fieldnum")

    sql = f"""
        select distinct {", ".join(columns)}
          from sysadm.pspnlfield
         where {predicate}
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, params)


def field_components(env_name, field_ref):
    pages = field_pages(env_name, field_ref)
    components = {}

    for page in pages:
        page_name = page.get("pnlname")

        if not page_name:
            continue

        for component in page_components(env_name, page_name):
            key = component.get("pnlgrpname")
            if key:
                components[key] = component

    return sorted(components.values(), key=lambda item: item.get("pnlgrpname") or "")


def field_search_records(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    fieldname = resolved["fieldname"]

    columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "MARKET", "SEARCHRECNAME", "ADDSRCHRECNAME"],
        required=["PNLGRPNAME"],
    )

    selected = [f"c.{col} as {col.lower()}" for col in columns]

    sql = f"""
        select distinct {", ".join(selected)},
               rf.recname,
               rf.fieldname
          from sysadm.pspnlgrpdefn c
          join sysadm.psrecfield rf
            on rf.recname in (c.searchrecname, c.addsearchrecname)
         where rf.fieldname = upper(:fieldname)
         order by c.pnlgrpname, rf.recname
    """

    return query(env_name, sql, {"fieldname": fieldname})


def field_views(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    fieldname = resolved["fieldname"]

    columns = select_existing_columns(
        env_name,
        "PSRECDEFN",
        ["RECDESCR", "RECTYPE", "SQLTABLENAME"],
        required=["RECNAME"],
    )

    selected = [f"r.{col} as {col.lower()}" for col in columns]

    sql = f"""
        select distinct {", ".join(selected)}
          from sysadm.psrecdefn r
          join sysadm.psrecfield f
            on f.recname = r.recname
         where f.fieldname = upper(:fieldname)
           and (r.rectype in (1, 5, 6, 7) or upper(r.recname) like '%VW')
         order by r.recname
    """

    return query(env_name, sql, {"fieldname": fieldname})


def field_peoplecode_metadata(env_name, field_ref):
    resolved = resolve_field_reference(env_name, field_ref)
    recname = resolved["recname"]
    fieldname = resolved["fieldname"]

    if not resolved["resolved"]:
        return []

    columns = select_existing_columns(
        env_name,
        "PSPCMPROG",
        ["OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "OBJECTVALUE4", "OBJECTID1", "OBJECTID2", "OBJECTID3", "OBJECTID4", "PROGSEQ"],
        required=[],
    )

    if not columns:
        return []

    predicates = []
    params = {"recname": recname, "fieldname": fieldname}

    for col in columns:
        predicates.append(f"upper({col}) in (upper(:recname), upper(:fieldname))")

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspcmprog
         where {" or ".join(predicates)}
         fetch first 100 rows only
    """

    return query(env_name, sql, params)


def record_indexes(env_name, recname):
    sql = """
        select
            indexid,
            platform_ora,
            custkeyorder,
            activeflag,
            uniqueflag
        from sysadm.psindexdefn
        where upper(recname) = upper(:recname)
        order by indexid
    """
    return query(env_name, sql, {"recname": recname.upper()})


def record_keys(env_name, recname):
    sql = """
        select
            recname,
            indexid,
            keyposn,
            fieldname,
            ascdesc
        from sysadm.pskeydefn
        where upper(recname) = upper(:recname)
        order by indexid, keyposn
    """
    return query(env_name, sql, {"recname": recname.upper()})


def record_ddl(env_name, recname):
    recname = recname.upper()

    rec_rows = query(env_name, """
        select
            recname,
            sqltablename,
            recdescr,
            rectype
        from sysadm.psrecdefn
        where recname = upper(:recname)
    """, {"recname": recname})

    if not rec_rows:
        return {
            "environment": env_name.upper(),
            "record": recname,
            "table": None,
            "ddl": "-- Record not found"
        }

    rec = rec_rows[0]

    table_name = (rec.get("sqltablename") or "").strip()

    if not table_name:
        fallback = "PS_" + recname
        exists = query(env_name, """
            select table_name
            from all_tables
            where owner = 'SYSADM'
              and table_name = :table_name
        """, {"table_name": fallback})

        table_name = exists[0]["table_name"] if exists else fallback

    table_name = safe_identifier(table_name)

    cols = query(env_name, """
        select
            column_id,
            column_name,
            data_type,
            data_length,
            data_precision,
            data_scale,
            nullable
        from all_tab_columns
        where owner = 'SYSADM'
          and table_name = :table_name
        order by column_id
    """, {"table_name": table_name})

    try:
        pk_rows = query(env_name, """
            select fieldname
            from sysadm.pskeydefn
            where recname = :recname
              and indexid = '0'
            order by keyposn
        """, {"recname": recname})
    except Exception:
        pk_rows = []

    key_fields = []
    seen = set()

    for k in pk_rows:
        field = k["fieldname"]
        if field not in seen:
            seen.add(field)
            key_fields.append(field)

    lines = []

    for c in cols:
        dtype = c["data_type"]

        if dtype == "VARCHAR2":
            dtype = f"VARCHAR2({c['data_length']})"
        elif dtype == "CHAR":
            dtype = f"CHAR({c['data_length']})"
        elif dtype == "NUMBER":
            precision = c.get("data_precision")
            scale = c.get("data_scale")

            if precision is not None and scale is not None:
                dtype = f"NUMBER({precision},{scale})"
            elif precision is not None:
                dtype = f"NUMBER({precision})"
            else:
                dtype = "NUMBER"
        elif dtype == "DATE":
            dtype = "DATE"

        nullable = " NOT NULL" if c["nullable"] == "N" else ""
        lines.append(f"    {c['column_name']:<30} {dtype}{nullable}")

    ddl = f"-- PeopleSoft Record: {recname}\n"
    ddl += f"-- Description: {rec.get('recdescr', '')}\n"
    ddl += f"-- Oracle Table: SYSADM.{table_name}\n\n"
    ddl += f"CREATE TABLE SYSADM.{table_name} (\n"

    if lines:
        ddl += ",\n".join(lines)

    if key_fields:
        if lines:
            ddl += ",\n"
        ddl += f"    CONSTRAINT PS_{recname}_PK PRIMARY KEY ({', '.join(key_fields)})"

    ddl += "\n);"

    return {
        "environment": env_name.upper(),
        "record": recname,
        "table": table_name,
        "description": (rec.get("recdescr", "")).strip(),
        "columns": cols,
        "keys": pk_rows,
        "ddl": ddl
    }


def record_sql_table(env_name, recname):
    recname = recname.upper()

    rows = query(env_name, """
        select sqltablename
        from sysadm.psrecdefn
        where recname = :recname
    """, {"recname": recname})

    if not rows:
        return None

    table_name = (rows[0].get("sqltablename") or "").strip()

    if not table_name:
        table_name = "PS_" + recname

    return table_name


def record_count(env_name, recname):
    table_name = record_sql_table(env_name, recname)

    if not table_name:
        return {
            "environment": env_name.upper(),
            "record": recname.upper(),
            "table": None,
            "row_count": "N/A",
            "error": "Record not found"
        }

    table_name = safe_identifier(table_name)

    rows = query(env_name, f"""
        select count(*) as row_count
        from sysadm.{table_name}
    """)

    return {
        "environment": env_name.upper(),
        "record": recname.upper(),
        "table": table_name,
        "row_count": rows[0]["row_count"]
    }


def record_sample(env_name, recname, limit=20):
    table_name = record_sql_table(env_name, recname)
    limit = max(1, min(int(limit), 100))

    if not table_name:
        return []

    table_name = safe_identifier(table_name)

    return query(env_name, f"""
        select *
        from sysadm.{table_name}
        fetch first {limit} rows only
    """)


def search_oprids(env_name, q="", limit=25):
    limit = max(1, min(int(limit), 100))

    sql = f"""
        select oprid,
               oprdefndesc,
               acctlock
          from sysadm.psoprdefn
         where upper(oprid) like :q
         order by oprid
         fetch first {limit} rows only
    """

    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def oprid(oprid, env_name):
    rows = query(env_name, """
        select oprid,
               oprdefndesc,
               acctlock
          from sysadm.psoprdefn
         where oprid = upper(:oprid)
    """, {"oprid": oprid})

    return rows[0] if rows else None


def oprid_roles(oprid, env_name, columns="identity"):
    if columns == "summary":
        select_columns = "roleuser, rolename, dynamic_sw"
    else:
        select_columns = "rolename"

    sql = f"""
        select {select_columns}
          from sysadm.psroleuser
         where roleuser = upper(:oprid)
         order by rolename
    """

    return query(env_name, sql, {"oprid": oprid})


def roles(env_name, q="", limit=100):
    limit = max(1, min(int(limit), 500))
    columns = select_existing_columns(
        env_name,
        "PSROLEDEFN",
        ["DESCR", "ROLESTATUS", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["ROLENAME"],
    )
    select_columns = ", ".join(columns)

    sql = f"""
        select {select_columns}
          from sysadm.psroledefn
         where upper(rolename) like :q
         order by rolename
         fetch first {limit} rows only
    """

    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def role(env_name, rolename):
    columns = select_existing_columns(
        env_name,
        "PSROLEDEFN",
        ["DESCR", "ROLESTATUS", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["ROLENAME"],
    )
    select_columns = ", ".join(columns)

    rows = query(env_name, f"""
        select {select_columns}
          from sysadm.psroledefn
         where upper(rolename) = upper(:rolename)
    """, {"rolename": rolename})

    return rows[0] if rows else None


def role_permissionlists(env_name, rolename):
    columns = select_existing_columns(
        env_name,
        "PSROLECLASS",
        ["DYNAMIC_SW", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["ROLENAME", "CLASSID"],
    )
    select_columns = ", ".join(f"rc.{col}" for col in columns)

    sql = f"""
        select {select_columns}
          from sysadm.psroleclass rc
         where rc.rolename = upper(:rolename)
         order by rc.classid
    """

    return query(env_name, sql, {"rolename": rolename})


def permissionlists(env_name, q="", limit=100):
    limit = max(1, min(int(limit), 500))
    columns = select_existing_columns(
        env_name,
        "PSCLASSDEFN",
        ["DESCR", "CLASSDEFNDESC", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["CLASSID"],
    )

    searchable = [col for col in ("DESCR", "CLASSDEFNDESC") if col in columns]
    predicates = ["upper(classid) like :q"]
    predicates.extend(f"upper({col}) like :q" for col in searchable)
    select_columns = ", ".join(columns)

    sql = f"""
        select {select_columns}
          from sysadm.psclassdefn
         where {" or ".join(predicates)}
         order by classid
         fetch first {limit} rows only
    """

    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def permissionlist(env_name, classid):
    columns = select_existing_columns(
        env_name,
        "PSCLASSDEFN",
        ["DESCR", "CLASSDEFNDESC", "TIMEOUTMINUTES", "STARTAPPSERVER",
         "ALLOWPSWDEMAIL", "DEFAULTBPM", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["CLASSID"],
    )
    select_columns = ", ".join(columns)

    rows = query(env_name, f"""
        select {select_columns}
          from sysadm.psclassdefn
         where classid = upper(:classid)
    """, {"classid": classid})

    return rows[0] if rows else None


def permissionlist_menus(env_name, classid):
    columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["BARNAME", "BARITEMNAME"],
        required=["CLASSID", "MENUNAME"],
    )
    select_columns = ", ".join(f"ai.{col}" for col in columns if col != "CLASSID")

    sql = f"""
        select distinct {select_columns}
          from sysadm.psauthitem ai
         where ai.classid = upper(:classid)
           and ai.menuname is not null
         order by ai.menuname
    """

    return query(env_name, sql, {"classid": classid})


def auth_component_source(env_name, auth_alias="ai", group_alias="auth_pg"):
    """Return a version-adaptive component expression for PSAUTHITEM rows."""
    auth_columns = table_columns(env_name, "PSAUTHITEM")
    if "pnlgrpname" in auth_columns:
        return {
            "column": "PNLGRPNAME",
            "expr": f"{auth_alias}.pnlgrpname",
            "join": "",
            "where": f"{auth_alias}.pnlgrpname",
            "order": f"{auth_alias}.pnlgrpname",
        }

    if "pnlitemname" in auth_columns:
        # Some PeopleTools schemas store the authorized page/item in PSAUTHITEM and
        # require PSPNLGROUP to resolve the owning component.
        select_existing_columns(env_name, "PSPNLGROUP", [], required=["PNLNAME", "PNLGRPNAME"])
        return {
            "column": "PNLITEMNAME",
            "expr": f"{group_alias}.pnlgrpname",
            "join": (
                f" left join sysadm.pspnlgroup {group_alias}"
                f" on {group_alias}.pnlname = {auth_alias}.pnlitemname"
            ),
            "where": f"{group_alias}.pnlgrpname",
            "order": f"{group_alias}.pnlgrpname",
        }

    raise ValueError("PSAUTHITEM has neither PNLGRPNAME nor PNLITEMNAME")


def permissionlist_components(env_name, classid):
    source = auth_component_source(env_name)
    auth_columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["MENUNAME", "MARKET", "AUTHORIZEDACTIONS", "DISPLAYONLY", "PNLITEMNAME"],
        required=["CLASSID", source["column"]],
    )
    component_columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME", "MARKET"],
        required=["PNLGRPNAME"],
    )

    select_columns = [
        "ai.classid",
        f"{source['expr']} as pnlgrpname",
    ]

    for col in auth_columns:
        if col not in ("CLASSID", "PNLGRPNAME"):
            select_columns.append(f"ai.{col}")

    for col in component_columns:
        if col != "PNLGRPNAME":
            select_columns.append(f"pg.{col} as component_{col.lower()}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psauthitem ai
          {source["join"]}
          left join sysadm.pspnlgrpdefn pg
            on pg.pnlgrpname = {source["expr"]}
         where ai.classid = upper(:classid)
           and {source["where"]} is not null
         order by ai.menuname, {source["order"]}
    """

    return with_decoded_actions(query(env_name, sql, {"classid": classid}))


def component_pages(env_name, component):
    group_columns = select_existing_columns(
        env_name,
        "PSPNLGROUP",
        ["MARKET", "ITEMNUM", "PNLGRPITEMTYPE"],
        required=["PNLGRPNAME", "PNLNAME"],
    )

    select_columns = [f"pg.{col}" for col in group_columns]
    order_columns = ["pg.itemnum"] if "ITEMNUM" in group_columns else []
    order_columns.append("pg.pnlname")

    page_columns = select_existing_columns(
        env_name,
        "PSPNLDEFN",
        ["DESCR", "PNLTYPE"],
        required=["PNLNAME"],
    )

    for col in page_columns:
        if col != "PNLNAME":
            select_columns.append(f"pd.{col} as page_{col.lower()}")

    sql = f"""
        select {", ".join(select_columns)}
          from sysadm.pspnlgroup pg
          left join sysadm.pspnldefn pd
            on pd.pnlname = pg.pnlname
         where pg.pnlgrpname = upper(:component)
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, {"component": component})


def components(env_name, q="", limit=100):
    limit = max(1, min(int(limit), 500))
    columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME", "MARKET", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["PNLGRPNAME"],
    )
    searchable = [col for col in ("DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME") if col in columns]
    predicates = ["upper(pnlgrpname) like :q"]
    predicates.extend(f"upper({col}) like :q" for col in searchable)

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspnlgrpdefn
         where {" or ".join(predicates)}
         order by pnlgrpname
         fetch first {limit} rows only
    """

    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def component(env_name, component):
    columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME", "MARKET", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["PNLGRPNAME"],
    )

    rows = query(env_name, f"""
        select {", ".join(columns)}
          from sysadm.pspnlgrpdefn
         where pnlgrpname = upper(:component)
    """, {"component": component})

    return rows[0] if rows else None


def component_permissionlists(env_name, component):
    source = auth_component_source(env_name)
    auth_columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["MENUNAME", "AUTHORIZEDACTIONS", "DISPLAYONLY", "MARKET", "PNLITEMNAME"],
        required=["CLASSID", source["column"]],
    )
    class_columns = select_existing_columns(
        env_name,
        "PSCLASSDEFN",
        ["DESCR", "CLASSDEFNDESC"],
        required=["CLASSID"],
    )

    select_columns = ["ai.classid", f"{source['expr']} as pnlgrpname"]

    for col in auth_columns:
        if col not in ("CLASSID", "PNLGRPNAME"):
            select_columns.append(f"ai.{col}")

    for col in class_columns:
        if col != "CLASSID":
            select_columns.append(f"cd.{col} as class_{col.lower()}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psauthitem ai
          {source["join"]}
          left join sysadm.psclassdefn cd
            on cd.classid = ai.classid
         where {source["where"]} = upper(:component)
         order by ai.classid
    """

    return query(env_name, sql, {"component": component})


def pages(env_name, q="", limit=100):
    limit = max(1, min(int(limit), 500))
    columns = select_existing_columns(
        env_name,
        "PSPNLDEFN",
        ["DESCR", "PNLTYPE", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["PNLNAME"],
    )
    searchable = [col for col in ("DESCR",) if col in columns]
    predicates = ["upper(pnlname) like :q"]
    predicates.extend(f"upper({col}) like :q" for col in searchable)

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspnldefn
         where {" or ".join(predicates)}
         order by pnlname
         fetch first {limit} rows only
    """

    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def page(env_name, page_name):
    columns = select_existing_columns(
        env_name,
        "PSPNLDEFN",
        ["DESCR", "PNLTYPE", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["PNLNAME"],
    )

    rows = query(env_name, f"""
        select {", ".join(columns)}
          from sysadm.pspnldefn
         where pnlname = upper(:page_name)
    """, {"page_name": page_name})

    return rows[0] if rows else None


def page_components(env_name, page_name):
    columns = select_existing_columns(
        env_name,
        "PSPNLGROUP",
        ["MARKET", "ITEMNUM", "PNLGRPITEMTYPE"],
        required=["PNLGRPNAME", "PNLNAME"],
    )

    order_columns = ["itemnum"] if "ITEMNUM" in columns else []
    order_columns.append("pnlgrpname")

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspnlgroup
         where pnlname = upper(:page_name)
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, {"page_name": page_name})


def page_fields(env_name, page_name):
    columns = select_existing_columns(
        env_name,
        "PSPNLFIELD",
        [
            "FIELDNUM",
            "RECNAME",
            "FIELDNAME",
            "LBLTEXT",
            "LEVELNUM",
            "OCCURSLEVEL",
            "PNLFIELDNAME",
            "FIELDTYPE",
            "REQUIRED",
            "INVISIBLE",
            "DISPLAYONLY",
            "USEEDIT",
            "PROMPTTABLE",
            "SUBPNLNAME",
            "ASSOCFIELDNUM",
        ],
        required=["PNLNAME"],
    )

    order_columns = []
    for col in ("LEVELNUM", "OCCURSLEVEL", "FIELDNUM", "RECNAME", "FIELDNAME"):
        if col in columns:
            order_columns.append(col)

    if not order_columns:
        order_columns.append("PNLNAME")

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspnlfield
         where pnlname = upper(:page_name)
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, {"page_name": page_name})


def page_records(env_name, page_name):
    rows = page_fields(env_name, page_name)
    records = {}

    for row in rows:
        recname = row.get("recname")

        if not recname:
            continue

        usage = set(records.setdefault(recname, {
            "recname": recname,
            "field_count": 0,
            "usage": set(),
        })["usage"])

        records[recname]["field_count"] += 1

        field_type = str(row.get("fieldtype") or "").upper()
        level = row.get("levelnum") or row.get("occurslevel")

        if recname.startswith("DERIVED") or recname.startswith("WORK") or recname.endswith("_WRK"):
            usage.add("derived/work")
        elif level not in (None, 0, "0"):
            usage.add(f"level {level}")
        else:
            usage.add("level 0")

        if row.get("prompttable"):
            usage.add("prompt source")

        if "GRID" in field_type:
            usage.add("grid")
        elif "SUB" in field_type:
            usage.add("subpage")
        elif "SCROLL" in field_type:
            usage.add("scroll")

        records[recname]["usage"] = usage

    return [
        {
            **record,
            "usage": sorted(record["usage"]),
        }
        for record in sorted(records.values(), key=lambda item: item["recname"])
    ]


def page_scroll_structure(env_name, page_name):
    rows = page_fields(env_name, page_name)
    structure = []

    for row in rows:
        field_type = str(row.get("fieldtype") or "").upper()
        level = row.get("levelnum") or row.get("occurslevel") or 0
        kind = "Field"

        if row.get("subpnlname") or "SUB" in field_type:
            kind = "Subpage"
        elif "GRID" in field_type:
            kind = "Grid"
        elif "SCROLL" in field_type:
            kind = "Scroll Area"

        structure.append({
            "level": level,
            "kind": kind,
            "recname": row.get("recname"),
            "fieldname": row.get("fieldname"),
            "pnlname": row.get("subpnlname") or row.get("pnlfieldname"),
            "label": row.get("lbltext"),
            "fieldnum": row.get("fieldnum"),
        })

    return structure


def page_grids(env_name, page_name):
    rows = page_scroll_structure(env_name, page_name)
    return [
        {
            "pnlname": page_name.upper(),
            "recname": row.get("recname"),
            "level": row.get("level"),
            "rowset": row.get("pnlname"),
            "related_record": row.get("recname"),
            "label": row.get("label"),
            "fieldnum": row.get("fieldnum"),
        }
        for row in rows
        if row.get("kind") == "Grid"
    ]


def page_subpages(env_name, page_name):
    rows = page_scroll_structure(env_name, page_name)
    return [
        {
            "pnlname": row.get("pnlname"),
            "parent_pnlname": page_name.upper(),
            "level": row.get("level"),
            "recname": row.get("recname"),
            "fieldname": row.get("fieldname"),
            "label": row.get("label"),
        }
        for row in rows
        if row.get("kind") == "Subpage" and row.get("pnlname")
    ]


def page_peoplecode_metadata(env_name, page_name):
    return component_optional_metadata(
        env_name,
        page_name,
        ["PSPCMPROG", "PSPCMPROGDEL", "PSPCMNAME"],
        ["PNLNAME", "OBJECTVALUE1", "OBJECTVALUE2", "OBJECTVALUE3", "PROGNAME"],
        [
            "OBJECTTYPE",
            "OBJECTVALUE1",
            "OBJECTVALUE2",
            "OBJECTVALUE3",
            "OBJECTVALUE4",
            "PROGNAME",
            "EVENTNAME",
            "LASTUPDDTTM",
            "LASTUPDOPRID",
        ],
    )


def page_related_content(env_name, page_name):
    return component_optional_metadata(
        env_name,
        page_name,
        ["PSRF_RINFO", "PSRF_RATTR", "PSRELCTNTDEFN", "PSPTCS_CONTENT"],
        ["PNLNAME", "PAGE", "PORTAL_OBJNAME", "CONTENT_REF", "SERVICEID", "OBJECTVALUE1", "OBJECTVALUE2"],
        ["PNLNAME", "PAGE", "PORTAL_OBJNAME", "CONTENT_REF", "SERVICEID", "DESCR", "LABEL", "OBJECTVALUE1", "OBJECTVALUE2"],
    )


def page_event_mapping(env_name, page_name):
    return component_optional_metadata(
        env_name,
        page_name,
        ["PSEMPMAPDEFN", "PSEMPMAPITEM", "PSEVTMAPDEFN", "PSEVTMAPITEM"],
        ["PNLNAME", "PAGE", "MAPNAME", "OBJECTVALUE1", "OBJECTVALUE2"],
        ["MAPNAME", "PNLNAME", "PAGE", "EVENTNAME", "OBJECTVALUE1", "OBJECTVALUE2", "DESCR"],
    )


def page_drop_zones(env_name, page_name):
    return component_optional_metadata(
        env_name,
        page_name,
        ["PSPTDZDEFN", "PSPTDZITEM", "PSPTDZCOMP", "PSPTDZPNL"],
        ["PNLNAME", "PAGE", "DZNAME", "OBJECTVALUE1", "OBJECTVALUE2"],
        ["DZNAME", "PNLNAME", "PAGE", "OBJECTVALUE1", "OBJECTVALUE2", "DESCR"],
    )


def page_transfers(env_name, page_name):
    return component_optional_metadata(
        env_name,
        page_name,
        ["PSPNLFIELD", "PSPNLFIELDLANG", "PSPNLFIELDDEFN"],
        ["PNLNAME", "FIELDNAME", "RECNAME", "DESTPNLGRPNAME", "MENUNAME", "TRANSFERNAME"],
        [
            "PNLNAME",
            "RECNAME",
            "FIELDNAME",
            "MENUNAME",
            "DESTPNLGRPNAME",
            "PNLGRPNAME",
            "TRANSFERNAME",
            "LBLTEXT",
        ],
    )


def role_users(env_name, rolename):
    columns = select_existing_columns(
        env_name,
        "PSROLEUSER",
        ["DYNAMIC_SW"],
        required=["ROLEUSER", "ROLENAME"],
    )

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psroleuser
         where upper(rolename) = upper(:rolename)
         order by roleuser
    """

    return query(env_name, sql, {"rolename": rolename})


def permissionlist_roles(env_name, classid):
    columns = select_existing_columns(
        env_name,
        "PSROLECLASS",
        ["DYNAMIC_SW", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["ROLENAME", "CLASSID"],
    )

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psroleclass
         where classid = upper(:classid)
         order by rolename
    """

    return query(env_name, sql, {"classid": classid})


def record_children(env_name, recname):
    columns = select_existing_columns(
        env_name,
        "PSRECDEFN",
        ["RECDESCR", "RECTYPE", "SQLTABLENAME"],
        required=["RECNAME", "PARENTRECNAME"],
    )

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psrecdefn
         where parentrecname = upper(:recname)
         order by recname
    """

    return query(env_name, sql, {"recname": recname})


def record_components(env_name, recname):
    columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "MARKET"],
        required=["PNLGRPNAME", "SEARCHRECNAME", "ADDSRCHRECNAME"],
    )

    sql = f"""
        select {", ".join(columns)}
          from sysadm.pspnlgrpdefn
         where searchrecname = upper(:recname)
            or addsearchrecname = upper(:recname)
         order by pnlgrpname
    """

    return query(env_name, sql, {"recname": recname})


def record_pages(env_name, recname):
    columns = select_existing_columns(
        env_name,
        "PSPNLFIELD",
        ["FIELDNUM", "FIELDNAME", "LBLTEXT"],
        required=["PNLNAME", "RECNAME"],
    )

    order_columns = ["pnlname"]
    if "FIELDNUM" in columns:
        order_columns.append("fieldnum")

    sql = f"""
        select distinct {", ".join(columns)}
          from sysadm.pspnlfield
         where recname = upper(:recname)
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, {"recname": recname})


def record_detail(env_name, recname):
    """Return a single PSRECDEFN row with derived metadata."""
    columns = select_existing_columns(
        env_name,
        "PSRECDEFN",
        ["RECDESCR", "RECTYPE", "SQLTABLENAME", "PARENTRECNAME",
         "SETCNTRLFLD", "FIELDCOUNT", "KEYCOUNT", "AUDITRECNAME",
         "OBJECTOWNERID", "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["RECNAME"],
    )
    sql = f"""
        SELECT {", ".join(columns)}
        FROM SYSADM.PSRECDEFN
        WHERE RECNAME = UPPER(:recname)
    """
    rows = query(env_name, sql, {"recname": recname})
    return rows[0] if rows else None


RECTYPE_LABELS = {
    0: "SQL Table",
    1: "SQL View",
    2: "Derived/Work",
    3: "SubRecord",
    5: "Dynamic View",
    6: "Query View",
    7: "Temporary Table",
}


def record_related(env_name, recname):
    """Return related records: parent, language variant, audit record, and views."""
    recname_upper = recname.upper()
    results = {
        "parent":   None,
        "lang":     None,
        "audit":    None,
        "views":    [],
    }

    # Parent record
    parent_rows = query(env_name, """
        SELECT r.RECNAME, r.RECTYPE, r.RECDESCR
        FROM SYSADM.PSRECDEFN r
        INNER JOIN SYSADM.PSRECDEFN child ON child.PARENTRECNAME = r.RECNAME
        WHERE child.RECNAME = :recname AND TRIM(r.RECNAME) IS NOT NULL
    """, {"recname": recname_upper})
    if parent_rows:
        results["parent"] = parent_rows[0]

    # Language variant (e.g. RECNAME_LANG)
    lang_rows = query(env_name, """
        SELECT RECNAME, RECTYPE, RECDESCR
        FROM SYSADM.PSRECDEFN
        WHERE RECNAME = :lang
    """, {"lang": recname_upper + "_LANG"})
    if lang_rows:
        results["lang"] = lang_rows[0]

    # Audit record from AUDITRECNAME column or _AUD suffix
    audit_rows = query(env_name, """
        SELECT r2.RECNAME, r2.RECTYPE, r2.RECDESCR
        FROM SYSADM.PSRECDEFN r1
        JOIN SYSADM.PSRECDEFN r2 ON r2.RECNAME = r1.AUDITRECNAME
        WHERE r1.RECNAME = :recname
          AND TRIM(r1.AUDITRECNAME) IS NOT NULL
    """, {"recname": recname_upper})
    if not audit_rows:
        audit_rows = query(env_name, """
            SELECT RECNAME, RECTYPE, RECDESCR
            FROM SYSADM.PSRECDEFN
            WHERE RECNAME = :aud
        """, {"aud": recname_upper + "_AUD"})
    if audit_rows:
        results["audit"] = audit_rows[0]

    # Views that share the same base table name (SQLTABLENAME or RECNAME)
    view_rows = query(env_name, """
        SELECT v.RECNAME, v.RECTYPE, v.RECDESCR
        FROM SYSADM.PSRECDEFN v
        WHERE v.RECTYPE IN (1, 5, 6)
          AND (
              v.SQLTABLENAME = :recname
              OR v.RECNAME LIKE :prefix
          )
          AND v.RECNAME != :recname
        ORDER BY v.RECTYPE, v.RECNAME
        FETCH FIRST 50 ROWS ONLY
    """, {
        "recname": recname_upper,
        "prefix": recname_upper + "%",
    })
    results["views"] = view_rows

    return results


def record_usages(env_name, recname):
    """Return usage references for a record: child records, AE state records, subrecord derivations."""
    recname_upper = recname.strip().upper()
    results = {"child_records": [], "ae_state_records": [], "subrecord_derivations": []}

    # Records with PARENTRECNAME = this record (derived / extension records)
    defn_cols = table_columns(env_name, "PSRECDEFN")
    if "parentrecname" in defn_cols:
        try:
            child_rows = query(env_name, """
                SELECT RECNAME, RECDESCR, RECTYPE, OBJECTOWNERID
                  FROM SYSADM.PSRECDEFN
                 WHERE PARENTRECNAME = :recname
                 ORDER BY RECNAME
                 FETCH FIRST 100 ROWS ONLY
            """, {"recname": recname_upper})
            results["child_records"] = [dict(r) for r in child_rows]
        except Exception:
            pass

    # AE programs that use this as a state record
    ae_cols = table_columns(env_name, "PSAEAPPLSTATE")
    if "ae_state_recname" in ae_cols:
        try:
            select_cols = [c.upper() for c in ["ae_applid", "ae_state_recname", "ae_default_state"] if c in ae_cols]
            ae_rows = query(env_name, f"""
                SELECT {", ".join(select_cols)}
                  FROM SYSADM.PSAEAPPLSTATE
                 WHERE UPPER(AE_STATE_RECNAME) = :recname
                 ORDER BY AE_APPLID
                 FETCH FIRST 100 ROWS ONLY
            """, {"recname": recname_upper})
            results["ae_state_records"] = [dict(r) for r in ae_rows]
        except Exception:
            pass

    # Records that pull fields from this record via subrecord inheritance (PSRECFIELD.DEFRECNAME)
    rec_fld_cols = table_columns(env_name, "PSRECFIELD")
    if "defrecname" in rec_fld_cols and "recname" in rec_fld_cols:
        try:
            sub_rows = query(env_name, """
                SELECT DISTINCT R.RECNAME, D.RECDESCR, D.RECTYPE
                  FROM SYSADM.PSRECFIELD R
                  JOIN SYSADM.PSRECDEFN D ON D.RECNAME = R.RECNAME
                 WHERE UPPER(R.DEFRECNAME) = :recname
                   AND R.RECNAME != :recname
                 ORDER BY R.RECNAME
                 FETCH FIRST 100 ROWS ONLY
            """, {"recname": recname_upper})
            results["subrecord_derivations"] = [dict(r) for r in sub_rows]
        except Exception:
            pass

    return results


def record_storage(env_name, recname):
    """Return Oracle table statistics from ALL_TABLES for a record's SQL table."""
    # Resolve SQL table name first.
    rec_rows = query(env_name, """
        SELECT NVL(TRIM(SQLTABLENAME), RECNAME) AS tbl
        FROM SYSADM.PSRECDEFN
        WHERE RECNAME = UPPER(:recname)
    """, {"recname": recname})
    if not rec_rows:
        return None

    tbl = (rec_rows[0].get("tbl") or recname).strip().upper()
    # PeopleSoft tables are prefixed with PS_ in Oracle.
    oracle_name = f"PS_{tbl}" if not tbl.startswith("PS") else tbl

    try:
        rows = query(env_name, """
            SELECT TABLE_NAME, NUM_ROWS, BLOCKS, AVG_ROW_LEN,
                   LAST_ANALYZED, PARTITIONED, COMPRESSION
            FROM ALL_TABLES
            WHERE TABLE_NAME = :tbl
              AND OWNER = 'SYSADM'
        """, {"tbl": oracle_name})
        return rows[0] if rows else None
    except Exception:
        return None


def operator_permissionlists(env_name, oprid):
    role_columns = select_existing_columns(
        env_name,
        "PSROLEUSER",
        ["DYNAMIC_SW"],
        required=["ROLEUSER", "ROLENAME"],
    )
    class_columns = select_existing_columns(
        env_name,
        "PSROLECLASS",
        ["DYNAMIC_SW"],
        required=["ROLENAME", "CLASSID"],
    )

    select_columns = ["ru.roleuser", "ru.rolename", "rc.classid"]

    for col in role_columns:
        if col not in ("ROLEUSER", "ROLENAME"):
            select_columns.append(f"ru.{col} as roleuser_{col.lower()}")

    for col in class_columns:
        if col not in ("ROLENAME", "CLASSID"):
            select_columns.append(f"rc.{col} as roleclass_{col.lower()}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psroleuser ru
          join sysadm.psroleclass rc
            on rc.rolename = ru.rolename
         where ru.roleuser = upper(:oprid)
         order by ru.rolename, rc.classid
    """

    return query(env_name, sql, {"oprid": oprid})


def operator_menus(env_name, oprid):
    auth_columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["BARNAME", "BARITEMNAME"],
        required=["CLASSID", "MENUNAME"],
    )

    select_columns = [
        "ru.roleuser",
        "ru.rolename",
        "rc.classid",
    ]

    for col in auth_columns:
        if col != "CLASSID":
            select_columns.append(f"ai.{col}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psroleuser ru
          join sysadm.psroleclass rc
            on rc.rolename = ru.rolename
          join sysadm.psauthitem ai
            on ai.classid = rc.classid
         where ru.roleuser = upper(:oprid)
           and ai.menuname is not null
         order by ai.menuname, ru.rolename, rc.classid
    """

    return query(env_name, sql, {"oprid": oprid})


def operator_components(env_name, oprid):
    source = auth_component_source(env_name)
    auth_columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["MENUNAME", "MARKET", "AUTHORIZEDACTIONS", "DISPLAYONLY", "PNLITEMNAME"],
        required=["CLASSID", source["column"]],
    )
    component_columns = select_existing_columns(
        env_name,
        "PSPNLGRPDEFN",
        ["DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME", "MARKET"],
        required=["PNLGRPNAME"],
    )

    select_columns = [
        "ru.roleuser",
        "ru.rolename",
        "rc.classid",
        f"{source['expr']} as pnlgrpname",
    ]

    for col in auth_columns:
        if col not in ("CLASSID", "PNLGRPNAME"):
            select_columns.append(f"ai.{col}")

    for col in component_columns:
        if col != "PNLGRPNAME":
            select_columns.append(f"pg.{col} as component_{col.lower()}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psroleuser ru
          join sysadm.psroleclass rc
            on rc.rolename = ru.rolename
          join sysadm.psauthitem ai
            on ai.classid = rc.classid
          {source["join"]}
          left join sysadm.pspnlgrpdefn pg
            on pg.pnlgrpname = {source["expr"]}
         where ru.roleuser = upper(:oprid)
           and {source["where"]} is not null
         order by {source["order"]}, ru.rolename, rc.classid
    """

    return with_decoded_actions(query(env_name, sql, {"oprid": oprid}))


def component_access(env_name, component):
    source = auth_component_source(env_name)
    auth_columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["MENUNAME", "MARKET", "AUTHORIZEDACTIONS", "DISPLAYONLY", "PNLITEMNAME"],
        required=["CLASSID", source["column"]],
    )

    select_columns = [
        f"{source['expr']} as pnlgrpname",
        "ai.classid",
        "rc.rolename",
        "ru.roleuser",
    ]

    for col in auth_columns:
        if col not in ("CLASSID", "PNLGRPNAME"):
            select_columns.append(f"ai.{col}")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psauthitem ai
          {source["join"]}
          left join sysadm.psroleclass rc
            on rc.classid = ai.classid
          left join sysadm.psroleuser ru
            on ru.rolename = rc.rolename
         where {source["where"]} = upper(:component)
         order by ai.classid, rc.rolename, ru.roleuser
    """

    return with_decoded_actions(query(env_name, sql, {"component": component}))


def explain_operator_component_access(env_name, oprid, component_name):
    oprid = oprid.upper()
    component_name = component_name.upper()
    warnings = []

    def load(label, fn, fallback):
        try:
            return fn()
        except Exception as exc:
            warnings.append(f"{label} unavailable: {exc}")
            return fallback

    operator = load("operator", lambda: operator_detail(env_name, oprid), None)
    component_row = load("component", lambda: component(env_name, component_name), None)
    roles = load("operator roles", lambda: operator_roles_full(env_name, oprid), [])
    operator_pls = load("operator permission lists", lambda: operator_permissionlists(env_name, oprid), [])
    component_pls = load("component permission lists", lambda: component_permissionlists(env_name, component_name), [])
    access = load("component access", lambda: component_access(env_name, component_name), [])

    role_names = sorted({row.get("rolename") for row in roles if row.get("rolename")})
    operator_classids = sorted({row.get("classid") for row in operator_pls if row.get("classid")})
    component_classids = sorted({row.get("classid") for row in component_pls if row.get("classid")})
    matching_classids = sorted(set(operator_classids) & set(component_classids))

    grant_paths = []
    for row in access:
        if str(row.get("roleuser") or "").upper() != oprid:
            continue
        item = dict(row)
        item["path"] = [
            {"type": "operator", "name": oprid},
            {"type": "role", "name": item.get("rolename")},
            {"type": "permissionlist", "name": item.get("classid")},
            {"type": "component", "name": item.get("pnlgrpname") or component_name},
        ]
        grant_paths.append(item)

    return {
        "env": env_name.upper(),
        "oprid": oprid,
        "component": component_name,
        "has_access": bool(grant_paths),
        "operator": operator,
        "component_row": component_row or {"pnlgrpname": component_name},
        "operator_roles": roles,
        "operator_permissionlists": operator_pls,
        "component_permissionlists": component_pls,
        "matching_permissionlists": matching_classids,
        "grant_paths": grant_paths,
        "counts": {
            "operator_roles": len(role_names),
            "operator_permissionlists": len(operator_classids),
            "component_permissionlists": len(component_classids),
            "matching_permissionlists": len(matching_classids),
            "grant_paths": len(grant_paths),
        },
        "explanation": (
            f"{oprid} has access to {component_name} through {len(grant_paths)} role/permission-list path(s)."
            if grant_paths else
            f"{oprid} does not have a visible role/permission-list path to {component_name}."
        ),
        "warnings": warnings,
    }


def explain_operator_page_access(env_name, oprid, page_name):
    oprid = oprid.upper()
    page_name = page_name.upper()
    warnings = []

    def load(label, fn, fallback):
        try:
            return fn()
        except Exception as exc:
            warnings.append(f"{label} unavailable: {exc}")
            return fallback

    page_row = load("page", lambda: page(env_name, page_name), None)
    components = load("page components", lambda: page_components(env_name, page_name), [])
    fields = load("page fields", lambda: page_fields(env_name, page_name), [])

    component_explanations = []
    grant_paths = []
    matching_components = []
    for row in components:
        component_name = row.get("pnlgrpname")
        if not component_name:
            continue
        explanation = explain_operator_component_access(env_name, oprid, component_name)
        explanation["page_component"] = row
        component_explanations.append(explanation)
        warnings.extend(explanation.get("warnings", []))
        if explanation.get("has_access"):
            matching_components.append(component_name)
            for path in explanation.get("grant_paths", []):
                item = dict(path)
                item["page"] = page_name
                item["path"] = (item.get("path") or []) + [{"type": "page", "name": page_name}]
                grant_paths.append(item)

    return {
        "env": env_name.upper(),
        "oprid": oprid,
        "page": page_name,
        "has_access": bool(grant_paths),
        "page_row": page_row or {"pnlname": page_name},
        "components": components,
        "fields": fields,
        "matching_components": sorted(set(matching_components)),
        "component_explanations": component_explanations,
        "grant_paths": grant_paths,
        "counts": {
            "components": len(components),
            "fields": len(fields),
            "visible_fields": sum(1 for row in fields if str(row.get("invisible") or "0").upper() not in {"1", "Y", "YES", "T", "TRUE"}),
            "invisible_fields": sum(1 for row in fields if str(row.get("invisible") or "0").upper() in {"1", "Y", "YES", "T", "TRUE"}),
            "display_only_fields": sum(1 for row in fields if str(row.get("displayonly") or "0").upper() in {"1", "Y", "YES", "T", "TRUE"}),
            "matching_components": len(set(matching_components)),
            "grant_paths": len(grant_paths),
        },
        "explanation": (
            f"{oprid} has access to page {page_name} through {len(set(matching_components))} component(s) and {len(grant_paths)} path(s)."
            if grant_paths else
            f"{oprid} does not have a visible component access path to page {page_name}."
        ),
        "warnings": sorted(set(warnings)),
    }


def explain_operator_menu_access(env_name, oprid, menu_name):
    oprid = oprid.upper()
    menu_name = menu_name.upper()
    warnings = []

    try:
        menus = operator_menus(env_name, oprid)
    except Exception as exc:
        menus = []
        warnings.append(f"operator menus unavailable: {exc}")

    grant_paths = []
    for row in menus:
        if str(row.get("menuname") or "").upper() != menu_name:
            continue
        item = dict(row)
        item["path"] = [
            {"type": "operator", "name": oprid},
            {"type": "role", "name": item.get("rolename")},
            {"type": "permissionlist", "name": item.get("classid")},
            {"type": "menu", "name": item.get("menuname")},
        ]
        grant_paths.append(item)

    return {
        "env": env_name.upper(),
        "oprid": oprid,
        "menu": menu_name,
        "has_access": bool(grant_paths),
        "grant_paths": grant_paths,
        "counts": {
            "grant_paths": len(grant_paths),
        },
        "explanation": (
            f"{oprid} has access to menu {menu_name} through {len(grant_paths)} role/permission-list path(s)."
            if grant_paths else
            f"{oprid} does not have a visible role/permission-list path to menu {menu_name}."
        ),
        "warnings": warnings,
    }


def decode_authorized_actions(value, display_only=None):
    actions = []

    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0

    flags = [
        (1, "Add"),
        (2, "Update/Display"),
        (4, "Update/Display All"),
        (8, "Correction"),
    ]

    for bit, label in flags:
        if number & bit:
            actions.append(label)

    if str(display_only or "").upper() in {"1", "Y", "YES", "T", "TRUE"}:
        actions.append("Display Only")

    return {
        "raw_authorizedactions": value,
        "raw_displayonly": display_only,
        "decoded_actions": actions,
    }


def with_decoded_actions(rows):
    enriched = []

    for row in rows:
        item = dict(row)
        action_info = decode_authorized_actions(
            item.get("authorizedactions"),
            item.get("displayonly"),
        )
        item.update(action_info)
        enriched.append(item)

    return enriched


def component_menu_placements(env_name, component):
    source = auth_component_source(env_name)
    columns = select_existing_columns(
        env_name,
        "PSAUTHITEM",
        ["MARKET", "BARNAME", "BARITEMNAME", "AUTHORIZEDACTIONS", "DISPLAYONLY", "PNLITEMNAME"],
        required=["MENUNAME", source["column"]],
    )

    select_columns = [col for col in columns if col != "PNLGRPNAME"]

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.psauthitem ai
          {source["join"]}
         where {source["where"]} = upper(:component)
           and ai.menuname is not null
         order by menuname
    """

    return with_decoded_actions(query(env_name, sql, {"component": component}))


def component_records_used_by_pages(env_name, component):
    group_columns = select_existing_columns(
        env_name,
        "PSPNLGROUP",
        ["MARKET", "ITEMNUM"],
        required=["PNLGRPNAME", "PNLNAME"],
    )
    field_columns = select_existing_columns(
        env_name,
        "PSPNLFIELD",
        ["FIELDNUM", "FIELDNAME", "LBLTEXT"],
        required=["PNLNAME", "RECNAME"],
    )

    select_columns = [
        "pg.pnlgrpname",
        "pg.pnlname",
        "pf.recname",
    ]

    for col in group_columns:
        if col not in ("PNLGRPNAME", "PNLNAME"):
            select_columns.append(f"pg.{col}")

    for col in field_columns:
        if col not in ("PNLNAME", "RECNAME"):
            select_columns.append(f"pf.{col}")

    order_columns = ["pg.pnlname"]
    if "FIELDNUM" in field_columns:
        order_columns.append("pf.fieldnum")
    order_columns.append("pf.recname")

    sql = f"""
        select distinct {", ".join(select_columns)}
          from sysadm.pspnlgroup pg
          join sysadm.pspnlfield pf
            on pf.pnlname = pg.pnlname
         where pg.pnlgrpname = upper(:component)
           and pf.recname is not null
         order by {", ".join(order_columns)}
    """

    return query(env_name, sql, {"component": component})


def component_portal_refs(env_name, component):
    columns = table_columns(env_name, "PSPRSMDEFN")

    if not columns:
        return []

    candidates = [
        "PORTAL_NAME",
        "PORTAL_OBJNAME",
        "PORTAL_LABEL",
        "PORTAL_PRNTOBJNAME",
        "PORTAL_URI_SEG1",
        "PORTAL_URI_SEG2",
        "PORTAL_URI_SEG3",
        "PORTAL_REFTYPE",
        "PORTAL_URLTEXT",
        "URL",
    ]
    selected = [col for col in candidates if col.lower() in columns]

    if not selected:
        return []

    search_columns = [
        col for col in selected
        if col.lower() in {
            "portal_objname",
            "portal_label",
            "portal_uri_seg1",
            "portal_uri_seg2",
            "portal_uri_seg3",
            "portal_urltext",
            "url",
        }
    ]

    if not search_columns:
        return []

    predicates = [f"upper({col}) like :component" for col in search_columns]

    sql = f"""
        select {", ".join(selected)}
          from sysadm.psprsmdefn
         where {" or ".join(predicates)}
         order by {selected[0]}
         fetch first 100 rows only
    """

    return query(env_name, sql, {"component": f"%{component.upper()}%"})


def _portal_registry_select_columns(env_name):
    columns = table_columns(env_name, "PSPRSMDEFN")

    if not columns:
        return []

    candidates = [
        "PORTAL_NAME",
        "PORTAL_OBJNAME",
        "PORTAL_LABEL",
        "DESCR254",
        "PORTAL_PRNTOBJNAME",
        "PORTAL_URI_SEG1",
        "PORTAL_URI_SEG2",
        "PORTAL_URI_SEG3",
        "PORTAL_URI_SEG4",
        "PORTAL_REFTYPE",
        "PORTAL_URLTEXT",
        "PORTAL_ISPUBLIC",
        "PORTAL_SEQ_NUM",
        "PORTAL_CREATION_DT",
        "PORTAL_EFFDT",
        "PORTAL_EXPIRE_DT",
        "FLUIDMODE",
        "OBJECTOWNERID",
        "LASTUPDDTTM",
        "LASTUPDOPRID",
        "VERSION",
    ]
    return [col for col in candidates if col.lower() in columns]


def portal_registry_ref(env_name, portal_objname, portal_name=None):
    selected = _portal_registry_select_columns(env_name)

    if not selected or "PORTAL_OBJNAME" not in selected:
        return None

    predicates = ["upper(portal_objname) = upper(:portal_objname)"]
    params = {"portal_objname": portal_objname}

    if portal_name and "PORTAL_NAME" in selected:
        predicates.append("upper(portal_name) = upper(:portal_name)")
        params["portal_name"] = portal_name

    sql = f"""
        select {", ".join(selected)}
          from sysadm.psprsmdefn
         where {" and ".join(predicates)}
         order by portal_name, portal_objname
         fetch first 1 rows only
    """

    rows = query(env_name, sql, params)
    return rows[0] if rows else None


def portal_registry_children(env_name, portal_objname, portal_name=None, limit=200):
    selected = _portal_registry_select_columns(env_name)

    if not selected or "PORTAL_PRNTOBJNAME" not in selected:
        return []

    limit = max(1, min(int(limit), 500))
    predicates = ["upper(portal_prntobjname) = upper(:portal_objname)"]
    params = {"portal_objname": portal_objname}

    if portal_name and "PORTAL_NAME" in selected:
        predicates.append("upper(portal_name) = upper(:portal_name)")
        params["portal_name"] = portal_name

    order_columns = []
    if "PORTAL_SEQ_NUM" in {col.upper() for col in selected}:
        order_columns.append("portal_seq_num")
    order_columns.extend(["portal_label", "portal_objname"])

    sql = f"""
        select {", ".join(selected)}
          from sysadm.psprsmdefn
         where {" and ".join(predicates)}
         order by {", ".join(order_columns)}
         fetch first {limit} rows only
    """

    return query(env_name, sql, params)


def portal_registry_parent(env_name, portal_row):
    parent = (portal_row or {}).get("portal_prntobjname")

    if not parent:
        return None

    return portal_registry_ref(env_name, parent, (portal_row or {}).get("portal_name"))


def portal_registry_breadcrumbs(env_name, portal_objname, portal_name=None, max_depth=12):
    chain = []
    seen = set()
    current = portal_registry_ref(env_name, portal_objname, portal_name)

    for _ in range(max_depth):
        if not current:
            break

        key = (
            str(current.get("portal_name") or "").upper(),
            str(current.get("portal_objname") or "").upper(),
        )
        if key in seen:
            break

        seen.add(key)
        chain.append(current)

        parent = current.get("portal_prntobjname")
        if not parent:
            break

        current = portal_registry_ref(env_name, parent, current.get("portal_name"))

    return list(reversed(chain))


def portal_registry_component_targets(env_name, portal_row):
    target = portal_row or {}
    component_name = (target.get("portal_uri_seg2") or "").strip()
    menu = (target.get("portal_uri_seg1") or "").strip()
    market = (target.get("portal_uri_seg3") or "").strip()

    if not component_name:
        return []

    rows = []
    try:
        component_row = component(env_name, component_name)
        if component_row:
            rows.append({
                "pnlgrpname": component_name,
                "market": market,
                "menu": menu,
                "portal_objname": target.get("portal_objname"),
                **component_row,
            })
    except Exception:
        rows.append({
            "pnlgrpname": component_name,
            "market": market,
            "menu": menu,
            "portal_objname": target.get("portal_objname"),
        })

    return rows


PORTAL_REFTYPE_LABELS = {
    "C": "Content Reference",
    "F": "Folder",
}

PORTAL_PERMTYPE_LABELS = {
    "P": "Permission List",
    "R": "Role",
}


def decode_portal_registry_row(row):
    item = dict(row or {})
    reftype = str(item.get("portal_reftype") or "").strip().upper()
    permtype = str(item.get("portal_permtype") or "").strip().upper()

    if reftype:
        item["portal_reftype_label"] = PORTAL_REFTYPE_LABELS.get(reftype, f"Type {reftype}")
    if permtype:
        item["portal_permtype_label"] = PORTAL_PERMTYPE_LABELS.get(permtype, f"Type {permtype}")
    if permtype == "P" and item.get("portal_permname"):
        item["classid"] = item["portal_permname"]
    if permtype == "R" and item.get("portal_permname"):
        item["rolename"] = item["portal_permname"]

    return item


def portal_registry_attributes(env_name, portal_objname, portal_name=None):
    columns = select_existing_columns(
        env_name,
        "PSPRSMATTR",
        ["PORTAL_REFTYPE", "PORTAL_ATTR_NAM", "PORTAL_ATTR_NMDSPL"],
        required=["PORTAL_NAME", "PORTAL_OBJNAME"],
    )

    predicates = ["upper(portal_objname) = upper(:portal_objname)"]
    params = {"portal_objname": portal_objname}

    if portal_name:
        predicates.append("upper(portal_name) = upper(:portal_name)")
        params["portal_name"] = portal_name

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psprsmattr
         where {" and ".join(predicates)}
         order by portal_attr_nam
    """

    return [decode_portal_registry_row(row) for row in query(env_name, sql, params)]


def portal_registry_permissions(env_name, portal_objname, portal_name=None, include_inherited=True):
    columns = select_existing_columns(
        env_name,
        "PSPRSMPERM",
        ["PORTAL_REFTYPE", "PORTAL_PERMNAME", "PORTAL_PERMTYPE", "PORTAL_ISCASCADE"],
        required=["PORTAL_NAME", "PORTAL_OBJNAME"],
    )

    target = portal_objname.upper()
    if include_inherited:
        refs = portal_registry_breadcrumbs(env_name, portal_objname, portal_name)
        object_names = [
            str(row.get("portal_objname") or "").upper()
            for row in refs
            if row.get("portal_objname")
        ]
    else:
        object_names = [target]

    if target not in object_names:
        object_names.append(target)

    object_names = list(dict.fromkeys(object_names))
    binds = {f"obj{i}": name for i, name in enumerate(object_names)}
    placeholders = ", ".join(f":obj{i}" for i in range(len(object_names)))
    predicates = [f"upper(portal_objname) in ({placeholders})"]
    params = dict(binds)

    if portal_name:
        predicates.append("upper(portal_name) = upper(:portal_name)")
        params["portal_name"] = portal_name

    sql = f"""
        select {", ".join(columns)}
          from sysadm.psprsmperm
         where {" and ".join(predicates)}
         order by portal_objname, portal_permtype, portal_permname
    """

    rows = []
    for row in query(env_name, sql, params):
        item = decode_portal_registry_row(row)
        source = str(item.get("portal_objname") or "").upper()
        cascades = str(item.get("portal_iscascade") or "0").upper() in {"1", "Y", "YES", "T", "TRUE"}
        inherited = source != target

        if inherited and not cascades:
            continue

        item["target_portal_objname"] = target
        item["inherited"] = inherited
        if inherited:
            item["inherited_from"] = source
        rows.append(item)

    return rows


def portal_registry_access(env_name, portal_objname, portal_name=None, max_paths=500):
    permissions = portal_registry_permissions(env_name, portal_objname, portal_name)
    paths = []
    role_cache = {}
    user_cache = {}

    def users_for_role(role):
        role = role.upper()
        if role not in user_cache:
            user_cache[role] = role_users(env_name, role)
        return user_cache[role]

    for grant in permissions:
        permtype = str(grant.get("portal_permtype") or "").upper()
        permname = str(grant.get("portal_permname") or "").upper()

        if not permname:
            continue

        if permtype == "P":
            if permname not in role_cache:
                role_cache[permname] = permissionlist_roles(env_name, permname)

            for role_row in role_cache[permname]:
                rolename = role_row.get("rolename")
                if not rolename:
                    continue
                for user_row in users_for_role(rolename):
                    paths.append({
                        **grant,
                        "classid": permname,
                        "rolename": rolename,
                        "roleuser": user_row.get("roleuser"),
                        "path_type": "permissionlist_role_operator",
                    })
                    if len(paths) >= max_paths:
                        return paths

        elif permtype == "R":
            for user_row in users_for_role(permname):
                paths.append({
                    **grant,
                    "rolename": permname,
                    "roleuser": user_row.get("roleuser"),
                    "path_type": "role_operator",
                })
                if len(paths) >= max_paths:
                    return paths

    return paths


def explain_operator_portal_access(env_name, oprid, portal_objname):
    oprid = oprid.upper()
    portal_objname = portal_objname.upper()
    warnings = []

    def load(label, fn, fallback):
        try:
            return fn()
        except Exception as exc:
            warnings.append(f"{label} unavailable: {exc}")
            return fallback

    portal_row = load("portal registry", lambda: portal_registry_ref(env_name, portal_objname), None)
    operator = load("operator", lambda: operator_detail(env_name, oprid), None)
    operator_roles = load("operator roles", lambda: oprid_roles(oprid, env_name, columns="summary"), [])
    operator_pls = load("operator permission lists", lambda: operator_permissionlists(env_name, oprid), [])
    portal_permissions = load(
        "portal permissions",
        lambda: portal_registry_permissions(env_name, portal_objname, (portal_row or {}).get("portal_name")),
        [],
    )

    role_names = {str(row.get("rolename") or "").upper() for row in operator_roles}
    classids = {str(row.get("classid") or "").upper() for row in operator_pls}
    grant_paths = []

    for grant in portal_permissions:
        permtype = str(grant.get("portal_permtype") or "").upper()
        permname = str(grant.get("portal_permname") or "").upper()

        if permtype == "P" and permname in classids:
            grant_paths.append({
                **grant,
                "classid": permname,
                "roleuser": oprid,
                "matched_by": "permissionlist",
            })
        elif permtype == "R" and permname in role_names:
            grant_paths.append({
                **grant,
                "rolename": permname,
                "roleuser": oprid,
                "matched_by": "role",
            })

    return {
        "oprid": oprid,
        "portal_objname": portal_objname,
        "has_access": bool(grant_paths),
        "operator": operator,
        "portal_row": decode_portal_registry_row(portal_row) if portal_row else None,
        "operator_roles": operator_roles,
        "operator_permissionlists": operator_pls,
        "portal_permissions": portal_permissions,
        "grant_paths": grant_paths,
        "warnings": warnings,
    }


def component_optional_metadata(env_name, component, table_names, search_candidates, label_candidates):
    results = []

    for table_name in table_names:
        columns = table_columns(env_name, table_name)

        if not columns:
            continue

        selected = [
            col for col in label_candidates
            if col.lower() in columns
        ]
        search_columns = [
            col for col in search_candidates
            if col.lower() in columns
        ]

        if not selected or not search_columns:
            continue

        predicates = [f"upper({col}) like :component" for col in search_columns]

        sql = f"""
            select {", ".join(selected)}
              from sysadm.{table_name}
             where {" or ".join(predicates)}
             fetch first 100 rows only
        """

        for row in query(env_name, sql, {"component": f"%{component.upper()}%"}):
            item = {"metadata_table": table_name}
            item.update(row)
            results.append(item)

    return results


def component_related_content(env_name, component):
    return component_optional_metadata(
        env_name,
        component,
        ["PSRF_RINFO", "PSRF_RATTR", "PSRELCTNTDEFN", "PSPTCS_CONTENT"],
        ["PNLGRPNAME", "COMPONENT", "PORTAL_OBJNAME", "CONTENT_REF", "SERVICEID"],
        ["PNLGRPNAME", "COMPONENT", "PORTAL_OBJNAME", "CONTENT_REF", "SERVICEID", "DESCR", "LABEL"],
    )


def component_event_mapping(env_name, component):
    return component_optional_metadata(
        env_name,
        component,
        ["PSEMPMAPDEFN", "PSEMPMAPITEM", "PSEVTMAPDEFN", "PSEVTMAPITEM"],
        ["PNLGRPNAME", "COMPONENT", "MAPNAME", "OBJECTVALUE1", "OBJECTVALUE2"],
        ["MAPNAME", "PNLGRPNAME", "COMPONENT", "EVENTNAME", "OBJECTVALUE1", "OBJECTVALUE2", "DESCR"],
    )


def component_drop_zones(env_name, component):
    return component_optional_metadata(
        env_name,
        component,
        ["PSPTDZDEFN", "PSPTDZITEM", "PSPTDZCOMP", "PSPTDZPNL"],
        ["PNLGRPNAME", "COMPONENT", "DZNAME", "OBJECTVALUE1", "OBJECTVALUE2"],
        ["DZNAME", "PNLGRPNAME", "COMPONENT", "PNLNAME", "OBJECTVALUE1", "OBJECTVALUE2", "DESCR"],
    )


def global_search(env_name, q, limit=20):
    limit = max(1, min(int(limit), 50))
    pattern = f"%{q.upper()}%"
    results = []

    specs = [
        ("operator", "PSOPRDEFN", "OPRID", ["OPRDEFNDESC"], ["OPRDEFNDESC"]),
        ("role", "PSROLEDEFN", "ROLENAME", ["DESCR"], ["DESCR"]),
        ("permissionlist", "PSCLASSDEFN", "CLASSID", ["DESCR", "CLASSDEFNDESC"], ["DESCR", "CLASSDEFNDESC"]),
        ("component", "PSPNLGRPDEFN", "PNLGRPNAME", ["DESCR"], ["DESCR", "SEARCHRECNAME", "ADDSRCHRECNAME"]),
        ("page", "PSPNLDEFN", "PNLNAME", ["DESCR"], ["DESCR"]),
        ("record", "PSRECDEFN", "RECNAME", ["RECDESCR"], ["RECDESCR", "SQLTABLENAME"]),
    ]

    for object_type, table_name, name_col, description_candidates, search_candidates in specs:
        try:
            columns = select_existing_columns(
                env_name,
                table_name,
                description_candidates + search_candidates,
                required=[name_col],
            )

            descriptions = [
                col for col in description_candidates
                if col.lower() in {existing.lower() for existing in columns}
            ]
            searches = [
                col for col in search_candidates
                if col.lower() in {existing.lower() for existing in columns}
            ]

            description_expr = descriptions[0] if descriptions else "null"
            predicates = [f"upper({name_col}) like :pattern"]
            predicates.extend(f"upper({col}) like :pattern" for col in searches)

            sql = f"""
                select {name_col} as name,
                       {description_expr} as description
                  from sysadm.{table_name}
                 where {" or ".join(predicates)}
                 order by {name_col}
                 fetch first {limit} rows only
            """

            for row in query(env_name, sql, {"pattern": pattern}):
                name = row["name"]
                description = row.get("description")
                name_upper = str(name or "").upper()
                description_upper = str(description or "").upper()
                score = 10

                if name_upper == q.upper():
                    score += 100
                elif name_upper.startswith(q.upper()):
                    score += 50

                if object_type == "page":
                    score += 8

                if q.upper() in description_upper:
                    score += 5

                results.append({
                    "type": object_type,
                    "name": name,
                    "description": description,
                    "score": score,
                })
        except Exception as exc:
            results.append({
                "type": object_type,
                "name": None,
                "description": f"Search failed: {exc}",
                "error": True,
            })

    return sorted(
        results,
        key=lambda item: (
            item.get("error", False),
            -item.get("score", 0),
            item.get("type") or "",
            item.get("name") or "",
        ),
    )


# ── Field Explorer ───────────────────────────────────────────────────────────

FIELDTYPE_LABELS = {
    0:  "Character",
    1:  "Long Character",
    2:  "Number",
    3:  "Signed Number",
    4:  "Date",
    5:  "Time",
    6:  "DateTime",
    8:  "Image",
    9:  "ImageReference",
}


def search_fields_distinct(env_name, q="", limit=100):
    """Return unique field names with record-usage count, ordered by relevance."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"

    # Only join PSDBFIELD if it's actually accessible (table_columns returns non-empty)
    psdbfield_available = bool(table_columns(env_name, "PSDBFIELD"))
    if psdbfield_available:
        db_cols = ["DESCR", "FIELDTYPE", "LENGTH"]
        db_sel = ", ".join(f"d.{c} as db_{c.lower()}" for c in db_cols)
        db_join = "LEFT JOIN SYSADM.PSDBFIELD d ON d.FIELDNAME = r.FIELDNAME"
        group_extra = ", " + ", ".join(f"d.{c}" for c in db_cols)
    else:
        db_cols = []
        db_sel = "NULL as db_descr, NULL as db_fieldtype, NULL as db_length"
        db_join = ""
        group_extra = ""

    sql = f"""
        SELECT * FROM (
            SELECT
                r.FIELDNAME,
                COUNT(*) AS RECORD_COUNT,
                {db_sel}
            FROM SYSADM.PSRECFIELD r
            {db_join}
            WHERE UPPER(r.FIELDNAME) LIKE :pattern
            GROUP BY r.FIELDNAME{group_extra}
            ORDER BY
                CASE WHEN UPPER(r.FIELDNAME) = UPPER(:exact) THEN 0 ELSE 1 END,
                COUNT(*) DESC,
                r.FIELDNAME
        ) WHERE ROWNUM <= {limit}
    """
    return query(env_name, sql, {"pattern": pattern, "exact": q.upper() or ""})


def field_record_summary(env_name, fieldname):
    """Return all records that use a given field, with record type and key position."""
    rec_cols = select_existing_columns(
        env_name, "PSRECFIELD",
        ["FIELDNUM", "USEEDIT", "EDITTABLE"],
        required=["RECNAME", "FIELDNAME"],
    )
    # PSRECDEFN is accessible — guard with table_columns check to be safe
    psrecdefn_cols = table_columns(env_name, "PSRECDEFN")
    want_def = ["RECDESCR", "RECTYPE"]
    available_def = [c for c in want_def if c.lower() in psrecdefn_cols]

    rec_sel = ", ".join(f"rf.{c} as {c.lower()}" for c in rec_cols if c not in ("RECNAME", "FIELDNAME"))
    if available_def:
        def_sel = ", ".join(f"d.{c} as {c.lower()}" for c in available_def)
        def_join = "LEFT JOIN SYSADM.PSRECDEFN d ON d.RECNAME = rf.RECNAME"
    else:
        def_sel = "NULL as recdescr, NULL as rectype"
        def_join = ""

    sql = f"""
        SELECT rf.RECNAME, rf.FIELDNAME,
               {rec_sel + ', ' if rec_sel else ''}{def_sel}
          FROM SYSADM.PSRECFIELD rf
          {def_join}
         WHERE UPPER(rf.FIELDNAME) = UPPER(:fieldname)
         ORDER BY rf.RECNAME
    """
    rows = query(env_name, sql, {"fieldname": fieldname})
    for r in rows:
        rt = r.get("rectype")
        r["rectype_label"] = RECTYPE_LABELS.get(int(rt) if rt is not None else -1, str(rt))
        ue = int(r.get("useedit") or 0)
        r["is_key"] = bool(ue & 1)
        r["is_search_key"] = bool(ue & 2048)
        r["is_required"] = bool(ue & 1)
    return rows


# ── Operator Explorer ────────────────────────────────────────────────────────

ACCTLOCK_LABELS = {0: "Active", 1: "Locked"}
OPRTYPE_LABELS  = {0: "User", 1: "Worklist Routing", 2: "Role", 3: "Membership List"}


_SQL_TYPE_LABELS = {
    0: "Standalone SQL",
    1: "AE SQL Action",
    2: "AE PeopleCode SQL",
    6: "Trigger",
}


def search_sql_definitions(env_name, q="", sqltype=None, limit=100):
    """Search PSSQLDEFN by SQLID, with optional SQLTYPE filter.

    sqltype: None = all types, 0 = standalone, 1 = AE SQL, 2 = PeopleCode SQL, 6 = Trigger.
    """
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%" if q else "%"

    cols = table_columns(env_name, "PSSQLDEFN")
    if not cols:
        return []

    select_cols = [c.upper() for c in
                   ["SQLID", "SQLTYPE", "OBJECTOWNERID", "VERSION", "LASTUPDDTTM", "LASTUPDOPRID"]
                   if c.lower() in cols]
    if not select_cols or "SQLID" not in select_cols:
        return []

    type_clause = ""
    params = {"pattern": pattern, "exact": q.upper() or ""}
    if sqltype is not None:
        try:
            type_clause = "AND SQLTYPE = :sqltype"
            params["sqltype"] = int(sqltype)
        except (TypeError, ValueError):
            pass

    sql = f"""
        SELECT * FROM (
            SELECT {", ".join(select_cols)}
              FROM SYSADM.PSSQLDEFN
             WHERE UPPER(SQLID) LIKE :pattern
               {type_clause}
             ORDER BY
                CASE WHEN UPPER(SQLID) = UPPER(:exact) THEN 0 ELSE 1 END,
                SQLID
        ) WHERE ROWNUM <= {limit}
    """
    rows = query(env_name, sql, params)
    result = []
    for r in rows:
        item = dict(r)
        st = item.get("sqltype")
        item["sqltype_label"] = _SQL_TYPE_LABELS.get(int(st) if st is not None else -1, f"Type {st}")
        result.append(item)
    return result


def search_operators(env_name, q="", limit=100):
    """Search PSOPRDEFN by OPRID, name, or email."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"

    cols = select_existing_columns(
        env_name, "PSOPRDEFN",
        ["OPRDEFNDESC", "EMPLID", "EMAILID", "ACCTLOCK", "LASTSIGNONDTTM", "FAILEDLOGINS"],
        required=["OPRID"],
    )
    col_sel = ", ".join(c for c in cols)

    email_pred = "OR UPPER(EMAILID) LIKE :pattern" if "EMAILID" in cols else ""
    desc_pred  = "OR UPPER(OPRDEFNDESC) LIKE :pattern" if "OPRDEFNDESC" in cols else ""

    sql = f"""
        SELECT * FROM (
            SELECT {col_sel}
              FROM SYSADM.PSOPRDEFN
             WHERE UPPER(OPRID) LIKE :pattern
               {desc_pred}
               {email_pred}
             ORDER BY
                CASE WHEN UPPER(OPRID) = UPPER(:exact) THEN 0 ELSE 1 END,
                OPRID
        ) WHERE ROWNUM <= {limit}
    """
    rows = query(env_name, sql, {"pattern": pattern, "exact": q.upper() or ""})
    for r in rows:
        al = r.get("acctlock")
        r["acctlock_label"] = ACCTLOCK_LABELS.get(int(al) if al is not None else 0, str(al))
    return rows


def operator_detail(env_name, oprid_val):
    """Return full PSOPRDEFN row for a single operator."""
    cols = select_existing_columns(
        env_name, "PSOPRDEFN",
        ["USERIDALIAS", "VERSION", "OPRDEFNDESC", "EMPLID", "EMAILID", "OPRCLASS",
         "ROWSECCLASS", "LANGUAGE_CD", "MULTILANG", "CURRENCY_CD", "LASTPSWDCHANGE",
         "ACCTLOCK", "PRCSPRFLCLS", "DEFAULTNAVHP", "FAILEDLOGINS", "EXPENT",
         "OPRTYPE", "LASTSIGNONDTTM", "LASTUPDDTTM", "LASTUPDOPRID",
         "PTALLOWSWITCHUSER", "PTACCTLOCKDATE", "PTACCTNEVERLOCK"],
        required=["OPRID"],
    )
    col_sel = ", ".join(c for c in cols)
    rows = query(env_name, f"""
        SELECT {col_sel}
          FROM SYSADM.PSOPRDEFN
         WHERE UPPER(OPRID) = UPPER(:oprid)
    """, {"oprid": oprid_val})
    if not rows:
        return None
    r = rows[0]
    al = r.get("acctlock")
    ot = r.get("oprtype")
    r["acctlock_label"] = ACCTLOCK_LABELS.get(int(al) if al is not None else 0, str(al))
    r["oprtype_label"]  = OPRTYPE_LABELS.get(int(ot) if ot is not None else 0, str(ot))
    return r


def operator_roles_full(env_name, oprid_val):
    """Return all roles assigned to an operator with role metadata."""
    cols = select_existing_columns(
        env_name, "PSROLEUSER", ["DYNAMIC_SW"], required=["ROLEUSER", "ROLENAME"],
    )
    rd_cols = select_existing_columns(
        env_name, "PSROLEDEFN", ["DESCR", "ROLESTATUS", "ROLETYPE"], required=["ROLENAME"],
    )
    ru_sel = ", ".join(f"ru.{c} as {c.lower()}" for c in cols if c not in ("ROLEUSER", "ROLENAME"))
    rd_sel = ", ".join(f"rd.{c} as {c.lower()}" for c in rd_cols if c != "ROLENAME")
    rd_join = "LEFT JOIN SYSADM.PSROLEDEFN rd ON rd.ROLENAME = ru.ROLENAME" if rd_cols else ""
    if not rd_sel:
        rd_sel = "NULL as descr"
    sql = f"""
        SELECT ru.ROLEUSER, ru.ROLENAME, {ru_sel + ', ' if ru_sel else ''}{rd_sel}
          FROM SYSADM.PSROLEUSER ru
          {rd_join}
         WHERE UPPER(ru.ROLEUSER) = UPPER(:oprid)
         ORDER BY ru.ROLENAME
    """
    rows = query(env_name, sql, {"oprid": oprid_val})
    for r in rows:
        rt = str(r.get("roletype") or "").strip()
        rs = str(r.get("rolestatus") or "").strip()
        r["roletype_label"]  = ROLETYPE_LABELS.get(rt, rt or "General")
        r["rolestatus_label"] = ROLESTATUS_LABELS.get(rs, rs)
    return rows


# ── Role Explorer ────────────────────────────────────────────────────────────

ROLETYPE_LABELS = {
    "U": "General",
    "Q": "Query-Based (Dynamic)",
    "P": "PeopleCode-Based (Dynamic)",
    "L": "LDAP-Based (Dynamic)",
}

ROLESTATUS_LABELS = {
    "A": "Active",
    "I": "Inactive",
}


def search_roles_with_count(env_name, q="", limit=100):
    """Search PSROLEDEFN; join PSROLEUSER member count when accessible."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%"

    rd_cols = select_existing_columns(
        env_name, "PSROLEDEFN",
        ["DESCR", "ROLETYPE", "ROLESTATUS", "LASTUPDDTTM"],
        required=["ROLENAME"],
    )
    rd_sel = ", ".join(f"r.{c} as {c.lower()}" for c in rd_cols if c != "ROLENAME")

    has_roleuser = bool(table_columns(env_name, "PSROLEUSER"))
    if has_roleuser:
        member_sel = "NVL(m.MEMBER_COUNT, 0) AS member_count"
        member_join = """
            LEFT JOIN (
                SELECT ROLENAME, COUNT(*) AS MEMBER_COUNT
                  FROM SYSADM.PSROLEUSER
                 GROUP BY ROLENAME
            ) m ON m.ROLENAME = r.ROLENAME"""
    else:
        member_sel = "NULL AS member_count"
        member_join = ""

    sql = f"""
        SELECT * FROM (
            SELECT r.ROLENAME, {rd_sel}, {member_sel}
              FROM SYSADM.PSROLEDEFN r
              {member_join}
             WHERE UPPER(r.ROLENAME) LIKE :pattern
                OR UPPER(r.DESCR) LIKE :pattern
             ORDER BY
                CASE WHEN UPPER(r.ROLENAME) = UPPER(:exact) THEN 0 ELSE 1 END,
                NVL(m.MEMBER_COUNT, 0) DESC,
                r.ROLENAME
        ) WHERE ROWNUM <= {limit}
    """ if has_roleuser else f"""
        SELECT * FROM (
            SELECT r.ROLENAME, {rd_sel}, NULL AS member_count
              FROM SYSADM.PSROLEDEFN r
             WHERE UPPER(r.ROLENAME) LIKE :pattern
                OR UPPER(r.DESCR) LIKE :pattern
             ORDER BY
                CASE WHEN UPPER(r.ROLENAME) = UPPER(:exact) THEN 0 ELSE 1 END,
                r.ROLENAME
        ) WHERE ROWNUM <= {limit}
    """
    rows = query(env_name, sql, {"pattern": pattern, "exact": q.upper() or ""})
    for r in rows:
        rt = str(r.get("roletype") or "").strip()
        rs = str(r.get("rolestatus") or "").strip()
        r["roletype_label"] = ROLETYPE_LABELS.get(rt, rt or "General")
        r["rolestatus_label"] = ROLESTATUS_LABELS.get(rs, rs)
    return rows


def role_detail(env_name, rolename):
    """Return full PSROLEDEFN row for a single role."""
    rd_cols = select_existing_columns(
        env_name, "PSROLEDEFN",
        ["DESCR", "ROLETYPE", "ROLESTATUS", "QRYNAME", "RECNAME", "FIELDNAME",
         "PC_EVENT_TYPE", "QRYNAME_SEC", "PC_FUNCTION_NAME",
         "ROLE_QUERY_RULE_ON", "ROLE_PCODE_RULE_ON", "LDAP_RULE_ON",
         "ALLOWNOTIFY", "ALLOWLOOKUP", "LASTUPDDTTM", "LASTUPDOPRID", "DESCRLONG"],
        required=["ROLENAME"],
    )
    rd_sel = ", ".join(c for c in rd_cols)
    rows = query(env_name, f"""
        SELECT {rd_sel}
          FROM SYSADM.PSROLEDEFN
         WHERE UPPER(ROLENAME) = UPPER(:rolename)
    """, {"rolename": rolename})
    if not rows:
        return None
    row = rows[0]
    rt = str(row.get("roletype") or "").strip()
    rs = str(row.get("rolestatus") or "").strip()
    row["roletype_label"] = ROLETYPE_LABELS.get(rt, rt or "General")
    row["rolestatus_label"] = ROLESTATUS_LABELS.get(rs, rs)
    return row


def security_report(env_name, report_type, limit=100):
    """Run a canned security audit report and return {title, columns, rows, note}."""
    REPORTS = {
        "empty_roles": {
            "title": "Roles with No Users",
            "note": "Roles defined in PSROLEDEFN with zero entries in PSROLEUSER — candidates for cleanup.",
            "sql": """
                SELECT R.ROLENAME, R.DESCR, COUNT(U.ROLEUSER) AS USER_COUNT
                  FROM SYSADM.PSROLEDEFN R
                  LEFT JOIN SYSADM.PSROLEUSER U ON U.ROLENAME = R.ROLENAME
                 GROUP BY R.ROLENAME, R.DESCR
                HAVING COUNT(U.ROLEUSER) = 0
                 ORDER BY R.ROLENAME
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["rolename", "descr", "user_count"],
        },
        "unused_permission_lists": {
            "title": "Permission Lists Not Assigned to Any Role",
            "note": "PSCLASSDEFN entries with no rows in PSROLECLASS — may be orphaned.",
            "sql": """
                SELECT C.CLASSID, C.CLASSDEFNDESC, COUNT(R.ROLENAME) AS ROLE_COUNT
                  FROM SYSADM.PSCLASSDEFN C
                  LEFT JOIN SYSADM.PSROLECLASS R ON R.CLASSID = C.CLASSID
                 GROUP BY C.CLASSID, C.CLASSDEFNDESC
                HAVING COUNT(R.ROLENAME) = 0
                 ORDER BY C.CLASSID
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["classid", "classdefndesc", "role_count"],
        },
        "top_operators_by_roles": {
            "title": "Operators with Most Role Assignments",
            "note": "Top operators by number of roles — identifies highly privileged accounts.",
            "sql": """
                SELECT U.ROLEUSER, O.EMAILID, COUNT(*) AS ROLE_COUNT
                  FROM SYSADM.PSROLEUSER U
                  LEFT JOIN SYSADM.PSOPRDEFN O ON O.OPRID = U.ROLEUSER
                 GROUP BY U.ROLEUSER, O.EMAILID
                 ORDER BY COUNT(*) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["roleuser", "emailid", "role_count"],
        },
        "top_roles_by_users": {
            "title": "Roles with Most User Assignments",
            "note": "Top roles by member count — most widely deployed roles.",
            "sql": """
                SELECT ROLENAME, COUNT(*) AS USER_COUNT
                  FROM SYSADM.PSROLEUSER
                 GROUP BY ROLENAME
                 ORDER BY COUNT(*) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["rolename", "user_count"],
        },
        "locked_operators": {
            "title": "Locked Operator Accounts",
            "note": "Operators with ACCTLOCK > 0 — accounts that may need review or unlocking.",
            "sql": """
                SELECT OPRID, EMAILID, ACCTLOCK, LASTUPDDTTM, LASTUPDOPRID
                  FROM SYSADM.PSOPRDEFN
                 WHERE ACCTLOCK > 0
                 ORDER BY LASTUPDDTTM DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["oprid", "emailid", "acctlock", "lastupddttm", "lastupdoprid"],
        },
        "permission_list_role_coverage": {
            "title": "Permission Lists by Role Coverage",
            "note": "Permission lists ordered by how many roles include them — identifies broadly shared vs. niche permission sets.",
            "sql": """
                SELECT C.CLASSID, C.CLASSDEFNDESC, COUNT(R.ROLENAME) AS ROLE_COUNT
                  FROM SYSADM.PSCLASSDEFN C
                  LEFT JOIN SYSADM.PSROLECLASS R ON R.CLASSID = C.CLASSID
                 GROUP BY C.CLASSID, C.CLASSDEFNDESC
                 ORDER BY COUNT(R.ROLENAME) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["classid", "classdefndesc", "role_count"],
        },
    }

    spec = REPORTS.get(report_type)
    if spec is None:
        return {
            "title": "Unknown Report",
            "columns": [],
            "rows": [],
            "note": f"No report named '{report_type}'. Available: {', '.join(REPORTS.keys())}",
            "available_reports": list(REPORTS.keys()),
        }

    try:
        rows = query(env_name, spec["sql"], {"limit": limit})
        return {
            "title": spec["title"],
            "columns": spec["columns"],
            "rows": [dict(r) for r in rows],
            "note": spec["note"],
            "available_reports": list(REPORTS.keys()),
        }
    except Exception as exc:
        return {
            "title": spec["title"],
            "columns": spec["columns"],
            "rows": [],
            "note": f"Query failed: {exc}",
            "available_reports": list(REPORTS.keys()),
        }
