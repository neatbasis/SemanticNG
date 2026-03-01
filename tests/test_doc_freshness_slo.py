from __future__ import annotations

import importlib.util
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
            "governance_doc": {"max_age_days": 30},
            "sprint_doc": {"max_age_days": 7},
        },
        "source_commit_policy": {
            "source_files": {
                "manifest": "docs/dod_manifest.json",
            },
            "governed_source_commits": {
                "*": {
                    "manifest": "abc1234",
                }
            },
        },
        "governed_files": [
            {"path": "docs/governed.md", "class": "governance_doc"},
        ],
    }


def _commit_resolver(_base_dir: Path, _repo_path: str) -> str | None:
    return "abc1234deadbeef"


def test_doc_freshness_slo_accepts_compliant_metadata(tmp_path: Path) -> None:
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
        commit_resolver=_commit_resolver,
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
        commit_resolver=_commit_resolver,
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
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 1
    assert "stale freshness metadata" in issues[0]["message"]


def test_doc_freshness_slo_validates_multiple_governed_files(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "governed.md").write_text(
        "# Governance\n\n_Last regenerated from manifest: 2026-02-25T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )
    (docs_dir / "release_checklist.md").write_text(
        "# Checklist\n\n_Last regenerated from manifest: 2026-02-24T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["governed_files"] = [
        {"path": "docs/governed.md", "class": "governance_doc"},
        {"path": "docs/release_checklist.md", "class": "governance_doc"},
    ]

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        commit_resolver=_commit_resolver,
    )

    assert issues == []


def test_doc_freshness_slo_reports_stale_metadata_across_classes_and_files(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    handoff_dir = docs_dir / "sprint_handoffs"
    handoff_dir.mkdir(parents=True)
    (docs_dir / "governed.md").write_text(
        "# Governance\n\n_Last regenerated from manifest: 2025-12-15T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )
    (handoff_dir / "sprint-1-handoff.md").write_text(
        "# Handoff\n\n_Last regenerated from manifest: 2026-02-01T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["governed_files"] = [
        {"path": "docs/governed.md", "class": "governance_doc"},
        {"path": "docs/sprint_handoffs/*.md", "class": "sprint_doc"},
    ]

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 2
    issue_paths = {issue["file_path"] for issue in issues}
    assert issue_paths == {"docs/governed.md", "docs/sprint_handoffs/sprint-1-handoff.md"}
    assert all("stale freshness metadata" in issue["message"] for issue in issues)


def test_doc_freshness_slo_reports_missing_timestamp_for_newly_governed_docs(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    handoff_dir = docs_dir / "sprint_handoffs"
    handoff_dir.mkdir(parents=True)
    (docs_dir / "governed.md").write_text(
        "# Governance\n\n_Last regenerated from manifest: 2026-02-27T00:00:00Z (UTC)._\n",
        encoding="utf-8",
    )
    (handoff_dir / "sprint-2-handoff.md").write_text(
        "# Newly Governed Handoff\n\nNo metadata line yet.\n",
        encoding="utf-8",
    )

    config = _base_config()
    config["governed_files"] = [
        {"path": "docs/governed.md", "class": "governance_doc"},
        {"path": "docs/sprint_handoffs/*.md", "class": "sprint_doc"},
    ]

    issues = validate_doc_freshness_slo._validate_doc_freshness(
        config,
        tmp_path,
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 1
    assert issues[0]["file_path"] == "docs/sprint_handoffs/sprint-2-handoff.md"
    assert "missing freshness metadata" in issues[0]["message"]


def test_doc_freshness_slo_rejects_commit_mismatch_with_fresh_timestamp(tmp_path: Path) -> None:
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
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 1
    assert "source commit mismatch" in issues[0]["message"]


def test_doc_freshness_slo_stale_timestamp_still_fails_when_commit_matches(tmp_path: Path) -> None:
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
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 1
    assert "stale freshness metadata" in issues[0]["message"]


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
        commit_resolver=_commit_resolver,
    )

    assert len(issues) == 1
    assert "missing source commit metadata" in issues[0]["message"]
