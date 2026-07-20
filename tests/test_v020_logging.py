"""Pytest wrapper for the v0.20 logging smoke test."""

from __future__ import annotations

from tests.smoke_v020_logging import run


def test_v020_logging_smoke() -> None:
    run()


