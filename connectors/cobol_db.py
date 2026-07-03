"""
SQLite store for PeopleSoft COBOL source artifact index.

Database: data/cobol.db
Schema:
  cobol_programs — one row per indexed .cbl file (program or copybook)
  cobol_tables   — PS_ table references found inside EXEC SQL blocks
  cobol_copies   — COPY dependencies (many per program)
  cobol_calls    — static CALL targets (many per program)
"""

import re
import sqlite3
from pathlib import Path

DATA_DIR = Path("/opt/deathstar-api/data")
DB_PATH  = DATA_DIR / "cobol.db"


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
            CREATE TABLE IF NOT EXISTS cobol_programs (
                id            INTEGER PRIMARY KEY,
                filename      TEXT NOT NULL,
                member_name   TEXT,
                file_type     TEXT,
                source_key    TEXT,
                source_type   TEXT,
                description   TEXT,
                compiled      INTEGER DEFAULT 0,
                table_count   INTEGER DEFAULT 0,
                copy_count    INTEGER DEFAULT 0,
                call_count    INTEGER DEFAULT 0,
                indexed_at    TEXT,
                source_text   TEXT,
                content_hash  TEXT,
                UNIQUE(filename, source_key)
            );

            CREATE TABLE IF NOT EXISTS cobol_tables (
                program_id  INTEGER NOT NULL REFERENCES cobol_programs(id) ON DELETE CASCADE,
                table_name  TEXT NOT NULL,
                operations  TEXT,
                UNIQUE(program_id, table_name)
            );
            CREATE INDEX IF NOT EXISTS cobol_tables_name ON cobol_tables(table_name);

            CREATE TABLE IF NOT EXISTS cobol_copies (
                program_id INTEGER NOT NULL REFERENCES cobol_programs(id) ON DELETE CASCADE,
                copy_name  TEXT NOT NULL,
                UNIQUE(program_id, copy_name)
            );
            CREATE INDEX IF NOT EXISTS cobol_copies_name ON cobol_copies(copy_name);

            CREATE TABLE IF NOT EXISTS cobol_calls (
                program_id INTEGER NOT NULL REFERENCES cobol_programs(id) ON DELETE CASCADE,
                call_name  TEXT NOT NULL,
                UNIQUE(program_id, call_name)
            );
            CREATE INDEX IF NOT EXISTS cobol_calls_name ON cobol_calls(call_name);
        """)
    c.close()


def upsert_program(parsed: dict, filename: str, source_key: str,
                    source_type: str = "", compiled: bool = False,
                    source_text: str = None, content_hash: str = None) -> int:
    """Insert or replace one parsed program/copybook. Returns program id."""
    import time
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tables = parsed.get("tables", {})
    copies = parsed.get("copies", [])
    calls  = parsed.get("calls", [])

    c = _conn()
    with c:
        c.execute("""
            INSERT INTO cobol_programs
                (filename, member_name, file_type, source_key, source_type, description,
                 compiled, table_count, copy_count, call_count, indexed_at,
                 source_text, content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(filename, source_key) DO UPDATE SET
                member_name=excluded.member_name,
                file_type=excluded.file_type,
                source_type=excluded.source_type,
                description=excluded.description,
                compiled=excluded.compiled,
                table_count=excluded.table_count,
                copy_count=excluded.copy_count,
                call_count=excluded.call_count,
                indexed_at=excluded.indexed_at,
                source_text=excluded.source_text,
                content_hash=excluded.content_hash
        """, (
            filename,
            parsed.get("member_name", ""),
            parsed.get("file_type", "copybook"),
            source_key,
            source_type or "",
            parsed.get("description", ""),
            1 if compiled else 0,
            len(tables),
            len(copies),
            len(calls),
            now,
            source_text,
            content_hash,
        ))

        row = c.execute(
            "SELECT id FROM cobol_programs WHERE lower(filename)=lower(?) AND source_key=?",
            (filename, source_key)
        ).fetchone()
        pid = row["id"]

        c.execute("DELETE FROM cobol_tables WHERE program_id=?", (pid,))
        for tbl, ops in tables.items():
            c.execute(
                "INSERT OR IGNORE INTO cobol_tables (program_id, table_name, operations) VALUES (?,?,?)",
                (pid, tbl, ",".join(ops))
            )

        c.execute("DELETE FROM cobol_copies WHERE program_id=?", (pid,))
        for copy_name in copies:
            c.execute(
                "INSERT OR IGNORE INTO cobol_copies (program_id, copy_name) VALUES (?,?)",
                (pid, copy_name)
            )

        c.execute("DELETE FROM cobol_calls WHERE program_id=?", (pid,))
        for call_name in calls:
            c.execute(
                "INSERT OR IGNORE INTO cobol_calls (program_id, call_name) VALUES (?,?)",
                (pid, call_name)
            )
    c.close()
    return pid


def get_content_hash(filename: str, source_key: str) -> str | None:
    c = _conn()
    row = c.execute(
        "SELECT content_hash FROM cobol_programs WHERE lower(filename)=lower(?) AND source_key=?",
        (filename, source_key),
    ).fetchone()
    c.close()
    return row["content_hash"] if row else None


def stats() -> dict:
    c = _conn()
    row = c.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN file_type='program' THEN 1 ELSE 0 END) AS programs, "
        "SUM(CASE WHEN file_type='copybook' THEN 1 ELSE 0 END) AS copybooks, "
        "SUM(compiled) AS compiled "
        "FROM cobol_programs"
    ).fetchone()
    distinct_tables = c.execute("SELECT COUNT(DISTINCT table_name) FROM cobol_tables").fetchone()[0]
    last_indexed = c.execute("SELECT MAX(indexed_at) AS ts FROM cobol_programs").fetchone()["ts"]
    c.close()
    return {
        "total":             row["total"] or 0,
        "programs":          row["programs"] or 0,
        "copybooks":         row["copybooks"] or 0,
        "compiled":          row["compiled"] or 0,
        "distinct_ps_tables": distinct_tables or 0,
        "last_indexed":      last_indexed,
    }


def search_programs(q: str = "", file_type: str = "", source_keys: list[str] | None = None,
                     page: int = 1, per_page: int = 50) -> dict:
    c = _conn()
    clauses = []
    params: list = []

    if q:
        clauses.append("(lower(filename) LIKE ? OR lower(member_name) LIKE ? OR lower(description) LIKE ?)")
        like = f"%{q.lower()}%"
        params += [like, like, like]

    if file_type in ("program", "copybook"):
        clauses.append("file_type=?")
        params.append(file_type)

    if source_keys:
        placeholders = ",".join("?" for _ in source_keys)
        clauses.append(f"source_key IN ({placeholders})")
        params += list(source_keys)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = c.execute(f"SELECT COUNT(*) FROM cobol_programs {where}", params).fetchone()[0]
    offset = (page - 1) * per_page

    rows = c.execute(
        f"SELECT id, filename, member_name, file_type, description, compiled, "
        f"table_count, copy_count, call_count, indexed_at "
        f"FROM cobol_programs {where} ORDER BY filename LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    c.close()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": [dict(r) for r in rows],
    }


def get_program(filename: str) -> dict | None:
    c = _conn()
    row = c.execute("SELECT * FROM cobol_programs WHERE lower(filename)=lower(?)", (filename,)).fetchone()
    if not row:
        c.close()
        return None

    pid = row["id"]
    tables = c.execute(
        "SELECT table_name, operations FROM cobol_tables WHERE program_id=? ORDER BY table_name", (pid,)
    ).fetchall()
    copies = c.execute(
        "SELECT copy_name FROM cobol_copies WHERE program_id=? ORDER BY copy_name", (pid,)
    ).fetchall()
    calls = c.execute(
        "SELECT call_name FROM cobol_calls WHERE program_id=? ORDER BY call_name", (pid,)
    ).fetchall()
    c.close()

    return {
        **dict(row),
        "tables": [{"table_name": r["table_name"], "operations": r["operations"]} for r in tables],
        "copies": [r["copy_name"] for r in copies],
        "calls": [r["call_name"] for r in calls],
    }


def get_programs_for_table(table_name: str) -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT p.filename, p.member_name, p.file_type, p.description, t.operations "
        "FROM cobol_tables t JOIN cobol_programs p ON p.id=t.program_id "
        "WHERE t.table_name=? ORDER BY p.filename",
        (table_name.upper(),)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_copy_deps(filename: str, max_depth: int = 6) -> dict:
    """Return full COPY dependency information for a file (forward + reverse closure).

    COPY statements reference a member by its *filename* (minus the .cbl
    extension), not its parsed member_name — copybooks are frequently plain
    SECTIONs whose member_name has nothing to do with the filename that
    programs COPY them by (e.g. `COPY PTCLOGMS.` targets PTCLOGMS.cbl even
    though that file's only SECTION might be named something else).
    """
    c = _conn()
    fname = filename.lower()
    base = re.sub(r'\.cbl$', '', fname)  # e.g. "ptclogms"

    meta_row = c.execute(
        "SELECT filename, member_name, file_type, description, "
        "table_count, copy_count, call_count FROM cobol_programs "
        "WHERE lower(filename)=? LIMIT 1", (fname,)
    ).fetchone()
    meta = dict(meta_row) if meta_row else None

    fwd_rows = c.execute("""
        WITH RECURSIVE fwd(member, depth) AS (
            SELECT lower(cc.copy_name), 1
              FROM cobol_copies cc
              JOIN cobol_programs p ON p.id = cc.program_id
             WHERE lower(p.filename) = ?
            UNION
            SELECT lower(cc2.copy_name), fwd.depth + 1
              FROM cobol_copies cc2
              JOIN cobol_programs p2 ON p2.id = cc2.program_id
              JOIN fwd ON lower(replace(p2.filename, '.cbl', '')) = fwd.member
             WHERE fwd.depth < ?
        )
        SELECT DISTINCT member FROM fwd ORDER BY member
    """, (fname, max_depth)).fetchall()
    all_copies = [r[0] for r in fwd_rows]

    direct_rows = c.execute(
        "SELECT DISTINCT lower(copy_name) AS cn FROM cobol_copies cc "
        "JOIN cobol_programs p ON p.id=cc.program_id "
        "WHERE lower(p.filename)=? ORDER BY cn",
        (fname,),
    ).fetchall()
    direct_copies = [r[0] for r in direct_rows]

    used_by_direct_rows = c.execute(
        "SELECT DISTINCT lower(p.filename) AS fn, p.file_type, p.description "
        "FROM cobol_copies cc JOIN cobol_programs p ON p.id=cc.program_id "
        "WHERE lower(cc.copy_name)=? ORDER BY fn",
        (base,),
    ).fetchall()
    used_by_direct = [dict(r) for r in used_by_direct_rows]

    rev_rows = c.execute("""
        WITH RECURSIVE rev(fn, depth) AS (
            SELECT lower(p.filename), 1
              FROM cobol_copies cc
              JOIN cobol_programs p ON p.id = cc.program_id
             WHERE lower(cc.copy_name) = ?
            UNION
            SELECT lower(p2.filename), rev.depth + 1
              FROM cobol_copies cc2
              JOIN cobol_programs p2 ON p2.id = cc2.program_id
              JOIN rev ON lower(cc2.copy_name) = replace(rev.fn, '.cbl', '')
             WHERE rev.depth < ?
        )
        SELECT DISTINCT fn FROM rev ORDER BY fn
    """, (base, max_depth)).fetchall()
    used_by_all = [r[0] for r in rev_rows]

    c.close()
    return {
        "filename":       fname,
        "meta":           meta,
        "direct_copies":  direct_copies,
        "all_copies":     all_copies,
        "used_by_direct": used_by_direct,
        "used_by_all":    used_by_all,
    }


def search_source(q: str, file_type: str = None, source_key: str = None, limit: int = 50) -> dict:
    """Search COBOL source text. Returns hits with line-context snippets."""
    if not q or len(q) < 2:
        return {"query": q, "hits": [], "total": 0, "indexed": 0}

    c = _conn()
    total_indexed = c.execute("SELECT COUNT(*) FROM cobol_programs WHERE source_text IS NOT NULL").fetchone()[0]
    total_programs = c.execute("SELECT COUNT(*) FROM cobol_programs").fetchone()[0]

    if total_indexed == 0:
        c.close()
        return {"query": q, "hits": [], "total": 0, "indexed": 0,
                "warning": "Source text not yet indexed. Trigger a Re-index to enable search."}

    predicates = ["LOWER(source_text) LIKE LOWER(:pat)", "source_text IS NOT NULL"]
    params: dict = {"pat": f"%{q}%"}
    if file_type:
        predicates.append("file_type = :ft")
        params["ft"] = file_type.lower()
    if source_key:
        predicates.append("source_key = :sk")
        params["sk"] = source_key

    all_rows = c.execute(
        f"SELECT filename, file_type, source_key, description, source_text "
        f"FROM cobol_programs WHERE {' AND '.join(predicates)} ORDER BY filename",
        params,
    ).fetchall()
    c.close()

    seen: set = set()
    rows = []
    for row in all_rows:
        key = row["filename"].lower()
        if key not in seen:
            seen.add(key)
            rows.append(row)

    has_more = len(rows) > limit
    rows = rows[:limit]

    q_lower = q.lower()
    hits = []
    for row in rows:
        src = row["source_text"] or ""
        lines = src.splitlines()
        snippets = []
        for i, line in enumerate(lines):
            if q_lower in line.lower():
                ctx_start = max(0, i - 1)
                ctx_end = min(len(lines), i + 2)
                snippets.append({
                    "line_no": i + 1,
                    "context": lines[ctx_start:ctx_end],
                    "match_offset": i - ctx_start,
                })
                if len(snippets) >= 5:
                    break
        total_hits = sum(1 for ln in lines if q_lower in ln.lower())
        hits.append({
            "filename": row["filename"],
            "file_type": row["file_type"],
            "source_key": row["source_key"],
            "description": row["description"] or "",
            "total_hits": total_hits,
            "snippets": snippets,
        })

    hits.sort(key=lambda h: h["total_hits"], reverse=True)
    return {
        "query": q, "hits": hits, "total": len(hits), "has_more": has_more,
        "indexed": total_indexed, "total_programs": total_programs,
    }


def source_index_status() -> dict:
    c = _conn()
    total = c.execute("SELECT COUNT(*) FROM cobol_programs").fetchone()[0]
    indexed = c.execute("SELECT COUNT(*) FROM cobol_programs WHERE source_text IS NOT NULL").fetchone()[0]
    c.close()
    return {"total": total, "indexed": indexed, "pct": round(indexed * 100 / total, 1) if total else 0}
