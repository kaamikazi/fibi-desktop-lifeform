"""Stable expression transitions independent of PyQt timers."""

from __future__ import annotations

import time

from fibi.engines.types import ExpressionState

VALID_EXPRESSIONS = {"idle", "happy", "thinking", "talking", "sleepy", "angry"}


class ExpressionController:
    """Prevent flicker and return temporary reactions to persistent mood."""

    def __init__(self, initial: str = "idle", minimum_duration_ms: int = 500) -> None:
        normalized = self._normalize(initial)
        self.state = ExpressionState(normalized, normalized, None, minimum_duration_ms, None)
        self._last_changed_ms = 0

    def set_persistent(self, expression: str, now_ms: int | None = None, force: bool = False) -> str:
        current = self._now_ms() if now_ms is None else now_ms
        normalized = self._normalize(expression)
        self.state.persistent_expression = normalized
        if self.state.temporary_expression is None:
            self._apply(normalized, current, force)
        return self.state.current_expression

    def show_temporary(self, expression: str, duration_ms: int, now_ms: int | None = None) -> str:
        current = self._now_ms() if now_ms is None else now_ms
        normalized = self._normalize(expression)
        self.state.temporary_expression = normalized
        self.state.temporary_until_ms = current + max(self.state.minimum_duration_ms, duration_ms)
        self._apply(normalized, current, True)
        return self.state.current_expression

    def current(self, now_ms: int | None = None) -> str:
        current = self._now_ms() if now_ms is None else now_ms
        until = self.state.temporary_until_ms
        if self.state.temporary_expression and until is not None and current >= until:
            self.state.temporary_expression = None
            self.state.temporary_until_ms = None
            self._apply(self.state.persistent_expression, current, True)
        return self.state.current_expression

    def clear_temporary(self, now_ms: int | None = None) -> str:
        current = self._now_ms() if now_ms is None else now_ms
        self.state.temporary_expression = None
        self.state.temporary_until_ms = None
        self._apply(self.state.persistent_expression, current, True)
        return self.state.current_expression

    def _apply(self, expression: str, now_ms: int, force: bool) -> None:
        if force or now_ms - self._last_changed_ms >= self.state.minimum_duration_ms:
            self.state.current_expression = expression
            self._last_changed_ms = now_ms

    @staticmethod
    def _normalize(expression: str) -> str:
        return expression if expression in VALID_EXPRESSIONS else "idle"

    @staticmethod
    def _now_ms() -> int:
        return int(time.monotonic() * 1000)
