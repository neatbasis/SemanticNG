from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_milestone_docs.py"

_spec = importlib.util.spec_from_file_location("validate_milestone_docs", SCRIPT_PATH)
assert _spec and _spec.loader
validate_milestone_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_milestone_docs)


def test_command_present_with_adjacent_url_passes() -> None:
    command = "pytest tests/test_schema_selector.py tests/test_capture_outcome_states.py"
    pr_body = "\n".join([command, "https://github.com/org/repo/actions/runs/42"])

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_command_present_without_evidence_fails() -> None:
    command = "pytest tests/test_schema_selector.py tests/test_capture_outcome_states.py"
    pr_body = command

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == [command]


def test_mismatched_command_string_fails() -> None:
    expected_command = "pytest tests/test_schema_selector.py tests/test_capture_outcome_states.py"
    pr_body = "\n".join(
        [
            "pytest tests/test_schema_selector.py",
            "https://github.com/org/repo/actions/runs/43",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [expected_command]) == [expected_command]




def test_command_and_evidence_inside_code_fence_passes() -> None:
    command = "pytest tests/test_schema_selector.py tests/test_capture_outcome_states.py"
    pr_body = "\n".join(
        [
            "```bash",
            command,
            "Evidence: https://github.com/org/repo/actions/runs/44",
            "```",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_command_with_comment_then_blank_line_before_evidence_fails() -> None:
    command = "pytest tests/test_schema_selector.py tests/test_capture_outcome_states.py"
    pr_body = "\n".join(
        [
            command,
            "<!-- kept for context -->",
            "",
            "Evidence: https://github.com/org/repo/actions/runs/45",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == [command]

def test_roadmap_status_transition_mismatch_detected() -> None:
    transitions = {"observer_authorization_contract": ("planned", "done")}
    roadmap_text = "\n".join(
        [
            "## Capability status alignment (manifest source-of-truth sync)",
            "- `done`: `prediction_persistence_baseline`.",
            "- `planned`: `observer_authorization_contract`.",
        ]
    )

    mismatches = validate_milestone_docs._roadmap_status_transition_mismatches(transitions, roadmap_text)

    assert len(mismatches) == 1
    assert "observer_authorization_contract" in mismatches[0]


def test_roadmap_status_transition_sync_passes_when_updated() -> None:
    transitions = {"observer_authorization_contract": ("planned", "done")}
    roadmap_text = "\n".join(
        [
            "## Capability status alignment (manifest source-of-truth sync)",
            "- `done`: `prediction_persistence_baseline`, `observer_authorization_contract`.",
            "- `planned`: `replay_projection_analytics`.",
        ]
    )

    assert validate_milestone_docs._roadmap_status_transition_mismatches(transitions, roadmap_text) == []
