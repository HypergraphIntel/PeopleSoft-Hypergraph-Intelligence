"""Ollama local inference provider implementation."""

import json
import urllib.request
import urllib.error
from connectors.ai import AIProvider


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model    = model

    def name(self) -> str:
        return f"Ollama ({self._base_url})"

    def model(self) -> str:
        return self._model

    def chat(self, messages, tools=None, system=None, max_tokens=4096) -> dict:
        # Ollama /api/chat endpoint (OpenAI-compatible tools in newer versions)
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        payload = {
            "model":    self._model,
            "messages": oai_messages,
            "stream":   False,
            "options":  {"num_predict": max_tokens},
        }
        if tools:
            # Ollama supports OpenAI-style tool definitions (llama3.1+ models)
            payload["tools"] = [_to_oai_tool(t) for t in tools]

        body = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama unreachable at {self._base_url}: {e}")

        msg = data.get("message", {})
        content = msg.get("content") or ""

        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            inp = fn.get("arguments", {})
            if isinstance(inp, str):
                try:
                    inp = json.loads(inp)
                except Exception:
                    inp = {"_raw": inp}
            tool_calls.append({
                "id":    tc.get("id", f"call_{fn.get('name','')}"),
                "name":  fn.get("name", ""),
                "input": inp,
            })

        usage = data.get("usage") or {}
        return {
            "content":    content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens":  usage.get("prompt_tokens", data.get("prompt_eval_count", 0)),
                "output_tokens": usage.get("completion_tokens", data.get("eval_count", 0)),
            },
            "model":      data.get("model", self._model),
            "stop_reason": data.get("done_reason", "stop"),
        }

    def format_tool_call_turn(self, content_text: str, tool_calls: list[dict]) -> dict:
        return {
            "role":       "assistant",
            "content":    content_text or None,
            "tool_calls": [
                {
                    "id":   tc["id"],
                    "type": "function",
                    "function": {
                        "name":      tc["name"],
                        "arguments": json.dumps(tc["input"]),
                    },
                }
                for tc in tool_calls
            ],
        }

    def format_tool_results_turn(self, tool_results: list[dict]) -> list[dict]:
        return [
            {"role": "tool", "tool_call_id": r["id"], "content": r["result_str"]}
            for r in tool_results
        ]


def _to_oai_tool(t: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name":        t["name"],
            "description": t.get("description", ""),
            "parameters":  t.get("input_schema", {"type": "object", "properties": {}}),
        },
    }
