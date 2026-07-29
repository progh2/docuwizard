"""Parsed document segments before chunking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextSegment:
    text: str
    page: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
