"""Composite Stage 1 query service over existing read adapters."""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict
from typing import Iterable

from fibi.memory.protocols import MemoryReadAdapter
from fibi.memory.policy import ConsentStatus, MemoryStatus, SensitivityLevel
from fibi.memory.query_models import (
    DuplicateCandidateGroup,
    MemoryListFilter,
    MemoryQueryHealth,
    MemoryQueryRequest,
    MemoryQueryResult,
    MemoryReadSource,
    MemoryRecordView,
    MemorySourceFailure,
    MemorySourceHealth,
    MemorySourceReadResult,
    MemorySourceReference,
    MemoryViewCategory,
)


class CompositeMemoryQueryService:
    """Normalize reads without selecting an authority or mutating a source."""

    def __init__(self, adapters: Iterable[MemoryReadAdapter]) -> None:
        indexed: dict[MemoryReadSource, MemoryReadAdapter] = {}
        for adapter in adapters:
            source = adapter.source
            if source in indexed:
                raise ValueError(f"duplicate memory read source: {source.value}")
            indexed[source] = adapter
        self._adapters = indexed

    @property
    def source_adapters(self) -> tuple[MemoryReadAdapter, ...]:
        return tuple(self._adapters[source] for source in sorted(self._adapters, key=lambda item: item.value))

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        adapter = self._adapters.get(reference.source)
        if adapter is None:
            return None
        try:
            record = adapter.get(reference)
        except Exception:
            return None
        return record if record is not None and _eligible_record(record) else None

    def query(self, request: MemoryQueryRequest) -> MemoryQueryResult:
        started = time.perf_counter()
        source_results = [self._safe_query(adapter, request) for adapter in self._selected(request.sources)]
        return self._combine(source_results, request.bounded_limit, request.categories, started)

    def list(self, filters: MemoryListFilter) -> MemoryQueryResult:
        started = time.perf_counter()
        source_results = [self._safe_list(adapter, filters) for adapter in self._selected(filters.sources)]
        return self._combine(source_results, filters.bounded_limit, filters.categories, started)

    def build_candidates(self, request: MemoryQueryRequest) -> MemoryQueryResult:
        """Return the same normalized candidates without provider formatting."""

        return self.query(request)

    def health(self) -> MemoryQueryHealth:
        health: list[MemorySourceHealth] = []
        for adapter in self.source_adapters:
            try:
                health.append(adapter.health())
            except Exception:
                health.append(MemorySourceHealth(adapter.source, False, error_category="health_unavailable"))
        return MemoryQueryHealth(tuple(health))

    def available_sources(self) -> tuple[MemorySourceHealth, ...]:
        return self.health().sources

    def _selected(self, requested: tuple[MemoryReadSource, ...]) -> tuple[MemoryReadAdapter, ...]:
        if not requested:
            return self.source_adapters
        return tuple(self._adapters[source] for source in requested if source in self._adapters)

    @staticmethod
    def _safe_query(adapter: MemoryReadAdapter, request: MemoryQueryRequest) -> MemorySourceReadResult:
        try:
            return adapter.query(request)
        except Exception:
            failure = MemorySourceFailure(adapter.source, "adapter_unavailable")
            return MemorySourceReadResult(adapter.source, failures=(failure,))

    @staticmethod
    def _safe_list(adapter: MemoryReadAdapter, filters: MemoryListFilter) -> MemorySourceReadResult:
        try:
            return adapter.list(filters)
        except Exception:
            failure = MemorySourceFailure(adapter.source, "adapter_unavailable")
            return MemorySourceReadResult(adapter.source, failures=(failure,))

    @staticmethod
    def _combine(
        source_results: list[MemorySourceReadResult],
        limit: int,
        categories: tuple[MemoryViewCategory, ...],
        started: float,
    ) -> MemoryQueryResult:
        records = [
            record
            for result in source_results
            for record in result.records
            if _eligible_record(record) and (not categories or record.category in categories)
        ]
        failures = tuple(failure for result in source_results for failure in result.failures)
        records.sort(key=_record_sort_key)
        duplicates = _duplicate_groups(records)
        duration_ms = (time.perf_counter() - started) * 1000.0
        return MemoryQueryResult(tuple(records[:limit]), failures, duplicates, duration_ms)


def _eligible_record(record: MemoryRecordView) -> bool:
    return (
        record.status not in {MemoryStatus.DELETED, MemoryStatus.EXPIRED}
        and record.consent_status not in {ConsentStatus.REJECTED, ConsentStatus.REVOKED}
        and record.sensitivity not in {SensitivityLevel.PROHIBITED, SensitivityLevel.RESTRICTED}
        and not (
            record.sensitivity is SensitivityLevel.SENSITIVE
            and record.consent_status is not ConsentStatus.APPROVED
        )
    )


def _record_sort_key(record: MemoryRecordView) -> tuple[float, float, str, str]:
    score = record.retrieval_score if record.retrieval_score is not None else -math.inf
    importance = record.importance if record.importance is not None else 0.0
    return (-score, -importance, record.source.value, record.source_record_id)


def _duplicate_groups(records: list[MemoryRecordView]) -> tuple[DuplicateCandidateGroup, ...]:
    grouped: dict[str, list[MemorySourceReference]] = defaultdict(list)
    for record in records:
        normalized = " ".join(record.content.casefold().split())
        if not normalized:
            continue
        fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        grouped[fingerprint].append(record.reference)
    duplicates = [
        DuplicateCandidateGroup(tuple(sorted(references, key=lambda item: (item.source.value, item.source_record_id))))
        for references in grouped.values()
        if len(references) > 1
    ]
    duplicates.sort(key=lambda group: tuple((item.source.value, item.source_record_id) for item in group.references))
    return tuple(duplicates)


__all__ = ["CompositeMemoryQueryService"]
