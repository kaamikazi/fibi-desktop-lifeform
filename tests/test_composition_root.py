"""Focused integration tests for one composed Fibi runtime."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

from fibi.app import composition
from fibi.app.composition import build_runtime
from fibi.ui.fibi_pet_window import FibiPetWindow


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_composition_builds_one_shared_core_graph(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "runtime-data"))
    runtime = build_runtime(gui_smoke=True)
    try:
        diagnostic = runtime.duplicate_service_diagnostic()
        assert diagnostic["ok"] is True
        assert all(diagnostic["checks"].values())
        assert runtime.core.services is runtime.services
        assert runtime.core.life is runtime.services.life
    finally:
        runtime.shutdown()


def test_pet_and_control_center_receive_the_same_core(qapp, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FIBI_DATA_DIR", str(tmp_path / "shared-ui-data"))
    runtime = build_runtime(gui_smoke=True)
    pet = FibiPetWindow(core=runtime.core, life=runtime.core.life)
    try:
        control_center = pet._open_control_center_shell()
        assert pet.core is runtime.core
        assert control_center.core is runtime.core
        assert control_center.life is runtime.core.life
    finally:
        pet._quitting = True
        pet.close()
        runtime.shutdown()


def test_configuration_is_resolved_once_per_runtime(monkeypatch, tmp_path: Path) -> None:
    calls = {"environment": 0, "paths": 0}

    def fake_environment(*_args, **_kwargs):
        calls["environment"] += 1
        from fibi.environment import EnvironmentStatus

        return EnvironmentStatus(False, "none", True, False, False, True)

    def fake_paths():
        calls["paths"] += 1
        from fibi.runtime_paths import RuntimePathInfo

        return RuntimePathInfo(False, False, tmp_path, tmp_path, tmp_path)

    monkeypatch.setattr(composition, "resolve_environment", fake_environment)
    monkeypatch.setattr(composition, "runtime_info", fake_paths)
    configuration = composition.resolve_runtime_configuration(gui_smoke=True)

    assert configuration.gui_smoke is True
    assert calls == {"environment": 1, "paths": 1}


def test_environment_resolution_is_cached_for_settings_imports(monkeypatch, tmp_path: Path) -> None:
    from fibi import environment

    calls = 0
    root = (tmp_path / "one-runtime").resolve()
    root.mkdir()
    key = (root, False, None)
    environment._RESOLVED_ENVIRONMENTS.pop(key, None)
    original = environment.load_environment

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(environment, "load_environment", counted)
    first = environment.resolve_environment(root, packaged=False)
    second = environment.resolve_environment(root, packaged=False)

    assert first is second
    assert calls == 1


def test_application_startup_imports_the_composition_root() -> None:
    from fibi import main

    source = inspect.getsource(main)
    assert "from fibi.app import build_runtime" in source
    assert "FibiPetWindow(core=runtime.core" in source
