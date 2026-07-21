"""Persistent privacy-first settings for voice input."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import VoiceInputSettings


class VoiceSettingsEngine:
    """Store push-to-talk voice settings locally in Fibi's state file."""

    KEY = "voice_input_settings"

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

    def _load(self) -> VoiceInputSettings:
        raw = self._read_state().get(self.KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(VoiceInputSettings())
        for key, value in raw.items():
            if key not in defaults:
                continue
            if key in {
                "require_confirmation_below_confidence",
                "wake_word_sensitivity",
                "wake_word_cooldown_seconds",
            }:
                defaults[key] = float(value)
            elif key in {"voice_language", "voice_provider", "microphone_device_id", "push_to_talk_hotkey"}:
                defaults[key] = None if value is None else str(value)
            else:
                defaults[key] = bool(value)
        return VoiceInputSettings(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.KEY] = asdict(self.settings)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def update(self, **values) -> VoiceInputSettings:
        current = asdict(self.settings)
        for key, value in values.items():
            if key not in current:
                continue
            if key in {
                "require_confirmation_below_confidence",
                "wake_word_sensitivity",
                "wake_word_cooldown_seconds",
            }:
                current[key] = float(value)
            elif key in {"voice_language", "voice_provider", "microphone_device_id", "push_to_talk_hotkey"}:
                current[key] = None if value is None else str(value)
            else:
                current[key] = bool(value)
        self.settings = VoiceInputSettings(**current)
        self.save()
        return self.settings

    def summary_line(self) -> str:
        ears = "ears on" if self.settings.allow_voice_input else "ears off"
        mode = "push-to-talk only" if self.settings.push_to_talk_enabled else "push-to-talk off"
        wake = "wake word sleeping" if not self.settings.wake_word_enabled else "wake word on"
        return f"{ears}. {mode}. {wake}."
