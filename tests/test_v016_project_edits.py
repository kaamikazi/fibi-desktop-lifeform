"""Pytest wrapper for the v0.16 project edit suggestion smoke suite."""

from __future__ import annotations

from tests.smoke_v016_project_edits import run


def test_v016_project_edits() -> None:
    run()


