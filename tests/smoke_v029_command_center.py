"""Smoke tests for Fibi v0.29 Command Center."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        before = (
            core.privacy.settings.allow_cloud_model,
            core.privacy.settings.allow_clipboard_observation,
            core.voice_settings.settings.allow_voice_input,
            core.app_settings.settings.beta_mode,
        )

        assert "try:" in core.respond("/help").display_text
        assert "/browser" in core.respond("/help search browser").display_text
        assert "capabilities:" in core.respond("/capabilities").display_text
        assert "Browser Helper" in core.respond("/capability browser").display_text
        assert "permissions:" in core.respond("/permissions").display_text
        assert "safety map" in core.respond("/safety").display_text
        assert "i refuse" in core.respond("/refusals").display_text
        assert "confirmation needed" in core.respond("/confirmations").display_text
        assert "command shelves" in core.respond("show commands").display_text
        assert "i can chat" in core.respond("what can you do?").display_text
        assert "commands:" in core.respond("/health gui").display_text

        after = (
            core.privacy.settings.allow_cloud_model,
            core.privacy.settings.allow_clipboard_observation,
            core.voice_settings.settings.allow_voice_input,
            core.app_settings.settings.beta_mode,
        )
        assert before == after
        assert model.calls == 0

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["FIBI_DATA_DIR"] = str(root / "gui-data")
        gui = subprocess.run(
            [sys.executable, "app.py", "--gui-smoke"],
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert "GUI_SMOKE_OK" in gui.stdout or "GUI_SMOKE_SKIPPED_OR_FAILED" in gui.stdout

        assert release_zip_path().name == "Fibi_Chubi_v0.30.2_windows_beta.zip"

    print("Fibi v0.29 command center smoke tests passed.")


if __name__ == "__main__":
    run()
