"""Persistent local privacy controls for Fibi."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import Observation, PrivacySettings


class PrivacySettingsEngine:
    """Store feature permissions inside the local state file."""

    KEY = "privacy_settings"

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

    def _load(self) -> PrivacySettings:
        state = self._read_state()
        raw = state.get(self.KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(PrivacySettings())
        for key, value in raw.items():
            if key not in defaults:
                continue
            defaults[key] = str(value) if key == "cloud_context_level" else bool(value)
        defaults["allow_clipboard_observation"] = bool(raw.get("allow_clipboard_observation", False))
        if defaults["cloud_context_level"] not in {"none", "minimal", "personality_only", "memory_hint"}:
            defaults["cloud_context_level"] = "minimal"
        return PrivacySettings(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.settings)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update(self, **values) -> PrivacySettings:
        current = asdict(self.settings)
        for key, value in values.items():
            if key in current:
                current[key] = str(value) if key == "cloud_context_level" else bool(value)
        current["allow_clipboard_observation"] = bool(current.get("allow_clipboard_observation", False))
        if current["cloud_context_level"] not in {"none", "minimal", "personality_only", "memory_hint"}:
            current["cloud_context_level"] = "minimal"
        self.settings = PrivacySettings(**current)
        self.save()
        return self.settings

    def export(self) -> dict:
        return asdict(self.settings)

    def filter_observation(self, observation: Observation) -> Observation:
        """Remove observation fields that the user has disabled."""
        return Observation(
            observation.timestamp,
            observation.time_of_day,
            observation.active_app if self.settings.allow_foreground_app_observation else None,
            observation.active_window_title if self.settings.allow_window_title_observation else None,
            observation.clipboard_text if self.settings.allow_clipboard_observation else None,
        )

    def summary_line(self) -> str:
        clipboard = "off" if not self.settings.allow_clipboard_observation else "on"
        ollama = "on" if self.settings.allow_ollama else "off"
        journal = "on" if self.settings.allow_journal else "off"
        cloud = "on" if self.settings.allow_cloud_model and self.settings.allow_nvidia_api else "off"
        return f"local only. clipboard {clipboard}. journal {journal}. ollama {ollama}. cloud {cloud}."
