"""Smoke tests for Fibi v0.28 workflow recipes."""

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

        assert "Debug Failed Project" in core.respond("/recipes").display_text
        assert "workflow safety on" in core.respond("/workflow safety").display_text
        assert "Safe Release Build" in core.respond("guide me through release").display_text

        started = core.respond("/workflow start Safe Release Build").display_text
        assert "recipe started" in started
        assert core.work_sessions.active() is not None
        assert "Safe Release Build" in core.respond("/workflow current").display_text

        build_step_seen = False
        for _ in range(5):
            reply = core.respond("/workflow next").display_text
            if "no auto-build" in reply:
                build_step_seen = True
        assert build_step_seen
        assert opened == []
        assert model.calls == 0

        assert "workflow curled up" in core.respond("/workflow pause").display_text
        assert "workflow awake-ish" in core.respond("/workflow resume").display_text
        assert "workflow exported" in core.respond("/workflow export last").display_text
        assert (root / "data" / "reports").exists()

        core.respond("/workflow cancel")
        core.respond("/workflow start Website Review / Outreach Research")
        browser_step = core.respond("/workflow next").display_text
        assert "no hidden browsing" in browser_step
        assert opened == []

        core.respond("/workflow cancel")
        core.respond("/workflow start Bug Report Support Bundle")
        bug_step = core.respond("/workflow next").display_text
        assert "/issue new" in bug_step
        assert "bug jar" in bug_step

        assert "workflow:" in core.respond("/health gui").display_text
        assert release_zip_path().name == "Fibi_Chubi_v0.30.0_windows_beta.zip"

    print("Fibi v0.28 workflow recipe smoke tests passed.")


if __name__ == "__main__":
    run()


