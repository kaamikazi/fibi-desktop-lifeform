"""Print a sanitized, read-only inventory of Fibi memory stores."""

from __future__ import annotations

import argparse
from pathlib import Path

from fibi.memory.inventory import MemoryInventoryScanner
from fibi.paths import data_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Fibi memory structure without reading memory content.")
    parser.add_argument("--data-dir", type=Path, default=data_dir(), help="Fibi data directory to inspect read-only.")
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON metadata.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = MemoryInventoryScanner(args.data_dir).scan()
    if args.json:
        print(report.to_json())
    else:
        print("Fibi memory inventory (content excluded)")
        for store in report.stores:
            state = "present" if store.exists else "missing"
            detail = f", files={store.file_count}" if store.kind == "file_set" else ""
            print(f"- {store.store_id}: {store.path} [{state}{detail}] -> {store.target_owner}")
            for table in store.tables:
                print(f"  table={table.name} rows={table.row_count} columns={len(table.columns)}")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
