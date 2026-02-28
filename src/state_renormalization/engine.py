# state_renormalization/engine.py
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence
from pydantic import BaseModel
from enum import Enum
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from state_renormalization.contracts import (
    AmbiguityStatus,
    CaptureOutcome,
    CaptureStatus,
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    HypothesisEvaluation,
    DecisionEffect,
    Episode,
    EpisodeOutputs,
    Observation,
    ObservationType,
    ObserverFrame,
    ProjectionState,
    PredictionOutcome,
    PredictionRecord,
    HaltRecord,
    EvidenceRef,
    SchemaSelection,
    UtteranceType,
    default_observer_frame,
    project_ambiguity_state,
)
from state_renormalization.adapters.persistence import append_halt, append_prediction_record_event
from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.invariants import (
    Flow as InvariantFlow,
    InvariantId,
    CheckerResult,
    InvariantOutcome,
    REGISTRY,
    default_check_context,
    normalize_outcome,
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


def _as_evidence_ref(item: Mapping[str, Any]) -> EvidenceRef:
    kind = str(item.get("kind") or "unknown")
    ref = item.get("ref")
    if ref is None and "value" in item:
        ref = item["value"]
    return EvidenceRef(kind=kind, ref=str(ref) if ref is not None else "")


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
    reason = outcome.reason
    return HaltRecord(
        halt_id=_stable_halt_id(stage=stage, outcome=outcome),
        stage=stage,
        invariant_id=outcome.invariant_id.value,
        reason=reason,
        evidence=[_as_evidence_ref(_to_dict(item)) for item in outcome.evidence],
        timestamp=_now_iso(),
        retryability=bool(outcome.action_hints),
    )


def _authorization_halt_record(*, stage: str, reason: str, context: Mapping[str, Any]) -> HaltRecord:
    evidence = [
        EvidenceRef(kind="authorization_scope", ref=f"action:{context.get('action', 'unknown')}"),
        EvidenceRef(kind="required_capability", ref=str(context.get("required_capability") or "unknown")),
    ]
    return HaltRecord(
        halt_id=f"halt:{sha1_text(f'{stage}|authorization.scope.v1|{reason}|{_to_dict(context)}')}",
        stage=stage,
        invariant_id="authorization.scope.v1",
        reason=reason,
        evidence=evidence,
        timestamp=_now_iso(),
        retryability=True,
    )


def _append_authorization_issue(ep: Episode, *, halt: HaltRecord, context: Mapping[str, Any]) -> None:
    _append_episode_artifact(
        ep,
        {
            "artifact_kind": "authorization_issue",
            "issue_type": "authorization_scope_violation",
            "halt_id": halt.halt_id,
            "stage": halt.stage,
            "invariant_id": halt.invariant_id,
            "reason": halt.reason,
            "observer": _to_dict(getattr(ep, "observer", None)),
            "authorization_context": _to_dict(context),
            "retryability": halt.retryability,
            "timestamp": halt.timestamp,
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

    try:
        doc = Parser().parse(TokenScanner(feature_path.read_text(encoding="utf-8")))
    except Exception:
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


def _run_invariant(invariant_id: InvariantId, *, ctx) -> InvariantOutcome:
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
        halt_evidence_ref = append_halt_record(halt, halt_log_path=halt_log_path, stable_ids=_episode_stable_ids(ep))
        _append_authorization_issue(ep, halt=halt, context=auth_context)
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "halt_observation",
                "observation_type": "halt",
                "halt_id": halt.halt_id,
                "stage": halt.stage,
                "invariant_id": halt.invariant_id,
                "reason": halt.reason,
                "retryability": halt.retryability,
                "timestamp": halt.timestamp,
                "evidence": [_to_dict(e) for e in halt.evidence],
                "halt_evidence_ref": halt_evidence_ref,
            },
        )
        return halt

    current_predictions = {
        key: pred.prediction_id
        for key, pred in projection_state.current_predictions.items()
    }

    pre_consume: Sequence[InvariantOutcome] = tuple()
    post_write: Sequence[InvariantOutcome] = tuple()
    gate_checks: list[GateInvariantCheck] = []
    evaluations: list[GateInvariantEvaluation] = []

    pre_outcome: Optional[InvariantOutcome] = None
    if _observer_allows_invariant(observer=observer, invariant_id=InvariantId.PREDICTION_AVAILABILITY):
        pre_ctx = default_check_context(
            scope=scope,
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
        )
        pre_outcome = _run_invariant(InvariantId.PREDICTION_AVAILABILITY, ctx=pre_ctx)
        pre_consume = (pre_outcome,)
        evaluations.append(GateInvariantEvaluation(phase="pre_consume", outcome=pre_outcome))

    post_outcome: Optional[InvariantOutcome] = None
    if just_written_prediction is not None and _observer_allows_invariant(
        observer=observer,
        invariant_id=InvariantId.EVIDENCE_LINK_COMPLETENESS,
    ):
        post_ctx = default_check_context(
            scope=scope,
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            just_written_prediction=just_written_prediction,
        )
        post_outcome = _run_invariant(InvariantId.EVIDENCE_LINK_COMPLETENESS, ctx=post_ctx)
        post_write = (post_outcome,)
        evaluations.append(GateInvariantEvaluation(phase="post_write", outcome=post_outcome))

    for evaluation in evaluations:
        gate_checks.append(
            GateInvariantCheck(
                gate_point=f"{gate_point}:{evaluation.phase}",
                output=normalize_outcome(evaluation.outcome, gate=gate_point),
            )
        )

    halt_outcome: Optional[InvariantOutcome] = None
    halt_stage: Optional[str] = None
    for evaluation in evaluations:
        if evaluation.outcome.flow == InvariantFlow.STOP:
            halt_outcome = evaluation.outcome
            halt_stage = f"{gate_point}:{evaluation.phase}"
            break

    halt_record: Optional[HaltRecord] = None
    if halt_outcome is not None and halt_stage is not None:
        halt_record = _halt_record_from_outcome(stage=halt_stage, outcome=halt_outcome)
        gate_checks.append(
            GateInvariantCheck(
                gate_point="halt_validation",
                output=normalize_outcome(
                    REGISTRY[InvariantId.EXPLAINABLE_HALT_PAYLOAD](
                        default_check_context(
                            scope=scope,
                            prediction_key=prediction_key,
                            current_predictions=current_predictions,
                            prediction_log_available=prediction_log_available,
                            just_written_prediction=just_written_prediction,
                            halt_candidate=halt_outcome,
                        )
                    ), gate=gate_point
                ),
            )
        )

    result_kind: str
    if halt_record is None:
        result = Success(artifact=GatePredictionOutcome(pre_consume=pre_consume, post_write=post_write))
        result_kind = "prediction"
    else:
        result = halt_record
        result_kind = "halt"

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
                "pre_consume": [_to_dict(outcome) for outcome in pre_consume],
                "post_write": [_to_dict(outcome) for outcome in post_write],
                "invariant_results": [_to_dict(outcome) for outcome in tuple(pre_consume) + tuple(post_write)],
                "invariant_checks": [
                    {
                        "gate_point": check.gate_point,
                        "invariant_id": check.output.invariant_id,
                        "passed": check.output.passed,
                        "evidence": _to_dict(check.output.evidence),
                        "reason": check.output.reason,
                    }
                    for check in gate_checks
                ],
                "kind": result_kind,
                "prediction": _to_dict(result.artifact) if isinstance(result, Success) else None,
                "halt": _to_dict(result) if isinstance(result, HaltRecord) else None,
                "halt_evidence_ref": halt_evidence_ref,
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
                    "halt_id": halt.halt_id,
                    "stage": halt.stage,
                    "invariant_id": halt.invariant_id,
                    "reason": halt.reason,
                    "retryability": halt.retryability,
                    "timestamp": halt.timestamp,
                    "evidence": [_to_dict(e) for e in halt.evidence],
                    "halt_evidence_ref": halt_evidence_ref,
                },
            )

    return result




def append_prediction_record(
    pred: PredictionRecord,
    *,
    prediction_log_path: str | Path = "artifacts/predictions.jsonl",
    stable_ids: Optional[Mapping[str, str]] = None,
    episode: Optional[Episode] = None,
) -> dict[str, str]:
    payload: Any = pred.model_dump(mode="json")
    if stable_ids:
        payload = {**dict(stable_ids), **payload}
    return append_prediction_record_event(
        payload,
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
) -> dict[str, str]:
    payload: Any = halt.to_persistence_dict()
    if stable_ids:
        payload = {**dict(stable_ids), **halt.to_persistence_dict()}
    return append_halt(halt_log_path, payload)


def project_current(pred: PredictionRecord, projection_state: ProjectionState) -> ProjectionState:
    current = dict(projection_state.current_predictions)
    current[pred.scope_key] = pred
    history = [*projection_state.prediction_history, pred]
    return ProjectionState(
        current_predictions=current,
        prediction_history=history,
        correction_metrics=dict(projection_state.correction_metrics),
        last_comparison_at_iso=projection_state.last_comparison_at_iso,
        updated_at_iso=_now_iso(),
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
) -> ProjectionState:
    observed_text = extract_user_utterance(ep)
    observed_value = 1.0 if observed_text else 0.0

    current_predictions = dict(projection_state.current_predictions)
    metrics = dict(projection_state.correction_metrics)
    compared = 0
    error_total = 0.0

    for scope_key, pred in list(current_predictions.items()):
        if pred.target_variable != "user_response_present" or pred.expectation is None:
            continue

        updated_pred, outcome = bind_prediction_outcome(pred, observed_outcome=observed_value)
        compared += 1
        error_total += outcome.absolute_error
        compared_at = outcome.recorded_at_iso
        current_predictions[scope_key] = updated_pred
        append_prediction_record(updated_pred, prediction_log_path=prediction_log_path, stable_ids=_episode_stable_ids(ep), episode=ep)

        binding_ctx = default_check_context(
            scope=scope_key,
            prediction_key=scope_key,
            current_predictions=current_predictions,
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
            },
        )

    if compared > 0:
        metrics["comparisons"] = float(metrics.get("comparisons", 0.0) + compared)
        metrics["absolute_error_total"] = float(metrics.get("absolute_error_total", 0.0) + error_total)
        metrics["mae"] = metrics["absolute_error_total"] / metrics["comparisons"]

    return ProjectionState(
        current_predictions=current_predictions,
        prediction_history=list(projection_state.prediction_history),
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
) -> tuple[Episode, BeliefState, ProjectionState]:
    """
    Mission-loop helper: materialize prediction updates before decision stages.
    """
    updated_projection = projection_state

    turn_prediction = _emit_turn_prediction(ep)
    turn_prediction_ref = append_prediction_record(
        turn_prediction,
        prediction_log_path=prediction_log_path,
        stable_ids=_episode_stable_ids(ep),
        episode=ep,
    )
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
        )
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

    ep = ingest_observation(ep)
    updated_projection = _reconcile_predictions(ep, updated_projection, prediction_log_path=prediction_log_path)

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

    pre_output_gate = evaluate_invariant_gates(
        ep=ep,
        scope=active_scope,
        prediction_key=last_written_prediction.get("key"),
        projection_state=updated_projection,
        prediction_log_available=True,
        gate_point="pre-output",
        just_written_prediction=last_written_prediction,
    )
    if isinstance(pre_output_gate, HaltRecord):
        append_turn_summary(ep)
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
    policy_decision,
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
