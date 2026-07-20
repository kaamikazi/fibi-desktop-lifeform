"""Optional local RVC voice skin settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from fibi.paths import data_path
from fibi.paths import PROJECT_ROOT

VOICE_SKIN_SETTINGS_PATH = data_path("voice_skin_settings.json")
DEFAULT_RVC_MODEL_PATH = PROJECT_ROOT / "voice_models" / "fibi_rvc" / "model.pth"
DEFAULT_RVC_INDEX_PATH = PROJECT_ROOT / "voice_models" / "fibi_rvc" / "model.index"


@dataclass(slots=True)
class VoiceSkinSettings:
    allow_rvc_voice_skin: bool = False
    rvc_enabled: bool = False
    rvc_model_path: str | None = None
    rvc_index_path: str | None = None
    rvc_pitch_extractor: str = "rmvpe"
    rvc_pitch_shift: int = 0
    rvc_speaker_id: int = 0
    rvc_backend: str = "disabled"
    rvc_webui_url: str = "http://127.0.0.1:7865"
    rvc_output_format: str = "wav"
    rvc_cache_enabled: bool = True
    rvc_cache_short_lines: bool = True
    rvc_timeout_seconds: int = 120
    edge_tts_base_voice_en: str = "en-US-AnaNeural"
    edge_tts_base_voice_ja: str = "ja-JP-NanamiNeural"


class VoiceSkinSettingsEngine:
    """Persist optional RVC voice skin settings outside core privacy state."""

    BACKENDS = {"disabled", "rvc_python", "rvc_webui_api"}

    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = Path(settings_path) if settings_path is not None else data_path("voice_skin_settings.json")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()
        self.save()

    def update(self, **changes) -> VoiceSkinSettings:
        current = asdict(self.settings)
        for key, value in changes.items():
            if key not in current:
                continue
            if key == "rvc_backend" and value not in self.BACKENDS:
                continue
            current[key] = value
        self.settings = VoiceSkinSettings(**current)
        self.save()
        return self.settings

    def status_line(self) -> str:
        if not self.settings.rvc_enabled:
            return "voice skin off."
        if not self.settings.allow_rvc_voice_skin:
            return "voice skin locked."
        if not self.settings.rvc_model_path or not self.settings.rvc_index_path:
            return "voice skin missing crumbs."
        return f"voice skin {self.settings.rvc_backend}. pitch {self.settings.rvc_pitch_shift}."

    def _load(self) -> VoiceSkinSettings:
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        defaults = asdict(VoiceSkinSettings())
        if isinstance(raw, dict):
            defaults.update({key: raw[key] for key in defaults if key in raw})
        settings = VoiceSkinSettings(**defaults)
        return self._repair_missing_model_paths(settings)

    def _repair_missing_model_paths(self, settings: VoiceSkinSettings) -> VoiceSkinSettings:
        """Recover from stale temp paths by using the bundled local model files."""
        model_path = self.resolve_path(settings.rvc_model_path)
        index_path = self.resolve_path(settings.rvc_index_path)
        changes = {}
        if (not model_path.exists() or model_path.suffix.lower() != ".pth") and DEFAULT_RVC_MODEL_PATH.exists():
            changes["rvc_model_path"] = str(DEFAULT_RVC_MODEL_PATH)
        if (not index_path.exists() or index_path.suffix.lower() != ".index") and DEFAULT_RVC_INDEX_PATH.exists():
            changes["rvc_index_path"] = str(DEFAULT_RVC_INDEX_PATH)
        if not changes:
            return settings
        current = asdict(settings)
        current.update(changes)
        return VoiceSkinSettings(**current)

    @staticmethod
    def resolve_path(path: str | None) -> Path:
        if not path:
            return Path("")
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            return candidate
        return PROJECT_ROOT / candidate

    def save(self) -> None:
        self.settings_path.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")
