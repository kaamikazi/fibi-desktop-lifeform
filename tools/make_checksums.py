"""Generate SHA256 checksums for Fibi release artifacts."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.build_windows import DIST_DIR, release_zip_path

CHECKSUM_PATH = DIST_DIR / "checksums_v0.30.2.txt"
INSTALLER_PATH = DIST_DIR / "installers" / "Fibi_Chubi_Setup_v0.30.2.exe"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_checksums() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for path in (release_zip_path(), INSTALLER_PATH):
        if path.exists():
            lines.append(f"{sha256(path)}  {path.name}")
    if not lines:
        lines.append("# no release artifacts found")
    CHECKSUM_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"checksums: {CHECKSUM_PATH}")
    return CHECKSUM_PATH


def main() -> int:
    generate_checksums()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
