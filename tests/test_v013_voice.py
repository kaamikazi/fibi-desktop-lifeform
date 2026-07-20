"""Pytest wrapper for the v0.13 voice smoke suite."""

from __future__ import annotations

from tests.smoke_v013_voice import run


def test_v013_voice() -> None:
    run()


