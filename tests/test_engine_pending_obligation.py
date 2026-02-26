# tests/test_engine_pending_obligation.py
from __future__ import annotations

from collections.abc import Callable

from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    CaptureOutcome,
    CaptureStatus,
    BeliefState,
    Channel,
    Episode,
    VerbosityDecision,
    VerbosityLevel,
)
from state_renormalization.engine import ingest_observation, apply_schema_bubbling


def test_apply_schema_bubbling_sets_pending_and_emits_schema_selection_artifact(
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    decision = make_policy_decision(channel=Channel.SATELLITE)
    ask = make_ask_result(
        status=AskStatus.NO_RESPONSE,
        error=CaptureOutcome(status=CaptureStatus.NO_RESPONSE),
        metrics=AskMetrics(elapsed_s=30.0, question_chars=0, question_words=0),
    )
    ep0 = ingest_observation(make_episode(decision=decision, ask=ask))

    belief0 = BeliefState()
    ep0, belief1 = apply_schema_bubbling(ep0, belief0)

    assert ep0.observations[0].source == "channel:satellite"

    assert any(a.get("kind") == "schema_selection" for a in ep0.artifacts)

    if belief1.ambiguity_state.value == "unresolved":
        pending_about = belief1.pending_about
        pending_question = belief1.pending_question

        assert pending_about is not None, "pending_about should not evaporate"
        assert isinstance(pending_about, dict), "pending_about should be a dict (Option A)"
        assert isinstance(pending_question, str) and pending_question.strip(), "pending_question must be set"
