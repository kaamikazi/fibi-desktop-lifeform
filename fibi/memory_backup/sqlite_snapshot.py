"""Consistent SQLite snapshots using SQLite's online backup API."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fibi.memory_backup.faults import (
    BackupFaultPoint,
    CancellationCheck,
    FaultInjector,
    InjectedBackupFault,
)


class SQLiteSnapshotError(RuntimeError):
    def __init__(self, category: str, *, cancelled: bool = False) -> None:
        super().__init__(category)
        self.category = category
        self.cancelled = cancelled


@dataclass(frozen=True, slots=True)
class SQLiteStructure:
    user_version: int
    table_names: tuple[str, ...]
    schema_fingerprint: str
    integrity_check: str


@dataclass(frozen=True, slots=True)
class SQLiteSnapshotResult:
    size_bytes: int
    structure: SQLiteStructure


def _read_only_connection(path: Path) -> sqlite3.Connection:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.execute("PRAGMA query_only = ON")
    return connection


def inspect_sqlite(path: Path, *, full_integrity_check: bool = False) -> SQLiteStructure:
    check_name = "integrity_check" if full_integrity_check else "quick_check"
    try:
        connection = _read_only_connection(path)
        try:
            results = tuple(str(row[0]).casefold() for row in connection.execute(f"PRAGMA {check_name}"))
            if not results or any(result != "ok" for result in results):
                raise SQLiteSnapshotError("sqlite_integrity_failed")
            user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            rows = tuple(
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3] or ""),
                )
                for row in connection.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_master "
                    "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
                )
            )
        finally:
            connection.close()
    except SQLiteSnapshotError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise SQLiteSnapshotError("sqlite_unavailable_or_invalid") from error
    table_names = tuple(sorted(row[1] for row in rows if row[0] == "table"))
    encoded = json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return SQLiteStructure(
        user_version=user_version,
        table_names=table_names,
        schema_fingerprint=hashlib.sha256(encoded).hexdigest(),
        integrity_check=check_name,
    )


class SQLiteBackupAdapter:
    """Create and validate one independent SQLite snapshot."""

    def backup(
        self,
        source: Path,
        destination: Path,
        *,
        full_integrity_check: bool,
        fault_injector: FaultInjector,
        cancelled: CancellationCheck,
    ) -> SQLiteSnapshotResult:
        source_path = Path(source)
        destination_path = Path(destination)
        if cancelled():
            raise SQLiteSnapshotError("cancelled", cancelled=True)
        fault_injector.check(BackupFaultPoint.SOURCE_UNAVAILABLE)
        if not source_path.is_file():
            raise SQLiteSnapshotError("required_source_missing")
        source_structure = inspect_sqlite(source_path, full_integrity_check=full_integrity_check)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_connection: sqlite3.Connection | None = None
        destination_connection: sqlite3.Connection | None = None
        try:
            source_connection = _read_only_connection(source_path)
            destination_connection = sqlite3.connect(destination_path, timeout=10)

            def progress(_status: int, _remaining: int, _total: int) -> None:
                if cancelled():
                    raise SQLiteSnapshotError("cancelled", cancelled=True)
                fault_injector.check(BackupFaultPoint.DISK_FULL)
                fault_injector.check(BackupFaultPoint.SQLITE_BACKUP_INTERRUPTED)

            source_connection.backup(
                destination_connection,
                pages=128,
                progress=progress,
                sleep=0.01,
            )
            destination_connection.commit()
            # The snapshot must be one self-contained artifact. Normalize only
            # the new destination; the source WAL mode is never changed.
            destination_connection.execute("PRAGMA journal_mode = DELETE").fetchone()
        except SQLiteSnapshotError:
            raise
        except InjectedBackupFault:
            raise
        except (OSError, sqlite3.Error) as error:
            raise SQLiteSnapshotError("sqlite_backup_failed") from error
        finally:
            if destination_connection is not None:
                destination_connection.close()
            if source_connection is not None:
                source_connection.close()
        try:
            fault_injector.check(BackupFaultPoint.CORRUPT_DESTINATION)
            destination_structure = inspect_sqlite(
                destination_path,
                full_integrity_check=full_integrity_check,
            )
            fault_injector.check(BackupFaultPoint.INTEGRITY_CHECK_FAILED)
        except Exception:
            destination_path.unlink(missing_ok=True)
            raise
        if destination_structure != source_structure:
            destination_path.unlink(missing_ok=True)
            raise SQLiteSnapshotError("sqlite_structure_mismatch")
        return SQLiteSnapshotResult(destination_path.stat().st_size, destination_structure)


__all__ = [
    "SQLiteBackupAdapter",
    "SQLiteSnapshotError",
    "SQLiteSnapshotResult",
    "SQLiteStructure",
    "inspect_sqlite",
]
