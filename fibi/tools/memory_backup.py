"""Explicit, privacy-safe CLI for memory backup and restore rehearsal."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from fibi.memory_backup.models import BackupRequest, RestoreRehearsalRequest
from fibi.memory_backup.rehearsal import RestoreRehearsalService
from fibi.memory_backup.service import MemoryBackupService
from fibi.memory_backup.verifier import BackupVerifier
from fibi.runtime_paths import project_root, resolved_user_data_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and verify private local Fibi memory backups.")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a verified private backup bundle.")
    create.add_argument("--output", type=Path)
    create.add_argument("--confirm-private-output", action="store_true")
    create.add_argument("--exclude-migration-support", action="store_true")
    create.add_argument("--full-integrity-check", action="store_true")

    verify = commands.add_parser("verify", help="Verify an existing backup bundle.")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--full-integrity-check", action="store_true")

    inspect = commands.add_parser("inspect", help="Print a content-free backup summary.")
    inspect.add_argument("bundle", type=Path)

    rehearse = commands.add_parser("rehearse-restore", help="Restore only into an isolated rehearsal directory.")
    rehearse.add_argument("bundle", type=Path)
    rehearse.add_argument("--destination", type=Path)
    rehearse.add_argument("--keep", action="store_true")
    rehearse.add_argument("--confirm-private-output", action="store_true")
    rehearse.add_argument("--full-integrity-check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "create":
        data_root = resolved_user_data_dir()
        output = args.output or (data_root / "private_memory_backups")
        result = MemoryBackupService(repository_root=project_root()).create(
            BackupRequest(
                data_root=data_root,
                output_root=output,
                confirm_private_output=args.confirm_private_output,
                include_migration_support=not args.exclude_migration_support,
                full_integrity_check=args.full_integrity_check,
            )
        )
        print(json.dumps(result.to_public_dict(), sort_keys=True))
        return 0 if result.success else 2
    if args.command in {"verify", "inspect"}:
        result = BackupVerifier().verify(
            args.bundle,
            full_integrity_check=bool(getattr(args, "full_integrity_check", False)),
        )
        print(json.dumps(result.to_public_dict(), sort_keys=True))
        return 0 if result.valid else 2
    if args.command == "rehearse-restore":
        result = RestoreRehearsalService(repository_root=project_root()).rehearse(
            RestoreRehearsalRequest(
                backup_bundle=args.bundle,
                active_data_root=resolved_user_data_dir(),
                destination_root=args.destination,
                confirm_private_output=args.confirm_private_output,
                cleanup=not args.keep,
                full_integrity_check=args.full_integrity_check,
            )
        )
        print(json.dumps(result.to_public_dict(), sort_keys=True))
        return 0 if result.success else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
