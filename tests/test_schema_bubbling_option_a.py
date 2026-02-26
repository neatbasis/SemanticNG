# tests/test_schema_bubbling_option_a.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Optional

import pytest

from state_renormalization.contracts import AmbiguityStatus, BeliefState
from state_renormalization.engine import apply_schema_bubbling


# ---- Minimal fakes matching what engine reads

@dataclass
class FakeSchemaHit:
    name: str
    score: float
    about: Any = None


@dataclass
class FakeAmbiguity:
    status: AmbiguityStatus
    about: Any
    ask: Any = None  # engine may look at ask/question/q


@dataclass
class FakeSelection:
    schemas: List[FakeSchemaHit]
    ambiguities: List[FakeAmbiguity]
    notes: Optional[str] = None


@dataclass
class FakeAskSat:
    error: Optional[str] = None


@dataclass
class FakeEpisode:
    # only what apply_schema_bubbling uses directly
    ask: FakeAskSat
    observations: list
    artifacts: list


def test_option_a_sets_pending_about_and_question_when_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: selector returns one unresolved ambiguity about "they"
    sel = FakeSelection(
        schemas=[FakeSchemaHit(name="actionable_intent", score=0.7, about=None)],
        ambiguities=[
            FakeAmbiguity(
                status=AmbiguityStatus.UNRESOLVED,
                about={"kind": "reference", "key": "ref:they", "span": "They"},
                ask=None,
            )
        ],
        notes=None,
    )

    # IMPORTANT: keyword-only `error` enforces engine callsite: naive_schema_selector(..., error=...)
    def fake_selector(user_text: Optional[str], *, error: Optional[str]) -> FakeSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = FakeEpisode(
        ask=FakeAskSat(error=None),
        observations=[],   # extract_user_utterance won't find any; that's OK for this unit
        artifacts=[],
    )
    belief = BeliefState()

    # Act
    ep2, b2 = apply_schema_bubbling(ep, belief)

    # Assert
    assert b2.ambiguity_state == AmbiguityStatus.UNRESOLVED
    assert b2.pending_about is not None
    assert b2.pending_about.get("key") == "ref:they"
    assert isinstance(b2.pending_question, str) and b2.pending_question.strip()
    assert b2.pending_attempts == 1
    assert any(a.get("kind") == "schema_selection" for a in ep2.artifacts)


def test_option_a_clears_pending_when_no_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = FakeSelection(schemas=[], ambiguities=[], notes=None)

    def fake_selector(user_text: Optional[str], *, error: Optional[str]) -> FakeSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = FakeEpisode(ask=FakeAskSat(error=None), observations=[], artifacts=[])
    belief = BeliefState(
        ambiguity_state=AmbiguityStatus.UNRESOLVED,
        pending_about={"key": "ref:they"},
        pending_question="Who is they?",
        pending_attempts=2,
    )

    _, b2 = apply_schema_bubbling(ep, belief)

    assert b2.ambiguity_state == AmbiguityStatus.NONE
    assert b2.pending_about is None
    assert b2.pending_question is None
    assert b2.pending_attempts == 0


def test_schema_selection_artifact_does_not_leak_channel_specific_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = FakeSelection(
        schemas=[FakeSchemaHit(name="actionable_intent", score=0.7, about=None)],
        ambiguities=[],
        notes="ok",
    )

    def fake_selector(user_text: Optional[str], *, error: Optional[str]) -> FakeSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = FakeEpisode(ask=FakeAskSat(error=None), observations=[], artifacts=[])
    belief = BeliefState()

    ep2, _ = apply_schema_bubbling(ep, belief)

    art = next(a for a in ep2.artifacts if a.get("kind") == "schema_selection")
    s = json.dumps(art, sort_keys=True)

    assert "ha_" not in s
    assert "satellite_" not in s

