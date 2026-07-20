"""Smoke tests for Fibi v0.27 safe browser helper mode."""

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
        opened: list[str] = []
        core, model, _ = make_core(root / "core", opened, [])

        assert "browser session started" in core.respond("/browser start research example").display_text
        assert "browser doorway ready" in core.respond("/browser open https://example.com").display_text
        assert opened == []
        assert "opened example.com" in core.respond("browser confirm").display_text
        assert opened == ["https://example.com"]
        assert "saved link crumb" in core.respond("/browser note https://example.com useful public page").display_text
        core.respond("/context add <html><body><h1>Acme</h1><p>Repairs laptops.</p><script>x()</script></body></html>")
        assert "Acme" in core.respond("/browser summarize").display_text
        assert "only have the link" in _summarize_url_only(core)
        assert "locked" in core.respond("read saved password from browser").display_text
        assert "locked" in core.respond("auto click the buy button").display_text
        assert "browser helper on" in core.respond("/health gui").display_text
        assert "browser helper on" in core.respond("/debug summary").display_text
        assert model.calls == 0
        assert release_zip_path().name == "Fibi_Chubi_v0.30.0_windows_beta.zip"

    print("Fibi v0.27 browser helper smoke tests passed.")


def _summarize_url_only(core) -> str:
    core.respond("/context add https://example.com")
    return core.respond("/browser summarize").display_text


if __name__ == "__main__":
    run()


