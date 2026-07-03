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

# Same fixed-format comment convention cobolparser.py already relies on
# (column 7 '*') — reused here so "ignore comments" means the same thing
# everywhere.
_RE_COMMENT_LINE = re.compile(r'^\s*\*.*$', re.MULTILINE)


def _normalize_source(text: str) -> str:
    """Strip comment lines and insignificant whitespace so two programs that
    differ only in commentary/formatting hash the same."""
    no_comments = _RE_COMMENT_LINE.sub('', text)
    lines = [ln.strip() for ln in no_comments.splitlines()]
    return "\n".join(ln for ln in lines if ln)


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
        "SUM(compiled) AS compiled, "
        "SUM(table_count) AS total_table_refs, "
        "SUM(copy_count) AS total_copies, "
        "SUM(call_count) AS total_calls "
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
        "total_table_refs":  row["total_table_refs"] or 0,
        "total_copies":      row["total_copies"] or 0,
        "total_calls":       row["total_calls"] or 0,
        "distinct_ps_tables": distinct_tables or 0,
        "last_indexed":      last_indexed,
    }


def analytics() -> dict:
    """Return analytics data for the COBOL library (mirrors sqrdb.analytics())."""
    c = _conn()

    top_tables = c.execute("""
        SELECT t.table_name,
               COUNT(DISTINCT t.program_id) AS program_count,
               SUM(CASE WHEN p.file_type='program' THEN 1 ELSE 0 END) AS program_type_count,
               GROUP_CONCAT(DISTINCT
                 REPLACE(REPLACE(REPLACE(t.operations,'SELECT','S'),'UPDATE','U'),
                   'INSERT','I')
               ) AS ops_summary
          FROM cobol_tables t
          JOIN cobol_programs p ON p.id = t.program_id
         GROUP BY t.table_name
         ORDER BY program_count DESC
         LIMIT 30
    """).fetchall()

    top_programs = c.execute("""
        SELECT filename, member_name, file_type, description,
               table_count, copy_count, call_count
          FROM cobol_programs
         WHERE file_type = 'program'
         ORDER BY table_count DESC
         LIMIT 20
    """).fetchall()

    top_copies = c.execute("""
        SELECT copy_name, COUNT(DISTINCT program_id) AS user_count
          FROM cobol_copies
         GROUP BY copy_name
         ORDER BY user_count DESC
         LIMIT 20
    """).fetchall()

    type_breakdown = c.execute("""
        SELECT source_type AS typ,
               COUNT(*) AS cnt,
               SUM(CASE WHEN file_type='program' THEN 1 ELSE 0 END) AS program_cnt,
               SUM(CASE WHEN file_type='copybook' THEN 1 ELSE 0 END) AS copybook_cnt
          FROM cobol_programs
         GROUP BY source_type
         ORDER BY cnt DESC
    """).fetchall()

    c.close()
    return {
        "top_tables":      [dict(r) for r in top_tables],
        "top_programs":    [dict(r) for r in top_programs],
        "top_copies":      [dict(r) for r in top_copies],
        "type_breakdown":  [dict(r) for r in type_breakdown],
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


def envcompare_cobol(source_keys_a: list[str], source_keys_b: list[str],
                      label_a: str = "A", label_b: str = "B",
                      diff_mode: str = "exact") -> dict:
    """Compare two sets of COBOL source keys and return a side-by-side diff.

    Same shape as sqrdb.envcompare_sqr() — a patch/drift-integrity check across
    environments, not because COBOL and SQR need parity, but because both are
    delivered-artifact trees where "did one environment get patched without the
    other" is the same real question.

    diff_mode:
        "exact"      — raw content_hash equality (default, unchanged behavior)
        "normalized" — ignore comment lines and insignificant whitespace;
                       only content_hash-differing pairs are re-checked.

    Returns:
        label_a, label_b — display labels
        only_a           — files present in A but not B
        only_b           — files present in B but not A
        in_both          — files in both with comparison columns
        counts           — summary counts
    """
    c = _conn()

    def _fetch(keys: list[str]) -> dict:
        if not keys:
            return {}
        ph = ",".join("?" for _ in keys)
        rows = c.execute(
            f"SELECT lower(filename) AS fn, filename, file_type, description, "
            f"table_count, copy_count, call_count, content_hash "
            f"FROM cobol_programs WHERE source_key IN ({ph})",
            list(keys),
        ).fetchall()
        seen = {}
        for r in rows:
            if r["fn"] not in seen:
                seen[r["fn"]] = dict(r)
        return seen

    map_a = _fetch(source_keys_a)
    map_b = _fetch(source_keys_b)

    keys_a = set(map_a)
    keys_b = set(map_b)

    only_a = sorted(
        [{"filename": map_a[k]["filename"], "file_type": map_a[k]["file_type"],
          "description": map_a[k]["description"], "table_count": map_a[k]["table_count"]}
         for k in keys_a - keys_b],
        key=lambda x: x["filename"],
    )
    only_b = sorted(
        [{"filename": map_b[k]["filename"], "file_type": map_b[k]["file_type"],
          "description": map_b[k]["description"], "table_count": map_b[k]["table_count"]}
         for k in keys_b - keys_a],
        key=lambda x: x["filename"],
    )
    in_both = []
    hash_diff_keys = []
    for k in sorted(keys_a & keys_b):
        ra, rb = map_a[k], map_b[k]
        hash_diff = bool(ra.get("content_hash") and rb.get("content_hash")
                          and ra["content_hash"] != rb["content_hash"])
        if hash_diff:
            hash_diff_keys.append(k)
        changed = (
            ra["table_count"] != rb["table_count"]
            or ra["copy_count"] != rb["copy_count"]
            or ra["call_count"] != rb["call_count"]
            or ra["description"] != rb["description"]
            or hash_diff
        )
        in_both.append({
            "filename": ra["filename"],
            "file_type": ra["file_type"],
            "description_a": ra["description"],
            "description_b": rb["description"],
            "table_count_a": ra["table_count"],
            "table_count_b": rb["table_count"],
            "copy_count_a": ra["copy_count"],
            "copy_count_b": rb["copy_count"],
            "call_count_a": ra["call_count"],
            "call_count_b": rb["call_count"],
            "content_hash_a": ra.get("content_hash"),
            "content_hash_b": rb.get("content_hash"),
            "changed": changed,
            "content_normalized_same": None,
        })

    if diff_mode == "normalized" and hash_diff_keys:
        ph = ",".join("?" for _ in hash_diff_keys)
        src_rows = c.execute(
            f"SELECT lower(filename) AS fn, source_key, source_text "
            f"FROM cobol_programs WHERE lower(filename) IN ({ph}) "
            f"AND source_key IN ({','.join('?' for _ in source_keys_a + source_keys_b)})",
            hash_diff_keys + source_keys_a + source_keys_b,
        ).fetchall()
        by_fn: dict[str, dict[str, str]] = {}
        for r in src_rows:
            by_fn.setdefault(r["fn"], {})[r["source_key"]] = r["source_text"]

        norm_same = set()
        for k in hash_diff_keys:
            texts = by_fn.get(k, {})
            text_a = next((texts[sk] for sk in source_keys_a if sk in texts and texts[sk] is not None), None)
            text_b = next((texts[sk] for sk in source_keys_b if sk in texts and texts[sk] is not None), None)
            if text_a is None or text_b is None:
                continue
            if _normalize_source(text_a) == _normalize_source(text_b):
                norm_same.add(k)

        for row in in_both:
            fn_lower = row["filename"].lower()
            if fn_lower in hash_diff_keys:
                is_same = fn_lower in norm_same
                row["content_normalized_same"] = is_same
                if is_same:
                    row["changed"] = (
                        row["table_count_a"] != row["table_count_b"]
                        or row["copy_count_a"] != row["copy_count_b"]
                        or row["call_count_a"] != row["call_count_b"]
                        or row["description_a"] != row["description_b"]
                    )

    c.close()

    changed_count = sum(1 for r in in_both if r["changed"])
    return {
        "label_a":      label_a,
        "label_b":      label_b,
        "diff_mode":    diff_mode,
        "only_a":       only_a,
        "only_b":       only_b,
        "in_both":      in_both,
        "counts": {
            "only_a":    len(only_a),
            "only_b":    len(only_b),
            "in_both":   len(in_both),
            "changed":   changed_count,
            "identical": len(in_both) - changed_count,
            "total_a":   len(map_a),
            "total_b":   len(map_b),
        },
    }
