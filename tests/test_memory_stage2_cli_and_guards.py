"""CLI, privacy, and architecture guards for Memory Stage 2."""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

from fibi.memory.boundaries import scan_memory_boundaries
from fibi.memory.comparison_models import MemoryComparisonReport, MemorySourceResult
from fibi.tools.memory_compare import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_data_requires_confirmation_and_remains_unimplemented(capsys) -> None:
    assert main(["--local-data", "--no-save"]) == 2
    refused = json.loads(capsys.readouterr().out)
    assert refused == {
        "schema_version": "fibi.memory-comparison-cli.v1",
        "executed": False,
        "error": "local_data_confirmation_required",
    }

    assert main(["--local-data", "--confirm-local-read", "--no-save"]) == 2
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["error"] == "local_data_mode_not_implemented"


def test_synthetic_cli_writes_stdout_only(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = list(tmp_path.iterdir())

    assert main(["--synthetic", "--no-save"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["synthetic"] is True
    assert payload["case_count"] == 20
    assert list(tmp_path.iterdir()) == before == []


def test_report_contract_has_no_payload_or_identifier_fields() -> None:
    fields = {field.name for field in dataclasses.fields(MemoryComparisonReport)}
    source_fields = {field.name for field in dataclasses.fields(MemorySourceResult)}
    forbidden = {
        "content",
        "query",
        "raw_query",
        "source_record_id",
        "database_path",
        "file_path",
        "prompt",
        "embedding",
        "fingerprint",
        "content_hash",
        "exception",
    }

    assert forbidden.isdisjoint(fields | source_fields)


def test_comparison_modules_have_no_provider_ui_or_storage_mutation_dependency() -> None:
    from fibi.memory import comparison_dataset, comparison_models, shadow_comparison
    from fibi.tools import memory_compare

    combined = "\n".join(inspect.getsource(module) for module in (
        comparison_dataset,
        comparison_models,
        shadow_comparison,
        memory_compare,
    ))
    assert "fibi.services.providers" not in combined
    assert "fibi.providers" not in combined
    assert "fibi.ui" not in combined
    assert "sqlite3" not in combined


def test_repository_memory_boundaries_pass() -> None:
    assert scan_memory_boundaries(PROJECT_ROOT) == []
