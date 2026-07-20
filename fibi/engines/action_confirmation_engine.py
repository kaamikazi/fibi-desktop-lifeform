"""Pending confirmation state for risky manual actions."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.permission_engine import PermissionEngine
from fibi.engines.types import ActionIntent, PendingAction


class ActionConfirmationEngine:
    """Store one pending risky action locally with a short expiry."""

    KEY = "pending_action"

    def __init__(self, state_path: Path = STATE_PATH, ttl_seconds: int = 30) -> None:
        self.state_path = Path(state_path)
        self.ttl_seconds = ttl_seconds
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def create(self, intent: ActionIntent) -> PendingAction:
        now = datetime.now().astimezone()
        pending = PendingAction(
            action_type=intent.action_type,
            target=intent.target,
            query=intent.query,
            created_at=now.isoformat(timespec="seconds"),
            expires_at=(now + timedelta(seconds=self.ttl_seconds)).isoformat(timespec="seconds"),
            required_confirmation_phrase=PermissionEngine.confirmation_phrase(intent.action_type),
            risk_level="confirm_required",
        )
        state = self._read_state()
        state[self.KEY] = asdict(pending)
        self._write_state(state)
        return pending

    def pending(self) -> PendingAction | None:
        raw = self._read_state().get(self.KEY)
        if not isinstance(raw, dict):
            return None
        try:
            pending = PendingAction(**raw)
        except TypeError:
            return None
        if self.is_expired(pending):
            self.cancel()
            return None
        return pending

    def consume_if_confirmed(self, user_text: str) -> PendingAction | None:
        pending = self.pending()
        if pending is None:
            return None
        if user_text.strip().lower() != pending.required_confirmation_phrase.lower():
            return None
        self.cancel()
        return pending

    def cancel(self) -> bool:
        state = self._read_state()
        existed = self.KEY in state
        state.pop(self.KEY, None)
        self._write_state(state)
        return existed

    @staticmethod
    def is_expired(pending: PendingAction) -> bool:
        try:
            expires = datetime.fromisoformat(pending.expires_at)
        except ValueError:
            return True
        return datetime.now().astimezone() > expires

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
