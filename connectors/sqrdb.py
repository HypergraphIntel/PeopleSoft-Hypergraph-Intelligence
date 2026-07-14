"""
SQLite store for SQR/SQC source artifact index.

Database: data/sqr.db
Schema:
  sqr_programs  — one row per indexed file
  sqr_tables    — PS_ table references (many per program)
  sqr_includes  — #include SQC dependencies (many per program)
  sqr_procedures— begin-procedure definitions (many per program)
"""

import re
import sqlite3
from pathlib import Path
from connectors import paths

DATA_DIR = paths.DATA_DIR
DB_PATH  = DATA_DIR / "sqr.db"

# Same comment-line convention sqrparser.py already relies on for SQL/include
# scanning — reused here so "ignore comments" means the same thing everywhere.
_RE_COMMENT_LINE = re.compile(r'^\s*!.*$', re.MULTILINE)


def _normalize_source(text: str) -> str:
    """Strip comment lines and insignificant whitespace so two programs that
    differ only in commentary/formatting hash the same."""
    no_comments = _RE_COMMENT_LINE.sub('', text)
    lines = [ln.strip() for ln in no_comments.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# begin-procedure/end-procedure pairs delimit SQR's real structural unit —
# confirmed live (battimes.sqr and others) that pairs are not nested in
# real PeopleSoft-delivered SQR, so a simple next-begin-procedure-or-EOF
# boundary is sufficient without needing to track nesting depth.
_RE_BEGIN_PROC_LINE = re.compile(r'(?im)^\s*begin-procedure\s+(\S+).*$')


def _extract_blocks(text: str) -> dict[str, str]:
    """Split SQR source into named blocks keyed by procedure name, plus an
    implicit "(preamble)" block for everything before the first procedure
    (#include, global variable setup, report layout — real changes there
    matter just as much as changes inside a procedure body)."""
    starts = list(_RE_BEGIN_PROC_LINE.finditer(text))
    if not starts:
        return {"(whole file)": text}
    blocks: dict[str, str] = {}
    preamble = text[:starts[0].start()]
    if preamble.strip():
        blocks["(preamble)"] = preamble
    for i, m in enumerate(starts):
        block_end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        blocks[m.group(1).upper()] = text[m.start():block_end]
    return blocks


def _structural_diff(text_a: str, text_b: str) -> dict:
    """Block-level (procedure-level) diff: which named blocks were added,
    removed, changed, or are identical after normalization — real
    structural insight instead of a single whole-file same/different bit.
    A procedure moved to a different position in the file, or an unrelated
    procedure added elsewhere, no longer makes every other procedure look
    "different" the way a whole-file text diff would."""
    blocks_a = _extract_blocks(text_a)
    blocks_b = _extract_blocks(text_b)
    names_a, names_b = set(blocks_a), set(blocks_b)
    changed, same = [], []
    for name in sorted(names_a & names_b):
        if _normalize_source(blocks_a[name]) == _normalize_source(blocks_b[name]):
            same.append(name)
        else:
            changed.append(name)
    return {
        "blocks_added":   sorted(names_b - names_a),
        "blocks_removed": sorted(names_a - names_b),
        "blocks_changed": changed,
        "blocks_same":    same,
    }


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
        # ── Migration: upgrade from UNIQUE(filename) → UNIQUE(filename, source_key)
        # and add source_type column if this is an existing database.
        existing = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='sqr_programs'"
        ).fetchone()

        if existing and "UNIQUE(filename, source_key)" not in (existing[0] or ""):
            # Recreate table with the new composite unique key
            c.executescript("""
                ALTER TABLE sqr_programs RENAME TO sqr_programs_v1;
                CREATE TABLE sqr_programs (
                    id            INTEGER PRIMARY KEY,
                    filename      TEXT NOT NULL,
                    program_name  TEXT,
                    file_type     TEXT,
                    source_key    TEXT,
                    source_type   TEXT,
                    description   TEXT,
                    release       TEXT,
                    revision      TEXT,
                    sqr_date      TEXT,
                    table_count   INTEGER DEFAULT 0,
                    include_count INTEGER DEFAULT 0,
                    proc_count    INTEGER DEFAULT 0,
                    indexed_at    TEXT,
                    UNIQUE(filename, source_key)
                );
                INSERT INTO sqr_programs
                    (id, filename, program_name, file_type, source_key,
                     description, release, revision, sqr_date,
                     table_count, include_count, proc_count, indexed_at)
                SELECT id, filename, program_name, file_type, source_key,
                       description, release, revision, sqr_date,
                       table_count, include_count, proc_count, indexed_at
                  FROM sqr_programs_v1;
                DROP TABLE sqr_programs_v1;
            """)
        elif not existing:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sqr_programs (
                    id            INTEGER PRIMARY KEY,
                    filename      TEXT NOT NULL,
                    program_name  TEXT,
                    file_type     TEXT,
                    source_key    TEXT,
                    source_type   TEXT,
                    description   TEXT,
                    release       TEXT,
                    revision      TEXT,
                    sqr_date      TEXT,
                    table_count   INTEGER DEFAULT 0,
                    include_count INTEGER DEFAULT 0,
                    proc_count    INTEGER DEFAULT 0,
                    indexed_at    TEXT,
                    UNIQUE(filename, source_key)
                );
            """)
        else:
            # Table already has the new schema; ensure new columns exist
            cols = {row[1] for row in c.execute("PRAGMA table_info(sqr_programs)")}
            if "source_type" not in cols:
                c.execute("ALTER TABLE sqr_programs ADD COLUMN source_type TEXT")
            if "source_text" not in cols:
                c.execute("ALTER TABLE sqr_programs ADD COLUMN source_text TEXT")
            if "content_hash" not in cols:
                c.execute("ALTER TABLE sqr_programs ADD COLUMN content_hash TEXT")

        # Fix stale FK references in sub-tables that point to dropped sqr_programs_v1
        for subtbl, unique in (
            ("sqr_includes",   "UNIQUE(program_id, include_file)"),
            ("sqr_procedures", ""),
            ("sqr_tables",     "UNIQUE(program_id, table_name)"),
        ):
            sub_sql = (c.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{subtbl}'"
            ).fetchone() or (None,))[0] or ""
            if "sqr_programs_v1" in sub_sql:
                unique_clause = f", {unique}" if unique else ""
                extra_cols = {
                    "sqr_includes":   "include_file TEXT NOT NULL",
                    "sqr_procedures": "proc_name TEXT NOT NULL",
                    "sqr_tables":     "table_name TEXT NOT NULL, operations TEXT",
                }[subtbl]
                c.execute("PRAGMA foreign_keys=OFF")
                c.executescript(f"""
                    ALTER TABLE {subtbl} RENAME TO {subtbl}_fkfix;
                    CREATE TABLE {subtbl} (
                        program_id INTEGER NOT NULL REFERENCES sqr_programs(id) ON DELETE CASCADE,
                        {extra_cols}{unique_clause}
                    );
                    INSERT OR IGNORE INTO {subtbl} SELECT * FROM {subtbl}_fkfix;
                    DROP TABLE {subtbl}_fkfix;
                """)
                c.execute("PRAGMA foreign_keys=ON")

        c.executescript("""
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



def upsert_program(parsed: dict, filename: str, file_type: str, source_key: str,
                   source_type: str = "", source_text: str = None,
                   content_hash: str = None) -> int:
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
                (filename, program_name, file_type, source_key, source_type, description,
                 release, revision, sqr_date, table_count, include_count, proc_count,
                 indexed_at, source_text, content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(filename, source_key) DO UPDATE SET
                program_name=excluded.program_name,
                file_type=excluded.file_type,
                source_type=excluded.source_type,
                description=excluded.description,
                release=excluded.release,
                revision=excluded.revision,
                sqr_date=excluded.sqr_date,
                table_count=excluded.table_count,
                include_count=excluded.include_count,
                proc_count=excluded.proc_count,
                indexed_at=excluded.indexed_at,
                source_text=excluded.source_text,
                content_hash=excluded.content_hash
        """, (
            filename,
            parsed.get("program_name", ""),
            file_type,
            source_key,
            source_type or "",
            parsed.get("description", ""),
            parsed.get("release", ""),
            parsed.get("revision", ""),
            parsed.get("date", ""),
            len(tables),
            len(includes),
            len(procs),
            now,
            source_text,
            content_hash,
        ))

        row = c.execute(
            "SELECT id FROM sqr_programs WHERE lower(filename)=lower(?) AND source_key=?",
            (filename, source_key)
        ).fetchone()
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


def overrides(env_source_keys: dict[str, list[str]]) -> list[dict]:
    """Return files that exist in BOTH delivered and custom sources for any env.

    env_source_keys = {"HCM": {"delivered": ["hcm_sqr_delivered"],
                                "custom":    ["hcm_sqr_custom"]}, ...}
    Returns list of {filename, env, delivered_key, custom_key, file_type, description}.
    """
    c = _conn()
    results = []
    for env, type_map in env_source_keys.items():
        del_keys = type_map.get("delivered", [])
        cust_keys = type_map.get("custom", [])
        if not del_keys or not cust_keys:
            continue
        del_ph  = ",".join("?" for _ in del_keys)
        cust_ph = ",".join("?" for _ in cust_keys)
        rows = c.execute(f"""
            SELECT d.filename, d.source_key AS delivered_key, cu.source_key AS custom_key,
                   d.file_type, d.description
              FROM sqr_programs d
              JOIN sqr_programs cu
                ON lower(cu.filename) = lower(d.filename)
               AND cu.source_key IN ({cust_ph})
             WHERE d.source_key IN ({del_ph})
             ORDER BY d.filename
        """, list(cust_keys) + list(del_keys)).fetchall()
        for r in rows:
            results.append({"env": env, **dict(r)})
    c.close()
    return results


def override_summary(env_source_keys: dict[str, list[str]]) -> dict:
    """Return delivered-only / custom-only / overridden categorization for
    each env, beyond just the duplicate-filename check `overrides()` does.

    env_source_keys = {"HCM": {"delivered": ["hcm_sqr_delivered"],
                                "custom":    ["hcm_sqr_custom"]}, ...}

    Returns {env: {overridden: [...], delivered_only_count, custom_only_count,
                   custom_only: [...] (capped, see below)}}.

    Notes on what this can and can't detect from a single snapshot:
      - "overridden" = filename present in both delivered and custom trees —
        a genuine customization of a delivered program.
      - "custom_only" = filename present in custom but not delivered. This is
        the practical union of what the roadmap called "custom-only objects"
        and "orphaned customizations" (a custom program whose delivered
        baseline was removed in a later PeopleTools upgrade) — a single
        snapshot can't distinguish "always custom" from "orphaned" without
        historical data, so both are reported under one category rather than
        guessing.
      - "delivered_only" is reported as a count only (can be tens of thousands
        of rows for a full delivered library — not useful as a browsable list,
        just a scale indicator for the two.
      - "missing delivered files" (a delivered file expected but absent) is
        not computed — there's no independent manifest of what *should* exist
        to compare against.
    """
    c = _conn()
    result = {}
    for env, type_map in env_source_keys.items():
        del_keys = type_map.get("delivered", [])
        cust_keys = type_map.get("custom", [])
        if not del_keys or not cust_keys:
            continue
        del_ph = ",".join("?" for _ in del_keys)
        cust_ph = ",".join("?" for _ in cust_keys)

        overridden = c.execute(f"""
            SELECT d.filename, d.source_key AS delivered_key, cu.source_key AS custom_key,
                   d.file_type, d.description
              FROM sqr_programs d
              JOIN sqr_programs cu
                ON lower(cu.filename) = lower(d.filename)
               AND cu.source_key IN ({cust_ph})
             WHERE d.source_key IN ({del_ph})
             ORDER BY d.filename
        """, list(cust_keys) + list(del_keys)).fetchall()

        custom_only = c.execute(f"""
            SELECT cu.filename, cu.source_key AS custom_key, cu.file_type, cu.description
              FROM sqr_programs cu
             WHERE cu.source_key IN ({cust_ph})
               AND NOT EXISTS (
                   SELECT 1 FROM sqr_programs d
                    WHERE lower(d.filename) = lower(cu.filename)
                      AND d.source_key IN ({del_ph})
               )
             ORDER BY cu.filename
        """, list(cust_keys) + list(del_keys)).fetchall()

        delivered_only_count = c.execute(f"""
            SELECT COUNT(*) FROM sqr_programs d
             WHERE d.source_key IN ({del_ph})
               AND NOT EXISTS (
                   SELECT 1 FROM sqr_programs cu
                    WHERE lower(cu.filename) = lower(d.filename)
                      AND cu.source_key IN ({cust_ph})
               )
        """, list(del_keys) + list(cust_keys)).fetchone()[0]

        result[env] = {
            "overridden": [dict(r) for r in overridden],
            "custom_only": [dict(r) for r in custom_only],
            "delivered_only_count": delivered_only_count,
            "counts": {
                "overridden": len(overridden),
                "custom_only": len(custom_only),
                "delivered_only": delivered_only_count,
            },
        }
    c.close()
    return result


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


def search_programs(q: str = "", file_type: str = "", source_keys: list[str] | None = None, page: int = 1, per_page: int = 50) -> dict:
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

    if source_keys:
        placeholders = ",".join("?" for _ in source_keys)
        clauses.append(f"source_key IN ({placeholders})")
        params += list(source_keys)

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


def get_include_tree(filename: str) -> dict:
    """Build recursive SQC include tree with cycle detection. Returns nested dict."""
    c = _conn()

    def _build(fn: str, ancestors: frozenset) -> dict:
        key = fn.lower()
        row = c.execute(
            "SELECT id FROM sqr_programs WHERE lower(filename)=?", (key,)
        ).fetchone()
        if not row:
            return {"filename": fn, "indexed": False, "cyclic": False, "children": []}
        includes = c.execute(
            "SELECT include_file FROM sqr_includes WHERE program_id=? ORDER BY include_file",
            (row["id"],)
        ).fetchall()
        children = []
        for inc_row in includes:
            inc = inc_row["include_file"]
            if inc.lower() in ancestors:
                children.append({"filename": inc, "indexed": True, "cyclic": True, "children": []})
            else:
                children.append(_build(inc, ancestors | {inc.lower()}))
        return {"filename": fn, "indexed": True, "cyclic": False, "children": children}

    tree = _build(filename, frozenset([filename.lower()]))
    c.close()
    return tree


def get_include_deps(filename: str, max_depth: int = 6) -> dict:
    """Return full include dependency information for a file.

    Returns:
        filename         — canonical filename (lowercased)
        meta             — program metadata row (or None if not indexed)
        direct_includes  — DISTINCT list of .sqc files this program directly includes
        all_includes     — recursive closure: all transitively included filenames
        include_tree     — nested tree [{filename, indexed, children:[...]}, ...]
        used_by_direct   — programs that directly #include this file (DISTINCT)
        used_by_all      — recursive reverse closure: all programs that transitively
                           include this file
    """
    c = _conn()
    fname = filename.lower()

    # ── program metadata ────────────────────────────────────────────────────
    meta_row = c.execute(
        "SELECT filename, program_name, file_type, description, "
        "table_count, include_count, proc_count FROM sqr_programs "
        "WHERE lower(filename)=? LIMIT 1",
        (fname,),
    ).fetchone()
    meta = dict(meta_row) if meta_row else None

    # ── forward recursive CTE ────────────────────────────────────────────────
    fwd_rows = c.execute("""
        WITH RECURSIVE fwd(inc, depth) AS (
            SELECT lower(i.include_file), 1
              FROM sqr_includes i
              JOIN sqr_programs p ON p.id = i.program_id
             WHERE lower(p.filename) = ?
            UNION
            SELECT lower(i2.include_file), fwd.depth + 1
              FROM sqr_includes i2
              JOIN sqr_programs p2 ON p2.id = i2.program_id
              JOIN fwd ON lower(p2.filename) = fwd.inc
             WHERE fwd.depth < ?
        )
        SELECT DISTINCT inc FROM fwd ORDER BY inc
    """, (fname, max_depth)).fetchall()
    all_includes = [r[0] for r in fwd_rows]

    # ── direct includes (DISTINCT) ───────────────────────────────────────────
    direct_rows = c.execute(
        "SELECT DISTINCT lower(include_file) AS inc FROM sqr_includes i "
        "JOIN sqr_programs p ON p.id=i.program_id "
        "WHERE lower(p.filename)=? ORDER BY inc",
        (fname,),
    ).fetchall()
    direct_includes = [r[0] for r in direct_rows]

    # ── indexed set lookup ───────────────────────────────────────────────────
    all_to_visit = {fname} | set(all_includes)
    if all_to_visit:
        ph = ",".join("?" for _ in all_to_visit)
        indexed_set = {
            r[0] for r in c.execute(
                f"SELECT lower(filename) FROM sqr_programs WHERE lower(filename) IN ({ph})",
                list(all_to_visit),
            ).fetchall()
        }
    else:
        indexed_set = set()

    # ── build children_map (DISTINCT) for tree construction ─────────────────
    if all_to_visit:
        ph2 = ",".join("?" for _ in all_to_visit)
        edge_rows = c.execute(
            f"SELECT DISTINCT lower(p.filename) AS parent, lower(i.include_file) AS child "
            f"FROM sqr_includes i JOIN sqr_programs p ON p.id=i.program_id "
            f"WHERE lower(p.filename) IN ({ph2})",
            list(all_to_visit),
        ).fetchall()
        children_map: dict[str, list[str]] = {}
        for er in edge_rows:
            children_map.setdefault(er[0], []).append(er[1])
    else:
        children_map = {}

    def _build_tree(node: str, visited: set, depth: int) -> list[dict]:
        if depth >= max_depth:
            return []
        kids = sorted(children_map.get(node, []))
        result = []
        for k in kids:
            entry = {"filename": k, "indexed": k in indexed_set}
            if k not in visited:
                entry["children"] = _build_tree(k, visited | {k}, depth + 1)
            else:
                entry["children"] = []
                entry["cycle"] = True
            result.append(entry)
        return result

    include_tree = _build_tree(fname, {fname}, 0)

    # ── reverse direct users (DISTINCT) ─────────────────────────────────────
    used_by_direct_rows = c.execute(
        "SELECT DISTINCT lower(p.filename) AS fn, p.file_type, p.description "
        "FROM sqr_includes i JOIN sqr_programs p ON p.id=i.program_id "
        "WHERE lower(i.include_file)=? ORDER BY fn",
        (fname,),
    ).fetchall()
    used_by_direct = [dict(r) for r in used_by_direct_rows]

    # ── reverse recursive CTE ────────────────────────────────────────────────
    rev_rows = c.execute("""
        WITH RECURSIVE rev(fn, depth) AS (
            SELECT lower(p.filename), 1
              FROM sqr_includes i
              JOIN sqr_programs p ON p.id = i.program_id
             WHERE lower(i.include_file) = ?
            UNION
            SELECT lower(p2.filename), rev.depth + 1
              FROM sqr_includes i2
              JOIN sqr_programs p2 ON p2.id = i2.program_id
              JOIN rev ON lower(i2.include_file) = rev.fn
             WHERE rev.depth < ?
        )
        SELECT DISTINCT fn FROM rev ORDER BY fn
    """, (fname, max_depth)).fetchall()
    used_by_all = [r[0] for r in rev_rows]

    c.close()
    return {
        "filename":        fname,
        "meta":            meta,
        "direct_includes": direct_includes,
        "all_includes":    all_includes,
        "include_tree":    include_tree,
        "used_by_direct":  used_by_direct,
        "used_by_all":     used_by_all,
    }


def search_source(q: str, file_type: str = None, source_key: str = None, limit: int = 50) -> dict:
    """Search SQR/SQC source text. Returns hits with line-context snippets."""
    if not q or len(q) < 2:
        return {"query": q, "hits": [], "total": 0, "indexed": 0}

    c = _conn()
    total_indexed = c.execute(
        "SELECT COUNT(*) FROM sqr_programs WHERE source_text IS NOT NULL"
    ).fetchone()[0]
    total_programs = c.execute("SELECT COUNT(*) FROM sqr_programs").fetchone()[0]

    if total_indexed == 0:
        c.close()
        return {"query": q, "hits": [], "total": 0, "indexed": 0,
                "warning": "Source text not yet indexed. Trigger a Re-index to enable search."}

    predicates = ["LOWER(source_text) LIKE LOWER(:pat)", "source_text IS NOT NULL"]
    params: dict = {"pat": f"%{q}%", "limit": limit + 1}

    if file_type:
        predicates.append("file_type = :ft")
        params["ft"] = file_type.lower()
    if source_key:
        predicates.append("source_key = :sk")
        params["sk"] = source_key

    all_rows = c.execute(
        f"SELECT filename, file_type, source_key, description, source_text"
        f"  FROM sqr_programs WHERE {' AND '.join(predicates)}"
        f" ORDER BY filename",
        params,
    ).fetchall()
    c.close()

    # Deduplicate by filename (same file indexed under multiple source_keys)
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
        "query": q,
        "hits": hits,
        "total": len(hits),
        "has_more": has_more,
        "indexed": total_indexed,
        "total_programs": total_programs,
    }


def source_index_status() -> dict:
    """Return count of programs with source_text populated vs total."""
    c = _conn()
    total = c.execute("SELECT COUNT(*) FROM sqr_programs").fetchone()[0]
    indexed = c.execute(
        "SELECT COUNT(*) FROM sqr_programs WHERE source_text IS NOT NULL"
    ).fetchone()[0]
    c.close()
    return {"total": total, "indexed": indexed, "pct": round(indexed * 100 / total, 1) if total else 0}


def get_content_hash(filename: str, source_key: str) -> str | None:
    """Return the stored MD5 content_hash for a given program, or None if not set."""
    c = _conn()
    row = c.execute(
        "SELECT content_hash FROM sqr_programs WHERE lower(filename)=lower(?) AND source_key=?",
        (filename, source_key),
    ).fetchone()
    c.close()
    return row["content_hash"] if row else None


def envcompare_sqr(source_keys_a: list[str], source_keys_b: list[str],
                   label_a: str = "A", label_b: str = "B",
                   diff_mode: str = "exact") -> dict:
    """Compare two sets of SQR source keys and return a side-by-side diff.

    diff_mode:
        "exact"      — raw content_hash equality (default, unchanged behavior)
        "normalized" — ignore comment lines and insignificant whitespace;
                       only content_hash-differing pairs are re-checked (an
                       extra source_text fetch), so exact mode stays cheap.

    Returns:
        label_a, label_b     — display labels
        only_a               — files present in A but not B (list of {filename, file_type, description, table_count})
        only_b               — files present in B but not A
        in_both              — files in both with comparison columns
        counts               — summary counts
    """
    c = _conn()

    def _fetch(keys: list[str]) -> dict:
        if not keys:
            return {}
        ph = ",".join("?" for _ in keys)
        rows = c.execute(
            f"SELECT lower(filename) AS fn, filename, file_type, description, "
            f"table_count, include_count, proc_count, content_hash "
            f"FROM sqr_programs WHERE source_key IN ({ph})",
            list(keys),
        ).fetchall()
        # dedupe by filename (take first row per filename across source keys)
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
            or ra["include_count"] != rb["include_count"]
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
            "include_count_a": ra["include_count"],
            "include_count_b": rb["include_count"],
            "content_hash_a": ra.get("content_hash"),
            "content_hash_b": rb.get("content_hash"),
            "changed": changed,
            "content_normalized_same": None,
        })

    if diff_mode == "normalized" and hash_diff_keys:
        ph = ",".join("?" for _ in hash_diff_keys)
        src_rows = c.execute(
            f"SELECT lower(filename) AS fn, source_key, source_text "
            f"FROM sqr_programs WHERE lower(filename) IN ({ph}) "
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
                        or row["include_count_a"] != row["include_count_b"]
                        or row["description_a"] != row["description_b"]
                    )
                else:
                    # Still genuinely different after normalization — this
                    # is exactly where "changed: true" alone isn't useful;
                    # break it down by which procedure(s) actually differ.
                    texts = by_fn.get(fn_lower, {})
                    text_a = next((texts[sk] for sk in source_keys_a if sk in texts and texts[sk] is not None), None)
                    text_b = next((texts[sk] for sk in source_keys_b if sk in texts and texts[sk] is not None), None)
                    if text_a is not None and text_b is not None:
                        row["structural_diff"] = _structural_diff(text_a, text_b)

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
