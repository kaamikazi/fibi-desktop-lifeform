"""Verify a local Fibi Windows release folder."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_DIR = PROJECT_ROOT / "dist" / "Fibi Chubi"
FORBIDDEN_SUFFIXES = {".env", ".pth", ".index"}
FORBIDDEN_NAMES = {
    "fibi_memory.db",
    "fibi.log",
    "startup_diagnostics.json",
    "shutdown_marker.json",
}
FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "tests",
}
FORBIDDEN_TOP_LEVEL_DIRS = {
    "data",
    "logs",
    "reports",
    "exports",
    "voice_cache",
    "tts_temp",
    "voice_models",
}


def forbidden_release_files(release_dir: Path) -> list[Path]:
    found: list[Path] = []
    if not release_dir.exists():
        return found
    for path in release_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(release_dir)
        lowered_parts = [part.lower() for part in relative.parts]
        parts = set(lowered_parts)
        if lowered_parts and lowered_parts[0] in FORBIDDEN_TOP_LEVEL_DIRS:
            found.append(relative)
            continue
        if parts & FORBIDDEN_PARTS:
            found.append(relative)
            continue
        if path.name.lower() in FORBIDDEN_NAMES:
            found.append(relative)
            continue
        if path.name.lower().startswith(".env"):
            found.append(relative)
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            found.append(relative)
    return found


def verify_release(release_dir: Path, run_gui_smoke: bool = False) -> list[str]:
    errors: list[str] = []
    exe = release_dir / "Fibi Chubi.exe"
    if not exe.exists():
        errors.append(f"missing executable: {exe}")
    if not (release_dir / "_internal" / "fibi" / "ui" / "assets").exists() and not (release_dir / "fibi" / "ui" / "assets").exists():
        errors.append("missing bundled UI assets")
    if not (release_dir / "_internal" / "config" / "default_settings.json").exists() and not (release_dir / "config" / "default_settings.json").exists():
        errors.append("missing default settings template")
    if not (release_dir / "_internal" / "fibi" / "version.py").exists() and not (release_dir / "fibi" / "version.py").exists():
        errors.append("missing version metadata")

    forbidden = forbidden_release_files(release_dir)
    if forbidden:
        errors.append("forbidden files bundled: " + ", ".join(str(item) for item in forbidden[:10]))

    if run_gui_smoke and exe.exists():
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run([str(exe), "--gui-smoke"], cwd=release_dir, env=env, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            errors.append(f"gui smoke failed: exit {result.returncode} {result.stdout[-500:]} {result.stderr[-500:]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Fibi Windows release folder.")
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    parser.add_argument("--gui-smoke", action="store_true")
    args = parser.parse_args()

    errors = verify_release(args.release_dir, run_gui_smoke=args.gui_smoke)
    if errors:
        print("release verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"release verification passed: {args.release_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
