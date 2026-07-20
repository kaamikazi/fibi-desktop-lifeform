"""Runtime filesystem paths for development and packaged Fibi builds.

Packaged desktop apps should not write beside their bundled executable payload.
This module gives every engine a stable place to ask for writable folders while
keeping the old development default of ``./data``.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "Fibi Chubi"
PORTABLE_MARKER = "portable_mode.txt"


@dataclass(frozen=True, slots=True)
class RuntimePathInfo:
    packaged: bool
    portable: bool
    app_root: Path
    executable_dir: Path
    user_data_dir: Path


def project_root() -> Path:
    """Return the source project root in dev mode."""

    return Path(__file__).resolve().parents[1]


def is_packaged() -> bool:
    """Return True when running from a PyInstaller executable."""

    return bool(getattr(sys, "frozen", False))


def executable_dir() -> Path:
    """Return the executable folder in packaged mode, otherwise project root."""

    if is_packaged():
        return Path(sys.executable).resolve().parent
    return project_root()


def app_root() -> Path:
    """Return the bundled app root used for read-only resources."""

    if is_packaged():
        return Path(getattr(sys, "_MEIPASS", executable_dir())).resolve()
    return project_root()


def portable_marker_path() -> Path:
    return executable_dir() / PORTABLE_MARKER


def is_portable_mode() -> bool:
    """Portable mode is enabled by placing ``portable_mode.txt`` beside the exe."""

    return is_packaged() and portable_marker_path().exists()


def user_data_dir() -> Path:
    """Return Fibi's writable user-data directory and create it if needed."""

    configured = os.getenv("FIBI_DATA_DIR", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            base = executable_dir() if is_packaged() else project_root()
            path = base / path
    elif is_portable_mode():
        path = executable_dir() / "data"
    elif is_packaged():
        appdata = os.getenv("APPDATA", "").strip()
        path = (Path(appdata) if appdata else Path.home() / "AppData" / "Roaming") / APP_DIR_NAME
    else:
        path = project_root() / "data"

    path.mkdir(parents=True, exist_ok=True)
    ensure_default_settings(path)
    return path


def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir() -> Path:
    path = user_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir() -> Path:
    path = user_data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def voice_models_dir() -> Path:
    path = user_data_dir() / "voice_models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_assets_dir() -> Path:
    """Return the preferred bundled mascot assets directory."""

    root = app_root()
    candidates = [
        root / "fibi" / "ui" / "assets",
        root / "_internal" / "fibi" / "ui" / "assets",
        root / "assets",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def bundled_config_dir() -> Path:
    return app_root() / "config"


def default_settings_template_path() -> Path:
    return bundled_config_dir() / "default_settings.json"


def ensure_default_settings(target_data_dir: Path | None = None) -> None:
    """Copy release defaults into user data on first run.

    The template itself is copied for visibility. The app settings subset is
    also written to ``fibi_settings.json`` if that file does not exist yet.
    """

    data = target_data_dir or user_data_dir()
    template = default_settings_template_path()
    if not template.exists():
        return

    copied_template = data / "default_settings.json"
    if not copied_template.exists():
        shutil.copyfile(template, copied_template)

    app_settings = data / "fibi_settings.json"
    if app_settings.exists():
        return

    try:
        import json

        raw = json.loads(template.read_text(encoding="utf-8"))
        settings = raw.get("app_settings", raw) if isinstance(raw, dict) else {}
        if isinstance(settings, dict):
            build_mode = os.getenv("FIBI_BUILD_MODE", "").lower()
            if not is_packaged() and "beta" not in build_mode and "rc" not in build_mode:
                settings["beta_mode"] = False
            app_settings.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        return


def runtime_info() -> RuntimePathInfo:
    return RuntimePathInfo(
        packaged=is_packaged(),
        portable=is_portable_mode(),
        app_root=app_root(),
        executable_dir=executable_dir(),
        user_data_dir=user_data_dir(),
    )
