"""Smoke tests for Fibi v0.15.1 routing stability and TTS policy."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_router import ModelRouter
from fibi.engines.types import ModelResult
from tests.smoke_v012_actions import make_core


class HealthyModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("python is a tiny programming language.", "healthy-model", 0.01, None)


class TimeoutModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("", "timeout-model", 8.0, "request timed out")


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root, opened, launched)

        start = time.perf_counter()
        hi = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert hi.model_used == "local-greeting"

        date = core.respond("what's the date")
        assert date.model_used == "local-action"
        assert date.tts_priority == "low"
        assert model.calls == 0
        assert not core.route_decisions.last_decision.model_router_allowed

        clock = core.respond("what time is it")
        assert clock.model_used == "local-action"
        assert model.calls == 0

        volume = core.respond("volume up")
        assert volume.model_used in {"local-action", "volume_up"}
        assert model.calls == 0

        status = core.respond("/status")
        assert status.model_used == "local-command"
        assert model.calls == 0

        route_test = core.respond("/route test what's the date")
        assert "would route:" in route_test.display_text
        assert "model: no" in route_test.display_text
        route_last = core.respond("/route last")
        assert "route:" in route_last.display_text

        core.privacy.update(allow_tts=False)
        silent_hi = core.respond("hello")
        tts_decision = core.tts_manager.decide(silent_hi.model_used, silent_hi.display_text, core.privacy.settings.allow_tts, silent_hi.tts_priority)
        assert silent_hi.display_text
        assert not tts_decision.should_speak
        assert tts_decision.skipped_reason == "disabled"

        core.privacy.update(allow_tts=True)
        utility_tts = core.tts_manager.decide(date.model_used, date.display_text, True, date.tts_priority)
        assert not utility_tts.should_speak
        assert utility_tts.skipped_reason == "utility_tts_off"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        healthy = HealthyModel()
        core, _, _ = make_core(root, opened, launched)
        core.model_router = ModelRouter(healthy)
        answer = core.respond("what is Python?")
        assert healthy.calls == 1
        assert answer.model_used == "healthy-model"
        assert core.route_decisions.last_decision.route_name == "model_complex_chat"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        sleepy = TimeoutModel()
        core, _, _ = make_core(root, opened, launched)
        core.model_router = ModelRouter(sleepy)
        first = core.respond("what is Python?")
        assert sleepy.calls == 1
        assert first.display_text
        second = core.respond("explain recursion")
        assert sleepy.calls == 1
        assert second.display_text

    print("Fibi v0.15.1 routing/TTS smoke tests passed.")


if __name__ == "__main__":
    run()


