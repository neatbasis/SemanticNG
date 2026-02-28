from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
ROADMAP_PATH = ROOT / "ROADMAP.md"
PROJECT_MATURITY_PATH = ROOT / "docs" / "project_maturity_evaluation.md"


def _load_manifest_status_map() -> dict[str, str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    capabilities = manifest.get("capabilities", [])
    return {
        cap["id"]: cap["status"]
        for cap in capabilities
        if isinstance(cap.get("id"), str) and isinstance(cap.get("status"), str)
    }


def _extract_roadmap_status_buckets(roadmap_text: str) -> tuple[dict[str, set[str]], dict[str, str]]:
    buckets: dict[str, set[str]] = {}
    context_by_status: dict[str, str] = {}
    in_alignment = False
    bullet_pattern = re.compile(r"^- `([^`]+)`: (.+)\.$")

    for line in roadmap_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Capability status alignment"):
            in_alignment = True
            continue
        if in_alignment and stripped.startswith("## "):
            break
        if not in_alignment:
            continue

        match = bullet_pattern.match(stripped)
        if not match:
            continue

        status = match.group(1)
        payload = match.group(2)
        buckets[status] = set(re.findall(r"`([^`]+)`", payload))
        context_by_status[status] = stripped

    return buckets, context_by_status


def _extract_project_maturity_status_mentions(text: str) -> list[tuple[str, str, str]]:
    mentions: list[tuple[str, str, str]] = []
    pattern = re.compile(r"`([a-z0-9_]+)`[^\n]*?\(`(done|in_progress|planned)`\)")
    for line in text.splitlines():
        stripped = line.strip()
        for cap_id, status in pattern.findall(stripped):
            mentions.append((cap_id, status, stripped))
    return mentions


def test_governance_docs_match_manifest_status_sources() -> None:
    manifest_status = _load_manifest_status_map()
    manifest_by_bucket: dict[str, set[str]] = {}
    for cap_id, status in manifest_status.items():
        manifest_by_bucket.setdefault(status, set()).add(cap_id)

    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    roadmap_buckets, roadmap_context = _extract_roadmap_status_buckets(roadmap_text)

    maturity_text = PROJECT_MATURITY_PATH.read_text(encoding="utf-8")

    mismatches: list[str] = []

    all_statuses = sorted(set(manifest_by_bucket) | set(roadmap_buckets))
    for status in all_statuses:
        manifest_caps = manifest_by_bucket.get(status, set())
        roadmap_caps = roadmap_buckets.get(status, set())

        for cap_id in sorted(manifest_caps - roadmap_caps):
            mismatches.append(
                "ROADMAP capability-status alignment mismatch: "
                f"capability_id='{cap_id}' expected bucket='{status}' from docs/dod_manifest.json, "
                f"but missing from roadmap bucket. Found line: "
                f"{roadmap_context.get(status, '<missing status bullet>')}"
            )

        for cap_id in sorted(roadmap_caps - manifest_caps):
            expected_status = manifest_status.get(cap_id, "<missing in manifest>")
            mismatches.append(
                "ROADMAP capability-status alignment mismatch: "
                f"capability_id='{cap_id}' found under bucket='{status}' in ROADMAP.md, "
                f"expected bucket='{expected_status}'. Found line: {roadmap_context.get(status, '<missing status bullet>')}"
            )

    done_count = sum(1 for status in manifest_status.values() if status == "done")
    in_progress_count = sum(1 for status in manifest_status.values() if status == "in_progress")
    planned_count = sum(1 for status in manifest_status.values() if status == "planned")
    count_patterns = {
        "done": (done_count, re.compile(r"^- \*\*Done:\*\*\s+(\d+)\s*$", re.MULTILINE)),
        "in_progress": (
            in_progress_count,
            re.compile(r"^- \*\*In progress:\*\*\s+(\d+)\s*$", re.MULTILINE),
        ),
        "planned": (planned_count, re.compile(r"^- \*\*Planned:\*\*\s+(\d+)\s*$", re.MULTILINE)),
    }
    for label, (expected, pattern) in count_patterns.items():
        match = pattern.search(maturity_text)
        if match and int(match.group(1)) != expected:
            mismatches.append(
                "Project maturity status-count mismatch: "
                f"capability_id='<aggregate:{label}>' expected '{expected}' from docs/dod_manifest.json, "
                f"found '{match.group(1)}' in docs/project_maturity_evaluation.md line: '{match.group(0)}'"
            )

    for cap_id, declared_status, context_line in _extract_project_maturity_status_mentions(maturity_text):
        expected_status = manifest_status.get(cap_id)
        if expected_status is None:
            mismatches.append(
                "Project maturity capability mention mismatch: "
                f"capability_id='{cap_id}' referenced with status='{declared_status}' but capability is not present "
                f"in docs/dod_manifest.json. Found text: '{context_line}'"
            )
            continue

        if declared_status != expected_status:
            mismatches.append(
                "Project maturity capability mention mismatch: "
                f"capability_id='{cap_id}' expected status='{expected_status}' from docs/dod_manifest.json, "
                f"found status='{declared_status}' in text: '{context_line}'"
            )

    bottleneck_match = re.search(r"Current bottleneck capability[^\n]*?\*\*`([a-z0-9_]+)`\*\*", maturity_text)
    if bottleneck_match:
        cap_id = bottleneck_match.group(1)
        expected_status = manifest_status.get(cap_id)
        if expected_status is None:
            mismatches.append(
                "Project maturity bottleneck mismatch: "
                f"capability_id='{cap_id}' declared as bottleneck but is not present in docs/dod_manifest.json."
            )
        elif expected_status == "done":
            mismatches.append(
                "Project maturity bottleneck mismatch: "
                f"capability_id='{cap_id}' declared as bottleneck but manifest status is 'done'."
            )

    assert not mismatches, "\n".join(mismatches)
