"""
Field Explorer router.
Field-name-centric search and cross-record analysis.
All endpoints are grant-aware.
"""

from fastapi import APIRouter, Query
from connectors import psdb

router = APIRouter(prefix="/api/field", tags=["Field Explorer"])


def _safe(fn, *args, empty=None, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:
        return empty, str(exc)


@router.get("/search")
def field_search(env: str = Query("HCM"), q: str = Query(""), limit: int = Query(100)):
    """Search distinct field names with usage count."""
    rows, err = _safe(psdb.search_fields_distinct, env, q, limit, empty=[])
    for r in (rows or []):
        ft = r.get("db_fieldtype")
        r["fieldtype_label"] = psdb.FIELDTYPE_LABELS.get(int(ft) if ft is not None else -1, f"Type {ft}") if ft is not None else ""
    return {"items": rows or [], "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{fieldname}/records")
def field_records(fieldname: str, env: str = Query("HCM")):
    """Return all records that contain this field."""
    rows, err = _safe(psdb.field_record_summary, env, fieldname, empty=[])
    return {"items": rows or [], "field": fieldname,
            "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{fieldname}/definition")
def field_definition(fieldname: str, env: str = Query("HCM"), record: str = Query("")):
    """Return field definition. record is optional; if given uses RECORD.FIELD context."""
    ref = f"{record}.{fieldname}" if record else fieldname
    result, err = _safe(psdb.field_definition, env, ref, empty={})
    return {"item": result or {}, "warnings": [{"message": err, "severity": "warning"}] if err else []}


@router.get("/{fieldname}/peoplecode")
def field_peoplecode(fieldname: str, env: str = Query("HCM")):
    """Return all PeopleCode programs that fire on this field across all records/components."""
    result, err = _safe(psdb.field_cross_record_peoplecode, env, fieldname, empty={})
    if err:
        return {"fieldname": fieldname, "component_handlers": [], "record_handlers": [],
                "total_handlers": 0, "warnings": [{"message": err, "severity": "warning"}]}
    return result
