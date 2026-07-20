"""Safety checks for confirmed patch application."""

from __future__ import annotations

from pathlib import Path

from fibi.engines.project_scanner_engine import BINARY_EXTENSIONS, SECRET_FILENAMES, SECRET_PREFIXES
from fibi.engines.types import PatchRiskResult


class PatchSafetyEngine:
    """Classify whether Fibi may apply a reviewed patch."""

    LOW_EXTENSIONS = {".md", ".txt", ".css", ".scss"}
    MEDIUM_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".toml", ".yaml", ".yml"}
    HIGH_PATH_SIGNALS = ("auth", "payment", "stripe", "database", "migration", "security", "permission", "encrypt")
    BLOCKED_NAMES = {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "pipfile.lock",
    }

    def assess(self, target_files: list[str], diff_text: str = "") -> PatchRiskResult:
        if not target_files:
            return PatchRiskResult(False, "blocked", "no target files", blocked=True, fibi_reply="what file crumb?")
        highest = "low"
        warnings: list[str] = []
        for relative_path in target_files:
            reason = self._blocked_reason(relative_path, diff_text)
            if reason:
                return PatchRiskResult(False, "blocked", reason, blocked=True, fibi_reply=self._fibi_reply(reason))
            lowered = relative_path.lower()
            suffix = Path(lowered).suffix
            if any(signal in lowered for signal in self.HIGH_PATH_SIGNALS):
                return PatchRiskResult(
                    False,
                    "high",
                    "touches high-risk auth, payment, database, security, or permission code",
                    blocked=False,
                    warnings=["manual only in v0.18"],
                    fibi_reply="manual only.",
                )
            if suffix in self.MEDIUM_EXTENSIONS:
                highest = "medium"
                warnings.append("review behavior changes carefully")
        reason = "small docs/UI patch" if highest == "low" else "code/config text patch"
        return PatchRiskResult(True, highest, reason, requires_confirmation=True, warnings=warnings)

    def _blocked_reason(self, relative_path: str, diff_text: str) -> str:
        path = Path(relative_path.replace("\\", "/"))
        name = path.name.lower()
        suffix = path.suffix.lower()
        if name in SECRET_FILENAMES or name.startswith(SECRET_PREFIXES):
            return "secret crumbs"
        if name.startswith(".env") or suffix in {".pem", ".key", ".p12", ".pfx"}:
            return "secret crumbs"
        if suffix in BINARY_EXTENSIONS:
            return "binary file"
        if name in self.BLOCKED_NAMES:
            return "lockfile patch blocked"
        if name.endswith(".min.js") or "/vendor/" in f"/{relative_path.lower()}":
            return "vendor/minified file blocked"
        if self._looks_like_delete(diff_text):
            return "deleting files blocked"
        return ""

    @staticmethod
    def _looks_like_delete(diff_text: str) -> bool:
        lowered = diff_text.lower()
        return "deleted file mode" in lowered or "--- a/" in lowered and "+++ /dev/null" in lowered

    @staticmethod
    def _fibi_reply(reason: str) -> str:
        if "secret" in reason:
            return "secret crumbs. not touching."
        if "binary" in reason:
            return "can't edit that kind of crumb."
        if "lockfile" in reason:
            return "package spellbook. manual only."
        return "too sharp for tiny hands."
