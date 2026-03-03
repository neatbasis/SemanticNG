from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl
from state_renormalization.read_model import (
    project_episode_scope_read_model,
    project_episode_scope_read_model_json,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "read_model_report.py"


def _write_fixture_logs(tmp_path: Path) -> tuple[Path, Path]:
    episode_log = tmp_path / "episodes.jsonl"
    prediction_log = tmp_path / "predictions.jsonl"

    append_jsonl(
        episode_log,
        {
            "episode_id": "ep:1",
            "conversation_id": "conv:1",
            "turn_index": 1,
            "t_asked_iso": "2026-01-01T00:00:00+00:00",
            "assistant_prompt_asked": "prompt",
            "policy_decision": {
                "decision_id": "dec:1",
                "hypothesis": "keep concise",
                "reason_codes": ["mission.loop.normal"],
                "channel": "dialog",
            },
            "ask": {"status": "ok", "answer": "yes", "error": None},
            "observations": [],
            "effects": [],
            "artifacts": [
                {
                    "artifact_kind": "invariant_outcomes",
                    "scope": "turn:1",
                    "kind": "halt",
                    "invariant_checks": [
                        {
                            "gate_point": "pre_consume",
                            "invariant_id": "prediction_availability.v1",
                            "passed": False,
                            "flow": "stop",
                            "code": "prediction_missing",
                            "reason": "prediction missing for scope",
                            "evidence": [{"kind": "scope", "ref": "turn:1"}],
                        }
                    ],
                    "halt": {
                        "halt_id": "halt:1",
                        "stage": "gate:pre_consume",
                        "invariant_id": "prediction_availability.v1",
                        "reason": "prediction missing",
                        "details": {"scope": "turn:1"},
                        "evidence": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
                        "retryability": True,
                        "timestamp": "2026-01-01T00:00:02+00:00",
                    },
                    "halt_evidence_ref": {"kind": "jsonl", "ref": "halts.jsonl@1"},
                }
            ],
        },
    )

    append_jsonl(
        prediction_log,
        {
            "event_kind": "prediction",
            "episode_id": "ep:1",
            "prediction_id": "pred:1",
            "scope_key": "turn:1",
            "prediction_key": "turn:1:user_response_present",
            "expectation": 0.25,
            "issued_at_iso": "2026-01-01T00:00:01+00:00",
            "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        },
    )

    append_jsonl(
        prediction_log,
        {
            "event_kind": "prediction_record",
            "episode_id": "ep:1",
            "prediction_id": "pred:1",
            "scope_key": "turn:1",
            "prediction_key": "turn:1:user_response_present",
            "expectation": 0.25,
            "issued_at_iso": "2026-01-01T00:00:01+00:00",
            "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        },
    )

    return episode_log, prediction_log


def test_project_episode_scope_read_model_has_stable_top_level_shape(tmp_path: Path) -> None:
    episode_log, prediction_log = _write_fixture_logs(tmp_path)

    report = project_episode_scope_read_model(
        episode_log_path=episode_log,
        prediction_log_path=prediction_log,
        episode_id="ep:1",
        scope="turn:1",
    )

    assert list(report) == [
        "episode_id",
        "scope",
        "prediction_used",
        "invariants_evaluated",
        "policy_decision",
        "halt_continue_rationale",
        "evidence_refs",
        "answer_provenance",
    ]
    assert report["episode_id"] == "ep:1"
    assert report["scope"] == "turn:1"
    assert report["policy_decision"]["decision_id"] == "dec:1"
    assert report["halt_continue_rationale"]["outcome"] == "halt"
    assert report["prediction_used"]["prediction_id"] == "pred:1"
    assert report["answer_provenance"]["mode"] == "reconstructed"
    assert report["answer_provenance"]["temporal_invariant"] == {
        "invariant_id": "time_travel_answering.as_of.v1",
        "query_mode": "latest",
        "as_of_iso": None,
        "satisfied": True,
    }
    assert report["answer_provenance"]["context_snapshot_ref"] == "missing:context_snapshot"
    assert report["answer_provenance"]["missing_artifact_disclosures"] == [
        {
            "artifact_role": "context_snapshot",
            "disclosure": "No persisted context_snapshot artifact found; answer was reconstructed without snapshot grounding.",
        }
    ]


def test_project_episode_scope_read_model_json_is_deterministic(tmp_path: Path) -> None:
    episode_log, prediction_log = _write_fixture_logs(tmp_path)

    first = project_episode_scope_read_model_json(
        episode_log_path=episode_log,
        prediction_log_path=prediction_log,
        episode_id="ep:1",
        scope="turn:1",
    )
    second = project_episode_scope_read_model_json(
        episode_log_path=episode_log,
        prediction_log_path=prediction_log,
        episode_id="ep:1",
        scope="turn:1",
    )

    assert first == second
    parsed = json.loads(first)
    assert parsed["invariants_evaluated"][0]["invariant_id"] == "prediction_availability.v1"


def test_cli_report_emits_json(tmp_path: Path) -> None:
    episode_log, prediction_log = _write_fixture_logs(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--episode-log",
            str(episode_log),
            "--prediction-log",
            str(prediction_log),
            "--episode-id",
            "ep:1",
            "--scope",
            "turn:1",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["episode_id"] == "ep:1"
    assert payload["scope"] == "turn:1"


def test_project_episode_scope_read_model_as_of_fails_closed_on_future_artifact(
    tmp_path: Path,
) -> None:
    episode_log, prediction_log = _write_fixture_logs(tmp_path)
    append_jsonl(
        prediction_log,
        {
            "event_kind": "prediction",
            "episode_id": "ep:1",
            "prediction_id": "pred:future",
            "scope_key": "turn:1",
            "issued_at_iso": "2026-01-01T00:10:00+00:00",
        },
    )

    try:
        project_episode_scope_read_model(
            episode_log_path=episode_log,
            prediction_log_path=prediction_log,
            episode_id="ep:1",
            scope="turn:1",
            query_mode="as_of",
            as_of_iso="2026-01-01T00:05:00+00:00",
        )
    except ValueError as exc:
        assert "temporal constraints cannot be satisfied" in str(exc)
    else:
        raise AssertionError("expected as_of read-model projection to fail closed")


def test_strict_replay_mode_fails_when_historical_output_artifact_is_absent(tmp_path: Path) -> None:
    episode_log, prediction_log = _write_fixture_logs(tmp_path)

    try:
        project_episode_scope_read_model(
            episode_log_path=episode_log,
            prediction_log_path=prediction_log,
            episode_id="ep:1",
            scope="turn:1",
            answer_mode="strict_replay",
            historical_output_artifact_ref="predictions.jsonl@999",
        )
    except ValueError as exc:
        assert "strict_replay mode requires a persisted historical output artifact reference" in str(exc)
    else:
        raise AssertionError("expected strict replay to fail when historical output artifact is absent")
