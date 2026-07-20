"""Optional text-to-speech support for Fibi.

Voice is deliberately optional. If edge-tts or audio playback is unavailable,
``speak`` returns False and the UI keeps running.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine

VOICE = "en-US-AnaNeural"
RATE = "+5%"
PITCH = "+8Hz"


@dataclass(slots=True)
class VoiceOutputResult:
    base_audio_path: Path | None = None
    final_audio_path: Path | None = None
    converted: bool = False
    fallback_used: bool = True
    fallback_reason: str = ""
    edge_tts_ok: bool = False
    rvc_duration_ms: float = 0.0


def is_voice_available() -> bool:
    """Return True when the optional voice dependencies can be imported."""
    try:
        import edge_tts  # noqa: F401
        import pygame  # noqa: F401
    except ImportError:
        return False

    return True


async def synthesize_to_file_async(text: str, output_path: str | Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(str(output_path))


def synthesize_to_file(text: str, output_path: str | Path) -> bool:
    if not text.strip() or not is_voice_available():
        return False
    try:
        asyncio.run(synthesize_to_file_async(text, output_path))
    except Exception:
        return False
    return True


def prepare_voice_output(
    text: str,
    settings,
    rvc_engine,
    voice_cache,
    *,
    synthesize: Callable[[str, str | Path], bool] = synthesize_to_file,
) -> VoiceOutputResult:
    """Create base edge-tts audio, then optionally convert it through RVC.

    The real unicode text cleanup happens before this helper. This function is
    only about file generation and keeping RVC fallback reasons visible.
    """
    result = VoiceOutputResult()
    rvc_enabled = bool(settings.allow_rvc_voice_skin and settings.rvc_enabled)
    model_path = VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)
    index_path = VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)
    print(f"RVC_ENABLED: {str(rvc_enabled).lower()}")
    print(f"RVC_BACKEND: {settings.rvc_backend}")
    print(f"RVC_MODEL_EXISTS: {str(model_path.exists()).lower()}")
    print(f"RVC_INDEX_EXISTS: {str(index_path.exists()).lower()}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=str(rvc_engine.temp_dir)) as file:
        base_path = Path(file.name)
    result.base_audio_path = base_path
    print(f"EDGE_TTS_OUTPUT_PATH: {base_path}")
    result.edge_tts_ok = synthesize(text, base_path)
    if not result.edge_tts_ok:
        result.fallback_reason = "edge_tts_failed"
        result.final_audio_path = None
        print("RVC_FALLBACK_USED: true")
        print(f"RVC_FALLBACK_REASON: {result.fallback_reason}")
        return result

    result.final_audio_path = base_path
    cache_path = None
    if (
        rvc_enabled
        and settings.rvc_cache_enabled
        and settings.rvc_cache_short_lines
        and voice_cache.can_cache(text)
    ):
        cache_path = voice_cache.key(
            text,
            "auto",
            settings.edge_tts_base_voice_en,
            settings.rvc_model_path or "",
            settings.rvc_pitch_shift,
            ".wav",
        )
        if cache_path.exists():
            print("VOICE_CACHE_HIT: true")
            result.final_audio_path = cache_path
            result.converted = True
            result.fallback_used = False
            result.fallback_reason = "none"
            print("RVC_FALLBACK_USED: false")
            print("RVC_FALLBACK_REASON: none")
            return result
        print("VOICE_CACHE_HIT: false")

    if not rvc_enabled:
        result.fallback_reason = "voice skin disabled"
        print("RVC_FALLBACK_USED: true")
        print(f"RVC_FALLBACK_REASON: {result.fallback_reason}")
        return result

    print("RVC_START")
    rvc_started = time.perf_counter()
    converted = rvc_engine.convert(base_path, settings)
    result.rvc_duration_ms = (time.perf_counter() - rvc_started) * 1000
    print(f"RVC_DURATION_MS: {result.rvc_duration_ms:.1f}")
    result.fallback_used = converted.fallback_used
    result.fallback_reason = converted.message or getattr(rvc_engine, "last_fallback_reason", "")
    if converted.ok and converted.output_path:
        result.converted = True
        result.final_audio_path = Path(converted.output_path)
        result.fallback_used = False
        result.fallback_reason = "none"
        if cache_path is not None:
            voice_cache.store(result.final_audio_path, cache_path)
            result.final_audio_path = cache_path

    print(f"RVC_FALLBACK_USED: {str(result.fallback_used).lower()}")
    print(f"RVC_FALLBACK_REASON: {result.fallback_reason or 'none'}")
    return result


def play_audio(path: str | Path) -> bool:
    try:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    except Exception:
        return False
    return True


def speak(text: str) -> bool:
    """Speak text in the current background thread.

    Returns False when optional voice support is missing or playback fails.
    """
    if not text.strip() or not is_voice_available():
        return False

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as file:
            temp_path = file.name
        if not synthesize_to_file(text, temp_path):
            return False
        return play_audio(temp_path)
    finally:
        if temp_path:
            with suppress(OSError):
                os.remove(temp_path)
