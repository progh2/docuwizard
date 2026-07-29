"""Test doubles."""

from __future__ import annotations

from docuwizard.llm.ollama import OllamaClient, OllamaConfig


class FakeOllama(OllamaClient):
    def __init__(self) -> None:
        super().__init__(OllamaConfig(embed_model="fake-embed", chat_model="fake-chat"))

    def ping(self) -> str:
        return "연결됨 (테스트)"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors_out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * 8
            for ch in text:
                vec[ord(ch) % 8] += 1.0
            vectors_out.append(vec)
        return vectors_out

    def chat(self, messages: list[dict[str, str]], *, stream: bool = False) -> str:
        return "마감일은 금요일입니다. [doc:1]"

    def chat_stream(self, messages: list[dict[str, str]]):
        yield "마감일은 "
        yield "금요일입니다. "
        yield "[doc:1]"
