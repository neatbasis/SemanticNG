#!/usr/bin/env python3
"""Validate 5S metrics spec structure/sanity and emit deterministic CI reports."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT / "docs" / "process" / "5s_metrics.json"
DEFAULT_MD_REPORT = ROOT / "artifacts" / "5s_metrics_validation.md"
DEFAULT_JSON_REPORT = ROOT / "artifacts" / "5s_metrics_validation.json"

VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_ENFORCEMENT_MODES = {"measure-only", "blocking"}
VALID_OPERATORS = {">=", ">", "<=", "<"}
EXPECTED_FIELDS = {
    "s",
    "metric_id",
    "definition",
    "source_of_truth",
    "target_threshold",
    "breach_severity",
    "enforcement_mode",
}


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_threshold(metric: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    metric_id = metric.get("metric_id", "<unknown>")
    threshold = metric.get("target_threshold")

    if not isinstance(threshold, dict):
        errors.append(f"{metric_id}: target_threshold must be an object")
        return

    for field in ("operator", "value", "unit"):
        if field not in threshold:
            errors.append(f"{metric_id}: target_threshold missing '{field}'")

    operator = threshold.get("operator")
    value = threshold.get("value")
    unit = threshold.get("unit")

    if operator not in VALID_OPERATORS:
        errors.append(f"{metric_id}: target_threshold.operator must be one of {sorted(VALID_OPERATORS)}")

    if not _is_number(value) or not math.isfinite(float(value)):
        errors.append(f"{metric_id}: target_threshold.value must be a finite number")
    elif value < 0 and unit in {"%", "count", "days"}:
        errors.append(f"{metric_id}: target_threshold.value must be >= 0 for unit '{unit}'")

    if not isinstance(unit, str) or not unit.strip():
        errors.append(f"{metric_id}: target_threshold.unit must be a non-empty string")

    if unit == "%" and _is_number(value) and not (0 <= float(value) <= 100):
        errors.append(f"{metric_id}: percentage thresholds must be in [0, 100]")

    if unit == "count" and _is_number(value) and int(value) != value:
        warnings.append(f"{metric_id}: count threshold is non-integer ({value})")


def _validate_metrics(payload: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if "spec_version" not in payload:
        errors.append("root: missing spec_version")

    window = payload.get("stabilization_window")
    if not isinstance(window, dict):
        errors.append("root: stabilization_window must be an object")
    else:
        non_blocking_until = window.get("non_blocking_until")
        if not isinstance(non_blocking_until, str):
            errors.append("root: stabilization_window.non_blocking_until must be an ISO date string")
        else:
            try:
                date.fromisoformat(non_blocking_until)
            except ValueError:
                errors.append("root: stabilization_window.non_blocking_until must be YYYY-MM-DD")

    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        errors.append("root: metrics must be a non-empty array")
        return ValidationResult(errors, warnings)

    ids_seen: set[str] = set()

    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            errors.append(f"metrics[{index}]: metric must be an object")
            continue

        missing = [field for field in EXPECTED_FIELDS if field not in metric]
        for field in missing:
            errors.append(f"metrics[{index}]: missing field '{field}'")

        metric_id = metric.get("metric_id")
        if not isinstance(metric_id, str) or not metric_id.strip():
            errors.append(f"metrics[{index}]: metric_id must be a non-empty string")
            metric_id = f"metrics[{index}]"
        elif metric_id in ids_seen:
            errors.append(f"{metric_id}: duplicate metric_id")
        else:
            ids_seen.add(metric_id)

        if metric.get("breach_severity") not in VALID_SEVERITIES:
            errors.append(f"{metric_id}: breach_severity must be one of {sorted(VALID_SEVERITIES)}")

        mode = metric.get("enforcement_mode")
        if mode not in VALID_ENFORCEMENT_MODES:
            errors.append(f"{metric_id}: enforcement_mode must be one of {sorted(VALID_ENFORCEMENT_MODES)}")

        if mode == "blocking" and metric.get("breach_severity") == "low":
            warnings.append(f"{metric_id}: blocking metric has low breach_severity")

        for text_field in ("s", "definition", "source_of_truth"):
            value = metric.get(text_field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{metric_id}: {text_field} must be a non-empty string")

        _validate_threshold(metric, errors, warnings)

    return ValidationResult(errors, warnings)


def _effective_mode(payload: dict[str, Any], mode: str) -> str:
    if mode in {"measure-only", "blocking"}:
        return mode

    non_blocking_until = payload["stabilization_window"]["non_blocking_until"]
    cutoff = date.fromisoformat(non_blocking_until)
    return "blocking" if date.today() > cutoff else "measure-only"


def _write_reports(
    *,
    payload: dict[str, Any],
    result: ValidationResult,
    effective_mode: str,
    report_md: Path,
    report_json: Path,
) -> None:
    metrics = sorted(payload.get("metrics", []), key=lambda item: item.get("metric_id", ""))

    report_data = {
        "effective_mode": effective_mode,
        "error_count": len(result.errors),
        "warning_count": len(result.warnings),
        "errors": result.errors,
        "warnings": result.warnings,
        "metrics": metrics,
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# 5S metrics validation report",
        "",
        f"- Effective enforcement mode: `{effective_mode}`",
        f"- Errors: `{len(result.errors)}`",
        f"- Warnings: `{len(result.warnings)}`",
        "",
        "## Metrics (deterministic order)",
        "",
        "| Metric ID | S | Threshold | Severity | Mode |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in metrics:
        threshold = item.get("target_threshold", {})
        threshold_text = f"{threshold.get('operator', '?')} {threshold.get('value', '?')} {threshold.get('unit', '?')}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("metric_id", "")),
                    str(item.get("s", "")),
                    threshold_text,
                    str(item.get("breach_severity", "")),
                    str(item.get("enforcement_mode", "")),
                ]
            )
            + " |"
        )

    if result.errors:
        lines.extend(["", "## Errors", ""] + [f"- {msg}" for msg in result.errors])

    if result.warnings:
        lines.extend(["", "## Warnings", ""] + [f"- {msg}" for msg in result.warnings])

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--enforce-mode",
        choices=["auto", "measure-only", "blocking"],
        default="auto",
        help="auto uses stabilization_window.non_blocking_until to switch from measure-only to blocking",
    )
    args = parser.parse_args()

    payload = _load_json(args.spec)
    validation = _validate_metrics(payload)
    effective_mode = _effective_mode(payload, args.enforce_mode)
    _write_reports(
        payload=payload,
        result=validation,
        effective_mode=effective_mode,
        report_md=args.report_md,
        report_json=args.report_json,
    )

    print(
        f"5S metrics validation complete: mode={effective_mode}, "
        f"errors={len(validation.errors)}, warnings={len(validation.warnings)}"
    )

    if effective_mode == "blocking" and validation.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
