"""Voice transcript router boundary."""

from __future__ import annotations

from fibi.engines.types import VoiceCommandResult, VoiceInputSettings, VoiceTranscriptionResult
from fibi.engines.voice_command_router import VoiceCommandRouter


class VoiceRouter:
    """Adapter around the existing voice command router."""

    def __init__(self, router: VoiceCommandRouter) -> None:
        self._router = router

    def route(
        self,
        transcription: VoiceTranscriptionResult,
        settings: VoiceInputSettings,
        *,
        quiet_active: bool,
    ) -> VoiceCommandResult:
        return self._router.route(transcription, settings, quiet_active=quiet_active)
