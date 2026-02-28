from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
ROADMAP_PATH = ROOT / "ROADMAP.md"
PROJECT_MATURITY_PATH = ROOT / "docs" / "project_maturity_evaluation.md"
VALID_STATUSES = {"done", "in_progress", "planned"}


def _load_manifest_status_map() -> dict[str, str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    capabilities = manifest.get("capabilities", [])
    return {
        cap["id"]: cap["status"]
        for cap in capabilities
        if isinstance(cap.get("id"), str)
        and isinstance(cap.get("status"), str)
        and cap["status"] in VALID_STATUSES
    }


def _manifest_status_buckets(manifest_status: dict[str, str]) -> dict[str, set[str]]:
    buckets: dict[str, set[str]] = {status: set() for status in VALID_STATUSES}
    for capability_id, status in manifest_status.items():
        buckets[status].add(capability_id)
    return buckets


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


def _extract_hardcoded_count_claims(text: str) -> list[tuple[str, int, str]]:
    claims: list[tuple[str, int, str]] = []
    patterns = {
        "done": [
            re.compile(r"^- \*\*Done:\*\*\s+(\d+)\s*$"),
            re.compile(r"\((\d+) done / \d+ in_progress / \d+ planned\)"),
        ],
        "in_progress": [
            re.compile(r"^- \*\*In progress:\*\*\s+(\d+)\s*$"),
            re.compile(r"\(\d+ done / (\d+) in_progress / \d+ planned\)"),
        ],
        "planned": [
            re.compile(r"^- \*\*Planned:\*\*\s+(\d+)\s*$"),
            re.compile(r"\(\d+ done / \d+ in_progress / (\d+) planned\)"),
        ],
    }
    for line in text.splitlines():
        stripped = line.strip()
        for status, regexes in patterns.items():
            for regex in regexes:
                match = regex.search(stripped)
                if match:
                    claims.append((status, int(match.group(1)), stripped))
    return claims


def _extract_completion_ratio_claims(text: str) -> list[tuple[int, int, str]]:
    claims: list[tuple[int, int, str]] = []
    ratio_pattern = re.compile(r"`(\d+)/(\d+)`")
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if "completion ratio" not in lowered and "accounting" not in lowered:
            continue

        match = ratio_pattern.search(stripped)
        if match:
            claims.append((int(match.group(1)), int(match.group(2)), stripped))

    return claims


def test_roadmap_capability_status_alignment_matches_manifest() -> None:
    manifest_status = _load_manifest_status_map()
    manifest_buckets = _manifest_status_buckets(manifest_status)

    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    roadmap_buckets, roadmap_context = _extract_roadmap_status_buckets(roadmap_text)

    mismatches: list[str] = []

    all_statuses = sorted(set(manifest_buckets) | set(roadmap_buckets))
    for status in all_statuses:
        manifest_caps = manifest_buckets.get(status, set())
        roadmap_caps = roadmap_buckets.get(status, set())

        for capability_id in sorted(manifest_caps - roadmap_caps):
            mismatches.append(
                "ROADMAP capability-status alignment mismatch: "
                f"expected capability_id='{capability_id}' in status bucket='{status}' based on docs/dod_manifest.json, "
                f"but ROADMAP bucket is missing it. Found bucket line: {roadmap_context.get(status, '<missing status bucket line>')}"
            )

        for capability_id in sorted(roadmap_caps - manifest_caps):
            expected_status = manifest_status.get(capability_id, "<missing in manifest>")
            mismatches.append(
                "ROADMAP capability-status alignment mismatch: "
                f"found capability_id='{capability_id}' in roadmap status bucket='{status}', "
                f"expected status bucket='{expected_status}' from docs/dod_manifest.json. "
                f"Found bucket line: {roadmap_context.get(status, '<missing status bucket line>')}"
            )

    assert not mismatches, "\n".join(mismatches)


def test_project_maturity_status_claims_do_not_contradict_manifest() -> None:
    manifest_status = _load_manifest_status_map()
    maturity_text = PROJECT_MATURITY_PATH.read_text(encoding="utf-8")

    expected_counts = {
        "done": sum(status == "done" for status in manifest_status.values()),
        "in_progress": sum(status == "in_progress" for status in manifest_status.values()),
        "planned": sum(status == "planned" for status in manifest_status.values()),
    }

    mismatches: list[str] = []

    for status, found_count, source_line in _extract_hardcoded_count_claims(maturity_text):
        expected = expected_counts[status]
        if found_count != expected:
            mismatches.append(
                "Project maturity status-count claim mismatch: "
                f"status='{status}' expected_count='{expected}' from docs/dod_manifest.json, "
                f"found_count='{found_count}' in line: '{source_line}'"
            )

    expected_done = expected_counts["done"]
    expected_total = len(manifest_status)
    for found_done, found_total, source_line in _extract_completion_ratio_claims(maturity_text):
        if (found_done, found_total) != (expected_done, expected_total):
            mismatches.append(
                "Project maturity completion-ratio claim mismatch: "
                f"expected_ratio='`{expected_done}/{expected_total}`' from docs/dod_manifest.json, "
                f"found_ratio='`{found_done}/{found_total}`' in line: '{source_line}'"
            )

    for cap_id, declared_status, source_line in _extract_project_maturity_status_mentions(maturity_text):
        expected_status = manifest_status.get(cap_id)
        if expected_status is None:
            mismatches.append(
                "Project maturity capability-status claim mismatch: "
                f"capability_id='{cap_id}' is referenced with status='{declared_status}', "
                "but the capability_id does not exist in docs/dod_manifest.json. "
                f"Source line: '{source_line}'"
            )
            continue

        if declared_status != expected_status:
            mismatches.append(
                "Project maturity capability-status claim mismatch: "
                f"capability_id='{cap_id}' expected_status='{expected_status}' from docs/dod_manifest.json, "
                f"found_status='{declared_status}' in line: '{source_line}'"
            )

    assert not mismatches, "\n".join(mismatches)


def test_project_maturity_bottleneck_claim_is_non_done_manifest_capability() -> None:
    manifest_status = _load_manifest_status_map()
    maturity_text = PROJECT_MATURITY_PATH.read_text(encoding="utf-8")

    match = re.search(r"Current bottleneck capability[^\n]*?\*\*`([a-z0-9_]+)`\*\*", maturity_text)
    assert match is not None, (
        "Project maturity bottleneck claim missing: expected a line like "
        "'Current bottleneck capability ... **`<capability_id>`**' in docs/project_maturity_evaluation.md"
    )

    capability_id = match.group(1)
    status = manifest_status.get(capability_id)

    assert status is not None, (
        "Project maturity bottleneck claim mismatch: "
        f"capability_id='{capability_id}' was declared as the bottleneck in docs/project_maturity_evaluation.md, "
        "but this capability_id is missing from docs/dod_manifest.json"
    )

    assert status != "done", (
        "Project maturity bottleneck claim mismatch: "
        f"capability_id='{capability_id}' is marked as current bottleneck, "
        "but docs/dod_manifest.json marks it as status='done'. "
        "Update either the bottleneck claim or the manifest status."
    )
