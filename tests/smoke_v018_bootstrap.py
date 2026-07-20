"""Smoke test for the safe app startup dependency bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.bootstrap import check_imports, format_dependency_help


def main() -> None:
    status = check_imports({"fake-package": "fake_fibi_bootstrap_import"})
    assert not status.ok
    assert status.missing_packages == ("fake-package",)

    message = format_dependency_help(status, PROJECT_ROOT / "requirements.txt")
    assert "fake-package" in message
    assert "--install-deps" in message
    assert "pip install -r" in message

    ok_status = check_imports({"sqlite3": "sqlite3"})
    assert ok_status.ok

    print("Fibi v0.18 bootstrap smoke tests passed.")


if __name__ == "__main__":
    main()


