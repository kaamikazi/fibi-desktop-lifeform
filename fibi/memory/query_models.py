"""Immutable Stage 1 models for storage-neutral memory reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from fibi.memory.policy import ConsentStatus, MemoryStatus, MetadataScalar, SensitivityLevel


class MemoryReadSource(str, Enum):
    """Existing stores exposed through the Stage 1 query boundary."""

    LEGACY = "legacy"
    RAG = "rag"


class MemoryViewCategory(str, Enum):
    """Small normalized read vocabulary; unknown source values stay explicit."""

    FACT = "fact"
    PREFERENCE = "preference"
    PROJECT = "project"
    SUMMARY = "summary"
    UNKNOWN_LEGACY = "unknown_legacy"


@dataclass(frozen=True, slots=True)
class MemorySourceReference:
    source: MemoryReadSource
    source_record_id: str

    def __post_init__(self) -> None:
        if not self.source_record_id.strip():
            raise ValueError("source_record_id cannot be empty")


@dataclass(frozen=True, slots=True)
class MemoryRecordView:
    """Provider-neutral view that never manufactures a persisted universal ID."""

    source: MemoryReadSource
    source_record_id: str
    category: MemoryViewCategory
    content: str
    consent_status: ConsentStatus | None = None
    sensitivity: SensitivityLevel | None = None
    importance: float | None = None
    confidence: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_used_at: str | None = None
    status: MemoryStatus | None = None
    retrieval_score: float | None = None
    provenance: Mapping[str, MetadataScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_record_id.strip():
            raise ValueError("source_record_id cannot be empty")
        if not self.content.strip():
            raise ValueError("content cannot be empty")
        for name, value in (("importance", self.importance), ("confidence", self.confidence)):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.retrieval_score is not None and self.retrieval_score < 0.0:
            raise ValueError("retrieval_score cannot be negative")
        if len(self.provenance) > 12:
            raise ValueError("provenance is limited to 12 fields")
        for key, value in self.provenance.items():
            if not key or len(key) > 64:
                raise ValueError("provenance keys must contain 1-64 characters")
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise TypeError("provenance values must be scalar")
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))

    @property
    def reference(self) -> MemorySourceReference:
        return MemorySourceReference(self.source, self.source_record_id)


@dataclass(frozen=True, slots=True)
class MemoryQueryRequest:
    query: str
    limit: int = 8
    sources: tuple[MemoryReadSource, ...] = ()
    categories: tuple[MemoryViewCategory, ...] = ()

    @property
    def bounded_limit(self) -> int:
        return max(1, min(int(self.limit), 50))


@dataclass(frozen=True, slots=True)
class MemoryListFilter:
    limit: int = 20
    sources: tuple[MemoryReadSource, ...] = ()
    categories: tuple[MemoryViewCategory, ...] = ()

    @property
    def bounded_limit(self) -> int:
        return max(1, min(int(self.limit), 100))


@dataclass(frozen=True, slots=True)
class MemorySourceHealth:
    source: MemoryReadSource
    available: bool
    record_count: int | None = None
    semantic_index_available: bool | None = None
    semantic_acceleration_available: bool | None = None
    semantic_backend: str | None = None
    error_category: str | None = None


@dataclass(frozen=True, slots=True)
class MemorySourceFailure:
    source: MemoryReadSource
    error_category: str
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class MemorySourceReadResult:
    source: MemoryReadSource
    records: tuple[MemoryRecordView, ...] = ()
    failures: tuple[MemorySourceFailure, ...] = ()


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGroup:
    """Potential duplicate references reported without merging source records."""

    references: tuple[MemorySourceReference, ...]


@dataclass(frozen=True, slots=True)
class MemoryQueryResult:
    records: tuple[MemoryRecordView, ...]
    failures: tuple[MemorySourceFailure, ...]
    duplicate_candidates: tuple[DuplicateCandidateGroup, ...]
    duration_ms: float


@dataclass(frozen=True, slots=True)
class MemoryQueryHealth:
    sources: tuple[MemorySourceHealth, ...]

    @property
    def available(self) -> bool:
        return any(item.available for item in self.sources)
