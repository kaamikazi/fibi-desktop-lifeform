"""Smoke test for Fibi v0.30.1 Gemini routing without real API calls."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.model_router import ModelRouter
from fibi.providers.gemini_provider import GeminiProvider
from fibi.providers.types import GeminiProviderConfig
from tests.smoke_v012_actions import make_core
from tests.test_v0301_gemini_provider import FakeClient, FakeModelsAPI


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, ollama, _ = make_core(root / "core", [], [])
        api = FakeModelsAPI(response_text="GEMINI_PROVIDER_OK")
        config = GeminiProviderConfig(
            selected_provider="gemini",
            api_key="fake-smoke-key",
            fallback_to_ollama=True,
        )
        gemini = GeminiProvider(config, client_factory=lambda _key, _timeout: FakeClient(api))
        core.model_router = ModelRouter(ollama=ollama, gemini=gemini)

        assert "provider:" in core.respond("/provider status").display_text
        assert api.generate_calls == 0
        selected = core.respond("/provider use gemini").display_text
        assert "Cloud request preview" in selected
        assert "Raw memory database: excluded" in selected
        tested = core.respond("/provider test").display_text
        assert "Gemini test ok" in tested
        assert api.prompts == ["Reply with GEMINI_PROVIDER_OK."]
        assert core.respond("/provider use ollama").display_text.startswith("back to LOCAL")

    print("Fibi v0.30.1 Gemini provider smoke tests passed.")


if __name__ == "__main__":
    run()
