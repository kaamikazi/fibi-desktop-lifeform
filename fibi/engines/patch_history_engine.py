"""Local JSONL history for patch application events."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.types import PatchApplyResult, PatchPlan, PatchRollbackResult
from fibi.paths import data_path


class PatchHistoryEngine:
    """Record patch metadata without storing full file contents."""

    def __init__(self, history_path: Path | None = None) -> None:
        self.history_path = Path(history_path) if history_path is not None else data_path("patch_history.jsonl")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

    def record_created(self, patch: PatchPlan) -> None:
        self._append({"event": "patch_created", "patch": self._patch_summary(patch)})

    def record_apply(self, patch: PatchPlan, result: PatchApplyResult) -> None:
        self._append({"event": "patch_applied" if result.ok else "patch_failed", "patch": self._patch_summary(patch), "result": asdict(result)})

    def record_rollback(self, patch: PatchPlan, result: PatchRollbackResult) -> None:
        self._append({"event": "patch_rolled_back" if result.ok else "patch_rollback_failed", "patch": self._patch_summary(patch), "result": asdict(result)})

    def recent(self, limit: int = 5) -> list[dict]:
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        rows: list[dict] = []
        for line in lines[-max(1, limit):]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def last_applied_patch_id(self) -> str:
        for row in reversed(self.recent(50)):
            if row.get("event") == "patch_applied" and row.get("result", {}).get("ok"):
                return str(row.get("patch", {}).get("patch_id", ""))
        return ""

    def _append(self, payload: dict) -> None:
        payload["timestamp"] = datetime.now().astimezone().isoformat(timespec="seconds")
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    @staticmethod
    def _patch_summary(patch: PatchPlan) -> dict:
        return {
            "patch_id": patch.patch_id,
            "project_id": patch.project_id,
            "files": patch.target_files,
            "risk_level": patch.risk_level,
            "summary": patch.summary,
            "backup_paths": patch.backup_paths,
            "applied": patch.applied,
            "rolled_back": patch.rolled_back,
        }
