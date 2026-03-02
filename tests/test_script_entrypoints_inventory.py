from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "inventory_script_entrypoints.py"

_spec = importlib.util.spec_from_file_location("inventory_script_entrypoints", SCRIPT_PATH)
assert _spec and _spec.loader
inventory_script_entrypoints = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory_script_entrypoints)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_inventory_is_sorted_and_deterministic(tmp_path: Path) -> None:
    _write(tmp_path / ".github" / "scripts" / "z_tool.py", "print('z')\n")
    _write(tmp_path / "scripts" / "ci" / "a_tool.sh", "echo hi\n")
    _write(
        tmp_path / ".github" / "workflows" / "ci.yml",
        """
name: CI
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python .github/scripts/z_tool.py
      - run: make qa-local
""".strip()
        + "\n",
    )
    _write(
        tmp_path / ".pre-commit-config.yaml",
        """
repos:
  - repo: local
    hooks:
      - id: local-lint
        entry: scripts/ci/a_tool.sh
""".strip()
        + "\n",
    )
    _write(
        tmp_path / "Makefile",
        """
qa-local:
	python .github/scripts/z_tool.py
""".strip()
        + "\n",
    )
    _write(
        tmp_path / "docs" / "process" / "quality_stage_commands.json",
        json.dumps(
            {
                "stages": {
                    "qa-ci": {
                        "commands": [
                            {"command": "python .github/scripts/z_tool.py"},
                            {"command": "make qa-local"},
                        ],
                        "precommit_hook": {
                            "id": "qa-hook",
                            "entry": "python .github/scripts/z_tool.py",
                        },
                    }
                }
            }
        ),
    )

    rows = inventory_script_entrypoints.build_inventory(tmp_path)

    paths = [row["entrypoint_path"] for row in rows]
    assert paths == sorted(paths)

    make_entry = next(row for row in rows if row["entrypoint_path"] == "Makefile:qa-local")
    assert make_entry["entrypoint_type"] == "make_target"
    assert make_entry["invoked_from"] == [
        "quality_stage:qa-ci:commands[1]",
        "workflow:.github/workflows/ci.yml:L7",
    ]


def test_inventory_captures_known_repo_entrypoints() -> None:
    rows = inventory_script_entrypoints.build_inventory(ROOT)

    by_path = {row["entrypoint_path"]: row for row in rows}
    run_stage_checks = by_path["scripts/ci/run_stage_checks.py"]
    assert run_stage_checks["entrypoint_type"] == "python_script"
    assert "make:qa-commit:L24" in run_stage_checks["invoked_from"]
    assert any(
        source.startswith("precommit:qa-commit-stage:")
        for source in run_stage_checks["invoked_from"]
    )
    assert "quality_stage:qa-commit:precommit_hook" in run_stage_checks["invoked_from"]

    precommit_hook = by_path["hook:precommit-governance-selector"]
    assert precommit_hook["entrypoint_type"] == "precommit_hook"
    assert any(
        source.startswith("precommit:precommit-governance-selector:")
        for source in precommit_hook["invoked_from"]
    )
