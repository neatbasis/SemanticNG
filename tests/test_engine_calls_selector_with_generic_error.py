from __future__ import annotations

from collections.abc import Callable

import pytest

from state_renormalization.contracts import (
    AskResult,
    BeliefState,
    CaptureOutcome,
    Episode,
    SchemaSelection,
)
from state_renormalization.engine import apply_schema_bubbling


def test_apply_schema_bubbling_calls_selector_with_error_kwarg(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
) -> None:
    # Fake selector only accepts keyword-only `error`, not `ha_error`.
    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return SchemaSelection()

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    apply_schema_bubbling(make_episode(turn_index=1, assistant_prompt_asked="prompt", ask=make_ask_result()), BeliefState())
