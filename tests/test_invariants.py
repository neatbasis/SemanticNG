from __future__ import annotations

from state_renormalization.invariants import (
    Flow,
    InvariantId,
    InvariantOutcome,
    Validity,
    check_authorization_scope,
    check_evidence_link_completeness,
    check_explainable_halt_payload,
    check_prediction_availability,
    check_prediction_outcome_binding,
    default_check_context,
    normalize_outcome,
)




def test_authorization_scope_invariant_pass_and_fail_have_deterministic_shape() -> None:
    denied = check_authorization_scope(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            authorization_allowed=False,
            authorization_context={
                "action": "evaluate_invariant_gates",
                "required_capability": "baseline.invariant_evaluation",
            },
        )
    )
    assert denied.invariant_id is InvariantId.AUTHORIZATION_SCOPE
    assert denied.code == "authorization_scope_denied"
    assert isinstance(denied.details, dict)
    assert isinstance(denied.evidence, tuple)

    allowed = check_authorization_scope(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            authorization_allowed=True,
            authorization_context={
                "action": "evaluate_invariant_gates",
                "required_capability": "baseline.invariant_evaluation",
            },
        )
    )
    normalized = normalize_outcome(allowed)
    assert normalized.invariant_id == "authorization.scope.v1"
    assert normalized.code == "authorization_scope_allowed"
    assert normalized.passed is True

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
    failing = check_evidence_link_completeness(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            just_written_prediction={"key": "scope:test", "evidence_refs": []},
        )
    )
    assert failing.invariant_id is InvariantId.EVIDENCE_LINK_COMPLETENESS
    assert failing.passed is False

    passing = check_evidence_link_completeness(
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
    assert normalized.invariant_id == "evidence_link_completeness.v1"
    assert normalized.passed is True


def test_explainable_halt_completeness_invariant_pass_and_fail() -> None:
    bad_halt = InvariantOutcome(
        invariant_id=InvariantId.PREDICTION_AVAILABILITY,
        passed=False,
        reason="bad halt",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="missing_fields",
        evidence=None,  # type: ignore[arg-type]
        details=None,  # type: ignore[arg-type]
    )
    failing = check_explainable_halt_payload(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
            halt_candidate=bad_halt,
        )
    )
    assert failing.invariant_id is InvariantId.EXPLAINABLE_HALT_PAYLOAD
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
    passing = check_explainable_halt_payload(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
            halt_candidate=good_halt,
        )
    )
    normalized = normalize_outcome(passing)
    assert normalized.invariant_id == "explainable_halt_payload.v1"
    assert normalized.passed is True


def test_prediction_outcome_binding_invariant_fail_and_pass() -> None:
    failing = check_prediction_outcome_binding(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            prediction_outcome={"error_metric": 0.1},
        )
    )
    assert failing.invariant_id is InvariantId.PREDICTION_OUTCOME_BINDING
    assert failing.passed is False

    passing = check_prediction_outcome_binding(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
            prediction_outcome={"prediction_id": "pred:1", "error_metric": 0.1},
        )
    )
    normalized = normalize_outcome(passing)
    assert normalized.invariant_id == "prediction_outcome_binding.v1"
    assert normalized.passed is True


def test_normalized_invariant_outcome_has_stable_json_safe_shape_for_continue_and_stop() -> None:
    continue_outcome = check_prediction_availability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={"scope:test": "pred:1"},
            prediction_log_available=True,
        )
    )
    stop_outcome = check_prediction_availability(
        default_check_context(
            scope="scope:test",
            prediction_key="scope:test",
            current_predictions={},
            prediction_log_available=True,
        )
    )

    normalized_continue = normalize_outcome(continue_outcome, gate="pre-decision")
    normalized_stop = normalize_outcome(stop_outcome, gate="pre-decision")

    for normalized in (normalized_continue, normalized_stop):
        assert set(normalized.__dict__.keys()) == {
            "gate",
            "invariant_id",
            "passed",
            "reason",
            "flow",
            "validity",
            "code",
            "evidence",
            "details",
            "action_hints",
        }
        assert isinstance(normalized.details, dict)
        assert isinstance(normalized.action_hints, tuple)
