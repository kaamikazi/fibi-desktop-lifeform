"""Small deterministic emotional weighting helpers."""

from __future__ import annotations

from fibi.engines.types import EmotionalWeightUpdate


SUCCESS_WORDS = ("fixed", "done", "passed", "worked", "success", "shipped", "solved")
FRUSTRATION_WORDS = ("error", "bug", "crash", "failed", "broken", "hate this")
TIRED_WORDS = ("tired", "sleepy", "exhausted", "late", "night")
QUIT_WORDS = ("quit", "give up", "delete this")


def emotional_weight_for_message(
    user_message: str,
    time_of_day: str = "",
    related_project: str | None = None,
) -> EmotionalWeightUpdate:
    """Score only meaningful moments higher; ordinary chatter stays light."""
    text = user_message.lower()
    weight = 0.35
    reasons: list[str] = []
    if any(word in text for word in SUCCESS_WORDS):
        weight += 0.3
        reasons.append("success")
    if any(word in text for word in FRUSTRATION_WORDS):
        weight += 0.25
        reasons.append("frustration")
    if any(word in text for word in TIRED_WORDS):
        weight += 0.15
        reasons.append("tired")
    if any(word in text for word in QUIT_WORDS):
        weight += 0.25
        reasons.append("quit_signal")
    if related_project:
        weight += 0.1
        reasons.append("project")
    if time_of_day == "late_night":
        weight += 0.1
        reasons.append("late_night")
    return EmotionalWeightUpdate(
        "user_message",
        max(0.0, min(1.0, weight)),
        ",".join(reasons) or "ordinary",
        related_project,
    )
