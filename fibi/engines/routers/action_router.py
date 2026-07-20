"""Action intent router for safe local desktop actions."""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import FibiResponse


class ActionRouter:
    """Keep action confirmation and execution ahead of model routing."""

    def __init__(
        self,
        confirmation_handler: Callable[[str], FibiResponse | None],
        intent_handler: Callable[[str], FibiResponse | None],
    ) -> None:
        self._confirmation_handler = confirmation_handler
        self._intent_handler = intent_handler

    def handle_pending_confirmation(self, text: str) -> FibiResponse | None:
        return self._confirmation_handler(text)

    def route(self, text: str) -> FibiResponse | None:
        return self._intent_handler(text)
