"""Conversation and message persistence (issue #19)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from docuwizard.db import db_session
from docuwizard.models import utc_now_iso
from docuwizard.rag.vectors import RetrievedChunk
from docuwizard.services import projects as project_service


@dataclass
class Conversation:
    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    is_starred: bool = False


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    model: str | None = None
    provider: str | None = None
    created_at: str = ""
    is_starred: bool = False
    citation_ids: list[str] | None = None


def create_conversation(project_id: str, title: str = "새 대화") -> Conversation:
    project_service.get_project(project_id)
    now = utc_now_iso()
    conversation = Conversation(
        id=uuid.uuid4().hex,
        project_id=project_id,
        title=title.strip() or "새 대화",
        created_at=now,
        updated_at=now,
    )
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO conversations(id, project_id, title, created_at, updated_at, is_starred)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (
                conversation.id,
                conversation.project_id,
                conversation.title,
                conversation.created_at,
                conversation.updated_at,
            ),
        )
    return conversation


def list_conversations(project_id: str) -> list[Conversation]:
    project_service.get_project(project_id)
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conversations
            WHERE project_id = ?
            ORDER BY updated_at DESC
            """,
            (project_id,),
        ).fetchall()
    return [_row_to_conversation(row) for row in rows]


def get_conversation(conversation_id: str) -> Conversation:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    if row is None:
        raise LookupError("대화를 찾을 수 없습니다.")
    return _row_to_conversation(row)


def rename_conversation(conversation_id: str, title: str) -> Conversation:
    cleaned = title.strip() or "새 대화"
    with db_session() as conn:
        conn.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (cleaned, utc_now_iso(), conversation_id),
        )
    return get_conversation(conversation_id)


def delete_conversation(conversation_id: str) -> None:
    with db_session() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def list_messages(conversation_id: str) -> list[Message]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        messages: list[Message] = []
        for row in rows:
            cite_rows = conn.execute(
                """
                SELECT chunk_id FROM message_citations
                WHERE message_id = ?
                ORDER BY rank ASC
                """,
                (row["id"],),
            ).fetchall()
            messages.append(
                Message(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    model=row["model"],
                    provider=row["provider"],
                    created_at=row["created_at"],
                    is_starred=bool(row["is_starred"]),
                    citation_ids=[c["chunk_id"] for c in cite_rows],
                )
            )
    return messages


def add_message(
    conversation_id: str,
    *,
    role: str,
    content: str,
    model: str | None = None,
    provider: str | None = None,
    citations: list[RetrievedChunk] | None = None,
    db: Path | None = None,
) -> Message:
    message_id = uuid.uuid4().hex
    now = utc_now_iso()
    with db_session(db) as conn:
        conn.execute(
            """
            INSERT INTO messages(
                id, conversation_id, role, content, model, provider, created_at, is_starred
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (message_id, conversation_id, role, content, model, provider, now),
        )
        if citations:
            conn.executemany(
                """
                INSERT OR IGNORE INTO message_citations(message_id, chunk_id, rank)
                VALUES (?, ?, ?)
                """,
                [
                    (message_id, chunk.chunk_id, rank)
                    for rank, chunk in enumerate(citations, start=1)
                ],
            )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
    return Message(
        id=message_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
        provider=provider,
        created_at=now,
        citation_ids=[c.chunk_id for c in citations] if citations else [],
    )


def _row_to_conversation(row) -> Conversation:
    return Conversation(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        is_starred=bool(row["is_starred"]),
    )
