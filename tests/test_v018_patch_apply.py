"""Pytest wrapper for v0.18 safe patch apply smoke tests."""

from __future__ import annotations

from tests.smoke_v018_patch_apply import run


def test_v018_patch_apply_smoke() -> None:
    run()


