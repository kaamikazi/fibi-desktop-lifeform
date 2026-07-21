"""Offscreen smoke test for the Fibi v0.30.2 demo layout."""

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

from fibi.engines.types import FibiResponse
from fibi.ui.fibi_window import FibiWindow


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        os.environ["FIBI_DATA_DIR"] = str(Path(temp) / "data")
        app = QApplication.instance() or QApplication([])
        window = FibiWindow()
        window.sprite.animation_timer.stop()
        window.idle_timer.stop()
        window.show()
        window.resize(window.minimumSize())
        app.processEvents()
        window.layout().activate()
        app.processEvents()

        input_rect = window.chat_input.geometry()
        mic_rect = window.mic_button.geometry()
        send_rect = window.send_button.geometry()
        assert input_rect.width() >= 180
        assert not input_rect.intersects(mic_rect)
        assert not input_rect.intersects(send_rect)
        assert not mic_rect.intersects(send_rect)
        assert window.sprite.rect().contains(window.sprite.rendered_sprite_rect())
        assert window.sprite.rendered_sprite_rect().height() >= 240
        assert window.size() == FibiWindow.COMPACT_SIZE
        menu_labels = [action.text() for action in window._build_pet_menu().actions() if not action.isSeparator()]
        assert "Workflows" in menu_labels
        assert "Settings" in menu_labels
        assert window.provider_badge.text() == "LOCAL - Ollama"

        window.core.model_router.set_mode("gemini")
        window.core.privacy.settings.allow_cloud_model = True
        window.core.privacy.settings.allow_gemini_api = True
        window._refresh_provider_badge()
        assert window.provider_badge.text() == "CLOUD - Gemini"
        window._refresh_provider_badge(
            FibiResponse("local rescue", "local rescue", "idle", "qwen2.5:1.5b", True)
        )
        assert window.provider_badge.text() == "FALLBACK - Ollama"

        window._quitting = True
        window.close()
        app.processEvents()

    print("Fibi v0.30.2 demo UI smoke tests passed.")


if __name__ == "__main__":
    run()
