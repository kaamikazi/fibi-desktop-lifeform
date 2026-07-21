"""Main entry point for the Fibi desktop assistant."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from fibi.ui.fibi_pet_window import FibiPetWindow


def main(gui_smoke: bool = False) -> int:
    """Start the PyQt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Fibi")

    window = FibiPetWindow()
    if gui_smoke:
        required = [
            "sprite",
            "bubble",
            "microphone_indicator",
            "chat_panel",
            "chat_input",
            "mic_button",
            "send_button",
            "core",
        ]
        missing = [name for name in required if not hasattr(window, name)]
        if missing:
            print("GUI_SMOKE_FAILED missing: " + ", ".join(missing))
            return 1
        menu_labels = [action.text() for action in window._build_pet_menu().actions() if not action.isSeparator()]
        expected = {"Talk", "Wake mode", "Provider", "Memory", "Actions", "Settings", "Control Center", "Hide", "Exit"}
        if not (140 <= window.width() <= 220) or set(menu_labels) != expected:
            print("GUI_SMOKE_FAILED lightweight pet contract")
            return 1
        print("GUI_SMOKE_OK")
        QTimer.singleShot(50, app.quit)
        return app.exec()
    if not window.core.app_settings.settings.start_minimized:
        window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
