import os
import subprocess
import psutil
from podman import PodmanClient

# Podman socket for host container introspection (Infrastructure page).
# PHI itself always runs inside a container, so it has no local podman
# engine/CLI -- this talks to the host's rootless Podman API instead,
# bind-mounted in via compose.yml. Requires the host to have run
# `systemctl --user enable --now podman.socket` once.
PODMAN_SOCKET = os.environ.get("PODMAN_SOCKET", "/run/podman/podman.sock")


def _podman_client():
    return PodmanClient(base_url=f"unix://{PODMAN_SOCKET}")


# Services to monitor — (display_name, systemd_unit, restartable)
MONITORED_SERVICES = [
    ("NGINX",         "nginx.service",              True),
    ("DeathStar API", "deathstar-api.service",       False),  # restarting self is dangerous
    ("GoAccess Live", "goaccess-live.service",       True),
]


def host_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory": psutil.virtual_memory()._asdict(),
        "disk": psutil.disk_usage("/")._asdict(),
        "loadavg": psutil.getloadavg(),
        "boot_time": psutil.boot_time(),
    }


def service_status(service: str):
    result = subprocess.run(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True,
        timeout=3
    )

    return {
        "service": service,
        "status": result.stdout.strip() or "unknown",
        "returncode": result.returncode
    }


def services_summary():
    results = []
    for display_name, unit, restartable in MONITORED_SERVICES:
        st = service_status(unit)
        results.append({
            "name": display_name,
            "unit": unit,
            "status": st["status"],
            "active": st["status"] == "active",
            "restartable": restartable,
        })
    return results


def restart_service(unit: str):
    # Only allow restarting known non-self services
    allowed = {u for _, u, ok in MONITORED_SERVICES if ok}
    if unit not in allowed:
        return {"status": "error", "message": f"Restart not permitted for {unit}"}

    result = subprocess.run(
        ["systemctl", "restart", unit],
        capture_output=True, text=True, timeout=15
    )
    return {
        "unit": unit,
        "status": "ok" if result.returncode == 0 else "error",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def reload_nginx():
    result = subprocess.run(
        ["systemctl", "reload", "nginx.service"],
        capture_output=True, text=True, timeout=10
    )
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def containers():
    try:
        with _podman_client() as client:
            items = []
            for c in client.containers.list(all=True):
                attrs = c.attrs
                names = attrs.get("Names") or [c.name]
                state = attrs.get("State", "")
                items.append({
                    "id": (attrs.get("Id") or "")[:12],
                    "name": names[0] if isinstance(names, list) else str(names),
                    "image": attrs.get("Image", ""),
                    "status": state or attrs.get("Status", ""),
                    "running": state.lower() == "running",
                    "created": attrs.get("Created", ""),
                })
            return {"containers": items}
    except Exception as exc:
        return {"containers": [], "error": str(exc)}


def container_logs(name: str, lines: int = 50):
    name = name.strip()
    lines = int(lines)
    try:
        with _podman_client() as client:
            container = client.containers.get(name)
            out_lines = []
            for chunk in container.logs(tail=lines, stream=False):
                if isinstance(chunk, bytes):
                    chunk = chunk.decode(errors="replace")
                out_lines.extend(chunk.splitlines())
            return {"name": name, "lines": out_lines[-lines:], "returncode": 0}
    except Exception as exc:
        return {"name": name, "lines": [], "returncode": 1, "error": str(exc)}


def restart_container(name: str):
    name = name.strip()
    try:
        with _podman_client() as client:
            container = client.containers.get(name)
            container.restart()
            return {"name": name, "status": "ok", "stdout": "", "stderr": "", "returncode": 0}
    except Exception as exc:
        return {"name": name, "status": "error", "stdout": "", "stderr": str(exc), "returncode": 1}


def journal(units: str = "nginx,deathstar-api", lines: int = 100):
    cmd = ["journalctl", "--no-pager", "-n", str(lines)]

    for unit in [u.strip() for u in units.split(",") if u.strip()]:
        cmd.extend(["-u", unit])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=5
    )

    return {
        "units": units,
        "lines": result.stdout.splitlines(),
        "stderr": result.stderr.splitlines(),
        "returncode": result.returncode
    }


