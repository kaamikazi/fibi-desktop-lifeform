"""Run the Stage 1 comparison against synthetic in-memory fixtures only."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.memory.policy import ConsentStatus, SensitivityLevel
from fibi.memory.query_models import (
    MemoryListFilter,
    MemoryQueryRequest,
    MemoryReadSource,
    MemoryRecordView,
    MemorySourceHealth,
    MemorySourceReadResult,
    MemorySourceReference,
    MemoryViewCategory,
)
from fibi.memory.query_service import CompositeMemoryQueryService
from fibi.memory.shadow_comparison import MemoryShadowComparison, MemoryShadowSettings


class _SyntheticAdapter:
    def __init__(self, source: MemoryReadSource, records: tuple[MemoryRecordView, ...]) -> None:
        self.source = source
        self._records = records

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        return next((record for record in self._records if record.reference == reference), None)

    def query(self, _request: MemoryQueryRequest) -> MemorySourceReadResult:
        return MemorySourceReadResult(self.source, self._records)

    def list(self, _filters: MemoryListFilter) -> MemorySourceReadResult:
        return MemorySourceReadResult(self.source, self._records)

    def health(self) -> MemorySourceHealth:
        return MemorySourceHealth(self.source, True, len(self._records))


def _record(source: MemoryReadSource, record_id: str) -> MemoryRecordView:
    return MemoryRecordView(
        source,
        record_id,
        MemoryViewCategory.FACT,
        "Synthetic comparison fixture.",
        consent_status=ConsentStatus.APPROVED,
        sensitivity=SensitivityLevel.NORMAL,
        provenance={"fixture": True},
    )


def main() -> int:
    adapters = (
        _SyntheticAdapter(MemoryReadSource.LEGACY, (_record(MemoryReadSource.LEGACY, "legacy-1"),)),
        _SyntheticAdapter(MemoryReadSource.RAG, (_record(MemoryReadSource.RAG, "rag-1"),)),
    )
    service = CompositeMemoryQueryService(adapters)
    comparison = MemoryShadowComparison(adapters, service, MemoryShadowSettings(enabled=True))
    metrics = comparison.compare(MemoryQueryRequest("synthetic fixture", limit=5))
    print(json.dumps(dataclasses.asdict(metrics), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
