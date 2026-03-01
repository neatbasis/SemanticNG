from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from state_renormalization.adapters.persistence import iter_projection_lineage_records, read_jsonl
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

    lifecycle_artifacts = [
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"
    ]
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
        intervention_hook=lambda **_: InterventionDecision(
            action=InterventionAction.PAUSE, reason="operator_pause"
        ),
    )

    assert any(
        a.get("artifact_kind") == "intervention_lifecycle"
        and a.get("phase") == "mission_loop:start"
        for a in episode.artifacts
    )
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

    lifecycle_artifacts = [
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"
    ]
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
    response = next(
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_response"
    )
    lifecycle = next(
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"
    )
    terminal = next(
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_terminal"
    )

    assert (
        request["request_id"]
        == response["request_id"]
        == lifecycle["request_id"]
        == terminal["request_id"]
    )
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
        raise AssertionError(
            "Expected resume intervention without provenance to fail contract validation"
        )


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

    lifecycle = next(
        a for a in episode.artifacts if a.get("artifact_kind") == "intervention_lifecycle"
    )
    assert lifecycle["action"] == "resume"
    assert lifecycle["override_source"] == "operator"
    assert lifecycle["override_provenance"] == "ticket:ops-77"


class _RecordingAskOutboxAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_request(self, title: str, question: str, context: Mapping[str, object]) -> str:
        request_id = f"ask:{len(self.calls) + 1}"
        self.calls.append(
            {
                "title": title,
                "question": question,
                "context": dict(context),
                "request_id": request_id,
            }
        )
        return request_id


def test_hitl_outbox_allow_persists_append_only_request_response_events(
    make_episode: Callable[..., Episode],
    tmp_path: Path,
) -> None:
    episode = make_episode(conversation_id="conv:ask-allow", turn_index=1)
    outbox = _RecordingAskOutboxAdapter()
    log_path = tmp_path / "predictions.jsonl"

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        prediction_log_path=log_path,
        intervention_hook=lambda **_: {"action": "none", "reason": "continue"},
        ask_outbox_adapter=outbox,
    )

    assert len(outbox.calls) == 4
    request_artifacts = [
        a for a in episode.artifacts if a.get("artifact_kind") == "ask_outbox_request"
    ]
    response_artifacts = [
        a for a in episode.artifacts if a.get("artifact_kind") == "ask_outbox_response"
    ]
    assert len(request_artifacts) == len(response_artifacts) == 4

    log_rows = [row for _, row in read_jsonl(log_path)]
    outbox_rows = [
        r for r in log_rows if r.get("event_kind") in {"ask_outbox_request", "ask_outbox_response"}
    ]
    assert len(outbox_rows) == 8
    assert outbox_rows[0]["event_kind"] == "ask_outbox_request"
    assert outbox_rows[1]["event_kind"] == "ask_outbox_response"


def test_hitl_outbox_deny_uses_policy_guard_and_halts_without_dispatch(
    make_episode: Callable[..., Episode],
    make_observer: Callable[..., object],
    tmp_path: Path,
) -> None:
    observer = make_observer(capabilities=["baseline.invariant_evaluation"])
    episode = make_episode(conversation_id="conv:ask-deny", turn_index=1, observer=observer)
    outbox = _RecordingAskOutboxAdapter()
    prediction_log = tmp_path / "predictions.jsonl"
    halt_log = tmp_path / "halts.jsonl"

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        prediction_log_path=prediction_log,
        intervention_hook=lambda **_: {"action": "none"},
        ask_outbox_adapter=outbox,
        halt_log_path=halt_log,
    )

    assert outbox.calls == []
    assert any(a.get("artifact_kind") == "capability_policy_denial" for a in episode.artifacts)
    halt_rows = [row for _, row in read_jsonl(halt_log)]
    assert halt_rows[0]["details"]["policy_code"] == "observer_scope_denied"


def test_hitl_outbox_timeout_and_escalation_are_persisted_for_replay(
    make_episode: Callable[..., Episode],
    tmp_path: Path,
) -> None:
    episode = make_episode(conversation_id="conv:ask-timeout", turn_index=1)
    outbox = _RecordingAskOutboxAdapter()
    log_path = tmp_path / "predictions.jsonl"

    def hook(*, phase, **_kwargs):
        if phase == "mission_loop:start":
            return {"action": "timeout", "reason": "operator-timeout"}
        return {"action": "escalate", "reason": "manual-escalation"}

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        prediction_log_path=log_path,
        intervention_hook=hook,
        ask_outbox_adapter=outbox,
    )

    rows = list(iter_projection_lineage_records(log_path))
    response_rows = [r for r in rows if r.get("event_kind") == "ask_outbox_response"]
    assert response_rows
    assert response_rows[0]["status"] == "timeout"
