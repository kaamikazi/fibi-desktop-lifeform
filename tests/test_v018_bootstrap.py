"""Pytest wrapper for the v0.18 startup bootstrap smoke test."""

from __future__ import annotations

from tests.smoke_v018_bootstrap import main


def test_v018_bootstrap_smoke() -> None:
    main()


