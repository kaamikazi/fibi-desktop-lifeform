"""Health checks for push-to-talk voice input."""

from __future__ import annotations

from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.types import VoiceInputSettings


class VoiceHealthEngine:
    """Report whether local voice input looks usable."""

    def __init__(self, recognizer: SpeechRecognitionEngine | None = None) -> None:
        self.recognizer = recognizer or SpeechRecognitionEngine()

    def status_line(self, settings: VoiceInputSettings) -> str:
        ears = "ears on" if settings.allow_voice_input else "ears off"
        try:
            import speech_recognition  # noqa: F401
            package = True
        except ImportError:
            package = False
        devices = self.recognizer.devices() if package else []
        mic = "mic maybe available" if devices else "mic unknown"
        if not package:
            mic = "voice brain not installed"
        mode = "push-to-talk only" if settings.push_to_talk_enabled else "push-to-talk off"
        return f"{ears}. {mode}. {mic}."

    def mic_test(self, settings: VoiceInputSettings) -> str:
        devices = self.recognizer.devices()
        if not devices:
            return "mic creature missing."
        selected = settings.microphone_device_id
        if selected and not any(device.device_id == selected for device in devices):
            return "selected mic vanished."
        return f"found {len(devices)} mic creature(s)."
