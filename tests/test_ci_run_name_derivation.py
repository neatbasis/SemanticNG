from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ci" / "derive_ci_run_name.py"

SPEC = importlib.util.spec_from_file_location("derive_ci_run_name", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_fixture_tree(base: Path) -> None:
    (base / "docs" / "process").mkdir(parents=True)
    (base / "docs" / "status").mkdir(parents=True)

    (base / "docs" / "dod_manifest.json").write_text('{"milestone":"m1","version":1}\n', encoding="utf-8")
    (base / "docs" / "system_contract_map.md").write_text("# Contract Map\n\n- A -> B\n", encoding="utf-8")
    (base / "docs" / "process" / "quality_stage_commands.json").write_text(
        '{"stages":{"qa-commit":{"commands":[{"command":"pytest -q","timeout_seconds":300}]}}}\n',
        encoding="utf-8",
    )

    (base / "docs" / "status" / "project.json").write_text('{"health":"green"}\n', encoding="utf-8")
    (base / "docs" / "status" / "objectives.json").write_text('{"items":["o1"]}\n', encoding="utf-8")


def test_same_inputs_produce_same_name(tmp_path: Path) -> None:
    _write_fixture_tree(tmp_path)
    run_name_one = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)
    run_name_two = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)

    assert run_name_one == run_name_two


def test_canonical_change_updates_name(tmp_path: Path) -> None:
    _write_fixture_tree(tmp_path)
    baseline = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)

    contract_map = tmp_path / "docs" / "system_contract_map.md"
    contract_map.write_text("# Contract Map\n\n- A -> C\n", encoding="utf-8")

    updated = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)

    assert baseline != updated


def test_non_canonical_changes_do_not_affect_name(tmp_path: Path) -> None:
    _write_fixture_tree(tmp_path)
    baseline = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)

    (tmp_path / "README.md").write_text("non-canonical change\n", encoding="utf-8")

    unchanged = MODULE.derive_ci_run_name(stage="qa-commit", branch="feature/demo", repo_root=tmp_path)

    assert baseline == unchanged
