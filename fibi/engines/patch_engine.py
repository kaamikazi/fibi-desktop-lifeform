"""Confirmed safe patch application for registered project workspaces."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fibi.engines.patch_backup_engine import PatchBackupEngine
from fibi.engines.patch_safety_engine import PatchSafetyEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import (
    EditSuggestionResult,
    PatchApplyResult,
    PatchFileChange,
    PatchPlan,
    PatchRiskResult,
    PatchRollbackResult,
)

LOGGER = logging.getLogger(__name__)


class PatchEngine:
    """Apply only user-reviewed, low/medium-risk text patches."""

    def __init__(
        self,
        workspace: ProjectWorkspaceEngine,
        safety: PatchSafetyEngine | None = None,
        backups: PatchBackupEngine | None = None,
        max_file_bytes: int = 1_000_000,
    ) -> None:
        self.workspace = workspace
        self.safety = safety or PatchSafetyEngine()
        self.backups = backups or PatchBackupEngine()
        self.max_file_bytes = max_file_bytes

    def create_plan_from_suggestion(self, suggestion: EditSuggestionResult) -> tuple[PatchPlan | None, PatchRiskResult]:
        project = self.workspace.current()
        if project is None or not suggestion.project_id:
            return None, PatchRiskResult(False, "blocked", "no project nest", blocked=True, fibi_reply="no project nest.")
        if not suggestion.ok:
            return None, PatchRiskResult(False, "blocked", suggestion.refused_reason or "no patch", blocked=True, fibi_reply="no patch crumb.")
        diff_text = suggestion.suggested_diff.diff_text if suggestion.suggested_diff else ""
        risk = self.safety.assess(suggestion.target_files, diff_text)
        LOGGER.info("patch_safety_result", extra={"risk_level": risk.risk_level, "allowed": risk.allowed, "reason": risk.reason})
        if not risk.allowed or risk.risk_level not in {"low", "medium"}:
            return None, risk
        changes: list[PatchFileChange] = []
        for block in suggestion.replacement_blocks:
            try:
                target = self._resolve_project_path(block.file_path)
                before_text = self._read_text_file(target)
            except Exception as exc:
                return None, PatchRiskResult(False, "blocked", str(exc), blocked=True, fibi_reply="too sharp for tiny hands.")
            if block.before and block.before not in before_text:
                return None, PatchRiskResult(False, "blocked", "replacement block no longer matches", blocked=True, fibi_reply="file changed. patch crumb stale.")
            after_text = before_text.replace(block.before, block.after, 1) if block.before else before_text
            if before_text == after_text:
                return None, PatchRiskResult(False, "blocked", "no file changes", blocked=True, fibi_reply="nothing to apply.")
            changes.append(
                PatchFileChange(
                    block.file_path,
                    self.hash_text(before_text),
                    self.hash_text(after_text),
                    diff_text,
                    block,
                )
            )
        if not changes:
            return None, PatchRiskResult(False, "blocked", "no replacement blocks", blocked=True, fibi_reply="no applyable patch crumb.")
        now = datetime.now(timezone.utc)
        patch = PatchPlan(
            patch_id=uuid.uuid4().hex[:12],
            project_id=project.project_id,
            target_files=[change.file_path for change in changes],
            diff_text=diff_text,
            file_changes=changes,
            before_hash=";".join(change.before_hash for change in changes),
            after_hash=";".join(change.after_hash for change in changes),
            risk_level=risk.risk_level,
            summary=suggestion.summary or f"Patch {', '.join(suggestion.target_files)}.",
            created_at=now.astimezone().isoformat(timespec="seconds"),
            expires_at=(now + timedelta(minutes=5)).astimezone().isoformat(timespec="seconds"),
            requires_confirmation=True,
        )
        LOGGER.info("patch_created", extra={"patch_id": patch.patch_id, "risk_level": patch.risk_level})
        return patch, risk

    def apply(self, patch: PatchPlan) -> PatchApplyResult:
        LOGGER.info("patch_apply_requested", extra={"patch_id": patch.patch_id, "risk_level": patch.risk_level})
        project = self.workspace.current()
        if project is None or project.project_id != patch.project_id:
            return PatchApplyResult(False, patch.patch_id, "project nest mismatch.", risk_level=patch.risk_level, error="project mismatch")
        project_root = Path(project.root_path)
        try:
            backups = self.backups.create_backups(patch, project_root)
            applied: list[str] = []
            for change in patch.file_changes:
                target = self._resolve_project_path(change.file_path)
                before_text = self._read_text_file(target)
                if self.hash_text(before_text) != change.before_hash:
                    raise RuntimeError(f"hash mismatch for {change.file_path}")
                if change.replacement is None or not change.replacement.before:
                    raise RuntimeError(f"unsupported patch shape for {change.file_path}")
                after_text = before_text.replace(change.replacement.before, change.replacement.after, 1)
                if self.hash_text(after_text) != change.after_hash:
                    raise RuntimeError(f"after hash mismatch for {change.file_path}")
                target.write_text(after_text, encoding="utf-8")
                change.applied = True
                applied.append(change.file_path)
            patch.applied = True
            patch.backup_paths = [backup.backup_path for backup in backups]
            result = PatchApplyResult(True, patch.patch_id, "patch applied. backup tucked away.", applied, patch.backup_paths, patch.risk_level)
            LOGGER.info("patch_applied", extra={"patch_id": patch.patch_id, "files": ",".join(applied)})
            return result
        except Exception as exc:
            patch.error = str(exc)
            LOGGER.warning("patch_failed", extra={"patch_id": patch.patch_id, "error": str(exc)})
            return PatchApplyResult(False, patch.patch_id, "patch failed. no sneaky edits.", risk_level=patch.risk_level, error=str(exc))

    def rollback(self, patch: PatchPlan) -> PatchRollbackResult:
        LOGGER.info("patch_rollback_requested", extra={"patch_id": patch.patch_id})
        project = self.workspace.current()
        if project is None or project.project_id != patch.project_id:
            return PatchRollbackResult(False, patch.patch_id, "project nest mismatch.", error="project mismatch")
        hashes: dict[str, str] = {}
        for change in patch.file_changes:
            target = self._resolve_project_path(change.file_path)
            hashes[change.file_path] = self.hash_text(self._read_text_file(target))
        result = self.backups.rollback(patch, Path(project.root_path), hashes)
        if result.ok:
            patch.rolled_back = True
            LOGGER.info("patch_rolled_back", extra={"patch_id": patch.patch_id})
        return result

    def _resolve_project_path(self, relative_path: str) -> Path:
        project = self.workspace.current()
        if project is None:
            raise ValueError("no project nest")
        root = Path(project.root_path).resolve()
        target = (root / relative_path.replace("\\", "/")).resolve()
        target.relative_to(root)
        if not target.exists() or not target.is_file():
            raise ValueError("target file missing")
        if target.stat().st_size > self.max_file_bytes:
            raise ValueError("file too big for tiny patch")
        if b"\x00" in target.read_bytes()[:4096]:
            raise ValueError("binary file")
        return target

    @staticmethod
    def _read_text_file(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
