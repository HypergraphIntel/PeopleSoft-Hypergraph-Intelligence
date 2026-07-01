"""
Impact Forecasting API — pre-migration impact reports.
"""

from fastapi import APIRouter, Query
from connectors import impact

router = APIRouter(prefix="/api/impact", tags=["Impact Forecasting"])


@router.get("/project")
def impact_project(
    env:     str = Query("HCM"),
    project: str = Query(..., description="Project name (PSPROJECTDEFN)"),
):
    """
    Pre-migration impact report for a PeopleSoft project.
    Enumerates PSPROJECTITEM objects, maps them to Knowledge Graph nodes,
    runs reverse dependency traversal, and returns an aggregated impact summary.
    """
    return impact.project_impact(env, project)


@router.get("/risk")
def impact_risk(
    env1: str = Query("HCM"),
    env2: str = Query("FSCM"),
):
    """
    KG-independent deployment risk assessment between two environments.
    Uses drift snapshot data to score risk by object type.
    """
    return impact.env_risk(env1, env2)
