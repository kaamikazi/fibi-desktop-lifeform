"""Small injected fault and cancellation boundary for deterministic tests."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Protocol


class BackupFaultPoint(str, Enum):
    SOURCE_UNAVAILABLE = "source_unavailable"
    DESTINATION_UNAVAILABLE = "destination_unavailable"
    DESTINATION_UNWRITABLE = "destination_unwritable"
    DISK_FULL = "disk_full"
    SQLITE_BACKUP_INTERRUPTED = "sqlite_backup_interrupted"
    CORRUPT_DESTINATION = "corrupt_destination"
    MANIFEST_WRITE_FAILED = "manifest_write_failed"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    REQUIRED_ASSET_MISSING = "required_asset_missing"
    MALFORMED_MANIFEST = "malformed_manifest"
    INVALID_SCHEMA_VERSION = "invalid_schema_version"
    REHEARSAL_DESTINATION_FAILED = "rehearsal_destination_failed"
    RESTORATION_INTERRUPTED = "restoration_interrupted"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    PATH_TRAVERSAL = "path_traversal"
    PROCESS_CANCELLED = "process_cancelled"


class FaultInjector(Protocol):
    def check(self, point: BackupFaultPoint) -> None: ...


class NoFaultInjector:
    def check(self, point: BackupFaultPoint) -> None:
        del point


class InjectedBackupFault(RuntimeError):
    def __init__(self, point: BackupFaultPoint) -> None:
        super().__init__(point.value)
        self.point = point


class DeterministicFaultInjector:
    """Fail once at configured points; intended for synthetic tests only."""

    def __init__(self, *points: BackupFaultPoint) -> None:
        self._remaining = set(points)

    def check(self, point: BackupFaultPoint) -> None:
        if point not in self._remaining:
            return
        self._remaining.remove(point)
        raise InjectedBackupFault(point)


CancellationCheck = Callable[[], bool]


def never_cancelled() -> bool:
    return False


__all__ = [
    "BackupFaultPoint",
    "CancellationCheck",
    "DeterministicFaultInjector",
    "FaultInjector",
    "InjectedBackupFault",
    "NoFaultInjector",
    "never_cancelled",
]
