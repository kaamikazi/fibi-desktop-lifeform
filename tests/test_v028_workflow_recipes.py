"""Tests for Fibi v0.28 workflow recipes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fibi.build_info import APP_VERSION
from fibi.engines.builtin_workflow_recipes import builtin_workflow_recipes
from fibi.engines.workflow_export_engine import WorkflowExportEngine
from fibi.engines.workflow_recipe_engine import WorkflowRecipeEngine
from fibi.engines.workflow_safety_engine import WorkflowSafetyEngine
from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path


def test_builtin_recipes_validate_safely() -> None:
    safety = WorkflowSafetyEngine()
    recipes = builtin_workflow_recipes()
    assert {recipe.recipe_id for recipe in recipes} >= {
        "debug_failed_project",
        "safe_release_build",
        "beta_qa_pass",
        "website_review_outreach",
        "bug_report_support_bundle",
        "daily_fibi_startup_check",
    }
    for recipe in recipes:
        result = safety.validate(recipe)
        assert result.allowed
        assert not result.blocked
        assert all(not step.allowed_to_auto_run for step in recipe.steps)


def test_workflow_engine_start_continue_pause_resume_cancel() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        engine = WorkflowRecipeEngine(
            state_path=root / "workflow_state.json",
            runs_path=root / "workflow_runs.jsonl",
        )
        run = engine.start("Daily Fibi Startup Check")
        assert run is not None
        assert run.recipe_name == "Daily Fibi Startup Check"
        assert engine.active() is not None

        assert engine.pause() is not None
        paused = engine.continue_run()
        assert not paused.ok and "napping" in paused.message
        assert engine.resume() is not None

        first = engine.continue_run()
        assert first.ok
        assert "startup" in first.message.lower()
        assert engine.active() is not None

        assert engine.cancel() is not None
        assert engine.active() is None
        assert (root / "workflow_runs.jsonl").exists()


def test_workflow_export_excludes_secrets() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        engine = WorkflowRecipeEngine(
            state_path=root / "workflow_state.json",
            runs_path=root / "workflow_runs.jsonl",
        )
        run = engine.start("Daily Fibi Startup Check")
        assert run is not None
        run.safe_summaries.append("token=abc123 should not leak")
        exporter = WorkflowExportEngine(root / "reports")
        exported = exporter.export(run)
        markdown = Path(exported.markdown_path).read_text(encoding="utf-8")
        payload = json.loads(Path(exported.json_path).read_text(encoding="utf-8"))
        assert "[redacted]" in markdown
        assert "raw logs" in payload["excluded"]
        assert "memory database" in payload["excluded"]


def test_core_workflow_commands_and_safety_routes() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        core, model, _ = make_core(root / "core", opened, [])

        listed = core.respond("/workflow list").display_text
        assert "Debug Failed Project" in listed
        assert "Safe Release Build" in listed

        natural = core.respond("guide me through release").display_text
        assert "Safe Release Build" in natural
        assert "say: /workflow start" in natural

        started = core.respond("/workflow start Safe Release Build").display_text
        assert "recipe started" in started
        assert core.workflow_recipes.active() is not None
        assert core.work_sessions.active() is not None

        step = core.respond("/workflow next").display_text
        assert "self-test" in step.lower()
        build_step_seen = False
        for _ in range(4):
            text = core.respond("/workflow next").display_text
            if "no auto-build" in text:
                build_step_seen = True
        assert build_step_seen
        assert model.calls == 0


def test_browser_and_bug_report_recipes_do_not_autorun() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        core, model, _ = make_core(root / "core", opened, [])

        core.respond("/workflow start Website Review / Outreach Research")
        reply = core.respond("/workflow next").display_text
        assert "no hidden browsing" in reply
        assert opened == []

        core.respond("/workflow cancel")
        core.respond("/workflow start Bug Report Support Bundle")
        bug_step = core.respond("/workflow next").display_text
        assert "/issue new" in bug_step
        assert "bug jar" in bug_step
        assert model.calls == 0


def test_workflow_completion_creates_short_rag_memory() -> None:
    class FakeRag:
        def __init__(self) -> None:
            self.events: list[str] = []

        def remember_event(self, content: str, **kwargs):
            self.events.append(content)

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])
        fake = FakeRag()
        core.memory_router.rag_memory = fake

        core.respond("/workflow start Daily Fibi Startup Check")
        for _ in range(6):
            core.respond("/workflow next")

        assert fake.events
        assert fake.events[-1] == f"Completed Daily Fibi Startup Check workflow for Fibi v{APP_VERSION}."
        assert "raw" not in fake.events[-1].lower()


def test_packaged_v028_paths() -> None:
    assert release_zip_path().name == "Fibi_Chubi_v0.30.1_windows_beta.zip"


