"""Direct Fibi v0.04 embodiment smoke tests; no pytest required."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.attention_engine import AttentionEngine
from fibi.engines.core import FibiCore
from fibi.engines.habit_engine import HabitEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.types import Observation


class StaticObservation:
    def __init__(self, time_of_day: str = "afternoon") -> None:
        self.current_time = time_of_day

    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation(datetime.now().astimezone().isoformat(), self.current_time, "code", "Fibi")

    @staticmethod
    def time_of_day(hour: int) -> str:
        return "late_night"


class NoModel:
    def generate(self, prompt: str):
        raise AssertionError("Ollama was called during a local creature reaction")


def make_core(root: Path, time_of_day: str = "afternoon") -> FibiCore:
    return FibiCore(
        life=LifeEngine(root / "state.json"),
        memory=MemoryEngine(root / "fibi.db"),
        observation=StaticObservation(time_of_day),
        model=NoModel(),
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        state = root / "state.json"
        state.write_text('{"mood":"idle","legacy":"preserved"}', encoding="utf-8")
        core = make_core(root, "late_night")

        affection = core.life.bond.affection
        assert core.handle_click(now=100)
        assert core.life.bond.affection > affection
        assert core.handle_click(now=101) is None

        core.handle_drag_start(now=200)
        core.handle_drag_end(100, 150, now=205)
        restored = LifeEngine(state)
        assert restored.window_position.x == 100 and restored.window_position.y == 150
        assert restored.restored_window_position(0, 0, 1920, 1080, 470, 330)
        restored.save_window_position(99999, 99999)
        assert restored.restored_window_position(0, 0, 1920, 1080, 470, 330) is None

        core.life.set_mood("sleepy")
        core.life.last_interaction_time = time.monotonic() - 2000
        assert core.check_nap(now=300)
        assert core.life.nap.is_napping
        assert core.handle_wake("smoke")
        assert not core.life.nap.is_napping

        attention = AttentionEngine()
        assert attention.evaluate("message", "sleepy", "speaking", "night").should_react
        attention.mark_reacted("click", now=10)
        assert not attention.evaluate("click", "idle", "idle", "afternoon", now=11).should_react

        assert HabitEngine().select("focused", "afternoon", "code").line
        assert make_core(root / "win").respond("build passed").model_used in {"local-personality", "local-micro-brain"}
        assert make_core(root / "error").respond("nothing works").model_used in {"local-personality", "local-micro-brain"}

        data = json.loads(state.read_text(encoding="utf-8"))
        assert data["legacy"] == "preserved"
        assert all(key in data for key in ("affection", "trust", "comfort", "mischief", "attachment_level"))
        assert all(key in data for key in ("is_napping", "nap_started_at", "last_woke_at", "window_x", "window_y"))

    print("Fibi v0.04 smoke tests passed.")


if __name__ == "__main__":
    main()


