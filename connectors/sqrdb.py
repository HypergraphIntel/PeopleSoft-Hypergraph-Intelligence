"""
SQLite store for SQR/SQC source artifact index.

Database: data/sqr.db
Schema:
  sqr_programs  — one row per indexed file
  sqr_tables    — PS_ table references (many per program)
  sqr_includes  — #include SQC dependencies (many per program)
  sqr_procedures— begin-procedure definitions (many per program)
"""

import sqlite3
from pathlib import Path

DATA_DIR = Path("/opt/deathstar-api/data")
DB_PATH  = DATA_DIR / "sqr.db"


def _conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db() -> None:
    c = _conn()
    with c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS sqr_programs (
                id            INTEGER PRIMARY KEY,
                filename      TEXT NOT NULL UNIQUE,
                program_name  TEXT,
                file_type     TEXT,
                source_key    TEXT,
                description   TEXT,
                release       TEXT,
                revision      TEXT,
                sqr_date      TEXT,
                table_count   INTEGER DEFAULT 0,
                include_count INTEGER DEFAULT 0,
                proc_count    INTEGER DEFAULT 0,
                indexed_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS sqr_tables (
                program_id  INTEGER NOT NULL REFERENCES sqr_programs(id) ON DELETE CASCADE,
                table_name  TEXT NOT NULL,
                operations  TEXT,
                UNIQUE(program_id, table_name)
            );

            CREATE INDEX IF NOT EXISTS sqr_tables_name ON sqr_tables(table_name);

            CREATE TABLE IF NOT EXISTS sqr_includes (
                program_id   INTEGER NOT NULL REFERENCES sqr_programs(id) ON DELETE CASCADE,
                include_file TEXT NOT NULL,
                UNIQUE(program_id, include_file)
            );

            CREATE INDEX IF NOT EXISTS sqr_includes_file ON sqr_includes(include_file);

            CREATE TABLE IF NOT EXISTS sqr_procedures (
                program_id INTEGER NOT NULL REFERENCES sqr_programs(id) ON DELETE CASCADE,
                proc_name  TEXT NOT NULL
            );
        """)
    c.close()


def upsert_program(parsed: dict, filename: str, file_type: str, source_key: str) -> int:
    """Insert or replace one parsed program. Returns program id."""
    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tables   = parsed.get("tables", {})
    includes = parsed.get("includes", [])
    procs    = parsed.get("procedures", [])

    c = _conn()
    with c:
        c.execute("""
            INSERT INTO sqr_programs
                (filename, program_name, file_type, source_key, description,
                 release, revision, sqr_date, table_count, include_count, proc_count, indexed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(filename) DO UPDATE SET
                program_name=excluded.program_name,
                file_type=excluded.file_type,
                source_key=excluded.source_key,
                description=excluded.description,
                release=excluded.release,
                revision=excluded.revision,
                sqr_date=excluded.sqr_date,
                table_count=excluded.table_count,
                include_count=excluded.include_count,
                proc_count=excluded.proc_count,
                indexed_at=excluded.indexed_at
        """, (
            filename,
            parsed.get("program_name", ""),
            file_type,
            source_key,
            parsed.get("description", ""),
            parsed.get("release", ""),
            parsed.get("revision", ""),
            parsed.get("date", ""),
            len(tables),
            len(includes),
            len(procs),
            now,
        ))

        row = c.execute("SELECT id FROM sqr_programs WHERE filename=?", (filename,)).fetchone()
        pid = row["id"]

        c.execute("DELETE FROM sqr_tables WHERE program_id=?", (pid,))
        for tbl, ops in tables.items():
            c.execute(
                "INSERT OR IGNORE INTO sqr_tables (program_id, table_name, operations) VALUES (?,?,?)",
                (pid, tbl, ",".join(ops))
            )

        c.execute("DELETE FROM sqr_includes WHERE program_id=?", (pid,))
        for inc in includes:
            c.execute(
                "INSERT OR IGNORE INTO sqr_includes (program_id, include_file) VALUES (?,?)",
                (pid, inc)
            )

        c.execute("DELETE FROM sqr_procedures WHERE program_id=?", (pid,))
        for proc in procs:
            c.execute(
                "INSERT INTO sqr_procedures (program_id, proc_name) VALUES (?,?)",
                (pid, proc)
            )

    c.close()
    return pid


def stats() -> dict:
    """Return high-level counts."""
    c = _conn()
    row = c.execute(
        "SELECT COUNT(*) AS programs, SUM(table_count) AS total_table_refs,"
        " SUM(include_count) AS total_includes FROM sqr_programs"
    ).fetchone()
    distinct_tables = c.execute("SELECT COUNT(DISTINCT table_name) FROM sqr_tables").fetchone()[0]
    last_indexed = c.execute(
        "SELECT MAX(indexed_at) AS ts FROM sqr_programs"
    ).fetchone()["ts"]
    c.close()
    return {
        "programs":           row["programs"] or 0,
        "total_table_refs":   row["total_table_refs"] or 0,
        "total_includes":     row["total_includes"] or 0,
        "distinct_ps_tables": distinct_tables or 0,
        "last_indexed":       last_indexed,
    }


def search_programs(q: str = "", file_type: str = "", page: int = 1, per_page: int = 50) -> dict:
    """Search programs by filename/description/program_name. Returns paginated results."""
    c = _conn()
    clauses = []
    params: list = []

    if q:
        clauses.append(
            "(lower(filename) LIKE ? OR lower(program_name) LIKE ? OR lower(description) LIKE ?)"
        )
        like = f"%{q.lower()}%"
        params += [like, like, like]

    if file_type in ("sqr", "sqc"):
        clauses.append("file_type=?")
        params.append(file_type)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = c.execute(f"SELECT COUNT(*) FROM sqr_programs {where}", params).fetchone()[0]
    offset = (page - 1) * per_page

    rows = c.execute(
        f"SELECT id, filename, program_name, file_type, description, release, "
        f"table_count, include_count, proc_count, indexed_at "
        f"FROM sqr_programs {where} ORDER BY filename LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    c.close()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": [dict(r) for r in rows],
    }


def analytics() -> dict:
    """Return analytics data for the SQR library."""
    c = _conn()

    top_tables = c.execute("""
        SELECT t.table_name,
               COUNT(DISTINCT t.program_id) AS program_count,
               SUM(CASE WHEN p.file_type='sqr' THEN 1 ELSE 0 END) AS sqr_count,
               GROUP_CONCAT(DISTINCT
                 REPLACE(REPLACE(REPLACE(t.operations,'SELECT','S'),'UPDATE','U'),
                   'INSERT','I')
               ) AS ops_summary
          FROM sqr_tables t
          JOIN sqr_programs p ON p.id = t.program_id
         GROUP BY t.table_name
         ORDER BY program_count DESC
         LIMIT 30
    """).fetchall()

    top_programs = c.execute("""
        SELECT filename, program_name, file_type, description,
               table_count, include_count, proc_count
          FROM sqr_programs
         WHERE file_type = 'sqr'
         ORDER BY table_count DESC
         LIMIT 20
    """).fetchall()

    top_includes = c.execute("""
        SELECT i.include_file, COUNT(DISTINCT i.program_id) AS user_count
          FROM sqr_includes i
         GROUP BY i.include_file
         ORDER BY user_count DESC
         LIMIT 20
    """).fetchall()

    release_breakdown = c.execute("""
        SELECT COALESCE(NULLIF(TRIM(release),''), 'Unknown') AS rel,
               COUNT(*) AS cnt,
               SUM(CASE WHEN file_type='sqr' THEN 1 ELSE 0 END) AS sqr_cnt,
               SUM(CASE WHEN file_type='sqc' THEN 1 ELSE 0 END) AS sqc_cnt
          FROM sqr_programs
         GROUP BY rel
         ORDER BY cnt DESC
    """).fetchall()

    c.close()
    return {
        "top_tables":        [dict(r) for r in top_tables],
        "top_programs":      [dict(r) for r in top_programs],
        "top_includes":      [dict(r) for r in top_includes],
        "release_breakdown": [dict(r) for r in release_breakdown],
    }


def get_program(filename: str) -> dict | None:
    """Return full detail for a single program, including tables/includes/procs."""
    c = _conn()
    row = c.execute(
        "SELECT * FROM sqr_programs WHERE filename=?", (filename,)
    ).fetchone()
    if not row:
        c.close()
        return None

    pid = row["id"]
    tables = c.execute(
        "SELECT table_name, operations FROM sqr_tables WHERE program_id=? ORDER BY table_name",
        (pid,)
    ).fetchall()
    includes = c.execute(
        "SELECT include_file FROM sqr_includes WHERE program_id=? ORDER BY include_file",
        (pid,)
    ).fetchall()
    procs = c.execute(
        "SELECT proc_name FROM sqr_procedures WHERE program_id=? ORDER BY proc_name",
        (pid,)
    ).fetchall()
    c.close()

    return {
        **dict(row),
        "tables": [{"table_name": r["table_name"], "operations": r["operations"]} for r in tables],
        "includes": [r["include_file"] for r in includes],
        "procedures": [r["proc_name"] for r in procs],
    }


def get_programs_for_table(table_name: str) -> list[dict]:
    """Return programs that reference a given PS_ table name."""
    c = _conn()
    rows = c.execute(
        "SELECT p.filename, p.program_name, p.file_type, p.description, t.operations "
        "FROM sqr_tables t JOIN sqr_programs p ON p.id=t.program_id "
        "WHERE t.table_name=? ORDER BY p.filename",
        (table_name.upper(),)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_includes_for_sqc(sqc_name: str) -> list[dict]:
    """Return programs that #include a given SQC file."""
    c = _conn()
    name = sqc_name.lower()
    if not name.endswith(".sqc"):
        name += ".sqc"
    rows = c.execute(
        "SELECT p.filename, p.program_name, p.file_type, p.description "
        "FROM sqr_includes i JOIN sqr_programs p ON p.id=i.program_id "
        "WHERE i.include_file=? ORDER BY p.filename",
        (name,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def clear_source(source_key: str) -> int:
    """Delete all programs for a given source key. Returns deleted count."""
    c = _conn()
    with c:
        n = c.execute(
            "SELECT COUNT(*) FROM sqr_programs WHERE source_key=?", (source_key,)
        ).fetchone()[0]
        c.execute("DELETE FROM sqr_programs WHERE source_key=?", (source_key,))
    c.close()
    return n
