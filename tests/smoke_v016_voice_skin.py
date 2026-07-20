"""Smoke tests for optional local RVC voice skin support."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.rvc_voice_skin_engine import RvcVoiceSkinEngine
from fibi.engines.voice_cache_engine import VoiceCacheEngine
from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine
from fibi.voice.speak import prepare_voice_output
from tests.smoke_v012_actions import make_core
from tools.install_rvc_voice_model import install


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        settings = VoiceSkinSettingsEngine(root / "voice_skin.json")
        assert settings.settings.rvc_enabled is False
        assert settings.settings.allow_rvc_voice_skin is False

        rvc = RvcVoiceSkinEngine(root / "tts_temp")
        assert not rvc.validate(settings.settings).ok

        fake_model = root / "fake.pth"
        fake_index = root / "fake.index"
        fake_model.write_bytes(b"fake model")
        fake_index.write_bytes(b"fake index")
        settings.update(
            allow_rvc_voice_skin=True,
            rvc_enabled=True,
            rvc_backend="rvc_python",
            rvc_model_path=str(fake_model),
            rvc_index_path=str(fake_index),
        )
        reloaded = VoiceSkinSettingsEngine(root / "voice_skin.json")
        assert reloaded.settings.allow_rvc_voice_skin is True
        assert reloaded.settings.rvc_enabled is True
        assert reloaded.settings.rvc_model_path == str(fake_model)
        assert reloaded.settings.rvc_index_path == str(fake_index)
        assert rvc.validate(settings.settings).ok
        backend_available = rvc.backend_available(settings.settings)
        assert isinstance(backend_available, bool)
        if not backend_available:
            assert rvc.last_rvc_error
        base_audio = root / "base.mp3"
        base_audio.write_bytes(b"audio")
        result = rvc.convert(base_audio, settings.settings)
        if not result.ok:
            assert result.fallback_used
            assert "fallback" in rvc.last_fallback_reason or "failed" in rvc.last_fallback_reason or "unavailable" in rvc.last_fallback_reason

        cache = VoiceCacheEngine(root / "voice_cache")
        key = cache.key("hello", "en", "voice", str(fake_model), 0)
        assert key.suffix == ".wav"
        assert cache.can_cache("hello")
        assert not cache.can_cache("x" * 200)
        assert "voice cache" in cache.status_line()
        assert cache.clear() == 0

        class FakeSuccessfulRvc:
            temp_dir = root / "tts_temp"
            last_fallback_reason = "none"

            def convert(self, base_audio_path, active_settings):
                from fibi.engines.rvc_voice_skin_engine import RvcConversionResult

                converted_path = root / "converted.wav"
                converted_path.write_bytes(b"converted")
                return RvcConversionResult(True, converted_path, "converted", False, 1.0)

        FakeSuccessfulRvc.temp_dir.mkdir(parents=True, exist_ok=True)

        def fake_synthesize(text, path):
            Path(path).write_bytes(b"base")
            return True

        played: list[str] = []
        voice_output = prepare_voice_output(
            "hello",
            settings.settings,
            FakeSuccessfulRvc(),
            cache,
            synthesize=fake_synthesize,
        )
        assert voice_output.final_audio_path is not None
        played.append(str(voice_output.final_audio_path))
        assert played[0].endswith("converted.wav") or played[0].endswith(".wav")
        assert "base.mp3" not in played[0]
        assert voice_output.converted is True
        assert voice_output.fallback_used is False

        zip_path = root / "voice.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("nested/model_file.pth", b"model")
            archive.writestr("nested/model_file.index", b"index")
            archive.writestr("nested/ignore.txt", b"ignore")
        destination = root / "voice_models" / "fibi_rvc"
        model_path, index_path = install(zip_path, destination)
        assert model_path.exists()
        assert index_path.exists()
        assert model_path.name == "model.pth"
        assert index_path.name == "model.index"

        opened: list[str] = []
        launched: list[str] = []
        core, model, _ = make_core(root / "core", opened, launched)
        core.voice_skin_settings = VoiceSkinSettingsEngine(root / "core" / "voice_skin_settings.json")
        core.rvc_voice_skin = RvcVoiceSkinEngine(root / "core" / "tts_temp")
        core.voice_cache = VoiceCacheEngine(root / "core" / "voice_cache")
        status = core.respond("/voice skin status")
        assert "rvc_enabled" in status.display_text
        assert "fallback reason" in status.display_text
        assert model.calls == 0
        model_cmd = core.respond(f"/voice skin model {model_path}")
        assert "model crumb found" in model_cmd.display_text
        index_cmd = core.respond(f"/voice skin index {index_path}")
        assert "index crumb found" in index_cmd.display_text
        backend = core.respond("/voice skin backend rvc_python")
        assert "rvc_python" in backend.display_text
        enabled = core.respond("/voice skin on confirm")
        assert "voice skin ready" in enabled.display_text or "voice skin tripped" in enabled.display_text
        test = core.respond("/voice skin test")
        assert "voice" in test.display_text
        clear = core.respond("/voice cache clear")
        assert "voice cache cleared" in clear.display_text
        cache_status = core.respond("/voice cache status")
        assert "voice cache" in cache_status.display_text
        assert model.calls == 0

    print("Fibi v0.16 voice skin smoke tests passed.")


if __name__ == "__main__":
    run()


