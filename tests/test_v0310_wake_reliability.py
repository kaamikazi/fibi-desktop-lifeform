"""Reliable local wake phrase, state-machine, and pet indicator tests."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from fibi.engines.types import VoiceInputSettings, VoiceTranscriptionResult
from fibi.engines.wake_word_engine import WakeSessionState, WakeWordEngine
from fibi.ui.fibi_pet_window import FibiPetWindow
from tests.smoke_v012_actions import make_core


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class QueuedRecognizer:
    def __init__(self, results: list[VoiceTranscriptionResult]) -> None:
        self.results = list(results)
        self.calls = 0

    def listen(self, *args, **kwargs) -> VoiceTranscriptionResult:
        self.calls += 1
        return self.results.pop(0)


@pytest.mark.parametrize(
    "phrase",
    [
        "oi fibi",
        "OI, FIBI!",
        "hey fibi",
        "fibi",
        "Hey Phoebe",
        "oy fee bee",
    ],
)
def test_supported_wake_phrases_and_stt_variations(phrase: str) -> None:
    assert WakeWordEngine.detected(phrase)


def test_sensitivity_threshold_is_configurable() -> None:
    phrase = "hey fib"
    assert WakeWordEngine.detected(phrase, sensitivity=0.55)
    assert not WakeWordEngine.detected(phrase, sensitivity=0.95, speech_confidence=0.4)


def test_duplicate_wake_triggers_are_suppressed_for_cooldown() -> None:
    clock = FakeClock()
    recognizer = QueuedRecognizer([])
    engine = WakeWordEngine(recognizer, clock=clock)  # type: ignore[arg-type]
    first = engine.evaluate("oi fibi", speech_confidence=0.9, sensitivity=0.7, cooldown_seconds=2.5)
    engine.reset()
    clock.now += 1.0
    duplicate = engine.evaluate("hey fibi", speech_confidence=0.9, sensitivity=0.7, cooldown_seconds=2.5)
    clock.now += 2.0
    allowed = engine.evaluate("fibi", speech_confidence=0.9, sensitivity=0.7, cooldown_seconds=2.5)
    assert first.detected
    assert duplicate.blocked_by_cooldown and not duplicate.detected
    assert allowed.detected


def test_complete_wake_session_state_sequence() -> None:
    recognizer = QueuedRecognizer([
        VoiceTranscriptionResult("oi fibi", confidence=0.9, should_route_to_core=True),
        VoiceTranscriptionResult("open settings", confidence=0.9, should_route_to_core=True),
    ])
    engine = WakeWordEngine(recognizer)  # type: ignore[arg-type]
    settings = VoiceInputSettings(allow_voice_input=True, wake_word_enabled=True)
    detected, _result = engine.listen_once(settings)
    assert detected
    command = engine.capture_command(settings)
    assert command.should_route_to_core
    engine.mark_thinking()
    engine.mark_speaking()
    engine.reset()
    assert engine.transition_history == [
        WakeSessionState.IDLE,
        WakeSessionState.WAKE_DETECTED,
        WakeSessionState.LISTENING,
        WakeSessionState.TRANSCRIBING,
        WakeSessionState.THINKING,
        WakeSessionState.SPEAKING,
        WakeSessionState.IDLE,
    ]


def test_command_timeout_returns_state_to_idle() -> None:
    recognizer = QueuedRecognizer([
        VoiceTranscriptionResult("oi fibi", confidence=0.9, should_route_to_core=True),
        VoiceTranscriptionResult(error="say again?", source="wake_word_command"),
    ])
    engine = WakeWordEngine(recognizer)  # type: ignore[arg-type]
    settings = VoiceInputSettings(allow_voice_input=True, wake_word_enabled=True)
    assert engine.listen_once(settings)[0]
    result = engine.capture_command(settings)
    assert result.error
    assert engine.state == WakeSessionState.IDLE


def test_disabled_wake_mode_does_not_touch_microphone(tmp_path: Path) -> None:
    core, _, _ = make_core(tmp_path / "core", [], [])
    recognizer = QueuedRecognizer([])
    core.wake_word = WakeWordEngine(recognizer)  # type: ignore[arg-type]
    detected, result = core.listen_for_wake_once()
    assert not detected
    assert result.error == "wake word disabled"
    assert recognizer.calls == 0
    assert "off" in core.respond("/wake test").display_text.lower()


def test_wake_test_and_logs_do_not_expose_transcript(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    core, _, _ = make_core(tmp_path / "core", [], [])
    secret_transcript = "oi fibi private spoken command"
    recognizer = QueuedRecognizer([
        VoiceTranscriptionResult(secret_transcript, confidence=0.9, should_route_to_core=True),
    ])
    core.wake_word = WakeWordEngine(recognizer)  # type: ignore[arg-type]
    core.respond("/wake on")
    with caplog.at_level(logging.INFO):
        response = core.respond("/wake test")
    assert "confidence" in response.display_text.lower()
    assert secret_transcript not in caplog.text
    assert "wake detector started" in caplog.text
    assert "wake phrase detected" in caplog.text


def test_pet_listening_and_transcribing_indicators(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    core, _, _ = make_core(tmp_path / "core", [], [])
    pet = FibiPetWindow(core=core, life=core.life)
    pet.sprite.animation_timer.stop()
    pet.idle_timer.stop()
    pet.show()
    app.processEvents()
    pet._on_wake_state_changed("wake_detected")
    assert pet.microphone_indicator.text() == "MIC: HEARD"
    assert pet.life.is_listening
    assert pet.bubble._full_text == "hm?"
    pet._on_wake_state_changed("listening")
    assert pet.microphone_indicator.text() == "MIC: LISTEN"
    assert pet.bubble._full_text == "I'm listening."
    pet._on_wake_state_changed("transcribing")
    assert pet.microphone_indicator.text() == "MIC: TEXT"
    assert pet.life.is_thinking
    pet._on_wake_state_changed("idle")
    assert not pet.life.is_listening
    assert not pet.life.is_thinking
    pet._quitting = True
    pet.close()
    app.processEvents()
