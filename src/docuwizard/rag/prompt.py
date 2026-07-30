"""RAG prompt construction with citation IDs (issue #17)."""

from __future__ import annotations

from docuwizard.rag.vectors import RetrievedChunk

SYSTEM_PROMPT = (
    "당신은 로컬 문서 기반 질의응답 도우미입니다.\n"
    "제공된 컨텍스트만 사용해 답하세요. 컨텍스트에 없으면 모른다고 말하고 "
    "추가 확인이 필요한 자료를 제안하세요.\n"
    "답변에서 근거가 되는 문서는 [doc:N] 형식으로 인용하세요. "
    "N은 컨텍스트에 표시된 번호입니다.\n"
    "추측하거나 컨텍스트 밖의 사실을 단정하지 마세요."
)


def format_location(chunk: RetrievedChunk) -> str:
    parts: list[str] = [chunk.original_name]
    if chunk.page is not None:
        parts.append(f"p.{chunk.page}")
    if chunk.line_start is not None:
        if chunk.line_end and chunk.line_end != chunk.line_start:
            parts.append(f"L{chunk.line_start}-{chunk.line_end}")
        else:
            parts.append(f"L{chunk.line_start}")
    if chunk.sheet:
        parts.append(f"sheet:{chunk.sheet}")
    if chunk.cell_range:
        parts.append(chunk.cell_range)
    return " · ".join(parts)


# Multi-turn context budget: keep at most this many prior messages and chars.
HISTORY_MAX_MESSAGES = 6
HISTORY_MAX_CHARS = 4000


def trim_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Keep the most recent user/assistant turns within the context budget."""
    if not history:
        return []
    recent = [m for m in history if m.get("role") in ("user", "assistant")]
    recent = recent[-HISTORY_MAX_MESSAGES:]
    trimmed: list[dict[str, str]] = []
    total = 0
    for message in reversed(recent):
        content = str(message.get("content", ""))
        if trimmed and total + len(content) > HISTORY_MAX_CHARS:
            break
        trimmed.insert(0, {"role": message["role"], "content": content})
        total += len(content)
    return trimmed


def build_messages(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    past = trim_history(history)
    if not chunks:
        user = (
            "관련 컨텍스트가 없습니다.\n"
            f"사용자 질문: {question}\n"
            "컨텍스트가 없으므로 모른다고 답하고, 어떤 문서를 더 넣으면 좋을지 짧게 제안하세요."
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            *past,
            {"role": "user", "content": user},
        ]

    blocks = []
    for idx, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[doc:{idx}] ({format_location(chunk)})\n{chunk.text}"
        )
    context = "\n\n".join(blocks)
    user = (
        f"컨텍스트:\n{context}\n\n"
        f"질문: {question}\n"
        "한국어로 답하고 근거에 [doc:N]을 포함하세요. "
        "이전 대화가 있으면 그 흐름을 이어서 답하세요."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *past,
        {"role": "user", "content": user},
    ]
