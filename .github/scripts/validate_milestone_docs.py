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
            missing_commands: list[str] = []
            for cap_id in status_transitions:
                for command in head_caps.get(cap_id, {}).get("pytest_commands", []):
                    if command not in pr_body:
                        missing_commands.append(command)
            if missing_commands:
                print("PR description must include exact milestone pytest commands for capability status transitions.")
                for command in sorted(set(missing_commands)):
                    print(f"  - Missing command in PR body: {command}")
                return 1

    if "docs/system_contract_map.md" in changed_files:
        base_map_text = subprocess.check_output(
            ["git", "show", f"{base_sha}:docs/system_contract_map.md"], text=True
        )
        head_map_text = Path("docs/system_contract_map.md").read_text(encoding="utf-8")
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
