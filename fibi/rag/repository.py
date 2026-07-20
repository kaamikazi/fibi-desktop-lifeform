"""SQLite metadata repository for RAG memories."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fibi.rag.types import RAGMemory

LOGGER = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "fact",
    "event",
    "project",
    "habit",
    "belief",
    "goal",
    "important_moment",
    "conversation",
    "document",
}


class RAGMemoryRepository:
    """Owns only SQLite metadata and never touches FAISS."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL DEFAULT 'conversation',
                    source_id TEXT NOT NULL DEFAULT '',
                    source_uri TEXT NOT NULL DEFAULT '',
                    source_title TEXT NOT NULL DEFAULT '',
                    source_timestamp TEXT NOT NULL DEFAULT '',
                    importance REAL NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
                    confidence REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    provenance_json TEXT NOT NULL DEFAULT '{}',
                    deleted INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_accessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_columns(connection)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_memories_deleted ON rag_memories(deleted)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_memories_category ON rag_memories(category)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_memories_hash ON rag_memories(content_hash)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_memories_source_id ON rag_memories(source_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_memories_expires ON rag_memories(expires_at)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    document_id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    mime_type TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'indexed',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    memory_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_char INTEGER NOT NULL DEFAULT 0,
                    end_char INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES rag_documents(document_id),
                    FOREIGN KEY(memory_id) REFERENCES rag_memories(id)
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_documents_hash ON rag_documents(source_hash)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_document ON rag_document_chunks(document_id)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id INTEGER,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(memory_id) REFERENCES rag_memories(id)
                )
                """
            )

    def add(self, memory: RAGMemory) -> int:
        category = self._category(memory.category)
        content = self._clean(memory.content)
        content_hash = memory.content_hash or self.content_hash(content)
        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO rag_memories(
                    category, content, content_hash, source, source_id,
                    source_uri, source_title, source_timestamp, importance,
                    confidence, metadata_json, provenance_json, expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    content,
                    content_hash,
                    memory.source,
                    memory.source_id,
                    memory.source_uri,
                    memory.source_title,
                    memory.source_timestamp,
                    self._clamp(memory.importance),
                    self._clamp(memory.confidence),
                    json.dumps(memory.metadata),
                    json.dumps(memory.provenance),
                    memory.expires_at,
                ),
            )
            memory_id = int(cursor.lastrowid)
            self._event(
                connection,
                memory_id,
                "add",
                {
                    "source": memory.source,
                    "source_id": memory.source_id,
                    "source_uri": memory.source_uri,
                },
            )
            LOGGER.info("Added RAG memory %s", memory_id)
            return memory_id

    def update(
        self,
        memory_id: int,
        *,
        content: str | None = None,
        category: str | None = None,
        importance: float | None = None,
        confidence: float | None = None,
        metadata: dict | None = None,
        source: str | None = None,
        source_id: str | None = None,
        source_uri: str | None = None,
        source_title: str | None = None,
        source_timestamp: str | None = None,
        provenance: dict | None = None,
        expires_at: str | None = None,
    ) -> RAGMemory | None:
        existing = self.get(memory_id, include_deleted=False)
        if existing is None:
            return None
        new_content = self._clean(content if content is not None else existing.content)
        new_category = self._category(category if category is not None else existing.category)
        new_hash = self.content_hash(new_content)
        new_metadata = metadata if metadata is not None else existing.metadata
        new_provenance = provenance if provenance is not None else existing.provenance
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE rag_memories
                SET content = ?, content_hash = ?, category = ?, source = ?,
                    source_id = ?, source_uri = ?, source_title = ?,
                    source_timestamp = ?, importance = ?, confidence = ?,
                    metadata_json = ?, provenance_json = ?,
                    expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND deleted = 0
                """,
                (
                    new_content,
                    new_hash,
                    new_category,
                    source if source is not None else existing.source,
                    source_id if source_id is not None else existing.source_id,
                    source_uri if source_uri is not None else existing.source_uri,
                    source_title if source_title is not None else existing.source_title,
                    source_timestamp if source_timestamp is not None else existing.source_timestamp,
                    self._clamp(importance if importance is not None else existing.importance),
                    self._clamp(confidence if confidence is not None else existing.confidence),
                    json.dumps(new_metadata),
                    json.dumps(new_provenance),
                    expires_at if expires_at is not None else existing.expires_at,
                    memory_id,
                ),
            )
            self._event(connection, memory_id, "update", {})
        return self.get(memory_id)

    def soft_delete(self, memory_id: int) -> bool:
        with self.connection() as connection:
            cursor = connection.execute(
                "UPDATE rag_memories SET deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND deleted = 0",
                (memory_id,),
            )
            if cursor.rowcount:
                self._event(connection, memory_id, "delete", {})
        return bool(cursor.rowcount)

    def get(self, memory_id: int, include_deleted: bool = False) -> RAGMemory | None:
        clause = "" if include_deleted else "AND deleted = 0"
        with self.connection() as connection:
            row = connection.execute(f"SELECT * FROM rag_memories WHERE id = ? {clause}", (memory_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def get_by_hash(self, content_hash: str) -> RAGMemory | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM rag_memories WHERE content_hash = ? AND deleted = 0",
                (content_hash,),
            ).fetchone()
        return self._row_to_memory(row) if row else None

    def list_active(self) -> list[RAGMemory]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM rag_memories
                WHERE deleted = 0
                  AND (expires_at = '' OR datetime(expires_at) > datetime('now'))
                ORDER BY id ASC
                """
            ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def count_active(self) -> int:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count FROM rag_memories
                WHERE deleted = 0
                  AND (expires_at = '' OR datetime(expires_at) > datetime('now'))
                """
            ).fetchone()
        return int(row["count"]) if row else 0

    def get_by_source_id(self, source_id: str) -> RAGMemory | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM rag_memories WHERE source_id = ? AND deleted = 0",
                (source_id,),
            ).fetchone()
        return self._row_to_memory(row) if row else None

    def mark_accessed(self, memory_ids: list[int]) -> None:
        if not memory_ids:
            return
        placeholders = ",".join("?" for _ in memory_ids)
        with self.connection() as connection:
            connection.execute(
                f"""
                UPDATE rag_memories
                SET access_count = access_count + 1,
                    last_accessed_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                """,
                memory_ids,
            )

    def search_lexical(self, query: str, limit: int = 20) -> list[tuple[RAGMemory, float]]:
        terms = [term for term in query.lower().split() if len(term) >= 2]
        if not terms:
            return []
        memories = self.list_active()
        scored: list[tuple[RAGMemory, float]] = []
        for memory in memories:
            haystack = f"{memory.content} {memory.category} {memory.source_title}".lower()
            hits = sum(1 for term in terms if term in haystack)
            if hits:
                scored.append((memory, hits / max(1, len(terms))))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(1, limit)]

    def upsert_document(
        self,
        *,
        document_id: str,
        source_path: str,
        source_hash: str,
        mime_type: str,
        metadata: dict,
        status: str = "indexed",
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO rag_documents(document_id, source_path, source_hash, mime_type, metadata_json, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source_path = excluded.source_path,
                    source_hash = excluded.source_hash,
                    mime_type = excluded.mime_type,
                    metadata_json = excluded.metadata_json,
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (document_id, source_path, source_hash, mime_type, json.dumps(metadata), status),
            )

    def add_document_chunk(
        self,
        *,
        document_id: str,
        memory_id: int,
        chunk_index: int,
        start_char: int,
        end_char: int,
        content_hash: str,
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO rag_document_chunks(
                    document_id, memory_id, chunk_index, start_char, end_char, content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, memory_id, chunk_index, start_char, end_char, content_hash),
            )

    def expire_due_memories(self) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE rag_memories
                SET deleted = 1, updated_at = CURRENT_TIMESTAMP
                WHERE deleted = 0 AND expires_at != '' AND datetime(expires_at) <= datetime('now')
                """
            )
        return int(cursor.rowcount)

    @staticmethod
    def content_hash(content: str) -> str:
        normalized = " ".join(content.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _clean(content: str) -> str:
        cleaned = " ".join(content.strip().split())
        if not cleaned:
            raise ValueError("memory content cannot be empty")
        return cleaned

    @staticmethod
    def _category(category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in VALID_CATEGORIES:
            raise ValueError(f"invalid RAG memory category: {category}")
        return normalized

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _event(connection: sqlite3.Connection, memory_id: int, event_type: str, details: dict) -> None:
        connection.execute(
            "INSERT INTO rag_memory_events(memory_id, event_type, details_json) VALUES (?, ?, ?)",
            (memory_id, event_type, json.dumps(details)),
        )

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> RAGMemory:
        try:
            metadata = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        try:
            provenance = json.loads(row["provenance_json"])
        except (TypeError, json.JSONDecodeError):
            provenance = {}
        return RAGMemory(
            id=int(row["id"]),
            category=str(row["category"]),
            content=str(row["content"]),
            source=str(row["source"]),
            source_id=str(row["source_id"]),
            source_uri=str(row["source_uri"]),
            source_title=str(row["source_title"]),
            source_timestamp=str(row["source_timestamp"]),
            importance=float(row["importance"]),
            confidence=float(row["confidence"]),
            metadata=metadata,
            provenance=provenance,
            content_hash=str(row["content_hash"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_accessed_at=str(row["last_accessed_at"]),
            access_count=int(row["access_count"]),
            expires_at=str(row["expires_at"]),
            deleted=bool(row["deleted"]),
        )

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(rag_memories)").fetchall()}
        columns = {
            "source_id": "TEXT NOT NULL DEFAULT ''",
            "source_uri": "TEXT NOT NULL DEFAULT ''",
            "source_title": "TEXT NOT NULL DEFAULT ''",
            "source_timestamp": "TEXT NOT NULL DEFAULT ''",
            "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
            "expires_at": "TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE rag_memories ADD COLUMN {name} {definition}")
