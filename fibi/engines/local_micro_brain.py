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
        "success": ["YAY.", "tiny victory.", "see? not doomed."],
        "frustration": ["hmm...", "pause maybe.", "tiny creature remains."],
        "tiny_status": ["still here.", "guarding.", "blinking professionally.", "tiny creature present.", "blink blink."],
        "social_checkin": [
            "sleepy. still guarding.",
            "tiny and operational.",
            "alive-ish.",
            "nest ok. brain tiny.",
            "eepy but here.",
        ],
        "doing_status": [
            "guarding desktop.",
            "watching the cursor escape.",
            "being tiny.",
            "pretending to debug.",
        ],
        "affection_click_like": ["eep.", "tiny creature appreciated.", "pat accepted."],
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
        if category == "social_checkin":
            category = self._social_subcategory(user_message)
        if time_of_day == "late_night" and category == "simple_chat":
            category = "late_night"
        if category in {"simple_chat", "unknown"}:
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

    @staticmethod
    def _social_subcategory(user_text_hint: str) -> str:
        hint = user_text_hint.lower()
        if "doing" in hint:
            return "doing_status"
        if "there" in hint or "alive" in hint:
            return "tiny_status"
        return "social_checkin"
