"""
Environment comparison router.
All endpoints are read-only and grant-aware.
"""

from fastapi import APIRouter, Query
from connectors import envcompare, graphdb
from connectors.psdb import load_envs

router = APIRouter(prefix="/api/envcompare", tags=["Environment Comparison"])


@router.get("/config")
def envcompare_config():
    """Return available environment names for the selectors."""
    envs = [e["name"] for e in load_envs()]
    return {"envs": envs}


@router.get("/summary")
def envcompare_summary(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
):
    """Catalog-count summary across key object types for both environments."""
    return envcompare.summary(env1, env2)


@router.get("/records")
def compare_records(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSRECDEFN between two environments."""
    return envcompare.compare_records(env1, env2, q=q, limit=limit)


@router.get("/fields")
def compare_fields(
    env1:   str = Query("HCM"),
    env2:   str = Query("FSCM"),
    record: str = Query(..., description="Record name to compare field-by-field"),
):
    """Diff PSRECFIELD for a specific record across two environments."""
    return envcompare.compare_fields(env1, env2, record)


@router.get("/components")
def compare_components(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSPNLGRPDEFN between two environments."""
    return envcompare.compare_components(env1, env2, q=q, limit=limit)


@router.get("/permissions")
def compare_permissions(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSCLASSDEFN (permission lists) between two environments."""
    return envcompare.compare_permissions(env1, env2, q=q, limit=limit)


@router.get("/ae")
def compare_ae(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSAEAPPLDEFN (AE programs) between two environments."""
    return envcompare.compare_ae(env1, env2, q=q, limit=limit)


@router.get("/roles")
def compare_roles(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSROLEDEFN (roles) between two environments."""
    return envcompare.compare_roles(env1, env2, q=q, limit=limit)


@router.get("/peoplecode")
def compare_peoplecode(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query("", description="Filter by parent object name (OBJECTVALUE1 or OBJECTVALUE2)"),
    limit: int = Query(500),
):
    """Diff PSPCMPROG (PeopleCode programs) between two environments."""
    return envcompare.compare_peoplecode(env1, env2, q=q, limit=limit)


@router.get("/sql_definitions")
def compare_sql_definitions(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSSQLDEFN (SQL definitions) between two environments."""
    return envcompare.compare_sql_definitions(env1, env2, q=q, limit=limit)


@router.get("/portals")
def compare_portals(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSPRSMDEFN (Portal Registry) between two environments."""
    return envcompare.compare_portals(env1, env2, q=q, limit=limit)


@router.get("/queries")
def compare_queries(
    env1:  str = Query("HCM"),
    env2:  str = Query("FSCM"),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSQRYDEFN (public PS Queries) between two environments."""
    return envcompare.compare_queries(env1, env2, q=q, limit=limit)


@router.get("/graph")
def compare_graph(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
    node_types: str = Query("", description="Optional comma-separated graph node type filter"),
    limit: int = Query(200),
):
    """Diff persisted/current Knowledge Graph snapshots between two environments."""
    return graphdb.diff(env1, env2, node_types=node_types, limit=limit)
