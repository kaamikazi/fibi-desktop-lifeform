"""Build a local Windows release candidate for Fibi Chubi."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = DIST_DIR / "Fibi Chubi"
SPEC_PATH = PROJECT_ROOT / "packaging" / "pyinstaller_fibi.spec"
SMOKE_TESTS = [
    "tests/smoke_v022_gui_packaging.py",
    "tests/smoke_v023_packaged_paths.py",
    "tests/smoke_v024_beta_release.py",
    "tests/smoke_v025_installer_release.py",
    "tests/smoke_v026_beta_feedback.py",
    "tests/smoke_v027_browser_helper.py",
    "tests/smoke_v028_workflow_recipes.py",
    "tests/smoke_v029_command_center.py",
    "tests/smoke_v030_memory_review.py",
    "tests/smoke_v0301_gemini_provider.py",
    "tests/smoke_v0302_demo_ui.py",
    "tests/smoke_v0303_routing_and_settings.py",
    "tests/smoke_v0304_provider_resilience.py",
]


def remove_python_caches(root: Path) -> None:
    """Remove Python cache folders so they are never bundled as data files."""
    if not root.exists():
        return
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)


def run_command(args: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(args))
    subprocess.run(args, cwd=PROJECT_ROOT, env=env, check=True)


def clean() -> None:
    for path in (BUILD_DIR, RELEASE_DIR):
        if path.exists():
            shutil.rmtree(path)


def ensure_pyinstaller() -> None:
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("PyInstaller is not installed. Install with: pip install pyinstaller")


def run_tests(skip_tests: bool) -> None:
    run_command([sys.executable, "-m", "compileall", "-q", "app.py", "fibi", "tests", "tools"])
    if skip_tests:
        return
    for smoke in SMOKE_TESTS:
        run_command([sys.executable, smoke])


def build() -> None:
    ensure_pyinstaller()
    remove_python_caches(PROJECT_ROOT)
    env = os.environ.copy()
    env["FIBI_BUILD_MODE"] = "windows-beta"
    env["FIBI_BUILD_DATE"] = datetime.now().astimezone().isoformat(timespec="seconds")
    run_command([sys.executable, "-m", "PyInstaller", str(SPEC_PATH), "--noconfirm"], env=env)
    remove_python_caches(RELEASE_DIR)


def verify() -> None:
    remove_python_caches(RELEASE_DIR)
    run_command([sys.executable, "tools/verify_release.py", "--release-dir", str(RELEASE_DIR)])


def zip_release() -> Path:
    remove_python_caches(RELEASE_DIR)
    target = release_zip_path()
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in RELEASE_DIR.rglob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(DIST_DIR))
    print(f"zip release: {target}")
    write_release_manifest(target)
    return target


def release_zip_path() -> Path:
    return DIST_DIR / "Fibi_Chubi_v0.30.4_windows_beta.zip"


def release_manifest_path() -> Path:
    return DIST_DIR / "release_manifest_v0.30.4.json"


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_release_manifest(zip_path: Path | None = None, installer_path: Path | None = None) -> Path:
    import json

    exe = RELEASE_DIR / "Fibi Chubi.exe"
    zip_path = zip_path or release_zip_path()
    installer_path = installer_path or (DIST_DIR / "installers" / "Fibi_Chubi_Setup_v0.30.4.exe")
    docs = [
        "README.md",
        "docs/RELEASE_NOTES_V024.md",
        "docs/RESET_AND_UNINSTALL.md",
        "docs/BETA_TESTER_GUIDE_V025.md",
        "docs/BETA_FEEDBACK_FLOW_V026.md",
        "docs/ISSUE_TRACKER_V026.md",
        "docs/UPDATE_PREP_V026.md",
        "docs/BROWSER_HELPER_V027.md",
        "docs/WORKFLOW_RECIPES_V028.md",
        "docs/BEGINNER_GUIDE_V029.md",
        "docs/CAPABILITIES_V029.md",
        "docs/COMMANDS_V029.md",
        "docs/SAFETY_MODEL_V029.md",
        "docs/MEMORY_REVIEW_CENTER_V030.md",
        "docs/MEMORY_PRIVACY_V030.md",
        "docs/GEMINI_PROVIDER_V0301.md",
        "docs/CLOUD_CONTEXT_PRIVACY_V0301.md",
        "docs/DEMO_UI_POLISH_V0302.md",
        "docs/CONVERSATION_GEMINI_HOTFIX_V0303.md",
        "packaging/installer_notes.md",
    ]
    manifest = {
        "app_version": "0.30.4",
        "build_date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "zip_path": str(zip_path),
        "installer_path": str(installer_path) if installer_path.exists() else "",
        "exe_size": exe.stat().st_size if exe.exists() else 0,
        "zip_size": zip_path.stat().st_size if zip_path.exists() else 0,
        "installer_size": installer_path.stat().st_size if installer_path.exists() else 0,
        "included_docs": docs,
        "excluded_sensitive_folders": ["data", "logs", "reports", "exports", "voice_cache", "tts_temp", "voice_models"],
        "test_summary": "compileall, smoke_v022 through smoke_v0303, verify_release",
        "checksums": {
            "zip_sha256": _sha256(zip_path) if zip_path.exists() else "",
            "installer_sha256": _sha256(installer_path) if installer_path.exists() else "",
        },
    }
    target = release_manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"release manifest: {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Fibi Chubi for Windows.")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--zip", action="store_true")
    args = parser.parse_args()

    try:
        if args.clean:
            clean()
        run_tests(args.skip_tests)
        build()
        verify()
        if args.zip:
            zip_release()
    except RuntimeError as exc:
        print(str(exc))
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"build command failed with exit {exc.returncode}")
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
