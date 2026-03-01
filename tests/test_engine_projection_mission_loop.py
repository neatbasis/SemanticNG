from __future__ import annotations

from collections.abc import Callable

from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.contracts import (
    AskResult,
    BeliefState,
    Episode,
    PredictionRecord,
    ProjectionState,
    VerbosityDecision,
)
from state_renormalization.engine import (
    append_turn_summary,
    evaluate_invariant_gates,
    run_mission_loop,
)


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
    assert any(a.get("artifact_kind") == "prediction_emit" for a in ep_out.artifacts)
    assert any(a.get("artifact_kind") == "turn_summary" for a in ep_out.artifacts)
    assert any(a.get("artifact_kind") == "prediction_comparison" for a in ep_out.artifacts)
    assert any(a.get("artifact_kind") == "prediction_update" for a in ep_out.artifacts)
    assert ep_out.observations
    assert any(a.get("artifact_kind") == "turn_summary" for a in ep_out.artifacts)
    assert projection_out.correction_metrics.get("comparisons", 0.0) >= 1.0

    events = [rec for _, rec in read_jsonl(tmp_path / "predictions.jsonl")]
    prediction_event = events[0]
    assert prediction_event["episode_id"] == ep.episode_id
    assert prediction_event["conversation_id"] == ep.conversation_id
    assert prediction_event["turn_index"] == ep.turn_index
    event_kinds = {evt["event_kind"] for evt in events}
    assert event_kinds.issubset({"prediction", "prediction_record"})
    assert "prediction_record" in event_kinds


def test_run_mission_loop_emits_turn_prediction_when_no_pending_predictions(
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

    assert "turn:0" in projection_out.current_predictions
    assert len(ep_out.observations) == 1
    assert ep_out.observations[0].type.value == "user_utterance"
    assert any(a.get("artifact_kind") == "prediction_emit" for a in ep_out.artifacts)


def test_append_turn_summary_includes_halts_for_operator_handoff(
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    ep = make_episode(
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="turn on the kitchen light"),
    )
    ep.artifacts.append(
        {
            "artifact_kind": "halt_observation",
            "halt_id": "halt:abc",
            "stage": "pre-output",
            "invariant_id": "evidence_link_completeness.v1",
            "reason": "missing evidence",
            "retryability": True,
            "timestamp": "2026-02-13T00:00:00+00:00",
            "halt_evidence_ref": {"kind": "jsonl", "ref": "halts.jsonl@1"},
        }
    )

    append_turn_summary(ep)

    summary = next(a for a in ep.artifacts if a.get("artifact_kind") == "turn_summary")
    assert summary["halt_count"] == 1
    assert summary["halts"][0]["halt_id"] == "halt:abc"
    assert summary["operator_action"] == "review_halts_then_resume_next_turn"


def test_run_mission_loop_timeout_intervention_short_circuits(
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

    def intervention_hook(**_kwargs):
        return {"action": "timeout", "reason": "operator timeout"}

    ep_out, _, projection_out = run_mission_loop(
        ep,
        belief,
        projection,
        intervention_hook=intervention_hook,
    )

    assert projection_out.current_predictions == {}
    assert any(
        a.get("artifact_kind") == "intervention_lifecycle" and a.get("action") == "timeout"
        for a in ep_out.artifacts
    )
    assert any(a.get("artifact_kind") == "turn_summary" for a in ep_out.artifacts)


def test_evaluate_invariant_gates_persists_complete_audit_shape_for_continue_and_stop(
    make_episode: Callable[..., Episode],
    make_observer,
    tmp_path,
) -> None:
    continue_ep = make_episode()
    continue_projection = ProjectionState(
        current_predictions={
            "scope:ok": PredictionRecord.model_validate(
                {
                    "prediction_id": "pred:ok",
                    "scope_key": "scope:ok",
                    "filtration_id": "conversation:c1",
                    "target_variable": "user_response_present",
                    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
                    "issued_at_iso": "2026-02-13T00:00:00+00:00",
                }
            )
        },
        updated_at_iso="2026-02-13T00:00:00+00:00",
    )
    evaluate_invariant_gates(
        ep=continue_ep,
        scope="scope:ok",
        prediction_key="scope:ok",
        projection_state=continue_projection,
        prediction_log_available=True,
        gate_point="pre-output",
        just_written_prediction={
            "key": "scope:ok",
            "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        },
        halt_log_path=tmp_path / "halts.jsonl",
    )

    stop_ep = make_episode()
    evaluate_invariant_gates(
        ep=stop_ep,
        scope="scope:stop",
        prediction_key=None,
        projection_state=ProjectionState(
            current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"
        ),
        prediction_log_available=True,
        gate_point="pre-decision",
        halt_log_path=tmp_path / "halts-stop.jsonl",
    )

    continue_audit = next(
        a for a in continue_ep.artifacts if a.get("artifact_kind") == "invariant_outcomes"
    )
    stop_audit = next(
        a for a in stop_ep.artifacts if a.get("artifact_kind") == "invariant_outcomes"
    )

    required = {
        "gate_point",
        "invariant_id",
        "passed",
        "reason",
        "flow",
        "validity",
        "code",
        "evidence",
        "details",
        "action_hints",
    }
    for bundle in (
        continue_audit["invariant_checks"],
        stop_audit["invariant_checks"],
        continue_audit["invariant_audit"],
        stop_audit["invariant_audit"],
    ):
        assert bundle
        for item in bundle:
            assert required.issubset(item)
