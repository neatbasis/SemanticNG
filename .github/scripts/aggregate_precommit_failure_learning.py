#!/usr/bin/env python3
"""Aggregate the last 7 days of pre-commit failure classifications."""

from __future__ import annotations

import argparse
import io
import json
import os
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ARTIFACT_NAME = "precommit-classification"
WORKFLOW_NAME = "quality-guardrails.yml"


def _api_get(url: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _download_artifact_zip(url: str, token: str) -> bytes:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:  # noqa: S310
        return resp.read()


def aggregate(repo: str, token: str, lookback_days: int) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    runs_url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_NAME}/runs"
        "?per_page=100&status=completed"
    )
    runs_payload = _api_get(runs_url, token)

    class_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    inspected_runs = 0

    for run in runs_payload.get("workflow_runs", []):
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if created < since:
            continue
        inspected_runs += 1
        run_id = run["id"]
        artifact_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
        artifacts_payload = _api_get(artifact_url, token)

        target = next(
            (a for a in artifacts_payload.get("artifacts", []) if a.get("name") == ARTIFACT_NAME),
            None,
        )
        if not target or target.get("expired"):
            continue

        archive = _download_artifact_zip(target["archive_download_url"], token)
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            for member in zf.namelist():
                if member.endswith("precommit_failure_classification.json"):
                    payload = json.loads(zf.read(member).decode("utf-8"))
                    class_counts.update(payload.get("classes_detected", []))
                    path_counts.update(payload.get("touched_paths", []))

    return {
        "lookback_days": lookback_days,
        "inspected_runs": inspected_runs,
        "failure_class_counts": dict(sorted(class_counts.items())),
        "touched_path_counts": dict(path_counts.most_common(50)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["## Weekly pre-commit quality learning loop", ""]
    lines.append(f"- Lookback window: last `{report['lookback_days']}` days")
    lines.append(f"- Workflow runs inspected: `{report['inspected_runs']}`")
    lines.append("")
    lines.append("### Failure classes")
    if report["failure_class_counts"]:
        for key, value in report["failure_class_counts"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Touched paths")
    if report["touched_path_counts"]:
        for key, value in list(report["touched_path_counts"].items())[:20]:
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--json-out", default="weekly_precommit_failure_summary.json")
    parser.add_argument("--md-out", default="weekly_precommit_failure_summary.md")
    args = parser.parse_args()

    if not args.repo or not args.token:
        raise SystemExit("repo/token required")

    report = aggregate(args.repo, args.token, args.lookback_days)
    summary = render_markdown(report)

    Path(args.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    Path(args.md_out).write_text(summary + "\n", encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
