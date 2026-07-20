"""Smoke tests for Fibi v0.30 Memory Review Center."""

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


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        memory = core.memory_router.rag_memory.service.add_memory(
            "User is testing the v030 memory review center.",
            category="project",
            source="smoke",
            confidence=0.8,
            allow_duplicate=True,
        )
        sensitive_text = "password=<dummy-test-password>"
        secret = core.memory_router.rag_memory.service.add_memory(
            sensitive_text,
            category="fact",
            source="smoke",
            allow_duplicate=True,
        )

        assert "memory review center" in core.respond("/memories").display_text
        assert str(memory.id) in core.respond("/memory search v030").display_text
        assert "approved" in core.respond(f"/memory show {memory.id}").display_text
        assert "pinned" in core.respond(f"/memory pin {memory.id}").display_text
        assert "archived" in core.respond(f"/memory archive {memory.id}").display_text
        assert "memory health" in core.respond("/memory health").display_text
        assert "memory consent" in core.respond("/memory consent").display_text
        assert "secrets never stored" in core.respond("/memory safety").display_text
        assert "memory paused" in core.respond("/memory learning off").display_text
        assert "memory learning on" in core.respond("/memory learning on").display_text

        assert "edit staged" in core.respond(f"/memory edit {memory.id} User updated the v030 memory review note.").display_text
        assert "edited" in core.respond("memory edit confirm").display_text
        assert "delete staged" in core.respond(f"/memory delete {memory.id}").display_text
        assert "forgot one" in core.respond("memory delete confirm").display_text

        export_reply = core.respond("/memory export").display_text
        assert "memory export packed locally" in export_reply
        reports = list((root / "data" / "reports").glob("memory_export_*.json"))
        assert reports
        payload = reports[-1].read_text(encoding="utf-8")
        assert sensitive_text not in payload
        assert core.memory_review.get_memory(secret.id) is not None

        assert "Memory Review" in core.respond("/capabilities").display_text
        assert "/memory" in core.respond("/help search memory").display_text.lower()
        assert model.calls == 0

    assert release_zip_path().name == "Fibi_Chubi_v0.30.4_windows_beta.zip"
    result = subprocess.run(
        [sys.executable, "app.py", "--gui-smoke"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GUI_SMOKE_OK" in result.stdout
    print("Fibi v0.30 memory review smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
