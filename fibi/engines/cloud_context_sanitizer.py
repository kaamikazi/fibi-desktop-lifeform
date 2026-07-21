"""Keep optional cloud model context tiny and safe."""

from __future__ import annotations

import re

from fibi.engines.types import Observation
from fibi.providers.types import CloudContextPreview


SECRET_PATTERNS = (
    re.compile(r"\b[A-Za-z]:\\[^\s]+"),
    re.compile(r"/(?:home|users|var|etc)/[^\s]+", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
)


class CloudContextSanitizer:
    """Prepare minimal model prompts without raw local data."""

    @staticmethod
    def sanitize_text(text: str, max_chars: int = 500) -> str:
        cleaned = str(text or "")
        for pattern in SECRET_PATTERNS:
            cleaned = pattern.sub("[redacted]", cleaned)
        return " ".join(cleaned.split())[:max_chars]

    def build_prompt(
        self,
        user_message: str,
        mood: str,
        context_level: str = "minimal",
        memory_hints: list[str] | None = None,
        observation: Observation | None = None,
    ) -> str:
        """Return a cloud-safe prompt with no raw DB rows, logs, dreams, or clipboard."""
        safe_message = self.sanitize_text(user_message, 500)
        lines = [
            "You write as Fibi, a helpful desktop lifeform.",
            "Answer the user's request directly and usefully first.",
            "Give concrete factual, explanatory, planning, coding, memory, project, or reasoning content when asked.",
            "Cute personality is optional light flavor after the answer, never a substitute for it.",
            "Avoid yawns, giggles, roleplay actions, and repetitive sleepy or tiny-creature filler.",
            "Never mention private data, logs, files, clipboard, or screenshots.",
            f"Current mood: {self.sanitize_text(mood, 40)}.",
        ]
        if context_level in {"minimal", "memory_hint"} and observation:
            lines.append(f"Time feel: {self.sanitize_text(observation.time_of_day, 40)}.")
        if context_level == "memory_hint":
            for hint in (memory_hints or [])[:2]:
                lines.append(f"Memory hint: {self.sanitize_text(hint, 120)}")
        if context_level == "none":
            lines = lines[:5]
        return "\n".join(lines) + f"\nUser: {safe_message}\nFibi:"

    @staticmethod
    def preview(
        *,
        approved_memory_summaries: list[str] | None = None,
        recent_turn_count: int = 0,
    ) -> CloudContextPreview:
        """Describe cloud categories without exposing their text."""

        return CloudContextPreview(
            recent_turn_count=max(0, min(4, int(recent_turn_count))),
            approved_memory_summary_count=min(2, len(approved_memory_summaries or [])),
        )
