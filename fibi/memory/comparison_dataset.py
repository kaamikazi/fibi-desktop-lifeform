"""Loader and synthetic adapters for the Stage 2 evaluation dataset."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fibi.memory.comparison_models import (
    SUITE_SCHEMA_VERSION,
    MemoryComparisonFinding,
    MemoryComparisonMode,
    MemoryComparisonRequest,
    MemoryComparisonSuiteReport,
    MemoryExclusionMetrics,
)
from fibi.memory.policy import ConsentStatus, MemoryStatus, SensitivityLevel
from fibi.memory.query_models import (
    MemoryListFilter,
    MemoryQueryRequest,
    MemoryReadSource,
    MemoryRecordView,
    MemorySourceFailure,
    MemorySourceHealth,
    MemorySourceReadResult,
    MemorySourceReference,
    MemoryViewCategory,
)
from fibi.memory.query_service import CompositeMemoryQueryService
from fibi.memory.shadow_comparison import MemoryComparisonService

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[2] / "eval" / "memory_stage2" / "dataset.json"
EXPECTED_DATASET_SCHEMA = "fibi.memory-comparison.dataset.v1"


class SyntheticMemoryAdapter:
    """In-memory read adapter built exclusively from fictional fixture data."""

    def __init__(self, source: MemoryReadSource, specification: Mapping[str, Any]) -> None:
        self.source = source
        self._records = tuple(_record(source, item) for item in specification.get("records", ()))
        self._failures = tuple(
            MemorySourceFailure(source, str(category), degraded=str(category) == "semantic_unavailable")
            for category in specification.get("failures", ())
        )
        health = specification.get("health", {})
        self._health = MemorySourceHealth(
            source,
            available=bool(health.get("available", True)),
            record_count=len(self._records),
            semantic_index_available=_optional_bool(health, "semantic_index_available"),
            semantic_acceleration_available=_optional_bool(health, "semantic_acceleration_available"),
            semantic_backend=str(health["semantic_backend"]) if "semantic_backend" in health else None,
            error_category=None if health.get("available", True) else "storage_missing",
        )
        self._exclusions = _exclusions(specification.get("exclusions", {}))
        self._delay_seconds = max(0.0, float(specification.get("delay_ms", 0.0)) / 1000.0)

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        return next((record for record in self._records if record.reference == reference), None)

    def query(self, request: MemoryQueryRequest) -> MemorySourceReadResult:
        if self._delay_seconds:
            time.sleep(self._delay_seconds)
        if request.sources and self.source not in request.sources:
            return MemorySourceReadResult(self.source)
        records = tuple(
            record
            for record in self._records
            if not request.categories or record.category in request.categories
        )[: request.bounded_limit]
        return MemorySourceReadResult(self.source, records, self._failures)

    def list(self, filters: MemoryListFilter) -> MemorySourceReadResult:
        records = tuple(
            record
            for record in self._records
            if not filters.categories or record.category in filters.categories
        )[: filters.bounded_limit]
        return MemorySourceReadResult(self.source, records, self._failures)

    def health(self) -> MemorySourceHealth:
        return self._health

    def comparison_exclusions(self, _request: MemoryQueryRequest) -> MemoryExclusionMetrics:
        return self._exclusions


def load_synthetic_dataset(path: Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != EXPECTED_DATASET_SCHEMA:
        raise ValueError("unsupported Stage 2 dataset schema")
    cases = raw.get("cases")
    if not isinstance(cases, list) or len(cases) != 20:
        raise ValueError("Stage 2 dataset must contain exactly 20 cases")
    identifiers = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(identifiers) != 20 or len(set(identifiers)) != 20:
        raise ValueError("Stage 2 dataset case IDs must be unique")
    return raw


def run_synthetic_suite(path: Path = DEFAULT_DATASET_PATH) -> MemoryComparisonSuiteReport:
    dataset = load_synthetic_dataset(path)
    reports = []
    for case in dataset["cases"]:
        adapters = (
            SyntheticMemoryAdapter(MemoryReadSource.LEGACY, case["legacy"]),
            SyntheticMemoryAdapter(MemoryReadSource.RAG, case["rag"]),
        )
        query_service = CompositeMemoryQueryService(adapters)
        comparison = MemoryComparisonService(adapters, query_service, enabled=True)
        request = MemoryComparisonRequest(
            query_identifier=str(case["id"]),
            query=str(case["query"]),
            mode=MemoryComparisonMode.SYNTHETIC,
            result_limit=int(case.get("limit", 5)),
            timeout_seconds=float(case.get("timeout_seconds", 0.5)),
            detailed_synthetic_diagnostics=True,
        )
        reports.append(comparison.compare(request))
    findings = [report.finding for report in reports]
    return MemoryComparisonSuiteReport(
        schema_version=SUITE_SCHEMA_VERSION,
        dataset_version=str(dataset["dataset_version"]),
        synthetic=True,
        case_count=len(reports),
        executed_count=sum(report.executed for report in reports),
        healthy_count=findings.count(MemoryComparisonFinding.HEALTHY.value),
        needs_investigation_count=findings.count(MemoryComparisonFinding.NEEDS_INVESTIGATION.value),
        migration_blocker_count=findings.count(MemoryComparisonFinding.MIGRATION_BLOCKER.value),
        timeout_count=sum(report.metrics.timeout_count for report in reports),
        unavailable_source_count=sum(
            not source.available for report in reports for source in report.sources
        ),
        total_overlap_at_k=sum(report.metrics.overlap_at_k for report in reports),
        total_exact_duplicate_pairs=sum(report.metrics.exact_duplicate_pairs for report in reports),
        reports=tuple(reports),
    )


def _record(source: MemoryReadSource, raw: Mapping[str, Any]) -> MemoryRecordView:
    consent_raw = raw.get("consent", "approved")
    sensitivity_raw = raw.get("sensitivity", "normal")
    status_raw = raw.get("status", "active")
    return MemoryRecordView(
        source=source,
        source_record_id=str(raw["id"]),
        category=MemoryViewCategory(str(raw.get("category", "unknown_legacy"))),
        content=str(raw["content"]),
        consent_status=ConsentStatus(str(consent_raw)) if consent_raw is not None else None,
        sensitivity=SensitivityLevel(str(sensitivity_raw)) if sensitivity_raw is not None else None,
        importance=_optional_float(raw, "importance", 0.7),
        confidence=_optional_float(raw, "confidence", 0.8),
        created_at=_optional_text(raw, "created_at", "2026-01-01T00:00:00Z"),
        updated_at=_optional_text(raw, "updated_at", "2026-01-01T00:00:00Z"),
        status=MemoryStatus(str(status_raw)) if status_raw is not None else None,
        retrieval_score=float(raw.get("score", 0.5)),
        provenance={
            "synthetic_fixture": True,
            "synthetic_relevant": bool(raw.get("relevant", True)),
            "synthetic_contradiction_group": str(raw["contradiction_group"])
            if "contradiction_group" in raw
            else None,
        },
    )


def _exclusions(raw: Mapping[str, Any]) -> MemoryExclusionMetrics:
    return MemoryExclusionMetrics(
        observation_complete=bool(raw.get("observation_complete", False)),
        sensitive=_optional_int(raw, "sensitive"),
        prohibited=_optional_int(raw, "prohibited"),
        deleted=_optional_int(raw, "deleted"),
        expired=_optional_int(raw, "expired"),
        revoked=_optional_int(raw, "revoked"),
        secret_bearing=_optional_int(raw, "secret_bearing"),
    )


def _optional_bool(raw: Mapping[str, Any], key: str) -> bool | None:
    return bool(raw[key]) if key in raw else None


def _optional_int(raw: Mapping[str, Any], key: str) -> int | None:
    return max(0, int(raw[key])) if key in raw else None


def _optional_float(raw: Mapping[str, Any], key: str, default: float) -> float | None:
    return float(raw[key]) if key in raw and raw[key] is not None else (None if key in raw else default)


def _optional_text(raw: Mapping[str, Any], key: str, default: str) -> str | None:
    return str(raw[key]) if key in raw and raw[key] is not None else (None if key in raw else default)


__all__ = [
    "DEFAULT_DATASET_PATH",
    "SyntheticMemoryAdapter",
    "load_synthetic_dataset",
    "run_synthetic_suite",
]
