#!/usr/bin/env python3
"""Run hook parity, capture logs, and always emit failure classification artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run() -> int:
    log_path = Path("precommit.log")

    with log_path.open("w", encoding="utf-8") as log_file:
        hook_proc = subprocess.Popen(
            ["make", "qa-hook-parity"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert hook_proc.stdout is not None
        for line in hook_proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            log_file.write(line)

        hook_proc.wait()

    classify_proc = subprocess.run(
        [
            "python",
            ".github/scripts/classify_precommit_failures.py",
            "--log",
            str(log_path),
            "--json-out",
            "precommit_failure_classification.json",
            "--md-out",
            "precommit_failure_classification.md",
        ],
        check=False,
    )

    if classify_proc.returncode != 0:
        print(
            "Warning: failure classification script failed; preserving original "
            f"qa-hook-parity exit code {hook_proc.returncode}.",
            file=sys.stderr,
        )

    return hook_proc.returncode


if __name__ == "__main__":
    raise SystemExit(run())
