"""Classify messages before any heavy work happens."""

from __future__ import annotations

import re
import unicodedata

from fibi.engines.types import FastResponseCategory

GREETINGS = {"hi", "hey", "hello", "yo", "sup", "oi", "oi g", "fibi", "you there"}
THANKS = ("thanks", "thank you", "ty", "appreciate it")
GOODBYE = ("bye", "goodbye", "see you", "later fibi", "gn", "good night")
TINY_STATUS = {"are you there", "you there", "still there", "you alive"}
SLEEP_REQUESTS = {"sleep", "go to sleep", "good night", "night fibi"}
WAKE_REQUESTS = {"wake", "wake up", "wake up fibi"}
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
LIVE_DATA_PHRASES = (
    "weather today",
    "weather now",
    "latest news",
    "breaking news",
    "live price",
    "live prices",
    "stock price",
    "crypto price",
    "sports score",
    "sports scores",
    "score today",
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
        if any(phrase in lowered for phrase in LIVE_DATA_PHRASES):
            return FastResponseCategory("live_data", 1.0, True)
        if lowered in DATE_QUESTIONS or lowered in TIME_QUESTIONS or self._looks_like_date_time_utility(lowered):
            return FastResponseCategory("local_utility", 1.0, False)
        if any(phrase in lowered for phrase in MEMORY_QUESTIONS):
            return FastResponseCategory("complex_chat", 1.0, True)
        if self._matches_short_local_intent(lowered, THANKS):
            return FastResponseCategory("thanks", 0.95, False)
        if self._matches_short_local_intent(lowered, GOODBYE):
            return FastResponseCategory("goodbye", 0.95, False)
        if lowered in SLEEP_REQUESTS:
            return FastResponseCategory("sleep", 1.0, False)
        if lowered in WAKE_REQUESTS:
            return FastResponseCategory("wake", 1.0, False)
        if lowered in TINY_STATUS:
            return FastResponseCategory("tiny_status", 0.9, False)
        if text.endswith("?"):
            return FastResponseCategory("complex_chat", 0.8, True)
        words = lowered.split()
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in COMPLEX_TERMS):
            return FastResponseCategory("complex_chat", 0.8, True)
        if len(words) > 4:
            return FastResponseCategory("complex_chat", 0.7, True)
        if len(words) <= 4:
            # Unknown direct chat is low confidence. The micro-brain may opt in,
            # otherwise the model router gets the message.
            return FastResponseCategory("simple_chat", 0.55, True)
        return FastResponseCategory("complex_chat", 0.7, True)

    def escalation_reason(self, user_message: str, category: FastResponseCategory | None = None) -> str:
        """Return a safe reason category without including the user's prompt."""

        classified = category or self.classify(user_message)
        if classified.category == "complex_chat":
            normalized = self.normalize_text(user_message)
            if user_message.rstrip().endswith("?"):
                return "content question requires model context"
            if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in COMPLEX_TERMS):
                return "reasoning or content term detected"
            return "multi-word conversational request"
        if classified.category == "simple_chat" and classified.should_use_model:
            return "uncertain local intent prefers model router"
        return "deterministic local intent"

    @staticmethod
    def _matches_short_local_intent(text: str, phrases: tuple[str, ...]) -> bool:
        if len(text.split()) > 4:
            return False
        return any(text == phrase or text == f"{phrase} fibi" for phrase in phrases)

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
