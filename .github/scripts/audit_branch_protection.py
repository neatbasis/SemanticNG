#!/usr/bin/env python3
"""Audit branch protection/rulesets against critical workflow checks.

The script derives expected check contexts from workflow YAML files by collecting jobs
that run on pull_request and merge_group events, then compares them to:
  1) required status checks on the protected branch (direct PR merge path), and
  2) required status checks in merge-queue rulesets (merge queue path).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkflowChecks:
    workflow_name: str
    has_pull_request: bool
    has_merge_group: bool
    check_contexts: list[str]


def _parse_workflow(path: Path) -> WorkflowChecks:
    text = path.read_text(encoding="utf-8")

    name_match = re.search(r"^name:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if not name_match:
        raise ValueError(f"Workflow {path} is missing a top-level name")
    workflow_name = name_match.group(1).strip().strip('"\'')

    on_match = re.search(r"^on:\n(?P<body>(?:^[ \t].*\n|^\n)*)", text, flags=re.MULTILINE)
    on_body = on_match.group("body") if on_match else ""
    has_pull_request = bool(re.search(r"^\s*pull_request(?:\s*:|\s*$)", on_body, flags=re.MULTILINE))
    has_merge_group = bool(re.search(r"^\s*merge_group(?:\s*:|\s*$)", on_body, flags=re.MULTILINE))

    jobs_match = re.search(r"^jobs:\n(?P<body>(?:^[ \t].*\n|^\n)*)", text, flags=re.MULTILINE)
    if not jobs_match:
        raise ValueError(f"Workflow {path} is missing a jobs section")
    jobs_body = jobs_match.group("body")

    job_ids = re.findall(r"^\s{2}([A-Za-z0-9_-]+):\s*$", jobs_body, flags=re.MULTILINE)
    contexts = [f"{workflow_name} / {job_id}" for job_id in job_ids]

    return WorkflowChecks(
        workflow_name=workflow_name,
        has_pull_request=has_pull_request,
        has_merge_group=has_merge_group,
        check_contexts=contexts,
    )


def _api_get(url: str, token: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {exc.code} for {url}: {body}") from exc


def _branch_matches(branch: str, default_branch: str, include: list[str], exclude: list[str]) -> bool:
    refs = [branch, f"refs/heads/{branch}"]

    def _pattern_matches(pattern: str) -> bool:
        if pattern == "~DEFAULT_BRANCH":
            return branch == default_branch
        return any(fnmatch.fnmatch(ref, pattern) for ref in refs)

    included = True if not include else any(_pattern_matches(pat) for pat in include)
    excluded = any(_pattern_matches(pat) for pat in exclude)
    return included and not excluded


def _extract_required_contexts_from_ruleset(ruleset: dict) -> set[str]:
    contexts: set[str] = set()
    for rule in ruleset.get("rules", []):
        if rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters", {})
        for check in params.get("required_status_checks", []):
            context = check.get("context")
            if isinstance(context, str) and context.strip():
                contexts.add(context.strip())
    return contexts


def _format_diff(label: str, expected: set[str], actual: set[str]) -> list[str]:
    lines = [f"\n[{label}]"]
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if not missing and not unexpected:
        lines.append("  OK: no drift")
        return lines
    if missing:
        lines.append("  Missing required checks:")
        lines.extend(f"    - {item}" for item in missing)
    if unexpected:
        lines.append("  Extra required checks not in critical set:")
        lines.extend(f"    - {item}" for item in unexpected)
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit branch protection and merge queue required checks.")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"), help="owner/repo (default: GITHUB_REPOSITORY)")
    parser.add_argument("--branch", default="main", help="Protected branch to audit")
    parser.add_argument(
        "--workflow",
        action="append",
        default=[],
        help="Workflow file to include (repeatable). Defaults to quality and milestone gates.",
    )
    args = parser.parse_args()

    if not args.repo:
        print("ERROR: --repo is required when GITHUB_REPOSITORY is not set", file=sys.stderr)
        return 2

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GH_TOKEN or GITHUB_TOKEN must be set", file=sys.stderr)
        return 2

    workflows = args.workflow or [
        ".github/workflows/quality-guardrails.yml",
        ".github/workflows/state-renorm-milestone-gate.yml",
    ]

    parsed = [_parse_workflow(Path(path)) for path in workflows]

    expected_pull_request: set[str] = set()
    expected_merge_group: set[str] = set()
    for item in parsed:
        if item.has_pull_request:
            expected_pull_request.update(item.check_contexts)
        if item.has_merge_group:
            expected_merge_group.update(item.check_contexts)

    expected_critical = expected_pull_request | expected_merge_group

    print("Expected critical checks (from workflow YAML):")
    for check in sorted(expected_critical):
        print(f"  - {check}")

    owner, repo = args.repo.split("/", 1)
    repo_info = _api_get(f"https://api.github.com/repos/{owner}/{repo}", token)
    default_branch = repo_info.get("default_branch", "main")

    protection = _api_get(
        f"https://api.github.com/repos/{owner}/{repo}/branches/{args.branch}/protection",
        token,
    )
    direct_required = set((protection.get("required_status_checks") or {}).get("contexts") or [])

    rulesets = _api_get(
        f"https://api.github.com/repos/{owner}/{repo}/rulesets?includes_parents=true",
        token,
    )
    merge_queue_required: set[str] = set()
    for ruleset in rulesets:
        if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
            continue
        conditions = ruleset.get("conditions") or {}
        ref_name = conditions.get("ref_name") or {}
        include = ref_name.get("include") or []
        exclude = ref_name.get("exclude") or []
        if not _branch_matches(args.branch, default_branch, include, exclude):
            continue

        has_merge_queue_rule = any(rule.get("type") == "merge_queue" for rule in ruleset.get("rules", []))
        if not has_merge_queue_rule:
            continue

        merge_queue_required.update(_extract_required_contexts_from_ruleset(ruleset))

    output_lines = []
    output_lines.extend(_format_diff("direct-pr-merge (branch protection)", expected_critical, direct_required))
    output_lines.extend(_format_diff("merge-queue (rulesets)", expected_critical, merge_queue_required))
    print("\n".join(output_lines))

    drift = (expected_critical != direct_required) or (expected_critical != merge_queue_required)
    if drift:
        print(
            "\nDrift detected. Update branch protection and merge queue required checks to match the expected list above.",
            file=sys.stderr,
        )
        return 1

    print("\nBranch protection and merge queue checks are aligned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
