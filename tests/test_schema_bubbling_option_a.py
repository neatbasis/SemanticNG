# tests/test_schema_bubbling_option_a.py
from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from state_renormalization.contracts import (
    AboutKind,
    Ambiguity,
    AmbiguityAbout,
    AmbiguityStatus,
    AmbiguityType,
    AskFormat,
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    ClarificationSlotId,
    ClarifyingQuestion,
    Episode,
    ResolutionPolicy,
    SchemaHit,
    SchemaSelection,
)
from state_renormalization.engine import (
    _binding_mission_draft,
    _binding_reminder_slot_values,
    apply_schema_bubbling,
)


def test_option_a_sets_pending_about_and_question_when_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
) -> None:
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

    ep2, b2 = apply_schema_bubbling(
        make_episode(ask=make_ask_result(status=AskStatus.OK)), BeliefState()
    )

    assert b2.ambiguity_state == AmbiguityStatus.UNRESOLVED
    assert b2.pending_about is not None
    assert b2.pending_about.get("key") == "ref:they"
    assert isinstance(b2.pending_question, str) and b2.pending_question.strip()
    assert b2.pending_attempts == 1
    assert any(a.get("kind") == "schema_selection" for a in ep2.artifacts)


def test_option_a_clears_pending_when_no_unresolved(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
) -> None:
    sel = SchemaSelection(schemas=[], ambiguities=[], notes=None)

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    belief = BeliefState(
        ambiguity_state=AmbiguityStatus.UNRESOLVED,
        pending_about={"key": "ref:they"},
        pending_question="Who is they?",
        pending_attempts=2,
    )

    _, b2 = apply_schema_bubbling(make_episode(), belief)

    assert b2.ambiguity_state == AmbiguityStatus.NONE
    assert b2.pending_about is None
    assert b2.pending_question is None
    assert b2.pending_attempts == 0


def test_schema_selection_artifact_does_not_leak_channel_specific_terms(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
) -> None:
    sel = SchemaSelection(
        schemas=[
            SchemaHit(
                name="actionable_intent",
                score=0.7,
                schema_id="schema:actionable_intent",
                source="selector:default",
            )
        ],
        ambiguities=[],
        notes="ok",
    )

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep2, _ = apply_schema_bubbling(make_episode(), BeliefState())

    art = next(a for a in ep2.artifacts if a.get("kind") == "schema_selection")
    s = json.dumps(art, sort_keys=True)

    assert "ha_" not in s
    assert "satellite_" not in s
    assert art["schemas"][0]["schema_id"] == "schema:actionable_intent"
    assert art["schemas"][0]["source"] == "selector:default"


def test_option_a_persists_typed_slots_and_composes_ask_outbox_options(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
) -> None:
    sel = SchemaSelection(
        schemas=[SchemaHit(name="clarify.reminder", score=0.9)],
        ambiguities=[
            Ambiguity(
                status=AmbiguityStatus.UNRESOLVED,
                about=AmbiguityAbout(kind=AboutKind.INTENT, key="reminder.intent"),
                type=AmbiguityType.UNDERSPECIFIED,
                ask=[
                    ClarifyingQuestion(
                        q="When should I remind you?",
                        format=AskFormat.MULTICHOICE,
                        options=["later today", "tomorrow"],
                        bind={"key": ClarificationSlotId.REMINDER_SCHEDULE.value},
                    ),
                    ClarifyingQuestion(
                        q="Completion mode?",
                        format=AskFormat.MULTICHOICE,
                        options=["manual", "auto", "until_fresh"],
                        bind={"key": ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value},
                    ),
                ],
                resolution_policy=ResolutionPolicy.ASK_USER,
            )
        ],
    )

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep2, b2 = apply_schema_bubbling(
        make_episode(
            ask=AskResult(
                status=AskStatus.OK,
                sentence="remind me",
                slots={ClarificationSlotId.REMINDER_SCHEDULE.value: "tomorrow"},
            )
        ),
        BeliefState(),
    )

    assert b2.pending_about is not None
    assert (
        b2.pending_about["typed_slot_values"][ClarificationSlotId.REMINDER_SCHEDULE.value]
        == "tomorrow"
    )
    assert b2.bindings[ClarificationSlotId.REMINDER_SCHEDULE.value] == "tomorrow"

    artifact = next(a for a in ep2.artifacts if a.get("kind") == "schema_selection")
    request = artifact["ask_outbox_request"]
    assert request is not None
    assert ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value in request["action_options"]


def test_option_a_routes_typed_slot_binding_writes_through_helper(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
) -> None:
    import state_renormalization.engine as engine

    sel = SchemaSelection(
        schemas=[SchemaHit(name="clarify.reminder", score=0.9)],
        ambiguities=[
            Ambiguity(
                status=AmbiguityStatus.UNRESOLVED,
                about=AmbiguityAbout(kind=AboutKind.INTENT, key="reminder.intent"),
                type=AmbiguityType.UNDERSPECIFIED,
                ask=[
                    ClarifyingQuestion(
                        q="When should I remind you?",
                        format=AskFormat.MULTICHOICE,
                        options=["later today", "tomorrow"],
                        bind={"key": ClarificationSlotId.REMINDER_SCHEDULE.value},
                    )
                ],
                resolution_policy=ResolutionPolicy.ASK_USER,
            )
        ],
    )

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    writes: list[tuple[dict[str, str], dict[str, object]]] = []
    original = engine._write_belief_bindings

    def spy_write(
        belief: BeliefState,
        *,
        updates: dict[str, object] | None = None,
        key: str | None = None,
        value: object = None,
    ) -> None:
        writes.append(
            (
                {"key": key or ""},
                {"updates": {} if updates is None else dict(updates), "value": value},
            )
        )
        original(belief, updates=updates, key=key, value=value)

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)
    monkeypatch.setattr(engine, "_write_belief_bindings", spy_write)

    _, belief = apply_schema_bubbling(
        make_episode(
            ask=AskResult(
                status=AskStatus.OK,
                sentence="remind me",
                slots={ClarificationSlotId.REMINDER_SCHEDULE.value: "tomorrow"},
            )
        ),
        BeliefState(),
    )

    assert belief.bindings[ClarificationSlotId.REMINDER_SCHEDULE.value] == "tomorrow"
    assert any(
        write[1]["updates"] == {ClarificationSlotId.REMINDER_SCHEDULE.value: "tomorrow"}
        for write in writes
    )


def test_option_a_routes_mission_draft_binding_write_through_helper(
    monkeypatch: pytest.MonkeyPatch,
    make_episode: Callable[..., Episode],
) -> None:
    import state_renormalization.engine as engine

    sel = SchemaSelection(
        schemas=[SchemaHit(name="intent.mission_create", score=0.95)],
        ambiguities=[],
    )

    def fake_selector(user_text: str | None, *, error: CaptureOutcome | None) -> SchemaSelection:
        return sel

    writes: list[tuple[str | None, object]] = []
    original = engine._write_belief_bindings

    def spy_write(
        belief: BeliefState,
        *,
        updates: dict[str, object] | None = None,
        key: str | None = None,
        value: object = None,
    ) -> None:
        writes.append((key, value if updates is None else dict(updates)))
        original(belief, updates=updates, key=key, value=value)

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)
    monkeypatch.setattr(engine, "_write_belief_bindings", spy_write)

    _, belief = apply_schema_bubbling(make_episode(), BeliefState())

    assert isinstance(belief.bindings.get("mission.draft"), dict)
    assert any(key == "mission.draft" for key, _ in writes)


def test_binding_reminder_slot_values_reads_known_slots_only() -> None:
    bindings = {
        ClarificationSlotId.REMINDER_SCHEDULE.value: "  tomorrow at 9  ",
        ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value: "manual",
        ClarificationSlotId.REMINDER_TARGET_ENTITY.value: "",
        "unrelated.key": "ignore",
    }
    values = _binding_reminder_slot_values(bindings)
    assert values == {
        ClarificationSlotId.REMINDER_SCHEDULE.value: "tomorrow at 9",
        ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value: "manual",
    }


def test_binding_mission_draft_reads_structured_binding_only() -> None:
    assert _binding_mission_draft({"mission.draft": {"intent": "reminder.create"}}) == {
        "intent": "reminder.create"
    }
    assert _binding_mission_draft({"mission.draft": "not-structured"}) is None
