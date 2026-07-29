"""Chunking strategy with configurable size/overlap (issue #13)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from docuwizard.ingest.segments import TextSegment


@dataclass(frozen=True)
class Chunk:
    id: str
    chunk_index: int
    text: str
    page: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    char_start: int | None = None
    char_end: int | None = None


def chunk_segments(
    segments: list[TextSegment],
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    if not segments:
        return []

    # Prefer grouping short line segments; fall back to sliding window on long text.
    joined_parts: list[tuple[str, TextSegment]] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            joined_parts.append((text, segment))
    if not joined_parts:
        return []

    chunks: list[Chunk] = []
    buffer_text = ""
    buffer_meta: list[TextSegment] = []
    char_cursor = 0

    def flush() -> None:
        nonlocal buffer_text, buffer_meta, char_cursor
        if not buffer_text.strip():
            buffer_text = ""
            buffer_meta = []
            return
        text = buffer_text.strip()
        start = char_cursor
        end = char_cursor + len(text)
        meta = _merge_meta(buffer_meta)
        chunks.append(
            Chunk(
                id=uuid.uuid4().hex,
                chunk_index=len(chunks),
                text=text,
                page=meta.page,
                line_start=meta.line_start,
                line_end=meta.line_end,
                sheet=meta.sheet,
                cell_range=meta.cell_range,
                char_start=start,
                char_end=end,
            )
        )
        if chunk_overlap > 0 and len(text) > chunk_overlap:
            overlap = text[-chunk_overlap:]
            buffer_text = overlap
            buffer_meta = buffer_meta[-1:] if buffer_meta else []
            char_cursor = end - len(overlap)
        else:
            buffer_text = ""
            buffer_meta = []
            char_cursor = end

    for text, segment in joined_parts:
        piece = text if not buffer_text else f"\n{text}"
        if len(buffer_text) + len(piece) <= chunk_size:
            buffer_text += piece
            buffer_meta.append(segment)
            continue
        if buffer_text:
            flush()
        if len(text) <= chunk_size:
            buffer_text = text
            buffer_meta = [segment]
            continue
        # Long single segment: sliding window
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            window = text[start:end]
            chunks.append(
                Chunk(
                    id=uuid.uuid4().hex,
                    chunk_index=len(chunks),
                    text=window,
                    page=segment.page,
                    line_start=segment.line_start,
                    line_end=segment.line_end,
                    sheet=segment.sheet,
                    cell_range=segment.cell_range,
                    char_start=char_cursor,
                    char_end=char_cursor + len(window),
                )
            )
            char_cursor += len(window)
            if end >= len(text):
                break
            start = max(end - chunk_overlap, start + 1)
        buffer_text = ""
        buffer_meta = []

    flush()
    return chunks


@dataclass(frozen=True)
class _Meta:
    page: int | None
    line_start: int | None
    line_end: int | None
    sheet: str | None
    cell_range: str | None


def _merge_meta(items: list[TextSegment]) -> _Meta:
    if not items:
        return _Meta(None, None, None, None, None)
    pages = {i.page for i in items if i.page is not None}
    lines = [i.line_start for i in items if i.line_start is not None] + [
        i.line_end for i in items if i.line_end is not None
    ]
    sheets = {i.sheet for i in items if i.sheet}
    cells = [i.cell_range for i in items if i.cell_range]
    return _Meta(
        page=next(iter(pages)) if len(pages) == 1 else (min(pages) if pages else None),
        line_start=min(lines) if lines else None,
        line_end=max(lines) if lines else None,
        sheet=next(iter(sheets)) if len(sheets) == 1 else None,
        cell_range=cells[0] if len(cells) == 1 else (f"{cells[0]}…{cells[-1]}" if cells else None),
    )
