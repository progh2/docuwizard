"""Domain models for projects and imported files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class FileStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )


@dataclass
class ProjectFile:
    id: str
    project_id: str
    original_name: str
    stored_name: str
    size: int
    status: FileStatus = FileStatus.PENDING
    error: str | None = None
    added_at: str = field(default_factory=utc_now_iso)
    content_hash: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "size": self.size,
            "status": str(self.status),
            "error": self.error,
            "added_at": self.added_at,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectFile:
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            original_name=data["original_name"],
            stored_name=data["stored_name"],
            size=int(data["size"]),
            status=FileStatus(data.get("status", FileStatus.PENDING)),
            error=data.get("error"),
            added_at=data.get("added_at", utc_now_iso()),
            content_hash=data.get("content_hash"),
        )
