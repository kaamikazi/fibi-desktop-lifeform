"""Optional local RVC voice conversion adapter.

The public surface is stable even if third-party RVC Python packages change.
When conversion is unavailable or fails, callers should play the base edge-tts
audio instead.
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from fibi.engines.voice_skin_settings_engine import VoiceSkinSettings, VoiceSkinSettingsEngine
from fibi.paths import PROJECT_ROOT, data_path

TTS_TEMP_DIR = data_path("tts_temp")


@dataclass(slots=True)
class RvcValidationResult:
    ok: bool
    message: str


@dataclass(slots=True)
class RvcConversionResult:
    ok: bool
    output_path: Path | None = None
    message: str = ""
    fallback_used: bool = True
    duration_ms: float = 0.0


class RvcVoiceSkinEngine:
    """Validate and optionally convert base TTS audio through local RVC."""

    def __init__(self, temp_dir: Path = TTS_TEMP_DIR) -> None:
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.last_rvc_error = ""
        self.last_fallback_reason = "not run yet"
        self.last_duration_ms = 0.0

    def backend_available(self, settings: VoiceSkinSettings) -> bool:
        """Check whether the selected backend can be reached without converting."""
        try:
            if settings.rvc_backend == "rvc_python":
                if self._current_python_has_rvc():
                    self._clear_backend_diagnostics()
                    return True
                if self._venv_python_has_rvc():
                    self._clear_backend_diagnostics()
                    return True
                if not self.last_rvc_error:
                    self._record_backend_error(
                        "rvc_python is unavailable; install the optional package in .venv-rvc or choose another backend."
                    )
                return False
            if settings.rvc_backend == "rvc_webui_api":
                import requests

                response = requests.get(self._webui_url(settings), timeout=2)
                if response.status_code < 500:
                    self._clear_backend_diagnostics()
                    return True
                self._record_backend_error(
                    "The local RVC WebUI returned a server error; check that its API is running."
                )
                return False
            self._record_backend_error(
                "RVC backend is disabled; choose rvc_python or rvc_webui_api to enable the experiment."
            )
            return False
        except Exception:
            if settings.rvc_backend == "rvc_webui_api":
                message = "The local RVC WebUI probe failed; check its URL and that its API is running."
            else:
                message = "The RVC Python probe failed; check the selected interpreter and optional package installation."
            self._record_backend_error(message)
            return False

    def _clear_backend_diagnostics(self) -> None:
        self.last_rvc_error = ""
        self.last_fallback_reason = "none"

    def _record_backend_error(self, message: str) -> None:
        self.last_rvc_error = message
        self.last_fallback_reason = message

    def status(self, settings: VoiceSkinSettings) -> dict[str, object]:
        """Return beginner-readable diagnostics for /voice skin status."""
        model = VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)
        index = VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)
        return {
            "rvc_enabled": bool(settings.allow_rvc_voice_skin and settings.rvc_enabled),
            "backend": settings.rvc_backend,
            "model_path_exists": model.exists() and model.suffix.lower() == ".pth",
            "index_path_exists": index.exists() and index.suffix.lower() == ".index",
            "backend_available": self.backend_available(settings),
            "last_rvc_error": self.last_rvc_error or "none",
            "fallback_reason": self.last_fallback_reason or "none",
            "backend_hint": self._backend_hint(settings),
        }

    def validate(self, settings: VoiceSkinSettings) -> RvcValidationResult:
        if not settings.allow_rvc_voice_skin or not settings.rvc_enabled:
            self.last_fallback_reason = "voice skin off"
            return RvcValidationResult(False, "voice skin off")
        if settings.rvc_backend == "disabled":
            self.last_fallback_reason = "backend disabled"
            return RvcValidationResult(False, "backend disabled")
        model = VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)
        index = VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)
        if not model.exists() or model.suffix.lower() != ".pth":
            self.last_fallback_reason = "model crumb missing"
            return RvcValidationResult(False, "model crumb missing")
        if not index.exists() or index.suffix.lower() != ".index":
            self.last_fallback_reason = "index crumb missing"
            return RvcValidationResult(False, "index crumb missing")
        return RvcValidationResult(True, "voice skin ready")

    def convert(self, base_audio_path: Path, settings: VoiceSkinSettings) -> RvcConversionResult:
        started = time.perf_counter()
        validation = self.validate(settings)
        if not validation.ok:
            result = RvcConversionResult(False, None, validation.message, True, self._elapsed(started))
            self.last_duration_ms = result.duration_ms
            return result
        if settings.rvc_backend == "rvc_python":
            result = self._convert_rvc_python(base_audio_path, settings, started)
        elif settings.rvc_backend == "rvc_webui_api":
            result = self._convert_webui(base_audio_path, settings, started)
        else:
            result = RvcConversionResult(False, None, "backend disabled", True, self._elapsed(started))
        self.last_duration_ms = result.duration_ms
        return result

    def _convert_rvc_python(self, base_audio_path: Path, settings: VoiceSkinSettings, started: float) -> RvcConversionResult:
        try:
            module = importlib.import_module("rvc_python")
        except Exception as error:
            return self._convert_rvc_subprocess(base_audio_path, settings, started, error)

        output_path = self.temp_dir / f"rvc_voice_{int(time.time() * 1000)}.wav"
        try:
            converted = self._try_rvc_python_api(module, base_audio_path, output_path, settings)
        except Exception as error:
            self.last_rvc_error = repr(error)
            self.last_fallback_reason = f"rvc_python conversion failed: {error}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        if converted and output_path.exists() and output_path.stat().st_size > 0:
            self.last_rvc_error = ""
            self.last_fallback_reason = "none"
            return RvcConversionResult(True, output_path, "rvc_python converted", False, self._elapsed(started))

        self.last_fallback_reason = "rvc_python adapter unavailable"
        return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

    def _convert_rvc_subprocess(
        self,
        base_audio_path: Path,
        settings: VoiceSkinSettings,
        started: float,
        import_error: Exception,
    ) -> RvcConversionResult:
        python_path = self._venv_python_path()
        if not python_path.exists():
            self.last_rvc_error = repr(import_error)
            self.last_fallback_reason = f"rvc_python import failed: {import_error}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        output_path = self.temp_dir / f"rvc_voice_{int(time.time() * 1000)}.wav"
        command = [
            str(python_path),
            str(PROJECT_ROOT / "tools" / "rvc_convert.py"),
            "--input",
            str(base_audio_path),
            "--output",
            str(output_path),
            "--model",
            str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)),
            "--index",
            str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)),
            "--pitch",
            str(settings.rvc_pitch_shift),
            "--pitch-method",
            settings.rvc_pitch_extractor,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=max(5, settings.rvc_timeout_seconds),
                check=False,
            )
        except Exception as error:
            self.last_rvc_error = repr(error)
            self.last_fallback_reason = f"rvc subprocess failed: {error}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown subprocess error").strip().splitlines()[-1]
            self.last_rvc_error = detail
            self.last_fallback_reason = f"rvc subprocess failed: {detail}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        if output_path.exists() and output_path.stat().st_size > 0:
            self.last_rvc_error = ""
            self.last_fallback_reason = "none"
            return RvcConversionResult(True, output_path, "rvc subprocess converted", False, self._elapsed(started))

        self.last_fallback_reason = "rvc subprocess produced no audio"
        return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

    def _convert_webui(self, base_audio_path: Path, settings: VoiceSkinSettings, started: float) -> RvcConversionResult:
        try:
            import requests
        except Exception as error:
            self.last_rvc_error = repr(error)
            self.last_fallback_reason = f"requests import failed: {error}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        try:
            response = requests.get(self._webui_url(settings), timeout=2)
            response.raise_for_status()
        except Exception as error:
            self.last_rvc_error = repr(error)
            self.last_fallback_reason = f"rvc_webui_api unreachable: {error}"
            return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

        self.last_fallback_reason = "rvc_webui_api conversion endpoint not configured"
        return RvcConversionResult(False, None, self.last_fallback_reason, True, self._elapsed(started))

    def _try_rvc_python_api(
        self,
        module,
        base_audio_path: Path,
        output_path: Path,
        settings: VoiceSkinSettings,
    ) -> bool:
        """Try common rvc-python shapes without binding Fibi to one release."""
        inference_class = getattr(module, "RVCInference", None)
        if inference_class is None:
            try:
                infer_module = importlib.import_module("rvc_python.infer")
                inference_class = getattr(infer_module, "RVCInference", None)
            except Exception:
                inference_class = None
        if inference_class is None:
            return False

        engine = inference_class()
        if hasattr(engine, "load_model"):
            engine.load_model(str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)))
        if hasattr(engine, "load_index"):
            engine.load_index(str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)))

        attempts = (
            ("infer_file", {
                "input_path": str(base_audio_path),
                "output_path": str(output_path),
                "f0up_key": settings.rvc_pitch_shift,
                "f0method": settings.rvc_pitch_extractor,
                "index_path": str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)),
            }),
            ("infer_file", {
                "input_path": str(base_audio_path),
                "output_path": str(output_path),
                "pitch": settings.rvc_pitch_shift,
                "f0_method": settings.rvc_pitch_extractor,
                "index_path": str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)),
            }),
            ("convert_file", {
                "input_path": str(base_audio_path),
                "output_path": str(output_path),
                "model_path": str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_model_path)),
                "index_path": str(VoiceSkinSettingsEngine.resolve_path(settings.rvc_index_path)),
                "pitch": settings.rvc_pitch_shift,
            }),
        )
        for method_name, kwargs in attempts:
            method = getattr(engine, method_name, None)
            if method is None:
                continue
            try:
                method(**kwargs)
                return output_path.exists()
            except TypeError:
                continue
        method = getattr(engine, "infer_file", None) or getattr(engine, "convert_file", None)
        if method is None:
            return False
        method(str(base_audio_path), str(output_path))
        return output_path.exists()

    @staticmethod
    def _webui_url(settings: VoiceSkinSettings) -> str:
        return getattr(settings, "rvc_webui_url", "http://127.0.0.1:7865")

    def _backend_hint(self, settings: VoiceSkinSettings) -> str:
        if settings.rvc_backend == "rvc_python":
            return "uses current Python if possible, otherwise .venv-rvc Python 3.10."
        if settings.rvc_backend == "rvc_webui_api":
            return f"start a local RVC WebUI API at {self._webui_url(settings)}."
        return "choose /voice skin backend rvc_python or /voice skin backend rvc_webui_api."

    @staticmethod
    def _current_python_has_rvc() -> bool:
        return importlib.util.find_spec("rvc_python") is not None

    @staticmethod
    def _venv_python_path() -> Path:
        if sys.platform.startswith("win"):
            return PROJECT_ROOT / ".venv-rvc" / "Scripts" / "python.exe"
        return PROJECT_ROOT / ".venv-rvc" / "bin" / "python"

    def _venv_python_has_rvc(self) -> bool:
        python_path = self._venv_python_path()
        if not python_path.exists():
            self._record_backend_error(
                "The configured .venv-rvc Python interpreter is missing; create that optional environment or choose another backend."
            )
            return False
        completed = subprocess.run(
            [str(python_path), "-c", "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('rvc_python') else 1)"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            if completed.returncode == 1:
                message = "rvc_python is missing from .venv-rvc; install the optional package or choose another backend."
            else:
                message = "The rvc_python package probe failed in .venv-rvc; repair that optional environment."
            self._record_backend_error(message)
            return False
        return True

    def fallback_copy(self, base_audio_path: Path, suffix: str = ".wav") -> Path:
        output = self.temp_dir / f"rvc_fallback_{int(time.time() * 1000)}{suffix}"
        shutil.copy2(base_audio_path, output)
        return output

    @staticmethod
    def _elapsed(started: float) -> float:
        return (time.perf_counter() - started) * 1000
