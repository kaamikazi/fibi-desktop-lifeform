"""Smoke tests for Fibi v0.26 local beta feedback flow."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.smoke_v012_actions import make_core
from tools.build_windows import release_zip_path


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        os.environ["FIBI_DATA_DIR"] = str(root / "data")
        core, _, _ = make_core(root / "core", [], [])

        assert "issue saved" in core.respond("/issue new voice squeaked").display_text
        issue = core.issues.last()
        assert issue is not None
        assert issue.issue_id in core.respond("/issue list").display_text
        assert "closed" in core.respond(f"/issue close {issue.issue_id}").display_text
        assert "reopened" in core.respond(f"/issue reopen {issue.issue_id}").display_text
        assert "packed issue crumb" in core.respond(f"/issue export {issue.issue_id}").display_text
        assert "feedback saved" in core.respond("/feedback new beta feels cozy").display_text
        assert "packed feedback crumbs" in core.respond("/feedback export").display_text
        assert "packed the safe crumbs" in core.respond(f"/support bundle for issue {issue.issue_id}").display_text
        assert "release health v0.30.0" in core.respond("/release health").display_text
        assert "local update manifest" in core.respond("/update status").display_text
        assert "update safety" in core.respond("/update safety").display_text
        assert "paths:" in core.respond("/debug paths").display_text
        assert release_zip_path().name == "Fibi_Chubi_v0.30.0_windows_beta.zip"

    print("Fibi v0.26 beta feedback smoke tests passed.")


if __name__ == "__main__":
    run()


