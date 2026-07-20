"""Small deterministic habits that make Fibi feel consistently alive."""

from __future__ import annotations

import hashlib
from datetime import datetime

from fibi.engines.types import DetectedPattern, HabitState


class HabitEngine:
    """Select local habits from mood, time, and sampled app context."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def select(
        self,
        mood: str,
        time_of_day: str,
        active_app: str | None,
        patterns: list[DetectedPattern] | None = None,
        timestamp: datetime | None = None,
    ) -> HabitState:
        now = timestamp or datetime.now().astimezone()
        candidates = self._candidates(mood, time_of_day, active_app, patterns or [])
        seed = f"{now.date().isoformat()}:{now.hour}:{mood}:{active_app or 'none'}"
        index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % len(candidates)
        name, line = candidates[index]
        self._counts[name] = self._counts.get(name, 0) + 1
        return HabitState(name, line, now.isoformat(timespec="seconds"), self._counts[name])

    @staticmethod
    def should_journal(habit: HabitState) -> bool:
        """Journal the first and then every third occurrence, not every tick."""
        return habit.times_performed == 1 or habit.times_performed % 3 == 0

    @staticmethod
    def _candidates(
        mood: str,
        time_of_day: str,
        active_app: str | None,
        patterns: list[DetectedPattern],
    ) -> list[tuple[str, str]]:
        app = (active_app or "").lower()
        if mood == "sleepy" or time_of_day in {"night", "late_night"}:
            return [
                ("nap_corner", "napping in the corner."),
                ("judge_late_code", "judging late-night coding."),
                ("guard_sleepily", "guarding with eyes closed."),
            ]
        if app in {"code", "vscode", "devenv"}:
            return [
                ("watch_vscode", "watching VS Code."),
                ("pretend_debug", "debugging emotionally."),
                ("compiler_watch", "compiler creature nearby."),
            ]
        if app in {"chrome", "msedge", "firefox", "brave", "opera"}:
            return [
                ("count_tabs", "counting tabs badly."),
                ("cursor_watch", "cursor escaped again."),
            ]
        if any(pattern.pattern == "late_night_coding" for pattern in patterns):
            return [("judge_late_code", "eepy dev hours again.")]
        return [
            ("guard_desktop", "guarding desktop."),
            ("tiny_patrol", "patrolling."),
            ("stare_cursor", "cursor escaped again."),
            ("inspect_nothing", "i found nothing. suspicious."),
        ]
