"""Tests for essentials report generation and stars (issues #25–#27)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docuwizard.ingest.pipeline import index_file
from docuwizard.services import essentials
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from fakes import FakeOllama


def _indexed_project(tmp_path: Path):
    project = project_service.create_project("필수 포인트")
    src = tmp_path / "notice.txt"
    src.write_text(
        "제안서 마감일은 8월 1일 금요일입니다.\n"
        "평가 배점은 기술 70점, 가격 30점입니다.\n",
        encoding="utf-8",
    )
    added = file_service.add_files(project.id, [src])[0]
    index_file(project.id, added, embedder=FakeOllama())
    return project


def test_generate_report_persists_items_and_citations(tmp_path: Path) -> None:
    project = _indexed_project(tmp_path)
    statuses: list[str] = []

    report = essentials.generate_report(
        project.id, client=FakeOllama(), on_status=statuses.append
    )
    assert report.version == 1
    assert report.items
    assert statuses  # progress was reported

    loaded = essentials.get_report(report.id)
    assert len(loaded.items) == len(report.items)
    # FakeOllama always answers with [doc:1] → every item cites a real chunk.
    assert all(item.citation_ids for item in loaded.items)
    assert all(item.category in essentials.CATEGORY_NAMES for item in loaded.items)


def test_generate_report_versions_increment(tmp_path: Path) -> None:
    project = _indexed_project(tmp_path)
    first = essentials.generate_report(project.id, client=FakeOllama())
    second = essentials.generate_report(project.id, client=FakeOllama())
    assert (first.version, second.version) == (1, 2)

    reports = essentials.list_reports(project.id)
    assert [r.version for r in reports] == [2, 1]
    # Old versions stay intact.
    assert essentials.get_report(first.id).items


def test_generate_report_requires_indexed_documents() -> None:
    project = project_service.create_project("빈 프로젝트")
    with pytest.raises(essentials.EssentialsError):
        essentials.generate_report(project.id, client=FakeOllama())


def test_star_report_and_items(tmp_path: Path) -> None:
    project = _indexed_project(tmp_path)
    report = essentials.generate_report(project.id, client=FakeOllama())

    assert essentials.toggle_report_star(report.id) is True
    assert essentials.list_reports(project.id)[0].is_starred is True
    assert essentials.toggle_report_star(report.id) is False

    item = report.items[0]
    assert essentials.toggle_item_star(item.id) is True
    starred = essentials.list_starred_items(project.id)
    assert [s.item.id for s in starred] == [item.id]
    assert starred[0].report_version == report.version
    assert essentials.toggle_item_star(item.id) is False
    assert essentials.list_starred_items(project.id) == []


def test_parse_items_handles_bullets_and_plain_text() -> None:
    bullets = "- 마감일은 금요일 [doc:1]\n- 배점은 70:30 [doc:2][doc:1]\n"
    parsed = essentials._parse_items(bullets)
    assert parsed == [
        ("마감일은 금요일", [1]),
        ("배점은 70:30", [2, 1]),
    ]

    plain = essentials._parse_items("마감일은 금요일입니다. [doc:1]")
    assert parsed[0][1] == [1]
    assert plain == [("마감일은 금요일입니다", [1])]

    assert essentials._parse_items("") == []
