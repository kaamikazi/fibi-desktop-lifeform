"""Isolated restore rehearsal; no live restore operation exists."""

from __future__ import annotations

import logging
import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fibi.memory_backup.faults import (
    BackupFaultPoint,
    CancellationCheck,
    FaultInjector,
    InjectedBackupFault,
    NoFaultInjector,
    never_cancelled,
)
from fibi.memory_backup.models import (
    REHEARSAL_EVIDENCE_VERSION,
    BackupError,
    RestoreRehearsalRequest,
    RestoreRehearsalResult,
)
from fibi.memory_backup.safety import (
    BackupSafetyError,
    is_link_like,
    replace_path,
    resolve_bundle_artifact,
    safe_remove_created_directory,
    validate_rehearsal_root,
    write_json_atomic,
)
from fibi.memory_backup.verifier import BackupVerifier

LOGGER = logging.getLogger(__name__)


class RestoreRehearsalService:
    """Prove that a verified bundle produces an independent valid copy."""

    def __init__(
        self,
        *,
        verifier: BackupVerifier | None = None,
        fault_injector: FaultInjector | None = None,
        cancelled: CancellationCheck = never_cancelled,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        repository_root: Path | None = None,
    ) -> None:
        self._faults = fault_injector or NoFaultInjector()
        self._verifier = verifier or BackupVerifier(self._faults)
        self._cancelled = cancelled
        self._id_factory = id_factory or (lambda: uuid4().hex[:12])
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._repository_root = Path(repository_root or Path(__file__).resolve().parents[2])

    def rehearse(self, request: RestoreRehearsalRequest) -> RestoreRehearsalResult:
        if not request.confirm_private_output:
            return _rehearsal_failure("private_output_confirmation_required", "request")
        verification = self._verifier.verify(
            request.backup_bundle,
            full_integrity_check=request.full_integrity_check,
        )
        if not verification.valid or verification.manifest is None:
            error = verification.errors[0] if verification.errors else BackupError("backup_invalid", "verification")
            return _rehearsal_failure(error.category, "backup_verification")
        manifest = verification.manifest
        auto_root = request.destination_root is None
        destination_root: Path | None = None
        staging: Path | None = None
        final: Path | None = None
        staging_created = False
        final_created = False
        rehearsal_id = "".join(char for char in self._id_factory() if char.isalnum())[:20] or uuid4().hex[:12]
        try:
            self._check_cancelled("request")
            if auto_root:
                destination_root = Path(tempfile.mkdtemp(prefix="fibi-memory-rehearsal-root-"))
            else:
                destination_root = Path(request.destination_root)  # type: ignore[arg-type]
            destination_root = validate_rehearsal_root(
                destination_root,
                request.active_data_root,
                request.backup_bundle,
                self._repository_root,
            )
            self._faults.check(BackupFaultPoint.REHEARSAL_DESTINATION_FAILED)
            destination_root.mkdir(parents=True, exist_ok=True)
            staging = destination_root / f".fibi-restore-rehearsal-staging-{rehearsal_id}"
            final = destination_root / f"fibi-restore-rehearsal-{rehearsal_id}"
            if staging.exists() or final.exists():
                raise BackupSafetyError("rehearsal_destination_collision")
            staging.mkdir()
            staging_created = True
            (staging / "INCOMPLETE").write_text("incomplete\n", encoding="ascii")
            shutil.copy2(Path(request.backup_bundle) / "manifest.json", staging / "manifest.json")
            for asset in manifest.assets:
                self._check_cancelled("restore_copy")
                self._faults.check(BackupFaultPoint.RESTORATION_INTERRUPTED)
                source = resolve_bundle_artifact(request.backup_bundle, asset.artifact_path)
                if is_link_like(source):
                    raise BackupSafetyError("unsafe_link_or_reparse_point")
                destination = staging.joinpath(*asset.artifact_path.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            restored = self._verifier.verify(
                staging,
                allow_incomplete_marker=True,
                full_integrity_check=request.full_integrity_check,
            )
            if not restored.valid:
                error = restored.errors[0]
                raise BackupSafetyError(error.category)
            evidence = {
                "schema_version": REHEARSAL_EVIDENCE_VERSION,
                "backup_id": manifest.backup_id,
                "created_at": self._clock().astimezone(timezone.utc).isoformat(),
                "backup_verified": True,
                "manifest_valid": True,
                "required_assets_verified": restored.required_verified_count,
                "restored_assets": restored.asset_count,
                "sqlite_integrity": "passed",
                "structurally_equivalent": True,
                "live_restore_performed": False,
            }
            write_json_atomic(staging / "rehearsal_evidence.json", evidence)
            self._check_cancelled("finalization")
            (staging / "INCOMPLETE").unlink()
            replace_path(staging, final)
            final_created = True
            staging_created = False
            staging = None
            result_path: Path | None = final
            cleaned = False
            if request.cleanup:
                cleaned = safe_remove_created_directory(final, destination_root, "fibi-restore-rehearsal-")
                if cleaned:
                    final_created = False
                    result_path = None
                if auto_root:
                    try:
                        destination_root.rmdir()
                    except OSError:
                        pass
            LOGGER.info(
                "memory_restore_rehearsal.completed",
                extra={"backup_id": manifest.backup_id, "asset_count": restored.asset_count},
            )
            return RestoreRehearsalResult(
                success=True,
                status="completed",
                backup_id=manifest.backup_id,
                restored_asset_count=restored.asset_count,
                required_verified_count=restored.required_verified_count,
                integrity="passed",
                structurally_equivalent=True,
                evidence_written=True,
                cleaned_up=cleaned,
                rehearsal_path=result_path,
            )
        except InjectedBackupFault as error:
            cancelled = error.point is BackupFaultPoint.PROCESS_CANCELLED
            failure = _rehearsal_failure(error.point.value, "injected_fault", manifest.backup_id, cancelled)
        except BackupSafetyError as error:
            failure = _rehearsal_failure(error.category, "rehearsal", manifest.backup_id)
        except OSError:
            failure = _rehearsal_failure("rehearsal_io_error", "filesystem", manifest.backup_id)
        if destination_root is not None:
            if staging_created and staging is not None:
                safe_remove_created_directory(staging, destination_root, ".fibi-restore-rehearsal-staging-")
            if final_created and final is not None:
                safe_remove_created_directory(final, destination_root, "fibi-restore-rehearsal-")
            if auto_root:
                try:
                    destination_root.rmdir()
                except OSError:
                    pass
        LOGGER.warning("memory_restore_rehearsal.failed", extra={"category": failure.errors[0].category})
        return failure

    def _check_cancelled(self, stage: str) -> None:
        self._faults.check(BackupFaultPoint.PROCESS_CANCELLED)
        if self._cancelled():
            raise InjectedBackupFault(BackupFaultPoint.PROCESS_CANCELLED)


def _rehearsal_failure(
    category: str,
    stage: str,
    backup_id: str | None = None,
    cancelled: bool = False,
) -> RestoreRehearsalResult:
    return RestoreRehearsalResult(
        success=False,
        status="cancelled" if cancelled else "failed",
        backup_id=backup_id,
        integrity="failed",
        errors=(BackupError(category, stage, cancelled=cancelled),),
    )


__all__ = ["RestoreRehearsalService"]
