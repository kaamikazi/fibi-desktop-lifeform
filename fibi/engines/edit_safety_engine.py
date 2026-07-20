"""Safety checks for v0.16 project edit suggestions.

This engine only decides whether Fibi may suggest an edit. It never applies
changes and it never runs commands.
"""

from __future__ import annotations

from pathlib import Path

from fibi.engines.project_scanner_engine import SECRET_FILENAMES, SECRET_PREFIXES
from fibi.engines.types import EditRiskAssessment, EditSafetyResult


class EditSafetyEngine:
    """Classify project edit requests before any suggestion is generated."""

    LOW_SIGNALS = ("copy", "text", "title", "css", "class", "color", "style", "ui", "label")
    MEDIUM_SIGNALS = ("logic", "config", "dependency", "package", "refactor", "api", "state")
    HIGH_SIGNALS = ("auth", "payment", "stripe", "database", "migration", "security", "token", "password")
    BLOCKED_SIGNALS = (
        "delete file",
        "remove file",
        "wipe",
        "drop database",
        "format disk",
        "run command",
        "execute",
        "install package",
        "npm install",
        "pip install",
        "bypass auth",
        "disable security",
        "hide malware",
        "steal",
        "exfiltrate",
    )

    def assess(self, user_request: str, target_files: list[str] | None = None) -> EditSafetyResult:
        request = user_request.lower()
        files = target_files or []
        blocked_reason = self._blocked_file_reason(files) or self._blocked_request_reason(request)
        if blocked_reason:
            return EditSafetyResult(
                False,
                EditRiskAssessment("blocked", blocked_reason, blocked=True),
                refused_reason=blocked_reason,
                fibi_reply=self._refusal(blocked_reason),
            )

        risk_level = "low"
        reason = "small text/UI-style suggestion"
        warnings: list[str] = []
        if any(signal in request for signal in self.HIGH_SIGNALS):
            risk_level = "high"
            reason = "touches security, payments, auth, or data"
            warnings.append("human review first")
        elif any(signal in request for signal in self.MEDIUM_SIGNALS):
            risk_level = "medium"
            reason = "could affect behavior or configuration"
            warnings.append("review before applying manually")
        elif not any(signal in request for signal in self.LOW_SIGNALS):
            risk_level = "medium"
            reason = "unclear code change"
            warnings.append("Fibi is guessing tiny; review carefully")

        return EditSafetyResult(
            True,
            EditRiskAssessment(risk_level, reason, blocked=False, warnings=warnings),
        )

    def _blocked_file_reason(self, files: list[str]) -> str:
        for file_name in files:
            name = Path(file_name).name.lower()
            if name in SECRET_FILENAMES or name.startswith(SECRET_PREFIXES):
                return "secret file edit blocked"
            if name.endswith(".env") or name.startswith(".env") or name.endswith(".pem") or name.endswith(".key"):
                return "secret crumbs"
        return ""

    def _blocked_request_reason(self, request: str) -> str:
        if any(signal in request for signal in self.BLOCKED_SIGNALS):
            return "too sharp for tiny hands"
        return ""

    @staticmethod
    def _refusal(reason: str) -> str:
        if "secret" in reason:
            return "nope. secret crumbs."
        if "sharp" in reason:
            return "too sharp for tiny hands."
        return "human review first."
