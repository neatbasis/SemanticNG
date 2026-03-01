from __future__ import annotations

from collections.abc import Callable

import pytest

from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.contracts import (
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    CaptureStatus,
    Episode,
)
from state_renormalization.engine import apply_schema_bubbling, ingest_observation


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


def test_malformed_selector_output_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
) -> None:
    def fake_selector(_text, *, error):
        return {"schemas": ["not-a-schema-hit"], "ambiguities": "not-a-list"}

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ask = make_ask_result(status=AskStatus.OK, sentence="hello")
    episode = ingest_observation(
        make_episode(turn_index=1, assistant_prompt_asked="prompt", ask=ask)
    )

    with pytest.raises(TypeError, match="must return SchemaSelection"):
        apply_schema_bubbling(episode, BeliefState())
