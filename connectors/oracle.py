import json
import socket
from pathlib import Path
import oracledb
from connectors import paths

CONFIG = paths.CONFIG_FILE


def load_databases():
    data = json.loads(CONFIG.read_text())
    return data["oracle"]["databases"]


def dsn(db):
    return f'{db["host"]}:{db["port"]}/{db["service"]}'


def listener_status(host="192.168.122.206", port=1521):
    try:
        with socket.create_connection((host, port), timeout=2):
            return {"host": host, "port": port, "status": "ONLINE"}
    except Exception as exc:
        return {"host": host, "port": port, "status": "OFFLINE", "error": str(exc)}


def query_db(db, sql):
    conn = oracledb.connect(
        user=db["user"],
        password=db["password"],
        dsn=dsn(db)
    )
    cur = conn.cursor()
    cur.execute(sql)
    cols = [c[0].lower() for c in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


def instances():
    out = []
    for db in load_databases():
        try:
            rows = query_db(db, """
                select
                    instance_name,
                    host_name,
                    version,
                    status,
                    startup_time
                from v$instance
            """)
            out.append({"name": db["name"], "status": "ONLINE", "instance": rows[0] if rows else {}})
        except Exception as exc:
            out.append({"name": db["name"], "status": "ERROR", "error": str(exc)})
    return {"databases": out}


def sessions():
    out = []
    for db in load_databases():
        try:
            rows = query_db(db, """
                select
                    status,
                    type,
                    count(*) as session_count
                from v$session
                group by status, type
                order by status, type
            """)
            out.append({"name": db["name"], "status": "ONLINE", "sessions": rows})
        except Exception as exc:
            out.append({"name": db["name"], "status": "ERROR", "error": str(exc)})
    return {"databases": out}


def health():
    listener = listener_status()
    inst = instances()
    return {
        "listener": listener,
        "instances": inst["databases"],
        "status": "ONLINE" if listener["status"] == "ONLINE" else "OFFLINE"
    }


def tablespaces():
    sql = """
        select
            df.tablespace_name,
            round(df.total_mb, 2) as total_mb,
            round(nvl(fs.free_mb, 0), 2) as free_mb,
            round(df.total_mb - nvl(fs.free_mb, 0), 2) as used_mb,
            round(((df.total_mb - nvl(fs.free_mb, 0)) / df.total_mb) * 100, 2) as used_pct
        from
            (
                select tablespace_name, sum(bytes) / 1024 / 1024 as total_mb
                from dba_data_files
                group by tablespace_name
            ) df
            left join
            (
                select tablespace_name, sum(bytes) / 1024 / 1024 as free_mb
                from dba_free_space
                group by tablespace_name
            ) fs
            on df.tablespace_name = fs.tablespace_name
        order by used_pct desc
    """

    out = []
    for db in load_databases():
        try:
            rows = query_db(db, sql)
            out.append({
                "name": db["name"],
                "status": "ONLINE",
                "tablespaces": rows
            })
        except Exception as exc:
            out.append({
                "name": db["name"],
                "status": "ERROR",
                "error": str(exc)
            })

    return {"databases": out}

def blocking_sessions():
    sql = """
        select
            sid,
            serial# as serial,
            username,
            status,
            machine,
            program,
            blocking_session,
            event,
            seconds_in_wait
        from v$session
        where blocking_session is not null
        order by seconds_in_wait desc
    """

    out = []
    for db in load_databases():
        try:
            out.append({
                "name": db["name"],
                "status": "ONLINE",
                "blocking_sessions": query_db(db, sql)
            })
        except Exception as exc:
            out.append({"name": db["name"], "status": "ERROR", "error": str(exc)})

    return {"databases": out}


def longops():
    sql = """
        select
            sid,
            serial# as serial,
            opname,
            target,
            sofar,
            totalwork,
            round(sofar / nullif(totalwork, 0) * 100, 2) as pct_done,
            elapsed_seconds,
            time_remaining
        from v$session_longops
        where totalwork > 0
          and sofar < totalwork
        order by time_remaining desc
    """

    out = []
    for db in load_databases():
        try:
            out.append({
                "name": db["name"],
                "status": "ONLINE",
                "longops": query_db(db, sql)
            })
        except Exception as exc:
            out.append({"name": db["name"], "status": "ERROR", "error": str(exc)})

    return {"databases": out}
