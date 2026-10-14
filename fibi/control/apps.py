"""Compatibility helpers that delegate app effects to the native action path."""

from __future__ import annotations

from collections.abc import Callable

from fibi.engines.types import ActionIntent, DesktopActionResult


def _execute(name: str, execute_action: Callable[[ActionIntent], DesktopActionResult] | None) -> str:
    if execute_action is None:
        return "Open applications through Fibi's permission-checked action interface."
    intent = ActionIntent("open_app", target=str(name), raw_text=f"open {name}")
    result = execute_action(intent)
    return result.message


def open_app(name: str, *, execute_action: Callable[[ActionIntent], DesktopActionResult] | None = None) -> str:
    """Open a known or explicitly registered app through the safe executor."""

    return _execute(name, execute_action)


def close_app(name: str) -> str:
    """Closing processes is intentionally outside the native action scope."""

    return f"Closing {name} is not supported by Fibi's safe action path."
