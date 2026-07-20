from fibi.brain.cleanup import clean_response, is_effectively_empty, remove_mood_tags, tts_safe_text


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


