"""Focused geometry and state tests for the Fibi v0.30.2 demo UI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from fibi.engines.types import FibiResponse
from fibi.ui import fibi_window as fibi_window_module
from fibi.ui.fibi_window import FibiWindow
from tests.smoke_v012_actions import make_core


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fibi_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    qt_app: QApplication,
):
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "data"))
    core_root = tmp_path / "core"

    def isolated_core(*, life):
        core, _, _ = make_core(core_root, [], [])
        core.life = life
        return core

    monkeypatch.setattr(fibi_window_module, "FibiCore", isolated_core)
    window = FibiWindow()
    window.sprite.animation_timer.stop()
    window.idle_timer.stop()
    window.show()
    window.resize(window.minimumSize())
    qt_app.processEvents()
    window.layout().activate()
    qt_app.processEvents()
    yield window
    window._quitting = True
    window.close()
    qt_app.processEvents()


def test_input_row_uses_layout_without_overlap(fibi_window: FibiWindow) -> None:
    assert fibi_window.input_bar.layout() is not None
    input_rect = fibi_window.chat_input.geometry()
    mic_rect = fibi_window.mic_button.geometry()
    send_rect = fibi_window.send_button.geometry()
    assert input_rect.width() >= fibi_window.chat_input.minimumWidth()
    assert not input_rect.intersects(mic_rect)
    assert not input_rect.intersects(send_rect)
    assert not mic_rect.intersects(send_rect)
    assert input_rect.right() < mic_rect.left() < send_rect.left()


def test_minimum_window_and_character_are_not_clipped(fibi_window: FibiWindow) -> None:
    minimum = fibi_window.minimumSize()
    assert minimum.width() >= 560
    assert minimum.height() >= 600
    assert fibi_window.sprite.height() >= 390
    rendered = fibi_window.sprite.rendered_sprite_rect()
    assert not rendered.isEmpty()
    assert rendered.height() >= 300
    assert fibi_window.sprite.rect().contains(rendered)


def test_compact_actions_remain_reachable(fibi_window: FibiWindow) -> None:
    buttons = {
        fibi_window.memory_review_button,
        fibi_window.workflow_button,
        fibi_window.browser_button,
        fibi_window.command_button,
        fibi_window.notebook_button,
        fibi_window.health_button,
        fibi_window.report_button,
        fibi_window.settings_button,
    }
    assert {button.text() for button in buttons} == {
        "Memory",
        "Workflows",
        "Browser",
        "Commands",
        "Notebook",
        "Health",
        "Report",
        "Settings",
    }
    assert all(button.isVisible() for button in buttons)
    assert all(button.parent() is fibi_window.action_footer for button in buttons)


def test_provider_badge_tracks_local_cloud_and_fallback(fibi_window: FibiWindow) -> None:
    fibi_window.core.model_router.set_mode("ollama")
    fibi_window.core.privacy.settings.allow_cloud_model = False
    fibi_window.core.privacy.settings.allow_gemini_api = False
    fibi_window._refresh_provider_badge()
    assert fibi_window.provider_badge.text() == "LOCAL - Ollama"

    fibi_window.core.model_router.set_mode("gemini")
    fibi_window.core.privacy.settings.allow_cloud_model = True
    fibi_window.core.privacy.settings.allow_gemini_api = True
    fibi_window._refresh_provider_badge()
    assert fibi_window.provider_badge.text() == "CLOUD - Gemini"

    fallback = FibiResponse("local rescue", "local rescue", "idle", "qwen2.5:1.5b", True)
    fibi_window._refresh_provider_badge(fallback)
    assert fibi_window.provider_badge.text() == "FALLBACK - Ollama"
    assert "key" not in fibi_window.provider_badge.toolTip().lower()


def test_visible_labels_never_show_api_key(fibi_window: FibiWindow) -> None:
    fake_key = "AIza" + "Z" * 28
    visible_text = "\n".join(
        [label.text() + "\n" + label.toolTip() for label in fibi_window.findChildren(QLabel)]
        + [button.text() + "\n" + button.toolTip() for button in fibi_window.findChildren(QPushButton)]
    )
    assert fake_key not in visible_text
    assert "GEMINI_API_KEY" not in visible_text


def test_demo_data_path_remains_isolated(fibi_window: FibiWindow, tmp_path: Path) -> None:
    database_path = Path(fibi_window.core.memory.database_path).resolve()
    assert database_path.is_relative_to(tmp_path.resolve())
    assert not database_path.is_relative_to((Path(__file__).resolve().parents[1] / "data").resolve())


def test_voice_preparation_indicator_does_not_replace_expression(fibi_window: FibiWindow) -> None:
    fibi_window.sprite.set_expression("sleepy", force=True)
    fibi_window._on_voice_preparing(False)
    assert fibi_window.bubble._voice_status == "speaking..."
    assert fibi_window.sprite.expression == "sleepy"

    fibi_window._on_voice_preparing(True)
    assert fibi_window.bubble._voice_status == "processing voice..."
    assert fibi_window.sprite.expression == "sleepy"

    fibi_window._on_speaking_finished(False)
    assert fibi_window.bubble._voice_status == ""
