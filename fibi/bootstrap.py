"""Startup dependency checks for the project-root Fibi launcher.

Fibi is a local-first desktop app, so startup should never install packages
without the user's explicit request. This module keeps the dependency check
small, testable, and safe.
"""

from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

LOGGER = logging.getLogger(__name__)

DESKTOP_IMPORTS: Mapping[str, str] = {
    "PyQt6": "PyQt6",
}


@dataclass(frozen=True)
class DependencyStatus:
    """Result of checking imports needed before the UI can start."""

    missing_packages: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_packages


def check_imports(required_imports: Mapping[str, str] = DESKTOP_IMPORTS) -> DependencyStatus:
    """Return the packages whose import modules are unavailable."""

    missing: list[str] = []
    for package_name, import_name in required_imports.items():
        if importlib.util.find_spec(import_name) is None:
            missing.append(package_name)
    return DependencyStatus(tuple(missing))


def format_dependency_help(status: DependencyStatus, requirements_path: Path) -> str:
    """Build a human-friendly setup message for missing desktop packages."""

    missing = ", ".join(status.missing_packages)
    return (
        f"Fibi is missing required desktop dependencies: {missing}\n\n"
        "Install them from the project root with:\n"
        f"    {Path(sys.executable).name} -m pip install -r \"{requirements_path}\"\n\n"
        "Or let this launcher run that exact install command once with:\n"
        f"    {Path(sys.executable).name} app.py --install-deps\n"
    )


def install_requirements(requirements_path: Path, extra_args: Sequence[str] | None = None) -> int:
    """Install requirements only after the user passes ``--install-deps``."""

    if not requirements_path.exists():
        LOGGER.error("requirements.txt not found at %s", requirements_path)
        print(f"requirements.txt not found: {requirements_path}")
        return 1

    command = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    if extra_args:
        command.extend(extra_args)

    LOGGER.info("Installing Fibi dependencies from %s", requirements_path)
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)
