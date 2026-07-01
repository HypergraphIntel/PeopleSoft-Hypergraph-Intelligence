"""OpenAI provider implementation."""

import json
from connectors.ai import AIProvider


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model   = model

    def name(self) -> str:
        return "OpenAI"

    def model(self) -> str:
        return self._model

    def chat(self, messages, tools=None, system=None, max_tokens=4096) -> dict:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed — run: pip install openai")

        client = OpenAI(api_key=self._api_key)

        # OpenAI uses a system message in the messages list
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        kwargs = dict(
            model=self._model,
            max_tokens=max_tokens,
            messages=oai_messages,
        )
        if tools:
            # Convert from Anthropic-style to OpenAI function-calling style
            kwargs["tools"] = [_to_oai_tool(t) for t in tools]
            kwargs["tool_choice"] = "auto"

        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    inp = json.loads(tc.function.arguments)
                except Exception:
                    inp = {"_raw": tc.function.arguments}
                tool_calls.append({
                    "id":    tc.id,
                    "name":  tc.function.name,
                    "input": inp,
                })

        return {
            "content":    msg.content or "",
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens":  resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            },
            "model":      resp.model,
            "stop_reason": resp.choices[0].finish_reason,
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
    """Convert Anthropic-style tool definition to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name":        t["name"],
            "description": t.get("description", ""),
            "parameters":  t.get("input_schema", {"type": "object", "properties": {}}),
        },
    }
