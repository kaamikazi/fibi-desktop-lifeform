"""Response cleanup helpers for Fibi.

Local models sometimes write emoji names as plain English, such as
``sleepy face`` or ``red heart``. Fibi should either use real unicode emojis or
say nothing about the emoji, so this module removes those written-out names.
Actual unicode emojis are left untouched.
"""

from __future__ import annotations

import re
import string
from functools import lru_cache


FALLBACK_EMOJI_PHRASES = {
    "angry face",
    "blue heart",
    "crying face",
    "face with tears of joy",
    "fire",
    "green heart",
    "grinning face",
    "grinning face with smiling eyes",
    "heart emoji",
    "loudly crying face",
    "pink heart",
    "pleading face",
    "pouting face",
    "red heart",
    "skull",
    "sleeping face",
    "sleepy face",
    "slightly smiling face",
    "smiling face",
    "smiling face with smiling eyes",
    "sparkles",
    "sparkles emoji",
    "thinking face",
    "winking face",
    "yellow heart",
}


def _name_to_phrase(name: str) -> str:
    """Turn ':sleepy_face:' or 'sleepy-face' into 'sleepy face'."""
    return name.strip(":").replace("_", " ").replace("-", " ").lower()


def _phrase_pattern(phrase: str) -> str:
    """Build a regex that tolerates spaces, underscores, or hyphens."""
    words = [re.escape(word) for word in phrase.split() if word]
    return r"[\s_-]+".join(words)


@lru_cache(maxsize=1)
def _emoji_name_phrases() -> tuple[str, ...]:
    """Collect emoji English names from the optional ``emoji`` package.

    If the package is missing, the fallback list below still catches common
    model outputs. The app keeps running either way.
    """
    phrases = set(FALLBACK_EMOJI_PHRASES)

    try:
        import emoji
    except ImportError:
        return tuple(sorted(phrases, key=len, reverse=True))

    for data in emoji.EMOJI_DATA.values():
        english_name = data.get("en", "")
        if english_name:
            phrases.add(_name_to_phrase(english_name))

        for alias in data.get("alias", []):
            phrases.add(_name_to_phrase(alias))

    return tuple(sorted(phrases, key=len, reverse=True))


@lru_cache(maxsize=1)
def _emoji_name_regex() -> re.Pattern:
    phrase_patterns = [_phrase_pattern(phrase) for phrase in _emoji_name_phrases()]
    joined_phrases = "|".join(phrase_patterns)

    # Match bare phrases and optional shortcode colons, e.g. sleepy face,
    # sleepy_face, sleepy-face, or :sleepy_face:.
    return re.compile(rf"(?<!\w):?(?:{joined_phrases}):?(?!\w)", re.IGNORECASE)


def clean_response(text: str) -> str:
    """Remove written emoji names while preserving actual unicode emojis."""
    cleaned = text or ""

    cleaned = _emoji_name_regex().sub("", cleaned)

    # Fallback for model phrases not present in the emoji package. This is
    # intentionally broad, but only targets short phrases ending in "face".
    cleaned = re.sub(
        r"\b(?:[a-z]+[\s_-]+){0,4}face\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Remove wrapper wording like "emoji: red heart" after the phrase itself
    # has already been removed.
    cleaned = re.sub(r"\bemoji\s*:\s*", "", cleaned, flags=re.IGNORECASE)

    # Tidy punctuation and spaces created by removals.
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"([([{])\s+", r"\1", cleaned)
    cleaned = re.sub(r"\s+([)\]}])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,.;:!?-]+|[\s,.;:!?-]+$", "", cleaned)

    return cleaned.strip()


def remove_mood_tags(text: str) -> tuple[str, str]:
    """Remove Fibi mood tags and return ``(text_without_tags, mood)``."""
    mood = "happy"
    match = re.search(r"\[(idle|happy|thinking|talking|sleepy|angry)\]", text or "", re.IGNORECASE)

    if match:
        mood = match.group(1).lower()

    without_tags = re.sub(r"\[(idle|happy|thinking|talking|sleepy|angry)\]", "", text or "", flags=re.IGNORECASE)
    return without_tags.strip(), mood


def is_effectively_empty(text: str) -> bool:
    """Return True when cleanup leaves no meaningful display text."""
    if not (text or "").strip():
        return True

    cleaned = clean_response(remove_mood_tags(text)[0])
    return not cleaned.strip(string.whitespace + string.punctuation)


def tts_safe_text(display_text: str) -> str:
    """Make a short pronounceable TTS string for emoji-only replies.

    Display text can be just an emoji, but most TTS voices handle a tiny word
    better than a standalone symbol.
    """
    if not display_text.strip():
        return ""

    emoji_sound = _emoji_only_sound(display_text)
    if emoji_sound:
        return emoji_sound

    text_without_emoji = display_text
    try:
        import emoji

        text_without_emoji = emoji.replace_emoji(display_text, replace="")
    except ImportError:
        text_without_emoji = re.sub(r"[^\w\s,.!?'-]", "", display_text)

    if text_without_emoji.strip(string.whitespace + string.punctuation):
        return text_without_emoji.strip()

    return "hehe"


def _emoji_only_sound(display_text: str) -> str:
    """Return a natural sound when the visible reply is only emoji."""
    text = display_text.strip()
    if not text:
        return ""

    try:
        import emoji

        without_emoji = emoji.replace_emoji(text, replace="")
    except ImportError:
        without_emoji = re.sub(r"[^\w\s,.!?'-]", "", text)

    if without_emoji.strip(string.whitespace + string.punctuation):
        return ""

    if "\U0001f923" in text or "\U0001f602" in text:
        return "hehe"
    if "\U0001f62d" in text or "\U0001f622" in text:
        return "wahh"
    if "\U0001f634" in text:
        return "eepy"
    if "\u2764" in text or "\U0001f497" in text or "\U0001fa77" in text:
        return "aww"
    if "\U0001f480" in text:
        return "dead."

    return "hehe"
