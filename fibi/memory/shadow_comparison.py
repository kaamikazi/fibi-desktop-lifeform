"""Explicit, content-free comparison over Stage 1 memory read views."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import secrets
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol, TypeVar

from fibi.memory.comparison_models import (
    COMPARISON_SCHEMA_VERSION,
    MemoryComparisonError,
    MemoryComparisonFinding,
    MemoryComparisonMetrics,
    MemoryComparisonMode,
    MemoryComparisonReport,
    MemoryComparisonRequest,
    MemoryExclusionMetrics,
    MemoryMetadataCompleteness,
    MemorySourceResult,
)
from fibi.memory.protocols import MemoryReadAdapter
from fibi.memory.query_models import (
    MemoryQueryRequest,
    MemoryQueryResult,
    MemoryReadSource,
    MemoryRecordView,
    MemorySourceReadResult,
    MemoryViewCategory,
)
from fibi.memory.query_service import CompositeMemoryQueryService

T = TypeVar("T")


class ComparisonQueryService(Protocol):
    def query(self, request: MemoryQueryRequest) -> MemoryQueryResult: ...


@dataclass(frozen=True, slots=True)
class _SourceSnapshot:
    source: MemoryReadSource
    records: tuple[MemoryRecordView, ...]
    public: MemorySourceResult


class MemoryComparisonService:
    """Run one bounded diagnostic only after explicit enablement."""

    def __init__(
        self,
        adapters: tuple[MemoryReadAdapter, ...],
        query_service: ComparisonQueryService,
        *,
        enabled: bool = False,
        salt_factory: Callable[[int], bytes] = secrets.token_bytes,
    ) -> None:
        self._adapters = {adapter.source: adapter for adapter in adapters}
        self._query_service = query_service
        self.enabled = bool(enabled)
        self._salt_factory = salt_factory

    def compare(self, request: MemoryComparisonRequest) -> MemoryComparisonReport:
        enabled_sources = tuple(source.value for source in self._selected_sources(request.sources))
        if not self.enabled:
            return self._not_executed(request, enabled_sources, "comparison_disabled")
        if request.mode is MemoryComparisonMode.LOCAL_DATA:
            category = (
                "local_data_mode_not_implemented"
                if request.local_data_approved
                else "local_data_confirmation_required"
            )
            return self._not_executed(request, enabled_sources, category)

        started = time.perf_counter()
        query = MemoryQueryRequest(
            request.query,
            limit=request.bounded_limit,
            sources=request.sources,
            categories=request.categories,
        )
        snapshots = tuple(
            self._read_source(self._adapters[source], query, request.bounded_timeout_seconds)
            for source in self._selected_sources(request.sources)
        )
        normalized, normalized_elapsed, normalized_timeout = _run_bounded(
            lambda: self._query_service.query(query),
            request.bounded_timeout_seconds,
        )
        errors = [
            MemoryComparisonError(category, snapshot.source.value, snapshot.public.timed_out)
            for snapshot in snapshots
            for category in snapshot.public.failure_categories
        ]
        normalized_records: tuple[MemoryRecordView, ...] = ()
        normalized_failures: tuple[str, ...] = ()
        if normalized_timeout:
            errors.append(MemoryComparisonError("normalized_timeout", "normalized", True))
        elif isinstance(normalized, MemoryQueryResult):
            normalized_records = normalized.records
            normalized_failures = tuple(sorted({failure.error_category for failure in normalized.failures}))
            errors.extend(MemoryComparisonError(category, "normalized") for category in normalized_failures)
        elif normalized is None:
            errors.append(MemoryComparisonError("normalized_unavailable", "normalized"))

        metrics = self._metrics(
            snapshots,
            normalized_records,
            request.bounded_limit,
            normalized_elapsed,
            normalized_timeout,
            (time.perf_counter() - started) * 1000.0,
        )
        unavailable = any(not snapshot.public.available for snapshot in snapshots)
        finding = _finding(snapshots, metrics, errors)
        comparison_id = (
            f"synthetic-{request.query_identifier}"
            if request.mode is MemoryComparisonMode.SYNTHETIC
            else f"local-{secrets.token_hex(8)}"
        )
        return MemoryComparisonReport(
            schema_version=COMPARISON_SCHEMA_VERSION,
            comparison_id=comparison_id,
            mode=request.mode.value,
            synthetic=request.mode is MemoryComparisonMode.SYNTHETIC,
            executed=True,
            enabled_sources=enabled_sources,
            sources=tuple(snapshot.public for snapshot in snapshots),
            metrics=metrics,
            errors=tuple(errors),
            source_unavailable=unavailable,
            finding=finding.value,
        )

    def _read_source(
        self,
        adapter: MemoryReadAdapter,
        request: MemoryQueryRequest,
        timeout_seconds: float,
    ) -> _SourceSnapshot:
        operation = lambda: (adapter.query(request), adapter.health())
        result, latency_ms, timed_out = _run_bounded(operation, timeout_seconds)
        if timed_out:
            public = MemorySourceResult(
                source=adapter.source.value,
                available=False,
                healthy=False,
                result_count=0,
                failure_categories=("source_timeout",),
                latency_ms=latency_ms,
                timed_out=True,
            )
            return _SourceSnapshot(adapter.source, (), public)
        if result is None:
            public = MemorySourceResult(
                source=adapter.source.value,
                available=False,
                healthy=False,
                result_count=0,
                failure_categories=("source_read_error",),
                latency_ms=latency_ms,
            )
            return _SourceSnapshot(adapter.source, (), public)

        read_result, health = result
        records = read_result.records
        exclusions = _comparison_exclusions(adapter, request)
        failure_categories = {failure.error_category for failure in read_result.failures}
        if health.error_category:
            failure_categories.add(health.error_category)
        failures = tuple(sorted(failure_categories))
        public = MemorySourceResult(
            source=adapter.source.value,
            available=health.available,
            healthy=health.available and not failures,
            result_count=len(records),
            category_counts=_counts(record.category.value for record in records),
            unknown_category_count=sum(
                record.category is MemoryViewCategory.UNKNOWN_LEGACY for record in records
            ),
            consent_counts=_counts(
                record.consent_status.value if record.consent_status is not None else "missing"
                for record in records
            ),
            sensitivity_counts=_counts(
                record.sensitivity.value if record.sensitivity is not None else "missing"
                for record in records
            ),
            metadata=_metadata_completeness(records),
            exclusions=exclusions,
            failure_categories=failures,
            latency_ms=latency_ms,
            semantic_index_available=health.semantic_index_available,
            semantic_acceleration_available=health.semantic_acceleration_available,
            semantic_backend=health.semantic_backend,
            irrelevant_candidate_count=_irrelevant_count(records),
        )
        return _SourceSnapshot(adapter.source, records, public)

    def _metrics(
        self,
        snapshots: tuple[_SourceSnapshot, ...],
        normalized: tuple[MemoryRecordView, ...],
        limit: int,
        normalized_latency_ms: float,
        normalized_timeout: bool,
        total_latency_ms: float,
    ) -> MemoryComparisonMetrics:
        salt = self._salt_factory(32)
        by_source = {snapshot.source: snapshot.records[:limit] for snapshot in snapshots}
        legacy = by_source.get(MemoryReadSource.LEGACY, ())
        rag = by_source.get(MemoryReadSource.RAG, ())
        legacy_fingerprints = _fingerprints(legacy, salt)
        rag_fingerprints = _fingerprints(rag, salt)
        normalized_fingerprints = _fingerprints(normalized[:limit], salt)
        legacy_set = set(legacy_fingerprints)
        rag_set = set(rag_fingerprints)
        union = legacy_set | rag_set
        overlap = legacy_set & rag_set
        normalized_set = set(normalized_fingerprints)
        return MemoryComparisonMetrics(
            overlap_at_k=len(overlap),
            jaccard_overlap=len(overlap) / len(union) if union else 1.0,
            normalized_retention_rate=len(normalized_set & union) / len(union) if union else 1.0,
            legacy_exclusive_candidates=len(legacy_set - rag_set),
            rag_exclusive_candidates=len(rag_set - legacy_set),
            rank_agreement=_rank_agreement(legacy_fingerprints, rag_fingerprints),
            reciprocal_rank_agreement=_reciprocal_rank_agreement(legacy_fingerprints, rag_fingerprints),
            top_result_agreement=(legacy_fingerprints[0] == rag_fingerprints[0]) if legacy and rag else None,
            deterministic_tie_ordering=_deterministic_ties(normalized),
            exact_duplicate_pairs=_exact_duplicate_pairs(tuple(legacy) + tuple(rag), salt),
            likely_paraphrase_pairs=_likely_paraphrase_pairs(legacy, rag, salt),
            possible_contradiction_pairs=_possible_contradiction_pairs(legacy, rag, salt),
            cross_source_duplicate_pairs=len(overlap),
            normalized_candidate_count=len(normalized),
            normalized_latency_ms=normalized_latency_ms,
            total_latency_ms=total_latency_ms,
            timeout_count=sum(snapshot.public.timed_out for snapshot in snapshots) + int(normalized_timeout),
        )

    def _selected_sources(self, requested: tuple[MemoryReadSource, ...]) -> tuple[MemoryReadSource, ...]:
        selected = requested or tuple(sorted(self._adapters, key=lambda source: source.value))
        return tuple(source for source in selected if source in self._adapters)

    @staticmethod
    def _not_executed(
        request: MemoryComparisonRequest,
        enabled_sources: tuple[str, ...],
        category: str,
    ) -> MemoryComparisonReport:
        return MemoryComparisonReport(
            schema_version=COMPARISON_SCHEMA_VERSION,
            comparison_id=f"not-executed-{request.query_identifier}",
            mode=request.mode.value,
            synthetic=request.mode is MemoryComparisonMode.SYNTHETIC,
            executed=False,
            enabled_sources=enabled_sources,
            sources=(),
            metrics=MemoryComparisonMetrics(),
            errors=(MemoryComparisonError(category),),
            finding=MemoryComparisonFinding.NOT_EXECUTED.value,
        )


def _run_bounded(operation: Callable[[], T], timeout_seconds: float) -> tuple[T | None, float, bool]:
    started = time.perf_counter()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fibi-memory-compare")
    future = executor.submit(operation)
    timed_out = False
    try:
        result = future.result(timeout=timeout_seconds)
    except FutureTimeoutError:
        timed_out = True
        future.cancel()
        result = None
    except Exception:
        result = None
    finally:
        executor.shutdown(wait=not timed_out, cancel_futures=True)
    return result, (time.perf_counter() - started) * 1000.0, timed_out


def _comparison_exclusions(adapter: MemoryReadAdapter, request: MemoryQueryRequest) -> MemoryExclusionMetrics:
    provider = getattr(adapter, "comparison_exclusions", None)
    if not callable(provider):
        return MemoryExclusionMetrics()
    try:
        exclusions = provider(request)
    except Exception:
        return MemoryExclusionMetrics()
    return exclusions if isinstance(exclusions, MemoryExclusionMetrics) else MemoryExclusionMetrics()


def _metadata_completeness(records: tuple[MemoryRecordView, ...]) -> MemoryMetadataCompleteness:
    return MemoryMetadataCompleteness(
        missing_consent=sum(record.consent_status is None for record in records),
        missing_sensitivity=sum(record.sensitivity is None for record in records),
        missing_timestamps=sum(not record.created_at or not record.updated_at for record in records),
        missing_provenance=sum(not record.provenance for record in records),
        missing_importance=sum(record.importance is None for record in records),
        missing_confidence=sum(record.confidence is None for record in records),
    )


def _counts(values: Iterable[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


def _normalize_content(content: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", content.casefold()))


def _fingerprint(content: str, salt: bytes) -> bytes:
    return hmac.new(salt, _normalize_content(content).encode("utf-8"), hashlib.sha256).digest()


def _fingerprints(records: tuple[MemoryRecordView, ...], salt: bytes) -> tuple[bytes, ...]:
    return tuple(_fingerprint(record.content, salt) for record in records)


def _rank_agreement(left: tuple[bytes, ...], right: tuple[bytes, ...]) -> float | None:
    shared = set(left) & set(right)
    if not shared:
        return None
    denominator = max(1, len(shared) * max(len(left), len(right)) - len(shared))
    difference = sum(abs(left.index(value) - right.index(value)) for value in shared)
    return max(0.0, 1.0 - difference / denominator)


def _reciprocal_rank_agreement(left: tuple[bytes, ...], right: tuple[bytes, ...]) -> float | None:
    shared = set(left) & set(right)
    if not shared:
        return None
    return sum(1.0 / (1.0 + abs(left.index(value) - right.index(value))) for value in shared) / len(shared)


def _exact_duplicate_pairs(records: tuple[MemoryRecordView, ...], salt: bytes) -> int:
    counts = Counter(_fingerprints(records, salt))
    return sum(math.comb(count, 2) for count in counts.values() if count > 1)


def _likely_paraphrase_pairs(
    legacy: tuple[MemoryRecordView, ...],
    rag: tuple[MemoryRecordView, ...],
    salt: bytes,
) -> int:
    count = 0
    for left in legacy:
        for right in rag:
            if _fingerprint(left.content, salt) == _fingerprint(right.content, salt):
                continue
            left_terms = set(_normalize_content(left.content).split())
            right_terms = set(_normalize_content(right.content).split())
            union = left_terms | right_terms
            similarity = len(left_terms & right_terms) / len(union) if union else 0.0
            count += int(similarity >= 0.6)
    return count


def _possible_contradiction_pairs(
    legacy: tuple[MemoryRecordView, ...],
    rag: tuple[MemoryRecordView, ...],
    salt: bytes,
) -> int:
    count = 0
    for left in legacy:
        left_group = left.provenance.get("synthetic_contradiction_group")
        if not isinstance(left_group, str) or not left_group:
            continue
        for right in rag:
            if right.provenance.get("synthetic_contradiction_group") != left_group:
                continue
            count += int(_fingerprint(left.content, salt) != _fingerprint(right.content, salt))
    return count


def _deterministic_ties(records: tuple[MemoryRecordView, ...]) -> bool:
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if (
                left.retrieval_score != right.retrieval_score
                or left.importance != right.importance
            ):
                continue
            left_key = (left.source.value, left.source_record_id)
            right_key = (right.source.value, right.source_record_id)
            if left_key > right_key:
                return False
    return True


def _irrelevant_count(records: tuple[MemoryRecordView, ...]) -> int | None:
    labels = [record.provenance.get("synthetic_relevant") for record in records]
    if not any(isinstance(value, bool) for value in labels):
        return None
    return sum(value is False for value in labels)


def _finding(
    snapshots: tuple[_SourceSnapshot, ...],
    metrics: MemoryComparisonMetrics,
    errors: list[MemoryComparisonError],
) -> MemoryComparisonFinding:
    if any(snapshot.public.timed_out or not snapshot.public.available for snapshot in snapshots):
        return MemoryComparisonFinding.MIGRATION_BLOCKER
    if errors or metrics.normalized_retention_rate < 1.0 or metrics.possible_contradiction_pairs:
        return MemoryComparisonFinding.NEEDS_INVESTIGATION
    if any(
        snapshot.public.metadata.missing_consent
        or snapshot.public.metadata.missing_sensitivity
        or snapshot.public.metadata.missing_provenance
        for snapshot in snapshots
    ):
        return MemoryComparisonFinding.NEEDS_INVESTIGATION
    return MemoryComparisonFinding.HEALTHY


# Stage 1 compatibility facade. It remains explicit and is never runtime-owned.
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
    """Compatibility wrapper retained for Stage 1 callers and tests."""

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
        categories = _counts(record.category.value for record in normalized.records)
        failures = _counts(
            failure.error_category for result in source_results for failure in result.failures
        )
        salt = secrets.token_bytes(32)
        by_source = {result.source: result.records for result in source_results}
        rank_agreement = _rank_agreement(
            _fingerprints(by_source.get(MemoryReadSource.LEGACY, ()), salt),
            _fingerprints(by_source.get(MemoryReadSource.RAG, ()), salt),
        )
        return MemoryShadowMetrics(
            executed=True,
            source_candidate_counts=source_counts,
            normalized_candidate_count=len(normalized.records),
            category_counts=categories,
            duplicate_candidate_count=len(normalized.duplicate_candidates),
            missing_consent_count=sum(record.consent_status is None for record in all_records),
            ranking_agreement=rank_agreement,
            failure_counts=failures,
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )


__all__ = [
    "MemoryComparisonService",
    "MemoryShadowComparison",
    "MemoryShadowMetrics",
    "MemoryShadowSettings",
]
