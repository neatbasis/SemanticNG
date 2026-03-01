from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / ".github/scripts/run_precommit_governance_checks.py"
)
SPEC = importlib.util.spec_from_file_location("run_precommit_governance_checks", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_selects_in_progress_commands_for_changed_code_paths() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "status": "in_progress",
                "code_paths": ["src/state_renormalization/engine.py"],
                "pytest_commands": ["pytest tests/test_engine_projection_mission_loop.py"],
            },
            {
                "id": "cap_b",
                "status": "done",
                "code_paths": ["src/state_renormalization/invariants.py"],
                "pytest_commands": ["pytest tests/test_invariants.py"],
            },
        ]
    }

    selected = MODULE.select_governance_commands(
        ["src/state_renormalization/engine.py"],
        head_manifest=manifest,
        base_manifest=None,
    )

    assert selected == ["pytest tests/test_engine_projection_mission_loop.py"]


def test_dedupes_commands_when_multiple_capabilities_map_to_same_pytest() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "status": "in_progress",
                "code_paths": ["docs"],
                "pytest_commands": ["pytest tests/test_invariants.py"],
            },
            {
                "id": "cap_b",
                "status": "in_progress",
                "code_paths": ["docs"],
                "pytest_commands": ["pytest tests/test_invariants.py"],
            },
        ]
    }

    selected = MODULE.select_governance_commands(["docs/architecture-map.md"], manifest)

    assert selected == ["pytest tests/test_invariants.py"]


def test_transition_to_done_requires_non_manifest_docs_update() -> None:
    base_manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "status": "in_progress",
                "pytest_commands": ["pytest tests/test_alpha.py"],
            }
        ]
    }
    head_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "done", "pytest_commands": ["pytest tests/test_alpha.py"]}
        ]
    }

    try:
        MODULE.select_governance_commands(
            ["docs/dod_manifest.json"],
            head_manifest=head_manifest,
            base_manifest=base_manifest,
        )
    except ValueError as err:
        assert "in_progress -> done" in str(err)
    else:
        raise AssertionError("Expected transition validation to fail without docs update")


def test_transition_to_done_includes_done_commands_when_docs_present() -> None:
    base_manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "status": "in_progress",
                "pytest_commands": ["pytest tests/test_alpha.py"],
            }
        ]
    }
    head_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "done", "pytest_commands": ["pytest tests/test_alpha.py"]}
        ]
    }

    selected = MODULE.select_governance_commands(
        ["docs/dod_manifest.json", "docs/system_contract_map.md"],
        head_manifest=head_manifest,
        base_manifest=base_manifest,
    )

    assert selected == ["pytest tests/test_alpha.py"]
