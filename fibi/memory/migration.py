"""Read-only migration preflight for Fibi's fragmented memory stores.

This module intentionally cannot migrate data. It provides the safe Stage 0
surface described by the memory migration plan while write-mode safeguards are
still being designed and tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fibi.memory.inventory import MemoryInventoryScanner


@dataclass(frozen=True, slots=True)
class MigrationPreflightReport:
    """Sanitized Stage 0 result containing no user memory values."""

    mode: str
    apply_supported: bool
    content_included: bool
    inventory: dict[str, Any]
    blockers: tuple[str, ...]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "apply_supported": self.apply_supported,
            "content_included": self.content_included,
            "inventory": self.inventory,
            "blockers": list(self.blockers),
        }


class MemoryMigrationPreflight:
    """Perform a structural, read-only inspection of a configured data root."""

    BLOCKERS = (
        "write mode is not implemented",
        "a verified backup is required before any future write mode",
        "transactional import and rollback are not implemented",
        "duplicate and conflict review are not implemented",
    )

    def __init__(self, data_root: Path) -> None:
        self._scanner = MemoryInventoryScanner(Path(data_root))

    def run(self) -> MigrationPreflightReport:
        inventory = self._scanner.scan().to_public_dict()
        return MigrationPreflightReport(
            mode="dry-run",
            apply_supported=False,
            content_included=False,
            inventory=inventory,
            blockers=self.BLOCKERS,
        )
