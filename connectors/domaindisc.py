"""
Filesystem-based PeopleSoft domain discovery.

Replaces the PSPMDOMAIN_VW-based approach (connectors/psdb.app_server_domains)
for environments where Performance Monitor is not configured/running —
PSPMDOMAIN_VW is populated by the PSPM agent, so it is empty or stale
whenever PSPM isn't set up, independent of whether the domains themselves
are healthy.

Instead, this reads domain names directly from PeopleSoft's own directory
layout under `<ps_cfg_home>/appserv/*` (App Server + Process Scheduler
domains) and `<ps_cfg_home>/webserv/*` (Web/PIA domains) via SSH/SFTP.
Domain type is derived from *which tree the directory lives under* plus a
`_PRCS`/`PRCSDOM` name-substring check for Process Scheduler — not from
guessing based on domain-name suffixes alone, which is unreliable for
domains that don't follow the `_APP`/`_WEB` naming convention.

Each PeopleSoft environment in config.json's `peoplesoft.environments`
supplies `ssh_host` (an alias into `ssh_hosts`) and `ps_cfg_home` (the
PS_CFG_HOME root for that environment/pillar) — both configurable, no
hardcoded paths or environment names.
"""

import json
import re
from pathlib import Path

from connectors import sshclient

CONFIG = Path(__file__).parent.parent / "config.json"

_PRCS_NAME_HINT = "PRCS"  # matches "prcs", "_PRCS", "PRCSDOM", "HRPRCS01", etc.

# psappsrv.cfg section + key structure for each App Server listener type,
# confirmed against real file content (not psadmin's display labels, which
# turned out not to match the literal INI text — see DEVELOPMENT_DIARY.md
# 2026-07-13 sessions 8-10). The real structure is section-scoped: each
# listener has its own section, and within it the plain port is the key
# literally named "PORT" and the encrypted port is "SSL PORT" — neither
# key is prefixed with "WSL"/"JSL"/"JRAD", so matching must select the
# section first (by header) and then read fixed key names inside it.
_APP_LISTENER_SECTIONS = {
    "wsl":  (("WORKSTATION", "LISTENER"), ()),
    "jsl":  (("JOLT", "LISTENER"), ("RELAY",)),   # exclude "JOLT RELAY ADAPTER"
    "jrad": (("RELAY",), ()),                      # "JOLT RELAY ADAPTER"
}
# (result field, section key above, INI key name within that section)
_APP_PORT_FIELDS = [
    ("wsl_port",     "wsl",  "PORT"),
    ("wsl_ssl_port", "wsl",  "SSL PORT"),
    ("jsl_port",     "jsl",  "PORT"),
    ("jsl_ssl_port", "jsl",  "SSL PORT"),
    ("jrad_port",    "jrad", "LISTENER PORT"),
]

_WEB_LISTEN_PORT_RE = re.compile(r"<listen-port>\s*(\d+)\s*</listen-port>", re.IGNORECASE)
_WEB_SSL_BLOCK_RE = re.compile(r"<ssl\b.*?</ssl>", re.IGNORECASE | re.DOTALL)


def _load_env(env_name: str) -> dict | None:
    data = json.loads(CONFIG.read_text())
    for e in data["peoplesoft"]["environments"]:
        if e["name"].upper() == env_name.upper():
            return e
    return None


def load_environments() -> list[dict]:
    data = json.loads(CONFIG.read_text())
    return data["peoplesoft"]["environments"]


def _resolve_hostname(ssh_host_alias: str) -> str:
    """Resolve an ssh_hosts alias (e.g. 'hcm_appserver') to the real
    hostname/IP it points to, so the UI shows the actual server address
    instead of the internal config key."""
    data = json.loads(CONFIG.read_text())
    hcfg = data.get("ssh_hosts", {}).get(ssh_host_alias, {})
    return hcfg.get("host") or ssh_host_alias


def _classify_appserv_dir(name: str) -> tuple[str, str]:
    if _PRCS_NAME_HINT in name.upper():
        return "process_scheduler", "Process Scheduler"
    return "app_server", "App Server"


def _read_text(ssh_host: str, path: str, max_bytes: int = 65536) -> str | None:
    """Best-effort remote text read; returns None on any failure (missing
    file, permission denied, etc.) rather than raising — port detail is a
    nice-to-have enrichment, not required for domain discovery to work."""
    try:
        data = sshclient.read_bytes(ssh_host, path, max_bytes=max_bytes)
        if not data:
            return None
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def _parse_ini_sections(text: str) -> dict[str, dict[str, str]]:
    """Parse an INI-style config file (psappsrv.cfg) into
    {SECTION_HEADER_UPPER: {KEY_UPPER: value}}, single pass."""
    sections: dict[str, dict[str, str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1].upper()
            sections.setdefault(current, {})
            continue
        if current is not None and "=" in stripped:
            key, _, val = stripped.partition("=")
            sections[current][key.strip().upper()] = val.strip()
    return sections


def _find_section(sections: dict[str, dict[str, str]], must_have: tuple[str, ...], must_not_have: tuple[str, ...]) -> dict[str, str] | None:
    for header, kv in sections.items():
        if all(h in header for h in must_have) and not any(h in header for h in must_not_have):
            return kv
    return None


def _app_server_ports(ssh_host: str, appserv_path: str, domain_name: str) -> dict:
    """Return {'wsl_port', 'wsl_ssl_port', 'jsl_port', 'jsl_ssl_port',
    'jrad_port'} parsed from this domain's psappsrv.cfg. Structure
    confirmed against real file content: each listener has its own
    section (found via _APP_LISTENER_SECTIONS), and within it the port is
    a fixed key name — "PORT" (plain) / "SSL PORT" (encrypted) for
    WSL/JSL, "LISTENER PORT" for JRAD (see _APP_PORT_FIELDS). None means
    either the section itself or that key within it wasn't found."""
    text = _read_text(ssh_host, f"{appserv_path}/{domain_name}/psappsrv.cfg")
    if not text:
        return {field: None for field, _, _ in _APP_PORT_FIELDS} | {"_cfg_sections": None}
    sections = _parse_ini_sections(text)
    resolved_sections = {
        name: _find_section(sections, must_have, must_not_have)
        for name, (must_have, must_not_have) in _APP_LISTENER_SECTIONS.items()
    }

    result = {}
    for field, section_name, key in _APP_PORT_FIELDS:
        kv = resolved_sections.get(section_name)
        val = kv.get(key) if kv else None
        result[field] = int(val) if val and val.isdigit() else None

    # Surface the actual key=value pairs inside the listener-related
    # sections whenever fewer than all five resolved — real evidence for
    # diagnosing any remaining gap (e.g. JRAD SSL, if this environment
    # turns out to have one under a key this parser doesn't check yet)
    # instead of another guess from outside the file.
    if sum(1 for v in result.values() if isinstance(v, int)) < len(_APP_PORT_FIELDS):
        listener_hints = ("LISTENER", "JRAD", "RELAY", "WORKSTATION", "JOLT")
        lines = []
        for header, kv in sections.items():
            if any(h in header for h in listener_hints):
                lines.append(f"[{header}]")
                lines.extend(f"  {k}={v}" for k, v in kv.items())
        result["_cfg_sections"] = lines or sorted(sections.keys())
    else:
        result["_cfg_sections"] = None
    return result


def _web_domain_ports(ssh_host: str, webserv_path: str, domain_name: str) -> tuple[int | None, int | None]:
    """
    Return (http_port, https_port) parsed from WebLogic's config.xml. The
    HTTPS/SSL listen port is nested inside a <ssl>...</ssl> block, distinct
    from the plain HTTP <listen-port> at the <server> level — so the SSL
    block is extracted first and searched separately, rather than taking
    whichever <listen-port> match comes first in the file (which would
    misattribute one port as both, or ignore SSL entirely).
    """
    text = _read_text(ssh_host, f"{webserv_path}/{domain_name}/config/config.xml")
    if not text:
        return None, None
    ssl_block = _WEB_SSL_BLOCK_RE.search(text)
    ssl_port = None
    if ssl_block:
        m = _WEB_LISTEN_PORT_RE.search(ssl_block.group(0))
        ssl_port = int(m.group(1)) if m else None
        text = text[:ssl_block.start()] + text[ssl_block.end():]
    m = _WEB_LISTEN_PORT_RE.search(text)
    http_port = int(m.group(1)) if m else None
    return http_port, ssl_port


def _fetch_process_cmdlines(ssh_host: str) -> list[str] | None:
    """
    Fetch every process command line on the host ONCE (single SSH round
    trip), for _domain_status() to check all domains against in Python.

    Originally each domain issued its own `pgrep -f <domain>` — with a
    dozen-plus domains per host, that's a dozen-plus sequential SSH round
    trips just for status, the dominant cost in this page's slow load.
    One `ps` call amortizes that to a single round trip per host no
    matter how many domains share it. Returns None (not an empty list) on
    failure, so callers can distinguish "checked, found nothing" from
    "couldn't check at all" the same way the old per-domain check did.
    """
    try:
        out, _err, code = sshclient.run_command(ssh_host, "ps -eo args=")
        if code != 0:
            return None
        return out.splitlines()
    except Exception:
        return None


_LISTEN_PORT_RE = re.compile(r":(\d+)\s*$")


def _fetch_listening_ports(ssh_host: str) -> set[int] | None:
    """
    Fetch every port currently in LISTEN state on the host ONCE (single
    SSH round trip: `ss -ltn`), so the real listener count for each
    domain can be computed as "how many of this domain's configured ports
    are actually bound" instead of "how many port fields did we manage to
    parse out of psappsrv.cfg/config.xml" — the latter is static
    configuration and stays the same whether the domain is up or down,
    which is exactly the bug being fixed here (a down domain still showed
    5 "listeners"). Returns None (not an empty set) on failure, so a
    domain's listener_count can honestly show None ("couldn't check")
    rather than a false 0 ("checked, nothing listening").
    """
    try:
        out, _err, code = sshclient.run_command(ssh_host, "ss -ltn")
        if code != 0:
            return None
        ports = set()
        for line in out.splitlines():
            cols = line.split()
            if len(cols) < 4:
                continue
            local_addr = cols[3]  # e.g. "0.0.0.0:9120" or "[::]:9120"
            m = _LISTEN_PORT_RE.search(local_addr)
            if m:
                ports.add(int(m.group(1)))
        return ports
    except Exception:
        return None


def _live_listener_count(listening_ports: set[int] | None, configured_ports) -> int | None:
    """Count how many of a domain's configured ports are actually
    LISTEN-state right now. None if the live port set couldn't be
    fetched at all (distinct from 0, a confirmed-down domain)."""
    if listening_ports is None:
        return None
    return sum(1 for p in configured_ports if isinstance(p, int) and p in listening_ports)


def _domain_status(cmdlines: list[str] | None, domain_name: str) -> str:
    """
    Best-effort live status from a pre-fetched process list (see
    _fetch_process_cmdlines): "running" if any command line contains this
    domain's name (covers Tuxedo PSAPPSRV/PSPRCSRQST boot processes, which
    run with '-C dom=<domain>', and WebLogic servers, whose command line
    includes the domain's config path), "down" if the process list was
    read successfully but nothing matched, "unknown" if the process list
    itself couldn't be fetched (distinct from a confirmed-down domain —
    don't conflate "couldn't check" with "checked and it's down").

    This is a heuristic, not a definitive health check (e.g. it doesn't
    confirm the listener actually accepts connections) — the port fields
    above come from static config either way, this just adds a live
    signal for whether *anything* related to the domain is running.
    """
    if cmdlines is None:
        return "unknown"
    return "running" if any(domain_name in line for line in cmdlines) else "down"


def _has_ib_gateway(ssh_host: str, webserv_path: str, domain_name: str) -> bool:
    """Whether this web domain also hosts the Integration Gateway servlet
    (PSIGW.war) — same physical listener/ports as the PIA domain it lives
    in, but a logically distinct component worth surfacing as its own row
    rather than silently folding it into 'Web / PIA'."""
    try:
        entries = sshclient.list_dirs(ssh_host, f"{webserv_path}/{domain_name}/applications/peoplesoft")
        return any(e.upper() == "PSIGW.WAR" for e in entries)
    except Exception:
        return False


def discover_domains_by_path(ssh_host: str, ps_cfg_home: str) -> dict:
    """
    List domains under a single ps_cfg_home tree, once. Multiple
    environments commonly share one physical app-server host and one
    ps_cfg_home root (e.g. an entire pillar deployed on a single box), so
    callers should discover each unique (ssh_host, ps_cfg_home) pair once
    and attribute the result to every environment that shares it — not
    re-query the same directory per environment name, which just repeats
    the identical listing once per environment.
    """
    items = []
    warnings = []
    hostname = _resolve_hostname(ssh_host)
    cmdlines = _fetch_process_cmdlines(ssh_host)
    listening_ports = _fetch_listening_ports(ssh_host)

    appserv_path = f"{ps_cfg_home}/appserv"
    try:
        for dname in sshclient.list_dirs(ssh_host, appserv_path):
            domain_type, domain_type_label = _classify_appserv_dir(dname)
            item = {
                "domain_name": dname,
                "domain_type": domain_type,
                "domain_type_label": domain_type_label,
                "hosts": [hostname],
                "status": _domain_status(cmdlines, dname),
            }
            if domain_type == "app_server":
                ports = _app_server_ports(ssh_host, appserv_path, dname)
                cfg_sections = ports.pop("_cfg_sections", None)
                item.update(ports)
                item["cfg_sections"] = cfg_sections
                item["listener_count"] = _live_listener_count(listening_ports, ports.values())
            else:
                item["listener_count"] = None
            items.append(item)
    except FileNotFoundError as exc:
        warnings.append({
            "code": "appserv_dir_missing",
            "message": str(exc),
            "severity": "warning",
        })
    except Exception as exc:
        warnings.append({
            "code": "appserv_discovery_failed",
            "message": f"appserv discovery failed: {exc}",
            "severity": "warning",
        })

    webserv_path = f"{ps_cfg_home}/webserv"
    try:
        for dname in sshclient.list_dirs(ssh_host, webserv_path):
            port, ssl_port = _web_domain_ports(ssh_host, webserv_path, dname)
            listener_count = _live_listener_count(listening_ports, (port, ssl_port))
            status = _domain_status(cmdlines, dname)
            items.append({
                "domain_name": dname,
                "domain_type": "web",
                "domain_type_label": "Web / PIA",
                "hosts": [hostname],
                "primary_port": port,
                "alt_port": ssl_port,
                "listener_count": listener_count,
                "status": status,
            })
            if _has_ib_gateway(ssh_host, webserv_path, dname):
                items.append({
                    "domain_name": dname,
                    "domain_type": "ib",
                    "domain_type_label": "Integration Gateway",
                    "hosts": [hostname],
                    "primary_port": port,
                    "alt_port": ssl_port,
                    "listener_count": listener_count,
                    "status": status,
                })
    except FileNotFoundError as exc:
        warnings.append({
            "code": "webserv_dir_missing",
            "message": str(exc),
            "severity": "warning",
        })
    except Exception as exc:
        warnings.append({
            "code": "webserv_discovery_failed",
            "message": f"webserv discovery failed: {exc}",
            "severity": "warning",
        })

    return {
        "items": items,
        "source": f"ssh:{ssh_host}:{ps_cfg_home}",
        "warnings": warnings,
    }


def attribute_domains_to_envs(items: list[dict], envs: list[dict]) -> list[dict]:
    """
    Tag each domain item with the specific environment (and its pillar) it
    belongs to, when multiple environments share one ps_cfg_home tree.

    Pass 1: match each domain name against configured environment names by
    longest case-insensitive substring (e.g. "HRDEV_APP" -> "HRDEV"). This
    correctly resolves domains that follow PeopleSoft's usual
    `<ENVNAME>_APP`/`<ENVNAME>_WEB` naming convention.

    Pass 2: domains that don't match any environment name (e.g. a legacy
    "demo" domain literally named "HCMDMO_APP"/"HCDMO" that predates the
    environment being renamed to "HRDMO") are assigned to whichever
    configured environment in the group has *no* domain matched to it —
    but only when that's unambiguous (exactly one such environment). If
    it's ambiguous, the domain keeps a shared group label rather than
    guessing wrong, the same "don't guess, degrade honestly" principle
    used throughout this connector.
    """
    env_names = [e["name"] for e in envs]
    pillars = {e.get("pillar") for e in envs}
    group_pillar = next(iter(pillars)) if len(pillars) == 1 and next(iter(pillars)) else None
    group_label = group_pillar or "/".join(env_names)
    pillar_by_env = {e["name"]: e.get("pillar") for e in envs}

    matched_envs = set()
    unmatched = []
    for item in items:
        name_upper = item["domain_name"].upper()
        best = None
        for en in env_names:
            if en.upper() in name_upper and (best is None or len(en) > len(best)):
                best = en
        if best:
            item["env"] = best
            item["pillar"] = pillar_by_env.get(best)
            matched_envs.add(best)
        else:
            unmatched.append(item)

    leftover_envs = [en for en in env_names if en not in matched_envs]
    if len(leftover_envs) == 1:
        for item in unmatched:
            item["env"] = leftover_envs[0]
            item["pillar"] = pillar_by_env.get(leftover_envs[0])
    else:
        for item in unmatched:
            item["env"] = group_label
            item["pillar"] = group_pillar

    return items


def discover_domains(env_name: str) -> dict:
    """
    Return {"items": [...], "source": str|None, "warnings": [...]}
    in the same shape as connectors/psdb.app_server_domains(), so callers
    (routers/runtime.py) don't need to know which discovery method ran.
    """
    env = _load_env(env_name)
    if env is None:
        return {
            "items": [],
            "source": None,
            "warnings": [{
                "code": "unknown_environment",
                "message": f"No peoplesoft.environments entry named {env_name!r} in config.json.",
                "severity": "warning",
            }],
        }

    ssh_host = env.get("ssh_host")
    ps_cfg_home = env.get("ps_cfg_home")
    if not ssh_host or not ps_cfg_home:
        return {
            "items": [],
            "source": None,
            "warnings": [{
                "code": "domain_discovery_unconfigured",
                "message": (
                    f"{env_name}: missing 'ssh_host' and/or 'ps_cfg_home' in "
                    "config.json peoplesoft.environments — filesystem domain "
                    "discovery requires both."
                ),
                "severity": "warning",
            }],
        }

    return discover_domains_by_path(ssh_host, ps_cfg_home)
