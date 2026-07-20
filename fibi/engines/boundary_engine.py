"""Boundary and quiet-mode detection for Fibi."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from fibi.engines.life_engine import STATE_PATH
from fibi.engines.types import BoundarySignal, BoundaryState, QuietModeState

SOFT_BOUNDARIES = ("not now", "later", "shh", "quiet", "stop poking me", "focus", "wait", "busy")
HARD_BOUNDARIES = ("shut up", "leave me alone", "stop talking", "don't say that", "dont say that", "forget this", "don't remember that", "dont remember that")


class BoundaryEngine:
    """Detect user boundaries and manage quiet mode locally."""

    BOUNDARY_KEY = "boundary_state"
    QUIET_KEY = "quiet_mode"

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.boundary = self._load_boundary()
        self.quiet = self._load_quiet()
        self.save()

    def _read_state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_boundary(self) -> BoundaryState:
        raw = self._read_state().get(self.BOUNDARY_KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(BoundaryState())
        defaults.update({key: raw[key] for key in defaults if key in raw})
        return BoundaryState(**defaults)

    def _load_quiet(self) -> QuietModeState:
        raw = self._read_state().get(self.QUIET_KEY, {})
        if not isinstance(raw, dict):
            raw = {}
        defaults = asdict(QuietModeState())
        defaults.update({key: raw[key] for key in defaults if key in raw})
        return QuietModeState(**defaults)

    def save(self) -> None:
        state = self._read_state()
        state[self.BOUNDARY_KEY] = asdict(self.boundary)
        state[self.QUIET_KEY] = asdict(self.quiet)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def export(self) -> dict:
        return {"boundary_state": asdict(self.boundary), "quiet_mode": asdict(self.quiet)}

    def detect(self, user_message: str) -> BoundarySignal | None:
        text = user_message.lower()
        for phrase in HARD_BOUNDARIES:
            if phrase in text:
                return BoundarySignal("hard", phrase, 60, should_apologize=True)
        for phrase in SOFT_BOUNDARIES:
            if phrase in text:
                return BoundarySignal("soft", phrase, 30, should_apologize=phrase in {"quiet", "stop poking me"})
        if "annoying" in text:
            return BoundarySignal("soft", "annoying", 30, should_apologize=True)
        return None

    def apply_boundary(self, signal: BoundarySignal) -> BoundaryState:
        now = datetime.now().astimezone()
        expires = now + timedelta(minutes=signal.quiet_minutes)
        self.boundary = BoundaryState(True, signal.level, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"), signal.phrase)
        self.enable_quiet(signal.quiet_minutes, reason=f"{signal.level}_boundary", save=False)
        self.save()
        return self.boundary

    def enable_quiet(self, minutes: int | None = None, reason: str = "manual", mute_tts: bool = False, save: bool = True) -> QuietModeState:
        now = datetime.now().astimezone()
        expires = now + timedelta(minutes=minutes) if minutes else None
        self.quiet = QuietModeState(True, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds") if expires else None, reason, mute_tts)
        if save:
            self.save()
        return self.quiet

    def disable_quiet(self) -> QuietModeState:
        self.quiet = QuietModeState(False)
        self.boundary.active = False
        self.save()
        return self.quiet

    def refresh(self) -> None:
        now = datetime.now().astimezone()
        if self.quiet.active and self.quiet.expires_at and self._parse(self.quiet.expires_at) <= now:
            self.quiet = QuietModeState(False)
        if self.boundary.active and self.boundary.expires_at and self._parse(self.boundary.expires_at) <= now:
            self.boundary.active = False
        self.save()

    def status(self) -> str:
        self.refresh()
        if not self.quiet.active:
            return "quiet mode off"
        if self.quiet.expires_at:
            return "quiet mode on"
        return "quiet mode on until told otherwise"

    @staticmethod
    def parse_quiet_minutes(command: str) -> int | None:
        match = re.search(r"/quiet\s+(\d+)\s*([mh]?)", command.lower())
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2) or "m"
        return value * 60 if unit == "h" else value

    @staticmethod
    def _parse(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now().astimezone()
