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


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_status_payload(status_show: str) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    required_files = {
        label: STATUS_DIR / f"{label}.json" for label in STATUS_FILE_CONTRACTS
    }

    payload: dict[str, Any] = {
        "meta": {
            "generator": "scripts/dev/status_report.py",
            "deterministic": True,
            "offline": True,
            "status_show": status_show,
            "unknown_policy": "Print unknown with reason when data is missing or unresolved.",
            "schema_contract": {
                "allowed_status": sorted(
                    STATUS_FILE_CONTRACTS["project"]["properties"]["status"]["enum"]
                ),
                "required_keys": list(STATUS_FILE_CONTRACTS["project"]["required"]),
                "files": {
                    label: str(path)
                    for label, path in required_files.items()
                },
            },
        },
        "project": {
            "id": "unknown",
            "name": "unknown",
            "status": "unknown",
            "active": True,
            "summary": "unknown",
            "reason": "project.json is missing or invalid",
            "as_of": "unknown",
            "analytics": [],
        },
        "milestones": [],
        "sprints": [],
        "objectives": [],
    }

    for label, path in required_files.items():
        if not path.exists():
            issues.append(Issue(str(path), "file is missing"))
            continue

        try:
            data = _load_json(path)
        except json.JSONDecodeError as exc:
            issues.append(Issue(str(path), f"invalid JSON: {exc.msg}"))
            continue

        if label == "project":
            issues.extend(validate_project_document(path, data))
            if isinstance(data, dict):
                payload["project"] = {
                    **payload["project"],
                    **{k: v for k, v in data.items() if k != "analytics"},
                    "analytics": data.get("analytics", []),
                }
            continue

        items, item_issues = validate_item_collection_document(path, data)
        issues.extend(item_issues)
        if status_show != "all":
            items = [item for item in items if item.get("active")]
        payload[label] = items

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic offline status reporting")
    parser.add_argument("mode", choices=["summary", "json", "check"])
    args = parser.parse_args()

    status_show = os.environ.get("STATUS_SHOW", "active")
    payload, issues = build_status_payload(status_show=status_show)

    if args.mode == "summary":
        emit_human_summary(payload, issues)
        return 0

    if args.mode == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(json.dumps({"issues": [issue.__dict__ for issue in issues]}, indent=2, sort_keys=True))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
