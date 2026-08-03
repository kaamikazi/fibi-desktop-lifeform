"""Fail when provider, UI, or derived-index code bypasses memory boundaries."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.memory.boundaries import scan_memory_boundaries


def main() -> int:
    violations = scan_memory_boundaries(PROJECT_ROOT)
    for violation in violations:
        print(f"{violation.path}:{violation.line}: {violation.rule}: {violation.detail}")
    if violations:
        return 1
    print("MEMORY_BOUNDARIES_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
