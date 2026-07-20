"""Persistent settings for Fibi's manual action core."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import ActionSettings


class ActionSettingsEngine:
    """Store action permissions locally inside Fibi's state file."""

    KEY = "action_settings"

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()
        self.save()

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _load(self) -> ActionSettings:
        state = self._read_state()
        raw = state.get(self.KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(ActionSettings())
        for key, value in raw.items():
            if key in defaults:
                defaults[key] = bool(value)
        return ActionSettings(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.settings)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update(self, **values) -> ActionSettings:
        current = asdict(self.settings)
        for key, value in values.items():
            if key in current:
                current[key] = bool(value)
        self.settings = ActionSettings(**current)
        self.save()
        return self.settings

    def summary_line(self) -> str:
        if not self.settings.allow_desktop_actions:
            return "hands tucked away."
        risky = "screens scary off" if not self.settings.allow_screenshot else "screens scary on"
        shutdown = "shutdown off" if not self.settings.allow_shutdown else "shutdown armed"
        return f"safe hands on. {risky}. {shutdown}."
