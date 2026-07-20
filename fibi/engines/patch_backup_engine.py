"""Backup and rollback support for patch application."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import PatchBackup, PatchPlan, PatchRollbackResult
from fibi.paths import data_path


class PatchBackupEngine:
    """Create local backups before patching and restore them on rollback."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir is not None else data_path("patch_backups")
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_backups(self, patch: PatchPlan, project_root: Path) -> list[PatchBackup]:
        backups: list[PatchBackup] = []
        patch_dir = self.root_dir / patch.patch_id
        patch_dir.mkdir(parents=True, exist_ok=True)
        for change in patch.file_changes:
            source = self._resolve(project_root, change.file_path)
            backup_path = patch_dir / change.file_path.replace("/", "__").replace("\\", "__")
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup_path)
            backups.append(
                PatchBackup(
                    patch.patch_id,
                    patch.project_id,
                    change.file_path,
                    str(backup_path),
                    change.before_hash,
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                )
            )
        metadata = {
            "patch_id": patch.patch_id,
            "project_id": patch.project_id,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "backups": [asdict(backup) for backup in backups],
        }
        (patch_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return backups

    def rollback(self, patch: PatchPlan, project_root: Path, current_hashes: dict[str, str]) -> PatchRollbackResult:
        restored: list[str] = []
        patch_dir = self.root_dir / patch.patch_id
        metadata_path = patch_dir / "metadata.json"
        if not metadata_path.exists():
            return PatchRollbackResult(False, patch.patch_id, "backup missing.", error="backup missing")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return PatchRollbackResult(False, patch.patch_id, "backup metadata broken.", error="metadata invalid")
        for item in metadata.get("backups", []):
            relative = str(item.get("original_relative_path", ""))
            target = self._resolve(project_root, relative)
            expected_after = next((change.after_hash for change in patch.file_changes if change.file_path == relative), "")
            if expected_after and current_hashes.get(relative) != expected_after:
                return PatchRollbackResult(False, patch.patch_id, "file changed after patch. manual rollback.", restored, "hash mismatch")
            backup_path = Path(str(item.get("backup_path", "")))
            if not backup_path.exists():
                return PatchRollbackResult(False, patch.patch_id, "backup crumb missing.", restored, "backup file missing")
            shutil.copy2(backup_path, target)
            restored.append(relative)
        return PatchRollbackResult(True, patch.patch_id, "rollback done. tiny undo.", restored)

    @staticmethod
    def _resolve(project_root: Path, relative_path: str) -> Path:
        root = project_root.resolve()
        target = (root / relative_path).resolve()
        target.relative_to(root)
        return target
