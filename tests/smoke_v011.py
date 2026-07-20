"""Direct smoke tests for Fibi v0.11 desktop integration."""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.asset_health_engine import AssetHealthEngine
from fibi.engines.autostart_engine import AutostartEngine
from fibi.engines.core import FibiCore
from fibi.engines.data_health_engine import DataHealthEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.types import ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "Fibi", None)


class NoModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("", "no-model", 0.0, "disabled")


def make_core(root: Path) -> FibiCore:
    root.mkdir(parents=True, exist_ok=True)
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    settings_path = root / "fibi_settings.json"
    state.write_text(json.dumps({"legacy_v010": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=NoModel(),
        privacy=PrivacySettingsEngine(state),
        app_settings=AppSettingsEngine(settings_path),
        data_health=DataHealthEngine(database, state, settings_path, root / "exports"),
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)

        settings = AppSettingsEngine(root / "settings.json")
        assert settings.settings.minimize_to_tray is True
        assert settings.settings.setup_complete is False
        settings.update(start_minimized=True, animation_intensity="low", performance_debug_logs=True)
        reloaded = AppSettingsEngine(root / "settings.json")
        assert reloaded.settings.start_minimized is True
        assert reloaded.settings.animation_intensity == "low"
        setup = reloaded.complete_setup(skipped=False)
        assert setup.completed

        autostart = AutostartEngine(project_root=root)
        autostart.startup_dir = root / "Startup"
        autostart.launcher_path = autostart.startup_dir / "Fibi.cmd"
        blocked = autostart.enable(confirm=False)
        assert not blocked.enabled and blocked.error == "confirm required"
        enabled = autostart.enable(confirm=True)
        assert enabled.enabled and autostart.launcher_path.exists()
        disabled = autostart.disable()
        assert not disabled.enabled

        core = make_core(root / "core")
        assert core.respond("/settings").model_used == "local-command"
        assert core.respond("/voice off").display_text == "voice tucked away."
        assert core.privacy.settings.allow_tts is False
        assert core.respond("/voice on").display_text == "voice unboxed."
        assert core.respond("/sounds off").display_text == "sounds tucked away."
        assert core.privacy.settings.allow_sounds is False
        assert "animations low" in core.respond("/animations low").display_text
        assert core.app_settings.settings.animation_intensity == "low"
        assert "confirm" in core.respond("/autostart on").display_text
        assert core.respond("/startup status").display_text in {"startup on.", "startup off."}
        assert core.respond("/health").display_text
        assert core.respond("/assets").display_text
        assert core.respond("/status").display_text
        assert core.respond("/model status").display_text
        assert core.respond("hi").model_used == "local-greeting"

        data_health = core.data_health.check()
        assert data_health.ok
        asset_health = AssetHealthEngine().check()
        assert "blink" in " ".join(asset_health.checks.keys())

        state_before_shutdown = json.loads((root / "core" / "fibi_state.json").read_text(encoding="utf-8"))
        assert state_before_shutdown["legacy_v010"] == "keep"
        assert state_before_shutdown["clean_shutdown"] is False
        core.shutdown()
        state_after_shutdown = json.loads((root / "core" / "fibi_state.json").read_text(encoding="utf-8"))
        assert state_after_shutdown["clean_shutdown"] is True
        assert state_after_shutdown["legacy_v010"] == "keep"

        os.environ["FIBI_DATA_DIR"] = str(root / "portable_data")
        import fibi.paths as paths
        importlib.reload(paths)
        assert paths.data_dir() == root / "portable_data"
        assert paths.data_path("x.txt").parent == root / "portable_data"
        os.environ.pop("FIBI_DATA_DIR", None)
        importlib.reload(paths)

    print("Fibi v0.11 smoke tests passed.")


if __name__ == "__main__":
    run()


