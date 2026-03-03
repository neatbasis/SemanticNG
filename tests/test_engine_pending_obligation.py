# tests/test_engine_pending_obligation.py
from __future__ import annotations

from collections.abc import Callable

from state_renormalization.contracts import (
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    CaptureStatus,
    Channel,
    ClarificationSlotId,
    Episode,
    VerbosityDecision,
)
from state_renormalization.engine import apply_schema_bubbling, ingest_observation


def test_apply_schema_bubbling_sets_pending_and_emits_schema_selection_artifact(
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    decision = make_policy_decision(channel=Channel.SATELLITE)
    ask = make_ask_result(
        status=AskStatus.NO_RESPONSE,
        error=CaptureOutcome(status=CaptureStatus.NO_RESPONSE),
        metrics=AskMetrics(elapsed_s=30.0, question_chars=0, question_words=0),
    )
    ep0 = ingest_observation(make_episode(decision=decision, ask=ask))

    belief0 = BeliefState()
    ep0, belief1 = apply_schema_bubbling(ep0, belief0)

    assert ep0.observations[0].source == "channel:satellite"

    assert any(a.get("kind") == "schema_selection" for a in ep0.artifacts)

    if belief1.ambiguity_state.value == "unresolved":
        pending_about = belief1.pending_about
        pending_question = belief1.pending_question

        assert pending_about is not None, "pending_about should not evaporate"
        assert isinstance(pending_about, dict), "pending_about should be a dict (Option A)"
        assert isinstance(pending_question, str) and pending_question.strip(), (
            "pending_question must be set"
        )


def test_pending_obligation_artifact_exposes_typed_reminder_options(
    monkeypatch,
    make_episode: Callable[..., Episode],
) -> None:
    from state_renormalization.contracts import (
        AboutKind,
        Ambiguity,
        AmbiguityAbout,
        AmbiguityStatus,
        AmbiguityType,
        AskFormat,
        ClarifyingQuestion,
        ResolutionPolicy,
        SchemaHit,
        SchemaSelection,
    )

    sel = SchemaSelection(
        schemas=[SchemaHit(name="clarify.reminder", score=0.92)],
        ambiguities=[
            Ambiguity(
                status=AmbiguityStatus.UNRESOLVED,
                about=AmbiguityAbout(kind=AboutKind.INTENT, key="reminder.intent"),
                type=AmbiguityType.UNDERSPECIFIED,
                ask=[
                    ClarifyingQuestion(
                        q="When should I remind you?",
                        format=AskFormat.MULTICHOICE,
                        bind={"key": ClarificationSlotId.REMINDER_SCHEDULE.value},
                    ),
                    ClarifyingQuestion(
                        q="Completion mode?",
                        format=AskFormat.MULTICHOICE,
                        bind={"key": ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value},
                    ),
                    ClarifyingQuestion(
                        q="About what?",
                        format=AskFormat.FREEFORM,
                        bind={"key": ClarificationSlotId.REMINDER_TARGET_ENTITY.value},
                    ),
                ],
                resolution_policy=ResolutionPolicy.ASK_USER,
            )
        ],
    )

    def fake_selector(user_text: str | None, *, error):
        return sel

    monkeypatch.setattr("state_renormalization.engine.naive_schema_selector", fake_selector)

    ep, belief = apply_schema_bubbling(make_episode(), BeliefState())
    assert belief.pending_about is not None
    assert belief.pending_about["required_slots"] == [
        ClarificationSlotId.REMINDER_SCHEDULE.value,
        ClarificationSlotId.REMINDER_COMPLETION_CONDITION.value,
        ClarificationSlotId.REMINDER_TARGET_ENTITY.value,
    ]

    artifact = next(a for a in ep.artifacts if a.get("kind") == "schema_selection")
    assert artifact["ask_outbox_request"]["action_options"][
        ClarificationSlotId.REMINDER_SCHEDULE.value
    ]
