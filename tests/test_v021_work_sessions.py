"""Unit coverage for Fibi v0.21 guided work sessions."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import WorkSessionStep
from fibi.engines.work_planner_engine import WorkPlannerEngine
from fibi.engines.work_session_engine import WorkSessionEngine
from fibi.engines.work_step_runner import WorkStepRunner
from tests.smoke_v012_actions import make_core
from tests.smoke_v021_work_sessions import wire_session_test_paths


def _workspace(root: Path):
    project = root / "app"
    project.mkdir()
    (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
    engine = ProjectWorkspaceEngine(root / "workspaces.json")
    assert engine.add_workspace(project).ok
    return engine.current()


def test_work_session_create_persist_resume_cancel() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = _workspace(root)
        planner = WorkPlannerEngine()
        plan = planner.plan("review this project", project)
        engine = WorkSessionEngine(root / "work_sessions.json")
        session = engine.create_session(project.project_id, "review this project", plan)
        assert engine.active().session_id == session.session_id

        loaded = WorkSessionEngine(root / "work_sessions.json")
        assert loaded.active().session_id == session.session_id
        assert loaded.pause().status == "paused"
        assert loaded.resume().status == "active"
        assert loaded.cancel().status == "cancelled"
        assert loaded.active() is None


def test_planner_safe_shapes_for_failed_build_ui_and_ambiguous_goals() -> None:
    with tempfile.TemporaryDirectory() as temp:
        project = _workspace(Path(temp))
        planner = WorkPlannerEngine()

        failed = planner.plan("help me fix the failed build", project)
        failed_types = [step.step_type for step in failed.steps]
        assert failed_types[:3] == ["inspect_project", "analyze_check_failure", "suggest_fix"]
        assert any(step.step_type == "apply_patch" and step.requires_confirmation for step in failed.steps)
        assert any(step.step_type == "run_check" and step.requires_confirmation for step in failed.steps)

        ui = planner.plan("make this UI cleaner", project)
        assert any(step.step_type == "read_file" and step.requires_confirmation for step in ui.steps)
        assert any(step.step_type == "suggest_edit" for step in ui.steps)

        risky = planner.plan("install package and git deploy this", project)
        all_text = " ".join(step.title + " " + step.description for step in risky.steps).lower()
        assert "install package" not in all_text
        assert "git deploy" not in all_text
        assert risky.notes

        ambiguous = planner.plan("make a plan", project)
        assert any(step.step_type == "ask_user" for step in ambiguous.steps)


def test_step_runner_restricts_patches_checks_and_file_reads() -> None:
    runner = WorkStepRunner(lambda: "project summary", lambda: "check analysis", lambda: "fix suggestion")
    safe = runner.run(WorkSessionStep("1", "inspect", "summary", "inspect_project", allowed_to_run_automatically=True))
    assert safe.allowed
    assert "project summary" in safe.message

    for step_type in ("apply_patch", "run_check", "read_file", "suggest_edit", "suggest_fix"):
        decision = runner.run(WorkSessionStep("x", step_type, "restricted", step_type, requires_confirmation=True))
        assert not decision.allowed
        assert decision.waiting_for_user
        assert "need permission" in decision.message


def test_core_session_flow_does_not_auto_apply_or_run_checks() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = root / "app"
        project.mkdir()
        (project / "app.py").write_text("print('ok')\n", encoding="utf-8")
        core, model, _ = make_core(root / "core", [], [])
        wire_session_test_paths(core, root)
        assert core.project_workspace.add_workspace(project).ok

        start = core.respond("/session start help me fix this")
        assert "tiny plan made" in start.display_text
        assert model.calls == 0
        core.respond("continue")
        core.respond("continue")
        assert core.check_confirmations.pending() is None
        assert core.patch_confirmations.pending() is None
        assert project.joinpath("app.py").read_text(encoding="utf-8") == "print('ok')\n"


