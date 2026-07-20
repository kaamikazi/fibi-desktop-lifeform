"""Smoke tests for Fibi v0.21 guided work sessions."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.patch_confirmation_engine import PatchConfirmationEngine
from fibi.engines.project_check_confirmation_engine import ProjectCheckConfirmationEngine
from fibi.engines.work_planner_engine import WorkPlannerEngine
from fibi.engines.work_session_engine import WorkSessionEngine
from fibi.engines.work_step_runner import WorkStepRunner
from tests.smoke_v012_actions import make_core


def wire_session_test_paths(core, root: Path) -> None:
    core.work_sessions = WorkSessionEngine(root / "work_sessions.json")
    core.work_planner = WorkPlannerEngine()
    core.patch_confirmations = PatchConfirmationEngine(root / "pending_patch.json")
    core.check_confirmations = ProjectCheckConfirmationEngine(root / "pending_project_check.json")
    core.work_step_runner = WorkStepRunner(
        core._session_project_summary,
        core._session_check_analysis,
        core._session_suggest_fix,
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "demo_project"
        project.mkdir()
        (project / "app.py").write_text("print('ok')\n", encoding="utf-8")

        core, model, _ = make_core(root / "core", [], [])
        wire_session_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        started = core.respond("/session start help me fix this project")
        assert "tiny plan made" in started.display_text
        assert "say: continue" in started.display_text
        assert core.work_sessions.active() is not None
        assert model.calls == 0

        persisted = WorkSessionEngine(root / "work_sessions.json")
        assert persisted.active() is not None

        current = core.respond("/session current")
        assert "session:" in current.display_text
        first = core.respond("continue")
        assert "project crumb" in first.display_text
        assert len(core.work_sessions.active().completed_steps) == 1

        blocked = core.respond("/session continue")
        assert "failed check" in blocked.display_text or "next crumb" in blocked.display_text
        assert core.check_confirmations.pending() is None
        assert core.patch_confirmations.pending() is None

        paused = core.respond("/session pause")
        assert "paused" in paused.display_text
        resumed = core.respond("/session resume")
        assert "awake" in resumed.display_text
        canceled = core.respond("/session cancel")
        assert "session sleeping" in canceled.display_text
        assert core.work_sessions.active() is None

        ui_plan = core.respond("/session start make this UI cleaner")
        assert "tiny plan made" in ui_plan.display_text
        steps = core.work_sessions.active().steps
        assert any(step.step_type == "read_file" and step.requires_confirmation for step in steps)
        assert any(step.step_type == "apply_patch" and step.requires_confirmation for step in steps)
        assert any(step.step_type == "run_check" and step.requires_confirmation for step in steps)
        assert all("install" not in step.description.lower() for step in steps)
        core.respond("/session cancel")

        review = core.respond("/session start review this project")
        assert "tiny plan made" in review.display_text
        for _ in range(5):
            reply = core.respond("/session continue")
            if "done-ish" in reply.display_text:
                break
        rows = core.work_sessions.summaries(limit=3)
        completed = [row for row in rows if row.status == "completed"]
        assert completed
        session_id = completed[-1].session_id
        assert core.memory_router.rag_memory.service.repository.get_by_source_id(f"session:{session_id}") is not None

        history = core.respond("/session history")
        assert "session footprints" in history.display_text
        cleared = core.respond("/session clear completed")
        assert "cleared" in cleared.display_text

    print("Fibi v0.21 guided work session smoke tests passed.")


if __name__ == "__main__":
    run()


