"""Compatibility entry point for the Stage 2 synthetic comparison suite."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.tools.memory_compare import main as comparison_main


def main() -> int:
    return comparison_main(["--synthetic", "--no-save"])


if __name__ == "__main__":
    raise SystemExit(main())
