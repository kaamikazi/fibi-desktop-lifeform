"""Central response cleanup helpers for final display and speech text."""

from __future__ import annotations

import logging
import re

from fibi.brain.cleanup import clean_response, remove_mood_tags, tts_safe_text

LOGGER = logging.getLogger(__name__)


class ResponsePipeline:
    """Normalize model text before UI, memory, and voice output."""

    MOOD_TAG_PATTERN = re.compile(r"\[(idle|happy|thinking|sleepy|angry|talking)\]", re.IGNORECASE)

    def clean_model_reply(self, raw: str) -> tuple[str, str]:
        has_mood_tag = bool(self.MOOD_TAG_PATTERN.search(raw or ""))
        after_mood, mood = remove_mood_tags(raw or "")
        display = clean_response(after_mood)
        LOGGER.info("response_pipeline.cleaned", extra={"mood": mood if has_mood_tag else "", "empty": not bool(display)})
        return display, mood if has_mood_tag else ""

    def tts_text(self, display_text: str) -> str:
        return tts_safe_text(display_text)
