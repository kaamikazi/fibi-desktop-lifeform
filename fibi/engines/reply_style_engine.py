"""Persisted response-length policy for direct Fibi replies."""

from __future__ import annotations

import re


REPLY_STYLES = {"concise", "normal", "detailed"}
DETAIL_REQUEST_PATTERN = re.compile(
    r"\b(in detail|give details|explain deeply|full explanation|detailed|thorough|"
    r"step[- ]by[- ]step|explain fully|long answer|be comprehensive|elaborate)\b",
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
            "Answer directly in no more than 2 short sentences or 45 words. For a simple "
            "question, use no more than 20 words. Add at most one tiny personality phrase. "
            "Do not add introductions, summaries, repeated explanations, filler, yawns, or roleplay."
        )

    def apply(self, text: str, style: str, user_message: str) -> str:
        """Trim overlong prose while leaving explicitly requested detail intact."""

        cleaned = (text or "").strip()
        selected = self.normalize(style)
        if not cleaned or self.requests_detail(user_message) or selected == "detailed":
            return cleaned

        max_sentences = 2 if selected == "concise" else 6
        max_words = 20 if selected == "concise" and self.is_simple_question(user_message) else 45 if selected == "concise" else 140
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

    @staticmethod
    def is_simple_question(user_message: str) -> bool:
        cleaned = re.sub(r"[^a-z0-9' ]+", " ", (user_message or "").lower())
        words = cleaned.split()
        return bool(words) and len(words) <= 8 and words[0] in {
            "what", "who", "when", "where", "which", "is", "are", "can", "do", "does",
        }
