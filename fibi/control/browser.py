"""Compatibility browser helper using the native URL allowlist."""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import ActionIntent, DesktopActionResult


def search(query: str, *, execute_action: Callable[[ActionIntent], DesktopActionResult] | None = None) -> str:
    if execute_action is None:
        return "Search through Fibi's permission-checked action interface."
    intent = ActionIntent("web_search", query=str(query), raw_text=f"search for {query}")
    result = execute_action(intent)
    return result.message
