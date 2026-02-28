from __future__ import annotations

from collections.abc import Callable

import pytest

from state_renormalization.contracts import (
    AskResult,
    BeliefState,
    EscalationTimeoutRule,
    Episode,
    InterventionRequest,
    InterventionResponseType,
    InterventionStatus,
    OperatorResponse,
    OverrideProvenance,
    ProjectionState,
    VerbosityDecision,
)
from state_renormalization.engine import run_mission_loop


def test_operator_override_requires_provenance() -> None:
    with pytest.raises(ValueError):
        OperatorResponse(
            intervention_id="intv:1",
            episode_id="ep:test",
            response_type=InterventionResponseType.OVERRIDE,
            provided_at_iso="2026-02-13T00:00:00+00:00",
            approved=True,
        )


def test_run_mission_loop_pauses_with_intervention_request(
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

    request = InterventionRequest(
        intervention_id="intv:1",
        episode_id=ep.episode_id,
        conversation_id=ep.conversation_id,
        turn_index=ep.turn_index,
        requested_at_iso="2026-02-13T00:00:00+00:00",
        reason="requires_approval",
        prompt="Approve unlocking front door?",
        context={"device_id": "front-door"},
        timeout_rule=EscalationTimeoutRule(
            timeout_seconds=60,
            max_timeouts_before_escalation=1,
            escalation_target="oncall_supervisor",
        ),
        timeout_count=1,
    )

    ep_out, _, projection_out = run_mission_loop(
        ep,
        belief,
        projection,
        intervention_request=request,
    )

    assert projection_out == projection
    assert len(ep_out.observations) == 0
    pause_event = next(a for a in ep_out.artifacts if a.get("artifact_kind") == "intervention_event" and a.get("event_type") == "pause")
    assert pause_event["status"] == InterventionStatus.PAUSED.value

    timeout_event = next(a for a in ep_out.artifacts if a.get("artifact_kind") == "intervention_event" and a.get("event_type") == "timeout_evaluation")
    assert timeout_event["status"] == InterventionStatus.ESCALATED.value


def test_run_mission_loop_resumes_with_operator_override(
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

    response = OperatorResponse(
        intervention_id="intv:2",
        episode_id=ep.episode_id,
        response_type=InterventionResponseType.OVERRIDE,
        message="Proceed with emergency override",
        provided_at_iso="2026-02-13T00:01:00+00:00",
        approved=True,
        override_payload={"lock_state": "unlock"},
        override_provenance=OverrideProvenance(
            override_id="ovr:1",
            operator_id="alice",
            operator_role="duty_officer",
            justification="emergency egress",
            source_channel="ops-console",
            applied_at_iso="2026-02-13T00:01:00+00:00",
        ),
    )

    ep_out, _, _ = run_mission_loop(
        ep,
        belief,
        projection,
        operator_response=response,
    )

    resume_event = next(a for a in ep_out.artifacts if a.get("artifact_kind") == "intervention_event" and a.get("event_type") == "resume")
    assert resume_event["response_type"] == InterventionResponseType.OVERRIDE.value

    override_event = next(a for a in ep_out.artifacts if a.get("artifact_kind") == "intervention_event" and a.get("event_type") == "override_applied")
    assert override_event["override_provenance"]["operator_id"] == "alice"
    assert len(ep_out.observations) == 1
