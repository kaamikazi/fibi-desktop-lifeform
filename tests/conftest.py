"""Shared test isolation for Fibi's persisted runtime settings."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_fibi_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Prevent tests from reading or changing the user's provider/voice choices."""

    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "fibi-runtime"))
