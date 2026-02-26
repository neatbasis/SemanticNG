# tests/test_engine_pending_obligation.py
from __future__ import annotations

from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    Channel,
    Episode,
    VerbosityDecision,
    VerbosityLevel,
)
from state_renormalization.engine import ingest_observation, apply_schema_bubbling


def _mk_episode_no_response() -> Episode:
    dec = VerbosityDecision(
        decision_id="dec:test",
        t_decided_iso="2026-02-11T00:00:00Z",
        action_type="prompt_user",
        verbosity_level=VerbosityLevel.V3_CONCISE,
        channel=Channel.SATELLITE,
        reason_codes=[],
        signals={},
        hypothesis=None,
        policy_version="test",
        source="test",
    )

    ask = AskResult(
        status=AskStatus.NO_RESPONSE,
        sentence=None,
        slots={},
        error="no_response",
        metrics=AskMetrics(elapsed_s=30.0, question_chars=0, question_words=0),
    )

    return Episode(
        episode_id="ep:test",
        conversation_id="conv:test",
        turn_index=0,
        t_asked_iso="2026-02-11T00:00:00Z",
        assistant_prompt_asked="(test prompt)",
        policy_decision=dec,
        ask=ask,
        observations=[],
        outputs=None,
        artifacts=[],
        effects=[],
    )


def test_apply_schema_bubbling_sets_pending_and_emits_schema_selection_artifact() -> None:
    belief0 = BeliefState()
    ep0 = ingest_observation(_mk_episode_no_response())
    ep0, belief1 = apply_schema_bubbling(ep0, belief0)

    assert ep0.observations[0].source == "channel:satellite"
    
    # Artifact exists
    assert any(a.get("kind") == "schema_selection" for a in ep0.artifacts)

    # If unresolved, pending must exist
    if belief1.ambiguity_state.value == "unresolved":
        pending_about = getattr(belief1, "pending_about", None)
        pending_question = getattr(belief1, "pending_question", None)

        assert pending_about is not None, "pending_about should not evaporate"
        assert isinstance(pending_about, dict), "pending_about should be a dict (Option A)"
        assert isinstance(pending_question, str) and pending_question.strip(), "pending_question must be set"

