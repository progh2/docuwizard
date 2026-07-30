"""SQLite connection and schema migrations (issue #8)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from docuwizard.paths import db_path, ensure_app_dirs

SCHEMA_VERSION = 3

MIGRATIONS: dict[int, str] = {
    1: """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        size INTEGER NOT NULL,
        status TEXT NOT NULL,
        error TEXT,
        added_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id);

    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        file_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        page INTEGER,
        line_start INTEGER,
        line_end INTEGER,
        sheet TEXT,
        cell_range TEXT,
        char_start INTEGER,
        char_end INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
    CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_starred INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        model TEXT,
        provider TEXT,
        created_at TEXT NOT NULL,
        is_starred INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS message_citations (
        message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
        chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
        rank INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (message_id, chunk_id)
    );

    CREATE TABLE IF NOT EXISTS essentials_reports (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        model TEXT,
        provider TEXT,
        is_starred INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS essentials_items (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL REFERENCES essentials_reports(id) ON DELETE CASCADE,
        category TEXT NOT NULL,
        summary TEXT NOT NULL,
        is_starred INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS essentials_item_citations (
        item_id TEXT NOT NULL REFERENCES essentials_items(id) ON DELETE CASCADE,
        chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
        PRIMARY KEY (item_id, chunk_id)
    );
    """,
    2: """
    CREATE TABLE IF NOT EXISTS embeddings (
        chunk_id TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        vector BLOB NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
    """,
    # FTS5 keyword index over chunk text; the trigram tokenizer handles Korean
    # substring matching (particles attached to words) without a morpheme
    # analyzer. Kept in sync with the chunks table via triggers.
    3: """
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        text, tokenize='trigram'
    );
    INSERT INTO chunks_fts(rowid, text) SELECT rowid, text FROM chunks;

    CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_insert
    AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text);
    END;

    CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_delete
    AFTER DELETE ON chunks BEGIN
        DELETE FROM chunks_fts WHERE rowid = old.rowid;
    END;

    CREATE TRIGGER IF NOT EXISTS trg_chunks_fts_update
    AFTER UPDATE OF text ON chunks BEGIN
        DELETE FROM chunks_fts WHERE rowid = old.rowid;
        INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text);
    END;
    """,
}


def connect(path: Path | None = None) -> sqlite3.Connection:
    ensure_app_dirs()
    db = path or db_path()
    conn = sqlite3.connect(str(db), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path | None = None) -> None:
    """Apply pending migrations."""
    with connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        current = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]
        for version in sorted(MIGRATIONS):
            if version <= current:
                continue
            conn.executescript(MIGRATIONS[version])
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
        conn.commit()


@contextmanager
def db_session(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
