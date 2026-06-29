"""
SQL Workspace API router.

Provides safe, read-only SQL execution against PeopleSoft Oracle databases.
All routes validate input before touching any database.
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

from connectors import sqlws

router = APIRouter(prefix="/api/sqlws", tags=["SQL Workspace"])


# ──────────────────────────────────────────────────────────────────────────────
# Request models
# ──────────────────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    sql: str


class ExecuteRequest(BaseModel):
    env: str = "HCM"
    sql: str
    binds: dict = {}
    page: int = 1
    page_size: int = sqlws.DEFAULT_PAGE_SIZE
    max_rows: int = None
    timeout_secs: int = 0


class ExplainRequest(BaseModel):
    env: str = "HCM"
    sql: str
    binds: dict = {}


class ExportRequest(BaseModel):
    env: str = "HCM"
    sql: str
    binds: dict = {}
    page_size: int = sqlws.MAX_PAGE_SIZE


# ──────────────────────────────────────────────────────────────────────────────
# Validate
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/validate")
def validate_sql(req: ValidateRequest):
    """Validate SQL without executing it. Returns allow/block decision."""
    result = sqlws.validate_readonly(req.sql)
    sqlws.audit_write("validate", {
        "sql": req.sql[:500],
        "allowed": result["allowed"],
        "statement_type": result["statement_type"],
        "blocked_reason": result.get("blocked_reason"),
    })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Execute
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/execute")
async def execute_sql(req: ExecuteRequest, request: Request):
    """Execute a read-only SQL statement with optional bind parameters and paging."""
    if await request.is_disconnected():
        return {
            "env": req.env.upper(),
            "statement_type": None,
            "elapsed_ms": 0,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "page": req.page,
            "page_size": req.page_size,
            "truncated": False,
            "warnings": ["Query execution was cancelled by the client."],
            "blocked": False,
            "blocked_reason": None,
            "timed_out": False,
            "cancelled": True,
            "status": "cancelled",
            "query_id": None,
        }

    result = await asyncio.to_thread(
        sqlws.execute_query,
        req.env,
        req.sql,
        req.binds,
        req.page,
        req.page_size,
        req.max_rows,
        req.timeout_secs,
        lambda: asyncio.get_running_loop().is_closed(),
    )

    if await request.is_disconnected() and not result.get("cancelled"):
        result["cancelled"] = True
        result["status"] = "cancelled"
        result["warnings"] = list(result.get("warnings", [])) + ["Query execution was cancelled by the client."]

    return result


# ──────────────────────────────────────────────────────────────────────────────
# EXPLAIN PLAN
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/explain")
def explain_sql(req: ExplainRequest):
    """Run EXPLAIN PLAN FOR <sql> and return DBMS_XPLAN output."""
    return sqlws.explain_query(
        env_name = req.env,
        sql      = req.sql,
        binds    = req.binds,
    )


# ──────────────────────────────────────────────────────────────────────────────
# History
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/history")
def get_history(
    pinned: bool = Query(False, description="Return only pinned queries"),
    limit:  int  = Query(100,   description="Maximum entries to return"),
):
    """Return query execution history, newest first."""
    return {"history": sqlws.history_list(pinned_only=pinned, limit=limit)}


@router.post("/history/{query_id}/pin")
def pin_history(query_id: str, pinned: bool = Query(True)):
    """Pin or unpin a history entry."""
    result = sqlws.history_pin(query_id, pinned=pinned)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.delete("/history/{query_id}")
def delete_history(query_id: str):
    """Delete a history entry."""
    result = sqlws.history_delete(query_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Schema browser
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/schema/search")
def schema_search(
    env: str = Query("HCM"),
    q:   str = Query(..., min_length=1),
    limit: int = Query(50),
):
    """Search for tables, views, and PeopleSoft records by name."""
    return sqlws.schema_search(env_name=env, q=q, limit=limit)


@router.get("/schema/{owner}/{object_name}/columns")
def schema_columns(
    owner: str,
    object_name: str,
    env: str = Query("HCM"),
):
    """Return column metadata for a table or view."""
    return sqlws.schema_columns(env_name=env, owner=owner, object_name=object_name)


# ──────────────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/export/json")
def export_json(req: ExportRequest):
    """Execute a query and return the result set as a JSON file download."""
    result = sqlws.execute_query(
        env_name  = req.env,
        sql       = req.sql,
        binds     = req.binds,
        page      = 1,
        page_size = req.page_size,
    )

    if result.get("blocked"):
        raise HTTPException(status_code=400, detail=result.get("blocked_reason"))

    sqlws.audit_write("export_json", {
        "env": req.env.upper(),
        "sql": req.sql[:500],
        "row_count": result.get("row_count", 0),
        "query_id": result.get("query_id"),
    })

    payload = json.dumps(result["rows"], default=str, indent=2)
    return Response(
        content    = payload,
        media_type = "application/json",
        headers    = {"Content-Disposition": 'attachment; filename="sqlws_export.json"'},
    )


@router.post("/export/csv")
def export_csv(req: ExportRequest):
    """Execute a query and return the result set as a CSV file download."""
    result = sqlws.execute_query(
        env_name  = req.env,
        sql       = req.sql,
        binds     = req.binds,
        page      = 1,
        page_size = req.page_size,
    )

    if result.get("blocked"):
        raise HTTPException(status_code=400, detail=result.get("blocked_reason"))

    sqlws.audit_write("export_csv", {
        "env": req.env.upper(),
        "sql": req.sql[:500],
        "row_count": result.get("row_count", 0),
        "query_id": result.get("query_id"),
    })

    csv_text = sqlws.export_csv(result)
    return Response(
        content    = csv_text,
        media_type = "text/csv",
        headers    = {"Content-Disposition": 'attachment; filename="sqlws_export.csv"'},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/config")
def sqlws_config():
    """Return available environments and workspace defaults."""
    return {
        "envs": sqlws.list_envs(),
        "default_page_size": sqlws.DEFAULT_PAGE_SIZE,
        "max_page_size": sqlws.MAX_PAGE_SIZE,
    }
