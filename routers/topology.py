import json
from pathlib import Path
from fastapi import APIRouter, Query

from connectors import domaindisc

router = APIRouter()

STATUS_JSON = Path("/opt/nginx/shared/status/status.json")

# Tiers we know how to draw for a PeopleSoft environment "lane", keyed by the
# suffix on the status.json system name (e.g. "HCMDMO_WEB" -> tier "WEB").
_TIER_KIND = {
    "WEB":  "weblogic",
    "APP":  "appserver",
    "PRCS": "prcs",
}

# domain_type (from connectors/domaindisc.py) -> lane tier
_DOMAIN_TYPE_TIER = {
    "web": "WEB",
    "app_server": "APP",
    "process_scheduler": "PRCS",
}


def _pillar_by_env_name() -> dict[str, str]:
    return {e["name"].upper(): e.get("pillar") for e in domaindisc.load_environments()}


def _discover_lanes(systems):
    """
    Group status.json systems into PeopleSoft environment lanes.

    A lane is any status.json "group" that has at least one WEB/APP/PRCS
    tier system (e.g. group "HCM" with systems "HCMDMO_WEB", "HCMDMO_APP",
    "HCMDMO_PRCS"). This makes the topology reflect whatever environments
    are actually monitored, instead of a fixed HCM/FSCM pair.

    status.json's "group" field is historically named after a pillar
    ("HCM") rather than a specific environment, which collides with
    domaindisc's environment-named lanes ("HRDMO", "HRDEV", ...) — a
    status.json group is treated as its own lane (not merged by pillar
    name into an environment lane), but tagged with a resolved `pillar`
    so the UI can still filter it alongside domaindisc's lanes by pillar.
    """
    pillar_by_env = _pillar_by_env_name()
    lanes = {}
    for s in systems:
        name = str(s.get("name", ""))
        group = str(s.get("group", ""))
        if "_" not in name:
            continue
        prefix, _, tier = name.rpartition("_")
        tier = tier.upper()
        if tier not in _TIER_KIND:
            continue
        lane = lanes.setdefault(group, {
            "group": group, "prefix": prefix, "tiers": {},
            # group might literally be a pillar name (legacy status.json
            # data) or an actual environment name — resolve whichever way
            # it matches, so it's never silently un-filterable.
            "pillar": pillar_by_env.get(group.upper(), group),
        })
        lane["tiers"][tier] = name
    return dict(sorted(lanes.items()))


def _domaindisc_lanes():
    """
    Group every configured PeopleSoft environment's discovered domains
    (connectors/domaindisc.py — SSH filesystem discovery, works across all
    environments, not just whatever happens to be in status.json) into the
    same {group: {"group", "prefix", "tiers": {WEB/APP/PRCS: domain_name}}}
    shape _discover_lanes() produces from status.json, plus a parallel
    status_by_name dict carrying each domain's live status/host/port so
    the topology reflects real discovered infrastructure for every
    environment, not only whichever one happens to be wired into the
    separate nginx status-page monitor.

    Returns (lanes, status_by_name).
    """
    groups: dict[tuple, list[dict]] = {}
    for env in domaindisc.load_environments():
        ssh_host = env.get("ssh_host")
        ps_cfg_home = env.get("ps_cfg_home")
        if not ssh_host or not ps_cfg_home:
            continue
        groups.setdefault((ssh_host, ps_cfg_home), []).append(env)

    lanes = {}
    status_by_name = {}
    for (ssh_host, ps_cfg_home), envs in groups.items():
        try:
            result = domaindisc.discover_domains_by_path(ssh_host, ps_cfg_home)
        except Exception:
            continue
        items = domaindisc.attribute_domains_to_envs(result.get("items", []), envs)
        for item in items:
            tier = _DOMAIN_TYPE_TIER.get(item["domain_type"])
            if not tier:
                continue
            group = item.get("env") or item.get("pillar") or "UNKNOWN"
            name = item["domain_name"]
            lane = lanes.setdefault(group, {
                "group": group, "prefix": group, "tiers": {},
                "pillar": item.get("pillar"),
            })
            lane["tiers"][tier] = name
            port = item.get("primary_port") or item.get("jsl_port") or item.get("wsl_port")
            host = (item.get("hosts") or [""])[0]
            status_by_name[name.upper()] = {
                "status": "ONLINE" if item.get("status") == "running"
                          else "OFFLINE" if item.get("status") == "down"
                          else "UNKNOWN",
                "target": f"{host}:{port}" if port else host,
                "meta": f"{item.get('pillar','')} {item.get('domain_type_label','')}".strip(),
            }
    return dict(sorted(lanes.items())), status_by_name


@router.get("/api/topology")
def topology(
    env: str = Query(None, description="Limit to a single lane/environment group"),
    pillar: str = Query(None, description="Limit to lanes belonging to a single pillar"),
):
    data = {}
    systems = []
    if STATUS_JSON.exists():
        data = json.loads(STATUS_JSON.read_text())
        systems = data.get("systems", [])

    # status.json only actively monitors whatever nginx's status page was
    # wired up for (in this lab: HCM only) — merge in every environment
    # discovered by connectors/domaindisc.py (SSH filesystem discovery,
    # works across all configured environments) so the topology reflects
    # real infrastructure instead of only the subset status.json covers.
    # status.json wins on overlap (it's an active live-probe monitor, a
    # stronger signal than domaindisc's process-presence heuristic), but
    # domaindisc fills in every lane/status status.json doesn't have.
    domaindisc_lanes, domaindisc_status = _domaindisc_lanes()
    all_lanes = dict(domaindisc_lanes)
    for group, lane in _discover_lanes(systems).items():
        merged = all_lanes.setdefault(group, {
            "group": group, "prefix": lane["prefix"], "tiers": {}, "pillar": lane.get("pillar"),
        })
        merged["tiers"].update(lane["tiers"])
        merged["pillar"] = merged.get("pillar") or lane.get("pillar")
    all_lanes = dict(sorted(all_lanes.items()))

    status_by_name = dict(domaindisc_status)
    status_by_name.update({
        str(s.get("name", "")).upper(): s
        for s in systems
    })

    def node(node_id, label, system_name=None, kind="system", lane=None):
        system = status_by_name.get((system_name or label).upper(), {})
        return {
            "id": node_id,
            "label": label,
            "kind": kind,
            "lane": lane,
            "status": system.get("status", "UNKNOWN"),
            "target": system.get("target", ""),
            "meta": system.get("meta", "")
        }

    envs = list(all_lanes.keys())
    pillars = sorted({l.get("pillar") for l in all_lanes.values() if l.get("pillar")})
    lanes = {
        g: l for g, l in all_lanes.items()
        if (not env or g.upper() == env.upper())
        and (not pillar or (l.get("pillar") or "").upper() == pillar.upper())
    }

    # ── Shared infrastructure ────────────────────────────────────────────────
    nodes = [
        {
            "id": "browser", "label": "BROWSER", "kind": "client", "lane": None,
            "status": "ONLINE", "target": "end user", "meta": ""
        },
        node("nginx", "NGINX", "Nginx", "proxy"),
        node("oracle", "ORACLE DB", "Oracle DB", "database"),
        node("opensearch", "OPENSEARCH", "OpenSearch", "search"),
    ]
    links = [
        {"from": "browser", "to": "nginx", "label": "HTTPS"},
    ]

    for group, lane in lanes.items():
        gid = group.lower().replace(" ", "_")
        tiers = lane["tiers"]

        if "WEB" in tiers:
            nodes.append(node(f"{gid}_web", tiers["WEB"], tiers["WEB"], "weblogic", lane=group))
            links.append({"from": "nginx", "to": f"{gid}_web", "label": ""})
            links.append({"from": f"{gid}_web", "to": "opensearch", "label": "REST"})
        if "APP" in tiers:
            nodes.append(node(f"{gid}_app", tiers["APP"], tiers["APP"], "appserver", lane=group))
            links.append({"from": f"{gid}_app", "to": "oracle", "label": "SQL*Net"})
            if "WEB" in tiers:
                links.append({"from": f"{gid}_web", "to": f"{gid}_app", "label": "Jolt"})
            # IB runs on the same app server; inherit its status.
            nodes.append({**node(f"{gid}_ib", f"{lane['prefix']}_IB", tiers["APP"], "ib", lane=group),
                          "label": f"{lane['prefix']}_IB"})
            links.append({"from": f"{gid}_app", "to": f"{gid}_ib", "label": "IB"})
            links.append({"from": f"{gid}_ib", "to": "oracle", "label": "SQL*Net"})
        if "PRCS" in tiers:
            nodes.append(node(f"{gid}_prcs", tiers["PRCS"], tiers["PRCS"], "prcs", lane=group))
            links.append({"from": f"{gid}_prcs", "to": "oracle", "label": "SQL*Net"})
            if "APP" in tiers:
                links.append({"from": f"{gid}_app", "to": f"{gid}_prcs", "label": "RPC"})

    return {
        "generated_at": data.get("generated_at"),
        "envs": envs,
        "env": env,
        "pillars": pillars,
        "pillar": pillar,
        "env_pillar": {g: l.get("pillar") for g, l in all_lanes.items()},
        "nodes": nodes,
        "links": links
    }
