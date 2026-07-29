"""Tests for RAG retrieval, prompts, conversations, and Ollama client helpers."""

from __future__ import annotations

from pathlib import Path

from docuwizard.ingest.pipeline import index_file
from docuwizard.rag import prompt, vectors
from docuwizard.rag.orchestrator import answer_question
from docuwizard.rag.vectors import RetrievedChunk
from docuwizard.services import conversations as conversation_service
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama


def test_pack_unpack_and_cosine() -> None:
    blob = vectors.pack_vector([1.0, 0.0, 0.0])
    assert vectors.unpack_vector(blob) == [1.0, 0.0, 0.0]
    assert vectors.cosine_similarity([1, 0], [1, 0]) == 1.0


def test_prompt_includes_citation_ids() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        project_id="p",
        file_id="f",
        text="제출 마감은 금요일",
        score=0.9,
        page=1,
        line_start=3,
        line_end=3,
        sheet=None,
        cell_range=None,
        original_name="guide.txt",
    )
    messages = prompt.build_messages("마감일은?", [chunk])
    assert "[doc:1]" in messages[1]["content"]
    assert "guide.txt" in messages[1]["content"]


def test_index_embed_search_and_answer(tmp_path: Path) -> None:
    fake = FakeOllama()
    project = project_service.create_project("RAG")
    src = tmp_path / "guide.txt"
    src.write_text(
        "사업 제출 마감은 금요일입니다.\n평가 배점은 기술 70점입니다.\n",
        encoding="utf-8",
    )
    added = file_service.add_files(project.id, [src])[0]
    count = index_file(project.id, added, embedder=fake)
    assert count >= 1

    answer = answer_question(project.id, "마감일은 언제인가요?", client=fake)
    assert "금요일" in answer.text
    assert answer.citations
    assert answer.provider == "ollama"


def test_conversation_persistence(tmp_path: Path) -> None:
    fake = FakeOllama()
    project = project_service.create_project("대화")
    src = tmp_path / "a.txt"
    src.write_text("필수 서류는 사업자등록증입니다.", encoding="utf-8")
    file = file_service.add_files(project.id, [src])[0]
    index_file(project.id, file, embedder=fake)

    conversation = conversation_service.create_conversation(project.id, "서류")
    conversation_service.add_message(conversation.id, role="user", content="필수 서류는?")
    answer = answer_question(project.id, "필수 서류는?", client=fake)
    conversation_service.add_message(
        conversation.id,
        role="assistant",
        content=answer.text,
        model=answer.model,
        provider=answer.provider,
        citations=answer.citations,
    )
    messages = conversation_service.list_messages(conversation.id)
    assert len(messages) == 2
    assert messages[1].citation_ids
    renamed = conversation_service.rename_conversation(conversation.id, "필수서류")
    assert renamed.title == "필수서류"
    conversation_service.delete_conversation(conversation.id)
    assert conversation_service.list_conversations(project.id) == []
