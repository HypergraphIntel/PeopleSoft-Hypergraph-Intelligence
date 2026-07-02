"""
Operator Explorer router — PSOPRDEFN + PSROLEUSER.
"""

from fastapi import APIRouter, Query
from connectors import psdb

router = APIRouter(prefix="/api/operator", tags=["Operator Explorer"])


def _safe(fn, *args, empty=None, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return empty, str(exc)


@router.get("/search")
def operator_search(env: str = Query("HCM"), q: str = Query(""), limit: int = Query(100)):
    rows, err = _safe(psdb.search_operators, env, q, limit, empty=[])
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{oprid_val}")
def operator_detail(oprid_val: str, env: str = Query("HCM")):
    item, err = _safe(psdb.operator_detail, env, oprid_val)
    return {"item": item, "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{oprid_val}/roles")
def operator_roles(oprid_val: str, env: str = Query("HCM")):
    rows, err = _safe(psdb.operator_roles_full, env, oprid_val, empty=[])
    return {"items": rows or [], "oprid": oprid_val,
            "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{oprid_val}/activity")
def operator_activity(oprid_val: str, env: str = Query("HCM"),
                      hours: int = Query(24), limit: int = Query(100)):
    """Recent page access activity for an operator (PSACCESSLOG)."""
    result, err = _safe(psdb.operator_activity, env, oprid_val, hours, limit, empty={})
    if err:
        return {"oprid": oprid_val, "items": [], "count": 0,
                "warnings": [{"message": err, "severity": "warning"}]}
    return result or {}


@router.get("/{oprid_val}/processes")
def operator_processes(oprid_val: str, env: str = Query("HCM"),
                       days: int = Query(7), limit: int = Query(100)):
    """Recent process scheduler submissions by an operator (PSPRCSRQST)."""
    result, err = _safe(psdb.operator_processes, env, oprid_val, days, limit, empty={})
    if err:
        return {"oprid": oprid_val, "items": [], "count": 0,
                "warnings": [{"message": err, "severity": "warning"}]}
    return result or {}
