"""Smoke test for Fibi v1 local RAG memory behavior."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.evaluation import evaluate_memory_retrieval, seed_service_from_corpus
from fibi.rag.service import RAGMemoryService


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        service = RAGMemoryService(
            RAGConfig(
                database_path=root / "fibi_memory.db",
                vector_dir=root / "rag",
                embedding_backend="hashing",
                embedding_dimension=256,
                similarity_threshold=0.05,
                duplicate_threshold=0.88,
                default_top_k=3,
            )
        )

        dataset = PROJECT_ROOT / "eval" / "rag_memory"
        seeded = seed_service_from_corpus(service, dataset)
        assert seeded >= 5

        results = service.retrieve_top_k("Fibi local memory privacy", top_k=3)
        assert results
        assert any(result.memory.source_id == "mem-goal-local-first" for result in results)
        assert all(result.memory.source_id for result in results)

        context = service.retrieve_conversation_context("Project Lantern", top_k=5)
        assert "mem-project-lantern" in context.context_text

        summary = evaluate_memory_retrieval(service, dataset)
        assert summary.recall_at_k >= 0.8
        assert summary.mean_reciprocal_rank >= 0.6

    print("Fibi v0.19/v1 RAG memory smoke tests passed.")


if __name__ == "__main__":
    run()


