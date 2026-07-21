"""Reliable local wake-word detection and wake-session state tracking."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
from typing import Callable

from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.types import VoiceInputSettings, VoiceTranscriptionResult

LOGGER = logging.getLogger(__name__)


class WakeSessionState(str, Enum):
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass(frozen=True, slots=True)
class WakeDetection:
    detected: bool
    confidence: float
    blocked_by_cooldown: bool = False


class WakeWordEngine:
    """Detect a small local phrase set and track one command-listening session."""

    TARGETS = ("oi fibi", "hey fibi", "fibi")
    ALIASES = {
        "oy": "oi",
        "hoi": "oi",
        "hay": "hey",
        "hei": "hey",
        "phoebe": "fibi",
        "feebee": "fibi",
        "feebe": "fibi",
        "fibby": "fibi",
        "fee bee": "fibi",
    }
    ALLOWED_TRANSITIONS = {
        WakeSessionState.IDLE: {WakeSessionState.WAKE_DETECTED},
        WakeSessionState.WAKE_DETECTED: {WakeSessionState.LISTENING, WakeSessionState.IDLE},
        WakeSessionState.LISTENING: {WakeSessionState.TRANSCRIBING, WakeSessionState.IDLE},
        WakeSessionState.TRANSCRIBING: {WakeSessionState.THINKING, WakeSessionState.IDLE},
        WakeSessionState.THINKING: {WakeSessionState.SPEAKING, WakeSessionState.IDLE},
        WakeSessionState.SPEAKING: {WakeSessionState.IDLE},
    }

    def __init__(
        self,
        recognizer: SpeechRecognitionEngine,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.recognizer = recognizer
        self.clock = clock
        self.state = WakeSessionState.IDLE
        self.transition_history: list[WakeSessionState] = [self.state]
        self.last_activation_at = float("-inf")
        self.last_detection = WakeDetection(False, 0.0)

    @classmethod
    def normalize(cls, transcript: str) -> str:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", (transcript or "").lower())
        normalized = " ".join(normalized.split())
        for source in sorted(cls.ALIASES, key=len, reverse=True):
            normalized = re.sub(
                rf"\b{re.escape(source)}\b",
                cls.ALIASES[source],
                normalized,
            )
        return " ".join(normalized.split())

    @classmethod
    def phrase_score(cls, transcript: str) -> float:
        normalized = cls.normalize(transcript)
        if not normalized:
            return 0.0
        words = normalized.split()
        candidates = {normalized}
        candidates.update(" ".join(words[index:index + 2]) for index in range(len(words)))
        if "fibi" in words:
            candidates.add("fibi")
        return max(
            SequenceMatcher(None, candidate, target).ratio()
            for candidate in candidates
            for target in cls.TARGETS
        )

    @classmethod
    def detected(
        cls,
        transcript: str,
        *,
        sensitivity: float = 0.72,
        speech_confidence: float = 0.85,
    ) -> bool:
        lexical = cls.phrase_score(transcript)
        confidence = lexical * 0.75 + max(0.0, min(1.0, speech_confidence)) * 0.25
        return confidence >= max(0.45, min(0.95, sensitivity))

    def evaluate(
        self,
        transcript: str,
        *,
        speech_confidence: float,
        sensitivity: float,
        cooldown_seconds: float,
    ) -> WakeDetection:
        lexical = self.phrase_score(transcript)
        confidence = lexical * 0.75 + max(0.0, min(1.0, speech_confidence)) * 0.25
        threshold = max(0.45, min(0.95, sensitivity))
        now = self.clock()
        cooldown = max(2.0, min(3.0, cooldown_seconds))
        blocked = confidence >= threshold and now - self.last_activation_at < cooldown
        detected = confidence >= threshold and not blocked
        if detected:
            self.last_activation_at = now
            self.transition(WakeSessionState.WAKE_DETECTED)
            LOGGER.info("wake phrase detected confidence=%.3f", confidence)
        elif blocked:
            LOGGER.info("wake duplicate suppressed confidence=%.3f", confidence)
        self.last_detection = WakeDetection(detected, confidence, blocked)
        return self.last_detection

    def listen_once(self, settings: VoiceInputSettings) -> tuple[bool, VoiceTranscriptionResult]:
        LOGGER.info("wake detector started")
        result = self.recognizer.listen(
            settings,
            source="wake_word_probe",
            max_duration_seconds=3,
            phrase_timeout_seconds=2,
        )
        detection = self.evaluate(
            result.transcript,
            speech_confidence=result.confidence,
            sensitivity=settings.wake_word_sensitivity,
            cooldown_seconds=settings.wake_word_cooldown_seconds,
        )
        result.confidence = detection.confidence
        return detection.detected, result

    def begin_command_capture(self) -> None:
        self.transition(WakeSessionState.LISTENING)
        LOGGER.info("wake listening started")

    def capture_command(self, settings: VoiceInputSettings) -> VoiceTranscriptionResult:
        self.begin_command_capture()
        result = self.recognizer.listen(
            settings,
            source="wake_word_command",
            max_duration_seconds=8,
            phrase_timeout_seconds=4,
        )
        self.transition(WakeSessionState.TRANSCRIBING)
        LOGGER.info("wake listening stopped")
        if result.error or not result.transcript:
            LOGGER.info("wake transcription failure")
            self.reset()
        else:
            LOGGER.info("wake transcription success confidence=%.3f", result.confidence)
        return result

    def mark_thinking(self) -> None:
        self.transition(WakeSessionState.THINKING)

    def mark_speaking(self) -> None:
        if self.state == WakeSessionState.THINKING:
            self.transition(WakeSessionState.SPEAKING)

    def reset(self) -> None:
        if self.state != WakeSessionState.IDLE:
            self.state = WakeSessionState.IDLE
            self.transition_history.append(self.state)
            LOGGER.info("wake session state=idle")

    def transition(self, state: WakeSessionState) -> None:
        if state == self.state:
            return
        if state not in self.ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid wake transition: {self.state.value} -> {state.value}")
        self.state = state
        self.transition_history.append(state)
        LOGGER.info("wake session state=%s", state.value)
