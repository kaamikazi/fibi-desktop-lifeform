"""Lightweight AST checks for memory ownership boundaries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BoundaryViolation:
    rule: str
    path: str
    line: int
    detail: str


def scan_memory_boundaries(project_root: Path) -> list[BoundaryViolation]:
    """Find direct dependencies that bypass memory ownership boundaries."""

    root = Path(project_root)
    violations: list[BoundaryViolation] = []
    provider_files = [*root.glob("fibi/services/providers/adapters/*.py"), *root.glob("fibi/providers/*.py")]
    for path in provider_files:
        violations.extend(
            _forbidden_imports(
                root,
                path,
                "provider_memory_access",
                ("fibi.memory", "fibi.rag.repository", "fibi.engines.memory_", "sqlite3"),
            )
        )
    for path in root.glob("fibi/ui/*.py"):
        violations.extend(
            _forbidden_imports(
                root,
                path,
                "ui_raw_memory_access",
                ("sqlite3", "fibi.rag.repository", "fibi.engines.memory_engine", "fibi.engines.memory_care_engine"),
            )
        )
    vector_path = root / "fibi" / "rag" / "vector_store.py"
    if vector_path.exists():
        violations.extend(
            _forbidden_imports(root, vector_path, "derived_index_authority", ("sqlite3", "fibi.rag.repository"))
        )
    runtime_files = [root / "fibi" / "app" / "composition.py", root / "fibi" / "engines" / "core.py"]
    for path in runtime_files:
        violations.extend(
            _forbidden_imports(
                root,
                path,
                "experimental_cognitive_runtime",
                ("sovereign_brain", "interpreter_brain", "autobiographical_cognition", "cognitive_architecture"),
            )
        )
    return violations


def _forbidden_imports(
    root: Path,
    path: Path,
    rule: str,
    forbidden_prefixes: tuple[str, ...],
) -> list[BoundaryViolation]:
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError) as error:
        return [BoundaryViolation("source_parse", _relative(root, path), 0, type(error).__name__)]
    violations: list[BoundaryViolation] = []
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
        for module in modules:
            if any(module == prefix or module.startswith(prefix) for prefix in forbidden_prefixes):
                violations.append(BoundaryViolation(rule, _relative(root, path), node.lineno, module))
    return violations


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
