from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_milestone_docs.py"

_spec = importlib.util.spec_from_file_location("validate_milestone_docs", SCRIPT_PATH)
assert _spec and _spec.loader
validate_milestone_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_milestone_docs)


def test_no_regression_budget_allows_refreshed_done_evidence_when_command_packs_pass() -> None:
    base_manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "ci_evidence_links": [
                    {
                        "command": "pytest tests/test_alpha.py",
                        "evidence": "https://ci.example/run/1",
                    }
                ],
            }
        ]
    }
    head_manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "ci_evidence_links": [
                    {
                        "command": "pytest tests/test_alpha.py",
                        "evidence": "https://ci.example/run/2",
                        "result": "pass",
                    }
                ],
            }
        ]
    }
    policy = {"done_capability_ids": ["cap_done"], "waivers": []}

    mismatches = validate_milestone_docs._done_capability_no_regression_budget_mismatches(
        base_manifest,
        head_manifest,
        policy,
    )

    assert mismatches == []


def test_no_regression_budget_allows_refreshed_failure_when_waived() -> None:
    base_manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "ci_evidence_links": [
                    {
                        "command": "pytest tests/test_alpha.py",
                        "evidence": "https://ci.example/run/1",
                    }
                ],
            }
        ]
    }
    head_manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "ci_evidence_links": [
                    {
                        "command": "pytest tests/test_alpha.py",
                        "evidence": "https://ci.example/run/2",
                        "result": "fail",
                    }
                ],
            }
        ]
    }
    policy = {
        "done_capability_ids": ["cap_done"],
        "waivers": [
            {
                "id": "waiver-1",
                "owner": "@owner",
                "reason": "temporary dependency outage",
                "rollback_by": "2027-01-01",
                "scope": {
                    "capability_id": "cap_done",
                    "command_packs": ["pytest tests/test_alpha.py"],
                },
            }
        ],
    }

    mismatches = validate_milestone_docs._done_capability_no_regression_budget_mismatches(
        base_manifest,
        head_manifest,
        policy,
    )

    assert mismatches == []


def test_policy_waiver_mismatches_rejects_expired_waiver() -> None:
    policy = {
        "waivers": [
            {
                "id": "waiver-expired",
                "owner": "@owner",
                "reason": "known flaky suite",
                "rollback_by": "2025-01-01",
                "scope": {"capability_id": "cap_done", "command_packs": "*"},
            }
        ]
    }

    mismatches = validate_milestone_docs._policy_waiver_mismatches(policy, today=date(2025, 1, 2))

    assert mismatches == [
        "waiver-expired: waiver expired on 2025-01-01; rollback-by dates must not be in the past."
    ]


def test_policy_waiver_mismatches_requires_owner_reason_rollback_by_and_scope() -> None:
    policy = {"waivers": [{"id": "waiver-missing-fields"}]}

    mismatches = validate_milestone_docs._policy_waiver_mismatches(policy, today=date(2025, 1, 1))

    assert "waivers[0] missing required field 'owner'." in mismatches
    assert "waivers[0] missing required field 'reason'." in mismatches
    assert "waivers[0] missing required field 'rollback_by'." in mismatches
    assert "waivers[0] missing required field 'scope'." in mismatches
