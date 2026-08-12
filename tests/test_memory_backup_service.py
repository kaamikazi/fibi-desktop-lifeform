"""Discovery and creation tests for private memory backups."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from fibi.memory_backup import safety
from fibi.memory_backup.discovery import PersistenceAssetDiscovery
from fibi.memory_backup.faults import (
    BackupFaultPoint,
    DeterministicFaultInjector,
)
from fibi.memory_backup.models import (
    AssetClassification,
    BackupRequest,
    BackupStrategy,
)
from fibi.memory_backup.service import MemoryBackupService
from fibi.memory_backup.verifier import BackupVerifier
from tests.memory_backup_test_support import (
    FIXED_TIME,
    SYNTHETIC_SENTINEL,
    create_backup,
    create_synthetic_data,
    file_hash,
    read_manifest,
    tree_hashes,
)


def test_discovery_classifies_only_bounded_assets(tmp_path: Path) -> None:
    data = tmp_path / "synthetic data"
    create_synthetic_data(data)

    plan = PersistenceAssetDiscovery().discover(data)
    by_id = {asset.logical_id: asset for asset in plan.assets}

    assert by_id["memory_database"].classification is AssetClassification.PRIMARY_PERSISTENCE
    assert by_id["memory_database"].strategy is BackupStrategy.SQLITE_BACKUP_API
    assert by_id["memory_database"].required is True
    assert by_id["memory_consent_state"].classification is AssetClassification.MIGRATION_SUPPORT
    assert by_id["memory_deletion_audit"].included is True
    assert by_id["rag_vector_index"].classification is AssetClassification.DERIVED_REBUILDABLE
    assert by_id["rag_vector_index"].included is False
    assert by_id["runtime_logs"].classification is AssetClassification.OUT_OF_SCOPE
    assert by_id["runtime_logs"].included is False


def test_contract_is_immutable_and_paths_are_not_public(tmp_path: Path) -> None:
    request = BackupRequest(tmp_path / "private source", tmp_path / "private output")
    with pytest.raises(FrozenInstanceError):
        request.confirm_private_output = True  # type: ignore[misc]
    assert str(tmp_path) not in repr(request)


def test_verified_backup_is_content_free_and_source_unchanged(tmp_path: Path) -> None:
    data = tmp_path / ("data with spaces and unicode " + "\u2603")
    database = create_synthetic_data(data)
    output = tmp_path / "private backup destination"
    source_before = tree_hashes(data)

    result = create_backup(data, output)

    assert result.success is True
    assert result.asset_count == 3
    assert result.required_verified_count == 1
    assert result.manifest_valid is True
    assert tree_hashes(data) == source_before
    assert result.bundle_path is not None
    verification = BackupVerifier().verify(result.bundle_path)
    assert verification.valid is True
    manifest_text = (result.bundle_path / "manifest.json").read_text(encoding="utf-8")
    assert SYNTHETIC_SENTINEL not in manifest_text
    assert str(tmp_path) not in manifest_text
    manifest = read_manifest(result.bundle_path)
    assert manifest["format_version"] == "fibi.memory-backup.v1"
    assert manifest["complete"] is True
    assert manifest["omitted_derived_asset_ids"] == [
        "rag_vector_id_map",
        "rag_vector_index",
        "rag_vector_manifest",
    ]
    backup_database = result.bundle_path / "databases" / "memory.sqlite"
    with sqlite3.connect(backup_database) as connection:
        assert connection.execute("SELECT content FROM memories").fetchone()[0] == SYNTHETIC_SENTINEL
    assert file_hash(database) == source_before["fibi_memory.db"]
    assert str(tmp_path) not in json.dumps(result.to_public_dict())


def test_wal_backed_database_captures_committed_rows_without_checkpointing_source(tmp_path: Path) -> None:
    data = tmp_path / "wal data"
    data.mkdir()
    database = data / "fibi_memory.db"
    writer = sqlite3.connect(database)
    try:
        assert writer.execute("PRAGMA journal_mode = WAL").fetchone()[0].casefold() == "wal"
        writer.execute("CREATE TABLE memories(id INTEGER PRIMARY KEY, content TEXT)")
        writer.execute("CREATE TABLE rag_memories(id INTEGER PRIMARY KEY, content TEXT)")
        writer.execute("INSERT INTO memories(content) VALUES ('first fictional row')")
        writer.commit()
        writer.execute("INSERT INTO memories(content) VALUES ('second fictional row')")
        writer.commit()
        database_before = file_hash(database)
        wal_path = database.with_name(database.name + "-wal")
        wal_before = file_hash(wal_path)

        result = create_backup(data, tmp_path / "wal backups")

        assert result.success is True and result.bundle_path is not None
        with sqlite3.connect(result.bundle_path / "databases" / "memory.sqlite") as restored:
            assert restored.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 2
        assert file_hash(database) == database_before
        assert file_hash(wal_path) == wal_before
    finally:
        writer.close()


def test_missing_optional_assets_are_tolerated_but_required_database_is_not(tmp_path: Path) -> None:
    data = tmp_path / "minimal data"
    create_synthetic_data(data, support_files=False)
    result = create_backup(data, tmp_path / "minimal backups")
    assert result.success is True
    assert result.asset_count == 1

    missing = tmp_path / "missing data"
    failed = MemoryBackupService(repository_root=tmp_path / "repo").create(
        BackupRequest(missing, tmp_path / "failed backups", confirm_private_output=True)
    )
    assert failed.success is False
    assert failed.errors[0].category == "required_asset_missing"
    assert not (tmp_path / "failed backups").exists()


def test_private_output_confirmation_and_destination_guards(tmp_path: Path) -> None:
    data = tmp_path / "data"
    create_synthetic_data(data)
    service = MemoryBackupService(repository_root=tmp_path / "repository")

    unconfirmed = service.create(BackupRequest(data, tmp_path / "output"))
    active = service.create(BackupRequest(data, data, confirm_private_output=True))
    repository = service.create(
        BackupRequest(data, tmp_path / "repository" / "backups", confirm_private_output=True)
    )

    assert unconfirmed.errors[0].category == "private_output_confirmation_required"
    assert active.errors[0].category == "unsafe_backup_destination"
    assert repository.errors[0].category == "source_controlled_backup_destination"


def test_missing_long_nested_output_path_is_created_safely(tmp_path: Path) -> None:
    data = tmp_path / "data"
    create_synthetic_data(data)
    output = tmp_path / "private output" / ("nested-" + "a" * 48) / "more nesting"

    result = create_backup(data, output)

    assert result.success is True
    assert result.bundle_path is not None
    assert result.bundle_path.parent == output.resolve()


def test_atomic_replace_retries_brief_windows_permission_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.tmp"
    destination = tmp_path / "destination.json"
    source.write_text("ready", encoding="utf-8")
    real_replace = safety.os.replace
    attempts = 0

    def briefly_locked(left: Path, right: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("synthetic Windows lock")
        real_replace(left, right)

    monkeypatch.setattr(safety.os, "replace", briefly_locked)
    monkeypatch.setattr(safety.time, "sleep", lambda _seconds: None)

    safety.replace_path(source, destination)

    assert attempts == 3
    assert destination.read_text(encoding="utf-8") == "ready"


def test_database_missing_expected_rag_table_is_rejected(tmp_path: Path) -> None:
    data = tmp_path / "incomplete schema"
    data.mkdir()
    with sqlite3.connect(data / "fibi_memory.db") as connection:
        connection.execute("CREATE TABLE memories(id INTEGER PRIMARY KEY, content TEXT)")

    result = create_backup(data, tmp_path / "backups")

    assert result.success is False
    assert result.errors[0].category == "expected_table_missing"


def test_unique_bundle_collision_never_overwrites_existing_backup(tmp_path: Path) -> None:
    data = tmp_path / "data"
    create_synthetic_data(data)
    output = tmp_path / "backups"
    first = create_backup(data, output)
    assert first.success is True and first.bundle_path is not None
    before = tree_hashes(first.bundle_path)

    second = create_backup(data, output)

    assert second.success is False
    assert second.errors[0].category == "backup_destination_collision"
    assert tree_hashes(first.bundle_path) == before


def test_existing_staging_collision_is_never_removed(tmp_path: Path) -> None:
    data = tmp_path / "data"
    create_synthetic_data(data)
    output = tmp_path / "backups"
    existing = output / ".fibi-memory-backup-staging-20260813T013000Z-fixture123"
    existing.mkdir(parents=True)
    marker = existing / "belongs-to-someone-else.txt"
    marker.write_text("preserve", encoding="utf-8")

    result = create_backup(data, output)

    assert result.success is False
    assert result.errors[0].category == "backup_destination_collision"
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_cancellation_removes_staging_and_never_finalizes(tmp_path: Path) -> None:
    data = tmp_path / "data"
    create_synthetic_data(data)
    calls = 0

    def cancel_after_discovery() -> bool:
        nonlocal calls
        calls += 1
        return calls >= 3

    output = tmp_path / "cancelled backups"
    result = MemoryBackupService(
        repository_root=tmp_path / "repo",
        id_factory=lambda: "cancel123",
        clock=lambda: FIXED_TIME,
        cancelled=cancel_after_discovery,
    ).create(BackupRequest(data, output, confirm_private_output=True))

    assert result.status == "cancelled"
    assert result.errors[0].cancelled is True
    assert not list(output.glob("fibi-memory-backup-*"))
    assert not list(output.glob(".fibi-memory-backup-staging-*"))


@pytest.mark.parametrize(
    "point",
    [
        BackupFaultPoint.SOURCE_UNAVAILABLE,
        BackupFaultPoint.DESTINATION_UNAVAILABLE,
        BackupFaultPoint.DESTINATION_UNWRITABLE,
        BackupFaultPoint.DISK_FULL,
        BackupFaultPoint.SQLITE_BACKUP_INTERRUPTED,
        BackupFaultPoint.CORRUPT_DESTINATION,
        BackupFaultPoint.MANIFEST_WRITE_FAILED,
        BackupFaultPoint.CHECKSUM_MISMATCH,
        BackupFaultPoint.REQUIRED_ASSET_MISSING,
        BackupFaultPoint.MALFORMED_MANIFEST,
        BackupFaultPoint.INVALID_SCHEMA_VERSION,
        BackupFaultPoint.INTEGRITY_CHECK_FAILED,
        BackupFaultPoint.PATH_TRAVERSAL,
        BackupFaultPoint.PROCESS_CANCELLED,
    ],
)
def test_backup_faults_leave_source_unchanged_and_no_valid_bundle(
    tmp_path: Path,
    point: BackupFaultPoint,
) -> None:
    data = tmp_path / point.value / "data"
    database = create_synthetic_data(data)
    before = file_hash(database)
    output = tmp_path / point.value / "backups"
    injector = DeterministicFaultInjector(point)

    result = MemoryBackupService(
        repository_root=tmp_path / "repo",
        fault_injector=injector,
        id_factory=lambda: "fault123",
        clock=lambda: FIXED_TIME,
    ).create(BackupRequest(data, output, confirm_private_output=True))

    assert result.success is False
    assert file_hash(database) == before
    assert not list(output.glob("fibi-memory-backup-*")) if output.exists() else True
    assert not list(output.glob(".fibi-memory-backup-staging-*")) if output.exists() else True
