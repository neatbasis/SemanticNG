from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.contracts import AskStatus, BeliefState, PredictionRecord, ProjectionState, RepairResolution
from state_renormalization.engine import run_mission_loop
from state_renormalization.invariants import InvariantHandlingMode


def _seed_projection() -> ProjectionState:
    pred = PredictionRecord.model_validate(
        {
            "prediction_id": "pred:policy",
            "scope_key": "turn:1",
            "prediction_key": "turn:1:user_response_present",
            "prediction_target": "user_response_present",
            "filtration_id": "conversation:c1",
            "target_variable": "user_response_present",
            "target_horizon_iso": "2026-02-13T00:00:00+00:00",
            "expectation": 0.1,
            "issued_at_iso": "2026-02-13T00:00:00+00:00",
        }
    )
    return ProjectionState(current_predictions={pred.scope_key: pred}, prediction_history=[pred], updated_at_iso=pred.issued_at_iso)


def test_repair_acceptance_policy_can_reject_proposals(make_episode, make_ask_result, tmp_path: Path) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    ep = make_episode(conversation_id="conv:reject", turn_index=1, ask=make_ask_result(status=AskStatus.OK, sentence="yes"))

    _, _, projection = run_mission_loop(
        ep,
        BeliefState(),
        _seed_projection(),
        pending_predictions=[],
        prediction_log_path=prediction_log,
        invariant_handling_mode=InvariantHandlingMode.REPAIR_EVENTS,
        repair_acceptance_policy=lambda _proposal: RepairResolution.REJECTED,
    )

    rows = [json.loads(line) for line in prediction_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    resolution = next(row for row in rows if row.get("event_kind") == "repair_resolution")

    assert resolution["decision"] == "rejected"
    assert resolution["accepted_prediction"] is None
    assert projection.current_predictions["turn:1"].correction_revision == 0
