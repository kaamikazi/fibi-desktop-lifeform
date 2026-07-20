"""Install a local RVC voice model zip into voice_models/fibi_rvc.

This helper only extracts .pth and .index files. It never runs code from the
archive and never downloads anything.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESTINATION = PROJECT_ROOT / "voice_models" / "fibi_rvc"


def install(zip_path: str | Path, destination: Path = DESTINATION) -> tuple[Path, Path]:
    source = Path(zip_path).expanduser().resolve()
    if not source.exists() or not source.is_file() or source.suffix.lower() != ".zip":
        raise SystemExit("give me a local .zip crumb.")
    destination.mkdir(parents=True, exist_ok=True)
    model_entry = None
    index_entry = None
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            name = Path(entry.filename).name
            suffix = Path(name).suffix.lower()
            if entry.is_dir() or not name:
                continue
            if suffix == ".pth" and model_entry is None:
                model_entry = entry
            elif suffix == ".index" and index_entry is None:
                index_entry = entry
        if model_entry is None or index_entry is None:
            raise SystemExit("zip needs one .pth and one .index crumb.")
        model_path = destination / "model.pth"
        index_path = destination / "model.index"
        _extract_one(archive, model_entry, model_path)
        _extract_one(archive, index_entry, index_path)
    return model_path, index_path


def _extract_one(archive: zipfile.ZipFile, entry: zipfile.ZipInfo, target: Path) -> None:
    if Path(entry.filename).name != entry.filename.split("/")[-1].split("\\")[-1]:
        # We flatten filenames intentionally to avoid zip-slip path tricks.
        pass
    with archive.open(entry) as source, target.open("wb") as output:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('usage: python tools/install_rvc_voice_model.py "path/to/model.zip"')
        return 2
    model_path, index_path = install(argv[1])
    print(f"installed model: {model_path}")
    print(f"installed index: {index_path}")
    print("Use only voice models you have permission to use. Do not distribute unauthorized models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
