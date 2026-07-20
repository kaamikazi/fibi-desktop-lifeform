"""Classify messages before any heavy work happens."""

from __future__ import annotations

import re
import unicodedata

from fibi.engines.types import FastResponseCategory

GREETINGS = {"hi", "hey", "hello", "yo", "sup", "oi", "oi g", "fibi", "you there"}
THANKS = ("thanks", "thank you", "ty", "appreciate it")
GOODBYE = ("bye", "goodbye", "see you", "later fibi", "gn", "good night")
SUCCESS = ("it worked", "fixed", "done", "passed", "success", "solved", "finally")
FRUSTRATION = ("bug", "crash", "failed", "broken", "nothing works", "i quit", "hate this")
TINY_STATUS = ("are you there", "you there", "what are you doing", "still there", "you alive")
SOCIAL_CHECKINS = (
    "how are you",
    "how are you doing",
    "how are u",
    "you okay",
    "are you okay",
    "are you there",
    "what are you doing",
    "still there",
    "you alive",
)
AFFECTION = ("cute", "good fibi", "pat pat", "pet", "boop")
DATE_QUESTIONS = {
    "what's the date",
    "whats the date",
    "what is the date",
    "what date is it",
    "today's date",
    "todays date",
    "date today",
    "current date",
    "what day is it",
    "day today",
    "date",
}
TIME_QUESTIONS = {
    "what time is it",
    "current time",
    "time now",
    "what's the time",
    "whats the time",
    "time",
}
MEMORY_QUESTIONS = (
    "what do you remember",
    "what do you know about me",
    "remember about me",
    "my memories",
)
SIMPLE_PERSONAL_QUESTIONS = (
    "how are you",
    "how are u",
    "you okay",
    "are you okay",
    "are you awake",
)
COMPLEX_TERMS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "explain",
    "tell me",
    "help",
    "fix",
    "solve",
    "build",
    "create",
    "make",
    "write",
    "code",
    "error",
    "issue",
    "problem",
    "search",
    "think",
)


class FastResponseClassifier:
    """Return a cheap category before observation, DB scans, or model calls."""

    def classify(self, user_message: str) -> FastResponseCategory:
        text = user_message.strip()
        command_text = re.sub(r"\s+", " ", text.lower()).strip()
        lowered = self.normalize_text(text)
        greeting_text = self.normalize_greeting_text(lowered)
        if not lowered:
            return FastResponseCategory("unknown", 0.2, False)
        if command_text.startswith("/"):
            if command_text.startswith("/privacy"):
                return FastResponseCategory("privacy_command", 1.0, False)
            if command_text.startswith(("/memory", "/memories", "/forget", "/dreams", "/journal", "/summary", "/privacy", "/reset")):
                return FastResponseCategory("memory_command", 1.0, False)
            if command_text.startswith(("/model", "/cloud", "/provider", "/perf", "/cancel", "/stop")):
                return FastResponseCategory("model_command", 1.0, False)
            return FastResponseCategory("privacy_command" if "privacy" in command_text else "memory_command", 0.9, False)
        if greeting_text in GREETINGS:
            return FastResponseCategory("greeting", 1.0, False)
        if lowered in DATE_QUESTIONS or lowered in TIME_QUESTIONS or self._looks_like_date_time_utility(lowered):
            return FastResponseCategory("local_utility", 1.0, False)
        if any(phrase in lowered for phrase in MEMORY_QUESTIONS):
            return FastResponseCategory("memory_command", 0.95, False)
        if any(phrase in lowered for phrase in THANKS):
            return FastResponseCategory("thanks", 0.95, False)
        if any(phrase in lowered for phrase in GOODBYE):
            return FastResponseCategory("goodbye", 0.95, False)
        if any(phrase in lowered for phrase in SUCCESS):
            return FastResponseCategory("success", 0.9, False)
        if any(lowered == phrase or lowered.startswith(phrase + " ") for phrase in SOCIAL_CHECKINS):
            return FastResponseCategory("social_checkin", 0.95, False)
        if any(phrase in lowered for phrase in TINY_STATUS):
            return FastResponseCategory("tiny_status", 0.9, False)
        if any(phrase in lowered for phrase in AFFECTION):
            return FastResponseCategory("affection_click_like", 0.8, False)
        if any(lowered.startswith(phrase) for phrase in SIMPLE_PERSONAL_QUESTIONS):
            return FastResponseCategory("simple_chat", 0.8, False)
        if text.endswith("?"):
            return FastResponseCategory("complex_chat", 0.8, True)
        words = lowered.split()
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in COMPLEX_TERMS):
            return FastResponseCategory("complex_chat", 0.8, True)
        if any(phrase in lowered for phrase in FRUSTRATION):
            return FastResponseCategory("frustration", 0.9, False)
        if len(words) > 4:
            return FastResponseCategory("complex_chat", 0.7, True)
        if len(words) <= 4:
            return FastResponseCategory("simple_chat", 0.65, False)
        return FastResponseCategory("complex_chat", 0.7, True)

    @staticmethod
    def normalize_text(text: str) -> str:
        cleaned = unicodedata.normalize("NFKC", text).lower()
        cleaned = cleaned.replace("\u2019", "'").replace("\u2018", "'")
        cleaned = re.sub(r"[^\w\s']", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def normalize_greeting_text(cls, text: str) -> str:
        """Normalize only casual greeting tokens with stretched endings."""
        tokens = text.split()
        if not tokens:
            return text
        normalized = [cls._normalize_greeting_token(token) for token in tokens]
        return " ".join(normalized)

    @staticmethod
    def _normalize_greeting_token(token: str) -> str:
        patterns = (
            (r"^he+y+$", "hey"),
            (r"^hi+$", "hi"),
            (r"^hello+$", "hello"),
            (r"^yo+$", "yo"),
            (r"^sup+$", "sup"),
        )
        for pattern, replacement in patterns:
            if re.fullmatch(pattern, token):
                return replacement
        return token

    @staticmethod
    def _looks_like_date_time_utility(text: str) -> bool:
        cleaned = unicodedata.normalize("NFKC", text).lower()
        words = set(re.findall(r"[a-z0-9]+", cleaned.replace("'", "")))
        asks_utility = bool(words & {"what", "whats", "is", "today", "todays", "current", "now", "tell", "me", "day"})
        if "time" in words and (asks_utility or words == {"time"}):
            return True
        if "date" in words and (asks_utility or words == {"date"}):
            return True
        return "day" in words and bool(words & {"what", "today", "todays", "current"})
