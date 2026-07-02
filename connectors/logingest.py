"""
Log ingestion orchestrator.

For each enabled log source:
  1. Resolve the glob pattern via SSH (or local) to get file list
  2. For each file, read only new bytes since the last known offset
  3. Parse lines with the appropriate parser
  4. Insert into logdb (web_entries / app_entries / log_errors)
  5. Save updated byte offsets back to logdb

Called by scheduler.py every 60 seconds.
Can also be called manually: python -m connectors.logingest
"""

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("logingest")

_WEB_TYPES   = {"pia_access", "apache_access", "f5_access"}
_APP_TYPES   = {"appsrv", "prcs_ae", "tuxedo", "pia_error", "pia_servlet", "pia_weblogic", "pia_stdout", "apache_error"}
_BLOCK_TYPES = {"igw_error_log"}   # multi-line HTML block parsers — not line-by-line


def _load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        return json.load(f)


def run_ingest():
    """Main entry point — ingest all enabled log sources."""
    try:
        from connectors import logdb, sshclient
        from connectors.logparser import parse_line
    except ImportError as exc:
        log.error("logingest: missing dependency: %s", exc)
        return

    cfg = _load_config()
    logdb.init_db()

    # Standard log sources
    sources = cfg.get("log_sources", [])
    if sources:
        logdb.upsert_sources([s for s in sources if s.get("name")])
        for src in logdb.get_sources(enabled_only=True):
            if src["type"] not in _BLOCK_TYPES:
                _ingest_source(src, logdb, sshclient, parse_line)

    # IGW log sources (block-based HTML parsers)
    igw_sources = cfg.get("igw_log_sources", [])
    if igw_sources:
        logdb.upsert_sources([s for s in igw_sources if s.get("name")])
        for src in logdb.get_sources(enabled_only=True):
            if src["type"] in _BLOCK_TYPES:
                _ingest_source(src, logdb, sshclient, parse_line)


def _ingest_source(src: dict, logdb, sshclient, parse_line):
    name     = src["name"]
    env      = src["env"]
    ssh_host = src["ssh_host"]
    pattern  = src["path"]
    log_type = src["type"]

    try:
        files = sshclient.list_files(ssh_host, pattern)
    except Exception as exc:
        log.warning("logingest[%s]: list_files failed: %s", name, exc)
        logdb.mark_ingest_done(name, error=str(exc))
        return

    if not files:
        msg = f"No files matched pattern: {pattern}"
        log.warning("logingest[%s]: %s", name, msg)
        logdb.mark_ingest_done(name, error=msg)
        return

    offsets = logdb.get_offsets(name)
    new_offsets = dict(offsets)
    file_errors = []

    for filepath in files:
        err = _ingest_file(
            name, env, ssh_host, filepath, log_type,
            offsets, new_offsets, logdb, sshclient, parse_line
        )
        if err:
            file_errors.append(err)

    logdb.save_offsets(name, new_offsets)
    error_summary = "; ".join(file_errors[:2]) if file_errors else None
    logdb.mark_ingest_done(name, error=error_summary)


def _ingest_file(source_name: str, env: str, ssh_host: str, filepath: str,
                 log_type: str, offsets: dict, new_offsets: dict,
                 logdb, sshclient, parse_line) -> Optional[str]:
    """Returns an error string if the file could not be read, else None."""
    offset = offsets.get(filepath, 0)

    try:
        raw_bytes = sshclient.read_bytes(ssh_host, filepath, offset=offset)
    except Exception as exc:
        msg = f"read failed ({filepath}): {exc}"
        log.warning("logingest[%s]: %s", source_name, msg)
        return msg

    if not raw_bytes:
        return None

    text = raw_bytes.decode("utf-8", errors="replace")

    web_rows:   list[dict] = []
    app_rows:   list[dict] = []
    error_rows: list[dict] = []

    if log_type in _BLOCK_TYPES:
        # Block parsers consume the entire content at once.
        # For HTML logs, we can only safely consume complete entries.
        # Entries are bounded by <BODY> tags; keep any partial trailing block.
        from connectors.logparser import parse_igw_error_log
        if log_type == "igw_error_log":
            # Find the last complete entry boundary before EOF
            last_body = text.rfind("<BODY", 0, len(text) - 1)
            if last_body > 0:
                safe_text      = text[:last_body]
                partial_bytes  = text[last_body:].encode("utf-8", errors="replace")
                consumed_bytes = len(raw_bytes) - len(partial_bytes)
            else:
                safe_text      = text
                consumed_bytes = len(raw_bytes)
            rows = parse_igw_error_log(safe_text)
            for row in rows:
                row.pop("_igw", None)   # don't store the extra detail dict
                app_rows.append(row)
                error_rows.append(row)  # IGW entries are always errors
    else:
        lines = text.splitlines()
        # If the read ended mid-line keep the partial tail for next cycle
        if not text.endswith("\n"):
            complete_lines = lines[:-1]
            partial_tail   = lines[-1].encode("utf-8", errors="replace")
            consumed_bytes = len(raw_bytes) - len(partial_tail)
        else:
            complete_lines = lines
            consumed_bytes = len(raw_bytes)

        for line in complete_lines:
            if not line.strip():
                continue
            try:
                row = parse_line(log_type, line)
            except Exception:
                row = None
            if row is None:
                continue

            if log_type in _WEB_TYPES:
                web_rows.append(row)
                if row.get("is_error"):
                    error_rows.append(row)
            else:
                app_rows.append(row)
                if row.get("is_error"):
                    error_rows.append(row)

    if web_rows:
        logdb.insert_web_entries(source_name, env, web_rows)
    if app_rows:
        logdb.insert_app_entries(source_name, env, app_rows)
    if error_rows:
        logdb.insert_errors(source_name, env, log_type, error_rows)

    new_offsets[filepath] = offset + consumed_bytes
    log.debug(
        "logingest[%s]: %s +%d bytes → %d web, %d app, %d errors",
        source_name, filepath, consumed_bytes, len(web_rows), len(app_rows), len(error_rows)
    )
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")
    run_ingest()
