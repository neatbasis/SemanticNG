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


class InvariantHandlingMode(str, Enum):
    STRICT_HALT = "strict_halt"
    REPAIR_EVENTS = "repair_events"


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
    flow: str
    validity: str
    code: str
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    details: Mapping[str, Any] = field(default_factory=dict)
    action_hints: Sequence[Mapping[str, Any]] = field(default_factory=tuple)


@dataclass(frozen=True)
class InvariantBranchBehavior:
    continue_behavior: str
    stop_behavior: Optional[str] = None


class CheckContext(Protocol):
    @property
    def now_iso(self) -> str: ...

    @property
    def scope(self) -> str: ...

    @property
    def prediction_key(self) -> Optional[str]: ...

    @property
    def current_predictions(self) -> Mapping[str, Any]: ...

    @property
    def prediction_log_available(self) -> bool: ...

    @property
    def just_written_prediction(self) -> Optional[Mapping[str, Any]]: ...

    @property
    def halt_candidate(self) -> Optional[InvariantOutcome]: ...

    @property
    def prediction_outcome(self) -> Optional[Mapping[str, Any]]: ...


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

    has_invariant_id = bool(candidate.invariant_id.value)
    has_details_field = candidate.details is not None
    has_evidence_field = candidate.evidence is not None
    if has_invariant_id and has_details_field and has_evidence_field:
        return _ok(InvariantId.EXPLAINABLE_HALT_PAYLOAD, "halt_payload_explainable")

    return InvariantOutcome(
        invariant_id=InvariantId.EXPLAINABLE_HALT_PAYLOAD,
        passed=False,
        reason="Stop outcomes must include invariant_id, details, and evidence fields.",
        flow=Flow.STOP,
        validity=Validity.DEGRADED,
        code="halt_payload_incomplete",
        details={
            "message": "Stop outcomes must include invariant_id, details, and evidence fields.",
            "offending_invariant": candidate.invariant_id.value,
            "offending_code": candidate.code,
            "has_invariant_id": has_invariant_id,
            "has_details_field": has_details_field,
            "has_evidence_field": has_evidence_field,
        },
        action_hints=({"kind": "normalize_halt_payload", "invariant": candidate.invariant_id.value},),
    )


REGISTRY: dict[InvariantId, Checker] = {
    InvariantId.PREDICTION_AVAILABILITY: check_prediction_availability,
    InvariantId.EVIDENCE_LINK_COMPLETENESS: check_evidence_link_completeness,
    InvariantId.PREDICTION_OUTCOME_BINDING: check_prediction_outcome_binding,
    InvariantId.EXPLAINABLE_HALT_PAYLOAD: check_explainable_halt_payload,
}


REGISTERED_INVARIANT_IDS: tuple[str, ...] = tuple(invariant_id.value for invariant_id in REGISTRY)


REGISTERED_INVARIANT_BRANCH_BEHAVIORS: dict[InvariantId, InvariantBranchBehavior] = {
    InvariantId.PREDICTION_AVAILABILITY: InvariantBranchBehavior(
        continue_behavior="Continue when at least one projected prediction exists and prediction_key resolves if provided.",
        stop_behavior="Stop when no projected predictions exist or requested prediction_key is absent from projections.",
    ),
    InvariantId.EVIDENCE_LINK_COMPLETENESS: InvariantBranchBehavior(
        continue_behavior="Continue when no prediction was just written (non-applicable) or when append has evidence links and projects current.",
        stop_behavior="Stop when prediction append log is unavailable, evidence links are missing, or write-before-use projection is violated.",
    ),
    InvariantId.PREDICTION_OUTCOME_BINDING: InvariantBranchBehavior(
        continue_behavior="Continue when no prediction outcome is supplied (non-applicable) or outcome includes prediction_id and numeric error_metric.",
        stop_behavior="Stop when prediction outcome omits prediction_id or supplies non-numeric error_metric.",
    ),
    InvariantId.EXPLAINABLE_HALT_PAYLOAD: InvariantBranchBehavior(
        continue_behavior="Continue when no halt candidate is present (non-applicable) or STOP candidate includes invariant_id/details/evidence fields.",
        stop_behavior="Stop when STOP candidate lacks invariant_id/details/evidence explainability fields.",
    ),
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
        flow=outcome.flow.value,
        validity=outcome.validity.value,
        code=outcome.code,
        evidence=tuple(_normalize_evidence_item(item) for item in outcome.evidence),
        details=_normalize_mapping(outcome.details),
        action_hints=tuple(_normalize_mapping(item) for item in (outcome.action_hints or ())),
    )


def repair_mode_enabled(mode: InvariantHandlingMode | str = InvariantHandlingMode.STRICT_HALT) -> bool:
    return InvariantHandlingMode(mode) == InvariantHandlingMode.REPAIR_EVENTS


def _normalize_evidence_item(item: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "kind": str(item.get("kind") or "unknown"),
        "ref": item.get("ref", item.get("value", "")),
    }


def _normalize_mapping(item: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if item is None:
        return {}
    return {str(k): item[k] for k in item}
