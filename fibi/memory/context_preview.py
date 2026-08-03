"""Disconnected preview of future approved memory context selection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

from fibi.memory.policy import ConsentStatus, MemoryStatus, SensitivityLevel
from fibi.memory.query_models import MemoryRecordView, MemoryViewCategory
from fibi.memory.read_policy import Sanitizer


@dataclass(frozen=True, slots=True)
class ContextPreviewRequest:
    max_items: int = 5
    max_characters: int = 900
    include_text: bool = False


@dataclass(frozen=True, slots=True)
class SanitizedContextItem:
    source: str
    source_reference_hash: str
    category: str
    text: str | None


@dataclass(frozen=True, slots=True)
class SanitizedContextPreview:
    executed: bool
    items: tuple[SanitizedContextItem, ...] = ()
    context_text: str | None = None
    included_count: int = 0
    excluded_count: int = 0
    total_characters: int = 0


class ContextBrokerPreview:
    """Apply future context rules without contacting providers or repositories."""

    def __init__(self, sanitizer: Sanitizer, *, enabled: bool = False) -> None:
        self._sanitizer = sanitizer
        self.enabled = bool(enabled)

    def build_preview(
        self,
        request: ContextPreviewRequest,
        approved_scopes: tuple[MemoryViewCategory, ...],
        candidates: Sequence[MemoryRecordView],
    ) -> SanitizedContextPreview:
        if not self.enabled:
            return SanitizedContextPreview(False)
        max_items = max(1, min(int(request.max_items), 10))
        max_characters = max(1, min(int(request.max_characters), 4000))
        items: list[SanitizedContextItem] = []
        lines: list[str] = []
        used = 0
        excluded = 0
        for candidate in candidates:
            if not self._eligible(candidate, approved_scopes):
                excluded += 1
                continue
            sanitized = self._sanitizer.sanitize(candidate.content)
            if sanitized != candidate.content or not sanitized.strip():
                excluded += 1
                continue
            line = f"- {candidate.category.value}: {sanitized}"
            if len(items) >= max_items or used + len(line) > max_characters:
                excluded += 1
                continue
            reference_hash = hashlib.sha256(
                f"{candidate.source.value}:{candidate.source_record_id}".encode("utf-8")
            ).hexdigest()[:12]
            items.append(
                SanitizedContextItem(
                    candidate.source.value,
                    reference_hash,
                    candidate.category.value,
                    sanitized if request.include_text else None,
                )
            )
            lines.append(line)
            used += len(line)
        context_text = "\n".join(lines) if request.include_text else None
        return SanitizedContextPreview(True, tuple(items), context_text, len(items), excluded, used)

    @staticmethod
    def _eligible(
        candidate: MemoryRecordView,
        approved_scopes: tuple[MemoryViewCategory, ...],
    ) -> bool:
        return (
            (not approved_scopes or candidate.category in approved_scopes)
            and candidate.consent_status is ConsentStatus.APPROVED
            and candidate.sensitivity is SensitivityLevel.NORMAL
            and candidate.status in {None, MemoryStatus.ACTIVE}
        )


__all__ = [
    "ContextBrokerPreview",
    "ContextPreviewRequest",
    "SanitizedContextItem",
    "SanitizedContextPreview",
]
