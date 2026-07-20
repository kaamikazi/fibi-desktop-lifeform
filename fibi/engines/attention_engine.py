"""Intentional reaction gating for Fibi's creature behaviors."""

from __future__ import annotations

import time

from fibi.engines.types import AttentionResult, DetectedPattern, JournalEntry, Observation

BUSY_STATES = {"thinking", "speaking", "listening"}


class AttentionEngine:
    """Decide when silence is better than another reaction."""

    COOLDOWNS = {
        "idle": 60.0,
        "click": 2.5,
        "drag_start": 4.0,
        "drag_end": 4.0,
        "nap": 600.0,
        "wake": 2.0,
        "project": 90.0,
        "late_night": 180.0,
        "error": 30.0,
        "celebration": 10.0,
        "frustration": 15.0,
        "message": 0.0,
    }

    BASE_ATTENTION = {
        "idle": 25,
        "click": 72,
        "drag_start": 75,
        "drag_end": 70,
        "nap": 48,
        "wake": 90,
        "project": 65,
        "late_night": 55,
        "error": 90,
        "celebration": 95,
        "frustration": 90,
        "message": 100,
    }

    def __init__(self) -> None:
        self._last_reacted_at: dict[str, float] = {}

    def evaluate(
        self,
        reaction_type: str,
        mood: str,
        presence_state: str,
        time_of_day: str,
        observation: Observation | None = None,
        recent_journal: list[JournalEntry] | None = None,
        patterns: list[DetectedPattern] | None = None,
        direct: bool = False,
        important: bool = False,
        now: float | None = None,
    ) -> AttentionResult:
        current = time.monotonic() if now is None else now
        base = self.BASE_ATTENTION.get(reaction_type, 35)

        if reaction_type == "message":
            return AttentionResult(100, "direct user message", True, reaction_type)

        if presence_state in BUSY_STATES and not important:
            return AttentionResult(0, f"Fibi is {presence_state}", False, reaction_type)

        cooldown = self.COOLDOWNS.get(reaction_type, 30.0)
        last = self._last_reacted_at.get(reaction_type)
        if last is not None and current - last < cooldown and not important:
            return AttentionResult(base, "reaction cooldown active", False, reaction_type)

        if mood == "sleepy" and reaction_type == "idle":
            base -= 10
        if mood == "sleepy" and reaction_type == "nap":
            base += 15
        if mood in {"excited", "happy"} and reaction_type in {"click", "celebration"}:
            base += 10
        if time_of_day == "late_night" and reaction_type in {"nap", "late_night"}:
            base += 20
        if direct:
            base += 15
        if patterns:
            base += min(10, len(patterns) * 2)
        if important:
            base = max(base, 90)

        level = max(0, min(100, base))
        threshold = 55 if reaction_type != "idle" else 30
        should_react = important or level >= threshold
        reason = "important event" if important else f"attention {level} meets threshold {threshold}"
        return AttentionResult(level, reason, should_react, reaction_type)

    def mark_reacted(self, reaction_type: str, now: float | None = None) -> None:
        self._last_reacted_at[reaction_type] = time.monotonic() if now is None else now
