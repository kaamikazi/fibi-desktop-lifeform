"""Explicit Stage 2 memory comparison command; synthetic mode only."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from fibi.memory.comparison_dataset import run_synthetic_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run content-free Fibi memory comparison diagnostics.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true", help="Run the committed fictional dataset.")
    mode.add_argument("--local-data", action="store_true", help="Request local-data comparison (currently blocked).")
    parser.add_argument("--confirm-local-read", action="store_true", help="Confirm an explicit local read request.")
    parser.add_argument("--no-save", action="store_true", help="Assert that no report should be persisted.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.local_data:
        category = (
            "local_data_mode_not_implemented"
            if args.confirm_local_read
            else "local_data_confirmation_required"
        )
        print(json.dumps({"schema_version": "fibi.memory-comparison-cli.v1", "executed": False, "error": category}))
        return 2
    suite = run_synthetic_suite()
    print(json.dumps(suite.to_public_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
