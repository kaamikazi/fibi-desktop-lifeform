"""Direct Fibi v0.05 continuity tests; no pytest required."""

from __future__ import annotations

import sys
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.reaction_library import ReactionLibrary
from fibi.engines.ritual_engine import RitualEngine
from fibi.engines.types import MemoryCategory


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        memory = MemoryEngine(root / "fibi.db")
        journal = JournalEngine(memory.database_path)

        reactions = ReactionLibrary()
        picked = reactions.choose("greeting", affection=70, time_of_day="morning")
        assert picked.text and picked.mood
        low_bond = ReactionLibrary().choose("greeting", affection=0, time_of_day="morning")
        assert low_bond.text != "welcome back, tiny human."

        rituals = RitualEngine(reactions)
        now = datetime.now().astimezone().replace(hour=9)
        first = rituals.startup("morning", 60, 12, now=now)
        second = rituals.startup("morning", 60, 12, now=now + timedelta(minutes=1))
        assert first.triggered and not second.triggered
        assert rituals.export_state()[first.name]["times_triggered"] == 1
        late = RitualEngine(reactions).ambient("late_night", 40, 60, now=now.replace(hour=2))
        assert late.triggered and late.name == "late_night_warning"

        life = LifeEngine(root / "state.json")
        assert not life.register_nest_placement(120, 180)
        assert not life.register_nest_placement(125, 176)
        assert life.register_nest_placement(122, 181)
        assert life.nest.position is not None and life.nest.confidence >= 0.65
        life.window_position = None
        restored, path = life.restored_position(0, 0, 1920, 1080, 470, 330)
        assert restored is not None and path == "nest"
        assert life.time_personality_curve("late_night").preferred_mood == "sleepy"
        life.nest.position.x = 99999
        life.window_position = None
        assert life.restored_position(0, 0, 1920, 1080, 470, 330)[1] == "default"
        life.mark_shutdown()
        assert LifeEngine(root / "state.json").last_shutdown_at

        stay_life = LifeEngine(root / "stay_state.json")
        stay_life.register_nest_placement(300, 300)
        first_seen = datetime.fromisoformat(stay_life._nest_candidate["first_seen_at"])
        assert stay_life.consider_nest_stay(300, 300, now=first_seen + timedelta(minutes=16))
        state_data = json.loads((root / "stay_state.json").read_text(encoding="utf-8"))
        assert state_data["nest_x"] == 300 and "total_sessions" in state_data

        memory.save(MemoryCategory.PROJECT, "Working on Fibi", importance=0.8)
        journal.record("user_message", "happy", "idle", "worked on Fibi", related_project="Fibi")
        journal.record("celebration", "excited", "idle", "Fibi build passed", related_project="Fibi")
        summary = journal.create_daily_summary()
        assert summary.interaction_count >= 2 and "Fibi" in summary.projects
        assert journal.get_daily_summary(summary.date) is not None
        yesterday = (datetime.now().astimezone().date() - timedelta(days=1)).isoformat()
        journal.record("user_message", "sleepy", "idle", "late code", related_project="Fibi", timestamp=f"{yesterday}T23:00:00+00:00")
        journal.create_daily_summary(yesterday)
        assert journal.yesterday_reference()

        patterns = PatternEngine(memory, journal)
        affinity = patterns.update_project_affinity("Fibi", "success")
        assert affinity is not None and affinity.success_weight == 1
        assert patterns.update_project_affinity("invented project", "success") is None
        assert patterns.favorite_project().project_name == "Fibi"

    print("Fibi v0.05 smoke tests passed.")


if __name__ == "__main__":
    main()


