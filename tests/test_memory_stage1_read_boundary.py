"""Synthetic verification for the Stage 1 read-only memory boundary."""

from __future__ import annotations

import builtins
import hashlib
import inspect
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from fibi.app.composition import _attach_memory_read_boundary, build_runtime
from fibi.app.contracts import MemoryQueryService
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
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
from fibi.memory.read_adapters import LegacyMemoryReadAdapter, RAGMemoryReadAdapter
from fibi.memory.read_policy import MemoryReadPolicy
from fibi.rag.config import RAGConfig
from fibi.rag.service import RAGMemoryService


def _policy() -> MemoryReadPolicy:
    sanitizer = SecretSanitizer()
    return MemoryReadPolicy(sanitizer, SensitiveMemoryGuard(sanitizer))


def _legacy_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE memories(
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL,
                confidence REAL,
                source TEXT,
                metadata_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_accessed_at TEXT,
                deleted INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                expires_at TEXT DEFAULT ''
            )
            """
        )
        rows = [
            (1, "fact", "Synthetic user likes local software.", 0.8, 0.9, "fixture", "{}", 0, "active"),
            (2, "odd_old_kind", "Synthetic unmapped record.", None, None, "fixture", "{}", 0, "active"),
            (3, "fact", "Synthetic deleted record.", 0.5, 0.5, "fixture", "{}", 1, "deleted"),
            (
                4,
                "fact",
                "Synthetic medical preference.",
                0.5,
                0.5,
                "fixture",
                '{"review":{"sensitive_flag":"medical","consent_status":"candidate"}}',
                0,
                "active",
            ),
        ]
        connection.executemany(
            """
            INSERT INTO memories(
                id, category, content, importance, confidence, source,
                metadata_json, created_at, updated_at, last_accessed_at,
                deleted, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '2026-01-01', NULL, NULL, ?, ?)
            """,
            rows,
        )


class _LegacyOwner:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def save(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("read adapter invoked a legacy write")

    def delete(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("read adapter invoked a legacy delete")


def _rag_service(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "rag-memory.db",
            vector_dir=root / "rag-index",
            embedding_backend="hashing",
            embedding_dimension=64,
            similarity_threshold=0.0,
        )
    )


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_contract_is_read_only_and_record_view_is_immutable() -> None:
    write_words = {"remember", "save", "add", "update", "delete", "approve", "import", "migrate", "merge"}
    exposed = {name.lower() for name, _ in inspect.getmembers(MemoryQueryService, inspect.isfunction)}
    assert not exposed.intersection(write_words)

    record = MemoryRecordView(
        MemoryReadSource.LEGACY,
        "7",
        MemoryViewCategory.FACT,
        "Synthetic fact.",
        provenance={"origin": "fixture"},
    )
    assert record.importance is None
    assert record.updated_at is None
    assert record.reference == MemorySourceReference(MemoryReadSource.LEGACY, "7")
    with pytest.raises(FrozenInstanceError):
        record.content = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        record.provenance["origin"] = "changed"  # type: ignore[index]


def test_legacy_adapter_normalizes_without_mutating_store(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    _legacy_database(database)
    adapter = LegacyMemoryReadAdapter(_LegacyOwner(database), _policy())
    before = database.read_bytes()

    result = adapter.list(MemoryListFilter(limit=20))
    fetched = adapter.get(MemorySourceReference(MemoryReadSource.LEGACY, "1"))
    health = adapter.health()

    assert database.read_bytes() == before
    assert fetched is not None and fetched.source_record_id == "1"
    assert fetched.provenance["origin_source"] == "fixture"
    assert {record.source_record_id for record in result.records} == {"1", "2"}
    unknown = next(record for record in result.records if record.source_record_id == "2")
    assert unknown.category is MemoryViewCategory.UNKNOWN_LEGACY
    assert unknown.importance is None and unknown.confidence is None
    assert health.available is True and health.record_count == 4


def test_legacy_missing_store_fails_closed(tmp_path: Path) -> None:
    adapter = LegacyMemoryReadAdapter(_LegacyOwner(tmp_path / "missing.db"), _policy())
    result = adapter.query(MemoryQueryRequest("synthetic"))

    assert result.records == ()
    assert result.failures[0].error_category == "storage_missing"
    assert adapter.health().available is False


def test_rag_adapter_preserves_ranking_and_store_bytes(tmp_path: Path) -> None:
    service = _rag_service(tmp_path)
    kept = service.add_memory(
        "Synthetic Project Lantern uses local retrieval.",
        category="project",
        source="synthetic_fixture",
        source_id="lantern-1",
        metadata={"review": {"consent_status": "approved"}},
        allow_duplicate=True,
    )
    deleted = service.add_memory("Synthetic deleted RAG record.", allow_duplicate=True)
    assert kept.id is not None and deleted.id is not None
    assert service.delete_memory(deleted.id)
    before = _file_hashes(tmp_path)
    adapter = RAGMemoryReadAdapter(service, _policy())

    result = adapter.query(MemoryQueryRequest("Project Lantern", limit=5))
    health = adapter.health()

    assert _file_hashes(tmp_path) == before
    assert len(result.records) == 1
    record = result.records[0]
    assert record.source_record_id == str(kept.id)
    assert record.category is MemoryViewCategory.PROJECT
    assert record.consent_status is ConsentStatus.APPROVED
    assert record.sensitivity is SensitivityLevel.NORMAL
    assert record.retrieval_score is not None
    assert record.provenance["rank"] == 1
    assert record.provenance["origin_source_id"] == "lantern-1"
    assert adapter.get(MemorySourceReference(MemoryReadSource.RAG, str(deleted.id))) is None
    assert health.available is True
    assert health.semantic_backend in {"faiss", "numpy"}


def test_rag_adapter_degrades_to_lexical_without_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _rag_service(tmp_path)
    service.add_memory("Synthetic local retrieval survives vector failure.", allow_duplicate=True)

    def unavailable(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("synthetic unavailable")

    monkeypatch.setattr(service.vector_store, "search", unavailable)
    monkeypatch.setattr(service, "rebuild_index", lambda: (_ for _ in ()).throw(AssertionError("rebuild called")))
    adapter = RAGMemoryReadAdapter(service, _policy())

    result = adapter.query(MemoryQueryRequest("local retrieval", limit=3))
    health = adapter.health()

    assert result.records
    assert result.failures == (MemorySourceFailure(MemoryReadSource.RAG, "semantic_unavailable", True),)
    assert health.available is True


def test_rag_adapter_reports_faiss_and_numpy_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def without_faiss(name: str, *args: object, **kwargs: object) -> object:
        if name == "faiss":
            raise ImportError("synthetic missing acceleration")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_faiss)
    service = _rag_service(tmp_path)
    service.add_memory("Synthetic NumPy fallback memory.", allow_duplicate=True)
    adapter = RAGMemoryReadAdapter(service, _policy())

    numpy_health = adapter.health()
    assert numpy_health.semantic_backend == "numpy"
    assert numpy_health.semantic_acceleration_available is False
    assert adapter.query(MemoryQueryRequest("NumPy fallback")).records

    monkeypatch.setattr(service.vector_store, "backend_name", "faiss")
    faiss_health = adapter.health()
    assert faiss_health.semantic_backend == "faiss"
    assert faiss_health.semantic_acceleration_available is True


class _StaticAdapter:
    def __init__(
        self,
        source: MemoryReadSource,
        records: tuple[MemoryRecordView, ...] = (),
        failures: tuple[MemorySourceFailure, ...] = (),
    ) -> None:
        self.source = source
        self.records = records
        self.failures = failures

    def get(self, reference: MemorySourceReference) -> MemoryRecordView | None:
        return next((item for item in self.records if item.reference == reference), None)

    def query(self, _request: MemoryQueryRequest) -> MemorySourceReadResult:
        return MemorySourceReadResult(self.source, self.records, self.failures)

    def list(self, _filters: MemoryListFilter) -> MemorySourceReadResult:
        return MemorySourceReadResult(self.source, self.records, self.failures)

    def health(self) -> MemorySourceHealth:
        return MemorySourceHealth(self.source, True, len(self.records))


def _view(source: MemoryReadSource, record_id: str, content: str, score: float) -> MemoryRecordView:
    return MemoryRecordView(
        source,
        record_id,
        MemoryViewCategory.FACT,
        content,
        consent_status=ConsentStatus.APPROVED,
        sensitivity=SensitivityLevel.NORMAL,
        importance=0.7,
        retrieval_score=score,
        provenance={"fixture": True},
    )


def test_composite_bounds_orders_isolates_and_reports_duplicates() -> None:
    duplicate = "Synthetic duplicate memory."
    legacy = _StaticAdapter(
        MemoryReadSource.LEGACY,
        (_view(MemoryReadSource.LEGACY, "2", duplicate, 0.8), _view(MemoryReadSource.LEGACY, "1", "Other.", 0.8)),
    )
    rag = _StaticAdapter(
        MemoryReadSource.RAG,
        (_view(MemoryReadSource.RAG, "9", duplicate, 0.9),),
        (MemorySourceFailure(MemoryReadSource.RAG, "synthetic_degraded", True),),
    )
    service = CompositeMemoryQueryService((legacy, rag))

    result = service.query(MemoryQueryRequest("synthetic", limit=2))

    assert [item.source_record_id for item in result.records] == ["9", "1"]
    assert result.failures == rag.failures
    assert len(result.duplicate_candidates) == 1
    assert len(result.duplicate_candidates[0].references) == 2
    assert {item.source for item in service.available_sources()} == {MemoryReadSource.LEGACY, MemoryReadSource.RAG}


def test_composite_isolates_unexpected_source_failure_and_rechecks_privacy() -> None:
    class _FailingAdapter(_StaticAdapter):
        def query(self, _request: MemoryQueryRequest) -> MemorySourceReadResult:
            raise RuntimeError("synthetic private exception detail")

    blocked = MemoryRecordView(
        MemoryReadSource.LEGACY,
        "blocked",
        MemoryViewCategory.FACT,
        "Synthetic unapproved sensitive record.",
        consent_status=ConsentStatus.CANDIDATE,
        sensitivity=SensitivityLevel.SENSITIVE,
    )
    legacy = _StaticAdapter(MemoryReadSource.LEGACY, (blocked,))
    rag = _FailingAdapter(MemoryReadSource.RAG)
    service = CompositeMemoryQueryService((legacy, rag))

    result = service.query(MemoryQueryRequest("synthetic"))

    assert result.records == ()
    assert result.failures == (MemorySourceFailure(MemoryReadSource.RAG, "adapter_unavailable"),)


def test_runtime_injects_one_service_and_reuses_existing_owners(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "runtime"))
    runtime = build_runtime(gui_smoke=True)
    try:
        adapters = runtime.memory_query.source_adapters  # type: ignore[attr-defined]
        legacy = next(item for item in adapters if item.source is MemoryReadSource.LEGACY)
        rag = next(item for item in adapters if item.source is MemoryReadSource.RAG)
        existing_rag = runtime.core.memory_router.rag_memory.service

        assert runtime.services.memory_query is runtime.memory_query
        assert runtime.core.services.memory_query is runtime.memory_query
        assert legacy._owner is runtime.services.memory  # type: ignore[attr-defined]
        assert rag._service is existing_rag  # type: ignore[attr-defined]
        assert runtime.duplicate_service_diagnostic()["checks"]["memory_query"] is True
        assert runtime.shutdown() is True
        assert runtime.shutdown() is False
    finally:
        runtime.shutdown()


def test_missing_sources_attach_without_preventing_runtime_construction(tmp_path: Path) -> None:
    services = SimpleNamespace(
        memory=_LegacyOwner(tmp_path / "missing.db"),
        memory_query=None,
        context_broker_preview=None,
        secret_sanitizer=SecretSanitizer(),
    )
    core = SimpleNamespace()

    _attach_memory_read_boundary(services, core)  # type: ignore[arg-type]

    assert services.memory_query is not None
    assert services.memory_query.health().available is False


def test_stage1_is_not_connected_to_current_core_retrieval() -> None:
    from fibi.engines import core

    source = inspect.getsource(core.FibiCore)
    assert "memory_query" not in source
    assert "context_broker_preview" not in source
