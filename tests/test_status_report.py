from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "status_report.py"


def _run_status(mode: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_check_mode_fails_when_canonical_manifest_missing(tmp_path: Path) -> None:
    result = _run_status("check", tmp_path)
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {"path": "docs/dod_manifest.json", "message": "file is missing"} in payload["issues"]


def test_json_mode_reads_status_from_canonical_manifest() -> None:
    result = _run_status("json", ROOT)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["meta"]["generated_from"]["manifest"] == "docs/dod_manifest.json"
    assert payload["dod"]["manifest"] == "docs/dod_manifest.json"
    assert isinstance(payload["milestones"], list)
    assert isinstance(payload["sprints"], list)
    assert isinstance(payload["objectives"], list)


def test_json_mode_adds_manifest_reference_annotations() -> None:
    result = _run_status("json", ROOT)
    payload = json.loads(result.stdout)
    for group in ("milestones", "sprints", "objectives"):
        for item in payload[group]:
            assert any(ref.startswith("docs/dod_manifest.json#") for ref in item.get("dod_refs", []))


def test_check_mode_passes_on_repository_state() -> None:
    result = _run_status("check", ROOT)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"issues": []}


def test_json_mode_reports_quality_gates_with_offline_safe_statuses() -> None:
    result = _run_status("json", ROOT)
    payload = json.loads(result.stdout)
    gates = payload["quality_gates"]
    assert any(gate["display_name"].startswith("Quality Guardrails /") for gate in gates)
    assert any(gate["id"].startswith("milestone_gate.") for gate in gates)
    allowed_statuses = {"ready", "unknown", "pass", "fail"}
    for gate in gates:
        assert gate["classification"] in {"blocking", "measurement-only"}
        assert gate["status"] in allowed_statuses
        assert gate["scope"].startswith("always-on/global") or gate["scope"].startswith("path-conditioned:")


def test_summary_mode_prints_quality_gates_section() -> None:
    result = _run_status("summary", ROOT)
    assert result.returncode == 0
    assert "Quality Gates:" in result.stdout
    assert "Quality Guardrails / no-regression-budget" in result.stdout
    assert "promotion-governance-pokayoke" in result.stdout


def test_json_mode_includes_relational_rollups_and_consistency_warnings() -> None:
    result = _run_status("json", ROOT)
    payload = json.loads(result.stdout)

    rollups = payload["relational_rollups"]
    assert set(rollups) == {"active", "in_progress", "done"}
    done_rollups = rollups["done"]
    assert any(row["capability_mapping"]["satisfies"] for row in done_rollups)
    assert all("sprint_id" in row and "milestone_id" in row for row in done_rollups)

    assert isinstance(payload["consistency_warnings"], list)
