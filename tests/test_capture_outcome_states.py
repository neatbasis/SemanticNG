from __future__ import annotations

import pytest

from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    CaptureStatus,
    Channel,
    Episode,
    VerbosityDecision,
    VerbosityLevel,
)
from state_renormalization.engine import apply_schema_bubbling, ingest_observation


def _episode_with_capture(error: CaptureOutcome | None, sentence: str | None = None) -> Episode:
    decision = VerbosityDecision(
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
        status=AskStatus.NO_RESPONSE if error and error.status == CaptureStatus.NO_RESPONSE else AskStatus.OK,
        sentence=sentence,
        slots={},
        error=error,
        metrics=AskMetrics(),
    )
    return Episode(
        episode_id="ep:test",
        conversation_id="conv:test",
        turn_index=1,
        t_asked_iso="2026-02-11T00:00:00Z",
        assistant_prompt_asked="prompt",
        policy_decision=decision,
        ask=ask,
        observations=[],
        outputs=None,
        artifacts=[],
        effects=[],
    )


def test_empty_text_is_distinct_from_capture_no_response() -> None:
    empty_sel = naive_schema_selector(text="   ", error=None)
    no_response_sel = naive_schema_selector(
        text=None,
        error=CaptureOutcome(status=CaptureStatus.NO_RESPONSE),
    )

    assert empty_sel.schemas[0].name == "clarify.empty_input"
    assert empty_sel.ambiguities[0].about.key == "cli.input.empty"

    assert no_response_sel.schemas[0].name == "clarify.capture"
    assert no_response_sel.ambiguities[0].about.key == "channel.capture"


def test_malformed_selector_output_raises_clear_error(monkeypatch) -> None:
    def fake_selector(_text, *, error):
        return {"schemas": ["not-a-schema-hit"], "ambiguities": "not-a-list"}

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    episode = ingest_observation(_episode_with_capture(error=None, sentence="hello"))

    with pytest.raises(TypeError, match="must return SchemaSelection"):
        apply_schema_bubbling(episode, BeliefState())
