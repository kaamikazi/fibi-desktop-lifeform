"""Direct smoke tests for Fibi v0.15 Project Workspace Mode."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.context_engine import ContextEngine
from fibi.engines.core import FibiCore
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.life_engine import LifeEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.types import ModelResult, Observation


class FakeObservation(ObservationEngine):
    def observe(self, include_clipboard: bool = False) -> Observation:
        return Observation("now", "afternoon", "Code", "Fibi", None)


class NoModel(ModelEngine):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> ModelResult:
        self.calls += 1
        return ModelResult("project thought", "no-model", 0.0, None)


def make_sample_project(root: Path) -> Path:
    project = root / "KamikazeOS"
    (project / "app").mkdir(parents=True)
    (project / "components").mkdir()
    (project / "node_modules" / "huge").mkdir(parents=True)
    (project / ".git").mkdir()
    (project / ".vscode").mkdir()
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"next": "1", "react": "1"}, "devDependencies": {"typescript": "1", "tailwindcss": "1"}, "scripts": {"dev": "next dev"}}),
        encoding="utf-8",
    )
    (project / "tsconfig.json").write_text("{}", encoding="utf-8")
    (project / "app" / "page.tsx").write_text("export default function Page(){return <main>Hello</main>}", encoding="utf-8")
    (project / "components" / "Button.tsx").write_text("export function Button(){return null}", encoding="utf-8")
    fake_api_key = "sk-" + "secretsecretsecretsecretsecret12"
    (project / ".env").write_text(f"OPENAI_API_KEY={fake_api_key}", encoding="utf-8")
    (project / "node_modules" / "huge" / "ignored.js").write_text("ignored", encoding="utf-8")
    return project


def make_core(root: Path, project: Path, launched: list[str]) -> FibiCore:
    database = root / "fibi_memory.db"
    state = root / "fibi_state.json"
    state.write_text(json.dumps({"legacy_v014": "keep"}), encoding="utf-8")
    memory = MemoryEngine(database)
    journal = JournalEngine(database)
    context = ContextEngine(SecretSanitizer())
    workspace = ProjectWorkspaceEngine(root / "project_workspaces.json", context=context, sanitizer=SecretSanitizer())
    app_index = AppIndexEngine(root / "app_index.json")
    fake_code = root / "Code.exe"
    fake_code.write_text("", encoding="utf-8")
    app_index.add_entry("Code", str(fake_code), "test")
    return FibiCore(
        life=LifeEngine(state),
        memory=memory,
        observation=FakeObservation(),
        journal=journal,
        patterns=PatternEngine(memory, journal),
        model=NoModel(),
        privacy=PrivacySettingsEngine(state),
        context_engine=context,
        project_workspace=workspace,
        app_index=app_index,
        desktop_actions=DesktopActionEngine(app_index, app_launcher=lambda path: launched.append(path)),
    )


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        project = make_sample_project(root)
        launched: list[str] = []
        core = make_core(root, project, launched)

        missing = core.respond("/project add")
        assert "unknown tiny command" in missing.display_text or "project" in missing.display_text

        added = core.respond(f"/project add {project}")
        assert "project nest added" in added.display_text
        assert core.project_workspace.current().name == "KamikazeOS"

        scan = core.project_workspace.scan_current()
        assert scan.ok
        names = {entry.relative_path for entry in scan.files}
        assert "app/page.tsx" in names
        assert "node_modules/huge/ignored.js" not in names
        assert ".git" not in names
        env_entry = next(entry for entry in scan.files if entry.relative_path == ".env")
        assert not env_entry.safe_to_read and "secret" in env_entry.ignored_reason
        assert {"Node", "React", "Next.js", "TypeScript", "Tailwind"}.issubset(set(scan.workspace.detected_stack))

        files = core.respond("/project files")
        assert "app/page.tsx" in files.display_text
        search = core.respond("/project search Button")
        assert "components/Button.tsx" in search.display_text

        read_safe = core.respond("/project read app/page.tsx")
        assert "reading that file crumb" in read_safe.display_text
        assert core.context_engine.last() is not None

        read_secret = core.respond("/project read .env")
        assert "secret crumbs" in read_secret.display_text

        outside = root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        traversal = core.respond(f"/project read ..\\{outside.name}")
        assert "outside the project" in traversal.display_text

        summary = core.respond("/project summary")
        assert "Next.js" in summary.display_text
        assert "OPENAI" not in summary.display_text

        note = core.respond("/project note remember this is the desktop creature project")
        assert "project note" in note.display_text
        memories = core.memory.retrieve("desktop creature project", limit=3)
        assert memories

        current = core.respond("/project current")
        assert "KamikazeOS" in current.display_text
        listed = core.respond("/project list")
        assert "KamikazeOS" in listed.display_text

        open_vscode = core.respond("/project open vscode")
        assert "opening the project nest" in open_vscode.display_text
        assert launched

        privacy = core.respond("/project privacy")
        assert "no terminal" in privacy.display_text and "no edits" in privacy.display_text
        assert core.privacy.settings.allow_cloud_model is False

        forget_prompt = core.respond("/project forget KamikazeOS")
        assert "needs confirm" in forget_prompt.display_text
        assert core.project_workspace.current() is not None
        forgot = core.respond("/project forget KamikazeOS confirm")
        assert "forgotten" in forgot.display_text
        assert core.project_workspace.current() is None

        assert (project / "app" / "page.tsx").read_text(encoding="utf-8").startswith("export default")

        start = time.perf_counter()
        greeting = core.respond("hi")
        assert (time.perf_counter() - start) * 1000 < 300
        assert greeting.model_used == "local-greeting"

    print("Fibi v0.15 project workspace smoke tests passed.")


if __name__ == "__main__":
    run()


