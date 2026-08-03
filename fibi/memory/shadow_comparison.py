"""Development-only, content-free Stage 1 memory comparison metrics."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass

from fibi.memory.protocols import MemoryReadAdapter
from fibi.memory.query_models import MemoryQueryRequest, MemoryReadSource, MemorySourceReadResult
from fibi.memory.query_service import CompositeMemoryQueryService


@dataclass(frozen=True, slots=True)
class MemoryShadowSettings:
    enabled: bool = False
    max_results: int = 20


@dataclass(frozen=True, slots=True)
class MemoryShadowMetrics:
    executed: bool
    source_candidate_counts: tuple[tuple[str, int], ...] = ()
    normalized_candidate_count: int = 0
    category_counts: tuple[tuple[str, int], ...] = ()
    duplicate_candidate_count: int = 0
    missing_consent_count: int = 0
    ranking_agreement: float | None = None
    failure_counts: tuple[tuple[str, int], ...] = ()
    duration_ms: float = 0.0


class MemoryShadowComparison:
    """Compare query-only source views only when explicitly enabled."""

    def __init__(
        self,
        adapters: tuple[MemoryReadAdapter, ...],
        query_service: CompositeMemoryQueryService,
        settings: MemoryShadowSettings | None = None,
    ) -> None:
        self._adapters = adapters
        self._query_service = query_service
        self.settings = settings or MemoryShadowSettings()

    def compare(self, request: MemoryQueryRequest) -> MemoryShadowMetrics:
        if not self.settings.enabled:
            return MemoryShadowMetrics(False)
        started = time.perf_counter()
        bounded = MemoryQueryRequest(
            request.query,
            limit=min(request.bounded_limit, max(1, self.settings.max_results)),
            sources=request.sources,
            categories=request.categories,
        )
        source_results = [adapter.query(bounded) for adapter in self._adapters]
        normalized = self._query_service.query(bounded)
        source_counts = tuple(sorted((result.source.value, len(result.records)) for result in source_results))
        all_records = [record for result in source_results for record in result.records]
        categories = tuple(sorted(Counter(record.category.value for record in normalized.records).items()))
        failures = tuple(
            sorted(Counter(failure.error_category for result in source_results for failure in result.failures).items())
        )
        return MemoryShadowMetrics(
            executed=True,
            source_candidate_counts=source_counts,
            normalized_candidate_count=len(normalized.records),
            category_counts=categories,
            duplicate_candidate_count=len(normalized.duplicate_candidates),
            missing_consent_count=sum(record.consent_status is None for record in all_records),
            ranking_agreement=_ranking_agreement(source_results),
            failure_counts=failures,
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )


def _ranking_agreement(source_results: list[MemorySourceReadResult]) -> float | None:
    by_source = {result.source: result.records for result in source_results}
    legacy = by_source.get(MemoryReadSource.LEGACY, ())
    rag = by_source.get(MemoryReadSource.RAG, ())
    if not legacy or not rag:
        return None
    left = [" ".join(item.content.casefold().split()) for item in legacy]
    right = [" ".join(item.content.casefold().split()) for item in rag]
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    differences = sum(abs(left.index(value) - right.index(value)) for value in shared)
    denominator = max(1, len(shared) * max(len(left), len(right)))
    return max(0.0, 1.0 - differences / denominator)


__all__ = ["MemoryShadowComparison", "MemoryShadowMetrics", "MemoryShadowSettings"]
