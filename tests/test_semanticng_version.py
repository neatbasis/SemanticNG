from __future__ import annotations

import importlib.metadata
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "semanticng" / "__init__.py"


def test_semanticng_version_falls_back_when_version_module_is_absent(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("semanticng_init_under_test", MODULE_PATH)
    assert spec and spec.loader

    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "state_renormalization", types.ModuleType("state_renormalization"))

    def _raise_not_found(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", _raise_not_found)

    spec.loader.exec_module(module)

    assert module.__version__ == "0+unknown"
