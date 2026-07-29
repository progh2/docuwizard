"""Tests for conversation search, stars, and favorites (M4)."""

from __future__ import annotations

from pathlib import Path

from docuwizard.ingest.pipeline import index_file
from docuwizard.rag.orchestrator import answer_question
from docuwizard.services import conversations as conversation_service
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama


def test_conversation_search_and_stars(tmp_path: Path) -> None:
    fake = FakeOllama()
    project = project_service.create_project("즐겨찾기")
    src = tmp_path / "rfp.txt"
    src.write_text("제출 마감은 월요일입니다. 배점은 기술 80점입니다.", encoding="utf-8")
    file = file_service.add_files(project.id, [src])[0]
    index_file(project.id, file, embedder=fake)

    first = conversation_service.create_conversation(project.id, "마감 문의")
    second = conversation_service.create_conversation(project.id, "배점 문의")
    conversation_service.add_message(first.id, role="user", content="마감일은?")
    answer = answer_question(project.id, "마감일은?", client=fake)
    assistant = conversation_service.add_message(
        first.id,
        role="assistant",
        content=answer.text,
        citations=answer.citations,
    )

    found = conversation_service.list_conversations(project.id, query="마감")
    assert {c.id for c in found} == {first.id}

    conversation_service.toggle_conversation_star(second.id)
    starred = conversation_service.list_starred_conversations(project.id)
    assert [c.id for c in starred] == [second.id]

    conversation_service.toggle_message_star(assistant.id)
    favorites = conversation_service.list_starred_messages(project.id)
    assert len(favorites) == 1
    assert favorites[0].message.id == assistant.id
    assert favorites[0].conversation_title == "마감 문의"

    chunks = conversation_service.get_chunks_by_ids(assistant.citation_ids or [])
    assert chunks
    assert chunks[0].original_name == "rfp.txt"
