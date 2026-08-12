"""Immutable contracts for verified memory backups and restore rehearsals."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

BACKUP_FORMAT_VERSION = "fibi.memory-backup.v1"
REHEARSAL_EVIDENCE_VERSION = "fibi.memory-restore-evidence.v1"
REQUIRED_ASSET_IDS = frozenset({"memory_database"})
EXPECTED_SQLITE_TABLES = {
    "memory_database": frozenset({"memories", "rag_memories"}),
}


class AssetClassification(str, Enum):
    PRIMARY_PERSISTENCE = "primary_persistence"
    MIGRATION_SUPPORT = "migration_support"
    DERIVED_REBUILDABLE = "derived_rebuildable"
    OUT_OF_SCOPE = "out_of_scope"


class BackupStrategy(str, Enum):
    SQLITE_BACKUP_API = "sqlite_backup_api"
    VERIFIED_FILE_COPY = "verified_file_copy"
    OMIT_DERIVED = "omit_derived"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class BackupAsset:
    logical_id: str
    classification: AssetClassification
    asset_type: str
    required: bool
    strategy: BackupStrategy
    source_logical_path: str
    exists: bool
    included: bool
    source_path: Path = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class BackupPlan:
    assets: tuple[BackupAsset, ...]
    data_root: Path = field(repr=False, compare=False)

    @property
    def missing_required(self) -> tuple[BackupAsset, ...]:
        return tuple(asset for asset in self.assets if asset.required and not asset.exists)

    @property
    def included_assets(self) -> tuple[BackupAsset, ...]:
        return tuple(asset for asset in self.assets if asset.included and asset.exists)


@dataclass(frozen=True, slots=True)
class BackupRequest:
    data_root: Path = field(repr=False, compare=False)
    output_root: Path = field(repr=False, compare=False)
    confirm_private_output: bool = False
    include_migration_support: bool = True
    full_integrity_check: bool = False
    cleanup_incomplete: bool = True


@dataclass(frozen=True, slots=True)
class BackupAssetManifest:
    logical_id: str
    classification: str
    asset_type: str
    required: bool
    strategy: str
    source_logical_path: str
    artifact_path: str
    size_bytes: int
    sha256: str
    sqlite_user_version: int | None = None
    schema_fingerprint: str | None = None
    table_names: tuple[str, ...] = ()
    verification: str = "checksum"
    verified: bool = False


@dataclass(frozen=True, slots=True)
class BackupManifest:
    format_version: str
    backup_id: str
    created_at: str
    fibi_version: str
    complete: bool
    integrity_check: str
    assets: tuple[BackupAssetManifest, ...]
    omitted_derived_asset_ids: tuple[str, ...] = ()
    out_of_scope_asset_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BackupError:
    category: str
    stage: str
    logical_asset_id: str | None = None
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class BackupResult:
    success: bool
    status: str
    backup_id: str | None = None
    asset_count: int = 0
    required_asset_count: int = 0
    required_verified_count: int = 0
    integrity: str = "not_run"
    manifest_valid: bool = False
    errors: tuple[BackupError, ...] = ()
    bundle_path: Path | None = field(default=None, repr=False, compare=False)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fibi.memory-backup-result.v1",
            "success": self.success,
            "status": self.status,
            "backup_id": self.backup_id,
            "asset_count": self.asset_count,
            "required_asset_count": self.required_asset_count,
            "required_verified_count": self.required_verified_count,
            "integrity": self.integrity,
            "manifest_valid": self.manifest_valid,
            "errors": [asdict(error) for error in self.errors],
        }


@dataclass(frozen=True, slots=True)
class BackupVerificationResult:
    valid: bool
    backup_id: str | None = None
    format_version: str | None = None
    asset_count: int = 0
    required_asset_count: int = 0
    required_verified_count: int = 0
    integrity: str = "not_run"
    manifest_valid: bool = False
    errors: tuple[BackupError, ...] = ()
    manifest: BackupManifest | None = field(default=None, repr=False, compare=False)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fibi.memory-backup-verification.v1",
            "valid": self.valid,
            "backup_id": self.backup_id,
            "format_version": self.format_version,
            "asset_count": self.asset_count,
            "required_asset_count": self.required_asset_count,
            "required_verified_count": self.required_verified_count,
            "integrity": self.integrity,
            "manifest_valid": self.manifest_valid,
            "errors": [asdict(error) for error in self.errors],
        }


@dataclass(frozen=True, slots=True)
class RestoreRehearsalRequest:
    backup_bundle: Path = field(repr=False, compare=False)
    active_data_root: Path = field(repr=False, compare=False)
    destination_root: Path | None = field(default=None, repr=False, compare=False)
    confirm_private_output: bool = False
    cleanup: bool = True
    full_integrity_check: bool = False


@dataclass(frozen=True, slots=True)
class RestoreRehearsalResult:
    success: bool
    status: str
    backup_id: str | None = None
    restored_asset_count: int = 0
    required_verified_count: int = 0
    integrity: str = "not_run"
    structurally_equivalent: bool = False
    evidence_written: bool = False
    cleaned_up: bool = False
    errors: tuple[BackupError, ...] = ()
    rehearsal_path: Path | None = field(default=None, repr=False, compare=False)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "fibi.memory-restore-rehearsal-result.v1",
            "success": self.success,
            "status": self.status,
            "backup_id": self.backup_id,
            "restored_asset_count": self.restored_asset_count,
            "required_verified_count": self.required_verified_count,
            "integrity": self.integrity,
            "structurally_equivalent": self.structurally_equivalent,
            "evidence_written": self.evidence_written,
            "cleaned_up": self.cleaned_up,
            "errors": [asdict(error) for error in self.errors],
        }


__all__ = [
    "BACKUP_FORMAT_VERSION",
    "EXPECTED_SQLITE_TABLES",
    "REHEARSAL_EVIDENCE_VERSION",
    "REQUIRED_ASSET_IDS",
    "AssetClassification",
    "BackupAsset",
    "BackupAssetManifest",
    "BackupError",
    "BackupManifest",
    "BackupPlan",
    "BackupRequest",
    "BackupResult",
    "BackupStrategy",
    "BackupVerificationResult",
    "RestoreRehearsalRequest",
    "RestoreRehearsalResult",
]
