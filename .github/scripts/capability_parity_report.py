import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MANIFEST_PATH = Path("docs/dod_manifest.json")
ROADMAP_PATH = Path("ROADMAP.md")
CONTRACT_MAP_PATH = Path("docs/system_contract_map.md")
PROJECT_MATURITY_PATH = Path("docs/project_maturity_evaluation.md")
DEFAULT_OUTPUT_PATH = Path("artifacts/capability_parity_report.txt")


@dataclass(frozen=True)
class RoadmapItem:
    section: str
    title: str
    pytest_commands: tuple[str, ...]


@dataclass(frozen=True)
class ContractRow:
    milestone: str
    name: str
    test_refs: tuple[str, ...]
    maturity: str


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _tokenize_title(title: str) -> set[str]:
    stop_words = {
        "and",
        "the",
        "for",
        "with",
        "without",
        "toward",
        "towards",
        "all",
        "path",
        "contract",
        "contracts",
        "baseline",
    }
    tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    return {token for token in tokens if len(token) > 2 and token not in stop_words}


def _title_similarity(left: str, right: str) -> float:
    if _normalize_title(left) == _normalize_title(right):
        return 1.0
    l_tokens = _tokenize_title(left)
    r_tokens = _tokenize_title(right)
    if not l_tokens or not r_tokens:
        return 0.0
    intersection = len(l_tokens & r_tokens)
    union = len(l_tokens | r_tokens)
    if union == 0:
        return 0.0
    return intersection / union


def _extract_test_files_from_pytest_command(command: str) -> set[str]:
    return {
        token
        for token in command.split()
        if token.endswith(".py") and token.startswith("tests/")
    }


def _extract_roadmap_items(text: str) -> list[RoadmapItem]:
    items: list[RoadmapItem] = []
    current_section: str | None = None
    current_title: str | None = None
    current_commands: list[str] = []

    def _flush() -> None:
        nonlocal current_title, current_commands
        if current_section and current_title:
            items.append(
                RoadmapItem(
                    section=current_section,
                    title=current_title,
                    pytest_commands=tuple(current_commands),
                )
            )
        current_title = None
        current_commands = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        section_match = re.match(r"^##\s+(Now|Next|Later)\b", line)
        if section_match:
            _flush()
            current_section = section_match.group(1)
            continue

        title_match = re.match(r"^###\s+\d+\)\s+(.+)$", line)
        if title_match:
            _flush()
            current_title = title_match.group(1).strip()
            continue

        for command in re.findall(r"`(pytest[^`]*)`", line):
            current_commands.append(command.strip())

    _flush()
    return items


def _parse_markdown_table_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().split("|")[1:-1]]


def _extract_contract_rows(text: str) -> list[ContractRow]:
    rows: list[ContractRow] = []
    current_milestone: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        milestone_match = re.match(r"^##\s+Milestone:\s+(.+)$", line)
        if milestone_match:
            current_milestone = milestone_match.group(1).strip()
            continue

        if not current_milestone or not line.startswith("|"):
            continue

        cells = _parse_markdown_table_line(line)
        if len(cells) < 7:
            continue
        if cells[0] == "Contract name" or set(cells[0]) == {"-"}:
            continue

        test_refs = tuple(sorted(set(re.findall(r"tests/[^`,\s]+\.py", cells[5]))))
        rows.append(ContractRow(current_milestone, cells[0], test_refs, cells[6]))
    return rows


def _manifest_capabilities() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("capabilities", [])


def _manifest_status_index(capabilities: Iterable[dict]) -> dict[str, set[str]]:
    by_status: dict[str, set[str]] = {}
    for capability in capabilities:
        status = capability.get("status")
        cap_id = capability.get("id")
        if not isinstance(status, str) or not isinstance(cap_id, str):
            continue
        by_status.setdefault(status, set()).add(cap_id)
    return by_status


def _extract_roadmap_status_alignment(text: str) -> dict[str, set[str]]:
    alignment: dict[str, set[str]] = {}
    in_alignment_section = False
    bullet_pattern = re.compile(r"^- `([^`]+)`: (.+)\.$")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## Capability status alignment"):
            in_alignment_section = True
            continue
        if in_alignment_section and line.startswith("## "):
            break
        if not in_alignment_section:
            continue

        match = bullet_pattern.match(line)
        if not match:
            continue

        status = match.group(1)
        capability_ids = {cap_id for cap_id in re.findall(r"`([^`]+)`", match.group(2))}
        alignment[status] = capability_ids

    return alignment


def roadmap_alignment_mismatches(capabilities: list[dict], roadmap_text: str) -> list[str]:
    mismatches: list[str] = []
    manifest_by_status = _manifest_status_index(capabilities)
    roadmap_alignment = _extract_roadmap_status_alignment(roadmap_text)

    for status in sorted(set(manifest_by_status) | set(roadmap_alignment)):
        manifest_caps = manifest_by_status.get(status, set())
        roadmap_caps = roadmap_alignment.get(status, set())
        missing = sorted(manifest_caps - roadmap_caps)
        extras = sorted(roadmap_caps - manifest_caps)
        if missing:
            mismatches.append(
                f"ROADMAP status alignment missing capabilities under '{status}': {', '.join(missing)}."
            )
        if extras:
            mismatches.append(
                f"ROADMAP status alignment includes capabilities not in manifest under '{status}': {', '.join(extras)}."
            )

    return mismatches


def _extract_changelog_lines(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    capture = False
    entries: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        if line.strip() == "### Changelog":
            capture = True
            continue
        if capture and re.match(r"^###\s+", line):
            break
        if capture and line.strip().startswith("- "):
            entries.append(line.strip())
    return entries


def contract_maturity_evidence_mismatches(contract_map_text: str) -> list[str]:
    maturity_rank = {"in_progress": 0, "prototype": 1, "operational": 2, "proven": 3}
    mismatches: list[str] = []
    contract_rows = {row.name: row for row in _extract_contract_rows(contract_map_text)}
    transition_pattern = re.compile(r"-\s+\d{4}-\d{2}-\d{2}\s+\([^)]+\):\s+(.+?)\s+(\w+)\s+->\s+(\w+)")

    for line in _extract_changelog_lines(contract_map_text):
        if "->" not in line:
            continue

        if "https://" not in line:
            mismatches.append(f"Contract map changelog transition missing https evidence URL: {line}")

        transition_match = transition_pattern.match(line)
        if not transition_match:
            mismatches.append(
                "Contract map changelog transition does not match required format '- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; ...'. "
                f"Line: {line}"
            )
            continue

        contract_name, before, after = transition_match.groups()
        row = contract_rows.get(contract_name)
        if row is None:
            mismatches.append(f"Contract map changelog references unknown contract '{contract_name}'.")
            continue

        before_rank = maturity_rank.get(before)
        after_rank = maturity_rank.get(after)
        current_rank = maturity_rank.get(row.maturity)
        if before_rank is None or after_rank is None or current_rank is None:
            mismatches.append(
                f"Contract map changelog contains unknown maturity values for '{contract_name}': {before} -> {after}."
            )
            continue

        if before_rank >= after_rank:
            mismatches.append(
                f"Contract map changelog transition for '{contract_name}' must be a forward maturity move: {before} -> {after}."
            )
        if after_rank > current_rank:
            mismatches.append(
                f"Contract map changelog transition for '{contract_name}' overshoots current maturity '{row.maturity}': {before} -> {after}."
            )

    return mismatches


def project_maturity_mismatches(capabilities: list[dict], project_maturity_text: str) -> list[str]:
    mismatches: list[str] = []
    status_counts = {
        "done": sum(1 for cap in capabilities if cap.get("status") == "done"),
        "in_progress": sum(1 for cap in capabilities if cap.get("status") == "in_progress"),
        "planned": sum(1 for cap in capabilities if cap.get("status") == "planned"),
    }
    total = len(capabilities)

    bullet_patterns = {
        "done": re.compile(r"^-\s+\*\*Done:\*\*\s+(\d+)\s*$", re.MULTILINE),
        "in_progress": re.compile(r"^-\s+\*\*In progress:\*\*\s+(\d+)\s*$", re.MULTILINE),
        "planned": re.compile(r"^-\s+\*\*Planned:\*\*\s+(\d+)\s*$", re.MULTILINE),
    }
    for status, pattern in bullet_patterns.items():
        match = pattern.search(project_maturity_text)
        if match and int(match.group(1)) != status_counts[status]:
            mismatches.append(
                f"Project maturity bullet for {status} is {match.group(1)} but manifest count is {status_counts[status]}."
            )

    ratio_match = re.search(r"\(`(\d+)/(\d+)`\)", project_maturity_text)
    if ratio_match:
        done_value = int(ratio_match.group(1))
        total_value = int(ratio_match.group(2))
        if done_value != status_counts["done"] or total_value != total:
            mismatches.append(
                f"Project maturity completion ratio reports {done_value}/{total_value} but manifest is {status_counts['done']}/{total}."
            )

    manifest_by_id = {
        capability.get("id"): capability.get("status")
        for capability in capabilities
        if isinstance(capability.get("id"), str)
    }
    for cap_id, status in re.findall(
        r"`([a-z0-9_]+)`[^\n]*?\(`(done|in_progress|planned)`\)", project_maturity_text
    ):
        manifest_status = manifest_by_id.get(cap_id)
        if manifest_status and manifest_status != status:
            mismatches.append(
                f"Project maturity status mention for '{cap_id}' says '{status}' but manifest status is '{manifest_status}'."
            )

    if "only capability currently marked `in_progress`" in project_maturity_text:
        in_progress_caps = sorted(cap_id for cap_id, status in manifest_by_id.items() if status == "in_progress")
        if len(in_progress_caps) != 1:
            mismatches.append(
                "Project maturity text claims there is only one in_progress capability, but manifest currently has "
                f"{len(in_progress_caps)} ({', '.join(in_progress_caps) if in_progress_caps else 'none'})."
            )

    return mismatches


def _capability_test_files(capability: dict) -> set[str]:
    files: set[str] = set()
    for command in capability.get("pytest_commands", []):
        files.update(_extract_test_files_from_pytest_command(command))
    return files


def _is_contract_exempt(capability: dict) -> bool:
    exemption_reason = capability.get("contract_map_exemption")
    exemptions = capability.get("contract_map_exemptions")
    if isinstance(exemption_reason, str) and exemption_reason.strip():
        return True
    if isinstance(exemptions, list) and any(isinstance(item, str) and item.strip() for item in exemptions):
        return True
    return False


def _match_titles(roadmap_titles: Iterable[str], manifest_titles: Iterable[str]) -> dict[str, str]:
    pairs: list[tuple[float, str, str]] = []
    for road_title in roadmap_titles:
        for man_title in manifest_titles:
            score = _title_similarity(road_title, man_title)
            if score > 0:
                pairs.append((score, road_title, man_title))

    matched: dict[str, str] = {}
    used_manifest: set[str] = set()
    for score, road_title, man_title in sorted(pairs, key=lambda item: (-item[0], item[1], item[2])):
        if score < 0.3:
            break
        if road_title in matched or man_title in used_manifest:
            continue
        matched[road_title] = man_title
        used_manifest.add(man_title)
    return matched


def build_report() -> str:
    capabilities = _manifest_capabilities()
    roadmap_items = _extract_roadmap_items(ROADMAP_PATH.read_text(encoding="utf-8"))
    contract_map_text = CONTRACT_MAP_PATH.read_text(encoding="utf-8")
    contract_rows = _extract_contract_rows(contract_map_text)
    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    project_maturity_text = PROJECT_MATURITY_PATH.read_text(encoding="utf-8")

    roadmap_titles = sorted(item.title for item in roadmap_items)
    manifest_titles = sorted(cap.get("title", "") for cap in capabilities)
    matches = _match_titles(roadmap_titles, manifest_titles)
    matched_manifest_titles = set(matches.values())

    roadmap_missing_in_manifest = sorted(title for title in roadmap_titles if title not in matches)
    manifest_missing_in_roadmap = sorted(title for title in manifest_titles if title not in matched_manifest_titles)

    contract_names = {row.name for row in contract_rows}
    manifest_without_contract_match: list[str] = []
    exempt_capabilities: list[str] = []
    for capability in sorted(capabilities, key=lambda c: c.get("id", "")):
        refs = capability.get("contract_map_refs") or []
        if not refs and _is_contract_exempt(capability):
            exempt_capabilities.append(f"{capability.get('id')} ({capability.get('title')})")
            continue

        has_match = any(ref in contract_names for ref in refs if isinstance(ref, str))
        if not has_match:
            manifest_without_contract_match.append(f"{capability.get('id')} ({capability.get('title')})")

    roadmap_by_title = {item.title: item for item in roadmap_items}
    in_progress_done_candidates: list[str] = []
    for capability in sorted(capabilities, key=lambda c: c.get("id", "")):
        if capability.get("status") != "in_progress":
            continue
        matched_roadmap_title = next(
            (road_title for road_title, man_title in matches.items() if man_title == capability.get("title")),
            None,
        )
        if not matched_roadmap_title:
            continue

        match = roadmap_by_title[matched_roadmap_title]
        manifest_commands = set(capability.get("pytest_commands") or [])
        roadmap_commands = set(match.pytest_commands)
        if manifest_commands and manifest_commands.issubset(roadmap_commands):
            in_progress_done_candidates.append(f"{capability.get('id')} ({capability.get('title')})")

    prototype_operational_candidates: list[str] = []
    for row in sorted(contract_rows, key=lambda r: r.name):
        if row.maturity != "prototype":
            continue
        referencing_caps = [cap for cap in capabilities if row.name in (cap.get("contract_map_refs") or [])]
        if not referencing_caps or not row.test_refs:
            continue

        all_cap_test_files = set().union(*(_capability_test_files(cap) for cap in referencing_caps))
        if set(row.test_refs).issubset(all_cap_test_files):
            cap_ids = ", ".join(sorted(cap.get("id", "") for cap in referencing_caps))
            prototype_operational_candidates.append(f"{row.name} (refs: {cap_ids})")

    roadmap_status_mismatches = roadmap_alignment_mismatches(capabilities, roadmap_text)
    contract_maturity_mismatches = contract_maturity_evidence_mismatches(contract_map_text)
    project_maturity_status_mismatches = project_maturity_mismatches(capabilities, project_maturity_text)

    lines = [
        "Capability Parity Report",
        "========================",
        f"Manifest path: {MANIFEST_PATH}",
        f"Roadmap path: {ROADMAP_PATH}",
        f"Contract map path: {CONTRACT_MAP_PATH}",
        "",
        "1) ROADMAP items missing in manifest",
    ]
    lines.extend(f"- {item}" for item in roadmap_missing_in_manifest)
    if not roadmap_missing_in_manifest:
        lines.append("- none")

    lines.extend(["", "2) Manifest items with no roadmap match"])
    lines.extend(f"- {item}" for item in manifest_missing_in_roadmap)
    if not manifest_missing_in_roadmap:
        lines.append("- none")

    lines.extend(["", "3) Manifest capabilities with no matching contract-map row"])
    lines.extend(f"- {item}" for item in manifest_without_contract_match)
    if not manifest_without_contract_match:
        lines.append("- none")

    lines.extend(["", "3a) Explicitly exempted manifest capabilities"])
    lines.extend(f"- {item}" for item in exempt_capabilities)
    if not exempt_capabilities:
        lines.append("- none")

    lines.extend([
        "",
        "4) Candidate promotions from listed pytest command coverage",
        "4a) in_progress -> done candidates",
    ])
    lines.extend(f"- {item}" for item in in_progress_done_candidates)
    if not in_progress_done_candidates:
        lines.append("- none")

    lines.append("4b) prototype -> operational candidates")
    lines.extend(f"- {item}" for item in prototype_operational_candidates)
    if not prototype_operational_candidates:
        lines.append("- none")

    lines.extend(["", "5) Deterministic parity checks (manifest as canonical source)"])
    lines.append("5a) ROADMAP capability-status alignment mismatches")
    lines.extend(f"- {item}" for item in roadmap_status_mismatches)
    if not roadmap_status_mismatches:
        lines.append("- none")

    lines.append("5b) Contract-map maturity transition evidence mismatches")
    lines.extend(f"- {item}" for item in contract_maturity_mismatches)
    if not contract_maturity_mismatches:
        lines.append("- none")

    lines.append("5c) Project maturity document status mismatches")
    lines.extend(f"- {item}" for item in project_maturity_status_mismatches)
    if not project_maturity_status_mismatches:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def deterministic_parity_mismatches() -> list[str]:
    capabilities = _manifest_capabilities()
    roadmap_text = ROADMAP_PATH.read_text(encoding="utf-8")
    contract_map_text = CONTRACT_MAP_PATH.read_text(encoding="utf-8")
    project_maturity_text = PROJECT_MATURITY_PATH.read_text(encoding="utf-8")

    return [
        *roadmap_alignment_mismatches(capabilities, roadmap_text),
        *contract_maturity_evidence_mismatches(contract_map_text),
        *project_maturity_mismatches(capabilities, project_maturity_text),
    ]


def main() -> int:
    report = build_report()
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"Wrote report to {DEFAULT_OUTPUT_PATH}")

    if deterministic_parity_mismatches():
        print("Deterministic capability parity checks failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
