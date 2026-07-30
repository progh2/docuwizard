"""Import and manage project source files (issue #6, #7, #43)."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from docuwizard.ingest import store
from docuwizard.models import FileStatus, ProjectFile
from docuwizard.services import projects as project_service


class FileError(Exception):
    """Raised when a file operation fails."""


def list_files(project_id: str) -> list[ProjectFile]:
    project_service.get_project(project_id)
    path = project_service.project_manifest_path(project_id)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return [ProjectFile.from_dict(item) for item in raw]


def add_files(
    project_id: str,
    sources: list[Path],
    *,
    skip_duplicates: bool = True,
) -> list[ProjectFile]:
    """Copy source files into the project files/ directory and update the manifest.

    Files whose content hash matches an existing project file are skipped
    (compare the returned list against ``sources`` to detect skips).
    """
    project = project_service.get_project(project_id)
    store.upsert_project(project)
    files_dir = project_service.project_files_dir(project_id)
    files_dir.mkdir(parents=True, exist_ok=True)

    current = list_files(project_id)
    known_hashes = {f.content_hash for f in current if f.content_hash}
    added: list[ProjectFile] = []

    for source in sources:
        src = Path(source)
        if not src.is_file():
            raise FileError(f"파일이 아닙니다: {src}")

        content_hash = _hash_file(src)
        if skip_duplicates and content_hash in known_hashes:
            continue

        file_id = uuid.uuid4().hex
        stored_name = _unique_stored_name(files_dir, src.name)
        dest = files_dir / stored_name
        shutil.copy2(src, dest)

        record = ProjectFile(
            id=file_id,
            project_id=project_id,
            original_name=src.name,
            stored_name=stored_name,
            size=dest.stat().st_size,
            status=FileStatus.PENDING,
            content_hash=content_hash,
        )
        current.append(record)
        added.append(record)
        known_hashes.add(content_hash)
        store.upsert_file(record)

    _write_manifest(project_id, current)
    project_service.touch_project(project_id)
    return added


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def update_file_status(
    project_id: str,
    file_id: str,
    status: FileStatus,
    error: str | None = None,
) -> ProjectFile:
    current = list_files(project_id)
    updated: ProjectFile | None = None
    for idx, item in enumerate(current):
        if item.id != file_id:
            continue
        updated = ProjectFile(
            id=item.id,
            project_id=item.project_id,
            original_name=item.original_name,
            stored_name=item.stored_name,
            size=item.size,
            status=status,
            error=error,
            added_at=item.added_at,
            content_hash=item.content_hash,
        )
        current[idx] = updated
        break
    if updated is None:
        raise FileError("파일을 찾을 수 없습니다.")
    _write_manifest(project_id, current)
    store.upsert_file(updated)
    return updated


def delete_file(project_id: str, file_id: str) -> None:
    project_service.get_project(project_id)
    current = list_files(project_id)
    target = next((f for f in current if f.id == file_id), None)
    if target is None:
        raise FileError("파일을 찾을 수 없습니다.")

    path = project_service.project_files_dir(project_id) / target.stored_name
    if path.exists():
        path.unlink()

    remaining = [f for f in current if f.id != file_id]
    _write_manifest(project_id, remaining)
    store.delete_file(file_id)
    project_service.touch_project(project_id)


def absolute_path(project_id: str, file: ProjectFile) -> Path:
    return project_service.project_files_dir(project_id) / file.stored_name


def _unique_stored_name(files_dir: Path, original_name: str) -> str:
    candidate = original_name
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix
    counter = 1
    while (files_dir / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _write_manifest(project_id: str, files: list[ProjectFile]) -> None:
    path = project_service.project_manifest_path(project_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in files], f, ensure_ascii=False, indent=2)
        f.write("\n")
