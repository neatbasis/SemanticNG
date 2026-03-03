from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = ROOT / "src" / "core"

FORBIDDEN_IMPORT_PREFIXES = (
    "state_renormalization.adapters",
    "state_renormalization.integration",
)
FORBIDDEN_IO_MODULES = {
    "asyncio",
    "http",
    "pathlib",
    "requests",
    "socket",
    "sqlite3",
    "subprocess",
    "urllib",
}


def _iter_core_python_files() -> list[Path]:
    return sorted(path for path in CORE_ROOT.glob("*.py") if path.is_file())


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_core_public_api_stays_minimal_even_if_internal_modules_expand() -> None:
    init_module = CORE_ROOT / "__init__.py"
    exported_symbols = importlib.import_module("core").__all__

    assert init_module.exists()
    assert exported_symbols == ["__version__"]


def test_core_modules_do_not_import_adapter_or_integration_layers() -> None:
    for path in _iter_core_python_files():
        imported_modules = _imported_modules(path)
        forbidden = sorted(
            module
            for module in imported_modules
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES)
            or module == "state_renormalization"
        )
        assert forbidden == [], f"{path} imports forbidden adapter/integration modules: {forbidden}"


def test_core_modules_avoid_direct_io_module_dependencies() -> None:
    for path in _iter_core_python_files():
        imported_modules = _imported_modules(path)
        forbidden = sorted(
            module
            for module in imported_modules
            if module.split(".", maxsplit=1)[0] in FORBIDDEN_IO_MODULES
        )
        assert forbidden == [], f"{path} imports forbidden I/O modules: {forbidden}"
