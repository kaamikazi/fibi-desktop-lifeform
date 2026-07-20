"""Local consent settings for Fibi's memory learning."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import MemoryConsentState, MemoryLearningStatus


class MemoryConsentEngine:
    """Persist user-owned memory consent toggles in Fibi's local state file."""

    KEY = "memory_consent"

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()
        self.save()

    def update(self, **values: object) -> MemoryConsentState:
        current = asdict(self.state)
        for key, value in values.items():
            if key in current:
                current[key] = bool(value)
        self.state = MemoryConsentState(**current)
        self.save()
        return self.state

    def reset(self) -> MemoryConsentState:
        self.state = MemoryConsentState()
        self.save()
        return self.state

    def status(self) -> MemoryLearningStatus:
        enabled = bool(self.state.memory_learning_enabled)
        return MemoryLearningStatus(
            enabled=enabled,
            consent=self.state,
            summary="memory learning on" if enabled else "memory paused",
        )

    def summary_line(self) -> str:
        bits = [
            "learning on" if self.state.memory_learning_enabled else "learning off",
            "sensitive approval on" if self.state.require_approval_for_sensitive_memory else "sensitive approval off",
            "project events on" if self.state.remember_project_events else "project events off",
            "browser notes on" if self.state.remember_browser_notes else "browser notes off",
            "workflow summaries on" if self.state.remember_workflow_summaries else "workflow summaries off",
        ]
        return "memory consent: " + "; ".join(bits) + "."

    def can_remember_source(self, source: str) -> bool:
        if not self.state.memory_learning_enabled:
            return False
        normalized = source.lower()
        if "browser" in normalized:
            return self.state.remember_browser_notes
        if "workflow" in normalized:
            return self.state.remember_workflow_summaries
        if any(token in normalized for token in ("project", "patch", "check", "session")):
            return self.state.remember_project_events
        if any(token in normalized for token in ("preference", "habit", "belief")):
            return self.state.remember_user_preferences
        if any(token in normalized for token in ("personality", "relationship", "inner")):
            return self.state.remember_personality_notes
        return True

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.state)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _load(self) -> MemoryConsentState:
        raw = self._read_state().get(self.KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(MemoryConsentState())
        for key, value in raw.items():
            if key in defaults:
                defaults[key] = bool(value)
        return MemoryConsentState(**defaults)

    def _read_state(self) -> dict:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}
