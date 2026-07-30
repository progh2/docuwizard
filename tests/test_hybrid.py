"""Tests for hybrid retrieval, multi-turn prompts, and cancellation (#38–#40)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docuwizard.db import db_session
from docuwizard.ingest.pipeline import index_file
from docuwizard.rag import prompt, vectors
from docuwizard.rag.orchestrator import RagCancelled, answer_question
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama


def _project_with_files(tmp_path: Path, texts: dict[str, str]):
    project = project_service.create_project("하이브리드")
    fake = FakeOllama()
    for name, text in texts.items():
        src = tmp_path / name
        src.write_text(text, encoding="utf-8")
        added = file_service.add_files(project.id, [src])[0]
        index_file(project.id, added, embedder=fake)
    return project


def test_keyword_search_finds_korean_terms(tmp_path: Path) -> None:
    project = _project_with_files(
        tmp_path,
        {
            "a.txt": "특별예산은 총 3억 원이며 초과 집행은 금지됩니다.",
            "b.txt": "회의실 예약은 총무팀에 문의하십시오.",
        },
    )
    hits = vectors.keyword_search_project(project.id, "특별예산 규모가 어떻게 되나요?")
    assert hits
    assert "특별예산" in hits[0].text
    # Terms absent from documents yield no hits.
    assert vectors.keyword_search_project(project.id, "블록체인 마이닝") == []


def test_fts_rows_removed_when_project_deleted(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path, {"a.txt": "특별예산은 3억 원입니다."})
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] > 0
    project_service.delete_project(project.id)
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 0


def test_hybrid_search_boosts_keyword_match(tmp_path: Path) -> None:
    project = _project_with_files(
        tmp_path,
        {
            "budget.txt": "특별예산은 총 3억 원 규모로 편성되었습니다.",
            "misc.txt": "사무용품 구매 절차 안내 문서입니다.",
        },
    )
    fake = FakeOllama()
    question = "특별예산 규모를 알려줘"
    query_vec = fake.embed([question])[0]
    results = vectors.hybrid_search_project(
        project.id, query_vec, question, top_k=2, model="fake-embed"
    )
    assert results
    assert "특별예산" in results[0].text
    # Fused scores are RRF sums, descending.
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_trim_history_respects_budget() -> None:
    history = [
        {"role": "user", "content": f"질문 {i}"} for i in range(20)
    ]
    trimmed = prompt.trim_history(history)
    assert len(trimmed) == prompt.HISTORY_MAX_MESSAGES
    assert trimmed[-1]["content"] == "질문 19"

    big = [
        {"role": "user", "content": "x" * 3000},
        {"role": "assistant", "content": "y" * 3000},
        {"role": "user", "content": "마지막"},
    ]
    trimmed = prompt.trim_history(big)
    # Newest message always kept; older ones dropped once over the char budget.
    assert trimmed[-1]["content"] == "마지막"
    assert sum(len(m["content"]) for m in trimmed) <= prompt.HISTORY_MAX_CHARS

    assert prompt.trim_history(None) == []
    # System/other roles are excluded.
    assert prompt.trim_history([{"role": "system", "content": "s"}]) == []


def test_build_messages_includes_history() -> None:
    history = [
        {"role": "user", "content": "마감일이 언제야?"},
        {"role": "assistant", "content": "8월 1일입니다. [doc:1]"},
    ]
    messages = prompt.build_messages("그날 제출 방법은?", [], history=history)
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "마감일이 언제야?"
    assert "그날 제출 방법은?" in messages[-1]["content"]


def test_answer_question_cancel_mid_stream(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path, {"a.txt": "마감일은 금요일입니다."})
    cancelled = {"flag": False}
    tokens: list[str] = []

    def on_token(token: str) -> None:
        tokens.append(token)
        cancelled["flag"] = True  # cancel after the first token

    with pytest.raises(RagCancelled) as excinfo:
        answer_question(
            project.id,
            "마감일은?",
            client=FakeOllama(),
            stream=True,
            on_token=on_token,
            cancel_check=lambda: cancelled["flag"],
        )
    assert tokens == ["마감일은 "]
    assert excinfo.value.partial == "마감일은 "


def test_answer_question_cancel_before_start(tmp_path: Path) -> None:
    project = _project_with_files(tmp_path, {"a.txt": "마감일은 금요일입니다."})
    with pytest.raises(RagCancelled):
        answer_question(
            project.id,
            "마감일은?",
            client=FakeOllama(),
            cancel_check=lambda: True,
        )
