"""Safe project check preset discovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fibi.engines.types import CheckCommandPreset, ProjectWorkspace

DANGEROUS_TOKENS = (
    "install",
    " add ",
    "remove",
    " rm",
    " del",
    "rmdir",
    "shutdown",
    "restart",
    "format",
    "migrate",
    "prisma migrate",
    "deploy",
    "publish",
    "curl",
    "wget",
    "powershell",
    "cmd",
    "bash",
    " sh",
    "sudo",
    "chmod",
    "chown",
    "ssh",
    "scp",
    "ftp",
    "git ",
)


class ProjectCheckPresetEngine:
    """Build a whitelist of checks from project files."""

    NODE_SCRIPT_KEYS = {
        "lint": ("npm run lint", ["npm", "run", "lint"], "low"),
        "test": ("npm run test", ["npm", "run", "test"], "medium"),
        "build": ("npm run build", ["npm", "run", "build"], "medium"),
        "typecheck": ("npm run typecheck", ["npm", "run", "typecheck"], "medium"),
    }

    def presets_for(self, workspace: ProjectWorkspace) -> list[CheckCommandPreset]:
        root = Path(workspace.root_path)
        presets = [
            CheckCommandPreset("python-version", "python --version", [sys.executable, "--version"], "low", "generic", "Show Python version."),
        ]
        if self._has_python_project(root):
            presets.append(CheckCommandPreset("python-compileall", "python -m compileall .", [sys.executable, "-m", "compileall", "."], "low", "python", "Compile Python files."))
            if (root / "tests").exists() or (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
                presets.append(CheckCommandPreset("python-pytest", "python -m pytest", [sys.executable, "-m", "pytest"], "medium", "python", "Run pytest."))
        if (root / "package.json").exists():
            presets.extend(self._node_presets(root / "package.json"))
            presets.append(CheckCommandPreset("node-version", "node --version", ["node", "--version"], "low", "generic", "Show Node version."))
            presets.append(CheckCommandPreset("npm-version", "npm --version", ["npm", "--version"], "low", "generic", "Show npm version."))
        return self._dedupe(presets)

    def find(self, workspace: ProjectWorkspace, key_or_alias: str) -> CheckCommandPreset | None:
        normalized = self.normalize_key(key_or_alias)
        aliases = {
            "compile": "python-compileall",
            "compileall": "python-compileall",
            "tests": "python-pytest",
            "test": "python-pytest",
            "lint": "npm-lint",
            "build": "npm-build",
            "typecheck": "npm-typecheck",
            "check": "python-compileall",
        }
        wanted = aliases.get(normalized, normalized)
        for preset in self.presets_for(workspace):
            if preset.command_key == wanted or self.normalize_key(preset.display) == wanted:
                return preset
        return None

    def detect_intent(self, text: str, workspace: ProjectWorkspace) -> CheckCommandPreset | None:
        lowered = text.lower().strip()
        if lowered in {"check this project", "compile project", "run check"}:
            return self.find(workspace, "compile")
        if "run lint" in lowered or "lint project" in lowered:
            return self.find(workspace, "lint")
        if "run test" in lowered or "run tests" in lowered or "test project" in lowered:
            return self.find(workspace, "tests") or self.find(workspace, "test")
        if "run build" in lowered or "build project" in lowered:
            return self.find(workspace, "build")
        if "typecheck" in lowered or "type check" in lowered:
            return self.find(workspace, "typecheck")
        return None

    def _node_presets(self, package_path: Path) -> list[CheckCommandPreset]:
        try:
            raw = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        scripts = raw.get("scripts", {}) if isinstance(raw, dict) else {}
        if not isinstance(scripts, dict):
            return []
        presets: list[CheckCommandPreset] = []
        for script, (display, args, risk) in self.NODE_SCRIPT_KEYS.items():
            command = str(scripts.get(script, ""))
            if not command or self._dangerous(command) or script in {"install", "preinstall", "postinstall", "deploy", "publish"}:
                continue
            key = f"npm-{script}"
            presets.append(CheckCommandPreset(key, display, args, risk, "package.json", f"Run package script {script}."))
            if (package_path.parent / "pnpm-lock.yaml").exists():
                presets.append(CheckCommandPreset(f"pnpm-{script}", f"pnpm run {script}", ["pnpm", "run", script], risk, "package.json", f"Run pnpm script {script}."))
            if (package_path.parent / "yarn.lock").exists():
                presets.append(CheckCommandPreset(f"yarn-{script}", f"yarn {script}", ["yarn", script], risk, "package.json", f"Run yarn script {script}."))
        return presets

    @staticmethod
    def _has_python_project(root: Path) -> bool:
        return any(root.glob("*.py")) or (root / "tests").exists() or (root / "requirements.txt").exists() or (root / "pyproject.toml").exists()

    @staticmethod
    def _dangerous(command: str) -> bool:
        padded = f" {command.lower()} "
        return any(token in padded for token in DANGEROUS_TOKENS)

    @staticmethod
    def normalize_key(text: str) -> str:
        return text.lower().strip().replace(" ", "-").replace("_", "-")

    @staticmethod
    def _dedupe(presets: list[CheckCommandPreset]) -> list[CheckCommandPreset]:
        seen: set[str] = set()
        clean: list[CheckCommandPreset] = []
        for preset in presets:
            if preset.command_key in seen:
                continue
            seen.add(preset.command_key)
            clean.append(preset)
        return clean
