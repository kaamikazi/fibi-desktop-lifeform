"""Immutable, content-free contracts for Memory Migration Stage 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from fibi.memory.query_models import MemoryReadSource, MemoryViewCategory

COMPARISON_SCHEMA_VERSION = "fibi.memory-comparison.v1"
SUITE_SCHEMA_VERSION = "fibi.memory-comparison-suite.v1"


class MemoryComparisonMode(str, Enum):
    SYNTHETIC = "synthetic"
    LOCAL_DATA = "local_data"


class MemoryComparisonFinding(str, Enum):
    HEALTHY = "healthy"
    NEEDS_INVESTIGATION = "needs_investigation"
    MIGRATION_BLOCKER = "migration_blocker"
    NOT_EXECUTED = "not_executed"


@dataclass(frozen=True, slots=True)
class MemoryComparisonRequest:
    """One explicit comparison request; query text never enters a report."""

    query_identifier: str
    query: str = field(repr=False, compare=False)
    mode: MemoryComparisonMode = MemoryComparisonMode.SYNTHETIC
    categories: tuple[MemoryViewCategory, ...] = ()
    sources: tuple[MemoryReadSource, ...] = ()
    result_limit: int = 5
    timeout_seconds: float = 1.0
    local_data_approved: bool = False
    detailed_synthetic_diagnostics: bool = False

    def __post_init__(self) -> None:
        identifier = self.query_identifier.strip()
        if not identifier or len(identifier) > 80:
            raise ValueError("query_identifier must contain 1-80 characters")
        if not all(character.isalnum() or character in {"-", "_"} for character in identifier):
            raise ValueError("query_identifier contains unsupported characters")
        if not self.query.strip():
            raise ValueError("comparison query cannot be empty")

    @property
    def bounded_limit(self) -> int:
        return max(1, min(int(self.result_limit), 25))

    @property
    def bounded_timeout_seconds(self) -> float:
        return max(0.01, min(float(self.timeout_seconds), 10.0))


@dataclass(frozen=True, slots=True)
class MemoryComparisonError:
    category: str
    source: str | None = None
    timed_out: bool = False


@dataclass(frozen=True, slots=True)
class MemoryExclusionMetrics:
    observation_complete: bool = False
    sensitive: int | None = None
    prohibited: int | None = None
    deleted: int | None = None
    expired: int | None = None
    revoked: int | None = None
    secret_bearing: int | None = None


@dataclass(frozen=True, slots=True)
class MemoryMetadataCompleteness:
    missing_consent: int = 0
    missing_sensitivity: int = 0
    missing_timestamps: int = 0
    missing_provenance: int = 0
    missing_importance: int = 0
    missing_confidence: int = 0


@dataclass(frozen=True, slots=True)
class MemorySourceResult:
    """Aggregate observations for one source, with no record payloads."""

    source: str
    available: bool
    healthy: bool
    result_count: int
    category_counts: tuple[tuple[str, int], ...] = ()
    unknown_category_count: int = 0
    consent_counts: tuple[tuple[str, int], ...] = ()
    sensitivity_counts: tuple[tuple[str, int], ...] = ()
    metadata: MemoryMetadataCompleteness = MemoryMetadataCompleteness()
    exclusions: MemoryExclusionMetrics = MemoryExclusionMetrics()
    failure_categories: tuple[str, ...] = ()
    latency_ms: float = 0.0
    timed_out: bool = False
    semantic_index_available: bool | None = None
    semantic_acceleration_available: bool | None = None
    semantic_backend: str | None = None
    irrelevant_candidate_count: int | None = None


@dataclass(frozen=True, slots=True)
class MemoryComparisonMetrics:
    overlap_at_k: int = 0
    jaccard_overlap: float = 0.0
    normalized_retention_rate: float = 0.0
    legacy_exclusive_candidates: int = 0
    rag_exclusive_candidates: int = 0
    rank_agreement: float | None = None
    reciprocal_rank_agreement: float | None = None
    top_result_agreement: bool | None = None
    deterministic_tie_ordering: bool = True
    exact_duplicate_pairs: int = 0
    likely_paraphrase_pairs: int = 0
    possible_contradiction_pairs: int = 0
    cross_source_duplicate_pairs: int = 0
    normalized_candidate_count: int = 0
    normalized_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    timeout_count: int = 0


@dataclass(frozen=True, slots=True)
class MemoryComparisonReport:
    schema_version: str
    comparison_id: str
    mode: str
    synthetic: bool
    executed: bool
    enabled_sources: tuple[str, ...]
    sources: tuple[MemorySourceResult, ...]
    metrics: MemoryComparisonMetrics
    errors: tuple[MemoryComparisonError, ...] = ()
    source_unavailable: bool = False
    finding: str = MemoryComparisonFinding.NOT_EXECUTED.value

    def to_public_dict(self) -> dict[str, Any]:
        """Serialize only the already content-free report contract."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryComparisonSuiteReport:
    schema_version: str
    dataset_version: str
    synthetic: bool
    case_count: int
    executed_count: int
    healthy_count: int
    needs_investigation_count: int
    migration_blocker_count: int
    timeout_count: int
    unavailable_source_count: int
    total_overlap_at_k: int
    total_exact_duplicate_pairs: int
    reports: tuple[MemoryComparisonReport, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "COMPARISON_SCHEMA_VERSION",
    "SUITE_SCHEMA_VERSION",
    "MemoryComparisonError",
    "MemoryComparisonFinding",
    "MemoryComparisonMetrics",
    "MemoryComparisonMode",
    "MemoryComparisonReport",
    "MemoryComparisonRequest",
    "MemoryComparisonSuiteReport",
    "MemoryExclusionMetrics",
    "MemoryMetadataCompleteness",
    "MemorySourceResult",
]
