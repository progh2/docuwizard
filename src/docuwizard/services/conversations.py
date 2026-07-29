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


def list_conversations(
    project_id: str,
    *,
    query: str | None = None,
) -> list[Conversation]:
    project_service.get_project(project_id)
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM conversations
            WHERE project_id = ?
            ORDER BY is_starred DESC, updated_at DESC
            """,
            (project_id,),
        ).fetchall()
    conversations = [_row_to_conversation(row) for row in rows]
    if query:
        q = query.strip().casefold()
        conversations = [
            c
            for c in conversations
            if q in c.title.casefold() or _conversation_matches_messages(c.id, q)
        ]
    return conversations


def _conversation_matches_messages(conversation_id: str, query: str) -> bool:
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM messages
            WHERE conversation_id = ? AND lower(content) LIKE ?
            LIMIT 1
            """,
            (conversation_id, f"%{query}%"),
        ).fetchone()
    return row is not None


def set_conversation_starred(conversation_id: str, starred: bool) -> Conversation:
    with db_session() as conn:
        conn.execute(
            "UPDATE conversations SET is_starred = ? WHERE id = ?",
            (1 if starred else 0, conversation_id),
        )
    return get_conversation(conversation_id)


def toggle_conversation_star(conversation_id: str) -> Conversation:
    conversation = get_conversation(conversation_id)
    return set_conversation_starred(conversation_id, not conversation.is_starred)


def set_message_starred(message_id: str, starred: bool) -> None:
    with db_session() as conn:
        conn.execute(
            "UPDATE messages SET is_starred = ? WHERE id = ?",
            (1 if starred else 0, message_id),
        )


def toggle_message_star(message_id: str) -> bool:
    with db_session() as conn:
        row = conn.execute(
            "SELECT is_starred FROM messages WHERE id = ?",
            (message_id,),
        ).fetchone()
        if row is None:
            raise LookupError("메시지를 찾을 수 없습니다.")
        new_value = 0 if row["is_starred"] else 1
        conn.execute(
            "UPDATE messages SET is_starred = ? WHERE id = ?",
            (new_value, message_id),
        )
        return bool(new_value)


@dataclass(frozen=True)
class FavoriteMessage:
    message: Message
    conversation_id: str
    conversation_title: str


def list_starred_conversations(project_id: str) -> list[Conversation]:
    return [c for c in list_conversations(project_id) if c.is_starred]


def list_starred_messages(project_id: str) -> list[FavoriteMessage]:
    project_service.get_project(project_id)
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT m.*, c.title AS conversation_title, c.id AS conversation_id
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.project_id = ? AND m.is_starred = 1
            ORDER BY m.created_at DESC
            """,
            (project_id,),
        ).fetchall()
        favorites: list[FavoriteMessage] = []
        for row in rows:
            cite_rows = conn.execute(
                """
                SELECT chunk_id FROM message_citations
                WHERE message_id = ?
                ORDER BY rank ASC
                """,
                (row["id"],),
            ).fetchall()
            message = Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                model=row["model"],
                provider=row["provider"],
                created_at=row["created_at"],
                is_starred=True,
                citation_ids=[c["chunk_id"] for c in cite_rows],
            )
            favorites.append(
                FavoriteMessage(
                    message=message,
                    conversation_id=row["conversation_id"],
                    conversation_title=row["conversation_title"],
                )
            )
    return favorites


def get_chunks_by_ids(chunk_ids: list[str]) -> list[RetrievedChunk]:
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    with db_session() as conn:
        rows = conn.execute(
            f"""
            SELECT c.id AS chunk_id, c.project_id, c.file_id, c.text, c.page,
                   c.line_start, c.line_end, c.sheet, c.cell_range, f.original_name
            FROM chunks c
            JOIN files f ON f.id = c.file_id
            WHERE c.id IN ({placeholders})
            """,
            chunk_ids,
        ).fetchall()
    by_id = {
        row["chunk_id"]: RetrievedChunk(
            chunk_id=row["chunk_id"],
            project_id=row["project_id"],
            file_id=row["file_id"],
            text=row["text"],
            score=0.0,
            page=row["page"],
            line_start=row["line_start"],
            line_end=row["line_end"],
            sheet=row["sheet"],
            cell_range=row["cell_range"],
            original_name=row["original_name"],
        )
        for row in rows
    }
    return [by_id[cid] for cid in chunk_ids if cid in by_id]


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
