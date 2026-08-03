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
    context_preview = root / "fibi" / "memory" / "context_preview.py"
    violations.extend(
        _forbidden_imports(
            root,
            context_preview,
            "context_preview_provider_access",
            ("fibi.providers", "fibi.services.providers", "fibi.rag", "sqlite3"),
        )
    )
    read_adapters = root / "fibi" / "memory" / "read_adapters.py"
    violations.extend(
        _forbidden_method_calls(
            root,
            read_adapters,
            "memory_read_adapter_mutation",
            (
                "add_memory",
                "update_memory",
                "delete_memory",
                "remember_fact",
                "save",
                "ingest_file",
                "mark_accessed",
                "soft_delete",
                "rebuild",
                "rebuild_index",
                "expire_memories",
            ),
        )
    )
    violations.extend(_query_service_construction_violations(root))
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


def _forbidden_method_calls(
    root: Path,
    path: Path,
    rule: str,
    method_names: tuple[str, ...],
) -> list[BoundaryViolation]:
    """Find mutation-shaped calls in a module whose role is read-only."""

    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError) as error:
        return [BoundaryViolation("source_parse", _relative(root, path), 0, type(error).__name__)]
    forbidden = set(method_names)
    return [
        BoundaryViolation(rule, _relative(root, path), node.lineno, node.func.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in forbidden
    ]


def _query_service_construction_violations(root: Path) -> list[BoundaryViolation]:
    """Keep production Stage 1 object ownership in the composition root."""

    allowed = (root / "fibi" / "app" / "composition.py").resolve()
    constructed_types = {
        "CompositeMemoryQueryService",
        "LegacyMemoryReadAdapter",
        "RAGMemoryReadAdapter",
        "MemoryShadowComparison",
        "ContextBrokerPreview",
    }
    violations: list[BoundaryViolation] = []
    for path in (root / "fibi").rglob("*.py"):
        if path.resolve() == allowed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError) as error:
            violations.append(BoundaryViolation("source_parse", _relative(root, path), 0, type(error).__name__))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in constructed_types:
                violations.append(
                    BoundaryViolation(
                        "memory_query_owner",
                        _relative(root, path),
                        node.lineno,
                        node.func.id,
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
