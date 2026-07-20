"""Backward-compatible filesystem path helpers for Fibi.

New code should prefer :mod:`fibi.runtime_paths`. This module remains as the
stable API used by older engines and now delegates to the packaged-aware path
resolver.
"""

from __future__ import annotations

from pathlib import Path

from fibi.runtime_paths import project_root, user_data_dir

PROJECT_ROOT = project_root()


def data_dir() -> Path:
    return user_data_dir()


def data_path(name: str) -> Path:
    return data_dir() / name
