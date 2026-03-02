#!/usr/bin/env python3
"""Validate delivery-program synchronization across status docs and planning artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sys

SCRIPT_DEV_DIR = Path(__file__).resolve().parents[1] / "dev"
if str(SCRIPT_DEV_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DEV_DIR))

from status_schema import validate_item_collection_document, validate_project_document

STATUS_DIR = Path("docs/status")
ROADMAP_PATH = Path("ROADMAP.md")
SPRINT_PLAN_PATH = Path("docs/sprint_plan_5x.md")
DOD_MANIFEST_PATH = Path("docs/dod_manifest.json")
STATUS_FILES = {
    "project": STATUS_DIR / "project.json",
    "milestones": STATUS_DIR / "milestones.json",
    "sprints": STATUS_DIR / "sprints.json",
    "objectives": STATUS_DIR / "objectives.json",
}


@dataclass(frozen=True)
class Issue:
    path: str
    message: str


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _rollup_group_status(member_statuses: list[str]) -> str:
    if not member_statuses:
        return "planned"
    if "in_progress" in member_statuses:
        return "in_progress"
    if "planned" in member_statuses:
        return "planned"
    return "done"


def _validate_status_schema() -> tuple[dict[str, Any], list[Issue]]:
    parsed: dict[str, Any] = {}
    issues: list[Issue] = []

    for label, path in STATUS_FILES.items():
        if not path.exists():
            issues.append(Issue(str(path), "file is missing"))
            continue

        try:
            data = _load_json(path)
        except json.JSONDecodeError as exc:
            issues.append(Issue(str(path), f"invalid JSON: {exc.msg}"))
            continue

        if label == "project":
            for issue in validate_project_document(path, data):
                issues.append(Issue(issue.path, issue.message))
            if isinstance(data, dict):
                parsed[label] = data
            continue

        items, doc_issues = validate_item_collection_document(path, data)
        for issue in doc_issues:
            issues.append(Issue(issue.path, issue.message))
        parsed[label] = items

    return parsed, issues


def _validate_relationships(collections: dict[str, list[dict[str, Any]]]) -> list[Issue]:
    issues: list[Issue] = []
    milestone_ids = {item.get("id") for item in collections["milestones"] if isinstance(item.get("id"), str)}
    sprint_ids = {item.get("id") for item in collections["sprints"] if isinstance(item.get("id"), str)}
    objective_ids = {item.get("id") for item in collections["objectives"] if isinstance(item.get("id"), str)}

    for idx, item in enumerate(collections["objectives"]):
        context = f"docs/status/objectives.json::items[{idx}]"
        depends_on = item.get("depends_on", [])
        if isinstance(depends_on, list):
            for ref in depends_on:
                if isinstance(ref, str) and ref not in objective_ids:
                    issues.append(Issue(context, f"depends_on references unknown objective id '{ref}'"))

        milestone_id = item.get("milestone_id")
        if isinstance(milestone_id, str) and milestone_id not in milestone_ids:
            issues.append(Issue(context, f"milestone_id references unknown milestone id '{milestone_id}'"))

        sprint_id = item.get("sprint_id")
        if isinstance(sprint_id, str) and sprint_id not in sprint_ids:
            issues.append(Issue(context, f"sprint_id references unknown sprint id '{sprint_id}'"))

    return issues


def _compute_dod_derived_status() -> tuple[dict[str, dict[str, str]], list[Issue]]:
    issues: list[Issue] = []
    derived = {"objectives": {}, "milestones": {}, "sprints": {}}

    if not DOD_MANIFEST_PATH.exists():
        return derived, [Issue(str(DOD_MANIFEST_PATH), "file is missing")]

    try:
        manifest = _load_json(DOD_MANIFEST_PATH)
    except json.JSONDecodeError as exc:
        return derived, [Issue(str(DOD_MANIFEST_PATH), f"invalid JSON: {exc.msg}")]

    if not isinstance(manifest, dict):
        return derived, [Issue(str(DOD_MANIFEST_PATH), "manifest root must be an object")]

    capability_statuses: dict[str, str] = {}
    for capability in manifest.get("capabilities", []):
        if isinstance(capability, dict) and isinstance(capability.get("id"), str) and isinstance(capability.get("status"), str):
            capability_statuses[capability["id"]] = capability["status"]

    objective_statuses: dict[str, str] = {}
    for group in manifest.get("capability_groups", []):
        if not isinstance(group, dict):
            continue
        group_id = group.get("id")
        members = group.get("capability_ids", [])
        if not isinstance(group_id, str) or not isinstance(members, list):
            continue
        member_statuses = [
            capability_statuses[member]
            for member in members
            if isinstance(member, str) and member in capability_statuses
        ]
        objective_statuses[group_id] = _rollup_group_status(member_statuses)

    milestone_statuses = {
        group["id"]: group["status"]
        for group in manifest.get("milestone_groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str) and isinstance(group.get("status"), str)
    }
    sprint_statuses = {
        group["id"]: group["status"]
        for group in manifest.get("sprint_groups", [])
        if isinstance(group, dict) and isinstance(group.get("id"), str) and isinstance(group.get("status"), str)
    }

    derived["objectives"] = objective_statuses
    derived["milestones"] = milestone_statuses
    derived["sprints"] = sprint_statuses
    return derived, issues


def _validate_dod_alignment(collections: dict[str, list[dict[str, Any]]], derived: dict[str, dict[str, str]]) -> list[Issue]:
    issues: list[Issue] = []
    for group in ("objectives", "milestones", "sprints"):
        observed = {
            item.get("id"): item.get("status")
            for item in collections[group]
            if isinstance(item.get("id"), str) and isinstance(item.get("status"), str)
        }
        for item_id, expected_status in derived[group].items():
            observed_status = observed.get(item_id)
            path = f"docs/status/{group}.json"
            if observed_status is None:
                issues.append(Issue(path, f"DoD alignment mismatch: expected id '{item_id}' with status '{expected_status}' but item is missing"))
            elif observed_status != expected_status:
                issues.append(Issue(path, f"DoD alignment mismatch: id '{item_id}' expected status '{expected_status}' but found '{observed_status}'"))

    return issues


def _validate_active_objective_references(objectives: list[dict[str, Any]]) -> list[Issue]:
    issues: list[Issue] = []

    roadmap = ROADMAP_PATH.read_text(encoding="utf-8") if ROADMAP_PATH.exists() else ""
    sprint_plan = SPRINT_PLAN_PATH.read_text(encoding="utf-8") if SPRINT_PLAN_PATH.exists() else ""

    if not ROADMAP_PATH.exists():
        issues.append(Issue(str(ROADMAP_PATH), "file is missing"))
    if not SPRINT_PLAN_PATH.exists():
        issues.append(Issue(str(SPRINT_PLAN_PATH), "file is missing"))

    active_objective_ids = [
        item["id"]
        for item in objectives
        if isinstance(item, dict) and item.get("active") is True and isinstance(item.get("id"), str)
    ]

    for objective_id in active_objective_ids:
        if objective_id not in roadmap:
            issues.append(Issue(str(ROADMAP_PATH), f"active objective '{objective_id}' is not referenced"))
        if objective_id not in sprint_plan:
            issues.append(Issue(str(SPRINT_PLAN_PATH), f"active objective '{objective_id}' is not referenced"))

    return issues


def main() -> int:
    parsed, issues = _validate_status_schema()

    collections = {
        "milestones": parsed.get("milestones", []),
        "sprints": parsed.get("sprints", []),
        "objectives": parsed.get("objectives", []),
    }

    issues.extend(_validate_relationships(collections))
    derived, dod_issues = _compute_dod_derived_status()
    issues.extend(dod_issues)
    issues.extend(_validate_dod_alignment(collections, derived))
    issues.extend(_validate_active_objective_references(collections["objectives"]))

    if issues:
        print("Program sync validation failed:")
        for issue in issues:
            print(f"- {issue.path}: {issue.message}")
        return 1

    print("Program sync validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
