"""Vector packing and cosine search over SQLite embeddings (issue #16)."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path

from docuwizard.db import db_session


def pack_vector(values: list[float]) -> bytes:
    return struct.pack(f"{len(values)}f", *values)


def unpack_vector(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return -1.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    project_id: str
    file_id: str
    text: str
    score: float
    page: int | None
    line_start: int | None
    line_end: int | None
    sheet: str | None
    cell_range: str | None
    original_name: str


def upsert_embeddings(
    items: list[tuple[str, str, list[float]]],
    *,
    db: Path | None = None,
) -> None:
    """items: (chunk_id, model, vector)."""
    with db_session(db) as conn:
        conn.executemany(
            """
            INSERT INTO embeddings(chunk_id, model, dim, vector)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                model=excluded.model,
                dim=excluded.dim,
                vector=excluded.vector
            """,
            [
                (chunk_id, model, len(vector), pack_vector(vector))
                for chunk_id, model, vector in items
            ],
        )


def search_project(
    project_id: str,
    query_vector: list[float],
    *,
    top_k: int = 5,
    model: str | None = None,
    db: Path | None = None,
) -> list[RetrievedChunk]:
    with db_session(db) as conn:
        sql = """
            SELECT e.chunk_id, e.model, e.vector,
                   c.project_id, c.file_id, c.text, c.page, c.line_start, c.line_end,
                   c.sheet, c.cell_range, f.original_name
            FROM embeddings e
            JOIN chunks c ON c.id = e.chunk_id
            JOIN files f ON f.id = c.file_id
            WHERE c.project_id = ?
        """
        params: list = [project_id]
        if model:
            sql += " AND e.model = ?"
            params.append(model)
        rows = conn.execute(sql, params).fetchall()

    scored: list[RetrievedChunk] = []
    for row in rows:
        vector = unpack_vector(row["vector"])
        score = cosine_similarity(query_vector, vector)
        scored.append(
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                project_id=row["project_id"],
                file_id=row["file_id"],
                text=row["text"],
                score=score,
                page=row["page"],
                line_start=row["line_start"],
                line_end=row["line_end"],
                sheet=row["sheet"],
                cell_range=row["cell_range"],
                original_name=row["original_name"],
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: max(top_k, 0)]
