"""Project CRUD against the local filesystem (issue #4, #7)."""

from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from docuwizard.models import Project, utc_now_iso
from docuwizard.paths import ensure_app_dirs, projects_dir


class ProjectError(Exception):
    """Raised when a project operation fails."""


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "-", name.strip(), flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-").lower()
    return slug or "project"


def project_root(project_id: str) -> Path:
    return projects_dir() / project_id


def project_meta_path(project_id: str) -> Path:
    return project_root(project_id) / "project.json"


def project_files_dir(project_id: str) -> Path:
    return project_root(project_id) / "files"


def project_manifest_path(project_id: str) -> Path:
    return project_root(project_id) / "files.json"


def create_project(name: str, description: str = "") -> Project:
    """Create a new project directory and metadata file."""
    ensure_app_dirs()
    cleaned = name.strip()
    if not cleaned:
        raise ProjectError("프로젝트 이름을 입력하세요.")

    project_id = f"{_slugify(cleaned)[:40]}-{uuid.uuid4().hex[:8]}"
    root = project_root(project_id)
    if root.exists():
        raise ProjectError("프로젝트 디렉터리를 만들 수 없습니다. 다시 시도하세요.")

    files_dir = project_files_dir(project_id)
    files_dir.mkdir(parents=True, exist_ok=False)
    project = Project(id=project_id, name=cleaned, description=description.strip())
    _write_project(project)
    project_manifest_path(project_id).write_text("[]\n", encoding="utf-8")
    return project


def list_projects(query: str | None = None) -> list[Project]:
    """List projects, newest updated first. Optional case-insensitive name search."""
    ensure_app_dirs()
    projects: list[Project] = []
    for meta in projects_dir().glob("*/project.json"):
        try:
            projects.append(_read_project(meta))
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    projects.sort(key=lambda p: p.updated_at, reverse=True)
    if query:
        q = query.strip().casefold()
        projects = [
            p
            for p in projects
            if q in p.name.casefold() or q in p.description.casefold()
        ]
    return projects


def get_project(project_id: str) -> Project:
    path = project_meta_path(project_id)
    if not path.exists():
        raise ProjectError("프로젝트를 찾을 수 없습니다.")
    return _read_project(path)


def rename_project(project_id: str, name: str, description: str | None = None) -> Project:
    cleaned = name.strip()
    if not cleaned:
        raise ProjectError("프로젝트 이름을 입력하세요.")
    project = get_project(project_id)
    project.name = cleaned
    if description is not None:
        project.description = description.strip()
    project.updated_at = utc_now_iso()
    _write_project(project)
    return project


def delete_project(project_id: str) -> None:
    """Remove project metadata, files, and directory tree."""
    root = project_root(project_id)
    if not root.exists():
        raise ProjectError("프로젝트를 찾을 수 없습니다.")
    shutil.rmtree(root)


def touch_project(project_id: str) -> None:
    project = get_project(project_id)
    project.updated_at = utc_now_iso()
    _write_project(project)


def _read_project(path: Path) -> Project:
    with path.open(encoding="utf-8") as f:
        return Project.from_dict(json.load(f))


def _write_project(project: Project) -> None:
    path = project_meta_path(project.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)
        f.write("\n")
