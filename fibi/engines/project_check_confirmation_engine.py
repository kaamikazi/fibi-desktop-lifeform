"""Pending project check confirmation store."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fibi.engines.types import PendingProjectCheck, ProjectCheckRequest
from fibi.paths import data_path


class ProjectCheckConfirmationEngine:
    """Store one pending check for exact confirmation."""

    CONFIRM_PHRASES = {"confirm run check", "run check confirm", "/check confirm"}

    def __init__(self, state_path: Path | None = None, ttl_seconds: int = 60) -> None:
        self.state_path = Path(state_path) if state_path is not None else data_path("pending_project_check.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def create(self, request: ProjectCheckRequest) -> PendingProjectCheck:
        now = datetime.now(timezone.utc)
        created = now.astimezone().isoformat(timespec="seconds")
        expires = (now + timedelta(seconds=self.ttl_seconds)).astimezone().isoformat(timespec="seconds")
        pending = PendingProjectCheck(request, "run check confirm", created, expires)
        self.state_path.write_text(json.dumps(asdict(pending), indent=2), encoding="utf-8")
        return pending

    def pending(self) -> PendingProjectCheck | None:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            request = ProjectCheckRequest(**raw.get("request", {}))
            pending = PendingProjectCheck(request, str(raw.get("required_confirmation_phrase", "run check confirm")), str(raw.get("created_at", "")), str(raw.get("expires_at", "")))
        except TypeError:
            return None
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
