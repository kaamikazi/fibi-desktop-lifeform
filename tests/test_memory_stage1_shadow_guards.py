"""Privacy, shadow-mode, and architecture guards for Memory Stage 1."""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.memory.boundaries import scan_memory_boundaries
from fibi.memory.context_preview import ContextBrokerPreview, ContextPreviewRequest
from fibi.memory.policy import ConsentStatus, MemoryStatus, SensitivityLevel
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _CountingAdapter:
    def __init__(self, source: MemoryReadSource, records: tuple[MemoryRecordView, ...]) -> None:
        self.source = source
        self.records = records
        self.query_count = 0

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        return next((record for record in self.records if record.reference == reference), None)

    def query(self, _request: MemoryQueryRequest) -> MemorySourceReadResult:
        self.query_count += 1
        return MemorySourceReadResult(self.source, self.records)

    def list(self, _filters: MemoryListFilter) -> MemorySourceReadResult:
        return MemorySourceReadResult(self.source, self.records)

    def health(self) -> MemorySourceHealth:
        return MemorySourceHealth(self.source, True, len(self.records))


def _record(
    record_id: str,
    content: str,
    *,
    category: MemoryViewCategory = MemoryViewCategory.FACT,
    consent: ConsentStatus | None = ConsentStatus.APPROVED,
    sensitivity: SensitivityLevel = SensitivityLevel.NORMAL,
    status: MemoryStatus | None = MemoryStatus.ACTIVE,
) -> MemoryRecordView:
    return MemoryRecordView(
        MemoryReadSource.LEGACY,
        record_id,
        category,
        content,
        consent_status=consent,
        sensitivity=sensitivity,
        status=status,
        provenance={"fixture": True},
    )


def test_shadow_comparison_is_disabled_and_does_not_query() -> None:
    adapter = _CountingAdapter(MemoryReadSource.LEGACY, (_record("1", "Synthetic sentinel content."),))
    service = CompositeMemoryQueryService((adapter,))
    shadow = MemoryShadowComparison((adapter,), service)

    metrics = shadow.compare(MemoryQueryRequest("synthetic"))

    assert metrics.executed is False
    assert adapter.query_count == 0
    assert dataclasses.asdict(metrics)["source_candidate_counts"] == ()


def test_enabled_shadow_returns_content_free_synthetic_metrics() -> None:
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    adapter = _CountingAdapter(MemoryReadSource.LEGACY, (_record("1", sentinel),))
    service = CompositeMemoryQueryService((adapter,))
    shadow = MemoryShadowComparison((adapter,), service, MemoryShadowSettings(enabled=True, max_results=3))

    metrics = shadow.compare(MemoryQueryRequest("fixture", limit=9))
    rendered = json.dumps(dataclasses.asdict(metrics))

    assert metrics.executed is True
    assert metrics.normalized_candidate_count == 1
    assert sentinel not in rendered
    assert "fixture" not in rendered


def test_context_preview_is_off_by_default_and_filters_private_candidates() -> None:
    preview = ContextBrokerPreview(SecretSanitizer())
    candidates = (
        _record("1", "Approved synthetic project.", category=MemoryViewCategory.PROJECT),
        _record("2", "Synthetic medical note.", sensitivity=SensitivityLevel.SENSITIVE),
        _record("3", "TOKEN=abcdefghijklmnopqrstuvwxyz0123456789"),
        _record("4", "Unapproved synthetic note.", consent=ConsentStatus.CANDIDATE),
        _record("5", "Deleted synthetic note.", status=MemoryStatus.DELETED),
    )

    assert preview.build_preview(ContextPreviewRequest(include_text=True), (), candidates).executed is False
    preview.enabled = True
    result = preview.build_preview(
        ContextPreviewRequest(max_items=1, max_characters=80, include_text=True),
        (MemoryViewCategory.PROJECT,),
        candidates,
    )

    assert result.executed is True
    assert result.included_count == 1
    assert result.excluded_count == 4
    assert result.context_text == "- project: Approved synthetic project."
    assert result.items[0].source_reference_hash != "1"
    assert "TOKEN" not in (result.context_text or "")


def test_context_preview_has_no_repository_or_provider_dependency() -> None:
    from fibi.memory import context_preview

    source = inspect.getsource(context_preview)
    assert "fibi.rag" not in source
    assert "fibi.providers" not in source
    assert "fibi.services.providers" not in source
    assert "sqlite3" not in source


def test_memory_boundary_architecture_checks_pass() -> None:
    assert scan_memory_boundaries(PROJECT_ROOT) == []


def test_companion_and_operational_state_cannot_be_registered() -> None:
    allowed_sources = {item.value for item in MemoryReadSource}
    allowed_categories = {item.value for item in MemoryViewCategory}

    assert allowed_sources == {"legacy", "rag"}
    assert allowed_categories == {"fact", "preference", "project", "summary", "unknown_legacy"}
    forbidden = {
        "affection",
        "trust",
        "comfort",
        "mood",
        "animation_state",
        "voice_configuration",
        "theme",
        "ritual_counter",
        "permission_audit",
        "task_audit",
        "diagnostic",
    }
    assert forbidden.isdisjoint(allowed_sources | allowed_categories)
