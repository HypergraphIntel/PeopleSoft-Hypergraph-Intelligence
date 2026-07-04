"""
SQL Proxy — human-only reveal API (Phase 11).

This router is the ONLY place a masked token can be decoded back to its
real value. It is deliberately never imported by connectors/ai_tools.py —
the AI dispatch table has no path to connectors.sqlmask.reveal() at all,
which is a structural isolation guarantee, not just a permission check.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/sql-proxy", tags=["SQL Proxy"])


class RevealRequest(BaseModel):
    token: str


@router.post("/reveal")
def reveal_token(req: RevealRequest):
    """Decode a masked token (e.g. 'EMP_9a41c2f0') back to its real value.
    Every call is recorded in the same audit trail as SQL Workspace/AI
    executions (logs/sqlws_audit.jsonl)."""
    from connectors import sqlmask
    from connectors.sqlws import audit_write

    result = sqlmask.reveal(req.token.strip())
    audit_write("reveal", {
        "token": req.token.strip(),
        "found": result.get("found", False),
        "category": result.get("category"),
    })
    if not result.get("found"):
        raise HTTPException(404, f"Unknown token: {req.token}")
    return result


@router.get("/stats")
def vault_stats():
    """Introspection only — token counts by category, never real values."""
    from connectors import sqlmask
    return sqlmask.vault_stats()
