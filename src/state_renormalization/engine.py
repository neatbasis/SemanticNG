# state_renormalization/engine.py
from __future__ import annotations

# Temporary integration merge-freeze marker:
# during stabilization of integration/pr-conflict-resolution, merge changes to this
# module only via the ordered integration stack documented in docs/integration_notes.md.
import hashlib
import importlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, cast

from pydantic import BaseModel

from state_renormalization.adapters.ask_outbox import AskOutboxAdapter
from state_renormalization.adapters.observation_freshness import ObservationFreshnessPolicyAdapter
from state_renormalization.adapters.persistence import (
    append_ask_outbox_request_event,
    append_ask_outbox_response_event,
    append_halt,
    append_jsonl,
    append_prediction_event,
    append_prediction_record_event,
    iter_projection_lineage_records,
)
from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.contracts import (
    AmbiguityStatus,
    AskMetrics,
    AskOutboxRequestArtifact,
    AskOutboxResponseArtifact,
    AskResult,
    AskStatus,
    BeliefState,
    CapabilityAdapterGate,
    CapabilityInvocationAttempt,
    CapabilityInvocationPolicyCode,
    CapabilityInvocationPolicyDecision,
    CapabilityPolicyHaltPayload,
    CaptureOutcome,
    CaptureStatus,
    CorrectionCostAttribution,
    DecisionEffect,
    Episode,
    EpisodeOutputs,
    EvidenceRef,
    HaltPayloadValidationError,
    HaltRecord,
    HypothesisEvaluation,
    InterventionAction,
    InterventionDecision,
    InterventionRequest,
    InvariantAuditResult,
    Observation,
    ObservationFreshnessDecision,
    ObservationFreshnessDecisionOutcome,
    ObservationFreshnessPolicyContract,
    ObservationType,
    ObserverFrame,
    PredictionOutcome,
    PredictionRecord,
    ProjectionAnalyticsSnapshot,
    ProjectionReplayResult,
    ProjectionState,
    RepairLineageRef,
    RepairProposalEvent,
    RepairResolution,
    RepairResolutionEvent,
    SchemaSelection,
    UtteranceType,
    VerbosityDecision,
    default_observer_frame,
    project_ambiguity_state,
)
from state_renormalization.invariants import (
    REGISTRY,
    CheckerResult,
    CheckContext,
    InvariantHandlingMode,
    InvariantId,
    InvariantOutcome,
    default_check_context,
    normalize_outcome,
    repair_mode_enabled,
)
from state_renormalization.invariants import (
    Flow as InvariantFlow,
)
from state_renormalization.stable_ids import derive_stable_ids

PHATIC_PATTERNS = [
    "that's a great question",
    "that's an interesting question",
    "good question",
    "interesting",
    "i don't know",
    "not sure",
    "thanks",
]


EXIT_EXACT = {"quit", "exit", "q", "lopeta", "pois", "stop"}
EXIT_PHRASES = [
    "take a break",
    "pause",
    "stop for now",
    "come back later",
    "not now",
    "later",
    "leave me alone",
]


@dataclass(frozen=True)
class GatePredictionOutcome:
    pre_consume: Sequence[InvariantOutcome] = field(default_factory=tuple)
    post_write: Sequence[InvariantOutcome] = field(default_factory=tuple)


    @property
    def combined(self) -> Sequence[InvariantOutcome]:
        return tuple(self.pre_consume) + tuple(self.post_write)


@dataclass(frozen=True)
class Success:
    artifact: GatePredictionOutcome


GateDecision = Success | HaltRecord

# Backward-compatible names retained for older callers/tests.
GateSuccessOutcome = Success


@dataclass(frozen=True)
class GateHaltOutcome:
    artifact: HaltRecord


@dataclass(frozen=True)
class GateInvariantCheck:
    gate_point: str
    output: CheckerResult


@dataclass(frozen=True)
class GateInvariantEvaluation:
    phase: str
    outcome: InvariantOutcome


class InterventionLifecycleHook(Protocol):
    def __call__(
        self,
        *,
        phase: str,
        episode: Episode,
        belief: BeliefState,
        projection_state: ProjectionState,
    ) -> InterventionDecision | Mapping[str, Any] | None:
        ...


def _parse_iso8601(value: str) -> Optional[datetime]:
    txt = (value or "").strip()
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(txt)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _observation_matches_scope(*, observation: Observation, scope: str) -> bool:
    normalized_scope = scope.strip().lower()
    return observation.type.value.lower() == normalized_scope or (observation.source or "").strip().lower() == normalized_scope


def evaluate_observation_freshness(
    *,
    ep: Episode,
    belief: BeliefState,
    projection_state: ProjectionState,
    policy_adapter: ObservationFreshnessPolicyAdapter,
    ask_outbox_adapter: Optional[AskOutboxAdapter] = None,
) -> ObservationFreshnessDecision:
    raw_contract = policy_adapter.get_contract(episode=ep, belief=belief, projection_state=projection_state)
    if raw_contract is None:
        return ObservationFreshnessDecision(
            scope="none",
            outcome=ObservationFreshnessDecisionOutcome.CONTINUE,
            reason="freshness policy adapter returned no contract",
            stale_after_seconds=0,
        )

    contract = raw_contract if isinstance(raw_contract, ObservationFreshnessPolicyContract) else ObservationFreshnessPolicyContract.model_validate(raw_contract)

    matched = [obs for obs in ep.observations if _observation_matches_scope(observation=obs, scope=contract.scope)]
    latest_observation = max(matched, key=lambda item: item.t_observed_iso, default=None)
    last_observed_at = latest_observation.t_observed_iso if latest_observation is not None else contract.observed_at_iso
    last_observed_value = latest_observation.text if latest_observation is not None else None

    reason = "observation freshness contract satisfied"
    outcome = ObservationFreshnessDecisionOutcome.CONTINUE
    evidence = {
        "reason": reason,
        "last_observed_at": last_observed_at,
        "last_observed_value": last_observed_value,
        "policy_threshold_seconds": contract.stale_after_seconds,
    }

    if not last_observed_at:
        reason = "no observation available for freshness scope"
        outcome = ObservationFreshnessDecisionOutcome.ASK_REQUEST
    else:
        observed_dt = _parse_iso8601(last_observed_at)
        now_dt = _parse_iso8601(_now_iso())
        if observed_dt is None or now_dt is None:
            reason = "observation freshness timestamp invalid"
            outcome = ObservationFreshnessDecisionOutcome.ASK_REQUEST
        else:
            age_seconds = max(0.0, (now_dt - observed_dt).total_seconds())
            evidence["observation_age_seconds"] = age_seconds
            if age_seconds > contract.stale_after_seconds:
                reason = "observation is stale for freshness policy"
                outcome = ObservationFreshnessDecisionOutcome.ASK_REQUEST

    outstanding_request_id = None
    if outcome == ObservationFreshnessDecisionOutcome.ASK_REQUEST:
        has_outstanding = getattr(policy_adapter, "has_outstanding_request", None)
        if callable(has_outstanding):
            outstanding_request_id = has_outstanding(scope=contract.scope)
        if outstanding_request_id:
            outcome = ObservationFreshnessDecisionOutcome.HOLD
            reason = "freshness request already outstanding for scope"

    evidence.update(
        {
            "reason": reason,
            "last_observed_at": last_observed_at,
            "last_observed_value": last_observed_value,
            "policy_threshold_seconds": contract.stale_after_seconds,
            "scope": contract.scope,
        }
    )
    if outstanding_request_id:
        evidence["outstanding_request_id"] = outstanding_request_id

    decision = ObservationFreshnessDecision(
        scope=contract.scope,
        outcome=outcome,
        reason=reason,
        stale_after_seconds=contract.stale_after_seconds,
        observed_at_iso=contract.observed_at_iso,
        last_observed_at_iso=last_observed_at,
        last_observed_value=last_observed_value,
        evidence=evidence,
    )

    artifact_payload = {
        "artifact_kind": "observation_freshness_decision",
        "decision": decision.model_dump(mode="json"),
        "reason": decision.reason,
        "last_observed_at": decision.last_observed_at_iso,
        "last_observed_value": decision.last_observed_value,
        "policy_threshold_seconds": decision.stale_after_seconds,
    }
    _append_episode_artifact(ep, artifact_payload)

    if decision.outcome == ObservationFreshnessDecisionOutcome.ASK_REQUEST and ask_outbox_adapter is not None:
        title = f"Freshness check required: {decision.scope}"
        question = f"Please provide a fresh observation for scope '{decision.scope}'."
        context = {
            "scope": decision.scope,
            "reason": decision.reason,
            "last_observed_at": decision.last_observed_at_iso,
            "last_observed_value": decision.last_observed_value,
            "policy_threshold_seconds": decision.stale_after_seconds,
        }
        request_id = ask_outbox_adapter.create_request(title, question, context)
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "observation_freshness_ask_request",
                "action": ObservationFreshnessDecisionOutcome.ASK_REQUEST.value,
                "request_id": request_id,
                "scope": decision.scope,
                "reason": decision.reason,
                "last_observed_at": decision.last_observed_at_iso,
                "last_observed_value": decision.last_observed_value,
                "policy_threshold_seconds": decision.stale_after_seconds,
            },
        )

    return decision


def _first_halt_from_evaluations(
    *,
    evaluations: Sequence[GateInvariantEvaluation],
    gate_point: str,
) -> tuple[Optional[InvariantOutcome], Optional[str]]:
    for evaluation in evaluations:
        if evaluation.outcome.flow == InvariantFlow.STOP:
            return evaluation.outcome, f"{gate_point}:{evaluation.phase}"
    return None, None


def _evaluate_gate_phase(
    *,
    scope: str,
    prediction_key: Optional[str],
    current_predictions: Mapping[str, str],
    prediction_log_available: bool,
    phase: str,
    invariant_id: InvariantId,
    just_written_prediction: Optional[Mapping[str, Any]],
) -> GateInvariantEvaluation:
    phase_ctx = default_check_context(
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
    )
    return GateInvariantEvaluation(
        phase=phase,
        outcome=_run_invariant(invariant_id, ctx=phase_ctx),
    )


def _result_from_gate_evaluations(
    *,
    evaluations: Sequence[GateInvariantEvaluation],
    gate_point: str,
) -> GateDecision:
    halt_outcome, halt_stage = _first_halt_from_evaluations(evaluations=evaluations, gate_point=gate_point)
    if halt_outcome is None or halt_stage is None:
        return Success(
            artifact=GatePredictionOutcome(
                pre_consume=tuple(ev.outcome for ev in evaluations if ev.phase == "pre_consume"),
                post_write=tuple(ev.outcome for ev in evaluations if ev.phase == "post_write"),
            )
        )
    return _halt_record_from_outcome(stage=halt_stage, outcome=halt_outcome)


def _observer_allowed_invariants(observer: Optional[ObserverFrame]) -> Optional[set[InvariantId]]:
    if observer is None:
        return None

    configured = getattr(observer, "evaluation_invariants", None) or []
    if not configured:
        return None

    allowed: set[InvariantId] = set()
    for invariant_name in configured:
        try:
            allowed.add(InvariantId(invariant_name))
        except ValueError:
            continue
    return allowed


def _observer_allows_invariant(*, observer: Optional[ObserverFrame], invariant_id: InvariantId) -> bool:
    allowed = _observer_allowed_invariants(observer)
    if allowed is None:
        return True
    return invariant_id in allowed


def _observer_has_capability(observer: Optional[ObserverFrame], capability: str) -> bool:
    if observer is None:
        return True
    configured = getattr(observer, "capabilities", None) or []
    return capability in configured


def _observer_authorized_for_action(
    *,
    observer: Optional[ObserverFrame],
    action: str,
    required_capability: str,
) -> tuple[bool, dict[str, Any]]:
    authorized = _observer_has_capability(observer, required_capability)
    context = {
        "action": action,
        "required_capability": required_capability,
        "observer_role": getattr(observer, "role", None),
        "authorization_level": getattr(observer, "authorization_level", None),
        "observer_capabilities": list(getattr(observer, "capabilities", []) or []),
        "authorized": authorized,
    }
    return authorized, context


def _stable_halt_id(*, stage: str, outcome: InvariantOutcome) -> str:
    basis = "|".join(
        [
            stage,
            outcome.invariant_id.value,
            outcome.reason,
            ",".join(sorted(str(_to_dict(item)) for item in outcome.evidence)),
        ]
    )
    return f"halt:{sha1_text(basis)}"


def _halt_record_from_outcome(*, stage: str, outcome: InvariantOutcome) -> HaltRecord:
    if outcome.details is None or outcome.evidence is None:
        raise HaltPayloadValidationError("halt payload is malformed or incomplete")

    reason = outcome.reason
    return HaltRecord.from_payload(
        HaltRecord.build_canonical_payload(
            halt_id=_stable_halt_id(stage=stage, outcome=outcome),
            stage=stage,
            invariant_id=outcome.invariant_id.value,
            reason=reason,
            details=dict(outcome.details),
            evidence=list(outcome.evidence),
            timestamp=_now_iso(),
            retryability=bool(outcome.action_hints),
        )
    )


def _authorization_halt_record(*, stage: str, reason: str, context: Mapping[str, Any]) -> HaltRecord:
    return HaltRecord.from_payload(
        HaltRecord.build_canonical_payload(
            halt_id=f"halt:{sha1_text(f'{stage}|authorization.scope.v1|{reason}|{_to_dict(context)}')}",
            stage=stage,
            invariant_id="authorization.scope.v1",
            reason=reason,
            details={"authorization_context": _to_dict(context)},
            evidence=[
                EvidenceRef(
                    kind="authorization_scope",
                    ref=f"action:{context.get('action', 'unknown')}",
                ),
                EvidenceRef(
                    kind="required_capability",
                    ref=str(context.get("required_capability") or "unknown"),
                ),
            ],
            timestamp=_now_iso(),
            retryability=True,
        )
    )


def _capability_invocation_policy_decision(
    *,
    observer: Optional[ObserverFrame],
    projection_state: ProjectionState,
    scope_key: str,
    prediction_key: Optional[str],
    explicit_gate_pass_present: bool,
    action: str,
    capability: str,
    required_capability: str,
    stage: str,
) -> CapabilityInvocationPolicyDecision:
    has_current_prediction = projection_state.has_current_predictions
    if prediction_key is None:
        has_current_prediction = True
    elif not has_current_prediction:
        has_current_prediction = prediction_key in projection_state.current_predictions

    attempt = CapabilityInvocationAttempt(
        invocation_id=_new_id("invoke:"),
        capability=capability,
        action=action,
        stage=stage,
        scope_key=scope_key,
        prediction_key=prediction_key,
        required_capability=required_capability,
        explicit_gate_pass_present=explicit_gate_pass_present,
        current_prediction_available=has_current_prediction,
        observer_role=getattr(observer, "role", None),
        observer_authorization_level=getattr(observer, "authorization_level", None),
        observer_capabilities=list(getattr(observer, "capabilities", []) or []),
    )

    code: CapabilityInvocationPolicyCode | None = None
    reason: str | None = None
    if not has_current_prediction:
        code = CapabilityInvocationPolicyCode.CURRENT_PREDICTION_REQUIRED
        reason = "capability invocation denied: current valid prediction is required"
    elif not explicit_gate_pass_present:
        code = CapabilityInvocationPolicyCode.EXPLICIT_GATE_PASS_REQUIRED
        reason = "capability invocation denied: explicit gate pass is required"
    elif not _observer_has_capability(observer, required_capability):
        code = CapabilityInvocationPolicyCode.OBSERVER_SCOPE_DENIED
        reason = "capability invocation denied: observer scope does not permit action"

    if code is None or reason is None:
        return CapabilityInvocationPolicyDecision(attempt=attempt, allowed=True)

    details = {
        "policy_code": code.value,
        "attempt": attempt.model_dump(mode="json"),
    }
    halt_payload = CapabilityPolicyHaltPayload(
        halt_id=f"halt:{sha1_text(f'{stage}|capability.invocation.policy.v1|{code.value}|{attempt.invocation_id}')}",
        stage=stage,
        invariant_id="capability.invocation.policy.v1",
        reason=reason,
        details=details,
        evidence=[
            EvidenceRef(kind="capability", ref=capability),
            EvidenceRef(kind="action", ref=action),
            EvidenceRef(kind="policy_code", ref=code.value),
        ],
        retryability=True,
        timestamp=_now_iso(),
    )
    return CapabilityInvocationPolicyDecision(
        attempt=attempt,
        allowed=False,
        denial_code=code,
        denial_reason=reason,
        halt_payload=halt_payload,
    )


def _persist_policy_denial(
    *,
    ep: Optional[Episode],
    decision: CapabilityInvocationPolicyDecision,
    halt_log_path: str | Path,
) -> HaltRecord:
    if decision.halt_payload is None:
        raise HaltPayloadValidationError("policy denial must provide halt payload")

    halt = HaltRecord.from_payload(decision.halt_payload.model_dump(mode="json"))
    halt_evidence_ref = append_halt_record(
        halt,
        halt_log_path=halt_log_path,
        stable_ids=_episode_stable_ids(ep) if ep is not None else None,
    )
    if ep is not None:
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "capability_policy_denial",
                "attempt": decision.attempt.model_dump(mode="json"),
                "denial_code": decision.denial_code.value if decision.denial_code else None,
                "denial_reason": decision.denial_reason,
                **_halt_payload(halt),
                "halt_evidence_ref": halt_evidence_ref,
            },
        )
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "halt_observation",
                "observation_type": "halt",
                **_halt_payload(halt),
                "halt_evidence_ref": halt_evidence_ref,
            },
        )
    return halt


def _evaluate_invariant_gate_pipeline(
    *,
    observer: Optional[ObserverFrame],
    scope: str,
    prediction_key: Optional[str],
    current_predictions: Mapping[str, str],
    prediction_log_available: bool,
    just_written_prediction: Optional[Mapping[str, Any]],
    gate_point: str,
) -> tuple[list[GateInvariantEvaluation], GateDecision]:
    evaluations: list[GateInvariantEvaluation] = []
    gate_specs: tuple[tuple[str, InvariantId, bool, Optional[Mapping[str, Any]]], ...] = (
        ("pre_consume", InvariantId.PREDICTION_AVAILABILITY, True, None),
        (
            "post_write",
            InvariantId.EVIDENCE_LINK_COMPLETENESS,
            just_written_prediction is not None,
            just_written_prediction,
        ),
    )

    for phase, invariant_id, is_enabled, phase_written_prediction in gate_specs:
        if not is_enabled or not _observer_allows_invariant(observer=observer, invariant_id=invariant_id):
            continue
        evaluation = _evaluate_gate_phase(
            scope=scope,
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            phase=phase,
            invariant_id=invariant_id,
            just_written_prediction=phase_written_prediction,
        )
        evaluations.append(evaluation)
        if evaluation.outcome.flow == InvariantFlow.STOP:
            break

    return evaluations, _result_from_gate_evaluations(evaluations=evaluations, gate_point=gate_point)


def _halt_payload(halt: HaltRecord) -> Dict[str, Any]:
    return halt.to_canonical_payload()

def _append_authorization_issue(ep: Episode, *, halt: HaltRecord, context: Mapping[str, Any]) -> None:
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "authorization_issue",
            "issue_type": "authorization_scope_violation",
            **_halt_payload(halt),
            "observer": _to_dict(getattr(ep, "observer", None)),
            "authorization_context": _to_dict(context),
        },
    )
    if not hasattr(ep, "observations") or getattr(ep, "observations") is None:
        setattr(ep, "observations", [])
    ep.observations.append(
        Observation(
            observation_id=_new_id("obs:"),
            t_observed_iso=_now_iso(),
            type=ObservationType.HALT,
            text=halt.reason,
            source=f"authorization:{context.get('action', 'unknown')}",
        )
    )


def _turn_halt_summary(ep: Episode) -> list[dict[str, Any]]:
    return [
        {
            "halt_id": artifact.get("halt_id"),
            "stage": artifact.get("stage"),
            "invariant_id": artifact.get("invariant_id") or artifact.get("violated_invariant_id"),
            "reason": artifact.get("reason"),
            "retryability": artifact.get("retryability") if "retryability" in artifact else artifact.get("retryable"),
            "timestamp": artifact.get("timestamp") or artifact.get("timestamp_iso"),
            "evidence_ref": artifact.get("halt_evidence_ref"),
        }
        for artifact in ep.artifacts
        if isinstance(artifact, dict) and artifact.get("artifact_kind") == "halt_observation"
    ]


def append_turn_summary(ep: Episode) -> None:
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "turn_summary",
            "turn_index": ep.turn_index,
            "halt_count": len(_turn_halt_summary(ep)),
            "halts": _turn_halt_summary(ep),
            "operator_action": "review_halts_then_resume_next_turn" if _turn_halt_summary(ep) else None,
        },
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "") -> str:
    s = str(uuid.uuid4())
    return f"{prefix}{s}" if prefix else s


def sha1_text(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:10]


def is_exit_intent(txt_lower: str) -> bool:
    if txt_lower.strip() in EXIT_EXACT:
        return True
    return any(p in txt_lower for p in EXIT_PHRASES)


def classify_utterance(sentence: Optional[str], error: Optional[CaptureOutcome]) -> UtteranceType:
    if error is not None and error.status == CaptureStatus.NO_RESPONSE:
        return UtteranceType.NONE
    txt = (sentence or "").strip().lower()
    if not txt:
        return UtteranceType.NONE
    if is_exit_intent(txt):
        return UtteranceType.EXIT_INTENT
    if any(p in txt for p in PHATIC_PATTERNS) and len(txt.split()) <= 8:
        return UtteranceType.LOW_SIGNAL
    return UtteranceType.NORMAL


def _to_dict(obj: Any) -> Any:
    """
    Convert dataclasses / pydantic models / enums / nested containers into JSON-safe primitives.
    """
    if obj is None:
        return None

    # Pydantic v2
    if isinstance(obj, BaseModel):
        # mode="json" ensures Enums become values, datetimes become iso strings if present, etc.
        return obj.model_dump(mode="json")

    # Enums
    if isinstance(obj, Enum):
        return obj.value

    # Containers
    if isinstance(obj, dict):
        return {str(k): _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]

    # Primitives / unknowns
    return obj


def _find_stable_ids_from_payload(payload: Mapping[str, Any]) -> Dict[str, str]:
    nested = payload.get("stable_ids")
    nested_stable = nested if isinstance(nested, Mapping) else {}
    explicit = {
        "feature_id": payload.get("feature_id") or nested_stable.get("feature_id"),
        "scenario_id": payload.get("scenario_id") or nested_stable.get("scenario_id"),
        "step_id": payload.get("step_id") or nested_stable.get("step_id"),
    }
    if explicit["feature_id"] and explicit["scenario_id"] and explicit["step_id"]:
        return {k: str(v) for k, v in explicit.items() if v is not None}

    feature_uri = payload.get("feature_uri") or payload.get("feature_path")
    if not isinstance(feature_uri, str) or not feature_uri.strip():
        return {}

    feature_path = Path(feature_uri)
    if not feature_path.exists():
        return {}

    feature_text = feature_path.read_text(encoding="utf-8")
    doc = _parse_feature_doc(feature_text)
    if doc is None:
        return {}

    doc["uri"] = feature_uri
    stable = derive_stable_ids(doc, uri=feature_uri)

    scenario_name = payload.get("scenario_name") or payload.get("scenario")
    step_text = payload.get("step_text") or payload.get("step_name")

    scenario_id: Optional[str] = None
    if isinstance(scenario_name, str) and scenario_name.strip():
        for key, sid in stable.scenario_ids.items():
            if key.split(":", 1)[-1].split("@", 1)[0] == scenario_name:
                scenario_id = sid
                break
    elif len(stable.scenario_ids) == 1:
        scenario_id = next(iter(stable.scenario_ids.values()))

    step_id: Optional[str] = None
    if isinstance(step_text, str) and step_text.strip():
        for key, sid in stable.step_ids.items():
            key_scenario, step_part = key.split("::", 1)
            key_step_text = step_part.split(":", 1)[-1].split("@", 1)[0]
            if key_step_text != step_text:
                continue
            if scenario_id is None:
                step_id = sid
                break
            scenario_key = next((k for k, v in stable.scenario_ids.items() if v == scenario_id), None)
            if scenario_key is not None and key_scenario == scenario_key:
                step_id = sid
                break
    elif len(stable.step_ids) == 1:
        step_id = next(iter(stable.step_ids.values()))

    out = {"feature_id": stable.feature_id}
    if scenario_id is not None:
        out["scenario_id"] = scenario_id
    if step_id is not None:
        out["step_id"] = step_id
    return out


def _parse_feature_doc(feature_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse Gherkin content if optional parser dependencies are installed.

    Returns None when parser modules are unavailable or parsing fails so core
    state renormalization behavior can remain available without BDD extras.
    """
    try:
        parser_module = importlib.import_module("gherkin.parser")
        scanner_module = importlib.import_module("gherkin.token_scanner")
        parser = parser_module.Parser()
        scanner = scanner_module.TokenScanner(feature_text)
        parsed = parser.parse(scanner)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _episode_stable_ids(ep: Episode) -> Dict[str, str]:
    for artifact in ep.artifacts:
        if not isinstance(artifact, dict):
            continue
        fid = artifact.get("feature_id")
        sid = artifact.get("scenario_id")
        stid = artifact.get("step_id")
        if isinstance(fid, str):
            out = {"feature_id": fid}
            if isinstance(sid, str):
                out["scenario_id"] = sid
            if isinstance(stid, str):
                out["step_id"] = stid
            return out
    return {}


def _append_episode_artifact(ep: Episode, artifact: Dict[str, Any], *, stable_ids: Optional[Mapping[str, str]] = None) -> None:
    sid = dict(stable_ids or _episode_stable_ids(ep))
    ep.artifacts.append({**sid, **artifact} if sid else artifact)


def _run_invariant(invariant_id: InvariantId, *, ctx: CheckContext) -> InvariantOutcome:
    checker = REGISTRY[invariant_id]
    outcome = checker(ctx)
    if outcome.flow != InvariantFlow.STOP:
        return outcome

    h0_ctx = default_check_context(
        scope=ctx.scope,
        prediction_key=ctx.prediction_key,
        current_predictions=ctx.current_predictions,
        prediction_log_available=ctx.prediction_log_available,
        just_written_prediction=ctx.just_written_prediction,
        halt_candidate=outcome,
    )
    explainable_halt = REGISTRY[InvariantId.EXPLAINABLE_HALT_PAYLOAD](h0_ctx)
    if explainable_halt.flow == InvariantFlow.STOP:
        return explainable_halt
    return outcome




def _invariant_audit_result_from_checker(gate_point: str, normalized: CheckerResult) -> InvariantAuditResult:
    return InvariantAuditResult(
        gate_point=gate_point,
        invariant_id=normalized.invariant_id,
        passed=normalized.passed,
        reason=normalized.reason,
        flow=normalized.flow,
        validity=normalized.validity,
        code=normalized.code,
        evidence=list(normalized.evidence),
        details=_to_dict(normalized.details) or {},
        action_hints=[_to_dict(item) for item in normalized.action_hints],
    )


def _build_intervention_request(
    *,
    ep: Episode,
    projection_state: ProjectionState,
    phase: str,
) -> InterventionRequest:
    return InterventionRequest(
        request_id=_new_id("hitl:"),
        phase=phase,
        episode_id=ep.episode_id,
        conversation_id=ep.conversation_id,
        turn_index=ep.turn_index,
        projection_updated_at_iso=projection_state.updated_at_iso,
        created_at_iso=_now_iso(),
    )
def _normalize_intervention_decision(decision: InterventionDecision | Mapping[str, Any] | None) -> InterventionDecision:
    if decision is None:
        return InterventionDecision(action=InterventionAction.NONE)
    if isinstance(decision, InterventionDecision):
        return decision
    return InterventionDecision.model_validate(decision)


def _apply_intervention_hook(
    *,
    ep: Episode,
    belief: BeliefState,
    projection_state: ProjectionState,
    phase: str,
    intervention_hook: Optional[InterventionLifecycleHook],
    ask_outbox_adapter: Optional[AskOutboxAdapter] = None,
    prediction_log_path: str | Path = "artifacts/predictions.jsonl",
    halt_log_path: str | Path = "halts.jsonl",
) -> tuple[bool, Optional[InterventionDecision]]:
    if intervention_hook is None:
        return True, None

    request = _build_intervention_request(ep=ep, projection_state=projection_state, phase=phase)
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "intervention_request",
            "phase": phase,
            "request": request.model_dump(mode="json"),
            "request_id": request.request_id,
        },
    )

    outbox_request_id: Optional[str] = None
    if ask_outbox_adapter is not None:
        policy_decision = _capability_invocation_policy_decision(
            observer=getattr(ep, "observer", None),
            projection_state=projection_state,
            scope_key=f"{ep.conversation_id}:{ep.turn_index}:{phase}",
            prediction_key=None,
            explicit_gate_pass_present=True,
            action="create_ask_request",
            capability="ask.outbox",
            required_capability="baseline.dialog",
            stage=f"{phase}:ask-outbox",
        )
        if not policy_decision.allowed:
            _persist_policy_denial(ep=ep, decision=policy_decision, halt_log_path=halt_log_path)
            append_turn_summary(ep)
            return False, InterventionDecision(action=InterventionAction.ESCALATE, reason="ask outbox denied by policy")

        adapter_gate = CapabilityAdapterGate(invocation_id=policy_decision.attempt.invocation_id, allowed=True)
        title = f"Human review required: {phase}"
        question = f"Review intervention request for conversation {ep.conversation_id} turn {ep.turn_index}."
        context = {
            "phase": phase,
            "request_id": request.request_id,
            "conversation_id": ep.conversation_id,
            "episode_id": ep.episode_id,
            "turn_index": ep.turn_index,
            "projection_updated_at_iso": projection_state.updated_at_iso,
        }
        outbox_request_id = ask_outbox_adapter.create_request(title, question, context)

        request_artifact = AskOutboxRequestArtifact(
            request_id=outbox_request_id,
            scope=phase,
            reason="human recruitment requested by intervention lifecycle",
            evidence_refs=[EvidenceRef(kind="intervention_request", ref=request.request_id)],
            created_at_iso=request.created_at_iso,
            metadata=context,
        )
        request_ref = append_ask_outbox_request_event(
            request_artifact.model_dump(mode="json"),
            adapter_gate=adapter_gate,
            path=prediction_log_path,
        )
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "ask_outbox_request",
                "phase": phase,
                "request": request_artifact.model_dump(mode="json"),
                "evidence_ref": request_ref,
            },
        )

    raw_decision = intervention_hook(
        phase=phase,
        episode=ep,
        belief=belief,
        projection_state=projection_state,
    )
    normalized_input = raw_decision
    if normalized_input is None:
        normalized_input = {"action": InterventionAction.NONE.value}
    if not isinstance(normalized_input, Mapping):
        normalized_input = _to_dict(normalized_input)
    normalized_input = dict(normalized_input)

    if normalized_input.get("action") == InterventionAction.RESUME.value and not normalized_input.get("responded_at_iso"):
        normalized_input.setdefault("responded_at_iso", _now_iso())

    decision = _normalize_intervention_decision(normalized_input)

    if ask_outbox_adapter is not None and outbox_request_id is not None:
        adapter_gate = CapabilityAdapterGate(invocation_id=_new_id("invoke:"), allowed=True)
        responded_at_iso = decision.responded_at_iso or _now_iso()
        response_artifact = AskOutboxResponseArtifact(
            request_id=outbox_request_id,
            scope=phase,
            reason=decision.reason or "intervention decision recorded",
            evidence_refs=[EvidenceRef(kind="intervention_request", ref=request.request_id)],
            created_at_iso=request.created_at_iso,
            responded_at_iso=responded_at_iso,
            status=decision.action.value,
            escalation=decision.action == InterventionAction.ESCALATE,
            metadata=_to_dict(decision.metadata),
        )
        response_ref = append_ask_outbox_response_event(
            response_artifact.model_dump(mode="json"),
            adapter_gate=adapter_gate,
            path=prediction_log_path,
        )
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "ask_outbox_response",
                "phase": phase,
                "response": response_artifact.model_dump(mode="json"),
                "evidence_ref": response_ref,
            },
        )

    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "intervention_response",
            "phase": phase,
            "request_id": request.request_id,
            "response": decision.model_dump(mode="json"),
        },
    )
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "intervention_lifecycle",
            "phase": phase,
            "request_id": request.request_id,
            "action": decision.action.value,
            "reason": decision.reason,
            "metadata": _to_dict(decision.metadata),
            "override_source": _to_dict(decision.override_source),
            "override_provenance": decision.override_provenance,
            "responded_at_iso": decision.responded_at_iso,
        },
    )

    if decision.action in {InterventionAction.PAUSE, InterventionAction.TIMEOUT, InterventionAction.ESCALATE}:
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "intervention_terminal",
                "phase": phase,
                "request_id": request.request_id,
                "action": decision.action.value,
                "reason": decision.reason,
            },
        )
        append_turn_summary(ep)
        return False, decision

    return True, decision


def evaluate_invariant_gates(
    *,
    ep: Optional[Episode],
    scope: str,
    prediction_key: Optional[str],
    projection_state: ProjectionState,
    prediction_log_available: bool,
    gate_point: str = "pre-decision",
    just_written_prediction: Optional[Mapping[str, Any]] = None,
    halt_log_path: str | Path = "halts.jsonl",
) -> GateDecision:
    observer = getattr(ep, "observer", None) if ep is not None else None
    is_authorized, auth_context = _observer_authorized_for_action(
        observer=observer,
        action="evaluate_invariant_gates",
        required_capability="baseline.invariant_evaluation",
    )
    if ep is not None and not is_authorized:
        halt = _authorization_halt_record(
            stage=gate_point,
            reason="observer is not authorized to evaluate invariant gates",
            context=auth_context,
        )
        auth_halt_evidence_ref = append_halt_record(halt, halt_log_path=halt_log_path, stable_ids=_episode_stable_ids(ep))
        _append_authorization_issue(ep, halt=halt, context=auth_context)
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "halt_observation",
                "observation_type": "halt",
                **_halt_payload(halt),
                "halt_evidence_ref": auth_halt_evidence_ref,
            },
        )
        return halt

    current_predictions = {
        key: pred.prediction_id
        for key, pred in projection_state.current_predictions.items()
    }

    evaluations, result = _evaluate_invariant_gate_pipeline(
        observer=observer,
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
        just_written_prediction=just_written_prediction,
        gate_point=gate_point,
    )
    gate_checks: list[GateInvariantCheck] = []
    invariant_audit: list[InvariantAuditResult] = []

    outcome_bundle = result.artifact if isinstance(result, Success) else GatePredictionOutcome(
        pre_consume=tuple(ev.outcome for ev in evaluations if ev.phase == "pre_consume"),
        post_write=tuple(ev.outcome for ev in evaluations if ev.phase == "post_write"),
    )

    for evaluation in evaluations:
        normalized = normalize_outcome(evaluation.outcome, gate=gate_point)
        gate_checks.append(
            GateInvariantCheck(
                gate_point=f"{gate_point}:{evaluation.phase}",
                output=normalized,
            )
        )
        invariant_audit.append(
            _invariant_audit_result_from_checker(
                f"{gate_point}:{evaluation.phase}",
                normalized,
            )
        )

    halt_outcome, _ = _first_halt_from_evaluations(evaluations=evaluations, gate_point=gate_point)

    if isinstance(result, HaltRecord) and halt_outcome is not None:
        halt_validation = normalize_outcome(
            REGISTRY[InvariantId.EXPLAINABLE_HALT_PAYLOAD](
                default_check_context(
                    scope=scope,
                    prediction_key=prediction_key,
                    current_predictions=current_predictions,
                    prediction_log_available=prediction_log_available,
                    just_written_prediction=just_written_prediction,
                    halt_candidate=halt_outcome,
                )
            ),
            gate=gate_point,
        )
        gate_checks.append(
            GateInvariantCheck(
                gate_point="halt_validation",
                output=halt_validation,
            )
        )
        invariant_audit.append(_invariant_audit_result_from_checker("halt_validation", halt_validation))

    result_kind = "prediction" if isinstance(result, Success) else "halt"

    halt_evidence_ref: Optional[Dict[str, str]] = None
    stable_ids = _episode_stable_ids(ep) if ep is not None else {}
    if isinstance(result, HaltRecord):
        halt_evidence_ref = append_halt_record(
            result,
            halt_log_path=halt_log_path,
            stable_ids=stable_ids,
        )

    if ep is not None:
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "invariant_outcomes",
                "observer": _to_dict(getattr(ep, "observer", None)),
                "observer_enforcement": {
                    "requested_evaluation_invariants": list(getattr(observer, "evaluation_invariants", []) or []),
                    "enforced": bool(getattr(observer, "evaluation_invariants", []) or []),
                    "observer_role": getattr(observer, "role", None),
                    "authorization_level": getattr(observer, "authorization_level", None),
                },
                "scope": scope,
                "prediction_key": prediction_key,
                "invariant_context": {
                    "has_current_predictions": projection_state.has_current_predictions,
                    "current_predictions": dict(current_predictions),
                    "prediction_log_available": prediction_log_available,
                    "just_written_prediction": _to_dict(just_written_prediction),
                },
                "pre_consume": [_to_dict(outcome) for outcome in outcome_bundle.pre_consume],
                "post_write": [_to_dict(outcome) for outcome in outcome_bundle.post_write],
                "invariant_results": [_to_dict(outcome) for outcome in outcome_bundle.combined],
                "invariant_checks": [
                    {
                        "gate_point": check.gate_point,
                        "invariant_id": check.output.invariant_id,
                        "passed": check.output.passed,
                        "evidence": _to_dict(check.output.evidence),
                        "reason": check.output.reason,
                        "flow": check.output.flow,
                        "validity": check.output.validity,
                        "code": check.output.code,
                        "details": _to_dict(check.output.details),
                        "action_hints": _to_dict(check.output.action_hints),
                    }
                    for check in gate_checks
                ],
                "invariant_audit": [item.model_dump(mode="json") for item in invariant_audit],
                "kind": result_kind,
                "prediction": _to_dict(result.artifact) if isinstance(result, Success) else None,
                "halt": _halt_payload(result) if isinstance(result, HaltRecord) else None,
                "halt_evidence_ref": auth_halt_evidence_ref,
            },
        )

        if isinstance(result, HaltRecord):
            halt = result
            halt_observation = Observation(
                observation_id=_new_id("obs:"),
                t_observed_iso=_now_iso(),
                type=ObservationType.HALT,
                text=halt.reason,
                source=f"invariant:{halt.invariant_id}",
            )
            if not hasattr(ep, "observations") or getattr(ep, "observations") is None:
                setattr(ep, "observations", [])
            ep.observations.append(halt_observation)
            _append_episode_artifact(
                ep,
                {
                    "artifact_kind": "halt_observation",
                    "observation_type": "halt",
                    "observation_id": halt_observation.observation_id,
                    **_halt_payload(halt),
                    "halt_evidence_ref": auth_halt_evidence_ref,
                },
            )

    return result




def append_prediction_record(
    pred: PredictionRecord,
    *,
    prediction_log_path: str | Path = "artifacts/predictions.jsonl",
    stable_ids: Optional[Mapping[str, str]] = None,
    episode: Optional[Episode] = None,
    projection_state: Optional[ProjectionState] = None,
    explicit_gate_pass_present: bool = True,
    halt_log_path: str | Path = "halts.jsonl",
) -> dict[str, str] | HaltRecord:
    state_for_policy = projection_state or ProjectionState(
        current_predictions={pred.scope_key: pred},
        prediction_history=[],
        updated_at_iso=_now_iso(),
    )
    if not state_for_policy.has_current_predictions:
        state_for_policy = state_for_policy.model_copy(
            update={"current_predictions": {pred.scope_key: pred}}
        )
    policy_decision = _capability_invocation_policy_decision(
        observer=getattr(episode, "observer", None),
        projection_state=state_for_policy,
        scope_key=pred.scope_key,
        prediction_key=pred.prediction_key,
        explicit_gate_pass_present=explicit_gate_pass_present,
        action="append_prediction_record_event",
        capability="prediction.persistence",
        required_capability="baseline.invariant_evaluation",
        stage="capability-invocation",
    )
    if not policy_decision.allowed:
        return _persist_policy_denial(ep=episode, decision=policy_decision, halt_log_path=halt_log_path)

    adapter_gate = CapabilityAdapterGate(invocation_id=policy_decision.attempt.invocation_id, allowed=True)

    prediction_payload: Any = pred.model_dump(mode="json")
    if stable_ids:
        prediction_payload = {**dict(stable_ids), **prediction_payload}
    prediction_ref = append_prediction_event(
        prediction_payload,
        adapter_gate=adapter_gate,
        path=prediction_log_path,
        episode_id=getattr(episode, "episode_id", None),
        conversation_id=getattr(episode, "conversation_id", None),
        turn_index=getattr(episode, "turn_index", None),
    )

    payload: Any = pred.model_dump(mode="json")
    payload["evidence_refs"] = [_to_dict(item) for item in pred.evidence_refs]
    payload["evidence_refs"].append(prediction_ref)
    if stable_ids:
        payload = {**dict(stable_ids), **payload}

    return append_prediction_record_event(
        payload,
        adapter_gate=adapter_gate,
        path=prediction_log_path,
        episode_id=getattr(episode, "episode_id", None),
        conversation_id=getattr(episode, "conversation_id", None),
        turn_index=getattr(episode, "turn_index", None),
    )


def append_halt_record(
    halt: HaltRecord,
    *,
    halt_log_path: str | Path = "halts.jsonl",
    stable_ids: Optional[Mapping[str, str]] = None,
    adapter_gate: Optional[CapabilityAdapterGate] = None,
) -> dict[str, str]:
    if adapter_gate is None:
        adapter_gate = CapabilityAdapterGate(invocation_id=_new_id("invoke:"), allowed=True)
    payload: Any = halt.to_canonical_payload()
    if stable_ids:
        payload = {**dict(stable_ids), **halt.to_canonical_payload()}
    return append_halt(halt_log_path, payload, adapter_gate=adapter_gate)


def _stable_repair_id(*, scope_key: str, prediction_id: str, compared_at_iso: str) -> str:
    return f"repair:{sha1_text(f'{scope_key}|{prediction_id}|{compared_at_iso}')}"


def _repair_lineage_ref(
    *,
    ep: Episode,
    pred: PredictionRecord,
) -> RepairLineageRef:
    return RepairLineageRef(
        conversation_id=ep.conversation_id,
        episode_id=ep.episode_id,
        turn_index=ep.turn_index,
        scope_key=pred.scope_key,
        prediction_id=pred.prediction_id,
        correction_root_prediction_id=pred.correction_root_prediction_id or pred.prediction_id,
    )


def _append_repair_event(
    event: RepairProposalEvent | RepairResolutionEvent,
    *,
    prediction_log_path: str | Path,
    stable_ids: Optional[Mapping[str, str]],
) -> dict[str, str]:
    payload: dict[str, Any] = event.model_dump(mode="json")
    if stable_ids:
        payload = {**dict(stable_ids), **payload}
    append_jsonl(prediction_log_path, payload)
    p = Path(prediction_log_path)
    line_count = len(p.read_text(encoding="utf-8").splitlines())
    return {"kind": "jsonl", "ref": f"{p.name}@{line_count}"}


def _apply_accepted_repair_event(
    projection_state: ProjectionState,
    *,
    resolution_event: RepairResolutionEvent,
) -> ProjectionState:
    if resolution_event.decision != RepairResolution.ACCEPTED or resolution_event.accepted_prediction is None:
        return projection_state
    return _project_current_at(
        resolution_event.accepted_prediction,
        projection_state,
        updated_at_iso=resolution_event.resolved_at_iso,
    )


def _project_current_at(
    pred: PredictionRecord,
    projection_state: ProjectionState,
    *,
    updated_at_iso: str,
) -> ProjectionState:
    current = dict(projection_state.current_predictions)
    current[pred.scope_key] = pred
    history = [*projection_state.prediction_history, pred]
    return ProjectionState(
        current_predictions=current,
        prediction_history=history,
        correction_metrics=dict(projection_state.correction_metrics),
        last_comparison_at_iso=projection_state.last_comparison_at_iso,
        updated_at_iso=updated_at_iso,
    )


def project_current(pred: PredictionRecord, projection_state: ProjectionState) -> ProjectionState:
    return _project_current_at(pred, projection_state, updated_at_iso=_now_iso())


def replay_projection_analytics(prediction_log_path: str | Path) -> ProjectionReplayResult:
    path = Path(prediction_log_path)
    if not path.exists():
        return ProjectionReplayResult(
            projection_state=ProjectionState(current_predictions={}, updated_at_iso="1970-01-01T00:00:00+00:00"),
            analytics_snapshot=ProjectionAnalyticsSnapshot(),
            records_processed=0,
        )

    projection = ProjectionState(current_predictions={}, updated_at_iso="1970-01-01T00:00:00+00:00")
    fields = set(PredictionRecord.model_fields)
    records_processed = 0
    lineage_rows: list[Mapping[str, Any]] = []
    seen_prediction_fingerprints: set[tuple[Any, ...]] = set()

    for raw in iter_projection_lineage_records(path):
        lineage_rows.append(raw)
        kind = raw.get("event_kind")
        if kind in {"prediction_record", "prediction"}:
            payload = {k: v for k, v in raw.items() if k in fields}
            pred = PredictionRecord.model_validate(payload)
            fingerprint = (
                pred.prediction_id,
                pred.correction_revision,
                pred.compared_at_iso,
                pred.corrected_at_iso,
                pred.was_corrected,
                pred.absolute_error,
                pred.expectation,
            )
            if fingerprint in seen_prediction_fingerprints:
                continue
            seen_prediction_fingerprints.add(fingerprint)
            event_time = pred.corrected_at_iso or pred.compared_at_iso or pred.issued_at_iso
            projection = _project_current_at(pred, projection, updated_at_iso=event_time)
            records_processed += 1
            continue

        if kind == "repair_resolution":
            resolution = RepairResolutionEvent.model_validate(raw)
            accepted = resolution.accepted_prediction
            if (
                resolution.decision == RepairResolution.ACCEPTED
                and accepted is not None
            ):
                accepted_fingerprint = (
                    accepted.prediction_id,
                    accepted.correction_revision,
                    accepted.compared_at_iso,
                    accepted.corrected_at_iso,
                    accepted.was_corrected,
                    accepted.absolute_error,
                    accepted.expectation,
                )
                if accepted_fingerprint in seen_prediction_fingerprints:
                    continue
                seen_prediction_fingerprints.add(accepted_fingerprint)
                projection = _apply_accepted_repair_event(projection, resolution_event=resolution)
                records_processed += 1

    analytics = derive_projection_analytics_from_lineage(lineage_rows)

    metrics: Dict[str, float] = {}
    if analytics.correction_count > 0:
        metrics["comparisons"] = float(analytics.correction_count)
        metrics["absolute_error_total"] = analytics.correction_cost_total
        metrics["mae"] = analytics.correction_cost_mean

    last_comparison_at_iso = next(
        (
            pred.compared_at_iso or pred.corrected_at_iso
            for pred in reversed(projection.prediction_history)
            if pred.was_corrected
        ),
        None,
    )

    projection = projection.model_copy(
        update={
            "correction_metrics": metrics,
            "last_comparison_at_iso": last_comparison_at_iso,
        }
    )

    return ProjectionReplayResult(
        projection_state=projection,
        analytics_snapshot=analytics,
        records_processed=records_processed,
    )


def derive_projection_analytics_from_lineage(
    records: Sequence[Mapping[str, Any]],
) -> ProjectionAnalyticsSnapshot:
    """Pure analytics derivation from append-only persisted lineage rows."""

    fields = set(PredictionRecord.model_fields)
    correction_count = 0
    halt_count = 0
    correction_cost_total = 0.0
    attribution: Dict[str, CorrectionCostAttribution] = {}
    outstanding_requests: Dict[str, AskOutboxRequestArtifact] = {}
    resolved_requests: Dict[str, AskOutboxResponseArtifact] = {}
    request_outcome_linkage: Dict[str, str] = {}
    seen_corrected_prediction_fingerprints: set[tuple[Any, ...]] = set()

    for raw in records:
        kind = raw.get("event_kind")
        pred: PredictionRecord | None = None
        if kind in {"prediction_record", "prediction"}:
            payload = {k: v for k, v in raw.items() if k in fields}
            pred = PredictionRecord.model_validate(payload)
        elif kind == "repair_resolution":
            resolution = RepairResolutionEvent.model_validate(raw)
            if resolution.decision == RepairResolution.ACCEPTED and resolution.accepted_prediction is not None:
                pred = resolution.accepted_prediction
        elif kind == "ask_outbox_request":
            request = AskOutboxRequestArtifact.model_validate(raw)
            outstanding_requests[request.request_id] = request
            continue
        elif kind == "ask_outbox_response":
            response = AskOutboxResponseArtifact.model_validate(raw)
            resolved_requests[response.request_id] = response
            request_outcome_linkage[response.request_id] = response.status
            outstanding_requests.pop(response.request_id, None)
            continue

        if pred is not None:
            if not pred.was_corrected or pred.absolute_error is None:
                continue
            corrected_fingerprint = (
                pred.prediction_id,
                pred.correction_revision,
                pred.compared_at_iso,
                pred.corrected_at_iso,
                pred.absolute_error,
            )
            if corrected_fingerprint in seen_corrected_prediction_fingerprints:
                continue
            seen_corrected_prediction_fingerprints.add(corrected_fingerprint)
            correction_count += 1
            correction_cost_total += float(pred.absolute_error)
            root_id = pred.correction_root_prediction_id or pred.prediction_id
            item = attribution.get(root_id)
            if item is None:
                item = CorrectionCostAttribution(root_prediction_id=root_id)
            item = item.model_copy(
                update={
                    "correction_count": item.correction_count + 1,
                    "correction_cost_total": item.correction_cost_total + float(pred.absolute_error),
                }
            )
            attribution[root_id] = item
            continue

        try:
            HaltRecord.from_payload(raw)
            halt_count += 1
        except HaltPayloadValidationError:
            continue

    return ProjectionAnalyticsSnapshot(
        correction_count=correction_count,
        halt_count=halt_count,
        correction_cost_total=correction_cost_total,
        correction_cost_attribution=attribution,
        outstanding_human_requests=outstanding_requests,
        resolved_human_requests=resolved_requests,
        request_outcome_linkage=request_outcome_linkage,
    )


def _emit_turn_prediction(ep: Episode) -> PredictionRecord:
    expectation = 1.0 if ep.ask.status == AskStatus.OK else 0.0
    now = _now_iso()
    return PredictionRecord(
        prediction_id=_new_id("pred:"),
        prediction_key=f"turn:{ep.turn_index}:user_response_present",
        scope_key=f"turn:{ep.turn_index}",
        prediction_target="user_response_present",
        filtration_id=f"conversation:{ep.conversation_id}",
        target_variable="user_response_present",
        target_horizon_iso=ep.t_asked_iso,
        target_horizon_turns=1,
        expectation=expectation,
        uncertainty=0.5,
        issued_at_iso=now,
        assumptions=["turn_observation_available"],
        evidence_refs=[],
    )


def _reconcile_predictions(
    ep: Episode,
    projection_state: ProjectionState,
    *,
    prediction_log_path: str | Path,
    invariant_handling_mode: InvariantHandlingMode = InvariantHandlingMode.STRICT_HALT,
) -> ProjectionState:
    observed_text = extract_user_utterance(ep)
    observed_value = 1.0 if observed_text else 0.0

    updated_projection = projection_state
    metrics = dict(projection_state.correction_metrics)
    compared = 0
    error_total = 0.0
    stable_ids = _episode_stable_ids(ep)

    for scope_key, pred in list(projection_state.current_predictions.items()):
        if pred.target_variable != "user_response_present" or pred.expectation is None:
            continue

        updated_pred, outcome = bind_prediction_outcome(pred, observed_outcome=observed_value)
        compared += 1
        error_total += outcome.absolute_error
        compared_at = outcome.recorded_at_iso

        if repair_mode_enabled(invariant_handling_mode):
            repair_id = _stable_repair_id(
                scope_key=scope_key,
                prediction_id=pred.prediction_id,
                compared_at_iso=compared_at,
            )
            lineage_ref = _repair_lineage_ref(ep=ep, pred=pred)
            proposal = RepairProposalEvent(
                repair_id=repair_id,
                proposed_at_iso=compared_at,
                reason="prediction outcome reconciliation proposed",
                invariant_id=InvariantId.PREDICTION_OUTCOME_BINDING.value,
                lineage_ref=lineage_ref,
                proposed_prediction=updated_pred,
                prediction_outcome=outcome,
            )
            proposal_ref = _append_repair_event(
                proposal,
                prediction_log_path=prediction_log_path,
                stable_ids=stable_ids,
            )
            resolution = RepairResolutionEvent(
                repair_id=repair_id,
                decision=RepairResolution.ACCEPTED,
                resolved_at_iso=compared_at,
                lineage_ref=lineage_ref,
                accepted_prediction=updated_pred,
            )
            resolution_ref = _append_repair_event(
                resolution,
                prediction_log_path=prediction_log_path,
                stable_ids=stable_ids,
            )
            updated_projection = _apply_accepted_repair_event(updated_projection, resolution_event=resolution)
            _append_episode_artifact(
                ep,
                {
                    "artifact_kind": "repair_event",
                    "repair_id": repair_id,
                    "mode": invariant_handling_mode.value,
                    "proposal": proposal.model_dump(mode="json"),
                    "resolution": resolution.model_dump(mode="json"),
                    "proposal_evidence_ref": proposal_ref,
                    "resolution_evidence_ref": resolution_ref,
                },
            )
        else:
            persist_result = append_prediction_record(
                updated_pred,
                prediction_log_path=prediction_log_path,
                stable_ids=stable_ids,
                episode=ep,
                projection_state=updated_projection,
            )
            if not isinstance(persist_result, HaltRecord):
                updated_projection = _project_current_at(updated_pred, updated_projection, updated_at_iso=compared_at)

        binding_ctx = default_check_context(
            scope=scope_key,
            prediction_key=scope_key,
            current_predictions={k: v.prediction_id for k, v in updated_projection.current_predictions.items()},
            prediction_log_available=True,
            prediction_outcome=outcome.model_dump(mode="json"),
        )
        binding_outcome = REGISTRY[InvariantId.PREDICTION_OUTCOME_BINDING](binding_ctx)

        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "prediction_comparison",
                "prediction_id": updated_pred.prediction_id,
                "scope_key": scope_key,
                "expected": pred.expectation,
                "observed": observed_value,
                "error": outcome.error_metric,
                "absolute_error": outcome.absolute_error,
                "compared_at_iso": compared_at,
                "prediction_outcome": outcome.model_dump(mode="json"),
                "prediction_outcome_binding": normalize_outcome(
                    binding_outcome,
                    gate="post-observation",
                ).__dict__,
                "repair_mode": invariant_handling_mode.value,
            },
        )

    if compared > 0:
        metrics["comparisons"] = float(metrics.get("comparisons", 0.0) + compared)
        metrics["absolute_error_total"] = float(metrics.get("absolute_error_total", 0.0) + error_total)
        metrics["mae"] = metrics["absolute_error_total"] / metrics["comparisons"]

    return ProjectionState(
        current_predictions=dict(updated_projection.current_predictions),
        prediction_history=list(updated_projection.prediction_history),
        correction_metrics=metrics,
        last_comparison_at_iso=_now_iso() if compared else projection_state.last_comparison_at_iso,
        updated_at_iso=_now_iso(),
    )


def bind_prediction_outcome(
    pred: PredictionRecord,
    *,
    observed_outcome: Any,
    recorded_at_iso: Optional[str] = None,
) -> tuple[PredictionRecord, PredictionOutcome]:
    expected = pred.expectation
    observed_value = float(observed_outcome)
    if expected is None:
        error_metric = 0.0
        absolute_error = 0.0
    else:
        error_metric = observed_value - expected
        absolute_error = abs(error_metric)

    compared_at = recorded_at_iso or _now_iso()
    updated_pred = pred.model_copy(
        update={
            "observed_value": observed_value,
            "prediction_error": error_metric,
            "absolute_error": absolute_error,
            "observed_at_iso": compared_at,
            "compared_at_iso": compared_at,
            "was_corrected": True,
            "corrected_at_iso": compared_at,
            "correction_parent_prediction_id": pred.prediction_id,
            "correction_root_prediction_id": pred.correction_root_prediction_id or pred.prediction_id,
            "correction_revision": int(pred.correction_revision) + 1,
        }
    )

    outcome = PredictionOutcome(
        prediction_id=pred.prediction_id,
        prediction_scope_key=pred.scope_key,
        target_variable=pred.target_variable,
        observed_outcome=observed_value,
        error_metric=error_metric,
        absolute_error=absolute_error,
        recorded_at_iso=compared_at,
    )
    return updated_pred, outcome

def run_mission_loop(
    ep: Episode,
    belief: BeliefState,
    projection_state: ProjectionState,
    *,
    pending_predictions: Sequence[PredictionRecord | Mapping[str, Any]] = (),
    prediction_log_path: str | Path = "artifacts/predictions.jsonl",
    intervention_hook: Optional[InterventionLifecycleHook] = None,
    ask_outbox_adapter: Optional[AskOutboxAdapter] = None,
    observation_freshness_policy_adapter: Optional[ObservationFreshnessPolicyAdapter] = None,
    invariant_handling_mode: InvariantHandlingMode = InvariantHandlingMode.STRICT_HALT,
    halt_log_path: str | Path = "halts.jsonl",
) -> tuple[Episode, BeliefState, ProjectionState]:
    """
    Mission-loop helper: materialize prediction updates before decision stages.
    """
    updated_projection = projection_state

    should_continue, _ = _apply_intervention_hook(
        ep=ep,
        belief=belief,
        projection_state=updated_projection,
        phase="mission_loop:start",
        intervention_hook=intervention_hook,
        ask_outbox_adapter=ask_outbox_adapter,
        prediction_log_path=prediction_log_path,
        halt_log_path=halt_log_path,
    )
    if not should_continue:
        return ep, belief, updated_projection

    if observation_freshness_policy_adapter is not None:
        evaluate_observation_freshness(
            ep=ep,
            belief=belief,
            projection_state=updated_projection,
            policy_adapter=observation_freshness_policy_adapter,
            ask_outbox_adapter=ask_outbox_adapter,
        )

    turn_prediction = _emit_turn_prediction(ep)
    turn_prediction_ref = append_prediction_record(
        turn_prediction,
        prediction_log_path=prediction_log_path,
        stable_ids=_episode_stable_ids(ep),
        episode=ep,
        projection_state=updated_projection,
    )
    if isinstance(turn_prediction_ref, HaltRecord):
        append_turn_summary(ep)
        return ep, belief, updated_projection
    updated_projection = project_current(turn_prediction, updated_projection)
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "prediction_emit",
            "prediction_id": turn_prediction.prediction_id,
            "scope_key": turn_prediction.scope_key,
            "target_variable": turn_prediction.target_variable,
            "target_horizon_iso": turn_prediction.target_horizon_iso,
            "evidence_ref": turn_prediction_ref,
        },
    )

    last_written_prediction = {"key": turn_prediction.scope_key, "evidence_refs": [turn_prediction_ref]}
    for pending in pending_predictions:
        pred = pending if isinstance(pending, PredictionRecord) else PredictionRecord.model_validate(pending)
        evidence_ref = append_prediction_record(
            pred,
            prediction_log_path=prediction_log_path,
            stable_ids=_episode_stable_ids(ep),
            episode=ep,
            projection_state=updated_projection,
        )
        if isinstance(evidence_ref, HaltRecord):
            append_turn_summary(ep)
            return ep, belief, updated_projection
        updated_projection = project_current(pred, updated_projection)
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "prediction_update",
                "prediction_id": pred.prediction_id,
                "scope_key": pred.scope_key,
                "filtration_id": pred.filtration_id,
                "target_variable": pred.target_variable,
                "target_horizon_iso": pred.target_horizon_iso,
                "evidence_ref": evidence_ref,
                "projection_updated_at_iso": updated_projection.updated_at_iso,
            },
        )
        last_written_prediction = {"key": pred.scope_key, "evidence_refs": [evidence_ref]}

    active_scope = next(iter(updated_projection.current_predictions), "decision_stage")
    pre_decision_gate = evaluate_invariant_gates(
        ep=ep,
        scope=active_scope,
        prediction_key=None,
        projection_state=updated_projection,
        prediction_log_available=True,
        gate_point="pre-decision",
    )
    if isinstance(pre_decision_gate, HaltRecord):
        append_turn_summary(ep)
        return ep, belief, updated_projection

    should_continue, _ = _apply_intervention_hook(
        ep=ep,
        belief=belief,
        projection_state=updated_projection,
        phase="mission_loop:post_pre_decision_gate",
        intervention_hook=intervention_hook,
        ask_outbox_adapter=ask_outbox_adapter,
        prediction_log_path=prediction_log_path,
        halt_log_path=halt_log_path,
    )
    if not should_continue:
        return ep, belief, updated_projection

    ep = ingest_observation(ep)
    updated_projection = _reconcile_predictions(
        ep,
        updated_projection,
        prediction_log_path=prediction_log_path,
        invariant_handling_mode=invariant_handling_mode,
    )

    post_observation_gate = evaluate_invariant_gates(
        ep=ep,
        scope=active_scope,
        prediction_key=None,
        projection_state=updated_projection,
        prediction_log_available=True,
        gate_point="post-observation",
    )
    if isinstance(post_observation_gate, HaltRecord):
        append_turn_summary(ep)
        return ep, belief, updated_projection

    should_continue, _ = _apply_intervention_hook(
        ep=ep,
        belief=belief,
        projection_state=updated_projection,
        phase="mission_loop:post_observation_gate",
        intervention_hook=intervention_hook,
        ask_outbox_adapter=ask_outbox_adapter,
        prediction_log_path=prediction_log_path,
        halt_log_path=halt_log_path,
    )
    if not should_continue:
        return ep, belief, updated_projection

    pre_output_gate = evaluate_invariant_gates(
        ep=ep,
        scope=active_scope,
        prediction_key=cast(Optional[str], last_written_prediction.get("key")),
        projection_state=updated_projection,
        prediction_log_available=True,
        gate_point="pre-output",
        just_written_prediction=last_written_prediction,
    )
    if isinstance(pre_output_gate, HaltRecord):
        append_turn_summary(ep)
        return ep, belief, updated_projection

    should_continue, _ = _apply_intervention_hook(
        ep=ep,
        belief=belief,
        projection_state=updated_projection,
        phase="mission_loop:post_pre_output_gate",
        intervention_hook=intervention_hook,
        ask_outbox_adapter=ask_outbox_adapter,
        prediction_log_path=prediction_log_path,
        halt_log_path=halt_log_path,
    )
    if not should_continue:
        return ep, belief, updated_projection

    ep, belief = apply_utterance_interpretation(ep, belief)
    ep, belief = apply_schema_bubbling(ep, belief)
    append_turn_summary(ep)
    return ep, belief, updated_projection

def build_episode(
    *,
    conversation_id: str,
    turn_index: int,
    assistant_prompt_asked: str,
    policy_decision: VerbosityDecision,
    payload: Dict[str, Any],
    outputs: EpisodeOutputs,
    observer: Optional[ObserverFrame] = None,
) -> Episode:
    err = payload.get("error")
    capture: Optional[CaptureOutcome]
    if isinstance(err, CaptureOutcome):
        capture = err
    elif isinstance(err, str):
        if err == CaptureStatus.NO_RESPONSE.value:
            capture = CaptureOutcome(status=CaptureStatus.NO_RESPONSE)
        else:
            capture = CaptureOutcome(status=CaptureStatus.ERROR, message=err)
    elif isinstance(err, dict):
        capture = CaptureOutcome.model_validate(err)
    else:
        capture = None

    if capture is not None and capture.status == CaptureStatus.NO_RESPONSE:
        status = AskStatus.NO_RESPONSE
    elif capture is not None:
        status = AskStatus.ERROR
    else:
        status = AskStatus.OK

    m = payload.get("metrics") or {}
    metrics = AskMetrics(
        elapsed_s=float(m.get("elapsed_s", 0.0)),
        question_chars=int(m.get("question_chars", 0)),
        question_words=int(m.get("question_words", 0)),
    )

    ask = AskResult(
        status=status,
        sentence=payload.get("sentence"),
        slots=payload.get("slots") or {},
        error=capture,
        metrics=metrics,
    )

    ep = Episode(
        episode_id=_new_id("ep:"),
        conversation_id=conversation_id,
        turn_index=int(turn_index),
        t_asked_iso=_now_iso(),
        assistant_prompt_asked=assistant_prompt_asked,
        observer=observer or default_observer_frame(),
        policy_decision=policy_decision,
        ask=ask,
        observations=[],
        outputs=outputs,
        artifacts=[],
        effects=[],
    )
    stable_ids = _find_stable_ids_from_payload(payload)
    _append_episode_artifact(
        ep,
        {
            "kind": "policy_hypothesis",
            "decision_id": policy_decision.decision_id,
            "hypothesis": policy_decision.hypothesis,
            "reason_codes": policy_decision.reason_codes,
        },
        stable_ids=stable_ids,
    )
    if stable_ids:
        _append_episode_artifact(ep, {"kind": "stable_ids", **stable_ids}, stable_ids=stable_ids)
    return ep


def ingest_observation(ep: Episode) -> Episode:
    obs_id = f"obs:{ep.episode_id}:0"
    t = _now_iso()

    if not hasattr(ep, "observations") or getattr(ep, "observations") is None:
        setattr(ep, "observations", [])

    if ep.ask.status == AskStatus.OK and (ep.ask.sentence or "").strip():
        ep.observations.append(
            Observation(
                observation_id=obs_id,
                t_observed_iso=t,
                type=ObservationType.USER_UTTERANCE,
                text=(ep.ask.sentence or "").strip(),
                source=f"channel:{ep.policy_decision.channel.value}",
            )
        )
    else:
        ep.observations.append(
            Observation(
                observation_id=obs_id,
                t_observed_iso=t,
                type=ObservationType.SILENCE,
                text=None,
                source=f"channel:{ep.policy_decision.channel.value}",
            )
        )
    return ep


def extract_user_utterance(ep: Episode) -> Optional[str]:
    for o in ep.observations:
        if o.type == ObservationType.USER_UTTERANCE:
            return (o.text or "").strip() or None
    return None

def attach_decision_effect(prev_ep: Optional[Episode], curr_ep: Episode) -> Episode:
    if not prev_ep:
        return curr_ep

    decision_id = getattr(prev_ep.policy_decision, "decision_id", None)
    if not decision_id:
        return curr_ep

    is_authorized, auth_context = _observer_authorized_for_action(
        observer=curr_ep.observer,
        action="attach_decision_effect",
        required_capability="baseline.evaluation",
    )
    if not is_authorized:
        halt = _authorization_halt_record(
            stage="decision-evaluation",
            reason="observer is not authorized to attach decision effects",
            context=auth_context,
        )
        _append_authorization_issue(curr_ep, halt=halt, context=auth_context)
        return curr_ep

    user_text = extract_user_utterance(curr_ep)
    had_user = bool(user_text)
    user_chars = len(user_text) if user_text else 0

    hyp = getattr(prev_ep.policy_decision, "hypothesis", None)
    held = bool(curr_ep.ask.status == AskStatus.OK and had_user)

    eff = DecisionEffect(
        evaluates_decision_id=decision_id,
        decision_episode_id=prev_ep.episode_id,
        evaluated_in_episode_id=curr_ep.episode_id,
        response_captured=held,
        status=curr_ep.ask.status,
        had_user_utterance=had_user,
        user_utterance_chars=int(user_chars),
        elapsed_s=float(curr_ep.ask.metrics.elapsed_s),
        notes={
            "hypothesis": hyp,
            "held": held,
            "observer": _to_dict(curr_ep.observer),
            "observer_role": getattr(curr_ep.observer, "role", None),
            "authorization_level": getattr(curr_ep.observer, "authorization_level", None),
        },
        hypothesis_eval=HypothesisEvaluation(hypothesis=hyp, held=held),
    )

    curr_ep.effects.append(eff)
    return curr_ep


def _validated_selection(raw_selection: Any) -> SchemaSelection:
    if isinstance(raw_selection, SchemaSelection):
        return raw_selection

    raise TypeError(
        "naive_schema_selector must return SchemaSelection; "
        f"got {type(raw_selection).__name__}"
    )


def apply_schema_bubbling(ep: Episode, belief: BeliefState) -> tuple[Episode, BeliefState]:
    """
    Single-writer: updates belief state based on the latest observation.

    Option A: pending obligation is represented via:
      - belief.pending_about (dict)
      - belief.pending_question (str)
      - belief.pending_attempts (int)
    """
    is_authorized, auth_context = _observer_authorized_for_action(
        observer=ep.observer,
        action="apply_schema_bubbling",
        required_capability="baseline.schema_selection",
    )
    if not is_authorized:
        halt = _authorization_halt_record(
            stage="policy-schema",
            reason="observer is not authorized for schema bubbling",
            context=auth_context,
        )
        _append_authorization_issue(ep, halt=halt, context=auth_context)
        return ep, belief

    user_text = extract_user_utterance(ep)
    raw_selection: SchemaSelection = naive_schema_selector(user_text, error=ep.ask.error)
    sel = _validated_selection(raw_selection)

    # --- Schemas
    belief.active_schemas = [h.name for h in sel.schemas]
    belief.schema_confidence = {h.name: float(h.score) for h in sel.schemas}

    # --- Ambiguities
    belief.ambiguities_active = list(sel.ambiguities or [])
    belief.ambiguity_state = project_ambiguity_state(belief.ambiguities_active)

    if belief.ambiguity_state != AmbiguityStatus.UNRESOLVED:
        # Clear pending obligation
        belief.pending_about = None
        belief.pending_question = None
        belief.pending_attempts = 0
    else:
        # If we already have a pending obligation, keep it (do not reset attempts here)
        if belief.pending_about is None:
            chosen = next((a for a in belief.ambiguities_active if a.status == AmbiguityStatus.UNRESOLVED), None)

            if chosen is not None:
                belief.pending_about = {
                    "kind": chosen.about.kind.value,
                    "key": chosen.about.key,
                }
                if chosen.about.span is not None:
                    belief.pending_about["span"] = {
                        "text": chosen.about.span.text,
                        "start": chosen.about.span.start,
                        "end": chosen.about.span.end,
                    }

                # Prefer the first ClarifyingQuestion.q if present
                q: Optional[str] = None
                if chosen.ask:
                    q = chosen.ask[0].q.strip()

                # Fallback: synthesize
                if not q:
                    span = chosen.about.span.text if chosen.about.span is not None else None
                    if isinstance(span, str) and span.strip():
                        q = f"Be specific: what does “{span.strip()}” refer to?"
                    else:
                        q = "Be specific: what exactly are you referring to?"

                belief.pending_question = q
                belief.pending_attempts = 1
            else:
                belief.pending_attempts += 1

    belief.belief_version += 1
    belief.updated_at_iso = _now_iso()

    _append_episode_artifact(
        ep,
        {
            "kind": "schema_selection",
            "observer": _to_dict(getattr(ep, "observer", None)),
            "schemas": [{"name": h.name, "score": h.score, "about": _to_dict(h.about)} for h in sel.schemas],
            "ambiguities": [_to_dict(a) for a in belief.ambiguities_active],
            "ambiguity_state": belief.ambiguity_state.value,
            "notes": sel.notes,
            "pending_about": _to_dict(belief.pending_about),
            "pending_question": belief.pending_question,
            "pending_attempts": belief.pending_attempts,
        },
    )

    return ep, belief





def apply_utterance_interpretation(ep: Episode, belief: BeliefState) -> tuple[Episode, BeliefState]:
    is_authorized, auth_context = _observer_authorized_for_action(
        observer=ep.observer,
        action="apply_utterance_interpretation",
        required_capability="baseline.dialog",
    )
    if not is_authorized:
        halt = _authorization_halt_record(
            stage="policy-utterance",
            reason="observer is not authorized for utterance interpretation",
            context=auth_context,
        )
        _append_authorization_issue(ep, halt=halt, context=auth_context)
        return ep, belief

    user_text = extract_user_utterance(ep)
    utype = classify_utterance(user_text, ep.ask.error)

    belief.last_utterance_type = utype
    belief.last_status = ep.ask.status

    # Update consecutive no-response streak
    if ep.ask.status == AskStatus.NO_RESPONSE:
        belief.consecutive_no_response += 1
    else:
        belief.consecutive_no_response = 0

    _append_episode_artifact(
        ep,
        {
            "kind": "utterance_interpretation",
            "observer": _to_dict(getattr(ep, "observer", None)),
            "interpretation_frame": {
                "observer_role": getattr(ep.observer, "role", None),
                "authorization_level": getattr(ep.observer, "authorization_level", None),
            },
            "utterance_type": utype.value,
            "text_preview": (user_text[:80] if isinstance(user_text, str) else None),
            "consecutive_no_response": belief.consecutive_no_response,
        },
    )
    return ep, belief


def to_jsonable_episode(ep: Episode) -> Dict[str, Any]:
    """
    Always return a dict that json.dumps can serialize.
    """
    out = _to_dict(ep)
    if not isinstance(out, dict):
        raise TypeError(f"to_jsonable_episode expected dict, got {type(out).__name__}")
    return out
