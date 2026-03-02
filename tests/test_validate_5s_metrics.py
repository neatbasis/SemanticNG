from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ci" / "validate_5s_metrics.py"


spec = importlib.util.spec_from_file_location("validate_5s_metrics", MODULE_PATH)
assert spec and spec.loader
validate_5s_metrics = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validate_5s_metrics
spec.loader.exec_module(validate_5s_metrics)


def _valid_payload(non_blocking_until: str = "2999-01-01") -> dict[str, object]:
    return {
        "spec_version": "1.0",
        "stabilization_window": {"non_blocking_until": non_blocking_until},
        "metrics": [
            {
                "s": "sort",
                "metric_id": "sort-open-items",
                "definition": "Open items older than SLA",
                "source_of_truth": "warehouse",
                "target_threshold": {"operator": "<=", "value": 3, "unit": "count"},
                "breach_severity": "medium",
                "enforcement_mode": "measure-only",
            }
        ],
    }


def _run_main(tmp_path: Path, payload: dict[str, object], enforce_mode: str) -> tuple[int, dict[str, object]]:
    spec_path = tmp_path / "spec.json"
    report_md = tmp_path / "report.md"
    report_json = tmp_path / "report.json"
    spec_path.write_text(json.dumps(payload), encoding="utf-8")

    argv = [
        "validate_5s_metrics.py",
        "--spec",
        str(spec_path),
        "--report-md",
        str(report_md),
        "--report-json",
        str(report_json),
        "--enforce-mode",
        enforce_mode,
    ]

    original_argv = validate_5s_metrics.sys.argv
    try:
        validate_5s_metrics.sys.argv = argv
        exit_code = validate_5s_metrics.main()
    finally:
        validate_5s_metrics.sys.argv = original_argv

    return exit_code, json.loads(report_json.read_text(encoding="utf-8"))


def test_happy_path_spec_acceptance() -> None:
    result = validate_5s_metrics._validate_metrics(_valid_payload())

    assert result.errors == []
    assert result.warnings == []


def test_required_fields_and_enum_failures() -> None:
    payload = _valid_payload()
    metric = payload["metrics"][0]
    del metric["definition"]
    metric["breach_severity"] = "urgent"
    metric["enforcement_mode"] = "auto"

    result = validate_5s_metrics._validate_metrics(payload)

    assert any("missing field 'definition'" in error for error in result.errors)
    assert any("breach_severity must be one of" in error for error in result.errors)
    assert any("enforcement_mode must be one of" in error for error in result.errors)


def test_threshold_validation_edge_cases() -> None:
    payload = _valid_payload()
    base_metric = payload["metrics"][0]
    payload["metrics"] = [
        {
            **deepcopy(base_metric),
            "metric_id": "pct-underflow",
            "target_threshold": {"operator": "<=", "value": -1, "unit": "%"},
        },
        {
            **deepcopy(base_metric),
            "metric_id": "pct-overflow",
            "target_threshold": {"operator": "<=", "value": 101, "unit": "%"},
        },
        {
            **deepcopy(base_metric),
            "metric_id": "nan-threshold",
            "target_threshold": {"operator": "<=", "value": float("nan"), "unit": "days"},
        },
        {
            **deepcopy(base_metric),
            "metric_id": "neg-count",
            "target_threshold": {"operator": "<=", "value": -5, "unit": "count"},
        },
        {
            **deepcopy(base_metric),
            "metric_id": "neg-days",
            "target_threshold": {"operator": "<=", "value": -2, "unit": "days"},
        },
    ]

    result = validate_5s_metrics._validate_metrics(payload)

    assert any("pct-underflow: percentage thresholds must be in [0, 100]" in err for err in result.errors)
    assert any("pct-overflow: percentage thresholds must be in [0, 100]" in err for err in result.errors)
    assert any("nan-threshold: target_threshold.value must be a finite number" in err for err in result.errors)
    assert any("neg-count: target_threshold.value must be >= 0 for unit 'count'" in err for err in result.errors)
    assert any("neg-days: target_threshold.value must be >= 0 for unit 'days'" in err for err in result.errors)


def test_duplicate_metric_id_rejection() -> None:
    payload = _valid_payload()
    metric = payload["metrics"][0]
    payload["metrics"] = [metric, deepcopy(metric)]

    result = validate_5s_metrics._validate_metrics(payload)

    assert any("duplicate metric_id" in error for error in result.errors)


def test_auto_enforce_mode_respects_stabilization_window(tmp_path: Path) -> None:
    future_code, future_report = _run_main(tmp_path, _valid_payload("2999-01-01"), "auto")
    past_code, past_report = _run_main(tmp_path, _valid_payload("2000-01-01"), "auto")

    assert future_code == 0
    assert future_report["effective_mode"] == "measure-only"
    assert past_code == 0
    assert past_report["effective_mode"] == "blocking"


def test_blocking_mode_exits_nonzero_when_errors_exist(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["metrics"] = []

    exit_code, report = _run_main(tmp_path, payload, "blocking")

    assert exit_code == 1
    assert report["error_count"] > 0
