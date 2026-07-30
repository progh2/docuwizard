"""Import and manage project source files (issues #6, #7, #43, #44).

SQLite is the source of truth for file metadata. A legacy ``files.json``
manifest, if present, is imported once and then removed.
"""

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
    _migrate_manifest_if_needed(project_id)
    return store.list_files(project_id)


def add_files(
    project_id: str,
    sources: list[Path],
    *,
    skip_duplicates: bool = True,
) -> list[ProjectFile]:
    """Copy source files into the project files/ directory.

    Files whose content hash matches an existing project file are skipped
    (compare the returned list against ``sources`` to detect skips).
    """
    project = project_service.get_project(project_id)
    store.upsert_project(project)
    _migrate_manifest_if_needed(project_id)
    files_dir = project_service.project_files_dir(project_id)
    files_dir.mkdir(parents=True, exist_ok=True)

    current = store.list_files(project_id)
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
        added.append(record)
        known_hashes.add(content_hash)
        store.upsert_file(record)

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
    project_service.get_project(project_id)
    _migrate_manifest_if_needed(project_id)
    item = store.get_file(file_id)
    if item is None or item.project_id != project_id:
        raise FileError("파일을 찾을 수 없습니다.")
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
    store.upsert_file(updated)
    return updated


def delete_file(project_id: str, file_id: str) -> None:
    project_service.get_project(project_id)
    _migrate_manifest_if_needed(project_id)
    target = store.get_file(file_id)
    if target is None or target.project_id != project_id:
        raise FileError("파일을 찾을 수 없습니다.")

    path = project_service.project_files_dir(project_id) / target.stored_name
    if path.exists():
        path.unlink()

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


def _migrate_manifest_if_needed(project_id: str) -> None:
    """One-time import of legacy files.json into SQLite, then delete the file."""
    path = project_service.project_manifest_path(project_id)
    if not path.exists():
        return
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(raw, list):
        return
    existing_ids = {f.id for f in store.list_files(project_id)}
    for item in raw:
        try:
            record = ProjectFile.from_dict(item)
        except (KeyError, TypeError, ValueError):
            continue
        if record.id in existing_ids:
            continue
        store.upsert_file(record)
    try:
        path.unlink()
    except OSError:
        pass
