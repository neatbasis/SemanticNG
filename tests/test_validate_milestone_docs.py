from __future__ import annotations

import importlib.util
import re
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
    assert any(
        "Contract B" in mismatch and "operational/proven" in mismatch for mismatch in mismatches
    )


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

    mismatches = validate_milestone_docs._maturity_promotion_evidence_mismatches(
        updates, changelog_lines
    )

    assert (
        "Contract A: changelog promotion entry must include an evidence URL (http:// or https://)."
        in mismatches
    )
    assert (
        "Contract B: missing changelog entry for maturity promotion operational -> proven."
        in mismatches
    )


def test_maturity_transition_changelog_mismatches_requires_dated_https_entry() -> None:
    updates = [("Contract A", "in_progress", "operational")]
    changelog_lines = ["- Contract A in_progress -> operational; no date and no link"]

    mismatches = validate_milestone_docs._maturity_transition_changelog_mismatches(
        updates, changelog_lines
    )

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
    assert (
        "cap_a: ci_evidence_links.command values must exactly match pytest_commands in the same order"
        in mismatches[0]
    )


def test_commands_missing_evidence_by_capability_reports_capability_id() -> None:
    pr_body = "pytest tests/test_alpha.py\nEvidence: https://ci.example/run/1"
    commands_by_capability = {
        "cap_a": ["pytest tests/test_alpha.py"],
        "cap_b": ["pytest tests/test_beta.py"],
    }

    mismatches = validate_milestone_docs._commands_missing_evidence_by_capability(
        pr_body, commands_by_capability
    )

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


def test_contract_map_transition_mismatches_requires_done_contract_rows_now_and_operational() -> (
    None
):
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


def test_validate_pr_template_fields_passes_with_all_required_sections() -> None:
    pr_body = "\n".join(
        [
            "## Dependency impact statement (mandatory)",
            "- Upstream capabilities/contracts consumed: contract_a",
            "- Downstream capabilities/contracts affected or unlocked: capability_b",
            "- Cross-capability risk if this change regresses: low",
            "",
            "## No-regression budget and rollback plan (mandatory)",
            "- Done-capability command packs impacted (if none, write `none`): none",
            "- Regression budget impact (`none` / `waiver_requested`): none",
            "- If waiver requested, include owner + rollback-by date + mitigation command packs: not_applicable (no waiver requested)",
            "",
            "## Documentation freshness and sprint handoff artifacts (mandatory for governance/maturity PRs)",
            "- Governed docs updated with fresh regeneration metadata (`yes`/`no`/`not_applicable`): yes",
            "- Sprint handoff artifact updates included (`yes`/`no`/`not_applicable`): not_applicable",
            "- If `no`, provide timeboxed follow-up issue/PR and owner: not_applicable",
        ]
    )

    assert (
        validate_milestone_docs._validate_pr_template_fields(
            pr_body, require_governance_fields=True
        )
        == []
    )


def test_validate_pr_template_fields_fails_missing_dependency_field() -> None:
    pr_body = "\n".join(
        [
            "## Dependency impact statement (mandatory)",
            "- Upstream capabilities/contracts consumed: contract_a",
            "- Downstream capabilities/contracts affected or unlocked:",
            "- Cross-capability risk if this change regresses: low",
            "",
            "## No-regression budget and rollback plan (mandatory)",
            "- Done-capability command packs impacted (if none, write `none`): none",
            "- Regression budget impact (`none` / `waiver_requested`): none",
            "- If waiver requested, include owner + rollback-by date + mitigation command packs: not_applicable",
        ]
    )

    mismatches = validate_milestone_docs._validate_pr_template_fields(
        pr_body, require_governance_fields=False
    )

    assert any(
        validate_milestone_docs.MISSING_PR_FIELD_MARKER in mismatch for mismatch in mismatches
    )
    assert any(
        "Downstream capabilities/contracts affected or unlocked:" in mismatch
        for mismatch in mismatches
    )


def test_validate_pr_template_fields_fails_missing_budget_declaration() -> None:
    pr_body = "\n".join(
        [
            "## Dependency impact statement (mandatory)",
            "- Upstream capabilities/contracts consumed: contract_a",
            "- Downstream capabilities/contracts affected or unlocked: capability_b",
            "- Cross-capability risk if this change regresses: low",
            "",
            "## No-regression budget and rollback plan (mandatory)",
            "- Done-capability command packs impacted (if none, write `none`): none",
            "- If waiver requested, include owner + rollback-by date + mitigation command packs: not_applicable",
        ]
    )

    mismatches = validate_milestone_docs._validate_pr_template_fields(
        pr_body, require_governance_fields=False
    )

    assert any(
        validate_milestone_docs.MISSING_PR_FIELD_MARKER in mismatch for mismatch in mismatches
    )
    assert any("Regression budget impact" in mismatch for mismatch in mismatches)


def test_validate_pr_template_fields_fails_without_rollback_plan_or_not_applicable() -> None:
    pr_body = "\n".join(
        [
            "## Dependency impact statement (mandatory)",
            "- Upstream capabilities/contracts consumed: contract_a",
            "- Downstream capabilities/contracts affected or unlocked: capability_b",
            "- Cross-capability risk if this change regresses: low",
            "",
            "## No-regression budget and rollback plan (mandatory)",
            "- Done-capability command packs impacted (if none, write `none`): none",
            "- Regression budget impact (`none` / `waiver_requested`): none",
            "- If waiver requested, include owner + rollback-by date + mitigation command packs:",
        ]
    )

    mismatches = validate_milestone_docs._validate_pr_template_fields(
        pr_body, require_governance_fields=False
    )

    assert any(
        validate_milestone_docs.MISSING_ROLLBACK_PLAN_MARKER in mismatch for mismatch in mismatches
    )


def test_validate_pr_template_fields_fails_missing_governance_handoff_fields() -> None:
    pr_body = "\n".join(
        [
            "## Dependency impact statement (mandatory)",
            "- Upstream capabilities/contracts consumed: contract_a",
            "- Downstream capabilities/contracts affected or unlocked: capability_b",
            "- Cross-capability risk if this change regresses: low",
            "",
            "## No-regression budget and rollback plan (mandatory)",
            "- Done-capability command packs impacted (if none, write `none`): none",
            "- Regression budget impact (`none` / `waiver_requested`): none",
            "- If waiver requested, include owner + rollback-by date + mitigation command packs: not_applicable",
            "",
            "## Documentation freshness and sprint handoff artifacts (mandatory for governance/maturity PRs)",
            "- Governed docs updated with fresh regeneration metadata (`yes`/`no`/`not_applicable`):",
            "- Sprint handoff artifact updates included (`yes`/`no`/`not_applicable`): no",
            "- If `no`, provide timeboxed follow-up issue/PR and owner:",
        ]
    )

    mismatches = validate_milestone_docs._validate_pr_template_fields(
        pr_body, require_governance_fields=True
    )

    assert any(
        validate_milestone_docs.MISSING_GOVERNANCE_HANDOFF_MARKER in mismatch
        for mismatch in mismatches
    )
    assert any(
        "Governed docs updated with fresh regeneration metadata" in mismatch
        for mismatch in mismatches
    )
    assert any(
        "If `no`, provide timeboxed follow-up issue/PR and owner:" in mismatch
        for mismatch in mismatches
    )


def test_live_contract_map_changelog_transitions_include_capability_id_and_evidence_link() -> None:
    manifest = validate_milestone_docs._load_manifest("HEAD")
    capability_ids = {
        cap.get("id") for cap in manifest.get("capabilities", []) if isinstance(cap.get("id"), str)
    }
    contract_map_text = (ROOT / "docs" / "system_contract_map.md").read_text(encoding="utf-8")

    mismatches: list[str] = []
    for line in validate_milestone_docs._extract_changelog_lines(contract_map_text):
        if "->" not in line:
            continue
        capability_match = re.search(r"capability_id=([a-z0-9_]+)", line)
        if capability_match is None:
            mismatches.append(f"missing capability_id in changelog line: {line}")
            continue
        if capability_match.group(1) not in capability_ids:
            mismatches.append(f"unknown capability_id in changelog line: {line}")
        if "https://" not in line and "http://" not in line:
            mismatches.append(f"missing evidence link in changelog line: {line}")

    assert not mismatches, "\n".join(mismatches)


def test_live_dependency_statements_match_between_roadmap_and_sprint_plan() -> None:
    pattern = re.compile(r"^- `([a-z0-9_]+)` depends on: (.+)\.$")

    def extract_map(text: str) -> dict[str, tuple[str, ...]]:
        parsed: dict[str, tuple[str, ...]] = {}
        for raw in text.splitlines():
            line = raw.strip()
            match = pattern.match(line)
            if not match:
                continue
            parsed[match.group(1)] = tuple(sorted(re.findall(r"`([a-z0-9_]+)`", match.group(2))))
        return parsed

    roadmap_text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    sprint_text = (ROOT / "docs" / "sprint_plan_5x.md").read_text(encoding="utf-8")

    roadmap_map = extract_map(roadmap_text)
    sprint_map = extract_map(sprint_text)

    shared = sorted(set(roadmap_map) & set(sprint_map))
    assert shared, "expected at least one shared canonical dependency statement across docs"

    mismatches = [cap_id for cap_id in shared if roadmap_map[cap_id] != sprint_map[cap_id]]

    assert not mismatches, (
        f"conflicting dependency statements across docs for capability IDs: {mismatches}"
    )


def test_documentation_change_control_mismatches_passes_with_current_docs() -> None:
    assert validate_milestone_docs._documentation_change_control_mismatches() == []


def test_documentation_change_control_mismatches_reports_missing_references(
    tmp_path, monkeypatch
) -> None:
    repo_root = tmp_path
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True)

    (docs_dir / "documentation_change_control.md").write_text(
        "\n".join(
            [
                "## DMAIC change-control matrix",
                "| DMAIC phase (change type) | Required files to update | Required commands / validators | Required evidence locations (PR body + handoff docs) | Merge-blocking criteria |",
                "| --- | --- | --- | --- | --- |",
                "| **Define** | a | b | c | d |",
                "| **Measure** | a | b | c | d |",
                "| **Analyze** | a | b | c | d |",
                "| **Improve** | a | b | c | d |",
                "| **Control** | a | b | c | d |",
            ]
        ),
        encoding="utf-8",
    )
    (repo_root / "README.md").write_text("# Placeholder\n", encoding="utf-8")
    (docs_dir / "release_checklist.md").write_text("# Release Checklist\n", encoding="utf-8")

    monkeypatch.chdir(repo_root)

    mismatches = validate_milestone_docs._documentation_change_control_mismatches()

    assert (
        "README.md must reference docs/documentation_change_control.md for canonical DMAIC change-control policy."
        in mismatches
    )
    assert (
        "docs/release_checklist.md must reference docs/documentation_change_control.md for release governance routing."
        in mismatches
    )
