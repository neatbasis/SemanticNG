#!/usr/bin/env python3
"""Derive a deterministic CI run name from canonical repository inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CANONICAL_FILES: tuple[str, ...] = (
    "docs/dod_manifest.json",
    "docs/system_contract_map.md",
    "docs/process/quality_stage_commands.json",
)
STATUS_GLOB = "docs/status/*.json"


def _canonicalize_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonicalize_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    normalized_lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(normalized_lines).rstrip("\n") + "\n"


def _canonical_entries(repo_root: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for relative in CANONICAL_FILES:
        path = repo_root / relative
        if not path.exists():
            raise FileNotFoundError(f"missing canonical input: {relative}")
        if path.suffix == ".json":
            canonical_content = _canonicalize_json(path)
        else:
            canonical_content = _canonicalize_markdown(path)
        entries.append((relative, canonical_content))

    for path in sorted(repo_root.glob(STATUS_GLOB), key=lambda candidate: candidate.name):
        relative = path.relative_to(repo_root).as_posix()
        entries.append((relative, _canonicalize_json(path)))

    if not any(path.startswith("docs/status/") for path, _ in entries):
        raise FileNotFoundError("missing canonical input: docs/status/*.json")

    return entries


def canonical_digest(repo_root: Path) -> str:
    digest = hashlib.sha256()
    digest.update(b"ci-run-name-v1\n")
    for relative_path, canonical_content in _canonical_entries(repo_root):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\n")
        digest.update(canonical_content.encode("utf-8"))
        digest.update(b"\n--\n")
    return digest.hexdigest()[:12]


def derive_ci_run_name(*, stage: str, branch: str, repo_root: Path | None = None) -> str:
    root = repo_root or Path(__file__).resolve().parents[2]
    return f"ci::{branch}::canon::{canonical_digest(root)}::stage::{stage}"


def _resolve_branch(explicit_branch: str | None) -> str:
    if explicit_branch:
        return explicit_branch
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "unable to determine branch name")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", help="Logical stage name for this CI run (for example: qa-commit).")
    parser.add_argument("--branch", help="Branch name to embed in the run name. Defaults to current git branch.")
    args = parser.parse_args()

    branch = _resolve_branch(args.branch)
    print(derive_ci_run_name(stage=args.stage, branch=branch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
