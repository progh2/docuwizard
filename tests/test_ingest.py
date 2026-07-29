"""Tests for parsers, chunking, and indexing pipeline (M2)."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from openpyxl import Workbook
from pypdf import PdfWriter

from docuwizard.db import connect
from docuwizard.ingest import chunking, parsers, store
from docuwizard.ingest.pipeline import index_file, index_project_files
from docuwizard.ingest.segments import TextSegment
from docuwizard.models import FileStatus
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service


def test_parse_text_line_metadata(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("첫번째\n\n두번째\n", encoding="utf-8")
    segments = parsers.parse_text(path)
    assert [(s.text, s.line_start, s.line_end) for s in segments] == [
        ("첫번째", 1, 1),
        ("두번째", 3, 3),
    ]


def test_parse_docx(tmp_path: Path) -> None:
    path = tmp_path / "doc.docx"
    document = Document()
    document.add_paragraph("제출 서류")
    document.add_paragraph("마감일 안내")
    document.save(path)
    segments = parsers.parse_docx(path)
    assert [s.text for s in segments] == ["제출 서류", "마감일 안내"]
    assert segments[0].line_start == 1


def test_parse_xlsx(tmp_path: Path) -> None:
    path = tmp_path / "sheet.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "일정"
    ws["A1"] = "항목"
    ws["B1"] = "마감"
    ws["A2"] = "제안서"
    ws["B2"] = "2026-08-01"
    wb.save(path)
    segments = parsers.parse_xlsx(path)
    assert any(s.sheet == "일정" and "제안서" in s.text for s in segments)
    assert any(s.cell_range for s in segments)


def test_parse_pdf(tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as f:
        writer.write(f)
    # Blank PDF yields no text segments; ensure it does not crash.
    assert parsers.parse_pdf(path) == []


def test_chunk_segments_respects_size() -> None:
    segments = [TextSegment(text="가" * 50, line_start=i, line_end=i) for i in range(1, 21)]
    chunks = chunking.chunk_segments(segments, chunk_size=120, chunk_overlap=20)
    assert chunks
    assert all(len(c.text) <= 120 for c in chunks)
    assert chunks[0].line_start is not None


def test_index_text_file_writes_chunks(tmp_path: Path) -> None:
    project = project_service.create_project("인덱싱")
    src = tmp_path / "guide.md"
    src.write_text("# 안내\n마감일은 다음 주 금요일입니다.\n", encoding="utf-8")
    added = file_service.add_files(project.id, [src])[0]

    count = index_file(project.id, added)
    assert count >= 1
    refreshed = file_service.list_files(project.id)[0]
    assert refreshed.status == FileStatus.READY
    assert store.count_chunks(project.id) == count
    rows = store.list_chunks_for_file(added.id)
    assert rows[0]["text"]


def test_index_failed_retry_and_delete_clears_chunks(tmp_path: Path) -> None:
    project = project_service.create_project("재시도")
    good = tmp_path / "ok.txt"
    good.write_text("유효한 내용", encoding="utf-8")
    unsupported = tmp_path / "image.webp"
    unsupported.write_bytes(b"webp")
    files = file_service.add_files(project.id, [good, unsupported])
    ok, failed = index_project_files(project.id)
    assert ok == 1
    assert failed == 1

    statuses = {f.original_name: f.status for f in file_service.list_files(project.id)}
    assert statuses["ok.txt"] == FileStatus.READY
    assert statuses["image.webp"] == FileStatus.FAILED

    file_id = next(f.id for f in files if f.original_name == "ok.txt")
    assert store.list_chunks_for_file(file_id)
    file_service.delete_file(project.id, file_id)
    assert store.list_chunks_for_file(file_id) == []


def test_schema_tables_exist() -> None:
    with connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"projects", "files", "chunks", "conversations", "messages"} <= tables
