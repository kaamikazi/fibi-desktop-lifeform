"""Sensitive-memory checks for local memory writes and exports."""

from __future__ import annotations

import re

from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import MemoryRiskResult


class SensitiveMemoryGuard:
    """Decide whether a memory is safe to keep, needs approval, or is blocked."""

    API_KEY = re.compile(r"\b(?:sk-|pk_)[A-Za-z0-9_\-]{20,}\b")
    TOKEN_WORD = re.compile(r"(?i)\b(api[_ -]?key|token|secret|password|passwd|private key|recovery code)\b")
    CARD_NUMBER = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
    GOV_ID = re.compile(r"(?i)\b(ssn|social security|passport number|national id|nid|driver'?s license)\b")
    HOME_ADDRESS = re.compile(r"(?i)\b\d{1,6}\s+[A-Za-z0-9 .'-]{4,}\s+(street|st|road|rd|avenue|ave|lane|ln|drive|dr|house)\b")
    MEDICAL = re.compile(r"(?i)\b(diagnosed with|diagnosis|medication|therapy|hospital|mental health)\b")
    LEGAL = re.compile(r"(?i)\b(lawsuit|divorce|custody|criminal charge|legal case)\b")
    RELATIONSHIP = re.compile(r"(?i)\b(affair|abuse|pregnant|breakup|relationship secret)\b")
    PRIVATE_PAGE = re.compile(r"(?i)\b(private page|bank page|account page|inbox|dm|direct message|medical portal)\b")
    PROJECT_SECRET = re.compile(r"(?i)\b(\.env|credentials|secrets\.json|id_rsa|ssh key)\b")

    def __init__(self, sanitizer: SecretSanitizer | None = None) -> None:
        self.sanitizer = sanitizer or SecretSanitizer()

    def assess(self, text: str, *, source: str = "", user_requested: bool = False) -> MemoryRiskResult:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return MemoryRiskResult(False, blocked=True, sensitive_flag="empty", reason="empty memory")

        masked = self.sanitizer.sanitize(cleaned)
        if masked != cleaned or self.API_KEY.search(cleaned) or self.TOKEN_WORD.search(cleaned) or self.PROJECT_SECRET.search(cleaned):
            masked_preview = masked if masked != cleaned else "[masked secret]"
            return MemoryRiskResult(
                allowed=False,
                blocked=True,
                sensitive_flag="secret",
                reason="secret-like text",
                safe_summary="secret crumb. not keeping.",
                masked_preview=self._preview(masked_preview),
            )
        if self.CARD_NUMBER.search(cleaned) or self.GOV_ID.search(cleaned):
            return MemoryRiskResult(
                allowed=False,
                blocked=True,
                sensitive_flag="regulated_id",
                reason="regulated identifier",
                safe_summary="too private. not keeping that.",
                masked_preview=self._preview(masked),
            )
        if self.PRIVATE_PAGE.search(cleaned) or "raw_browser_page" in source.lower():
            return MemoryRiskResult(
                allowed=False,
                blocked=True,
                sensitive_flag="private_page_text",
                reason="raw private page text",
                safe_summary="private page crumb. summary only, if you ask clearly.",
                masked_preview=self._preview(masked),
            )

        sensitive_patterns = [
            ("home_address", self.HOME_ADDRESS),
            ("medical", self.MEDICAL),
            ("legal", self.LEGAL),
            ("relationship", self.RELATIONSHIP),
        ]
        for flag, pattern in sensitive_patterns:
            if pattern.search(cleaned):
                if user_requested:
                    return MemoryRiskResult(
                        allowed=True,
                        requires_approval=False,
                        sensitive_flag=flag,
                        reason="user explicitly requested memory",
                        safe_summary=self._safe_summary(cleaned),
                        masked_preview=self._preview(masked),
                    )
                return MemoryRiskResult(
                    allowed=False,
                    requires_approval=True,
                    sensitive_flag=flag,
                    reason="sensitive personal note",
                    safe_summary="too private. ask me to remember it clearly first.",
                    masked_preview=self._preview(masked),
                )

        return MemoryRiskResult(
            allowed=True,
            sensitive_flag="",
            reason="safe general memory",
            safe_summary=self._safe_summary(cleaned),
            masked_preview=self._preview(masked),
        )

    def can_export(self, text: str, sensitive_flag: str = "") -> bool:
        risk = self.assess(text)
        if risk.blocked:
            return False
        return sensitive_flag not in {"secret", "regulated_id", "private_page_text"}

    @staticmethod
    def _preview(text: str, limit: int = 180) -> str:
        return text[:limit] + ("..." if len(text) > limit else "")

    @staticmethod
    def _safe_summary(text: str, limit: int = 220) -> str:
        summary = " ".join(text.split())
        return summary[:limit] + ("..." if len(summary) > limit else "")
