#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path

MANIFEST_PATH = "docs/dod_manifest.json"
CONTRACT_MAP_PATH = "docs/system_contract_map.md"
ROADMAP_PATH = "ROADMAP.md"
ROADMAP_PROGRESS_PATHS = [
    ROADMAP_PATH,
    "docs/sprint_plan_5x.md",
    "docs/sprint_handoffs/sprint-5-handoff.md",
]
VALID_STATUSES = ("done", "in_progress", "planned")


def _git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], text=True)


def _changed_files(base_sha: str, head_sha: str) -> set[str]:
    out = _git_output(["diff", "--name-only", base_sha, head_sha])
    return {line.strip() for line in out.splitlines() if line.strip()}


def _manifest_changed_capability_ids(base_sha: str, head_sha: str) -> list[str]:
    try:
        diff = _git_output(["diff", "--unified=0", base_sha, head_sha, "--", MANIFEST_PATH])
    except subprocess.CalledProcessError:
        return []

    ids: list[str] = []
    seen: set[str] = set()
    for line in diff.splitlines():
        if not line or line[0] not in "+-":
            continue
        match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
        if match:
            cap_id = match.group(1)
            if cap_id not in seen:
                seen.add(cap_id)
                ids.append(cap_id)
    return ids


def _load_manifest() -> dict:
    return json.loads(Path(MANIFEST_PATH).read_text(encoding="utf-8"))


def _load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _extract_roadmap_status_alignment(roadmap_text: str) -> dict[str, set[str]]:
    status_alignment: dict[str, set[str]] = {status: set() for status in VALID_STATUSES}
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
        if status not in status_alignment:
            continue
        capability_ids = {cap_id for cap_id in re.findall(r"`([^`]+)`", match.group(2))}
        status_alignment[status] = capability_ids

    return status_alignment


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
        rows[cells[0]] = {"milestone": current_milestone, "maturity": cells[-1].strip("`").strip().lower()}
    return rows


def _capability_status_map(manifest: dict) -> dict[str, str]:
    capability_status: dict[str, str] = {}
    for cap in manifest.get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        cap_id = cap.get("id")
        status = cap.get("status")
        if isinstance(cap_id, str) and isinstance(status, str) and status in VALID_STATUSES:
            capability_status[cap_id] = status
    return capability_status


def _diagnostic(file_path: str, key: str, expected: str, actual: str) -> str:
    return f"file={file_path} key={key} expected={expected} actual={actual}"


def _cross_file_parity_diagnostics(manifest: dict, roadmap_text: str, contract_map_text: str) -> list[str]:
    diagnostics: list[str] = []
    capability_status = _capability_status_map(manifest)
    roadmap_alignment = _extract_roadmap_status_alignment(roadmap_text)
    contract_rows = _extract_contract_rows_by_name(contract_map_text)

    for status in VALID_STATUSES:
        manifest_ids = sorted([cap_id for cap_id, cap_status in capability_status.items() if cap_status == status])
        roadmap_ids = sorted(roadmap_alignment.get(status, set()))
        if manifest_ids != roadmap_ids:
            diagnostics.append(
                _diagnostic(
                    ROADMAP_PATH,
                    f"status_alignment.{status}",
                    f"manifest ids={manifest_ids}",
                    f"roadmap ids={roadmap_ids}",
                )
            )

    for cap in manifest.get("capabilities", []):
        if not isinstance(cap, dict):
            continue
        cap_id = cap.get("id")
        roadmap_section = cap.get("roadmap_section")
        contract_refs = cap.get("contract_map_refs")
        if not isinstance(cap_id, str):
            continue
        if not isinstance(roadmap_section, str) or not roadmap_section.strip():
            diagnostics.append(
                _diagnostic(MANIFEST_PATH, f"capabilities.{cap_id}.roadmap_section", "non-empty milestone", repr(roadmap_section))
            )
            continue
        if not isinstance(contract_refs, list):
            diagnostics.append(
                _diagnostic(MANIFEST_PATH, f"capabilities.{cap_id}.contract_map_refs", "list[str]", repr(contract_refs))
            )
            continue
        for ref in contract_refs:
            if not isinstance(ref, str):
                diagnostics.append(
                    _diagnostic(MANIFEST_PATH, f"capabilities.{cap_id}.contract_map_refs[]", "string contract name", repr(ref))
                )
                continue
            row = contract_rows.get(ref)
            if row is None:
                diagnostics.append(
                    _diagnostic(CONTRACT_MAP_PATH, f"contract:{ref}", f"referenced by {cap_id}", "missing row")
                )
                continue
            if row["milestone"] != roadmap_section:
                diagnostics.append(
                    _diagnostic(
                        CONTRACT_MAP_PATH,
                        f"contract:{ref}.milestone",
                        f"{roadmap_section} (from {MANIFEST_PATH}:{cap_id})",
                        row["milestone"],
                    )
                )

    return diagnostics


def _suggestions(changed_capability_ids: list[str]) -> list[str]:
    focus = ", ".join(f"`{cap}`" for cap in changed_capability_ids) if changed_capability_ids else "changed capabilities"
    return [
        f"Update `{CONTRACT_MAP_PATH}` milestone/maturity rows and changelog entries for {focus}.",
        f"Mirror status/horizon updates in `{ROADMAP_PATH}` capability status alignment for {focus}.",
        f"Capture sprint progress impact in `docs/sprint_plan_5x.md` or `docs/sprint_handoffs/sprint-5-handoff.md`.",
        "Re-run `make promotion-governance-check` before pushing.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate governance docs synchronization.")
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args()

    head_sha = args.head or _git_output(["rev-parse", "HEAD"]).strip()
    base_sha = args.base
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
            base_sha = _git_output(["rev-parse", f"{head_sha}~1"]).strip()

    changed_files = _changed_files(base_sha, head_sha)
    manifest_changed = MANIFEST_PATH in changed_files
    contract_changed = CONTRACT_MAP_PATH in changed_files
    roadmap_progress_changed = any(path in changed_files for path in ROADMAP_PROGRESS_PATHS)

    if not (manifest_changed or contract_changed or roadmap_progress_changed):
        print("No governance synchronization inputs changed.")
        return 0

    diagnostics: list[str] = []
    if manifest_changed and not contract_changed:
        diagnostics.append(_diagnostic(MANIFEST_PATH, "changed_without_pair", CONTRACT_MAP_PATH, "not changed"))
    if contract_changed and not manifest_changed:
        diagnostics.append(_diagnostic(CONTRACT_MAP_PATH, "changed_without_pair", MANIFEST_PATH, "not changed"))
    if (manifest_changed or contract_changed) and not roadmap_progress_changed:
        diagnostics.append(
            _diagnostic(
                ROADMAP_PATH,
                "governance_progress_updates",
                f"at least one changed in {ROADMAP_PROGRESS_PATHS}",
                "none changed",
            )
        )

    manifest = _load_manifest()
    roadmap_text = _load_text(ROADMAP_PATH)
    contract_map_text = _load_text(CONTRACT_MAP_PATH)
    diagnostics.extend(_cross_file_parity_diagnostics(manifest, roadmap_text, contract_map_text))

    if diagnostics:
        changed_ids = _manifest_changed_capability_ids(base_sha, head_sha) if manifest_changed else []
        print("Governance docs synchronization check failed:")
        for item in diagnostics:
            print(f"  - {item}")
        print("\nSuggested synchronized follow-ups:")
        for suggestion in _suggestions(changed_ids):
            print(f"  - {suggestion}")
        return 1

    capability_status = _capability_status_map(manifest)
    print(
        "Governance docs synchronization check passed "
        f"(validated {len(capability_status)} capabilities across {ROADMAP_PATH}, {MANIFEST_PATH}, and {CONTRACT_MAP_PATH})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
