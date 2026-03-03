from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STATUS = {"done", "in_progress", "planned", "blocked", "unknown"}
REQUIRED_ITEM_KEYS = ("id", "name", "status", "active", "summary", "reason", "as_of")
REQUIRED_GROUP_ITEM_KEYS = ("stable_id",)
OPTIONAL_LINKAGE_KEYS = (
    "capability_ids",
    "depends_on",
    "satisfies",
    "milestone_id",
    "sprint_id",
    "dod_refs",
)

PROJECT_SCHEMA_CONTRACT: dict[str, Any] = {
    "type": "object",
    "required": [*REQUIRED_ITEM_KEYS, "waste_metrics"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "status": {"type": "string", "enum": sorted(ALLOWED_STATUS)},
        "active": {"type": "boolean"},
        "summary": {"type": "string"},
        "reason": {"type": "string"},
        "as_of": {"type": "string"},
        "waste_metrics": {
            "type": "object",
            "required": [
                "duplicate_logic_count",
                "unused_code_delta",
                "stale_doc_count",
                "mypy_debt_delta",
                "flaky_test_count",
            ],
            "properties": {
                "duplicate_logic_count": {"type": "integer"},
                "unused_code_delta": {"type": "integer"},
                "stale_doc_count": {"type": "integer"},
                "mypy_debt_delta": {"type": "integer"},
                "flaky_test_count": {"type": "integer"},
            },
        },
        "analytics": {"type": "array"},
    },
}

ITEM_COLLECTION_SCHEMA_CONTRACT: dict[str, Any] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": list(REQUIRED_ITEM_KEYS),
                "properties": {
                    "id": {"type": "string"},
                    "stable_id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": sorted(ALLOWED_STATUS)},
                    "active": {"type": "boolean"},
                    "summary": {"type": "string"},
                    "reason": {"type": "string"},
                    "as_of": {"type": "string"},
                    "capability_ids": {"type": "array", "items": {"type": "string"}},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                    "satisfies": {"type": "array", "items": {"type": "string"}},
                    "milestone_id": {"type": ["string", "null"]},
                    "sprint_id": {"type": ["string", "null"]},
                    "dod_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}

STATUS_FILE_CONTRACTS: dict[str, dict[str, Any]] = {
    "project": PROJECT_SCHEMA_CONTRACT,
    "milestones": ITEM_COLLECTION_SCHEMA_CONTRACT,
    "sprints": ITEM_COLLECTION_SCHEMA_CONTRACT,
    "objectives": ITEM_COLLECTION_SCHEMA_CONTRACT,
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


def validate_status_item(item: dict[str, Any], context: str, *, require_stable_id: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key in REQUIRED_ITEM_KEYS:
        if key not in item:
            issues.append(ValidationIssue(context, f"missing required key '{key}'"))
    if require_stable_id:
        for key in REQUIRED_GROUP_ITEM_KEYS:
            if key not in item:
                issues.append(ValidationIssue(context, f"missing required key '{key}'"))

    status = item.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        issues.append(ValidationIssue(context, f"invalid status '{status}'"))

    if "active" in item and not isinstance(item["active"], bool):
        issues.append(ValidationIssue(context, "'active' must be boolean"))

    for list_key in ("capability_ids", "depends_on", "satisfies", "dod_refs"):
        if list_key in item and not (
            isinstance(item[list_key], list)
            and all(isinstance(value, str) for value in item[list_key])
        ):
            issues.append(ValidationIssue(context, f"'{list_key}' must be an array of strings"))

    for id_key in ("milestone_id", "sprint_id"):
        if id_key in item and item[id_key] is not None and not isinstance(item[id_key], str):
            issues.append(ValidationIssue(context, f"'{id_key}' must be string or null"))

    return issues


def validate_project_document(path: Path, data: Any) -> list[ValidationIssue]:
    if not isinstance(data, dict):
        return [ValidationIssue(str(path), "project must be an object")]
    issues = validate_status_item(data, str(path))

    waste_metrics = data.get("waste_metrics")
    required_metric_keys = (
        "duplicate_logic_count",
        "unused_code_delta",
        "stale_doc_count",
        "mypy_debt_delta",
        "flaky_test_count",
    )
    if not isinstance(waste_metrics, dict):
        issues.append(ValidationIssue(str(path), "'waste_metrics' must be an object"))
        return issues

    for key in required_metric_keys:
        if key not in waste_metrics:
            issues.append(ValidationIssue(str(path), f"waste_metrics missing required key '{key}'"))
            continue
        if not isinstance(waste_metrics[key], int):
            issues.append(ValidationIssue(str(path), f"waste_metrics['{key}'] must be integer"))

    return issues


def validate_item_collection_document(path: Path, data: Any) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return [], [ValidationIssue(str(path), "expected object with an 'items' array")]

    items: list[dict[str, Any]] = []
    issues: list[ValidationIssue] = []

    for idx, item in enumerate(data["items"]):
        context = f"{path}::items[{idx}]"
        if not isinstance(item, dict):
            issues.append(ValidationIssue(context, "item must be object"))
            continue

        issues.extend(validate_status_item(item, context, require_stable_id=True))
        items.append(item)

    return items, issues
