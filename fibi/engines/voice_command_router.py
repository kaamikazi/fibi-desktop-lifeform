"""Route transcribed voice text into Fibi's normal safe text pipeline."""

from __future__ import annotations

from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.types import VoiceCommandResult, VoiceInputSettings, VoiceTranscriptionResult


class VoiceCommandRouter:
    """Decide whether voice text can be treated as a direct user message."""

    def __init__(self, action_detector: ActionIntentDetector | None = None) -> None:
        self.action_detector = action_detector or ActionIntentDetector()

    def route(
        self,
        transcription: VoiceTranscriptionResult,
        settings: VoiceInputSettings,
        quiet_active: bool = False,
    ) -> VoiceCommandResult:
        if not settings.allow_voice_input:
            return VoiceCommandResult(True, False, response_text="ears tucked away.", error="voice disabled", source=transcription.source)
        if transcription.source in {"future_wake_word", "wake_word_command"} and not settings.wake_word_enabled:
            return VoiceCommandResult(True, False, response_text="wake word sleeping.", error="wake word disabled", source=transcription.source)
        if transcription.error:
            return VoiceCommandResult(True, False, response_text=transcription.error, error=transcription.error, source=transcription.source)

        text = transcription.transcript.strip()
        if not text:
            return VoiceCommandResult(True, False, response_text="say again?", error="empty transcript", source=transcription.source)

        intent = self.action_detector.detect(text, direct_user_initiated=True)
        if transcription.confidence < settings.require_confirmation_below_confidence:
            if intent is not None:
                return VoiceCommandResult(
                    True,
                    False,
                    text,
                    transcription.confidence,
                    f"not sure. i heard: {text}",
                    needs_user_confirmation=True,
                    source=transcription.source,
                )
            return VoiceCommandResult(True, False, text, transcription.confidence, "not sure. say again?", source=transcription.source)

        return VoiceCommandResult(
            True,
            True,
            text,
            transcription.confidence,
            f"i heard: {text}" if settings.show_transcript_before_action and intent is not None else "",
            source=transcription.source,
        )
