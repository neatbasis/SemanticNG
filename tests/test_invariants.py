from __future__ import annotations

from state_renormalization.invariants import (
    Flow,
    InvariantId,
    InvariantOutcome,
    Validity,
    check_explainable_halt_completeness,
    check_prediction_availability,
    check_prediction_retrievability,
    default_check_context,
    normalize_outcome,
)


def test_prediction_availability_invariant_pass_and_fail() -> None:
    failing = check_prediction_availability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
        )
    )
    assert failing.invariant_id is InvariantId.PREDICTION_AVAILABILITY
    assert failing.passed is False

    passing = check_prediction_availability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
        )
    )
    normalized = normalize_outcome(passing)
    assert normalized.invariant_id == "prediction_availability.v1"
    assert normalized.passed is True


def test_prediction_retrievability_invariant_pass_and_fail() -> None:
    failing = check_prediction_retrievability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            just_written_prediction={"key": "scope:test", "evidence_refs": []},
        )
    )
    assert failing.invariant_id is InvariantId.PREDICTION_RETRIEVABILITY
    assert failing.passed is False

    passing = check_prediction_retrievability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            just_written_prediction={
                "key": "scope:test",
                "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
            },
        )
    )
    normalized = normalize_outcome(passing)
    assert normalized.invariant_id == "prediction_retrievability.v1"
    assert normalized.passed is True


def test_explainable_halt_completeness_invariant_pass_and_fail() -> None:
    bad_halt = InvariantOutcome(
        invariant_id=InvariantId.PREDICTION_AVAILABILITY,
        passed=False,
        reason="bad halt",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="missing_evidence",
        evidence=(),
        details={},
    )
    failing = check_explainable_halt_completeness(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
            halt_candidate=bad_halt,
        )
    )
    assert failing.invariant_id is InvariantId.EXPLAINABLE_HALT_COMPLETENESS
    assert failing.passed is False

    good_halt = InvariantOutcome(
        invariant_id=InvariantId.PREDICTION_AVAILABILITY,
        passed=False,
        reason="good halt",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="with_evidence",
        evidence=({"kind": "scope", "value": "scope:test"},),
        details={"message": "has details"},
    )
    passing = check_explainable_halt_completeness(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
            halt_candidate=good_halt,
        )
    )
    normalized = normalize_outcome(passing)
    assert normalized.invariant_id == "explainable_halt_completeness.v1"
    assert normalized.passed is True
