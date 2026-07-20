"""Pytest wrapper for the v0.12 manual action smoke suite."""

from __future__ import annotations

from tests.smoke_v012_actions import run


def test_v012_actions() -> None:
    run()


