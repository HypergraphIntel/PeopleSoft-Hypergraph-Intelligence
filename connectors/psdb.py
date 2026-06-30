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

    add_col = "c.ADDSRCHRECNAME" if "ADDSRCHRECNAME" in columns else "c.SEARCHRECNAME"
    sql = f"""
        SELECT DISTINCT {", ".join(selected)},
               rf.RECNAME,
               rf.FIELDNAME
          FROM sysadm.PSPNLGRPDEFN c
          JOIN sysadm.PSRECFIELD rf
            ON rf.RECNAME IN (c.SEARCHRECNAME, {add_col})
         WHERE rf.FIELDNAME = UPPER(:fieldname)
         ORDER BY c.PNLGRPNAME, rf.RECNAME
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
    """Return PeopleCode programs that are attached to a specific record.fieldname.

    Queries PSPCMPROG for:
      - objectid1=2  (Record/Field level): OV1=RECNAME, OV2=FIELDNAME
      - objectid1=10 (Component Record/Field level): OV3=RECNAME, OV4=FIELDNAME
    Results normalized with peoplecode.normalize_program().
    """
    from connectors import peoplecode as _pc, ptmetadata

    resolved = resolve_field_reference(env_name, field_ref)
    if not resolved.get("resolved"):
        return []

    recname = resolved["recname"].upper()
    fieldname = resolved["fieldname"].upper()

    if not ptmetadata.has_table(env_name, "PSPCMPROG"):
        return []

    try:
        rows = query(env_name, """
            SELECT OBJECTID1, OBJECTID2, OBJECTID3, OBJECTID4,
                   OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3, OBJECTVALUE4,
                   OBJECTVALUE5, OBJECTVALUE6, OBJECTVALUE7, PROGSEQ,
                   LASTUPDDTTM, LASTUPDOPRID
              FROM sysadm.PSPCMPROG
             WHERE (
                   (OBJECTID1 = 2
                    AND UPPER(OBJECTVALUE1) = :recname
                    AND UPPER(OBJECTVALUE2) = :fieldname)
                OR (OBJECTID1 = 10
                    AND UPPER(OBJECTVALUE3) = :recname
                    AND UPPER(OBJECTVALUE4) = :fieldname)
             )
             ORDER BY OBJECTID1, OBJECTVALUE1, OBJECTVALUE2, OBJECTVALUE3, OBJECTVALUE5
             FETCH FIRST 200 ROWS ONLY
        """, {"recname": recname, "fieldname": fieldname})
        return [_pc.normalize_program(row) for row in rows]
    except Exception:
        return []


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


def search_menus(env_name, q=""):
    sql = """
        SELECT MENUNAME, DESCR, MENUTYPE, MENUGROUP, OBJECTOWNERID, LASTUPDDTTM
          FROM SYSADM.PSMENUDEFN
         WHERE UPPER(MENUNAME) LIKE :q
            OR UPPER(DESCR) LIKE :q
         ORDER BY MENUNAME
         FETCH FIRST 200 ROWS ONLY
    """
    return query(env_name, sql, {"q": f"%{q.upper()}%"})


def menu(env_name, menuname):
    rows = query(env_name, """
        SELECT MENUNAME, DESCR, DESCRLONG, MENUTYPE, MENUGROUP,
               INSTALLED, GROUPORDER, MENUORDER, OBJECTOWNERID,
               LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSMENUDEFN
         WHERE UPPER(MENUNAME) = UPPER(:menuname)
    """, {"menuname": menuname})
    return rows[0] if rows else None


def menu_items(env_name, menuname):
    return query(env_name, """
        SELECT m.BARNAME,
               m.ITEMNAME,
               m.ITEMNUM,
               m.ITEMTYPE,
               m.PNLGRPNAME,
               m.MARKET,
               m.BARLABEL,
               m.ITEMLABEL,
               m.SEARCHRECNAME,
               p.DESCR AS component_descr
          FROM SYSADM.PSMENUITEM m
          LEFT JOIN SYSADM.PSPNLGRPDEFN p
            ON p.PNLGRPNAME = m.PNLGRPNAME
           AND p.MARKET     = m.MARKET
         WHERE UPPER(m.MENUNAME) = UPPER(:menuname)
         ORDER BY m.BARNAME, m.ITEMNUM
    """, {"menuname": menuname})


def component_menus(env_name, component_name):
    """Find menus that reference a component (PNLGRPNAME)."""
    return query(env_name, """
        SELECT m.MENUNAME,
               d.DESCR  AS menu_descr,
               m.BARNAME,
               m.ITEMNAME,
               m.ITEMLABEL,
               m.MARKET
          FROM SYSADM.PSMENUITEM m
          JOIN SYSADM.PSMENUDEFN d ON d.MENUNAME = m.MENUNAME
         WHERE UPPER(m.PNLGRPNAME) = UPPER(:component)
         ORDER BY m.MENUNAME, m.BARNAME
    """, {"component": component_name})


def _batch_in_query(env_name, sql_template, items, chunk_size=500):
    """Execute an IN-clause query across chunks to stay under Oracle's 1000-item limit.

    sql_template must contain the literal __IN_CLAUSE__ where the bind placeholders go.
    Returns the concatenated result rows from all chunks.
    """
    results = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        binds = {f"b{j}": item for j, item in enumerate(chunk)}
        in_clause = ", ".join(f":b{j}" for j in range(len(chunk)))
        sql = sql_template.replace("__IN_CLAUSE__", in_clause)
        try:
            results.extend(query(env_name, sql, binds))
        except Exception:
            pass
    return results


def batch_operator_roles(env_name, oprids):
    """Return {oprid: [rows]} — all role memberships for a set of operators in one query."""
    if not oprids:
        return {}
    rows = _batch_in_query(env_name, """
        SELECT ROLEUSER, ROLENAME, DYNAMIC_SW
          FROM sysadm.PSROLEUSER
         WHERE ROLEUSER IN (__IN_CLAUSE__)
         ORDER BY ROLEUSER, ROLENAME
    """, [str(o).upper() for o in oprids])
    result: dict = {}
    for row in rows:
        result.setdefault(str(row.get("roleuser") or "").strip().upper(), []).append(row)
    return result


def batch_role_permissionlists(env_name, rolenames):
    """Return {rolename: [rows]} — all permission list assignments for a set of roles in one query."""
    if not rolenames:
        return {}
    columns = select_existing_columns(
        env_name, "PSROLECLASS", ["DYNAMIC_SW"], required=["ROLENAME", "CLASSID"]
    )
    rows = _batch_in_query(env_name, f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSROLECLASS
         WHERE UPPER(ROLENAME) IN (__IN_CLAUSE__)
         ORDER BY ROLENAME, CLASSID
    """, [str(r).upper() for r in rolenames])
    result: dict = {}
    for row in rows:
        result.setdefault(str(row.get("rolename") or "").strip().upper(), []).append(row)
    return result


def batch_permissionlist_components(env_name, classids):
    """Return {classid: [rows]} — all component grants for a set of permission lists in one query."""
    if not classids:
        return {}
    source = auth_component_source(env_name)
    rows = _batch_in_query(env_name, f"""
        SELECT DISTINCT ai.CLASSID, {source['expr']} AS pnlgrpname, ai.MENUNAME,
               ai.AUTHORIZEDACTIONS, ai.DISPLAYONLY
          FROM sysadm.PSAUTHITEM ai
          {source["join"]}
         WHERE ai.CLASSID IN (__IN_CLAUSE__)
           AND {source["where"]} IS NOT NULL
         ORDER BY ai.CLASSID, ai.MENUNAME
    """, [str(c).upper() for c in classids])
    result: dict = {}
    for row in rows:
        result.setdefault(str(row.get("classid") or "").strip().upper(), []).append(row)
    return result


def batch_component_pages(env_name, component_names):
    """Return {component_name: [rows]} — all pages for a set of components in one query."""
    if not component_names:
        return {}
    group_columns = select_existing_columns(
        env_name, "PSPNLGROUP", ["MARKET", "ITEMNUM"], required=["PNLGRPNAME", "PNLNAME"]
    )
    rows = _batch_in_query(env_name, f"""
        SELECT {", ".join(group_columns)}
          FROM sysadm.PSPNLGROUP
         WHERE PNLGRPNAME IN (__IN_CLAUSE__)
         ORDER BY PNLGRPNAME, PNLNAME
    """, [str(c).upper() for c in component_names])
    result: dict = {}
    for row in rows:
        result.setdefault(str(row.get("pnlgrpname") or "").strip().upper(), []).append(row)
    return result


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
         where upper(rc.rolename) = upper(:rolename)
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


def component_page_hierarchy(env_name, component_name):
    """Return pages and their structural contents (subpages/grids) for a component.

    Returns a flat leveled list suitable for renderRows():
      level 0 = page header (type chip, links to Page Explorer)
      level 1 = structural element within that page (Subpage/Grid chip, links to Page Explorer)
    Batch-fetches PSPNLFIELD for all pages in one query (FIELDTYPE IN (11, 18, 21)).
    """
    pages = component_pages(env_name, component_name)
    if not pages:
        return []

    page_names = [str(p.get("pnlname") or "").strip().upper() for p in pages if p.get("pnlname")]
    if not page_names:
        return []

    field_columns = select_existing_columns(
        env_name, "PSPNLFIELD",
        ["FIELDTYPE", "LEVELNUM", "OCCURSLEVEL", "SUBPNLNAME", "RECNAME", "LBLTEXT", "FIELDNUM"],
        required=["PNLNAME"],
    )

    struct_by_page = {}
    try:
        binds = {f"p{i}": name for i, name in enumerate(page_names)}
        in_clause = ", ".join(f":p{i}" for i in range(len(page_names)))
        rows = query(env_name, f"""
            SELECT {", ".join(field_columns)}
              FROM sysadm.PSPNLFIELD
             WHERE PNLNAME IN ({in_clause})
               AND FIELDTYPE IN (11, 18, 21)
             ORDER BY PNLNAME, FIELDNUM
        """, binds)
        for row in rows:
            pn = str(row.get("pnlname") or "").strip().upper()
            struct_by_page.setdefault(pn, []).append(row)
    except Exception:
        pass

    _PNLTYPE_LABELS = {0: "Standard", 1: "Subpage", 2: "Secondary", 3: "Popup"}
    _SUBPAGE_FT = {11, 18}
    _GRID_FT = {21}

    result = []
    for page_row in pages:
        pnlname = str(page_row.get("pnlname") or "").strip()
        if not pnlname:
            continue
        try:
            pnltype_int = int(page_row.get("page_pnltype") or 0)
        except (TypeError, ValueError):
            pnltype_int = 0
        type_label = _PNLTYPE_LABELS.get(pnltype_int, f"type{pnltype_int}")
        descr = str(page_row.get("page_descr") or "").strip()

        result.append({
            "level": 0,
            "pnlname": pnlname,
            "name": descr or pnlname,
            "relationship": type_label,
            "_links": {"admin": f"/admin/object/page/{pnlname}"},
        })

        for srow in struct_by_page.get(pnlname, []):
            try:
                ft = int(srow.get("fieldtype") or -1)
            except (TypeError, ValueError):
                ft = -1
            subpnl = str(srow.get("subpnlname") or "").strip()
            if not subpnl:
                continue
            if ft in _SUBPAGE_FT:
                kind = "Subpage"
            elif ft in _GRID_FT:
                kind = "Grid"
            else:
                continue
            lbl = str(srow.get("lbltext") or "").strip()
            rec = str(srow.get("recname") or "").strip()
            result.append({
                "level": 1,
                "pnlname": subpnl,
                "name": lbl or subpnl,
                "relationship": kind,
                "recname": rec or None,
                "_links": {"admin": f"/admin/object/page/{subpnl}"},
            })

    return result


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
    """Build a structural summary of a page's controls from PSPNLFIELD.

    Returns only structural elements: Subpage inclusions, Grids, and Scroll Areas.
    Regular field controls (edit boxes, buttons, etc.) are excluded.

    PeopleTools PSPNLFIELD.FIELDTYPE numeric values (PeopleTools 8.5+):
      11 = Subpage
      18 = Scroll Area (subpage-like)
      21 = Grid
      All others = non-structural controls
    """
    rows = page_fields(env_name, page_name)
    structure = []

    _SUBPAGE_TYPES = {11, 18}
    _GRID_TYPES = {21}

    for row in rows:
        try:
            ft = int(row.get("fieldtype") or -1)
        except (TypeError, ValueError):
            ft = -1

        level = row.get("levelnum") or row.get("occurslevel") or 0
        subpnl = str(row.get("subpnlname") or "").strip()

        if ft in _SUBPAGE_TYPES and subpnl:
            kind = "Subpage"
        elif ft in _GRID_TYPES and subpnl:
            kind = "Grid"
        else:
            continue

        structure.append({
            "level": level,
            "kind": kind,
            "recname": str(row.get("recname") or "").strip() or None,
            "fieldname": str(row.get("fieldname") or "").strip() or None,
            "pnlname": subpnl,
            "label": str(row.get("lbltext") or "").strip() or None,
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
        if row.get("kind") == "Subpage"
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
        ["DESCR", "MARKET", "ADDSRCHRECNAME"],
        required=["PNLGRPNAME", "SEARCHRECNAME"],
    )

    add_clause = "OR ADDSRCHRECNAME = UPPER(:recname)" if "ADDSRCHRECNAME" in columns else ""

    sql = f"""
        SELECT {", ".join(columns)}
          FROM sysadm.PSPNLGRPDEFN
         WHERE SEARCHRECNAME = UPPER(:recname)
            {add_clause}
         ORDER BY PNLGRPNAME
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
        classid = str(item.get("classid") or "").strip()
        permissionlist_detail = None
        if classid:
            try:
                permissionlist_detail = permissionlist(env_name, classid)
            except Exception:
                permissionlist_detail = None
        action_info = decode_authorized_actions(
            item.get("authorizedactions"),
            item.get("displayonly"),
        )
        item.update(action_info)
        item["permissionlist_detail"] = permissionlist_detail or {"classid": classid}
        item["path"] = [
            {"type": "operator", "name": oprid},
            {"type": "role", "name": item.get("rolename")},
            {"type": "permissionlist", "name": classid},
            {"type": "component", "name": item.get("pnlgrpname") or component_name},
        ]
        item["path_summary"] = " → ".join(
            f"{step['type']}:{step['name']}"
            for step in item["path"]
            if step.get("name")
        )
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
        classid = str(item.get("classid") or "").strip()
        permissionlist_detail = None
        if classid:
            try:
                permissionlist_detail = permissionlist(env_name, classid)
            except Exception:
                permissionlist_detail = None
        action_info = decode_authorized_actions(
            item.get("authorizedactions"),
            item.get("displayonly"),
        )
        item.update(action_info)
        item["permissionlist_detail"] = permissionlist_detail or {"classid": classid}
        item["path"] = [
            {"type": "operator", "name": oprid},
            {"type": "role", "name": item.get("rolename")},
            {"type": "permissionlist", "name": classid},
            {"type": "menu", "name": item.get("menuname")},
        ]
        item["path_summary"] = " → ".join(
            f"{step['type']}:{step['name']}"
            for step in item["path"]
            if step.get("name")
        )
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


def permissionlist_page_grants(env_name, classid, limit=200):
    """Return page-level grants for a permission list from PSAUTHITEM."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSAUTHITEM"):
        return []
    sql = f"""
        SELECT MENUNAME, BARNAME, BARITEMNAME, PNLITEMNAME, DISPLAYONLY, AUTHORIZEDACTIONS
          FROM sysadm.PSAUTHITEM
         WHERE CLASSID = :classid
           AND PNLITEMNAME IS NOT NULL
           AND PNLITEMNAME != ' '
         ORDER BY BARITEMNAME, PNLITEMNAME
         FETCH FIRST {int(limit)} ROWS ONLY
    """
    try:
        return with_decoded_actions(query(env_name, sql, {"classid": classid.upper()}))
    except Exception:
        return []


def component_page_grants(env_name, component_name, limit=300):
    """Return page-level security for a component — which permission lists grant each page."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSAUTHITEM"):
        return []
    sql = f"""
        SELECT CLASSID, MENUNAME, BARNAME, PNLITEMNAME, DISPLAYONLY, AUTHORIZEDACTIONS
          FROM sysadm.PSAUTHITEM
         WHERE UPPER(BARITEMNAME) = :component
           AND PNLITEMNAME IS NOT NULL
           AND PNLITEMNAME != ' '
         ORDER BY PNLITEMNAME, CLASSID
         FETCH FIRST {int(limit)} ROWS ONLY
    """
    try:
        return with_decoded_actions(query(env_name, sql, {"component": component_name.upper()}))
    except Exception:
        return []


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
    """Return portal registry entries that reference this component.

    Searches PSPRSMDEFN by PORTAL_URI_SEG2 = component (type C refs) plus
    a LIKE fallback for URL-type refs. Joins parent and grandparent folder
    labels to reconstruct the navigation path (portal > grandparent > parent > label).
    """
    columns = table_columns(env_name, "PSPRSMDEFN")
    if not columns:
        return []

    has_seg2 = "portal_uri_seg2" in columns
    has_label = "portal_label" in columns
    has_prnt = "portal_prntobjname" in columns

    candidates = [
        "PORTAL_NAME", "PORTAL_OBJNAME", "PORTAL_LABEL", "PORTAL_PRNTOBJNAME",
        "PORTAL_URI_SEG1", "PORTAL_URI_SEG2", "PORTAL_URI_SEG3",
        "PORTAL_REFTYPE", "PORTAL_URLTEXT",
    ]
    base_cols = [col for col in candidates if col.lower() in columns]
    if not base_cols:
        return []

    select_parts = [f"p.{col}" for col in base_cols]

    # Parent/grandparent label joins for navigation path reconstruction
    join_clause = ""
    if has_prnt and has_label:
        select_parts.append("par.PORTAL_LABEL AS nav_parent_label")
        select_parts.append("par.PORTAL_PRNTOBJNAME AS nav_gpar_objname" if "portal_prntobjname" in columns else "NULL AS nav_gpar_objname")
        select_parts.append("gpar.PORTAL_LABEL AS nav_grandparent_label")
        join_clause = """
          LEFT JOIN sysadm.PSPRSMDEFN par
            ON par.PORTAL_OBJNAME = p.PORTAL_PRNTOBJNAME
           AND par.PORTAL_NAME = p.PORTAL_NAME
          LEFT JOIN sysadm.PSPRSMDEFN gpar
            ON gpar.PORTAL_OBJNAME = par.PORTAL_PRNTOBJNAME
           AND gpar.PORTAL_NAME = p.PORTAL_NAME"""

    # Primary: exact match on PORTAL_URI_SEG2 for content refs
    where_parts = []
    if has_seg2:
        where_parts.append("(UPPER(p.PORTAL_URI_SEG2) = :component AND p.PORTAL_REFTYPE = 'C')")
    # Fallback: LIKE on urltext for URL-type refs
    if "portal_urltext" in columns:
        where_parts.append("(UPPER(p.PORTAL_URLTEXT) LIKE :component_like AND p.PORTAL_REFTYPE != 'C')")

    if not where_parts:
        return []

    sql = f"""
        SELECT {", ".join(select_parts)}
          FROM sysadm.PSPRSMDEFN p{join_clause}
         WHERE {" OR ".join(where_parts)}
         ORDER BY p.PORTAL_NAME, p.PORTAL_PRNTOBJNAME, p.PORTAL_LABEL
         FETCH FIRST 200 ROWS ONLY
    """

    rows = query(env_name, sql, {
        "component": component.upper(),
        "component_like": f"%{component.upper()}%",
    })

    # Build nav_path string: grandparent > parent > label
    result = []
    for row in rows:
        gpar = str(row.get("nav_grandparent_label") or "").strip()
        par = str(row.get("nav_parent_label") or "").strip()
        lbl = str(row.get("portal_label") or "").strip()
        path_parts = [p for p in (gpar, par, lbl) if p]
        row = dict(row)
        if len(path_parts) > 1:
            row["nav_path"] = " › ".join(path_parts)
        result.append(row)
    return result


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


def portal_registry_breadcrumbs_fast(env_name, portal_objname, portal_name=None):
    """Build breadcrumb chain from leaf to root using Oracle CONNECT BY (single query).

    START WITH filters on both PORTAL_OBJNAME and PORTAL_NAME to start with exactly
    one leaf row, then walks upward via PRIOR PORTAL_PRNTOBJNAME = PORTAL_OBJNAME.
    Returns list from root → leaf (depth DESC order).
    """
    pn = portal_name or "EMPLOYEE"
    try:
        rows = query(env_name, """
            SELECT PORTAL_OBJNAME,
                   PORTAL_LABEL,
                   PORTAL_REFTYPE,
                   PORTAL_PRNTOBJNAME,
                   PORTAL_SEQ_NUM,
                   LEVEL AS depth
              FROM SYSADM.PSPRSMDEFN
             WHERE UPPER(PORTAL_NAME) = UPPER(:pn)
             START WITH UPPER(PORTAL_OBJNAME) = UPPER(:objname)
                    AND UPPER(PORTAL_NAME)    = UPPER(:pn)
           CONNECT BY NOCYCLE
                      UPPER(PORTAL_NAME)          = UPPER(:pn)
                  AND PRIOR PORTAL_PRNTOBJNAME    = PORTAL_OBJNAME
                  AND TRIM(PRIOR PORTAL_PRNTOBJNAME) != ' '
             ORDER BY depth DESC
        """, {"pn": pn, "objname": portal_objname})
        return rows
    except Exception:
        return portal_registry_breadcrumbs(env_name, portal_objname, portal_name)


def portal_registry_folder_children(env_name, portal_name, parent_objname, include_crefs=True):
    """Return immediate children of a portal folder, sorted by sequence number.

    Used for lazy tree navigation — only fetches one level at a time.
    include_crefs=False returns only sub-folders (for tree expand nodes).
    """
    reftype_filter = "" if include_crefs else "AND PORTAL_REFTYPE = 'F'"
    try:
        rows = query(env_name, f"""
            SELECT PORTAL_OBJNAME,
                   PORTAL_LABEL,
                   PORTAL_REFTYPE,
                   PORTAL_PRNTOBJNAME,
                   PORTAL_SEQ_NUM,
                   PORTAL_URI_SEG1,
                   PORTAL_URI_SEG2,
                   PORTAL_URI_SEG3,
                   DESCR254,
                   PORTAL_CREF_USGT
              FROM SYSADM.PSPRSMDEFN
             WHERE UPPER(PORTAL_NAME) = UPPER(:pn)
               AND UPPER(PORTAL_PRNTOBJNAME) = UPPER(:parent)
               {reftype_filter}
             ORDER BY PORTAL_SEQ_NUM NULLS LAST, PORTAL_LABEL
             FETCH FIRST 500 ROWS ONLY
        """, {"pn": portal_name, "parent": parent_objname})
        return rows
    except Exception:
        return []


def portal_registry_portals(env_name):
    """Return the list of portal names and their root-level statistics."""
    try:
        rows = query(env_name, """
            SELECT PORTAL_NAME,
                   COUNT(*) AS total,
                   SUM(CASE WHEN PORTAL_REFTYPE = 'F' THEN 1 ELSE 0 END) AS folders,
                   SUM(CASE WHEN PORTAL_REFTYPE = 'C' THEN 1 ELSE 0 END) AS content_refs,
                   MIN(LASTUPDDTTM) AS oldest_update,
                   MAX(LASTUPDDTTM) AS latest_update
              FROM SYSADM.PSPRSMDEFN
             GROUP BY PORTAL_NAME
             ORDER BY total DESC
        """)
        # Find root folder for each portal
        for r in rows:
            root_rows = query(env_name, """
                SELECT PORTAL_OBJNAME, PORTAL_LABEL
                  FROM SYSADM.PSPRSMDEFN
                 WHERE UPPER(PORTAL_NAME) = UPPER(:pn)
                   AND PORTAL_REFTYPE = 'F'
                   AND LENGTH(TRIM(PORTAL_PRNTOBJNAME)) = 0
                 FETCH FIRST 1 ROWS ONLY
            """, {"pn": r["portal_name"]})
            if root_rows:
                r["root_objname"] = root_rows[0]["portal_objname"]
                r["root_label"] = root_rows[0]["portal_label"]
            else:
                r["root_objname"] = None
                r["root_label"] = None
        return rows
    except Exception:
        return []


def portal_registry_analysis(env_name, portal_name):
    """Structural analysis: orphans, depth distribution, most-referenced components."""
    results = {}
    try:
        # Total counts
        cnt = query(env_name, """
            SELECT PORTAL_REFTYPE, COUNT(*) AS cnt
              FROM SYSADM.PSPRSMDEFN
             WHERE UPPER(PORTAL_NAME) = UPPER(:pn)
             GROUP BY PORTAL_REFTYPE
        """, {"pn": portal_name})
        results["counts"] = {r["portal_reftype"]: r["cnt"] for r in cnt}

        # Orphaned entries — parent doesn't exist in this portal
        orphans = query(env_name, """
            SELECT c.PORTAL_OBJNAME,
                   c.PORTAL_LABEL,
                   c.PORTAL_REFTYPE,
                   c.PORTAL_PRNTOBJNAME
              FROM SYSADM.PSPRSMDEFN c
              LEFT JOIN SYSADM.PSPRSMDEFN p
                ON UPPER(p.PORTAL_NAME)    = UPPER(c.PORTAL_NAME)
               AND UPPER(p.PORTAL_OBJNAME) = UPPER(c.PORTAL_PRNTOBJNAME)
             WHERE UPPER(c.PORTAL_NAME) = UPPER(:pn)
               AND TRIM(c.PORTAL_PRNTOBJNAME) != ' '
               AND TRIM(c.PORTAL_PRNTOBJNAME) != ''
               AND p.PORTAL_OBJNAME IS NULL
             FETCH FIRST 50 ROWS ONLY
        """, {"pn": portal_name})
        results["orphans"] = orphans
        results["orphan_count"] = len(orphans)

        # Most-referenced components (top 20 by content ref count)
        top_components = query(env_name, """
            SELECT UPPER(PORTAL_URI_SEG2) AS component,
                   COUNT(*) AS ref_count
              FROM SYSADM.PSPRSMDEFN
             WHERE UPPER(PORTAL_NAME) = UPPER(:pn)
               AND PORTAL_REFTYPE = 'C'
               AND TRIM(PORTAL_URI_SEG2) != ' '
               AND TRIM(PORTAL_URI_SEG2) != ''
             GROUP BY UPPER(PORTAL_URI_SEG2)
             ORDER BY ref_count DESC
             FETCH FIRST 20 ROWS ONLY
        """, {"pn": portal_name})
        results["top_components"] = top_components

        # Empty folders (folders with no children)
        empty_folders = query(env_name, """
            SELECT f.PORTAL_OBJNAME,
                   f.PORTAL_LABEL,
                   f.PORTAL_PRNTOBJNAME
              FROM SYSADM.PSPRSMDEFN f
              LEFT JOIN SYSADM.PSPRSMDEFN c
                ON UPPER(c.PORTAL_NAME) = UPPER(f.PORTAL_NAME)
               AND UPPER(c.PORTAL_PRNTOBJNAME) = UPPER(f.PORTAL_OBJNAME)
             WHERE UPPER(f.PORTAL_NAME) = UPPER(:pn)
               AND f.PORTAL_REFTYPE = 'F'
               AND c.PORTAL_OBJNAME IS NULL
             FETCH FIRST 30 ROWS ONLY
        """, {"pn": portal_name})
        results["empty_folders"] = empty_folders
        results["empty_folder_count"] = len(empty_folders)

    except Exception as exc:
        results["error"] = str(exc)
    return results


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


def search_queries(env_name, q="", folder=None, limit=100):
    """Search public PS Queries (OPRID=' ') by name or description."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%" if q else "%"
    params = {"pattern": pattern}

    cols = select_existing_columns(
        env_name, "PSQRYDEFN",
        ["QRYNAME", "OPRID", "DESCR", "QRYFOLDER", "QRYTYPE",
         "QRYDISABLED", "QRYVALID", "SELCOUNT", "BNDCOUNT", "EXPCOUNT",
         "LASTUPDDTTM", "LASTUPDOPRID"],
        required=["QRYNAME"],
    )
    if not cols:
        return []

    folder_clause = ""
    if folder:
        folder_clause = "AND UPPER(QRYFOLDER) = UPPER(:folder)"
        params["folder"] = folder

    return query(env_name, f"""
        SELECT * FROM (
            SELECT {", ".join(cols)}
              FROM SYSADM.PSQRYDEFN
             WHERE OPRID = ' '
               AND (UPPER(QRYNAME) LIKE :pattern OR UPPER(DESCR) LIKE :pattern)
               {folder_clause}
             ORDER BY QRYNAME
        ) WHERE ROWNUM <= {limit}
    """, params)


def query_folders(env_name):
    """Return distinct QRYFOLDER values for public queries."""
    rows = query(env_name, """
        SELECT DISTINCT QRYFOLDER
          FROM SYSADM.PSQRYDEFN
         WHERE OPRID = ' '
           AND TRIM(QRYFOLDER) IS NOT NULL
           AND QRYFOLDER != ' '
         ORDER BY QRYFOLDER
    """)
    return [r["qryfolder"] for r in rows if r.get("qryfolder")]


def search_trees(env_name, q="", setid=None, limit=100):
    """Search PSTREEDEFN by name or description (latest effective-dated row per tree)."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%" if q else "%"
    params = {"pattern": pattern}

    cols = select_existing_columns(
        env_name, "PSTREEDEFN",
        ["TREE_NAME", "SETID", "SETCNTRLVALUE", "EFFDT", "EFF_STATUS",
         "TREE_STRCT_ID", "DESCR", "ALL_VALUES", "USE_LEVELS", "VALID_TREE",
         "NODE_COUNT", "LEAF_COUNT"],
        required=["TREE_NAME"],
    )
    if not cols:
        return []

    alias_map = {
        "TREE_NAME": "TREENAME",
        "TREE_STRCT_ID": "TREESTRCTPNM",
    }
    select_exprs = [
        f"t.{col} AS {alias_map[col]}" if col in alias_map else f"t.{col}"
        for col in cols
    ]

    setid_clause = ""
    if setid:
        setid_clause = "AND UPPER(t.SETID) = UPPER(:setid)"
        params["setid"] = setid

    descr_clause = "OR UPPER(t.DESCR) LIKE :pattern" if "DESCR" in cols else ""

    return query(env_name, f"""
        SELECT * FROM (
            SELECT {", ".join(select_exprs)}
              FROM SYSADM.PSTREEDEFN t
             WHERE (UPPER(t.TREE_NAME) LIKE :pattern {descr_clause})
               {setid_clause}
               AND t.EFFDT = (
                   SELECT MAX(t2.EFFDT) FROM SYSADM.PSTREEDEFN t2
                    WHERE t2.TREE_NAME = t.TREE_NAME AND t2.SETID = t.SETID
                      AND t2.SETCNTRLVALUE = t.SETCNTRLVALUE
               )
             ORDER BY t.TREE_NAME
        ) WHERE ROWNUM <= {limit}
    """, params)


def search_cis(env_name, q="", limit=100):
    """Search PSBCDEFN component interfaces by name or description."""
    limit = max(1, min(int(limit), 500))
    pattern = f"%{q.upper()}%" if q else "%"

    cols = select_existing_columns(
        env_name, "PSBCDEFN",
        ["BCNAME", "DESCR", "BCDISPLAYNAME", "BCTYPE", "PNLGRPNAME",
         "VERSION", "OBJECTOWNERID", "LASTUPDDTTM"],
        required=["BCNAME"],
    )
    if not cols:
        return []

    return query(env_name, f"""
        SELECT * FROM (
            SELECT {", ".join(cols)}
              FROM SYSADM.PSBCDEFN
             WHERE UPPER(BCNAME) LIKE :pattern
                OR UPPER(DESCR) LIKE :pattern
             ORDER BY BCNAME
        ) WHERE ROWNUM <= {limit}
    """, {"pattern": pattern})


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
         "ALLOWNOTIFY", "ALLOWLOOKUP", "LASTUPDDTTM", "LASTUPDOPRID", "DESCRLONG",
         "DYNAMIC_SW"],
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

    if "role_query_rule_on" not in row and "role_query_rule_on" in {c.lower() for c in rd_cols}:
        row["role_query_rule_on"] = None
    if "role_pcode_rule_on" not in row and "role_pcode_rule_on" in {c.lower() for c in rd_cols}:
        row["role_pcode_rule_on"] = None
    if "ldap_rule_on" not in row and "ldap_rule_on" in {c.lower() for c in rd_cols}:
        row["ldap_rule_on"] = None

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
            "category": "security",
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
            "category": "security",
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
            "category": "security",
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
            "category": "security",
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
            "category": "security",
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
            "category": "security",
        },
        "operators_without_roles": {
            "title": "Operators With No Role Assignments",
            "note": "PS operators defined in PSOPRDEFN with zero entries in PSROLEUSER — accounts that cannot access anything meaningful.",
            "sql": """
                SELECT O.OPRID, O.EMAILID, O.OPERPSWD IS NOT NULL AS HAS_PASSWORD,
                       O.LASTUPDDTTM, O.LASTUPDOPRID
                  FROM SYSADM.PSOPRDEFN O
                  LEFT JOIN SYSADM.PSROLEUSER R ON R.ROLEUSER = O.OPRID
                 WHERE R.ROLEUSER IS NULL
                   AND O.OPRID != ' '
                 ORDER BY O.OPRID
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["oprid", "emailid", "has_password", "lastupddttm", "lastupdoprid"],
            "category": "security",
        },
        "components_most_permissions": {
            "title": "Components Secured by Most Permission Lists",
            "note": "Components granted access by the highest number of distinct permission lists — potential over-exposure.",
            "sql": """
                SELECT A.PNLGRPNAME, A.MARKET, COUNT(DISTINCT A.CLASSID) AS PERM_LIST_COUNT
                  FROM SYSADM.PSAUTHITEM A
                 WHERE A.PNLGRPNAME != ' '
                 GROUP BY A.PNLGRPNAME, A.MARKET
                 ORDER BY COUNT(DISTINCT A.CLASSID) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["pnlgrpname", "market", "perm_list_count"],
            "category": "security",
        },
        "large_records": {
            "title": "Records with Most Fields",
            "note": "Records by descending field count — wide records may indicate design issues or consolidation candidates.",
            "sql": """
                SELECT R.RECNAME, R.RECTYPE, D.DESCR, COUNT(F.FIELDNAME) AS FIELD_COUNT
                  FROM SYSADM.PSRECDEFN R
                  LEFT JOIN SYSADM.PSDBFLDLABL D
                    ON D.RECNAME = R.RECNAME AND D.DEFAULT_LABEL = 1
                  LEFT JOIN SYSADM.PSRECFIELD F ON F.RECNAME = R.RECNAME
                 GROUP BY R.RECNAME, R.RECTYPE, D.DESCR
                 ORDER BY COUNT(F.FIELDNAME) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["recname", "rectype", "descr", "field_count"],
            "category": "objects",
        },
        "recently_changed_records": {
            "title": "Recently Changed Records",
            "note": "Records with the latest LASTUPDDTTM — useful for auditing recent schema changes.",
            "sql": """
                SELECT RECNAME, RECTYPE, DESCR, LASTUPDDTTM, LASTUPDOPRID, OBJECTOWNERID
                  FROM SYSADM.PSRECDEFN
                 WHERE LASTUPDDTTM IS NOT NULL
                 ORDER BY LASTUPDDTTM DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["recname", "rectype", "descr", "lastupddttm", "lastupdoprid", "objectownerid"],
            "category": "objects",
        },
        "records_by_type": {
            "title": "Record Count by Type",
            "note": "Distribution of record types (0=SQL Table, 1=SQL View, 2=Derived/Work, 3=SubRecord, 5=Dynamic View, 6=Query View, 7=Temp Table, 8=AE Work Record).",
            "sql": """
                SELECT RECTYPE, COUNT(*) AS COUNT
                  FROM SYSADM.PSRECDEFN
                 GROUP BY RECTYPE
                 ORDER BY RECTYPE
            """,
            "columns": ["rectype", "count"],
            "params": {},
            "category": "objects",
        },
        "largest_peoplecode_programs": {
            "title": "Largest PeopleCode Programs",
            "note": "Programs ranked by source length in PSPCMTXT — very large programs may indicate complexity or refactoring candidates.",
            "sql": """
                SELECT p.OBJECTVALUE1, p.OBJECTVALUE2, p.OBJECTVALUE3,
                       p.OBJECTVALUE4, p.OBJECTVALUE5, p.OBJECTVALUE6,
                       LENGTH(t.PCTEXT) AS SOURCE_LEN,
                       p.LASTUPDDTTM
                  FROM SYSADM.PSPCMPROG p
                  JOIN SYSADM.PSPCMTXT  t ON t.OBJECTID1   = p.OBJECTID1
                                          AND t.OBJECTVALUE1 = p.OBJECTVALUE1
                                          AND t.OBJECTVALUE2 = p.OBJECTVALUE2
                                          AND t.OBJECTVALUE3 = p.OBJECTVALUE3
                                          AND t.OBJECTVALUE4 = p.OBJECTVALUE4
                                          AND t.OBJECTVALUE5 = p.OBJECTVALUE5
                                          AND t.OBJECTVALUE6 = p.OBJECTVALUE6
                                          AND t.OBJECTVALUE7 = p.OBJECTVALUE7
                 ORDER BY LENGTH(t.PCTEXT) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["objectvalue1", "objectvalue2", "objectvalue3", "objectvalue4", "objectvalue5", "objectvalue6", "source_len", "lastupddttm"],
            "category": "objects",
        },
        "process_errors_7d": {
            "title": "Process Errors (Last 7 Days)",
            "note": "Failed process scheduler jobs in the last 7 days (RUNSTATUS=3). Useful for monitoring automation health.",
            "sql": """
                SELECT PRCSNAME, PRCSTYPE, OPRID, RUNCNTLID,
                       RUNDTTM, ENDDTTM, RUNSTATUS
                  FROM SYSADM.PSPRCSRQST
                 WHERE RUNSTATUS = 3
                   AND RUNDTTM >= SYSDATE - 7
                 ORDER BY RUNDTTM DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["prcsname", "prcstype", "oprid", "runcntlid", "rundttm", "enddttm", "runstatus"],
            "category": "system",
        },
        "ae_most_state_records": {
            "title": "Application Engines with Most State Records",
            "note": "AE programs with the most temporary state record definitions — indicates complex multi-step processing.",
            "sql": """
                SELECT A.AE_APPLID, D.DESCR, COUNT(DISTINCT A.RECNAME) AS STATE_REC_COUNT
                  FROM SYSADM.PSAEAPPLSTATE A
                  LEFT JOIN SYSADM.PSAEAPPLDEFN D ON D.AE_APPLID = A.AE_APPLID
                 GROUP BY A.AE_APPLID, D.DESCR
                 ORDER BY COUNT(DISTINCT A.RECNAME) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["ae_applid", "descr", "state_rec_count"],
            "category": "objects",
        },
        "menus_by_component_count": {
            "title": "Menus by Component Count",
            "note": "Menus ranked by how many component items they contain.",
            "sql": """
                SELECT D.MENUNAME, D.DESCR, D.MENUTYPE,
                       COUNT(DISTINCT TRIM(I.PNLGRPNAME)) AS COMPONENT_COUNT
                  FROM SYSADM.PSMENUDEFN D
                  LEFT JOIN SYSADM.PSMENUITEM I
                    ON I.MENUNAME = D.MENUNAME AND TRIM(I.PNLGRPNAME) IS NOT NULL
                 GROUP BY D.MENUNAME, D.DESCR, D.MENUTYPE
                 ORDER BY COUNT(DISTINCT TRIM(I.PNLGRPNAME)) DESC
                 FETCH FIRST :limit ROWS ONLY
            """,
            "columns": ["menuname", "descr", "menutype", "component_count"],
            "category": "objects",
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

    sql = spec["sql"]
    # Use spec-level params if provided, otherwise inject :limit if the SQL uses it
    if "params" in spec:
        params = dict(spec["params"])
    else:
        params = {"limit": limit} if ":limit" in sql else {}

    category = spec.get("category", "security")
    try:
        rows = query(env_name, sql, params)
        return {
            "title": spec["title"],
            "columns": spec["columns"],
            "rows": [dict(r) for r in rows],
            "note": spec["note"],
            "category": category,
            "available_reports": [
                {"key": k, "title": v["title"], "category": v.get("category", "security")}
                for k, v in REPORTS.items()
            ],
        }
    except Exception as exc:
        return {
            "title": spec["title"],
            "columns": spec["columns"],
            "rows": [],
            "note": f"Query failed: {exc}",
            "category": category,
            "available_reports": [
                {"key": k, "title": v["title"], "category": v.get("category", "security")}
                for k, v in REPORTS.items()
            ],
        }


PSSERVERSTAT_STATUS_LABELS = {
    "0": "Unknown",
    "1": "Stopped",
    "2": "Starting",
    "3": "Running",
    "4": "Stopping",
    "5": "Error",
    "6": "Suspended",
}

PSSERVERSTAT_DAEMON_LABELS = {
    "0": "None",
    "1": "Restart",
    "2": "Stop",
    "3": "Reload",
}


# ── App Server domain monitoring ──────────────────────────────────────────────
#
# PeopleSoft exposes domain topology through runtime views whose names vary
# across PeopleTools releases.  Discovery order:
#   1. SYSADM.PSPMDOMAIN_VW   (primary — has PM_SYSTEMID, PM_DOMAIN_NAME, PM_HOST_PORT)
#   2. SYSADM.PS_PSPMDOMAIN1_VW  (fallback — PM_DOMAIN_NAME, PM_HOST_PORT only)
# Neither PSAPPSRV nor PSAPPSRVDOM is required.

_APPSRV_DOMAIN_VIEWS = ["PSPMDOMAIN_VW", "PS_PSPMDOMAIN1_VW"]

_DOMAIN_TYPE_RULES = [
    # (substring, label, key)  — evaluated in order; first match wins
    ("_APP",   "App Server",        "app_server"),
    ("APPDOM", "App Server",        "app_server"),
    ("_PRCS",  "Process Scheduler", "process_scheduler"),
    ("PRCSDOM","Process Scheduler", "process_scheduler"),
    ("_WEB",   "Web / PIA",         "web"),
]

def _classify_domain(name):
    n = (name or "").upper()
    for fragment, label, key in _DOMAIN_TYPE_RULES:
        if fragment in n:
            return label, key
    # common web-tier aliases
    if n in ("PS", "PEOPLESOFT"):
        return "Web / PIA", "web"
    return "Integration Broker", "ib"


def _parse_host_port(hp_str):
    """Split 'host:port' or 'host:port1:port2' into structured fields."""
    parts = str(hp_str or "").split(":")
    host = parts[0].strip() if parts else ""
    port = parts[1].strip() if len(parts) > 1 else None
    alt_port = parts[2].strip() if len(parts) > 2 else None
    return {
        "host": host or None,
        "port": port or None,
        "alt_port": alt_port or None,
    }


def app_server_domains(env_name):
    """
    Return PeopleSoft application domain topology from runtime views.

    Tries PSPMDOMAIN_VW first, falls back to PS_PSPMDOMAIN1_VW.
    Returns domains grouped by PM_DOMAIN_NAME, with each domain's
    listeners, inferred type, and host breakdown.
    """
    from connectors import ptmetadata

    source_view = None
    for view in _APPSRV_DOMAIN_VIEWS:
        if ptmetadata.has_table(env_name, view):
            source_view = view
            break

    if source_view is None:
        return {
            "items": [],
            "source_view": None,
            "warnings": [{
                "code": "app_server_domains_unavailable",
                "message": (
                    "App Server domain monitoring unavailable: "
                    "neither PSPMDOMAIN_VW nor PS_PSPMDOMAIN1_VW is accessible."
                ),
                "severity": "warning",
            }],
        }

    try:
        available_cols = table_columns(env_name, source_view)
        want = ["PM_DOMAIN_NAME", "PM_HOST_PORT"]
        if "pm_systemid" in available_cols:
            want.insert(0, "PM_SYSTEMID")
        sel = [c for c in want if c.lower() in available_cols]
        rows = query(env_name, f"""
            SELECT {", ".join(sel)}
              FROM sysadm.{source_view}
             ORDER BY PM_DOMAIN_NAME, PM_HOST_PORT
        """, {})
    except Exception as exc:
        return {
            "items": [],
            "source_view": source_view,
            "warnings": [{
                "code": "app_server_domains_query_failed",
                "message": f"{source_view} query failed: {exc}",
                "severity": "warning",
            }],
        }

    # Group by domain name
    groups = {}
    for row in rows:
        dname = str(row.get("pm_domain_name") or "").strip()
        if not dname:
            continue
        if dname not in groups:
            groups[dname] = {"domain_name": dname, "listeners": []}
        hp = str(row.get("pm_host_port") or "").strip()
        if hp:
            groups[dname]["listeners"].append(_parse_host_port(hp))

    items = []
    for dname, g in sorted(groups.items()):
        type_label, type_key = _classify_domain(dname)
        listeners = g["listeners"]
        # Collect unique hosts
        hosts = sorted({l["host"] for l in listeners if l["host"]})
        # Primary listener = first entry with a non-empty port
        primary = next((l for l in listeners if l.get("port")), listeners[0] if listeners else {})
        items.append({
            "domain_name": dname,
            "domain_type": type_key,
            "domain_type_label": type_label,
            "hosts": hosts,
            "primary_host": primary.get("host"),
            "primary_port": primary.get("port"),
            "alt_port": primary.get("alt_port"),
            "listener_count": len(listeners),
            "title": dname,
            "relationship": type_label,
        })

    type_counts = {}
    for item in items:
        k = item["domain_type_label"]
        type_counts[k] = type_counts.get(k, 0) + 1

    return {
        "items": items,
        "source_view": source_view,
        "counts": {
            "total": len(items),
            **type_counts,
        },
        "warnings": [],
    }


def process_scheduler_servers(env_name):
    """Return Process Scheduler server status rows from PSSERVERSTAT."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSSERVERSTAT"):
        return {"items": [], "warnings": ["PSSERVERSTAT not accessible"]}

    cols = select_existing_columns(
        env_name, "PSSERVERSTAT",
        ["SERVERNAME", "SERVERSTATUS", "BEGINDTTM", "LASTUPDDTTM",
         "SRVRHOSTNAME", "SERVERACTION", "DAEMONACTION", "DAEMONPROCESSID",
         "SCHDLROESRVCNT", "SCHDLRAESRVCNT", "MAXCPU", "MINMEM",
         "PRCSTHRESHOLD", "PRCSDISKSPACE", "ORDERNO"],
        required=["SERVERNAME"],
    )
    try:
        rows = query(env_name, f"""
            SELECT {", ".join(cols)}
              FROM sysadm.psserverstat
             ORDER BY serverstatus DESC, lastupddttm DESC
        """, {})
    except Exception as exc:
        return {"items": [], "warnings": [f"PSSERVERSTAT query failed: {exc}"]}

    items = []
    for row in rows:
        item = dict(row)
        status_code = str(item.get("serverstatus") or "")
        item["serverstatus_label"] = PSSERVERSTAT_STATUS_LABELS.get(status_code, f"Status {status_code}")
        daemon_code = str(item.get("daemonaction") or "")
        item["daemonaction_label"] = PSSERVERSTAT_DAEMON_LABELS.get(daemon_code, "")
        items.append(item)

    running = sum(1 for i in items if str(i.get("serverstatus") or "") == "3")
    return {
        "items": items,
        "counts": {"total": len(items), "running": running, "stopped": len(items) - running},
        "warnings": [],
    }


# ── Message Catalog ───────────────────────────────────────────────────────────

_MSG_SEVERITY = {0: "Message", 1: "Warning", 2: "Error", 3: "Cancel"}


def _msg_severity_label(value):
    try:
        return _MSG_SEVERITY.get(int(value), str(value))
    except (TypeError, ValueError):
        return str(value or "")


def search_messages(env_name, q="", set_nbr=None, severity=None, limit=100):
    """Search PSMSGCATDEFN by text content or message set number."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSMSGCATDEFN"):
        return {"items": [], "warnings": ["PSMSGCATDEFN not accessible"]}

    clauses = []
    params = {}
    if q:
        clauses.append(
            "(UPPER(MESSAGE_TEXT) LIKE UPPER(:q) OR UPPER(DESCRLONG) LIKE UPPER(:q2))"
        )
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    if set_nbr is not None:
        clauses.append("MESSAGE_SET_NBR = :set_nbr")
        params["set_nbr"] = int(set_nbr)
    if severity is not None:
        clauses.append("SEVERITY = :severity")
        params["severity"] = int(severity)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT MESSAGE_SET_NBR, MESSAGE_NBR, SEVERITY, MESSAGE_TEXT, DESCRLONG
          FROM SYSADM.PSMSGCATDEFN
         {where}
         ORDER BY MESSAGE_SET_NBR, MESSAGE_NBR
         FETCH FIRST :lim ROWS ONLY
    """
    params["lim"] = limit
    try:
        rows = query(env_name, sql, params)
    except Exception as exc:
        return {"items": [], "warnings": [f"Search failed: {exc}"]}

    items = []
    for row in rows:
        item = dict(row)
        item["severity_label"] = _msg_severity_label(item.get("severity"))
        item["name"] = f"{item['message_set_nbr']}.{item['message_nbr']}"
        items.append(item)
    return {"items": items, "count": len(items), "warnings": []}


def message_sets(env_name):
    """Return message sets with descriptions and message counts."""
    from connectors import ptmetadata
    warnings = []

    if ptmetadata.has_table(env_name, "PSMSGSETDEFN"):
        try:
            rows = query(env_name, """
                SELECT s.MESSAGE_SET_NBR, s.DESCR,
                       COUNT(m.MESSAGE_NBR) AS msg_count
                  FROM SYSADM.PSMSGSETDEFN s
                  LEFT JOIN SYSADM.PSMSGCATDEFN m
                    ON m.MESSAGE_SET_NBR = s.MESSAGE_SET_NBR
                 GROUP BY s.MESSAGE_SET_NBR, s.DESCR
                 ORDER BY s.MESSAGE_SET_NBR
            """, {})
            return {"items": rows, "source": "PSMSGSETDEFN", "warnings": []}
        except Exception as exc:
            warnings.append(f"PSMSGSETDEFN join failed: {exc}")

    if not ptmetadata.has_table(env_name, "PSMSGCATDEFN"):
        return {"items": [], "warnings": ["PSMSGCATDEFN not accessible"]}

    try:
        rows = query(env_name, """
            SELECT MESSAGE_SET_NBR, NULL AS DESCR,
                   COUNT(*) AS msg_count
              FROM SYSADM.PSMSGCATDEFN
             GROUP BY MESSAGE_SET_NBR
             ORDER BY MESSAGE_SET_NBR
        """, {})
        return {"items": rows, "source": "PSMSGCATDEFN", "warnings": warnings}
    except Exception as exc:
        return {"items": [], "warnings": warnings + [f"message_sets fallback failed: {exc}"]}


def get_message(env_name, set_nbr, msg_nbr):
    """Fetch a specific message by set number and message number."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSMSGCATDEFN"):
        return None
    try:
        rows = query(env_name, """
            SELECT MESSAGE_SET_NBR, MESSAGE_NBR, SEVERITY, MESSAGE_TEXT, DESCRLONG
              FROM SYSADM.PSMSGCATDEFN
             WHERE MESSAGE_SET_NBR = :sn AND MESSAGE_NBR = :mn
        """, {"sn": int(set_nbr), "mn": int(msg_nbr)})
    except Exception:
        return None
    if not rows:
        return None
    row = dict(rows[0])
    row["severity_label"] = _msg_severity_label(row.get("severity"))
    row["name"] = f"{row['message_set_nbr']}.{row['message_nbr']}"
    return row


def message_set_info(env_name, set_nbr):
    """Return message set header (description) for a given set number."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSMSGSETDEFN"):
        return None
    try:
        rows = query(env_name, """
            SELECT MESSAGE_SET_NBR, DESCR, DESCRLONG
              FROM SYSADM.PSMSGSETDEFN
             WHERE MESSAGE_SET_NBR = :sn
        """, {"sn": int(set_nbr)})
    except Exception:
        return None
    return dict(rows[0]) if rows else None


# ── Approval Framework ────────────────────────────────────────────────────────

_AW_STATUS = {"A": "Active", "I": "Inactive"}
_AW_PROCESS_TYPE = {
    "0": "No Approval",
    "1": "User",
    "2": "Role",
    "3": "Query",
    "4": "Application Class",
    "5": "Supervisory",
    "6": "Position",
    "7": "Department Security",
    "8": "Role User",
}


def search_approvals(env_name, q="", status=None, limit=100):
    """Search PSAWDEFN approval workflow definitions."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSAWDEFN"):
        return {"items": [], "warnings": ["PSAWDEFN not accessible"]}

    clauses = []
    params = {}
    if q:
        clauses.append("(UPPER(AWDEFNID) LIKE UPPER(:q) OR UPPER(DESCR) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    if status:
        clauses.append("STATUS = :status")
        params["status"] = status.upper()

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT AWDEFNID, DESCR, STATUS, OBJECTOWNERID, LASTUPDOPRID, LASTUPDDTTM
          FROM SYSADM.PSAWDEFN
         {where}
         ORDER BY AWDEFNID
         FETCH FIRST :lim ROWS ONLY
    """
    params["lim"] = limit
    try:
        rows = query(env_name, sql, params)
    except Exception as exc:
        return {"items": [], "warnings": [f"PSAWDEFN search failed: {exc}"]}

    items = []
    for row in rows:
        item = dict(row)
        item["status_label"] = _AW_STATUS.get(str(item.get("status") or "").strip(), str(item.get("status") or ""))
        items.append(item)
    return {"items": items, "count": len(items), "warnings": []}


def get_approval(env_name, awdefnid):
    """Fetch an approval definition with its stages, paths, and step counts."""
    from connectors import ptmetadata
    warnings = []

    if not ptmetadata.has_table(env_name, "PSAWDEFN"):
        return {"definition": None, "stages": [], "warnings": ["PSAWDEFN not accessible"]}

    defn_rows = query(env_name, """
        SELECT AWDEFNID, DESCR, STATUS, OBJECTOWNERID, LASTUPDOPRID, LASTUPDDTTM
          FROM SYSADM.PSAWDEFN
         WHERE AWDEFNID = :id
    """, {"id": awdefnid.upper()})
    defn = dict(defn_rows[0]) if defn_rows else None
    if defn:
        defn["status_label"] = _AW_STATUS.get(str(defn.get("status") or "").strip(), "")

    stages = []
    if ptmetadata.has_table(env_name, "PSAWSTAGEDEFN"):
        try:
            stage_rows = query(env_name, """
                SELECT STAGE_NO, DESCR, PROCESS_TYPE
                  FROM SYSADM.PSAWSTAGEDEFN
                 WHERE AWDEFNID = :id
                 ORDER BY STAGE_NO
            """, {"id": awdefnid.upper()})
            for sr in stage_rows:
                stage = dict(sr)
                stage["process_type_label"] = _AW_PROCESS_TYPE.get(str(stage.get("process_type") or ""), "")
                stages.append(stage)
        except Exception as exc:
            warnings.append(f"PSAWSTAGEDEFN: {exc}")

    paths = []
    if ptmetadata.has_table(env_name, "PSAWPATHDEFN"):
        try:
            path_rows = query(env_name, """
                SELECT STAGE_NO, PATH_NO, DESCR, PROCESS_TYPE
                  FROM SYSADM.PSAWPATHDEFN
                 WHERE AWDEFNID = :id
                 ORDER BY STAGE_NO, PATH_NO
            """, {"id": awdefnid.upper()})
            for pr in path_rows:
                path = dict(pr)
                path["process_type_label"] = _AW_PROCESS_TYPE.get(str(path.get("process_type") or ""), "")
                paths.append(path)
        except Exception as exc:
            warnings.append(f"PSAWPATHDEFN: {exc}")

    steps = []
    if ptmetadata.has_table(env_name, "PSAWSTEPDEFN"):
        try:
            step_rows = query(env_name, """
                SELECT STAGE_NO, PATH_NO, STEP_NO, DESCR, PROCESS_TYPE, AWUSERLISTID
                  FROM SYSADM.PSAWSTEPDEFN
                 WHERE AWDEFNID = :id
                 ORDER BY STAGE_NO, PATH_NO, STEP_NO
            """, {"id": awdefnid.upper()})
            for sr2 in step_rows:
                step = dict(sr2)
                step["process_type_label"] = _AW_PROCESS_TYPE.get(str(step.get("process_type") or ""), "")
                steps.append(step)
        except Exception as exc:
            warnings.append(f"PSAWSTEPDEFN: {exc}")

    return {
        "definition": defn,
        "stages": stages,
        "paths": paths,
        "steps": steps,
        "counts": {
            "stages": len(stages),
            "paths": len(paths),
            "steps": len(steps),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# XML Publisher
# ---------------------------------------------------------------------------

_XPUB_DATASRC_TYPE = {
    "A": "Application Engine",
    "Q": "PS Query",
    "S": "SQL",
    "C": "Connected Query",
    "G": "Group",
    "F": "File",
}

_XPUB_TEMPLATE_FORMAT = {
    "RTF":   "RTF",
    "XSL":   "XSL",
    "XLSXI": "Excel",
    "ETEXT": "eText",
    "PDF":   "PDF Form",
    "FLASH": "Flash",
}

_XPUB_OUTPUT_FORMAT = {
    "PDF":  "PDF",
    "XLS":  "Excel",
    "RTF":  "RTF",
    "HTML": "HTML",
    "CSV":  "CSV",
    "XMLP": "XML",
    "XML":  "XML",
    "PCLP": "PCL",
}


def search_xpub_reports(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPREPORTDEFN"):
        return {"items": [], "warnings": ["PSXPREPORTDEFN not accessible"]}
    pat = f"%{q.upper()}%" if q else "%"
    try:
        rows = query(env_name, """
            SELECT REPORTID, DESCR, OBJECTOWNERID, DATASRCID
              FROM SYSADM.PSXPREPORTDEFN
             WHERE UPPER(REPORTID) LIKE :pat OR UPPER(DESCR) LIKE :pat
             ORDER BY REPORTID
             FETCH FIRST :lim ROWS ONLY
        """, {"pat": pat, "lim": limit})
        return {"items": [dict(r) for r in (rows or [])], "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def search_xpub_datasources(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPDATASRC"):
        return {"items": [], "warnings": ["PSXPDATASRC not accessible"]}
    pat = f"%{q.upper()}%" if q else "%"
    try:
        rows = query(env_name, """
            SELECT DATASRCID, DESCR, DATASRCTYPE
              FROM SYSADM.PSXPDATASRC
             WHERE UPPER(DATASRCID) LIKE :pat OR UPPER(DESCR) LIKE :pat
             ORDER BY DATASRCID
             FETCH FIRST :lim ROWS ONLY
        """, {"pat": pat, "lim": limit})
        results = []
        for r in (rows or []):
            row = dict(r)
            row["datasrctype_label"] = _XPUB_DATASRC_TYPE.get(str(row.get("datasrctype") or ""), row.get("datasrctype") or "")
            results.append(row)
        return {"items": results, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_xpub_report(env_name, reportid):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPREPORTDEFN"):
        return {"error": "not_accessible", "warnings": ["PSXPREPORTDEFN not accessible"]}
    warnings = []
    reportid = reportid.upper()
    rows = query(env_name, """
        SELECT REPORTID, DESCR, OBJECTOWNERID, DATASRCID, LASTUPDOPRID, LASTUPDDTTM
          FROM SYSADM.PSXPREPORTDEFN
         WHERE REPORTID = :id
    """, {"id": reportid})
    if not rows:
        return {"error": "not_found", "warnings": [f"Report {reportid!r} not found"]}
    defn = dict(rows[0])

    datasrc = None
    if defn.get("datasrcid") and ptmetadata.has_table(env_name, "PSXPDATASRC"):
        try:
            ds_rows = query(env_name, """
                SELECT DATASRCID, DESCR, DATASRCTYPE
                  FROM SYSADM.PSXPDATASRC
                 WHERE DATASRCID = :id
            """, {"id": defn["datasrcid"]})
            if ds_rows:
                datasrc = dict(ds_rows[0])
                datasrc["datasrctype_label"] = _XPUB_DATASRC_TYPE.get(
                    str(datasrc.get("datasrctype") or ""), datasrc.get("datasrctype") or ""
                )
        except Exception as exc:
            warnings.append(f"PSXPDATASRC: {exc}")

    templates = []
    if ptmetadata.has_table(env_name, "PSXPTEMPLDEFN"):
        try:
            tmpl_rows = query(env_name, """
                SELECT PSFBDILANGCD, TEMPLATEFORMAT, OUTPUTFORMAT, EFFDT, EFF_STATUS
                  FROM SYSADM.PSXPTEMPLDEFN
                 WHERE REPORTID = :id
                 ORDER BY PSFBDILANGCD, EFFDT DESC
            """, {"id": reportid})
            for t in (tmpl_rows or []):
                tmpl = dict(t)
                tmpl["templateformat_label"] = _XPUB_TEMPLATE_FORMAT.get(
                    str(tmpl.get("templateformat") or ""), tmpl.get("templateformat") or ""
                )
                tmpl["outputformat_label"] = _XPUB_OUTPUT_FORMAT.get(
                    str(tmpl.get("outputformat") or ""), tmpl.get("outputformat") or ""
                )
                templates.append(tmpl)
        except Exception as exc:
            warnings.append(f"PSXPTEMPLDEFN: {exc}")

    return {
        "definition": defn,
        "datasource": datasrc,
        "templates": templates,
        "counts": {"templates": len(templates)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Navigation Collections (Fluid)
# ---------------------------------------------------------------------------

_NC_LINE_TYPE = {
    "C": "Content Ref",
    "F": "Folder",
    "T": "Tile",
    "S": "Static Link",
}

_NC_EFF_STATUS = {
    "A": "Active",
    "I": "Inactive",
}


def search_nav_collections(env_name, q="", portal="EMPLOYEE", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PTNC_COLLECTION"):
        return {"items": [], "warnings": ["PTNC_COLLECTION not accessible"]}
    clauses = []
    params = {"lim": limit}
    if portal:
        clauses.append("PORTAL_NAME = :portal")
        params["portal"] = portal.upper()
    if q:
        clauses.append("(UPPER(COLL_ID) LIKE UPPER(:q) OR UPPER(COLL_TITLE) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT PORTAL_NAME, COLL_ID, COLL_TITLE, EFF_STATUS, OBJECTOWNERID, LASTUPDDTTM
              FROM SYSADM.PTNC_COLLECTION
             {where}
             ORDER BY PORTAL_NAME, COLL_ID
             FETCH FIRST :lim ROWS ONLY
        """, params)
        results = []
        for r in (rows or []):
            row = dict(r)
            row["eff_status_label"] = _NC_EFF_STATUS.get(str(row.get("eff_status") or ""), row.get("eff_status") or "")
            results.append(row)
        return {"items": results, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_nav_collection(env_name, coll_id, portal="EMPLOYEE"):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PTNC_COLLECTION"):
        return {"error": "not_accessible", "warnings": ["PTNC_COLLECTION not accessible"]}
    warnings = []
    params = {"id": coll_id.upper()}
    if portal:
        params["portal"] = portal.upper()
        portal_clause = "AND PORTAL_NAME = :portal"
    else:
        portal_clause = ""
    rows = query(env_name, f"""
        SELECT PORTAL_NAME, COLL_ID, COLL_TITLE, EFF_STATUS, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PTNC_COLLECTION
         WHERE COLL_ID = :id {portal_clause}
         ORDER BY PORTAL_NAME
         FETCH FIRST 1 ROWS ONLY
    """, params)
    if not rows:
        return {"error": "not_found", "warnings": [f"Navigation Collection {coll_id!r} not found"]}
    defn = dict(rows[0])
    defn["eff_status_label"] = _NC_EFF_STATUS.get(str(defn.get("eff_status") or ""), defn.get("eff_status") or "")

    lines = []
    if ptmetadata.has_table(env_name, "PTNC_COLL_LINE"):
        try:
            line_params = {"id": coll_id.upper()}
            if portal:
                line_params["portal"] = portal.upper()
                line_portal_clause = "AND PORTAL_NAME = :portal"
            else:
                line_portal_clause = ""
            line_rows = query(env_name, f"""
                SELECT LINE_NBR, LINE_TYPE, LABEL, PORTAL_URLTEXT
                  FROM SYSADM.PTNC_COLL_LINE
                 WHERE COLL_ID = :id {line_portal_clause}
                 ORDER BY LINE_NBR
            """, line_params)
            for lr in (line_rows or []):
                line = dict(lr)
                line["line_type_label"] = _NC_LINE_TYPE.get(str(line.get("line_type") or ""), line.get("line_type") or "")
                lines.append(line)
        except Exception as exc:
            warnings.append(f"PTNC_COLL_LINE: {exc}")

    return {
        "definition": defn,
        "lines": lines,
        "counts": {"lines": len(lines)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Event Mapping (Fluid, PT 8.55+)
# ---------------------------------------------------------------------------

def search_event_mappings(env_name, q="", status=None, limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSEFMAPPINGDEFN"):
        return {"items": [], "warnings": ["PSEFMAPPINGDEFN not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(EFMAPPINGID) LIKE UPPER(:q) OR UPPER(DESCR) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    if status:
        clauses.append("STATUS = :status")
        params["status"] = status.upper()
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT EFMAPPINGID, DESCR, STATUS, OBJECTOWNERID, LASTUPDDTTM
              FROM SYSADM.PSEFMAPPINGDEFN
             {where}
             ORDER BY EFMAPPINGID
             FETCH FIRST :lim ROWS ONLY
        """, params)
        return {"items": [dict(r) for r in (rows or [])], "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_event_mapping(env_name, efmappingid):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSEFMAPPINGDEFN"):
        return {"error": "not_accessible", "warnings": ["PSEFMAPPINGDEFN not accessible"]}
    warnings = []
    efmappingid = efmappingid.upper()
    rows = query(env_name, """
        SELECT EFMAPPINGID, DESCR, STATUS, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSEFMAPPINGDEFN
         WHERE EFMAPPINGID = :id
    """, {"id": efmappingid})
    if not rows:
        return {"error": "not_found", "warnings": [f"Event Mapping {efmappingid!r} not found"]}
    defn = dict(rows[0])

    contexts = []
    if ptmetadata.has_table(env_name, "PSEFMAPPINGCTXT"):
        try:
            ctx_rows = query(env_name, """
                SELECT SEQNO, EFCONTEXTTYPE, EFCONTEXTVALUE, APPEVENTNAME, APPEVENTHANDLER
                  FROM SYSADM.PSEFMAPPINGCTXT
                 WHERE EFMAPPINGID = :id
                 ORDER BY SEQNO
            """, {"id": efmappingid})
            contexts = [dict(r) for r in (ctx_rows or [])]
        except Exception as exc:
            warnings.append(f"PSEFMAPPINGCTXT: {exc}")

    return {
        "definition": defn,
        "contexts": contexts,
        "counts": {"contexts": len(contexts)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Related Content (Service Framework)
# ---------------------------------------------------------------------------

_RC_SERVICE_TYPE = {
    "U": "URL",
    "C": "Component",
    "S": "Script",
    "A": "Application Class",
    "P": "PeopleSoft Page",
    "I": "iScript",
    "R": "Related Action",
}


def search_related_content(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSRELCONDEFN"):
        return {"items": [], "warnings": ["PSRELCONDEFN not accessible"]}
    pat = f"%{q.upper()}%" if q else "%"
    try:
        rows = query(env_name, """
            SELECT RELCONID, DESCR, STATUS, SERVICETYPE, OBJECTOWNERID
              FROM SYSADM.PSRELCONDEFN
             WHERE UPPER(RELCONID) LIKE :pat OR UPPER(DESCR) LIKE :pat
             ORDER BY RELCONID
             FETCH FIRST :lim ROWS ONLY
        """, {"pat": pat, "lim": limit})
        results = []
        for r in (rows or []):
            row = dict(r)
            row["servicetype_label"] = _RC_SERVICE_TYPE.get(str(row.get("servicetype") or ""), row.get("servicetype") or "")
            results.append(row)
        return {"items": results, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_related_content(env_name, relconid):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSRELCONDEFN"):
        return {"error": "not_accessible", "warnings": ["PSRELCONDEFN not accessible"]}
    relconid = relconid.upper()
    rows = query(env_name, """
        SELECT RELCONID, DESCR, STATUS, SERVICETYPE, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSRELCONDEFN
         WHERE RELCONID = :id
    """, {"id": relconid})
    if not rows:
        return {"error": "not_found", "warnings": [f"Related Content {relconid!r} not found"]}
    defn = dict(rows[0])
    defn["servicetype_label"] = _RC_SERVICE_TYPE.get(str(defn.get("servicetype") or ""), defn.get("servicetype") or "")
    return {"definition": defn, "warnings": []}
