from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from state_renormalization._compat import UTC, StrEnum
from state_renormalization.contracts import EvidenceRef


class InvariantId(StrEnum):
    AUTHORIZATION_SCOPE = "authorization.scope.v1"
    PREDICTION_AVAILABILITY = "prediction_availability.v1"
    EVIDENCE_LINK_COMPLETENESS = "evidence_link_completeness.v1"
    PREDICTION_OUTCOME_BINDING = "prediction_outcome_binding.v1"
    EXPLAINABLE_HALT_PAYLOAD = "explainable_halt_payload.v1"


class Flow(StrEnum):
    CONTINUE = "continue"
    STOP = "stop"


class InvariantHandlingMode(StrEnum):
    STRICT_HALT = "strict_halt"
    REPAIR_EVENTS = "repair_events"


class Validity(StrEnum):
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
    evidence: Sequence[EvidenceRef] = field(default_factory=tuple)
    details: Mapping[str, Any] = field(default_factory=dict)
    action_hints: Sequence[Mapping[str, Any]] | None = None


@dataclass(frozen=True)
class CheckerResult:
    gate: str
    invariant_id: str
    passed: bool
    reason: str
    flow: str
    validity: str
    code: str
    evidence: Sequence[EvidenceRef] = field(default_factory=tuple)
    details: Mapping[str, Any] = field(default_factory=dict)
    action_hints: Sequence[Mapping[str, Any]] = field(default_factory=tuple)


@dataclass(frozen=True)
class InvariantBranchBehavior:
    continue_behavior: str
    stop_behavior: str | None = None


class CheckContext(Protocol):
    @property
    def now_iso(self) -> str: ...

    @property
    def scope(self) -> str: ...

    @property
    def prediction_key(self) -> str | None: ...

    @property
    def current_predictions(self) -> Mapping[str, Any]: ...

    @property
    def prediction_log_available(self) -> bool: ...

    @property
    def just_written_prediction(self) -> Mapping[str, Any] | None: ...

    @property
    def halt_candidate(self) -> InvariantOutcome | None: ...

    @property
    def prediction_outcome(self) -> Mapping[str, Any] | None: ...

    @property
    def authorization_allowed(self) -> bool | None: ...

    @property
    def authorization_context(self) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True)
class InvariantCheckContext:
    now_iso: str
    scope: str
    prediction_key: str | None
    current_predictions: Mapping[str, Any] = field(default_factory=dict)
    prediction_log_available: bool = True
    just_written_prediction: Mapping[str, Any] | None = None
    halt_candidate: InvariantOutcome | None = None
    prediction_outcome: Mapping[str, Any] | None = None
    authorization_allowed: bool | None = None
    authorization_context: Mapping[str, Any] | None = None


def check_authorization_scope(ctx: CheckContext) -> InvariantOutcome:
    if ctx.authorization_allowed is None:
        return _ok(
            InvariantId.AUTHORIZATION_SCOPE,
            "authorization_not_applicable",
            {"message": "Authorization scope check not requested for this gate evaluation."},
        )

    action = str((ctx.authorization_context or {}).get("action") or "unknown")
    capability = str((ctx.authorization_context or {}).get("required_capability") or "unknown")
    if ctx.authorization_allowed:
        return _ok(
            InvariantId.AUTHORIZATION_SCOPE,
            "authorization_scope_allowed",
            {
                "message": "Observer is authorized for invariant gate evaluation.",
                "authorization_context": _normalize_mapping(ctx.authorization_context),
            },
        )

    return InvariantOutcome(
        invariant_id=InvariantId.AUTHORIZATION_SCOPE,
        passed=False,
        reason="observer is not authorized to evaluate invariant gates",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="authorization_scope_denied",
        evidence=(
            EvidenceRef(kind="authorization_scope", ref=f"action:{action}"),
            EvidenceRef(kind="required_capability", ref=capability),
        ),
        details={
            "message": "Observer is not authorized for invariant gate evaluation.",
            "authorization_context": _normalize_mapping(ctx.authorization_context),
        },
        action_hints=({"kind": "review_authorization", "scope": ctx.scope},),
    )


Checker = Callable[[CheckContext], InvariantOutcome]


def _ok(
    invariant_id: InvariantId, code: str, details: Mapping[str, Any] | None = None
) -> InvariantOutcome:
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
            evidence=(EvidenceRef(kind="scope", ref=ctx.scope),),
            details={
                "message": "Action selection requires at least one projected current prediction."
            },
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
            evidence=(
                EvidenceRef(kind="scope", ref=ctx.scope),
                EvidenceRef(kind="prediction_key", ref=key),
            ),
            details={
                "message": "Action selection attempted to consume a missing current prediction."
            },
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(
        InvariantId.PREDICTION_AVAILABILITY, "current_prediction_available", {"prediction_key": key}
    )


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
            evidence=(EvidenceRef(kind="scope", ref=ctx.scope),),
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
            evidence=(EvidenceRef(kind="prediction_key", ref=key),),
            details={"message": "Prediction write did not materialize into current projections."},
            action_hints=({"kind": "rebuild_view", "scope": ctx.scope},),
        )

    return _ok(
        InvariantId.EVIDENCE_LINK_COMPLETENESS,
        "evidence_links_complete",
        {"prediction_key": key or None},
    )


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
            evidence=(EvidenceRef(kind="prediction_id", ref=prediction_id),),
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
        action_hints=(
            {"kind": "normalize_halt_payload", "invariant": candidate.invariant_id.value},
        ),
    )


REGISTRY: dict[InvariantId, Checker] = {
    InvariantId.AUTHORIZATION_SCOPE: check_authorization_scope,
    InvariantId.PREDICTION_AVAILABILITY: check_prediction_availability,
    InvariantId.EVIDENCE_LINK_COMPLETENESS: check_evidence_link_completeness,
    InvariantId.PREDICTION_OUTCOME_BINDING: check_prediction_outcome_binding,
    InvariantId.EXPLAINABLE_HALT_PAYLOAD: check_explainable_halt_payload,
}


REGISTERED_INVARIANT_IDS: tuple[str, ...] = tuple(invariant_id.value for invariant_id in REGISTRY)


REGISTERED_INVARIANT_BRANCH_BEHAVIORS: dict[InvariantId, InvariantBranchBehavior] = {
    InvariantId.AUTHORIZATION_SCOPE: InvariantBranchBehavior(
        continue_behavior="Continue when authorization check is non-applicable or observer is authorized for invariant gate evaluation.",
        stop_behavior="Stop when observer lacks required capability for invariant gate evaluation.",
    ),
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
    prediction_key: str | None,
    current_predictions: Mapping[str, Any],
    prediction_log_available: bool,
    just_written_prediction: Mapping[str, Any] | None = None,
    halt_candidate: InvariantOutcome | None = None,
    prediction_outcome: Mapping[str, Any] | None = None,
    authorization_allowed: bool | None = None,
    authorization_context: Mapping[str, Any] | None = None,
) -> InvariantCheckContext:
    return InvariantCheckContext(
        now_iso=datetime.now(UTC).isoformat(),
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
        halt_candidate=halt_candidate,
        prediction_outcome=prediction_outcome,
        authorization_allowed=authorization_allowed,
        authorization_context=authorization_context,
    )


def run_checkers(
    *, gate: str, ctx: CheckContext, invariant_ids: Sequence[InvariantId]
) -> tuple[InvariantOutcome, ...]:
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


def repair_mode_enabled(
    mode: InvariantHandlingMode | str = InvariantHandlingMode.STRICT_HALT,
) -> bool:
    return InvariantHandlingMode(mode) == InvariantHandlingMode.REPAIR_EVENTS


def _normalize_evidence_item(item: EvidenceRef | Mapping[str, Any]) -> EvidenceRef:
    # Already normalized
    if isinstance(item, EvidenceRef):
        return item

    kind = str(item.get("kind") or "unknown")
    ref = item.get("ref", item.get("value", ""))
    return EvidenceRef(kind=kind, ref=str(ref))


def _normalize_mapping(item: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if item is None:
        return {}
    return {str(k): item[k] for k in item}
