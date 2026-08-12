"""Architecture and privacy guards for the backup foundation."""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

from fibi.memory.boundaries import scan_memory_boundaries
from fibi.memory_backup import discovery, rehearsal, safety, service, sqlite_snapshot, verifier
from fibi.memory_backup.models import BackupAssetManifest, BackupManifest
from fibi.tools import memory_backup

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_repository_memory_boundaries_cover_backup_services() -> None:
    assert scan_memory_boundaries(PROJECT_ROOT) == []


def test_backup_modules_have_no_provider_ui_network_or_environment_dependency() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (discovery, rehearsal, safety, service, sqlite_snapshot, verifier, memory_backup)
    ).casefold()
    forbidden = (
        "fibi.providers",
        "fibi.services.providers",
        "fibi.ui",
        "requests",
        "httpx",
        "import socket",
        "import urllib",
        "cloud-upload",
        ".env",
    )
    assert all(value not in source for value in forbidden)


def test_normal_runtime_does_not_import_or_construct_backup_services() -> None:
    from fibi import main
    from fibi.app import composition, runtime
    from fibi.engines import core

    for module in (main, composition, runtime, core):
        source = inspect.getsource(module)
        assert "fibi.memory_backup" not in source
        assert "MemoryBackupService" not in source
        assert "RestoreRehearsalService" not in source


def test_no_stage3_importer_or_live_restore_surface_exists() -> None:
    forbidden_paths = (
        PROJECT_ROOT / "fibi" / "memory" / "importer.py",
        PROJECT_ROOT / "fibi" / "memory" / "migration_importer.py",
        PROJECT_ROOT / "fibi" / "memory_backup" / "importer.py",
    )
    assert all(not path.exists() for path in forbidden_paths)
    choices = memory_backup.build_parser()._subparsers._group_actions[0].choices  # type: ignore[attr-defined]
    assert "restore" not in choices
    assert "restore-live" not in choices


def test_manifest_contract_has_no_raw_path_or_payload_fields() -> None:
    fields = {field.name for field in dataclasses.fields(BackupManifest)}
    asset_fields = {field.name for field in dataclasses.fields(BackupAssetManifest)}
    forbidden = {
        "source_path",
        "absolute_path",
        "database_path",
        "memory_content",
        "rows",
        "prompt",
        "credentials",
    }
    assert forbidden.isdisjoint(fields | asset_fields)
    assert "content" not in json.dumps(sorted(fields | asset_fields))
