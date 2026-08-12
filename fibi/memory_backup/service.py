"""Explicit creation of verified, private Fibi memory backup bundles."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fibi.memory_backup.discovery import PersistenceAssetDiscovery
from fibi.memory_backup.faults import (
    BackupFaultPoint,
    CancellationCheck,
    FaultInjector,
    InjectedBackupFault,
    NoFaultInjector,
    never_cancelled,
)
from fibi.memory_backup.models import (
    BACKUP_FORMAT_VERSION,
    EXPECTED_SQLITE_TABLES,
    AssetClassification,
    BackupAsset,
    BackupAssetManifest,
    BackupError,
    BackupManifest,
    BackupRequest,
    BackupResult,
    BackupStrategy,
)
from fibi.memory_backup.safety import (
    BackupSafetyError,
    is_link_like,
    replace_path,
    safe_remove_created_directory,
    sha256_file,
    validate_backup_output_root,
    write_json_atomic,
)
from fibi.memory_backup.sqlite_snapshot import (
    SQLiteBackupAdapter,
    SQLiteSnapshotError,
)
from fibi.memory_backup.verifier import BackupVerifier
from fibi.version import APP_VERSION

LOGGER = logging.getLogger(__name__)

_ARTIFACT_PATHS = {
    "memory_database": "databases/memory.sqlite",
    "memory_consent_state": "metadata/companion_state.json",
    "memory_deletion_audit": "metadata/memory_deletion_audit.jsonl",
}


class BackupOperationError(RuntimeError):
    def __init__(self, category: str, stage: str, asset_id: str | None = None, *, cancelled: bool = False) -> None:
        super().__init__(category)
        self.category = category
        self.stage = stage
        self.asset_id = asset_id
        self.cancelled = cancelled


class MemoryBackupService:
    """Create one verified bundle only when called explicitly."""

    def __init__(
        self,
        *,
        discovery: PersistenceAssetDiscovery | None = None,
        sqlite_backup: SQLiteBackupAdapter | None = None,
        verifier: BackupVerifier | None = None,
        fault_injector: FaultInjector | None = None,
        cancelled: CancellationCheck = never_cancelled,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        repository_root: Path | None = None,
    ) -> None:
        self._discovery = discovery or PersistenceAssetDiscovery()
        self._sqlite = sqlite_backup or SQLiteBackupAdapter()
        self._faults = fault_injector or NoFaultInjector()
        self._verifier = verifier or BackupVerifier(self._faults)
        self._cancelled = cancelled
        self._id_factory = id_factory or (lambda: uuid4().hex[:12])
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._repository_root = Path(repository_root or Path(__file__).resolve().parents[2])

    def create(self, request: BackupRequest) -> BackupResult:
        if not request.confirm_private_output:
            return _backup_failure("private_output_confirmation_required", "request")
        backup_id = self._backup_id()
        staging: Path | None = None
        final: Path | None = None
        output: Path | None = None
        staging_created = False
        final_created = False
        try:
            self._check_cancelled("request")
            plan = self._discovery.discover(
                request.data_root,
                include_migration_support=request.include_migration_support,
            )
            self._faults.check(BackupFaultPoint.REQUIRED_ASSET_MISSING)
            if plan.missing_required:
                missing = plan.missing_required[0]
                raise BackupOperationError("required_asset_missing", "discovery", missing.logical_id)
            output = validate_backup_output_root(request.output_root, request.data_root, self._repository_root)
            self._faults.check(BackupFaultPoint.DESTINATION_UNAVAILABLE)
            output.mkdir(parents=True, exist_ok=True)
            self._faults.check(BackupFaultPoint.DESTINATION_UNWRITABLE)
            staging = output / f".fibi-memory-backup-staging-{backup_id}"
            final = output / f"fibi-memory-backup-{backup_id}"
            if staging.exists() or final.exists():
                raise BackupOperationError("backup_destination_collision", "destination")
            staging.mkdir()
            staging_created = True
            (staging / "INCOMPLETE").write_text("incomplete\n", encoding="ascii")
            self._check_cancelled("discovery")
            manifests = tuple(
                self._backup_asset(asset, staging, request.full_integrity_check)
                for asset in plan.included_assets
            )
            required_count = sum(asset.required for asset in manifests)
            if required_count != sum(asset.required for asset in plan.assets):
                raise BackupOperationError("required_asset_missing", "asset_backup")
            self._check_cancelled("manifest")
            manifest = BackupManifest(
                format_version=BACKUP_FORMAT_VERSION,
                backup_id=backup_id,
                created_at=self._clock().astimezone(timezone.utc).isoformat(),
                fibi_version=APP_VERSION,
                complete=True,
                integrity_check="integrity_check" if request.full_integrity_check else "quick_check",
                assets=manifests,
                omitted_derived_asset_ids=tuple(
                    sorted(
                        asset.logical_id
                        for asset in plan.assets
                        if asset.classification is AssetClassification.DERIVED_REBUILDABLE
                    )
                ),
                out_of_scope_asset_ids=tuple(
                    sorted(
                        asset.logical_id
                        for asset in plan.assets
                        if asset.classification is AssetClassification.OUT_OF_SCOPE
                    )
                ),
            )
            self._faults.check(BackupFaultPoint.MANIFEST_WRITE_FAILED)
            write_json_atomic(staging / "manifest.json", manifest.to_dict())
            staging_verification = self._verifier.verify(
                staging,
                allow_incomplete_marker=True,
                full_integrity_check=request.full_integrity_check,
            )
            if not staging_verification.valid:
                first = staging_verification.errors[0]
                raise BackupOperationError(first.category, "verification", first.logical_asset_id)
            self._check_cancelled("finalization")
            incomplete = staging / "INCOMPLETE"
            incomplete.unlink()
            replace_path(staging, final)
            final_created = True
            staging_created = False
            staging = None
            final_verification = self._verifier.verify(
                final,
                full_integrity_check=request.full_integrity_check,
            )
            if not final_verification.valid:
                (final / "INCOMPLETE").write_text("verification failed\n", encoding="ascii")
                first = final_verification.errors[0]
                raise BackupOperationError(first.category, "final_verification", first.logical_asset_id)
            LOGGER.info(
                "memory_backup.created",
                extra={"backup_id": backup_id, "asset_count": len(manifests)},
            )
            return BackupResult(
                success=True,
                status="created",
                backup_id=backup_id,
                asset_count=len(manifests),
                required_asset_count=final_verification.required_asset_count,
                required_verified_count=final_verification.required_verified_count,
                integrity="passed",
                manifest_valid=True,
                bundle_path=final,
            )
        except InjectedBackupFault as error:
            cancelled = error.point is BackupFaultPoint.PROCESS_CANCELLED
            failure = _backup_failure(error.point.value, "injected_fault", backup_id, cancelled=cancelled)
        except BackupOperationError as error:
            failure = _backup_failure(
                error.category,
                error.stage,
                backup_id,
                error.asset_id,
                cancelled=error.cancelled,
            )
        except SQLiteSnapshotError as error:
            failure = _backup_failure(error.category, "sqlite_backup", backup_id, cancelled=error.cancelled)
        except BackupSafetyError as error:
            failure = _backup_failure(error.category, "destination", backup_id)
        except OSError:
            failure = _backup_failure("backup_io_error", "filesystem", backup_id)
        if request.cleanup_incomplete and output is not None:
            if staging_created and staging is not None:
                safe_remove_created_directory(staging, output, ".fibi-memory-backup-staging-")
            if final_created and final is not None:
                safe_remove_created_directory(final, output, "fibi-memory-backup-")
        LOGGER.warning("memory_backup.failed", extra={"category": failure.errors[0].category})
        return failure

    def _backup_asset(
        self,
        asset: BackupAsset,
        staging: Path,
        full_integrity_check: bool,
    ) -> BackupAssetManifest:
        self._check_cancelled("asset_backup", asset.logical_id)
        if is_link_like(asset.source_path):
            raise BackupOperationError("unsafe_source_link", "asset_backup", asset.logical_id)
        artifact_relative = _ARTIFACT_PATHS.get(asset.logical_id)
        if artifact_relative is None:
            raise BackupOperationError("unsupported_backup_asset", "asset_backup", asset.logical_id)
        destination = staging.joinpath(*artifact_relative.split("/"))
        if asset.strategy is BackupStrategy.SQLITE_BACKUP_API:
            result = self._sqlite.backup(
                asset.source_path,
                destination,
                full_integrity_check=full_integrity_check,
                fault_injector=self._faults,
                cancelled=self._cancelled,
            )
            structure = result.structure
            expected_tables = EXPECTED_SQLITE_TABLES.get(asset.logical_id, frozenset())
            if not expected_tables.issubset(structure.table_names):
                destination.unlink(missing_ok=True)
                raise BackupOperationError("expected_table_missing", "sqlite_backup", asset.logical_id)
            size_bytes = result.size_bytes
            verification = structure.integrity_check
            user_version = structure.user_version
            fingerprint = structure.schema_fingerprint
            tables = structure.table_names
        elif asset.strategy is BackupStrategy.VERIFIED_FILE_COPY:
            size_bytes = self._copy_support_asset(asset, destination)
            verification = "checksum"
            user_version = None
            fingerprint = None
            tables = ()
        else:
            raise BackupOperationError("unsupported_backup_strategy", "asset_backup", asset.logical_id)
        return BackupAssetManifest(
            logical_id=asset.logical_id,
            classification=asset.classification.value,
            asset_type=asset.asset_type,
            required=asset.required,
            strategy=asset.strategy.value,
            source_logical_path=asset.source_logical_path,
            artifact_path=artifact_relative,
            size_bytes=size_bytes,
            sha256=sha256_file(destination),
            sqlite_user_version=user_version,
            schema_fingerprint=fingerprint,
            table_names=tables,
            verification=verification,
            verified=True,
        )

    def _copy_support_asset(self, asset: BackupAsset, destination: Path) -> int:
        if not asset.source_path.is_file():
            raise BackupOperationError("support_asset_missing", "asset_backup", asset.logical_id)
        before = asset.source_path.stat()
        source_hash_before = sha256_file(asset.source_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset.source_path, destination)
        after = asset.source_path.stat()
        source_hash_after = sha256_file(asset.source_path)
        destination_hash = sha256_file(destination)
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or source_hash_before != source_hash_after
            or destination_hash != source_hash_before
        ):
            destination.unlink(missing_ok=True)
            raise BackupOperationError("support_asset_changed", "asset_backup", asset.logical_id)
        return destination.stat().st_size

    def _check_cancelled(self, stage: str, asset_id: str | None = None) -> None:
        self._faults.check(BackupFaultPoint.PROCESS_CANCELLED)
        if self._cancelled():
            raise BackupOperationError("cancelled", stage, asset_id, cancelled=True)

    def _backup_id(self) -> str:
        timestamp = self._clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = "".join(char for char in self._id_factory() if char.isalnum())[:20]
        if not suffix:
            suffix = uuid4().hex[:12]
        return f"{timestamp}-{suffix}"


def _backup_failure(
    category: str,
    stage: str,
    backup_id: str | None = None,
    asset_id: str | None = None,
    *,
    cancelled: bool = False,
) -> BackupResult:
    return BackupResult(
        success=False,
        status="cancelled" if cancelled else "failed",
        backup_id=backup_id,
        integrity="not_run",
        manifest_valid=False,
        errors=(BackupError(category, stage, asset_id, cancelled),),
    )


__all__ = ["BackupOperationError", "MemoryBackupService"]
