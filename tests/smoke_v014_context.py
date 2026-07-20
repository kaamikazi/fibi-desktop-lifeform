"""Direct smoke tests for Fibi v0.14 context drop and file awareness."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.context_engine import ContextEngine
from fibi.engines.core import FibiCore
from fibi.engines.file_reader_engine import FileReaderEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_router import ModelRouter
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "Fibi", None)


class PromptModel(ModelEngine):
    def __init__(self, text: str = "tiny explanation [thinking]") -> None:
        self.calls = 0
        self.prompts: list[str] = []
        self.text = text

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        self.prompts.append(prompt)
        return ModelResult(self.text, "prompt-model", 0.0, None)


def make_core(root: Path, model: PromptModel | None = None) -> tuple[FibiCore, PromptModel]:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"legacy_v013": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    model = model or PromptModel()
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=model,
        model_router=ModelRouter(model),
        privacy=PrivacySettingsEngine(state),
        context_engine=ContextEngine(SecretSanitizer()),
    ), model


def run() -> None:
    sanitizer = SecretSanitizer()
    fake_api_key = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    masked = sanitizer.sanitize(f"OPENAI_API_KEY={fake_api_key}\npassword=<dummy-test-password>")
    assert "sk-" not in masked
    assert "dummy-test-password" not in masked

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        core, model = make_core(root)

        item = core.context_engine.add_text("hello pasted context", "pasted_text", "paste")
        assert item.source == "pasted_text"
        assert core.context_engine.last().title == "paste"

        long_text = "line\n" * 130
        long_reply = core.respond(long_text)
        assert "context crumb" in long_reply.display_text
        assert core.context_engine.last() is not None

        code_reply = core.respond("```\nprint('hi')\n```\n" * 20)
        assert "code crumb" in code_reply.display_text

        safe_file = root / "app.py"
        file_api_key = "sk-" + "secretsecretsecretsecretsecret12"
        safe_file.write_text(f"OPENAI_API_KEY={file_api_key}\nprint('hi')", encoding="utf-8")
        file_reply = core.handle_dropped_file(str(safe_file))
        assert "tiny file acquired" in file_reply.display_text
        last = core.context_engine.last()
        assert last.title == "app.py"
        assert "sk-" not in last.content_preview

        unsupported = root / "image.png"
        unsupported.write_text("not really an image", encoding="utf-8")
        unsupported_reply = core.handle_dropped_file(str(unsupported))
        assert "can't chew" in unsupported_reply.display_text

        large = root / "big.txt"
        large.write_text("x" * 1_000_001, encoding="utf-8")
        large_reply = core.handle_dropped_file(str(large))
        assert "too big" in large_reply.display_text

        neighbor = root / "neighbor.txt"
        neighbor.write_text("do not read me", encoding="utf-8")
        assert "neighbor" not in (core.context_engine.last().content_text if core.context_engine.last() else "")

        explain = core.respond("explain this file")
        assert model.calls >= 1
        assert "OPENAI_API_KEY=[masked]" in model.prompts[-1]
        assert file_api_key not in model.prompts[-1]
        assert core.privacy.settings.allow_cloud_model is False

        status = core.respond("/context")
        assert status.model_used == "local-command"
        last_reply = core.respond("/context last")
        assert last_reply.model_used == "local-command"
        privacy = core.respond("/context privacy")
        assert "no clipboard" in privacy.display_text

        remember = core.respond("/context remember last confirm")
        assert "summary" in remember.display_text
        memories = core.memory.retrieve("User-provided context summary", limit=3)
        assert memories
        assert file_api_key not in memories[0].content

        forget = core.respond("/context forget last")
        assert "forgot" in forget.display_text
        clear = core.respond("/context clear")
        assert "cleared" in clear.display_text
        assert not core.context_engine.session().items

        selected = core.respond("/context add selected text here")
        assert "context crumb held" in selected.display_text

        explain_cmd = core.respond("/explain function add(a,b){return a+b}")
        assert explain_cmd.display_text
        assert model.calls >= 2

        start = time.perf_counter()
        greeting = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert greeting.model_used == "local-greeting"

    print("Fibi v0.14 context smoke tests passed.")


if __name__ == "__main__":
    run()


