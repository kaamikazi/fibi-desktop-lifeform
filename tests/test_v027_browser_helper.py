"""Tests for Fibi v0.27 safe browser helper mode."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fibi.engines.browser_helper_engine import BrowserHelperEngine
from fibi.engines.browser_safety_engine import BrowserSafetyEngine
from fibi.engines.html_text_extractor import HtmlTextExtractor
from tests.smoke_v012_actions import make_core


def test_browser_session_note_and_url_validation() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        helper = BrowserHelperEngine(browser_open=lambda url: opened.append(url) or True)

        session = helper.start_session("research tiny keyboards")
        assert session.browser_session_id
        note = helper.save_url_note("https://example.com/page", "looks useful")
        assert note is not None
        assert note.url == "https://example.com/page"
        assert (root / "data" / "browser" / "browser_sessions.jsonl").exists()
        assert (root / "data" / "browser" / "browser_notes.jsonl").exists()

        safety = BrowserSafetyEngine()
        assert safety.validate_url("https://example.com").allowed
        assert safety.validate_url("http://example.com").allowed
        for bad in ("file:///tmp/x", "javascript:alert(1)", "data:text/plain,hi"):
            assert safety.validate_url(bad).blocked


def test_open_url_requires_confirmation_and_cancel() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        core, model, _ = make_core(root / "core", opened, [])

        reply = core.respond("/browser open https://example.com").display_text
        assert "say: browser confirm" in reply
        assert opened == []
        assert "pending browser open" in core.respond("/browser pending").display_text
        assert "browser doorway canceled" in core.respond("/browser cancel").display_text
        assert opened == []

        core.respond("/browser open https://example.com")
        assert "opened example.com" in core.respond("browser confirm").display_text
        assert opened == ["https://example.com"]
        assert model.calls == 0


def test_pasted_html_summarizes_without_remote_fetch() -> None:
    extractor = HtmlTextExtractor()
    html = "<html><script>secret()</script><style>.x{}</style><h1>Acme</h1><p>We repair laptops.</p></html>"
    text = extractor.extract(html)
    assert "secret()" not in text
    assert ".x" not in text
    assert "Acme" in text
    assert "repair laptops" in text

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        opened: list[str] = []
        core, _, _ = make_core(root / "core", opened, [])
        core.respond("/context add " + html)
        summary = core.respond("/browser summarize").display_text
        assert "Acme" in summary
        assert "secret()" not in summary
        assert opened == []


def test_blocked_browser_requests_and_url_only_summary_refusal() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        blocked_inputs = [
            "read browser history",
            "read cookies",
            "show saved password",
            "auto click the buy button",
            "fill form and submit form",
            "send message to them",
            "buy this for me",
            "scrape this website secretly",
        ]
        for message in blocked_inputs:
            reply = core.respond(message).display_text
            assert "locked" in reply or "nope" in reply

        core.respond("/context add https://example.com")
        reply = core.respond("/browser summarize").display_text
        assert "only have the link" in reply
        assert "not the page" in reply


def test_browser_remember_note_and_work_session_browser_steps() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        core.respond("/browser note https://example.com public services page")
        remembered = core.respond("/browser remember note").display_text
        assert "remembered the note summary" in remembered

        session = core.respond("/session start help me research this website").display_text
        assert "tiny plan made" in session
        active = core.work_sessions.active()
        assert active is not None
        assert any(step.step_type.startswith("browser_") for step in active.steps)


def test_browser_health_debug_and_gui_command_path() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        core.respond("/browser start inspect example site")
        health = core.respond("/health gui").display_text
        assert "browser helper on" in health
        debug = core.respond("/debug summary").display_text
        assert "browser helper on" in debug
        assert "no scraping" in core.respond("/browser safety").display_text

        try:
            from PyQt6.QtWidgets import QApplication
            from fibi.ui.fibi_window import FibiWindow
        except Exception:
            return
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication.instance() or QApplication([])
        try:
            window = FibiWindow()
        except RuntimeError:
            return
        window._open_browser_help()
        assert window.chat_input.text() == "/browser "
        window.close()
        app.processEvents()


