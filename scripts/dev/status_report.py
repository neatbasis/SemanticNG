from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from status_schema import (
    STATUS_FILE_CONTRACTS,
    ValidationIssue,
    validate_item_collection_document,
    validate_project_document,
)

DOD_MANIFEST_PATH = Path("docs/dod_manifest.json")
GOVERNED_PATHS_KEY = "governed_paths"
OFFLINE_MODE_BANNER = "Offline deterministic mode"
CI_RESOLVED_MODE_BANNER = "CI-resolved mode"
CI_UNRESOLVED_REASON = "CI not resolved offline"
CI_RESOLVED_REASON = "resolved from canonical CI evidence"
Issue = ValidationIssue


def _default_project_payload() -> dict[str, Any]:
    return {
        "id": "unknown",
        "name": "unknown",
        "status": "unknown",
        "active": True,
        "summary": "unknown",
        "reason": "dod_manifest.json is missing or invalid",
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


def _base_payload(status_show: str) -> dict[str, Any]:
    return {
        "meta": {
            "generator": "scripts/dev/status_report.py",
            "deterministic": True,
            "offline": True,
            "status_show": status_show,
            "mode": OFFLINE_MODE_BANNER,
            "unknown_policy": "Print unknown with reason when data is missing or unresolved.",
            "generated_from": {
                "manifest": DOD_MANIFEST_PATH.as_posix(),
                "manifest_commit": "unknown",
                "generated_at": "unknown",
            },
            "schema_contract": {
                "allowed_status": sorted(STATUS_FILE_CONTRACTS["project"]["properties"]["status"]["enum"]),
                "required_keys": list(STATUS_FILE_CONTRACTS["project"]["required"]),
                "files": {
                    "canonical_manifest": DOD_MANIFEST_PATH.as_posix(),
                    "generated_views": "docs/status/*.json",
                    "narrative_only": ["ROADMAP.md", "docs/sprint_plan_5x.md", "docs/sprint_handoffs/*.md"],
                },
                "governed_paths": {"src": [], "ci_triggers": []},
            },
        },
        "project": _default_project_payload(),
        "milestones": [],
        "sprints": [],
        "objectives": [],
    }




def _manifest_governed_paths(manifest: dict[str, Any]) -> dict[str, list[str]]:
    governed = manifest.get(GOVERNED_PATHS_KEY, {})
    if not isinstance(governed, dict):
        return {"src": [], "ci_triggers": []}
    src = [item for item in governed.get("src", []) if isinstance(item, str)]
    ci_triggers = [item for item in governed.get("ci_triggers", []) if isinstance(item, str)]
    return {"src": src, "ci_triggers": ci_triggers}

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _filter_items(items: list[dict[str, Any]], status_show: str) -> list[dict[str, Any]]:
    return items if status_show == "all" else [item for item in items if item.get("active")]


def _rollup_group_status(member_statuses: list[str]) -> str:
    if not member_statuses:
        return "planned"
    if "in_progress" in member_statuses:
        return "in_progress"
    if "planned" in member_statuses:
        return "planned"
    return "done"


def _safe_git(*args: str) -> str | None:
    try:
        completed = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _load_manifest_at_git_ref(git_ref: str) -> dict[str, Any] | None:
    payload = _safe_git("show", f"{git_ref}:{DOD_MANIFEST_PATH.as_posix()}")
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_capability_statuses(manifest: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for item in manifest.get("capabilities", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("status"), str):
            statuses[item["id"]] = item["status"]
    return statuses


def _recent_capability_transitions(limit: int = 5) -> list[dict[str, str]]:
    log_output = _safe_git("log", "--format=%H\t%cI", "-n", "25", "--", DOD_MANIFEST_PATH.as_posix())
    if not log_output:
        return []
    transitions: list[dict[str, str]] = []
    for line in log_output.splitlines():
        if len(transitions) >= limit:
            break
        commit, *rest = line.split("\t", 1)
        if not rest:
            continue
        current_manifest = _load_manifest_at_git_ref(commit)
        previous_manifest = _load_manifest_at_git_ref(f"{commit}^")
        if current_manifest is None or previous_manifest is None:
            continue
        current = _extract_capability_statuses(current_manifest)
        previous = _extract_capability_statuses(previous_manifest)
        for capability_id, after in sorted(current.items()):
            before = previous.get(capability_id)
            if before and before != after:
                transitions.append({"capability_id": capability_id, "from": before, "to": after, "commit": commit, "committed_at": rest[0]})
                if len(transitions) >= limit:
                    break
    return transitions


def _manifest_collections(manifest: dict[str, Any], as_of: str) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[Issue]]:
    issues: list[Issue] = []
    capabilities = _extract_capability_statuses(manifest)

    objectives: list[dict[str, Any]] = []
    for idx, group in enumerate(manifest.get("capability_groups", [])):
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            issues.append(Issue(str(DOD_MANIFEST_PATH), f"capability_groups[{idx}] missing id"))
            continue
        capability_ids = [cap_id for cap_id in group.get("capability_ids", []) if isinstance(cap_id, str)]
        statuses = [capabilities[cap_id] for cap_id in capability_ids if cap_id in capabilities]
        status = _rollup_group_status(statuses)
        objectives.append(
            {
                "id": group["id"],
                "stable_id": str(group.get("stable_id", group["id"])),
                "name": str(group.get("name", group["id"])),
                "status": status,
                "active": bool(group.get("active", status == "in_progress")),
                "summary": str(group.get("summary", "")),
                "reason": str(group.get("reason", "")),
                "as_of": as_of,
                "capability_ids": capability_ids,
                "depends_on": [cap_id for cap_id in group.get("depends_on", []) if isinstance(cap_id, str)],
                "satisfies": [cap_id for cap_id in group.get("satisfies", capability_ids) if isinstance(cap_id, str)],
                "milestone_id": group.get("milestone_id") if isinstance(group.get("milestone_id"), str) else None,
                "sprint_id": group.get("sprint_id") if isinstance(group.get("sprint_id"), str) else None,
                "dod_refs": [f"{DOD_MANIFEST_PATH.as_posix()}#capability_groups/{group['id']}"]
            }
        )

    def _groups(key: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for group in manifest.get(key, []):
            if not isinstance(group, dict) or not isinstance(group.get("id"), str):
                continue
            status = str(group.get("status", "planned"))
            rows.append(
                {
                    "id": group["id"],
                    "stable_id": str(group.get("stable_id", group["id"])),
                    "name": str(group.get("name", group["id"])),
                    "status": status,
                    "active": bool(group.get("active", status == "in_progress")),
                    "summary": str(group.get("summary", "")),
                    "reason": str(group.get("reason", "")),
                    "as_of": as_of,
                    "depends_on": [item for item in group.get("depends_on", []) if isinstance(item, str)],
                    "milestone_id": group.get("milestone_id") if isinstance(group.get("milestone_id"), str) else None,
                    "sprint_id": group.get("sprint_id") if isinstance(group.get("sprint_id"), str) else None,
                    "dod_refs": [f"{DOD_MANIFEST_PATH.as_posix()}#{key}/{group['id']}"]
                }
            )
        return rows

    milestones = _groups("milestone_groups")
    sprints = _groups("sprint_groups")

    project_template = manifest.get("project_status", {}) if isinstance(manifest.get("project_status", {}), dict) else {}
    objective_statuses = [item["status"] for item in objectives]
    project_status = _rollup_group_status(objective_statuses or ["planned"])
    project = {
        "id": str(project_template.get("id", "semanticng")),
        "name": str(project_template.get("name", "SemanticNG")),
        "status": project_status,
        "active": project_status == "in_progress",
        "summary": str(project_template.get("summary", "")),
        "reason": str(project_template.get("reason", "")),
        "as_of": as_of,
        "waste_metrics": {
            "duplicate_logic_count": int(project_template.get("waste_metrics", {}).get("duplicate_logic_count", 0)),
            "unused_code_delta": int(project_template.get("waste_metrics", {}).get("unused_code_delta", 0)),
            "stale_doc_count": int(project_template.get("waste_metrics", {}).get("stale_doc_count", 0)),
            "mypy_debt_delta": int(project_template.get("waste_metrics", {}).get("mypy_debt_delta", 0)),
            "flaky_test_count": int(project_template.get("waste_metrics", {}).get("flaky_test_count", 0)),
        },
        "analytics": list(project_template.get("analytics", [])),
    }
    return project, {"objectives": objectives, "milestones": milestones, "sprints": sprints}, issues


def _objective_relational_rollups(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rollups: dict[str, list[dict[str, Any]]] = {"active": [], "in_progress": [], "done": []}
    sprint_by_id = {item["id"]: item for item in payload.get("sprints", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    milestone_by_id = {item["id"]: item for item in payload.get("milestones", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}

    for objective in payload.get("objectives", []):
        if not isinstance(objective, dict):
            continue
        bucket = "done" if objective.get("status") == "done" else "in_progress" if objective.get("status") == "in_progress" else "active" if objective.get("active") else "done"
        sprint_id = objective.get("sprint_id")
        milestone_id = objective.get("milestone_id")
        rollups[bucket].append(
            {
                "objective_id": objective.get("id"),
                "objective_name": objective.get("name"),
                "status": objective.get("status"),
                "sprint_id": sprint_id,
                "sprint_name": sprint_by_id.get(sprint_id, {}).get("name") if isinstance(sprint_id, str) else None,
                "milestone_id": milestone_id,
                "milestone_name": milestone_by_id.get(milestone_id, {}).get("name") if isinstance(milestone_id, str) else None,
                "capability_mapping": {
                    "depends_on": [item for item in objective.get("depends_on", []) if isinstance(item, str)],
                    "satisfies": [item for item in objective.get("satisfies", []) if isinstance(item, str)],
                },
            }
        )
    return rollups


def _consistency_warnings(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    active_sprint_ids = {
        item["id"] for item in payload.get("sprints", []) if isinstance(item, dict) and item.get("active") is True and isinstance(item.get("id"), str)
    }

    objectives = [item for item in payload.get("objectives", []) if isinstance(item, dict)]
    for item in objectives:
        if item.get("active") is not True:
            continue
        sprint_id = item.get("sprint_id")
        if isinstance(sprint_id, str) and sprint_id not in active_sprint_ids:
            warnings.append(f"active objective '{item.get('id')}' is not linked to an active sprint")

    objectives_by_sprint: dict[str, int] = {}
    for item in objectives:
        sprint_id = item.get("sprint_id")
        if isinstance(sprint_id, str):
            objectives_by_sprint[sprint_id] = objectives_by_sprint.get(sprint_id, 0) + 1
    for sprint in payload.get("sprints", []):
        if not isinstance(sprint, dict) or sprint.get("active") is not True:
            continue
        sprint_id = sprint.get("id")
        if isinstance(sprint_id, str) and objectives_by_sprint.get(sprint_id, 0) == 0:
            warnings.append(f"active sprint '{sprint_id}' has zero objectives")

    for item in objectives:
        if item.get("status") != "done":
            continue
        satisfies = item.get("satisfies") if isinstance(item.get("satisfies"), list) else []
        if not satisfies:
            warnings.append(f"done objective '{item.get('id')}' is missing DoD capability mapping")
    return warnings


def _build_dod_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "manifest": DOD_MANIFEST_PATH.as_posix(),
        "available": True,
        "counts_by_status": {"done": 0, "in_progress": 0, "planned": 0},
        "recent_transitions": _recent_capability_transitions(),
        "missing_metadata": [],
    }
    for capability in manifest.get("capabilities", []):
        if not isinstance(capability, dict):
            continue
        status = capability.get("status")
        if status in summary["counts_by_status"]:
            summary["counts_by_status"][status] += 1
    return summary


def _manifest_quality_gates(manifest: dict[str, Any]) -> list[dict[str, str]]:
    gates: list[dict[str, str]] = []
    raw_gates = manifest.get("quality_gates", [])
    if not isinstance(raw_gates, list):
        return gates

    for gate in raw_gates:
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("id")
        display_name = gate.get("display_name")
        classification = gate.get("classification")
        scope = gate.get("scope")
        if not all(isinstance(item, str) and item for item in (gate_id, display_name, classification, scope)):
            continue

        evidence = gate.get("ci_evidence") if isinstance(gate.get("ci_evidence"), dict) else {}
        evidence_status = evidence.get("status")
        has_evidence_link = isinstance(evidence.get("link"), str) and bool(evidence["link"])

        status = "unknown"
        status_reason = CI_UNRESOLVED_REASON
        if isinstance(evidence_status, str) and has_evidence_link and evidence_status in {"pass", "fail"}:
            status = evidence_status
            status_reason = CI_RESOLVED_REASON
        elif bool(gate.get("ready", False)):
            status = "ready"
            status_reason = f"ready in canonical manifest; {CI_UNRESOLVED_REASON}"

        gates.append(
            {
                "id": gate_id,
                "display_name": display_name,
                "classification": classification,
                "scope": scope,
                "status": status,
                "status_reason": status_reason,
            }
        )
    return gates


def _resolve_mode_banner(quality_gates: list[dict[str, str]]) -> str:
    return (
        CI_RESOLVED_MODE_BANNER
        if any(gate.get("status") in {"pass", "fail"} and gate.get("status_reason") == CI_RESOLVED_REASON for gate in quality_gates)
        else OFFLINE_MODE_BANNER
    )


def build_status_payload(status_show: str) -> tuple[dict[str, Any], list[Issue]]:
    issues: list[Issue] = []
    payload = _base_payload(status_show=status_show)
    if not DOD_MANIFEST_PATH.exists():
        issues.append(Issue(str(DOD_MANIFEST_PATH), "file is missing"))
        return payload, issues
    try:
        manifest = _load_json(DOD_MANIFEST_PATH)
    except json.JSONDecodeError as exc:
        issues.append(Issue(str(DOD_MANIFEST_PATH), f"invalid JSON: {exc.msg}"))
        return payload, issues
    if not isinstance(manifest, dict):
        issues.append(Issue(str(DOD_MANIFEST_PATH), "manifest root must be an object"))
        return payload, issues

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    as_of = generated_at[:10]
    payload["meta"]["generated_from"] = {
        "manifest": DOD_MANIFEST_PATH.as_posix(),
        "manifest_commit": _safe_git("rev-parse", "HEAD") or "unknown",
        "generated_at": generated_at,
    }

    project, collections, collection_issues = _manifest_collections(manifest, as_of)
    payload["meta"]["schema_contract"]["governed_paths"] = _manifest_governed_paths(manifest)
    issues.extend(collection_issues)
    payload["project"] = project
    payload["dod"] = _build_dod_summary(manifest)
    payload["quality_gates"] = _manifest_quality_gates(manifest)
    payload["meta"]["mode"] = _resolve_mode_banner(payload["quality_gates"])

    _, project_issues = project, validate_project_document(Path("docs/dod_manifest.json::project_status"), project)
    issues.extend(project_issues)

    validated_collections: dict[str, list[dict[str, Any]]] = {}
    for label in ("milestones", "sprints", "objectives"):
        doc = {"items": collections[label]}
        validated, validation_issues = validate_item_collection_document(Path(f"docs/dod_manifest.json::{label}"), doc)
        issues.extend(validation_issues)
        validated_collections[label] = validated
        payload[label] = _filter_items(validated, status_show)

    payload["relational_rollups"] = _objective_relational_rollups(validated_collections)
    payload["consistency_warnings"] = _consistency_warnings(validated_collections)

    return payload, issues


def emit_human_summary(payload: dict[str, Any], validation_issues: list[Issue]) -> None:
    project = payload["project"]
    print("SemanticNG Delivery Status")
    print("=" * 26)
    print(f"Mode: {payload.get('meta', {}).get('mode', OFFLINE_MODE_BANNER)}")
    print(f"Project: {project['name']} ({project['status']})")
    print(f"Summary: {project['summary']}")
    print(f"Reason: {project['reason']}")
    governed_src = payload.get("meta", {}).get("schema_contract", {}).get("governed_paths", {}).get("src", [])
    if governed_src:
        print(f"Governed source scope: {', '.join(governed_src)}")
    for group in ("milestones", "sprints", "objectives"):
        print(f"\n{group.title()}:")
        rows = payload[group]
        if not rows:
            print("- unknown: no active data available (set STATUS_SHOW=all for full inventory)")
        for item in rows:
            print(f"- {item['name']} [{item['status']}]")
            print(f"  summary: {item['summary']}")
            print(f"  reason: {item['reason']}")
            refs = item.get("dod_refs", [])
            if refs:
                print(f"  refs: {', '.join(refs)}")
    quality_gates = payload.get("quality_gates", [])
    print("\nQuality Gates:")
    if not quality_gates:
        print("- unknown: no quality gate inventory available")
    for gate in quality_gates:
        print(f"- {gate['id']} ({gate['display_name']})")
        print(f"  classification: {gate['classification']}")
        print(f"  scope: {gate['scope']}")
        print(f"  status: {gate['status']}")
        print(f"  reason: {gate['status_reason']}")
    if validation_issues:
        print("\nValidation warnings:")
        for issue in validation_issues:
            print(f"- {issue.path}: {issue.message}")
    relational_rollups = payload.get("relational_rollups", {})
    print("\nObjective Relational Rollups:")
    for key in ("active", "in_progress", "done"):
        print(f"{key}:")
        rows = relational_rollups.get(key, []) if isinstance(relational_rollups, dict) else []
        if not rows:
            print("- none")
            continue
        for row in rows:
            mapping = row.get("capability_mapping", {})
            depends_on = mapping.get("depends_on", []) if isinstance(mapping, dict) else []
            satisfies = mapping.get("satisfies", []) if isinstance(mapping, dict) else []
            print(
                f"- {row.get('objective_name')} ({row.get('objective_id')})"
                f" | sprint={row.get('sprint_id')}"
                f" | milestone={row.get('milestone_id')}"
                f" | depends_on={depends_on}"
                f" | satisfies={satisfies}"
            )

    consistency_warnings = payload.get("consistency_warnings", [])
    print("\nConsistency warnings:")
    if not consistency_warnings:
        print("- none")
    else:
        for warning in consistency_warnings:
            print(f"- {warning}")


def emit_json_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def emit_check_issues(validation_issues: list[Issue]) -> None:
    print(json.dumps({"issues": [issue.__dict__ for issue in validation_issues]}, indent=2, sort_keys=True))


def main() -> int:
    mode_aliases = {"summary": "summary", "json": "json", "check": "check", "status": "summary", "status-json": "json", "status-check": "check", "integrity": "integrity", "status-integrity": "integrity"}
    parser = argparse.ArgumentParser(description="Deterministic offline status reporting")
    parser.add_argument("mode", choices=sorted(mode_aliases))
    args = parser.parse_args()
    resolved_mode = mode_aliases[args.mode]
    payload, issues = build_status_payload(status_show=os.environ.get("STATUS_SHOW", "active"))
    if resolved_mode == "summary":
        emit_human_summary(payload, issues)
        return 0
    if resolved_mode == "json":
        emit_json_payload(payload)
        return 0
    if resolved_mode == "integrity":
        integrity_issues = [issue for issue in issues if "references unknown" in issue.message or "linked objectives are not done" in issue.message]
        emit_check_issues(integrity_issues)
        return 1 if integrity_issues else 0
    emit_check_issues(issues)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
