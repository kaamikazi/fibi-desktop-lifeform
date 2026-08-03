"""Synthetic tests for memory ownership, inventory, and privacy foundations."""

from __future__ import annotations

import builtins
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from fibi.engines.memory_review_engine import MemoryReviewEngine
from fibi.engines.types import MemoryExportRequest
from fibi.memory.boundaries import scan_memory_boundaries
from fibi.memory.inventory import KNOWN_STORES, MemoryInventoryScanner
from fibi.memory.migration import MemoryMigrationPreflight
from fibi.memory.policy import (
    ApprovedMemoryCategory,
    ApprovedMemoryRecord,
    ConsentStatus,
    MemoryStatus,
    SensitivityLevel,
    duplicate_record_types,
    ownership_rules,
)
from fibi.rag.config import RAGConfig
from fibi.rag.ingestion import DocumentIngestionService
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from fibi.rag.service import RAGMemoryService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _rag(root: Path) -> RAGMemoryService:
    return RAGMemoryService(
        RAGConfig(
            database_path=root / "memory.db",
            vector_dir=root / "rag",
            embedding_backend="hashing",
            embedding_dimension=128,
            similarity_threshold=0.08,
        )
    )


def test_target_ownership_has_one_owner_per_record_type() -> None:
    rules = ownership_rules()
    assert rules
    assert duplicate_record_types(rules) == set()
    assert len({rule.record_type for rule in rules}) == len(rules)


def test_approved_record_context_requires_active_normal_approval() -> None:
    base = dict(
        record_id=1,
        category=ApprovedMemoryCategory.FACT,
        content="The user prefers keyboard navigation.",
        subject_key="preference:input",
        importance=0.8,
        confidence=0.9,
        source="explicit_user_request",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    approved = ApprovedMemoryRecord(**base, consent_status=ConsentStatus.APPROVED)
    pending = ApprovedMemoryRecord(**base, consent_status=ConsentStatus.CANDIDATE)
    sensitive = ApprovedMemoryRecord(
        **base,
        consent_status=ConsentStatus.APPROVED,
        sensitivity=SensitivityLevel.SENSITIVE,
    )
    deleted = ApprovedMemoryRecord(
        **base,
        consent_status=ConsentStatus.APPROVED,
        status=MemoryStatus.DELETED,
    )
    assert approved.eligible_for_model_context
    assert not pending.eligible_for_model_context
    assert not sensitive.eligible_for_model_context
    assert not deleted.eligible_for_model_context


def test_approved_record_rejects_unbounded_metadata() -> None:
    with pytest.raises(ValueError, match="16 fields"):
        ApprovedMemoryRecord(
            1,
            ApprovedMemoryCategory.FACT,
            "Synthetic fact.",
            "fact:synthetic",
            0.5,
            0.5,
            "test",
            ConsentStatus.APPROVED,
            "now",
            "now",
            metadata={f"key_{index}": index for index in range(17)},
        )


def test_inventory_is_read_only_sanitized_and_handles_spaces(tmp_path: Path) -> None:
    data_root = tmp_path / "data root with spaces"
    data_root.mkdir()
    database = data_root / "fibi_memory.db"
    sentinel = "PRIVATE_MEMORY_SENTINEL"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE memories(id INTEGER PRIMARY KEY, content TEXT)")
        connection.execute("CREATE TABLE rag_memories(id INTEGER PRIMARY KEY, content TEXT)")
        connection.execute("INSERT INTO memories(content) VALUES (?)", (sentinel,))
    state_path = data_root / "fibi_state.json"
    state_path.write_text(json.dumps({"last_user_message": sentinel}), encoding="utf-8")
    before_hash = hashlib.sha256(database.read_bytes()).hexdigest()
    before_files = sorted(path.relative_to(data_root) for path in data_root.rglob("*"))

    report = MemoryInventoryScanner(data_root).scan()
    rendered = report.to_json()

    assert sentinel not in rendered
    assert str(tmp_path) not in rendered
    assert '"content_included": false' in rendered
    legacy = next(store for store in report.stores if store.store_id == "legacy_memory")
    assert legacy.exists
    assert legacy.tables[0].row_count == 1
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before_hash
    assert sorted(path.relative_to(data_root) for path in data_root.rglob("*")) == before_files


def test_inventory_detects_every_declared_store_and_missing_is_safe(tmp_path: Path) -> None:
    report = MemoryInventoryScanner(tmp_path / "missing data").scan()
    assert {store.store_id for store in report.stores} == {store.store_id for store in KNOWN_STORES}
    assert all(not store.exists for store in report.stores)
    assert not (tmp_path / "missing data").exists()


def test_migration_preflight_is_read_only_and_sanitized(tmp_path: Path) -> None:
    data_root = tmp_path / "data with spaces"
    data_root.mkdir()
    database = data_root / "fibi_memory.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, content TEXT)")
        connection.execute("INSERT INTO memories(content) VALUES (?)", ("private sentinel value",))
    before = database.read_bytes()

    result = MemoryMigrationPreflight(data_root).run().to_public_dict()

    assert database.read_bytes() == before
    assert result["mode"] == "dry-run"
    assert result["apply_supported"] is False
    assert result["content_included"] is False
    assert "private sentinel value" not in json.dumps(result)
    assert any("backup" in blocker for blocker in result["blockers"])


def test_migration_cli_rejects_apply_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from fibi.tools.memory_migrate import main

    marker = tmp_path / "unchanged.txt"
    marker.write_text("sentinel", encoding="utf-8")

    assert main(["--data-dir", str(tmp_path), "--apply"]) == 2
    assert marker.read_text(encoding="utf-8") == "sentinel"
    output = capsys.readouterr().out
    assert "blocked" in output.lower()
    assert "sentinel" not in output


def test_repository_memory_boundaries_pass() -> None:
    assert scan_memory_boundaries(PROJECT_ROOT) == []


def test_rag_memory_operates_without_faiss_acceleration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real_import = builtins.__import__

    def without_faiss(name: str, *args: object, **kwargs: object) -> object:
        if name == "faiss":
            raise ImportError("synthetic missing optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_faiss)
    service = _rag(tmp_path)
    memory = service.add_memory(
        "The user prefers local retrieval.",
        category="preference",
        source="synthetic_test",
    )

    assert service.vector_store.backend_name == "numpy"
    assert service.retrieve_top_k("local retrieval", top_k=1)[0].memory.id == memory.id

    reloaded = _rag(tmp_path)
    assert reloaded.vector_store.backend_name == "numpy"
    assert reloaded.retrieve_top_k("local retrieval", top_k=1)[0].memory.id == memory.id


def test_secret_paths_and_secret_content_are_not_ingested(tmp_path: Path) -> None:
    service = _rag(tmp_path)
    ingestion = DocumentIngestionService(service)
    env_path = tmp_path / ".env"
    env_path.write_text("TEST_TOKEN=not-a-real-token", encoding="utf-8")
    blocked_path = ingestion.ingest_file(env_path)
    assert blocked_path.skipped_reason == "blocked sensitive path"
    assert "not-a-real-token" not in blocked_path.source_path

    text_path = tmp_path / "notes.txt"
    text_path.write_text("TEST_TOKEN=not-a-real-token", encoding="utf-8")
    blocked_content = ingestion.ingest_file(text_path)
    assert blocked_content.skipped_reason == "blocked secret-bearing content"
    assert service.repository.count_active() == 0
    with service.repository.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM rag_documents").fetchone()[0] == 0


def test_export_never_includes_prohibited_content_and_sensitive_needs_opt_in(tmp_path: Path) -> None:
    facade = RAGMemoryServiceFacade(database_path=tmp_path / "memory.db", vector_dir=tmp_path / "rag")
    review = MemoryReviewEngine(
        facade,
        deletion_log_path=tmp_path / "deletions.jsonl",
        export_dir=tmp_path / "exports",
    )
    fake_key = "sk-" + "x" * 36
    facade.service.add_memory(
        f"API_KEY={fake_key}",
        category="fact",
        source="synthetic_test",
        allow_duplicate=True,
    )
    facade.service.add_memory(
        "The user discussed a medical preference.",
        category="fact",
        source="synthetic_test",
        metadata={"review": {"approved": True, "sensitive_flag": "medical"}},
        allow_duplicate=True,
    )

    default_json, _ = review.export_memories(MemoryExportRequest())
    default_text = default_json.read_text(encoding="utf-8")
    assert fake_key not in default_text
    assert "medical preference" not in default_text

    sensitive_json, _ = review.export_memories(MemoryExportRequest(include_sensitive=True))
    sensitive_text = sensitive_json.read_text(encoding="utf-8")
    assert fake_key not in sensitive_text
    assert "medical preference" in sensitive_text
