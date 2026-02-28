from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class InvariantId(str, Enum):
    PREDICTION_AVAILABILITY = "prediction_availability.v1"
    EVIDENCE_LINK_COMPLETENESS = "evidence_link_completeness.v1"
    PREDICTION_OUTCOME_BINDING = "prediction_outcome_binding.v1"
    EXPLAINABLE_HALT_PAYLOAD = "explainable_halt_payload.v1"


class Flow(str, Enum):
    CONTINUE = "continue"
    STOP = "stop"


class Validity(str, Enum):
    VALID = "valid"
    DEGRADED = "degraded"
    INVALID = "invalid"


@dataclass(frozen=True)
class InvariantOutcome:
    invariant_id: InvariantId
    passed: bool
    reason: str
    flow: Flow
    validity: Validity
    code: str
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    details: Mapping[str, Any] = field(default_factory=dict)
    action_hints: Optional[Sequence[Mapping[str, Any]]] = None


@dataclass(frozen=True)
class CheckerResult:
    gate: str
    invariant_id: str
    passed: bool
    reason: str
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    code: str = ""


class CheckContext(Protocol):
    now_iso: str
    scope: str
    prediction_key: Optional[str]
    current_predictions: Mapping[str, Any]
    prediction_log_available: bool
    just_written_prediction: Optional[Mapping[str, Any]]
    halt_candidate: Optional[InvariantOutcome]
    prediction_outcome: Optional[Mapping[str, Any]]


@dataclass(frozen=True)
class InvariantCheckContext:
    now_iso: str
    scope: str
    prediction_key: Optional[str]
    current_predictions: Mapping[str, Any] = field(default_factory=dict)
    prediction_log_available: bool = True
    just_written_prediction: Optional[Mapping[str, Any]] = None
    halt_candidate: Optional[InvariantOutcome] = None
    prediction_outcome: Optional[Mapping[str, Any]] = None


Checker = Callable[[CheckContext], InvariantOutcome]


def _ok(invariant_id: InvariantId, code: str, details: Optional[Mapping[str, Any]] = None) -> InvariantOutcome:
    detail_map = dict(details or {})
    reason = str(detail_map.get("message") or code)
    return InvariantOutcome(
        invariant_id=invariant_id,
        passed=True,
        reason=reason,
        flow=Flow.CONTINUE,
        validity=Validity.VALID,
        code=code,
        details=detail_map,
    )


def check_prediction_availability(ctx: CheckContext) -> InvariantOutcome:
    if not ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_AVAILABILITY,
            passed=False,
            reason="Action selection requires at least one projected current prediction.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_predictions_projected",
            evidence=({"kind": "scope", "value": ctx.scope},),
            details={"message": "Action selection requires at least one projected current prediction."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    key = ctx.prediction_key
    if not key:
        return _ok(InvariantId.PREDICTION_AVAILABILITY, "availability_not_keyed")

    if key not in ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_AVAILABILITY,
            passed=False,
            reason="Action selection attempted to consume a missing current prediction.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_current_prediction",
            evidence=({"kind": "scope", "value": ctx.scope}, {"kind": "prediction_key", "value": key}),
            details={"message": "Action selection attempted to consume a missing current prediction."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(InvariantId.PREDICTION_AVAILABILITY, "current_prediction_available", {"prediction_key": key})


def check_evidence_link_completeness(ctx: CheckContext) -> InvariantOutcome:
    written = ctx.just_written_prediction
    if written is None:
        return _ok(InvariantId.EVIDENCE_LINK_COMPLETENESS, "evidence_check_not_applicable")

    if not ctx.prediction_log_available:
        return InvariantOutcome(
            invariant_id=InvariantId.EVIDENCE_LINK_COMPLETENESS,
            passed=False,
            reason="Prediction write attempted without an available append log.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="prediction_log_unavailable",
            details={"message": "Prediction write attempted without an available append log."},
            action_hints=({"kind": "fallback", "action": "buffer_prediction"},),
        )

    evidence_refs = written.get("evidence_refs")
    if not evidence_refs:
        return InvariantOutcome(
            invariant_id=InvariantId.EVIDENCE_LINK_COMPLETENESS,
            passed=False,
            reason="Prediction append did not produce linked evidence.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="missing_evidence_links",
            evidence=({"kind": "scope", "value": ctx.scope},),
            details={"message": "Prediction append did not produce linked evidence."},
            action_hints=({"kind": "retry_append", "scope": ctx.scope},),
        )

    key = str(written.get("key") or ctx.prediction_key or "")
    if key and key not in ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.EVIDENCE_LINK_COMPLETENESS,
            passed=False,
            reason="Prediction write did not materialize into current projections.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="write_before_use_violation",
            evidence=({"kind": "prediction_key", "value": key},),
            details={"message": "Prediction write did not materialize into current projections."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(InvariantId.EVIDENCE_LINK_COMPLETENESS, "evidence_links_complete", {"prediction_key": key or None})



def check_prediction_outcome_binding(ctx: CheckContext) -> InvariantOutcome:
    outcome = ctx.prediction_outcome
    if outcome is None:
        return _ok(InvariantId.PREDICTION_OUTCOME_BINDING, "outcome_binding_not_applicable")

    prediction_id = str(outcome.get("prediction_id") or "").strip()
    if not prediction_id:
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_OUTCOME_BINDING,
            passed=False,
            reason="Prediction outcome must include prediction_id.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="missing_prediction_id",
            details={"message": "Prediction outcome must include prediction_id."},
            action_hints=({"kind": "repair_outcome", "scope": ctx.scope},),
        )

    error_metric = outcome.get("error_metric")
    if not isinstance(error_metric, (int, float)):
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_OUTCOME_BINDING,
            passed=False,
            reason="Prediction outcome must include numeric error_metric.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="non_numeric_error_metric",
            evidence=({"kind": "prediction_id", "value": prediction_id},),
            details={"message": "Prediction outcome must include numeric error_metric."},
            action_hints=({"kind": "repair_outcome", "scope": ctx.scope},),
        )

    return _ok(
        InvariantId.PREDICTION_OUTCOME_BINDING,
        "prediction_outcome_bound",
        {"prediction_id": prediction_id},
    )

def check_explainable_halt_payload(ctx: CheckContext) -> InvariantOutcome:
    candidate = ctx.halt_candidate
    if candidate is None or candidate.flow != Flow.STOP:
        return _ok(InvariantId.EXPLAINABLE_HALT_PAYLOAD, "halt_check_not_applicable")

    has_details = bool(candidate.details)
    has_evidence = bool(candidate.evidence)
    if has_details and has_evidence:
        return _ok(InvariantId.EXPLAINABLE_HALT_PAYLOAD, "halt_payload_explainable")

    return InvariantOutcome(
        invariant_id=InvariantId.EXPLAINABLE_HALT_PAYLOAD,
        passed=False,
        reason="Stop outcomes must include both details and evidence.",
        flow=Flow.STOP,
        validity=Validity.DEGRADED,
        code="halt_payload_incomplete",
        details={
            "message": "Stop outcomes must include both details and evidence.",
            "offending_invariant": candidate.invariant_id.value,
            "offending_code": candidate.code,
        },
        action_hints=({"kind": "add_evidence", "invariant": candidate.invariant_id.value},),
    )


REGISTRY: dict[InvariantId, Checker] = {
    InvariantId.PREDICTION_AVAILABILITY: check_prediction_availability,
    InvariantId.EVIDENCE_LINK_COMPLETENESS: check_evidence_link_completeness,
    InvariantId.PREDICTION_OUTCOME_BINDING: check_prediction_outcome_binding,
    InvariantId.EXPLAINABLE_HALT_PAYLOAD: check_explainable_halt_payload,
}


def default_check_context(
    *,
    scope: str,
    prediction_key: Optional[str],
    current_predictions: Mapping[str, Any],
    prediction_log_available: bool,
    just_written_prediction: Optional[Mapping[str, Any]] = None,
    halt_candidate: Optional[InvariantOutcome] = None,
    prediction_outcome: Optional[Mapping[str, Any]] = None,
) -> InvariantCheckContext:
    return InvariantCheckContext(
        now_iso=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
        halt_candidate=halt_candidate,
        prediction_outcome=prediction_outcome,
    )


def run_checkers(*, gate: str, ctx: CheckContext, invariant_ids: Sequence[InvariantId]) -> tuple[InvariantOutcome, ...]:
    return tuple(REGISTRY[invariant_id](ctx) for invariant_id in invariant_ids)


def normalize_outcome(outcome: InvariantOutcome, *, gate: str = "") -> CheckerResult:
    return CheckerResult(
        gate=gate,
        invariant_id=outcome.invariant_id.value,
        passed=outcome.passed,
        reason=outcome.reason,
        evidence=tuple(_normalize_evidence_item(item) for item in outcome.evidence),
        code=outcome.code,
    )


def _normalize_evidence_item(item: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "kind": str(item.get("kind") or "unknown"),
        "ref": item.get("ref", item.get("value", "")),
    }
