from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "render_transition_evidence.py"

_spec = importlib.util.spec_from_file_location("render_transition_evidence", SCRIPT_PATH)
assert _spec and _spec.loader
render_transition_evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_transition_evidence)


def test_status_transitions_detects_changed_capability_statuses() -> None:
    base_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "in_progress"},
            {"id": "cap_b", "status": "done"},
        ]
    }
    head_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "done"},
            {"id": "cap_b", "status": "done"},
            {"id": "cap_c", "status": "in_progress"},
        ]
    }

    transitioned = render_transition_evidence._status_transitions(base_manifest, head_manifest)

    assert transitioned == {"cap_a"}


def test_transitioned_capability_commands_filters_to_transitioned_and_non_empty_strings() -> None:
    head_manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "pytest_commands": ["pytest tests/test_alpha.py", "", None, "pytest tests/test_beta.py"],
            },
            {"id": "cap_b", "pytest_commands": ["pytest tests/test_gamma.py"]},
        ]
    }

    commands = render_transition_evidence._transitioned_capability_commands(head_manifest, {"cap_a"})

    assert commands == {
        "cap_a": [
            "pytest tests/test_alpha.py",
            "pytest tests/test_beta.py",
        ]
    }


def test_render_block_includes_expected_markers_and_evidence_lines() -> None:
    block = render_transition_evidence._render_block(
        {
            "cap_a": ["pytest tests/test_alpha.py"],
            "cap_b": ["pytest tests/test_beta.py"],
        }
    )

    assert "<!-- transition-evidence:start -->" in block
    assert "<!-- transition-evidence:end -->" in block
    assert "#### cap_a" in block
    assert "pytest tests/test_alpha.py" in block
    assert "Evidence: https://example.com/replace-with-evidence/cap_a/1" in block


def test_render_block_reports_no_transitions_message_when_empty() -> None:
    block = render_transition_evidence._render_block({})

    assert "No capability status transitions were detected for this diff." in block
