"""Pending patch confirmation store."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fibi.engines.types import PatchFileChange, PatchPlan, PendingPatch, ReplacementBlock
from fibi.paths import data_path


class PatchConfirmationEngine:
    """Store one pending patch that needs exact user confirmation."""

    CONFIRM_PHRASES = {"confirm apply patch", "apply patch confirm"}

    def __init__(self, state_path: Path | None = None, ttl_seconds: int = 300) -> None:
        self.state_path = Path(state_path) if state_path is not None else data_path("pending_patch.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def create(self, patch: PatchPlan) -> PendingPatch:
        now = datetime.now(timezone.utc)
        patch.created_at = patch.created_at or now.astimezone().isoformat(timespec="seconds")
        patch.expires_at = (now + timedelta(seconds=self.ttl_seconds)).astimezone().isoformat(timespec="seconds")
        pending = PendingPatch(patch, "apply patch confirm", patch.created_at, patch.expires_at)
        self.state_path.write_text(json.dumps(asdict(pending), indent=2), encoding="utf-8")
        return pending

    def pending(self) -> PendingPatch | None:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        pending = self._from_dict(raw)
        if self._expired(pending.expires_at):
            self.cancel()
            return None
        return pending

    def cancel(self) -> bool:
        existed = self.state_path.exists()
        try:
            self.state_path.unlink(missing_ok=True)
        except OSError:
            return False
        return existed

    def is_confirmation(self, text: str) -> bool:
        return " ".join(text.lower().strip().split()) in self.CONFIRM_PHRASES

    @staticmethod
    def _expired(expires_at: str) -> bool:
        try:
            expires = datetime.fromisoformat(expires_at)
        except ValueError:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires.astimezone(timezone.utc)

    @staticmethod
    def _from_dict(raw: dict) -> PendingPatch:
        patch_raw = raw.get("patch", {})
        changes: list[PatchFileChange] = []
        for item in patch_raw.get("file_changes", []):
            replacement_raw = item.get("replacement")
            replacement = ReplacementBlock(**replacement_raw) if isinstance(replacement_raw, dict) else None
            clean = {**item, "replacement": replacement}
            changes.append(PatchFileChange(**clean))
        patch = PatchPlan(**{**patch_raw, "file_changes": changes})
        return PendingPatch(
            patch,
            str(raw.get("required_confirmation_phrase", "apply patch confirm")),
            str(raw.get("created_at", "")),
            str(raw.get("expires_at", "")),
        )
