"""Common chat-client interface shared by Ollama and external providers (#30)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable


class LlmError(Exception):
    """Raised when any LLM request fails."""


@runtime_checkable
class ChatClient(Protocol):
    """What the RAG orchestrator needs from an answer-generating client."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def chat(self, messages: list[dict[str, str]], *, stream: bool = False) -> str: ...

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]: ...

    def abort(self) -> None: ...

    def ping(self) -> str: ...
