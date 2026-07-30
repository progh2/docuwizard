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


class RagCancelled(RagError):
    """Raised when the user cancels an in-flight answer."""

    def __init__(self, partial: str = "") -> None:
        super().__init__("응답이 중단되었습니다.")
        self.partial = partial


def answer_question(
    project_id: str,
    question: str,
    *,
    client: OllamaClient | None = None,
    settings: dict[str, Any] | None = None,
    db: Path | None = None,
    stream: bool = False,
    history: list[dict[str, str]] | None = None,
    on_token=None,
    on_status=None,
    cancel_check=None,
) -> RagAnswer:
    cfg = settings or load_settings()
    ollama = client or OllamaClient(OllamaConfig.from_settings(cfg))
    top_k = int(cfg.get("rag", {}).get("top_k", 5))
    embed_model = ollama.config.embed_model

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    def check_cancel(partial: str = "") -> None:
        if cancel_check and cancel_check():
            raise RagCancelled(partial)

    check_cancel()
    status(f"질문 임베딩 중… ({embed_model})")
    try:
        query_vecs = ollama.embed([question])
    except OllamaError as exc:
        raise RagError(str(exc)) from exc
    if not query_vecs:
        raise RagError("질문 임베딩을 만들지 못했습니다.")

    check_cancel()
    status("관련 문서 검색 중… (벡터+키워드)")
    citations = vectors.hybrid_search_project(
        project_id,
        query_vecs[0],
        question,
        top_k=top_k,
        model=embed_model,
        db=db,
    )
    messages = prompt.build_messages(question, citations, history=history)
    check_cancel()
    status(
        f"모델 응답 대기 중… ({ollama.config.chat_model}) "
        f"— 큰 모델은 첫 글자까지 수 분이 걸릴 수 있습니다"
    )
    parts: list[str] = []
    try:
        if stream and on_token is not None:
            first = True
            for token in ollama.chat_stream(messages):
                check_cancel("".join(parts))
                if first:
                    status(f"응답 생성 중… ({ollama.config.chat_model})")
                    first = False
                parts.append(token)
                on_token(token)
            text = "".join(parts)
        else:
            text = ollama.chat(messages, stream=False)
    except RagCancelled:
        raise
    except OllamaError as exc:
        if cancel_check and cancel_check():
            # The stream was aborted by the user; report as cancellation.
            raise RagCancelled("".join(parts)) from exc
        raise RagError(str(exc)) from exc

    return RagAnswer(
        text=text.strip(),
        citations=citations,
        model=ollama.config.chat_model,
        provider="ollama",
    )
