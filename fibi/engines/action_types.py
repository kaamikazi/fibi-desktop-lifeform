"""Action registry for Fibi v0.12 manual hands.

This file is intentionally declarative. Engines can ask "what kind of action is
this?" without each one inventing its own safety rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fibi.engines.types import ActionRiskLevel


@dataclass(frozen=True, slots=True)
class ActionTypeDefinition:
    action_name: str
    risk_level: ActionRiskLevel
    requires_confirmation: bool
    enabled_by_default: bool
    description: str
    success_lines: list[str] = field(default_factory=list)
    blocked_lines: list[str] = field(default_factory=list)
    confirmation_lines: list[str] = field(default_factory=list)


SUCCESS_LINES = ["opening it.", "app creature summoned.", "internet hole opened.", "tiny volume push."]
BLOCKED_LINES = ["nope. too dangerous.", "human hands for that.", "tiny creature refuses.", "not touching that yet."]
CONFIRMATION_LINES = ["danger button.", "confirm?", "say the scary words."]


def _safe(name: str, description: str) -> ActionTypeDefinition:
    return ActionTypeDefinition(
        name,
        ActionRiskLevel.SAFE,
        False,
        True,
        description,
        SUCCESS_LINES,
        BLOCKED_LINES,
        CONFIRMATION_LINES,
    )


def _confirm(name: str, description: str) -> ActionTypeDefinition:
    return ActionTypeDefinition(
        name,
        ActionRiskLevel.CONFIRM_REQUIRED,
        True,
        False,
        description,
        SUCCESS_LINES,
        BLOCKED_LINES,
        CONFIRMATION_LINES,
    )


def _blocked(name: str, description: str) -> ActionTypeDefinition:
    return ActionTypeDefinition(
        name,
        ActionRiskLevel.BLOCKED_FOR_NOW,
        False,
        False,
        description,
        SUCCESS_LINES,
        BLOCKED_LINES,
        CONFIRMATION_LINES,
    )


ACTION_TYPES: dict[str, ActionTypeDefinition] = {
    "open_app": _safe("open_app", "Open a known indexed desktop app."),
    "open_folder": _safe("open_folder", "Open an allowlisted user folder."),
    "open_project_vscode": _safe("open_project_vscode", "Open a registered project in indexed VS Code."),
    "open_website": _safe("open_website", "Open a known website in the default browser."),
    "copy_text": _safe("copy_text", "Copy user-provided non-secret text to the clipboard."),
    "web_search": _safe("web_search", "Open a Google search in the default browser."),
    "youtube_search": _safe("youtube_search", "Open a YouTube search in the default browser."),
    "wikipedia_search": _safe("wikipedia_search", "Open a Wikipedia search in the default browser."),
    "volume_up": _safe("volume_up", "Press the system volume-up media key."),
    "volume_down": _safe("volume_down", "Press the system volume-down media key."),
    "mute": _safe("mute", "Press the system mute media key."),
    "unmute": _safe("unmute", "Press the system mute media key when audio is muted."),
    "tell_time": _safe("tell_time", "Tell the local system time."),
    "tell_date": _safe("tell_date", "Tell the local system date."),
    "refresh_app_index": _safe("refresh_app_index", "Refresh the local app index."),
    "list_known_apps": _safe("list_known_apps", "Summarize known local apps."),
    "search_known_apps": _safe("search_known_apps", "Search the local app index."),
    "screenshot": _confirm("screenshot", "Take a screenshot, disabled by default."),
    "type_text": _confirm("type_text", "Type user-approved non-secret text into the active application."),
    "create_folder": _confirm("create_folder", "Create one folder inside an allowlisted location."),
    "run_safe_command": _confirm("run_safe_command", "Run one exact command from Fibi's safe command allowlist."),
    "shutdown_pc": _confirm("shutdown_pc", "Shut down the PC, disabled by default."),
    "restart_pc": _confirm("restart_pc", "Restart the PC, disabled by default."),
    "open_file_location": _confirm("open_file_location", "Open a file location, disabled by default."),
    "launch_unknown_executable": _confirm("launch_unknown_executable", "Launch an unknown executable, disabled by default."),
    "delete_file": _blocked("delete_file", "Delete files. Not allowed in v0.12."),
    "modify_file": _blocked("modify_file", "Modify files. Not allowed in v0.12."),
    "run_terminal_command": _blocked("run_terminal_command", "Run terminal commands. Not allowed in v0.12."),
    "send_message": _blocked("send_message", "Send messages. Not allowed in v0.12."),
    "send_email": _blocked("send_email", "Send email. Not allowed in v0.12."),
    "read_private_messages": _blocked("read_private_messages", "Read private messages. Not allowed in v0.12."),
    "read_clipboard": _blocked("read_clipboard", "Read clipboard. Disabled in v0.12 action core."),
    "purchase": _blocked("purchase", "Buy things. Not allowed in v0.12."),
    "login_action": _blocked("login_action", "Login or account actions. Not allowed in v0.12."),
    "password_action": _blocked("password_action", "Password actions. Not allowed in v0.12."),
    "install_software": _blocked("install_software", "Install software. Not allowed."),
    "autonomous_clicking": _blocked("autonomous_clicking", "Autonomous clicking. Not allowed in v0.12."),
    "autonomous_typing": _blocked("autonomous_typing", "Autonomous typing. Not allowed in v0.12."),
}


def get_action_definition(action_type: str) -> ActionTypeDefinition | None:
    return ACTION_TYPES.get(action_type)
