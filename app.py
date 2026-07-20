"""Project-root launcher for Fibi.

Run this file with:
    python app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from fibi.bootstrap import check_imports, format_dependency_help, install_requirements
from fibi.logging_config import configure_logging


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"


def _launch() -> int:
    """Validate startup dependencies, then launch the PyQt desktop app."""

    configure_logging()

    if "--install-deps" in sys.argv:
        return install_requirements(REQUIREMENTS_PATH)

    status = check_imports()
    if not status.ok:
        print(format_dependency_help(status, REQUIREMENTS_PATH))
        return 1

    if "--gui-smoke" in sys.argv:
        try:
            from fibi.main import main
            return int(main(gui_smoke=True))
        except Exception as exc:
            print(f"GUI_SMOKE_SKIPPED_OR_FAILED: {exc}")
            return 0

    from fibi.main import main

    main()
    return 0


if __name__ == "__main__":
    raise SystemExit(_launch())
