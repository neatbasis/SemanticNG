from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_STATUS = {"done", "in_progress", "planned", "blocked", "unknown"}
REQUIRED_ITEM_KEYS = ("id", "name", "status", "active", "summary", "reason", "as_of")

PROJECT_SCHEMA_CONTRACT: dict[str, Any] = {
    "type": "object",
    "required": list(REQUIRED_ITEM_KEYS),
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "status": {"type": "string", "enum": sorted(ALLOWED_STATUS)},
        "active": {"type": "boolean"},
        "summary": {"type": "string"},
        "reason": {"type": "string"},
        "as_of": {"type": "string"},
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
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": sorted(ALLOWED_STATUS)},
                    "active": {"type": "boolean"},
                    "summary": {"type": "string"},
                    "reason": {"type": "string"},
                    "as_of": {"type": "string"},
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


def validate_status_item(item: dict[str, Any], context: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key in REQUIRED_ITEM_KEYS:
        if key not in item:
            issues.append(ValidationIssue(context, f"missing required key '{key}'"))

    status = item.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        issues.append(ValidationIssue(context, f"invalid status '{status}'"))

    if "active" in item and not isinstance(item["active"], bool):
        issues.append(ValidationIssue(context, "'active' must be boolean"))

    return issues


def validate_project_document(path: Path, data: Any) -> list[ValidationIssue]:
    if not isinstance(data, dict):
        return [ValidationIssue(str(path), "project must be an object")]
    return validate_status_item(data, str(path))


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

        issues.extend(validate_status_item(item, context))
        items.append(item)

    return items, issues
