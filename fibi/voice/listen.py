"""Compatibility wrapper for Fibi's push-to-talk speech recognition."""

from __future__ import annotations

from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.types import VoiceInputSettings


def listen() -> str:
    """Return a transcript or an empty string when voice input is unavailable."""
    result = SpeechRecognitionEngine().listen(VoiceInputSettings(allow_voice_input=True))
    return result.transcript
