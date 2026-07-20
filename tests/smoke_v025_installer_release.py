"""Smoke tests for Fibi v0.25 installer and release flow."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke_v012_actions import make_core
from tools.build_windows import release_manifest_path, release_zip_path
from tools.make_checksums import CHECKSUM_PATH


def run() -> None:
    assert (PROJECT_ROOT / "packaging" / "inno" / "FibiChubi.iss").exists()
    assert release_zip_path().name == "Fibi_Chubi_v0.30.2_windows_beta.zip"
    assert release_manifest_path().name == "release_manifest_v0.30.2.json"
    assert CHECKSUM_PATH.name == "checksums_v0.30.2.txt"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        core, _, _ = make_core(root / "core", opened, [])
        assert "install status" in core.respond("/install status").display_text
        assert "data nest" in core.respond("/data folder").display_text
        assert "folder opened" in core.respond("/open data folder").display_text
        assert "reset:" in core.respond("/reset instructions").display_text
        assert "packed the safe crumbs" in core.respond("/support bundle").display_text

    print("Fibi v0.25 installer release smoke tests passed.")


if __name__ == "__main__":
    run()


