"""Floating PyQt6 desktop window for Fibi."""

from __future__ import annotations

import threading
import math
import time
import logging
from contextlib import suppress
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QBitmap,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QRegion,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from fibi.engines import FibiCore
from fibi.engines.types import BubbleDisplayOptions, FibiResponse, MemoryDeleteRequest, MotionIntent
from fibi.life.life_engine import LifeEngine
from fibi.ui.expression_controller import ExpressionController
from fibi.voice.sounds import play_sound, play_sound_event

LOGGER = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parents[1]
ASSET_DIRS = [PROJECT_DIR / "assets", PROJECT_DIR / "ui" / "assets"]
EXPRESSIONS = ("idle", "happy", "thinking", "talking", "sleepy", "angry")
BLINK_EXPRESSION = "blink"


class FibiBridge(QObject):
    """Moves messages safely from worker threads back to the PyQt UI thread."""

    response_ready = pyqtSignal(object)
    voice_preparing = pyqtSignal(bool)
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal(bool)
    wake_detected = pyqtSignal()
    microphone_state = pyqtSignal(str)
    wake_state_changed = pyqtSignal(str)

def _asset_path(expression: str) -> Path | None:
    """Find an expression PNG in the supported asset folders."""
    for folder in ASSET_DIRS:
        path = folder / f"{expression}.png"
        if path.exists():
            return path
    return None


class FibiSprite(QWidget):
    """Animated chibi image that can switch expressions."""

    def __init__(self, life: LifeEngine, *, compact: bool = False) -> None:
        super().__init__()
        self.life = life
        self.expression = "idle"
        self.expression_controller = ExpressionController("idle")
        self.is_blinking = False
        self.float_offset = 0
        self.talk_offset = 0
        self.breath_scale = 1.0
        self.motion_offset_x = 0
        self.motion_offset_y = 0
        self.motion_scale_x = 1.0
        self.motion_scale_y = 1.0
        self._motion: MotionIntent | None = None
        self._motion_started_at = 0.0
        self.pixmaps = self._load_pixmaps()

        if compact:
            self.setMinimumSize(120, 145)
        else:
            self.setMinimumSize(190, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animate)
        self.animation_timer.start(30)

        self.blink_timer = QTimer(self)
        self.blink_timer.setSingleShot(True)
        self.blink_timer.timeout.connect(self._start_blink)
        self._schedule_next_blink()

    def _load_pixmaps(self) -> dict[str, QPixmap]:
        loaded: dict[str, QPixmap] = {}
        visible_bounds = QRect()

        for expression in (*EXPRESSIONS, BLINK_EXPRESSION):
            path = _asset_path(expression)
            if path is None:
                continue

            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                loaded[expression] = pixmap
                alpha_mask = QBitmap.fromImage(pixmap.toImage().createAlphaMask())
                bounds = QRegion(alpha_mask).boundingRect()
                if not bounds.isEmpty():
                    visible_bounds = bounds if visible_bounds.isEmpty() else visible_bounds.united(bounds)

        if visible_bounds.isEmpty():
            return loaded

        # The supplied expression canvases include large transparent margins.
        # Crop one shared padded rectangle so Fibi scales visibly without
        # expression-to-expression jumps or changes to the source assets.
        crop = visible_bounds.adjusted(-34, -34, 34, 34)
        return {
            expression: pixmap.copy(crop.intersected(pixmap.rect()))
            for expression, pixmap in loaded.items()
        }

    def set_expression(self, expression: str, temporary_ms: int = 0, force: bool = False) -> None:
        """Switch expression, falling back to idle when the PNG is missing."""
        expression = {
            "listening": "thinking",
            "error": "angry",
            "excited": "happy",
        }.get(expression, expression)
        if temporary_ms:
            selected = self.expression_controller.show_temporary(expression, temporary_ms)
        else:
            selected = self.expression_controller.set_persistent(expression, force=force)
        self.expression = selected if selected in self.pixmaps else "idle"
        self.update()

    def start_motion(self, intent: MotionIntent | None) -> None:
        if intent is None:
            return
        if self._motion and not self._motion.can_interrupt:
            return
        self._motion = intent
        self._motion_started_at = time.monotonic()

    def set_talking(self, talking: bool) -> None:
        self.is_blinking = False
        if talking:
            self.set_expression("talking", temporary_ms=60 * 60 * 1000)
        else:
            self.expression = self.expression_controller.clear_temporary()

    def _animate(self) -> None:
        self.float_offset, self.talk_offset, self.breath_scale = self.life.next_animation_frame()
        current_expression = self.expression_controller.current()
        self.expression = current_expression if current_expression in self.pixmaps else "idle"
        self._update_motion()
        self.update()

    def _update_motion(self) -> None:
        self.motion_offset_x = self.motion_offset_y = 0
        self.motion_scale_x = self.motion_scale_y = 1.0
        if self._motion is None:
            return
        if self.life.presence.value == "being_dragged" and self._motion.motion_name != "drag_squish":
            self._motion = None
            return
        elapsed = (time.monotonic() - self._motion_started_at) * 1000
        progress = min(1.0, elapsed / max(1, self._motion.duration_ms))
        wave = math.sin(progress * math.pi)
        strength = self._motion.intensity
        name = self._motion.motion_name
        if name in {"happy_bounce", "tiny_hop", "celebration_pop"}:
            self.motion_offset_y = int(-14 * strength * wave)
        if name == "sleepy_sway":
            self.motion_offset_x = int(math.sin(progress * math.pi * 2) * 8 * strength)
        elif name == "annoyed_shake":
            self.motion_offset_x = int(math.sin(progress * math.pi * 8) * 10 * strength)
        elif name == "thinking_tilt":
            self.motion_offset_x = int(7 * strength * wave)
        elif name == "wake_stretch":
            self.motion_scale_y = 1.0 + 0.1 * strength * wave
        elif name == "nap_settle":
            self.motion_offset_y = int(7 * strength * wave)
            self.motion_scale_y = 1.0 - 0.05 * strength * wave
        elif name == "drag_squish":
            self.motion_scale_x = 1.0 + 0.08 * strength * wave
            self.motion_scale_y = 1.0 - 0.08 * strength * wave
        elif name == "pet_recoil":
            self.motion_offset_y = int(8 * strength * wave)
        if name in {"celebration_pop", "happy_bounce"}:
            self.motion_scale_x = self.motion_scale_y = 1.0 + 0.08 * strength * wave
        if progress >= 1.0:
            self._motion = None

    def _schedule_next_blink(self) -> None:
        """Blink only when blink.png exists; otherwise the timer stays quiet."""
        if BLINK_EXPRESSION not in self.pixmaps:
            return

        self.blink_timer.start(self.life.random_blink_delay_ms())

    def _start_blink(self) -> None:
        if self.life.is_speaking or BLINK_EXPRESSION not in self.pixmaps:
            self._schedule_next_blink()
            return

        self.is_blinking = True
        self.update()
        QTimer.singleShot(130, self._finish_blink)

    def _finish_blink(self) -> None:
        self.is_blinking = False
        self.update()
        self._schedule_next_blink()

    def rendered_sprite_rect(self) -> QRect:
        """Return the current sprite bounds using the same math as painting."""

        pixmap = self.pixmaps.get(BLINK_EXPRESSION) if self.is_blinking else None
        pixmap = pixmap or self.pixmaps.get(self.expression) or self.pixmaps.get("idle")
        if pixmap is None:
            return QRect()
        target_width = max(1, int((self.width() - 10) * self.breath_scale * self.motion_scale_x))
        target_height = max(1, int((self.height() - 24) * self.breath_scale * self.motion_scale_y))
        scaled = pixmap.scaled(
            QSize(target_width, target_height),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2 + self.motion_offset_x
        y = (
            (self.height() - scaled.height()) // 2
            + self.float_offset
            + self.talk_offset
            + self.motion_offset_y
        )
        return QRect(x, y, scaled.width(), scaled.height())

    def paintEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        width = self.width()
        height = self.height()
        shadow = QRadialGradient(width // 2, height - 14, 60)
        shadow.setColorAt(0, QColor(0, 0, 0, 50))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(shadow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(width // 2 - 60, height - 30, 120, 24)

        pixmap = self.pixmaps.get(BLINK_EXPRESSION) if self.is_blinking else None
        pixmap = pixmap or self.pixmaps.get(self.expression) or self.pixmaps.get("idle")
        if pixmap:
            scaled = pixmap.scaled(
                self.rendered_sprite_rect().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(self.rendered_sprite_rect().topLeft(), scaled)
            return

        painter.setPen(QPen(QColor(255, 225, 245)))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(QRect(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, "Fibi")


class SpeechBubble(QWidget):
    """Small rounded chat bubble beside Fibi."""

    def __init__(self) -> None:
        super().__init__()
        self.text = "Hi, I'm Fibi!"
        self._full_text = self.text
        self._last_text = ""
        self._typing_index = 0
        self._active = True
        self._speaking = False
        self._voice_status = ""
        self._auto_hide_ms = 0
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self._type_next)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide)
        self.setMinimumSize(130, 88)
        self.setMaximumSize(165, 132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def show_text(self, text: str, options: BubbleDisplayOptions | None = None) -> None:
        options = options or BubbleDisplayOptions()
        cleaned = text.strip() or "..."
        if cleaned == self._last_text and not options.allow_repeat:
            return
        self._last_text = cleaned
        self._full_text = cleaned
        self._active = True
        self.hide_timer.stop()
        self.typing_timer.stop()
        if options.typing_style == "instant":
            self.text = cleaned
        else:
            self.text = ""
            self._typing_index = 0
            interval = {"excited": 18, "thinking": 38, "soft": 45, "sleepy": 75}.get(options.typing_style, 40)
            self.typing_timer.start(interval)
        if options.auto_hide_ms > 0:
            self._auto_hide_ms = options.auto_hide_ms
            self.hide_timer.start(options.auto_hide_ms)
        else:
            self._auto_hide_ms = 0
        self.update()

    def set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
        if speaking:
            self._active = True
            self.hide_timer.stop()
        elif self._auto_hide_ms > 0:
            self.hide_timer.start(self._auto_hide_ms)
        self.update()

    def set_voice_status(self, status: str) -> None:
        """Show a small non-blocking voice state beneath the reply."""

        self._voice_status = status.strip()
        self.update()

    def _type_next(self) -> None:
        self._typing_index += 1
        self.text = self._full_text[:self._typing_index]
        if self._typing_index >= len(self._full_text):
            self.typing_timer.stop()
        self.update()

    def _auto_hide(self) -> None:
        if not self._speaking:
            self._active = False
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._active:
            return

        width = self.width()
        height = self.height()
        bubble_rect = QRect(14, 6, width - 20, height - 14)

        painter.setBrush(QColor(255, 248, 253, 238))
        painter.setPen(QPen(QColor(244, 155, 205), 2))
        painter.drawRoundedRect(bubble_rect, 16, 16)

        tail = QPainterPath()
        tail.moveTo(15, height - 34)
        tail.lineTo(2, height - 22)
        tail.lineTo(18, height - 18)
        tail.closeSubpath()
        painter.setBrush(QColor(255, 248, 253, 238))
        painter.setPen(QPen(QColor(244, 155, 205), 2))
        painter.drawPath(tail)

        painter.setPen(QColor(58, 35, 70))
        painter.setFont(QFont("Segoe UI", 9))
        text_rect = bubble_rect.adjusted(12, 9, -12, -22 if self._voice_status else -9)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self.text,
        )
        if self._voice_status:
            painter.setPen(QColor(142, 92, 132))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(
                bubble_rect.adjusted(12, 0, -12, -7),
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                self._voice_status,
            )


class FibiNotebookDialog(QDialog):
    """Small local notebook for viewing and caring for Fibi's stored crumbs."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.entries = []
        self.setWindowTitle("Fibi's notebook")
        self.setMinimumSize(520, 420)
        self._build_ui()
        self._load_section("memories")

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        left = QVBoxLayout()
        for label, section in (
            ("things Fibi remembers", "memories"),
            ("journal", "journal"),
            ("dream crumbs", "dreams"),
            ("tiny preferences", "preferences"),
            ("project creatures", "projects"),
            ("relationship", "relationship"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, value=section: self._load_section(value))
            left.addWidget(button)
        self.export_button = QPushButton("export local bundle")
        self.export_button.clicked.connect(self._export)
        left.addWidget(self.export_button)
        self.clear_dreams_button = QPushButton("clear dreams")
        self.clear_dreams_button.clicked.connect(self._clear_dreams)
        left.addWidget(self.clear_dreams_button)
        self.clear_journal_button = QPushButton("clear journal")
        self.clear_journal_button.clicked.connect(self._clear_journal)
        left.addWidget(self.clear_journal_button)
        left.addStretch(1)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.status = QLabel("tiny memory pile")
        right.addWidget(self.status)
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._select_entry)
        right.addWidget(self.list_widget, 2)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("selected crumb...")
        right.addWidget(self.editor, 2)

        actions = QHBoxLayout()
        self.save_button = QPushButton("save edit")
        self.save_button.clicked.connect(self._save_edit)
        actions.addWidget(self.save_button)
        self.delete_button = QPushButton("forget selected")
        self.delete_button.clicked.connect(self._delete_selected)
        actions.addWidget(self.delete_button)
        right.addLayout(actions)
        layout.addLayout(right, 2)

        self.setStyleSheet(
            """
            QDialog { background: #fff7fc; color: #39243f; }
            QPushButton {
                background: #f49bcd;
                border: 0;
                border-radius: 8px;
                color: white;
                font: 9pt 'Segoe UI';
                padding: 7px 9px;
            }
            QPushButton:hover { background: #ec73b4; }
            QListWidget, QTextEdit {
                background: rgba(255,255,255,235);
                border: 1px solid #efb4d3;
                border-radius: 8px;
                padding: 6px;
                font: 9pt 'Segoe UI';
            }
            QLabel { font: bold 10pt 'Segoe UI'; color: #5b3768; }
            """
        )

    def _load_section(self, section: str) -> None:
        self.current_section = section
        self.entries = self.core.memory_care.notebook_entries(section, limit=50)
        self.list_widget.clear()
        for entry in self.entries:
            self.list_widget.addItem(entry.title)
        self.status.setText(section.replace("_", " "))
        self.editor.setPlainText("")

    def _select_entry(self, index: int) -> None:
        if index < 0 or index >= len(self.entries):
            self.editor.setPlainText("")
            return
        entry = self.entries[index]
        details = entry.body
        if entry.source_info:
            details += (
                f"\n\nsource: {entry.source_info.source}"
                f"\nconfidence: {entry.source_info.confidence:.2f}"
                f"\ncreated: {entry.source_info.created_at}"
                f"\nupdated: {entry.source_info.updated_at}"
            )
        self.editor.setPlainText(details)

    def _save_edit(self) -> None:
        index = self.list_widget.currentRow()
        if index < 0 or index >= len(self.entries):
            self.status.setText("pick a crumb first.")
            return
        entry = self.entries[index]
        if self.current_section != "memories" or not isinstance(entry.entry_id, int):
            self.status.setText("only memory crumbs can be edited here.")
            return
        result = self.core.memory_care.edit_memory(entry.entry_id, self.editor.toPlainText())
        self.status.setText(result.message)
        self._load_section("memories")

    def _delete_selected(self) -> None:
        index = self.list_widget.currentRow()
        if index < 0 or index >= len(self.entries):
            self.status.setText("pick a crumb first.")
            return
        entry = self.entries[index]
        if self.current_section != "memories" or not isinstance(entry.entry_id, int):
            self.status.setText("only memory crumbs can be forgotten here.")
            return
        result = self.core.memory_care.delete_memory(entry.entry_id, confirm=True)
        self.status.setText(result.message)
        self._load_section("memories")

    def _export(self) -> None:
        result = self.core.memory_care.export_bundle(self.core.privacy.settings)
        self.status.setText(result.export_path or result.message)

    def _clear_dreams(self) -> None:
        result = self.core.memory_care.clear_dreams(confirm=True)
        self.status.setText(result.message)
        self._load_section("dreams")

    def _clear_journal(self) -> None:
        result = self.core.memory_care.clear_journal(confirm=True)
        self.status.setText(result.message)
        self._load_section("journal")


class FibiSettingsDialog(QDialog):
    """Readable, responsive local settings panel."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.setWindowTitle("Fibi settings")
        self.setMinimumSize(600, 500)
        self.resize(720, 620)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        heading = QLabel("Fibi settings")
        heading.setObjectName("settingsHeading")
        subtitle = QLabel("Local controls for Fibi's presence, privacy, language, and voice.")
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsTabs")
        self.tabs.setUsesScrollButtons(True)
        layout.addWidget(self.tabs, 1)
        self.checks: dict[str, QCheckBox] = {}

        def add_tab(
            name: str,
            section_title: str,
            items: list[tuple[str, str, bool]],
        ) -> QVBoxLayout:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            page = QWidget()
            page.setObjectName(f"{name.lower()}SettingsPage")
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(12, 14, 12, 14)
            page_layout.setSpacing(14)
            group = QGroupBox(section_title)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(14, 18, 14, 14)
            group_layout.setSpacing(10)
            for key, label, checked in items:
                box = QCheckBox(label)
                box.setChecked(bool(checked))
                box.setObjectName(f"setting_{key}")
                self.checks[key] = box
                group_layout.addWidget(box)
            page_layout.addWidget(group)
            page_layout.addStretch(1)
            scroll.setWidget(page)
            self.tabs.addTab(scroll, name)
            return page_layout

        settings = self.core.app_settings.settings
        privacy = self.core.privacy.settings
        general_layout = add_tab("General", "Desktop presence", [
            ("start_minimized", "Start minimized", settings.start_minimized),
            ("start_pet_with_windows", "Start Fibi Pet with Windows", settings.start_pet_with_windows),
            ("minimize_to_tray", "Minimize to tray", settings.minimize_to_tray),
            ("always_on_top", "Always on top", settings.always_on_top),
            ("click_through_mode", "Click-through mode", settings.click_through_mode),
        ])
        setup = QPushButton("First-run setup")
        setup.setObjectName("firstRunSetupButton")
        setup.clicked.connect(self._open_setup)
        general_layout.insertWidget(general_layout.count() - 1, setup)

        behavior_layout = add_tab("Behavior", "Presence and behavior", [
            ("allow_idle_bubbles", "Idle bubbles", privacy.allow_idle_bubbles),
            ("quiet_mode", "Quiet mode", self.core.boundary.quiet.active),
            ("bubble_typing_effect", "Bubble typing effect", settings.bubble_typing_effect),
            ("allow_project_checks", "Project checks", settings.allow_project_checks),
            ("speak_utility_replies", "Speak utility replies", self.core.tts_manager.speak_utility_replies),
        ])
        reply_group = QGroupBox("Reply length")
        reply_layout = QHBoxLayout(reply_group)
        reply_layout.addWidget(QLabel("Default style"))
        self.reply_style_combo = QComboBox()
        self.reply_style_combo.setObjectName("replyStyleCombo")
        self.reply_style_combo.addItem("Concise", "concise")
        self.reply_style_combo.addItem("Normal", "normal")
        self.reply_style_combo.addItem("Detailed", "detailed")
        reply_index = self.reply_style_combo.findData(settings.reply_style)
        self.reply_style_combo.setCurrentIndex(max(0, reply_index))
        reply_layout.addWidget(self.reply_style_combo, 1)
        behavior_layout.insertWidget(behavior_layout.count() - 1, reply_group)
        add_tab("Privacy", "Local privacy controls", [
            ("allow_memory_learning", "Memory learning", privacy.allow_memory_learning),
            ("allow_journal", "Journal", privacy.allow_journal),
            ("allow_dreams", "Dreams", privacy.allow_dreams),
            ("allow_inner_thoughts", "Inner thoughts", privacy.allow_inner_thoughts),
            ("allow_foreground_app_observation", "Foreground app observation", privacy.allow_foreground_app_observation),
            ("allow_window_title_observation", "Window title observation", privacy.allow_window_title_observation),
            ("allow_clipboard_observation", "Clipboard observation", privacy.allow_clipboard_observation),
        ])

        models_layout = add_tab("Models", "Model permissions", [
            ("allow_ollama", "Ollama enabled", privacy.allow_ollama),
            ("allow_cloud_model", "Cloud language model enabled", privacy.allow_cloud_model),
            ("allow_nvidia_api", "NVIDIA/API provider enabled", privacy.allow_nvidia_api),
            ("allow_gemini_api", "Gemini API enabled", privacy.allow_gemini_api),
        ])
        provider_group = QGroupBox("Language Provider")
        provider_group.setObjectName("providerSection")
        provider_layout = QVBoxLayout(provider_group)
        provider_layout.setContentsMargins(14, 18, 14, 14)
        provider_layout.setSpacing(10)
        provider_row = QHBoxLayout()
        provider_row.addWidget(QLabel("Provider"))
        self.provider_combo = QComboBox()
        self.provider_combo.setObjectName("languageProviderCombo")
        self.provider_combo.addItem("LOCAL - Ollama", "ollama")
        self.provider_combo.addItem("CLOUD - Gemini", "gemini")
        selected = self.core.get_selected_provider_id()
        self.provider_combo.setCurrentIndex(1 if selected == "gemini" else 0)
        self.provider_combo.currentIndexChanged.connect(self._refresh_pending_provider_labels)
        provider_row.addWidget(self.provider_combo, 1)
        provider_layout.addLayout(provider_row)
        self.provider_status_badge = QLabel(self._selected_provider_label())
        self.provider_status_badge.setObjectName("providerStatusBadge")
        self.provider_status_badge.setWordWrap(True)
        provider_layout.addWidget(self.provider_status_badge)
        self.provider_fallback_checkbox = QCheckBox("Allow automatic provider fallback")
        self.provider_fallback_checkbox.setChecked(
            self.core.app_settings.settings.automatic_provider_fallback
        )
        self.provider_fallback_checkbox.toggled.connect(self._refresh_pending_provider_labels)
        provider_layout.addWidget(self.provider_fallback_checkbox)
        self.provider_fallback_status = QLabel(self._automatic_fallback_label())
        provider_layout.addWidget(self.provider_fallback_status)
        self.cloud_label = QLabel(
            f"Gemini API key: {'configured' if self.core.get_provider_model_metadata('gemini').configured else 'not configured'}\n"
            + self.core.get_provider_status()
        )
        self.cloud_label.setObjectName("providerStatusDetails")
        self.cloud_label.setWordWrap(True)
        self.cloud_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        provider_layout.addWidget(self.cloud_label)
        provider_buttons = QHBoxLayout()
        self.provider_privacy_button = QPushButton("Cloud privacy")
        self.provider_privacy_button.clicked.connect(self._show_provider_privacy)
        self.provider_test_button = QPushButton("Test provider")
        self.provider_test_button.clicked.connect(self._test_provider)
        provider_buttons.addWidget(self.provider_privacy_button)
        provider_buttons.addWidget(self.provider_test_button)
        provider_buttons.addStretch(1)
        provider_layout.addLayout(provider_buttons)
        models_layout.insertWidget(models_layout.count() - 1, provider_group)

        voice_layout = add_tab("Voice", "Voice basics", [
            ("allow_tts", "TTS voice", privacy.allow_tts),
            ("allow_voice_input", "Voice input", self.core.voice_settings.settings.allow_voice_input),
            ("wake_word_enabled", "Wake Word Mode: oi fibi (local)", self.core.voice_settings.settings.wake_word_enabled),
            ("allow_sounds", "Sounds", privacy.allow_sounds),
        ])
        processing_group = QGroupBox("Voice processing")
        processing_group.setObjectName("voiceProcessingSection")
        processing_layout = QVBoxLayout(processing_group)
        rvc_enabled = bool(
            self.core.voice_skin_settings.settings.allow_rvc_voice_skin
            and self.core.voice_skin_settings.settings.rvc_enabled
        )
        self.rvc_checkbox = QCheckBox("Use RVC voice processing")
        self.rvc_checkbox.setObjectName("rvcEnabledCheckbox")
        self.rvc_checkbox.setChecked(rvc_enabled)
        self.rvc_checkbox.toggled.connect(self._refresh_pending_provider_labels)
        processing_layout.addWidget(self.rvc_checkbox)
        self.rvc_status_label = QLabel(self._rvc_label())
        processing_layout.addWidget(self.rvc_status_label)
        self.rvc_warning_label = QLabel("RVC may add significant processing time on CPU.")
        self.rvc_warning_label.setObjectName("rvcWarning")
        self.rvc_warning_label.setWordWrap(True)
        processing_layout.addWidget(self.rvc_warning_label)
        wake_group = QGroupBox("Wake detector")
        wake_layout = QVBoxLayout(wake_group)
        wake_row = QHBoxLayout()
        wake_row.addWidget(QLabel("Sensitivity"))
        self.wake_sensitivity_spin = QDoubleSpinBox()
        self.wake_sensitivity_spin.setObjectName("wakeSensitivitySpin")
        self.wake_sensitivity_spin.setRange(0.45, 0.95)
        self.wake_sensitivity_spin.setSingleStep(0.05)
        self.wake_sensitivity_spin.setDecimals(2)
        self.wake_sensitivity_spin.setValue(self.core.voice_settings.settings.wake_word_sensitivity)
        wake_row.addWidget(self.wake_sensitivity_spin)
        wake_layout.addLayout(wake_row)
        self.wake_detector_status = QLabel()
        self.wake_detector_status.setObjectName("wakeDetectorStatus")
        self.wake_detector_status.setWordWrap(True)
        wake_layout.addWidget(self.wake_detector_status)
        self.checks["wake_word_enabled"].toggled.connect(self._refresh_wake_status)
        self._refresh_wake_status()
        processing_layout.addWidget(wake_group)
        voice_layout.insertWidget(voice_layout.count() - 1, processing_group)

        actions_layout = add_tab("Actions", "Desktop actions", [
            ("allow_desktop_actions", "Safe actions", self.core.action_settings.settings.allow_desktop_actions),
        ])
        applications_group = QGroupBox("Applications")
        applications_layout = QVBoxLayout(applications_group)
        self.application_list = QListWidget()
        self.application_list.setObjectName("registeredApplicationsList")
        self.application_list.currentRowChanged.connect(self._load_selected_application)
        applications_layout.addWidget(self.application_list)
        self.application_name_input = QLineEdit()
        self.application_name_input.setObjectName("applicationNameInput")
        self.application_name_input.setPlaceholderText("Application name")
        applications_layout.addWidget(self.application_name_input)
        path_row = QHBoxLayout()
        self.application_path_input = QLineEdit()
        self.application_path_input.setObjectName("applicationPathInput")
        self.application_path_input.setPlaceholderText(r"C:\Path\Application.exe")
        browse_application = QPushButton("Browse")
        browse_application.setObjectName("browseApplicationButton")
        browse_application.clicked.connect(self._browse_application)
        path_row.addWidget(self.application_path_input, 1)
        path_row.addWidget(browse_application)
        applications_layout.addLayout(path_row)
        application_buttons = QHBoxLayout()
        test_application = QPushButton("Test")
        test_application.setObjectName("testApplicationButton")
        test_application.setToolTip("Validate the executable without launching it")
        test_application.clicked.connect(self._test_application_path)
        save_application = QPushButton("Save")
        save_application.setObjectName("saveApplicationButton")
        save_application.clicked.connect(self._save_application)
        remove_application = QPushButton("Remove")
        remove_application.setObjectName("removeApplicationButton")
        remove_application.clicked.connect(self._remove_application)
        application_buttons.addWidget(test_application)
        application_buttons.addWidget(save_application)
        application_buttons.addWidget(remove_application)
        application_buttons.addStretch(1)
        applications_layout.addLayout(application_buttons)
        self.application_status = QLabel("Only existing .exe files are accepted. No arguments or scripts.")
        self.application_status.setObjectName("applicationStatus")
        self.application_status.setWordWrap(True)
        applications_layout.addWidget(self.application_status)
        actions_layout.insertWidget(actions_layout.count() - 1, applications_group)
        self._refresh_registered_applications()
        add_tab("Performance", "Diagnostics", [
            ("performance_debug_logs", "Performance debug logs", settings.performance_debug_logs),
        ])

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.setObjectName("settingsCloseButton")
        close.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setObjectName("settingsSaveButton")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(close)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        self.setStyleSheet(self._settings_stylesheet())

    def _provider_status_heading(self) -> str:
        configured = self.core.get_provider_model_metadata("gemini").configured
        selected = self.core.get_selected_provider_id()
        provider = "CLOUD - Gemini" if selected == "gemini" else "LOCAL - Ollama"
        return f"{provider} | Gemini {'configured' if configured else 'not configured'}"

    def _selected_provider_label(self) -> str:
        selected = str(self.provider_combo.currentData()) if hasattr(self, "provider_combo") else self.core.get_selected_provider_id()
        return f"Selected provider: {'Gemini' if selected == 'gemini' else 'Ollama'}"

    def _automatic_fallback_label(self) -> str:
        enabled = self.provider_fallback_checkbox.isChecked()
        return f"Automatic fallback: {'On' if enabled else 'Off'}"

    def _rvc_label(self) -> str:
        return f"RVC: {'On' if self.rvc_checkbox.isChecked() else 'Off'}"

    def _refresh_pending_provider_labels(self, _value=None) -> None:
        """Reflect pending dialog choices without changing runtime settings."""

        self.provider_status_badge.setText(self._selected_provider_label())
        self.provider_fallback_status.setText(self._automatic_fallback_label())
        self.rvc_status_label.setText(self._rvc_label())

    def _refresh_wake_status(self, _value=None) -> None:
        enabled = self.checks["wake_word_enabled"].isChecked()
        microphone = self.checks["allow_voice_input"].isChecked() or enabled
        self.wake_detector_status.setText(
            f"Microphone: {'active' if microphone and enabled else 'inactive'} | "
            f"Wake detector: {'active' if enabled else 'inactive'}"
        )

    @staticmethod
    def _settings_stylesheet() -> str:
        return """
            QDialog { background: #fff7fc; color: #35213d; }
            QLabel, QCheckBox, QComboBox, QPushButton, QGroupBox {
                color: #35213d; font: 9pt 'Segoe UI';
            }
            QLabel#settingsHeading { color: #3d2448; font: bold 15pt 'Segoe UI'; }
            QLabel#settingsSubtitle { color: #684c72; }
            QTabWidget::pane {
                border: 1px solid #d9bed6; border-radius: 7px;
                background: #fffafd; top: -1px;
            }
            QTabBar::tab {
                background: #ead8e9; color: #4b3055;
                border: 1px solid #cfb1cb; padding: 8px 7px;
                min-width: 44px; font: 8pt 'Segoe UI';
            }
            QTabBar::tab:selected {
                background: #7a4f8d; color: #ffffff;
                border-color: #69407c; font-weight: bold;
            }
            QTabBar::tab:hover:!selected { background: #f3e5f1; }
            QScrollArea, QScrollArea > QWidget > QWidget { background: #fffafd; }
            QGroupBox {
                background: #ffffff; border: 1px solid #ddc5db;
                border-radius: 7px; margin-top: 10px; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
                color: #563460; background: #fffafd;
            }
            QCheckBox { spacing: 8px; min-height: 24px; }
            QCheckBox::indicator { width: 17px; height: 17px; }
            QComboBox {
                background: #ffffff; border: 1px solid #b996b8;
                border-radius: 6px; padding: 6px 9px; min-height: 20px;
            }
            QLabel#providerStatusBadge {
                background: #f1e7f5; color: #4c2d5b;
                border: 1px solid #c9acd2; border-radius: 6px;
                padding: 7px 9px; font-weight: bold;
            }
            QLabel#providerStatusDetails { color: #523b5b; }
            QLabel#rvcWarning {
                background: #fff4d9; color: #654814;
                border: 1px solid #dfc174; border-radius: 6px; padding: 7px;
            }
            QPushButton {
                background: #f2e5f0; color: #412849;
                border: 1px solid #bd9abd; border-radius: 6px;
                padding: 7px 12px; min-height: 22px;
            }
            QPushButton:hover { background: #ead5e8; }
            QPushButton:pressed { background: #dfc3dc; }
            QPushButton:disabled {
                background: #eee9ed; color: #8a7b88; border-color: #d4cbd2;
            }
            QPushButton#settingsSaveButton {
                background: #765087; color: #ffffff;
                border-color: #654075; font-weight: bold;
            }
        """

    def _save(self) -> None:
        previous_autostart = self.core.app_settings.settings.start_pet_with_windows
        requested_autostart = self.checks["start_pet_with_windows"].isChecked()
        self.core.update_settings(
            start_minimized=self.checks["start_minimized"].isChecked(),
            start_pet_with_windows=requested_autostart,
            minimize_to_tray=self.checks["minimize_to_tray"].isChecked(),
            always_on_top=self.checks["always_on_top"].isChecked(),
            click_through_mode=self.checks["click_through_mode"].isChecked(),
            bubble_typing_effect=self.checks["bubble_typing_effect"].isChecked(),
            performance_debug_logs=self.checks["performance_debug_logs"].isChecked(),
            allow_project_checks=self.checks["allow_project_checks"].isChecked(),
            automatic_provider_fallback=self.provider_fallback_checkbox.isChecked(),
            reply_style=str(self.reply_style_combo.currentData()),
        )
        if requested_autostart != previous_autostart:
            if requested_autostart:
                self.core.autostart.enable(confirm=True)
            else:
                self.core.autostart.disable()
        self.core.tts_manager.speak_utility_replies = self.checks["speak_utility_replies"].isChecked()
        wake_enabled = self.checks["wake_word_enabled"].isChecked()
        self.core.update_voice_settings(
            allow_voice_input=self.checks["allow_voice_input"].isChecked() or wake_enabled,
            wake_word_enabled=wake_enabled,
            wake_word_sensitivity=self.wake_sensitivity_spin.value(),
            save_voice_audio=False,
        )
        use_rvc = self.rvc_checkbox.isChecked()
        self.core.voice_skin_settings.update(allow_rvc_voice_skin=use_rvc, rvc_enabled=use_rvc)
        self.core.action_settings.update(allow_desktop_actions=self.checks["allow_desktop_actions"].isChecked())
        self.core.privacy.update(
            allow_idle_bubbles=self.checks["allow_idle_bubbles"].isChecked(),
            allow_memory_learning=self.checks["allow_memory_learning"].isChecked(),
            allow_journal=self.checks["allow_journal"].isChecked(),
            allow_dreams=self.checks["allow_dreams"].isChecked(),
            allow_inner_thoughts=self.checks["allow_inner_thoughts"].isChecked(),
            allow_foreground_app_observation=self.checks["allow_foreground_app_observation"].isChecked(),
            allow_window_title_observation=self.checks["allow_window_title_observation"].isChecked(),
            allow_clipboard_observation=self.checks["allow_clipboard_observation"].isChecked(),
            allow_ollama=self.checks["allow_ollama"].isChecked(),
            allow_cloud_model=self.checks["allow_cloud_model"].isChecked(),
            allow_nvidia_api=self.checks["allow_nvidia_api"].isChecked(),
            allow_gemini_api=self.checks["allow_gemini_api"].isChecked(),
            allow_tts=self.checks["allow_tts"].isChecked(),
            allow_sounds=self.checks["allow_sounds"].isChecked(),
        )
        selected_provider = str(self.provider_combo.currentData())
        self.core.handle_local_command(f"/provider use {selected_provider}")
        parent = self.parent()
        if parent is not None and hasattr(parent, "_refresh_provider_badge"):
            parent._refresh_provider_badge()
        if parent is not None and hasattr(parent, "_sync_wake_listener"):
            parent._sync_wake_listener()
        if self.checks["quiet_mode"].isChecked():
            self.core.boundary.enable_quiet(None, reason="settings")
        else:
            self.core.boundary.disable_quiet()
        self.accept()

    def _refresh_registered_applications(self) -> None:
        self.application_list.clear()
        for entry in self.core.app_index.manual_entries():
            self.application_list.addItem(f"{entry.display_name}  |  {entry.path}")

    def _load_selected_application(self, row: int) -> None:
        entries = self.core.app_index.manual_entries()
        if 0 <= row < len(entries):
            self.application_name_input.setText(entries[row].display_name)
            self.application_path_input.setText(entries[row].path)

    def _browse_application(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(
            self,
            "Choose application",
            str(Path.home()),
            "Windows applications (*.exe)",
        )
        if selected:
            self.application_path_input.setText(selected)
            if not self.application_name_input.text().strip():
                self.application_name_input.setText(Path(selected).stem)

    def _test_application_path(self) -> None:
        valid, message = self.core.app_index.validate_manual_executable(
            self.application_path_input.text().strip()
        )
        self.application_status.setText("Executable is valid." if valid else message)

    def _save_application(self) -> None:
        saved, message = self.core.app_index.register_manual(
            self.application_name_input.text(),
            self.application_path_input.text(),
        )
        self.application_status.setText(message)
        if saved:
            self._refresh_registered_applications()

    def _remove_application(self) -> None:
        name = self.application_name_input.text().strip()
        if not name:
            self.application_status.setText("Select a registered application first.")
            return
        removed = self.core.app_index.remove_entry(name)
        self.application_status.setText(f"{name} removed." if removed else "Registered application was not found.")
        if removed:
            self.application_name_input.clear()
            self.application_path_input.clear()
            self._refresh_registered_applications()

    def _test_provider(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_ask_fibi"):
            self.accept()
            parent._ask_fibi("/provider test")
            return
        result = self.core.handle_local_command("/provider test")
        self.cloud_label.setText(result.response.display_text if result.response else "Provider test unavailable.")

    def _show_provider_privacy(self) -> None:
        result = self.core.handle_local_command("/provider privacy")
        text = result.response.display_text if result.response else "Cloud privacy details unavailable."
        self.cloud_label.setText(text)

    def _open_setup(self) -> None:
        FibiFirstRunDialog(self.core, self).exec()


class FibiFirstRunDialog(QDialog):
    """Tiny first-run setup flow."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.setWindowTitle("hi. i live here now.")
        self.setMinimumSize(420, 260)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("hi. i live here now."))
        layout.addWidget(QLabel("cloud off. secrets safe."))
        layout.addWidget(QLabel("voice ears are closed unless you open them."))
        layout.addWidget(QLabel("RVC is optional. tiny creature can start without it."))
        self.voice = QCheckBox("voice output")
        self.voice.setChecked(self.core.privacy.settings.allow_tts)
        layout.addWidget(self.voice)
        self.memory = QCheckBox("let Fibi remember clear things")
        self.memory.setChecked(self.core.privacy.settings.allow_memory_learning)
        layout.addWidget(self.memory)
        buttons = QHBoxLayout()
        finish = QPushButton("finish")
        finish.clicked.connect(self._finish)
        skip = QPushButton("skip")
        skip.clicked.connect(self._skip)
        buttons.addWidget(finish)
        buttons.addWidget(skip)
        layout.addLayout(buttons)

    def _finish(self) -> None:
        self.core.privacy.update(
            allow_tts=self.voice.isChecked(),
            allow_memory_learning=self.memory.isChecked(),
            allow_cloud_model=False,
            allow_nvidia_api=False,
            allow_gemini_api=False,
            allow_clipboard_observation=False,
        )
        self.core.update_voice_settings(allow_voice_input=False)
        self.core.voice_skin_settings.update(allow_rvc_voice_skin=False, rvc_enabled=False)
        self.core.app_settings.complete_setup(False)
        self.accept()

    def _skip(self) -> None:
        self.core.app_settings.complete_setup(True)
        self.accept()


class FibiHealthDialog(QDialog):
    """Small runtime health panel for manual desktop QA."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.setWindowTitle("tiny health panel")
        self.setMinimumSize(460, 340)
        layout = QVBoxLayout(self)
        self.text = QLabel(self.core.get_gui_health_snapshot())
        self.text.setWordWrap(True)
        self.text.setStyleSheet("color: #39243f; font: 9pt 'Segoe UI';")
        layout.addWidget(self.text)
        refresh = QPushButton("refresh")
        refresh.clicked.connect(self._refresh)
        layout.addWidget(refresh)
        self.setStyleSheet("QDialog { background: #fff7fc; } QPushButton { padding: 6px; }")

    def _refresh(self) -> None:
        self.text.setText(self.core.get_gui_health_snapshot())


class FibiCommandCenterDialog(QDialog):
    """Small searchable command map for Fibi."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.setWindowTitle("command center")
        self.setMinimumSize(560, 460)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search commands: browser, patch, voice, release...")
        self.search.textChanged.connect(lambda _text="": self._refresh())
        layout.addWidget(self.search)

        self.categories = QListWidget()
        self.categories.setFixedHeight(92)
        self.categories.addItem("all")
        for category in self.core.command_registry.categories():
            self.categories.addItem(category)
        self.categories.currentTextChanged.connect(lambda _text="": self._refresh())
        self.categories.setCurrentRow(0)
        layout.addWidget(self.categories)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results)

        self.safety = QLabel(self.core.safety_explainer.safety_overview())
        self.safety.setWordWrap(True)
        layout.addWidget(self.safety)

        self.setStyleSheet(
            """
            QDialog { background: #fff7fc; color: #39243f; }
            QLineEdit, QTextEdit, QListWidget {
                background: rgba(255, 255, 255, 235);
                border: 1px solid rgba(244, 155, 205, 180);
                border-radius: 8px;
                padding: 6px;
                color: #39243f;
                font: 9pt 'Segoe UI';
            }
            QLabel { color: #5b3768; font: 9pt 'Segoe UI'; }
            """
        )

    def _refresh(self) -> None:
        term = self.search.text().strip()
        category = self.categories.currentItem().text() if self.categories.currentItem() else "all"
        if term:
            commands = self.core.command_registry.search(term, limit=20)
        elif category and category != "all":
            commands = self.core.command_registry.by_category(category)
        else:
            commands = self.core.command_registry.all()[:24]
        command_lines = [self.core.command_registry.format_command(command) for command in commands]
        caps = self.core.capability_registry.all(self.core._capability_status_overrides())[:8]
        cap_lines = [f"{cap.name}: {'on' if cap.enabled else 'off'} - {cap.status_summary}" for cap in caps]
        self.results.setPlainText(
            "Commands\n"
            + ("\n".join(command_lines) if command_lines else "no command crumbs matched.")
            + "\n\nCapabilities\n"
            + "\n".join(cap_lines)
            + "\n\nExamples\n/help search browser\n/workflow list\n/permissions\n/safety"
        )


class FibiMemoryReviewDialog(QDialog):
    """Search and manage Fibi's local RAG memory notebook."""

    def __init__(self, core: FibiCore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.core = core
        self.items = []
        self.setWindowTitle("memory review")
        self.setMinimumSize(620, 500)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.status = QLabel(self.core.memory_consent.summary_line())
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search memories...")
        self.search.returnPressed.connect(self._refresh)
        controls.addWidget(self.search, 2)
        self.category = QLineEdit()
        self.category.setPlaceholderText("category filter")
        self.category.returnPressed.connect(self._refresh)
        controls.addWidget(self.category, 1)
        refresh = QPushButton("refresh")
        refresh.clicked.connect(self._refresh)
        controls.addWidget(refresh)
        layout.addLayout(controls)

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._select)
        body.addWidget(self.list_widget, 1)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        body.addWidget(self.detail, 2)
        layout.addLayout(body, 1)

        actions = QHBoxLayout()
        for label, callback in (
            ("approve", self._approve),
            ("pin", self._pin),
            ("archive", self._archive),
            ("delete", self._delete),
            ("export", self._export),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)

        self.safety = QLabel("local only. secrets and raw private page text are excluded from memory export.")
        self.safety.setWordWrap(True)
        layout.addWidget(self.safety)

        self.setStyleSheet(
            """
            QDialog { background: #fff7fc; color: #39243f; }
            QLineEdit, QTextEdit, QListWidget {
                background: rgba(255,255,255,235);
                border: 1px solid #efb4d3;
                border-radius: 8px;
                padding: 6px;
                font: 9pt 'Segoe UI';
            }
            QPushButton {
                background: #f49bcd;
                border: 0;
                border-radius: 8px;
                color: white;
                padding: 7px 9px;
                font: 9pt 'Segoe UI';
            }
            QPushButton:hover { background: #ec73b4; }
            QLabel { color: #5b3768; font: 9pt 'Segoe UI'; }
            """
        )

    def _refresh(self) -> None:
        term = self.search.text().strip()
        category = self.category.text().strip() or None
        if term:
            self.items = [result.item for result in self.core.memory_review.search_memories(term, top_k=50)]
        else:
            self.items = self.core.memory_review.list_memories(category=category, limit=100)
        self.list_widget.clear()
        for item in self.items:
            suffix = " pinned" if item.pinned else " pending" if item.sensitive_flag and not item.approved else ""
            self.list_widget.addItem(f"{item.memory_id}: {item.category}{suffix}")
        self.status.setText(self.core.memory_review.format_health(self.core.memory_consent.status().summary))
        self.detail.setPlainText("")

    def _current(self):
        index = self.list_widget.currentRow()
        if index < 0 or index >= len(self.items):
            self.status.setText("pick a memory crumb first.")
            return None
        return self.items[index]

    def _select(self, index: int) -> None:
        if index < 0 or index >= len(self.items):
            self.detail.setPlainText("")
            return
        self.detail.setPlainText(self.core.memory_review.format_item(self.items[index]))

    def _approve(self) -> None:
        item = self._current()
        if not item:
            return
        self.status.setText(self.core.memory_review.approve_memory(item.memory_id).message)
        self._refresh()

    def _pin(self) -> None:
        item = self._current()
        if not item:
            return
        self.status.setText(self.core.memory_review.pin_memory(item.memory_id, not item.pinned).message)
        self._refresh()

    def _archive(self) -> None:
        item = self._current()
        if not item:
            return
        self.status.setText(self.core.memory_review.archive_memory(item.memory_id, True).message)
        self._refresh()

    def _delete(self) -> None:
        item = self._current()
        if not item:
            return
        result = self.core.memory_review.delete_memory(MemoryDeleteRequest(memory_id=item.memory_id, user_confirmed=True, reason="gui_memory_review"))
        self.status.setText(result.message)
        self._refresh()

    def _export(self) -> None:
        json_path, md_path = self.core.memory_review.export_memories()
        self.status.setText(f"exported: {json_path}; {md_path}")


class FibiWindow(QWidget):
    """Full Fibi Control Center window."""

    COMPACT_SIZE = QSize(380, 460)
    EXPANDED_SIZE = QSize(560, 620)

    def __init__(
        self,
        core: FibiCore | None = None,
        life: LifeEngine | None = None,
        *,
        control_center: bool = False,
        startup_surface: bool = False,
    ) -> None:
        super().__init__()
        self._control_center = control_center
        self.life = life or (core.life if core is not None else LifeEngine())
        self.core = core or FibiCore(life=self.life)
        self._owns_core = core is None
        self.chat_history: list[dict[str, str]] = []
        self.drag_offset: QPoint | None = None
        self._press_global: QPoint | None = None
        self._press_target = None
        self._is_dragging = False
        self._pending_user_text = ""
        self._request_serial = 0
        self._quitting = False
        self._voice_listening = False
        self._wake_stop = threading.Event()
        self._wake_thread: threading.Thread | None = None
        self.bridge = FibiBridge(self)
        self.tray_icon: QSystemTrayIcon | None = None
        self.health_dialog: FibiHealthDialog | None = None
        self.command_center_dialog: FibiCommandCenterDialog | None = None
        self.memory_review_dialog: FibiMemoryReviewDialog | None = None
        self.window_mode = "expanded" if control_center else self.core.app_settings.settings.window_mode

        self._setup_window()
        self._build_ui()
        if not control_center:
            self._setup_tray()
        self._connect_signals()
        self._move_to_saved_or_bottom_right()

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._idle_quirk)
        if not control_center:
            self.idle_timer.start(5000)
            QTimer.singleShot(700, self._greet)
            QTimer.singleShot(1000, self._sync_wake_listener)
            if startup_surface and not self.core.app_settings.settings.setup_complete:
                QTimer.singleShot(900, self._show_first_run)

    def _setup_window(self) -> None:
        if self._control_center:
            self.setWindowTitle("Fibi Control Center")
            self.setWindowFlags(Qt.WindowType.Window)
            self.setMinimumSize(self.COMPACT_SIZE)
            self.resize(self.EXPANDED_SIZE)
            self.setAcceptDrops(True)
            return
        self.setWindowTitle("Fibi")
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.core.app_settings.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(self.COMPACT_SIZE)
        self.resize(self.EXPANDED_SIZE if self.window_mode == "expanded" else self.COMPACT_SIZE)
        self.setAcceptDrops(True)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(7)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(10)

        self.name_label = QLabel("Fibi")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.name_label.setAccessibleName("Fibi companion")
        self.name_label.setStyleSheet("color: rgba(255, 248, 253, 245); font: bold 12pt 'Segoe UI';")
        header_layout.addWidget(self.name_label)
        header_layout.addStretch(1)

        self.provider_badge = QLabel()
        self.provider_badge.setObjectName("providerBadge")
        self.provider_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.provider_badge.setAccessibleName("Current language provider")
        self.provider_badge.setMinimumHeight(24)
        self.provider_badge.setContentsMargins(6, 0, 6, 0)
        header_layout.addWidget(self.provider_badge)
        self.microphone_indicator = QLabel("MIC")
        self.microphone_indicator.setObjectName("microphoneIndicator")
        self.microphone_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.microphone_indicator.setToolTip("Microphone is listening locally")
        self.microphone_indicator.setStyleSheet(
            "background: rgba(255, 232, 240, 240); color: #8a2347; border: 1px solid #e69ab5; "
            "border-radius: 6px; font: bold 7pt 'Segoe UI'; padding: 3px 5px;"
        )
        self.microphone_indicator.hide()
        header_layout.addWidget(self.microphone_indicator)
        self.menu_button = QPushButton("...")
        self.menu_button.setObjectName("petMenuButton")
        self.menu_button.setFixedSize(28, 24)
        self.menu_button.setToolTip("Fibi menu")
        self.menu_button.clicked.connect(self._show_pet_menu)
        header_layout.addWidget(self.menu_button)
        self.collapse_button = QPushButton()
        self.collapse_button.setObjectName("collapseButton")
        self.collapse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.collapse_button.setFixedSize(28, 24)
        self.collapse_button.setToolTip("Collapse to compact pet mode")
        self.collapse_button.clicked.connect(self._collapse_chat)
        header_layout.addWidget(self.collapse_button)
        main_layout.addLayout(header_layout)

        self.presence_area = QWidget()
        self.presence_area.setObjectName("presenceArea")
        presence_layout = QHBoxLayout(self.presence_area)
        presence_layout.setContentsMargins(0, 0, 0, 0)
        presence_layout.setSpacing(6)

        self.sprite = FibiSprite(self.life)
        presence_layout.addWidget(self.sprite, 3)

        self.bubble = SpeechBubble()
        presence_layout.addWidget(self.bubble, 2, Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(self.presence_area, 1)

        self.context_label = QLabel("")
        self.context_label.setMinimumHeight(22)
        self.context_label.setStyleSheet(
            """
            QLabel {
                color: #5b3768;
                background: rgba(255, 248, 253, 190);
                border: 1px solid rgba(244, 155, 205, 160);
                border-radius: 8px;
                padding: 2px 7px;
                font: 8pt 'Segoe UI';
            }
            """
        )
        self.context_label.hide()
        main_layout.addWidget(self.context_label)

        self.session_label = QLabel("")
        self.session_label.setMinimumHeight(22)
        self.session_label.setStyleSheet(
            """
            QLabel {
                color: #4a3a1f;
                background: rgba(255, 250, 231, 195);
                border: 1px solid rgba(225, 184, 92, 160);
                border-radius: 8px;
                padding: 2px 7px;
                font: 8pt 'Segoe UI';
            }
            """
        )
        self.session_label.hide()
        main_layout.addWidget(self.session_label)

        self.input_bar = QWidget()
        self.input_bar.setObjectName("inputBar")
        input_row = QHBoxLayout(self.input_bar)
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Talk to Fibi...")
        self.chat_input.setAccessibleName("Message Fibi")
        self.chat_input.setMinimumHeight(36)
        self.chat_input.setMinimumWidth(150)
        self.chat_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.chat_input.returnPressed.connect(lambda: self._safe_ui_call("send_message", self._send_message))
        self.chat_input.setStyleSheet(
            """
            QLineEdit {
                background: rgba(255, 255, 255, 230);
                border: 2px solid rgba(244, 155, 205, 210);
                border-radius: 8px;
                color: #33223d;
                font: 10pt 'Segoe UI';
                padding: 0 10px;
            }
            QLineEdit:focus {
                border-color: rgba(139, 92, 246, 230);
            }
            """
        )
        input_row.addWidget(self.chat_input, 1)

        self.mic_button = QPushButton("Mic")
        self.mic_button.setAccessibleName("Start voice input")
        self.mic_button.setFixedSize(48, 36)
        self.mic_button.clicked.connect(lambda: self._safe_ui_call("mic_button", self._listen_voice))
        self.mic_button.setToolTip("Push to talk")
        self.mic_button.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 248, 253, 230);
                border: 1px solid rgba(244, 155, 205, 210);
                border-radius: 8px;
                color: #5b3768;
                font: bold 9pt 'Segoe UI';
            }
            QPushButton:hover { background: rgba(255, 230, 245, 245); }
            QPushButton:focus { border: 2px solid rgba(139, 92, 246, 230); }
            QPushButton:disabled { color: rgba(91, 55, 104, 110); }
            """
        )
        input_row.addWidget(self.mic_button)

        self.send_button = QPushButton("Send")
        self.send_button.setAccessibleName("Send message")
        self.send_button.setFixedSize(58, 36)
        self.send_button.clicked.connect(lambda: self._safe_ui_call("send_button", self._send_message))
        self.send_button.setStyleSheet(
            """
            QPushButton {
                background: rgba(244, 155, 205, 235);
                border: 1px solid rgba(255, 255, 255, 90);
                border-radius: 8px;
                color: white;
                font: bold 9pt 'Segoe UI';
            }
            QPushButton:hover { background: rgba(236, 115, 180, 245); }
            QPushButton:pressed { background: rgba(215, 90, 160, 255); }
            QPushButton:focus { border: 2px solid rgba(255, 255, 255, 230); }
            """
        )
        input_row.addWidget(self.send_button)
        main_layout.addWidget(self.input_bar)

        self.setTabOrder(self.chat_input, self.mic_button)
        self.setTabOrder(self.mic_button, self.send_button)

        self._refresh_provider_badge()
        self.collapse_button.setVisible(self.window_mode == "expanded")
        self.pet_menu = self._build_pet_menu()

        # These areas are safe handles for moving the floating window around.
        if not self._control_center:
            for widget in (self, self.sprite, self.bubble, self.name_label):
                widget.installEventFilter(self)

    def _build_pet_menu(self) -> QMenu:
        """Build the small on-demand menu shared by sprite and menu button."""

        menu = QMenu(self)

        def add(label: str, callback) -> None:
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, cb=callback, name=label: self._safe_ui_call(f"pet-menu:{name}", cb))

        add("Chat", self._expand_chat)
        add("Settings", self._open_settings)
        add("Memory", self._open_memory_review)
        add("Commands", self._open_command_center)
        add("Browser", self._open_browser_help)
        add("Workflows", self._open_workflow_help)
        add("Health", self._open_health)
        menu.addSeparator()
        add("Hide", self.hide)
        add("Exit", self._quit_from_tray)
        return menu

    def _show_pet_menu(self, _checked: bool = False, global_position: QPoint | None = None) -> QMenu:
        anchor = global_position or self.menu_button.mapToGlobal(self.menu_button.rect().bottomRight())
        self.pet_menu.popup(anchor)
        return self.pet_menu

    def _set_window_mode(self, mode: str) -> None:
        selected = mode if mode in {"compact", "expanded"} else "compact"
        self.window_mode = selected
        self.core.update_settings(window_mode=selected)
        self.resize(self.EXPANDED_SIZE if selected == "expanded" else self.COMPACT_SIZE)
        self.collapse_button.setVisible(selected == "expanded")

    def _expand_chat(self) -> None:
        self._set_window_mode("expanded")
        self.chat_input.setFocus()
        QTimer.singleShot(0, self.chat_input.setFocus)

    def _collapse_chat(self) -> None:
        self._set_window_mode("compact")

    def _provider_badge_details(self, response: FibiResponse | None = None) -> tuple[str, str, str]:
        """Return a concise provider label derived from current runtime state."""

        selected = self.core.get_selected_provider_id()
        privacy = self.core.privacy.settings
        gemini_active = bool(
            selected == "gemini"
            and privacy.allow_cloud_model
            and privacy.allow_gemini_api
        )
        if response is not None and gemini_active and response.used_fallback:
            model = response.model_used.lower()
            if model and "local" not in model and "fallback" not in model:
                return "FALLBACK - Ollama", "Gemini fell back to the enabled local Ollama provider.", "fallback"
            return "LOCAL - Fibi", "The cloud provider was unavailable; Fibi used a local fallback.", "local"
        if gemini_active:
            return "CLOUD - Gemini", "Gemini is selected. Only approved cloud context may be sent.", "cloud"
        return "LOCAL - Ollama", "Local language mode. Cloud generation is not active.", "local"

    def _refresh_provider_badge(self, response: FibiResponse | None = None) -> None:
        text, tooltip, mode = self._provider_badge_details(response)
        self.provider_badge.setText(text)
        self.provider_badge.setToolTip(tooltip)
        self.provider_badge.setProperty("providerMode", mode)
        colors = {
            "cloud": ("rgba(239, 233, 255, 235)", "#4c2f78", "rgba(190, 163, 238, 220)"),
            "fallback": ("rgba(255, 244, 214, 238)", "#6b4b15", "rgba(225, 184, 92, 220)"),
            "local": ("rgba(255, 248, 253, 230)", "#5b3768", "rgba(244, 155, 205, 205)"),
        }
        background, foreground, border = colors[mode]
        self.provider_badge.setStyleSheet(
            f"""
            QLabel {{
                background: {background};
                color: {foreground};
                border: 1px solid {border};
                border-radius: 8px;
                font: bold 8pt 'Segoe UI';
                padding: 3px 9px;
            }}
            """
        )

    def _connect_signals(self) -> None:
        self.bridge.response_ready.connect(self._on_response)
        self.bridge.voice_preparing.connect(self._on_voice_preparing)
        self.bridge.speaking_started.connect(self._on_speaking_started)
        self.bridge.speaking_finished.connect(self._on_speaking_finished)
        self.bridge.wake_detected.connect(self._on_wake_detected)
        self.bridge.microphone_state.connect(self._set_microphone_state)
        self.bridge.wake_state_changed.connect(self._on_wake_state_changed)

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self._tray_icon()
        self.tray_icon = QSystemTrayIcon(icon, self)
        menu = QMenu()

        def add(label: str, callback) -> None:
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, cb=callback, name=label: self._safe_ui_call(f"tray:{name}", cb))
            menu.addAction(action)

        add("Show Fibi", self.show)
        add("Hide Fibi", self.hide)
        add("Nap", lambda: self._show_creature_reaction(self.core.nap()))
        add("Wake", lambda: self._show_creature_reaction(self.core.wake()))
        add("Quiet Mode", lambda: self._ask_fibi("/quiet"))
        add("Open Notebook", self._open_notebook)
        add("Command Center", self._open_command_center)
        add("Memory Review", self._open_memory_review)
        add("Open Settings", self._open_settings)
        add("Health", self._open_health)
        add("Report Issue", self._open_beta_report)
        add("Recipes", self._open_workflow_help)
        add("Browser Help", self._open_browser_help)
        add("Model Status", lambda: self._ask_fibi("/model status"))
        add("Privacy Status", lambda: self._ask_fibi("/privacy"))
        menu.addSeparator()
        add("Quit", self._quit_from_tray)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(lambda reason: self.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray_icon.show()

    def _tray_icon(self) -> QIcon:
        for name in ("tray", "idle"):
            path = _asset_path(name)
            if path:
                return QIcon(str(path))
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(244, 155, 205))
        return QIcon(pixmap)

    def _move_to_saved_or_bottom_right(self) -> None:
        for screen in QApplication.screens():
            area = screen.availableGeometry()
            saved, path = self.life.restored_position(
                area.left(),
                area.top(),
                area.right(),
                area.bottom(),
                self.width(),
                self.height(),
            )
            if saved:
                self.move(saved.x, saved.y)
                self.core.record_restoration_path(path)
                return

        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 20, area.bottom() - self.height() - 20)
        self.core.record_restoration_path("default")

    def _greet(self) -> None:
        self.sprite.set_expression(self.life.expression)
        self.bubble.show_text(self.core.startup_message)
        self._play_sound("startup")

    def _open_notebook(self) -> None:
        self.notebook_dialog = FibiNotebookDialog(self.core, self)
        self.notebook_dialog.show()

    def _open_command_center(self) -> None:
        self.command_center_dialog = FibiCommandCenterDialog(self.core, self)
        self.command_center_dialog.show()

    def _open_memory_review(self) -> None:
        self.memory_review_dialog = FibiMemoryReviewDialog(self.core, self)
        self.memory_review_dialog.show()

    def _open_settings(self) -> None:
        self.settings_dialog = FibiSettingsDialog(self.core, self)
        self.settings_dialog.show()

    def _open_health(self) -> None:
        self.health_dialog = FibiHealthDialog(self.core, self)
        self.health_dialog.show()

    def _open_beta_report(self) -> None:
        self.chat_input.setText("/issue new ")
        self.chat_input.setFocus()
        self.chat_input.setCursorPosition(len(self.chat_input.text()))
        self.bubble.show_text("bug jar opened. tell me what squeaked.", BubbleDisplayOptions("instant", 0, True, True))

    def _open_browser_help(self) -> None:
        self.chat_input.setText("/browser ")
        self.chat_input.setFocus()
        self.chat_input.setCursorPosition(len(self.chat_input.text()))
        self.bubble.show_text("browser helper. paste page text; no sneaky reading.", BubbleDisplayOptions("instant", 0, True, True))

    def _open_workflow_help(self) -> None:
        self.chat_input.setText("/workflow ")
        self.chat_input.setFocus()
        self.chat_input.setCursorPosition(len(self.chat_input.text()))
        self.bubble.show_text("recipes guide rituals. no tiny autopilot.", BubbleDisplayOptions("instant", 0, True, True))

    def _safe_ui_call(self, where: str, callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            self.core.record_ui_error(where, exc)
            if hasattr(self, "bubble"):
                self.bubble.show_text("small stumble.", BubbleDisplayOptions("instant", 0, True, True))
            return None

    def _set_context_chip(self, text: str) -> None:
        if not text:
            self.context_label.hide()
            return
        self.context_label.setText(f"Context: {text[:32]}")
        self.context_label.show()

    def _set_session_chip(self) -> None:
        try:
            text = self.core.session_status_chip()
            if not text:
                self.session_label.hide()
                return
            self.session_label.setText(f"Session: {text[:34]}")
            self.session_label.show()
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            self.core.record_ui_error("session_chip", exc)

    def _show_first_run(self) -> None:
        FibiFirstRunDialog(self.core, self).show()

    def _quit_from_tray(self) -> None:
        self._quitting = True
        self.close()

    def _play_sound(self, name: str) -> None:
        if self.core.privacy.settings.allow_sounds:
            play_sound(name)

    def _play_sound_event(self, name: str) -> None:
        if self.core.privacy.settings.allow_sounds:
            play_sound_event(name)

    def _send_message(self) -> None:
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
        is_cancel = user_text.lower().strip() in {"/cancel", "/stop"}
        if self.life.is_busy() and not is_cancel:
            return

        self.chat_input.clear()
        self._ask_fibi(user_text)

    def _listen_voice(self) -> None:
        if self._voice_listening or self.life.is_speaking:
            return
        self._voice_listening = True
        self._set_microphone_state("command")
        self.mic_button.setEnabled(False)
        self.life.set_thinking(False)
        self.sprite.set_expression("thinking", temporary_ms=6000)
        self.bubble.show_text("ears on.", BubbleDisplayOptions("soft", 0, True, True))

        def worker() -> None:
            try:
                result = self.core.start_voice_listen(source="mic_button")
                self.bridge.response_ready.emit(result)
            except Exception as error:
                print(f"ERROR: voice listen failed: {error}")
                timing = self.core.timing.select(event="fallback", mood="sleepy", fallback=True)
                self.bridge.response_ready.emit(
                    FibiResponse("mic creature tripped.", "mic creature tripped", "sleepy", "voice-ui-fallback", True, timing, None)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _ask_fibi(self, user_text: str) -> None:
        self._request_serial += 1
        request_id = self._request_serial
        self._pending_user_text = user_text
        is_greeting = user_text.lower().strip(" .!?") in {"hey", "hi", "hello", "yo", "sup"}
        if is_greeting:
            self.bubble.show_text("...", BubbleDisplayOptions("instant", 0, True, True))
        else:
            self.life.set_thinking(True)
            self.sprite.set_expression("thinking", temporary_ms=60 * 1000)
            self.sprite.start_motion(
                self.core.motion.select(
                    mood="curious", presence_state="thinking", event="thinking",
                    time_of_day=self.core.observation.observe().time_of_day,
                )
            )
            self.bubble.show_text("Fibi is thinking...", BubbleDisplayOptions("soft", 0, True, True))
            self._play_sound("thinking")

        def worker() -> None:
            try:
                result = self.core.respond(user_text)
                if request_id != self._request_serial:
                    return
                response = result.display_text
                expression = result.mood
                self.chat_history.append({"role": "user", "content": user_text})
                self.chat_history.append({"role": "assistant", "content": response})
                self.chat_history = self.chat_history[-20:]
                self.bridge.response_ready.emit(result)
            except Exception as error:
                print(f"ERROR: FibiCore response failed: {error}")
                if request_id != self._request_serial:
                    return
                timing = self.core.timing.select(event="fallback", mood="idle", fallback=True)
                self.bridge.response_ready.emit(
                    FibiResponse("tiny engine tripped. one sec.", "tiny engine tripped", "idle", "ui-fallback", True, timing, None)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_response(self, result: FibiResponse) -> None:
        from fibi.brain.cleanup import clean_response

        self._voice_listening = False
        self._sync_wake_listener()
        if hasattr(self, "mic_button"):
            self.mic_button.setEnabled(True)
        self._refresh_provider_badge(result)
        text = clean_response(result.display_text)
        self.life.set_thinking(False)
        timing = result.timing or self.core.timing.select(event="reply", mood=result.mood)

        def display() -> None:
            self.sprite.set_expression(result.mood, temporary_ms=3000 if result.mood == "happy" else 1600)
            self.sprite.start_motion(result.motion)
            self._set_session_chip()
            self.bubble.show_text(text, self.core.timing.bubble_options(text, timing.typing_style))
            self._play_sound_event("success") if result.motion and result.motion.motion_name == "celebration_pop" else self._play_sound("message")
            self._speak_in_background(result.tts_text, result.mood, result.model_used, result.tts_priority)

        if timing.pre_delay_ms:
            if timing.show_thinking_bubble and timing.thinking_line:
                self.bubble.show_text(timing.thinking_line, BubbleDisplayOptions("soft", 0, True, True))
            QTimer.singleShot(timing.pre_delay_ms, display)
        else:
            display()

    def _sync_wake_listener(self) -> None:
        if self._control_center:
            return
        enabled = bool(
            self.core.voice_settings.settings.allow_voice_input
            and self.core.voice_settings.settings.wake_word_enabled
        )
        if not enabled:
            self._wake_stop.set()
            self._set_microphone_state("")
            return
        if self.core.wake_word.state.value == "idle":
            self._set_microphone_state("wake")
        if self._wake_thread is not None and self._wake_thread.is_alive():
            return
        self._wake_stop.clear()
        self._wake_thread = threading.Thread(target=self._wake_listener_worker, daemon=True)
        self._wake_thread.start()

    def _wake_listener_worker(self) -> None:
        while not self._wake_stop.is_set():
            if self.life.is_busy() or self._voice_listening:
                self._wake_stop.wait(0.4)
                continue
            try:
                detected, result = self.core.listen_for_wake_once()
                if self._wake_stop.is_set():
                    return
                if detected:
                    self.bridge.wake_state_changed.emit("wake_detected")
                    self.bridge.wake_detected.emit()
                    self.bridge.wake_state_changed.emit("listening")
                    transcription = self.core.capture_wake_transcript()
                    self.bridge.wake_state_changed.emit("transcribing")
                    if transcription.error or not transcription.should_route_to_core:
                        self.core.wake_word.reset()
                        self.bridge.wake_state_changed.emit("idle")
                        self._wake_stop.wait(0.8)
                        continue
                    self.core.wake_word.mark_thinking()
                    self.bridge.wake_state_changed.emit("thinking")
                    self.bridge.response_ready.emit(self.core.route_wake_transcript(transcription))
                    self._wake_stop.wait(self.core.voice_settings.settings.wake_word_cooldown_seconds)
                elif result.error:
                    self._wake_stop.wait(1.2)
            except Exception as error:
                LOGGER.error("wake listener failed error_type=%s", type(error).__name__)
                self.core.wake_word.reset()
                self.bridge.wake_state_changed.emit("idle")
                self._wake_stop.wait(1.5)

    def _on_wake_detected(self) -> None:
        self.life.set_listening(True)
        self.sprite.set_expression("listening", temporary_ms=9000)
        self.bubble.show_text("hm?", BubbleDisplayOptions("instant", 0, True, True))
        self._play_sound("click")

    def _on_wake_state_changed(self, state: str) -> None:
        if state == "wake_detected":
            self._set_microphone_state("heard")
            self.life.set_listening(True)
            self.sprite.set_expression("listening", temporary_ms=9000)
            self.bubble.show_text("hm?", BubbleDisplayOptions("instant", 0, True, True))
            return
        if state == "listening":
            self._set_microphone_state("command")
            self.life.set_listening(True)
            self.sprite.set_expression("listening", temporary_ms=9000)
            self.bubble.show_text("I'm listening.", BubbleDisplayOptions("instant", 0, True, True))
            return
        if state == "transcribing":
            self.life.set_listening(False)
            self.life.set_thinking(True)
            self._set_microphone_state("transcribing")
            self.sprite.set_expression("thinking", temporary_ms=6000)
            self.bubble.show_text("one sec...", BubbleDisplayOptions("instant", 0, True, True))
            return
        if state == "thinking":
            self.life.set_listening(False)
            self.life.set_thinking(True)
            self._set_microphone_state("")
            self.sprite.set_expression("thinking", temporary_ms=60_000)
            self.bubble.show_text("Fibi is thinking...", BubbleDisplayOptions("soft", 0, True, True))
            return
        if state == "speaking":
            self._set_microphone_state("")
            return
        self.life.set_listening(False)
        self.life.set_thinking(False)
        self.sprite.set_expression("idle", force=True)
        if self.core.voice_settings.settings.wake_word_enabled:
            self._set_microphone_state("wake")
        else:
            self._set_microphone_state("")

    def _set_microphone_state(self, state: str) -> None:
        if not hasattr(self, "microphone_indicator"):
            return
        if state == "command":
            self.microphone_indicator.setText("MIC: LISTEN")
            self.microphone_indicator.show()
            return
        if state == "heard":
            self.microphone_indicator.setText("MIC: HEARD")
            self.microphone_indicator.show()
            return
        if state == "transcribing":
            self.microphone_indicator.setText("MIC: TEXT")
            self.microphone_indicator.show()
            return
        if state == "wake":
            self.microphone_indicator.setText("MIC: WAKE")
            self.microphone_indicator.show()
            self.life.set_listening(False)
            return
        self.microphone_indicator.hide()
        self.life.set_listening(False)

    def _speak_in_background(self, text: str, expression_after: str, model_used: str = "", tts_priority: str = "") -> None:
        from fibi.brain.cleanup import tts_safe_text
        from fibi.voice.speak import is_voice_available

        decision = self.core.tts_manager.decide(
            model_used,
            text,
            self.core.privacy.settings.allow_tts,
            tts_priority,
        )
        print(f"TTS_PRIORITY: {decision.priority}")
        if not decision.should_speak:
            print(f"TTS_SKIPPED_REASON: {decision.skipped_reason}")
            self._finish_wake_session()
            return
        if not is_voice_available():
            print("TTS_SKIPPED_REASON: unavailable")
            self._finish_wake_session()
            return

        speech_text = tts_safe_text(text)
        if not speech_text:
            print("TTS_SKIPPED_REASON: empty")
            self._finish_wake_session()
            return

        skin_settings = self.core.voice_skin_settings.settings
        rvc_enabled = bool(skin_settings.allow_rvc_voice_skin and skin_settings.rvc_enabled)
        self.core.tts_manager.mark_started()
        self.bridge.voice_preparing.emit(rvc_enabled)

        def worker() -> None:
            from fibi.voice.speak import play_audio, prepare_voice_output

            started = time.perf_counter()
            print("EDGE_TTS_START")
            base_path = ""
            spoke = False
            try:
                try:
                    edge_started = time.perf_counter()
                    voice_output = prepare_voice_output(
                        speech_text,
                        skin_settings,
                        self.core.rvc_voice_skin,
                        self.core.voice_cache,
                    )
                    if voice_output.base_audio_path:
                        base_path = str(voice_output.base_audio_path)
                    if not voice_output.edge_tts_ok or not voice_output.final_audio_path:
                        print("TTS_SKIPPED_REASON: edge_tts_failed")
                    else:
                        print(f"EDGE_TTS_DURATION_MS: {(time.perf_counter() - edge_started) * 1000:.1f}")
                        print(f"FINAL_AUDIO_PLAYED_PATH: {voice_output.final_audio_path}")
                        self.bridge.speaking_started.emit()
                        spoke = play_audio(voice_output.final_audio_path)
                except Exception as error:
                    print(f"TTS_SKIPPED_REASON: {type(error).__name__}")
            finally:
                duration_ms = (time.perf_counter() - started) * 1000
                if base_path:
                    with suppress(OSError):
                        Path(base_path).unlink()
                print(f"TTS_DURATION_MS: {duration_ms:.1f}")
                self.core.tts_manager.mark_finished(duration_ms)
                self.core.health.record_tts(duration_ms)
                self.bridge.speaking_finished.emit(spoke)

        self._expression_after_speech = (
            expression_after
            if expression_after in EXPRESSIONS and expression_after != "talking"
            else "idle"
        )
        threading.Thread(target=worker, daemon=True).start()

    def _on_voice_preparing(self, rvc_enabled: bool) -> None:
        self.life.set_speaking(True)
        self.bubble.set_speaking(True)
        self.bubble.set_voice_status("processing voice..." if rvc_enabled else "speaking...")

    def _on_speaking_started(self) -> None:
        self.core.wake_word.mark_speaking()
        self._on_wake_state_changed("speaking")
        self.life.set_speaking(True)
        self.bubble.set_speaking(True)
        self.bubble.set_voice_status("speaking...")
        self.sprite.set_talking(True)

    def _on_speaking_finished(self, spoke: bool) -> None:
        self.life.set_speaking(False)
        self.bubble.set_speaking(False)
        self.bubble.set_voice_status("")
        self.sprite.set_talking(False)
        next_mood = getattr(self, "_expression_after_speech", "happy") if spoke else "idle"
        self.sprite.set_expression(next_mood, force=True)
        self._finish_wake_session()

    def _finish_wake_session(self) -> None:
        if self.core.wake_word.state.value == "idle":
            return
        self.core.wake_word.reset()
        self._on_wake_state_changed("idle")

    def _idle_quirk(self) -> None:
        self.life.consider_nest_stay(self.x(), self.y())
        nap_reaction = self.core.check_nap()
        if nap_reaction:
            self._show_creature_reaction(nap_reaction)
            return
        if self.life.nap.is_napping:
            return
        if not self.life.should_idle_react():
            return

        line, expression = self.core.contextual_idle_reaction()
        self.sprite.start_motion(self.core.take_pending_idle_motion())
        if not line:
            return
        self.sprite.set_expression(expression, temporary_ms=1800)
        self.bubble.show_text(line, self.core.timing.bubble_options(line, "sleepy" if expression == "sleepy" else "soft"))
        self._play_sound("message")

    def _show_creature_reaction(self, reaction) -> None:
        if reaction is None:
            return
        self.sprite.start_motion(reaction.motion)
        if not reaction.should_display or not reaction.text:
            return

        def display() -> None:
            self.sprite.set_expression(reaction.expression, temporary_ms=1600)
            style = reaction.timing.typing_style if reaction.timing else "soft"
            self.bubble.show_text(reaction.text, self.core.timing.bubble_options(reaction.text, style))
            if reaction.sound_name:
                self._play_sound_event(reaction.sound_name)
            if reaction.reaction_type == "wake":
                QTimer.singleShot(1200, self.life.finish_waking)

        delay = reaction.timing.pre_delay_ms if reaction.timing else 0
        QTimer.singleShot(delay, display) if delay else display()

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        return self._safe_ui_call("drop_event", self._handle_drop_event, event)

    def _handle_drop_event(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path:
            return
        result = self.core.handle_dropped_file(path)
        self._on_response(result)
        last = self.core.context_engine.last()
        if last and result.model_used == "local-command":
            self._set_context_chip(last.title)

    def closeEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        if self._control_center and not self._owns_core:
            self.hide()
            event.accept()
            return
        if (
            not self._quitting
            and self.core.app_settings.settings.minimize_to_tray
            and self.tray_icon is not None
            and self.tray_icon.isVisible()
        ):
            self.hide()
            event.ignore()
            return
        self._wake_stop.set()
        goodbye = self.core.shutdown() if self._owns_core else None
        if goodbye:
            print(f"FIBI GOODBYE: {goodbye.text}")
        if self.tray_icon:
            self.tray_icon.hide()
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: N802 - PyQt method name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(115, 85, 180, 218))
        gradient.setColorAt(1, QColor(232, 128, 184, 205))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 70), 2))
        painter.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4, 22, 22)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - PyQt method name
        if event.type() == QEvent.Type.WindowActivate and self.life.nap.is_napping:
            self._show_creature_reaction(self.core.handle_wake("focus"))

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.RightButton
            and watched in {self, self.sprite, self.bubble}
        ):
            self._show_pet_menu(global_position=event.globalPosition().toPoint())
            return True

        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global = event.globalPosition().toPoint()
            self._press_target = watched
            self._is_dragging = False
            return True

        if event.type() == QEvent.Type.MouseMove and self.drag_offset and event.buttons() & Qt.MouseButton.LeftButton:
            current = event.globalPosition().toPoint()
            if not self._is_dragging and self._press_global:
                self._is_dragging = (current - self._press_global).manhattanLength() >= 6
                if self._is_dragging:
                    self._show_creature_reaction(self.core.handle_drag_start())
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            return True

        if event.type() == QEvent.Type.MouseButtonRelease:
            if self._is_dragging:
                self._show_creature_reaction(self.core.handle_drag_end(self.x(), self.y()))
            elif self._press_target is self.sprite:
                self._show_pet_menu(global_position=event.globalPosition().toPoint())
            self.drag_offset = None
            self._press_global = None
            self._press_target = None
            self._is_dragging = False
            return True

        if event.type() == QEvent.Type.MouseButtonDblClick:
            self._expand_chat()
            return True

        return super().eventFilter(watched, event)
