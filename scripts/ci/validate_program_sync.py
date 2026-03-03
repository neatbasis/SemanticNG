from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dev"))
from status_schema import ValidationIssue  # noqa: E402

Issue = ValidationIssue
DOD_MANIFEST_PATH = Path("docs/dod_manifest.json")
ROADMAP_PATH = Path("ROADMAP.md")
SPRINT_PLAN_PATH = Path("docs/sprint_plan_5x.md")
STATUS_TRUTH_CONTRACT_PATH = Path("docs/status_truth_contract.md")
README_PATH = ROOT / "README.md"
DEVELOPMENT_PATH = ROOT / "docs" / "DEVELOPMENT.md"
MILESTONE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "state-renorm-milestone-gate.yml"


def _extract_manifest_governed_paths(manifest: dict[str, Any]) -> dict[str, list[str]]:
    governed = manifest.get("governed_paths")
    if not isinstance(governed, dict):
        return {"src": [], "ci_triggers": []}
    src = [item for item in governed.get("src", []) if isinstance(item, str)]
    ci_triggers = [item for item in governed.get("ci_triggers", []) if isinstance(item, str)]
    return {"src": src, "ci_triggers": ci_triggers}


def _extract_workflow_paths(workflow_text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    lines = workflow_text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped != "paths:":
            idx += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        idx += 1
        values: list[str] = []
        while idx < len(lines):
            candidate = lines[idx]
            cstrip = candidate.strip()
            cindent = len(candidate) - len(candidate.lstrip(" "))
            if not cstrip:
                idx += 1
                continue
            if cindent <= indent:
                break
            if cstrip.startswith("- "):
                value = cstrip[2:].strip().strip("'").strip('"')
                values.append(value)
                idx += 1
                continue
            break
        blocks.append(values)
    return blocks




def _validate_status_report_governed_paths(manifest: dict[str, Any]) -> list[Issue]:
    governed = _extract_manifest_governed_paths(manifest)
    result = subprocess.run(
        [sys.executable, "scripts/dev/status_report.py", "status-json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "STATUS_SHOW": "all"},
    )
    if result.returncode != 0:
        return [Issue("scripts/dev/status_report.py", f"status-json failed during sync check: {result.stderr.strip() or result.stdout.strip()}")]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [Issue("scripts/dev/status_report.py", f"status-json emitted invalid JSON: {exc.msg}")]

    status_governed = (
        payload.get("meta", {})
        .get("schema_contract", {})
        .get("governed_paths", {})
    )
    if status_governed != governed:
        return [Issue("scripts/dev/status_report.py", "status-report governed_paths differs from docs/dod_manifest.json governed_paths")]
    return []

def _validate_governed_paths_sync(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    governed = _extract_manifest_governed_paths(manifest)
    src_globs = governed["src"]
    ci_paths = governed["ci_triggers"]

    if not src_globs:
        issues.append(Issue(str(DOD_MANIFEST_PATH), "governed_paths.src must list governed src globs"))
    if not any(fnmatch.fnmatch("src/core/example.py", pattern) for pattern in src_globs):
        issues.append(Issue(str(DOD_MANIFEST_PATH), "governed_paths.src must include src/core/**"))

    expected_src_sentence = f"Governed source scope (canonical): {', '.join(src_globs)}"
    for doc_path in (README_PATH, DEVELOPMENT_PATH):
        if not doc_path.exists():
            issues.append(Issue(str(doc_path), "file is missing"))
            continue
        text = doc_path.read_text(encoding="utf-8")
        if expected_src_sentence not in text:
            issues.append(Issue(str(doc_path), f"missing governed scope sentence '{expected_src_sentence}'"))

    if not MILESTONE_WORKFLOW_PATH.exists():
        issues.append(Issue(str(MILESTONE_WORKFLOW_PATH), "file is missing"))
    else:
        workflow_text = MILESTONE_WORKFLOW_PATH.read_text(encoding="utf-8")
        for index, path_block in enumerate(_extract_workflow_paths(workflow_text), start=1):
            if path_block != ci_paths:
                issues.append(Issue(str(MILESTONE_WORKFLOW_PATH), f"paths block #{index} does not match docs/dod_manifest.json governed_paths.ci_triggers"))

    return issues

NON_CANONICAL_STATUS_INPUTS = (
    Path("docs/status/project.json"),
    Path("docs/status/milestones.json"),
    Path("docs/status/sprints.json"),
    Path("docs/status/objectives.json"),
    ROADMAP_PATH,
    SPRINT_PLAN_PATH,
)
STATUS_VIEW_FILES = (
    Path("docs/status/objectives.json"),
    Path("docs/status/milestones.json"),
    Path("docs/status/sprints.json"),
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


def _collect_manifest_ids(manifest: dict[str, Any], key: str) -> set[str]:
    return {
        item["id"]
        for item in manifest.get(key, [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _validate_single_authoritative_source(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    source = manifest.get("canonical_source_of_truth")
    if not isinstance(source, dict):
        return issues

    extras = source.get("authoritative_sources")
    if isinstance(extras, list) and len([item for item in extras if isinstance(item, str)]) > 1:
        issues.append(Issue(str(DOD_MANIFEST_PATH), "multiple authoritative sources configured in canonical_source_of_truth.authoritative_sources"))
    return issues


def _validate_scope_sync_across_manifest_docs_and_status(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    objective_ids = _collect_manifest_ids(manifest, "capability_groups")
    milestone_ids = _collect_manifest_ids(manifest, "milestone_groups")
    sprint_ids = _collect_manifest_ids(manifest, "sprint_groups")

    roadmap = ROADMAP_PATH.read_text(encoding="utf-8") if ROADMAP_PATH.exists() else ""
    sprint_plan = SPRINT_PLAN_PATH.read_text(encoding="utf-8") if SPRINT_PLAN_PATH.exists() else ""
    docs_text = f"{roadmap}\n{sprint_plan}"

    for objective_id in sorted(objective_ids):
        if objective_id not in docs_text:
            issues.append(Issue(str(ROADMAP_PATH), f"governed objective scope drift: '{objective_id}' missing from roadmap/sprint docs"))
    for milestone_id in sorted(milestone_ids):
        if milestone_id not in docs_text:
            issues.append(Issue(str(ROADMAP_PATH), f"governed milestone scope drift: '{milestone_id}' missing from roadmap/sprint docs"))
    for sprint_id in sorted(sprint_ids):
        if sprint_id not in docs_text:
            issues.append(Issue(str(SPRINT_PLAN_PATH), f"governed sprint scope drift: '{sprint_id}' missing from roadmap/sprint docs"))

    result = subprocess.run(
        [sys.executable, "scripts/dev/status_report.py", "status-json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "STATUS_SHOW": "all"},
    )
    if result.returncode != 0:
        issues.append(Issue("scripts/dev/status_report.py", f"status-json failed during scope sync check: {result.stderr.strip() or result.stdout.strip()}"))
        return issues
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        issues.append(Issue("scripts/dev/status_report.py", f"status-json emitted invalid JSON: {exc.msg}"))
        return issues

    rendered_objective_ids = {item.get("id") for item in payload.get("objectives", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    rendered_milestone_ids = {item.get("id") for item in payload.get("milestones", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    rendered_sprint_ids = {item.get("id") for item in payload.get("sprints", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}

    if rendered_objective_ids != objective_ids:
        issues.append(Issue("scripts/dev/status_report.py", "governed objective scope differs between manifest and status renderer"))
    if rendered_milestone_ids != milestone_ids:
        issues.append(Issue("scripts/dev/status_report.py", "governed milestone scope differs between manifest and status renderer"))
    if rendered_sprint_ids != sprint_ids:
        issues.append(Issue("scripts/dev/status_report.py", "governed sprint scope differs between manifest and status renderer"))
    return issues


def _validate_unknown_status_references(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    capability_ids = _collect_manifest_ids(manifest, "capabilities")
    gate_ids = _collect_manifest_ids(manifest, "quality_gates")
    milestone_ids = _collect_manifest_ids(manifest, "milestone_groups")
    sprint_ids = _collect_manifest_ids(manifest, "sprint_groups")

    result = subprocess.run(
        [sys.executable, "scripts/dev/status_report.py", "status-json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "STATUS_SHOW": "all"},
    )
    if result.returncode != 0:
        return [Issue("scripts/dev/status_report.py", f"status-json failed during reference check: {result.stderr.strip() or result.stdout.strip()}")]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [Issue("scripts/dev/status_report.py", f"status-json emitted invalid JSON: {exc.msg}")]

    for gate in payload.get("quality_gates", []):
        if not isinstance(gate, dict) or not isinstance(gate.get("id"), str):
            continue
        if gate["id"] not in gate_ids:
            issues.append(Issue("scripts/dev/status_report.py", f"status references unknown gate '{gate['id']}'"))

    for objective in payload.get("objectives", []):
        if not isinstance(objective, dict):
            continue
        objective_id = objective.get("id") if isinstance(objective.get("id"), str) else "<unknown>"
        for field in ("capability_ids", "depends_on", "satisfies"):
            values = objective.get(field)
            if not isinstance(values, list):
                continue
            for capability_id in values:
                if isinstance(capability_id, str) and capability_id not in capability_ids:
                    issues.append(Issue("scripts/dev/status_report.py", f"objective '{objective_id}' {field} references unknown capability '{capability_id}'"))
        milestone_id = objective.get("milestone_id")
        if isinstance(milestone_id, str) and milestone_id not in milestone_ids:
            issues.append(Issue("scripts/dev/status_report.py", f"objective '{objective_id}' references unknown milestone '{milestone_id}'"))
        sprint_id = objective.get("sprint_id")
        if isinstance(sprint_id, str) and sprint_id not in sprint_ids:
            issues.append(Issue("scripts/dev/status_report.py", f"objective '{objective_id}' references unknown sprint '{sprint_id}'"))
    return issues


def _validate_relational_integrity(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    objective_ids = _collect_manifest_ids(manifest, "capability_groups")
    milestone_ids = _collect_manifest_ids(manifest, "milestone_groups")
    sprint_ids = _collect_manifest_ids(manifest, "sprint_groups")
    capability_ids = _collect_manifest_ids(manifest, "capabilities")

    if len(objective_ids) != len([item for item in manifest.get("capability_groups", []) if isinstance(item, dict)]):
        issues.append(Issue(str(DOD_MANIFEST_PATH), "capability_groups contain records with missing IDs"))
    if len(milestone_ids) != len([item for item in manifest.get("milestone_groups", []) if isinstance(item, dict)]):
        issues.append(Issue(str(DOD_MANIFEST_PATH), "milestone_groups contain records with missing IDs"))
    if len(sprint_ids) != len([item for item in manifest.get("sprint_groups", []) if isinstance(item, dict)]):
        issues.append(Issue(str(DOD_MANIFEST_PATH), "sprint_groups contain records with missing IDs"))

    linked_milestones: set[str] = set()
    linked_sprints: set[str] = set()
    for group in manifest.get("capability_groups", []):
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            continue
        for capability_id in group.get("capability_ids", []):
            if isinstance(capability_id, str) and capability_id not in capability_ids:
                issues.append(Issue(str(DOD_MANIFEST_PATH), f"objective '{group['id']}' references unknown capability '{capability_id}'"))
        milestone_id = group.get("milestone_id")
        if isinstance(milestone_id, str):
            linked_milestones.add(milestone_id)
            if milestone_id not in milestone_ids:
                issues.append(Issue(str(DOD_MANIFEST_PATH), f"objective '{group['id']}' links to unknown milestone '{milestone_id}'"))
        sprint_id = group.get("sprint_id")
        if isinstance(sprint_id, str):
            linked_sprints.add(sprint_id)
            if sprint_id not in sprint_ids:
                issues.append(Issue(str(DOD_MANIFEST_PATH), f"objective '{group['id']}' links to unknown sprint '{sprint_id}'"))

    for milestone_id in sorted(milestone_ids - linked_milestones):
        issues.append(Issue(str(DOD_MANIFEST_PATH), f"orphan milestone record '{milestone_id}' has no linked objectives"))
    for sprint_id in sorted(sprint_ids - linked_sprints):
        issues.append(Issue(str(DOD_MANIFEST_PATH), f"orphan sprint record '{sprint_id}' has no linked objectives"))

    for status_view in STATUS_VIEW_FILES:
        if not status_view.exists():
            issues.append(Issue(str(status_view), "generated status view is missing"))
            continue
        try:
            doc = _load_json(status_view)
        except json.JSONDecodeError as exc:
            issues.append(Issue(str(status_view), f"invalid JSON: {exc.msg}"))
            continue
        items = doc.get("items") if isinstance(doc, dict) else None
        if not isinstance(items, list):
            issues.append(Issue(str(status_view), "expected object with an 'items' array"))
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                issues.append(Issue(str(status_view), f"items[{idx}] missing id"))

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
            issues.extend(_validate_single_authoritative_source(manifest))
            _compute_manifest_statuses(manifest)
            issues.extend(_validate_narrative_docs_reference_active_objectives(manifest))
            issues.extend(_validate_governed_paths_sync(manifest))
            issues.extend(_validate_status_report_governed_paths(manifest))
            issues.extend(_validate_scope_sync_across_manifest_docs_and_status(manifest))
            issues.extend(_validate_unknown_status_references(manifest))
            issues.extend(_validate_relational_integrity(manifest))

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
