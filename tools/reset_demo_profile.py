"""Reset Fibi's isolated v0.30 demo profile with fictional memories.

This tool is intentionally narrow: it only operates on the demo profile folder
and refuses to touch Fibi's normal ``data/`` directory. Use it before recording
demo takes so every run starts from the same safe, fictional notebook.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_PROFILE = PROJECT_ROOT / "demo_runtime"
MARKER_FILENAME = ".fibi_demo_profile"
MARKER_TEXT = "FIBI_DEMO_PROFILE_V030"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True, slots=True)
class DemoMemorySeed:
    content: str
    category: str
    source_id: str
    pinned: bool = False
    approved: bool = True


DEMO_MEMORIES: tuple[DemoMemorySeed, ...] = (
    DemoMemorySeed("Imran prefers Fibi to remain local-first.", "fact", "demo_fact_local_first", pinned=True),
    DemoMemorySeed(
        "Fibi's guiding principle is: Presence before intelligence.",
        "belief",
        "demo_belief_presence_before_intelligence",
        pinned=True,
    ),
    DemoMemorySeed(
        "The current demo project is preparing a safe Build Week submission.",
        "project",
        "demo_project_build_week",
    ),
    DemoMemorySeed(
        "The user prefers confirmation before patches or browser actions.",
        "habit",
        "demo_habit_confirmation_first",
    ),
    DemoMemorySeed("Demo memory scheduled for deletion.", "event", "demo_event_delete_me"),
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset only Fibi's isolated demo profile.")
    parser.add_argument(
        "--confirm-demo-reset",
        action="store_true",
        help="Required. Confirms this may delete and recreate the isolated demo profile only.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=Path(os.getenv("FIBI_DEMO_PROFILE_DIR", DEFAULT_DEMO_PROFILE)),
        help="Demo profile directory. Defaults to E:\\Fibi chubi\\demo_runtime.",
    )
    return parser.parse_args(argv)


def resolve_demo_profile(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    project = PROJECT_ROOT.resolve()
    expected = DEFAULT_DEMO_PROFILE.resolve()

    if resolved == (project / "data").resolve():
        raise ValueError("Refusing to reset normal Fibi data/.")
    if resolved == project:
        raise ValueError("Refusing to reset the project root.")
    if resolved != expected and not _is_child_of(resolved, expected):
        raise ValueError(f"Refusing to reset outside the demo profile: {resolved}")
    return resolved


def reset_profile(profile_dir: Path) -> None:
    marker = profile_dir / MARKER_FILENAME
    if profile_dir.exists():
        if not marker.exists() and not any(profile_dir.iterdir()):
            marker.write_text(MARKER_TEXT + "\n", encoding="utf-8")
        if not marker.exists() or marker.read_text(encoding="utf-8").strip() != MARKER_TEXT:
            raise ValueError(f"Refusing to delete unmarked demo profile: {profile_dir}")
        shutil.rmtree(profile_dir)

    profile_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER_TEXT + "\n", encoding="utf-8")
    os.environ["FIBI_DATA_DIR"] = str(profile_dir)

    from fibi.engines.life_engine import LifeEngine
    from fibi.engines.memory_consent_engine import MemoryConsentEngine
    from fibi.engines.memory_review_engine import MemoryReviewEngine
    from fibi.rag.rag_memory_service import RAGMemoryServiceFacade

    life = LifeEngine(profile_dir / "fibi_state.json")
    life.update_mood("happy")
    consent = MemoryConsentEngine(profile_dir / "fibi_state.json")
    consent.reset()
    configure_demo_voice(profile_dir)

    rag = RAGMemoryServiceFacade()
    review = MemoryReviewEngine(rag, deletion_log_path=profile_dir / "memory" / "memory_deletion_log.jsonl")

    for seed in DEMO_MEMORIES:
        memory = rag.service.add_memory(
            seed.content,
            category=seed.category,
            source="demo_seed",
            source_id=seed.source_id,
            confidence=0.9,
            importance=0.7,
            metadata={
                "demo": True,
                "review": {
                    "approved": seed.approved,
                    "pinned": seed.pinned,
                    "archived": False,
                    "summary": seed.content,
                    "sensitive_flag": "",
                    "user_visible": True,
                },
            },
            provenance={"created_by": "tools/reset_demo_profile.py", "fictional_demo_data": True},
            allow_duplicate=True,
        )
        if seed.pinned and memory.id is not None:
            review.pin_memory(memory.id, True)

    manifest = {
        "profile": "fibi_v030_demo",
        "marker": MARKER_TEXT,
        "fictional_memory_count": len(DEMO_MEMORIES),
        "safe_fake_sensitive_value_for_manual_demo": "FAKE_DEMO_KEY_NOT_REAL_12345",
        "normal_data_copied": False,
        "network_used": False,
        "rvc_enabled": False,
    }
    (profile_dir / "demo_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def configure_demo_voice(profile_dir: Path) -> None:
    """Disable slow RVC only in the explicitly isolated demo profile."""

    from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine

    VoiceSkinSettingsEngine(profile_dir / "voice_skin_settings.json").update(
        allow_rvc_voice_skin=False,
        rvc_enabled=False,
    )


def _is_child_of(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv if argv is not None else sys.argv[1:]))
    if not args.confirm_demo_reset:
        print("Refusing reset without --confirm-demo-reset.")
        return 2

    try:
        profile_dir = resolve_demo_profile(Path(args.profile_dir))
        print(f"Resolved demo profile: {profile_dir}")
        reset_profile(profile_dir)
    except Exception as exc:
        print(f"DEMO_RESET_REFUSED: {exc}")
        return 1

    print("DEMO_PROFILE_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
