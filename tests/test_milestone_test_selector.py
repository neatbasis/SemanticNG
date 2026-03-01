from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / ".github/scripts/select_milestone_test_commands.py"
)
SPEC = importlib.util.spec_from_file_location("select_milestone_test_commands", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


SURFACE_MANIFEST = {
    "baseline": {
        "guaranteed_pytest_commands": ["pytest --cov --cov-report=term-missing --cov-report=xml"]
    },
    "change_scope_filters": {
        "docs_only_prefixes": ["docs/", ".github/"],
        "docs_only_allowlist": ["README.md", "ROADMAP.md"],
        "impacting_docs_paths": ["docs/dod_manifest.json", "docs/sprint_handoffs/"],
    },
}


def test_docs_only_non_impacting_change_skips_delta_selection() -> None:
    selection = MODULE.select_milestone_commands(
        changed_files=["docs/architecture.md"],
        head_manifest={
            "capabilities": [
                {
                    "id": "cap",
                    "status": "in_progress",
                    "code_paths": ["src/state_renormalization/engine.py"],
                    "pytest_commands": ["pytest tests/test_engine_projection_mission_loop.py"],
                }
            ]
        },
        base_manifest={"capabilities": []},
        surface_manifest=SURFACE_MANIFEST,
    )

    assert selection["selected_commands"] == []
    assert selection["docs_only_change"] is True


def test_excludes_baseline_commands_from_milestone_runner() -> None:
    selection = MODULE.select_milestone_commands(
        changed_files=["src/state_renormalization/engine.py"],
        head_manifest={
            "capabilities": [
                {
                    "id": "cap",
                    "status": "in_progress",
                    "code_paths": ["src/state_renormalization/engine.py"],
                    "pytest_commands": ["pytest --cov --cov-report=term-missing --cov-report=xml"],
                }
            ]
        },
        base_manifest={"capabilities": []},
        surface_manifest=SURFACE_MANIFEST,
    )

    assert selection["selected_commands"] == []
    assert selection["skipped_already_covered"] == [
        "pytest --cov --cov-report=term-missing --cov-report=xml"
    ]


def test_transition_only_suites_are_selected() -> None:
    selection = MODULE.select_milestone_commands(
        changed_files=["docs/dod_manifest.json", "docs/sprint_handoffs/m4.md"],
        head_manifest={
            "capabilities": [
                {
                    "id": "cap",
                    "status": "done",
                    "pytest_commands": ["pytest tests/test_invariants.py"],
                }
            ]
        },
        base_manifest={
            "capabilities": [
                {
                    "id": "cap",
                    "status": "in_progress",
                    "pytest_commands": ["pytest tests/test_invariants.py"],
                }
            ]
        },
        surface_manifest=SURFACE_MANIFEST,
    )

    assert selection["selected_commands"] == ["pytest tests/test_invariants.py"]
    assert selection["selection_reasons"]["pytest tests/test_invariants.py"] == [
        "transition_only:cap"
    ]
