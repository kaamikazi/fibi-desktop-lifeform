"""Lightweight transparent desktop-pet shell for Fibi's existing backend."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibi.engines import FibiCore
from fibi.engines.types import FibiResponse
from fibi.life.life_engine import LifeEngine
from fibi.ui.fibi_window import FibiSprite, FibiWindow, SpeechBubble


class PetChatPanel(QFrame):
    """Small transient text/voice entry panel owned by the pet."""

    INACTIVITY_MS = 30_000

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("petChatPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 58)
        self.setStyleSheet(
            "QFrame#petChatPanel { background: rgba(255,248,253,245); border: 1px solid #e69ab5; "
            "border-radius: 7px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Talk to Fibi...")
        self.input.setAccessibleName("Message Fibi")
        self.mic = QPushButton("Mic")
        self.mic.setFixedWidth(42)
        self.mic.setToolTip("Push to talk")
        self.send = QPushButton("Send")
        self.send.setFixedWidth(48)
        self.close_button = QPushButton("X")
        self.close_button.setFixedWidth(26)
        self.close_button.setToolTip("Close chat")
        for button in (self.mic, self.send, self.close_button):
            button.setFixedHeight(34)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.mic)
        layout.addWidget(self.send)
        layout.addWidget(self.close_button)

        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self.hide)
        self.input.textEdited.connect(lambda _text: self.touch())
        self.close_button.clicked.connect(self.hide)

    def open_and_focus(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()
        self.touch()

    def touch(self) -> None:
        self.inactivity_timer.start(self.INACTIVITY_MS)


class FibiPetWindow(FibiWindow):
    """Tiny UI adapter that delegates all behavior to one shared ``FibiCore``."""

    PET_SIZE = QSize(200, 220)
    BUBBLE_TIMEOUT_MS = 8_000

    def __init__(self, core: FibiCore | None = None, life: LifeEngine | None = None) -> None:
        self.control_center_window: FibiWindow | None = None
        super().__init__(core=core, life=life, control_center=False, startup_surface=True)

    def _setup_window(self) -> None:
        self.setWindowTitle("Fibi Pet")
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.core.app_settings.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.PET_SIZE)
        self.setAcceptDrops(True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self.bubble = SpeechBubble()
        self.bubble.setFixedSize(165, 88)
        layout.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignRight)

        self.sprite = FibiSprite(self.life, compact=True)
        layout.addWidget(self.sprite, 1)

        self.microphone_indicator = QLabel("MIC", self)
        self.microphone_indicator.setObjectName("microphoneIndicator")
        self.microphone_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.microphone_indicator.setFixedSize(72, 22)
        self.microphone_indicator.move(4, 91)
        self.microphone_indicator.setStyleSheet(
            "background: rgba(255,232,240,245); color: #8a2347; border: 1px solid #e69ab5; "
            "border-radius: 6px; font: bold 7pt 'Segoe UI';"
        )
        self.microphone_indicator.hide()

        self.chat_panel = PetChatPanel(self)
        self.chat_input = self.chat_panel.input
        self.mic_button = self.chat_panel.mic
        self.send_button = self.chat_panel.send
        self.chat_input.returnPressed.connect(self._send_message)
        self.send_button.clicked.connect(self._send_message)
        self.mic_button.clicked.connect(self._listen_voice)

        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.bubble.hide)
        self.pet_menu = self._build_pet_menu()
        for widget in (self, self.sprite, self.bubble):
            widget.installEventFilter(self)

    def _build_pet_menu(self) -> QMenu:
        menu = QMenu(self)

        talk = menu.addAction("Talk")
        talk.triggered.connect(self._expand_chat)

        wake = menu.addAction("Wake mode")
        wake.setCheckable(True)
        wake.setChecked(self.core.voice_settings.settings.wake_word_enabled)
        wake.triggered.connect(self._set_wake_mode)

        provider = menu.addMenu("Provider")
        gemini = provider.addAction("Gemini")
        ollama = provider.addAction("Ollama")
        gemini.triggered.connect(lambda: self._select_provider("gemini"))
        ollama.triggered.connect(lambda: self._select_provider("ollama"))

        memory = menu.addAction("Memory")
        memory.triggered.connect(self._open_memory_review)
        actions = menu.addAction("Actions")
        actions.triggered.connect(self._open_command_center)
        settings = menu.addAction("Settings")
        settings.triggered.connect(self._open_settings)
        control = menu.addAction("Control Center")
        control.triggered.connect(self._open_control_center_shell)
        menu.addSeparator()
        hide = menu.addAction("Hide")
        hide.triggered.connect(self.hide)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self._quit_from_tray)
        return menu

    def _show_pet_menu(self, _checked: bool = False, global_position: QPoint | None = None) -> QMenu:
        anchor = global_position or self.mapToGlobal(self.rect().center())
        wake = next((action for action in self.pet_menu.actions() if action.text() == "Wake mode"), None)
        if wake is not None:
            wake.setChecked(self.core.voice_settings.settings.wake_word_enabled)
        self.pet_menu.popup(anchor)
        return self.pet_menu

    def _set_wake_mode(self, enabled: bool) -> None:
        self._on_response(self.core.respond("/wake on" if enabled else "/wake off"))
        self._sync_wake_listener()

    def _select_provider(self, provider: str) -> None:
        self._on_response(self.core.respond(f"/provider use {provider}"))

    def _expand_chat(self) -> None:
        self._position_chat_panel()
        self.chat_panel.open_and_focus()

    def _collapse_chat(self) -> None:
        self.chat_panel.hide()

    def _position_chat_panel(self) -> None:
        screen = self.screen().availableGeometry() if self.screen() else None
        right = self.x() + self.width() + 8
        left = self.x() - self.chat_panel.width() - 8
        x = right if screen is None or right + self.chat_panel.width() <= screen.right() else left
        y = self.y() + self.height() - self.chat_panel.height()
        self.chat_panel.move(max(0, x), max(0, y))

    def moveEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        super().moveEvent(event)
        if hasattr(self, "chat_panel") and self.chat_panel.isVisible():
            self._position_chat_panel()

    def _open_control_center_shell(self) -> FibiWindow:
        if self.control_center_window is None:
            self.control_center_window = FibiWindow(
                core=self.core,
                life=self.life,
                control_center=True,
            )
        self.control_center_window.show()
        self.control_center_window.raise_()
        self.control_center_window.activateWindow()
        return self.control_center_window

    def _refresh_provider_badge(self, response: FibiResponse | None = None) -> None:
        return None

    def _set_session_chip(self) -> None:
        return None

    def _set_context_chip(self, text: str) -> None:
        return None

    def _on_response(self, result: FibiResponse) -> None:
        self.bubble.show()
        self.chat_panel.touch()
        super()._on_response(result)
        self.bubble_timer.start(self.BUBBLE_TIMEOUT_MS)
        pending = self.core.action_confirmations.pending()
        if pending is not None and result.model_used == "action-confirmation":
            QTimer.singleShot(0, lambda: self._confirm_pending_action(pending.required_confirmation_phrase, pending.action_type, pending.target))

    def _confirm_pending_action(self, phrase: str, action_type: str, target: str) -> None:
        description = f"Action: {action_type.replace('_', ' ')}\nTarget: {target or '(none)'}\n\nRun this action?"
        answer = QMessageBox.question(
            self,
            "Fibi action confirmation",
            description,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._ask_fibi(phrase)
        else:
            self.core.action_confirmations.cancel()
            self.bubble.show_text("action canceled.")

    def paintEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        # The pet shell itself has no panel; only sprite and bubble paint pixels.
        return None

    def closeEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        self.chat_panel.close()
        if self.control_center_window is not None:
            self.control_center_window.close()
        super().closeEvent(event)
