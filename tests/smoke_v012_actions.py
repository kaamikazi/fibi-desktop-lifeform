"""Direct smoke tests for Fibi v0.12 Manual Action Core."""

from __future__ import annotations

import builtins
import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.action_confirmation_engine import ActionConfirmationEngine
from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.action_journal_engine import ActionJournalEngine
from fibi.engines.action_settings_engine import ActionSettingsEngine
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.core import FibiCore
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.permission_engine import PermissionEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import ActionIntent, ModelResult, Observation
from fibi.engines.warmup_engine import WarmupStatus


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "Fibi", None)


class NoModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("", "no-model", 0.0, "should not be called")


class DeferredWarmup:
    """Capture startup checks so tests can release them after an action is pending."""

    def __init__(self) -> None:
        self.status = WarmupStatus()
        self.checks: list[tuple[str, object]] = []

    def start(self, checks) -> None:
        self.checks = list(checks)
        self.status.running = True

    def run_persistence_checks(self) -> None:
        for name, check in self.checks:
            if name == "tts_probe":
                continue
            check()
        self.status.running = False
        self.status.completed = True


def make_core(
    root: Path,
    opened: list[str],
    launched: list[str],
    warmup=None,
) -> tuple[FibiCore, NoModel, AppIndexEngine]:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"legacy_v011": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    model = NoModel()
    app_index = AppIndexEngine(root / "app_index.json")
    fake_exe = root / "chrome.exe"
    fake_exe.write_text("", encoding="utf-8")
    app_index.add_entry("Chrome", str(fake_exe), "test")
    actions = DesktopActionEngine(
        app_index,
        browser_open=lambda url: opened.append(url) or True,
        app_launcher=lambda path: launched.append(path),
    )
    core = FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=model,
        privacy=PrivacySettingsEngine(state),
        action_settings=ActionSettingsEngine(state),
        app_index=app_index,
        desktop_actions=actions,
        action_journal=ActionJournalEngine(root / "action_journal.jsonl"),
        action_confirmations=ActionConfirmationEngine(state),
        project_workspace=ProjectWorkspaceEngine(root / "project_workspaces.json"),
        warmup=warmup,
    )
    return core, model, app_index


def test_missing_import_fallbacks(root: Path) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"pyautogui", "win32com.client"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    builtins.__import__ = fake_import
    try:
        volume = DesktopActionEngine().execute(ActionIntent("volume_up"))
        assert not volume.ok and "missing" in volume.message
        shortcut = root / "Fake.lnk"
        shortcut.write_text("", encoding="utf-8")
        assert AppIndexEngine._resolve_shortcut(shortcut) == shortcut
    finally:
        builtins.__import__ = original_import


def run() -> None:
    detector = ActionIntentDetector()
    assert detector.detect("open chrome").action_type == "open_app"
    assert detector.detect("open YouTube").action_type == "open_website"
    assert detector.detect("search Google for Python recursion").action_type == "web_search"
    assert detector.detect("search YouTube for lo-fi music").action_type == "youtube_search"
    assert detector.detect("wiki Alan Turing").action_type == "wikipedia_search"
    assert detector.detect("volume up").action_type == "volume_up"
    assert detector.detect("what time is it").action_type == "tell_time"
    assert detector.detect("what date is it").action_type == "tell_date"
    assert detector.detect("delete this file").action_type == "delete_file"
    assert detector.detect("run this command").action_type == "run_terminal_command"
    assert detector.detect("send message").action_type == "send_message"
    assert detector.detect("read clipboard").action_type == "read_clipboard"
    assert detector.detect("open chrome", direct_user_initiated=False) is None

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opened: list[str] = []
        launched: list[str] = []
        deferred_warmup = DeferredWarmup()
        core, model, app_index = make_core(root, opened, launched, warmup=deferred_warmup)

        permission = PermissionEngine()
        settings = core.action_settings.settings
        privacy = core.privacy.settings
        assert permission.check(ActionIntent("web_search", query="x"), settings, privacy, True).allowed
        core.action_settings.update(allow_desktop_actions=False)
        assert permission.check(ActionIntent("web_search", query="x"), core.action_settings.settings, privacy, True).blocked
        core.action_settings.update(allow_desktop_actions=True)
        assert permission.check(ActionIntent("screenshot"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("run_terminal_command"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("delete_file"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("send_message"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("read_clipboard"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("launch_unknown_executable"), settings, privacy, True).blocked
        assert permission.check(ActionIntent("web_search", query="x", direct_user_initiated=False), settings, privacy, False).blocked
        core.action_settings.update(allow_shutdown=True)
        shutdown_permission = permission.check(ActionIntent("shutdown_pc"), core.action_settings.settings, privacy, True)
        assert shutdown_permission.requires_confirmation

        expiring = ActionConfirmationEngine(root / "expire_state.json", ttl_seconds=-1)
        expiring.create(ActionIntent("shutdown_pc"))
        assert expiring.pending() is None

        pending = core.respond("shutdown pc")
        assert "say: confirm shutdown" in pending.display_text
        saved_pending = json.loads((root / "fibi_state.json").read_text(encoding="utf-8")).get("pending_action")
        assert core.action_confirmations.pending() is not None, f"saved pending action was {saved_pending!r}"
        deferred_warmup.run_persistence_checks()
        assert core.action_confirmations.pending() is not None
        cancel = core.respond("/cancel action")
        assert "canceled" in cancel.display_text
        assert core.action_confirmations.pending() is None

        # The confirmation is consumed once, while the destructive executor
        # remains unreachable even after the user supplies the exact phrase.
        executed_actions: list[str] = []
        original_execute = core.desktop_actions.execute

        def record_execute(intent):
            executed_actions.append(intent.action_type)
            return original_execute(intent)

        core.desktop_actions.execute = record_execute
        second_pending = core.respond("shutdown pc")
        assert "say: confirm shutdown" in second_pending.display_text
        confirmed = core.respond("confirm shutdown")
        assert "destructive system power actions remain disabled" in confirmed.display_text
        assert core.action_confirmations.pending() is None
        assert executed_actions == []
        assert core.action_confirmations.consume_if_confirmed("confirm shutdown") is None
        assert executed_actions == []

        status = core.respond("/actions status")
        assert status.model_used == "local-command"
        assert model.calls == 0
        assert "hands" in status.display_text

        search = core.respond("search Google for Python recursion")
        assert "search" in search.display_text or "opened" in search.display_text
        assert opened and "Python+recursion" in opened[-1]
        assert model.calls == 0

        youtube = core.respond("search YouTube lofi music")
        assert "youtube.com/results" in opened[-1]
        assert model.calls == 0

        wiki = core.respond("wiki Alan Turing")
        assert "wikipedia.org" in opened[-1]
        assert model.calls == 0

        opened_app = core.respond("open chrome")
        assert "Result: completed" in opened_app.display_text
        assert "Chrome opened" in opened_app.display_text
        assert launched
        assert model.calls == 0

        app_count = core.respond("/apps count")
        assert app_count.model_used == "local-command"
        app_search = core.respond("/apps search chrome")
        assert "Chrome" in app_search.display_text
        assert app_index.search("chrome").matches

        time_reply = core.respond("what time is it")
        date_reply = core.respond("what date is it")
        assert time_reply.model_used == "local-action"
        assert date_reply.model_used == "local-action"

        start = time.perf_counter()
        greeting = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert greeting.model_used == "local-greeting"
        assert model.calls == 0

        journal_entries = core.action_journal.recent(limit=5)
        assert journal_entries
        assert any(entry.action_type == "open_app" for entry in journal_entries)

        test_missing_import_fallbacks(root)

    print("Fibi v0.12 action smoke tests passed.")


if __name__ == "__main__":
    run()


