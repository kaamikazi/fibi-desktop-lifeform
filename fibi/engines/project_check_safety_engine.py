"""Safety validation for project check commands."""

from __future__ import annotations

from pathlib import Path

from fibi.engines.project_check_preset_engine import DANGEROUS_TOKENS
from fibi.engines.types import CheckCommandPreset, ProjectCheckRequest, ProjectCheckSafetyResult, ProjectWorkspace


class ProjectCheckSafetyEngine:
    """Refuse arbitrary, destructive, or outside-project check execution."""

    def assess(
        self,
        request: ProjectCheckRequest,
        workspace: ProjectWorkspace,
        preset: CheckCommandPreset | None,
        require_confirmation: bool = True,
    ) -> ProjectCheckSafetyResult:
        if preset is None:
            return ProjectCheckSafetyResult(False, "blocked", "unknown command refused", True, "unknown command")
        root = Path(workspace.root_path).resolve()
        cwd = Path(request.cwd).resolve()
        try:
            cwd.relative_to(root)
        except ValueError:
            return ProjectCheckSafetyResult(False, "blocked", "cwd outside project", True, "outside project")
        if request.command_args != preset.command_args:
            return ProjectCheckSafetyResult(False, "blocked", "command args do not match preset", True, "not whitelisted")
        if self._dangerous(request.command_args):
            return ProjectCheckSafetyResult(False, "blocked", "dangerous command token", True, "dangerous token")
        if preset.risk_level in {"high", "blocked"}:
            return ProjectCheckSafetyResult(False, preset.risk_level, "manual only", True, "manual only")
        return ProjectCheckSafetyResult(True, preset.risk_level, "safe preset", require_confirmation)

    @staticmethod
    def _dangerous(args: list[str]) -> bool:
        joined = " " + " ".join(args).lower() + " "
        return any(token in joined for token in DANGEROUS_TOKENS)
