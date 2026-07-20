"""Tiny TTS queue policy for Fibi.

The PyQt window still performs playback in a background thread. This manager
only decides whether speech should start, so bubble display and route decisions
stay instant.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


UTILITY_MODELS = {
    "local-action",
    "local-command",
    "action-confirmation",
    "action-blocked",
    "local-greeting",
}


@dataclass(slots=True)
class TtsDecision:
    should_speak: bool
    priority: str
    skipped_reason: str = ""


class TtsManager:
    def __init__(self, speak_utility_replies: bool = False) -> None:
        self.speak_utility_replies = speak_utility_replies
        self.is_busy = False
        self.last_duration_ms = 0.0
        self.last_started_at = 0.0

    def decide(self, model_used: str, text: str, allow_tts: bool, requested_priority: str = "") -> TtsDecision:
        priority = requested_priority or self.priority_for(model_used)
        if not allow_tts:
            return TtsDecision(False, priority, "disabled")
        if not text.strip():
            return TtsDecision(False, priority, "empty")
        if priority == "silent":
            return TtsDecision(False, priority, "silent")
        if priority == "low" and not self.speak_utility_replies:
            return TtsDecision(False, priority, "utility_tts_off")
        if self.is_busy and priority in {"low", "medium"}:
            return TtsDecision(False, priority, "busy")
        return TtsDecision(True, priority, "")

    def mark_started(self) -> None:
        self.is_busy = True
        self.last_started_at = time.perf_counter()

    def mark_finished(self, duration_ms: float) -> None:
        self.is_busy = False
        self.last_duration_ms = duration_ms

    def stop(self) -> str:
        self.is_busy = False
        return "voice stopped-ish."

    def status_line(self) -> str:
        state = "busy" if self.is_busy else "idle"
        utility = "utility voice on" if self.speak_utility_replies else "utility voice off"
        return f"tts {state}. {utility}. last {self.last_duration_ms:.0f}ms."

    @staticmethod
    def priority_for(model_used: str) -> str:
        if model_used in {"local-command"}:
            return "silent"
        if model_used in UTILITY_MODELS or model_used.startswith("local-action"):
            return "low"
        if model_used.startswith("local"):
            return "high"
        return "medium"
