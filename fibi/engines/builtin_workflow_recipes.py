"""Built-in guided workflow recipes for Fibi v0.28."""

from __future__ import annotations

from datetime import datetime

from fibi.engines.types import WorkflowRecipe, WorkflowRecipeStep


def builtin_workflow_recipes() -> list[WorkflowRecipe]:
    """Return the local, versioned recipe catalogue.

    Recipes are guidance only. Risky steps point to existing confirmation
    commands instead of running anything behind the user's back.
    """

    now = _now()
    return [
        _recipe(
            "debug_failed_project",
            "Debug Failed Project",
            "Walk through a failed project check without auto-editing files.",
            "project_debug",
            "medium",
            [
                _step("check_project", "Check active project", "Confirm the current project nest.", "inspect_project"),
                _step("last_check", "Show last check result", "Look at the last saved check result summary.", "analyze_check"),
                _step("analyze_failure", "Analyze failed check", "Explain the failure from saved output only.", "analyze_check"),
                _step("resolve_files", "Resolve related files", "Suggest likely files to inspect safely.", "read_safe_file", True, "/project read <file>", "file path"),
                _step("suggest_fix", "Suggest fix", "Suggest a patch for review without applying it.", "suggest_patch", True, "/check suggest fix"),
                _step("patch_confirm", "Wait for patch confirmation", "Only apply after the existing patch confirmation phrase.", "apply_patch_confirmed", True, "apply patch confirm"),
                _step("rerun_check", "Suggest rerun check", "Ask before rerunning project checks.", "run_check_confirmed", True, "/check run <preset>"),
            ],
            now,
        ),
        _recipe(
            "safe_release_build",
            "Safe Release Build",
            "Prepare a local beta release with explicit confirmations.",
            "project_release",
            "high",
            [
                _step("self_test", "Run self-test", "Use /self test and inspect the result.", "manual_step", False, "/self test"),
                _step("run_checks", "Run checks with confirmation", "Run pytest or smoke checks only after user confirmation.", "run_check_confirmed", True, "run check confirm"),
                _step("build_zip", "Build Windows zip with confirmation", "Build release zip only through the confirmed release flow.", "build_release_confirmed", True, "python tools/build_windows.py --clean --zip"),
                _step("verify_release", "Verify release", "Run release verification only after confirmation.", "run_check_confirmed", True, "python tools/verify_release.py --gui-smoke"),
                _step("checksums", "Make checksums", "Generate local checksums for built artifacts.", "run_check_confirmed", True, "python tools/make_checksums.py"),
                _step("artifact_paths", "Show artifact paths", "List local zip, manifest, and checksum paths.", "manual_step"),
                _step("release_summary", "Export release summary", "Export a safe summary without logs or secrets.", "manual_step"),
            ],
            now,
        ),
        _recipe(
            "beta_qa_pass",
            "Beta QA Pass",
            "Run a small local beta QA ritual.",
            "beta_qa",
            "medium",
            [
                _step("qa_checklist", "Open QA checklist", "Review the beta tester checklist.", "manual_step", False, "docs/BETA_TESTER_GUIDE_V025.md"),
                _step("gui_smoke", "Run GUI smoke", "Run GUI smoke only by explicit command.", "run_check_confirmed", True, "python app.py --gui-smoke"),
                _step("self_test", "Run self-test", "Use /self test.", "manual_step", False, "/self test"),
                _step("health_gui", "Check health GUI", "Use /health gui.", "manual_step", False, "/health gui"),
                _step("support_bundle", "Test support bundle", "Create a local support bundle only if the user asks.", "export_support_bundle", True, "/support bundle"),
                _step("record_result", "Record QA result", "Save a short local QA note.", "manual_step"),
            ],
            now,
        ),
        _recipe(
            "website_review_outreach",
            "Website Review / Outreach Research",
            "Review a website from user-provided text only.",
            "browser_research",
            "medium",
            [
                _step("save_url", "Save URL", "Save the public URL as a note.", "browser_open_confirmed", True, "/browser note <url> <note>"),
                _step("paste_text", "Ask user to paste page text", "User pastes visible page text; Fibi does not scrape.", "ask_user"),
                _step("summarize_page", "Summarize pasted page", "Summarize only provided text.", "summarize_pasted_page", False, "/browser summarize"),
                _step("pain_points", "Identify visible pain points", "Use only the provided page text.", "manual_step"),
                _step("draft_outreach", "Draft outreach message", "Draft for the user to review. Do not send.", "manual_step"),
                _step("save_note", "Save browser research note", "Save an approved summary only.", "manual_step", False, "/browser save page"),
            ],
            now,
        ),
        _recipe(
            "bug_report_support_bundle",
            "Bug Report Support Bundle",
            "Create a local issue and safe support bundle.",
            "issue_report",
            "medium",
            [
                _step("create_issue", "Create issue", "Start the issue flow.", "create_issue", False, "/issue new <title | details>"),
                _step("repro_steps", "Ask reproduction steps", "Ask for steps, expected behavior, and actual behavior.", "ask_user"),
                _step("release_health", "Capture release health", "Use /release health.", "manual_step", False, "/release health"),
                _step("export_bundle", "Export support bundle for issue", "Export safe local bundle after issue exists.", "export_support_bundle", True, "/support bundle for issue <id>"),
                _step("show_paths", "Show saved files", "Show issue/support bundle paths.", "manual_step"),
            ],
            now,
        ),
        _recipe(
            "daily_fibi_startup_check",
            "Daily Fibi Startup Check",
            "A small morning check-in for Fibi's local state.",
            "daily_startup",
            "low",
            [
                _step("startup_status", "Run startup status", "Use /startup status.", "manual_step", False, "/startup status"),
                _step("health_gui", "Run health gui", "Use /health gui.", "manual_step", False, "/health gui"),
                _step("active_session", "Show active session/project", "Show current project and session crumbs.", "inspect_project"),
                _step("critical_issues", "Show open critical issues", "List local issue tracker summary.", "manual_step", False, "/issue list"),
                _step("done", "Done", "Tiny ritual complete.", "done"),
            ],
            now,
        ),
    ]


def _recipe(
    recipe_id: str,
    name: str,
    description: str,
    category: str,
    safety_level: str,
    steps: list[WorkflowRecipeStep],
    now: str,
) -> WorkflowRecipe:
    return WorkflowRecipe(
        recipe_id=recipe_id,
        name=name,
        description=description,
        category=category,
        version="0.30.3",
        steps=steps,
        safety_level=safety_level,
        created_at=now,
        updated_at=now,
        built_in=True,
        enabled=True,
    )


def _step(
    step_id: str,
    title: str,
    instruction: str,
    step_type: str,
    confirmation: bool = False,
    linked_command: str = "",
    expected_input: str = "",
) -> WorkflowRecipeStep:
    return WorkflowRecipeStep(
        step_id=step_id,
        title=title,
        instruction=instruction,
        step_type=step_type,
        requires_confirmation=confirmation,
        allowed_to_auto_run=False,
        linked_command=linked_command,
        expected_input=expected_input,
        safety_notes="Guidance only. Existing confirmations still apply.",
    )


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
