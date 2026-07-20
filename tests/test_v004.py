import json
import time
from datetime import datetime
from pathlib import Path

from fibi.engines.attention_engine import AttentionEngine
from fibi.engines.core import FibiCore
from fibi.engines.habit_engine import HabitEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.types import Observation


class StaticObservation:
    def __init__(self, time_of_day: str = "afternoon", app: str = "code") -> None:
        self.current_time = time_of_day
        self.app = app

    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation(datetime.now().astimezone().isoformat(), self.current_time, self.app, "Fibi")

    @staticmethod
    def time_of_day(hour: int) -> str:
        return "late_night" if hour < 5 else "afternoon"


class NoModel:
    def generate(self, prompt: str):
        raise AssertionError("Creature reactions must not call Ollama")


def _core(tmp_path: Path, time_of_day: str = "afternoon") -> FibiCore:
    return FibiCore(
        life=LifeEngine(tmp_path / "state.json"),
        memory=MemoryEngine(tmp_path / "fibi.db"),
        observation=StaticObservation(time_of_day),
        model=NoModel(),
    )


def test_affection_state_persistence_and_migration(tmp_path: Path):
    state = tmp_path / "state.json"
    state.write_text('{"mood":"idle","old_field":"safe"}', encoding="utf-8")
    life = LifeEngine(state)
    before = life.bond.affection
    life.update_bond("pet")

    restored = LifeEngine(state)
    data = json.loads(state.read_text(encoding="utf-8"))
    assert restored.bond.affection >= before + 1
    assert data["old_field"] == "safe"


def test_click_reaction_cooldown(tmp_path: Path):
    core = _core(tmp_path)
    assert core.handle_click(now=100) is not None
    assert core.handle_click(now=101) is None


def test_drag_position_persistence(tmp_path: Path):
    core = _core(tmp_path)
    core.handle_drag_start(now=100)
    core.handle_drag_end(120, 220, now=105)
    restored = LifeEngine(tmp_path / "state.json")
    assert restored.window_position.x == 120
    assert restored.window_position.y == 220


def test_invalid_window_position_falls_back(tmp_path: Path):
    life = LifeEngine(tmp_path / "state.json")
    life.save_window_position(99999, 99999)
    assert life.restored_window_position(0, 0, 1920, 1080, 470, 330) is None


def test_nap_and_wake(tmp_path: Path):
    core = _core(tmp_path, "late_night")
    core.life.set_mood("sleepy")
    core.life.last_interaction_time = time.monotonic() - 2000
    nap = core.check_nap(now=100)
    assert nap and core.life.nap.is_napping
    wake = core.handle_wake("test")
    assert wake and not core.life.nap.is_napping


def test_attention_cooldown_and_direct_message():
    attention = AttentionEngine()
    first = attention.evaluate("click", "happy", "idle", "afternoon", now=100)
    assert first.should_react
    attention.mark_reacted("click", now=100)
    assert not attention.evaluate("click", "happy", "idle", "afternoon", now=101).should_react
    assert attention.evaluate("message", "sleepy", "speaking", "night", now=101).should_react


def test_habit_selection_is_local():
    habit = HabitEngine().select("focused", "afternoon", "code", timestamp=datetime(2026, 6, 19, 14))
    assert habit.name in {"watch_vscode", "pretend_debug", "compiler_watch"}
    assert habit.line


def test_celebration_and_frustration_need_no_model(tmp_path: Path):
    celebration = _core(tmp_path / "celebration").respond("it worked")
    frustration = _core(tmp_path / "frustration").respond("nothing works")
    assert celebration.model_used in {"local-personality", "local-micro-brain"}
    assert frustration.model_used in {"local-personality", "local-micro-brain"}


def test_click_reaction_needs_no_model(tmp_path: Path):
    assert _core(tmp_path).handle_click(now=100) is not None


