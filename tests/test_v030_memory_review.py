"""Tests for Fibi v0.30 Memory Review Center."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
from fibi.engines.types import MemoryDeleteRequest, MemoryEditRequest, MemoryExportRequest
from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path


def test_memory_review_lifecycle(tmp_path: Path) -> None:
    os.environ["FIBI_DATA_DIR"] = str(tmp_path / "data")
    core, model, _ = make_core(tmp_path / "core", [], [])
    memory = core.memory_router.rag_memory.service.add_memory(
        "User is building Fibi memory review.",
        category="project",
        source="test",
        confidence=0.8,
        allow_duplicate=True,
    )

    listed = core.memory_review.list_memories()
    assert any(item.memory_id == memory.id for item in listed)

    results = core.memory_review.search_memories("memory review")
    assert results
    assert results[0].item.memory_id == memory.id

    assert core.memory_review.approve_memory(memory.id).ok
    assert core.memory_review.pin_memory(memory.id).ok
    pinned = core.memory_review.get_memory(memory.id)
    assert pinned and pinned.pinned

    staged = core.memory_review.edit_memory(MemoryEditRequest(memory.id, "User is testing memory review."))
    assert staged.requires_confirmation
    edited = core.memory_review.edit_memory(MemoryEditRequest(memory.id, "User is testing memory review.", True))
    assert edited.ok
    assert "testing memory review" in core.memory_review.get_memory(memory.id).text

    assert core.memory_review.archive_memory(memory.id).ok
    archived = core.memory_review.get_memory(memory.id)
    assert archived and archived.archived
    assert model.calls == 0


def test_memory_delete_export_and_guard(tmp_path: Path) -> None:
    os.environ["FIBI_DATA_DIR"] = str(tmp_path / "data")
    core, _, _ = make_core(tmp_path / "core", [], [])
    safe = core.memory_router.rag_memory.service.add_memory(
        "User likes short sleepy replies.",
        category="fact",
        source="test",
        allow_duplicate=True,
    )
    fake_api_key = "sk-" + "abcdefghijklmnopqrstuvwxyz1234567890"
    secret = core.memory_router.rag_memory.service.add_memory(
        f"API_KEY={fake_api_key}",
        category="fact",
        source="test",
        allow_duplicate=True,
    )

    json_path, md_path = core.memory_review.export_memories(MemoryExportRequest())
    payload = json_path.read_text(encoding="utf-8")
    assert "short sleepy replies" in payload
    assert "API_KEY" not in payload
    assert md_path.exists()

    pending = core.memory_review.delete_memory(MemoryDeleteRequest(memory_id=safe.id))
    assert pending.requires_confirmation
    deleted = core.memory_review.delete_memory(MemoryDeleteRequest(memory_id=safe.id, user_confirmed=True))
    assert deleted.ok
    audit = tmp_path / "data" / "memory" / "memory_deletion_log.jsonl"
    assert audit.exists()
    assert "short sleepy replies" not in audit.read_text(encoding="utf-8")

    guard = SensitiveMemoryGuard()
    assert guard.assess("password=<dummy-test-password>").blocked
    assert guard.assess("I was diagnosed with insomnia").requires_approval
    assert guard.assess("I was diagnosed with insomnia", user_requested=True).allowed
    assert core.memory_review.get_memory(secret.id) is not None


def test_core_memory_commands_and_learning_pause(tmp_path: Path) -> None:
    os.environ["FIBI_DATA_DIR"] = str(tmp_path / "data")
    core, model, _ = make_core(tmp_path / "core", [], [])
    memory = core.memory_router.rag_memory.service.add_memory(
        "User is testing v030 commands.",
        category="project",
        source="test",
        allow_duplicate=True,
    )

    assert "testing v030" in core.respond("/memory search v030").display_text
    assert f"memory {memory.id}" in core.respond(f"/memory show {memory.id}").display_text
    assert "pinned" in core.respond(f"/memory pin {memory.id}").display_text
    assert "edit staged" in core.respond(f"/memory edit {memory.id} User edited v030 memory.").display_text
    assert "edited" in core.respond("memory edit confirm").display_text
    assert "delete staged" in core.respond(f"/memory delete {memory.id}").display_text
    assert "forgot one" in core.respond("memory delete confirm").display_text
    assert model.calls == 0

    before = core.memory_router.rag_memory.health_check().active_memories
    assert "memory paused" in core.respond("/memory learning off").display_text
    core.respond("my name is Pause Test")
    after = core.memory_router.rag_memory.health_check().active_memories
    assert after == before

    assert "memory health" in core.respond("/memory health").display_text
    assert "secrets never stored" in core.respond("/memory safety").display_text


def test_gui_smoke_and_packaged_path() -> None:
    assert release_zip_path().name == "Fibi_Chubi_v0.30.4_windows_beta.zip"
    result = subprocess.run(
        [sys.executable, "app.py", "--gui-smoke"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GUI_SMOKE_OK" in result.stdout
