from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_milestone_docs.py"


_spec = importlib.util.spec_from_file_location("validate_milestone_docs", SCRIPT_PATH)
assert _spec and _spec.loader
validate_milestone_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_milestone_docs)


def test_commands_missing_evidence_accepts_http_and_https_urls() -> None:
    command = "pytest tests/test_dod_manifest.py"
    pr_body = "\n".join(
        [
            f"- {command}",
            "  - CI run: http://ci.example/runs/100",
            "- second command",
            "  - CI run: https://ci.example/runs/101",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_accepts_artifact_and_attached_output_tokens() -> None:
    command = "pytest tests/test_replay_projection_determinism.py"
    pr_body = "\n".join(
        [
            f"- {command}",
            "  - Log artifact: artifact://milestone/projection-determinism",
            "  - Inline output: attached:projection-determinism.txt",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_reports_missing_when_no_supported_evidence_is_present() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            f"- {command}",
            "  - Evidence: see CI logs in the repo",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == [command]
