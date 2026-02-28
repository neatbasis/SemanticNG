from __future__ import annotations

import json
from pathlib import Path

from demos.reporting.convergence import build_convergence_report, write_convergence_report
from demos.run_scenario_sessions import (
    ScenarioSessionArtifact,
    ScenarioSessionBatch,
    write_scenario_session_batch,
)
from state_renormalization.adapters.persistence import append_halt, append_prediction_record_event
from state_renormalization.contracts import PredictionRecord


def _append_prediction(
    log_path: Path,
    *,
    prediction_id: str,
    issued_at_iso: str,
    compared_at_iso: str,
    absolute_error: float,
    root_prediction_id: str | None = None,
) -> None:
    append_prediction_record_event(
        PredictionRecord(
            prediction_id=prediction_id,
            prediction_key=f"{prediction_id}:key",
            scope_key=f"scope:{prediction_id}",
            prediction_target="user_response_present",
            filtration_id="conversation:demo",
            target_variable="user_response_present",
            target_horizon_iso="2026-02-13T00:00:00+00:00",
            expectation=1.0,
            issued_at_iso=issued_at_iso,
            compared_at_iso=compared_at_iso,
            observed_value=0.0,
            absolute_error=absolute_error,
            prediction_error=absolute_error,
            was_corrected=True,
            correction_root_prediction_id=root_prediction_id,
            corrected_at_iso=compared_at_iso,
        ),
        path=log_path,
    )


def test_convergence_report_integrates_session_outputs_with_replay_analytics(tmp_path: Path) -> None:
    log_a = tmp_path / "pack_a_session_1.jsonl"
    log_b = tmp_path / "pack_a_session_2.jsonl"

    _append_prediction(
        log_a,
        prediction_id="pred:a1",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        compared_at_iso="2026-02-13T00:01:00+00:00",
        absolute_error=0.5,
    )
    append_halt(
        log_a,
        {
            "halt_id": "halt:a",
            "stage": "pre_output_gate",
            "timestamp": "2026-02-13T00:01:30+00:00",
            "invariant_id": "prediction_availability.v1",
            "reason": "missing_prediction",
            "details": {"message": "missing evidence", "context": {"turn_index": 1}},
            "evidence": [],
            "retryability": True,
        },
    )

    _append_prediction(
        log_b,
        prediction_id="pred:a2",
        issued_at_iso="2026-02-13T00:02:00+00:00",
        compared_at_iso="2026-02-13T00:03:00+00:00",
        absolute_error=0.25,
        root_prediction_id="pred:a2-root",
    )

    sessions = ScenarioSessionBatch(
        generated_at_iso="2026-02-13T00:10:00+00:00",
        sessions=[
            ScenarioSessionArtifact(
                session_id="sess:a1",
                scenario_id="scn:a1",
                scenario_pack="pack-a",
                prediction_log_path=str(log_a),
                intervention_count=1,
            ),
            ScenarioSessionArtifact(
                session_id="sess:a2",
                scenario_id="scn:a2",
                scenario_pack="pack-a",
                prediction_log_path=str(log_b),
                intervention_count=0,
            ),
        ],
    )
    sessions_path = write_scenario_session_batch(output_path=tmp_path / "sessions.json", batch=sessions)

    report = build_convergence_report(sessions_path)

    assert report.total_sessions == 2
    assert report.total_halts == 1
    assert report.total_interventions == 1
    assert len(report.pack_reports) == 1

    pack = report.pack_reports[0]
    assert pack.scenario_pack == "pack-a"
    assert pack.halt_frequency == 0.5
    assert pack.intervention_frequency == 0.5
    assert pack.correction_count_trend == [1, 1]
    assert pack.correction_cost_total_trend == [0.5, 0.25]
    assert pack.correction_cost_mean_trend == [0.5, 0.25]


def test_convergence_report_persists_contract_payload(tmp_path: Path) -> None:
    log_path = tmp_path / "pack_b_session_1.jsonl"
    _append_prediction(
        log_path,
        prediction_id="pred:b1",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        compared_at_iso="2026-02-13T00:00:30+00:00",
        absolute_error=0.1,
    )

    sessions_path = write_scenario_session_batch(
        output_path=tmp_path / "sessions.json",
        batch=ScenarioSessionBatch(
            generated_at_iso="2026-02-13T00:11:00+00:00",
            sessions=[
                ScenarioSessionArtifact(
                    session_id="sess:b1",
                    scenario_id="scn:b1",
                    scenario_pack="pack-b",
                    prediction_log_path=str(log_path),
                    intervention_count=2,
                )
            ],
        ),
    )

    report_path = write_convergence_report(sessions_path=sessions_path, output_path=tmp_path / "convergence_report.json")
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["total_sessions"] == 1
    assert payload["total_interventions"] == 2
    assert payload["pack_reports"][0]["correction_cost_total_trend"] == [0.1]


def test_convergence_report_consumers_use_projection_replay_analytics_snapshot(tmp_path: Path) -> None:
    sessions_path = write_scenario_session_batch(
        output_path=tmp_path / "sessions.json",
        batch=ScenarioSessionBatch(
            generated_at_iso="2026-02-13T00:12:00+00:00",
            sessions=[
                ScenarioSessionArtifact(
                    session_id="sess:c1",
                    scenario_id="scn:c1",
                    scenario_pack="pack-c",
                    prediction_log_path="/tmp/unused.jsonl",
                    intervention_count=3,
                )
            ],
        ),
    )

    class _Snapshot:
        correction_count = 4
        correction_cost_total = 1.2
        correction_cost_mean = 0.3
        halt_count = 2

    class _ReplayResult:
        analytics_snapshot = _Snapshot()

    report = build_convergence_report(sessions_path, replay_loader=lambda _path: _ReplayResult())

    pack = report.pack_reports[0]
    assert pack.correction_count_trend == [4]
    assert pack.correction_cost_total_trend == [1.2]
    assert pack.correction_cost_mean_trend == [0.3]
    assert report.total_halts == 2
