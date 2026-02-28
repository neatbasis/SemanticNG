import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REQUIRED_EVENT_KEYS = {
    "ts",
    "ci_run",
    "capability_id",
    "pack_command",
    "test",
    "status",
    "bucket",
    "cause",
    "seed",
    "artifact_ref",
}
ALLOWED_STATUSES = {"pass", "fail", "flake"}


@dataclass(frozen=True)
class CommandMembership:
    capability_id: str
    pack_command: str
    test_files: tuple[str, ...]


@dataclass(frozen=True)
class TestResult:
    test: str
    test_file: str | None
    status: str
    cause: str


def _load_manifest(manifest_path: Path) -> list[CommandMembership]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    memberships: list[CommandMembership] = []
    for capability in manifest.get("capabilities", []):
        capability_id = capability.get("id")
        if not isinstance(capability_id, str):
            continue
        for command in capability.get("pytest_commands", []):
            if not isinstance(command, str):
                continue
            test_files = tuple(
                token
                for token in command.split()
                if token.startswith("tests/") and token.endswith(".py")
            )
            memberships.append(
                CommandMembership(
                    capability_id=capability_id,
                    pack_command=command,
                    test_files=test_files,
                )
            )
    return memberships


def _normalize_test_identifier(test_file: str | None, classname: str | None, name: str | None) -> str:
    if test_file and name:
        return f"{test_file}::{name}"
    if classname and name:
        return f"{classname}::{name}"
    return name or classname or "unknown"


def _parse_junit_results(junit_paths: list[Path]) -> list[TestResult]:
    results: list[TestResult] = []
    for junit_path in junit_paths:
        if not junit_path.exists():
            continue
        root = ET.fromstring(junit_path.read_text(encoding="utf-8"))
        testcases = root.findall(".//testcase")
        for testcase in testcases:
            test_file = testcase.attrib.get("file")
            classname = testcase.attrib.get("classname")
            name = testcase.attrib.get("name")
            test_id = _normalize_test_identifier(test_file, classname, name)

            failure_node = testcase.find("failure")
            error_node = testcase.find("error")
            if failure_node is not None or error_node is not None:
                failure = failure_node if failure_node is not None else error_node
                cause = (failure.attrib.get("message") or (failure.text or "").strip() or "test_failure")
                results.append(TestResult(test=test_id, test_file=test_file, status="fail", cause=cause))
            else:
                results.append(TestResult(test=test_id, test_file=test_file, status="pass", cause=""))
    return results


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_rerun_metadata(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}

    payload = _load_json(path)
    entries: list[Any] = []
    if isinstance(payload, dict):
        for key in ("flaky_tests", "flakes", "reruns"):
            value = payload.get(key)
            if isinstance(value, list):
                entries.extend(value)
    elif isinstance(payload, list):
        entries = payload

    parsed: dict[str, dict[str, Any]] = {}
    for item in entries:
        if isinstance(item, str):
            parsed[item] = {"status": "flake"}
            continue
        if not isinstance(item, dict):
            continue
        test = item.get("test") or item.get("nodeid") or item.get("name")
        if not isinstance(test, str):
            continue
        parsed[test] = {
            "status": "flake",
            "cause": item.get("cause", "rerun_recovered"),
            "seed": item.get("seed", ""),
            "bucket": item.get("bucket", "unknown"),
            "artifact_ref": item.get("artifact_ref", ""),
            "pack_command": item.get("pack_command"),
        }
    return parsed


def _map_test_to_memberships(test_file: str | None, memberships: list[CommandMembership]) -> list[CommandMembership]:
    if not test_file:
        return []
    return [membership for membership in memberships if test_file in membership.test_files]


def _read_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        striped = line.strip()
        if not striped:
            continue
        events.append(json.loads(striped))
    return events


def _append_events(path: Path, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def _derive_capability_run_statuses(
    memberships: list[CommandMembership], results: list[TestResult], rerun_meta: dict[str, dict[str, Any]]
) -> dict[str, str]:
    statuses: dict[str, str] = {membership.capability_id: "pass" for membership in memberships}

    def _apply(capability_id: str, status: str) -> None:
        current = statuses.get(capability_id, "pass")
        if current == "fail":
            return
        if status == "fail":
            statuses[capability_id] = "fail"
        elif status == "flake" and current != "fail":
            statuses[capability_id] = "flake"

    for result in results:
        mapped = _map_test_to_memberships(result.test_file, memberships)
        if result.status == "fail":
            for membership in mapped:
                _apply(membership.capability_id, "fail")
        if result.test in rerun_meta:
            for membership in mapped:
                _apply(membership.capability_id, "flake")

    for rerun_test, _meta in rerun_meta.items():
        if "::" in rerun_test:
            test_file = rerun_test.split("::", 1)[0]
        else:
            test_file = None
        mapped = _map_test_to_memberships(test_file, memberships)
        for membership in mapped:
            _apply(membership.capability_id, "flake")

    return statuses


def _build_event(
    *,
    ts: str,
    ci_run: str,
    capability_id: str,
    pack_command: str,
    test: str,
    status: str,
    bucket: str,
    cause: str,
    seed: str,
    artifact_ref: str,
) -> dict[str, Any]:
    bucket_value = bucket if bucket in {"A", "B", "C"} else "unknown"
    event = {
        "ts": ts,
        "ci_run": ci_run,
        "capability_id": capability_id,
        "pack_command": pack_command,
        "test": test,
        "status": status if status in ALLOWED_STATUSES else "fail",
        "bucket": bucket_value,
        "cause": cause,
        "seed": seed,
        "artifact_ref": artifact_ref,
    }
    missing = REQUIRED_EVENT_KEYS - set(event)
    if missing:
        raise ValueError(f"Event missing required keys: {sorted(missing)}")
    return event


def _gather_failure_and_flake_events(
    *,
    ts: str,
    ci_run: str,
    artifact_ref: str,
    memberships: list[CommandMembership],
    results: list[TestResult],
    rerun_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for result in results:
        mapped = _map_test_to_memberships(result.test_file, memberships)
        if not mapped:
            continue
        if result.status == "fail":
            for membership in mapped:
                events.append(
                    _build_event(
                        ts=ts,
                        ci_run=ci_run,
                        capability_id=membership.capability_id,
                        pack_command=membership.pack_command,
                        test=result.test,
                        status="fail",
                        bucket="unknown",
                        cause=result.cause,
                        seed="",
                        artifact_ref=artifact_ref,
                    )
                )

    for test_name, meta in rerun_meta.items():
        test_file = test_name.split("::", 1)[0] if "::" in test_name else None
        mapped = _map_test_to_memberships(test_file, memberships)
        if not mapped:
            continue
        for membership in mapped:
            events.append(
                _build_event(
                    ts=ts,
                    ci_run=ci_run,
                    capability_id=membership.capability_id,
                    pack_command=(meta.get("pack_command") or membership.pack_command),
                    test=test_name,
                    status="flake",
                    bucket=str(meta.get("bucket", "unknown")),
                    cause=str(meta.get("cause", "rerun_recovered")),
                    seed=str(meta.get("seed", "")),
                    artifact_ref=str(meta.get("artifact_ref", artifact_ref)),
                )
            )

    return events


def _calculate_rates(
    history: list[dict[str, Any]], current_ci_run: str, current_statuses: dict[str, str], last_n_runs: int
) -> tuple[dict[str, tuple[float, float, int]], Counter[str], Counter[str]]:
    per_run_capability: dict[str, dict[str, str]] = defaultdict(dict)
    for event in history:
        ci_run = str(event.get("ci_run", ""))
        cap_id = event.get("capability_id")
        status = event.get("status")
        if not ci_run or not isinstance(cap_id, str) or status not in ALLOWED_STATUSES:
            continue
        current = per_run_capability[ci_run].get(cap_id, "pass")
        if current == "fail":
            continue
        if status == "fail":
            per_run_capability[ci_run][cap_id] = "fail"
        elif status == "flake" and current != "fail":
            per_run_capability[ci_run][cap_id] = "flake"
        else:
            per_run_capability[ci_run].setdefault(cap_id, "pass")

    per_run_capability[current_ci_run] = current_statuses

    run_order = sorted(per_run_capability.keys())[-last_n_runs:]
    by_capability: dict[str, list[str]] = defaultdict(list)
    top_failures: Counter[str] = Counter()
    buckets: Counter[str] = Counter()

    for event in history:
        if str(event.get("status")) == "fail":
            top_failures[str(event.get("test", "unknown"))] += 1
        if str(event.get("status")) in {"fail", "flake"}:
            buckets[str(event.get("bucket", "unknown"))] += 1

    for run in run_order:
        for capability_id, status in per_run_capability[run].items():
            by_capability[capability_id].append(status)

    rates: dict[str, tuple[float, float, int]] = {}
    for capability_id, statuses in by_capability.items():
        total = len(statuses)
        if total == 0:
            continue
        pass_rate = sum(1 for status in statuses if status == "pass") / total
        flaky_rate = sum(1 for status in statuses if status == "flake") / total
        rates[capability_id] = (pass_rate, flaky_rate, total)

    return rates, top_failures, buckets


def _render_summary(
    *,
    rates: dict[str, tuple[float, float, int]],
    top_failures: Counter[str],
    buckets: Counter[str],
    output_path: Path,
    last_n_runs: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reliability Summary",
        "",
        "## Per-capability pass rate",
        f"Computed across up to the last {last_n_runs} runs.",
        "",
        "| Capability ID | Pass rate | Runs |",
        "| --- | ---: | ---: |",
    ]

    for capability_id in sorted(rates):
        pass_rate, _flake_rate, run_count = rates[capability_id]
        lines.append(f"| {capability_id} | {pass_rate:.2%} | {run_count} |")

    lines.extend(
        [
            "",
            "## Per-capability flaky rate",
            "",
            "| Capability ID | Flaky rate | Runs |",
            "| --- | ---: | ---: |",
        ]
    )

    for capability_id in sorted(rates):
        _pass_rate, flaky_rate, run_count = rates[capability_id]
        lines.append(f"| {capability_id} | {flaky_rate:.2%} | {run_count} |")

    lines.extend(["", "## Top failing tests", ""])
    for test_name, count in top_failures.most_common(10):
        lines.append(f"- `{test_name}`: {count}")
    if not top_failures:
        lines.append("- None recorded.")

    lines.extend(["", "## A/B/C bucket counts", ""])
    for bucket in ("A", "B", "C", "unknown"):
        lines.append(f"- {bucket}: {buckets.get(bucket, 0)}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _default_ci_run() -> str:
    return os.environ.get("GITHUB_RUN_ID", "local")


def _default_timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reliability telemetry artifacts from CI test outputs.")
    parser.add_argument("--manifest", type=Path, default=Path("docs/dod_manifest.json"))
    parser.add_argument("--junit", action="append", type=Path, default=[])
    parser.add_argument("--junit-glob", default="artifacts/junit*.xml")
    parser.add_argument("--rerun-metadata", type=Path, default=None)
    parser.add_argument("--history", type=Path, default=Path("docs/reliability/flaky_history.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("artifacts/reliability_summary.md"))
    parser.add_argument("--ci-run", default=_default_ci_run())
    parser.add_argument("--artifact-ref", default="")
    parser.add_argument("--last-n-runs", type=int, default=20)
    parser.add_argument("--timestamp", default=_default_timestamp())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    memberships = _load_manifest(args.manifest)

    junit_paths = list(args.junit)
    if args.junit_glob:
        junit_paths.extend(sorted(Path().glob(args.junit_glob)))
    results = _parse_junit_results(junit_paths)

    rerun_meta = _parse_rerun_metadata(args.rerun_metadata)
    new_events = _gather_failure_and_flake_events(
        ts=args.timestamp,
        ci_run=str(args.ci_run),
        artifact_ref=str(args.artifact_ref),
        memberships=memberships,
        results=results,
        rerun_meta=rerun_meta,
    )

    _append_events(args.history, new_events)
    history = _read_history(args.history)

    current_statuses = _derive_capability_run_statuses(memberships, results, rerun_meta)
    rates, top_failures, buckets = _calculate_rates(
        history=history,
        current_ci_run=str(args.ci_run),
        current_statuses=current_statuses,
        last_n_runs=max(1, args.last_n_runs),
    )
    _render_summary(
        rates=rates,
        top_failures=top_failures,
        buckets=buckets,
        output_path=args.summary,
        last_n_runs=max(1, args.last_n_runs),
    )


if __name__ == "__main__":
    main()
