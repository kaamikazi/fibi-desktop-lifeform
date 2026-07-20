"""Slash/local command router.

This router is deliberately thin in v0.17. It gives FibiCore a stable boundary
while existing command handlers are moved over gradually.
"""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import LocalCommandResult


class CommandRouter:
    """Route local slash commands to the current command handler."""

    def __init__(self, command_handler: Callable[[str], LocalCommandResult]) -> None:
        self._command_handler = command_handler

    def route(self, text: str) -> LocalCommandResult:
        return self._command_handler(text)
