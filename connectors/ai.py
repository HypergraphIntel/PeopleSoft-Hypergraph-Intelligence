"""
AI Provider abstraction layer.

get_provider() returns the configured AIProvider implementation.
All provider-specific code lives in ai_claude.py, ai_openai.py, ai_ollama.py.
Nothing above this layer imports provider SDKs directly.

Config precedence (highest to lowest):
  1. Environment variables (CLAUDE_API_KEY, OPENAI_API_KEY, OLLAMA_BASE_URL)
  2. config.json ["ai"][<provider>] section
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
import json


def _load_ai_config() -> dict:
    cfg_path = Path(__file__).resolve().parent.parent / "config.json"
    try:
        return json.loads(cfg_path.read_text()).get("ai", {})
    except Exception:
        return {}


class AIProvider(ABC):
    """Common interface all AI providers must implement."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Send a chat completion request.

        Returns:
            {
                "content":    str,           # final text response
                "tool_calls": list[dict],    # [{name, input, id}] — may be empty
                "usage":      dict,          # {input_tokens, output_tokens}
                "model":      str,
                "stop_reason": str,
            }
        """

    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @abstractmethod
    def model(self) -> str:
        """Active model identifier."""

    @abstractmethod
    def format_tool_call_turn(self, content_text: str, tool_calls: list[dict]) -> dict:
        """
        Return the assistant message dict that contains pending tool calls.
        Format differs per provider (Anthropic content blocks vs OpenAI tool_calls array).
        """

    @abstractmethod
    def format_tool_results_turn(self, tool_results: list[dict]) -> list[dict]:
        """
        Return a list of messages that carry tool results back to the model.
        Anthropic: one user message with multiple tool_result blocks.
        OpenAI/Ollama: one 'tool' role message per result.
        Each item in tool_results: {id, name, result_str}
        """


def get_provider() -> AIProvider:
    """
    Instantiate and return the configured AI provider.
    Raises ValueError if provider is unknown or misconfigured.
    """
    cfg = _load_ai_config()
    provider_name = cfg.get("provider", "claude").lower()

    if provider_name == "claude":
        from connectors.ai_claude import ClaudeProvider
        api_key = os.environ.get("CLAUDE_API_KEY") or cfg.get("claude", {}).get("api_key", "")
        model   = cfg.get("claude", {}).get("model", "claude-sonnet-4-6")
        return ClaudeProvider(api_key=api_key, model=model)

    if provider_name == "openai":
        from connectors.ai_openai import OpenAIProvider
        api_key = os.environ.get("OPENAI_API_KEY") or cfg.get("openai", {}).get("api_key", "")
        model   = cfg.get("openai", {}).get("model", "gpt-4o")
        return OpenAIProvider(api_key=api_key, model=model)

    if provider_name == "ollama":
        from connectors.ai_ollama import OllamaProvider
        base_url = os.environ.get("OLLAMA_BASE_URL") or cfg.get("ollama", {}).get("base_url", "http://localhost:11434")
        model    = cfg.get("ollama", {}).get("model", "llama3.1")
        return OllamaProvider(base_url=base_url, model=model)

    raise ValueError(f"Unknown AI provider: {provider_name!r}. Choose claude, openai, or ollama.")


def provider_status() -> dict:
    """Return config status for all providers (no secrets exposed)."""
    cfg = _load_ai_config()
    active = cfg.get("provider", "claude")

    def _key_status(env_var: str, cfg_key: str, section: str) -> str:
        if os.environ.get(env_var):
            return "env-var"
        v = cfg.get(section, {}).get(cfg_key, "")
        return "configured" if v else "missing"

    return {
        "active_provider": active,
        "claude": {
            "api_key": _key_status("CLAUDE_API_KEY", "api_key", "claude"),
            "model":   cfg.get("claude", {}).get("model", "claude-sonnet-4-6"),
        },
        "openai": {
            "api_key": _key_status("OPENAI_API_KEY", "api_key", "openai"),
            "model":   cfg.get("openai", {}).get("model", "gpt-4o"),
        },
        "ollama": {
            "base_url": os.environ.get("OLLAMA_BASE_URL") or cfg.get("ollama", {}).get("base_url", "http://localhost:11434"),
            "model":    cfg.get("ollama", {}).get("model", "llama3.1"),
        },
    }
