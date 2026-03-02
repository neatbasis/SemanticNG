from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from status_schema import (
    STATUS_FILE_CONTRACTS,
    ValidationIssue,
    validate_item_collection_document,
    validate_project_document,
)

STATUS_DIR = Path("docs/status")
Issue = ValidationIssue


def _default_project_payload() -> dict[str, Any]:
    return {
        "id": "unknown",
        "name": "unknown",
        "status": "unknown",
        "active": True,
        "summary": "unknown",
        "reason": "project.json is missing or invalid",
        "as_of": "unknown",
        "waste_metrics": {
            "duplicate_logic_count": 0,
            "unused_code_delta": 0,
            "stale_doc_count": 0,
            "mypy_debt_delta": 0,
            "flaky_test_count": 0,
        },
        "analytics": [],
    }


def _base_payload(status_show: str, required_files: dict[str, Path]) -> dict[str, Any]:
    return {
        "meta": {
            "generator": "scripts/dev/status_report.py",
            "deterministic": True,
            "offline": True,
            "status_show": status_show,
            "unknown_policy": "Print unknown with reason when data is missing or unresolved.",
            "generated_from": {
                "manifest": "unknown",
                "manifest_commit": "unknown",
                "generated_at": "unknown",
            },
            "schema_contract": {
                "allowed_status": sorted(
                    STATUS_FILE_CONTRACTS["project"]["properties"]["status"]["enum"]
                ),
                "required_keys": list(STATUS_FILE_CONTRACTS["project"]["required"]),
                "files": {label: str(path) for label, path in required_files.items()},
            },
        },
        "project": _default_project_payload(),
        "milestones": [],
        "sprints": [],
        "objectives": [],
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_status_file(path: Path) -> tuple[Any | None, list[Issue]]:
    if not path.exists():
        return None, [Issue(str(path), "file is missing")]

    try:
        return _load_json(path), []
    except json.JSONDecodeError as exc:
        return None, [Issue(str(path), f"invalid JSON: {exc.msg}")]


def _validate_item(
    label: str,
    path: Path,
    data: Any,
) -> tuple[dict[str, Any] | list[dict[str, Any]] | None, list[Issue]]:
    if label == "project":
        issues = validate_project_document(path, data)
        if isinstance(data, dict):
            normalized = {
                **_default_project_payload(),
                **{k: v for k, v in data.items() if k != "analytics"},
                "analytics": data.get("analytics", []),
            }
            return normalized, issues
        return None, issues

    return validate_item_collection_document(path, data)


def _filter_items(items: list[dict[str, Any]], status_show: str) -> list[dict[str, Any]]:
    if status_show == "all":
        return items
    return [item for item in items if item.get("active")]


def _load_manifest_capability_ids() -> set[str]:
    manifest_path = Path("docs/dod_manifest.json")
    if not manifest_path.exists():
        return set()

    try:
        manifest = _load_json(manifest_path)
    except json.JSONDecodeError:
        return set()

    capabilities = manifest.get("capabilities", []) if isinstance(manifest, dict) else []
    return {
        item.get("id")
        for item in capabilities
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _validate_relationships(collections: dict[str, list[dict[str, Any]]]) -> list[Issue]:
    issues: list[Issue] = []

    objective_ids = {
        item.get("id") for item in collections["objectives"] if isinstance(item.get("id"), str)
    }
    sprint_ids = {item.get("id") for item in collections["sprints"] if isinstance(item.get("id"), str)}
    milestone_ids = {
        item.get("id") for item in collections["milestones"] if isinstance(item.get("id"), str)
    }
    capability_ids = _load_manifest_capability_ids()

    for group in ("milestones", "sprints", "objectives"):
        for idx, item in enumerate(collections[group]):
            context = f"docs/status/{group}.json::items[{idx}]"
            if not isinstance(item, dict):
                continue

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

            item_capability_ids = item.get("capability_ids", [])
            if isinstance(item_capability_ids, list):
                for capability_id in item_capability_ids:
                    if isinstance(capability_id, str) and capability_id not in capability_ids:
                        issues.append(
                            Issue(
                                context,
                                f"capability_ids references unknown capability id '{capability_id}'",
                            )
                        )

    objective_by_milestone: dict[str, list[dict[str, Any]]] = {}
    objective_by_sprint: dict[str, list[dict[str, Any]]] = {}
    for objective in collections["objectives"]:
        milestone_id = objective.get("milestone_id")
        if isinstance(milestone_id, str):
            objective_by_milestone.setdefault(milestone_id, []).append(objective)
        sprint_id = objective.get("sprint_id")
        if isinstance(sprint_id, str):
            objective_by_sprint.setdefault(sprint_id, []).append(objective)

    for idx, milestone in enumerate(collections["milestones"]):
        if milestone.get("status") != "done":
            continue
        linked = objective_by_milestone.get(milestone.get("id"), [])
        not_done = [objective.get("id", "unknown") for objective in linked if objective.get("status") != "done"]
        if not_done:
            issues.append(
                Issue(
                    f"docs/status/milestones.json::items[{idx}]",
                    "milestone status is 'done' but linked objectives are not done: " + ", ".join(not_done),
                )
            )

    for idx, sprint in enumerate(collections["sprints"]):
        if sprint.get("status") != "done":
            continue
        linked = objective_by_sprint.get(sprint.get("id"), [])
        not_done = [objective.get("id", "unknown") for objective in linked if objective.get("status") != "done"]
        if not_done:
            issues.append(
                Issue(
                    f"docs/status/sprints.json::items[{idx}]",
                    "sprint status is 'done' but linked objectives are not done: " + ", ".join(not_done),
                )
            )

    return issues


def build_status_payload(status_show: str) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    required_files = {
        label: STATUS_DIR / f"{label}.json" for label in STATUS_FILE_CONTRACTS
    }

    payload = _base_payload(status_show=status_show, required_files=required_files)
    collections: dict[str, list[dict[str, Any]]] = {
        "milestones": [],
        "sprints": [],
        "objectives": [],
    }

    for label, path in required_files.items():
        data, load_issues = _load_status_file(path)
        issues.extend(load_issues)
        if data is None:
            continue

        validated, validation_issues = _validate_item(label=label, path=path, data=data)
        issues.extend(validation_issues)

        if label == "project":
            if isinstance(validated, dict):
                payload["project"] = validated
                payload["meta"]["generated_from"] = {
                    "manifest": validated.get("generated_from", "unknown"),
                    "manifest_commit": validated.get("manifest_commit", "unknown"),
                    "generated_at": validated.get("generated_at", "unknown"),
                }
            continue

        if isinstance(validated, list):
            collections[label] = validated
            payload[label] = _filter_items(validated, status_show=status_show)

    issues.extend(_validate_relationships(collections))

    return payload, issues


def emit_human_summary(payload: dict[str, Any], validation_issues: list[Issue]) -> None:
    project = payload["project"]
    print("SemanticNG Delivery Status")
    print("=" * 26)
    print(f"Project: {project['name']} ({project['status']})")
    print(f"Summary: {project['summary']}")
    print(f"Reason: {project['reason']}")
    print("")

    for group in ("milestones", "sprints", "objectives"):
        print(f"{group.title()}:")
        rows = payload[group]
        if not rows:
            print("- unknown: no active data available (set STATUS_SHOW=all for full inventory)")
        for item in rows:
            print(f"- {item['name']} [{item['status']}]")
            print(f"  summary: {item['summary']}")
            print(f"  reason: {item['reason']}")
        print("")

    print("Analytics callable:")
    analytics = project.get("analytics", [])
    if not analytics:
        print("- unknown: no analytics declared in docs/status/project.json")
    else:
        for analytic in analytics:
            status = analytic.get("status", "unknown")
            reason = analytic.get("reason")
            detail = f"{analytic.get('name', 'unknown')} -> {analytic.get('entrypoint', 'unknown')} [{status}]"
            print(f"- {detail}")
            if reason:
                print(f"  reason: {reason}")

    metrics = project.get("waste_metrics", {})
    print("")
    print("Waste metrics:")
    print(
        "- dup={duplicate_logic_count} | unusedΔ={unused_code_delta} | stale_docs={stale_doc_count} "
        "| mypyΔ={mypy_debt_delta} | flaky={flaky_test_count}".format(
            duplicate_logic_count=metrics.get("duplicate_logic_count", "unknown"),
            unused_code_delta=metrics.get("unused_code_delta", "unknown"),
            stale_doc_count=metrics.get("stale_doc_count", "unknown"),
            mypy_debt_delta=metrics.get("mypy_debt_delta", "unknown"),
            flaky_test_count=metrics.get("flaky_test_count", "unknown"),
        )
    )

    if validation_issues:
        print("")
        print("Validation warnings:")
        for issue in validation_issues:
            print(f"- {issue.path}: {issue.message}")


def emit_json_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def emit_check_issues(validation_issues: list[Issue]) -> None:
    print(json.dumps({"issues": [issue.__dict__ for issue in validation_issues]}, indent=2, sort_keys=True))


def main() -> int:
    mode_aliases = {
        "summary": "summary",
        "json": "json",
        "check": "check",
        "status": "summary",
        "status-json": "json",
        "status-check": "check",
        "integrity": "integrity",
        "status-integrity": "integrity",
    }

    parser = argparse.ArgumentParser(description="Deterministic offline status reporting")
    parser.add_argument("mode", choices=sorted(mode_aliases))
    args = parser.parse_args()
    resolved_mode = mode_aliases[args.mode]

    status_show = os.environ.get("STATUS_SHOW", "active")
    payload, issues = build_status_payload(status_show=status_show)

    if resolved_mode == "summary":
        emit_human_summary(payload, issues)
        return 0

    if resolved_mode == "json":
        emit_json_payload(payload)
        return 0

    if resolved_mode == "integrity":
        integrity_issues = [
            issue
            for issue in issues
            if "references unknown" in issue.message or "linked objectives are not done" in issue.message
        ]
        emit_check_issues(integrity_issues)
        return 1 if integrity_issues else 0

    emit_check_issues(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
