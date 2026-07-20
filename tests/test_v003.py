from datetime import datetime, timedelta
from pathlib import Path

from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.personality_engine import PersonalityEngine
from fibi.engines.types import Memory, MemoryCategory, Observation


def _observation(time_of_day: str = "afternoon") -> Observation:
    return Observation(
        timestamp=datetime.now().astimezone().isoformat(),
        time_of_day=time_of_day,
        active_app="code",
        active_window_title="Project Fibi - Visual Studio Code",
    )


def test_journal_entry_creation(tmp_path: Path):
    journal = JournalEngine(tmp_path / "fibi.db")
    journal.record("startup", "happy", "idle", "back already?")
    assert journal.recent(limit=1)[0].event_type == "startup"


def test_state_continuity_preserves_existing_fields(tmp_path: Path):
    state_path = tmp_path / "state.json"
    previous = datetime.now().astimezone() - timedelta(minutes=5)
    state_path.write_text(
        '{"mood":"happy","custom_field":"keep-me","last_seen_at":"'
        + previous.isoformat(timespec="seconds")
        + '","total_sessions":2}',
        encoding="utf-8",
    )
    life = LifeEngine(state_path)
    saved = state_path.read_text(encoding="utf-8")
    assert life.startup_line
    assert life.total_sessions == 3
    assert '"custom_field": "keep-me"' in saved


def test_pattern_detection_from_sample_journal(tmp_path: Path):
    database = tmp_path / "fibi.db"
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    for _ in range(3):
        journal.record(
            "late_night_session",
            "sleepy",
            "observing",
            "Sampled coding.",
            metadata={"time_of_day": "late_night", "active_app": "code"},
        )
    patterns = PatternEngine(memory, journal).detect(_observation("late_night"))
    assert any(pattern.pattern == "late_night_coding" for pattern in patterns)


def test_idle_reaction_context_cooldown(tmp_path: Path):
    life = LifeEngine(tmp_path / "state.json")
    first = life.idle_reaction(active_app="code", now=100)
    second = life.idle_reaction(active_app="code", now=101)
    assert first in {"still building?", "compiler creature nearby."}
    assert second in {"hm.", "blink blink.", "still here."}


def test_natural_memory_hint_uses_real_memory(tmp_path: Path):
    personality = PersonalityEngine(MemoryEngine(tmp_path / "fibi.db"))
    memory = Memory(None, MemoryCategory.PROJECT, "The user is building KamikazeOS.", 0.9)
    assert personality.natural_memory_hints([memory]) == ["still working on KamikazeOS?"]


def test_opinion_layer_requires_evidence(tmp_path: Path):
    personality = PersonalityEngine(MemoryEngine(tmp_path / "fibi.db"))
    observation = _observation()
    assert personality.opinion_reaction("I should quit", observation, [], [], []) is None

    project = Memory(None, MemoryCategory.PROJECT, "Building Fibi", 0.9)
    assert personality.opinion_reaction("I should quit", observation, [project], [], []) is not None


def test_no_invented_memory_hint(tmp_path: Path):
    personality = PersonalityEngine(MemoryEngine(tmp_path / "fibi.db"))
    assert personality.natural_memory_hints([]) == []


def test_clipboard_remains_disabled_by_default():
    assert ObservationEngine().read_clipboard(permission=True) is None


