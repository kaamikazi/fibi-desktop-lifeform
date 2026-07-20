"""Smoke tests for Fibi v0.24 beta release hardening."""

from __future__ import annotations

import os
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
        core, _, _ = make_core(root / "core", [], [])

        assert "Fibi Chubi v0.30.3" in core.respond("/version").display_text
        assert "cloud off" in core.respond("/first run status").display_text
        assert "beta mode" in core.respond("/beta status").display_text
        assert "beta mode on" in core.respond("/beta on").display_text
        assert "installer later" in core.respond("/limitations").display_text
        assert "self test survived" in core.respond("/self test").display_text
        assert "packed the safe crumbs" in core.respond("/support bundle").display_text
        assert (Path(os.environ["FIBI_DATA_DIR"]) / "reports").exists()
        assert release_zip_path().name == "Fibi_Chubi_v0.30.3_windows_beta.zip"

    print("Fibi v0.24 beta release smoke tests passed.")


if __name__ == "__main__":
    run()


