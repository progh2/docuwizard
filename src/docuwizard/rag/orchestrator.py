"""RAG orchestration: retrieve → prompt → LLM (issues #15–#18)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docuwizard.config import load_settings
from docuwizard.llm.ollama import OllamaClient, OllamaConfig, OllamaError
from docuwizard.rag import prompt, vectors
from docuwizard.rag.vectors import RetrievedChunk


@dataclass(frozen=True)
class RagAnswer:
    text: str
    citations: list[RetrievedChunk]
    model: str
    provider: str


class RagError(Exception):
    """Raised when RAG fails."""


def answer_question(
    project_id: str,
    question: str,
    *,
    client: OllamaClient | None = None,
    settings: dict[str, Any] | None = None,
    db: Path | None = None,
    stream: bool = False,
    on_token=None,
) -> RagAnswer:
    cfg = settings or load_settings()
    ollama = client or OllamaClient(OllamaConfig.from_settings(cfg))
    top_k = int(cfg.get("rag", {}).get("top_k", 5))
    embed_model = ollama.config.embed_model

    try:
        query_vecs = ollama.embed([question])
    except OllamaError as exc:
        raise RagError(str(exc)) from exc
    if not query_vecs:
        raise RagError("질문 임베딩을 만들지 못했습니다.")

    citations = vectors.search_project(
        project_id,
        query_vecs[0],
        top_k=top_k,
        model=embed_model,
        db=db,
    )
    messages = prompt.build_messages(question, citations)
    try:
        if stream and on_token is not None:
            parts: list[str] = []
            for token in ollama.chat_stream(messages):
                parts.append(token)
                on_token(token)
            text = "".join(parts)
        else:
            text = ollama.chat(messages, stream=False)
    except OllamaError as exc:
        raise RagError(str(exc)) from exc

    return RagAnswer(
        text=text.strip(),
        citations=citations,
        model=ollama.config.chat_model,
        provider="ollama",
    )
