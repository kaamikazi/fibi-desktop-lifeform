"""Push-to-talk speech recognition with safe local fallbacks."""

from __future__ import annotations

import time

from fibi.engines.types import VoiceDeviceInfo, VoiceInputSettings, VoiceTranscriptionResult


class SpeechRecognitionEngine:
    """Record a short phrase only after an explicit user listen request."""

    def listen(
        self,
        settings: VoiceInputSettings,
        source: str = "mic_button",
        max_duration_seconds: int = 6,
        phrase_timeout_seconds: int = 3,
    ) -> VoiceTranscriptionResult:
        started = time.perf_counter()
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError:
            return self._failure("voice brain not installed.", started, source)

        recognizer = sr.Recognizer()
        try:
            device_index = int(settings.microphone_device_id) if settings.microphone_device_id else None
        except (TypeError, ValueError):
            device_index = None
        try:
            with sr.Microphone(device_index=device_index) as microphone:
                recognizer.adjust_for_ambient_noise(microphone, duration=0.4)
                audio = recognizer.listen(
                    microphone,
                    timeout=phrase_timeout_seconds,
                    phrase_time_limit=max_duration_seconds,
                )
        except sr.WaitTimeoutError:
            return self._failure("say again?", started, source)
        except Exception:
            return self._failure("mic creature missing.", started, source)

        try:
            text = recognizer.recognize_sphinx(audio, language=settings.voice_language)
        except sr.UnknownValueError:
            return self._failure("i heard static.", started, source)
        except Exception:
            return self._failure("voice brain not installed.", started, source)

        transcript = str(text or "").strip()
        duration_ms = (time.perf_counter() - started) * 1000
        return VoiceTranscriptionResult(
            transcript=transcript,
            raw_text=transcript,
            confidence=0.85 if transcript else 0.0,
            duration_ms=duration_ms,
            error=None if transcript else "empty transcript",
            user_confirmed=False,
            source=source,
            should_route_to_core=bool(transcript),
        )

    def devices(self) -> list[VoiceDeviceInfo]:
        try:
            import speech_recognition as sr  # type: ignore
            names = sr.Microphone.list_microphone_names()
        except Exception:
            return []
        return [VoiceDeviceInfo(str(index), name, index == 0) for index, name in enumerate(names)]

    @staticmethod
    def _failure(message: str, started: float, source: str) -> VoiceTranscriptionResult:
        return VoiceTranscriptionResult(
            transcript="",
            raw_text="",
            confidence=0.0,
            duration_ms=(time.perf_counter() - started) * 1000,
            error=message,
            source=source,
            should_route_to_core=False,
        )
