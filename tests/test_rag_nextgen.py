"""Next-generation local RAG architecture tests."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.ingestion import BackgroundIndexingQueue, DocumentIngestionService
from fibi.rag.service import RAGMemoryService


def make_service(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "memory.db",
            vector_dir=root / "rag",
            embedding_backend="hashing",
            embedding_dimension=128,
            similarity_threshold=0.01,
            duplicate_threshold=0.9,
            retrieval_cache_ttl_seconds=60,
            chunk_size_chars=120,
            chunk_overlap_chars=20,
        )
    )


def test_incremental_index_health_and_cache(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    first_version = service.health().last_index_version

    service.add_memory("Fibi remembers local privacy boundaries.", source_id="privacy")
    health = service.health()
    assert health.healthy
    assert health.active_memories == 1
    assert health.vector_count == 1
    assert health.last_index_version > first_version

    results = service.search_memories("privacy boundary", top_k=1)
    assert results
    assert service.health().cache_entries == 1
    cached = service.search_memories("privacy boundary", top_k=1)
    assert cached[0].memory.id == results[0].memory.id


def test_hybrid_search_finds_keyword_match(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.add_memory("Project Lantern is a synthetic operating system project.", category="project", source_id="lantern")

    results = service.search_memories("operating system project", top_k=1, categories=["project"])
    assert results
    assert results[0].memory.source_id == "lantern"


def test_document_ingestion_and_background_queue(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    document = tmp_path / "notes.md"
    document.write_text("Fibi document memory.\n\nProject Lantern notes live here.\nPrivacy stays local.", encoding="utf-8")

    ingestion = DocumentIngestionService(service)
    result = ingestion.ingest_file(document)
    assert result.chunk_count >= 1
    assert result.indexed_count == result.chunk_count

    results = service.search_memories("Project Lantern notes", top_k=3, categories=["document"])
    assert results
    assert results[0].memory.source == "document"

    queued_doc = tmp_path / "queued.txt"
    queued_doc.write_text("Queued indexing keeps Fibi responsive.", encoding="utf-8")
    queue = BackgroundIndexingQueue(ingestion)
    queue.enqueue(queued_doc)
    queue.stop()
    assert any(item.source_path.endswith("queued.txt") for item in queue.results)


def test_memory_expiration_policy(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    expired_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    service.add_memory("Temporary memory should expire.", source_id="expired", expires_at=expired_at)

    expired = service.expire_memories()
    assert expired == 1
    assert not service.search_memories("temporary memory", top_k=3, similarity_threshold=0.0)


def test_migration_adds_nextgen_columns(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE rag_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL DEFAULT 'conversation',
                importance REAL NOT NULL DEFAULT 0.5,
                confidence REAL NOT NULL DEFAULT 0.5,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                deleted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    RAGMemoryService(
        RAGConfig(
            database_path=database,
            vector_dir=tmp_path / "rag",
            embedding_backend="hashing",
            embedding_dimension=128,
        )
    )
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(rag_memories)").fetchall()}
    assert {"source_id", "source_uri", "source_title", "source_timestamp", "provenance_json", "expires_at"} <= columns


