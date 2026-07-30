"""Regression tests for the lightweight ``fibi.engines`` package boundary."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_isolated(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_lightweight_engine_import_does_not_load_application_graph() -> None:
    result = _run_isolated(
        "import sys\n"
        "import fibi.engines.action_confirmation_engine\n"
        "blocked = (\n"
        "    'fibi.engines.core',\n"
        "    'fibi.engines.nvidia_model_engine',\n"
        "    'fibi.engines.openai_compatible_provider',\n"
        ")\n"
        "assert not [name for name in blocked if name in sys.modules]\n"
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_all_compatibility_exports_still_resolve() -> None:
    result = _run_isolated(
        "import fibi.engines as engines\n"
        "assert 'fibi.engines.core' not in __import__('sys').modules\n"
        "for name in engines.__all__:\n"
        "    value = getattr(engines, name)\n"
        "    assert value.__name__ == name, (name, value)\n"
    )

    assert result.returncode == 0, result.stderr or result.stdout
