"""Smoke tests for Fibi v0.17 core decomposition."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.legacy_memory_adapter import LegacyMemoryAdapter
from fibi.engines.migration_manager import MigrationManager
from fibi.engines.routers import (
    ActionRouter,
    ChatRouter,
    CommandRouter,
    ContextRouter,
    MemoryRouter,
    ProjectRouter,
    ResponsePipeline,
    VoiceRouter,
)
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from tests.smoke_v012_actions import make_core
from tools.migrate_legacy_memory_to_rag import migrate


def run() -> None:
    assert CommandRouter
    assert ActionRouter
    assert ChatRouter
    assert ContextRouter
    assert MemoryRouter
    assert ProjectRouter
    assert ResponsePipeline
    assert VoiceRouter

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root, opened, launched)

        assert isinstance(core.command_router, CommandRouter)
        assert isinstance(core.action_router, ActionRouter)
        assert isinstance(core.chat_router, ChatRouter)
        assert isinstance(core.memory_router, MemoryRouter)

        route_last = core.respond("/route last")
        assert route_last.model_used == "local-command"
        assert "route:" in route_last.display_text
        assert model.calls == 0

        for message in ("heyyyy", "are you there?"):
            before = model.calls
            start = time.perf_counter()
            response = core.respond(message)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 300, f"{message!r} was too slow: {elapsed_ms:.1f} ms"
            assert model.calls == before
            assert response.model_used in {"local-greeting", "local-micro-brain"}
            assert "Ollama is unavailable" not in response.display_text

        for message in ("how are you?", "what are you doing?"):
            before = model.calls
            response = core.respond(message)
            assert model.calls == before + 1
            assert response.model_used == "local-fallback"

        date = core.respond("what's the date")
        assert date.model_used == "local-action"
        assert model.calls == 2

        context = core.respond("/context")
        assert context.model_used == "local-command"
        project = core.respond("/project list")
        assert project.model_used == "local-command"

        memory = core.memory_router.rag_memory.remember_project(
            "User is building KamikazeOS.",
            source="test",
            source_id="v017:test:project",
        )
        assert memory.id is not None
        relevant = core._relevant_memories("KamikazeOS")
        assert any("KamikazeOS" in item.content for item in relevant)

        adapter = LegacyMemoryAdapter(
            RAGMemoryServiceFacade(database_path=root / "adapter_memory.db"),
        )
        legacy_id = adapter.save("fact", "User likes tiny desktop creatures.", importance=0.7)
        assert legacy_id is not None
        assert adapter.retrieve("desktop creatures", limit=1)

        migration_db = root / "migration_memory.db"
        legacy_core, _, _ = make_core(root / "migration_core", [], [])
        legacy_core.memory.save("fact", "Legacy memory crumb.", source="legacy-test")
        report = migrate(legacy_core.memory.database_path, apply=False)
        assert report["seen"] >= 1
        assert report["apply"] is False
        assert Path(report["report_path"]).exists()

        migrations = MigrationManager(migration_db, namespace="v017-test")
        applied = migrations.apply({"001": lambda connection: connection.execute("CREATE TABLE IF NOT EXISTS tiny(id INTEGER)")})
        assert applied == ["001"]
        assert migrations.apply({"001": lambda connection: connection.execute("CREATE TABLE IF NOT EXISTS tiny(id INTEGER)")}) == []

    print("Fibi v0.17 core decomposition smoke tests passed.")


if __name__ == "__main__":
    run()


