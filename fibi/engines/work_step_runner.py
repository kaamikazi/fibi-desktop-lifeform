"""Run only safe guided-session steps."""

from __future__ import annotations

import logging
from collections.abc import Callable

from fibi.engines.types import WorkSessionDecision, WorkSessionStep

LOGGER = logging.getLogger(__name__)


class WorkStepRunner:
    """Execute safe informational steps and refuse restricted automation."""

    RESTRICTED_STEPS = {"apply_patch", "run_check", "read_file", "create_patch", "suggest_edit", "suggest_fix"}

    def __init__(
        self,
        project_summary: Callable[[], str],
        check_analysis: Callable[[], str],
        suggest_fix: Callable[[], str],
    ) -> None:
        self.project_summary = project_summary
        self.check_analysis = check_analysis
        self.suggest_fix = suggest_fix

    def run(self, step: WorkSessionStep) -> WorkSessionDecision:
        if step.step_type in self.RESTRICTED_STEPS or step.requires_confirmation:
            LOGGER.info("session_waiting_for_confirmation", extra={"step_type": step.step_type})
            return WorkSessionDecision(
                False,
                None,
                f"need permission. next crumb: {step.title}. {self._confirmation_hint(step)}",
                True,
            )
        if not step.allowed_to_run_automatically:
            return WorkSessionDecision(False, None, f"need permission. next crumb: {step.title}.", True)
        if step.step_type in {"inspect_project", "summarize_project"}:
            return WorkSessionDecision(True, None, self.project_summary(), False)
        if step.step_type == "analyze_check_failure":
            return WorkSessionDecision(True, None, self.check_analysis(), False)
        if step.step_type == "suggest_fix":
            return WorkSessionDecision(True, None, self.suggest_fix(), False)
        if step.step_type == "ask_user":
            return WorkSessionDecision(True, None, f"next crumb: {step.description}", True)
        if step.step_type == "manual_instruction":
            return WorkSessionDecision(True, None, step.description, True)
        if step.step_type == "done":
            return WorkSessionDecision(True, None, "done-ish.", False)
        return WorkSessionDecision(False, None, f"not running that step automatically: {step.title}.", True)

    @staticmethod
    def _confirmation_hint(step: WorkSessionStep) -> str:
        if step.step_type == "apply_patch":
            return "say: apply patch confirm"
        if step.step_type == "run_check":
            return "say: /check run <preset>"
        if step.step_type == "read_file":
            return "say: /project read <file>"
        if step.step_type == "suggest_fix":
            return "say: /check suggest fix"
        if step.step_type == "suggest_edit":
            return "say: /edit file <path> <request>"
        return "confirm first."
