"""Smoke tests for Fibi v0.18 safe patch apply mode."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.patch_backup_engine import PatchBackupEngine
from fibi.engines.patch_confirmation_engine import PatchConfirmationEngine
from fibi.engines.patch_engine import PatchEngine
from fibi.engines.patch_history_engine import PatchHistoryEngine
from fibi.engines.patch_safety_engine import PatchSafetyEngine
from fibi.engines.project_edit_planner import ProjectEditPlanner
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import EditSuggestionResult, ReplacementBlock
from tests.smoke_v012_actions import make_core


def wire_patch_test_paths(core, root: Path) -> None:
    core.project_workspace = ProjectWorkspaceEngine(root / "project_workspaces.json", context=core.context_engine, sanitizer=core.secret_sanitizer)
    core.project_edit_planner = ProjectEditPlanner(core.project_workspace, journal_path=root / "project_edit_journal.jsonl", last_path=root / "last_edit_suggestion.json")
    core.patch_safety = PatchSafetyEngine()
    core.patch_engine = PatchEngine(core.project_workspace, core.patch_safety, PatchBackupEngine(root / "patch_backups"))
    core.patch_confirmations = PatchConfirmationEngine(root / "pending_patch.json")
    core.patch_history = PatchHistoryEngine(root / "patch_history.jsonl")


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "demo_project"
        project.mkdir()
        target = project / "app.py"
        target.write_text("print('hello')\n", encoding="utf-8")
        secret = project / ".env"
        secret.write_text("TOKEN=secret", encoding="utf-8")
        auth_file = project / "auth.py"
        auth_file.write_text("ALLOW = False\n", encoding="utf-8")

        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root / "core", opened, launched)
        wire_patch_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        no_pending = core.respond("apply that")
        assert "no patch crumb" in no_pending.display_text
        assert target.read_text(encoding="utf-8") == "print('hello')\n"

        suggestion = core.respond('/edit file app.py replace "hello" with "hello tiny"')
        assert "tiny edit ready" in suggestion.display_text
        assert "apply patch confirm" in suggestion.display_text
        assert core.patch_confirmations.pending() is not None
        assert target.read_text(encoding="utf-8") == "print('hello')\n"
        assert model.calls == 0

        nudge = core.respond("apply that")
        assert "apply patch confirm" in nudge.display_text
        assert target.read_text(encoding="utf-8") == "print('hello')\n"

        applied = core.respond("apply patch confirm")
        assert "patch applied" in applied.display_text
        assert "hello tiny" in target.read_text(encoding="utf-8")
        assert core.patch_confirmations.pending() is None
        applied_patch_id = core._last_applied_patch.patch_id
        assert list((root / "patch_backups").glob("*/metadata.json"))
        history = core.patch_history.recent(limit=10)
        assert any(row.get("event") == "patch_created" for row in history)
        assert any(row.get("event") == "patch_applied" for row in history)
        assert core.memory_router.rag_memory.service.repository.get_by_source_id(f"patch:{applied_patch_id}") is not None

        rollback = core.respond("/patch rollback last")
        assert "rollback done" in rollback.display_text
        assert target.read_text(encoding="utf-8") == "print('hello')\n"
        assert any(row.get("event") == "patch_rolled_back" for row in core.patch_history.recent(limit=10))

        blocked = core.respond('/edit file .env replace "secret" with "public"')
        assert "secret" in blocked.display_text.lower() or "not touching" in blocked.display_text.lower()
        assert core.patch_confirmations.pending() is None
        assert secret.read_text(encoding="utf-8") == "TOKEN=secret"

        high = core.respond('/edit file auth.py replace "False" with "True"')
        assert "manual only" in high.display_text.lower()
        assert core.patch_confirmations.pending() is None
        assert auth_file.read_text(encoding="utf-8") == "ALLOW = False\n"

        pending_again = core.respond('/edit file app.py replace "hello" with "hello sleepy"')
        assert "tiny edit ready" in pending_again.display_text
        assert core.patch_confirmations.pending() is not None
        canceled = core.respond("/patch cancel")
        assert "canceled" in canceled.display_text
        assert core.patch_confirmations.pending() is None

        stale = core.respond('/edit file app.py replace "hello" with "hello stale"')
        assert "tiny edit ready" in stale.display_text
        target.write_text("print('changed by human')\n", encoding="utf-8")
        stale_apply = core.respond("apply patch confirm")
        assert "patch failed" in stale_apply.display_text
        assert "changed by human" in target.read_text(encoding="utf-8")
        core.patch_confirmations.cancel()
        target.write_text("print('hello')\n", encoding="utf-8")

        binary_risk = core.patch_safety.assess(["image.png"], "")
        assert not binary_risk.allowed and binary_risk.blocked
        delete_risk = core.patch_safety.assess(["app.py"], "--- a/app.py\n+++ /dev/null\n")
        assert not delete_risk.allowed and delete_risk.blocked
        outside = EditSuggestionResult(
            True,
            project_id=core.project_workspace.current().project_id,
            target_files=["../outside.txt"],
            summary="outside test",
            risk_level="low",
            replacement_blocks=[ReplacementBlock("../outside.txt", 1, 1, "x", "y")],
        )
        outside_plan, outside_risk = core.patch_engine.create_plan_from_suggestion(outside)
        assert outside_plan is None
        assert not outside_risk.allowed

        status = core.respond("/patch history")
        assert "patch footprints" in status.display_text
        safety = core.respond("/patch safety")
        assert "low/medium" in safety.display_text

    print("Fibi v0.18 safe patch apply smoke tests passed.")


if __name__ == "__main__":
    run()


