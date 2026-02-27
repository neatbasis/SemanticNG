from __future__ import annotations

from collections.abc import Callable

from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.contracts import (
    AskResult,
    BeliefState,
    Episode,
    ProjectionState,
    VerbosityDecision,
)
from state_renormalization.engine import run_mission_loop


def test_run_mission_loop_updates_projection_before_decision_stages(
    tmp_path,
    belief: BeliefState,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    ep = make_episode(
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="turn on the kitchen light"),
    )
    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    ep_out, _, projection_out = run_mission_loop(
        ep,
        belief,
        projection,
        pending_predictions=[
            {
                "prediction_id": "pred:test",
                "scope_key": "room:kitchen:light",
                "filtration_id": "filt:1",
                "target_variable": "light_on",
                "target_horizon_iso": "2026-02-13T00:05:00+00:00",
                "expectation": 0.7,
                "variance": 0.21,
                "issued_at_iso": "2026-02-13T00:00:00+00:00",
                "valid_from_iso": "2026-02-13T00:00:00+00:00",
                "valid_until_iso": "2026-02-13T00:10:00+00:00",
                "assumptions": ["prediction_availability.v1"],
                "evidence_refs": [],
            }
        ],
        prediction_log_path=tmp_path / "predictions.jsonl",
    )

    assert "room:kitchen:light" in projection_out.current_predictions
    assert any(a.get("artifact_kind") == "prediction_update" for a in ep_out.artifacts)
    assert ep_out.observations

    (_, prediction_event), = list(read_jsonl(tmp_path / "predictions.jsonl"))
    assert prediction_event["episode_id"] == ep.episode_id
    assert prediction_event["conversation_id"] == ep.conversation_id
    assert prediction_event["turn_index"] == ep.turn_index


def test_run_mission_loop_halts_before_downstream_decision_without_predictions(
    belief: BeliefState,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    ep = make_episode(
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="turn on the kitchen light"),
    )
    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    ep_out, _, projection_out = run_mission_loop(ep, belief, projection)

    assert projection_out.current_predictions == {}
    assert len(ep_out.observations) == 1
    assert ep_out.observations[0].type.value == "halt"
    assert any(a.get("artifact_kind") == "invariant_outcomes" and a.get("kind") == "halt" for a in ep_out.artifacts)
