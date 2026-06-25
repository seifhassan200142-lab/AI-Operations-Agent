from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings


class LLMConfigurationError(RuntimeError):
    pass


class LLMClient:
    """Small wrapper for OpenAI-compatible APIs, Groq, Ollama, and a test-only mock provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        provider = self.settings.llm_provider
        if provider == "openai":
            return bool(self.settings.openai_api_key)
        if provider == "groq":
            return bool(self.settings.groq_api_key)
        if provider == "ollama":
            return bool(self.settings.ollama_model)
        if provider == "mock":
            return True
        return False

    def setup_error(self) -> str:
        return (
            "No LLM provider is configured. Set AI_OPS_LLM_PROVIDER to openai, groq, or ollama "
            "and provide the required model/API settings in .env. See .env.example."
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.is_configured():
            raise LLMConfigurationError(self.setup_error())
        provider = self.settings.llm_provider
        if provider == "openai":
            return self._openai_compatible(
                base_url=self.settings.openai_base_url,
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
                messages=messages,
            )
        if provider == "groq":
            return self._openai_compatible(
                base_url=self.settings.groq_base_url,
                api_key=self.settings.groq_api_key,
                model=self.settings.groq_model,
                messages=messages,
            )
        if provider == "ollama":
            return self._ollama(messages)
        if provider == "mock":
            return self._mock(messages)
        raise LLMConfigurationError(self.setup_error())

    def _openai_compatible(self, base_url: str, api_key: str, model: str, messages: list[dict[str, str]]) -> str:
        url = base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.1}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    def _ollama(self, messages: list[dict[str, str]]) -> str:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/chat"
        payload = {"model": self.settings.ollama_model, "messages": messages, "stream": False}
        with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["message"]["content"]

    def _mock(self, messages: list[dict[str, str]]) -> str:
        """Deterministic provider for tests and demos. Real deployments should use an LLM."""
        user_content = "\n".join(message["content"] for message in messages if message["role"] == "user").lower()
        if "observations so far:\n[]" not in user_content and "pending approval" in user_content:
            return '{"action":"finish","final_answer":"The requested action is waiting for human approval.","reasoning_summary":"A sensitive tool action was routed to the approval gate."}'
        if "summarize" in user_content and "ticket" in user_content and "observations so far:\n[]" in user_content:
            return '{"action":"tool","tool_name":"ticket_summary","arguments":{"status":"open"},"reasoning_summary":"The agent needs the ticket summary tool to inspect open tickets."}'
        if "calculate" in user_content or " + " in user_content:
            return '{"action":"tool","tool_name":"calculator","arguments":{"expression":"2+2"},"reasoning_summary":"The agent needs the calculator for arithmetic."}'
        if "observations so far:\n[]" in user_content:
            return '{"action":"tool","tool_name":"knowledge_search","arguments":{"query":"operations policy","top_k":3},"reasoning_summary":"The agent starts by searching the knowledge base."}'
        return '{"action":"finish","final_answer":"I completed the requested workflow using the available tools.","reasoning_summary":"The agent called the selected tool and summarized the observation."}'
