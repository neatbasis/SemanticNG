from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from state_renormalization.contracts import (
    AskResult,
    AskStatus,
    BeliefState,
    Episode,
    InterventionAction,
    InterventionDecision,
    PredictionRecord,
    ProjectionState,
)
from state_renormalization.engine import run_mission_loop


FIXED_PENDING_PREDICTION = {
    "prediction_id": "pred:hitl",
    "scope_key": "turn:1",
    "prediction_key": "turn:1:user_response_present",
    "prediction_target": "user_response_present",
    "filtration_id": "conversation:hitl",
    "target_variable": "user_response_present",
    "target_horizon_iso": "2026-02-13T00:00:00+00:00",
    "expectation": 0.75,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
}


def _blank_projection() -> ProjectionState:
    return ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")


def test_hitl_hook_lifecycle_artifacts_are_emitted_in_expected_order(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    phases: list[str] = []

    def hook(*, phase, episode, belief, projection_state):
        phases.append(phase)
        return InterventionDecision(action=InterventionAction.NONE, reason="noop")

    episode = make_episode(
        conversation_id="conv:hitl-order",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="yes"),
    )

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=tmp_path / "predictions.jsonl",
        intervention_hook=hook,
    )

    expected_phases = [
        "mission_loop:start",
        "mission_loop:post_pre_decision_gate",
        "mission_loop:post_observation_gate",
        "mission_loop:post_pre_output_gate",
    ]
    assert phases == expected_phases

    lifecycle_artifacts = [a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"]
    assert [a["phase"] for a in lifecycle_artifacts] == expected_phases
    assert [a["action"] for a in lifecycle_artifacts] == ["none", "none", "none", "none"]
    for artifact in lifecycle_artifacts:
        assert set(artifact.keys()) >= {"artifact_kind", "phase", "action", "reason", "metadata"}


def test_hitl_pause_at_start_short_circuits_loop_but_preserves_turn_summary(
    make_episode: Callable[..., Episode],
) -> None:
    episode = make_episode(conversation_id="conv:hitl-pause", turn_index=1)

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        intervention_hook=lambda **_: InterventionDecision(action=InterventionAction.PAUSE, reason="operator_pause"),
    )

    assert any(a.get("artifact_kind") == "intervention_lifecycle" and a.get("phase") == "mission_loop:start" for a in episode.artifacts)
    assert any(a.get("artifact_kind") == "turn_summary" for a in episode.artifacts)
    assert not any(a.get("artifact_kind") == "prediction_emit" for a in episode.artifacts)


def test_hitl_mapping_decision_payload_is_normalized_and_timeout_halts_after_gate(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    def hook(*, phase, episode, belief, projection_state):
        if phase == "mission_loop:post_pre_decision_gate":
            return {
                "action": "timeout",
                "reason": "operator_timeout",
                "metadata": {"ticket": "ops:123"},
            }
        return {"action": "none"}

    episode = make_episode(
        conversation_id="conv:hitl-timeout",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="yes"),
    )

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        pending_predictions=[PredictionRecord.model_validate(FIXED_PENDING_PREDICTION)],
        prediction_log_path=tmp_path / "predictions.jsonl",
        intervention_hook=hook,
    )

    lifecycle_artifacts = [a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"]
    assert [a["phase"] for a in lifecycle_artifacts] == [
        "mission_loop:start",
        "mission_loop:post_pre_decision_gate",
    ]
    assert lifecycle_artifacts[-1]["action"] == "timeout"
    assert lifecycle_artifacts[-1]["metadata"] == {"ticket": "ops:123"}
    assert any(a.get("artifact_kind") == "turn_summary" for a in episode.artifacts)


def test_hitl_escalation_stops_loop_and_persists_request_response_artifacts(
    make_episode: Callable[..., Episode],
) -> None:
    episode = make_episode(conversation_id="conv:hitl-escalate", turn_index=1)

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        intervention_hook=lambda **_: {
            "action": "escalate",
            "reason": "needs-human-review",
            "metadata": {"queue": "tier2"},
        },
    )

    request = next(a for a in episode.artifacts if a.get("artifact_kind") == "intervention_request")
    response = next(a for a in episode.artifacts if a.get("artifact_kind") == "intervention_response")
    lifecycle = next(a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle")
    terminal = next(a for a in episode.artifacts if a.get("artifact_kind") == "intervention_terminal")

    assert request["request_id"] == response["request_id"] == lifecycle["request_id"] == terminal["request_id"]
    assert lifecycle["action"] == "escalate"
    assert response["response"]["metadata"] == {"queue": "tier2"}
    assert any(a.get("artifact_kind") == "turn_summary" for a in episode.artifacts)


def test_hitl_resume_requires_explicit_override_provenance(
    make_episode: Callable[..., Episode],
) -> None:
    episode = make_episode(conversation_id="conv:hitl-resume", turn_index=1)

    def invalid_resume(**_kwargs):
        return {"action": "resume", "reason": "force-continue"}

    try:
        run_mission_loop(
            episode,
            BeliefState(),
            _blank_projection(),
            intervention_hook=invalid_resume,
        )
    except ValueError as exc:
        assert "override_source" in str(exc)
    else:
        raise AssertionError("Expected resume intervention without provenance to fail contract validation")


def test_hitl_resume_with_override_provenance_is_persisted(
    make_episode: Callable[..., Episode],
) -> None:
    episode = make_episode(conversation_id="conv:hitl-resume-ok", turn_index=1)

    def hook(*, phase, **_kwargs):
        if phase == "mission_loop:start":
            return {
                "action": "resume",
                "reason": "manual override",
                "override_source": "operator",
                "override_provenance": "ticket:ops-77",
            }
        return {"action": "none"}

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        intervention_hook=hook,
    )

    lifecycle = next(a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle")
    assert lifecycle["action"] == "resume"
    assert lifecycle["override_source"] == "operator"
    assert lifecycle["override_provenance"] == "ticket:ops-77"
