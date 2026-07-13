"""
Environment comparison router.
All endpoints are read-only and grant-aware.
"""

from fastapi import APIRouter, Query
from connectors import envcompare, graphdb
from connectors.psdb import load_envs, default_env, default_env2

router = APIRouter(prefix="/api/envcompare", tags=["Environment Comparison"])


@router.get("/config")
def envcompare_config():
    """Return available environment names for the selectors."""
    envs = [e["name"] for e in load_envs()]
    return {"envs": envs}


@router.get("/summary")
def envcompare_summary(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
):
    """Catalog-count summary across key object types for both environments."""
    return envcompare.summary(env1, env2)


@router.get("/records")
def compare_records(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSRECDEFN between two environments."""
    return envcompare.compare_records(env1, env2, q=q, limit=limit)


@router.get("/field_definitions")
def compare_field_definitions(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSDBFIELD — the standalone Field object type — between two
    environments. Not scoped to a record; a Field is its own metadata
    definition (FIELDNAME, FIELDTYPE, LENGTH, DECIMALPOS, DESCR)."""
    return envcompare.compare_field_definitions(env1, env2, q=q, limit=limit)


@router.get("/fields")
def compare_fields(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    record: str = Query(..., description="Record name to compare field-by-field"),
):
    """Diff PSRECFIELD — a record's field usage/structure ("Record.Fields")
    — for a specific record across two environments."""
    return envcompare.compare_fields(env1, env2, record)


@router.get("/components")
def compare_components(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSPNLGRPDEFN between two environments."""
    return envcompare.compare_components(env1, env2, q=q, limit=limit)


@router.get("/permissions")
def compare_permissions(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSCLASSDEFN (permission lists) between two environments."""
    return envcompare.compare_permissions(env1, env2, q=q, limit=limit)


@router.get("/ae")
def compare_ae(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSAEAPPLDEFN (AE programs) between two environments."""
    return envcompare.compare_ae(env1, env2, q=q, limit=limit)


@router.get("/roles")
def compare_roles(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSROLEDEFN (roles) between two environments."""
    return envcompare.compare_roles(env1, env2, q=q, limit=limit)


@router.get("/peoplecode")
def compare_peoplecode(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query("", description="Filter by parent object name (OBJECTVALUE1 or OBJECTVALUE2)"),
    limit: int = Query(500),
):
    """Diff PSPCMPROG (PeopleCode programs) between two environments."""
    return envcompare.compare_peoplecode(env1, env2, q=q, limit=limit)


@router.get("/sql_definitions")
def compare_sql_definitions(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSSQLDEFN (SQL definitions) between two environments."""
    return envcompare.compare_sql_definitions(env1, env2, q=q, limit=limit)


@router.get("/portals")
def compare_portals(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSPRSMDEFN (Portal Registry) between two environments."""
    return envcompare.compare_portals(env1, env2, q=q, limit=limit)


@router.get("/portal-object")
def compare_portal_object(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    name:   str = Query(..., description="PORTAL_OBJNAME to compare"),
):
    """Deep diff of a specific Portal Registry object across two environments."""
    return envcompare.compare_portal_object(env1, env2, name)


@router.get("/peoplecode-source")
def compare_peoplecode_source(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    ref:  str = Query(..., description="Encoded PeopleCode reference (e.g. JOB.EMPLID.FieldEdit.0)"),
):
    """Unified diff of PeopleCode source for a specific program across two environments."""
    return envcompare.compare_peoplecode_source(env1, env2, ref)


@router.get("/queries")
def compare_queries(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSQRYDEFN (public PS Queries) between two environments."""
    return envcompare.compare_queries(env1, env2, q=q, limit=limit)


@router.get("/menus")
def compare_menus(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSMENUDEFN (Menu definitions) between two environments."""
    return envcompare.compare_menus(env1, env2, q=q, limit=limit)


@router.get("/trees")
def compare_trees(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSTREEDEFN (Tree definitions) between two environments."""
    return envcompare.compare_trees(env1, env2, q=q, limit=limit)


@router.get("/process_definitions")
def compare_process_definitions(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PS_PRCSDEFN (Process Scheduler definitions) between two environments."""
    return envcompare.compare_process_definitions(env1, env2, q=q, limit=limit)


@router.get("/ib_routings")
def compare_ib_routings(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSIBRTNGDEFN (IB Routing definitions) between two environments."""
    return envcompare.compare_ib_routings(env1, env2, q=q, limit=limit)


@router.get("/ib_messages")
def compare_ib_messages(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSMSGDEFN (IB Message definitions) between two environments."""
    return envcompare.compare_ib_messages(env1, env2, q=q, limit=limit)


@router.get("/ci")
def compare_ci(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    q:     str = Query(""),
    limit: int = Query(500),
):
    """Diff PSBCDEFN (Component Interface definitions) between two environments."""
    return envcompare.compare_ci(env1, env2, q=q, limit=limit)


@router.get("/ae-body")
def compare_ae_body(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    ae_applid: str = Query(..., description="AE program name to diff step-by-step"),
):
    """Step-level diff of an AE program (sections, steps, SQL text) across two environments."""
    return envcompare.compare_ae_body(env1, env2, ae_applid)


@router.get("/graph")
def compare_graph(
    env1: str = Query(default_env()),
    env2: str = Query(default_env2()),
    node_types: str = Query("", description="Optional comma-separated graph node type filter"),
    limit: int = Query(200),
):
    """Diff persisted/current Knowledge Graph snapshots between two environments."""
    return graphdb.diff(env1, env2, node_types=node_types, limit=limit)
