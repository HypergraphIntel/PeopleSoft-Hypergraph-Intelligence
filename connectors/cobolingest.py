"""
SSH-based PeopleSoft COBOL source indexer.

Reads cobol_sources from config.json, SSHes to each host, reads all .cbl
files under cbl_src_dir, parses them with cobolparser, and stores results
in cobol_db. Also lists cbl_compiled_dir (best-effort) to flag whether a
compiled binary exists for each program.

Each source entry in config.json cobol_sources:
  {
    "key":             "hcm_cobol_delivered",
    "env":             "HCM",
    "source_type":     "delivered",
    "ssh_host":        "hcm_appserver",
    "label":           "HCM COBOL Library - Delivered",
    "cbl_src_dir":      "/opt/psoft/hcm/ps_app_home/ps_home8.62.07/src/cbl",
    "cbl_compiled_dir": "/opt/psoft/hcm/ps_app_home/ps_home8.62.07/cblbin"
  }

Many delivered .cbl files are owner-only (mode 700) on the PeopleSoft
filesystem and are not readable by the SSH service account — this is
expected, not an error. Per-file permission/read failures are counted
and reported, never raised, per the "grant-aware, read-only, warn not
crash" architecture rule.

Incremental scanning: each file's MD5 hash is stored in
cobol_programs.content_hash; files whose hash matches are skipped.
"""

import hashlib
import logging
import time

logger = logging.getLogger("deathstar.cobolingest")


def _load_sources() -> list[dict]:
    import json
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent / "config.json"
    with open(cfg_path) as f:
        cfg = json.load(f)
    return cfg.get("cobol_sources", [])


def _list_compiled_names(ssh_host: str, compiled_dir: str) -> set[str]:
    """Best-effort listing of the compiled-binary directory. Returns a set of
    uppercased base names (without extension) found there. Never raises."""
    from connectors import sshclient
    if not compiled_dir:
        return set()
    try:
        files = sshclient.list_files(ssh_host, f"{compiled_dir.rstrip('/')}/*")
    except Exception as exc:
        logger.debug("cobolingest: compiled dir listing failed for %s — %s", compiled_dir, exc)
        return set()
    names = set()
    for path in files:
        base = path.split("/")[-1].split(".")[0]
        if base:
            names.add(base.upper())
    return names


def index_source(source: dict, progress_cb=None) -> dict:
    """Index one cobol_source entry. Returns a summary dict.
    progress_cb(done, total) — optional progress callback."""
    from connectors import sshclient, cobolparser, cobol_db

    cobol_db.init_db()

    ssh_host    = source["ssh_host"]
    src_dir     = source["cbl_src_dir"].rstrip("/")
    compiled_dir = source.get("cbl_compiled_dir", "")
    key         = source["key"]
    source_type = source.get("source_type", "")

    compiled_names = _list_compiled_names(ssh_host, compiled_dir)

    indexed = 0
    skipped = 0
    errors  = 0
    denied  = 0
    error_list = []

    try:
        files = sshclient.list_files(ssh_host, f"{src_dir}/*.cbl")
    except FileNotFoundError as exc:
        logger.warning("cobolingest: directory not found for %s — %s", key, exc)
        return {
            "source_key": key, "label": source.get("label", key),
            "indexed": 0, "skipped": 0, "errors": 0, "denied": 0,
            "error_sample": [], "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "warning": f"cbl_src_dir not found: {src_dir}",
        }

    total = len(files)
    logger.info("cobolingest: indexing %d .cbl files from %s:%s", total, ssh_host, src_dir)

    for i, path in enumerate(files):
        if progress_cb:
            progress_cb(i, total)
        filename = path.split("/")[-1]
        try:
            raw = sshclient.read_bytes(ssh_host, path, max_bytes=512 * 1024)
        except PermissionError as exc:
            denied += 1
            error_list.append({"file": filename, "error": f"permission denied: {exc}"})
            continue
        except Exception as exc:
            errors += 1
            error_list.append({"file": filename, "error": str(exc)})
            logger.debug("cobolingest: error reading %s — %s", path, exc)
            continue

        try:
            file_hash = hashlib.md5(raw).hexdigest()
            stored_hash = cobol_db.get_content_hash(filename, key)
            if stored_hash and stored_hash == file_hash:
                skipped += 1
                continue

            try:
                content = raw.decode("utf-8", errors="replace")
            except Exception:
                content = raw.decode("latin-1", errors="replace")

            parsed = cobolparser.parse(content, filename=filename)
            base_name = filename.rsplit(".", 1)[0].upper()
            compiled = base_name in compiled_names
            cobol_db.upsert_program(parsed, filename, key, source_type,
                                     compiled=compiled, source_text=content,
                                     content_hash=file_hash)
            indexed += 1
        except Exception as exc:
            errors += 1
            error_list.append({"file": filename, "error": str(exc)})
            logger.debug("cobolingest: error parsing %s — %s", path, exc)

    return {
        "source_key":   key,
        "label":        source.get("label", key),
        "indexed":      indexed,
        "skipped":      skipped,
        "errors":       errors,
        "denied":       denied,
        "error_sample": error_list[:5],
        "ts":           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def index_all() -> list[dict]:
    """Index every source in config.json cobol_sources. Returns list of summaries."""
    sources = _load_sources()
    if not sources:
        logger.info("cobolingest: no cobol_sources configured")
        return []
    results = []
    for source in sources:
        logger.info("cobolingest: starting index of source '%s'", source.get("key"))
        try:
            result = index_source(source)
            logger.info("cobolingest: %s — indexed=%d denied=%d errors=%d",
                        source["key"], result["indexed"], result.get("denied", 0), result["errors"])
        except Exception as exc:
            result = {"source_key": source.get("key"), "error": str(exc)}
            logger.warning("cobolingest: source '%s' failed — %s", source.get("key"), exc)
        results.append(result)
    return results
