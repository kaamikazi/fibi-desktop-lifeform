"""Safe, local desktop observations for Fibi."""

from __future__ import annotations

import ctypes
import os
from datetime import datetime
from pathlib import Path

from fibi.engines.types import Observation


class ObservationEngine:
    """Observe small bits of desktop context without continuous tracking."""

    def __init__(self, allow_clipboard: bool = False) -> None:
        self.allow_clipboard = allow_clipboard

    def observe(self, include_clipboard: bool = False) -> Observation:
        app, title = self.active_window()
        now = datetime.now().astimezone()
        clipboard = None
        if include_clipboard and self.allow_clipboard:
            clipboard = self.read_clipboard(permission=True)
        return Observation(
            timestamp=now.isoformat(timespec="seconds"),
            time_of_day=self.time_of_day(now.hour),
            active_app=app,
            active_window_title=title,
            clipboard_text=clipboard,
        )

    @staticmethod
    def time_of_day(hour: int) -> str:
        if 0 <= hour < 5:
            return "late_night"
        if hour < 12:
            return "morning"
        if hour < 17:
            return "afternoon"
        if hour < 22:
            return "evening"
        return "night"

    def active_window(self) -> tuple[str | None, str | None]:
        """Read only the foreground window title/process on Windows."""
        if os.name != "nt":
            return None, None

        try:
            user32 = ctypes.windll.user32
            user32.GetForegroundWindow.restype = ctypes.c_void_p
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None, None

            length = user32.GetWindowTextLengthW(hwnd)
            title_buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, length + 1)

            process_id = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            app = self._process_name(process_id.value)
            return app, title_buffer.value or None
        except Exception:
            return None, None

    @staticmethod
    def _process_name(process_id: int) -> str | None:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.restype = ctypes.c_void_p
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
            if not handle:
                return None
            try:
                size = ctypes.c_ulong(1024)
                buffer = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                    return Path(buffer.value).stem.lower()
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return None
        return None

    def read_clipboard(self, permission: bool = False) -> str | None:
        """Read clipboard only after both configuration and call-site consent."""
        if not self.allow_clipboard or not permission:
            return None
        try:
            import tkinter

            root = tkinter.Tk()
            root.withdraw()
            try:
                value = root.clipboard_get()
            finally:
                root.destroy()
            return str(value)[:2000]
        except Exception:
            return None
