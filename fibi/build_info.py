"""Build metadata exposed to Fibi commands and release reports."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime

from fibi.runtime_paths import is_packaged

APP_VERSION = "0.30.0"
BUILD_DATE = os.getenv("FIBI_BUILD_DATE", datetime.now().astimezone().isoformat(timespec="seconds"))
BUILD_MODE = os.getenv("FIBI_BUILD_MODE", "local-dev")
GIT_COMMIT = os.getenv("FIBI_GIT_COMMIT", "")
PACKAGED = is_packaged()


def git_commit() -> str:
    """Return a short git commit if available without making startup fragile."""

    if GIT_COMMIT:
        return GIT_COMMIT
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def build_summary() -> dict[str, object]:
    return {
        "app_version": APP_VERSION,
        "build_date": BUILD_DATE,
        "build_mode": BUILD_MODE,
        "git_commit": git_commit(),
        "packaged": PACKAGED,
    }
