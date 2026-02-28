import json
import os
import re
import subprocess
import sys
from pathlib import Path


MISSING_PR_EVIDENCE_MARKER = "MILESTONE_VALIDATION_ERROR=MISSING_PR_EVIDENCE"
MISSING_PR_HEADING_MARKER = "MILESTONE_VALIDATION_ERROR=MISSING_PR_TEMPLATE_HEADING"
MISSING_PR_FIELD_MARKER = "MILESTONE_VALIDATION_ERROR=MISSING_PR_TEMPLATE_FIELD"
MISSING_ROLLBACK_PLAN_MARKER = "MILESTONE_VALIDATION_ERROR=MISSING_ROLLBACK_PLAN"
MISSING_GOVERNANCE_HANDOFF_MARKER = "MILESTONE_VALIDATION_ERROR=MISSING_GOVERNANCE_HANDOFF_FIELDS"


def _load_manifest(rev: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{rev}:docs/dod_manifest.json"], text=True)
    return json.loads(raw)


def _changed_files(base_sha: str, head_sha: str) -> list[str]:
    out = subprocess.check_output(["git", "diff", "--name-only", base_sha, head_sha], text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _status_transitions(base_manifest: dict, head_manifest: dict) -> dict[str, tuple[str, str]]:
    base = {cap["id"]: cap for cap in base_manifest.get("capabilities", [])}
    transitions: dict[str, tuple[str, str]] = {}
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id")
        if cap_id not in base:
            continue
        from_status = base[cap_id].get("status")
        to_status = capability.get("status")
        if from_status != to_status:
            transitions[cap_id] = (from_status, to_status)
    return transitions


def _extract_roadmap_status_alignment(roadmap_text: str) -> dict[str, set[str]]:
    status_alignment: dict[str, set[str]] = {}
    in_alignment_section = False
    bullet_pattern = re.compile(r"^- `([^`]+)`: (.+)\.$")

    for raw_line in roadmap_text.splitlines():
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
        status_alignment[status] = capability_ids

    return status_alignment


def _roadmap_status_transition_mismatches(
    status_transitions: dict[str, tuple[str, str]], roadmap_text: str
) -> list[str]:
    status_alignment = _extract_roadmap_status_alignment(roadmap_text)
    mismatches: list[str] = []

    for cap_id, (_, to_status) in sorted(status_transitions.items()):
        status_caps = status_alignment.get(to_status, set())
        if cap_id not in status_caps:
            mismatches.append(
                f"{cap_id}: transitioned to status '{to_status}' but ROADMAP.md capability status alignment is missing this capability under '{to_status}'."
            )

    return mismatches


def _extract_maturity_map(markdown_text: str) -> dict[str, str]:
    maturity: dict[str, str] = {}
    for line in markdown_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
        if len(cells) < 7:
            continue
        if cells[0] == "Contract name" or set(cells[0]) == {"-"}:
            continue
        maturity[cells[0]] = cells[-1]
    return maturity


def _extract_contract_names_by_milestone(markdown_text: str) -> dict[str, list[str]]:
    contracts: dict[str, list[str]] = {}
    current_milestone: str | None = None
    for line in markdown_text.splitlines():
        header = re.match(r"^## Milestone: (.+)$", line.strip())
        if header:
            current_milestone = header.group(1).strip()
            contracts.setdefault(current_milestone, [])
            continue
        if not current_milestone or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
        if len(cells) < 7:
            continue
        if cells[0] == "Contract name" or set(cells[0]) == {"-"}:
            continue
        contracts[current_milestone].append(cells[0])
    return contracts


def _extract_contract_rows_by_name(markdown_text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    current_milestone: str | None = None
    for line in markdown_text.splitlines():
        header = re.match(r"^## Milestone: (.+)$", line.strip())
        if header:
            current_milestone = header.group(1).strip()
            continue
        if not current_milestone or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
        if len(cells) < 7:
            continue
        if cells[0] == "Contract name" or set(cells[0]) == {"-"}:
            continue
        rows[cells[0]] = {"milestone": current_milestone, "maturity": cells[-1]}
    return rows


def _maturity_transitions(base_text: str, head_text: str) -> list[tuple[str, str, str]]:
    base_map = _extract_maturity_map(base_text)
    head_map = _extract_maturity_map(head_text)
    updates: list[tuple[str, str, str]] = []
    for contract_name, after in head_map.items():
        before = base_map.get(contract_name)
        if before is None:
            continue
        if before != after:
            updates.append((contract_name, before, after))
    return updates


def _added_changelog_entries(base_sha: str, head_sha: str) -> list[str]:
    diff = subprocess.check_output(
        ["git", "diff", "--unified=0", base_sha, head_sha, "--", "docs/system_contract_map.md"],
        text=True,
    )
    entries = []
    for line in diff.splitlines():
        if re.match(r"^\+- \d{4}-\d{2}-\d{2} \([^)]+\): ", line):
            entries.append(line[1:])
    return entries


def _extract_changelog_lines(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    capture = False
    entries: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        if line.strip() == "### Changelog":
            capture = True
            continue
        if capture and re.match(r"^###\s+", line.strip()):
            break
        if capture and line.startswith("- "):
            entries.append(line)
    return entries


def _done_capability_sync_mismatches(
    head_manifest: dict, contract_rows_by_name: dict[str, dict[str, str]]
) -> list[str]:
    mismatches: list[str] = []
    for capability in head_manifest.get("capabilities", []):
        if capability.get("status") != "done":
            continue
        cap_id = capability.get("id", "<unknown>")
        roadmap_section = capability.get("roadmap_section")
        if roadmap_section != "Now":
            mismatches.append(
                f"{cap_id}: done capabilities must use roadmap_section='Now' (found '{roadmap_section}')."
            )

        for contract_name in capability.get("contract_map_refs", []):
            row = contract_rows_by_name.get(contract_name)
            if not row:
                continue
            milestone = row["milestone"]
            maturity = row["maturity"]
            if milestone != "Now":
                mismatches.append(
                    f"{cap_id} -> {contract_name}: done capabilities must reference contracts in Milestone: Now (found '{milestone}')."
                )
            if maturity in {"prototype", "in_progress"}:
                mismatches.append(
                    f"{cap_id} -> {contract_name}: done capabilities require operational/proven maturity (found '{maturity}')."
                )
    return mismatches


def _milestone_policy_mismatches(
    head_manifest: dict, contract_rows_by_name: dict[str, dict[str, str]]
) -> list[str]:
    order = {"Now": 0, "Next": 1, "Later": 2}
    mismatches: list[str] = []
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id", "<unknown>")
        cap_section = capability.get("roadmap_section")
        cap_rank = order.get(cap_section)
        if cap_rank is None:
            continue
        for contract_name in capability.get("contract_map_refs", []):
            row = contract_rows_by_name.get(contract_name)
            if not row:
                continue
            contract_milestone = row["milestone"]
            contract_rank = order.get(contract_milestone)
            if contract_rank is None:
                continue
            if contract_rank > cap_rank:
                mismatches.append(
                    f"{cap_id} ({cap_section}) -> {contract_name} ({contract_milestone}): capabilities cannot depend on later-milestone contracts."
                )
    return mismatches


def _maturity_promotion_evidence_mismatches(
    maturity_updates: list[tuple[str, str, str]], changelog_lines: list[str]
) -> list[str]:
    promotion_mismatches: list[str] = []
    evidence_pattern = re.compile(r"https?://\S+")
    for contract_name, before, after in maturity_updates:
        if before == after:
            continue
        if before == "prototype" and after in {"operational", "proven"}:
            is_promotion = True
        elif before == "operational" and after == "proven":
            is_promotion = True
        else:
            is_promotion = False
        if not is_promotion:
            continue

        matching_entries = [
            line
            for line in changelog_lines
            if contract_name in line and f"{before} -> {after}" in line
        ]
        if not matching_entries:
            promotion_mismatches.append(
                f"{contract_name}: missing changelog entry for maturity promotion {before} -> {after}."
            )
            continue

        if not any(evidence_pattern.search(line) for line in matching_entries):
            promotion_mismatches.append(
                f"{contract_name}: changelog promotion entry must include an evidence URL (http:// or https://)."
            )

    return promotion_mismatches


def _maturity_transition_changelog_mismatches(
    maturity_updates: list[tuple[str, str, str]], changelog_lines: list[str]
) -> list[str]:
    mismatches: list[str] = []
    dated_line_pattern = re.compile(r"^- \d{4}-\d{2}-\d{2} \([^)]+\): ")
    https_link_pattern = re.compile(r"https://\S+")

    for contract_name, before, after in maturity_updates:
        matching_entries = [
            line
            for line in changelog_lines
            if contract_name in line and f"{before} -> {after}" in line
        ]
        if not matching_entries:
            mismatches.append(
                f"{contract_name}: missing changelog entry for maturity transition {before} -> {after}."
            )
            continue

        if not any(dated_line_pattern.match(line) for line in matching_entries):
            mismatches.append(
                f"{contract_name}: changelog entry for maturity transition {before} -> {after} must start with '- YYYY-MM-DD (Milestone):'."
            )

        if not any(https_link_pattern.search(line) for line in matching_entries):
            mismatches.append(
                f"{contract_name}: changelog entry for maturity transition {before} -> {after} must include at least one https:// evidence link."
            )

    return mismatches


def _transitioned_capability_commands(head_manifest: dict, transitioned_cap_ids: set[str]) -> dict[str, list[str]]:
    commands_by_capability: dict[str, list[str]] = {}
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id")
        if cap_id not in transitioned_cap_ids:
            continue
        pytest_commands = capability.get("pytest_commands") or []
        commands = [command for command in pytest_commands if isinstance(command, str) and command.strip()]
        commands_by_capability[cap_id] = commands
    return commands_by_capability


def _ci_evidence_links_command_mismatches(head_manifest: dict, transitioned_cap_ids: set[str]) -> list[str]:
    mismatches: list[str] = []
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id", "<unknown>")
        if cap_id not in transitioned_cap_ids:
            continue

        pytest_commands = capability.get("pytest_commands") or []
        normalized_pytest_commands = [
            command for command in pytest_commands if isinstance(command, str) and command.strip()
        ]

        ci_evidence_links = capability.get("ci_evidence_links")
        if not isinstance(ci_evidence_links, list):
            mismatches.append(
                f"{cap_id}: ci_evidence_links must be a list for transitioned capabilities and commands must exactly match pytest_commands."
            )
            continue

        ci_commands: list[str] = []
        malformed_entries: list[int] = []
        for idx, entry in enumerate(ci_evidence_links):
            if not isinstance(entry, dict):
                malformed_entries.append(idx)
                continue
            command = entry.get("command")
            if not isinstance(command, str) or not command.strip():
                malformed_entries.append(idx)
                continue
            ci_commands.append(command)

        if malformed_entries:
            joined_indexes = ", ".join(str(idx) for idx in malformed_entries)
            mismatches.append(
                f"{cap_id}: ci_evidence_links entries at indexes [{joined_indexes}] must be objects containing a non-empty 'command' string."
            )
            continue

        if ci_commands != normalized_pytest_commands:
            mismatches.append(
                f"{cap_id}: ci_evidence_links.command values must exactly match pytest_commands in the same order. "
                f"pytest_commands={normalized_pytest_commands}; ci_evidence_links.command={ci_commands}."
            )

    return mismatches


def _contract_map_transition_mismatches(
    head_manifest: dict,
    transitioned_cap_ids: set[str],
    contract_rows_by_name: dict[str, dict[str, str]],
) -> list[str]:
    mismatches: list[str] = []
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id", "<unknown>")
        if cap_id not in transitioned_cap_ids:
            continue

        to_status = capability.get("status")
        contract_refs = capability.get("contract_map_refs", [])
        for contract_name in contract_refs:
            row = contract_rows_by_name.get(contract_name)
            if row is None:
                mismatches.append(
                    f"{cap_id}: transitioned to status '{to_status}' but contract_map_refs entry '{contract_name}' "
                    "is missing from docs/system_contract_map.md."
                )
                continue

            milestone = row["milestone"]
            maturity = row["maturity"]
            if to_status == "done" and milestone != "Now":
                mismatches.append(
                    f"{cap_id} -> {contract_name}: transitioned to status 'done' but mapped contract row must be in "
                    f"Milestone: Now (found '{milestone}')."
                )

            if to_status == "done" and maturity in {"prototype", "in_progress"}:
                mismatches.append(
                    f"{cap_id} -> {contract_name}: transitioned to status 'done' but mapped contract row must use "
                    f"operational/proven maturity (found '{maturity}')."
                )

    return mismatches


def _commands_missing_evidence(pr_body: str, commands: list[str]) -> list[str]:
    lines = pr_body.splitlines()
    invalid: list[str] = []
    evidence_line_pattern = re.compile(r"^(Evidence:\s+)?https?://\S+$")
    html_comment_pattern = re.compile(r"^<!--.*-->$")

    normalized_lines = [_normalize_markdown_line(line) for line in lines]
    for command in commands:
        normalized_command = _normalize_markdown_line(command)
        found_valid_pair = False
        for idx, line in enumerate(normalized_lines):
            if line != normalized_command:
                continue
            if idx + 1 >= len(lines):
                continue
            evidence_idx = idx + 1
            while evidence_idx < len(normalized_lines) and html_comment_pattern.match(normalized_lines[evidence_idx]):
                evidence_idx += 1
            if evidence_idx >= len(normalized_lines):
                continue

            evidence_line = normalized_lines[evidence_idx]
            if evidence_line_pattern.match(evidence_line):
                found_valid_pair = True
                break
        if not found_valid_pair:
            invalid.append(command)
    return invalid


def _normalize_markdown_line(line: str) -> str:
    normalized = line.replace("\r", "").strip()
    normalized = re.sub(r"^[-*+]\s+", "", normalized)
    if normalized.startswith("`") and normalized.endswith("`") and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _commands_with_invalid_evidence_format(pr_body: str, commands: list[str]) -> list[str]:
    """Backward-compatible alias for older tests/callers."""
    return _commands_missing_evidence(pr_body, commands)


def _commands_missing_evidence_by_capability(
    pr_body: str, commands_by_capability: dict[str, list[str]]
) -> list[str]:
    missing: list[str] = []
    for cap_id, commands in sorted(commands_by_capability.items()):
        for command in _commands_missing_evidence(pr_body, commands):
            missing.append(
                f"{cap_id}: command must be present as an exact line and immediately followed by "
                f"a http(s) evidence URL line (optionally prefixed with 'Evidence: '): {command}"
            )
    return missing


def _load_pr_body() -> str:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return ""
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request") or {}
    return pull_request.get("body") or ""


def _extract_pr_section(pr_body: str, heading: str) -> str | None:
    lines = pr_body.splitlines()
    heading_pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE)
    section_start: int | None = None
    for idx, raw_line in enumerate(lines):
        if heading_pattern.match(raw_line.strip()):
            section_start = idx + 1
            break
    if section_start is None:
        return None

    section_lines: list[str] = []
    for raw_line in lines[section_start:]:
        if raw_line.strip().startswith("## "):
            break
        section_lines.append(raw_line)
    return "\n".join(section_lines)


def _find_missing_prefixed_fields(section_body: str, field_prefixes: list[str]) -> list[str]:
    missing: list[str] = []
    normalized_lines = [line.strip() for line in section_body.splitlines()]
    for prefix in field_prefixes:
        matched = False
        for line in normalized_lines:
            if not line.startswith("- "):
                continue
            if not line.lower().startswith(f"- {prefix.lower()}"):
                continue
            after_colon = line.split(":", 1)
            if len(after_colon) < 2:
                continue
            value = after_colon[1].strip()
            if value:
                matched = True
                break
        if not matched:
            missing.append(prefix)
    return missing


def _validate_pr_template_fields(pr_body: str, require_governance_fields: bool) -> list[str]:
    mismatches: list[str] = []

    dependency_heading = "Dependency impact statement (mandatory)"
    dependency_section = _extract_pr_section(pr_body, dependency_heading)
    if dependency_section is None:
        mismatches.append(f"{MISSING_PR_HEADING_MARKER};heading={dependency_heading}")
    else:
        dependency_fields = [
            "Upstream capabilities/contracts consumed:",
            "Downstream capabilities/contracts affected or unlocked:",
            "Cross-capability risk if this change regresses:",
        ]
        for field in _find_missing_prefixed_fields(dependency_section, dependency_fields):
            mismatches.append(f"{MISSING_PR_FIELD_MARKER};heading={dependency_heading};field={field}")

    budget_heading = "No-regression budget and rollback plan (mandatory)"
    budget_section = _extract_pr_section(pr_body, budget_heading)
    if budget_section is None:
        mismatches.append(f"{MISSING_PR_HEADING_MARKER};heading={budget_heading}")
    else:
        budget_fields = [
            "Done-capability command packs impacted (if none, write `none`):",
            "Regression budget impact (`none` / `waiver_requested`):",
        ]
        for field in _find_missing_prefixed_fields(budget_section, budget_fields):
            mismatches.append(f"{MISSING_PR_FIELD_MARKER};heading={budget_heading};field={field}")

        rollback_field = "If waiver requested, include owner + rollback-by date + mitigation command packs:"
        rollback_missing = _find_missing_prefixed_fields(budget_section, [rollback_field])
        if rollback_missing:
            mismatches.append(
                f"{MISSING_ROLLBACK_PLAN_MARKER};heading={budget_heading};field={rollback_field};"
                "expected=provide rollback plan details or explicit `not_applicable` rationale"
            )

    if require_governance_fields:
        governance_heading = "Documentation freshness and sprint handoff artifacts (mandatory for governance/maturity PRs)"
        governance_section = _extract_pr_section(pr_body, governance_heading)
        if governance_section is None:
            mismatches.append(f"{MISSING_PR_HEADING_MARKER};heading={governance_heading}")
        else:
            governance_fields = [
                "Governed docs updated with fresh regeneration metadata (`yes`/`no`/`not_applicable`):",
                "Sprint handoff artifact updates included (`yes`/`no`/`not_applicable`):",
                "If `no`, provide timeboxed follow-up issue/PR and owner:",
            ]
            for field in _find_missing_prefixed_fields(governance_section, governance_fields):
                mismatches.append(
                    f"{MISSING_GOVERNANCE_HANDOFF_MARKER};heading={governance_heading};field={field}"
                )

    return mismatches


def main() -> int:
    head_sha = os.environ.get("HEAD_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    base_sha = os.environ.get("BASE_SHA")
    if not base_sha:
        merge_base = subprocess.run(
            ["git", "merge-base", "origin/main", head_sha],
            text=True,
            capture_output=True,
            check=False,
        )
        if merge_base.returncode == 0:
            base_sha = merge_base.stdout.strip()
        else:
            base_sha = subprocess.check_output(["git", "rev-parse", f"{head_sha}~1"], text=True).strip()

    if not base_sha or not head_sha:
        print("Unable to determine BASE_SHA or HEAD_SHA.")
        return 1

    changed_files = _changed_files(base_sha, head_sha)
    if "docs/dod_manifest.json" not in changed_files:
        print("No dod_manifest governance changes detected.")
        return 0

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name in {"pull_request", "pull_request_target"}:
        pr_body = _load_pr_body()
        pr_template_mismatches = _validate_pr_template_fields(pr_body, require_governance_fields=True)
        if pr_template_mismatches:
            print("Pull request body is missing mandatory milestone governance fields.")
            for mismatch in pr_template_mismatches:
                print(f"  - {mismatch}")
            return 1

    base_manifest = _load_manifest(base_sha)
    head_manifest = _load_manifest(head_sha)
    status_transitions = _status_transitions(base_manifest, head_manifest)

    if status_transitions:
        roadmap_text = Path("ROADMAP.md").read_text(encoding="utf-8")
        roadmap_mismatches = _roadmap_status_transition_mismatches(status_transitions, roadmap_text)
        if roadmap_mismatches:
            print("Capability status transitions must be mirrored in ROADMAP.md status alignment.")
            for mismatch in roadmap_mismatches:
                print(f"  - {mismatch}")
            return 1

        contract_map_text = Path("docs/system_contract_map.md").read_text(encoding="utf-8")
        contract_rows = _extract_contract_rows_by_name(contract_map_text)
        contract_map_mismatches = _contract_map_transition_mismatches(
            head_manifest, set(status_transitions), contract_rows
        )
        if contract_map_mismatches:
            print("Capability status transitions must be mirrored in docs/system_contract_map.md contract rows.")
            for mismatch in contract_map_mismatches:
                print(f"  - {mismatch}")
            return 1

        ci_command_mismatches = _ci_evidence_links_command_mismatches(head_manifest, set(status_transitions))
        if ci_command_mismatches:
            print(
                "Transitioned capabilities must keep ci_evidence_links.command exactly synchronized with pytest_commands."
            )
            for mismatch in sorted(ci_command_mismatches):
                print(f"  - {mismatch}")
            return 1

    print("Milestone documentation governance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
