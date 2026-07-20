"""Direct smoke tests for Fibi v0.08 memory care and privacy controls."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.core import FibiCore
from fibi.engines.inner_life_engine import InnerLifeEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_care_engine import MemoryCareEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.types import MemoryCategory, ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "late_night", "Code", "Secret Window", "clipboard secret")


class CountingModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("local test reply [idle]", "counting-model", 0.01, None)


def count_rows(database: Path, table: str, where: str = "1=1") -> int:
    connection = sqlite3.connect(database)
    try:
        row = connection.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()
        return int(row[0])
    finally:
        connection.close()


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        database = root / "fibi_memory.db"
        state_path = root / "fibi_state.json"
        state_path.write_text(json.dumps({"mood": "happy", "v007_field": "keep"}), encoding="utf-8")

        memory = MemoryEngine(database)
        journal = JournalEngine(database)
        care = MemoryCareEngine(database, state_path)
        privacy = PrivacySettingsEngine(state_path)

        settings = privacy.settings
        assert settings.allow_foreground_app_observation is True
        assert settings.allow_window_title_observation is True
        assert settings.allow_clipboard_observation is False
        assert json.loads(state_path.read_text(encoding="utf-8"))["v007_field"] == "keep"

        first_id = memory.save(MemoryCategory.PROJECT, "working on KamikazeOS", 0.85)
        second_id = memory.save(MemoryCategory.FACT, "my name is Imran", 0.9)
        assert first_id and second_id

        listed = care.list_memories("projects")
        assert listed.ok and listed.entries and "KamikazeOS" in listed.entries[0].title
        searched = care.search_memories("Imran")
        assert searched.ok and searched.entries and searched.entries[0].entry_id == second_id

        edited = care.edit_memory(second_id, "my name is tiny human", confidence=0.7)
        assert edited.ok
        assert care.search_memories("tiny human").entries

        deleted = care.delete_memory(second_id, confirm=True)
        assert deleted.ok and deleted.changed_count == 1
        assert not care.search_memories("tiny human").entries

        memory.save(MemoryCategory.HABIT, "i usually say one more commit", 0.7)
        blocked = care.forget_category("habits", confirm=False)
        assert not blocked.ok
        wiped = care.forget_category("habits", confirm=True)
        assert wiped.ok and wiped.changed_count == 1

        inner = InnerLifeEngine(database)
        inner.create_dream("sleepy", known_projects=["KamikazeOS"])
        assert count_rows(database, "fibi_dreams") == 1
        assert not care.clear_dreams(confirm=False).ok
        assert care.clear_dreams(confirm=True).ok
        assert count_rows(database, "fibi_dreams") == 0

        journal.record("user_message", "idle", "idle", "hello", emotional_weight=0.4)
        assert count_rows(database, "journal_entries") == 1
        assert not care.clear_journal(confirm=False).ok
        assert care.clear_journal(confirm=True).ok
        assert count_rows(database, "journal_entries") == 0

        export = care.export_bundle(privacy.settings)
        assert export.ok and export.export_path and Path(export.export_path).exists()
        bundle = json.loads(Path(export.export_path).read_text(encoding="utf-8"))
        assert "memories" in bundle and "privacy_settings" in bundle
        assert "screenshots" not in bundle

        invalid = root / "bad_import.json"
        invalid.write_text(json.dumps({"memories": [{"category": "dreams", "content": "nope"}]}), encoding="utf-8")
        assert not care.validate_import_bundle(invalid).ok

        assert not care.reset_all("wrong confirm").ok

        model = CountingModel()
        core = FibiCore(
            life=LifeEngine(state_path),
            memory=memory,
            observation=FakeObservation(),
            journal=journal,
            patterns=PatternEngine(memory, journal),
            model=model,
            memory_care=care,
            privacy=privacy,
        )
        response = core.respond("/memories")
        assert response.model_used == "local-command"
        assert model.calls == 0

        core.respond("what do you remember about KamikazeOS?")
        assert core._last_referenced_memory_id is not None
        forgot = core.respond("forget that")
        assert "delete confirm" in forgot.display_text
        confirmed_forget = core.respond("memory delete confirm")
        assert "forgot" in confirmed_forget.display_text
        assert not care.search_memories("KamikazeOS").entries

        privacy.update(allow_journal=False, allow_ollama=False)
        before_journal = count_rows(database, "journal_entries")
        core.respond("my name is Journal Test")
        assert count_rows(database, "journal_entries") == before_journal

        privacy.update(allow_memory_learning=False)
        before_facts = count_rows(database, "memories", "category = 'fact'")
        core.respond("my name is Memory Blocked")
        assert count_rows(database, "memories", "category = 'fact'") == before_facts

        privacy.update(allow_dreams=False)
        before_dreams = count_rows(database, "fibi_dreams")
        core.life.nap.energy = 0
        core.life.last_interaction_time = time.monotonic() - 4000
        core.check_nap()
        assert count_rows(database, "fibi_dreams") == before_dreams

        full = care.reset_all("reset fibi confirm", create_backup=False)
        assert full.ok
        assert count_rows(database, "memories") == 0
        assert "privacy_settings" in json.loads(state_path.read_text(encoding="utf-8"))

    print("Fibi v0.08 smoke tests passed.")


if __name__ == "__main__":
    run()


