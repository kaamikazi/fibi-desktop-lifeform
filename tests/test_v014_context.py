"""Pytest wrapper for the v0.14 context smoke suite."""

from __future__ import annotations

from tests.smoke_v014_context import run


def test_v014_context() -> None:
    run()


