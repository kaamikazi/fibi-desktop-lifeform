import pytest

from fibi.brain.cleanup import (
    clean_response,
    extract_expression_markers,
    is_effectively_empty,
    remove_mood_tags,
    tts_safe_text,
)
from fibi.engines.routers.response_pipeline import ResponsePipeline


def test_clean_response_replaces_emoji_descriptions():
    assert clean_response("hehe smiling face with smiling eyes") == "hehe"


def test_clean_response_keeps_real_emojis():
    assert clean_response("hehe \U0001f60a") == "hehe \U0001f60a"


def test_clean_response_removes_multiple_emoji_names():
    assert clean_response("hehe sleepy face red heart") == "hehe"


def test_clean_response_keeps_real_sleepy_and_heart_emojis():
    assert clean_response("hehe \U0001f634 \u2764\ufe0f") == "hehe \U0001f634 \u2764\ufe0f"


def test_remove_mood_tags_strips_expression_text():
    text, mood = remove_mood_tags("[happy]")
    assert text == ""
    assert mood == "happy"


def test_removed_emoji_description_counts_as_empty():
    assert is_effectively_empty("sleepy face red heart")


def test_emoji_only_display_gets_tts_fallback():
    assert tts_safe_text("\U0001f923") == "hehe"


def test_emoji_only_sleepy_gets_sleepy_tts():
    assert tts_safe_text("\U0001f634") == "eepy"


def test_mixed_text_tts_drops_emoji():
    assert tts_safe_text("hehe \U0001f634") == "hehe"


@pytest.mark.parametrize(
    ("raw", "visible", "expression"),
    [
        ("*yawn* I'm getting sleepy.", "I'm getting sleepy.", "sleepy"),
        ("*smiles* hello.", "hello.", "happy"),
        ("*giggles* giggles. okay.", "okay.", "happy"),
        ("*sighs* still broken.", "still broken.", "thinking"),
        ("*blinks* here.", "here.", "idle"),
        ("*looks away* hmm.", "hmm.", "thinking"),
        ("*sleepy* eepy.", "eepy.", "sleepy"),
        ("*excited* it worked!", "it worked!", "happy"),
    ],
)
def test_expression_markers_are_extracted(raw: str, visible: str, expression: str) -> None:
    result = extract_expression_markers(raw)
    assert result.text == visible
    assert result.expression == expression
    assert tts_safe_text(raw) == visible


def test_unknown_asterisk_emphasis_is_preserved() -> None:
    result = extract_expression_markers("that is *really* tiny")
    assert result.text == "that is *really* tiny"
    assert not result.expression


def test_response_pipeline_separates_animation_from_display() -> None:
    display, expression = ResponsePipeline().clean_model_reply("[happy] *yawn* I'm getting sleepy.")
    assert display == "I'm getting sleepy."
    assert expression == "sleepy"
