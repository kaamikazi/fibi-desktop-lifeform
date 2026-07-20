"""Unit tests for Fibi's local RAG memory system."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService


def make_service(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "memory.db",
            vector_dir=root / "rag",
            embedding_backend="hashing",
            embedding_dimension=128,
            similarity_threshold=0.08,
            duplicate_threshold=0.88,
        )
    )


def test_rag_memory_lifecycle(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    first = service.add_memory("Imran is building Project Fibi.", category="project", importance=0.8)
    assert first.id is not None

    duplicate = service.add_memory("Imran is building Project Fibi.", category="project")
    assert duplicate.id == first.id

    results = service.search_memories("Fibi project", top_k=3)
    assert results
    assert results[0].memory.id == first.id
    assert results[0].score >= results[0].similarity * 0.5

    updated = service.update_memory(first.id, content="Imran is building Fibi as a desktop lifeform.", category="project")
    assert updated is not None
    assert "lifeform" in updated.content

    context = service.retrieve_conversation_context("what do you remember about Fibi?", top_k=2)
    assert "lifeform" in context.context_text

    assert service.delete_memory(first.id)
    assert not service.search_memories("Fibi lifeform", top_k=3)


def test_rag_persistence(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    memory = service.add_memory("The user likes sleepy tiny replies.", category="habit")
    assert memory.id is not None

    reloaded = make_service(tmp_path)
    results = reloaded.retrieve_top_k("sleepy replies", top_k=1)
    assert results
    assert results[0].memory.id == memory.id


def test_similarity_threshold(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    service.add_memory("KamikazeOS is a project name.", category="project")
    permissive = service.search_memories("KamikazeOS", top_k=1, similarity_threshold=0.01)
    strict = service.search_memories("horses and land", top_k=1, similarity_threshold=0.99)
    assert permissive
    assert strict == []


