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


def build_status_payload(status_show: str) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    required_files = {
        label: STATUS_DIR / f"{label}.json" for label in STATUS_FILE_CONTRACTS
    }

    payload = _base_payload(status_show=status_show, required_files=required_files)

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
            payload[label] = _filter_items(validated, status_show=status_show)

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

    emit_check_issues(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
