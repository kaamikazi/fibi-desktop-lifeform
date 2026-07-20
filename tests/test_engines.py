from pathlib import Path

from fibi.engines.life_engine import MoodStateMachine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.types import MemoryCategory


def test_memory_engine_saves_and_retrieves(tmp_path: Path):
    engine = MemoryEngine(tmp_path / "memory.db")
    engine.save(MemoryCategory.PROJECT, "The user is building KamikazeOS.", 0.9)

    memories = engine.retrieve("KamikazeOS")

    assert len(memories) == 1
    assert memories[0].category == MemoryCategory.PROJECT


def test_memory_engine_learns_clear_user_statements(tmp_path: Path):
    engine = MemoryEngine(tmp_path / "memory.db")

    saved = engine.learn_from_message("My name is Imran.")

    assert saved
    assert engine.retrieve("Imran")[0].category == MemoryCategory.FACT


def test_observation_time_of_day():
    assert ObservationEngine.time_of_day(3) == "late_night"
    assert ObservationEngine.time_of_day(10) == "morning"
    assert ObservationEngine.time_of_day(23) == "night"


def test_clipboard_is_denied_by_default():
    engine = ObservationEngine(allow_clipboard=False)
    assert engine.read_clipboard(permission=True) is None


def test_mood_state_machine_is_deterministic_for_errors():
    machine = MoodStateMachine()
    assert machine.transition("reply", user_text="the build failed") == "annoyed"


