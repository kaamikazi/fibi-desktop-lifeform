"""Central response cleanup helpers for final display and speech text."""

from __future__ import annotations

import logging
import re

from fibi.brain.cleanup import clean_response, extract_expression_markers, remove_mood_tags, tts_safe_text

LOGGER = logging.getLogger(__name__)


class ResponsePipeline:
    """Normalize model text before UI, memory, and voice output."""

    MOOD_TAG_PATTERN = re.compile(r"\[(idle|happy|thinking|sleepy|angry|talking)\]", re.IGNORECASE)

    def clean_model_reply(self, raw: str) -> tuple[str, str]:
        has_mood_tag = bool(self.MOOD_TAG_PATTERN.search(raw or ""))
        after_mood, mood = remove_mood_tags(raw or "")
        marker_result = extract_expression_markers(after_mood)
        display = clean_response(marker_result.text)
        expression = marker_result.expression or (mood if has_mood_tag else "")
        LOGGER.info(
            "response_pipeline.cleaned",
            extra={"mood": expression, "empty": not bool(display), "marker_count": len(marker_result.markers)},
        )
        return display, expression

    def tts_text(self, display_text: str) -> str:
        return tts_safe_text(display_text)
