"""Load optional local environment configuration without exposing secrets."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - exercised by fallback parser tests
    load_dotenv = None


SAFE_ENV_NAMES = {
    "GEMINI_API_KEY",
    "FIBI_PROVIDER",
    "FIBI_GEMINI_MODEL",
    "FIBI_GEMINI_TIMEOUT_SECONDS",
    "FIBI_GEMINI_FALLBACK_TO_OLLAMA",
    "FIBI_GEMINI_STREAMING",
    "FIBI_CLOUD_CONTEXT_PREVIEW",
}
PLACEHOLDER_KEYS = {"", "YOUR_GEMINI_API_KEY_HERE"}


@dataclass(frozen=True, slots=True)
class EnvironmentStatus:
    """Secret-free environment loading diagnostics."""

    loaded: bool
    source: str
    checked_project_env: bool
    project_env_exists: bool
    gemini_key_configured: bool
    dotenv_available: bool


def _is_configured_key(value: str | None) -> bool:
    return (value or "").strip().upper() not in PLACEHOLDER_KEYS


def _fallback_load(path: Path) -> bool:
    """Conservatively parse known provider settings when python-dotenv is absent."""

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return False
    loaded = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name not in SAFE_ENV_NAMES or name in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[name] = value
        loaded = True
    return loaded


def load_environment(
    project_root: Path,
    *,
    packaged: bool | None = None,
    explicit_path: Path | None = None,
) -> EnvironmentStatus:
    """Load provider settings with process environment taking precedence.

    Development checks ``<project root>/.env``. Packaged builds only load an
    explicitly supplied ``FIBI_ENV_FILE`` path and otherwise rely on external
    process environment variables. Values are never returned or logged.
    """

    frozen = bool(getattr(sys, "frozen", False)) if packaged is None else packaged
    preconfigured = _is_configured_key(os.getenv("GEMINI_API_KEY"))
    configured_path = explicit_path
    if configured_path is None:
        raw_explicit = os.getenv("FIBI_ENV_FILE", "").strip()
        configured_path = Path(raw_explicit).expanduser() if raw_explicit else None

    project_env = Path(project_root).resolve() / ".env"
    checked_project = not frozen and configured_path is None
    candidate = configured_path if configured_path is not None else (project_env if not frozen else None)
    source = "process_environment" if preconfigured else "none"
    loaded = preconfigured

    if candidate is not None and candidate.is_file():
        if load_dotenv is not None:
            load_dotenv(dotenv_path=candidate, override=False)
            loaded = True
        else:
            loaded = _fallback_load(candidate) or loaded
        source = "explicit_runtime_file" if configured_path is not None else "project_root_env"

    return EnvironmentStatus(
        loaded=loaded,
        source=source,
        checked_project_env=checked_project,
        project_env_exists=project_env.is_file() if checked_project else False,
        gemini_key_configured=_is_configured_key(os.getenv("GEMINI_API_KEY")),
        dotenv_available=load_dotenv is not None,
    )
