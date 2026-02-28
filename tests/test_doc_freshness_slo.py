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
        },
        "governed_files": [
            {"path": "docs/governed.md", "class": "governance_doc"},
        ],
    }


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
    )

    assert len(issues) == 1
    assert "stale freshness metadata" in issues[0]["message"]
