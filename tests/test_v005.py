"""Pytest entry point for the dependency-free v0.05 smoke suite."""

from tests.smoke_v005 import main


def test_v005_smoke() -> None:
    main()


