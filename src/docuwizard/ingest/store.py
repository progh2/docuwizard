"""Persist projects/files/chunks in SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from docuwizard.db import db_session
from docuwizard.ingest.chunking import Chunk
from docuwizard.models import Project, ProjectFile


def upsert_project(project: Project, *, db: Path | None = None) -> None:
    with db_session(db) as conn:
        conn.execute(
            """
            INSERT INTO projects(id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                updated_at=excluded.updated_at
            """,
            (
                project.id,
                project.name,
                project.description,
                project.created_at,
                project.updated_at,
            ),
        )


def delete_project(project_id: str, *, db: Path | None = None) -> None:
    with db_session(db) as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


def upsert_file(file: ProjectFile, *, db: Path | None = None) -> None:
    with db_session(db) as conn:
        conn.execute(
            """
            INSERT INTO files(
                id, project_id, original_name, stored_name, size, status, error,
                added_at, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                original_name=excluded.original_name,
                stored_name=excluded.stored_name,
                size=excluded.size,
                status=excluded.status,
                error=excluded.error,
                content_hash=excluded.content_hash
            """,
            (
                file.id,
                file.project_id,
                file.original_name,
                file.stored_name,
                file.size,
                str(file.status),
                file.error,
                file.added_at,
                file.content_hash,
            ),
        )


def delete_file(file_id: str, *, db: Path | None = None) -> None:
    with db_session(db) as conn:
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))


def replace_chunks(
    *,
    project_id: str,
    file_id: str,
    chunks: list[Chunk],
    db: Path | None = None,
) -> int:
    with db_session(db) as conn:
        conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
        conn.executemany(
            """
            INSERT INTO chunks(
                id, project_id, file_id, chunk_index, text,
                page, line_start, line_end, sheet, cell_range, char_start, char_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    c.id,
                    project_id,
                    file_id,
                    c.chunk_index,
                    c.text,
                    c.page,
                    c.line_start,
                    c.line_end,
                    c.sheet,
                    c.cell_range,
                    c.char_start,
                    c.char_end,
                )
                for c in chunks
            ],
        )
    return len(chunks)


def count_chunks(project_id: str, *, db: Path | None = None) -> int:
    with db_session(db) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        return int(row["n"])


def list_chunks_for_file(file_id: str, *, db: Path | None = None) -> list[sqlite3.Row]:
    with db_session(db) as conn:
        return list(
            conn.execute(
                "SELECT * FROM chunks WHERE file_id = ? ORDER BY chunk_index",
                (file_id,),
            ).fetchall()
        )
