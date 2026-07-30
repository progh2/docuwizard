"""Ingest pipeline: parse → chunk → store (issues #9–#14)."""

from __future__ import annotations

from pathlib import Path

from docuwizard.config import load_settings
from docuwizard.ingest import chunking, parsers, store
from docuwizard.ingest.parsers import ParseError
from docuwizard.llm.ollama import OllamaClient, OllamaConfig, OllamaError
from docuwizard.models import FileStatus, ProjectFile
from docuwizard.rag import vectors
from docuwizard.services import files as file_service
from docuwizard.services import projects as project_service


class IndexingError(Exception):
    """Raised when indexing a file fails."""


def index_file(
    project_id: str,
    file: ProjectFile,
    *,
    db: Path | None = None,
    cancel_check=None,
    embedder: OllamaClient | None = None,
) -> int:
    """Index one file. Returns chunk count. Updates file status in manifest."""
    if cancel_check and cancel_check():
        raise IndexingError("인덱싱이 취소되었습니다.")

    path = file_service.absolute_path(project_id, file)
    if not path.exists():
        raise IndexingError(f"파일이 없습니다: {file.original_name}")

    project = project_service.get_project(project_id)
    store.upsert_project(project, db=db)
    file_service.update_file_status(project_id, file.id, FileStatus.INDEXING)
    store.upsert_file(
        _with_status(file, FileStatus.INDEXING),
        db=db,
    )

    try:
        if cancel_check and cancel_check():
            raise IndexingError("인덱싱이 취소되었습니다.")
        segments = parsers.parse_file(path)
        settings = load_settings()
        chunk_cfg = settings.get("chunking", {})
        chunks = chunking.chunk_segments(
            segments,
            chunk_size=int(chunk_cfg.get("chunk_size", 800)),
            chunk_overlap=int(chunk_cfg.get("chunk_overlap", 120)),
        )
        if cancel_check and cancel_check():
            raise IndexingError("인덱싱이 취소되었습니다.")
        count = store.replace_chunks(
            project_id=project_id,
            file_id=file.id,
            chunks=chunks,
            db=db,
        )
        if chunks:
            client = embedder or OllamaClient(OllamaConfig.from_settings(settings))
            batch_size = max(int(settings.get("rag", {}).get("embed_batch_size", 32)), 1)
            embeddings: list[list[float]] = []
            for start in range(0, len(chunks), batch_size):
                if cancel_check and cancel_check():
                    raise IndexingError("인덱싱이 취소되었습니다.")
                batch = chunks[start : start + batch_size]
                try:
                    embeddings.extend(client.embed([c.text for c in batch]))
                except OllamaError as exc:
                    raise IndexingError(f"임베딩 실패: {exc}") from exc
            if len(embeddings) != len(chunks):
                raise IndexingError("임베딩 개수가 청크 개수와 일치하지 않습니다.")
            vectors.upsert_embeddings(
                [
                    (chunk.id, client.config.embed_model, vector)
                    for chunk, vector in zip(chunks, embeddings, strict=True)
                ],
                db=db,
            )
        ready = _with_status(file, FileStatus.READY, error=None)
        file_service.update_file_status(project_id, file.id, FileStatus.READY, error=None)
        store.upsert_file(ready, db=db)
        return count
    except ParseError as exc:
        _fail(project_id, file, str(exc), db=db)
        raise IndexingError(str(exc)) from exc
    except IndexingError:
        pending = _with_status(file, FileStatus.PENDING, error=None)
        file_service.update_file_status(project_id, file.id, FileStatus.PENDING)
        store.upsert_file(pending, db=db)
        raise
    except Exception as exc:  # noqa: BLE001
        _fail(project_id, file, str(exc), db=db)
        raise IndexingError(str(exc)) from exc


def index_project_files(
    project_id: str,
    *,
    only_failed_or_pending: bool = True,
    db: Path | None = None,
    cancel_check=None,
    on_progress=None,
    embedder: OllamaClient | None = None,
) -> tuple[int, int]:
    """Index files in a project. Returns (success_count, fail_count)."""
    files = file_service.list_files(project_id)
    if only_failed_or_pending:
        files = [f for f in files if f.status in {FileStatus.PENDING, FileStatus.FAILED}]
    ok = 0
    failed = 0
    total = len(files)
    for idx, file in enumerate(files, start=1):
        if cancel_check and cancel_check():
            break
        if on_progress:
            on_progress(idx, total, file.original_name, "indexing")
        try:
            index_file(
                project_id,
                file,
                db=db,
                cancel_check=cancel_check,
                embedder=embedder,
            )
            ok += 1
            if on_progress:
                on_progress(idx, total, file.original_name, "ready")
        except IndexingError:
            failed += 1
            if on_progress:
                on_progress(idx, total, file.original_name, "failed")
    return ok, failed


def _fail(project_id: str, file: ProjectFile, error: str, *, db: Path | None) -> None:
    failed = _with_status(file, FileStatus.FAILED, error=error)
    file_service.update_file_status(project_id, file.id, FileStatus.FAILED, error=error)
    store.upsert_file(failed, db=db)


def _with_status(
    file: ProjectFile,
    status: FileStatus,
    error: str | None = None,
) -> ProjectFile:
    return ProjectFile(
        id=file.id,
        project_id=file.project_id,
        original_name=file.original_name,
        stored_name=file.stored_name,
        size=file.size,
        status=status,
        error=error,
        added_at=file.added_at,
        content_hash=file.content_hash,
    )
