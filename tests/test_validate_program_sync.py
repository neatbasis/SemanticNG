from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.ci import validate_program_sync

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "validate_program_sync.py"


def test_status_sync_check_passes_on_repo_state() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Program sync validation passed." in result.stdout


def test_program_sync_fails_when_multiple_authoritative_sources_configured() -> None:
    issues = validate_program_sync._validate_single_authoritative_source(
        {
            "canonical_source_of_truth": {
                "manifest_path": "docs/dod_manifest.json",
                "authoritative_sources": ["docs/dod_manifest.json", "docs/status/project.json"],
            }
        }
    )
    assert any("multiple authoritative sources configured" in issue.message for issue in issues)


def test_program_sync_fails_on_relational_integrity_breaks(tmp_path: Path, monkeypatch) -> None:
    milestone_view = tmp_path / "milestones.json"
    sprint_view = tmp_path / "sprints.json"
    objective_view = tmp_path / "objectives.json"

    milestone_view.write_text(json.dumps({"items": [{"name": "missing-id"}]}), encoding="utf-8")
    sprint_view.write_text(json.dumps({"items": [{"id": "sprint-1"}]}), encoding="utf-8")
    objective_view.write_text(json.dumps({"items": [{"id": "objective-1"}]}), encoding="utf-8")

    monkeypatch.setattr(validate_program_sync, "STATUS_VIEW_FILES", (objective_view, milestone_view, sprint_view))

    manifest = {
        "capabilities": [{"id": "known-capability"}],
        "capability_groups": [
            {
                "id": "objective-1",
                "capability_ids": ["unknown-capability"],
                "milestone_id": "missing-milestone",
                "sprint_id": "missing-sprint",
            },
            {"name": "broken-objective"},
        ],
        "milestone_groups": [{"id": "milestone-1"}, {"name": "broken-milestone"}],
        "sprint_groups": [{"id": "sprint-1"}, {"name": "broken-sprint"}],
    }

    issues = validate_program_sync._validate_relational_integrity(manifest)
    messages = [issue.message for issue in issues]
    assert any("missing IDs" in message for message in messages)
    assert any("unknown capability" in message for message in messages)
    assert any("unknown milestone" in message for message in messages)
    assert any("unknown sprint" in message for message in messages)
    assert any("orphan milestone" in message for message in messages)
    assert any("items[0] missing id" in message for message in messages)
