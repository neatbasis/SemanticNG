#!/usr/bin/env python3
"""Warn about root-level untracked scratch/artifact files before push."""

from __future__ import annotations

import subprocess
from pathlib import PurePosixPath

SCRATCH_PREFIXES = (
    "tmp",
    "scratch",
    "artifact",
    "debug",
)
SCRATCH_SUFFIXES = (
    ".log",
    ".tmp",
    ".bak",
    ".swp",
)
EXPLICIT_NAMES = {
    "precommit.log",
    "nohup.out",
}


def list_untracked() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("?? "):
            continue
        files.append(line[3:])
    return files


def is_root_level(path: str) -> bool:
    return "/" not in path.strip("/")


def looks_like_scratch(path: str) -> bool:
    name = PurePosixPath(path).name
    lower_name = name.lower()
    return (
        lower_name in EXPLICIT_NAMES
        or lower_name.startswith(SCRATCH_PREFIXES)
        or lower_name.endswith(SCRATCH_SUFFIXES)
    )


def main() -> int:
    flagged = [p for p in list_untracked() if is_root_level(p) and looks_like_scratch(p)]
    if not flagged:
        return 0

    print("[scratch-hygiene] Warning: untracked root-level scratch files detected:")
    for path in flagged:
        print(f"  - {path}")
    print(
        "[scratch-hygiene] Consider moving to artifacts/ or deleting before push to avoid accidental hook scans."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
