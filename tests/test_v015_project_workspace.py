"""Pytest wrapper for the v0.15 project workspace smoke suite."""

from __future__ import annotations

from tests.smoke_v015_project_workspace import run


def test_v015_project_workspace() -> None:
    run()


