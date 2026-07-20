"""Response cleanup helpers for Fibi.

Local models sometimes write emoji names as plain English, such as
``sleepy face`` or ``red heart``. Fibi should either use real unicode emojis or
say nothing about the emoji, so this module removes those written-out names.
Actual unicode emojis are left untouched.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
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

ACTION_MARKER_EXPRESSIONS = {
    "yawn": "sleepy",
    "yawns": "sleepy",
    "smile": "happy",
    "smiles": "happy",
    "giggle": "happy",
    "giggles": "happy",
    "sigh": "thinking",
    "sighs": "thinking",
    "blink": "idle",
    "blinks": "idle",
    "looks away": "thinking",
    "sleepy": "sleepy",
    "excited": "happy",
}
ACTION_MARKER_PATTERN = re.compile(
    r"\*\s*(yawns?|smiles?|giggles?|sighs?|blinks?|looks\s+away|sleepy|excited)\s*\*",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExpressionMarkerResult:
    """Visible text and animation metadata extracted from model stage directions."""

    text: str
    expression: str = ""
    markers: tuple[str, ...] = ()


def extract_expression_markers(text: str) -> ExpressionMarkerResult:
    """Remove supported ``*action*`` markers and select an expression.

    Only Fibi's small action vocabulary is stripped. Other asterisk text is
    left alone so ordinary emphasis is not mistaken for an animation command.
    """

    source = text or ""
    markers = tuple(
        re.sub(r"\s+", " ", match.group(1).lower()).strip()
        for match in ACTION_MARKER_PATTERN.finditer(source)
    )
    cleaned = ACTION_MARKER_PATTERN.sub(" ", source)
    cleaned = _remove_duplicated_action_prefix(cleaned, markers)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # Sleepy actions should win over short happy/idle cues when a model emits
    # more than one stage direction in a single short reply.
    expressions = [ACTION_MARKER_EXPRESSIONS[marker] for marker in markers]
    expression = next(
        (candidate for candidate in ("sleepy", "thinking", "happy", "idle") if candidate in expressions),
        "",
    )
    return ExpressionMarkerResult(cleaned, expression, markers)


def _remove_duplicated_action_prefix(text: str, markers: tuple[str, ...]) -> str:
    """Drop only a repeated leading stage direction, never natural prose."""

    cleaned = text.strip()
    for marker in markers:
        words = {
            "yawn": ("yawn", "yawns"),
            "yawns": ("yawn", "yawns"),
            "smile": ("smile", "smiles"),
            "smiles": ("smile", "smiles"),
            "giggle": ("giggle", "giggles"),
            "giggles": ("giggle", "giggles"),
            "sigh": ("sigh", "sighs"),
            "sighs": ("sigh", "sighs"),
            "blink": ("blink", "blinks"),
            "blinks": ("blink", "blinks"),
            "looks away": ("looks away",),
            "sleepy": ("sleepy",),
            "excited": ("excited",),
        }.get(marker, ())
        if not words:
            continue
        alternatives = "|".join(re.escape(word) for word in words)
        cleaned = re.sub(
            rf"^(?:{alternatives})\s*(?:[.!,:;-]+\s*|(?=(?:i|we|you|she|he|it|this|that)\b))",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
    return cleaned


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
            phrase = _name_to_phrase(english_name)
            if len(phrase.split()) > 1:
                phrases.add(phrase)

        for alias in data.get("alias", []):
            phrase = _name_to_phrase(alias)
            if len(phrase.split()) > 1:
                phrases.add(phrase)

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
    # Remove punctuation stranded at the beginning by cleanup, but preserve
    # the model's intentional sentence-ending punctuation.
    cleaned = re.sub(r"^[\s,.;:!?-]+", "", cleaned)

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
    display_text = extract_expression_markers(display_text).text
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
