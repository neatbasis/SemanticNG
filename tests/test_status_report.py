from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "status_report"
SCRIPT = ROOT / "scripts" / "dev" / "status_report.py"


def _stage_scenario(tmp_path: Path, name: str) -> Path:
    scenario_src = FIXTURES / name
    run_dir = tmp_path / name
    shutil.copytree(scenario_src, run_dir)
    return run_dir


def _run_status(mode: str, cwd: Path, *, status_show: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if status_show is not None:
        env["STATUS_SHOW"] = status_show
    else:
        env.pop("STATUS_SHOW", None)

    return subprocess.run(
        [sys.executable, str(SCRIPT), mode],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_file_missing_reports_validation_issue(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "missing_milestones")

    result = _run_status("check", run_dir)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {"path": "docs/status/milestones.json", "message": "file is missing"} in payload["issues"]


def test_invalid_json_reports_decode_issue(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "invalid_json")

    result = _run_status("check", run_dir)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    issue = next(item for item in payload["issues"] if item["path"] == "docs/status/project.json")
    assert issue["message"].startswith("invalid JSON:")


def test_invalid_status_value_is_reported(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "invalid_status")

    result = _run_status("check", run_dir)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {
        "path": "docs/status/project.json",
        "message": "invalid status 'shipping'",
    } in payload["issues"]


def test_json_mode_filters_active_by_default_and_shows_all_when_requested(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "mixed_activity")

    active_only = _run_status("json", run_dir)
    show_all = _run_status("json", run_dir, status_show="all")

    assert active_only.returncode == 0
    assert json.loads(active_only.stdout) == _load_json(FIXTURES / "expected" / "mixed_active.json")

    assert show_all.returncode == 0
    assert json.loads(show_all.stdout) == _load_json(FIXTURES / "expected" / "mixed_all.json")


def test_unknown_fallback_and_reason_propagation_use_stable_shape(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "missing_project")

    result = _run_status("json", run_dir)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == _load_json(FIXTURES / "expected" / "missing_project_unknown.json")
    assert payload["project"]["status"] == "unknown"
    assert payload["project"]["reason"] == "project.json is missing or invalid"
    assert payload["milestones"][0]["reason"] == "Blocked on external signal"


def test_check_mode_exit_codes_follow_issue_presence(tmp_path: Path) -> None:
    valid_dir = _stage_scenario(tmp_path, "valid")
    invalid_dir = _stage_scenario(tmp_path, "invalid_status")

    valid_result = _run_status("check", valid_dir)
    invalid_result = _run_status("check", invalid_dir)

    assert valid_result.returncode == 0
    assert json.loads(valid_result.stdout) == {"issues": []}
    assert invalid_result.returncode == 1
    assert json.loads(invalid_result.stdout)["issues"]


def test_check_mode_fails_on_broken_references(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "broken_links")

    result = _run_status("check", run_dir)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any("references unknown" in item["message"] for item in payload["issues"])


def test_integrity_mode_fails_on_rollup_conflicts(tmp_path: Path) -> None:
    run_dir = _stage_scenario(tmp_path, "rollup_conflict")

    result = _run_status("integrity", run_dir)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any("linked objectives are not done" in item["message"] for item in payload["issues"])


def test_status_report_json_surfaces_generated_from_provenance() -> None:
    result = _run_status("json", ROOT)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    generated_from = payload["meta"]["generated_from"]
    assert generated_from["manifest"] == "docs/dod_manifest.json"
    assert isinstance(generated_from["manifest_commit"], str) and len(generated_from["manifest_commit"]) == 40
    assert generated_from["generated_at"].endswith("Z")


def test_generated_status_files_are_manifest_synchronized() -> None:
    manifest = _load_json(ROOT / "docs" / "dod_manifest.json")
    objectives = _load_json(ROOT / "docs" / "status" / "objectives.json")
    milestones = _load_json(ROOT / "docs" / "status" / "milestones.json")
    sprints = _load_json(ROOT / "docs" / "status" / "sprints.json")

    capability_status = {item["id"]: item["status"] for item in manifest["capabilities"]}

    expected_objective_ids = {group["id"] for group in manifest["capability_groups"]}
    observed_objective_ids = {item["id"] for item in objectives["items"]}
    assert observed_objective_ids == expected_objective_ids

    for group in manifest["capability_groups"]:
        member_statuses = [capability_status[cap_id] for cap_id in group["capability_ids"]]
        expected_status = (
            "in_progress"
            if "in_progress" in member_statuses
            else "planned"
            if "planned" in member_statuses
            else "done"
        )
        objective = next(item for item in objectives["items"] if item["id"] == group["id"])
        assert objective["status"] == expected_status

    for manifest_key, status_doc in (("milestone_groups", milestones), ("sprint_groups", sprints)):
        expected = {group["id"]: group["status"] for group in manifest[manifest_key]}
        observed = {item["id"]: item["status"] for item in status_doc["items"]}
        assert observed == expected


def test_generated_status_files_validate_against_status_schema() -> None:
    from scripts.dev.status_schema import validate_item_collection_document, validate_project_document

    objectives_path = ROOT / "docs" / "status" / "objectives.json"
    milestones_path = ROOT / "docs" / "status" / "milestones.json"
    sprints_path = ROOT / "docs" / "status" / "sprints.json"
    project_path = ROOT / "docs" / "status" / "project.json"

    _, objective_issues = validate_item_collection_document(objectives_path, _load_json(objectives_path))
    _, milestone_issues = validate_item_collection_document(milestones_path, _load_json(milestones_path))
    _, sprint_issues = validate_item_collection_document(sprints_path, _load_json(sprints_path))
    project_issues = validate_project_document(project_path, _load_json(project_path))

    assert objective_issues == []
    assert milestone_issues == []
    assert sprint_issues == []
    assert project_issues == []
