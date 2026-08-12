"""Isolated restore rehearsal, CLI privacy, and live-restore guards."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from fibi.memory_backup.faults import BackupFaultPoint, DeterministicFaultInjector
from fibi.memory_backup.models import RestoreRehearsalRequest
from fibi.memory_backup.rehearsal import RestoreRehearsalService
from fibi.tools.memory_backup import build_parser, main
from tests.memory_backup_test_support import (
    FIXED_TIME,
    SYNTHETIC_SENTINEL,
    create_backup,
    create_synthetic_data,
    tree_hashes,
)


def _backup(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "active data"
    create_synthetic_data(data)
    result = create_backup(data, tmp_path / "private backups")
    assert result.success is True and result.bundle_path is not None
    return data, result.bundle_path


def test_restore_rehearsal_is_isolated_structurally_equivalent_and_evidenced(tmp_path: Path) -> None:
    active, bundle = _backup(tmp_path)
    active_before = tree_hashes(active)
    backup_before = tree_hashes(bundle)
    destination = tmp_path / ("restore destination with spaces " + "\u2603")
    result = RestoreRehearsalService(
        repository_root=tmp_path / "repository",
        id_factory=lambda: "restore123",
        clock=lambda: FIXED_TIME,
    ).rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            destination,
            confirm_private_output=True,
            cleanup=False,
        )
    )

    assert result.success is True
    assert result.structurally_equivalent is True
    assert result.evidence_written is True
    assert result.rehearsal_path is not None
    restored_database = result.rehearsal_path / "databases" / "memory.sqlite"
    with sqlite3.connect(restored_database) as connection:
        assert connection.execute("SELECT content FROM memories").fetchone()[0] == SYNTHETIC_SENTINEL
    evidence = json.loads((result.rehearsal_path / "rehearsal_evidence.json").read_text(encoding="utf-8"))
    assert evidence["live_restore_performed"] is False
    assert evidence["structurally_equivalent"] is True
    assert SYNTHETIC_SENTINEL not in json.dumps(evidence)
    assert str(tmp_path) not in json.dumps(evidence)
    assert tree_hashes(active) == active_before
    assert tree_hashes(bundle) == backup_before


def test_cleanup_removes_only_created_rehearsal(tmp_path: Path) -> None:
    active, bundle = _backup(tmp_path)
    destination = tmp_path / "rehearsals"
    unrelated = destination / "keep.txt"
    destination.mkdir()
    unrelated.write_text("keep", encoding="utf-8")

    result = RestoreRehearsalService(repository_root=tmp_path / "repo").rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            destination,
            confirm_private_output=True,
            cleanup=True,
        )
    )

    assert result.success is True
    assert result.cleaned_up is True
    assert result.rehearsal_path is None
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert not list(destination.glob("fibi-restore-rehearsal-*"))


@pytest.mark.parametrize("relation", ["active", "active_parent", "active_child", "bundle", "repository"])
def test_live_or_unsafe_rehearsal_destinations_are_rejected(tmp_path: Path, relation: str) -> None:
    active, bundle = _backup(tmp_path)
    repository = tmp_path / "repository"
    repository.mkdir()
    destinations = {
        "active": active,
        "active_parent": active.parent,
        "active_child": active / "restore",
        "bundle": bundle,
        "repository": repository / "private restore",
    }
    result = RestoreRehearsalService(repository_root=repository).rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            destinations[relation],
            confirm_private_output=True,
            cleanup=False,
        )
    )
    assert result.success is False
    assert "destination_rejected" in result.errors[0].category


def test_resolved_alias_of_active_data_is_rejected(tmp_path: Path) -> None:
    active, bundle = _backup(tmp_path)
    aliased = active.parent / "unused" / ".." / active.name
    result = RestoreRehearsalService(repository_root=tmp_path / "repo").rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            aliased,
            confirm_private_output=True,
            cleanup=False,
        )
    )
    assert result.success is False
    assert result.errors[0].category == "active_data_destination_rejected"


def test_existing_rehearsal_staging_collision_is_never_removed(tmp_path: Path) -> None:
    active, bundle = _backup(tmp_path)
    destination = tmp_path / "rehearsals"
    existing = destination / ".fibi-restore-rehearsal-staging-restore123"
    existing.mkdir(parents=True)
    marker = existing / "belongs-to-someone-else.txt"
    marker.write_text("preserve", encoding="utf-8")

    result = RestoreRehearsalService(
        repository_root=tmp_path / "repo",
        id_factory=lambda: "restore123",
    ).rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            destination,
            confirm_private_output=True,
            cleanup=False,
        )
    )

    assert result.success is False
    assert result.errors[0].category == "rehearsal_destination_collision"
    assert marker.read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize(
    "point",
    [
        BackupFaultPoint.REHEARSAL_DESTINATION_FAILED,
        BackupFaultPoint.RESTORATION_INTERRUPTED,
        BackupFaultPoint.PROCESS_CANCELLED,
    ],
)
def test_rehearsal_faults_leave_backup_and_active_data_unchanged(
    tmp_path: Path,
    point: BackupFaultPoint,
) -> None:
    active, bundle = _backup(tmp_path)
    active_before = tree_hashes(active)
    backup_before = tree_hashes(bundle)
    destination = tmp_path / point.value
    result = RestoreRehearsalService(
        repository_root=tmp_path / "repo",
        fault_injector=DeterministicFaultInjector(point),
    ).rehearse(
        RestoreRehearsalRequest(
            bundle,
            active,
            destination,
            confirm_private_output=True,
            cleanup=False,
        )
    )
    assert result.success is False
    if point is BackupFaultPoint.PROCESS_CANCELLED:
        assert result.status == "cancelled"
    assert tree_hashes(active) == active_before
    assert tree_hashes(bundle) == backup_before
    assert not list(destination.glob("fibi-restore-rehearsal-*")) if destination.exists() else True


def test_cli_is_explicit_content_free_and_has_no_live_restore_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = tmp_path / "cli data"
    create_synthetic_data(data)
    output = tmp_path / "cli backups"
    monkeypatch.setenv("FIBI_DATA_DIR", str(data))

    assert main(["create", "--output", str(output)]) == 2
    refused = json.loads(capsys.readouterr().out)
    assert refused["errors"][0]["category"] == "private_output_confirmation_required"

    assert main(["create", "--output", str(output), "--confirm-private-output"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["success"] is True
    rendered = json.dumps(created)
    assert SYNTHETIC_SENTINEL not in rendered
    assert str(tmp_path) not in rendered

    commands = build_parser()._subparsers._group_actions[0].choices  # type: ignore[attr-defined]
    assert set(commands) == {"create", "verify", "inspect", "rehearse-restore"}
    assert "restore" not in commands


def test_rehearsal_requires_private_output_confirmation(tmp_path: Path) -> None:
    active, bundle = _backup(tmp_path)
    result = RestoreRehearsalService(repository_root=tmp_path / "repo").rehearse(
        RestoreRehearsalRequest(bundle, active, tmp_path / "restore")
    )
    assert result.errors[0].category == "private_output_confirmation_required"
