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
- For log questions ("what errors are we seeing?", "what was USER doing?", "are there ORA errors?", \
  "show me web server errors"): use log_errors for error surface questions; use log_search to filter \
  by user/component/time; use session_log_chain to get the full web→app picture for one user in a time window. \
  If tools return empty with a "no log sources" note, inform the user that log sources need to be configured \
  in config.json → log_sources and enabled before data can appear.
- Keep answers focused and technical. Use object names, table names, and field names precisely.
- If a tool returns an error or empty result, say so clearly rather than guessing.
- Default to HCM environment unless the user specifies otherwise.
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
