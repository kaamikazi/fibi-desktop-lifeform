"""Pytest wrapper for optional RVC voice skin smoke tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from fibi.engines.rvc_voice_skin_engine import RvcVoiceSkinEngine
from fibi.engines.voice_cache_engine import VoiceCacheEngine
from fibi.engines.voice_skin_settings_engine import VoiceSkinSettings
from fibi.voice.speak import prepare_voice_output
from tests.smoke_v016_voice_skin import run


def test_v016_voice_skin() -> None:
    run()


def _enabled_rvc_settings() -> VoiceSkinSettings:
    return VoiceSkinSettings(
        allow_rvc_voice_skin=True,
        rvc_enabled=True,
        rvc_backend="rvc_python",
    )


def test_rvc_missing_interpreter_has_actionable_safe_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = RvcVoiceSkinEngine(tmp_path / "tts_temp")
    missing_interpreter = tmp_path / "missing-python"
    monkeypatch.setattr(engine, "_current_python_has_rvc", lambda: False)
    monkeypatch.setattr(engine, "_venv_python_path", lambda: missing_interpreter)

    assert engine.backend_available(_enabled_rvc_settings()) is False
    assert "interpreter is missing" in engine.last_rvc_error
    assert "create that optional environment" in engine.last_rvc_error
    assert str(tmp_path) not in engine.last_rvc_error


def test_rvc_missing_optional_package_has_actionable_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = RvcVoiceSkinEngine(tmp_path / "tts_temp")
    interpreter = tmp_path / "python"
    interpreter.touch()
    monkeypatch.setattr(engine, "_current_python_has_rvc", lambda: False)
    monkeypatch.setattr(engine, "_venv_python_path", lambda: interpreter)
    monkeypatch.setattr(
        "fibi.engines.rvc_voice_skin_engine.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr=""),
    )

    assert engine.backend_available(_enabled_rvc_settings()) is False
    assert "rvc_python is missing" in engine.last_rvc_error
    assert "install the optional package" in engine.last_rvc_error


def test_rvc_probe_failure_is_safe_and_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = RvcVoiceSkinEngine(tmp_path / "tts_temp")
    interpreter = tmp_path / "python"
    interpreter.touch()
    monkeypatch.setattr(engine, "_current_python_has_rvc", lambda: False)
    monkeypatch.setattr(engine, "_venv_python_path", lambda: interpreter)

    def fail_probe(*args, **kwargs):
        raise OSError(f"private probe path: {tmp_path}")

    monkeypatch.setattr("fibi.engines.rvc_voice_skin_engine.subprocess.run", fail_probe)

    assert engine.backend_available(_enabled_rvc_settings()) is False
    assert "probe failed" in engine.last_rvc_error
    assert "check the selected interpreter" in engine.last_rvc_error
    assert str(tmp_path) not in engine.last_rvc_error


def test_available_rvc_backend_clears_stale_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = RvcVoiceSkinEngine(tmp_path / "tts_temp")
    engine.last_rvc_error = "stale failure"
    engine.last_fallback_reason = "stale fallback"
    monkeypatch.setattr(engine, "_current_python_has_rvc", lambda: True)

    assert engine.backend_available(_enabled_rvc_settings()) is True
    assert engine.last_rvc_error == ""
    assert engine.last_fallback_reason == "none"


def test_base_voice_output_uses_injected_synthesis_without_rvc(
    tmp_path: Path,
) -> None:
    engine = RvcVoiceSkinEngine(tmp_path / "tts_temp")
    cache = VoiceCacheEngine(tmp_path / "voice_cache")
    settings = VoiceSkinSettings()

    def synthesize_synthetic_audio(text: str, destination: str | Path) -> bool:
        Path(destination).write_bytes(b"synthetic base audio")
        return True

    result = prepare_voice_output(
        "synthetic voice fallback",
        settings,
        engine,
        cache,
        synthesize=synthesize_synthetic_audio,
    )

    assert result.edge_tts_ok is True
    assert result.final_audio_path == result.base_audio_path
    assert result.converted is False
    assert result.fallback_used is True
    assert result.fallback_reason == "voice skin disabled"


