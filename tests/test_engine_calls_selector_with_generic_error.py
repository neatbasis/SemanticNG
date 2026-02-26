from __future__ import annotations

import pytest

from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    Channel,
    Episode,
    Observation,
    ObservationType,
    SchemaSelection,
    VerbosityDecision,
    VerbosityLevel,
)
from state_renormalization.engine import apply_schema_bubbling


def _episode(error: CaptureOutcome | None = None) -> Episode:
    return Episode(
        episode_id="ep:test",
        conversation_id="conv:test",
        turn_index=1,
        t_asked_iso="2026-02-11T00:00:00Z",
        assistant_prompt_asked="prompt",
        policy_decision=VerbosityDecision(
            decision_id="dec:test",
            t_decided_iso="2026-02-11T00:00:00Z",
            action_type="prompt_user",
            verbosity_level=VerbosityLevel.V3_CONCISE,
            channel=Channel.SATELLITE,
            reason_codes=[],
            signals={},
            policy_version="test",
            source="test",
        ),
        ask=AskResult(status=AskStatus.OK, sentence=None, slots={}, error=error, metrics=AskMetrics()),
        observations=[
            Observation(
                observation_id="obs:test:0",
                t_observed_iso="2026-02-11T00:00:00Z",
                type=ObservationType.USER_UTTERANCE,
                text="Hello",
                source="channel:satellite",
            )
        ],
        outputs=None,
        artifacts=[],
        effects=[],
    )


def test_apply_schema_bubbling_calls_selector_with_error_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fake selector only accepts keyword-only `error`, not `ha_error`.
    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return SchemaSelection()

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    apply_schema_bubbling(_episode(), BeliefState())
