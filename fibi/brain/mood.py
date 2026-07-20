"""Tiny mood engine for choosing Fibi expressions.

The rules are intentionally simple so beginners can adjust them later.
"""

from __future__ import annotations

VALID_MOODS = {"idle", "happy", "thinking", "talking", "sleepy", "angry"}

MOOD_KEYWORDS = {
    "angry": ("error", "problem", "bug", "crash", "failed"),
    "happy": ("thanks", "thank", "good", "love", "cute"),
    "thinking": ("wait", "think", "search", "loading"),
    "sleepy": ("sleep", "tired", "night"),
}


def choose_mood(user_text: str = "", reply_text: str = "", speaking: bool = False) -> str:
    """Pick an expression from user input, Fibi's reply, and speaking state."""
    if speaking:
        return "talking"

    combined_text = f"{user_text} {reply_text}".lower()

    for mood, keywords in MOOD_KEYWORDS.items():
        if any(keyword in combined_text for keyword in keywords):
            return mood

    return "idle"


def normalize_mood(mood: str | None, fallback: str = "idle") -> str:
    """Return a safe mood name."""
    if mood in VALID_MOODS:
        return mood
    return fallback
