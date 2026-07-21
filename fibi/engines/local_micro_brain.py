"""Deterministic tiny response generator for offline survival."""

from __future__ import annotations

import random
from collections.abc import Collection

from fibi.engines.types import LocalMicroBrainResult, RelationshipState


class LocalMicroBrain:
    """Not an LLM. Just Fibi staying alive when models are slow or missing."""

    LINES = {
        "greeting": ["eep.", "hi.", "tiny creature online.", "hm?", "guarding.", "eepy but here."],
        "thanks": ["hmph. welcome.", "tiny help.", "mm. okay."],
        "goodbye": ["sleep mode.", "guarding paused.", "bye. tiny patrol later."],
        "sleep": ["okay. sleep mode.", "night. guarding quietly."],
        "wake": ["awake.", "here. eyes open-ish."],
        "tiny_status": ["still here.", "here.", "present."],
        "model_unavailable": [
            "tiny local mode only.",
            "model creature is asleep.",
            "i can do small thoughts right now.",
            "local mode. explainy brain unavailable.",
        ],
        "memory_unavailable": ["memory pile unavailable. still here.", "crumbs are hiding."],
        "quiet_mode": ["quiet mode.", "small and silent.", "i'll just blink."],
        "boundary_ack": ["okay.", "got it.", "i'll be small."],
        "late_night": ["sleep is suspiciously useful.", "eepy hour.", "tiny creature recommends bed."],
        # Low-confidence direct chat is declined so FibiCore can try the model.
        # "tiny thought" is reserved for idle inner-life bubbles only.
        "simple_chat": [],
        "unknown": [],
    }

    def reply(
        self,
        category: str,
        mood: str = "idle",
        time_of_day: str = "",
        relationship: RelationshipState | None = None,
        user_message: str = "",
        excluded_texts: Collection[str] = (),
    ) -> LocalMicroBrainResult:
        if time_of_day == "late_night" and category == "simple_chat":
            category = "late_night"
        if category not in {"greeting", "thanks", "goodbye", "sleep", "wake", "tiny_status"}:
            return LocalMicroBrainResult(None, mood, category, "local", False, "low", False)
        lines = list(self.LINES.get(category, self.LINES["unknown"]))
        excluded = {line.strip().lower() for line in excluded_texts}
        lines = [line for line in lines if line.strip().lower() not in excluded]
        if not lines:
            return LocalMicroBrainResult(None, mood, category, "local", False, "low", False)
        if relationship and relationship.user_prefers_quiet:
            lines = [line for line in lines if len(line) <= 18] or ["okay."]
        mood_hint = {
            "success": "happy",
            "frustration": "thinking",
            "thanks": "happy",
            "goodbye": "sleepy",
            "late_night": "sleepy",
        }.get(category, mood if mood in {"happy", "sleepy", "thinking", "idle"} else "idle")
        return LocalMicroBrainResult(random.choice(lines), mood_hint, category, "local", False, "high", True)
