"""Direct smoke tests for Fibi v0.07 inner-life systems."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fibi.engines.inner_life_engine as inner_module
from fibi.engines.core import FibiCore
from fibi.engines.emotional_weighting import emotional_weight_for_message
from fibi.engines.inner_life_engine import InnerLifeEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.opinion_engine import OpinionEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.preference_engine import PreferenceEngine
from fibi.engines.types import JournalEntry, MemoryCategory, ModelResult, NestState, Observation, WindowPosition


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "late_night", "Code", "Project window", None)


class EmptyModel(ModelEngine):
    def generate(self, prompt: str) -> ModelResult:
        return ModelResult("", "fake-unavailable", 0.0, "offline")


class ShortModel(ModelEngine):
    def generate(self, prompt: str) -> ModelResult:
        return ModelResult("KamikazeOS is definitely real [happy]", "fake-model", 0.01, None)


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

        memory = MemoryEngine(database)
        journal = JournalEngine(database)
        inner = InnerLifeEngine(database)
        preferences = PreferenceEngine(database)
        opinions = OpinionEngine(database)

        project_id = memory.save(MemoryCategory.PROJECT, "working on KamikazeOS", 0.85)
        assert project_id is not None
        memories = memory.retrieve("KamikazeOS", limit=3)
        journal.record("celebration", "happy", "idle", "it worked", "KamikazeOS", 0.85)
        recent = journal.recent(limit=10)

        thought = inner.create_thought(
            "curious",
            "evening",
            memories=memories,
            recent_journal=recent,
            known_projects=["KamikazeOS"],
            nest=NestState(WindowPosition(20, 30), confidence=0.8),
        )
        assert thought.id is not None
        assert thought.related_project == "KamikazeOS"
        assert thought.category in {"project_thought", "memory_thought"}
        assert len(thought.text) <= 160

        original_random = inner_module.random.random
        inner_module.random.random = lambda: 0.0
        try:
            inner.save_thought(
                "silly_thought",
                "idle",
                "tiny thought.",
                should_surface_to_user=True,
            )
            bubble = inner.thought_bubble_candidate(40, focused=False, busy=False, mood="idle")
        finally:
            inner_module.random.random = original_random
        assert bubble is not None and bubble.should_display
        assert inner.thought_bubble_candidate(40, focused=True, busy=False, mood="idle") is None

        facts_before = count_rows(database, "memories", "category = 'fact'")
        dream = inner.create_dream(
            "sleepy",
            recent_journal=recent,
            known_projects=["KamikazeOS"],
            nest=NestState(WindowPosition(20, 30), confidence=0.8),
        )
        assert dream.id is not None
        assert count_rows(database, "fibi_dreams") == 1
        assert count_rows(database, "memories", "category = 'fact'") == facts_before

        updates = preferences.update_from_context(
            NestState(WindowPosition(20, 30), confidence=0.85),
            None,
            [
                JournalEntry(None, "now", "late_night_session", "sleepy", "idle", "late code", None, 0.6, "test", {}),
                JournalEntry(None, "now", "late_night_session", "sleepy", "idle", "late code", None, 0.6, "test", {}),
            ],
        )
        keys = {update.preference_key for update in updates}
        assert "favorite_nest_spot" in keys
        assert "dislikes_late_night_overwork" in keys

        activity = [
            JournalEntry(None, "now", "user_message", "focused", "idle", "worked", None, 0.6, "test", {}),
            JournalEntry(None, "now", "error_seen", "annoyed", "idle", "bug", None, 0.8, "test", {}),
            JournalEntry(None, "now", "celebration", "happy", "idle", "fixed", None, 0.8, "test", {}),
        ]
        supported = opinions.evaluate("I did nothing today", activity, memories, [], preferences.list_preferences())
        assert supported is not None and supported.supported and "false" in supported.text
        unsupported = opinions.evaluate("I did nothing today", [], [], [], [])
        assert unsupported is not None and not unsupported.supported and unsupported.text == ""

        weight = emotional_weight_for_message("the bug failed but it finally passed", "late_night", "KamikazeOS")
        assert weight.weight >= 0.8
        assert "success" in weight.reason and "frustration" in weight.reason

        state_path.write_text(
            json.dumps(
                {
                    "mood": "idle",
                    "nest_x": 11,
                    "nest_y": 22,
                    "nest_confidence": 0.7,
                    "custom_v006_field": "keep me",
                }
            ),
            encoding="utf-8",
        )
        life = LifeEngine(state_path)
        drift = life.drift_mood("late_night", idle_seconds=60 * 60)
        assert drift.new_mood == "sleepy"
        saved = json.loads(state_path.read_text(encoding="utf-8"))
        assert saved["custom_v006_field"] == "keep me"
        assert saved["nest_x"] == 11 and saved["nest_y"] == 22

        temp_core = FibiCore(
            life=life,
            memory=memory,
            observation=FakeObservation(),
            journal=journal,
            patterns=PatternEngine(memory, journal),
            model=EmptyModel(),
            inner_life=inner,
            preferences=preferences,
            opinions=opinions,
        )
        response = temp_core.respond("hey")
        assert response.display_text
        assert response.model_used in {"local-personality", "local-greeting"}

        no_project_db = root / "no_project.db"
        no_project_memory = MemoryEngine(no_project_db)
        no_project_journal = JournalEngine(no_project_db)
        no_project_core = FibiCore(
            life=LifeEngine(root / "no_project_state.json"),
            memory=no_project_memory,
            observation=FakeObservation(),
            journal=no_project_journal,
            patterns=PatternEngine(no_project_memory, no_project_journal),
            model=ShortModel(),
        )
        no_project_core.respond("what now?")
        assert count_rows(no_project_db, "project_affinity") == 0
        assert count_rows(no_project_db, "memories", "category = 'project'") == 0

    print("Fibi v0.07 smoke tests passed.")


if __name__ == "__main__":
    run()


