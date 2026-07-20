"""Temporary user-provided context for Fibi v0.14."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from datetime import datetime, timedelta

from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import ContextItem, ContextMemoryDecision, ContextSession, ContextSummary

CONTEXT_SOURCES = {
    "pasted_text",
    "manual_selected_text",
    "dropped_file",
    "manual_file_open",
    "voice_transcript",
    "action_result",
    "browser_page_text",
    "future_screen_reading_disabled",
}


class ContextEngine:
    """Hold recent context locally for the current conversation."""

    def __init__(self, sanitizer: SecretSanitizer | None = None, ttl_minutes: int = 90) -> None:
        self.sanitizer = sanitizer or SecretSanitizer()
        self.ttl_minutes = ttl_minutes
        self._items: list[ContextItem] = []
        self.active_context_id: str | None = None

    def add_text(
        self,
        text: str,
        source: str = "pasted_text",
        title: str = "pasted text",
        mime_type: str = "text/plain",
        file_path: str | None = None,
        user_initiated: bool = True,
        can_remember: bool = True,
    ) -> ContextItem:
        self.expire_old()
        now = datetime.now().astimezone()
        safe_source = source if source in CONTEXT_SOURCES else "pasted_text"
        preview = self.sanitizer.sanitize(text)[:500]
        item = ContextItem(
            context_id=str(uuid.uuid4())[:12],
            source=safe_source,
            title=title.strip()[:120] or "context crumb",
            content_preview=preview,
            content_text=text,
            mime_type=mime_type,
            file_path=file_path,
            created_at=now.isoformat(timespec="seconds"),
            expires_at=(now + timedelta(minutes=self.ttl_minutes)).isoformat(timespec="seconds"),
            token_estimate=max(1, len(text) // 4),
            user_initiated=user_initiated,
            can_remember=can_remember,
            remembered=False,
            sensitivity_hint=self.sanitizer.sensitivity_hint(text),
            error=None,
        )
        self._items.append(item)
        self.active_context_id = item.context_id
        return item

    def session(self) -> ContextSession:
        self.expire_old()
        return ContextSession(list(self._items), self.active_context_id)

    def last(self) -> ContextItem | None:
        self.expire_old()
        return self._items[-1] if self._items else None

    def clear(self) -> int:
        count = len(self._items)
        self._items.clear()
        self.active_context_id = None
        return count

    def forget_last(self) -> bool:
        if not self._items:
            return False
        removed = self._items.pop()
        if self.active_context_id == removed.context_id:
            self.active_context_id = self._items[-1].context_id if self._items else None
        return True

    def remember_last(self) -> ContextMemoryDecision:
        item = self.last()
        if item is None:
            return ContextMemoryDecision(False, "", "no context")
        summary = self.local_summary(item).summary
        self._items[-1] = replace(item, remembered=True)
        return ContextMemoryDecision(True, summary, "user confirmed")

    def local_summary(self, item: ContextItem | None = None) -> ContextSummary:
        selected = item or self.last()
        if selected is None:
            return ContextSummary("", "no context", "no context crumb loaded.", 0)
        sanitized = self.sanitizer.sanitize(selected.content_text)
        lines = [line.strip() for line in sanitized.splitlines() if line.strip()]
        first_lines = " ".join(lines[:8]) if lines else sanitized[:700]
        summary = first_lines[:1200] or selected.content_preview
        return ContextSummary(
            selected.context_id,
            selected.title,
            summary,
            max(1, len(summary) // 4),
            selected.sensitivity_hint,
        )

    def model_context(self, max_chars: int = 3500) -> str:
        item = self.last()
        if item is None:
            return ""
        sanitized = self.sanitizer.sanitize(item.content_text)
        return (
            f"User-provided context ({item.source}, title: {item.title}). "
            "Use only because the user handed it to Fibi. "
            f"Content:\n{sanitized[:max_chars]}"
        )

    def should_use_for(self, user_message: str) -> bool:
        if self.last() is None:
            return False
        lowered = user_message.lower()
        triggers = (
            "this",
            "it",
            "context",
            "file",
            "code",
            "summarize",
            "explain",
            "find bug",
            "what does",
            "remember this",
        )
        return any(trigger in lowered for trigger in triggers)

    def expire_old(self) -> None:
        now = datetime.now().astimezone()
        kept = []
        for item in self._items:
            try:
                expires = datetime.fromisoformat(item.expires_at)
            except ValueError:
                continue
            if expires > now:
                kept.append(item)
        self._items = kept[-12:]
        if self.active_context_id and not any(item.context_id == self.active_context_id for item in self._items):
            self.active_context_id = self._items[-1].context_id if self._items else None

    @staticmethod
    def looks_like_context(text: str) -> bool:
        if len(text) > 500:
            return True
        if "```" in text:
            return True
        if text.count("\n") >= 8:
            return True
        lowered = text.lower()
        if "traceback (most recent call last)" in lowered or "exception" in lowered and "\n" in text:
            return True
        return False

    @staticmethod
    def has_question_or_task(text: str) -> bool:
        lowered = text.lower()
        return "?" in text or any(word in lowered for word in ("explain", "summarize", "find bug", "what does", "why", "how"))
