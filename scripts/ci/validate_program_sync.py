from __future__ import annotations

import json
import sys
import re
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dev"))
from status_schema import ValidationIssue

Issue = ValidationIssue
DOD_MANIFEST_PATH = Path("docs/dod_manifest.json")
ROADMAP_PATH = Path("ROADMAP.md")
SPRINT_PLAN_PATH = Path("docs/sprint_plan_5x.md")
STATUS_TRUTH_CONTRACT_PATH = Path("docs/status_truth_contract.md")

NON_CANONICAL_STATUS_INPUTS = (
    Path("docs/status/project.json"),
    Path("docs/status/milestones.json"),
    Path("docs/status/sprints.json"),
    Path("docs/status/objectives.json"),
    ROADMAP_PATH,
    SPRINT_PLAN_PATH,
)
PROHIBITED_SOURCE_PATTERN = re.compile(
    r"(?i)(docs/status/(project|milestones|sprints|objectives)\.json|ROADMAP\.md|docs/sprint_plan_5x\.md).{0,120}(authoritative|source[- ]of[- ]truth)"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rollup_group_status(member_statuses: list[str]) -> str:
    if not member_statuses:
        return "planned"
    if "in_progress" in member_statuses:
        return "in_progress"
    if "planned" in member_statuses:
        return "planned"
    return "done"


def _compute_manifest_statuses(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    capability_statuses = {
        item["id"]: item["status"]
        for item in manifest.get("capabilities", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("status"), str)
    }
    objectives: dict[str, str] = {}
    for group in manifest.get("capability_groups", []):
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            continue
        members = [m for m in group.get("capability_ids", []) if isinstance(m, str)]
        member_statuses = [capability_statuses[m] for m in members if m in capability_statuses]
        objectives[group["id"]] = _rollup_group_status(member_statuses)

    milestones = {
        group["id"]: group["status"]
        for group in manifest.get("milestone_groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str) and isinstance(group.get("status"), str)
    }
    sprints = {
        group["id"]: group["status"]
        for group in manifest.get("sprint_groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str) and isinstance(group.get("status"), str)
    }
    return {"objectives": objectives, "milestones": milestones, "sprints": sprints}


def _validate_truth_contract_doc() -> list[Issue]:
    if not STATUS_TRUTH_CONTRACT_PATH.exists():
        return [Issue(str(STATUS_TRUTH_CONTRACT_PATH), "file is missing")]
    text = STATUS_TRUTH_CONTRACT_PATH.read_text(encoding="utf-8")
    required_snippets = ["docs/dod_manifest.json", "Generated views", "Narrative-only"]
    issues: list[Issue] = []
    for snippet in required_snippets:
        if snippet not in text:
            issues.append(Issue(str(STATUS_TRUTH_CONTRACT_PATH), f"missing required contract section '{snippet}'"))
    return issues


def _validate_manifest_canonical_source(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    source = manifest.get("canonical_source_of_truth")
    if not isinstance(source, dict):
        return [Issue(str(DOD_MANIFEST_PATH), "canonical_source_of_truth must be an object")]
    if source.get("manifest_path") != DOD_MANIFEST_PATH.as_posix():
        issues.append(Issue(str(DOD_MANIFEST_PATH), "canonical_source_of_truth.manifest_path must equal docs/dod_manifest.json"))
    return issues


def _validate_noncanonical_inputs_not_authoritative() -> list[Issue]:
    issues: list[Issue] = []
    for path in NON_CANONICAL_STATUS_INPUTS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if PROHIBITED_SOURCE_PATTERN.search(text):
            issues.append(
                Issue(
                    str(path),
                    "non-canonical file marks milestones/sprints/objectives/capability state as authoritative",
                )
            )
    return issues


def _validate_narrative_docs_reference_active_objectives(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8") if ROADMAP_PATH.exists() else ""
    sprint = SPRINT_PLAN_PATH.read_text(encoding="utf-8") if SPRINT_PLAN_PATH.exists() else ""

    active_objectives = [
        group.get("id")
        for group in manifest.get("capability_groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str) and _rollup_group_status([
            item.get("status")
            for item in manifest.get("capabilities", [])
            if isinstance(item, dict) and item.get("id") in group.get("capability_ids", []) and isinstance(item.get("status"), str)
        ]) == "in_progress"
    ]
    for objective_id in active_objectives:
        if objective_id not in roadmap:
            issues.append(Issue(str(ROADMAP_PATH), f"active objective '{objective_id}' missing reference annotation"))
        if objective_id not in sprint:
            issues.append(Issue(str(SPRINT_PLAN_PATH), f"active objective '{objective_id}' missing reference annotation"))
    return issues


def main() -> int:
    issues: list[Issue] = []
    if not DOD_MANIFEST_PATH.exists():
        issues.append(Issue(str(DOD_MANIFEST_PATH), "file is missing"))
    else:
        try:
            manifest = _load_json(DOD_MANIFEST_PATH)
        except json.JSONDecodeError as exc:
            issues.append(Issue(str(DOD_MANIFEST_PATH), f"invalid JSON: {exc.msg}"))
            manifest = {}
        if not isinstance(manifest, dict):
            issues.append(Issue(str(DOD_MANIFEST_PATH), "manifest root must be an object"))
            manifest = {}

        if isinstance(manifest, dict) and manifest:
            issues.extend(_validate_manifest_canonical_source(manifest))
            _compute_manifest_statuses(manifest)
            issues.extend(_validate_narrative_docs_reference_active_objectives(manifest))

    issues.extend(_validate_truth_contract_doc())
    issues.extend(_validate_noncanonical_inputs_not_authoritative())

    if issues:
        print("Program sync validation failed:")
        for issue in issues:
            print(f"- {issue.path}: {issue.message}")
        return 1

    print("Program sync validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
