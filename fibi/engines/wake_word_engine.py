"""Lightweight local wake-word detection built on Fibi's offline STT path."""

from __future__ import annotations

import re

from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.types import VoiceInputSettings, VoiceTranscriptionResult


class WakeWordEngine:
    """Detect ``oi fibi`` locally and capture one follow-up command in memory."""

    WAKE_PHRASES = {"oi fibi", "oy fibi", "oi phoebe", "oy phoebe"}

    def __init__(self, recognizer: SpeechRecognitionEngine) -> None:
        self.recognizer = recognizer

    @classmethod
    def detected(cls, transcript: str) -> bool:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", (transcript or "").lower())
        normalized = " ".join(normalized.split())
        return any(re.search(rf"\b{re.escape(phrase)}\b", normalized) for phrase in cls.WAKE_PHRASES)

    def listen_once(self, settings: VoiceInputSettings) -> tuple[bool, VoiceTranscriptionResult]:
        result = self.recognizer.listen(
            settings,
            source="wake_word_probe",
            max_duration_seconds=3,
            phrase_timeout_seconds=2,
        )
        return self.detected(result.transcript), result

    def capture_command(self, settings: VoiceInputSettings) -> VoiceTranscriptionResult:
        return self.recognizer.listen(
            settings,
            source="wake_word_command",
            max_duration_seconds=8,
            phrase_timeout_seconds=4,
        )
