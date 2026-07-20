"""Offline RAG memory evaluation utilities.

This module follows the spirit of NVIDIA's ``rag-eval`` skill: keep a
filesystem dataset with a corpus and ``train.json``, run from local files, and
report retrieval-quality metrics. Fibi's memory eval is intentionally local and
does not require RAGAS, NVIDIA services, or a remote judge.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from pathlib import Path
from typing import Any

from fibi.rag.service import RAGMemoryService
from fibi.rag.types import RAGEvaluationCase, RAGEvaluationResult, RAGEvaluationSummary

LOGGER = logging.getLogger(__name__)

CORPUS_DIR = "corpus"
TRAIN_FILE = "train.json"


def seed_service_from_corpus(service: RAGMemoryService, dataset_path: Path) -> int:
    """Load memory records from ``corpus/*.jsonl`` into a service.

    Existing records are not deleted. Exact duplicates are handled by the
    service's normal duplicate detection.
    """

    corpus_dir = Path(dataset_path) / CORPUS_DIR
    if not corpus_dir.exists():
        raise FileNotFoundError(f"RAG eval corpus directory not found: {corpus_dir}")

    added = 0
    for corpus_file in sorted(corpus_dir.glob("*.jsonl")):
        for record in _read_jsonl(corpus_file):
            content = _required_text(record, "content", corpus_file)
            source_id = str(record.get("source_id") or record.get("doc_id") or "").strip()
            memory = service.add_memory(
                content,
                category=str(record.get("category") or "fact"),
                source=str(record.get("source") or "rag_eval_corpus"),
                source_id=source_id,
                source_uri=str(record.get("source_uri") or corpus_file.as_posix()),
                source_title=str(record.get("source_title") or corpus_file.name),
                source_timestamp=str(record.get("source_timestamp") or ""),
                importance=float(record.get("importance", 0.5)),
                confidence=float(record.get("confidence", 0.8)),
                metadata=dict(record.get("metadata") or {}),
                provenance=dict(record.get("provenance") or {"dataset_file": corpus_file.name}),
                allow_duplicate=True,
            )
            if memory.source_id == source_id:
                added += 1
    LOGGER.info("Seeded %d RAG eval memories from %s", added, corpus_dir)
    return added


def load_eval_cases(dataset_path: Path) -> list[RAGEvaluationCase]:
    """Load query cases from ``train.json``."""

    train_path = Path(dataset_path) / TRAIN_FILE
    try:
        raw_cases = json.loads(train_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"RAG eval train.json not found: {train_path}") from None
    if not isinstance(raw_cases, list):
        raise ValueError("RAG eval train.json must be a JSON array")

    cases: list[RAGEvaluationCase] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("each RAG eval case must be a JSON object")
        query = _required_text(raw, "query", train_path)
        expected = raw.get("expected_source_ids") or raw.get("expected_doc_ids")
        if not isinstance(expected, list) or not expected:
            raise ValueError(f"RAG eval case requires expected_source_ids: {query}")
        cases.append(
            RAGEvaluationCase(
                query=query,
                expected_source_ids=[str(value) for value in expected],
                top_k=int(raw.get("top_k", 3)),
                category=str(raw["category"]) if raw.get("category") else None,
            )
        )
    return cases


def evaluate_memory_retrieval(service: RAGMemoryService, dataset_path: Path) -> RAGEvaluationSummary:
    """Run top-k memory retrieval eval and return deterministic local metrics."""

    cases = load_eval_cases(dataset_path)
    results: list[RAGEvaluationResult] = []
    hit_count = 0
    reciprocal_total = 0.0
    precision_total = 0.0
    latencies: list[float] = []
    empty_count = 0
    false_positive_count = 0
    failures: list[str] = []

    for case in cases:
        started = time.perf_counter()
        search_results = service.search_memories(
            case.query,
            top_k=case.top_k,
            categories=[case.category] if case.category else None,
            similarity_threshold=0.0,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        source_ids = [result.memory.source_id for result in search_results]
        if not source_ids:
            empty_count += 1
        expected = set(case.expected_source_ids)
        hit = False
        reciprocal_rank = 0.0
        for rank, source_id in enumerate(source_ids, start=1):
            if source_id in expected:
                hit = True
                reciprocal_rank = 1.0 / rank
                break
        true_positives = sum(1 for source_id in source_ids if source_id in expected)
        false_positive_count += sum(1 for source_id in source_ids if source_id not in expected)
        precision = true_positives / max(1, len(source_ids))
        if hit:
            hit_count += 1
            reciprocal_total += reciprocal_rank
        else:
            failures.append(f"miss: {case.query} expected={case.expected_source_ids} got={source_ids}")
        precision_total += precision
        results.append(RAGEvaluationResult(case, source_ids, hit, reciprocal_rank, precision, latency_ms))

    case_count = len(cases)
    sorted_latencies = sorted(latencies)
    p95_index = min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95)) if sorted_latencies else 0
    return RAGEvaluationSummary(
        dataset_path=str(Path(dataset_path)),
        case_count=case_count,
        hit_count=hit_count,
        recall_at_k=hit_count / case_count if case_count else 0.0,
        mean_reciprocal_rank=reciprocal_total / case_count if case_count else 0.0,
        mean_precision_at_k=precision_total / case_count if case_count else 0.0,
        mean_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        p95_latency_ms=sorted_latencies[p95_index] if sorted_latencies else 0.0,
        empty_result_count=empty_count,
        false_positive_count=false_positive_count,
        failures=failures,
        results=results,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        records.append(record)
    return records


def _required_text(record: dict[str, Any], key: str, source: Path) -> str:
    value = str(record.get(key) or "").strip()
    if not value:
        raise ValueError(f"{source} is missing required text field: {key}")
    return value
