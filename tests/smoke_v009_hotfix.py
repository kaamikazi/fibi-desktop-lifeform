"""Emergency v0.09 hotfix smoke tests for fast routing and optional NVIDIA."""

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
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_router import ModelRouter
from fibi.engines.nvidia_model_engine import NvidiaModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.types import ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "C:\\secret\\project", "clipboard secret")


class CountingOllama(ModelEngine):
    def __init__(self, text: str = "ollama reply [idle]") -> None:
        self.calls = 0
        self.text = text

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult(self.text, "fake-ollama", 0.01, None)


class CountingNvidia(NvidiaModelEngine):
    def __init__(self, text: str = "nvidia reply", error: str | None = None, has_key: bool = True) -> None:
        super().__init__()
        self.calls = 0
        self.text = text
        self.error = error
        self.has_key = has_key

    def api_key_available(self) -> bool:
        return self.has_key

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult(self.text, "fake-nvidia", 0.01, self.error)


def make_core(root: Path, ollama: CountingOllama, nvidia: CountingNvidia) -> FibiCore:
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"mood": "idle", "legacy": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    privacy = PrivacySettingsEngine(state)
    router = ModelRouter(ollama, nvidia)
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=ollama,
        nvidia_model=nvidia,
        model_router=router,
        privacy=privacy,
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        ollama = CountingOllama()
        nvidia = CountingNvidia()
        core = make_core(root, ollama, nvidia)

        start = time.perf_counter()
        response = core.respond("hi")
        duration_ms = (time.perf_counter() - start) * 1000
        assert duration_ms < 300, f"greeting took {duration_ms:.1f} ms"
        assert response.model_used == "local-greeting"
        assert ollama.calls == 0
        assert nvidia.calls == 0

        slash = core.respond("/model status")
        assert slash.model_used == "local-command"
        assert ollama.calls == 0
        assert nvidia.calls == 0

        core.respond("/cloud off")
        normal = core.respond("tell me a tiny thing")
        assert nvidia.calls == 0
        assert normal.display_text

        missing_key_router = ModelRouter(CountingOllama(), CountingNvidia(has_key=False))
        routed = missing_key_router.route(
            "prompt",
            "hello non-greeting",
            "idle",
            core.privacy.update(allow_cloud_model=True, allow_nvidia_api=True),
            observation=FakeObservation().observe(),
        )
        assert routed.provider_used in {"ollama", "fallback"}

        timeout_router = ModelRouter(CountingOllama(text=""), CountingNvidia(text="", error="timeout", has_key=True))
        timeout_result = timeout_router.route(
            "prompt",
            "normal message",
            "idle",
            core.privacy.update(allow_cloud_model=True, allow_nvidia_api=True),
            observation=FakeObservation().observe(),
        )
        assert timeout_result.provider_used == "fallback"
        assert timeout_result.fallback_used

        sanitizer = CloudContextSanitizer()
        prompt = sanitizer.build_prompt(
            "open C:\\Users\\imran\\secret.txt token=abc123",
            "idle",
            "memory_hint",
            memory_hints=["raw path C:\\private\\thing"],
            observation=FakeObservation().observe(include_clipboard=True),
        )
        assert "abc123" not in prompt
        assert "C:\\Users" not in prompt
        assert "clipboard secret" not in prompt

        masked = NvidiaModelEngine.mask_api_key("abcd1234wxyz")
        assert masked == "abcd...wxyz"

        core.respond("/cloud on confirm")
        cloud_context = core.respond("/cloud context memory_hint")
        assert "memory hints allowed" in cloud_context.display_text

        state = json.loads((root / "fibi_state.json").read_text(encoding="utf-8"))
        assert state["legacy"] == "keep"
        assert state["privacy_settings"]["allow_cloud_model"] is True
        assert state["privacy_settings"]["cloud_context_level"] == "memory_hint"

    print(f"Fibi v0.09 hotfix smoke tests passed. greeting_ms={duration_ms:.1f}")


if __name__ == "__main__":
    run()


