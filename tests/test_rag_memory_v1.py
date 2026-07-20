"""v1 tests for provenance and local RAG retrieval evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.evaluation import evaluate_memory_retrieval, seed_service_from_corpus
from fibi.rag.service import RAGMemoryService


def make_service(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "memory.db",
            vector_dir=root / "rag",
            embedding_backend="hashing",
            embedding_dimension=256,
            similarity_threshold=0.05,
            duplicate_threshold=0.88,
        )
    )


def test_provenance_round_trip_and_context(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    memory = service.add_memory(
        "Imran is building Fibi as a tiny desktop lifeform.",
        category="project",
        source="test",
        source_id="case-001",
        source_uri="local://tests/case-001",
        source_title="Project Fibi",
        provenance={"turn_id": "turn-001", "collector": "unit-test"},
        importance=0.9,
        confidence=0.95,
    )

    reloaded = service.repository.get(memory.id)
    assert reloaded is not None
    assert reloaded.source_id == "case-001"
    assert reloaded.source_uri == "local://tests/case-001"
    assert reloaded.provenance["turn_id"] == "turn-001"

    context = service.retrieve_conversation_context("what is Fibi?")
    assert "[test:case-001]" in context.context_text
    assert "desktop lifeform" in context.context_text


def test_local_rag_eval_dataset_passes_quality_bar(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    dataset = PROJECT_ROOT / "eval" / "rag_memory"
    seeded = seed_service_from_corpus(service, dataset)
    summary = evaluate_memory_retrieval(service, dataset)

    assert seeded >= 5
    assert summary.case_count == 5
    assert summary.empty_result_count == 0
    assert summary.recall_at_k >= 0.8
    assert summary.mean_reciprocal_rank >= 0.6


