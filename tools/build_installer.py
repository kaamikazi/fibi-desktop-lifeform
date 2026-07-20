"""Build or prepare the Fibi Chubi Inno Setup installer."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "packaging" / "inno" / "FibiChubi.iss"
RELEASE_DIR = PROJECT_ROOT / "dist" / "Fibi Chubi"
INSTALLER_PATH = PROJECT_ROOT / "dist" / "installers" / "Fibi_Chubi_Setup_v0.30.2.exe"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.runtime_paths import reports_dir
from tools.build_windows import release_manifest_path, release_zip_path, write_release_manifest
from tools.make_checksums import generate_checksums
from tools.verify_release import verify_release


def find_iscc() -> Path | None:
    configured = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if configured:
        return Path(configured)
    candidates = [
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def write_report(status: str, details: dict[str, object]) -> Path:
    target = reports_dir() / "installer_build_report_v0.30.2.json"
    payload = {
        "status": status,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        **details,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"installer report: {target}")
    return target


def manual_instructions() -> str:
    return (
        "Inno Setup compiler not found. Install Inno Setup 6, then run:\n"
        f'  "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" "{SPEC_PATH}"\n'
        "or add ISCC.exe to PATH and run: python tools/build_installer.py"
    )


def build_installer(skip_build: bool = False) -> int:
    if not (RELEASE_DIR / "Fibi Chubi.exe").exists():
        print("missing PyInstaller build. run: python tools/build_windows.py --clean --zip")
        write_report("missing_release", {"release_dir": str(RELEASE_DIR)})
        return 1
    errors = verify_release(RELEASE_DIR)
    if errors:
        print("release verification failed before installer:")
        for error in errors:
            print(f"- {error}")
        write_report("release_verification_failed", {"errors": errors})
        return 1
    if skip_build:
        write_release_manifest(release_zip_path(), INSTALLER_PATH)
        generate_checksums()
        write_report("skipped", {"installer_path": str(INSTALLER_PATH), "inno_script": str(SPEC_PATH)})
        return 0
    iscc = find_iscc()
    if iscc is None:
        instructions = manual_instructions()
        print(instructions)
        write_release_manifest(release_zip_path(), INSTALLER_PATH)
        generate_checksums()
        write_report("inno_missing", {"instructions": instructions, "installer_path": str(INSTALLER_PATH)})
        return 0
    INSTALLER_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(iscc), str(SPEC_PATH)], cwd=PROJECT_ROOT, check=True)
    if not INSTALLER_PATH.exists():
        write_report("installer_missing", {"installer_path": str(INSTALLER_PATH)})
        return 1
    write_release_manifest(release_zip_path(), INSTALLER_PATH)
    generate_checksums()
    write_report("built", {"installer_path": str(INSTALLER_PATH), "size": INSTALLER_PATH.stat().st_size})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Fibi Chubi Inno Setup installer.")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    return build_installer(skip_build=args.skip_build)


if __name__ == "__main__":
    raise SystemExit(main())
