"""Safety validation for guided workflow recipes."""

from __future__ import annotations

from fibi.engines.types import WorkflowRecipe, WorkflowRecipeSafetyResult


ALLOWED_STEP_TYPES = {
    "ask_user",
    "inspect_project",
    "read_safe_file",
    "suggest_patch",
    "apply_patch_confirmed",
    "run_check_confirmed",
    "analyze_check",
    "browser_open_confirmed",
    "summarize_pasted_page",
    "create_issue",
    "export_support_bundle",
    "build_release_confirmed",
    "manual_step",
    "done",
}

RISKY_STEP_TYPES = {
    "read_safe_file",
    "suggest_patch",
    "apply_patch_confirmed",
    "run_check_confirmed",
    "browser_open_confirmed",
    "export_support_bundle",
    "build_release_confirmed",
}

BLOCKED_COMMAND_WORDS = (
    "rm ",
    "del ",
    "delete ",
    "format ",
    "shutdown ",
    "restart ",
    "git push",
    "git reset",
    "deploy",
    "publish",
    "upload",
    "send ",
    "buy ",
    "checkout",
    "password",
    "cookie",
    "history",
    "scrape",
    "crawl",
    "pip install",
    "npm install",
)


class WorkflowSafetyEngine:
    """Refuse recipes that try to become autopilot."""

    def validate(self, recipe: WorkflowRecipe) -> WorkflowRecipeSafetyResult:
        warnings: list[str] = []
        blocked_reasons: list[str] = []
        if not recipe.steps:
            blocked_reasons.append("recipe has no steps")
        for step in recipe.steps:
            if step.step_type not in ALLOWED_STEP_TYPES:
                blocked_reasons.append(f"blocked step type: {step.step_type}")
            if step.allowed_to_auto_run:
                blocked_reasons.append(f"auto-run disabled for recipes: {step.title}")
            command = step.linked_command.lower()
            if any(word in command for word in BLOCKED_COMMAND_WORDS):
                blocked_reasons.append(f"blocked command phrase in step: {step.title}")
            if step.step_type in RISKY_STEP_TYPES and not step.requires_confirmation:
                warnings.append(f"{step.title} should require confirmation")
        if blocked_reasons:
            return WorkflowRecipeSafetyResult(
                False,
                True,
                "blocked",
                "; ".join(blocked_reasons[:4]),
                warnings,
            )
        safety_level = "high" if warnings or recipe.safety_level == "high" else recipe.safety_level
        return WorkflowRecipeSafetyResult(True, False, safety_level, "recipe is guided-only", warnings)

    def status_line(self) -> str:
        return "workflow safety on. recipes guide only. no autopilot."
