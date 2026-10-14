"""Untrusted-manifest and backup-integrity tests."""

from __future__ import annotations

import json
import shutil
import stat
from types import SimpleNamespace
from pathlib import Path

import pytest

from fibi.memory_backup import verifier as verifier_module
from fibi.memory_backup import safety as safety_module
from fibi.memory_backup.verifier import BackupVerifier
from tests.memory_backup_test_support import (
    create_backup,
    create_synthetic_data,
    file_hash,
    read_manifest,
    write_manifest,
)


@pytest.fixture
def valid_bundle(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    create_synthetic_data(data)
    result = create_backup(data, tmp_path / "backups")
    assert result.success is True and result.bundle_path is not None
    return result.bundle_path


def _copy_bundle(bundle: Path, target: Path) -> Path:
    shutil.copytree(bundle, target)
    return target


def test_valid_manifest_is_deterministic_and_structurally_verified(valid_bundle: Path) -> None:
    result = BackupVerifier().verify(valid_bundle)
    assert result.valid is True
    assert result.format_version == "fibi.memory-backup.v1"
    assert result.asset_count == 3
    assert result.required_verified_count == 1
    assert result.integrity == "passed"


def test_ordinary_artifacts_remain_contained_and_valid(valid_bundle: Path) -> None:
    manifest = read_manifest(valid_bundle)
    relative = manifest["assets"][0]["artifact_path"]

    resolved = safety_module.resolve_bundle_artifact(valid_bundle, relative)
    result = BackupVerifier().verify(valid_bundle)

    assert resolved == (valid_bundle / relative).resolve()
    assert resolved.is_file()
    assert result.valid is True


@pytest.mark.parametrize(
    ("mutation", "category"),
    [
        ("malformed", "manifest_malformed"),
        ("unsupported_version", "manifest_version_unsupported"),
        ("missing_required_id", "required_asset_missing"),
        ("duplicate_id", "duplicate_asset_identifier"),
        ("duplicate_path", "duplicate_artifact_path"),
        ("path_traversal", "unsafe_manifest_path"),
        ("absolute_source", "unsafe_source_logical_path"),
        ("schema_mismatch", "sqlite_structure_mismatch"),
        ("integrity_level_mismatch", "manifest_integrity_level_mismatch"),
    ],
)
def test_manifest_tampering_is_rejected(
    valid_bundle: Path,
    tmp_path: Path,
    mutation: str,
    category: str,
) -> None:
    bundle = _copy_bundle(valid_bundle, tmp_path / f"tampered-{mutation}")
    if mutation == "malformed":
        (bundle / "manifest.json").write_text("{broken", encoding="utf-8")
    else:
        manifest = read_manifest(bundle)
        if mutation == "unsupported_version":
            manifest["format_version"] = "fibi.memory-backup.v999"
        elif mutation == "missing_required_id":
            manifest["assets"] = [item for item in manifest["assets"] if item["logical_id"] != "memory_database"]
        elif mutation == "duplicate_id":
            manifest["assets"][1]["logical_id"] = manifest["assets"][0]["logical_id"]
        elif mutation == "duplicate_path":
            manifest["assets"][1]["artifact_path"] = manifest["assets"][0]["artifact_path"]
        elif mutation == "path_traversal":
            manifest["assets"][0]["artifact_path"] = "databases/../../escape.sqlite"
        elif mutation == "absolute_source":
            manifest["assets"][0]["source_logical_path"] = "C:/private/memory.db"
        elif mutation == "schema_mismatch":
            manifest["assets"][0]["schema_fingerprint"] = "0" * 64
        elif mutation == "integrity_level_mismatch":
            manifest["integrity_check"] = "integrity_check"
        write_manifest(bundle, manifest)

    result = BackupVerifier().verify(bundle)

    assert result.valid is False
    assert result.errors[0].category == category


def test_checksum_mismatch_missing_asset_and_unexpected_file_are_rejected(
    valid_bundle: Path,
    tmp_path: Path,
) -> None:
    checksum = _copy_bundle(valid_bundle, tmp_path / "checksum")
    database = checksum / "databases" / "memory.sqlite"
    changed = bytearray(database.read_bytes())
    changed[-1] ^= 1
    database.write_bytes(changed)
    assert BackupVerifier().verify(checksum).errors[0].category == "checksum_mismatch"

    missing = _copy_bundle(valid_bundle, tmp_path / "missing")
    (missing / "databases" / "memory.sqlite").unlink()
    assert BackupVerifier().verify(missing).errors[0].category == "required_asset_missing"

    unexpected = _copy_bundle(valid_bundle, tmp_path / "unexpected")
    (unexpected / "private-extra.txt").write_text("unexpected", encoding="utf-8")
    assert BackupVerifier().verify(unexpected).errors[0].category == "unexpected_artifact"


def test_truncated_database_fails_integrity_even_with_matching_manifest_checksum(
    valid_bundle: Path,
    tmp_path: Path,
) -> None:
    bundle = _copy_bundle(valid_bundle, tmp_path / "truncated")
    database = bundle / "databases" / "memory.sqlite"
    database.write_bytes(database.read_bytes()[:128])
    manifest = read_manifest(bundle)
    memory = next(item for item in manifest["assets"] if item["logical_id"] == "memory_database")
    memory["size_bytes"] = database.stat().st_size
    memory["sha256"] = file_hash(database)
    write_manifest(bundle, manifest)

    result = BackupVerifier().verify(bundle)

    assert result.valid is False
    assert result.errors[0].category in {"sqlite_unavailable_or_invalid", "sqlite_integrity_failed"}


def test_incomplete_bundle_and_symlink_artifact_are_rejected(
    valid_bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incomplete = _copy_bundle(valid_bundle, tmp_path / "incomplete")
    (incomplete / "INCOMPLETE").write_text("incomplete", encoding="ascii")
    assert BackupVerifier().verify(incomplete).errors[0].category == "backup_incomplete"

    link_bundle = _copy_bundle(valid_bundle, tmp_path / "link-bundle")
    artifact = link_bundle / "metadata" / "companion_state.json"
    artifact.unlink()
    outside_artifact = valid_bundle / "metadata" / "companion_state.json"
    try:
        artifact.symlink_to(outside_artifact)
    except OSError:
        pytest.skip("symlink creation is unavailable in this environment")

    real_hash = verifier_module.sha256_file
    hashed_paths: list[Path] = []

    def hash_only_bundle_artifacts(path: Path) -> str:
        candidate = Path(path).resolve()
        assert candidate != outside_artifact.resolve()
        hashed_paths.append(candidate)
        return real_hash(path)

    monkeypatch.setattr(verifier_module, "sha256_file", hash_only_bundle_artifacts)
    result = BackupVerifier().verify(link_bundle)

    assert result.errors[0].category == "unsafe_link_or_reparse_point"
    assert outside_artifact.resolve() not in hashed_paths


def test_linked_ancestor_directory_is_rejected_before_reading_target(
    valid_bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _copy_bundle(valid_bundle, tmp_path / "linked-ancestor")
    outside_directory = tmp_path / "external-directory"
    outside_directory.mkdir()
    outside_artifact = outside_directory / "companion_state.json"
    outside_artifact.write_text("synthetic external content", encoding="utf-8")
    link = bundle / "metadata" / "linked"
    try:
        link.symlink_to(outside_directory, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable in this environment")

    manifest = read_manifest(bundle)
    companion = next(item for item in manifest["assets"] if item["logical_id"] == "memory_consent_state")
    companion["artifact_path"] = "metadata/linked/companion_state.json"
    write_manifest(bundle, manifest)

    real_hash = verifier_module.sha256_file

    def hash_only_bundle_artifacts(path: Path) -> str:
        assert Path(path).resolve() != outside_artifact.resolve()
        return real_hash(path)

    monkeypatch.setattr(verifier_module, "sha256_file", hash_only_bundle_artifacts)
    result = BackupVerifier().verify(bundle)

    assert result.errors[0].category == "unsafe_link_or_reparse_point"


def test_junction_artifact_is_rejected_with_platform_independent_mock(
    valid_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = valid_bundle / "metadata" / "companion_state.json"
    monkeypatch.setattr(Path, "is_junction", lambda path: path == artifact, raising=False)

    result = BackupVerifier().verify(valid_bundle)

    assert result.errors[0].category == "unsafe_link_or_reparse_point"


def test_windows_reparse_attribute_is_classified_as_link_like(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "reparse-artifact"
    original_symlink = Path.is_symlink
    original_lstat = Path.lstat
    original_junction = getattr(Path, "is_junction", None)

    def is_symlink(path: Path) -> bool:
        return False if path == artifact else original_symlink(path)

    def is_junction(path: Path) -> bool:
        if path == artifact:
            return False
        return bool(original_junction and original_junction(path))

    def lstat(path: Path):
        if path == artifact:
            return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
        return original_lstat(path)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    monkeypatch.setattr(Path, "is_junction", is_junction, raising=False)
    monkeypatch.setattr(Path, "lstat", lstat)

    assert safety_module.is_link_like(artifact) is True


def test_manifest_and_verification_output_never_expose_private_payload(valid_bundle: Path) -> None:
    rendered = json.dumps(BackupVerifier().verify(valid_bundle).to_public_dict())
    assert "Fictional comet" not in rendered
    assert str(valid_bundle) not in rendered
    assert "sha256" not in rendered


def test_manifest_full_integrity_level_is_honored(
    valid_bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = read_manifest(valid_bundle)
    manifest["integrity_check"] = "integrity_check"
    manifest["assets"][0]["verification"] = "integrity_check"
    write_manifest(valid_bundle, manifest)
    calls: list[bool] = []
    real_inspect = verifier_module.inspect_sqlite

    def inspect_at_declared_level(path: Path, *, full_integrity_check: bool = False):
        calls.append(full_integrity_check)
        return real_inspect(path, full_integrity_check=full_integrity_check)

    monkeypatch.setattr(verifier_module, "inspect_sqlite", inspect_at_declared_level)

    result = BackupVerifier().verify(valid_bundle)

    assert result.valid is True
    assert calls == [True]
