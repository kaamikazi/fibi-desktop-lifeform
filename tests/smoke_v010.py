"""Direct smoke tests for Fibi v0.10 speed and offline survival."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.cloud_context_sanitizer import CloudContextSanitizer
from fibi.engines.core import FibiCore
from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_router import ModelRouter
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.response_budget_engine import ResponseBudgetEngine
from fibi.engines.types import ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "late_night", "Code", "C:\\private\\window", "clipboard secret")


class CountingModel(ModelEngine):
    def __init__(self, text: str = "model reply [idle]", delay: float = 0.0, error: str | None = None) -> None:
        self.calls = 0
        self.text = text
        self.delay = delay
        self.error = error

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return ModelResult(self.text, "counting-model", self.delay, self.error)


def make_core(root: Path, model: CountingModel) -> FibiCore:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"legacy_v009": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    privacy = PrivacySettingsEngine(state)
    router = ModelRouter(model)
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=model,
        model_router=router,
        privacy=privacy,
    )


def run() -> None:
    classifier = FastResponseClassifier()
    assert classifier.classify("hi").category == "greeting"
    assert classifier.classify("thanks!").category == "thanks"
    assert classifier.classify("bye").category == "goodbye"
    assert classifier.classify("it worked").category == "simple_chat"
    assert classifier.classify("this bug crashed").category == "simple_chat"
    assert classifier.classify("/privacy").category == "privacy_command"
    assert classifier.classify("what is Python?").category == "complex_chat"
    assert classifier.classify("explain this code").category == "complex_chat"
    assert classifier.classify("how do I fix this error?").category == "complex_chat"
    assert classifier.classify("tell me about KamikazeOS").category == "complex_chat"
    assert classifier.classify("make a plan").category == "complex_chat"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        model = CountingModel()
        core = make_core(root, model)

        for message in ["hi", "thanks", "bye", "are you there?"]:
            start = time.perf_counter()
            response = core.respond(message)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert elapsed_ms < 300 if message == "hi" else elapsed_ms < 500
            assert response.model_used in {"local-greeting", "local-micro-brain"}
        assert model.calls == 0

        for message in ["it worked", "this bug crashed"]:
            response = core.respond(message)
            assert response.model_used == "counting-model"
        assert model.calls == 2

        command = core.respond("/model status")
        assert command.model_used == "local-command"
        assert model.calls == 2

        cancel = core.respond("/cancel")
        assert cancel.model_used == "local-command"
        assert cancel.display_text in {"stopped.", "thought escaped.", "okay."}

        perf = core.respond("/perf")
        assert "last reply" in perf.display_text
        reset = core.respond("/perf reset")
        assert "reset" in reset.display_text

        assert core.privacy.settings.allow_cloud_model is False
        assert core.privacy.settings.allow_nvidia_api is False

        # Complex chat may call model. If provider is repeatedly failing, health falls back locally.
        failing = CountingModel("", error="timeout")
        fail_core = make_core(root / "fail", failing)
        fail_core.health.record_provider_result("ollama", 9000, False)
        fail_core.health.record_provider_result("ollama", 9000, False)
        fail_core.health.record_provider_result("ollama", 9000, False)
        response = fail_core.respond("please explain why this architecture should be reliable over time")
        assert response.display_text
        assert response.model_used in {"health-local-fallback", "local-micro-brain"}

        budget, started = ResponseBudgetEngine().start("greeting")
        time.sleep(0.001)
        updated = ResponseBudgetEngine.update(budget, started)
        assert updated.budget_ms == 300
        assert updated.elapsed_ms >= 0

        prompt = CloudContextSanitizer().build_prompt(
            "open C:\\Users\\imran\\secret.txt api_key=abc123",
            "idle",
            "memory_hint",
            memory_hints=["C:\\private\\memory"],
            observation=FakeObservation().observe(include_clipboard=True),
        )
        assert "abc123" not in prompt
        assert "C:\\Users" not in prompt
        assert "clipboard secret" not in prompt

        state = json.loads((root / "fibi_state.json").read_text(encoding="utf-8"))
        assert state["legacy_v009"] == "keep"
        assert "model_health" in state
        assert "performance_metric" in state

    print("Fibi v0.10 smoke tests passed.")


if __name__ == "__main__":
    run()


