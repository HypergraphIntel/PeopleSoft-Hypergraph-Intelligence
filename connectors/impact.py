"""
Impact Forecasting connector.
Given a PeopleSoft project, enumerates its objects and runs Knowledge Graph
impact traversal to predict downstream effects of migrating the project.

Also provides env_risk() — a KG-independent deployment risk assessment
based on envcompare drift summary data.
"""

from connectors import graphdb, psdb, ptmetadata

# Risk weights by object type (higher = more dangerous to have drift in)
_TYPE_RISK_WEIGHT = {
    "Permission Lists": 5,
    "Roles":            5,
    "PeopleCode":       4,
    "IB Routings":      4,
    "IB Messages":      4,
    "AE Programs":      3,
    "SQL Definitions":  3,
    "Components":       2,
    "Comp. Interfaces": 2,
    "Records":          1,
    "Fields":           1,
    "Pages":            1,
    "PS Queries":       1,
    "Menus":            1,
    "Trees":            1,
    "Portal Entries":   1,
}

def _delta_level(delta: int) -> int:
    """0=none, 1=minor(<10), 2=moderate(<100), 3=significant(<1000), 4=major(>=1000)"""
    d = abs(delta)
    if d == 0:   return 0
    if d < 10:   return 1
    if d < 100:  return 2
    if d < 1000: return 3
    return 4

_LEVEL_LABELS = ["None", "Minor", "Moderate", "Significant", "Major"]


def env_risk(env1: str, env2: str) -> dict:
    """
    Deployment risk assessment for migrating between two environments.
    Uses drift snapshot data (or live envcompare summary as fallback).
    Does NOT require the Knowledge Graph to be built.
    """
    from connectors import driftdb

    env1 = env1.upper()
    env2 = env2.upper()

    # Prefer cached snapshot data (already collected); get_latest returns a list
    snap_rows = driftdb.get_latest(env1, env2)  # [] if no snapshots yet
    data_source = "snapshot"

    if not snap_rows:
        # Fallback: run live summary (slower, hits Oracle)
        try:
            from connectors import envcompare
            raw = envcompare.summary(env1, env2)
            snap_rows = [
                {
                    "type": r.get("label", r.get("type", "")),
                    "env1_count": r.get("env1_count", 0),
                    "env2_count": r.get("env2_count", 0),
                    "delta": r.get("env1_count", 0) - r.get("env2_count", 0),
                }
                for r in raw.get("rows", [])
            ]
            data_source = "live"
        except Exception:
            snap_rows = []

    if not snap_rows:
        return {
            "error": "No drift data available — trigger a snapshot first",
            "env1": env1,
            "env2": env2,
        }

    type_risks = []
    risk_score = 0
    for item in snap_rows:
        obj_type = item.get("type", "")
        delta = item.get("delta", 0)
        level = _delta_level(delta)
        weight = _TYPE_RISK_WEIGHT.get(obj_type, 1)
        contribution = weight * level
        risk_score += contribution
        type_risks.append({
            "type":        obj_type,
            "delta":       delta,
            "env1_count":  item.get("env1_count", 0),
            "env2_count":  item.get("env2_count", 0),
            "weight":      weight,
            "drift_level": _LEVEL_LABELS[level],
            "contribution": contribution,
        })

    type_risks.sort(key=lambda x: -x["contribution"])

    if risk_score == 0:
        risk_label = "None"
    elif risk_score < 10:
        risk_label = "Low"
    elif risk_score < 30:
        risk_label = "Medium"
    elif risk_score < 60:
        risk_label = "High"
    else:
        risk_label = "Critical"

    return {
        "env1":        env1,
        "env2":        env2,
        "risk_score":  risk_score,
        "risk_label":  risk_label,
        "type_risks":  type_risks,
        "data_source": data_source,
    }

# Map from PSPROJECTITEM OBJECTTYPE to KG node type key.
# KG type strings verified from live graphdb.current() node inventory.
_OTYPE_TO_KG = {
    0:  "record",
    2:  "page",
    4:  "component",
    6:  "menu",
    7:  "application_engine",
    9:  "field",
    10: "query",
    26: "role",
    27: "permissionlist",
    44: "peoplecode",
    51: "ib_routing",
}

# Display label for each KG node type in the impact report
_KG_TYPE_LABEL = {
    "record":              "Records",
    "page":                "Pages",
    "component":           "Components",
    "menu":                "Menus",
    "application_engine":  "AE Programs",
    "field":               "Fields",
    "query":               "PS Queries",
    "sql_definition":      "SQL Definitions",
    "role":                "Roles",
    "permissionlist":      "Permission Lists",
    "peoplecode":          "PeopleCode Programs",
    "service_operation":   "IB Service Operations",
    "ib_routing":          "IB Routings",
    "operator":            "Operators",
    "ib_operation":        "IB Operations",
    "node":                "IB Nodes",
    "message":             "IB Messages",
    "queue":               "IB Queues",
}

# Max objects per type to run full impact traversal for (avoid huge queries)
_IMPACT_LIMIT_PER_TYPE = 30
_IMPACT_DEPTH = 3


def project_impact(env: str, project_name: str) -> dict:
    """
    Pre-migration impact report for a project.

    Steps:
    1. Enumerate project items from PSPROJECTITEM.
    2. Map project object types to KG node types.
    3. For each mapped object (capped per type), look up its KG node.
    4. Run reverse impact traversal (what depends on this object?).
    5. Aggregate affected node counts by type.
    6. Compute a risk score based on affected critical types.

    Returns a structured impact report.
    """
    env = env.upper()
    project_name = project_name.strip().upper()
    warnings = []

    # ── Step 1: Load project items ───────────────────────────────────────────
    if not ptmetadata.has_table(env, "PSPROJECTITEM"):
        return {"error": "PSPROJECTITEM not accessible", "env": env,
                "project": project_name, "warnings": warnings}

    try:
        item_rows = psdb.query(env, """
            SELECT OBJECTTYPE, OBJECTVALUE1, OBJECTVALUE2
              FROM SYSADM.PSPROJECTITEM
             WHERE PROJECTNAME = :name
             ORDER BY OBJECTTYPE, OBJECTVALUE1
        """, {"name": project_name})
    except Exception as exc:
        return {"error": str(exc), "env": env, "project": project_name, "warnings": warnings}

    if not item_rows:
        return {"error": f"Project not found or empty: {project_name}",
                "env": env, "project": project_name, "warnings": warnings}

    # Group by object type
    by_type: dict = {}
    total_items = 0
    from connectors.psdb import _PRJOBJ_TYPE_LABEL, _PRJOBJ_ENCODED
    for r in item_rows:
        otype = r.get("objecttype")
        name_val = str(r.get("objectvalue1") or "").strip()
        if not name_val or otype in _PRJOBJ_ENCODED:
            continue
        by_type.setdefault(otype, []).append(name_val)
        total_items += 1

    # ── Step 2: Map to KG types ──────────────────────────────────────────────
    g = graphdb.current(env)
    nodes = g.get("nodes", {}) if g else {}

    # Build lookup: (kg_type, name) → node
    node_lookup: dict = {}
    for node_id, node in nodes.items():
        ntype = node.get("type", "")
        nname = (node.get("name") or "").upper()
        node_lookup[(ntype, nname)] = node

    # ── Step 3 & 4: Traverse impact per project object ───────────────────────
    affected_by_type: dict = {}   # node_type → set of node IDs affected
    traversed_objects: list = []  # {name, kg_type, affected_count}
    skipped_no_kg = 0

    for otype, names in by_type.items():
        kg_type = _OTYPE_TO_KG.get(otype)
        if not kg_type:
            continue
        for name in names[:_IMPACT_LIMIT_PER_TYPE]:
            node = node_lookup.get((kg_type, name.upper()))
            if not node:
                skipped_no_kg += 1
                continue
            node_id = node.get("id") or f"{kg_type}:{name}"
            # Reverse traversal: what depends on THIS node?
            rev = graphdb.dependency_tree(env, node_id, reverse=True,
                                          depth=_IMPACT_DEPTH)
            affected_nodes = rev.get("nodes", [])
            n_affected = 0
            for an in affected_nodes:
                if an.get("id") == node_id:
                    continue  # skip self
                atype = an.get("type", "unknown")
                affected_by_type.setdefault(atype, set()).add(an.get("id", ""))
                n_affected += 1
            traversed_objects.append({
                "name": name,
                "kg_type": kg_type,
                "affected_count": n_affected,
            })

    # ── Step 5: Aggregate ────────────────────────────────────────────────────
    affected_summary = [
        {
            "type": atype,
            "label": _KG_TYPE_LABEL.get(atype, atype),
            "count": len(ids),
        }
        for atype, ids in sorted(affected_by_type.items(),
                                 key=lambda kv: -len(kv[1]))
    ]

    # ── Step 6: Risk scoring ─────────────────────────────────────────────────
    # Critical types that elevate risk: operators, permission_lists, components
    HIGH_RISK_TYPES = {"operator", "permission_list", "component", "service_operation"}
    risk_score = 0
    total_affected = sum(r["count"] for r in affected_summary)

    for r in affected_summary:
        w = 3 if r["type"] in HIGH_RISK_TYPES else 1
        risk_score += r["count"] * w

    if risk_score == 0:
        risk_label = "Low"
    elif risk_score < 50:
        risk_label = "Medium"
    elif risk_score < 200:
        risk_label = "High"
    else:
        risk_label = "Critical"

    # Top impacted objects sorted by affected count
    traversed_objects.sort(key=lambda x: -x["affected_count"])

    # Project item type breakdown (for display)
    from connectors.psdb import _PRJOBJ_TYPE_LABEL as TYPE_LABEL
    item_breakdown = [
        {
            "objecttype": otype,
            "label": TYPE_LABEL.get(otype, f"Type {otype}"),
            "count": len(names),
            "mapped_to_kg": _OTYPE_TO_KG.get(otype),
        }
        for otype, names in sorted(by_type.items(), key=lambda kv: -len(kv[1]))
    ]

    if skipped_no_kg:
        warnings.append(f"{skipped_no_kg} objects had no matching KG node (graph may not be current)")

    graph_built = g.get("built_at") if g else None
    if not graph_built:
        warnings.append(f"No knowledge graph found for {env} — run a graph build first")

    return {
        "env": env,
        "project": project_name,
        "total_items": total_items,
        "item_breakdown": item_breakdown,
        "traversed_count": len(traversed_objects),
        "top_impacted_objects": traversed_objects[:50],
        "affected_summary": affected_summary,
        "total_affected_nodes": total_affected,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "graph_built_at": graph_built,
        "warnings": warnings,
    }
