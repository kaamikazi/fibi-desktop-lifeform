"""Project workspace router boundary."""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import FibiResponse, LocalCommandResult


class ProjectRouter:
    """Wrap project commands and edit-intent detection."""

    def __init__(
        self,
        command_handler: Callable[[str, str], LocalCommandResult],
        edit_intent_handler: Callable[[str], FibiResponse | None],
        patch_command_handler: Callable[[str, str], LocalCommandResult] | None = None,
        check_command_handler: Callable[[str, str], LocalCommandResult] | None = None,
        check_intent_handler: Callable[[str], FibiResponse | None] | None = None,
    ) -> None:
        self._command_handler = command_handler
        self._edit_intent_handler = edit_intent_handler
        self._patch_command_handler = patch_command_handler
        self._check_command_handler = check_command_handler
        self._check_intent_handler = check_intent_handler

    def route_command(self, text: str, lowered: str) -> LocalCommandResult:
        return self._command_handler(text, lowered)

    def route_patch_command(self, text: str, lowered: str) -> LocalCommandResult:
        if self._patch_command_handler is None:
            return LocalCommandResult(False)
        return self._patch_command_handler(text, lowered)

    def route_check_command(self, text: str, lowered: str) -> LocalCommandResult:
        if self._check_command_handler is None:
            return LocalCommandResult(False)
        return self._check_command_handler(text, lowered)

    def maybe_handle_edit_intent(self, text: str) -> FibiResponse | None:
        return self._edit_intent_handler(text)

    def maybe_handle_check_intent(self, text: str) -> FibiResponse | None:
        if self._check_intent_handler is None:
            return None
        return self._check_intent_handler(text)
