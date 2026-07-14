"""
PeopleSoft Server Trace connector — Phase 12 extension.

When the AI Assistant (or a human) can't determine root cause from metadata,
logic, and data alone, PeopleSoft's own SQL/PeopleCode server trace is the
next level of evidence: a line-by-line record of every SQL statement (with
bind values) and every PeopleCode statement executed during a request.

This connector locates and reads trace files from the app server domain's
LOGS directory (confirmed via live SSH inspection to be where
`psappsrv.cfg`'s `[Trace]` section writes `*.tracesql`/`*.tracepc` output
when `TraceSql`/`TracePC` are non-zero — no separate `TraceDir` is
configured in this environment). It does not parse the PeopleTools trace
format into a bespoke structure — that format is dense but genuinely
human/LLM-readable text (`Sql:`/`Bind-n:` lines, PeopleCode statement
lines), so raw (truncated) text is handed to the AI to read directly, the
same way source code already is via peoplecode_search/sqr_program/
cobol_program, rather than risking a parser built against zero real trace
samples in this environment (TraceSql=0/TracePC=0 by default — tracing has
to be turned on before any trace file exists to parse).
"""

import json
from pathlib import Path
from connectors import paths

CONFIG_PATH = paths.CONFIG_FILE


def _trace_sources() -> dict:
    """Return {ENV: {ssh_host, trace_dir, cfg_path}} from config.json."""
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {s["env"].upper(): s for s in cfg.get("trace_sources", []) if s.get("env")}


def trace_config(env: str) -> dict:
    """Return the real, current TraceSql/TracePC bitfield values for an
    environment's app server domain, read live from psappsrv.cfg — so
    instructions to the user always reflect the actual current state
    (already-on vs. currently-off) rather than a stale assumption."""
    source = _trace_sources().get(env.upper())
    if not source:
        return {"error": f"No trace_sources entry configured for env '{env}'"}

    from connectors import sshclient
    try:
        text = sshclient.read_bytes(source["ssh_host"], source["cfg_path"], max_bytes=200_000).decode(
            "utf-8", errors="replace"
        )
    except Exception as exc:
        return {"error": f"Could not read {source['cfg_path']}: {exc}"}

    import re
    values = {}
    for key in ("TraceSql", "TraceSqlMask", "TracePC", "TracePCMask"):
        m = re.search(rf"^{key}=(\d+)", text, re.MULTILINE)
        values[key] = int(m.group(1)) if m else None

    return {
        "env": env.upper(),
        "cfg_path": source["cfg_path"],
        "trace_dir": source["trace_dir"],
        "current": values,
        "sql_trace_enabled": bool(values.get("TraceSql")),
        "pc_trace_enabled": bool(values.get("TracePC")),
    }


def list_trace_files(env: str, pattern: str = "*.trace*", limit: int = 50) -> dict:
    """List trace files in the environment's app server LOGS directory.

    An empty list is a legitimate, common result — it means tracing hasn't
    been enabled/run yet, not that something is broken. Mirrors the
    "gracefully empty" convention used elsewhere in this codebase for
    real-but-unpopulated categories."""
    source = _trace_sources().get(env.upper())
    if not source:
        return {"error": f"No trace_sources entry configured for env '{env}'", "files": []}

    from connectors import sshclient
    try:
        names = sshclient.list_files(source["ssh_host"], f"{source['trace_dir']}/{pattern}")
    except Exception as exc:
        return {"error": str(exc), "files": [], "trace_dir": source["trace_dir"]}

    files = []
    for name in names[:limit]:
        try:
            size = sshclient.file_size(source["ssh_host"], name)
        except Exception:
            size = None
        files.append({"path": name, "name": Path(name).name, "size_bytes": size})

    files.sort(key=lambda f: f["name"], reverse=True)
    return {"env": env.upper(), "trace_dir": source["trace_dir"], "files": files, "count": len(files)}


def read_trace_file(env: str, filename: str, max_kb: int = 200) -> dict:
    """Read a trace file's content (truncated) for the AI/human to read
    directly. filename may be a bare name (resolved under trace_dir) or a
    full path already returned by list_trace_files()."""
    source = _trace_sources().get(env.upper())
    if not source:
        return {"error": f"No trace_sources entry configured for env '{env}'"}

    path = filename if filename.startswith("/") else f"{source['trace_dir']}/{filename}"
    from connectors import sshclient
    try:
        raw = sshclient.read_bytes(source["ssh_host"], path, max_bytes=max_kb * 1024)
    except FileNotFoundError:
        return {"error": f"Trace file not found: {path}"}
    except Exception as exc:
        return {"error": str(exc)}

    content = raw.decode("utf-8", errors="replace")
    return {
        "env": env.upper(),
        "path": path,
        "content": content,
        "size_bytes": len(raw),
        "truncated": len(raw) >= max_kb * 1024,
    }
