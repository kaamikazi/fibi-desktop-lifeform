"""Local benchmark runner for Fibi RAG memory.

Inspired by NVIDIA rag-eval's filesystem contract, this script expects:

    eval/
      corpus/*.jsonl
      train.json

It is fully local: no cloud APIs, no RAGAS judge, no NVIDIA service dependency.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.rag.config import RAGConfig
from fibi.rag.evaluation import evaluate_memory_retrieval, seed_service_from_corpus
from fibi.rag.service import RAGMemoryService


def run_benchmark(dataset_path: Path) -> dict:
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

        seed_started = time.perf_counter()
        seeded = seed_service_from_corpus(service, dataset_path)
        indexing_ms = (time.perf_counter() - seed_started) * 1000

        embedding_started = time.perf_counter()
        service.embedding_provider.embed(["Fibi local memory benchmark", "KamikazeOS project memory"])
        embedding_ms = (time.perf_counter() - embedding_started) * 1000

        retrieval_started = time.perf_counter()
        summary = evaluate_memory_retrieval(service, dataset_path)
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        health = service.health()

        return {
            "dataset_path": str(dataset_path),
            "seeded_memories": seeded,
            "recall_at_k": summary.recall_at_k,
            "mrr": summary.mean_reciprocal_rank,
            "precision_at_k": summary.mean_precision_at_k,
            "mean_latency_ms": summary.mean_latency_ms,
            "p95_latency_ms": summary.p95_latency_ms,
            "indexing_ms": indexing_ms,
            "embedding_benchmark_ms": embedding_ms,
            "retrieval_benchmark_ms": retrieval_ms,
            "false_positive_count": summary.false_positive_count,
            "empty_result_count": summary.empty_result_count,
            "failures": summary.failures,
            "health": {
                "healthy": health.healthy,
                "active_memories": health.active_memories,
                "vector_count": health.vector_count,
                "index_version": health.last_index_version,
                "warnings": health.warnings,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Fibi RAG retrieval benchmark.")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    args = parser.parse_args()

    result = run_benchmark(args.dataset)
    output = json.dumps(result, indent=2)
    print(output)
    if result["recall_at_k"] < args.min_recall:
        return 1
    if result["failures"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
