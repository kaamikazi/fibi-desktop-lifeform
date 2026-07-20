"""Pytest wrapper for optional RVC voice skin smoke tests."""

from __future__ import annotations

from tests.smoke_v016_voice_skin import run


def test_v016_voice_skin() -> None:
    run()


