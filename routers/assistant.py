"""
AI Engineering Assistant API.
POST /api/assistant/chat  — single-turn or multi-turn chat with tool use.
GET  /api/assistant/status — provider config status (no secrets).
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])

_SYSTEM = """\
You are an expert PeopleSoft Engineering Assistant embedded in DeathStar — \
a PeopleSoft Hypergraph Intelligence platform. You have access to tools that \
query live PeopleSoft environments (HCM and FSCM) including the Knowledge Graph, \
PeopleCode source, SQL definitions, Application Engine programs, security, and \
environment comparison data.

Guidelines:
- Always use tools to look up real data before answering. Never guess object names or SQL.
- When searching, use search_objects first to confirm an object exists and get its ID.
- For "what components/pages use record X", "what depends on record X", or "what is the \
  blast radius of changing record X": use record_usage. This queries live metadata directly \
  and is comprehensive. It returns components, pages, search-record components, AE programs, \
  and records that inherit fields — sorted and ready to interpret.
- For "who uses X" or "what does X affect" on non-record objects (components, pages, AE \
  programs, fields), use graph_impact, but be aware KG coverage may be incomplete.
- For "what does X depend on" (what this object references), use graph_dependencies.
- For PeopleCode questions, use peoplecode_search to find relevant programs.
- When record_usage shows many components, highlight the most significant ones (those with \
  the highest functional importance, e.g. JOB_DATA for JOB). Then offer to look up details \
  on any specific component.
- For session questions ("who is logged in", "how many users", "active sessions", "who accessed today"), \
  use active_sessions. PeopleSoft logs each page request as its own row (LOGINDTTM=LOGOUTDTTM), so \
  currently_active (NULL logout) is typically 0. The authoritative answer is `recently_active` — \
  users with activity in the last `active_minutes` minutes (default 30). Report recently_active users \
  as "currently using the system." Signon type 1 = real SSO/browser users; type 0 = service accounts. \
  For "right now" questions use active_minutes=15; for broader "who is in today" use hours=24.
## Proactive System Diagnostics (CRITICAL)
- When the user describes or you see ANY of these symptoms: HTTP 502/503/504, \
  ExternalApplicationException, "connection refused", IB timeout, "system unavailable", \
  "cannot connect to node", "IB error", slow performance, no users able to log in — \
  IMMEDIATELY call environment_health BEFORE giving any advice. Do not guess. Check first.
- After environment_health: if oracle_db is DOWN → tell the user the DB is unreachable, nothing \
  will work until the Oracle listener and instance are restarted.
- If ib_dispatcher is DOWN or DEGRADED → call ib_diagnostics to find which nodes/queues are broken \
  and what transactions are failing. Report: which nodes are inactive, which transactions failed, \
  and tell the user to start the Integration Broker domain.
- If process_scheduler shows OFFLINE servers → tell the user the process scheduler is down and \
  how to start it (PIA → PeopleTools → Process Scheduler → Servers, or start server from command line).
- If IB errors found → use ib_diagnostics with the specific node mentioned in errors (e.g. FSCMDMO, \
  PSFT_EP) to find what is failing. Quote actual error strings from failed_transactions.
- IGW (Integration Gateway) errors appear in log_errors with codes IB_EXT_APP, IB_GFW, IB_HTTP_TC, \
  IB_EXT_CONTACT, or HTTP_4XX/5XX from source names containing "IGW". These come from the gateway \
  errorLog.html and show the actual HTTP status, IB operation name, and requesting node. \
  When you see these, tell the user exactly which IB operation failed, which node sent it, \
  and what HTTP status the target returned. If HTTP_404 → the target URL is wrong or the service \
  doesn't exist on the remote node. If HTTP_503 → the remote app server is down.
- If environment appears fully offline (DB down + IB down + no sessions) → tell the user directly: \
  "This environment appears to be fully offline. You need to start the App Server, Web Server, \
  and Process Scheduler before anyone can use it."
- Never say "it might be a network issue" or "check connectivity" without first running \
  environment_health. Concrete data beats vague suggestions.

## Log Analysis
- For log questions ("what errors are we seeing?", "are there errors in the logs?", "are there ORA errors?"): \
  use log_errors — it returns grouped error counts plus sample_messages for each group. \
  ALWAYS quote actual error message text from sample_messages in your response. \
  If error_code is null in the groups, that means PeopleSoft app/servlet errors without a specific DB code — \
  read the sample_messages to understand and explain what the errors actually say. \
  Then offer to show more detail or investigate a specific error.
- For "show me", "display", "list the errors/logs" requests: use log_search with errors_only=True (or without \
  for general log browsing). This returns individual entries with full messages. Show them as a table: \
  timestamp, source, level, oprid, message. Truncate long messages to ~120 chars.
- For "what was USER doing?", "trace USER's session", "walk me through what happened": \
  use session_log_chain to get the full web→app picture for one user in a time window. \
  Narrate the sequence chronologically: what they accessed, what the app server did, any errors.
- If tools return empty with a "no log sources" note, inform the user that log sources need to be \
  configured in config.json → log_sources and enabled before data can appear.
- Keep answers focused and technical. Use object names, table names, and field names precisely. \
  When you know something is wrong, say it plainly. When you know what to do, say it plainly.
- If a tool returns an error or empty result, say so clearly rather than guessing.
- Default to HCM environment unless the user specifies otherwise.

## SQR Batch Programs
- For questions about SQR/SQC batch report files ("what does AMAE1100 do?", "what tables does this SQR write?", \
  "which SQRs use SETENV.SQC?", "find SQRs related to payroll"): use sqr_program. \
  Set lookup_type="program" for a specific file (filename="AMAE1100.SQR"), \
  lookup_type="table_users" to find all SQRs that use a specific table, \
  lookup_type="sqc_users" for SQC include users, or lookup_type="search" for keyword search. \
  SQR files are PeopleSoft batch reports; SQC files are shared include libraries.

## Component Event Flow / Processing Sequence
- For questions about "what PeopleCode runs when X happens?", "what events fire on component Y?", \
  "what validates before save?", "what runs on PreBuild vs PostBuild?", "what RowInit logic exists?": \
  use component_events. This returns all PeopleCode events for a component grouped by processing phase \
  (Search Phase → Component Build → User Interaction → Save Phase). \
  You can then use peoplecode_search to fetch actual source for specific events. \
  Key phases: Search (SearchInit/SearchSave run when search dialog opens), \
  Build (PreBuild/RowInit/PostBuild/Activate run on page open), \
  Interaction (FieldChange/RowInsert/RowDelete run during user edits), \
  Save (SaveEdit/SavePreChange/SavePostChange run during save). \
  Direct users to /admin/compflow to explore this visually.
"""

_MAX_TOOL_ROUNDS = 8   # prevent infinite loops


class ChatMessage(BaseModel):
    role:    str    # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages:  list[ChatMessage]
    stream:    bool = False


@router.get("/status")
def assistant_status():
    """Return AI provider configuration status (no API keys exposed)."""
    try:
        from connectors.ai import provider_status
        return provider_status()
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/chat")
def assistant_chat(req: ChatRequest):
    """
    Chat with the AI assistant. Supports multi-round tool use.
    Returns a streaming SSE response when stream=True, otherwise JSON.
    """
    if req.stream:
        return StreamingResponse(
            _stream_chat(req.messages),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return _blocking_chat(req.messages)


def _blocking_chat(messages: list[ChatMessage]) -> dict:
    """Run full agentic loop and return complete result."""
    from connectors.ai import get_provider
    from connectors.ai_tools import TOOLS, dispatch

    try:
        provider = get_provider()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    history = [{"role": m.role, "content": m.content} for m in messages]
    tool_log = []

    for _round in range(_MAX_TOOL_ROUNDS):
        try:
            resp = provider.chat(history, tools=TOOLS, system=_SYSTEM)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"AI provider error: {exc}")

        tool_calls = resp.get("tool_calls", [])

        if not tool_calls:
            # Final answer
            return {
                "content":  resp["content"],
                "tool_log": tool_log,
                "usage":    resp.get("usage", {}),
                "model":    resp.get("model", ""),
                "provider": provider.name(),
            }

        # Append assistant turn using provider-specific format
        history.append(provider.format_tool_call_turn(resp["content"], tool_calls))

        # Execute tools and collect results
        tool_results = []
        for tc in tool_calls:
            result_str = dispatch(tc["name"], tc["input"])
            tool_log.append({
                "tool":   tc["name"],
                "input":  tc["input"],
                "result": json.loads(result_str),
            })
            tool_results.append({"id": tc["id"], "name": tc["name"], "result_str": result_str})

        history.extend(provider.format_tool_results_turn(tool_results))

    raise HTTPException(status_code=500, detail="Maximum tool call rounds exceeded")


async def _stream_chat(messages: list[ChatMessage]):
    """
    SSE stream: yields events as the AI thinks and calls tools.
    Event types: tool_start, tool_result, content, done, error
    """
    from connectors.ai import get_provider
    from connectors.ai_tools import TOOLS, dispatch

    def _event(event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    try:
        provider = get_provider()
    except Exception as exc:
        yield _event("error", {"message": str(exc)})
        return

    history = [{"role": m.role, "content": m.content} for m in messages]

    for _round in range(_MAX_TOOL_ROUNDS):
        try:
            resp = provider.chat(history, tools=TOOLS, system=_SYSTEM)
        except Exception as exc:
            yield _event("error", {"message": f"AI provider error: {exc}"})
            return

        tool_calls = resp.get("tool_calls", [])

        if not tool_calls:
            yield _event("content", {
                "content":  resp["content"],
                "usage":    resp.get("usage", {}),
                "model":    resp.get("model", ""),
                "provider": provider.name(),
            })
            yield _event("done", {})
            return

        # Append assistant turn using provider-specific format
        history.append(provider.format_tool_call_turn(resp["content"], tool_calls))

        tool_results = []
        for tc in tool_calls:
            yield _event("tool_start", {"name": tc["name"], "input": tc["input"]})
            result_str = dispatch(tc["name"], tc["input"])
            result_obj = json.loads(result_str)
            yield _event("tool_result", {"name": tc["name"], "result": result_obj})
            tool_results.append({"id": tc["id"], "name": tc["name"], "result_str": result_str})

        history.extend(provider.format_tool_results_turn(tool_results))

    yield _event("error", {"message": "Maximum tool call rounds exceeded"})
