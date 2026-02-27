from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class InvariantId(str, Enum):
    PREDICTION_AVAILABILITY = "prediction_availability.v1"
    PREDICTION_RETRIEVABILITY = "prediction_retrievability.v1"
    EXPLAINABLE_HALT_COMPLETENESS = "explainable_halt_completeness.v1"


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


class CheckContext(Protocol):
    now_iso: str
    scope: str
    prediction_key: Optional[str]
    current_predictions: Mapping[str, Any]
    prediction_log_available: bool
    just_written_prediction: Optional[Mapping[str, Any]]
    halt_candidate: Optional[InvariantOutcome]


@dataclass(frozen=True)
class InvariantCheckContext:
    now_iso: str
    scope: str
    prediction_key: Optional[str]
    current_predictions: Mapping[str, Any] = field(default_factory=dict)
    prediction_log_available: bool = True
    just_written_prediction: Optional[Mapping[str, Any]] = None
    halt_candidate: Optional[InvariantOutcome] = None


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


def check_prediction_retrievability(ctx: CheckContext) -> InvariantOutcome:
    written = ctx.just_written_prediction
    if written is None:
        return _ok(InvariantId.PREDICTION_RETRIEVABILITY, "retrievability_not_applicable")

    if not ctx.prediction_log_available:
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_RETRIEVABILITY,
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
            invariant_id=InvariantId.PREDICTION_RETRIEVABILITY,
            passed=False,
            reason="Prediction append did not produce retrievable evidence.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="prediction_append_unverified",
            evidence=({"kind": "scope", "value": ctx.scope},),
            details={"message": "Prediction append did not produce retrievable evidence."},
            action_hints=({"kind": "retry_append", "scope": ctx.scope},),
        )

    key = str(written.get("key") or ctx.prediction_key or "")
    if key and key not in ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_RETRIEVABILITY,
            passed=False,
            reason="Prediction write did not materialize into current predictions.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="write_before_use_violation",
            evidence=({"kind": "prediction_key", "value": key},),
            details={"message": "Prediction write did not materialize into current predictions."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(InvariantId.PREDICTION_RETRIEVABILITY, "prediction_write_materialized", {"prediction_key": key or None})


def check_explainable_halt_completeness(ctx: CheckContext) -> InvariantOutcome:
    candidate = ctx.halt_candidate
    if candidate is None or candidate.flow != Flow.STOP:
        return _ok(InvariantId.EXPLAINABLE_HALT_COMPLETENESS, "halt_check_not_applicable")

    has_details = bool(candidate.details)
    has_evidence = bool(candidate.evidence)
    if has_details and has_evidence:
        return _ok(InvariantId.EXPLAINABLE_HALT_COMPLETENESS, "halt_explainable")

    return InvariantOutcome(
        invariant_id=InvariantId.EXPLAINABLE_HALT_COMPLETENESS,
        passed=False,
        reason="Stop outcomes must include both details and evidence.",
        flow=Flow.STOP,
        validity=Validity.DEGRADED,
        code="halt_not_explainable",
        details={
            "message": "Stop outcomes must include both details and evidence.",
            "offending_invariant": candidate.invariant_id.value,
            "offending_code": candidate.code,
        },
        action_hints=({"kind": "add_evidence", "invariant": candidate.invariant_id.value},),
    )


REGISTRY: dict[InvariantId, Checker] = {
    InvariantId.PREDICTION_AVAILABILITY: check_prediction_availability,
    InvariantId.PREDICTION_RETRIEVABILITY: check_prediction_retrievability,
    InvariantId.EXPLAINABLE_HALT_COMPLETENESS: check_explainable_halt_completeness,
}


def default_check_context(
    *,
    scope: str,
    prediction_key: Optional[str],
    current_predictions: Mapping[str, Any],
    prediction_log_available: bool,
    just_written_prediction: Optional[Mapping[str, Any]] = None,
    halt_candidate: Optional[InvariantOutcome] = None,
) -> InvariantCheckContext:
    return InvariantCheckContext(
        now_iso=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
        halt_candidate=halt_candidate,
    )
