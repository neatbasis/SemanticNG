# tests/test_schema_bubbling_option_a.py
from __future__ import annotations

import json

import pytest

from state_renormalization.contracts import (
    Ambiguity,
    AmbiguityAbout,
    AboutKind,
    AmbiguityStatus,
    AmbiguityType,
    AskFormat,
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    Channel,
    CaptureOutcome,
    ClarifyingQuestion,
    Episode,
    ResolutionPolicy,
    SchemaHit,
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
        observations=[],
        outputs=None,
        artifacts=[],
        effects=[],
    )


def test_option_a_sets_pending_about_and_question_when_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    about = AmbiguityAbout(kind=AboutKind.ENTITY, key="ref:they")
    sel = SchemaSelection(
        schemas=[SchemaHit(name="actionable_intent", score=0.7)],
        ambiguities=[
            Ambiguity(
                status=AmbiguityStatus.UNRESOLVED,
                about=about,
                type=AmbiguityType.UNDERSPECIFIED,
                ask=[ClarifyingQuestion(q="Who is 'they'?", format=AskFormat.FREEFORM)],
                resolution_policy=ResolutionPolicy.ASK_USER,
            )
        ],
    )

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = _episode()
    belief = BeliefState()

    ep2, b2 = apply_schema_bubbling(ep, belief)

    assert b2.ambiguity_state == AmbiguityStatus.UNRESOLVED
    assert b2.pending_about is not None
    assert b2.pending_about.get("key") == "ref:they"
    assert isinstance(b2.pending_question, str) and b2.pending_question.strip()
    assert b2.pending_attempts == 1
    assert any(a.get("kind") == "schema_selection" for a in ep2.artifacts)


def test_option_a_clears_pending_when_no_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    sel = SchemaSelection(schemas=[], ambiguities=[], notes=None)

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = _episode()
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
    sel = SchemaSelection(schemas=[SchemaHit(name="actionable_intent", score=0.7)], ambiguities=[], notes="ok")

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep = _episode()
    belief = BeliefState()

    ep2, _ = apply_schema_bubbling(ep, belief)

    art = next(a for a in ep2.artifacts if a.get("kind") == "schema_selection")
    s = json.dumps(art, sort_keys=True)

    assert "ha_" not in s
    assert "satellite_" not in s
