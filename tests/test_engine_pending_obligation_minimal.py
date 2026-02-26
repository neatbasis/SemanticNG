# tests/test_engine_pending_obligation_minimal.py
from __future__ import annotations

from collections.abc import Callable

from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    Channel,
    Episode,
    VerbosityDecision,
)
from state_renormalization.engine import ingest_observation, apply_schema_bubbling


def test_apply_schema_bubbling_sets_minimal_pending_obligation(
    belief: BeliefState,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    decision = make_policy_decision(
        t_decided_iso="2026-02-13T00:00:00+00:00",
        action_type="ask",
        channel=Channel.CLI,
    )
    ask = make_ask_result(
        status=AskStatus.OK,
        sentence="They are here",
        metrics=AskMetrics(elapsed_s=0.0, question_chars=0, question_words=0),
    )
    ep = ingest_observation(
        make_episode(
            t_asked_iso="2026-02-13T00:00:00+00:00",
            assistant_prompt_asked="(test)",
            decision=decision,
            ask=ask,
        )
    )

    assert ep.observations[0].source == "channel:cli"
    ep_out, belief2 = apply_schema_bubbling(ep, belief)

    assert belief2.ambiguity_state.value == "unresolved"
    assert belief2.pending_about is not None
    assert isinstance(belief2.pending_about, dict)
    assert any(a.get("kind") == "schema_selection" for a in ep_out.artifacts)
