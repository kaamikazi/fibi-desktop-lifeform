"""Pytest wrapper for v0.17 core decomposition smoke tests."""

from __future__ import annotations

from tests.smoke_v017_core_decomposition import run


def test_v017_core_decomposition_smoke() -> None:
    run()


