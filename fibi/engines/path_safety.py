"""Small filesystem safety helpers shared by native project actions."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def is_reparse_point(path: str | Path) -> bool:
    """Return whether *path* is a symlink, junction, or Windows reparse point.

    Missing paths are allowed here so callers can validate a new child beneath
    an already-approved directory. Permission and other filesystem failures
    fail closed.
    """

    candidate = Path(path).expanduser()
    try:
        if candidate.is_symlink() or bool(getattr(candidate, "is_junction", lambda: False)()):
            return True
        attributes = int(getattr(os.lstat(candidate), "st_file_attributes", 0))
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        return True
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))
    return bool(attributes & reparse_flag)


def contains_reparse_point(path: str | Path) -> bool:
    """Check every existing component in a path for link/reparse escapes."""

    current = Path(path).expanduser()
    while True:
        if is_reparse_point(current):
            return True
        if current == current.parent:
            return False
        current = current.parent


def canonical_path(path: str | Path) -> Path | None:
    """Canonicalize a safe path without following a known link chain."""

    candidate = Path(path).expanduser()
    if contains_reparse_point(candidate):
        return None
    try:
        return candidate.resolve()
    except (OSError, RuntimeError):
        return None


def is_within(root: str | Path, candidate: str | Path) -> bool:
    """Return whether a canonical candidate is inside an approved root."""

    safe_root = canonical_path(root)
    safe_candidate = canonical_path(candidate)
    if safe_root is None or safe_candidate is None:
        return False
    try:
        safe_candidate.relative_to(safe_root)
    except ValueError:
        return False
    return True
