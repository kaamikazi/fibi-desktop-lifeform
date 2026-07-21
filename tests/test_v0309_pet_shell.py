"""Regression tests for the lightweight Fibi desktop-pet shell."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox

from fibi.ui.fibi_pet_window import FibiPetWindow
from fibi.ui.fibi_window import FibiSettingsDialog
from tests.smoke_v012_actions import make_core


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pet(tmp_path: Path, qt_app: QApplication):
    core, _, _ = make_core(tmp_path / "core", [], [])
    window = FibiPetWindow(core=core, life=core.life)
    window.sprite.animation_timer.stop()
    window.idle_timer.stop()
    window.show()
    qt_app.processEvents()
    yield window
    window._quitting = True
    window.close()
    qt_app.processEvents()


def test_pet_is_tiny_transparent_and_frameless(pet: FibiPetWindow) -> None:
    assert 140 <= pet.width() <= 220
    assert pet.height() <= 240
    assert pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert pet.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert pet.windowTitle() == "Fibi Pet"
    assert not pet.chat_panel.isVisible()


def test_pet_menu_has_required_quick_actions(pet: FibiPetWindow) -> None:
    labels = [action.text() for action in pet.pet_menu.actions() if not action.isSeparator()]
    assert labels == [
        "Talk", "Wake mode", "Provider", "Memory", "Actions", "Settings",
        "Control Center", "Hide", "Exit",
    ]


def test_click_opens_menu_and_double_click_opens_transient_chat(
    pet: FibiPetWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[QPoint | None] = []
    original = pet._show_pet_menu

    def record_menu(_checked: bool = False, global_position: QPoint | None = None):
        opened.append(global_position)
        return pet.pet_menu

    monkeypatch.setattr(pet, "_show_pet_menu", record_menu)
    QTest.mouseClick(pet.sprite, Qt.MouseButton.LeftButton)
    assert opened
    monkeypatch.setattr(pet, "_show_pet_menu", original)
    QTest.mouseDClick(pet.sprite, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert pet.chat_panel.isVisible()
    assert pet.chat_input.hasFocus()


def test_drag_saves_pet_position(pet: FibiPetWindow) -> None:
    start = pet.pos()
    center = pet.sprite.rect().center()
    QTest.mousePress(pet.sprite, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(pet.sprite, center + QPoint(18, 14), delay=20)
    QTest.mouseRelease(pet.sprite, Qt.MouseButton.LeftButton, pos=center + QPoint(18, 14))
    QApplication.processEvents()
    assert pet.pos() != start
    assert pet.life.window_position is not None
    assert (pet.life.window_position.x, pet.life.window_position.y) == (pet.x(), pet.y())


def test_control_center_is_lazy_and_reuses_exact_backend(pet: FibiPetWindow) -> None:
    assert pet.control_center_window is None
    control = pet._open_control_center_shell()
    QApplication.processEvents()
    assert control.core is pet.core
    assert control.life is pet.life
    assert control.core.memory_router is pet.core.memory_router
    assert control.core.model_router is pet.core.model_router
    assert control.core.desktop_actions is pet.core.desktop_actions
    assert control.core.permissions is pet.core.permissions
    assert control.core.tts_manager is pet.core.tts_manager
    assert control._owns_core is False
    assert control.windowTitle() == "Fibi Control Center"
    assert control.tray_icon is None
    assert not control.idle_timer.isActive()
    pet.core.voice_settings.settings.wake_word_enabled = True
    control._sync_wake_listener()
    assert control._wake_thread is None
    pet.core.voice_settings.settings.wake_word_enabled = False
    control.close()


def test_wake_mode_changes_only_by_manual_pet_control(
    pet: FibiPetWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pet, "_sync_wake_listener", lambda: None)
    provider = pet.core.model_router.selected_provider()
    rvc = pet.core.voice_skin_settings.settings.rvc_enabled
    assert not pet.core.voice_settings.settings.wake_word_enabled
    pet._set_wake_mode(True)
    assert pet.core.voice_settings.settings.wake_word_enabled
    assert not pet.core.voice_settings.settings.save_voice_audio
    pet._set_wake_mode(False)
    assert not pet.core.voice_settings.settings.wake_word_enabled
    assert pet.core.model_router.selected_provider() == provider
    assert pet.core.voice_skin_settings.settings.rvc_enabled == rvc


def test_sensitive_action_dialog_can_cancel_without_execution(
    pet: FibiPetWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intent = pet.core.action_intents.detect("create a folder named demo on Desktop")
    assert intent is not None
    pet.core.action_confirmations.create(intent)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    pet._confirm_pending_action("confirm create folder", "create_folder", "demo")
    assert pet.core.action_confirmations.pending() is None


def test_expression_aliases_are_visual_only(pet: FibiPetWindow) -> None:
    pet.sprite.set_expression("listening", force=True)
    assert pet.sprite.expression in {"thinking", "idle"}
    pet.sprite.set_expression("error", force=True)
    assert pet.sprite.expression in {"angry", "idle"}


def test_chat_panel_auto_closes_after_inactivity(pet: FibiPetWindow) -> None:
    pet._expand_chat()
    pet.chat_panel.inactivity_timer.timeout.emit()
    QApplication.processEvents()
    assert not pet.chat_panel.isVisible()


def test_windows_startup_setting_uses_mocked_autostart_only_on_save(
    pet: FibiPetWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeAutostart:
        def enable(self, confirm: bool = False):
            calls.append(f"enable:{confirm}")

        def disable(self):
            calls.append("disable")

    pet.core.autostart = FakeAutostart()  # type: ignore[assignment]
    monkeypatch.setattr(pet, "_sync_wake_listener", lambda: None)
    dialog = FibiSettingsDialog(pet.core, pet)
    assert not dialog.checks["start_pet_with_windows"].isChecked()
    dialog.checks["start_pet_with_windows"].setChecked(True)
    dialog._save()
    assert pet.core.app_settings.settings.start_pet_with_windows
    assert calls == ["enable:True"]
