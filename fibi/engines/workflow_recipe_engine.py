"""Guided workflow recipe engine for Fibi v0.28."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.engines.builtin_workflow_recipes import builtin_workflow_recipes
from fibi.engines.types import (
    WorkflowRecipe,
    WorkflowRecipeStep,
    WorkflowRun,
    WorkflowRunState,
    WorkflowStepResult,
)
from fibi.engines.workflow_safety_engine import WorkflowSafetyEngine
from fibi.paths import data_path

LOGGER = logging.getLogger(__name__)


class WorkflowRecipeEngine:
    """Manage local guided recipe runs.

    The engine only tracks and explains steps. Existing patch/check/browser
    confirmation systems remain responsible for all actions.
    """

    def __init__(
        self,
        state_path: Path | None = None,
        runs_path: Path | None = None,
        *,
        safety: WorkflowSafetyEngine | None = None,
    ) -> None:
        self.state_path = Path(state_path) if state_path else data_path("workflows/workflow_state.json")
        self.runs_path = Path(runs_path) if runs_path else data_path("workflows/workflow_runs.jsonl")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.runs_path.parent.mkdir(parents=True, exist_ok=True)
        self.safety = safety or WorkflowSafetyEngine()
        self._recipes = builtin_workflow_recipes()
        self.state = self._load()

    def recipes(self) -> list[WorkflowRecipe]:
        return [recipe for recipe in self._recipes if recipe.enabled]

    def get_recipe(self, name_or_id: str) -> WorkflowRecipe | None:
        needle = _normalize(name_or_id)
        for recipe in self.recipes():
            aliases = {
                _normalize(recipe.recipe_id),
                _normalize(recipe.name),
                _normalize(recipe.name.replace("/", " ")),
            }
            if needle in aliases:
                return recipe
        for recipe in self.recipes():
            if needle and (needle in _normalize(recipe.name) or needle in _normalize(recipe.recipe_id)):
                return recipe
        return None

    def recipe_summary(self, recipe: WorkflowRecipe) -> str:
        safety = self.safety.validate(recipe)
        first_steps = "; ".join(step.title for step in recipe.steps[:4])
        return (
            f"{recipe.name}: {recipe.description} "
            f"{len(recipe.steps)} steps. safety: {safety.safety_level}. "
            f"first crumbs: {first_steps}."
        )

    def start(
        self,
        name_or_id: str,
        *,
        linked_session_id: str = "",
        linked_project_id: str = "",
    ) -> WorkflowRun | None:
        recipe = self.get_recipe(name_or_id)
        if recipe is None:
            return None
        safety = self.safety.validate(recipe)
        if safety.blocked:
            LOGGER.warning("workflow_recipe_blocked", extra={"recipe_id": recipe.recipe_id, "reason": safety.reason})
            return None
        now = _now()
        run = WorkflowRun(
            run_id="WFR-" + uuid.uuid4().hex[:8],
            recipe_id=recipe.recipe_id,
            recipe_name=recipe.name,
            status="active",
            created_at=now,
            updated_at=now,
            steps=[WorkflowRecipeStep(**asdict(step)) for step in recipe.steps],
            linked_session_id=linked_session_id,
            linked_project_id=linked_project_id,
            safety_level=safety.safety_level,
        )
        self.state.runs.append(run)
        self.state.active_run_id = run.run_id
        self._save()
        LOGGER.info("workflow_started", extra={"run_id": run.run_id, "recipe_id": recipe.recipe_id})
        return run

    def active(self) -> WorkflowRun | None:
        if not self.state.active_run_id:
            return None
        return self.get_run(self.state.active_run_id)

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return next((run for run in self.state.runs if run.run_id == run_id), None)

    def current_step(self, run: WorkflowRun | None = None) -> WorkflowRecipeStep | None:
        run = run or self.active()
        if run is None or run.current_step_index >= len(run.steps):
            return None
        return run.steps[run.current_step_index]

    def continue_run(self) -> WorkflowStepResult:
        run = self.active()
        if run is None:
            return WorkflowStepResult(False, "no workflow ritual. use /workflow start <name>.", blocked=True)
        if run.status == "paused":
            return WorkflowStepResult(False, "workflow is napping. say /workflow resume.", blocked=True)
        step = self.current_step(run)
        if step is None:
            self.complete("Workflow completed.")
            return WorkflowStepResult(True, "workflow complete. tiny ritual done.", completed=True)
        step.status = "completed"
        if step.step_id not in run.completed_steps:
            run.completed_steps.append(step.step_id)
        run.current_step_index = min(run.current_step_index + 1, len(run.steps))
        message = self._step_message(step)
        run.safe_summaries.append(f"{step.title}: {self._safe_summary(step)}")
        run.updated_at = _now()
        if step.step_type == "done" or run.current_step_index >= len(run.steps):
            run.status = "completed"
            self.state.active_run_id = ""
            self._append_history(run)
            message = message + "\nworkflow complete. tiny ritual done."
        self._save()
        return WorkflowStepResult(
            True,
            message,
            step.step_id,
            step.step_type,
            completed=True,
            waiting_for_user=step.requires_confirmation or step.step_type in {"ask_user", "manual_step", "create_issue"},
        )

    def pause(self) -> WorkflowRun | None:
        run = self.active()
        if run is None:
            return None
        run.status = "paused"
        run.updated_at = _now()
        self._save()
        return run

    def resume(self) -> WorkflowRun | None:
        run = self.active()
        if run is None:
            return None
        if run.status == "paused":
            run.status = "active"
            run.updated_at = _now()
            self._save()
        return run

    def cancel(self) -> WorkflowRun | None:
        run = self.active()
        if run is None:
            return None
        run.status = "cancelled"
        run.updated_at = _now()
        self.state.active_run_id = ""
        self._save()
        self._append_history(run)
        return run

    def complete(self, summary: str = "") -> WorkflowRun | None:
        run = self.active()
        if run is None:
            return None
        run.status = "completed"
        run.updated_at = _now()
        if summary:
            run.safe_summaries.append(summary[:500])
        self.state.active_run_id = ""
        self._save()
        self._append_history(run)
        return run

    def history(self, limit: int = 5) -> list[WorkflowRun]:
        return self.state.runs[-max(1, limit):]

    def status_line(self) -> str:
        run = self.active()
        if run is None:
            return "workflow: none."
        step = self.current_step(run)
        title = step.title if step else "done"
        return f"workflow: {run.recipe_name} {len(run.completed_steps)}/{len(run.steps)}. next: {title}."

    def _step_message(self, step: WorkflowRecipeStep) -> str:
        command = f" use: {step.linked_command}." if step.linked_command else ""
        confirm = " waits for confirmation." if step.requires_confirmation else ""
        if step.step_type == "browser_open_confirmed":
            return f"browser crumb: {step.instruction}{command} no hidden browsing."
        if step.step_type == "summarize_pasted_page":
            return f"page crumb: {step.instruction}{command} only pasted text."
        if step.step_type == "apply_patch_confirmed":
            return f"patch crumb: {step.instruction}{command} no auto-apply."
        if step.step_type == "run_check_confirmed":
            return f"check crumb: {step.instruction}{command} no auto-run."
        if step.step_type == "build_release_confirmed":
            return f"release crumb: {step.instruction}{command} no auto-build."
        if step.step_type == "create_issue":
            return f"bug jar crumb: {step.instruction}{command}"
        if step.step_type == "export_support_bundle":
            return f"support crumb: {step.instruction}{command} safe bundle only."
        if step.step_type == "done":
            return "done crumb reached."
        return f"next crumb: {step.title}. {step.instruction}{command}{confirm}"

    @staticmethod
    def _safe_summary(step: WorkflowRecipeStep) -> str:
        return f"showed guidance for {step.step_type}; auto_run=false; command={step.linked_command or 'none'}"

    def _load(self) -> WorkflowRunState:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return WorkflowRunState()
        runs: list[WorkflowRun] = []
        for item in raw.get("runs", []) if isinstance(raw, dict) else []:
            try:
                steps = [WorkflowRecipeStep(**step) for step in item.get("steps", [])]
                runs.append(WorkflowRun(**{**item, "steps": steps}))
            except TypeError:
                continue
        return WorkflowRunState(str(raw.get("active_run_id", "")), runs)

    def _save(self) -> None:
        payload = {
            "active_run_id": self.state.active_run_id,
            "runs": [asdict(run) for run in self.state.runs],
        }
        self.state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _append_history(self, run: WorkflowRun) -> None:
        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())
