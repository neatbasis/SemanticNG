#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.demo_runner import run_packs


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    packs_dir = root / "scenario_packs"
    output_path = root / "output" / "session_report.json"

    report = run_packs(packs_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote report: {output_path}")
    print(json.dumps(report["summary_metrics"], indent=2))
