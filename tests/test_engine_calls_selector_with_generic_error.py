from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from state_renormalization.contracts import CaptureOutcome, ObservationType, BeliefState, SchemaSelection
from state_renormalization.engine import apply_schema_bubbling


@dataclass
class FakeAskSat:
    error: Optional[CaptureOutcome] = None


@dataclass
class FakeObs:
    type: ObservationType
    text: Optional[str] = None


@dataclass
class FakeEpisode:
    ask: FakeAskSat
    observations: list
    artifacts: list


def test_apply_schema_bubbling_calls_selector_with_error_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fake selector only accepts keyword-only `error`, not `ha_error`.
    def fake_selector(user_text: Optional[str], *, error: Optional[CaptureOutcome]) -> SchemaSelection:
        return SchemaSelection()

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = FakeEpisode(
        ask=FakeAskSat(error=None),
        observations=[FakeObs(type=ObservationType.USER_UTTERANCE, text="Hello")],
        artifacts=[],
    )

    apply_schema_bubbling(ep, BeliefState())
