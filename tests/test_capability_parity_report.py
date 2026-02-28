from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "capability_parity_report.py"
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"

_spec = importlib.util.spec_from_file_location("capability_parity_report", SCRIPT_PATH)
assert _spec and _spec.loader
capability_parity_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capability_parity_report)


class CapabilityRecord(TypedDict, total=False):
    id: str
    status: str


class ManifestDocument(TypedDict, total=False):
    capabilities: list[CapabilityRecord]
    canonical_source_of_truth: dict[str, str]


def _load_manifest() -> ManifestDocument:
    return cast(ManifestDocument, json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))


def test_manifest_declares_canonical_status_and_pytest_command_fields() -> None:
    manifest = _load_manifest()

    canonical = manifest.get("canonical_source_of_truth")
    assert canonical == {
        "capability_status_field": "status",
        "required_pytest_commands_field": "pytest_commands",
    }


def test_roadmap_alignment_mismatches_detect_missing_and_extra_capabilities() -> None:
    capabilities = [
        {"id": "cap_done", "status": "done"},
        {"id": "cap_in_progress", "status": "in_progress"},
    ]
    roadmap_text = "\n".join(
        [
            "## Capability status alignment (manifest source-of-truth sync)",
            "- `done`: `cap_done`, `cap_extra`.",
            "- `in_progress`: .",
        ]
    )

    mismatches = capability_parity_report.roadmap_alignment_mismatches(capabilities, roadmap_text)

    assert any("cap_extra" in mismatch for mismatch in mismatches)
    assert any("cap_in_progress" in mismatch for mismatch in mismatches)


def test_contract_maturity_evidence_mismatches_require_https_and_known_contract() -> None:
    contract_map_text = "\n".join(
        [
            "## Milestone: Now",
            "| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |",
            "|---|---|---|---|---|---|---|",
            "| Known Contract | a | b | c | d | e | operational |",
            "",
            "### Changelog",
            "- 2026-02-28 (Now): Unknown Contract prototype -> operational; no evidence",
            "- 2026-02-28 (Now): Known Contract operational -> prototype; downgrade. https://example.test/evidence",
        ]
    )

    mismatches = capability_parity_report.contract_maturity_evidence_mismatches(contract_map_text)

    assert any("missing https evidence URL" in mismatch for mismatch in mismatches)
    assert any("unknown contract" in mismatch.lower() for mismatch in mismatches)
    assert any("forward maturity move" in mismatch for mismatch in mismatches)


def test_contract_maturity_evidence_mismatches_accepts_capability_id_prefix() -> None:
    contract_map_text = "\n".join(
        [
            "## Milestone: Now",
            "| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |",
            "|---|---|---|---|---|---|---|",
            "| Known Contract | a | b | c | d | e | operational |",
            "",
            "### Changelog",
            "- 2026-02-28 (Now): capability_id=known_capability; Known Contract prototype -> operational; promotion evidence. https://example.test/evidence",
        ]
    )

    mismatches = capability_parity_report.contract_maturity_evidence_mismatches(contract_map_text)

    assert mismatches == []


def test_project_maturity_mismatches_detects_status_and_ratio_drift() -> None:
    capabilities = [
        {"id": "cap_done", "status": "done"},
        {"id": "cap_planned", "status": "planned"},
    ]
    maturity_text = "\n".join(
        [
            "- **Done:** 2",
            "- **In progress:** 1",
            "- **Planned:** 0",
            "Completion ratio (done / total): **66.7%** (`2/3`).",
            "Current bottleneck capability: **`cap_planned`** (`in_progress`).",
            "It is the only capability currently marked `in_progress` in the DoD manifest.",
        ]
    )

    mismatches = capability_parity_report.project_maturity_mismatches(capabilities, maturity_text)

    assert any("bullet for done" in mismatch for mismatch in mismatches)
    assert any("completion ratio reports" in mismatch for mismatch in mismatches)
    assert any("cap_planned" in mismatch for mismatch in mismatches)
    assert any("only one in_progress capability" in mismatch for mismatch in mismatches)


def test_deterministic_parity_mismatches_is_empty_for_repo_state() -> None:
    assert capability_parity_report.deterministic_parity_mismatches() == []
