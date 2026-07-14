"""
SSH/SFTP client with per-host connection pooling.
Reads ssh_hosts from config.json; supports key-based and password auth.
Special host alias "local" skips SSH and reads files directly from disk.
"""

import io
import os
import glob
import threading
from pathlib import Path
from typing import Optional
from connectors import paths

_pools: dict[str, object] = {}   # host_alias -> paramiko.SSHClient
_locks: dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def _load_config() -> dict:
    import json
    cfg_path = paths.CONFIG_FILE
    with open(cfg_path) as f:
        return json.load(f)


def _host_cfg(alias: str) -> dict:
    cfg = _load_config()
    hosts = cfg.get("ssh_hosts", {})
    if alias not in hosts:
        raise KeyError(f"SSH host alias '{alias}' not in config.json ssh_hosts")
    return hosts[alias]


def _get_lock(alias: str) -> threading.Lock:
    with _global_lock:
        if alias not in _locks:
            _locks[alias] = threading.Lock()
        return _locks[alias]


def _connect(alias: str):
    """Return a connected paramiko SSHClient for the given alias."""
    try:
        import paramiko
    except ImportError:
        raise RuntimeError("paramiko not installed — run: pip install paramiko")

    hcfg = _host_cfg(alias)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": hcfg["host"],
        "port":     hcfg.get("port", 22),
        "username": hcfg["username"],
        "timeout":  10,
    }

    key_path = hcfg.get("key_path")
    password  = hcfg.get("password")

    if key_path:
        expanded = os.path.expanduser(key_path)
        connect_kwargs["key_filename"] = expanded
    if password:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)
    return client


def _get_client(alias: str):
    """Return a live SSHClient from the pool, reconnecting if needed."""
    lock = _get_lock(alias)
    with lock:
        client = _pools.get(alias)
        if client is not None:
            transport = client.get_transport()
            if transport and transport.is_active():
                return client
            # stale — close and reconnect
            try:
                client.close()
            except Exception:
                pass
        client = _connect(alias)
        _pools[alias] = client
        return client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_files(alias: str, pattern: str) -> list[str]:
    """
    Return sorted list of file paths on remote host matching glob pattern.
    Raises FileNotFoundError if the directory portion of the pattern does not exist.
    """
    if alias == "local":
        return sorted(glob.glob(os.path.expanduser(pattern)))

    client = _get_client(alias)
    sftp = client.open_sftp()
    try:
        directory = os.path.dirname(pattern)
        basename  = os.path.basename(pattern)
        import fnmatch
        try:
            all_files = sftp.listdir(directory)
        except IOError as exc:
            raise FileNotFoundError(
                f"Directory not found on {alias}: {directory!r}"
            ) from exc
        matched = sorted(
            f"{directory}/{f}" for f in all_files if fnmatch.fnmatch(f, basename)
        )
        return matched
    finally:
        sftp.close()


def list_dirs(alias: str, path: str) -> list[str]:
    """
    Return sorted list of subdirectory names (not full paths, not files)
    directly under `path` on the remote host. Raises FileNotFoundError if
    `path` itself does not exist.
    """
    if alias == "local":
        expanded = os.path.expanduser(path)
        try:
            entries = os.listdir(expanded)
        except OSError as exc:
            raise FileNotFoundError(f"Directory not found: {path!r}") from exc
        return sorted(e for e in entries if os.path.isdir(os.path.join(expanded, e)))

    client = _get_client(alias)
    sftp = client.open_sftp()
    try:
        import stat as _stat
        try:
            attrs = sftp.listdir_attr(path)
        except IOError as exc:
            raise FileNotFoundError(
                f"Directory not found on {alias}: {path!r}"
            ) from exc
        return sorted(a.filename for a in attrs if _stat.S_ISDIR(a.st_mode))
    finally:
        sftp.close()


def read_bytes(alias: str, path: str, offset: int = 0, max_bytes: int = 4 * 1024 * 1024) -> bytes:
    """
    Read up to max_bytes from a remote file starting at byte offset.
    Returns bytes (may be empty if offset is at/past EOF).
    Raises PermissionError or FileNotFoundError on access failures.
    """
    if alias == "local":
        with open(path, "rb") as f:
            f.seek(offset)
            return f.read(max_bytes)

    client = _get_client(alias)
    sftp = client.open_sftp()
    try:
        try:
            stat = sftp.stat(path)
            file_size = stat.st_size
        except IOError as exc:
            raise PermissionError(
                f"Cannot stat {path!r} on {alias} — check file permissions for SSH user"
            ) from exc

        if offset >= file_size:
            return b""

        try:
            with sftp.open(path, "rb") as remote_file:
                remote_file.seek(offset)
                return remote_file.read(max_bytes)
        except IOError as exc:
            raise PermissionError(
                f"Cannot read {path!r} on {alias} — check file permissions for SSH user"
            ) from exc
    finally:
        sftp.close()


def file_size(alias: str, path: str) -> int:
    """Return file size in bytes, or -1 if the file does not exist."""
    if alias == "local":
        try:
            return os.path.getsize(path)
        except OSError:
            return -1

    client = _get_client(alias)
    sftp = client.open_sftp()
    try:
        return sftp.stat(path).st_size
    except Exception:
        return -1
    finally:
        sftp.close()


def run_command(alias: str, command: str, timeout: int = 15) -> tuple[str, str, int]:
    """
    Run a read-only shell command on the remote host. Returns (stdout, stderr, exit_status).
    Raises the same exceptions as _connect() on connection failure; a nonzero
    exit_status is returned to the caller rather than raised, since many
    read-only introspection commands (e.g. grep with no matches) exit nonzero
    without indicating a real failure.
    """
    if alias == "local":
        import subprocess
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr, proc.returncode

    client = _get_client(alias)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    return out, err, exit_status


def close_all():
    """Close all pooled connections (call on shutdown)."""
    with _global_lock:
        for alias, client in list(_pools.items()):
            try:
                client.close()
            except Exception:
                pass
        _pools.clear()
