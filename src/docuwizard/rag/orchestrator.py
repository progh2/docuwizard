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
    on_status=None,
) -> RagAnswer:
    cfg = settings or load_settings()
    ollama = client or OllamaClient(OllamaConfig.from_settings(cfg))
    top_k = int(cfg.get("rag", {}).get("top_k", 5))
    embed_model = ollama.config.embed_model

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    status(f"질문 임베딩 중… ({embed_model})")
    try:
        query_vecs = ollama.embed([question])
    except OllamaError as exc:
        raise RagError(str(exc)) from exc
    if not query_vecs:
        raise RagError("질문 임베딩을 만들지 못했습니다.")

    status("관련 문서 검색 중…")
    citations = vectors.search_project(
        project_id,
        query_vecs[0],
        top_k=top_k,
        model=embed_model,
        db=db,
    )
    messages = prompt.build_messages(question, citations)
    status(
        f"모델 응답 대기 중… ({ollama.config.chat_model}) "
        f"— 큰 모델은 첫 글자까지 수 분이 걸릴 수 있습니다"
    )
    try:
        if stream and on_token is not None:
            parts: list[str] = []
            first = True
            for token in ollama.chat_stream(messages):
                if first:
                    status(f"응답 생성 중… ({ollama.config.chat_model})")
                    first = False
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
