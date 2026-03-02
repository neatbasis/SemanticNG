#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from pathlib import Path

MANIFEST_PATH = "docs/dod_manifest.json"
CONTRACT_MAP_PATH = "docs/system_contract_map.md"
ROADMAP_PROGRESS_PATHS = [
    "ROADMAP.md",
    "docs/sprint_plan_5x.md",
    "docs/sprint_handoffs/sprint-5-handoff.md",
]


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


def _suggestions(changed_capability_ids: list[str]) -> list[str]:
    focus = ", ".join(f"`{cap}`" for cap in changed_capability_ids) if changed_capability_ids else "changed capabilities"
    return [
        f"Update `{CONTRACT_MAP_PATH}` milestone/maturity rows and changelog entries for {focus}.",
        f"Mirror status/horizon updates in `ROADMAP.md` capability status alignment for {focus}.",
        "Capture sprint progress impact in `docs/sprint_plan_5x.md` or `docs/sprint_handoffs/sprint-5-handoff.md`.",
        "Re-run `make promotion-check` before pushing.",
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

    mismatches: list[str] = []
    if manifest_changed and not contract_changed:
        mismatches.append(f"`{MANIFEST_PATH}` changed without `{CONTRACT_MAP_PATH}` update.")
    if contract_changed and not manifest_changed:
        mismatches.append(f"`{CONTRACT_MAP_PATH}` changed without `{MANIFEST_PATH}` update.")
    if (manifest_changed or contract_changed) and not roadmap_progress_changed:
        mismatches.append(
            "Governance source updates are missing roadmap/progress docs update "
            f"(expected one of: {', '.join(ROADMAP_PROGRESS_PATHS)})."
        )

    if mismatches:
        changed_ids = _manifest_changed_capability_ids(base_sha, head_sha) if manifest_changed else []
        print("Governance docs synchronization check failed:")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        print("\nSuggested synchronized follow-ups:")
        for suggestion in _suggestions(changed_ids):
            print(f"  - {suggestion}")
        return 1

    # Lightweight integrity check for local author feedback.
    manifest = _load_manifest()
    capability_ids = [cap.get("id") for cap in manifest.get("capabilities", []) if isinstance(cap, dict)]
    print(
        "Governance docs synchronization check passed "
        f"(validated {len(capability_ids)} manifest capabilities across synchronized docs updates)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
