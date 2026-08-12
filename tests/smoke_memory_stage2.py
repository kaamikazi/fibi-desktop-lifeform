"""Synthetic smoke check for Memory Migration Stage 2."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.memory.comparison_dataset import run_synthetic_suite


def main() -> None:
    suite = run_synthetic_suite()
    assert suite.synthetic is True
    assert suite.case_count == suite.executed_count == 20
    assert suite.migration_blocker_count == 2
    print("Memory Stage 2 synthetic comparison smoke tests passed.")


if __name__ == "__main__":
    main()
