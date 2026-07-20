"""Convert user goals into conservative supervised work-session plans."""

from __future__ import annotations

import uuid

from fibi.engines.types import ProjectWorkspace, WorkSessionPlan, WorkSessionStep

BLOCKED_PLAN_WORDS = ("install", "git", "deploy", "publish", "delete", "remove all", "rm -rf", "migration", "migrate")


class WorkPlannerEngine:
    """Create safe, permission-first plans for project work."""

    def plan(self, user_goal: str, project: ProjectWorkspace | None) -> WorkSessionPlan:
        goal = " ".join(user_goal.strip().split())
        lowered = goal.lower()
        notes: list[str] = []
        if any(word in lowered for word in BLOCKED_PLAN_WORDS):
            notes.append("Blocked risky request terms from the plan.")
        if project is None:
            if self._is_browser_goal(lowered):
                return WorkSessionPlan(
                    goal,
                    [
                        self._step("browser_open_manual", "open URL manually", "Use /browser open <url> and confirm only if you want.", confirmation=True),
                        self._step("browser_paste_text", "paste page text", "Paste public page text; Fibi will not scrape it.", automatic=True),
                        self._step("browser_summarize", "summarize provided page", "Summarize only the text the user provided.", automatic=True),
                        self._step("browser_save_note", "save approved note", "Remember only a user-approved summary.", confirmation=True),
                        self._step("done", "wrap up", "List manual next steps.", automatic=True),
                    ],
                    "medium",
                    notes or ["Browser helper plan is manual-only."],
                )
            return WorkSessionPlan(
                goal,
                [self._step("ask_user", "pick a project", "Add or switch to a project nest first.", confirmation=False, automatic=True)],
                "low",
                notes,
            )
        if self._is_failed_build_goal(lowered):
            steps = [
                self._step("inspect_project", "inspect project", "Review the active project summary.", automatic=True),
                self._step("analyze_check_failure", "check last failure", "Analyze the last failed check output.", automatic=True),
                self._step("suggest_fix", "suggest safe fix", "Create a pending patch only if the fix is safe.", automatic=True),
                self._step("apply_patch", "wait for patch confirm", "User reviews and confirms any pending patch.", confirmation=True),
                self._step("run_check", "suggest checking again", "Ask before running a safe project check.", confirmation=True),
                self._step("done", "wrap up", "Summarize what changed.", automatic=True),
            ]
            return WorkSessionPlan(goal, steps, "medium", notes)
        if self._is_ui_goal(lowered):
            steps = [
                self._step("ask_user", "choose target file", "Ask which UI file to improve if unclear.", automatic=True),
                self._step("read_file", "read chosen file", "Read only the user-approved project file.", confirmation=True),
                self._step("suggest_edit", "suggest edit", "Prepare a safe edit suggestion.", automatic=True),
                self._step("apply_patch", "wait for patch confirm", "User reviews and confirms the patch.", confirmation=True),
                self._step("run_check", "suggest safe check", "Ask before running checks.", confirmation=True),
                self._step("done", "wrap up", "Summarize the UI work.", automatic=True),
            ]
            return WorkSessionPlan(goal, steps, "medium", notes)
        if self._is_review_goal(lowered):
            steps = [
                self._step("inspect_project", "inspect project", "Review registered project metadata.", automatic=True),
                self._step("summarize_project", "summarize project", "Summarize files and likely stack.", automatic=True),
                self._step("manual_instruction", "give review notes", "Offer safe next actions without changing files.", automatic=True),
                self._step("done", "wrap up", "Summarize the review.", automatic=True),
            ]
            return WorkSessionPlan(goal, steps, "low", notes)
        if self._is_browser_goal(lowered):
            steps = [
                self._step("browser_open_manual", "open URL manually", "Use /browser open <url>; no hidden scraping.", confirmation=True),
                self._step("browser_paste_text", "paste page text", "User provides page text or drops an HTML/text file.", automatic=True),
                self._step("browser_summarize", "summarize provided page", "Summarize only user-provided text.", automatic=True),
                self._step("browser_research_note", "make research note", "Create a manual research/outreach note from provided text.", automatic=True),
                self._step("browser_save_note", "save approved note", "Remember only the approved summary.", confirmation=True),
                self._step("done", "wrap up", "Summarize manual next steps.", automatic=True),
            ]
            return WorkSessionPlan(goal, steps, "medium", notes or ["Browser helper plan is manual-only."])
        return WorkSessionPlan(
            goal,
            [
                self._step("inspect_project", "inspect project", "Review the active project summary.", automatic=True),
                self._step("ask_user", "narrow goal", "Ask for the target file or expected behavior.", automatic=True),
                self._step("manual_instruction", "guide next action", "Suggest the safest next command.", automatic=True),
                self._step("done", "wrap up", "Summarize the session.", automatic=True),
            ],
            "low",
            notes or ["Ambiguous goal; plan starts by asking a clarifying question."],
        )

    @staticmethod
    def _is_failed_build_goal(lowered: str) -> bool:
        return any(phrase in lowered for phrase in ("failed build", "build fail", "debug", "fix this project", "help me fix", "fix the project", "fix tests", "fix the tests"))

    @staticmethod
    def _is_ui_goal(lowered: str) -> bool:
        return any(phrase in lowered for phrase in ("ui", "cleaner", "button", "page", "screen", "layout", "feature"))

    @staticmethod
    def _is_review_goal(lowered: str) -> bool:
        return "review" in lowered or "look over" in lowered

    @staticmethod
    def _is_browser_goal(lowered: str) -> bool:
        return any(phrase in lowered for phrase in ("browser", "website", "web page", "research this", "contact this business", "outreach", "site"))

    @staticmethod
    def _step(
        step_type: str,
        title: str,
        description: str,
        confirmation: bool = False,
        automatic: bool = False,
    ) -> WorkSessionStep:
        return WorkSessionStep(
            step_id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            step_type=step_type,
            requires_confirmation=confirmation,
            allowed_to_run_automatically=automatic and not confirmation,
        )
