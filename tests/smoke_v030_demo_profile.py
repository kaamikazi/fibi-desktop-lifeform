"""Smoke tests for the isolated v0.30 demo profile reset tool."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import reset_demo_profile


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        demo_root = reset_demo_profile.DEFAULT_DEMO_PROFILE
        normal_data = PROJECT_ROOT / "data"

        assert not reset_demo_profile.resolve_demo_profile(demo_root) == normal_data.resolve()
        try:
            reset_demo_profile.resolve_demo_profile(normal_data)
        except ValueError as exc:
            assert "normal Fibi data" in str(exc)
        else:
            raise AssertionError("normal data path was not refused")

        custom_outside = temp_root / "not_demo"
        try:
            reset_demo_profile.resolve_demo_profile(custom_outside)
        except ValueError as exc:
            assert "outside the demo profile" in str(exc)
        else:
            raise AssertionError("outside profile path was not refused")

        unmarked = demo_root / "unmarked_test"
        unmarked.mkdir(parents=True, exist_ok=True)
        (unmarked / "unknown.txt").write_text("not a demo marker", encoding="utf-8")
        try:
            try:
                reset_demo_profile.reset_profile(unmarked)
            except ValueError as exc:
                assert "unmarked demo profile" in str(exc)
            else:
                raise AssertionError("unmarked existing profile was not refused")
        finally:
            (unmarked / "unknown.txt").unlink(missing_ok=True)
            unmarked.rmdir()

    env = os.environ.copy()
    env.pop("FIBI_DATA_DIR", None)
    result = subprocess.run(
        [sys.executable, "tools/reset_demo_profile.py", "--confirm-demo-reset"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DEMO_PROFILE_READY" in result.stdout

    manifest = reset_demo_profile.DEFAULT_DEMO_PROFILE / "demo_manifest.json"
    payload = manifest.read_text(encoding="utf-8")
    assert "fictional_memory_count" in payload
    assert "normal_data_copied\": false" in payload
    assert "network_used\": false" in payload

    os.environ["FIBI_DATA_DIR"] = str(reset_demo_profile.DEFAULT_DEMO_PROFILE)
    from fibi.engines.core import FibiCore

    core = FibiCore()
    memories = core.memory_review.list_memories(include_archived=True, limit=20)
    texts = [item.text for item in memories]
    assert "Imran prefers Fibi to remain local-first." in texts
    assert "Demo memory scheduled for deletion." in texts
    assert any(item.pinned for item in memories)

    result_again = subprocess.run(
        [sys.executable, "tools/reset_demo_profile.py", "--confirm-demo-reset"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result_again.returncode == 0, result_again.stdout + result_again.stderr
    core_again = FibiCore()
    assert len(core_again.memory_review.list_memories(include_archived=True, limit=20)) == len(memories)

    print("Fibi v0.30 demo profile smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
