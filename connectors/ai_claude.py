"""Anthropic Claude provider implementation."""

from connectors.ai import AIProvider


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model   = model

    def name(self) -> str:
        return "Claude (Anthropic)"

    def model(self) -> str:
        return self._model

    def chat(self, messages, tools=None, system=None, max_tokens=4096) -> dict:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed — run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self._api_key)

        kwargs = dict(
            model=self._model,
            max_tokens=max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        resp = client.messages.create(**kwargs)

        content_text = ""
        tool_calls = []
        for block in resp.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id":    block.id,
                    "name":  block.name,
                    "input": block.input,
                })

        return {
            "content":    content_text,
            "tool_calls": tool_calls,
            "usage":      {
                "input_tokens":  resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
            "model":      resp.model,
            "stop_reason": resp.stop_reason,
        }

    def format_tool_call_turn(self, content_text: str, tool_calls: list[dict]) -> dict:
        blocks = []
        if content_text:
            blocks.append({"type": "text", "text": content_text})
        for tc in tool_calls:
            blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]})
        return {"role": "assistant", "content": blocks}

    def format_tool_results_turn(self, tool_results: list[dict]) -> list[dict]:
        return [{
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": r["id"], "content": r["result_str"]}
                for r in tool_results
            ],
        }]
