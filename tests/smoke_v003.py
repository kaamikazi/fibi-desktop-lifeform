"""Direct Fibi v0.03 smoke tests; does not require pytest."""

from __future__ import annotations

import tempfile
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.personality_engine import PersonalityEngine
from fibi.engines.types import Memory, MemoryCategory, Observation


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        database = root / "fibi.db"
        state_path = root / "state.json"
        memory = MemoryEngine(database)
        journal = JournalEngine(database)

        journal.record("startup", "happy", "idle", "back already?")
        assert journal.recent(limit=1)[0].short_summary == "back already?"

        previous = datetime.now().astimezone() - timedelta(hours=4)
        state_path.write_text(
            '{"mood":"sleepy","last_seen_at":"'
            + previous.isoformat(timespec="seconds")
            + '","total_sessions":1,"custom":"preserved"}',
            encoding="utf-8",
        )
        life = LifeEngine(state_path)
        assert life.startup_line
        assert "preserved" in state_path.read_text(encoding="utf-8")

        for _ in range(3):
            journal.record(
                "late_night_session",
                "sleepy",
                "observing",
                "Sampled coding.",
                metadata={"time_of_day": "late_night", "active_app": "code"},
            )
        observation = Observation(
            datetime.now().astimezone().isoformat(),
            "late_night",
            "code",
            "Fibi - Visual Studio Code",
        )
        patterns = PatternEngine(memory, journal).detect(observation)
        assert any(item.pattern == "late_night_coding" for item in patterns)

        first = life.idle_reaction(active_app="code", now=100)
        second = life.idle_reaction(active_app="code", now=101)
        assert first != second

        personality = PersonalityEngine(memory)
        project = Memory(None, MemoryCategory.PROJECT, "Building KamikazeOS", 0.9)
        assert personality.natural_memory_hints([project]) == ["still working on KamikazeOS?"]
        assert personality.natural_memory_hints([]) == []
        assert personality.opinion_reaction("I should quit", observation, [], patterns, []) is None
        assert personality.opinion_reaction("I should quit", observation, [project], patterns, [])

        assert ObservationEngine().read_clipboard(permission=True) is None
        assert journal.summarize_day()

    print("Fibi v0.03 smoke tests passed.")


if __name__ == "__main__":
    main()


