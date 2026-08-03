"""Safe Stage 0 command for inspecting a future memory migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from fibi.memory.migration import MemoryMigrationPreflight


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect Fibi memory stores without reading memory content or writing data."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Run the read-only preflight (default).")
    mode.add_argument("--apply", action="store_true", help="Unavailable until safe migration stages ship.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.apply:
        print("Memory migration apply mode is blocked; no data was changed.")
        return 2
    report = MemoryMigrationPreflight(args.data_dir).run()
    print(json.dumps(report.to_public_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
