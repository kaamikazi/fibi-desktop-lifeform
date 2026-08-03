"""Architecture guards for Fibi's experimental provider subsystem."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIBI_ROOT = PROJECT_ROOT / "fibi"
CORE_PATH = FIBI_ROOT / "engines" / "core.py"
UI_ROOT = FIBI_ROOT / "ui"
PROVIDER_ROOT = FIBI_ROOT / "services" / "providers"
ADAPTER_ROOT = PROVIDER_ROOT / "adapters"

PROVIDER_SDK_ROOTS = frozenset({"google", "ollama", "requests", "httpx"})
PROVIDER_CONSTRUCTORS = frozenset(
    {
        "CompanionGenerationService",
        "ProviderDiagnostics",
        "ProviderRegistry",
        "ProviderSelectionService",
    }
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _uses_import_root(import_name: str, roots: frozenset[str]) -> bool:
    return any(import_name == root or import_name.startswith(root + ".") for root in roots)


def _constructor_calls(path: Path) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        if name in PROVIDER_CONSTRUCTORS:
            calls.add(name)
    return calls


def test_core_and_ui_do_not_import_provider_sdks() -> None:
    checked = (CORE_PATH, *UI_ROOT.rglob("*.py"))

    violations = {
        str(path.relative_to(PROJECT_ROOT)): sorted(
            name for name in _imports(path) if _uses_import_root(name, PROVIDER_SDK_ROOTS)
        )
        for path in checked
    }

    assert not {path: names for path, names in violations.items() if names}


def test_provider_adapters_do_not_depend_on_ui_or_memory_storage() -> None:
    forbidden_roots = frozenset(
        {
            "PyQt6",
            "sqlite3",
            "fibi.rag",
            "fibi.engines.memory_engine",
            "fibi.engines.memory_care_engine",
            "fibi.services.providers.selection",
        }
    )
    violations = {
        str(path.relative_to(PROJECT_ROOT)): sorted(
            name for name in _imports(path) if _uses_import_root(name, forbidden_roots)
        )
        for path in ADAPTER_ROOT.glob("*.py")
    }

    assert not {path: names for path, names in violations.items() if names}


def test_provider_service_construction_is_centralized_in_factory() -> None:
    callers = {
        path.relative_to(PROJECT_ROOT): _constructor_calls(path)
        for path in FIBI_ROOT.rglob("*.py")
        if path != PROVIDER_ROOT / "factory.py"
    }

    assert not {str(path): names for path, names in callers.items() if names}
    assert _constructor_calls(PROVIDER_ROOT / "factory.py") == PROVIDER_CONSTRUCTORS


def test_provider_adapters_cannot_modify_manual_selection() -> None:
    violations: dict[str, list[str]] = {}
    for path in ADAPTER_ROOT.glob("*.py"):
        calls = [
            node.func.attr
            for node in ast.walk(_tree(path))
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"select_provider", "set_mode"}
        ]
        if calls:
            violations[str(path.relative_to(PROJECT_ROOT))] = calls

    assert not violations
