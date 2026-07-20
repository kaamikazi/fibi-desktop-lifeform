"""Context command and capture router boundary."""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import FibiResponse, LocalCommandResult


class ContextRouter:
    """Wrap context commands while FibiCore is being decomposed."""

    def __init__(
        self,
        command_handler: Callable[[str, str], LocalCommandResult],
        capture_handler: Callable[[str], FibiResponse | None],
    ) -> None:
        self._command_handler = command_handler
        self._capture_handler = capture_handler

    def route_command(self, text: str, lowered: str) -> LocalCommandResult:
        return self._command_handler(text, lowered)

    def maybe_capture(self, text: str) -> FibiResponse | None:
        return self._capture_handler(text)
