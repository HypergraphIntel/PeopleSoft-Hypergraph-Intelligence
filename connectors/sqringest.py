"""
SSH-based SQR/SQC source indexer.

Reads sqr_sources from config.json, SSHes to each host, reads all .sqr/.sqc files,
parses them with sqrparser, and stores results in sqrdb.

Each source entry in config.json sqr_sources:
  {
    "key":      "fscm_sqr",         # unique identifier
    "env":      "FSCM",             # environment this source belongs to
    "ssh_host": "hcm_appserver",    # ssh_hosts key (or "local")
    "label":    "FSCM SQR Library",
    "sqr_dir":  "/opt/psoft/fin/..."
  }

Incremental scanning: each file's MD5 hash is stored in sqr_programs.content_hash.
On subsequent indexing runs, files whose hash matches the stored value are skipped
(not re-parsed), so only changed or new files are processed.
"""

import hashlib
import logging
import time
from connectors import paths

logger = logging.getLogger("deathstar.sqringest")


def _load_sources() -> list[dict]:
    import json
    from pathlib import Path
    cfg_path = paths.CONFIG_FILE
    with open(cfg_path) as f:
        cfg = json.load(f)
    return cfg.get("sqr_sources", [])


def index_source(source: dict, progress_cb=None) -> dict:
    """
    Index one sqr_source entry. Returns a summary dict.
    progress_cb(done, total) — optional progress callback.
    """
    from connectors import sshclient, sqrparser, sqrdb

    sqrdb.init_db()

    ssh_host    = source["ssh_host"]
    sqr_dir     = source["sqr_dir"].rstrip("/")
    key         = source["key"]
    source_type = source.get("source_type", "")

    indexed  = 0
    skipped  = 0
    errors   = 0
    error_list = []

    for ext in ("sqr", "sqc"):
        try:
            files = sshclient.list_files(ssh_host, f"{sqr_dir}/*.{ext}")
        except FileNotFoundError as exc:
            logger.warning("sqringest: directory not found for %s — %s", key, exc)
            continue

        total = len(files)
        logger.info("sqringest: indexing %d .%s files from %s:%s", total, ext, ssh_host, sqr_dir)

        for i, path in enumerate(files):
            if progress_cb:
                progress_cb(i, total)
            filename = path.split("/")[-1]
            try:
                raw = sshclient.read_bytes(ssh_host, path, max_bytes=512 * 1024)
                file_hash = hashlib.md5(raw).hexdigest()

                # Skip unchanged files (incremental scan)
                stored_hash = sqrdb.get_content_hash(filename, key)
                if stored_hash and stored_hash == file_hash:
                    skipped += 1
                    continue

                try:
                    content = raw.decode("utf-8", errors="replace")
                except Exception:
                    content = raw.decode("latin-1", errors="replace")

                parsed = sqrparser.parse(content, filename=filename)
                sqrdb.upsert_program(parsed, filename, ext, key, source_type,
                                     source_text=content, content_hash=file_hash)
                indexed += 1
            except Exception as exc:
                errors += 1
                error_list.append({"file": filename, "error": str(exc)})
                logger.debug("sqringest: error indexing %s — %s", path, exc)

    return {
        "source_key":   key,
        "label":        source.get("label", key),
        "indexed":      indexed,
        "skipped":      skipped,
        "errors":       errors,
        "error_sample": error_list[:5],
        "ts":           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def index_all() -> list[dict]:
    """Index every source in config.json sqr_sources. Returns list of summaries."""
    sources = _load_sources()
    if not sources:
        logger.info("sqringest: no sqr_sources configured")
        return []
    results = []
    for source in sources:
        logger.info("sqringest: starting index of source '%s'", source.get("key"))
        try:
            result = index_source(source)
            logger.info("sqringest: %s — indexed=%d errors=%d",
                        source["key"], result["indexed"], result["errors"])
        except Exception as exc:
            result = {"source_key": source.get("key"), "error": str(exc)}
            logger.warning("sqringest: source '%s' failed — %s", source.get("key"), exc)
        results.append(result)
    return results
