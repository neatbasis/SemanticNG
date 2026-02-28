import json
import subprocess
import sys
from pathlib import Path


def _write_junit(path: Path) -> None:
    path.write_text(
        """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<testsuites>
  <testsuite name=\"pytest\" tests=\"2\" failures=\"1\">
    <testcase classname=\"tests.test_stable_ids\" name=\"test_ok\" file=\"tests/test_stable_ids.py\" />
    <testcase classname=\"tests.test_stable_ids\" name=\"test_bad\" file=\"tests/test_stable_ids.py\">
      <failure message=\"assert 1 == 2\">traceback</failure>
    </testcase>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )


def test_reliability_history_event_schema_and_summary_headings(tmp_path: Path) -> None:
    junit_path = tmp_path / "junit.xml"
    rerun_path = tmp_path / "rerun.json"
    history_path = tmp_path / "flaky_history.jsonl"
    summary_path = tmp_path / "reliability_summary.md"

    _write_junit(junit_path)
    rerun_path.write_text(
        json.dumps(
            {
                "flaky_tests": [
                    {
                        "test": "tests/test_stable_ids.py::test_ok",
                        "bucket": "B",
                        "cause": "intermittent_network",
                        "seed": "12345",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    command = [
        sys.executable,
        ".github/scripts/reliability_report.py",
        "--manifest",
        "docs/dod_manifest.json",
        "--junit",
        str(junit_path),
        "--rerun-metadata",
        str(rerun_path),
        "--history",
        str(history_path),
        "--summary",
        str(summary_path),
        "--ci-run",
        "run-1",
        "--artifact-ref",
        "artifact://unit-test",
        "--timestamp",
        "2026-01-01T00:00:00+00:00",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "Expected at least one failure/flake history event"

    required_keys = {
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

    for raw in lines:
        event = json.loads(raw)
        assert required_keys.issubset(event), event
        assert event["status"] in {"pass", "fail", "flake"}
        assert event["bucket"] in {"A", "B", "C", "unknown"}

    summary = summary_path.read_text(encoding="utf-8")
    assert "## Per-capability pass rate" in summary
    assert "## Per-capability flaky rate" in summary
    assert "## Top failing tests" in summary
    assert "## A/B/C bucket counts" in summary
