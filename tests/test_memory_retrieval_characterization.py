"""Synthetic characterization of current memory retrieval guarantees."""

from __future__ import annotations

from pathlib import Path

from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService


def _service(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "memory.db",
            vector_dir=root / "rag",
            embedding_backend="hashing",
            embedding_dimension=192,
            similarity_threshold=0.12,
            duplicate_threshold=0.88,
        )
    )


def test_exact_fact_preference_and_project_recall(tmp_path: Path) -> None:
    service = _service(tmp_path)
    fact = service.add_memory("The user's display name is Rowan.", category="user_fact", source_id="fact-name")
    preference = service.add_memory("The user prefers keyboard navigation.", category="preference", source_id="pref-input")
    project = service.add_memory("The user is building Project Lantern.", category="project", source_id="project-lantern")

    assert service.search_memories("display name Rowan", top_k=1)[0].memory.id == fact.id
    assert service.search_memories("keyboard navigation preference", top_k=1)[0].memory.id == preference.id
    assert service.search_memories("Project Lantern", top_k=1)[0].memory.id == project.id


def test_structured_contradiction_updates_in_place_and_exact_duplicate_is_stable(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.add_memory(
        "The user's preferred editor is Cedar.",
        category="preference",
        memory_key="preference:editor",
    )
    duplicate = service.add_memory(
        "The user's preferred editor is Cedar.",
        category="preference",
        memory_key="preference:editor",
    )
    newer = service.add_memory(
        "The user's preferred editor is Birch.",
        category="preference",
        memory_key="preference:editor",
    )
    assert first.id == duplicate.id == newer.id
    assert service.repository.count_active() == 1
    assert "Birch" in newer.content


def test_irrelevant_and_deleted_memory_are_excluded(tmp_path: Path) -> None:
    service = _service(tmp_path)
    memory = service.add_memory("Project Lantern uses a local SQLite store.", category="project")
    assert service.search_memories("astronomy telescope", top_k=3, similarity_threshold=0.8) == []
    assert service.delete_memory(int(memory.id))
    assert service.search_memories("Project Lantern SQLite", top_k=3, similarity_threshold=0.0) == []


def test_storage_is_provider_independent(tmp_path: Path) -> None:
    service = _service(tmp_path)
    saved = service.add_memory("The user prefers local model independence.", category="preference")
    module_names = {
        service.__class__.__module__,
        service.repository.__class__.__module__,
        service.embedding_provider.__class__.__module__,
    }
    assert all("provider" not in name for name in module_names)
    assert service.repository.get(int(saved.id)) is not None
