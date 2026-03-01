from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


_GLOB_META_CHARS = set("*?[]")


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


def _validate_doc_freshness(config: dict, base_dir: Path, now_utc: datetime) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    timestamp_policy = config.get("timestamp_policy", {})
    timestamp_pattern = str(timestamp_policy.get("pattern", ""))
    timestamp_format = str(timestamp_policy.get("format", ""))

    file_classes = config.get("file_classes", {})
    governed_files = config.get("governed_files", [])

    for entry in governed_files:
        configured_path = str(entry.get("path", "")).strip()
        file_class = str(entry.get("class", "")).strip()

        if file_class not in file_classes:
            issues.append({"file_path": configured_path, "message": f"references unknown class '{file_class}'."})
            continue

        max_age_days = file_classes[file_class].get("max_age_days")
        if not isinstance(max_age_days, int) or max_age_days < 0:
            issues.append({"file_path": configured_path, "message": "has invalid max_age_days in configured class."})
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
