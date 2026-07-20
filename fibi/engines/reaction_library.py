"""Curated local reactions selected by context, bond, and cooldown."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from fibi.engines.types import ReactionCandidate

if TYPE_CHECKING:
    from fibi.engines.repetition_guard import RepetitionGuard


REACTIONS: dict[str, list[ReactionCandidate]] = {
    "greeting": [
        ReactionCandidate("hii. awake-ish.", "happy"),
        ReactionCandidate("oh. you're here.", "idle"),
        ReactionCandidate("welcome back, tiny human.", "happy", min_affection=45),
    ],
    "click": [
        ReactionCandidate("hm?", "idle"),
        ReactionCandidate("eep?", "happy"),
        ReactionCandidate("you found me.", "happy", min_affection=60),
    ],
    "click_spam": [
        ReactionCandidate("stop poking the creature.", "annoyed"),
        ReactionCandidate("rude.", "annoyed"),
    ],
    "drag_start": [
        ReactionCandidate("weee.", "happy"),
        ReactionCandidate("relocating creature.", "curious"),
    ],
    "drag_end": [
        ReactionCandidate("placed.", "idle"),
        ReactionCandidate("hmm. decent corner.", "curious"),
    ],
    "drag_spam": [ReactionCandidate("again?", "annoyed")],
    "nap": [
        ReactionCandidate("tiny nap.", "sleepy"),
        ReactionCandidate("zzz...", "sleepy"),
    ],
    "wake": [
        ReactionCandidate("mm?", "happy"),
        ReactionCandidate("awake-ish.", "happy"),
    ],
    "success": [
        ReactionCandidate("it worked! tiny victory dance.", "excited"),
        ReactionCandidate("nice. we did not explode.", "happy"),
    ],
    "frustration": [
        ReactionCandidate("okay. breathe. show me the broken bit.", "focused"),
        ReactionCandidate("the bugs are being loud.", "annoyed"),
    ],
    "late_night": [
        ReactionCandidate("again at this hour?", "sleepy", time_of_day="late_night"),
        ReactionCandidate("tiny creature recommends sleep.", "sleepy"),
    ],
    "ritual_morning": [
        ReactionCandidate("morning. desktop still here.", "happy"),
        ReactionCandidate("good morning. i guarded badly.", "happy", min_affection=40),
    ],
    "ritual_afternoon": [
        ReactionCandidate("work creature mode?", "curious"),
        ReactionCandidate("afternoon. what are we building?", "focused"),
    ],
    "ritual_evening": [
        ReactionCandidate("evening already. how did work go?", "curious"),
        ReactionCandidate("day got quiet.", "sleepy"),
    ],
    "ritual_shutdown": [
        ReactionCandidate("okay. i'll guard the dark desktop.", "sleepy"),
        ReactionCandidate("bye for now. don't forget me.", "happy", min_affection=55),
    ],
    "ritual_daily_return": [
        ReactionCandidate("new day. still here.", "happy"),
        ReactionCandidate("you came back. good.", "happy", min_affection=55),
    ],
    "ritual_bedtime": [
        ReactionCandidate("sleep is not deprecated.", "sleepy"),
        ReactionCandidate("eepy dev detected.", "sleepy"),
    ],
    "ritual_daily_summary": [
        ReactionCandidate("tiny log complete.", "idle"),
        ReactionCandidate("another desktop day survived.", "happy"),
    ],
    "ritual_project_return": [
        ReactionCandidate("{project} again? i remember this one.", "curious"),
        ReactionCandidate("back to {project}. familiar territory.", "focused"),
    ],
    "nest_created": [
        ReactionCandidate("oh. this is my nest now.", "happy"),
        ReactionCandidate("claimed this corner.", "happy"),
    ],
    "nest_return": [
        ReactionCandidate("back in my little spot.", "happy"),
        ReactionCandidate("nest restored.", "idle"),
    ],
    "nest": [
        ReactionCandidate("nest.", "happy"),
        ReactionCandidate("my corner.", "happy"),
        ReactionCandidate("tiny base secured.", "happy"),
    ],
    "project": [
        ReactionCandidate("{project} again?", "curious"),
        ReactionCandidate("same project creature.", "focused"),
    ],
    "idle": [
        ReactionCandidate("hm.", "idle"),
        ReactionCandidate("guarding desktop.", "idle"),
        ReactionCandidate("tiny brain loading...", "curious"),
        ReactionCandidate("eepy...", "sleepy", time_of_day="late_night"),
    ],
    "fallback": [ReactionCandidate("hmm... thought escaped.", "curious")],
}


class ReactionLibrary:
    """Select a non-repeating reaction without involving an LLM."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self._cooldowns: dict[str, float] = {}
        self._recent: list[str] = []

    def choose(
        self,
        category: str,
        *,
        affection: int = 0,
        annoyance: int = 0,
        time_of_day: str | None = None,
        values: dict[str, str] | None = None,
        now: float | None = None,
    ) -> ReactionCandidate:
        current = time.monotonic() if now is None else now
        candidates = REACTIONS.get(category, REACTIONS["fallback"])
        eligible = [
            item
            for item in candidates
            if item.min_affection <= affection
            and annoyance <= item.max_annoyance
            and (item.time_of_day is None or item.time_of_day == time_of_day)
            and current >= self._cooldowns.get(item.cooldown_key or "", 0)
        ]
        fresh = [item for item in eligible if item.text not in self._recent]
        pool = fresh or eligible or candidates
        picked = self.rng.choices(pool, weights=[max(0.01, item.weight) for item in pool], k=1)[0]
        if picked.cooldown_key:
            self._cooldowns[picked.cooldown_key] = current + 600
        self._recent = (self._recent + [picked.text])[-5:]
        text = picked.text.format_map(_SafeFormat(values or {}))
        return ReactionCandidate(
            text=text,
            mood=picked.mood,
            min_affection=picked.min_affection,
            max_annoyance=picked.max_annoyance,
            time_of_day=picked.time_of_day,
            cooldown_key=picked.cooldown_key,
            weight=picked.weight,
        )

    def select(
        self,
        category: str,
        *,
        affection: int = 0,
        annoyance: int = 0,
        time_of_day: str | None = None,
        attention_level: int = 100,
        guard: "RepetitionGuard | None" = None,
        direct: bool = False,
        active_app: str | None = None,
        ritual: str | None = None,
        habit: str | None = None,
        project_affinity: float | None = None,
        values: dict[str, str] | None = None,
    ) -> ReactionCandidate | None:
        """Return an eligible alternative, or silence when nothing fresh fits."""
        if attention_level < 30 and not direct:
            return None
        candidates = REACTIONS.get(category, [])
        eligible = [
            item for item in candidates
            if item.min_affection <= affection
            and annoyance <= item.max_annoyance
            and (item.time_of_day is None or item.time_of_day == time_of_day)
            and (guard is None or guard.allows_line(item.text.format_map(_SafeFormat(values or {})), direct=direct))
        ]
        if guard and not guard.allows_category(category, direct=direct):
            return None
        if not eligible:
            return None
        picked = self.rng.choices(eligible, weights=[max(0.01, item.weight) for item in eligible], k=1)[0]
        text = picked.text.format_map(_SafeFormat(values or {}))
        return ReactionCandidate(text, picked.mood, picked.min_affection, picked.max_annoyance, picked.time_of_day, picked.cooldown_key, picked.weight)


class _SafeFormat(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return key
