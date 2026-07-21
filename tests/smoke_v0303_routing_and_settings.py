"""Mock-only smoke test for Fibi v0.30.3 routing and Settings hotfix."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication

from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.ui.fibi_window import FibiSettingsDialog
from tests.smoke_v012_actions import make_core


def run() -> None:
    classifier = FastResponseClassifier()
    assert classifier.classify("heyyyyyyy").category == "greeting"
    assert classifier.classify("what are you doing?").category == "complex_chat"
    for prompt in (
        "what do you think about memory?",
        "explain why Fibi separates identity from the model",
        "tell me something interesting",
        "how does your memory work?",
        "help me plan a software project",
    ):
        assert classifier.classify(prompt).should_use_model

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, model, _ = make_core(root / "core", [], [])
        assert core.respond("hello").model_used == "local-greeting"
        assert model.calls == 0
        first = core.respond("what are you doing?")
        second = core.respond("what are you doing?")
        assert first.display_text != second.display_text
        assert model.calls == 0
        core.respond("explain why memory remains outside the model")
        assert model.calls == 1
        core.privacy.update(allow_tts=True)
        core.voice_skin_settings.update(allow_rvc_voice_skin=True, rvc_enabled=True)
        core.respond("/voice rvc off")
        assert core.privacy.settings.allow_tts
        assert not core.voice_skin_settings.settings.rvc_enabled

        app = QApplication.instance() or QApplication([])
        dialog = FibiSettingsDialog(core)
        dialog.show()
        dialog.tabs.setCurrentIndex(3)
        app.processEvents()
        assert dialog.tabs.count() == 7
        assert all(dialog.tabs.tabText(index) for index in range(dialog.tabs.count()))
        assert dialog.provider_combo.isVisible()
        assert dialog.provider_status_badge.isVisible()
        assert dialog.provider_test_button.isVisible()
        dialog.close()
        app.processEvents()

    print("Fibi v0.30.3 routing and Settings smoke tests passed.")


if __name__ == "__main__":
    run()
