"""Create the configured chat client (issue #30).

Embeddings always run locally through Ollama; only answer generation can be
routed to an external provider.
"""

from __future__ import annotations

from typing import Any

from docuwizard import apikeys
from docuwizard.llm.base import ChatClient
from docuwizard.llm.external import AnthropicClient, OpenAIClient
from docuwizard.llm.ollama import OllamaClient, OllamaConfig

PROVIDERS = ("ollama", "openai", "anthropic")


def chat_provider(settings: dict[str, Any]) -> str:
    provider = str(settings.get("llm", {}).get("provider", "ollama")).strip().lower()
    return provider if provider in PROVIDERS else "ollama"


def create_chat_client(
    settings: dict[str, Any],
    *,
    embedder: OllamaClient | None = None,
) -> ChatClient:
    """Return the chat client for the configured provider.

    When the provider is Ollama, an existing embedder client is reused so both
    roles share one connection config.
    """
    llm = settings.get("llm", {})
    provider = chat_provider(settings)
    timeout = float(llm.get("ollama_timeout_sec", 600) or 600)

    if provider == "openai":
        return OpenAIClient(
            model=str(llm.get("openai_model", "gpt-4o-mini")),
            api_key=apikeys.get_api_key("openai"),
            base_url=str(llm.get("openai_base_url", "https://api.openai.com/v1")),
            timeout_sec=timeout,
        )
    if provider == "anthropic":
        return AnthropicClient(
            model=str(llm.get("anthropic_model", "claude-sonnet-4-5")),
            api_key=apikeys.get_api_key("anthropic"),
            base_url=str(llm.get("anthropic_base_url", "https://api.anthropic.com/v1")),
            timeout_sec=timeout,
        )
    return embedder or OllamaClient(OllamaConfig.from_settings(settings))
