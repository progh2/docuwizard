"""Tests for project and file services (M1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service
from docuwizard.services.files import FileError
from docuwizard.services.projects import ProjectError


@pytest.fixture(autouse=True)
def isolated_app_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = tmp_path / "data"
    config = tmp_path / "config"
    projects = data / "projects"
    monkeypatch.setattr("docuwizard.paths.data_dir", lambda: data)
    monkeypatch.setattr("docuwizard.paths.config_dir", lambda: config)
    monkeypatch.setattr("docuwizard.paths.projects_dir", lambda: projects)
    monkeypatch.setattr("docuwizard.services.projects.projects_dir", lambda: projects)
    yield


def test_create_list_rename_delete_project() -> None:
    project = project_service.create_project("입찰 A", "RFP 모음")
    assert project.name == "입찰 A"
    assert project_service.project_files_dir(project.id).is_dir()

    listed = project_service.list_projects()
    assert len(listed) == 1
    assert listed[0].id == project.id

    found = project_service.list_projects("입찰")
    assert len(found) == 1
    assert project_service.list_projects("없는이름") == []

    renamed = project_service.rename_project(project.id, "입찰 B", "수정됨")
    assert renamed.name == "입찰 B"
    assert renamed.description == "수정됨"

    project_service.delete_project(project.id)
    assert project_service.list_projects() == []
    assert not project_service.project_root(project.id).exists()


def test_create_project_rejects_empty_name() -> None:
    with pytest.raises(ProjectError):
        project_service.create_project("   ")


def test_add_and_delete_files(tmp_path: Path) -> None:
    project = project_service.create_project("문서")
    src1 = tmp_path / "a.txt"
    src2 = tmp_path / "b.md"
    src1.write_text("hello", encoding="utf-8")
    src2.write_text("# title", encoding="utf-8")

    added = file_service.add_files(project.id, [src1, src2])
    assert len(added) == 2
    listed = file_service.list_files(project.id)
    assert {f.original_name for f in listed} == {"a.txt", "b.md"}
    for record in listed:
        assert file_service.absolute_path(project.id, record).is_file()

    file_service.delete_file(project.id, listed[0].id)
    remaining = file_service.list_files(project.id)
    assert len(remaining) == 1

    with pytest.raises(FileError):
        file_service.delete_file(project.id, "missing")


def test_delete_project_removes_copied_files(tmp_path: Path) -> None:
    project = project_service.create_project("삭제테스트")
    src = tmp_path / "note.txt"
    src.write_text("x", encoding="utf-8")
    file_service.add_files(project.id, [src])
    root = project_service.project_root(project.id)
    assert root.exists()
    project_service.delete_project(project.id)
    assert not root.exists()
