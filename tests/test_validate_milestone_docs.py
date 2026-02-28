from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_milestone_docs.py"


_spec = importlib.util.spec_from_file_location("validate_milestone_docs", SCRIPT_PATH)
assert _spec and _spec.loader
validate_milestone_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_milestone_docs)


def test_commands_missing_evidence_accepts_https_evidence_line() -> None:
    command = "pytest tests/test_dod_manifest.py"
    pr_body = "\n".join(
        [
            command,
            "Evidence: https://ci.example/runs/100",
            "pytest tests/test_invariants.py",
            "Evidence: https://ci.example/runs/101",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_rejects_unsupported_evidence_format() -> None:
    command = "pytest tests/test_replay_projection_determinism.py"
    pr_body = "\n".join(
        [
            command,
            "Evidence: s3://bucket/path/to/log",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == [command]


def test_commands_missing_evidence_accepts_markdown_bullet_wrapped_command() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            f"- {command}",
            "Evidence: https://ci.example/runs/200",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_reports_missing_when_evidence_not_next_line() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            command,
            "Additional details:",
            "Evidence: https://ci.example/runs/300",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == [command]


def test_commands_missing_evidence_accepts_markdown_bullet_and_inline_code_command() -> None:
    command = "pytest tests/test_invariants.py"
    pr_body = "\n".join(
        [
            "- `pytest   tests/test_invariants.py`",
            "- Evidence: https://ci.example/runs/400",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_accepts_crlf_body() -> None:
    command = "pytest tests/test_schema_selector.py"
    pr_body = "\r\n".join(
        [
            command,
            "Evidence: https://ci.example/runs/401",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_commands_missing_evidence_accepts_single_adjacent_html_comment_before_evidence() -> None:
    command = "pytest tests/test_capture_outcome_states.py"
    pr_body = "\n".join(
        [
            command,
            "<!-- rerun details -->",
            "Evidence: https://ci.example/runs/402",
        ]
    )

    assert validate_milestone_docs._commands_missing_evidence(pr_body, [command]) == []


def test_done_capability_sync_mismatches_reports_roadmap_milestone_and_maturity_issues() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_done_bad",
                "status": "done",
                "roadmap_section": "Next",
                "contract_map_refs": ["Contract A", "Contract B"],
            }
        ]
    }
    contract_rows = {
        "Contract A": {"milestone": "Later", "maturity": "operational"},
        "Contract B": {"milestone": "Now", "maturity": "prototype"},
    }

    mismatches = validate_milestone_docs._done_capability_sync_mismatches(manifest, contract_rows)

    assert any("roadmap_section='Now'" in mismatch for mismatch in mismatches)
    assert any("Contract A" in mismatch and "Milestone: Now" in mismatch for mismatch in mismatches)
    assert any("Contract B" in mismatch and "operational/proven" in mismatch for mismatch in mismatches)


def test_milestone_policy_mismatches_reports_later_contract_dependency() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_now",
                "roadmap_section": "Now",
                "contract_map_refs": ["Contract Future"],
            }
        ]
    }
    contract_rows = {"Contract Future": {"milestone": "Later", "maturity": "prototype"}}

    mismatches = validate_milestone_docs._milestone_policy_mismatches(manifest, contract_rows)

    assert mismatches == [
        "cap_now (Now) -> Contract Future (Later): capabilities cannot depend on later-milestone contracts."
    ]


def test_maturity_promotion_evidence_mismatches_requires_entry_and_url() -> None:
    updates = [
        ("Contract A", "prototype", "operational"),
        ("Contract B", "operational", "proven"),
    ]
    changelog_lines = [
        "- 2026-02-28 (Next): Contract A prototype -> operational; promoted without link",
    ]

    mismatches = validate_milestone_docs._maturity_promotion_evidence_mismatches(updates, changelog_lines)

    assert "Contract A: changelog promotion entry must include an evidence URL (http:// or https://)." in mismatches
    assert "Contract B: missing changelog entry for maturity promotion operational -> proven." in mismatches


def test_maturity_transition_changelog_mismatches_requires_dated_https_entry() -> None:
    updates = [("Contract A", "in_progress", "operational")]
    changelog_lines = ["- Contract A in_progress -> operational; no date and no link"]

    mismatches = validate_milestone_docs._maturity_transition_changelog_mismatches(updates, changelog_lines)

    assert (
        "Contract A: changelog entry for maturity transition in_progress -> operational must start with '- YYYY-MM-DD (Milestone):'."
        in mismatches
    )
    assert (
        "Contract A: changelog entry for maturity transition in_progress -> operational must include at least one https:// evidence link."
        in mismatches
    )


def test_ci_evidence_links_command_mismatches_detects_order_drift() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "pytest_commands": [
                    "pytest tests/test_alpha.py",
                    "pytest tests/test_beta.py",
                ],
                "ci_evidence_links": [
                    {"command": "pytest tests/test_beta.py"},
                    {"command": "pytest tests/test_alpha.py"},
                ],
            }
        ]
    }

    mismatches = validate_milestone_docs._ci_evidence_links_command_mismatches(manifest, {"cap_a"})

    assert len(mismatches) == 1
    assert "cap_a: ci_evidence_links.command values must exactly match pytest_commands in the same order" in mismatches[0]


def test_commands_missing_evidence_by_capability_reports_capability_id() -> None:
    pr_body = "pytest tests/test_alpha.py\nEvidence: https://ci.example/run/1"
    commands_by_capability = {
        "cap_a": ["pytest tests/test_alpha.py"],
        "cap_b": ["pytest tests/test_beta.py"],
    }

    mismatches = validate_milestone_docs._commands_missing_evidence_by_capability(pr_body, commands_by_capability)

    assert len(mismatches) == 1
    assert mismatches[0].startswith("cap_b:")
    assert "pytest tests/test_beta.py" in mismatches[0]


def test_contract_map_transition_mismatches_requires_existing_contract_row() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "contract_map_refs": ["Missing Contract"],
            }
        ]
    }

    mismatches = validate_milestone_docs._contract_map_transition_mismatches(
        manifest,
        {"cap_done"},
        {},
    )

    assert len(mismatches) == 1
    assert "Missing Contract" in mismatches[0]


def test_contract_map_transition_mismatches_requires_done_contract_rows_now_and_operational() -> None:
    manifest = {
        "capabilities": [
            {
                "id": "cap_done",
                "status": "done",
                "contract_map_refs": ["Contract Future", "Contract Prototype"],
            }
        ]
    }
    rows = {
        "Contract Future": {"milestone": "Next", "maturity": "operational"},
        "Contract Prototype": {"milestone": "Now", "maturity": "prototype"},
    }

    mismatches = validate_milestone_docs._contract_map_transition_mismatches(
        manifest,
        {"cap_done"},
        rows,
    )

    assert any("Milestone: Now" in mismatch for mismatch in mismatches)
    assert any("operational/proven" in mismatch for mismatch in mismatches)
