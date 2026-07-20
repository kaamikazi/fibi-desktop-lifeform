"""Pytest entry point for the dependency-free v0.06 smoke suite."""

from tests.smoke_v006 import main


def test_v006_smoke() -> None:
    main()


