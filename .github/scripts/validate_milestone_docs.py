import json
import os
import re
import subprocess
import sys
from pathlib import Path


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


def _commands_missing_evidence(pr_body: str, commands: list[str]) -> list[str]:
    lines = pr_body.splitlines()
    missing: list[str] = []
    for command in commands:
        found_with_evidence = False
        for idx, line in enumerate(lines):
            if command not in line:
                continue
            window = "\n".join(lines[idx : idx + 4])
            if "http://" in window or "https://" in window:
                found_with_evidence = True
                break
        if not found_with_evidence:
            missing.append(command)
    return missing


def _load_pr_body() -> str:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return ""
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request") or {}
    return pull_request.get("body") or ""


def main() -> int:
    base_sha = os.environ.get("BASE_SHA")
    head_sha = os.environ.get("HEAD_SHA")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if not base_sha or not head_sha:
        print("Missing BASE_SHA or HEAD_SHA.")
        return 1

    changed_files = _changed_files(base_sha, head_sha)
    if "docs/dod_manifest.json" not in changed_files and "docs/system_contract_map.md" not in changed_files:
        print("No manifest or system contract map governance changes detected.")
        return 0

    base_manifest = _load_manifest(base_sha)
    head_manifest = _load_manifest(head_sha)
    status_transitions = _status_transitions(base_manifest, head_manifest)

    if status_transitions:
        required_updates = {"ROADMAP.md", "docs/system_contract_map.md"}
        missing = sorted(required_updates - set(changed_files))
        if missing:
            print("Capability status transitions require roadmap and contract-map updates.")
            for cap_id, (from_status, to_status) in status_transitions.items():
                print(f"  - {cap_id}: {from_status} -> {to_status}")
            print("Missing required changed files:")
            for path in missing:
                print(f"  - {path}")
            return 1

        if event_name == "pull_request":
            pr_body = _load_pr_body()
            head_caps = {cap["id"]: cap for cap in head_manifest.get("capabilities", [])}
            required_commands: list[str] = []
            for cap_id in status_transitions:
                required_commands.extend(head_caps.get(cap_id, {}).get("pytest_commands", []))

            missing_commands = [command for command in required_commands if command not in pr_body]
            if missing_commands:
                print("PR description must include exact milestone pytest commands for capability status transitions.")
                for command in sorted(set(missing_commands)):
                    print(f"  - Missing command in PR body: {command}")
                return 1

            missing_evidence = _commands_missing_evidence(pr_body, sorted(set(required_commands)))
            if missing_evidence:
                print("PR description must link passing CI evidence near each milestone pytest command.")
                print("Include workflow/job URL(s) or attached output for every command.")
                for command in missing_evidence:
                    print(f"  - Missing evidence link near command: {command}")
                return 1

    head_map_text = Path("docs/system_contract_map.md").read_text(encoding="utf-8")

    contract_names_by_milestone = _extract_contract_names_by_milestone(head_map_text)
    known_contract_names = {
        contract_name
        for contract_names in contract_names_by_milestone.values()
        for contract_name in contract_names
    }
    referenced_contracts: dict[str, list[str]] = {}
    unknown_references: list[tuple[str, str]] = []
    for capability in head_manifest.get("capabilities", []):
        cap_id = capability.get("id", "<unknown>")
        refs = capability.get("contract_map_refs") or []
        if not isinstance(refs, list):
            print(f"Capability '{cap_id}' must define 'contract_map_refs' as a list of contract names.")
            return 1
        normalized_refs = [ref for ref in refs if isinstance(ref, str) and ref.strip()]
        referenced_contracts[cap_id] = normalized_refs
        for contract_name in normalized_refs:
            if contract_name not in known_contract_names:
                unknown_references.append((cap_id, contract_name))

    if unknown_references:
        print("Found capability references to unknown system contracts.")
        print("Update docs/dod_manifest.json contract_map_refs or docs/system_contract_map.md contract names.")
        for cap_id, contract_name in sorted(unknown_references):
            print(f"  - {cap_id}: {contract_name}")
        print("Known contract names:")
        for contract_name in sorted(known_contract_names):
            print(f"  - {contract_name}")
        return 1

    active_contracts = set(contract_names_by_milestone.get("Next", [])) | set(
        contract_names_by_milestone.get("Later", [])
    )
    referenced_contract_set = {
        contract_name
        for refs in referenced_contracts.values()
        for contract_name in refs
    }
    missing_active_contract_refs = sorted(active_contracts - referenced_contract_set)
    if missing_active_contract_refs:
        print("Every active Next/Later contract must be referenced by at least one capability contract_map_refs entry.")
        print("Add references in docs/dod_manifest.json under the relevant capabilities.")
        for contract_name in missing_active_contract_refs:
            print(f"  - Missing reference for contract: {contract_name}")
        return 1

    if "docs/system_contract_map.md" in changed_files:
        base_map_text = subprocess.check_output(
            ["git", "show", f"{base_sha}:docs/system_contract_map.md"], text=True
        )
        maturity_updates = _maturity_transitions(base_map_text, head_map_text)
        if maturity_updates:
            changelog_entries = _added_changelog_entries(base_sha, head_sha)
            if not changelog_entries:
                print("Maturity changes in docs/system_contract_map.md require changelog entries.")
                for contract_name, before, after in maturity_updates:
                    print(f"  - {contract_name}: {before} -> {after}")
                print("Add one or more entries under '### Changelog' in the format:")
                print("- YYYY-MM-DD (Milestone): ...")
                return 1

    print("Milestone documentation governance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
