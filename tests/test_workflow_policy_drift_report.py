from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "workflow_policy_drift_report.py"

_spec = importlib.util.spec_from_file_location("workflow_policy_drift_report", SCRIPT_PATH)
assert _spec and _spec.loader
workflow_policy_drift_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workflow_policy_drift_report)


def test_generate_report_passes_for_repo_policy() -> None:
    missing, coverage = workflow_policy_drift_report.generate_report(
        ROOT / "docs" / "workflow_command_policy.json"
    )

    assert missing == []
    assert coverage


def test_generate_report_flags_missing_required_command(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.yml"
    workflow_path.write_text("name: x\njobs:\n  a:\n    steps:\n      - run: echo hi\n", encoding="utf-8")

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "required_commands": [
                    {
                        "command": "pytest --cov --cov-report=term-missing --cov-report=xml",
                        "workflows": [str(workflow_path)],
                        "policy_sources": ["docs/release_checklist.md"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    missing, _ = workflow_policy_drift_report.generate_report(policy_path)

    assert len(missing) == 1
    assert "missing required command" in missing[0]
