"""Lifecycle tests contain no GUI, provider, microphone, or desktop I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from fibi.app.composition import build_runtime
from fibi.app.runtime import ApplicationRuntime, RuntimeConfiguration
from fibi.environment import EnvironmentStatus
from fibi.runtime_paths import RuntimePathInfo


class _Services:
    def __init__(self) -> None:
        self.stop_count = 0
        self.tts_manager = object()

    def stop_partial(self) -> None:
        self.stop_count += 1


class _Core:
    life = object()

    def __init__(self) -> None:
        self.shutdown_count = 0

    def shutdown(self) -> None:
        self.shutdown_count += 1


def _configuration(tmp_path: Path) -> RuntimeConfiguration:
    paths = RuntimePathInfo(False, False, tmp_path, tmp_path, tmp_path)
    environment = EnvironmentStatus(False, "none", True, False, False, True)
    return RuntimeConfiguration(paths, environment)


def test_runtime_start_and_shutdown_are_idempotent(tmp_path: Path) -> None:
    services = _Services()
    core = _Core()
    runtime = ApplicationRuntime(_configuration(tmp_path), services, core)  # type: ignore[arg-type]

    assert runtime.start() is True
    assert runtime.start() is False
    assert runtime.shutdown() is True
    assert runtime.shutdown() is False
    assert core.shutdown_count == 1
    assert services.stop_count == 1


def test_partial_core_failure_cleans_constructed_services(tmp_path: Path) -> None:
    services = _Services()

    def fail_core(**_kwargs):
        raise RuntimeError("construction failed")

    with pytest.raises(RuntimeError, match="construction failed"):
        build_runtime(
            configuration=_configuration(tmp_path),
            services_factory=lambda _configuration: services,  # type: ignore[arg-type,return-value]
            core_factory=fail_core,
        )

    assert services.stop_count == 1


def test_configuration_repr_is_secret_free(tmp_path: Path) -> None:
    configuration = _configuration(tmp_path)
    rendered = repr(configuration)

    assert "API_KEY" not in rendered
    assert "token" not in rendered.lower()
    assert "gemini_key_configured=False" in rendered
