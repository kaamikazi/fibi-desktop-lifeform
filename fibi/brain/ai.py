"""Local-first AI brain for Fibi.

Fast path:
- tiny local greeting replies return instantly
- normal replies use a short prompt and small Ollama model
- slow/empty Ollama replies retry once, then use varied fallbacks
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

import requests

from fibi.brain.cleanup import clean_response, is_effectively_empty, remove_mood_tags
from fibi.brain.mood import choose_mood, normalize_mood
from fibi.settings import OLLAMA_MODEL, OLLAMA_MODEL_FALLBACKS, OLLAMA_TIMEOUT_SECONDS, OLLAMA_URL

FIBI_SYSTEM = """You are Fibi, a cute chibi desktop AI assistant.
Sleepy, playful, slightly chaotic, helpful.
Answer the user's question or request directly and usefully first.
Add at most one short playful sentence after the useful answer.
Never replace information with cute filler or a roleplay action.
Use actual unicode emojis only.
Never write emoji names like "sleepy face" or "red heart".
No excessive emojis.
End with one mood tag: [idle] [happy] [thinking] [talking] [sleepy] [angry].
"""

GREETING_WORDS = {"hey", "hi", "hello", "yo", "sup"}
GREETING_REPLIES = [
    "hii, I'm awake-ish \U0001f634",
    "eepy but here.",
    "yo tiny human.",
]


@dataclass
class GenerationResult:
    raw: str | None
    try_next_model: bool = False


def _fallback_response() -> tuple[str, str]:
    replies = [
        "eepy... say that again?",
        "my tiny brain dropped the thought.",
        "wait wait, I forgot what I was saying.",
        "hmm... Windows distracted me.",
    ]
    reply = clean_response(random.choice(replies))
    return reply, choose_mood(reply_text=reply)


def _local_greeting(user_message: str) -> tuple[str, str] | None:
    cleaned = user_message.strip().lower().strip(" .,!?\t\r\n")
    if cleaned in GREETING_WORDS:
        start = time.perf_counter()
        reply = random.choice(GREETING_REPLIES)
        print(f"AI START TIME: {start:.3f}")
        print(f"AI END TIME: {time.perf_counter():.3f}")
        print("MODEL USED: local-greeting")
        print("AI DURATION SECONDS: 0.00")
        print(f"CLEANED DISPLAY: {reply}")
        return reply, "happy"
    return None


def parse_response(raw: str) -> tuple[str, str]:
    """Run Fibi's reply cleanup in the intended order."""
    without_mood, expression = remove_mood_tags(raw)
    print(f"AFTER MOOD CLEAN: {without_mood}")

    cleaned = clean_response(without_mood)
    print(f"CLEANED DISPLAY: {cleaned}")

    return cleaned, normalize_mood(expression)


def _format_history(history: list[dict]) -> str:
    """Keep only the last two messages so prompts stay fast."""
    lines: list[str] = []

    for message in history[-2:]:
        role = "User" if message.get("role") == "user" else "Fibi"
        content = str(message.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def ask_fibi(user_message: str, history: list[dict] | None = None, smart: bool = False) -> tuple[str, str]:
    """Ask Fibi something and return ``(reply_text, expression)``."""
    local_reply = _local_greeting(user_message)
    if local_reply:
        return local_reply

    history = history or []
    prompt = _build_prompt(user_message, history)

    raw = _generate_with_model_priority(prompt)
    if raw is None:
        return _fallback_response()

    print(f"RAW AI REPLY: {raw}")

    if is_effectively_empty(raw):
        retry_prompt = _simple_retry_prompt(user_message)
        raw = _generate_with_model_priority(retry_prompt)
        if raw is None:
            return _fallback_response()

        print(f"RAW AI REPLY: {raw}")

    reply, expression = parse_response(raw)
    if is_effectively_empty(reply):
        return _fallback_response()

    mood = choose_mood(user_text=user_message, reply_text=reply)
    return reply, mood if mood != "idle" else expression


def _build_prompt(user_message: str, history: list[dict]) -> str:
    prompt_parts = [f"System: {FIBI_SYSTEM}"]
    previous_messages = _format_history(history)
    if previous_messages:
        prompt_parts.append(previous_messages)
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Fibi:")
    return "\n\n".join(prompt_parts)


def _model_candidates() -> list[str]:
    """Return model priority with duplicates removed."""
    models = [OLLAMA_MODEL, *OLLAMA_MODEL_FALLBACKS]
    candidates: list[str] = []
    for model in models:
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _generate_with_model_priority(prompt: str) -> str | None:
    """Try configured model priority, stopping on slow/network failures."""
    for model in _model_candidates():
        result = _generate_reply(model, prompt)
        if result.raw is not None:
            return result.raw
        if not result.try_next_model:
            return None
    return None


def _generate_reply(model: str, prompt: str) -> GenerationResult:
    """Call Ollama once with timing logs and a hard timeout."""
    start = time.perf_counter()
    print(f"AI START TIME: {start:.3f}")
    print(f"MODEL USED: {model}")

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 320,
                    "temperature": 0.8,
                    "top_p": 0.9,
                },
            },
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            _log_ai_end(start, RuntimeError(response.text.strip() or "model not found"))
            return GenerationResult(None, try_next_model=True)

        response.raise_for_status()
        data = response.json()
    except requests.Timeout as error:
        _log_ai_end(start, error)
        return GenerationResult(None)
    except requests.RequestException as error:
        _log_ai_end(start, error)
        return GenerationResult(None)
    except ValueError as error:
        _log_ai_end(start, error)
        return GenerationResult(None)

    _log_ai_end(start)

    raw = str(data.get("response", ""))
    if not raw.strip():
        print(f"RAW OLLAMA RESPONSE OBJECT: {data}")

    return GenerationResult(raw)


def _log_ai_end(start: float, error: Exception | None = None) -> None:
    end = time.perf_counter()
    print(f"AI END TIME: {end:.3f}")
    print(f"AI DURATION SECONDS: {end - start:.2f}")
    if error:
        print(f"ERROR: {error}")


def _simple_retry_prompt(user_message: str) -> str:
    """Simpler prompt used once when Ollama returns an empty-looking reply."""
    return (
        "Answer the user directly with concrete, useful information. "
        "No cute-only filler, emoji names, stage directions, or mood-only answer.\n"
        f"User: {user_message}\n"
        "Fibi:"
    )


def analyze_screen(screen_text: str) -> tuple[str, str]:
    """Optional helper for later screen-aware behavior."""
    if not screen_text.strip():
        return "", "idle"

    return ask_fibi(
        "Give one short helpful observation about this screen text:\n"
        f"{screen_text[:500]}",
        smart=True,
    )
