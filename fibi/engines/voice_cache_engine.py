"""Local voice skin cache for short converted lines."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fibi.paths import data_path

VOICE_CACHE_DIR = data_path("voice_cache")


class VoiceCacheEngine:
    """Cache optional converted audio without storing long/private messages."""

    def __init__(self, cache_dir: Path = VOICE_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def key(
        self,
        text: str,
        language: str,
        base_voice: str,
        model_path: str,
        pitch_shift: int,
        suffix: str = ".wav",
    ) -> Path:
        model_hash = hashlib.sha256(str(model_path).encode("utf-8")).hexdigest()[:12]
        text_hash = hashlib.sha256(f"{text}|{language}|{base_voice}|{model_hash}|{pitch_shift}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{text_hash}{suffix}"

    @staticmethod
    def can_cache(text: str, max_chars: int = 120) -> bool:
        return 0 < len(text.strip()) <= max_chars and "\n" not in text

    def status_line(self) -> str:
        files = list(self.cache_dir.glob("*"))
        size = sum(path.stat().st_size for path in files if path.is_file())
        return f"voice cache: {len(files)} crumbs, {size // 1024} KB."

    def clear(self) -> int:
        count = 0
        for path in self.cache_dir.glob("*"):
            if path.is_file():
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    pass
        return count

    def store(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
