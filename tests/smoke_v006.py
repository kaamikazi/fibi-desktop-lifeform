"""Direct Fibi v0.06 creature-polish tests; no PyQt or pytest required."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.core import FibiCore
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.motion_engine import MotionEngine
from fibi.engines.repetition_guard import RepetitionGuard
from fibi.engines.timing_engine import TimingEngine
from fibi.engines.types import AttentionResult, Observation
from fibi.ui.expression_controller import ExpressionController
from fibi.voice.sounds import play_sound_event


class StaticObservation:
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation(datetime.now().astimezone().isoformat(), "late_night", "code", "Fibi")

    @staticmethod
    def time_of_day(hour: int) -> str:
        return "late_night"


class NoModel:
    def generate(self, prompt: str):
        raise AssertionError("Ollama was called for a local greeting")


def main() -> None:
    motion = MotionEngine()
    click = motion.select(mood="happy", presence_state="idle", event="click", now=100)
    assert click and click.motion_name == "pet_recoil"
    assert motion.select(mood="happy", presence_state="idle", event="click", now=101) is None
    sleepy = MotionEngine().select(mood="sleepy", presence_state="idle", time_of_day="night")
    assert sleepy and sleepy.motion_name == "sleepy_sway"
    low = AttentionResult(10, "quiet", False, "idle")
    assert MotionEngine().select(mood="idle", presence_state="idle", attention=low) is None

    expressions = ExpressionController("idle", minimum_duration_ms=500)
    assert expressions.set_persistent("happy", now_ms=100, force=True) == "happy"
    assert expressions.set_persistent("sleepy", now_ms=200) == "happy"
    assert expressions.show_temporary("thinking", 500, now_ms=1000) == "thinking"
    assert expressions.current(now_ms=1600) == "sleepy"
    assert expressions.set_persistent("missing", now_ms=2200, force=True) == "idle"

    timing = TimingEngine()
    sleepy_timing = timing.select(event="reply", mood="sleepy", time_of_day="night", local=True)
    assert sleepy_timing.pre_delay_ms > 0 and sleepy_timing.typing_style == "sleepy"
    thinking = timing.select(event="reply", mood="focused", local=True)
    assert thinking.show_thinking_bubble and thinking.thinking_line == "hmm..."
    bubble = timing.bubble_options("small words", "soft")
    assert bubble.auto_hide_ms >= 3000 and bubble.keep_while_speaking

    guard = RepetitionGuard()
    guard.remember(line="eepy...", category="idle")
    assert not guard.allows_line("eepy...")
    assert guard.allows_line("eepy...", direct=True)
    restored_guard = RepetitionGuard(guard.export_state())
    assert not restored_guard.allows_line("eepy...")

    # Missing pygame or files must remain a silent no-op.
    play_sound_event("success")
    play_sound_event("unknown")

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        state = root / "state.json"
        state.write_text(json.dumps({"mood": "idle", "nest_x": 20, "nest_y": 30, "v005_field": "safe"}), encoding="utf-8")
        life = LifeEngine(state)
        core = FibiCore(
            life=life,
            memory=MemoryEngine(root / "fibi.db"),
            observation=StaticObservation(),
            model=NoModel(),
        )
        response = core.respond("hey")
        assert response.model_used in {"local-personality", "local-greeting"}
        assert response.timing is not None
        saved = json.loads(state.read_text(encoding="utf-8"))
        assert saved["v005_field"] == "safe" and saved["nest_x"] == 20
        assert "repetition" in saved

    print("Fibi v0.06 smoke tests passed.")


if __name__ == "__main__":
    main()


