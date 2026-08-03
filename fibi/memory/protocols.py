"""Internal structural contracts for Stage 1 memory read adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fibi.memory.query_models import (
    MemoryListFilter,
    MemoryQueryRequest,
    MemorySourceHealth,
    MemorySourceReadResult,
    MemorySourceReference,
    MemoryRecordView,
    MemoryReadSource,
)


@runtime_checkable
class MemoryReadAdapter(Protocol):
    """Read-only source adapter; it deliberately exposes no mutation surface."""

    source: MemoryReadSource

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None: ...

    def query(self, request: MemoryQueryRequest) -> MemorySourceReadResult: ...

    def list(self, filters: MemoryListFilter) -> MemorySourceReadResult: ...

    def health(self) -> MemorySourceHealth: ...
