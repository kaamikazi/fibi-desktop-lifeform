"""Runtime permission overview for Fibi."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionOverview:
    desktop_actions: bool
    project_checks: bool
    patch_apply: bool
    browser_helper: bool
    voice_input: bool
    rvc_voice_skin: bool
    cloud: bool
    memory_learning: bool
    beta_mode: bool


class PermissionOverviewEngine:
    """Format current permission switches without mutating them."""

    def format(self, overview: PermissionOverview) -> str:
        rows = [
            ("desktop actions", overview.desktop_actions),
            ("project checks", overview.project_checks),
            ("patch apply", overview.patch_apply),
            ("browser helper", overview.browser_helper),
            ("voice input", overview.voice_input),
            ("RVC voice skin", overview.rvc_voice_skin),
            ("cloud", overview.cloud),
            ("memory learning", overview.memory_learning),
            ("beta mode", overview.beta_mode),
        ]
        return "permissions:\n" + "\n".join(f"- {name}: {'on' if enabled else 'off'}" for name, enabled in rows)
