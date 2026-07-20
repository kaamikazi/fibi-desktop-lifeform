"""Unit tests for Fibi's safe startup bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.bootstrap import DependencyStatus, check_imports, format_dependency_help


def test_check_imports_reports_missing_package() -> None:
    status = check_imports({"definitely-missing-package": "definitely_missing_fibi_import"})

    assert not status.ok
    assert status.missing_packages == ("definitely-missing-package",)


def test_check_imports_accepts_existing_module() -> None:
    status = check_imports({"pathlib": "pathlib"})

    assert status.ok
    assert status.missing_packages == ()


def test_dependency_help_is_explicit_and_non_automatic(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    message = format_dependency_help(DependencyStatus(("PyQt6",)), requirements)

    assert "PyQt6" in message
    assert "pip install -r" in message
    assert "--install-deps" in message
    assert str(requirements) in message


