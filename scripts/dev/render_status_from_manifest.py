from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
STATUS_DIR = ROOT / "docs" / "status"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_head_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _rollup_status(statuses: list[str]) -> str:
    if any(status == "in_progress" for status in statuses):
        return "in_progress"
    if any(status == "planned" for status in statuses):
        return "planned"
    return "done"


def _build_objectives(manifest: dict[str, Any], as_of: str) -> dict[str, Any]:
    capabilities = {
        str(cap["id"]): str(cap["status"]) for cap in manifest.get("capabilities", []) if isinstance(cap, dict)
    }
    groups = manifest.get("capability_groups", [])
    items: list[dict[str, Any]] = []
    for group in groups:
        capability_ids = [str(cap_id) for cap_id in group.get("capability_ids", [])]
        member_statuses = [capabilities[cap_id] for cap_id in capability_ids if cap_id in capabilities]
        status = _rollup_status(member_statuses or ["planned"])
        items.append(
            {
                "id": str(group["id"]),
                "stable_id": str(group.get("stable_id", group["id"])),
                "name": str(group["name"]),
                "status": status,
                "active": status == "in_progress",
                "summary": str(group.get("summary", "")),
                "reason": str(group.get("reason", "")),
                "as_of": as_of,
                "capability_ids": capability_ids,
                "depends_on": [str(cap_id) for cap_id in group.get("depends_on", []) if isinstance(cap_id, str)],
                "satisfies": [str(cap_id) for cap_id in group.get("satisfies", capability_ids) if isinstance(cap_id, str)],
                "milestone_id": str(group.get("milestone_id")) if isinstance(group.get("milestone_id"), str) else None,
                "sprint_id": str(group.get("sprint_id")) if isinstance(group.get("sprint_id"), str) else None,
            }
        )
    return {"items": items}


def _build_group_items(manifest: dict[str, Any], key: str, as_of: str) -> dict[str, Any]:
    groups = manifest.get(key, [])
    items: list[dict[str, Any]] = []
    for group in groups:
        status = str(group.get("status", "planned"))
        items.append(
            {
                "id": str(group["id"]),
                "stable_id": str(group.get("stable_id", group["id"])),
                "name": str(group["name"]),
                "status": status,
                "active": bool(group.get("active", status == "in_progress")),
                "summary": str(group.get("summary", "")),
                "reason": str(group.get("reason", "")),
                "as_of": as_of,
                "depends_on": [str(item) for item in group.get("depends_on", []) if isinstance(item, str)],
                "milestone_id": str(group.get("milestone_id")) if isinstance(group.get("milestone_id"), str) else None,
                "sprint_id": str(group.get("sprint_id")) if isinstance(group.get("sprint_id"), str) else None,
            }
        )
    return {"items": items}


def _build_project(manifest: dict[str, Any], objectives: dict[str, Any], as_of: str, generated_at: str) -> dict[str, Any]:
    template = manifest.get("project_status", {})
    objective_statuses = [str(item.get("status", "planned")) for item in objectives.get("items", [])]
    project_status = _rollup_status(objective_statuses or ["planned"])
    return {
        "id": str(template.get("id", "semanticng")),
        "name": str(template.get("name", "SemanticNG")),
        "status": project_status,
        "active": project_status == "in_progress",
        "summary": str(template.get("summary", "")),
        "reason": str(template.get("reason", "")),
        "as_of": as_of,
        "waste_metrics": {
            "duplicate_logic_count": int(template.get("waste_metrics", {}).get("duplicate_logic_count", 0)),
            "unused_code_delta": int(template.get("waste_metrics", {}).get("unused_code_delta", 0)),
            "stale_doc_count": int(template.get("waste_metrics", {}).get("stale_doc_count", 0)),
            "mypy_debt_delta": int(template.get("waste_metrics", {}).get("mypy_debt_delta", 0)),
            "flaky_test_count": int(template.get("waste_metrics", {}).get("flaky_test_count", 0)),
        },
        "generated_at": generated_at,
        "manifest_commit": _git_head_commit(),
        "generated_from": str(MANIFEST_PATH.relative_to(ROOT)),
        "analytics": list(template.get("analytics", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render docs/status artifacts from docs/dod_manifest.json")
    parser.parse_args()

    manifest = _read_json(MANIFEST_PATH)
    generated_at = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    as_of = generated_at[:10]

    objectives = _build_objectives(manifest, as_of=as_of)
    milestones = _build_group_items(manifest, key="milestone_groups", as_of=as_of)
    sprints = _build_group_items(manifest, key="sprint_groups", as_of=as_of)
    project = _build_project(
        manifest,
        objectives=objectives,
        as_of=as_of,
        generated_at=generated_at,
    )

    _write_json(STATUS_DIR / "objectives.json", objectives)
    _write_json(STATUS_DIR / "milestones.json", milestones)
    _write_json(STATUS_DIR / "sprints.json", sprints)
    _write_json(STATUS_DIR / "project.json", project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
