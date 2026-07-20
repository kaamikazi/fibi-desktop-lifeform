"""Smoke tests for Fibi v0.16 Safe Project Edit Suggestions."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.diff_generator import DiffGenerator
from fibi.engines.project_edit_planner import ProjectEditPlanner
from tests.smoke_v015_project_workspace import make_core


def make_edit_project(root: Path) -> Path:
    project = root / "TinyApp"
    (project / "app").mkdir(parents=True)
    (project / "components").mkdir()
    (project / "lib").mkdir()
    (project / "package.json").write_text(json.dumps({"dependencies": {"next": "1", "react": "1"}}), encoding="utf-8")
    (project / "app" / "page.tsx").write_text(
        "export default function Page(){return <main><h1>Old Title</h1></main>}\n",
        encoding="utf-8",
    )
    (project / "components" / "Button.tsx").write_text(
        "export function Button(){return <button className=\"px-2\">Click</button>}\n",
        encoding="utf-8",
    )
    (project / "lib" / "auth.ts").write_text("export const checkAuth = () => true\n", encoding="utf-8")
    (project / ".env").write_text("SECRET_KEY=<dummy-secret-value>", encoding="utf-8")
    return project


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = make_edit_project(root)
        launched: list[str] = []
        core = make_core(root, project, launched)
        core.respond(f"/project add {project}")

        assert core.project_edit_planner.detects_edit_intent("make the button blue")

        ambiguous = core.respond("/edit plan change the title in package page")
        assert "which file crumb" in ambiguous.display_text

        button_path = project / "components" / "Button.tsx"
        original_button = button_path.read_text(encoding="utf-8")
        safe = core.respond("/edit file components/Button.tsx make the button blue")
        assert "manual edit suggestion" in safe.display_text
        assert "no auto-apply" in safe.display_text
        assert "diff" in safe.display_text
        assert button_path.read_text(encoding="utf-8") == original_button

        natural = core.respond("change components/Button.tsx to make the button blue")
        assert "manual edit suggestion" in natural.display_text
        assert button_path.read_text(encoding="utf-8") == original_button

        secret = core.respond("/edit file .env change SECRET_KEY")
        assert "secret crumbs" in secret.display_text

        outside = root / "outside.ts"
        outside.write_text("outside", encoding="utf-8")
        outside_result = core.respond("/edit file ../outside.ts change text")
        assert "outside the project" in outside_result.display_text or "can't chew" in outside_result.display_text

        delete_result = core.respond("/edit file components/Button.tsx delete file")
        assert "too sharp" in delete_result.display_text

        terminal_result = core.respond("/edit plan run command npm install left-pad")
        assert "too sharp" in terminal_result.display_text

        auth = core.project_edit_planner.plan("change lib/auth.ts auth payment security behavior", ["lib/auth.ts"])
        assert auth.risk_level == "high"
        assert auth.can_apply_automatically is False

        diff = DiffGenerator().unified_diff("x.txt", "hello\n", "hello tiny\n")
        assert diff.diff_text.startswith("--- a/x.txt")
        block = DiffGenerator().replacement_block("x.txt", "hello\n", "hello tiny\n")
        assert block.before == "hello"
        assert block.after == "hello tiny"

        copy_last = core.respond("/edit copy last")
        assert "manual edit suggestion" in copy_last.display_text or copy_last.display_text.strip()

        assert core.privacy.settings.allow_cloud_model is False
        assert button_path.read_text(encoding="utf-8") == original_button

        start = time.perf_counter()
        greeting = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert greeting.model_used == "local-greeting"

    print("Fibi v0.16 project edit suggestion smoke tests passed.")


if __name__ == "__main__":
    run()


