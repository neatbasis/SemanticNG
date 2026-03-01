from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_doc_freshness_slo.py"

_spec = importlib.util.spec_from_file_location("validate_doc_freshness_slo", SCRIPT_PATH)
assert _spec and _spec.loader
validate_doc_freshness_slo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_doc_freshness_slo)


def _base_config() -> dict:
    return {
        "timestamp_policy": {
            "field_name": "Last regenerated from manifest",
            "pattern": r"^_Last regenerated from manifest: (?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) \(UTC\)\._\s*$",
            "format": "%Y-%m-%dT%H:%M:%SZ",
            "timezone": "UTC",
        },
        "file_classes": {
            "governance_doc": {"max_age_days": 30, "max_commit_lag": 2},
            "sprint_doc": {"max_age_days": 7, "max_commit_lag": 1},
        },
        "source_commit_policy": {
            "source_files": {
                "manifest": {"path": "docs/dod_manifest.json", "lag_reference": "head"},
                "roadmap": {"path": "ROADMAP.md", "lag_reference": "source_tip"},
            },
            "governed_source_map": {
                "docs/governed.md": ["manifest"],
                "docs/sprint_handoffs/*.md": ["roadmap"],
            },
            "governed_source_commits": {
                "*": {
                    "manifest": "abc1234",
                    "roadmap": "def5678",
                }
            },
        },
        "governed_files": [
            {"path": "docs/governed.md", "class": "governance_doc"},
        ],
    }


def _git_runner(_base_dir: Path, args: list[str]) -> str | None:
    if args[:2] == ["rev-list", "--count"]:
        ranges = {
            "abc1234..head": "2",
            "def5678..feedface": "1",
            "fffffff..head": "8",
            "def5678..badc0de": "3",
        }
        return ranges.get(args[2])
    if args[:5] == ["rev-list", "-1", "HEAD", "--", "ROADMAP.md"]:
        return "feedface"
    if args[:5] == ["rev-list", "-1", "HEAD", "--", "docs/dod_manifest.json"]:
        return "c0ffee"
    return None


def test_doc_freshness_slo_accepts_compliant_metadata_and_commit_lag(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        _base_config(),
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert issues == []


def test_doc_freshness_slo_rejects_missing_metadata(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text("# Governed Doc\n\nNo timestamp here.\n", encoding="utf-8")

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        _base_config(),
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "missing freshness metadata" in issues[0]["message"]


def test_doc_freshness_slo_rejects_stale_document(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2025-12-01T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        _base_config(),
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "stale freshness metadata" in issues[0]["message"]


def test_doc_freshness_slo_commit_lag_at_threshold_passes(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["file_classes"]["governance_doc"]["max_commit_lag"] = 2

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert issues == []


def test_doc_freshness_slo_commit_lag_above_threshold_fails(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["source_commit_policy"]["governed_source_commits"]["*"]["manifest"] = "fffffff"

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "commit lag violation" in issues[0]["message"]


def test_doc_freshness_slo_source_tip_reference_uses_source_commit_distance(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    handoff_dir = docs_dir / "sprint_handoffs"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / "sprint-1-handoff.md").write_text(
        "# Handoff\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["governed_files"] = [{"path": "docs/sprint_handoffs/*.md", "class": "sprint_doc"}]

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert issues == []


def test_doc_freshness_slo_source_tip_reference_violation_fails(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    handoff_dir = docs_dir / "sprint_handoffs"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / "sprint-2-handoff.md").write_text(
        "# Handoff\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["governed_files"] = [{"path": "docs/sprint_handoffs/*.md", "class": "sprint_doc"}]

    def lagging_runner(base_dir: Path, args: list[str]) -> str | None:
        if args[:2] == ["rev-list", "--count"] and args[2] == "def5678..badc0de":
            return "3"
        if args[:5] == ["rev-list", "-1", "HEAD", "--", "ROADMAP.md"]:
            return "badc0de"
        return _git_runner(base_dir, args)

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=lagging_runner,
    )

    assert len(issues) == 1
    assert "commit lag violation" in issues[0]["message"]


def test_doc_freshness_slo_rejects_missing_source_mapping(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["source_commit_policy"]["governed_source_map"] = {}

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "missing source mapping" in issues[0]["message"]


def test_doc_freshness_slo_rejects_missing_source_commit_metadata(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["source_commit_policy"]["governed_source_commits"] = {}

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "missing source commit metadata" in issues[0]["message"]



def test_doc_freshness_slo_config_error_invalid_max_commit_lag(tmp_path: Path) -> None:
    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text(
        "# Governed Doc\n\n_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["file_classes"]["governance_doc"]["max_commit_lag"] = "bad"

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        git_runner=_git_runner,
    )

    assert len(issues) == 1
    assert "invalid max_commit_lag" in issues[0]["message"]


def test_doc_freshness_slo_main_prints_release_checklist_remediation_on_failure(tmp_path: Path, capsys) -> None:
    config_path = tmp_path / "doc_freshness_slo.json"
    config_path.write_text(json.dumps(_base_config()), encoding="utf-8")

    governed = tmp_path / "docs" / "governed.md"
    governed.parent.mkdir(parents=True)
    governed.write_text("# Governed Doc\n\nNo timestamp here.\n", encoding="utf-8")

    previous_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        exit_code = validate_doc_freshness_slo.main(["--config", str(config_path)])
    finally:
        os.chdir(previous_cwd)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing freshness metadata" in captured.err
    assert "docs/release_checklist.md#freshness-validator-remediation-playbook" in captured.err
