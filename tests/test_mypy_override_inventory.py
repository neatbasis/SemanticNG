from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "mypy_override_inventory.py"

_spec = importlib.util.spec_from_file_location("mypy_override_inventory", SCRIPT_PATH)
assert _spec and _spec.loader
mypy_override_inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mypy_override_inventory)


def test_inventory_includes_known_suppressions() -> None:
    rows = mypy_override_inventory._suppression_rows(
        mypy_override_inventory._load_overrides(ROOT / "pyproject.toml")
    )

    assert any(
        row["module"] == "semanticng.bdd_compat" and row["suppression"] == "warn_return_any = false"
        for row in rows
    )
    assert any(
        row["module"] == "tests" and row["suppression"] == "strict = false"
        for row in rows
    )


def test_json_output_is_valid() -> None:
    rows = mypy_override_inventory._suppression_rows(
        mypy_override_inventory._load_overrides(ROOT / "pyproject.toml")
    )
    payload = json.dumps(rows)

    decoded = json.loads(payload)
    assert isinstance(decoded, list)
    assert decoded

