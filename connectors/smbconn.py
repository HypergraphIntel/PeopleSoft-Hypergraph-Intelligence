"""
SMB/CIFS client for reading files off Windows-hosted PeopleSoft domains
(e.g. a Process Scheduler running on Windows, where SSH isn't available).

Same public API shape as sshclient.py (list_files/read_bytes/file_size) so
logingest.py can dispatch to either transport interchangeably. Aliases are
resolved from config.json's "smb_hosts" section; paths passed in are relative
to that host's share (e.g. "appserv/prcs/HRDEV_PRCS_WIN/LOGS/AESRV_*.LOG*").
"""

import fnmatch
import json
import threading
from connectors import paths

_sessions_lock = threading.Lock()
_registered: set[str] = set()   # host keys we've already called register_session() for


def _load_config() -> dict:
    with open(paths.CONFIG_FILE) as f:
        return json.load(f)


def _host_cfg(alias: str) -> dict:
    cfg = _load_config()
    hosts = cfg.get("smb_hosts", {})
    if alias not in hosts:
        raise KeyError(f"SMB host alias '{alias}' not in config.json smb_hosts")
    return hosts[alias]


def _ensure_session(alias: str, hcfg: dict):
    """Register an authenticated SMB session for this host, once per alias."""
    import smbclient

    with _sessions_lock:
        if alias in _registered:
            return
        smbclient.register_session(
            hcfg["host"],
            username=hcfg["username"],
            password=paths.resolve_secret(hcfg["password"]),
            port=hcfg.get("port", 445),
        )
        _registered.add(alias)


def _unc(hcfg: dict, rel_path: str) -> str:
    """Build a UNC path from a host config + share-relative path (forward or back slashes)."""
    rel_path = rel_path.replace("/", "\\").lstrip("\\")
    return f"\\\\{hcfg['host']}\\{hcfg['share']}\\{rel_path}"


def list_files(alias: str, pattern: str) -> list[str]:
    """
    Return sorted list of share-relative file paths matching a glob pattern
    (e.g. "appserv/prcs/HRDEV_PRCS_WIN/LOGS/AESRV_*.LOG*").
    Raises FileNotFoundError if the directory portion doesn't exist.
    """
    import smbclient

    hcfg = _host_cfg(alias)
    _ensure_session(alias, hcfg)

    pattern = pattern.replace("\\", "/")
    directory = pattern.rsplit("/", 1)[0] if "/" in pattern else ""
    basename = pattern.rsplit("/", 1)[-1]

    unc_dir = _unc(hcfg, directory)
    try:
        entries = smbclient.listdir(unc_dir)
    except Exception as exc:
        raise FileNotFoundError(f"Directory not found on smb:{alias}: {directory!r}") from exc

    matched = sorted(f"{directory}/{e}" if directory else e
                      for e in entries if fnmatch.fnmatch(e, basename))
    return matched


def read_bytes(alias: str, path: str, offset: int = 0, max_bytes: int = 4 * 1024 * 1024) -> bytes:
    """
    Read up to max_bytes from a remote file starting at byte offset.
    share_access='rwd' is required because PeopleSoft's own server processes
    hold these log files open (write) at all times — an exclusive-open read
    would otherwise fail with STATUS_SHARING_VIOLATION.
    """
    import smbclient

    hcfg = _host_cfg(alias)
    _ensure_session(alias, hcfg)
    unc_path = _unc(hcfg, path)

    try:
        info = smbclient.stat(unc_path)
        file_size_bytes = info.st_size
    except Exception as exc:
        raise PermissionError(f"Cannot stat {path!r} on smb:{alias} — {exc}") from exc

    if offset >= file_size_bytes:
        return b""

    try:
        with smbclient.open_file(unc_path, mode="rb", share_access="rwd") as f:
            f.seek(offset)
            return f.read(max_bytes)
    except Exception as exc:
        raise PermissionError(f"Cannot read {path!r} on smb:{alias} — {exc}") from exc


def file_size(alias: str, path: str) -> int:
    """Return file size in bytes, or -1 if the file does not exist."""
    import smbclient

    hcfg = _host_cfg(alias)
    _ensure_session(alias, hcfg)
    unc_path = _unc(hcfg, path)
    try:
        return smbclient.stat(unc_path).st_size
    except Exception:
        return -1
