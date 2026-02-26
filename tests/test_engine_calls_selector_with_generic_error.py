from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from state_renormalization.contracts import ObservationType, BeliefState
from state_renormalization.engine import apply_schema_bubbling


@dataclass
class FakeAskSat:
    error: Optional[str] = None


@dataclass
class FakeObs:
    type: ObservationType
    text: Optional[str] = None


@dataclass
class FakeEpisode:
    ask: FakeAskSat
    observations: list
    artifacts: list


@dataclass
class FakeSelection:
    schemas: list = None
    ambiguities: list = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.schemas is None:
            self.schemas = []
        if self.ambiguities is None:
            self.ambiguities = []


def test_apply_schema_bubbling_calls_selector_with_error_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fake selector only accepts keyword-only `error`, not `ha_error`.
    def fake_selector(user_text: Optional[str], *, error: Optional[str]) -> FakeSelection:
        return FakeSelection()

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = FakeEpisode(
        ask=FakeAskSat(error=None),
        observations=[FakeObs(type=ObservationType.USER_UTTERANCE, text="Hello")],
        artifacts=[],
    )

    apply_schema_bubbling(ep, BeliefState())

