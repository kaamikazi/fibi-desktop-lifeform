"""Optional tiny sound effects for Fibi.

If pygame or sound assets are missing, this module quietly does nothing.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SOUND_DIRS = [PROJECT_DIR / "assets" / "sounds", PROJECT_DIR / "ui" / "assets" / "sounds"]
SOUND_EVENT_MAP = {
    "click": "click",
    "happy": "happy",
    "annoyed": "annoyed",
    "sleep": "sleep",
    "wake": "wake",
    "drag": "drag",
    "success": "success",
}


def _sound_path(name: str) -> Path | None:
    for folder in SOUND_DIRS:
        for suffix in (".wav", ".mp3", ".ogg"):
            path = folder / f"{name}{suffix}"
            if path.exists():
                return path
    return None


def play_sound(name: str) -> None:
    """Play a small sound if pygame and a matching asset are available."""
    path = _sound_path(name)
    if path is None:
        return

    try:
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.Sound(str(path)).play()
    except Exception:
        return


def play_sound_event(event: str) -> None:
    """Play an optional mapped creature sound; missing files remain silent."""
    name = SOUND_EVENT_MAP.get(str(event).lower())
    if name:
        play_sound(name)
