"""Central allowlists for Fibi's narrow manual desktop controls."""

from __future__ import annotations

import re
import sys
from pathlib import Path

KNOWN_WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
}
ALLOWED_WEB_HOSTS = {
    "www.youtube.com",
    "youtube.com",
    "www.google.com",
    "google.com",
    "github.com",
    "www.github.com",
    "mail.google.com",
    "chatgpt.com",
    "www.chatgpt.com",
    "en.wikipedia.org",
}

SAFE_COMMANDS: dict[str, tuple[str, ...]] = {
    "git status": ("git", "status", "--short"),
    "git diff --stat": ("git", "diff", "--stat"),
    "git log --oneline -5": ("git", "log", "--oneline", "-5"),
    "python --version": (sys.executable, "--version"),
}


def named_user_folders() -> dict[str, Path]:
    """Return the small set of folders natural-language actions may target."""

    home = Path.home().resolve()
    return {
        "desktop": (home / "Desktop").resolve(),
        "downloads": (home / "Downloads").resolve(),
        "documents": (home / "Documents").resolve(),
    }


def contains_secret_marker(text: str) -> bool:
    """Conservatively block typing or copying likely credential material."""

    return bool(
        re.search(
            r"(?:\b(api[_-]?key|token|password|passwd|secret|authorization)\b\s*[:=]\s*\S+|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:sk-|pk_|ghp_|AIza)[A-Za-z0-9_-]{16,})",
            text or "",
            flags=re.IGNORECASE,
        )
    )
