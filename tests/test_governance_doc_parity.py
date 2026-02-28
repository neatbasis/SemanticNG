from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
ROADMAP_PATH = ROOT / "ROADMAP.md"
SYSTEM_CONTRACT_MAP_PATH = ROOT / "docs" / "system_contract_map.md"
SPRINT_PLAN_PATH = ROOT / "docs" / "sprint_plan_5x.md"
PROJECT_MATURITY_PATH = ROOT / "docs" / "project_maturity_evaluation.md"
RELEASE_CHECKLIST_PATH = ROOT / "docs" / "release_checklist.md"
VALID_STATUSES = {"done", "in_progress", "planned"}
ALLOWED_DONE_MILESTONES = {"Now"}
ALLOWED_DONE_MATURITY = {"operational", "proven"}


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_manifest_status_map() -> dict[str, str]:
    manifest = _load_manifest()
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


def _extract_roadmap_status_buckets(roadmap_text: str) -> dict[str, set[str]]:
    buckets: dict[str, set[str]] = {status: set() for status in VALID_STATUSES}
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
        if status in buckets:
            buckets[status] = set(re.findall(r"`([^`]+)`", payload))

    return buckets


def _extract_contract_maturity_rows(text: str) -> dict[str, tuple[str, str]]:
    contract_rows: dict[str, tuple[str, str]] = {}
    current_milestone: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        milestone_match = re.match(r"## Milestone: (.+)$", stripped)
        if milestone_match:
            current_milestone = milestone_match.group(1).strip()
            continue

        if not current_milestone or not stripped.startswith("|"):
            continue
        if stripped.startswith("|---"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 7:
            continue
        if cells[0] == "Contract name":
            continue

        contract_name = cells[0]
        maturity = cells[6].strip("`").strip().lower()
        contract_rows[contract_name] = (current_milestone, maturity)

    return contract_rows


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


def _normalize_doc_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_dependency_map(text: str) -> dict[str, tuple[str, ...]]:
    dependencies: dict[str, tuple[str, ...]] = {}
    pattern = re.compile(r"^- `([a-z0-9_]+)` depends on: (.+)\.$")
    for line in text.splitlines():
        stripped = line.strip()
        match = pattern.match(stripped)
        if not match:
            continue
        capability_id = match.group(1)
        dependency_ids = tuple(sorted(re.findall(r"`([a-z0-9_]+)`", match.group(2))))
        dependencies[capability_id] = dependency_ids
    return dependencies


def _extract_maturity_changelog_capability_refs(contract_map_text: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for line in contract_map_text.splitlines():
        stripped = line.strip()
        if not re.match(r"^- \d{4}-\d{2}-\d{2} \([^)]+\): ", stripped):
            continue
        if "->" not in stripped:
            continue
        match = re.search(r"capability_id=([a-z0-9_]+)", stripped)
        refs.append((match.group(1) if match else "", stripped))
    return refs


def test_roadmap_capability_status_alignment_matches_manifest() -> None:
    manifest_status = _load_manifest_status_map()
    manifest_buckets = _manifest_status_buckets(manifest_status)

    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    roadmap_buckets = _extract_roadmap_status_buckets(roadmap_text)

    mismatches: list[str] = []

    for status in sorted(VALID_STATUSES):
        expected = manifest_buckets.get(status, set())
        found = roadmap_buckets.get(status, set())
        if expected != found:
            missing = sorted(expected - found)
            extra = sorted(found - expected)
            mismatches.append(
                "ROADMAP capability-status alignment mismatch: "
                f"status='{status}' expected_capability_ids={sorted(expected)} found_capability_ids={sorted(found)} "
                f"missing={missing} extra={extra}"
            )

    assert not mismatches, "\n".join(mismatches)


def test_done_capabilities_only_reference_allowed_contract_maturity_rows() -> None:
    manifest = _load_manifest()
    capabilities = manifest.get("capabilities", [])
    contract_map = _extract_contract_maturity_rows(SYSTEM_CONTRACT_MAP_PATH.read_text(encoding="utf-8"))

    mismatches: list[str] = []

    for capability in capabilities:
        if capability.get("status") != "done":
            continue

        capability_id = capability.get("id", "<missing capability id>")
        refs = capability.get("contract_map_refs", [])

        for ref in refs:
            row = contract_map.get(ref)
            if row is None:
                mismatches.append(
                    "System contract-map parity mismatch: "
                    f"done capability_id='{capability_id}' references contract='{ref}', "
                    "but no matching contract row exists in docs/system_contract_map.md"
                )
                continue

            milestone, maturity = row
            if milestone not in ALLOWED_DONE_MILESTONES or maturity not in ALLOWED_DONE_MATURITY:
                mismatches.append(
                    "System contract-map maturity mismatch: "
                    f"done capability_id='{capability_id}' references contract='{ref}' with "
                    f"milestone='{milestone}', maturity='{maturity}'. "
                    f"Allowed milestone={sorted(ALLOWED_DONE_MILESTONES)} "
                    f"allowed maturity={sorted(ALLOWED_DONE_MATURITY)}"
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
                f"status='{status}' expected_count='{expected}' found_count='{found_count}' "
                f"source='{source_line}'"
            )

    expected_done = expected_counts["done"]
    expected_total = len(manifest_status)
    for found_done, found_total, source_line in _extract_completion_ratio_claims(maturity_text):
        if (found_done, found_total) != (expected_done, expected_total):
            mismatches.append(
                "Project maturity completion-ratio claim mismatch: "
                f"expected_ratio='`{expected_done}/{expected_total}`' found_ratio='`{found_done}/{found_total}`' "
                f"source='{source_line}'"
            )

    for cap_id, declared_status, source_line in _extract_project_maturity_status_mentions(maturity_text):
        expected_status = manifest_status.get(cap_id)
        if expected_status is None:
            mismatches.append(
                "Project maturity capability-status claim mismatch: "
                f"capability_id='{cap_id}' declared_status='{declared_status}' but capability_id missing from manifest. "
                f"Known_manifest_capability_ids={sorted(manifest_status)} source='{source_line}'"
            )
            continue

        if declared_status != expected_status:
            mismatches.append(
                "Project maturity capability-status claim mismatch: "
                f"capability_id='{cap_id}' expected_status='{expected_status}' found_status='{declared_status}' "
                f"source='{source_line}'"
            )

    no_in_progress_claimed = bool(re.search(r"no\*\* `in_progress` capabilities", maturity_text))
    if no_in_progress_claimed and expected_counts["in_progress"] != 0:
        mismatches.append(
            "Project maturity in-progress claim mismatch: "
            "document claims no in_progress capabilities, "
            f"but manifest in_progress_capability_ids="
            f"{sorted([cap_id for cap_id, st in manifest_status.items() if st == 'in_progress'])}"
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
        f"capability_id='{capability_id}' missing from manifest. "
        f"Known_manifest_capability_ids={sorted(manifest_status)}"
    )

    assert status != "done", (
        "Project maturity bottleneck claim mismatch: "
        f"capability_id='{capability_id}' declared_bottleneck_status='done'. "
        f"Expected bottleneck in non-done set={sorted([k for k, v in manifest_status.items() if v != 'done'])}"
    )


def test_release_checklist_has_no_duplicate_headers_or_checklist_labels() -> None:
    checklist_text = RELEASE_CHECKLIST_PATH.read_text(encoding="utf-8")

    heading_pattern = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
    checklist_pattern = re.compile(r"^- \[[ xX]\]\s+\*\*(.+?)\*\*:")

    heading_occurrences: dict[str, list[int]] = {}
    checklist_occurrences: dict[str, list[int]] = {}

    for line_number, line in enumerate(checklist_text.splitlines(), start=1):
        stripped = line.strip()

        heading_match = heading_pattern.match(stripped)
        if heading_match:
            heading = _normalize_doc_label(heading_match.group(2))
            heading_occurrences.setdefault(heading, []).append(line_number)

        checklist_match = checklist_pattern.match(stripped)
        if checklist_match:
            label = _normalize_doc_label(checklist_match.group(1))
            checklist_occurrences.setdefault(label, []).append(line_number)

    duplicate_headings = {
        label: lines for label, lines in heading_occurrences.items() if len(lines) > 1
    }
    duplicate_checklist_labels = {
        label: lines for label, lines in checklist_occurrences.items() if len(lines) > 1
    }

    assert not duplicate_headings and not duplicate_checklist_labels, (
        "Release checklist duplicate labels detected: "
        f"duplicate_headings={duplicate_headings} "
        f"duplicate_checklist_labels={duplicate_checklist_labels}"
    )


def test_planned_or_in_progress_capabilities_are_present_in_sprint_plan() -> None:
    manifest_status = _load_manifest_status_map()
    sprint_plan_text = SPRINT_PLAN_PATH.read_text(encoding="utf-8")

    active_capabilities = sorted(
        cap_id for cap_id, status in manifest_status.items() if status in {"planned", "in_progress"}
    )
    mentioned_capability_ids = set(re.findall(r"`([a-z0-9_]+)`", sprint_plan_text))

    missing = [cap_id for cap_id in active_capabilities if cap_id not in mentioned_capability_ids]

    assert not missing, (
        "Sprint plan parity mismatch: every planned/in_progress capability must appear in docs/sprint_plan_5x.md. "
        f"missing={missing}"
    )


def test_contract_map_maturity_transitions_reference_manifest_capability_and_evidence() -> None:
    manifest_status = _load_manifest_status_map()
    contract_map_text = SYSTEM_CONTRACT_MAP_PATH.read_text(encoding="utf-8")

    mismatches: list[str] = []
    for capability_id, source_line in _extract_maturity_changelog_capability_refs(contract_map_text):
        if not capability_id:
            mismatches.append(
                "System contract-map changelog mismatch: maturity transition entry missing capability_id=... "
                f"source='{source_line}'"
            )
            continue
        if capability_id not in manifest_status:
            mismatches.append(
                "System contract-map changelog mismatch: maturity transition references unknown capability_id. "
                f"capability_id='{capability_id}' source='{source_line}'"
            )
        if "https://" not in source_line and "http://" not in source_line:
            mismatches.append(
                "System contract-map changelog mismatch: maturity transition entry missing evidence URL. "
                f"capability_id='{capability_id}' source='{source_line}'"
            )

    assert not mismatches, "\n".join(mismatches)


def test_dependency_statements_are_consistent_across_roadmap_and_sprint_plan() -> None:
    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    sprint_plan_text = SPRINT_PLAN_PATH.read_text(encoding="utf-8")

    roadmap_dependencies = _extract_dependency_map(roadmap_text)
    sprint_dependencies = _extract_dependency_map(sprint_plan_text)

    shared_capabilities = sorted(set(roadmap_dependencies) & set(sprint_dependencies))
    mismatches: list[str] = []
    for capability_id in shared_capabilities:
        if roadmap_dependencies[capability_id] != sprint_dependencies[capability_id]:
            mismatches.append(
                "Dependency statement conflict across docs: "
                f"capability_id='{capability_id}' roadmap={roadmap_dependencies[capability_id]} "
                f"sprint_plan={sprint_dependencies[capability_id]}"
            )

    assert shared_capabilities, (
        "Dependency parity check requires canonical dependency statements in both ROADMAP.md and "
        "docs/sprint_plan_5x.md (use '- `<capability_id>` depends on: `<dependency_id>`, ... .')."
    )
    assert not mismatches, "\n".join(mismatches)
