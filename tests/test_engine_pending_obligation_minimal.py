# tests/test_engine_pending_obligation_minimal.py
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


def _mk_episode_with_text(text: str) -> Episode:
    decision = VerbosityDecision(
        decision_id="dec:test",
        t_decided_iso="2026-02-13T00:00:00+00:00",
        action_type="ask",
        verbosity_level=VerbosityLevel.V3_CONCISE,
        channel=Channel.CLI,
        reason_codes=[],
        signals={},
        hypothesis=None,
        policy_version="test",
        source="test",
    )

    ask = AskResult(
        status=AskStatus.OK,
        sentence=text,
        slots={},
        error=None,
        metrics=AskMetrics(elapsed_s=0.0, question_chars=0, question_words=0),
    )

    return Episode(
        episode_id="ep:test",
        conversation_id="conv:test",
        turn_index=0,
        t_asked_iso="2026-02-13T00:00:00+00:00",
        assistant_prompt_asked="(test)",
        policy_decision=decision,
        ask=ask,
        observations=[],
        outputs=None,
        artifacts=[],
        effects=[],
    )


def test_apply_schema_bubbling_sets_minimal_pending_obligation(belief: BeliefState) -> None:
    ep = _mk_episode_with_text("They are here")
    ep = ingest_observation(ep)

    assert ep.observations[0].source == "channel:cli"
    ep_out, belief2 = apply_schema_bubbling(ep, belief)

    assert belief2.ambiguity_state.value == "unresolved"
    assert belief2.pending_about is not None
    assert isinstance(belief2.pending_about, dict)

    # and the episode gets the artifact
    assert any(a.get("kind") == "schema_selection" for a in ep_out.artifacts)

