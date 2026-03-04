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




def test_json_mode_uses_offline_deterministic_mode_when_ci_evidence_unresolved() -> None:
    result = _run_status("json", ROOT)
    payload = json.loads(result.stdout)

    assert payload["meta"]["mode"] == "Offline deterministic mode"
    for gate in payload["quality_gates"]:
        if gate["status"] in {"ready", "unknown"}:
            assert "CI not resolved offline" in gate["status_reason"]


def test_summary_mode_prints_quality_gates_section() -> None:
    result = _run_status("summary", ROOT)
    assert result.returncode == 0
    assert "Quality Gates:" in result.stdout
    assert "Mode: Offline deterministic mode" in result.stdout
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


def test_json_mode_reports_semanticng_governed_paths() -> None:
    result = _run_status("json", ROOT)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    governed_src = payload["meta"]["schema_contract"]["governed_paths"]["src"]
    assert "src/semanticng/**" in governed_src


def test_json_mode_includes_required_status_artifacts_fields() -> None:
    result = _run_status("json", ROOT)
    assert result.returncode == 0
    payload = json.loads(result.stdout)

    artifacts = payload["meta"]

    latest_directive = artifacts["latest_directive"]
    assert set(latest_directive) == {"id", "version", "date", "source", "reason"}
    assert isinstance(latest_directive["id"], str)
    assert isinstance(latest_directive["version"], (int, str))
    assert isinstance(latest_directive["date"], str)
    assert isinstance(latest_directive["source"], str)

    ci_run_name = artifacts["ci_deterministic_run_name"]
    assert set(ci_run_name) == {"stage", "branch", "value", "reason"}
    assert ci_run_name["stage"] == "qa-ci"
    assert isinstance(ci_run_name["branch"], str)
    assert isinstance(ci_run_name["value"], str)

    fail_fast = artifacts["last_fail_fast_stop_reason"]
    assert set(fail_fast) == {"summary", "reason_code", "stage_id", "next_action", "reason"}
    assert isinstance(fail_fast["summary"], str)
    assert isinstance(fail_fast["reason_code"], str)
    assert isinstance(fail_fast["stage_id"], str)
    assert isinstance(fail_fast["next_action"], str)

    drift_incidents = artifacts["drift_incidents"]
    assert set(drift_incidents) == {"open_incident_count", "last_incident_summary", "resolution_sla"}
    assert isinstance(drift_incidents["last_incident_summary"], str)

    resolution_sla = drift_incidents["resolution_sla"]
    assert set(resolution_sla) == {"triage_business_days", "fix_business_days", "waiver_business_days", "source"}
    assert isinstance(resolution_sla["triage_business_days"], int)
    assert isinstance(resolution_sla["fix_business_days"], int)
    assert isinstance(resolution_sla["waiver_business_days"], int)
    assert isinstance(resolution_sla["source"], str)
