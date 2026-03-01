from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


_GLOB_META_CHARS = set("*?[]")
_HEX_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


GitCommandRunner = Callable[[Path, list[str]], str | None]


def _load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_now(now_utc: str | None) -> datetime:
    if now_utc is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(now_utc.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now-utc must include timezone information (e.g., trailing 'Z').")
    return parsed.astimezone(timezone.utc)


def _extract_timestamp(content: str, pattern: str) -> str | None:
    regex = re.compile(pattern, re.MULTILINE)
    for line in content.splitlines():
        match = regex.match(line.strip())
        if match:
            return match.group("timestamp")
    return None


def _contains_glob(path_value: str) -> bool:
    return any(char in path_value for char in _GLOB_META_CHARS)


def _resolve_governed_paths(base_dir: Path, configured_path: str) -> list[str]:
    candidate = configured_path.strip()
    if not candidate:
        return []

    candidate_path = Path(candidate)
    if candidate_path.is_absolute() or ".." in candidate_path.parts:
        return []

    if _contains_glob(candidate):
        return sorted(str(path.relative_to(base_dir)) for path in base_dir.glob(candidate) if path.is_file())

    return [candidate]


def _run_git_command(base_dir: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(base_dir), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    stdout = result.stdout.strip().lower()
    return stdout or None


def _resolve_git_commit(base_dir: Path, repo_relative_path: str, git_runner: GitCommandRunner) -> str | None:
    return git_runner(base_dir, ["rev-list", "-1", "HEAD", "--", repo_relative_path])


def _resolve_commit_lag(
    base_dir: Path,
    expected_commit: str,
    reference_commit: str,
    git_runner: GitCommandRunner,
) -> int | None:
    count = git_runner(base_dir, ["rev-list", "--count", f"{expected_commit}..{reference_commit}"])
    if count is None:
        return None
    try:
        return int(count)
    except ValueError:
        return None


def _lookup_commit_binding(file_path: str, policy: dict) -> dict[str, str] | None:
    bindings = policy.get("governed_source_commits", {})
    if not isinstance(bindings, dict):
        return None

    direct = bindings.get(file_path)
    if isinstance(direct, dict):
        return direct

    wildcard = bindings.get("*")
    if isinstance(wildcard, dict):
        return wildcard

    return None


def _path_matches_pattern(path: str, pattern: str) -> bool:
    return Path(path).match(pattern)


def _lookup_source_map(file_path: str, policy: dict) -> list[str] | None:
    source_map = policy.get("governed_source_map", {})
    if not isinstance(source_map, dict):
        return None

    direct = source_map.get(file_path)
    if isinstance(direct, list) and all(isinstance(item, str) and item.strip() for item in direct):
        return direct

    for pattern, aliases in source_map.items():
        if pattern in {file_path, "*"}:
            continue
        if not isinstance(pattern, str) or not _contains_glob(pattern):
            continue
        if _path_matches_pattern(file_path, pattern) and isinstance(aliases, list):
            normalized = [item for item in aliases if isinstance(item, str) and item.strip()]
            if normalized:
                return normalized

    wildcard = source_map.get("*")
    if isinstance(wildcard, list) and all(isinstance(item, str) and item.strip() for item in wildcard):
        return wildcard

    return None


def _validate_doc_freshness(
    config: dict,
    base_dir: Path,
    now_utc: datetime,
    *,
    git_runner: GitCommandRunner | None = None,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    git_runner = git_runner or _run_git_command

    timestamp_policy = config.get("timestamp_policy", {})
    timestamp_pattern = str(timestamp_policy.get("pattern", ""))
    timestamp_format = str(timestamp_policy.get("format", ""))

    file_classes = config.get("file_classes", {})
    governed_files = config.get("governed_files", [])
    source_commit_policy = config.get("source_commit_policy", {})
    source_files = source_commit_policy.get("source_files", {}) if isinstance(source_commit_policy, dict) else {}

    for entry in governed_files:
        configured_path = str(entry.get("path", "")).strip()
        file_class = str(entry.get("class", "")).strip()

        if file_class not in file_classes:
            issues.append({"file_path": configured_path, "message": f"references unknown class '{file_class}'."})
            continue

        class_policy = file_classes[file_class] if isinstance(file_classes[file_class], dict) else {}
        max_age_days = class_policy.get("max_age_days")
        max_commit_lag = class_policy.get("max_commit_lag")

        if max_age_days is not None and (not isinstance(max_age_days, int) or max_age_days < 0):
            issues.append({"file_path": configured_path, "message": "has invalid max_age_days in configured class."})
            continue
        if not isinstance(max_commit_lag, int) or max_commit_lag < 0:
            issues.append({"file_path": configured_path, "message": "has invalid max_commit_lag in configured class."})
            continue

        resolved_paths = _resolve_governed_paths(base_dir, configured_path)
        if not resolved_paths:
            if _contains_glob(configured_path):
                issues.append({"file_path": configured_path, "message": "glob pattern did not match any files."})
            else:
                issues.append({"file_path": configured_path, "message": "governed file does not exist."})
            continue

        for file_path in resolved_paths:
            absolute_path = base_dir / file_path
            if not absolute_path.exists():
                issues.append({"file_path": file_path, "message": "governed file does not exist."})
                continue

            if source_commit_policy:
                source_aliases = _lookup_source_map(file_path, source_commit_policy)
                if not source_aliases:
                    issues.append({"file_path": file_path, "message": "missing source mapping for governed document."})
                    continue

                commit_binding = _lookup_commit_binding(file_path, source_commit_policy)
                if commit_binding is None:
                    issues.append({"file_path": file_path, "message": "missing source commit metadata for governed document."})
                    continue

                for source_alias in source_aliases:
                    source_entry = source_files.get(source_alias)
                    source_path: str | None = None
                    lag_reference = "head"
                    if isinstance(source_entry, str):
                        source_path = source_entry
                    elif isinstance(source_entry, dict):
                        source_path = source_entry.get("path")
                        lag_reference = str(source_entry.get("lag_reference", "head")).strip().lower()

                    if not isinstance(source_path, str) or not source_path.strip():
                        issues.append({"file_path": file_path, "message": f"source alias '{source_alias}' is not configured in source_commit_policy.source_files."})
                        continue

                    if lag_reference not in {"head", "source_tip"}:
                        issues.append({"file_path": file_path, "message": f"source alias '{source_alias}' has invalid lag_reference '{lag_reference}'."})
                        continue

                    expected_commit = commit_binding.get(source_alias)
                    if not isinstance(expected_commit, str) or not _HEX_COMMIT_PATTERN.fullmatch(expected_commit.lower()):
                        issues.append({"file_path": file_path, "message": f"source alias '{source_alias}' has invalid commit hash metadata '{expected_commit}'."})
                        continue

                    reference_commit = "head"
                    if lag_reference == "source_tip":
                        resolved_source_commit = _resolve_git_commit(base_dir, source_path, git_runner)
                        if resolved_source_commit is None:
                            issues.append({"file_path": file_path, "message": f"unable to resolve git commit for source file '{source_path}'."})
                            continue
                        reference_commit = resolved_source_commit

                    commit_lag = _resolve_commit_lag(base_dir, expected_commit.lower(), reference_commit, git_runner)
                    if commit_lag is None:
                        issues.append({"file_path": file_path, "message": f"unable to resolve commit lag for source alias '{source_alias}' from '{expected_commit}' to '{reference_commit}'."})
                        continue

                    if commit_lag > max_commit_lag:
                        issues.append(
                            {
                                "file_path": file_path,
                                "message": (
                                    f"commit lag violation for '{source_alias}' ({source_path}): "
                                    f"lag={commit_lag} commits exceeds max_commit_lag={max_commit_lag} "
                                    f"for class '{file_class}' (reference={lag_reference}, expected_commit='{expected_commit}', reference_commit='{reference_commit}')."
                                ),
                            }
                        )

            content = absolute_path.read_text(encoding="utf-8")
            extracted = _extract_timestamp(content, timestamp_pattern)
            if extracted is None:
                issues.append({"file_path": file_path, "message": "missing freshness metadata line matching configured timestamp policy."})
                continue

            try:
                timestamp = datetime.strptime(extracted, timestamp_format).replace(tzinfo=timezone.utc)
            except ValueError:
                issues.append({"file_path": file_path, "message": f"metadata timestamp '{extracted}' does not match format '{timestamp_format}'."})
                continue

            if max_age_days is not None:
                age_days = (now_utc - timestamp).total_seconds() / 86400
                if age_days > max_age_days:
                    issues.append({"file_path": file_path, "message": f"stale freshness metadata: age={age_days:.1f} days exceeds max_age_days={max_age_days} for class '{file_class}'."})

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate governed documentation freshness metadata SLOs.")
    parser.add_argument(
        "--config",
        default="docs/doc_freshness_slo.json",
        help="Path to the doc freshness SLO configuration JSON.",
    )
    parser.add_argument(
        "--now-utc",
        default=None,
        help="Override current UTC timestamp for deterministic checks (ISO-8601, e.g., 2026-03-01T00:00:00Z).",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    config = _load_config(config_path)
    now_utc = _parse_now(args.now_utc)
    issues = _validate_doc_freshness(config, Path.cwd(), now_utc)

    if issues:
        print("Documentation freshness SLO validation failed:", file=sys.stderr)
        for issue in issues:
            print(f" - {issue['file_path']}: {issue['message']}", file=sys.stderr)
        return 1

    print(f"Documentation freshness SLO validation passed for {len(config.get('governed_files', []))} governed file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
