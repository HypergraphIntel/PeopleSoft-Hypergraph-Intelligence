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

    # PeopleTools 8.5x: BARITEMNAME holds the component (PNLGRPNAME equivalent)
    if "baritemname" in auth_columns:
        return {
            "column": "BARITEMNAME",
            "expr": f"{auth_alias}.baritemname",
            "join": "",
            "where": f"{auth_alias}.baritemname",
            "order": f"{auth_alias}.baritemname",
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

    raise ValueError("PSAUTHITEM has neither PNLGRPNAME nor BARITEMNAME nor PNLITEMNAME")


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


def record_usage(env_name, recname):
    """
    Find every component, page, and AE program that uses a given record.
    Queries PSPNLFIELD/PSPNLGROUP, PSPNLGRPDEFN, PSAEAPPLSTATE, PSRECFIELD directly.
    Does not rely on the Knowledge Graph — always returns live metadata.
    """
    from connectors import ptmetadata
    rec = recname.strip().upper()
    result = {"record": rec}

    # Components that display this record's fields (PSPNLFIELD -> PSPNLGROUP join)
    components = []
    if ptmetadata.has_table(env_name, "PSPNLFIELD") and ptmetadata.has_table(env_name, "PSPNLGROUP"):
        try:
            rows = query(env_name, """
                SELECT DISTINCT pg.PNLGRPNAME
                  FROM SYSADM.PSPNLFIELD pf
                  JOIN SYSADM.PSPNLGROUP  pg ON pg.PNLNAME = pf.PNLNAME
                 WHERE pf.RECNAME = :rec
                 ORDER BY pg.PNLGRPNAME
                 FETCH FIRST 200 ROWS ONLY
            """, {"rec": rec})
            components = [r.get("pnlgrpname") for r in rows if r.get("pnlgrpname")]
        except Exception as exc:
            result["components_error"] = str(exc)
    result["components"] = components
    result["component_count"] = len(components)

    # Pages that display this record's fields (PSPNLFIELD)
    pages = []
    if ptmetadata.has_table(env_name, "PSPNLFIELD"):
        try:
            rows = query(env_name, """
                SELECT DISTINCT PNLNAME
                  FROM SYSADM.PSPNLFIELD
                 WHERE RECNAME = :rec
                 ORDER BY PNLNAME
                 FETCH FIRST 200 ROWS ONLY
            """, {"rec": rec})
            pages = [r.get("pnlname") for r in rows if r.get("pnlname")]
        except Exception as exc:
            result["pages_error"] = str(exc)
    result["pages"] = pages
    result["page_count"] = len(pages)

    # Components using this record as search or add-search record (PSPNLGRPDEFN)
    search_comps = []
    if ptmetadata.has_table(env_name, "PSPNLGRPDEFN"):
        grp_cols = table_columns(env_name, "PSPNLGRPDEFN")
        has_add = "addsrchrecname" in grp_cols
        sql = (
            "SELECT DISTINCT PNLGRPNAME FROM SYSADM.PSPNLGRPDEFN"
            " WHERE SEARCHRECNAME = :rec OR ADDSRCHRECNAME = :rec"
            " ORDER BY PNLGRPNAME FETCH FIRST 100 ROWS ONLY"
            if has_add else
            "SELECT DISTINCT PNLGRPNAME FROM SYSADM.PSPNLGRPDEFN"
            " WHERE SEARCHRECNAME = :rec"
            " ORDER BY PNLGRPNAME FETCH FIRST 100 ROWS ONLY"
        )
        try:
            rows = query(env_name, sql, {"rec": rec})
            search_comps = [r.get("pnlgrpname") for r in rows if r.get("pnlgrpname")]
        except Exception:
            pass
    result["search_record_components"] = search_comps

    # AE programs using this record as their state record (PSAEAPPLSTATE)
    ae_programs = []
    if ptmetadata.has_table(env_name, "PSAEAPPLSTATE"):
        ae_cols = table_columns(env_name, "PSAEAPPLSTATE")
        if "ae_state_recname" in ae_cols:
            try:
                rows = query(env_name, """
                    SELECT DISTINCT AE_APPLID
                      FROM SYSADM.PSAEAPPLSTATE
                     WHERE UPPER(AE_STATE_RECNAME) = :rec
                     ORDER BY AE_APPLID
                     FETCH FIRST 100 ROWS ONLY
                """, {"rec": rec})
                ae_programs = [r.get("ae_applid") for r in rows if r.get("ae_applid")]
            except Exception:
                pass
    result["ae_state_programs"] = ae_programs

    # Records that inherit fields from this record as a subrecord (PSRECFIELD.DEFRECNAME)
    subrecord_derivations = []
    rec_fld_cols = table_columns(env_name, "PSRECFIELD")
    if "defrecname" in rec_fld_cols:
        try:
            rows = query(env_name, """
                SELECT DISTINCT R.RECNAME
                  FROM SYSADM.PSRECFIELD R
                 WHERE UPPER(R.DEFRECNAME) = :rec
                   AND R.RECNAME != :rec
                 ORDER BY R.RECNAME
                 FETCH FIRST 100 ROWS ONLY
            """, {"rec": rec})
            subrecord_derivations = [r.get("recname") for r in rows if r.get("recname")]
        except Exception:
            pass
    result["records_inheriting_fields"] = subrecord_derivations

    result["total_count"] = result["component_count"] + len(ae_programs) + len(subrecord_derivations)
    return result


def active_sessions(env_name, hours=8, active_minutes=30, limit=50):
    """
    Return active and recent PeopleSoft user sessions from PSACCESSLOG.

    In PeopleSoft, each page request creates its own PSACCESSLOG row where
    LOGINDTTM = LOGOUTDTTM (the row closes immediately). A user is "currently
    active" if they have had any request within the last `active_minutes` minutes.

    - currently_active: LOGOUTDTTM IS NULL (traditional open sessions, rare in PS)
    - recently_active: unique users with activity in the last `active_minutes` mins,
      with is_active=True — these users ARE currently using the system
    - recent_users: unique users in the broader `hours` window (login history)
    - by_signon_type: signon type breakdown (1=SSO/web user, 0=service/IB)
    """
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSACCESSLOG"):
        return {"error": "PSACCESSLOG not accessible", "env": env_name}

    hours = max(1, min(int(hours), 168))
    active_minutes = max(5, min(int(active_minutes), 480))
    limit = max(1, min(int(limit), 200))
    result = {"env": env_name, "window_hours": hours, "active_minutes": active_minutes}

    has_opr = ptmetadata.has_table(env_name, "PSOPRDEFN")
    log_cols = table_columns(env_name, "PSACCESSLOG")
    has_signon_type = "pt_signon_type" in log_cols

    opr_join   = "LEFT JOIN SYSADM.PSOPRDEFN o ON o.OPRID = a.OPRID" if has_opr else ""
    opr_select = ", o.OPRDEFNDESC, o.EMAILID, o.OPRCLASS" if has_opr else ""
    stype_col  = ", MAX(a.PT_SIGNON_TYPE) as pt_signon_type" if has_signon_type else ""

    # Traditional open sessions (LOGOUTDTTM IS NULL)
    try:
        open_rows = query(env_name, f"""
            SELECT a.OPRID, a.LOGINDTTM, a.LOGIPADDRESS
                   {',' + 'a.PT_SIGNON_TYPE' if has_signon_type else ''}
                   {opr_select}
              FROM SYSADM.PSACCESSLOG a {opr_join}
             WHERE a.LOGOUTDTTM IS NULL
             ORDER BY a.LOGINDTTM DESC
             FETCH FIRST {limit} ROWS ONLY
        """)
        result["currently_active"] = [dict(r) for r in open_rows]
        result["currently_active_count"] = len(open_rows)
    except Exception as exc:
        result["currently_active"] = []
        result["currently_active_count"] = 0
        result["currently_active_error"] = str(exc)

    # Recently active users — grouped by OPRID, activity within active_minutes
    # is_active=True for these users: they ARE using the system right now
    try:
        active_rows = query(env_name, f"""
            SELECT a.OPRID{opr_select}{stype_col},
                   COUNT(*) as request_count,
                   MAX(a.LOGINDTTM) as last_seen,
                   MIN(a.LOGINDTTM) as first_seen_in_window
              FROM SYSADM.PSACCESSLOG a {opr_join}
             WHERE a.LOGINDTTM >= SYSDATE - :mins/1440
             GROUP BY a.OPRID{', o.OPRDEFNDESC, o.EMAILID, o.OPRCLASS' if has_opr else ''}
             ORDER BY last_seen DESC
             FETCH FIRST {limit} ROWS ONLY
        """, {"mins": active_minutes})
        for r in active_rows:
            r = dict(r)
            r["is_active"] = True
        result["recently_active"] = [dict(r) for r in active_rows]
        result["recently_active_count"] = len(active_rows)
    except Exception as exc:
        result["recently_active"] = []
        result["recently_active_count"] = 0
        result["recently_active_error"] = str(exc)

    # Broader historical window — unique users over `hours`
    try:
        user_rows = query(env_name, f"""
            SELECT a.OPRID{opr_select}{stype_col},
                   COUNT(*) as request_count,
                   MAX(a.LOGINDTTM) as last_seen,
                   MIN(a.LOGINDTTM) as first_seen_in_window
              FROM SYSADM.PSACCESSLOG a {opr_join}
             WHERE a.LOGINDTTM >= SYSDATE - :hours/24
             GROUP BY a.OPRID{', o.OPRDEFNDESC, o.EMAILID, o.OPRCLASS' if has_opr else ''}
             ORDER BY last_seen DESC
             FETCH FIRST {limit} ROWS ONLY
        """, {"hours": hours})
        result["recent_users"] = [dict(r) for r in user_rows]
        result["unique_user_count"] = len(user_rows)
    except Exception as exc:
        result["recent_users"] = []
        result["unique_user_count"] = 0
        result["recent_users_error"] = str(exc)

    # Total request count in window
    try:
        cnt = query(env_name, "SELECT COUNT(*) as n FROM SYSADM.PSACCESSLOG WHERE LOGINDTTM >= SYSDATE - :h/24", {"h": hours})
        result["total_requests_in_window"] = cnt[0].get("n", 0) if cnt else 0
    except Exception:
        pass

    # Breakdown by signon type in window (1=SSO/web user, 0=service/IB)
    if has_signon_type:
        try:
            type_rows = query(env_name, """
                SELECT PT_SIGNON_TYPE, COUNT(DISTINCT OPRID) as unique_users, COUNT(*) as requests
                  FROM SYSADM.PSACCESSLOG
                 WHERE LOGINDTTM >= SYSDATE - :h/24
                 GROUP BY PT_SIGNON_TYPE
                 ORDER BY unique_users DESC
            """, {"h": hours})
            result["by_signon_type"] = [dict(r) for r in type_rows]
        except Exception:
            pass

    return result


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


def portal_registry_subtree(env_name, portal_name, parent_objname, max_depth=6, max_rows=1000):
    """Return the full descendant subtree of a portal folder using CONNECT BY.

    Returns a flat list of rows ordered top-down, each row includes 'depth' for
    indentation and all standard PSPRSMDEFN columns needed for display.
    Useful for building a full portal sitemap or comparing two environments'
    subtree structures in one shot.
    """
    try:
        rows = query(env_name, f"""
            SELECT PORTAL_OBJNAME, PORTAL_LABEL, PORTAL_REFTYPE,
                   PORTAL_PRNTOBJNAME, PORTAL_SEQ_NUM,
                   PORTAL_URI_SEG1, PORTAL_URI_SEG2, PORTAL_URI_SEG3,
                   PORTAL_URLTEXT, DESCR254, PORTAL_CREF_USGT,
                   LEVEL AS depth
              FROM SYSADM.PSPRSMDEFN
             WHERE LEVEL <= :maxd
            CONNECT BY NOCYCLE PRIOR PORTAL_OBJNAME = PORTAL_PRNTOBJNAME
                   AND UPPER(PORTAL_NAME) = UPPER(:pn)
            START WITH UPPER(PORTAL_PRNTOBJNAME) = UPPER(:parent)
                   AND UPPER(PORTAL_NAME) = UPPER(:pn)
             ORDER SIBLINGS BY PORTAL_SEQ_NUM NULLS LAST, PORTAL_LABEL
             FETCH FIRST :maxr ROWS ONLY
        """, {"pn": portal_name, "parent": parent_objname,
              "maxd": max(1, min(int(max_depth), 10)),
              "maxr": max(10, min(int(max_rows), 2000))})
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

    available = table_columns(env_name, "PSBCDEFN")
    if "bcname" not in available:
        return []

    candidates = ["BCNAME", "DESCR", "BCDISPLAYNAME", "BCTYPE",
                  "VERSION", "OBJECTOWNERID", "LASTUPDDTTM"]
    select_exprs = [col for col in candidates if col.lower() in available]
    if "bcpgname" in available:
        select_exprs.append("BCPGNAME AS PNLGRPNAME")
    elif "pnlgrpname" in available:
        select_exprs.append("PNLGRPNAME")
    else:
        select_exprs.append("NULL AS PNLGRPNAME")

    descr_filter = "OR UPPER(DESCR) LIKE :pattern" if "descr" in available else ""
    return query(env_name, f"""
        SELECT * FROM (
            SELECT {", ".join(select_exprs)}
              FROM SYSADM.PSBCDEFN
             WHERE UPPER(BCNAME) LIKE :pattern
                {descr_filter}
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
_MSG_SEVERITY_CODE = {0: "M", 1: "W", 2: "E", 3: "C"}


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

    cols = table_columns(env_name, "PSMSGCATDEFN")
    severity_col = "SEVERITY" if "severity" in cols else "MSG_SEVERITY" if "msg_severity" in cols else None
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
    if severity is not None and severity_col:
        clauses.append(f"{severity_col} = :severity")
        if severity_col == "MSG_SEVERITY":
            try:
                params["severity"] = _MSG_SEVERITY_CODE.get(int(severity), str(severity).upper())
            except (TypeError, ValueError):
                params["severity"] = str(severity).upper()
        else:
            params["severity"] = int(severity)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    severity_select = f"{severity_col} AS SEVERITY" if severity_col else "NULL AS SEVERITY"
    sql = f"""
        SELECT MESSAGE_SET_NBR, MESSAGE_NBR, {severity_select}, MESSAGE_TEXT, DESCRLONG
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
    cols = table_columns(env_name, "PSMSGCATDEFN")
    severity_col = "SEVERITY" if "severity" in cols else "MSG_SEVERITY" if "msg_severity" in cols else None
    severity_select = f"{severity_col} AS SEVERITY" if severity_col else "NULL AS SEVERITY"
    try:
        rows = query(env_name, f"""
            SELECT MESSAGE_SET_NBR, MESSAGE_NBR, {severity_select}, MESSAGE_TEXT, DESCRLONG
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


# ── Approval Framework (Approval Workflow Engine / EOAW) ──────────────────────
#
# Verified against the live SYSADM schema: the legacy PSAWDEFN/PSAWSTAGEDEFN/
# PSAWPATHDEFN/PSAWSTEPDEFN tables referenced by an earlier revision of this
# module do not exist. The real, populated AWE schema uses the EOAW-prefixed
# tables below. PS_EOAW_TXN is the top-level "Transaction" (what's being
# approved, e.g. Absence Cancelation); each transaction has one or more
# effective-dated PS_EOAW_PRCS "Process Definitions" (routing variants);
# each process definition has PS_EOAW_STAGE -> PS_EOAW_STEP -> PS_EOAW_PATH.

_EOAW_EFF_STATUS = {"A": "Active", "I": "Inactive"}


def search_approvals(env_name, q="", status=None, limit=100):
    """Search PS_EOAW_TXN approval transaction definitions."""
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PS_EOAW_TXN"):
        return {"items": [], "warnings": ["PS_EOAW_TXN not accessible"]}

    clauses = []
    params = {}
    if q:
        clauses.append("(UPPER(EOAWPRCS_ID) LIKE UPPER(:q) OR UPPER(DESCR) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT EOAWPRCS_ID, DESCR, OBJECTOWNERID, PACKAGEROOT, EOAWAPPR_COMPONENT
          FROM SYSADM.PS_EOAW_TXN
         {where}
         ORDER BY EOAWPRCS_ID
         FETCH FIRST :lim ROWS ONLY
    """
    params["lim"] = limit
    try:
        rows = query(env_name, sql, params)
    except Exception as exc:
        return {"items": [], "warnings": [f"PS_EOAW_TXN search failed: {exc}"]}

    items = [dict(row) for row in rows]

    if status and ptmetadata.has_table(env_name, "PS_EOAW_PRCS"):
        try:
            active_ids = {
                r["eoawprcs_id"] for r in query(env_name, """
                    SELECT DISTINCT EOAWPRCS_ID FROM SYSADM.PS_EOAW_PRCS
                     WHERE EFF_STATUS = :st
                """, {"st": status.upper()})
            }
            items = [it for it in items if it.get("eoawprcs_id") in active_ids]
        except Exception:
            pass

    return {"items": items, "count": len(items), "warnings": []}


def get_approval(env_name, eoawprcs_id):
    """Fetch an approval transaction with its process definitions, stages, steps, and paths."""
    from connectors import ptmetadata
    warnings = []
    eoawprcs_id_u = eoawprcs_id

    if not ptmetadata.has_table(env_name, "PS_EOAW_TXN"):
        return {"definition": None, "process_definitions": [], "stages": [], "steps": [], "paths": [],
                "warnings": ["PS_EOAW_TXN not accessible"]}

    defn_rows = query(env_name, """
        SELECT EOAWPRCS_ID, DESCR, OBJECTOWNERID, PACKAGEROOT, APPCLASS_PATH,
               MENUNAME, PNLNAME, EOAWAPPR_COMPONENT, EOAWENTRY_COMP,
               EOAW_EMAIL, EOAW_WORKLIST, EOAW_PUSH
          FROM SYSADM.PS_EOAW_TXN
         WHERE EOAWPRCS_ID = :id
    """, {"id": eoawprcs_id_u})
    if not defn_rows:
        return {"error": "not_found", "warnings": [f"Approval Transaction {eoawprcs_id!r} not found"]}
    defn = dict(defn_rows[0])

    process_definitions = []
    if ptmetadata.has_table(env_name, "PS_EOAW_PRCS"):
        try:
            proc_rows = query(env_name, """
                SELECT EOAWDEFN_ID, EFFDT, EFF_STATUS, DESCR, EOAWADMIN_ROLENAME,
                       EOAWAUTO_APPROVE, EOAWDEFN_DEFAULT, EOAWDEFN_PRIORITY
                  FROM SYSADM.PS_EOAW_PRCS
                 WHERE EOAWPRCS_ID = :id
                 ORDER BY EOAWDEFN_PRIORITY, EOAWDEFN_ID
            """, {"id": eoawprcs_id_u})
            for pr in proc_rows:
                row = dict(pr)
                row["eff_status_label"] = _EOAW_EFF_STATUS.get(str(row.get("eff_status") or ""), row.get("eff_status") or "")
                process_definitions.append(row)
        except Exception as exc:
            warnings.append(f"PS_EOAW_PRCS: {exc}")

    default_defn_id = None
    for pd in process_definitions:
        if pd.get("eoawdefn_default") == "Y":
            default_defn_id = pd.get("eoawdefn_id")
            break
    if default_defn_id is None:
        active = [pd for pd in process_definitions if pd.get("eff_status") == "A"]
        if active or process_definitions:
            default_defn_id = (active or process_definitions)[0].get("eoawdefn_id")

    stages = []
    steps = []
    paths = []
    if default_defn_id is not None:
        if ptmetadata.has_table(env_name, "PS_EOAW_STAGE"):
            try:
                stage_rows = query(env_name, """
                    SELECT EOAWSTAGE_NBR, DESCR, EOAWLEVEL, SEQ_NBR
                      FROM SYSADM.PS_EOAW_STAGE
                     WHERE EOAWPRCS_ID = :id AND EOAWDEFN_ID = :defn
                     ORDER BY EOAWSTAGE_NBR
                """, {"id": eoawprcs_id_u, "defn": default_defn_id})
                stages = [dict(r) for r in (stage_rows or [])]
            except Exception as exc:
                warnings.append(f"PS_EOAW_STAGE: {exc}")

        if ptmetadata.has_table(env_name, "PS_EOAW_STEP"):
            try:
                step_rows = query(env_name, """
                    SELECT EOAWSTAGE_NBR, EOAWSTEP_NBR, EOAWPATH_ID, DESCR,
                           EOAWROLENAME, EOAWAPPROVER_LIST, EOAWMIN_APPROVERS, EOAWSELF_APPROVAL
                      FROM SYSADM.PS_EOAW_STEP
                     WHERE EOAWPRCS_ID = :id AND EOAWDEFN_ID = :defn
                     ORDER BY EOAWSTAGE_NBR, EOAWSTEP_NBR
                """, {"id": eoawprcs_id_u, "defn": default_defn_id})
                steps = [dict(r) for r in (step_rows or [])]
            except Exception as exc:
                warnings.append(f"PS_EOAW_STEP: {exc}")

        if ptmetadata.has_table(env_name, "PS_EOAW_PATH"):
            try:
                path_rows = query(env_name, """
                    SELECT EOAWSTAGE_NBR, EOAWPATH_ID, DESCR, EOAWNUMBER_DAYS,
                           EOAWNUMBER_HOURS, EOAWESCALATN_OPTN
                      FROM SYSADM.PS_EOAW_PATH
                     WHERE EOAWPRCS_ID = :id AND EOAWDEFN_ID = :defn
                     ORDER BY EOAWSTAGE_NBR, EOAWPATH_ID
                """, {"id": eoawprcs_id_u, "defn": default_defn_id})
                paths = [dict(r) for r in (path_rows or [])]
            except Exception as exc:
                warnings.append(f"PS_EOAW_PATH: {exc}")

    return {
        "definition": defn,
        "process_definitions": process_definitions,
        "default_process_definition": default_defn_id,
        "stages": stages,
        "steps": steps,
        "paths": paths,
        "counts": {
            "process_definitions": len(process_definitions),
            "stages": len(stages),
            "steps": len(steps),
            "paths": len(paths),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# XML Publisher
#
# Verified against the live SYSADM schema: the legacy PSXPREPORTDEFN table
# referenced by an earlier revision of this module does not exist. The real,
# populated XML Publisher schema is PSXPRPTDEFN (report definitions, keyed by
# REPORT_DEFN_ID), linked to PSXPDATASRC (data sources, keyed by DS_ID) and
# PSXPRPTCAT (report categories, keyed by REPORT_CATEGORY_ID). Templates are
# linked via PSXPRPTTMPL (REPORT_DEFN_ID -> TMPLDEFN_ID) to PSXPTMPLDEFN
# (template definitions).
# ---------------------------------------------------------------------------

_XPUB_DATASRC_TYPE = {
    "XML": "XML",
    "CQR": "Connected Query",
    "QRY": "PS Query",
    "XMD": "XML Data",
    "RST": "REST",
}

_XPUB_REPORT_STATUS = {
    "A": "Active",
    "I": "Inactive",
}


def search_xpub_reports(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPRPTDEFN"):
        return {"items": [], "warnings": ["PSXPRPTDEFN not accessible"]}
    pat = f"%{q.upper()}%" if q else "%"
    try:
        rows = query(env_name, """
            SELECT REPORT_DEFN_ID, DESCR, OBJECTOWNERID, DS_ID, DS_TYPE,
                   REPORT_CATEGORY_ID, PT_REPORT_STATUS, PT_TEMPLATE_TYPE
              FROM SYSADM.PSXPRPTDEFN
             WHERE UPPER(REPORT_DEFN_ID) LIKE :pat OR UPPER(DESCR) LIKE :pat
             ORDER BY REPORT_DEFN_ID
             FETCH FIRST :lim ROWS ONLY
        """, {"pat": pat, "lim": limit})
        items = []
        for r in (rows or []):
            row = dict(r)
            row["pt_report_status_label"] = _XPUB_REPORT_STATUS.get(
                str(row.get("pt_report_status") or ""), row.get("pt_report_status") or ""
            )
            items.append(row)
        return {"items": items, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def search_xpub_datasources(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPDATASRC"):
        return {"items": [], "warnings": ["PSXPDATASRC not accessible"]}
    pat = f"%{q.upper()}%" if q else "%"
    try:
        rows = query(env_name, """
            SELECT DS_ID, DESCR, DS_TYPE, ACTIVE_FLAG, OBJECTOWNERID
              FROM SYSADM.PSXPDATASRC
             WHERE UPPER(DS_ID) LIKE :pat OR UPPER(DESCR) LIKE :pat
             ORDER BY DS_ID
             FETCH FIRST :lim ROWS ONLY
        """, {"pat": pat, "lim": limit})
        results = []
        for r in (rows or []):
            row = dict(r)
            row["ds_type_label"] = _XPUB_DATASRC_TYPE.get(str(row.get("ds_type") or ""), row.get("ds_type") or "")
            results.append(row)
        return {"items": results, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_xpub_report(env_name, report_defn_id):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSXPRPTDEFN"):
        return {"error": "not_accessible", "warnings": ["PSXPRPTDEFN not accessible"]}
    warnings = []
    rows = query(env_name, """
        SELECT REPORT_DEFN_ID, DESCR, OBJECTOWNERID, DS_ID, DS_TYPE,
               REPORT_CATEGORY_ID, PT_REPORT_STATUS, PT_TEMPLATE_TYPE,
               LASTUPDOPRID, LASTUPDDTTM
          FROM SYSADM.PSXPRPTDEFN
         WHERE REPORT_DEFN_ID = :id
    """, {"id": report_defn_id})
    if not rows:
        return {"error": "not_found", "warnings": [f"Report {report_defn_id!r} not found"]}
    defn = dict(rows[0])
    defn["pt_report_status_label"] = _XPUB_REPORT_STATUS.get(
        str(defn.get("pt_report_status") or ""), defn.get("pt_report_status") or ""
    )

    datasrc = None
    if defn.get("ds_id") and ptmetadata.has_table(env_name, "PSXPDATASRC"):
        try:
            ds_rows = query(env_name, """
                SELECT DS_ID, DESCR, DS_TYPE, ACTIVE_FLAG
                  FROM SYSADM.PSXPDATASRC
                 WHERE DS_ID = :id
            """, {"id": defn["ds_id"]})
            if ds_rows:
                datasrc = dict(ds_rows[0])
                datasrc["ds_type_label"] = _XPUB_DATASRC_TYPE.get(
                    str(datasrc.get("ds_type") or ""), datasrc.get("ds_type") or ""
                )
        except Exception as exc:
            warnings.append(f"PSXPDATASRC: {exc}")

    category = None
    if defn.get("report_category_id") and ptmetadata.has_table(env_name, "PSXPRPTCAT"):
        try:
            cat_rows = query(env_name, """
                SELECT REPORT_CATEGORY_ID, DESCR, OBJECTOWNERID
                  FROM SYSADM.PSXPRPTCAT
                 WHERE REPORT_CATEGORY_ID = :id
            """, {"id": defn["report_category_id"]})
            if cat_rows:
                category = dict(cat_rows[0])
        except Exception as exc:
            warnings.append(f"PSXPRPTCAT: {exc}")

    templates = []
    if ptmetadata.has_table(env_name, "PSXPRPTTMPL") and ptmetadata.has_table(env_name, "PSXPTMPLDEFN"):
        try:
            tmpl_rows = query(env_name, """
                SELECT l.TMPLDEFN_ID, l.IS_DEFAULT, d.DESCR, d.PT_TEMPLATE_TYPE,
                       d.DIST_CHANNEL, d.TMPLLANGCD
                  FROM SYSADM.PSXPRPTTMPL l
                  JOIN SYSADM.PSXPTMPLDEFN d ON d.TMPLDEFN_ID = l.TMPLDEFN_ID
                 WHERE l.REPORT_DEFN_ID = :id
                 ORDER BY l.IS_DEFAULT DESC, d.TMPLDEFN_ID
            """, {"id": report_defn_id})
            templates = [dict(t) for t in (tmpl_rows or [])]
        except Exception as exc:
            warnings.append(f"PSXPRPTTMPL/PSXPTMPLDEFN: {exc}")

    output_formats = []
    if ptmetadata.has_table(env_name, "PSXPRPTOUTFMT"):
        try:
            fmt_rows = query(env_name, """
                SELECT PT_FORMAT_TYPE, IS_DEFAULT
                  FROM SYSADM.PSXPRPTOUTFMT
                 WHERE REPORT_DEFN_ID = :id
                 ORDER BY IS_DEFAULT DESC, PT_FORMAT_TYPE
            """, {"id": report_defn_id})
            output_formats = [dict(f) for f in (fmt_rows or [])]
        except Exception as exc:
            warnings.append(f"PSXPRPTOUTFMT: {exc}")

    return {
        "definition": defn,
        "datasource": datasrc,
        "category": category,
        "templates": templates,
        "output_formats": output_formats,
        "counts": {"templates": len(templates), "output_formats": len(output_formats)},
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


# ---------------------------------------------------------------------------
# Search Definitions (PeopleSoft Search Framework, PTSF)
#
# Verified against the live SYSADM schema: the legacy PTSF_SRCDEFN/PTSF_SRCMAP
# tables referenced by an earlier revision of this module do not exist. The
# real, populated Search Framework schema is PSPTSF_SD (Search Definitions).
# Note PSPTSF_SD.APPCLASSID is blank on every row in the live data; the actual
# unique key is PTSF_SOURCE_NAME. Each definition references a Search Business
# Object (PTSF_SBO_NAME) whose indexed/displayed fields live in
# PSPTSF_SD_ATTR and whose component/page-group registrations live in
# PSPTSF_SD_PNLGP, both keyed by PTSF_SBO_NAME (not by the source name).
# ---------------------------------------------------------------------------

_SRCH_SOURCE_TYPE = {
    "A": "Application Class",
    "C": "Connected Query",
    "Q": "PS Query",
}


def search_search_definitions(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTSF_SD"):
        return {"items": [], "warnings": ["PSPTSF_SD not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(PTSF_SOURCE_NAME) LIKE UPPER(:q) OR UPPER(DESCR100) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT PTSF_SOURCE_NAME, DESCR100, PTSF_SOURCE_TYPE, PTSF_SBO_NAME, OBJECTOWNERID
              FROM SYSADM.PSPTSF_SD
             {where}
             ORDER BY PTSF_SOURCE_NAME
             FETCH FIRST :lim ROWS ONLY
        """, params)
        results = []
        for r in (rows or []):
            row = dict(r)
            row["ptsf_source_type_label"] = _SRCH_SOURCE_TYPE.get(
                str(row.get("ptsf_source_type") or ""), row.get("ptsf_source_type") or ""
            )
            results.append(row)
        return {"items": results, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_search_definition(env_name, source_name):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTSF_SD"):
        return {"error": "not_accessible", "warnings": ["PSPTSF_SD not accessible"]}
    warnings = []
    rows = query(env_name, """
        SELECT PTSF_SOURCE_NAME, DESCR100, PTSF_SOURCE_TYPE, PTSF_SBO_NAME,
               OBJECTOWNERID, PACKAGEROOT, PTSF_ISGBLSRCH, PTSF_KEYWORDS,
               PTSF_CONTENT_URL, LASTUPDDTTM, LASTUPDOPRID, LASTREFRESHDTTM
          FROM SYSADM.PSPTSF_SD
         WHERE PTSF_SOURCE_NAME = :id
    """, {"id": source_name})
    if not rows:
        return {"error": "not_found", "warnings": [f"Search Definition {source_name!r} not found"]}
    defn = dict(rows[0])
    defn["ptsf_source_type_label"] = _SRCH_SOURCE_TYPE.get(
        str(defn.get("ptsf_source_type") or ""), defn.get("ptsf_source_type") or ""
    )
    sbo_name = defn.get("ptsf_sbo_name")

    fields = []
    if sbo_name and ptmetadata.has_table(env_name, "PSPTSF_SD_ATTR"):
        try:
            fld_rows = query(env_name, """
                SELECT PTSF_SRCATTR_NAME, QRYFLDNAME, QRYNAME, SEQNUM,
                       PTSF_ISFIELDTOIDX, PTSF_ISFLDTODISPL, PTSF_IS_FACETED
                  FROM SYSADM.PSPTSF_SD_ATTR
                 WHERE PTSF_SBO_NAME = :sbo
                 ORDER BY SEQNUM
            """, {"sbo": sbo_name})
            fields = [dict(r) for r in (fld_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_SD_ATTR: {exc}")

    panel_groups = []
    if sbo_name and ptmetadata.has_table(env_name, "PSPTSF_SD_PNLGP"):
        try:
            pg_rows = query(env_name, """
                SELECT PNLGRPNAME, MARKET, PTSF_SRCH_CRITERIA
                  FROM SYSADM.PSPTSF_SD_PNLGP
                 WHERE PTSF_SBO_NAME = :sbo
                 ORDER BY MARKET
            """, {"sbo": sbo_name})
            panel_groups = [dict(r) for r in (pg_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_SD_PNLGP: {exc}")

    return {
        "definition": defn,
        "fields": fields,
        "panel_groups": panel_groups,
        "counts": {"fields": len(fields), "panel_groups": len(panel_groups)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Drop Zones (PeopleTools page composer drop zones)
# ---------------------------------------------------------------------------

def search_drop_zones(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTDZDEFN"):
        return {"items": [], "warnings": ["PSPTDZDEFN not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(DZNAME) LIKE UPPER(:q) OR UPPER(DESCR) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT DZNAME, DESCR, OBJECTOWNERID
              FROM SYSADM.PSPTDZDEFN
             {where}
             ORDER BY DZNAME
             FETCH FIRST :lim ROWS ONLY
        """, params)
        return {"items": [dict(r) for r in (rows or [])], "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_drop_zone(env_name, dzname):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTDZDEFN"):
        return {"error": "not_accessible", "warnings": ["PSPTDZDEFN not accessible"]}
    warnings = []
    dzname = dzname.upper()
    rows = query(env_name, """
        SELECT DZNAME, DESCR, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSPTDZDEFN
         WHERE DZNAME = :id
    """, {"id": dzname})
    if not rows:
        return {"error": "not_found", "warnings": [f"Drop Zone {dzname!r} not found"]}
    defn = dict(rows[0])

    components = []
    if ptmetadata.has_table(env_name, "PSPTDZCOMP"):
        try:
            comp_rows = query(env_name, """
                SELECT PNLGRPNAME, COMPONENT
                  FROM SYSADM.PSPTDZCOMP
                 WHERE DZNAME = :id
                 ORDER BY PNLGRPNAME
            """, {"id": dzname})
            components = [dict(r) for r in (comp_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTDZCOMP: {exc}")

    pages = []
    if ptmetadata.has_table(env_name, "PSPTDZPNL"):
        try:
            pnl_rows = query(env_name, """
                SELECT PNLNAME, PAGE
                  FROM SYSADM.PSPTDZPNL
                 WHERE DZNAME = :id
                 ORDER BY PNLNAME
            """, {"id": dzname})
            pages = [dict(r) for r in (pnl_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTDZPNL: {exc}")

    items = []
    if ptmetadata.has_table(env_name, "PSPTDZITEM"):
        try:
            item_rows = query(env_name, """
                SELECT OBJECTVALUE1, OBJECTVALUE2, SEQNO
                  FROM SYSADM.PSPTDZITEM
                 WHERE DZNAME = :id
                 ORDER BY SEQNO
            """, {"id": dzname})
            items = [dict(r) for r in (item_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTDZITEM: {exc}")

    return {
        "definition": defn,
        "components": components,
        "pages": pages,
        "items": items,
        "counts": {"components": len(components), "pages": len(pages), "items": len(items)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Search Categories (PeopleSoft Search Framework, PTSF)
#
# Verified against the live SYSADM schema: the legacy PTSF_SRCAT table
# referenced by an earlier revision of this module does not exist. The real,
# populated schema is PSPTSF_SRCCAT, keyed by PTSF_SRCCAT_NAME. Categories
# reference a Search Business Object (PTSF_SBO_NAME) via PSPTSF_CATPTSD —
# the same SBO concept used by Search Definitions (see PSPTSF_SD above).
# Display/advanced search fields and facets live in PSPTSF_CATDSPFD,
# PSPTSF_CATADVFD, and PSPTSF_CATFACET, all keyed by PTSF_SRCCAT_NAME.
# ---------------------------------------------------------------------------

def search_search_categories(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTSF_SRCCAT"):
        return {"items": [], "warnings": ["PSPTSF_SRCCAT not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(PTSF_SRCCAT_NAME) LIKE UPPER(:q) OR UPPER(DESCR100) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT PTSF_SRCCAT_NAME, DESCR100, MARKET, OBJECTOWNERID, PTSF_SRCH_ENG
              FROM SYSADM.PSPTSF_SRCCAT
             {where}
             ORDER BY PTSF_SRCCAT_NAME
             FETCH FIRST :lim ROWS ONLY
        """, params)
        return {"items": [dict(r) for r in (rows or [])], "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_search_category(env_name, srccat_name):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTSF_SRCCAT"):
        return {"error": "not_accessible", "warnings": ["PSPTSF_SRCCAT not accessible"]}
    warnings = []
    rows = query(env_name, """
        SELECT PTSF_SRCCAT_NAME, DESCR100, MARKET, OBJECTOWNERID, PACKAGEROOT,
               MENUNAME, PNLGRPNAME, PTSF_SRCH_ENG, PTSF_DISPLAY_TYPE,
               PTSF_ISGBLSRCH, PTSF_ALLOW_DUPS, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSPTSF_SRCCAT
         WHERE PTSF_SRCCAT_NAME = :id
    """, {"id": srccat_name})
    if not rows:
        return {"error": "not_found", "warnings": [f"Search Category {srccat_name!r} not found"]}
    defn = dict(rows[0])

    sbo_links = []
    if ptmetadata.has_table(env_name, "PSPTSF_CATPTSD"):
        try:
            sbo_rows = query(env_name, """
                SELECT PTSF_SBO_NAME, MSGNODENAME
                  FROM SYSADM.PSPTSF_CATPTSD
                 WHERE PTSF_SRCCAT_NAME = :id
                 ORDER BY PTSF_SBO_NAME
            """, {"id": srccat_name})
            sbo_links = [dict(r) for r in (sbo_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_CATPTSD: {exc}")

    display_fields = []
    if ptmetadata.has_table(env_name, "PSPTSF_CATDSPFD"):
        try:
            fld_rows = query(env_name, """
                SELECT PTSF_SRCATTR_NAME, PTSF_FLD_DISP_TYPE, SEQNO
                  FROM SYSADM.PSPTSF_CATDSPFD
                 WHERE PTSF_SRCCAT_NAME = :id
                 ORDER BY SEQNO
            """, {"id": srccat_name})
            display_fields = [dict(r) for r in (fld_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_CATDSPFD: {exc}")

    advanced_fields = []
    if ptmetadata.has_table(env_name, "PSPTSF_CATADVFD"):
        try:
            fld_rows = query(env_name, """
                SELECT PTSF_SRCATTR_NAME, SEQNO
                  FROM SYSADM.PSPTSF_CATADVFD
                 WHERE PTSF_SRCCAT_NAME = :id
                 ORDER BY SEQNO
            """, {"id": srccat_name})
            advanced_fields = [dict(r) for r in (fld_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_CATADVFD: {exc}")

    facets = []
    if ptmetadata.has_table(env_name, "PSPTSF_CATFACET"):
        try:
            facet_rows = query(env_name, """
                SELECT PTSF_FACET_NAME, PTSF_FACET_ORDER, PTSF_FCT_MULTISEL, SEQNO
                  FROM SYSADM.PSPTSF_CATFACET
                 WHERE PTSF_SRCCAT_NAME = :id
                 ORDER BY PTSF_FACET_ORDER
            """, {"id": srccat_name})
            facets = [dict(r) for r in (facet_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTSF_CATFACET: {exc}")

    return {
        "definition": defn,
        "sbo_links": sbo_links,
        "display_fields": display_fields,
        "advanced_fields": advanced_fields,
        "facets": facets,
        "counts": {
            "sbo_links": len(sbo_links),
            "display_fields": len(display_fields),
            "advanced_fields": len(advanced_fields),
            "facets": len(facets),
        },
        "warnings": warnings,
    }

# ---------------------------------------------------------------------------
# PivotGrid (PSPGCORE)
#
# Verified against the live SYSADM schema 2026-06-30.  PSPGCORE is the
# PivotGrid definition header (154 rows in HCM, all type PUB).  Keyed by
# PTPG_PGRIDNAME.  Data source is either a PS Query (PSQUERY, 140 rows) or
# a Component (COMPONENT, 14 rows).  For PSQUERY grids the query name is in
# PSPGSETTINGS WHERE PTPG_DSNAME='QRYNAME'.  Data model columns come from
# PSPGMODEL (3228 rows, keyed by PTPG_PGRIDNAME).  Display options come from
# PSPGDISPOPT (154 rows, 1:1 with header).  NUI options from PSPGNUIOPT
# (137 rows, subset with query/access config).
# ---------------------------------------------------------------------------

_PTPG_DSTYPE = {"PSQUERY": "PS Query", "COMPONENT": "Component"}
_PTPG_COLTYPE = {"DIM": "Dimension", "DISO": "Display Only", "VAL": "Value"}


def search_pivot_grids(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPGCORE"):
        return {"items": [], "warnings": ["PSPGCORE not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(PTPG_PGRIDNAME) LIKE UPPER(:q) OR UPPER(PTPG_PGRIDTITLE) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT PTPG_PGRIDNAME, PTPG_PGRIDTITLE, PTPG_DSTYPE, PTPG_PGRIDTYPE,
                   OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSPGCORE
             {where}
             ORDER BY PTPG_PGRIDNAME
             FETCH FIRST :lim ROWS ONLY
        """, params)
        items = []
        for r in (rows or []):
            item = dict(r)
            item["ptpg_dstype_label"] = _PTPG_DSTYPE.get(item.get("ptpg_dstype"), item.get("ptpg_dstype"))
            items.append(item)
        return {"items": items, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_pivot_grid(env_name, pgridname):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPGCORE"):
        return {"error": "not_accessible", "warnings": ["PSPGCORE not accessible"]}
    warnings = []

    rows = query(env_name, """
        SELECT PTPG_PGRIDNAME, PTPG_PGRIDTITLE, PTPG_DSTYPE, PTPG_PGRIDTYPE,
               OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID, DESCRLONG,
               PTPG_ISVALIDMODEL, PTPG_ISSIMPL_WIZ, PTPG_USESQLTYPE
          FROM SYSADM.PSPGCORE
         WHERE PTPG_PGRIDNAME = :id
    """, {"id": pgridname})
    if not rows:
        return {"error": "not_found", "warnings": [f"PivotGrid {pgridname!r} not found"]}
    defn = dict(rows[0])
    defn["ptpg_dstype_label"] = _PTPG_DSTYPE.get(defn.get("ptpg_dstype"), defn.get("ptpg_dstype"))

    # Data source name (query name for PSQUERY type)
    datasource_name = None
    if ptmetadata.has_table(env_name, "PSPGSETTINGS"):
        try:
            sr = query(env_name, """
                SELECT PTPG_DSVALUE FROM SYSADM.PSPGSETTINGS
                 WHERE PTPG_PGRIDNAME = :id AND PTPG_DSNAME = 'QRYNAME'
                 FETCH FIRST 1 ROWS ONLY
            """, {"id": pgridname})
            if sr:
                datasource_name = str(sr[0].get("ptpg_dsvalue") or "").strip() or None
        except Exception as exc:
            warnings.append(f"PSPGSETTINGS: {exc}")

    # Data model columns
    columns = []
    if ptmetadata.has_table(env_name, "PSPGMODEL"):
        try:
            col_rows = query(env_name, """
                SELECT PTPG_DSCOLUMN, PTPG_COLMNTYPE, PTPG_AGGREGATE, PTPG_FORMAT,
                       PTPG_TOTAL
                  FROM SYSADM.PSPGMODEL
                 WHERE PTPG_PGRIDNAME = :id
                 ORDER BY PTPG_DSCOLUMN
            """, {"id": pgridname})
            for r in (col_rows or []):
                item = dict(r)
                item["ptpg_colmntype_label"] = _PTPG_COLTYPE.get(
                    str(item.get("ptpg_colmntype") or "").strip(),
                    str(item.get("ptpg_colmntype") or "").strip()
                )
                columns.append(item)
        except Exception as exc:
            warnings.append(f"PSPGMODEL: {exc}")

    # NUI options (query access group, view name)
    nui_opts = {}
    if ptmetadata.has_table(env_name, "PSPGNUIOPT"):
        try:
            nr = query(env_name, """
                SELECT PTPG_VIEWNAME, ACCESS_GROUP, PTPG_COMPMAPPING,
                       PTPG_ALLOWPUBTILE, PTPG_ALLOWSHARE
                  FROM SYSADM.PSPGNUIOPT
                 WHERE PTPG_PGRIDNAME = :id
                 FETCH FIRST 1 ROWS ONLY
            """, {"id": pgridname})
            if nr:
                nui_opts = dict(nr[0])
        except Exception as exc:
            warnings.append(f"PSPGNUIOPT: {exc}")

    return {
        "definition": defn,
        "datasource_name": datasource_name,
        "columns": columns,
        "nui_opts": nui_opts,
        "counts": {"columns": len(columns)},
        "warnings": warnings,
    }

# ---------------------------------------------------------------------------
# Connected Query (PSCONQRSDEFN)
#
# Verified against the live SYSADM schema 2026-06-30.  PSCONQRSDEFN is the
# Connected Query definition header (97 rows in HCM), keyed by CONQRSNAME.
# PT_REPORT_STATUS: A=Active, I=Inactive.  The query composition (parent/child
# PS Query links) lives in PSCONQRSMAP (356 rows): row with blank QRYNAMEPARENT
# is the root query; subsequent rows link child queries to their parent by
# query name.  Join field relationships are in PSCONQRSFLDREL (597 rows): each
# row (same SEQNUM as the PSCONQRSMAP row) holds QRYFLDNAMEPAR / QRYFLDNAMECHILD
# field references; root query row (seqnum=1) has blank fields since it has no
# parent join.
# ---------------------------------------------------------------------------

_CONQRS_STATUS = {"A": "Active", "I": "Inactive"}


def search_connected_queries(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSCONQRSDEFN"):
        return {"items": [], "warnings": ["PSCONQRSDEFN not accessible"]}
    clauses = []
    params = {"lim": limit}
    if q:
        clauses.append("(UPPER(CONQRSNAME) LIKE UPPER(:q) OR UPPER(DESCR) LIKE UPPER(:q2))")
        params["q"] = f"%{q}%"
        params["q2"] = f"%{q}%"
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = query(env_name, f"""
            SELECT CONQRSNAME, DESCR, PT_REPORT_STATUS, OBJECTOWNERID, LASTUPDDTTM
              FROM SYSADM.PSCONQRSDEFN
             {where}
             ORDER BY CONQRSNAME
             FETCH FIRST :lim ROWS ONLY
        """, params)
        items = []
        for r in (rows or []):
            item = dict(r)
            item["pt_report_status_label"] = _CONQRS_STATUS.get(
                str(item.get("pt_report_status") or "").strip(), "")
            items.append(item)
        return {"items": items, "warnings": []}
    except Exception as exc:
        return {"items": [], "warnings": [str(exc)]}


def get_connected_query(env_name, conqrsname):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSCONQRSDEFN"):
        return {"error": "not_accessible", "warnings": ["PSCONQRSDEFN not accessible"]}
    warnings = []

    rows = query(env_name, """
        SELECT CONQRSNAME, DESCR, PT_REPORT_STATUS, OBJECTOWNERID,
               VERSION, LASTUPDDTTM, LASTUPDOPRID, DESCRLONG
          FROM SYSADM.PSCONQRSDEFN
         WHERE CONQRSNAME = :id
    """, {"id": conqrsname})
    if not rows:
        return {"error": "not_found", "warnings": [f"Connected Query {conqrsname!r} not found"]}
    defn = dict(rows[0])
    defn["pt_report_status_label"] = _CONQRS_STATUS.get(
        str(defn.get("pt_report_status") or "").strip(), "")

    # Query composition map (parent-child query chain)
    query_map = []
    if ptmetadata.has_table(env_name, "PSCONQRSMAP"):
        try:
            map_rows = query(env_name, """
                SELECT SEQNUM, QRYNAMEPARENT, QRYNAMECHILD, EFFDTCONDTYPE,
                       CQ_SUPPORTSORDERBY, RECNAME
                  FROM SYSADM.PSCONQRSMAP
                 WHERE CONQRSNAME = :id
                 ORDER BY SEQNUM
            """, {"id": conqrsname})
            query_map = [dict(r) for r in (map_rows or [])]
        except Exception as exc:
            warnings.append(f"PSCONQRSMAP: {exc}")

    # Field join relationships (skip root row which has blank fields)
    field_rels = []
    if ptmetadata.has_table(env_name, "PSCONQRSFLDREL"):
        try:
            fld_rows = query(env_name, """
                SELECT SEQNUM, QRYFLDNAMEPAR, QRYFLDNAMECHILD, SELCOUNT
                  FROM SYSADM.PSCONQRSFLDREL
                 WHERE CONQRSNAME = :id
                   AND TRIM(QRYFLDNAMECHILD) IS NOT NULL
                   AND TRIM(QRYFLDNAMECHILD) != ' '
                 ORDER BY SEQNUM
            """, {"id": conqrsname})
            field_rels = [dict(r) for r in (fld_rows or [])]
        except Exception as exc:
            warnings.append(f"PSCONQRSFLDREL: {exc}")

    return {
        "definition": defn,
        "query_map": query_map,
        "field_rels": field_rels,
        "counts": {
            "sub_queries": len(query_map),
            "field_joins": len(field_rels),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Process Definitions (PS_PRCSDEFN)
# ---------------------------------------------------------------------------

_PRCS_RUNLOC = {"0": "Server", "1": "Client", "2": "Server"}
_PRCS_OUTDEST = {
    "5": "File", "6": "Printer", "8": "E-mail", "9": "Web", "10": "Window",
    "11": "Default", "12": "Feed",
}


def search_process_definitions(env_name, q="", prcstype="", limit=100):
    from connectors import ptmetadata
    warnings = []
    items = []
    if not ptmetadata.has_table(env_name, "PS_PRCSDEFN"):
        warnings.append("PS_PRCSDEFN not found in schema")
        return {"items": [], "warnings": warnings}
    try:
        sql = """
            SELECT PRCSTYPE, PRCSNAME, DESCR, PRCSCATEGORY, RESTARTENABLED,
                   LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PS_PRCSDEFN
             WHERE (:q IS NULL OR UPPER(PRCSNAME) LIKE UPPER(:q)
                    OR UPPER(DESCR) LIKE UPPER(:q))
               AND (:pt IS NULL OR PRCSTYPE = :pt)
             ORDER BY PRCSTYPE, PRCSNAME
             FETCH FIRST :lim ROWS ONLY
        """
        q_param = f"%{q}%" if q else None
        pt_param = prcstype if prcstype else None
        rows = query(env_name, sql, {"q": q_param, "pt": pt_param, "lim": limit})
        for r in rows:
            d = dict(r)
            d["_key"] = f"{d['prcstype']}~{d['prcsname']}"
            items.append(d)
    except Exception as exc:
        warnings.append(f"PS_PRCSDEFN search: {exc}")
    return {"items": items, "warnings": warnings}


def get_process_definition(env_name, compound_key):
    """compound_key is '{prcstype}~{prcsname}'"""
    from connectors import ptmetadata
    warnings = []
    if "~" not in compound_key:
        return {"error": f"Invalid key format: {compound_key!r}"}

    sep = compound_key.index("~")
    prcstype = compound_key[:sep]
    prcsname = compound_key[sep + 1:]

    if not ptmetadata.has_table(env_name, "PS_PRCSDEFN"):
        return {"error": "PS_PRCSDEFN not found"}

    # Header
    defn = None
    try:
        rows = query(env_name, """
            SELECT PRCSTYPE, PRCSNAME, DESCR, PRCSCATEGORY, PARMLIST,
                   RESTARTENABLED, RETRYCOUNT, TIMEOUTMINUTES, MAXCONCURRENT,
                   RUNLOCATION, SERVERNAME, MSGLOGTBL, RQSTTBL, RECURNAME,
                   RETENTIONDAYS, PT_RETENTIONDAYS, OUTDESTTYPE, OUTDEST,
                   PRCSPRIORITY, PRCSFILENAME, LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PS_PRCSDEFN
             WHERE PRCSTYPE = :pt AND PRCSNAME = :pn
        """, {"pt": prcstype, "pn": prcsname})
        if not rows:
            return {"error": f"Process definition not found: {compound_key}"}
        defn = dict(rows[0])
    except Exception as exc:
        return {"error": str(exc)}

    # Run control pages
    run_cntl_pages = []
    if ptmetadata.has_table(env_name, "PS_PRCSDEFNPNL"):
        try:
            pnl_rows = query(env_name, """
                SELECT PNLGRPNAME FROM SYSADM.PS_PRCSDEFNPNL
                 WHERE PRCSTYPE = :pt AND PRCSNAME = :pn
                   AND TRIM(PNLGRPNAME) IS NOT NULL
                   AND TRIM(PNLGRPNAME) != ' '
                 ORDER BY PNLGRPNAME
            """, {"pt": prcstype, "pn": prcsname})
            run_cntl_pages = [r["pnlgrpname"].strip() for r in (pnl_rows or []) if r.get("pnlgrpname", "").strip()]
        except Exception as exc:
            warnings.append(f"PS_PRCSDEFNPNL: {exc}")

    # Process groups
    prcs_groups = []
    if ptmetadata.has_table(env_name, "PS_PRCSDEFNGRP"):
        try:
            grp_rows = query(env_name, """
                SELECT PRCSGRP FROM SYSADM.PS_PRCSDEFNGRP
                 WHERE PRCSTYPE = :pt AND PRCSNAME = :pn
                 ORDER BY PRCSGRP
            """, {"pt": prcstype, "pn": prcsname})
            prcs_groups = [r["prcsgrp"].strip() for r in (grp_rows or []) if r.get("prcsgrp", "").strip()]
        except Exception as exc:
            warnings.append(f"PS_PRCSDEFNGRP: {exc}")

    return {
        "definition": defn,
        "run_cntl_pages": run_cntl_pages,
        "prcs_groups": prcs_groups,
        "counts": {
            "run_cntl_pages": len(run_cntl_pages),
            "prcs_groups": len(prcs_groups),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# File Layout Definitions (PSFLDDEFN)
# ---------------------------------------------------------------------------

_FILE_LAYOUT_FMT = {0: "Fixed Width", 1: "Delimited", 2: "XML"}


def search_file_layouts(env_name, q="", limit=100):
    from connectors import ptmetadata
    warnings = []
    items = []
    if not ptmetadata.has_table(env_name, "PSFLDDEFN"):
        warnings.append("PSFLDDEFN not found in schema")
        return {"items": [], "warnings": warnings}
    try:
        sql = """
            SELECT FLDDEFNNAME, FLDFORMAT, FLDSEGCOUNT, DESCR, LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSFLDDEFN
             WHERE (:q IS NULL OR UPPER(FLDDEFNNAME) LIKE UPPER(:q)
                    OR UPPER(DESCR) LIKE UPPER(:q))
             ORDER BY FLDDEFNNAME
             FETCH FIRST :lim ROWS ONLY
        """
        q_param = f"%{q}%" if q else None
        rows = query(env_name, sql, {"q": q_param, "lim": limit})
        for r in rows:
            d = dict(r)
            d["fldformat_label"] = _FILE_LAYOUT_FMT.get(d.get("fldformat"), "Unknown")
            items.append(d)
    except Exception as exc:
        warnings.append(f"PSFLDDEFN search: {exc}")
    return {"items": items, "warnings": warnings}


def get_file_layout(env_name, flddefnname):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSFLDDEFN"):
        return {"error": "PSFLDDEFN not found"}

    # Header
    defn = None
    try:
        rows = query(env_name, """
            SELECT FLDDEFNNAME, FLDFORMAT, FLDSEGCOUNT, DESCR, DESCRLONG,
                   FLDTAG, FLDQUALIFIER, FLDDELIMITERTYPE, FLDDELIMITER,
                   FLDIMPLYDECIMAL, FLDEXCELFORMAT, FLDCONVERTTABS, FLDFILENAME,
                   FLDSEGID, FLDSEGIDSTART, FLDSEGIDLENGTH,
                   LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSFLDDEFN
             WHERE FLDDEFNNAME = :id
        """, {"id": flddefnname.upper()})
        if not rows:
            return {"error": f"File layout not found: {flddefnname}"}
        defn = dict(rows[0])
        defn["fldformat_label"] = _FILE_LAYOUT_FMT.get(defn.get("fldformat"), "Unknown")
    except Exception as exc:
        return {"error": str(exc)}

    # Segments
    segments = []
    if ptmetadata.has_table(env_name, "PSFLDSEGDEFN"):
        try:
            seg_rows = query(env_name, """
                SELECT FLDSEGNAME, FLDSEGID, FLDSEGPARENT, FLDSEQNO,
                       FLDFIELDCOUNT, FLDMAXSEGLEN, RECNAME_FILE, DESCR100,
                       FLDDELIMITER, FLDQUALIFIER
                  FROM SYSADM.PSFLDSEGDEFN
                 WHERE FLDDEFNNAME = :id
                 ORDER BY FLDSEQNO, FLDSEGNAME
            """, {"id": flddefnname.upper()})
            segments = [dict(r) for r in (seg_rows or [])]
        except Exception as exc:
            warnings.append(f"PSFLDSEGDEFN: {exc}")

    # Fields (top-level segment fields, limited to keep response manageable)
    fields = []
    if ptmetadata.has_table(env_name, "PSFLDFIELDDEFN"):
        try:
            fld_rows = query(env_name, """
                SELECT FLDSEGNAME, FLDFIELDNAME, FLDSEQNO, FLDSTART,
                       FLDLENGTH, FLDFIELDTYPE, DESCR100, FLDTAG
                  FROM SYSADM.PSFLDFIELDDEFN
                 WHERE FLDDEFNNAME = :id
                 ORDER BY FLDSEGNAME, FLDSEQNO
                 FETCH FIRST 200 ROWS ONLY
            """, {"id": flddefnname.upper()})
            fields = [dict(r) for r in (fld_rows or [])]
        except Exception as exc:
            warnings.append(f"PSFLDFIELDDEFN: {exc}")

    return {
        "definition": defn,
        "segments": segments,
        "fields": fields,
        "counts": {
            "segments": len(segments),
            "fields": len(fields),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Translate Values (PSXLATITEM / PSXLATDEFN)
# ---------------------------------------------------------------------------

def search_translate_fields(env_name, q="", limit=200):
    from connectors import ptmetadata
    warnings = []
    items = []
    if not ptmetadata.has_table(env_name, "PSXLATDEFN"):
        warnings.append("PSXLATDEFN not found in schema")
        return {"items": [], "warnings": warnings}
    try:
        sql = """
            SELECT d.FIELDNAME,
                   COUNT(DISTINCT i.FIELDVALUE) AS VALUE_COUNT,
                   SUM(CASE WHEN i.EFF_STATUS = 'A' THEN 1 ELSE 0 END) AS ACTIVE_COUNT
              FROM SYSADM.PSXLATDEFN d
              LEFT JOIN SYSADM.PSXLATITEM i ON i.FIELDNAME = d.FIELDNAME
             WHERE (:q IS NULL OR UPPER(d.FIELDNAME) LIKE UPPER(:q))
             GROUP BY d.FIELDNAME
             ORDER BY d.FIELDNAME
             FETCH FIRST :lim ROWS ONLY
        """
        q_param = f"%{q}%" if q else None
        rows = query(env_name, sql, {"q": q_param, "lim": limit})
        items = [dict(r) for r in (rows or [])]
    except Exception as exc:
        warnings.append(f"PSXLATDEFN search: {exc}")
    return {"items": items, "warnings": warnings}


def get_translate_values(env_name, fieldname):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSXLATITEM"):
        return {"error": "PSXLATITEM not found"}

    # Confirm field exists in translate table
    if ptmetadata.has_table(env_name, "PSXLATDEFN"):
        try:
            check = query(env_name, """
                SELECT FIELDNAME FROM SYSADM.PSXLATDEFN WHERE FIELDNAME = :id
            """, {"id": fieldname.upper()})
            if not check:
                return {"error": f"No translate values defined for field: {fieldname}"}
        except Exception:
            pass

    # Get all effective-dated values — latest active per FIELDVALUE
    values = []
    try:
        rows = query(env_name, """
            SELECT FIELDVALUE, EFFDT, EFF_STATUS, XLATLONGNAME, XLATSHORTNAME,
                   LASTUPDOPRID, LASTUPDDTTM
              FROM SYSADM.PSXLATITEM
             WHERE FIELDNAME = :id
             ORDER BY FIELDVALUE, EFFDT DESC
        """, {"id": fieldname.upper()})
        # Deduplicate: keep only the row with the latest EFFDT per FIELDVALUE
        seen = set()
        for r in (rows or []):
            fv = r.get("fieldvalue")
            if fv not in seen:
                seen.add(fv)
                values.append(dict(r))
    except Exception as exc:
        return {"error": str(exc)}

    active = [v for v in values if v.get("eff_status") == "A"]
    inactive = [v for v in values if v.get("eff_status") != "A"]

    return {
        "fieldname": fieldname.upper(),
        "values": values,
        "active_values": active,
        "inactive_values": inactive,
        "counts": {
            "total": len(values),
            "active": len(active),
            "inactive": len(inactive),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# App Designer Projects (PSPROJECTDEFN / PSPROJECTITEM)
# ---------------------------------------------------------------------------

_PRJOBJ_TYPE_LABEL = {
    0:   "Record",
    2:   "Page",
    4:   "Component",
    5:   "Component Interface",
    6:   "Menu",
    7:   "Application Engine",
    8:   "Application Package",
    9:   "Field",
    10:  "PS Query",
    11:  "Crystal Report",
    12:  "HTML Object",
    14:  "Image/File",
    17:  "StyleSheet",
    19:  "Free-form Style",
    22:  "nVision Report",
    25:  "SQL Definition",
    26:  "Role",
    27:  "Permission List",
    28:  "Security Group",
    30:  "AE SQL Step",
    33:  "Process Definition",
    34:  "Process Job",
    37:  "Query Group",
    43:  "AE Activity",
    44:  "PeopleCode",
    46:  "Related Content Defn",
    47:  "Related Content Service",
    48:  "Portal Registry",
    49:  "IB Handler",
    50:  "Stylesheet (Free-form)",
    51:  "IB Routing",
    53:  "Fluid Tile/Homepage",
    55:  "Classic Menu",
    58:  "Tree",
    60:  "Portal Content Ref",
    74:  "PS Query",
    104: "App Package Class",
    106: "Message Catalog Set",
}

# Types where OBJECTVALUE1 is NOT a human-readable name
_PRJOBJ_ENCODED = {25, 30, 106}
_PRJOBJ_UOM_TYPE = {
    0: "record",
    2: "page",
    4: "component",
    5: "ci",
    6: "menu",
    10: "query",
    58: "tree",
    74: "query",
}


def project_item_target(row):
    """Map a PSPROJECTITEM row to a canonical UOM object when safe."""
    try:
        objecttype = int(row.get("objecttype"))
    except (TypeError, ValueError):
        return None

    target_type = _PRJOBJ_UOM_TYPE.get(objecttype)
    target_name = str(row.get("objectvalue1") or "").strip().upper()
    if not target_type or not target_name or target_name == " ":
        return None

    return {
        "type": target_type,
        "name": target_name,
        "objecttype": objecttype,
        "label": _PRJOBJ_TYPE_LABEL.get(objecttype, f"Type {objecttype}"),
    }


def search_projects(env_name, q="", limit=200):
    from connectors import ptmetadata
    warnings = []
    items = []
    if not ptmetadata.has_table(env_name, "PSPROJECTDEFN"):
        warnings.append("PSPROJECTDEFN not found in schema")
        return {"items": [], "warnings": warnings}
    try:
        sql = """
            SELECT d.PROJECTNAME, d.PROJECTDESCR, d.RELEASELABEL,
                   d.LASTUPDOPRID, d.LASTUPDDTTM,
                   COUNT(i.OBJECTTYPE) AS ITEM_COUNT
              FROM SYSADM.PSPROJECTDEFN d
              LEFT JOIN SYSADM.PSPROJECTITEM i ON i.PROJECTNAME = d.PROJECTNAME
             WHERE (:q IS NULL OR UPPER(d.PROJECTNAME) LIKE UPPER(:q)
                    OR UPPER(d.PROJECTDESCR) LIKE UPPER(:q))
             GROUP BY d.PROJECTNAME, d.PROJECTDESCR, d.RELEASELABEL,
                      d.LASTUPDOPRID, d.LASTUPDDTTM
             ORDER BY d.LASTUPDDTTM DESC, d.PROJECTNAME
             FETCH FIRST :lim ROWS ONLY
        """
        q_param = f"%{q}%" if q else None
        rows = query(env_name, sql, {"q": q_param, "lim": limit})
        items = [dict(r) for r in (rows or [])]
    except Exception as exc:
        warnings.append(f"PSPROJECTDEFN search: {exc}")
    return {"items": items, "warnings": warnings}


def get_project(env_name, projectname):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSPROJECTDEFN"):
        return {"error": "PSPROJECTDEFN not found"}

    # Header
    defn = None
    try:
        rows = query(env_name, """
            SELECT PROJECTNAME, PROJECTDESCR, RELEASELABEL, DESCRLONG,
                   MAINTPROJ, COMPARETYPE, LASTUPDOPRID, LASTUPDDTTM
              FROM SYSADM.PSPROJECTDEFN
             WHERE PROJECTNAME = :id
        """, {"id": projectname.upper()})
        if not rows:
            return {"error": f"Project not found: {projectname}"}
        defn = dict(rows[0])
    except Exception as exc:
        return {"error": str(exc)}

    # Object type summary
    type_summary = []
    items_by_type = {}
    if ptmetadata.has_table(env_name, "PSPROJECTITEM"):
        try:
            # Summary counts
            sum_rows = query(env_name, """
                SELECT OBJECTTYPE, COUNT(*) CNT
                  FROM SYSADM.PSPROJECTITEM
                 WHERE PROJECTNAME = :id
                 GROUP BY OBJECTTYPE
                 ORDER BY CNT DESC
            """, {"id": projectname.upper()})
            for r in (sum_rows or []):
                otype = r.get("objecttype", -1)
                type_summary.append({
                    "objecttype": otype,
                    "label": _PRJOBJ_TYPE_LABEL.get(otype, f"Type {otype}"),
                    "count": r.get("cnt", 0),
                    "encoded": otype in _PRJOBJ_ENCODED,
                })
        except Exception as exc:
            warnings.append(f"PSPROJECTITEM summary: {exc}")

        try:
            # All items (cap at 500 for performance)
            item_rows = query(env_name, """
                SELECT OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2,
                       SOURCESTATUS, TARGETSTATUS, UPGRADEACTION
                  FROM SYSADM.PSPROJECTITEM
                 WHERE PROJECTNAME = :id
                 ORDER BY OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2
                 FETCH FIRST 500 ROWS ONLY
            """, {"id": projectname.upper()})
            for r in (item_rows or []):
                otype = r.get("objecttype", -1)
                if otype not in items_by_type:
                    items_by_type[otype] = []
                item = dict(r)
                item["uom_target"] = project_item_target(item)
                items_by_type[otype].append(item)
        except Exception as exc:
            warnings.append(f"PSPROJECTITEM items: {exc}")

    total = sum(t["count"] for t in type_summary)
    return {
        "definition": defn,
        "type_summary": type_summary,
        "items_by_type": items_by_type,
        "counts": {
            "types": len(type_summary),
            "total_items": total,
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# IB Message Definitions (PSMSGDEFN)
# ---------------------------------------------------------------------------

_IB_MSG_STATUS = {0: "Active", 1: "Inactive"}
_IB_MSG_TYPE = {0: "Document", 1: "Service", 2: "Rowset-Based", 3: "Non-Structured", 4: "Container"}


def search_ib_messages(env_name, q="", limit=200):
    from connectors import ptmetadata
    warnings = []
    items = []
    if not ptmetadata.has_table(env_name, "PSMSGDEFN"):
        warnings.append("PSMSGDEFN not found in schema")
        return {"items": [], "warnings": warnings}
    try:
        sql = """
            SELECT MSGNAME, DESCR, CHNLNAME, MSGSTATUS, OBJECTOWNERID,
                   LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSMSGDEFN
             WHERE (:q IS NULL OR UPPER(MSGNAME) LIKE UPPER(:q)
                    OR UPPER(DESCR) LIKE UPPER(:q))
             ORDER BY MSGNAME
             FETCH FIRST :lim ROWS ONLY
        """
        q_param = f"%{q}%" if q else None
        rows = query(env_name, sql, {"q": q_param, "lim": limit})
        for r in rows:
            d = dict(r)
            d["msgstatus_label"] = _IB_MSG_STATUS.get(d.get("msgstatus"), "Unknown")
            items.append(d)
    except Exception as exc:
        warnings.append(f"PSMSGDEFN search: {exc}")
    return {"items": items, "warnings": warnings}


def get_ib_message(env_name, msgname):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSMSGDEFN"):
        return {"error": "PSMSGDEFN not found"}

    # Header
    defn = None
    try:
        rows = query(env_name, """
            SELECT MSGNAME, DESCR, MSGDISPLAYNAME, CHNLNAME, DEFAULTVER,
                   MSGSTATUS, XMLALIAS, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
              FROM SYSADM.PSMSGDEFN
             WHERE MSGNAME = :id
        """, {"id": msgname.upper()})
        if not rows:
            return {"error": f"IB Message not found: {msgname}"}
        defn = dict(rows[0])
        defn["msgstatus_label"] = _IB_MSG_STATUS.get(defn.get("msgstatus"), "Unknown")
    except Exception as exc:
        return {"error": str(exc)}

    # Versions
    versions = []
    if ptmetadata.has_table(env_name, "PSMSGVER"):
        try:
            ver_rows = query(env_name, """
                SELECT APMSGVER, IB_MSGTYPE, IB_PARTS, IB_PACKAGEID, IB_SCHEMANAME
                  FROM SYSADM.PSMSGVER
                 WHERE MSGNAME = :id
                 ORDER BY APMSGVER
            """, {"id": msgname.upper()})
            for r in (ver_rows or []):
                d = dict(r)
                d["ib_msgtype_label"] = _IB_MSG_TYPE.get(d.get("ib_msgtype"), f"Type {d.get('ib_msgtype')}")
                versions.append(d)
        except Exception as exc:
            warnings.append(f"PSMSGVER: {exc}")

    # Records (schema) — use default version
    schema_records = []
    default_ver = (defn.get("defaultver") or "").strip()
    if default_ver and ptmetadata.has_table(env_name, "PSMSGREC"):
        try:
            rec_rows = query(env_name, """
                SELECT RECNAME, PRNTRECNAME, SEQNO, XMLALIAS, IB_SCHEMAMIN, IB_SCHEMAMAX
                  FROM SYSADM.PSMSGREC
                 WHERE MSGNAME = :id AND APMSGVER = :ver
                 ORDER BY SEQNO, RECNAME
                 FETCH FIRST 100 ROWS ONLY
            """, {"id": msgname.upper(), "ver": default_ver})
            schema_records = [dict(r) for r in (rec_rows or [])]
        except Exception as exc:
            warnings.append(f"PSMSGREC: {exc}")

    return {
        "definition": defn,
        "versions": versions,
        "schema_records": schema_records,
        "counts": {
            "versions": len(versions),
            "schema_records": len(schema_records),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# IB Application Services (ASF REST API Framework)
# ---------------------------------------------------------------------------

def search_ib_applications(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSIBAPPLDEFN"):
        return []
    where, params = "WHERE 1=1", {}
    if q:
        where = "WHERE UPPER(d.PTIBAPPLNAME) LIKE :q OR UPPER(d.PTIB_APPSRVGRP) LIKE :q OR UPPER(d.DESCR) LIKE :q"
        params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT d.PTIBAPPLNAME, d.PTIB_APPSRVGRP, d.STATUS, d.PTIBAPPLTYPE,
               d.IB_SERVICENAME, d.PTIBURLPARAMNAME, d.OBJECTOWNERID,
               d.DESCRLONG,
               (SELECT COUNT(*) FROM SYSADM.PSIBAPPMETHOD m
                WHERE m.PTIBAPPLNAME = d.PTIBAPPLNAME) AS OP_COUNT
          FROM SYSADM.PSIBAPPLDEFN d
        {where}
         ORDER BY d.PTIBAPPLNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    results = []
    for r in (rows or []):
        d = dict(r)
        d["descr"] = (d.get("descrlong") or "").split("\n")[0].strip()[:120]
        results.append(d)
    return results


def get_ib_application(env_name, applname):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSIBAPPLDEFN"):
        return {"warnings": ["PSIBAPPLDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PTIBAPPLNAME, PTIB_APPSRVGRP, STATUS, PTIBAPPLTYPE,
               IB_SERVICENAME, PTIBURLPARAMNAME, PTCBURLPARAMNAME,
               IB_PACKAGEID, IB_SCHEMANAME, IB_VARIANTNAME,
               IB_SSL, PTIB_SUPPORT_XML, PTIB_EXPORT, PTIB_EXPORT_CB,
               OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID, DESCRLONG
          FROM SYSADM.PSIBAPPLDEFN
         WHERE PTIBAPPLNAME = :id
    """, {"id": applname.upper()})
    if not defn_rows:
        return {"warnings": [f"Application '{applname}' not found"]}
    defn = dict(defn_rows[0])

    # Operations: join methods + URIs
    operations = []
    if ptmetadata.has_table(env_name, "PSIBAPPMETHOD"):
        try:
            op_rows = query(env_name, """
                SELECT m.PTIBAPPLOPR, m.IB_URI_SEQ, m.IB_RESTMETHOD,
                       m.IBTRANSACTIONID, m.PTIBCACHESUPPORT, m.IB_CACHETIME,
                       m.PTMULTIROWINPUT, m.PTMULTIROWOUTPUT,
                       u.IB_URI_TEMPLATE,
                       t.DESCR100 AS TRAN_DESCR
                  FROM SYSADM.PSIBAPPMETHOD m
                  LEFT JOIN SYSADM.PSIBAPPURI u
                    ON u.PTIBAPPLNAME = m.PTIBAPPLNAME
                   AND u.PTIBAPPLOPR  = m.PTIBAPPLOPR
                   AND u.IB_URI_SEQ   = m.IB_URI_SEQ
                  LEFT JOIN SYSADM.PSIBAPPTRAN t
                    ON t.PTIBAPPLNAME    = m.PTIBAPPLNAME
                   AND t.IBTRANSACTIONID = m.IBTRANSACTIONID
                 WHERE m.PTIBAPPLNAME = :id
                 ORDER BY m.PTIBAPPLOPR, m.IB_URI_SEQ
            """, {"id": applname.upper()})
            operations = [dict(r) for r in (op_rows or [])]
        except Exception as exc:
            warnings.append(f"PSIBAPPMETHOD: {exc}")

    # Response states
    states = []
    if ptmetadata.has_table(env_name, "PSIBAPPLSTATES"):
        try:
            st_rows = query(env_name, """
                SELECT PTIBAPPLOPR, IB_URI_SEQ, IB_RESTMETHOD,
                       PTIBRSLT_STATE, IB_HTTP_STATUS_CD, PTIBRSLTCAT
                  FROM SYSADM.PSIBAPPLSTATES
                 WHERE PTIBAPPLNAME = :id
                 ORDER BY PTIBAPPLOPR, IB_URI_SEQ
            """, {"id": applname.upper()})
            states = [dict(r) for r in (st_rows or [])]
        except Exception as exc:
            warnings.append(f"PSIBAPPLSTATES: {exc}")

    return {
        "definition": defn,
        "operations": operations,
        "states": states,
        "counts": {
            "operations": len(operations),
            "states": len(states),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Application Class Definitions
# ---------------------------------------------------------------------------

def _app_class_full_path(packageroot, qualifypath, appclassid):
    """Build the PeopleCode-style full class path."""
    qp = (qualifypath or "").strip()
    if qp == ":" or not qp:
        return f"{packageroot}:{appclassid}"
    return f"{packageroot}:{qp}:{appclassid}"


def search_app_classes(env_name, q="", pkg="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSAPPCLASSDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append("(UPPER(APPCLASSID) LIKE :q OR UPPER(PACKAGEROOT) LIKE :q OR UPPER(QUALIFYPATH) LIKE :q)")
        params["q"] = f"%{q.upper()}%"
    if pkg:
        where_parts.append("UPPER(PACKAGEROOT) = :pkg")
        params["pkg"] = pkg.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT APPCLASSID, PACKAGEROOT, QUALIFYPATH, APPCLASSREF
          FROM SYSADM.PSAPPCLASSDEFN
        {where}
         ORDER BY PACKAGEROOT, QUALIFYPATH, APPCLASSID
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    results = []
    for r in (rows or []):
        d = dict(r)
        d["_key"] = f"{d['packageroot']}~{d['qualifypath']}~{d['appclassid']}"
        d["full_path"] = _app_class_full_path(d["packageroot"], d["qualifypath"], d["appclassid"])
        results.append(d)
    return results


def get_app_class(env_name, compound_key):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSAPPCLASSDEFN"):
        return {"warnings": ["PSAPPCLASSDEFN table not accessible"]}

    # Key format: PACKAGEROOT~QUALIFYPATH~APPCLASSID
    parts = compound_key.split("~", 2)
    if len(parts) != 3:
        return {"warnings": [f"Invalid compound key '{compound_key}' (expected PKG~QP~CLASSID)"]}
    packageroot, qualifypath, appclassid = parts

    defn_rows = query(env_name, """
        SELECT APPCLASSID, PACKAGEROOT, QUALIFYPATH, APPCLASSREF
          FROM SYSADM.PSAPPCLASSDEFN
         WHERE UPPER(PACKAGEROOT) = UPPER(:pkg) AND UPPER(QUALIFYPATH) = UPPER(:qp) AND UPPER(APPCLASSID) = UPPER(:cid)
    """, {"pkg": packageroot, "qp": qualifypath, "cid": appclassid})
    if not defn_rows:
        return {"warnings": [f"Class '{compound_key}' not found"]}
    defn = dict(defn_rows[0])
    defn["full_path"] = _app_class_full_path(packageroot, qualifypath, appclassid)

    # Use DB-correct-case values for all subsequent queries
    packageroot = defn.get("packageroot", packageroot)
    qualifypath = defn.get("qualifypath", qualifypath)
    appclassid = defn.get("appclassid", appclassid)
    defn["full_path"] = _app_class_full_path(packageroot, qualifypath, appclassid)

    # Siblings — other classes in same package:sub-path
    siblings = []
    try:
        sib_rows = query(env_name, """
            SELECT APPCLASSID, APPCLASSREF
              FROM SYSADM.PSAPPCLASSDEFN
             WHERE PACKAGEROOT = :pkg AND QUALIFYPATH = :qp
               AND APPCLASSID != :cid
             ORDER BY APPCLASSID
             FETCH FIRST 100 ROWS ONLY
        """, {"pkg": packageroot, "qp": qualifypath, "cid": appclassid})
        siblings = [dict(r) for r in (sib_rows or [])]
    except Exception as exc:
        warnings.append(f"Siblings: {exc}")

    # All sub-paths in the same package
    sub_paths = []
    try:
        sp_rows = query(env_name, """
            SELECT QUALIFYPATH, COUNT(*) AS CLASS_COUNT
              FROM SYSADM.PSAPPCLASSDEFN
             WHERE PACKAGEROOT = :pkg
             GROUP BY QUALIFYPATH
             ORDER BY QUALIFYPATH
             FETCH FIRST 50 ROWS ONLY
        """, {"pkg": packageroot})
        sub_paths = [dict(r) for r in (sp_rows or [])]
    except Exception as exc:
        warnings.append(f"SubPaths: {exc}")

    total_in_pkg = sum(sp.get("class_count", 0) for sp in sub_paths)

    # Fetch PeopleCode source from PSPCMTXT
    # Key: OV1=packageroot, [OV2..n-2]=qualifypath parts, OV(n-1)=classid, OVn=OnExecute
    source = None
    try:
        if ptmetadata.has_table(env_name, "PSPCMTXT"):
            qp_parts = [p for p in qualifypath.split(":") if p.strip()]
            ov_values = [packageroot] + qp_parts + [appclassid, "OnExecute"]
            while len(ov_values) < 7:
                ov_values.append(" ")
            ov_values = ov_values[:7]

            txt_columns = select_existing_columns(
                env_name, "PSPCMTXT",
                ["PCTEXT", "PROGTXT", "TXT", "TEXT"],
            )
            text_col = next((c for c in ("PCTEXT", "PROGTXT", "TXT", "TEXT") if c in txt_columns), None)
            if text_col:
                predicates = [f"OBJECTVALUE{i+1} = :ov{i+1}" for i in range(7)]
                params_ov = {f"ov{i+1}": ov_values[i] for i in range(7)}
                src_rows = query(env_name, f"""
                    SELECT {text_col} AS chunk
                      FROM SYSADM.PSPCMTXT
                     WHERE {" AND ".join(predicates)}
                     ORDER BY PROGSEQ
                """, params_ov)
                if src_rows:
                    source = "".join(str(r.get("chunk") or "") for r in src_rows).rstrip()
    except Exception as exc:
        warnings.append(f"Source: {exc}")

    return {
        "definition": defn,
        "siblings": siblings,
        "sub_paths": sub_paths,
        "source": source,
        "counts": {
            "siblings": len(siblings),
            "sub_paths": len(sub_paths),
            "total_in_package": total_in_pkg,
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Content Service Provider Definitions (PSPTCSSRVDEFN)
# ---------------------------------------------------------------------------

_PTCS_URL_TYPE = {
    "UPGE": "Page Component",
    "UAPC": "App Class",
    "UTIL": "Utility",
    "UGEN": "URL (Generic)",
    "USCR": "URL Script",
}
_PTCS_SVC_TYPE = {"S": "Service", "C": "Custom", "G": "Group"}


def search_content_services(env_name, q="", owner="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTCSSRVDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(PTCS_SERVICEID) LIKE :q OR UPPER(PTCS_SERVICENAME) LIKE :q OR UPPER(DESCR254) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    if owner:
        where_parts.append("UPPER(OBJECTOWNERID) = :own")
        params["own"] = owner.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT d.PTCS_SERVICEID, d.PTCS_SERVICENAME, d.DESCR254,
               d.PTCS_SERVICEURLTYP, d.PTCS_SERVICETYPE,
               d.PORTAL_MENUNAME, d.PNLGRPNAME, d.MARKET,
               d.PACKAGEROOT, d.QUALIFYPATH, d.APPCLASSID,
               d.OBJECTOWNERID, d.PTTILECATEGORY,
               (SELECT COUNT(*) FROM SYSADM.PSPTCS_PARAMS p
                WHERE p.PTCS_SERVICEID = d.PTCS_SERVICEID) AS PARAM_COUNT
          FROM SYSADM.PSPTCSSRVDEFN d
        {where}
         ORDER BY d.PTCS_SERVICEID
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    results = []
    for r in (rows or []):
        d = dict(r)
        d["url_type_label"] = _PTCS_URL_TYPE.get(d.get("ptcs_serviceurltyp", ""), d.get("ptcs_serviceurltyp", ""))
        results.append(d)
    return results


def get_content_service(env_name, service_id):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSPTCSSRVDEFN"):
        return {"warnings": ["PSPTCSSRVDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PTCS_SERVICEID, PTCS_SERVICENAME, DESCR254,
               PTCS_SERVICEURLTYP, PTCS_SERVICETYPE, PTCS_SRVCATTR,
               PORTAL_MENUNAME, PNLGRPNAME, MARKET, PNLNAME,
               PORTAL_URI_TEXT, PTCS_QUERYNAME,
               PACKAGEROOT, QUALIFYPATH, APPCLASSID,
               OBJECTOWNERID, PTTILECATEGORY,
               MSGNODENAME, PTCS_SECUSEEDIT, USEEDIT,
               PTCS_BULKACTION, PTCS_ESCAPEPARAM,
               LASTUPDDTTM, LASTUPDOPRID, VERSION
          FROM SYSADM.PSPTCSSRVDEFN
         WHERE PTCS_SERVICEID = :id
    """, {"id": service_id.upper()})
    if not defn_rows:
        return {"warnings": [f"Content Service '{service_id}' not found"]}
    defn = dict(defn_rows[0])

    # Parameters
    params_list = []
    if ptmetadata.has_table(env_name, "PSPTCS_PARAMS"):
        try:
            p_rows = query(env_name, """
                SELECT PTCS_PARAMETERNAME, SEQNUM, REQUIRED_FLG, PTCS_DESCR128
                  FROM SYSADM.PSPTCS_PARAMS
                 WHERE PTCS_SERVICEID = :id
                 ORDER BY SEQNUM
            """, {"id": service_id.upper()})
            params_list = [dict(r) for r in (p_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTCS_PARAMS: {exc}")

    # Where used — distinct portal objects referencing this service (via menu links)
    usage = []
    if ptmetadata.has_table(env_name, "PSPTCS_MNULINKS"):
        try:
            u_rows = query(env_name, """
                SELECT DISTINCT PORTAL_NAME, PORTAL_OBJNAME
                  FROM SYSADM.PSPTCS_MNULINKS
                 WHERE PTCS_SERVICEID = :id
                 ORDER BY PORTAL_OBJNAME
                 FETCH FIRST 50 ROWS ONLY
            """, {"id": service_id.upper()})
            usage = [dict(r) for r in (u_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTCS_MNULINKS: {exc}")

    # Map fields count (too granular for display, just count)
    mapfld_count = 0
    if ptmetadata.has_table(env_name, "PSPTCS_MAPFLDS"):
        try:
            mf = query(env_name, """
                SELECT COUNT(*) CNT FROM SYSADM.PSPTCS_MAPFLDS
                 WHERE PTCS_SERVICEID = :id
            """, {"id": service_id.upper()})
            mapfld_count = (mf or [{"cnt": 0}])[0].get("cnt", 0)
        except Exception:
            pass

    return {
        "definition": defn,
        "params": params_list,
        "usage": usage,
        "counts": {
            "params": len(params_list),
            "usage": len(usage),
            "map_fields": mapfld_count,
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# PeopleTools Test Framework (PTF) Definitions
# ---------------------------------------------------------------------------

_PTF_TYPE = {"S": "Script", "H": "Shell", "L": "Library"}


def search_ptf_tests(env_name, q="", ptf_type="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPTTSTDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(PTTST_NAME) LIKE :q OR UPPER(DESCR) LIKE :q OR UPPER(PTTST_PARENTFOLDER) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    if ptf_type:
        where_parts.append("PTTST_TYPE = :tp")
        params["tp"] = ptf_type.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT d.PTTST_NAME, d.PTTST_PARENTFOLDER, d.PTTST_TYPE, d.DESCR,
               d.PTTST_APP_VER, d.LASTUPDDTTM, d.LASTUPDOPRID,
               (SELECT COUNT(*) FROM SYSADM.PSPTTSTCOMMAND c
                WHERE c.PTTST_NAME = d.PTTST_NAME) AS CMD_COUNT
          FROM SYSADM.PSPTTSTDEFN d
        {where}
         ORDER BY d.PTTST_TYPE, d.PTTST_NAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    results = []
    for r in (rows or []):
        d = dict(r)
        d["type_label"] = _PTF_TYPE.get(d.get("pttst_type", ""), d.get("pttst_type", ""))
        results.append(d)
    return results


def get_ptf_test(env_name, test_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSPTTSTDEFN"):
        return {"warnings": ["PSPTTSTDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PTTST_NAME, PTTST_PARENTFOLDER, PTTST_TYPE, DESCR,
               PTTST_APP_VER, PTTST_USE_ERROR, PTTST_PV_ACTN,
               VERSION, LASTUPDDTTM, LASTUPDOPRID, OBJECTOWNERID, DESCRLONG
          FROM SYSADM.PSPTTSTDEFN
         WHERE PTTST_NAME = :id
    """, {"id": test_name.upper()})
    if not defn_rows:
        return {"warnings": [f"PTF test '{test_name}' not found"]}
    defn = dict(defn_rows[0])

    # Test cases
    cases = []
    if ptmetadata.has_table(env_name, "PSPTTSTCASE"):
        try:
            c_rows = query(env_name, """
                SELECT PTTST_CASE_NAME, DESCR, LASTUPDDTTM, LASTUPDOPRID
                  FROM SYSADM.PSPTTSTCASE
                 WHERE PTTST_NAME = :id
                 ORDER BY PTTST_CASE_NAME
            """, {"id": test_name.upper()})
            cases = [dict(r) for r in (c_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTTSTCASE: {exc}")

    # Commands — joined with description (first description line)
    commands = []
    if ptmetadata.has_table(env_name, "PSPTTSTCOMMAND"):
        try:
            cmd_rows = query(env_name, """
                SELECT c.PTTST_CMD_ID, c.SEQNBR, c.PTTST_CMD_TYPE,
                       c.PTTST_CMD_OBJ_ID, c.PTTST_CMDPARAMETRS,
                       c.MENUNAME, c.PNLGRPNAME, c.MARKET, c.PNLNAME,
                       c.PTTST_PAGEFIELD_NM, c.RECNAME, c.FIELDNAME,
                       c.PTTST_CMD_STATUS
                  FROM SYSADM.PSPTTSTCOMMAND c
                 WHERE c.PTTST_NAME = :id AND c.PTTST_LANG_CD IN (' ', 'ENG')
                 ORDER BY c.SEQNBR
                 FETCH FIRST 150 ROWS ONLY
            """, {"id": test_name.upper()})
            commands = [dict(r) for r in (cmd_rows or [])]
        except Exception as exc:
            warnings.append(f"PSPTTSTCOMMAND: {exc}")

    return {
        "definition": defn,
        "cases": cases,
        "commands": commands,
        "counts": {
            "cases": len(cases),
            "commands": len(commands),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Application Data Set (ADS) Definitions
# ---------------------------------------------------------------------------

def search_ads_definitions(env_name, q="", owner="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSADSDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(PTADSNAME) LIKE :q OR UPPER(DESCR) LIKE :q OR UPPER(DESCR254) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    if owner:
        where_parts.append("UPPER(OBJECTOWNERID) = :own")
        params["own"] = owner.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT d.PTADSNAME, d.DESCR, d.DESCR254, d.OBJECTOWNERID,
               d.PTCOPYABLE, d.PTCOMPARABLE, d.PTDERVTYPE,
               d.PTKEYCOL1,
               (SELECT COUNT(*) FROM SYSADM.PSADSDEFNITEM i
                WHERE i.PTADSNAME = d.PTADSNAME) AS RECORD_COUNT
          FROM SYSADM.PSADSDEFN d
        {where}
         ORDER BY d.PTADSNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_ads_definition(env_name, ads_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSADSDEFN"):
        return {"warnings": ["PSADSDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PTADSNAME, DESCR, DESCR254, OBJECTOWNERID,
               PTCOPYABLE, PTCOMPARABLE, PTDERVTYPE,
               PTDERVKEY1, PTDERVKEY2, PTVALIDATESTATIC,
               PACKAGEROOT, QUALIFYPATH, APPCLASSID,
               PTKEYCOL1, PTKEYCOL2, PTKEYCOL3, PTKEYCOL4,
               PTKEYCOL5, PTKEYCOL6, PTKEYCOL7, PTKEYCOL8,
               VERSION, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSADSDEFN
         WHERE PTADSNAME = :id
    """, {"id": ads_name.upper()})
    if not defn_rows:
        return {"warnings": [f"ADS definition '{ads_name}' not found"]}
    defn = dict(defn_rows[0])

    # Key columns (strip blanks)
    key_cols = [
        defn.get(f"ptkeycol{i}", "").strip()
        for i in range(1, 9)
        if (defn.get(f"ptkeycol{i}") or "").strip()
    ]

    # Records (PSADSDEFNITEM)
    records = []
    if ptmetadata.has_table(env_name, "PSADSDEFNITEM"):
        try:
            rec_rows = query(env_name, """
                SELECT RECNAME, PTPARENTRECNAME, PTPEERORDER
                  FROM SYSADM.PSADSDEFNITEM
                 WHERE PTADSNAME = :id
                 ORDER BY PTPARENTRECNAME, RECNAME
            """, {"id": ads_name.upper()})
            records = [dict(r) for r in (rec_rows or [])]
        except Exception as exc:
            warnings.append(f"PSADSDEFNITEM: {exc}")

    # Groups
    groups = []
    if ptmetadata.has_table(env_name, "PSADSGROUP"):
        try:
            grp_rows = query(env_name, """
                SELECT g.PTGROUPNAME, g.PTGRPDISPNAME,
                       COUNT(m.FIELDNAME) AS FIELD_COUNT
                  FROM SYSADM.PSADSGROUP g
                  LEFT JOIN SYSADM.PSADSGROUPMEMB m
                    ON m.PTADSNAME = g.PTADSNAME
                   AND m.PTGROUPNAME = g.PTGROUPNAME
                 WHERE g.PTADSNAME = :id
                 GROUP BY g.PTGROUPNAME, g.PTGRPDISPNAME
                 ORDER BY g.PTGROUPNAME
            """, {"id": ads_name.upper()})
            groups = [dict(r) for r in (grp_rows or [])]
        except Exception as exc:
            warnings.append(f"PSADSGROUP: {exc}")

    return {
        "definition": defn,
        "key_cols": key_cols,
        "records": records,
        "groups": groups,
        "counts": {
            "records": len(records),
            "groups": len(groups),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# IB Service Groups
# ---------------------------------------------------------------------------

def search_ib_service_groups(env_name, q="", owner="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSIBGROUPDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(g.IB_INTGROUPNAME) LIKE :q OR UPPER(g.DESCR) LIKE :q OR UPPER(g.DESCRLONG) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    if owner:
        where_parts.append("UPPER(g.OBJECTOWNERID) = :own")
        params["own"] = owner.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT g.IB_INTGROUPNAME, g.DESCR, g.DESCRLONG, g.OBJECTOWNERID,
               (SELECT COUNT(*) FROM SYSADM.PSIBSRVGROUP m
                WHERE m.IB_INTGROUPNAME = g.IB_INTGROUPNAME) AS SERVICE_COUNT
          FROM SYSADM.PSIBGROUPDEFN g
        {where}
         ORDER BY g.IB_INTGROUPNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_ib_service_group(env_name, group_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSIBGROUPDEFN"):
        return {"warnings": ["PSIBGROUPDEFN table not accessible"]}

    header_rows = query(env_name, """
        SELECT IB_INTGROUPNAME, DESCR, DESCRLONG, OBJECTOWNERID,
               LASTUPDDTTM, LASTUPDOPRID, VERSION
          FROM SYSADM.PSIBGROUPDEFN
         WHERE IB_INTGROUPNAME = :id
    """, {"id": group_name.upper()})
    if not header_rows:
        return {"warnings": [f"IB Service Group '{group_name}' not found"]}
    header = dict(header_rows[0])

    # Member services
    members = []
    if ptmetadata.has_table(env_name, "PSIBSRVGROUP"):
        try:
            mem_rows = query(env_name, """
                SELECT m.IB_SERVICENAME,
                       s.DESCR, s.IB_OPERATION_TYPE, s.VERSION_NUM,
                       s.EFF_STATUS
                  FROM SYSADM.PSIBSRVGROUP m
                  LEFT JOIN SYSADM.PSIBSVCOPER s
                    ON s.IB_OPERATIONNAME = m.IB_SERVICENAME
                   AND s.VERSION_NUM = (
                       SELECT MAX(s2.VERSION_NUM) FROM SYSADM.PSIBSVCOPER s2
                        WHERE s2.IB_OPERATIONNAME = m.IB_SERVICENAME
                   )
                 WHERE m.IB_INTGROUPNAME = :id
                 ORDER BY m.IB_SERVICENAME
            """, {"id": group_name.upper()})
            members = [dict(r) for r in (mem_rows or [])]
        except Exception:
            # Fallback: just the names without join
            try:
                mem_rows = query(env_name, """
                    SELECT IB_SERVICENAME FROM SYSADM.PSIBSRVGROUP
                     WHERE IB_INTGROUPNAME = :id
                     ORDER BY IB_SERVICENAME
                """, {"id": group_name.upper()})
                members = [{"ib_servicename": r["ib_servicename"]} for r in (mem_rows or [])]
            except Exception as exc:
                warnings.append(f"PSIBSRVGROUP: {exc}")

    return {
        "header": header,
        "members": members,
        "counts": {"services": len(members)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# URL Definitions
# ---------------------------------------------------------------------------

def search_url_definitions(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSURLDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(URL_ID) LIKE :q OR UPPER(DESCR) LIKE :q OR UPPER(URL) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT URL_ID, DESCR, URL, OBJECTOWNERID, ICLIENT_SERVERFLAG,
               COMMENTS, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSURLDEFN
        {where}
         ORDER BY URL_ID
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_url_definition(env_name, url_id):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSURLDEFN"):
        return {"warnings": ["PSURLDEFN table not accessible"]}

    rows = query(env_name, """
        SELECT URL_ID, DESCR, URL, OBJECTOWNERID, ICLIENT_SERVERFLAG,
               COMMENTS, LASTUPDDTTM, LASTUPDOPRID, VERSION
          FROM SYSADM.PSURLDEFN
         WHERE URL_ID = :id
    """, {"id": url_id.upper()})
    if not rows:
        return {"warnings": [f"URL definition '{url_id}' not found"]}

    return {
        "definition": dict(rows[0]),
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Chatbot Skill Definitions
# ---------------------------------------------------------------------------

_CB_PARAM_DTYPE = {
    "STR": "String", "INT": "Integer", "NUM": "Number",
    "DATE": "Date", "BOOL": "Boolean", "OBJ": "Object",
}
_CB_PARAM_TYPE = {"IN": "Input", "OUT": "Output", "INOUT": "In/Out"}
_CB_RSLT_CAT = {"S": "Success", "E": "Error", "W": "Warning", "I": "Info"}


def search_chatbot_skills(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSCBAPPLDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(d.PTCBAPPLNAME) LIKE :q OR UPPER(d.DESCR50) LIKE :q OR UPPER(d.PTCBURLPARAMNAME) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT d.PTCBAPPLNAME, d.DESCR50, d.PTCBURLPARAMNAME,
               d.PACKAGEROOT, d.QUALIFYPATH, d.APPCLASSID, d.APPCLASSMETHOD,
               d.STATUS, d.PTCBCACHESUPPORT,
               (SELECT COUNT(*) FROM SYSADM.PSCBAPPLPARAM p
                WHERE p.PTCBAPPLNAME = d.PTCBAPPLNAME) AS PARAM_COUNT
          FROM SYSADM.PSCBAPPLDEFN d
        {where}
         ORDER BY d.PTCBAPPLNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_chatbot_skill(env_name, skill_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSCBAPPLDEFN"):
        return {"warnings": ["PSCBAPPLDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PTCBAPPLNAME, PTCBAPPLTYPE, PTCBURLPARAMNAME, DESCR50,
               APPCLASSID, APPCLASSMETHOD, PACKAGEROOT, QUALIFYPATH,
               PTCBCACHESUPPORT, PTMULTIROWINPUT, PTMULTIROWOUTPUT,
               PTCB_ASENDUSER, STATUS, PTCB_SRC_TYPE
          FROM SYSADM.PSCBAPPLDEFN
         WHERE PTCBAPPLNAME = :id
    """, {"id": skill_name.upper()})
    if not defn_rows:
        return {"warnings": [f"Chatbot skill '{skill_name}' not found"]}
    defn = dict(defn_rows[0])

    # Parameters
    params_list = []
    if ptmetadata.has_table(env_name, "PSCBAPPLPARAM"):
        try:
            param_rows = query(env_name, """
                SELECT PARAM_NAME, PTCBPARAMTYPE, PTCBPARAMDTYPE,
                       DESCR60, PTCB_PARAMVAL_TYPE, PTCB_PARAM_VALUE
                  FROM SYSADM.PSCBAPPLPARAM
                 WHERE PTCBAPPLNAME = :id
                 ORDER BY PTCBPARAMTYPE, PARAM_NAME
            """, {"id": skill_name.upper()})
            params_list = [dict(r) for r in (param_rows or [])]
        except Exception as exc:
            warnings.append(f"PSCBAPPLPARAM: {exc}")

    # Result states
    states = []
    if ptmetadata.has_table(env_name, "PSCBAPPLSTATES"):
        try:
            state_rows = query(env_name, """
                SELECT PTCBRSLT_STATE, DESCR60, PTCBRSLTCAT
                  FROM SYSADM.PSCBAPPLSTATES
                 WHERE PTCBAPPLNAME = :id
                 ORDER BY PTCBRSLTCAT, PTCBRSLT_STATE
            """, {"id": skill_name.upper()})
            states = [dict(r) for r in (state_rows or [])]
        except Exception as exc:
            warnings.append(f"PSCBAPPLSTATES: {exc}")

    return {
        "definition": defn,
        "params": params_list,
        "states": states,
        "counts": {
            "params": len(params_list),
            "states": len(states),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# IB Routing Definitions
# ---------------------------------------------------------------------------

_IB_RTNG_TYPE = {"S": "Synchronous", "A": "Asynchronous", "R": "REST", "X": "Internal"}
_IB_DELIVER_MODE = {
    0: "Guaranteed", 1: "Best Effort", 2: "Unsolicited",
}


def search_ib_routings(env_name, q="", rtng_type="", status="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return []
    where_parts = ["ROUTINGDEFNNAME NOT LIKE '~%'"]
    params = {}
    if q:
        where_parts.append(
            "(UPPER(ROUTINGDEFNNAME) LIKE :q OR UPPER(IB_OPERATIONNAME) LIKE :q "
            "OR UPPER(SENDERNODENAME) LIKE :q OR UPPER(RECEIVERNODENAME) LIKE :q)"
        )
        params["q"] = f"%{q.upper()}%"
    if rtng_type:
        where_parts.append("RTNGTYPE = :rt")
        params["rt"] = rtng_type.upper()
    if status:
        where_parts.append("EFF_STATUS = :st")
        params["st"] = status.upper()
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT ROUTINGDEFNNAME, EFF_STATUS, SENDERNODENAME, RECEIVERNODENAME,
               IB_OPERATIONNAME, RTNGTYPE, DESCR, OBJECTOWNERID,
               ONSNDHDLRNAME, ONRCVHDLRNAME
          FROM SYSADM.PSIBRTNGDEFN
        {where}
         ORDER BY IB_OPERATIONNAME, ROUTINGDEFNNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_ib_routing(env_name, routing_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        return {"warnings": ["PSIBRTNGDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT ROUTINGDEFNNAME, EFFDT, EFF_STATUS, SENDERNODENAME, RECEIVERNODENAME,
               IB_OPERATIONNAME, VERSIONNAME, RTNGTYPE, IB_DELIVERYMODE,
               CONNOVERRIDE, CONNGATEWAYID, CONNID,
               ONSNDHDLRNAME, ONRCVHDLRNAME, ONPREHDLRNAME, ONPOSTHDLRNAME,
               LOGMSGDTLFLG, IB_SYNCHNONBLOCK, GENERATED,
               DESCR, DESCRLONG, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSIBRTNGDEFN
         WHERE ROUTINGDEFNNAME = :id
    """, {"id": routing_name.upper()})
    if not defn_rows:
        return {"warnings": [f"IB Routing '{routing_name}' not found"]}
    defn = dict(defn_rows[0])

    # Alias records
    aliases = []
    if ptmetadata.has_table(env_name, "PSIBRTNGSUBDEFN"):
        try:
            alias_rows = query(env_name, """
                SELECT SEQNUM, IB_DIRECTION, RTNGTYPE,
                       SENDERNODENAME, RECEIVERNODENAME, ALIASNAME
                  FROM SYSADM.PSIBRTNGSUBDEFN
                 WHERE ROUTINGDEFNNAME = :id
                 ORDER BY SEQNUM
            """, {"id": routing_name.upper()})
            aliases = [dict(r) for r in (alias_rows or [])]
        except Exception as exc:
            warnings.append(f"PSIBRTNGSUBDEFN: {exc}")

    return {
        "definition": defn,
        "aliases": aliases,
        "counts": {"aliases": len(aliases)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Style Sheet Definitions
# ---------------------------------------------------------------------------

_SS_TYPE = {0: "Classic", 1: "Fluid Theme", 2: "Component Style"}


def search_style_sheets(env_name, q="", ss_type="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSSTYLSHEETDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append("(UPPER(STYLESHEETNAME) LIKE :q OR UPPER(DESCR) LIKE :q)")
        params["q"] = f"%{q.upper()}%"
    if ss_type != "":
        where_parts.append("STYLESHEETTYPE = :sst")
        params["sst"] = int(ss_type)
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT s.STYLESHEETNAME, s.STYLESHEETTYPE, s.DESCR,
               s.PARENTSTYLENAME, s.OBJECTOWNERID,
               (SELECT COUNT(*) FROM SYSADM.PSSTYLECLASS c
                WHERE c.STYLESHEETNAME = s.STYLESHEETNAME) AS CLASS_COUNT
          FROM SYSADM.PSSTYLSHEETDEFN s
        {where}
         ORDER BY s.STYLESHEETTYPE, s.STYLESHEETNAME
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_style_sheet(env_name, stylesheet_name):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSSTYLSHEETDEFN"):
        return {"warnings": ["PSSTYLSHEETDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT STYLESHEETNAME, VERSION, STYLESHEETTYPE, PARENTSTYLENAME,
               DESCR, NUMSTYLECLASS, OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSSTYLSHEETDEFN
         WHERE STYLESHEETNAME = :id
    """, {"id": stylesheet_name.upper()})
    if not defn_rows:
        return {"warnings": [f"Style Sheet '{stylesheet_name}' not found"]}
    defn = dict(defn_rows[0])

    # Style classes (names only — CSS property columns are numeric encoded)
    classes = []
    if ptmetadata.has_table(env_name, "PSSTYLECLASS"):
        try:
            cls_rows = query(env_name, """
                SELECT STYLECLASSNAME, SEQNO
                  FROM SYSADM.PSSTYLECLASS
                 WHERE STYLESHEETNAME = :id
                 ORDER BY SEQNO
                 FETCH FIRST 300 ROWS ONLY
            """, {"id": stylesheet_name.upper()})
            classes = [r["styleclassname"] for r in (cls_rows or [])]
        except Exception as exc:
            warnings.append(f"PSSTYLECLASS: {exc}")

    return {
        "definition": defn,
        "classes": classes,
        "counts": {"classes": len(classes)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Data Archive Object Definitions
# ---------------------------------------------------------------------------

def search_archive_objects(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSARCHOBJDEFN"):
        return []
    where_parts = ["1=1"]
    params = {}
    if q:
        where_parts.append("(UPPER(PSARCH_OBJECT) LIKE :q OR UPPER(DESCR) LIKE :q)")
        params["q"] = f"%{q.upper()}%"
    where = "WHERE " + " AND ".join(where_parts)
    rows = query(env_name, f"""
        SELECT d.PSARCH_OBJECT, d.DESCR, d.OBJECTOWNERID, d.VERSION,
               d.LASTUPDDTTM, d.LASTUPDOPRID,
               (SELECT COUNT(*) FROM SYSADM.PSARCHOBJREC r
                WHERE r.PSARCH_OBJECT = d.PSARCH_OBJECT) AS RECORD_COUNT
          FROM SYSADM.PSARCHOBJDEFN d
        {where}
         ORDER BY d.PSARCH_OBJECT
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_archive_object(env_name, arch_object):
    from connectors import ptmetadata
    warnings = []
    if not ptmetadata.has_table(env_name, "PSARCHOBJDEFN"):
        return {"warnings": ["PSARCHOBJDEFN table not accessible"]}

    defn_rows = query(env_name, """
        SELECT PSARCH_OBJECT, DESCR, OBJECTOWNERID, VERSION,
               LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSARCHOBJDEFN
         WHERE PSARCH_OBJECT = :id
    """, {"id": arch_object.upper()})
    if not defn_rows:
        return {"warnings": [f"Archive object '{arch_object}' not found"]}
    defn = dict(defn_rows[0])

    # Records in this archive object
    records = []
    if ptmetadata.has_table(env_name, "PSARCHOBJREC"):
        try:
            rec_rows = query(env_name, """
                SELECT RECNAME, HIST_RECNAME, PSARCH_BASETABLE
                  FROM SYSADM.PSARCHOBJREC
                 WHERE PSARCH_OBJECT = :id
                 ORDER BY RECNAME
            """, {"id": arch_object.upper()})
            records = [dict(r) for r in (rec_rows or [])]
        except Exception as exc:
            warnings.append(f"PSARCHOBJREC: {exc}")

    return {
        "definition": defn,
        "records": records,
        "counts": {"records": len(records)},
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Timezone Definitions
# ---------------------------------------------------------------------------

def search_timezones(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSTIMEZONEDEFN"):
        return []
    where = ""
    params = {}
    if q:
        where = "WHERE UPPER(TIMEZONE) LIKE :q OR UPPER(TZDESCR) LIKE :q"
        params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT TIMEZONE, TZDESCR, TIMEZONESTDLBL, TIMEZONEDSTLBL,
               UTCOFFSET, OBSERVEDST, DSTOFFSET
          FROM SYSADM.PSTIMEZONEDEFN t
         WHERE PTEFFDTTM = (
               SELECT MAX(t2.PTEFFDTTM) FROM SYSADM.PSTIMEZONEDEFN t2
                WHERE t2.TIMEZONE = t.TIMEZONE)
         {where}
         ORDER BY TIMEZONE
         FETCH FIRST :lim ROWS ONLY
    """, {**params, "lim": limit})
    return [dict(r) for r in (rows or [])]


def get_timezone(env_name, tz_code):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSTIMEZONEDEFN"):
        return {"warnings": ["PSTIMEZONEDEFN table not accessible"]}
    rows = query(env_name, """
        SELECT TIMEZONE, TZDESCR, TIMEZONESTDLBL, TIMEZONEDSTLBL,
               UTCOFFSET, OBSERVEDST, DSTOFFSET, DSTSTART, DSTEND,
               PTEFFDTTM, LASTUPDDTTM
          FROM SYSADM.PSTIMEZONEDEFN
         WHERE TIMEZONE = :id
           AND PTEFFDTTM = (SELECT MAX(t2.PTEFFDTTM) FROM SYSADM.PSTIMEZONEDEFN t2
                             WHERE t2.TIMEZONE = :id)
    """, {"id": tz_code.upper()})
    # Also get IANA mapping
    iana = []
    if ptmetadata.has_table(env_name, "PSTIMEZONEIANA"):
        try:
            iana_rows = query(env_name, """
                SELECT IANAZONEID FROM SYSADM.PSTIMEZONEIANA
                 WHERE TIMEZONE = :id ORDER BY IANAZONEID
            """, {"id": tz_code.upper()})
            iana = [r["ianazoneid"] for r in (iana_rows or [])]
        except Exception:
            pass
    return {"definition": dict(rows[0]) if rows else {}, "iana": iana,
            "warnings": [] if rows else [f"Timezone '{tz_code}' not found"]}


def search_locales(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSLOCALEDEFN"):
        return []
    where = ""
    params: dict = {"lim": limit}
    if q:
        where = "WHERE UPPER(d.LOCALECD) LIKE :q OR UPPER(d.DESCR) LIKE :q"
        params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT d.LOCALECD, d.DESCR
          FROM SYSADM.PSLOCALEDEFN d
        {where}
         ORDER BY d.LOCALECD
         FETCH FIRST :lim ROWS ONLY
    """, params)
    return [dict(r) for r in (rows or [])]


def get_locale(env_name, locale_cd):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSLOCALEDEFN"):
        return {"definition": {}, "options": [], "warnings": ["PSLOCALEDEFN not accessible"]}
    rows = query(env_name, "SELECT LOCALECD, DESCR FROM SYSADM.PSLOCALEDEFN WHERE LOCALECD = :cd",
                 {"cd": locale_cd})
    defn = rows[0] if rows else None
    warnings_out = [] if defn else [f"Locale '{locale_cd}' not found"]
    options = []
    if ptmetadata.has_table(env_name, "PSLOCALEOPTNDFN"):
        options = query(env_name, """
            SELECT USEROPTN, USER_OPTION_VALUE
              FROM SYSADM.PSLOCALEOPTNDFN
             WHERE LOCALECD = :cd
             ORDER BY USEROPTN
        """, {"cd": locale_cd}) or []
    return {"definition": dict(defn) if defn else {}, "options": [dict(o) for o in options],
            "warnings": warnings_out}


def search_pm_metrics(env_name, q="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMMETRICDEFN"):
        return []
    where = ""
    params: dict = {"lim": limit}
    if q:
        # Support numeric search by ID or text search by label
        if q.isdigit():
            where = "WHERE m.PM_METRICID = :qid"
            params["qid"] = int(q)
        else:
            where = "WHERE UPPER(m.PM_METRICLABEL) LIKE :q OR UPPER(m.DESCR60) LIKE :q"
            params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT m.PM_METRICID, m.PM_METRICLABEL, m.DESCR60, m.PM_METRICTYPE,
               m.PM_METRICINT, m.PM_METRIC_DISP, m.PM_METRIC_DEFSCALE
          FROM SYSADM.PSPMMETRICDEFN m
        {where}
         ORDER BY m.PM_METRICID
         FETCH FIRST :lim ROWS ONLY
    """, params)
    return [dict(r) for r in (rows or [])]


def get_pm_metric(env_name, metric_id):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMMETRICDEFN"):
        return {"definition": {}, "enum_values": [], "transactions": [], "events": [], "warnings": ["PSPMMETRICDEFN not accessible"]}
    try:
        mid = int(metric_id)
    except (ValueError, TypeError):
        return {"definition": {}, "enum_values": [], "transactions": [], "events": [], "warnings": [f"Invalid metric ID: {metric_id}"]}
    rows = query(env_name, """
        SELECT PM_METRICID, PM_METRICLABEL, DESCR60, PM_METRICTYPE,
               PM_METRICINT, PM_METRIC_DISP, PM_METRIC_DEFSCALE
          FROM SYSADM.PSPMMETRICDEFN
         WHERE PM_METRICID = :id
    """, {"id": mid})
    defn = rows[0] if rows else None
    warnings_out = [] if defn else [f"PM Metric ID {mid} not found"]
    enum_values = []
    if ptmetadata.has_table(env_name, "PSPMMETRICVALUE"):
        enum_values = query(env_name, """
            SELECT PM_METRIC_VALUE, PM_METRICLABEL
              FROM SYSADM.PSPMMETRICVALUE
             WHERE PM_METRICID = :id
             ORDER BY PM_METRIC_VALUE
        """, {"id": mid}) or []
    transactions = []
    if ptmetadata.has_table(env_name, "PSPMTRANSDEFN"):
        transactions = query(env_name, """
            SELECT PM_TRANS_DEFN_ID, PM_TRANS_LABEL, DESCR60
              FROM SYSADM.PSPMTRANSDEFN
             WHERE :id IN (PM_METRICID_1, PM_METRICID_2, PM_METRICID_3,
                           PM_METRICID_4, PM_METRICID_5, PM_METRICID_6, PM_METRICID_7)
             ORDER BY PM_TRANS_LABEL
        """, {"id": mid}) or []
    events = []
    if ptmetadata.has_table(env_name, "PSPMEVENTDEFN"):
        events = query(env_name, """
            SELECT PM_EVENT_DEFN_ID, PM_EVENT_LABEL, DESCR60
              FROM SYSADM.PSPMEVENTDEFN
             WHERE :id IN (PM_METRICID_1, PM_METRICID_2, PM_METRICID_3,
                           PM_METRICID_4, PM_METRICID_5, PM_METRICID_6, PM_METRICID_7)
             ORDER BY PM_EVENT_LABEL
        """, {"id": mid}) or []
    return {
        "definition": dict(defn) if defn else {},
        "enum_values": [dict(v) for v in enum_values],
        "transactions": [dict(t) for t in transactions],
        "events": [dict(e) for e in events],
        "warnings": warnings_out,
    }


def search_pm_transactions(env_name, q="", limit=100):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMTRANSDEFN"):
        return []
    where = ""
    params: dict = {"lim": limit}
    if q:
        where = "WHERE UPPER(t.PM_TRANS_LABEL) LIKE :q OR UPPER(t.DESCR60) LIKE :q"
        params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT t.PM_TRANS_DEFN_ID, t.PM_TRANS_LABEL, t.DESCR60,
               t.PM_FILTER_LEVEL, t.PM_SAMPLING_ENABLE
          FROM SYSADM.PSPMTRANSDEFN t
        {where}
         ORDER BY t.PM_TRANS_LABEL
         FETCH FIRST :lim ROWS ONLY
    """, params)
    return [dict(r) for r in (rows or [])]


def get_pm_transaction(env_name, trans_id):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMTRANSDEFN"):
        return {"definition": {}, "warnings": ["PSPMTRANSDEFN not accessible"]}
    try:
        tid = int(trans_id)
    except (ValueError, TypeError):
        return {"definition": {}, "warnings": [f"Invalid transaction ID: {trans_id}"]}
    rows = query(env_name, """
        SELECT t.PM_TRANS_DEFN_ID, t.PM_TRANS_LABEL, t.DESCR60,
               t.PM_FILTER_LEVEL, t.PM_SAMPLING_ENABLE,
               t.PM_CONTEXTID_1, t.PM_CONTEXTID_2, t.PM_CONTEXTID_3,
               t.PM_METRICID_1, t.PM_METRICID_2, t.PM_METRICID_3,
               t.PM_METRICID_4, t.PM_METRICID_5, t.PM_METRICID_6, t.PM_METRICID_7,
               c1.PM_CONTEXT_LABEL ctx1_label, c2.PM_CONTEXT_LABEL ctx2_label,
               c3.PM_CONTEXT_LABEL ctx3_label,
               m1.PM_METRICLABEL met1_label, m2.PM_METRICLABEL met2_label,
               m3.PM_METRICLABEL met3_label, m4.PM_METRICLABEL met4_label,
               m5.PM_METRICLABEL met5_label, m6.PM_METRICLABEL met6_label,
               m7.PM_METRICLABEL met7_label
          FROM SYSADM.PSPMTRANSDEFN t
          LEFT JOIN SYSADM.PSPMCONTEXTDEFN c1 ON c1.PM_CONTEXTID = t.PM_CONTEXTID_1 AND t.PM_CONTEXTID_1 != 0
          LEFT JOIN SYSADM.PSPMCONTEXTDEFN c2 ON c2.PM_CONTEXTID = t.PM_CONTEXTID_2 AND t.PM_CONTEXTID_2 != 0
          LEFT JOIN SYSADM.PSPMCONTEXTDEFN c3 ON c3.PM_CONTEXTID = t.PM_CONTEXTID_3 AND t.PM_CONTEXTID_3 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m1 ON m1.PM_METRICID = t.PM_METRICID_1 AND t.PM_METRICID_1 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m2 ON m2.PM_METRICID = t.PM_METRICID_2 AND t.PM_METRICID_2 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m3 ON m3.PM_METRICID = t.PM_METRICID_3 AND t.PM_METRICID_3 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m4 ON m4.PM_METRICID = t.PM_METRICID_4 AND t.PM_METRICID_4 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m5 ON m5.PM_METRICID = t.PM_METRICID_5 AND t.PM_METRICID_5 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m6 ON m6.PM_METRICID = t.PM_METRICID_6 AND t.PM_METRICID_6 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m7 ON m7.PM_METRICID = t.PM_METRICID_7 AND t.PM_METRICID_7 != 0
         WHERE t.PM_TRANS_DEFN_ID = :id
    """, {"id": tid})
    defn = rows[0] if rows else None
    return {
        "definition": dict(defn) if defn else {},
        "warnings": [] if defn else [f"PM Transaction ID {tid} not found"],
    }


def search_pm_events(env_name, q="", limit=50):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMEVENTDEFN"):
        return []
    where = ""
    params: dict = {"lim": limit}
    if q:
        where = "WHERE UPPER(e.PM_EVENT_LABEL) LIKE :q OR UPPER(e.DESCR60) LIKE :q"
        params["q"] = f"%{q.upper()}%"
    rows = query(env_name, f"""
        SELECT e.PM_EVENT_DEFN_ID, e.PM_EVENT_LABEL, e.DESCR60,
               e.PM_FILTER_LEVEL, e.PM_SAMPLING_ENABLE
          FROM SYSADM.PSPMEVENTDEFN e
        {where}
         ORDER BY e.PM_EVENT_LABEL
         FETCH FIRST :lim ROWS ONLY
    """, params)
    return [dict(r) for r in (rows or [])]


def get_pm_event(env_name, event_id):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSPMEVENTDEFN"):
        return {"definition": {}, "warnings": ["PSPMEVENTDEFN not accessible"]}
    try:
        eid = int(event_id)
    except (ValueError, TypeError):
        return {"definition": {}, "warnings": [f"Invalid event ID: {event_id}"]}
    rows = query(env_name, """
        SELECT e.PM_EVENT_DEFN_ID, e.PM_EVENT_LABEL, e.DESCR60,
               e.PM_FILTER_LEVEL, e.PM_SAMPLING_ENABLE,
               e.PM_METRICID_1, e.PM_METRICID_2, e.PM_METRICID_3,
               e.PM_METRICID_4, e.PM_METRICID_5, e.PM_METRICID_6, e.PM_METRICID_7,
               m1.PM_METRICLABEL met1_label, m2.PM_METRICLABEL met2_label,
               m3.PM_METRICLABEL met3_label, m4.PM_METRICLABEL met4_label,
               m5.PM_METRICLABEL met5_label, m6.PM_METRICLABEL met6_label,
               m7.PM_METRICLABEL met7_label
          FROM SYSADM.PSPMEVENTDEFN e
          LEFT JOIN SYSADM.PSPMMETRICDEFN m1 ON m1.PM_METRICID = e.PM_METRICID_1 AND e.PM_METRICID_1 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m2 ON m2.PM_METRICID = e.PM_METRICID_2 AND e.PM_METRICID_2 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m3 ON m3.PM_METRICID = e.PM_METRICID_3 AND e.PM_METRICID_3 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m4 ON m4.PM_METRICID = e.PM_METRICID_4 AND e.PM_METRICID_4 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m5 ON m5.PM_METRICID = e.PM_METRICID_5 AND e.PM_METRICID_5 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m6 ON m6.PM_METRICID = e.PM_METRICID_6 AND e.PM_METRICID_6 != 0
          LEFT JOIN SYSADM.PSPMMETRICDEFN m7 ON m7.PM_METRICID = e.PM_METRICID_7 AND e.PM_METRICID_7 != 0
         WHERE e.PM_EVENT_DEFN_ID = :id
    """, {"id": eid})
    defn = rows[0] if rows else None
    return {
        "definition": dict(defn) if defn else {},
        "warnings": [] if defn else [f"PM Event ID {eid} not found"],
    }


def search_ib_operations(env_name, q="", rtype="", limit=200):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSOPERATION"):
        return []
    clauses = []
    params: dict = {"lim": limit}
    if q:
        clauses.append("(UPPER(op.IB_OPERATIONNAME) LIKE :q OR UPPER(op.IB_SERVICENAME) LIKE :q OR UPPER(op.DESCR) LIKE :q)")
        params["q"] = f"%{q.upper()}%"
    if rtype:
        clauses.append("op.RTNGTYPE = :rtype")
        params["rtype"] = rtype.upper()
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = query(env_name, f"""
        SELECT op.IB_OPERATIONNAME, op.IB_SERVICENAME, op.RTNGTYPE,
               op.IB_RESTMETHOD, op.IB_REST_SERVICE, op.MSGNAME,
               op.IB_MSGVERSION, op.DESCR, op.OBJECTOWNERID
          FROM SYSADM.PSOPERATION op
        {where}
         ORDER BY op.IB_OPERATIONNAME
         FETCH FIRST :lim ROWS ONLY
    """, params)
    return [dict(r) for r in (rows or [])]


def get_ib_operation(env_name, op_name):
    from connectors import ptmetadata
    if not ptmetadata.has_table(env_name, "PSOPERATION"):
        return {"definition": {}, "routings": [], "warnings": ["PSOPERATION not accessible"]}
    rows = query(env_name, """
        SELECT IB_OPERATIONNAME, IB_SERVICENAME, RTNGTYPE, IB_RESTMETHOD,
               IB_REST_SERVICE, MSGNAME, IB_MSGVERSION, DESCR, DESCRLONG,
               OBJECTOWNERID, LASTUPDDTTM, LASTUPDOPRID
          FROM SYSADM.PSOPERATION
         WHERE IB_OPERATIONNAME = :id
    """, {"id": op_name.upper()})
    defn = rows[0] if rows else None
    warnings_out = [] if defn else [f"IB Operation '{op_name}' not found"]
    routings = []
    if ptmetadata.has_table(env_name, "PSIBRTNGDEFN"):
        routings = query(env_name, """
            SELECT ROUTINGDEFNNAME, RTNGTYPE, EFF_STATUS,
                   SENDERNODENAME, RECEIVERNODENAME, DESCR
              FROM SYSADM.PSIBRTNGDEFN
             WHERE IB_OPERATIONNAME = :id
               AND ROUTINGDEFNNAME NOT LIKE '~%'
             ORDER BY ROUTINGDEFNNAME
             FETCH FIRST 100 ROWS ONLY
        """, {"id": op_name.upper()}) or []
    return {
        "definition": dict(defn) if defn else {},
        "routings": [dict(r) for r in routings],
        "warnings": warnings_out,
    }
