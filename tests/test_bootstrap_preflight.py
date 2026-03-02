from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "dev" / "bootstrap_preflight.py"

spec = importlib.util.spec_from_file_location("bootstrap_preflight", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_parse_lower_bound_with_minor_only() -> None:
    assert module._parse_lower_bound(">=3.10") == (3, 10, 0)


def test_parse_lower_bound_with_patch() -> None:
    assert module._parse_lower_bound(">=3.10.4,<4") == (3, 10, 4)


def test_check_precommit_executable_reports_fix_when_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(module.shutil, "which", lambda _: None)

    failure = module._check_precommit_executable()

    assert failure == "pre-commit executable not found. Fix: python -m pip install pre-commit"


def test_check_editable_import_reports_fix_when_missing(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(module.importlib.util, "find_spec", lambda _: None)

    failure = module._check_editable_import()

    assert failure == 'semanticng import not found. Fix: python -m pip install -e ".[test]"'
