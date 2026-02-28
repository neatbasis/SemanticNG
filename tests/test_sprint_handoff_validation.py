from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "validate_sprint_handoff.py"
HANDOFF_PATH = ROOT / "docs" / "sprint_handoffs" / "sprint-5-handoff.md"
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"

_spec = importlib.util.spec_from_file_location("validate_sprint_handoff", SCRIPT_PATH)
assert _spec and _spec.loader
validate_sprint_handoff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_sprint_handoff)


def _load_manifest_capability_ids() -> set[str]:
    manifest = cast(dict[str, Any], json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
    capability_ids: set[str] = set()
    for cap in manifest.get("capabilities", []):
        if isinstance(cap, dict) and isinstance(cap.get("id"), str):
            capability_ids.add(cap["id"])
    return capability_ids


def test_handoff_contains_required_sections() -> None:
    text = HANDOFF_PATH.read_text(encoding="utf-8")

    for heading in validate_sprint_handoff.REQUIRED_HEADINGS:
        assert heading in text


def test_handoff_preload_capability_ids_exist_in_manifest() -> None:
    capability_ids = _load_manifest_capability_ids()

    mismatches = validate_sprint_handoff._validate_handoff_file(HANDOFF_PATH, capability_ids)
    assert mismatches == []


def test_detects_unknown_preload_capability_id(tmp_path: Path) -> None:
    bad_handoff = tmp_path / "sprint-99-handoff.md"
    bad_handoff.write_text(
        "\n".join(
            [
                "# Sprint 99 handoff",
                "",
                "## Exit criteria pass/fail matrix",
                "| Exit criterion | Status (`pass`/`fail`) | Evidence |",
                "| --- | --- | --- |",
                "| Ready | pass | evidence |",
                "",
                "## Open risk register with owners/dates",
                "| Risk | Owner | Target resolution date (YYYY-MM-DD) | Mitigation/next step |",
                "| --- | --- | --- | --- |",
                "| Drift | Owner | 2026-01-30 | Mitigate |",
                "",
                "## Next-sprint preload mapped to capability IDs",
                "| Capability ID | Preload objective | Dependency notes |",
                "| --- | --- | --- |",
                "| `not_in_manifest` | Objective | Notes |",
            ]
        ),
        encoding="utf-8",
    )

    mismatches = validate_sprint_handoff._validate_handoff_file(bad_handoff, {"known_capability"})

    assert len(mismatches) == 1
    assert "not found in docs/dod_manifest.json" in mismatches[0]
