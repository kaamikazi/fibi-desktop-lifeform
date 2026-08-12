"""Focused synthetic and byte-stability tests for Memory Stage 2."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
from fibi.memory.comparison_dataset import (
    DEFAULT_DATASET_PATH,
    SyntheticMemoryAdapter,
    load_synthetic_dataset,
    run_synthetic_suite,
)
from fibi.memory.comparison_models import (
    COMPARISON_SCHEMA_VERSION,
    MemoryComparisonMode,
    MemoryComparisonRequest,
)
from fibi.memory.query_models import MemoryQueryRequest, MemoryReadSource
from fibi.memory.query_service import CompositeMemoryQueryService
from fibi.memory.read_adapters import LegacyMemoryReadAdapter, RAGMemoryReadAdapter
from fibi.memory.read_policy import MemoryReadPolicy
from fibi.memory.shadow_comparison import MemoryComparisonService
from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService


def _case(case_id: str) -> dict:
    dataset = load_synthetic_dataset()
    return next(case for case in dataset["cases"] if case["id"] == case_id)


def _report(case_id: str):
    case = _case(case_id)
    adapters = (
        SyntheticMemoryAdapter(MemoryReadSource.LEGACY, case["legacy"]),
        SyntheticMemoryAdapter(MemoryReadSource.RAG, case["rag"]),
    )
    service = MemoryComparisonService(adapters, CompositeMemoryQueryService(adapters), enabled=True)
    request = MemoryComparisonRequest(
        case_id,
        case["query"],
        result_limit=case.get("limit", 5),
        timeout_seconds=case.get("timeout_seconds", 0.5),
        detailed_synthetic_diagnostics=True,
    )
    return service.compare(request)


def _hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _policy() -> MemoryReadPolicy:
    sanitizer = SecretSanitizer()
    return MemoryReadPolicy(sanitizer, SensitiveMemoryGuard(sanitizer))


class _CountingAdapter(SyntheticMemoryAdapter):
    def __init__(self) -> None:
        super().__init__(MemoryReadSource.LEGACY, {"records": []})
        self.query_count = 0

    def query(self, request: MemoryQueryRequest):
        self.query_count += 1
        return super().query(request)


def test_contracts_are_immutable_bounded_and_content_free() -> None:
    request = MemoryComparisonRequest("bounded_case", "raw synthetic query", result_limit=999, timeout_seconds=999)
    assert request.bounded_limit == 25
    assert request.bounded_timeout_seconds == 10.0
    assert "raw synthetic query" not in repr(request)
    with pytest.raises(FrozenInstanceError):
        request.result_limit = 3  # type: ignore[misc]

    report = _report("exact_fact_both")
    rendered = json.dumps(report.to_public_dict(), sort_keys=True)
    assert report.schema_version == COMPARISON_SCHEMA_VERSION
    assert "Nova prefers teal notebooks" not in rendered
    assert "What color does Nova prefer" not in rendered
    assert "source_record_id" not in rendered
    assert "content_hash" not in rendered
    assert "fingerprint" not in rendered
    assert not re.search(r"[a-f0-9]{64}", rendered)
    with pytest.raises(FrozenInstanceError):
        report.executed = False  # type: ignore[misc]


def test_disabled_comparison_runs_no_query_and_creates_no_report(tmp_path: Path) -> None:
    adapter = _CountingAdapter()
    query_service = CompositeMemoryQueryService((adapter,))
    comparison = MemoryComparisonService((adapter,), query_service)
    before = list(tmp_path.iterdir())

    report = comparison.compare(MemoryComparisonRequest("disabled", "synthetic query"))

    assert report.executed is False
    assert report.errors[0].category == "comparison_disabled"
    assert adapter.query_count == 0
    assert list(tmp_path.iterdir()) == before == []


def test_local_data_mode_is_blocked_even_after_confirmation() -> None:
    adapter = _CountingAdapter()
    comparison = MemoryComparisonService(
        (adapter,),
        CompositeMemoryQueryService((adapter,)),
        enabled=True,
    )
    request = MemoryComparisonRequest(
        "local_blocked",
        "must not be read",
        mode=MemoryComparisonMode.LOCAL_DATA,
        local_data_approved=True,
    )

    report = comparison.compare(request)

    assert report.executed is False
    assert report.errors[0].category == "local_data_mode_not_implemented"
    assert adapter.query_count == 0


def test_exact_overlap_rank_and_duplicate_metrics() -> None:
    report = _report("exact_fact_both")
    metrics = report.metrics

    assert metrics.overlap_at_k == 1
    assert metrics.jaccard_overlap == 1.0
    assert metrics.normalized_retention_rate == 1.0
    assert metrics.top_result_agreement is True
    assert metrics.rank_agreement == 1.0
    assert metrics.reciprocal_rank_agreement == 1.0
    assert metrics.exact_duplicate_pairs == 1
    assert metrics.cross_source_duplicate_pairs == 1


def test_paraphrase_exclusive_contradiction_and_tie_metrics() -> None:
    preference = _report("preference_different_wording")
    project = _report("legacy_only_project")
    contradiction = _report("contradicted_fact")
    ties = _report("equal_score_ordering")

    assert preference.metrics.likely_paraphrase_pairs == 1
    assert project.metrics.legacy_exclusive_candidates == 1
    assert project.metrics.rag_exclusive_candidates == 0
    assert contradiction.metrics.possible_contradiction_pairs == 1
    assert contradiction.finding == "needs_investigation"
    assert ties.metrics.deterministic_tie_ordering is True


def test_metadata_exclusion_and_irrelevant_metrics() -> None:
    unknown = _report("unknown_legacy_category")
    deleted = _report("deleted_memory")
    expired = _report("expired_temporary_memory")
    revoked = _report("revoked_memory")
    sensitive = _report("unapproved_sensitive_memory")
    secret = _report("secret_bearing_memory")
    irrelevant = _report("irrelevant_candidate")

    legacy_unknown = next(source for source in unknown.sources if source.source == "legacy")
    assert legacy_unknown.category_counts == (("unknown_legacy", 1),)
    assert legacy_unknown.unknown_category_count == 1
    assert legacy_unknown.metadata.missing_consent == 1
    assert legacy_unknown.metadata.missing_sensitivity == 1
    assert deleted.sources[0].exclusions.deleted == 1
    assert expired.sources[0].exclusions.expired == 1
    assert revoked.sources[0].exclusions.revoked == 1
    assert sensitive.sources[0].exclusions.sensitive == 1
    assert secret.sources[0].exclusions.prohibited == 1
    assert secret.sources[0].exclusions.secret_bearing == 1
    assert irrelevant.sources[0].irrelevant_candidate_count == 1


def test_optional_index_failure_timeout_unavailable_and_empty_results() -> None:
    fallback = _report("numpy_fallback")
    semantic = _report("semantic_unavailable")
    unavailable = _report("one_source_unavailable")
    timeout = _report("source_timeout")
    empty = _report("empty_result_set")

    rag = next(source for source in fallback.sources if source.source == "rag")
    assert rag.semantic_backend == "numpy"
    assert rag.semantic_index_available is True
    assert rag.semantic_acceleration_available is False
    assert {error.category for error in semantic.errors} == {"semantic_unavailable"}
    assert unavailable.source_unavailable is True
    assert any("storage_missing" in source.failure_categories for source in unavailable.sources)
    assert unavailable.finding == "migration_blocker"
    assert timeout.metrics.timeout_count >= 1
    assert any(error.timed_out for error in timeout.errors)
    assert empty.metrics.normalized_candidate_count == 0
    assert empty.metrics.jaccard_overlap == 1.0


def test_source_exception_is_normalized_without_exception_text() -> None:
    class _BrokenAdapter(_CountingAdapter):
        def query(self, _request: MemoryQueryRequest):
            raise RuntimeError("PRIVATE_SYNTHETIC_EXCEPTION_DETAIL")

    adapter = _BrokenAdapter()
    service = MemoryComparisonService((adapter,), CompositeMemoryQueryService((adapter,)), enabled=True)
    report = service.compare(MemoryComparisonRequest("broken", "synthetic query"))
    rendered = json.dumps(report.to_public_dict())

    assert "PRIVATE_SYNTHETIC_EXCEPTION_DETAIL" not in rendered
    assert report.sources[0].failure_categories == ("source_read_error",)


def test_real_temporary_stores_remain_byte_stable(tmp_path: Path) -> None:
    database = tmp_path / "memory.db"
    legacy_owner = MemoryEngine(database)
    legacy_id = legacy_owner.save("fact", "Synthetic byte-stable legacy memory.", source="fixture")
    rag_service = RAGMemoryService(
        RAGConfig(
            database_path=database,
            vector_dir=tmp_path / "rag",
            embedding_backend="hashing",
            embedding_dimension=64,
            similarity_threshold=0.0,
        )
    )
    rag_memory = rag_service.add_memory(
        "Synthetic byte-stable RAG memory.",
        source="fixture",
        allow_duplicate=True,
    )
    assert legacy_id is not None and rag_memory.id is not None
    adapters = (
        LegacyMemoryReadAdapter(legacy_owner, _policy()),
        RAGMemoryReadAdapter(rag_service, _policy()),
    )
    comparison = MemoryComparisonService(adapters, CompositeMemoryQueryService(adapters), enabled=True)
    with sqlite3.connect(database) as connection:
        legacy_access_before = connection.execute(
            "SELECT access_count, last_accessed_at FROM memories WHERE id = ?", (legacy_id,)
        ).fetchone()
        rag_access_before = connection.execute(
            "SELECT access_count, last_accessed_at FROM rag_memories WHERE id = ?", (rag_memory.id,)
        ).fetchone()
    before = _hashes(tmp_path)

    report = comparison.compare(MemoryComparisonRequest("byte_stability", "byte stable memory", result_limit=5))

    with sqlite3.connect(database) as connection:
        legacy_access_after = connection.execute(
            "SELECT access_count, last_accessed_at FROM memories WHERE id = ?", (legacy_id,)
        ).fetchone()
        rag_access_after = connection.execute(
            "SELECT access_count, last_accessed_at FROM rag_memories WHERE id = ?", (rag_memory.id,)
        ).fetchone()
    assert report.executed is True
    assert _hashes(tmp_path) == before
    assert legacy_access_after == legacy_access_before
    assert rag_access_after == rag_access_before


def test_dataset_is_static_fictional_and_privacy_scanned() -> None:
    dataset = load_synthetic_dataset()
    raw = DEFAULT_DATASET_PATH.read_text(encoding="utf-8")
    lowered = raw.casefold()
    maintainer_name = "im" + "ran"
    private_windows_root = "c:" + "\\users"
    private_posix_root = "/" + "users/"

    assert len(dataset["cases"]) == 20
    assert maintainer_name not in lowered
    assert "@" not in raw
    assert private_windows_root not in lowered
    assert private_posix_root not in lowered
    assert ".env" not in lowered
    assert not re.search(r"AIza[A-Za-z0-9_-]{20,}", raw)
    assert not re.search(r"(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}", raw)


def test_synthetic_suite_reports_all_cases_without_payloads() -> None:
    suite = run_synthetic_suite()
    rendered = json.dumps(suite.to_public_dict(), sort_keys=True)

    assert suite.case_count == suite.executed_count == 20
    assert suite.migration_blocker_count == 2
    assert suite.timeout_count >= 1
    assert "Nova prefers teal notebooks" not in rendered
    assert "raw_query" not in rendered
    assert "database_path" not in rendered


def test_default_runtime_and_providers_do_not_reference_comparison() -> None:
    from fibi.app import composition, runtime
    from fibi.engines import core
    from fibi import main

    for module in (composition, runtime, core, main):
        source = inspect.getsource(module)
        assert "MemoryComparisonService" not in source
        assert "MemoryShadowComparison" not in source
        assert "memory_compare" not in source
