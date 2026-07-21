"""Focused geometry and state tests for the Fibi v0.30.2 demo UI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from fibi.engines.types import FibiResponse
from fibi.life.life_engine import LifeEngine
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
    assert minimum == FibiWindow.COMPACT_SIZE
    assert fibi_window.sprite.height() >= 280
    rendered = fibi_window.sprite.rendered_sprite_rect()
    assert not rendered.isEmpty()
    assert rendered.height() >= 240
    assert fibi_window.sprite.rect().contains(rendered)


def test_compact_actions_live_in_pet_menu(fibi_window: FibiWindow) -> None:
    assert not hasattr(fibi_window, "action_footer")
    menu = fibi_window._build_pet_menu()
    assert [action.text() for action in menu.actions() if not action.isSeparator()] == [
        "Chat", "Settings", "Memory", "Commands", "Browser", "Workflows", "Health", "Hide", "Exit"
    ]


def test_sprite_click_and_right_click_open_pet_menu(
    fibi_window: FibiWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[object] = []

    def fake_menu(_checked: bool = False, global_position=None):
        opened.append(global_position)
        return fibi_window._build_pet_menu()

    monkeypatch.setattr(fibi_window, "_show_pet_menu", fake_menu)
    QTest.mouseClick(fibi_window.sprite, Qt.MouseButton.LeftButton)
    QTest.mouseClick(fibi_window.sprite, Qt.MouseButton.RightButton)
    assert len(opened) == 2


def test_expand_collapse_and_mode_persistence(fibi_window: FibiWindow) -> None:
    fibi_window._expand_chat()
    assert fibi_window.size() == FibiWindow.EXPANDED_SIZE
    assert fibi_window.window_mode == "expanded"
    assert fibi_window.core.app_settings.settings.window_mode == "expanded"
    assert fibi_window.collapse_button.isVisible()

    fibi_window._collapse_chat()
    assert fibi_window.size() == FibiWindow.COMPACT_SIZE
    assert fibi_window.window_mode == "compact"
    assert fibi_window.core.app_settings.settings.window_mode == "compact"


def test_double_click_focuses_chat(fibi_window: FibiWindow) -> None:
    QTest.mouseDClick(fibi_window.sprite, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert fibi_window.window_mode == "expanded"
    assert fibi_window.chat_input.hasFocus()


def test_window_position_is_saved(fibi_window: FibiWindow) -> None:
    fibi_window.core.handle_drag_end(123, 234)
    restored = LifeEngine(fibi_window.life.state_path)
    assert restored.window_position is not None
    assert (restored.window_position.x, restored.window_position.y) == (123, 234)


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
