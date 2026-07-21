"""Persisted response-length policy for direct Fibi replies."""

from __future__ import annotations

import re


REPLY_STYLES = {"concise", "normal", "detailed"}
DETAIL_REQUEST_PATTERN = re.compile(
    r"\b(in detail|detailed|thorough|step[- ]by[- ]step|explain fully|long answer|"
    r"be comprehensive|elaborate)\b",
    re.IGNORECASE,
)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class ReplyStyleEngine:
    """Build prompt guidance and enforce a bounded final prose response."""

    def instruction(self, style: str, user_message: str) -> str:
        selected = self.normalize(style)
        if self.requests_detail(user_message) or selected == "detailed":
            return (
                "Give a direct, sufficiently detailed answer. Keep personality light and do not "
                "repeat cute filler or roleplay actions."
            )
        if selected == "normal":
            return (
                "Answer directly in roughly 3-6 clear sentences. Add at most one short personality "
                "line and avoid repeated cute filler or roleplay actions."
            )
        return (
            "Answer directly in 1-3 short sentences and no more than 60 words. For a simple "
            "question, target 15-35 words. Add at most one tiny personality line. Do not use "
            "repeated cute filler, yawns, or roleplay actions."
        )

    def apply(self, text: str, style: str, user_message: str) -> str:
        """Trim overlong prose while leaving explicitly requested detail intact."""

        cleaned = (text or "").strip()
        selected = self.normalize(style)
        if not cleaned or self.requests_detail(user_message) or selected == "detailed":
            return cleaned

        max_sentences = 3 if selected == "concise" else 6
        max_words = 60 if selected == "concise" else 140
        sentences = [part.strip() for part in SENTENCE_BOUNDARY.split(cleaned) if part.strip()]
        bounded = " ".join(sentences[:max_sentences]) if sentences else cleaned
        words = bounded.split()
        if len(words) <= max_words:
            return bounded
        shortened = " ".join(words[:max_words]).rstrip(" ,;:-")
        if shortened and shortened[-1] not in ".!?":
            shortened += "."
        return shortened

    @staticmethod
    def normalize(style: str) -> str:
        return style if style in REPLY_STYLES else "concise"

    @staticmethod
    def requests_detail(user_message: str) -> bool:
        return bool(DETAIL_REQUEST_PATTERN.search(user_message or ""))
