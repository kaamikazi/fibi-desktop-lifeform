"""Smoke tests for Fibi v0.23 packaged runtime paths."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.runtime_paths import runtime_info, user_data_dir
from tools.verify_release import forbidden_release_files
from tests.smoke_v012_actions import make_core


def run() -> None:
    original_frozen = getattr(sys, "frozen", None)
    original_meipass = getattr(sys, "_MEIPASS", None)
    original_executable = sys.executable
    original_appdata = os.environ.get("APPDATA")
    original_data = os.environ.get("FIBI_DATA_DIR")

    try:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe_dir = root / "release" / "Fibi Chubi"
            bundle = exe_dir / "_internal"
            (bundle / "config").mkdir(parents=True)
            (bundle / "config" / "default_settings.json").write_text(
                '{"app_settings": {"minimize_to_tray": true, "allow_project_checks": true}}',
                encoding="utf-8",
            )
            (bundle / "fibi" / "ui" / "assets").mkdir(parents=True)
            (exe_dir / "Fibi Chubi.exe").write_text("stub", encoding="utf-8")

            sys.frozen = True
            sys._MEIPASS = str(bundle)
            sys.executable = str(exe_dir / "Fibi Chubi.exe")
            os.environ.pop("FIBI_DATA_DIR", None)
            os.environ["APPDATA"] = str(root / "AppData" / "Roaming")

            appdata_dir = user_data_dir()
            assert appdata_dir == root / "AppData" / "Roaming" / "Fibi Chubi"
            assert (appdata_dir / "default_settings.json").exists()
            assert (appdata_dir / "fibi_settings.json").exists()

            (exe_dir / "portable_mode.txt").write_text("portable", encoding="utf-8")
            info = runtime_info()
            assert info.portable
            assert info.user_data_dir == exe_dir / "data"

            release = root / "bad_release"
            (release / "data").mkdir(parents=True)
            (release / "data" / "fibi_memory.db").write_text("private", encoding="utf-8")
            assert forbidden_release_files(release)

        with tempfile.TemporaryDirectory() as temp:
            os.environ["FIBI_DATA_DIR"] = str(Path(temp) / "data")
            core, _, _ = make_core(Path(temp) / "core", [], [])
            assert "Fibi Chubi v0.30.1" in core.respond("/version detailed").display_text
    finally:
        if original_frozen is None:
            if hasattr(sys, "frozen"):
                delattr(sys, "frozen")
        else:
            sys.frozen = original_frozen
        if original_meipass is None:
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_meipass
        sys.executable = original_executable
        if original_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = original_appdata
        if original_data is None:
            os.environ.pop("FIBI_DATA_DIR", None)
        else:
            os.environ["FIBI_DATA_DIR"] = original_data

    print("Fibi v0.23 packaged path smoke tests passed.")


if __name__ == "__main__":
    run()


