"""Harmless synthetic memory backup and restore-rehearsal smoke test."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.memory_backup.models import RestoreRehearsalRequest
from fibi.memory_backup.rehearsal import RestoreRehearsalService
from tests.memory_backup_test_support import create_backup, create_synthetic_data, tree_hashes


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fibi-memory-backup-smoke-") as temporary:
        root = Path(temporary)
        active = root / "synthetic active data"
        create_synthetic_data(active)
        active_before = tree_hashes(active)
        backup = create_backup(active, root / "private backups")
        assert backup.success and backup.bundle_path is not None
        backup_before = tree_hashes(backup.bundle_path)
        rehearsal = RestoreRehearsalService(repository_root=root / "repo").rehearse(
            RestoreRehearsalRequest(
                backup.bundle_path,
                active,
                root / "rehearsal output",
                confirm_private_output=True,
                cleanup=False,
            )
        )
        assert rehearsal.success and rehearsal.rehearsal_path is not None
        with closing(sqlite3.connect(rehearsal.rehearsal_path / "databases" / "memory.sqlite")) as connection:
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 1
        assert tree_hashes(active) == active_before
        assert tree_hashes(backup.bundle_path) == backup_before
    print("Memory backup and restore rehearsal synthetic smoke tests passed.")


if __name__ == "__main__":
    main()
