from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_milestone_docs.py"


_spec = importlib.util.spec_from_file_location("validate_milestone_docs", SCRIPT_PATH)
assert _spec and _spec.loader
validate_milestone_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_milestone_docs)


def test_commands_with_invalid_evidence_format_accepts_exact_command_plus_https_line() -> None:
    command = "pytest tests/test_dod_manifest.py"
    pr_body = "\n".join(
        [
            command,
            "Evidence: https://ci.example/runs/100",
            "pytest tests/test_invariants.py",
            "Evidence: https://ci.example/runs/101",
        ]
    )

    assert validate_milestone_docs._commands_with_invalid_evidence_format(pr_body, [command]) == []


def test_commands_with_invalid_evidence_format_rejects_non_https_evidence_line() -> None:
    command = "pytest tests/test_replay_projection_determinism.py"
    pr_body = "\n".join(
        [
            command,
            "Evidence: artifact://milestone/projection-determinism",
        ]
    )

    assert validate_milestone_docs._commands_with_invalid_evidence_format(pr_body, [command]) == [command]


def test_commands_with_invalid_evidence_format_reports_missing_when_no_immediate_evidence_line() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            f"- {command}",
            "Evidence: https://ci.example/runs/200",
        ]
    )

    assert validate_milestone_docs._commands_with_invalid_evidence_format(pr_body, [command]) == [command]


def test_commands_with_invalid_evidence_format_reports_missing_when_evidence_not_next_line() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            command,
            "Additional details:",
            "Evidence: https://ci.example/runs/300",
        ]
    )

    assert validate_milestone_docs._commands_with_invalid_evidence_format(pr_body, [command]) == [command]
