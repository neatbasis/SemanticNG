from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence


class InvariantId(str, Enum):
    P0_NO_CURRENT_PREDICTION = "P0_NO_CURRENT_PREDICTION"
    P1_WRITE_BEFORE_USE = "P1_WRITE_BEFORE_USE"
    H0_EXPLAINABLE_HALT = "H0_EXPLAINABLE_HALT"


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
    return InvariantOutcome(
        invariant_id=invariant_id,
        flow=Flow.CONTINUE,
        validity=Validity.VALID,
        code=code,
        details=details or {},
    )


def check_p0_no_current_prediction(ctx: CheckContext) -> InvariantOutcome:
    if not ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.P0_NO_CURRENT_PREDICTION,
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_predictions_projected",
            evidence=({"kind": "scope", "value": ctx.scope},),
            details={"message": "Action selection requires at least one projected current prediction."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    key = ctx.prediction_key
    if not key:
        return _ok(InvariantId.P0_NO_CURRENT_PREDICTION, "p0_not_applicable")

    if key not in ctx.current_predictions:
        return InvariantOutcome(
            invariant_id=InvariantId.P0_NO_CURRENT_PREDICTION,
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_current_prediction",
            evidence=({"kind": "scope", "value": ctx.scope}, {"kind": "prediction_key", "value": key}),
            details={"message": "Action selection attempted to consume a missing current prediction."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(
        InvariantId.P0_NO_CURRENT_PREDICTION,
        "current_prediction_available",
        {"prediction_key": key},
    )


def check_p1_write_before_use(ctx: CheckContext) -> InvariantOutcome:
    written = ctx.just_written_prediction
    if written is None:
        return _ok(InvariantId.P1_WRITE_BEFORE_USE, "p1_not_applicable")

    if not ctx.prediction_log_available:
        return InvariantOutcome(
            invariant_id=InvariantId.P1_WRITE_BEFORE_USE,
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="prediction_log_unavailable",
            details={"message": "Prediction write attempted without an available append log."},
            action_hints=({"kind": "fallback", "action": "buffer_prediction"},),
        )

    evidence_refs = written.get("evidence_refs")
    if not evidence_refs:
        return InvariantOutcome(
            invariant_id=InvariantId.P1_WRITE_BEFORE_USE,
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
            invariant_id=InvariantId.P1_WRITE_BEFORE_USE,
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="write_before_use_violation",
            evidence=({"kind": "prediction_key", "value": key},),
            details={"message": "Prediction write did not materialize into current predictions."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(InvariantId.P1_WRITE_BEFORE_USE, "prediction_write_materialized", {"prediction_key": key or None})


def check_h0_explainable_halt(ctx: CheckContext) -> InvariantOutcome:
    candidate = ctx.halt_candidate
    if candidate is None or candidate.flow != Flow.STOP:
        return _ok(InvariantId.H0_EXPLAINABLE_HALT, "h0_not_applicable")

    has_details = bool(candidate.details)
    has_evidence = bool(candidate.evidence)
    if has_details and has_evidence:
        return _ok(InvariantId.H0_EXPLAINABLE_HALT, "halt_explainable")

    return InvariantOutcome(
        invariant_id=InvariantId.H0_EXPLAINABLE_HALT,
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
    InvariantId.P0_NO_CURRENT_PREDICTION: check_p0_no_current_prediction,
    InvariantId.P1_WRITE_BEFORE_USE: check_p1_write_before_use,
    InvariantId.H0_EXPLAINABLE_HALT: check_h0_explainable_halt,
}


def default_check_context(*, scope: str, prediction_key: Optional[str], current_predictions: Mapping[str, Any], prediction_log_available: bool, just_written_prediction: Optional[Mapping[str, Any]] = None, halt_candidate: Optional[InvariantOutcome] = None) -> InvariantCheckContext:
    return InvariantCheckContext(
        now_iso=datetime.now(timezone.utc).isoformat(),
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
        halt_candidate=halt_candidate,
    )
