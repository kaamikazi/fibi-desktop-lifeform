"""Smoke test for next-generation local RAG architecture."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.benchmark import run_benchmark
from fibi.rag.config import RAGConfig
from fibi.rag.ingestion import DocumentIngestionService
from fibi.rag.service import RAGMemoryService


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        service = RAGMemoryService(
            RAGConfig(
                database_path=root / "memory.db",
                vector_dir=root / "rag",
                embedding_backend="hashing",
                embedding_dimension=128,
                similarity_threshold=0.01,
                chunk_size_chars=140,
                chunk_overlap_chars=20,
            )
        )
        document = root / "fibi_notes.txt"
        document.write_text("Fibi is a local desktop lifeform.\nShe remembers privacy boundaries.", encoding="utf-8")
        ingestion = DocumentIngestionService(service)
        result = ingestion.ingest_file(document)
        assert result.indexed_count >= 1

        found = service.search_memories("desktop lifeform privacy", top_k=3)
        assert found
        assert service.health().healthy
        assert service.health().cache_entries >= 1

    benchmark = run_benchmark(PROJECT_ROOT / "eval")
    assert benchmark["recall_at_k"] >= 0.8, json.dumps(benchmark, indent=2)
    assert benchmark["health"]["healthy"], json.dumps(benchmark, indent=2)
    print("Fibi v0.21 next-gen RAG smoke tests passed.")


if __name__ == "__main__":
    run()


