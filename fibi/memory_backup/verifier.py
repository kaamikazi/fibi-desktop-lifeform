"""Strict verification for untrusted local memory backup bundles."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fibi.memory_backup.faults import (
    BackupFaultPoint,
    FaultInjector,
    InjectedBackupFault,
    NoFaultInjector,
)
from fibi.memory_backup.models import (
    BACKUP_FORMAT_VERSION,
    EXPECTED_SQLITE_TABLES,
    REQUIRED_ASSET_IDS,
    AssetClassification,
    BackupAssetManifest,
    BackupError,
    BackupManifest,
    BackupStrategy,
    BackupVerificationResult,
)
from fibi.memory_backup.safety import (
    BackupSafetyError,
    is_link_like,
    resolve_bundle_artifact,
    safe_relative_path,
    sha256_file,
)
from fibi.memory_backup.sqlite_snapshot import SQLiteSnapshotError, inspect_sqlite

_HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")
_MANIFEST_KEYS = {
    "format_version",
    "backup_id",
    "created_at",
    "fibi_version",
    "complete",
    "integrity_check",
    "assets",
    "omitted_derived_asset_ids",
    "out_of_scope_asset_ids",
}
_ASSET_KEYS = {
    "logical_id",
    "classification",
    "asset_type",
    "required",
    "strategy",
    "source_logical_path",
    "artifact_path",
    "size_bytes",
    "sha256",
    "sqlite_user_version",
    "schema_fingerprint",
    "table_names",
    "verification",
    "verified",
}


class ManifestValidationError(ValueError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class BackupVerifier:
    """Verify manifest shape, paths, checksums, and SQLite structure."""

    def __init__(self, fault_injector: FaultInjector | None = None) -> None:
        self._faults = fault_injector or NoFaultInjector()

    def verify(
        self,
        bundle_path: Path,
        *,
        allow_incomplete_marker: bool = False,
        full_integrity_check: bool = False,
    ) -> BackupVerificationResult:
        bundle = Path(bundle_path)
        try:
            if not bundle.is_dir() or is_link_like(bundle):
                raise ManifestValidationError("backup_bundle_unavailable")
            incomplete = bundle / "INCOMPLETE"
            if incomplete.exists() and not allow_incomplete_marker:
                raise ManifestValidationError("backup_incomplete")
            manifest_path = bundle / "manifest.json"
            if not manifest_path.is_file() or is_link_like(manifest_path):
                raise ManifestValidationError("manifest_missing")
            if manifest_path.stat().st_size > 1024 * 1024:
                raise ManifestValidationError("manifest_too_large")
            self._faults.check(BackupFaultPoint.MALFORMED_MANIFEST)
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise ManifestValidationError("manifest_malformed") from error
            self._faults.check(BackupFaultPoint.INVALID_SCHEMA_VERSION)
            manifest = parse_manifest(raw)
            if manifest.format_version != BACKUP_FORMAT_VERSION:
                raise ManifestValidationError("manifest_version_unsupported")
            if not manifest.complete:
                raise ManifestValidationError("manifest_not_complete")
            effective_full_check = full_integrity_check or manifest.integrity_check == "integrity_check"
            asset_ids = {asset.logical_id for asset in manifest.assets}
            self._faults.check(BackupFaultPoint.REQUIRED_ASSET_MISSING)
            if not REQUIRED_ASSET_IDS.issubset(asset_ids):
                raise ManifestValidationError("required_asset_missing")
            required_verified = 0
            allowed_files = {"manifest.json"}
            if allow_incomplete_marker and incomplete.exists():
                allowed_files.add("INCOMPLETE")
            for asset in manifest.assets:
                self._faults.check(BackupFaultPoint.PATH_TRAVERSAL)
                artifact = resolve_bundle_artifact(bundle, asset.artifact_path)
                if is_link_like(artifact):
                    raise ManifestValidationError("unsafe_link_or_reparse_point")
                if not artifact.is_file():
                    category = "required_asset_missing" if asset.required else "asset_missing"
                    raise ManifestValidationError(category)
                allowed_files.add(asset.artifact_path)
                if artifact.stat().st_size != asset.size_bytes:
                    raise ManifestValidationError("asset_size_mismatch")
                self._faults.check(BackupFaultPoint.CHECKSUM_MISMATCH)
                if sha256_file(artifact) != asset.sha256:
                    raise ManifestValidationError("checksum_mismatch")
                if asset.asset_type == "sqlite_database":
                    if asset.verification != manifest.integrity_check:
                        raise ManifestValidationError("manifest_integrity_level_mismatch")
                    try:
                        structure = inspect_sqlite(
                            artifact,
                            full_integrity_check=effective_full_check,
                        )
                        self._faults.check(BackupFaultPoint.INTEGRITY_CHECK_FAILED)
                    except (SQLiteSnapshotError, InjectedBackupFault) as error:
                        if isinstance(error, InjectedBackupFault):
                            raise
                        raise ManifestValidationError(error.category) from error
                    if (
                        structure.user_version != asset.sqlite_user_version
                        or structure.schema_fingerprint != asset.schema_fingerprint
                        or structure.table_names != asset.table_names
                    ):
                        raise ManifestValidationError("sqlite_structure_mismatch")
                    expected_tables = EXPECTED_SQLITE_TABLES.get(asset.logical_id, frozenset())
                    if not expected_tables.issubset(structure.table_names):
                        raise ManifestValidationError("expected_table_missing")
                    if asset.size_bytes <= 0:
                        raise ManifestValidationError("sqlite_empty")
                if asset.required:
                    required_verified += 1
            self._reject_unexpected_artifacts(bundle, allowed_files)
            required_count = sum(asset.required for asset in manifest.assets)
            return BackupVerificationResult(
                valid=True,
                backup_id=manifest.backup_id,
                format_version=manifest.format_version,
                asset_count=len(manifest.assets),
                required_asset_count=required_count,
                required_verified_count=required_verified,
                integrity="passed",
                manifest_valid=True,
                manifest=manifest,
            )
        except InjectedBackupFault as error:
            return _verification_failure(error.point.value, "verification")
        except (ManifestValidationError, BackupSafetyError) as error:
            category = error.category
            return _verification_failure(category, "verification")
        except OSError:
            return _verification_failure("verification_io_error", "verification")

    @staticmethod
    def _reject_unexpected_artifacts(bundle: Path, allowed_files: set[str]) -> None:
        for path in bundle.rglob("*"):
            if is_link_like(path):
                raise ManifestValidationError("unsafe_link_or_reparse_point")
            if not path.is_file():
                continue
            relative = path.relative_to(bundle).as_posix()
            if relative not in allowed_files:
                raise ManifestValidationError("unexpected_artifact")


def parse_manifest(raw: Any) -> BackupManifest:
    if not isinstance(raw, dict) or set(raw) != _MANIFEST_KEYS:
        raise ManifestValidationError("manifest_schema_invalid")
    format_version = _text(raw, "format_version", 80)
    backup_id = _identifier(raw, "backup_id")
    created_at = _text(raw, "created_at", 80)
    fibi_version = _text(raw, "fibi_version", 40)
    complete = _boolean(raw, "complete")
    integrity_check = _text(raw, "integrity_check", 32)
    if integrity_check not in {"quick_check", "integrity_check"}:
        raise ManifestValidationError("manifest_schema_invalid")
    assets_raw = raw.get("assets")
    if not isinstance(assets_raw, list) or not 1 <= len(assets_raw) <= 16:
        raise ManifestValidationError("manifest_schema_invalid")
    assets = tuple(_parse_asset(item) for item in assets_raw)
    identifiers = [asset.logical_id for asset in assets]
    paths = [asset.artifact_path for asset in assets]
    if len(set(identifiers)) != len(identifiers):
        raise ManifestValidationError("duplicate_asset_identifier")
    if len(set(paths)) != len(paths):
        raise ManifestValidationError("duplicate_artifact_path")
    for required_id in REQUIRED_ASSET_IDS & set(identifiers):
        asset = next(item for item in assets if item.logical_id == required_id)
        if not asset.required:
            raise ManifestValidationError("required_asset_flag_invalid")
    return BackupManifest(
        format_version=format_version,
        backup_id=backup_id,
        created_at=created_at,
        fibi_version=fibi_version,
        complete=complete,
        integrity_check=integrity_check,
        assets=assets,
        omitted_derived_asset_ids=_identifier_list(raw, "omitted_derived_asset_ids"),
        out_of_scope_asset_ids=_identifier_list(raw, "out_of_scope_asset_ids"),
    )


def _parse_asset(raw: Any) -> BackupAssetManifest:
    if not isinstance(raw, dict) or set(raw) != _ASSET_KEYS:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    logical_id = _identifier(raw, "logical_id")
    classification = _text(raw, "classification", 48)
    strategy = _text(raw, "strategy", 48)
    if classification not in {item.value for item in AssetClassification}:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    if strategy not in {item.value for item in BackupStrategy}:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    source_logical_path = _text(raw, "source_logical_path", 240)
    artifact_path = _text(raw, "artifact_path", 240)
    if not source_logical_path.startswith("data/"):
        raise ManifestValidationError("unsafe_source_logical_path")
    safe_relative_path(source_logical_path)
    safe_artifact = safe_relative_path(artifact_path)
    if safe_artifact.parts[0] not in {"databases", "metadata"}:
        raise ManifestValidationError("unsafe_manifest_path")
    sensitive_basename = "." + "env"
    all_path_parts = (*safe_artifact.parts, *safe_relative_path(source_logical_path).parts)
    if any(part.casefold().startswith(sensitive_basename) for part in all_path_parts):
        raise ManifestValidationError("sensitive_manifest_path")
    size = raw.get("size_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    checksum = _text(raw, "sha256", 64)
    if not _HASH_PATTERN.fullmatch(checksum):
        raise ManifestValidationError("manifest_asset_schema_invalid")
    user_version = raw.get("sqlite_user_version")
    if user_version is not None and (not isinstance(user_version, int) or isinstance(user_version, bool)):
        raise ManifestValidationError("manifest_asset_schema_invalid")
    schema_fingerprint = raw.get("schema_fingerprint")
    if schema_fingerprint is not None and (
        not isinstance(schema_fingerprint, str) or not _HASH_PATTERN.fullmatch(schema_fingerprint)
    ):
        raise ManifestValidationError("manifest_asset_schema_invalid")
    table_names_raw = raw.get("table_names")
    if not isinstance(table_names_raw, list) or len(table_names_raw) > 128:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    table_names = tuple(table_names_raw)
    if any(not isinstance(name, str) or not name or len(name) > 128 for name in table_names):
        raise ManifestValidationError("manifest_asset_schema_invalid")
    if tuple(sorted(set(table_names))) != table_names:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    asset_type = _text(raw, "asset_type", 48)
    verification = _text(raw, "verification", 48)
    verified = _boolean(raw, "verified")
    if not verified:
        raise ManifestValidationError("manifest_asset_unverified")
    if classification not in {
        AssetClassification.PRIMARY_PERSISTENCE.value,
        AssetClassification.MIGRATION_SUPPORT.value,
    }:
        raise ManifestValidationError("manifest_asset_classification_invalid")
    if asset_type == "sqlite_database":
        if strategy != BackupStrategy.SQLITE_BACKUP_API.value or verification not in {
            "quick_check",
            "integrity_check",
        }:
            raise ManifestValidationError("manifest_asset_schema_invalid")
        if user_version is None or schema_fingerprint is None:
            raise ManifestValidationError("manifest_asset_schema_invalid")
    elif asset_type in {"json_file", "jsonl_file"}:
        if strategy != BackupStrategy.VERIFIED_FILE_COPY.value or verification != "checksum":
            raise ManifestValidationError("manifest_asset_schema_invalid")
        if user_version is not None or schema_fingerprint is not None or table_names:
            raise ManifestValidationError("manifest_asset_schema_invalid")
    else:
        raise ManifestValidationError("manifest_asset_schema_invalid")
    return BackupAssetManifest(
        logical_id=logical_id,
        classification=classification,
        asset_type=asset_type,
        required=_boolean(raw, "required"),
        strategy=strategy,
        source_logical_path=source_logical_path,
        artifact_path=artifact_path,
        size_bytes=size,
        sha256=checksum,
        sqlite_user_version=user_version,
        schema_fingerprint=schema_fingerprint,
        table_names=table_names,
        verification=verification,
        verified=verified,
    )


def _text(raw: dict[str, Any], key: str, maximum: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value or len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ManifestValidationError("manifest_schema_invalid")
    return value


def _identifier(raw: dict[str, Any], key: str) -> str:
    value = _text(raw, key, 96)
    if not _ID_PATTERN.fullmatch(value):
        raise ManifestValidationError("manifest_schema_invalid")
    return value


def _identifier_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or len(value) > 32:
        raise ManifestValidationError("manifest_schema_invalid")
    identifiers = tuple(value)
    if any(not isinstance(item, str) or not _ID_PATTERN.fullmatch(item) for item in identifiers):
        raise ManifestValidationError("manifest_schema_invalid")
    if len(set(identifiers)) != len(identifiers):
        raise ManifestValidationError("manifest_schema_invalid")
    return tuple(sorted(identifiers))


def _boolean(raw: dict[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ManifestValidationError("manifest_schema_invalid")
    return value


def _verification_failure(category: str, stage: str) -> BackupVerificationResult:
    return BackupVerificationResult(
        valid=False,
        integrity="failed",
        manifest_valid=category not in {
            "manifest_missing",
            "manifest_malformed",
            "manifest_schema_invalid",
            "manifest_asset_schema_invalid",
            "manifest_version_unsupported",
        },
        errors=(BackupError(category, stage),),
    )


__all__ = ["BackupVerifier", "ManifestValidationError", "parse_manifest"]
