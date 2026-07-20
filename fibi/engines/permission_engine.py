"""Permission checks for manual desktop actions."""

from __future__ import annotations

import random

from fibi.engines.action_types import get_action_definition
from fibi.engines.types import ActionIntent, ActionPermissionResult, ActionRiskLevel, ActionSettings, PrivacySettings


class PermissionEngine:
    """Decide whether a detected action may run."""

    def check(
        self,
        intent: ActionIntent,
        action_settings: ActionSettings,
        privacy_settings: PrivacySettings,
        direct_user_initiated: bool,
        quiet_active: bool = False,
        boundary_active: bool = False,
        confirmed: bool = False,
    ) -> ActionPermissionResult:
        definition = get_action_definition(intent.action_type)
        if definition is None:
            return self._blocked("unknown action creature.")
        if not direct_user_initiated or not intent.direct_user_initiated:
            return self._blocked("model hands blocked.")
        if definition.risk_level == ActionRiskLevel.BLOCKED_FOR_NOW:
            return self._blocked(random.choice(definition.blocked_lines), definition.description)
        if not action_settings.allow_desktop_actions:
            return self._blocked("hands tucked away.", "desktop actions disabled")
        if quiet_active and intent.action_type not in {"tell_time", "tell_date", "list_known_apps"}:
            return self._blocked("quiet hands.", "quiet mode active")
        if boundary_active:
            return self._blocked("boundary hands off.", "boundary active")

        setting_reason = self._setting_block_reason(intent.action_type, action_settings, privacy_settings)
        if setting_reason:
            return self._blocked(random.choice(definition.blocked_lines), setting_reason)

        if definition.requires_confirmation:
            if confirmed:
                return ActionPermissionResult(True, False, False, "confirmed", "", "doing the scary thing.")
            phrase = self.confirmation_phrase(intent.action_type)
            return ActionPermissionResult(
                False,
                False,
                True,
                definition.description,
                f"danger button. say: {phrase}",
                f"danger button. say: {phrase}",
            )

        return ActionPermissionResult(True, False, False, "safe manual action", "", random.choice(definition.success_lines))

    @staticmethod
    def confirmation_phrase(action_type: str) -> str:
        return {
            "shutdown_pc": "confirm shutdown",
            "restart_pc": "confirm restart",
            "screenshot": "confirm screenshot",
            "open_file_location": "confirm open location",
            "launch_unknown_executable": "confirm launch",
        }.get(action_type, f"confirm {action_type.replace('_', ' ')}")

    @staticmethod
    def _blocked(reply: str, reason: str = "blocked") -> ActionPermissionResult:
        return ActionPermissionResult(False, True, False, reason, "", reply)

    @staticmethod
    def _setting_block_reason(
        action_type: str,
        action_settings: ActionSettings,
        privacy_settings: PrivacySettings,
    ) -> str:
        if action_type == "open_app" and not action_settings.allow_open_apps:
            return "opening apps disabled"
        if action_type in {"open_website", "web_search", "youtube_search", "wikipedia_search"} and not action_settings.allow_web_search:
            return "web actions disabled"
        if action_type in {"volume_up", "volume_down", "mute", "unmute"} and not action_settings.allow_volume_control:
            return "volume control disabled"
        if action_type == "screenshot" and not action_settings.allow_screenshot:
            return "screenshots disabled"
        if action_type in {"shutdown_pc", "restart_pc"} and not action_settings.allow_shutdown:
            return "shutdown actions disabled"
        if action_type == "launch_unknown_executable" and not action_settings.allow_unknown_executables:
            return "unknown executable launch disabled"
        if action_type == "run_terminal_command" and not action_settings.allow_terminal_commands:
            return "terminal commands disabled"
        if action_type in {"delete_file", "modify_file"} and not action_settings.allow_file_modification:
            return "file modification disabled"
        if action_type == "read_clipboard" and (
            not action_settings.allow_clipboard_actions or not privacy_settings.allow_clipboard_observation
        ):
            return "clipboard actions disabled"
        return ""
