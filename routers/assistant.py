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
- For "who uses X" or "what does X affect" questions, use graph_impact.
- For "what does X depend on" questions, use graph_dependencies.
- For PeopleCode questions, use peoplecode_search to find relevant programs.
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
