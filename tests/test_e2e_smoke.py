"""End-to-end smoke: fixture → index → RAG → essentials → cascade delete (#36, #34)."""

from __future__ import annotations

from pathlib import Path

from docuwizard.db import connect
from docuwizard.ingest import store
from docuwizard.ingest.pipeline import index_file
from docuwizard.rag.orchestrator import answer_question
from docuwizard.services import conversations as conversation_service
from docuwizard.services import essentials
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_rfp.txt"


def test_e2e_sample_fixture_rag_and_essentials() -> None:
    assert FIXTURE.is_file()
    project = project_service.create_project("스모크", "샘플 RFP")
    added = file_service.add_files(project.id, [FIXTURE])
    assert len(added) == 1
    assert added[0].content_hash

    fake = FakeOllama()
    chunks = index_file(project.id, added[0], embedder=fake)
    assert chunks >= 1
    assert store.count_chunks(project.id) == chunks

    answer = answer_question(
        project.id,
        "제안서 마감일은 언제인가요?",
        client=fake,
        chat_client=fake,
    )
    assert answer.text
    assert answer.citations
    assert answer.provider == "ollama"

    conversation = conversation_service.create_conversation(project.id, "마감 문의")
    conversation_service.add_message(
        conversation.id, role="user", content="마감일은?"
    )
    conversation_service.add_message(
        conversation.id,
        role="assistant",
        content=answer.text,
        model=answer.model,
        provider=answer.provider,
        citations=answer.citations,
    )
    assert conversation_service.list_messages(conversation.id)

    report = essentials.generate_report(project.id, client=fake, chat_client=fake)
    assert report.version == 1
    assert report.items

    # SQLite is source of truth — no files.json after add.
    assert not project_service.project_manifest_path(project.id).exists()


def test_delete_project_cascades_db_vectors_and_files() -> None:
    project = project_service.create_project("캐스케이드")
    src = Path(__file__).resolve().parents[1] / "fixtures" / "sample_rfp.txt"
    added = file_service.add_files(project.id, [src])[0]
    fake = FakeOllama()
    index_file(project.id, added, embedder=fake)

    conversation = conversation_service.create_conversation(project.id, "대화")
    conversation_service.add_message(conversation.id, role="user", content="안녕")

    root = project_service.project_root(project.id)
    file_path = file_service.absolute_path(project.id, added)
    assert root.exists() and file_path.exists()
    assert store.count_chunks(project.id) >= 1

    project_service.delete_project(project.id)

    assert not root.exists()
    with connect() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM projects WHERE id = ?", (project.id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM files WHERE project_id = ?", (project.id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE project_id = ?", (project.id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                """
                SELECT COUNT(*) FROM embeddings e
                JOIN chunks c ON c.id = e.chunk_id
                WHERE c.project_id = ?
                """,
                (project.id,),
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE project_id = ?",
                (project.id,),
            ).fetchone()[0]
            == 0
        )
        # Orphan FTS rows should be gone (chunks deleted → trigger cleans FTS).
        assert conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0] == 0


def test_legacy_files_json_migrates_to_sqlite(tmp_path: Path) -> None:
    import json

    project = project_service.create_project("마이그레이션")
    # Simulate a pre-#44 project that only has files.json.
    src = tmp_path / "legacy.txt"
    src.write_text("레거시", encoding="utf-8")
    stored = "legacy.txt"
    dest = project_service.project_files_dir(project.id) / stored
    dest.write_text("레거시", encoding="utf-8")
    record = {
        "id": "legacyid000000000000000000000001",
        "project_id": project.id,
        "original_name": "legacy.txt",
        "stored_name": stored,
        "size": dest.stat().st_size,
        "status": "pending",
        "error": None,
        "added_at": "2026-01-01T00:00:00+00:00",
        "content_hash": None,
    }
    manifest = project_service.project_manifest_path(project.id)
    manifest.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")

    listed = file_service.list_files(project.id)
    assert len(listed) == 1
    assert listed[0].original_name == "legacy.txt"
    assert store.get_file(listed[0].id) is not None
    assert not manifest.exists()
