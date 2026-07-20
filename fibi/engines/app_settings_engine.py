"""Persistent app-level settings for daily Fibi usage."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.build_info import BUILD_MODE
from fibi.engines.types import AppSettings, FirstRunState
from fibi.paths import data_path

SETTINGS_PATH = data_path("fibi_settings.json")


class AppSettingsEngine:
    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = Path(settings_path) if settings_path is not None else data_path("fibi_settings.json")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.was_first_run = not self.settings_path.exists()
        self.settings = self._load()
        self.save()

    def _read(self) -> dict:
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _load(self) -> AppSettings:
        raw = self._read()
        defaults = asdict(AppSettings())
        if isinstance(raw, dict):
            defaults.update({key: raw[key] for key in defaults if key in raw})
        if "beta_mode" not in raw and any(token in BUILD_MODE.lower() for token in ("rc", "beta")):
            defaults["beta_mode"] = True
        if defaults["animation_intensity"] not in {"off", "low", "normal"}:
            defaults["animation_intensity"] = "normal"
        if defaults["language_provider"] not in {"", "ollama", "gemini"}:
            defaults["language_provider"] = ""
        return AppSettings(**defaults)

    def save(self) -> None:
        self.settings_path.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")

    def update(self, **values) -> AppSettings:
        current = asdict(self.settings)
        for key, value in values.items():
            if key in current:
                current[key] = value
        if current["animation_intensity"] not in {"off", "low", "normal"}:
            current["animation_intensity"] = "normal"
        if current["language_provider"] not in {"", "ollama", "gemini"}:
            current["language_provider"] = ""
        self.settings = AppSettings(**current)
        self.save()
        return self.settings

    def first_run_state(self) -> FirstRunState:
        return FirstRunState(self.settings.setup_complete, self.settings.first_run_skipped)

    def complete_setup(self, skipped: bool = False) -> FirstRunState:
        self.settings.setup_complete = True
        self.settings.first_run_skipped = skipped
        self.save()
        return FirstRunState(True, skipped, datetime.now().astimezone().isoformat(timespec="seconds"))
