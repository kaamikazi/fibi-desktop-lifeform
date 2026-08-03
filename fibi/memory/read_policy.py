"""Consent and sensitivity policy shared by Stage 1 read adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from fibi.memory.policy import ConsentStatus, MemoryStatus, SensitivityLevel


class Sanitizer(Protocol):
    def sanitize(self, text: str) -> str: ...


class RiskAssessment(Protocol):
    blocked: bool
    requires_approval: bool
    sensitive_flag: str


class RiskGuard(Protocol):
    def assess(self, text: str, *, source: str = "", user_requested: bool = False) -> RiskAssessment: ...


@dataclass(frozen=True, slots=True)
class ReadPolicyDecision:
    allowed: bool
    consent: ConsentStatus | None
    sensitivity: SensitivityLevel
    status: MemoryStatus | None


class MemoryReadPolicy:
    """Fail closed for secrets, deleted rows, and unapproved sensitive data."""

    _PROHIBITED_FLAGS = {"secret", "regulated_id", "private_page_text"}

    def __init__(self, sanitizer: Sanitizer, guard: RiskGuard) -> None:
        self._sanitizer = sanitizer
        self._guard = guard

    def evaluate(self, content: str, metadata: Mapping[str, Any], source: str) -> ReadPolicyDecision:
        review = metadata.get("review", {})
        if not isinstance(review, Mapping):
            review = {}
        consent = self._consent(review, metadata)
        status = self._status(review, metadata)
        risk = self._guard.assess(content, source=source)
        flag = str(review.get("sensitive_flag") or metadata.get("sensitive_flag") or risk.sensitive_flag)
        sensitivity = self._sensitivity(flag, risk.blocked, risk.requires_approval)
        secret_changed = self._sanitizer.sanitize(content) != content
        allowed = (
            bool(content.strip())
            and not secret_changed
            and not risk.blocked
            and sensitivity not in {SensitivityLevel.PROHIBITED, SensitivityLevel.RESTRICTED}
            and status not in {MemoryStatus.DELETED, MemoryStatus.EXPIRED}
            and consent not in {ConsentStatus.REJECTED, ConsentStatus.REVOKED}
            and not (sensitivity is SensitivityLevel.SENSITIVE and consent is not ConsentStatus.APPROVED)
        )
        return ReadPolicyDecision(allowed, consent, sensitivity, status)

    @staticmethod
    def _consent(review: Mapping[str, Any], metadata: Mapping[str, Any]) -> ConsentStatus | None:
        raw = review.get("consent_status", metadata.get("consent_status"))
        if isinstance(raw, str):
            try:
                return ConsentStatus(raw.lower())
            except ValueError:
                return None
        approved = review.get("approved", metadata.get("approved"))
        if approved is True:
            return ConsentStatus.APPROVED
        if approved is False:
            return ConsentStatus.CANDIDATE
        return None

    @staticmethod
    def _status(review: Mapping[str, Any], metadata: Mapping[str, Any]) -> MemoryStatus | None:
        if review.get("archived") is True or metadata.get("archived") is True:
            return MemoryStatus.ARCHIVED
        raw = review.get("deletion_status", metadata.get("status"))
        if isinstance(raw, str):
            try:
                return MemoryStatus(raw.lower())
            except ValueError:
                return None
        return None

    @classmethod
    def _sensitivity(cls, flag: str, blocked: bool, requires_approval: bool) -> SensitivityLevel:
        lowered = flag.lower().strip()
        if blocked or lowered in cls._PROHIBITED_FLAGS:
            return SensitivityLevel.PROHIBITED
        if lowered == SensitivityLevel.RESTRICTED.value:
            return SensitivityLevel.RESTRICTED
        if requires_approval or lowered not in {"", "normal"}:
            return SensitivityLevel.SENSITIVE
        return SensitivityLevel.NORMAL
