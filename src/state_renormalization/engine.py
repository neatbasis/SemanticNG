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
    NormalizedCheckerOutput,
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
class PredictionOutcome:
    pre_consume: Sequence[InvariantOutcome] = field(default_factory=tuple)
    post_write: Sequence[InvariantOutcome] = field(default_factory=tuple)


    @property
    def combined(self) -> Sequence[InvariantOutcome]:
        return tuple(self.pre_consume) + tuple(self.post_write)


@dataclass(frozen=True)
class GateSuccessOutcome:
    artifact: PredictionOutcome


@dataclass(frozen=True)
class GateHaltOutcome:
    artifact: HaltRecord


GateDecision = GateSuccessOutcome | GateHaltOutcome


@dataclass(frozen=True)
class GateInvariantCheck:
    gate_point: str
    output: NormalizedCheckerOutput


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
        violated_invariant_id=outcome.invariant_id.value,
        reason=reason,
        evidence_refs=[_as_evidence_ref(_to_dict(item)) for item in outcome.evidence],
        timestamp_iso=_now_iso(),
        retryable=bool(outcome.action_hints),
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
    explainable_halt = REGISTRY[InvariantId.EXPLAINABLE_HALT_COMPLETENESS](h0_ctx)
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
    just_written_prediction: Optional[Mapping[str, Any]] = None,
    halt_log_path: str | Path = "halts.jsonl",
) -> GateDecision:
    observer = getattr(ep, "observer", None) if ep is not None else None
    current_predictions = {
        key: pred.prediction_id
        for key, pred in projection_state.current_predictions.items()
    }

    pre_consume: Sequence[InvariantOutcome] = tuple()
    gate_checks: list[GateInvariantCheck] = []
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
        gate_checks.append(GateInvariantCheck(gate_point="pre_consume", output=normalize_outcome(pre_outcome)))

    post_write: Sequence[InvariantOutcome] = tuple()
    if just_written_prediction is not None and _observer_allows_invariant(
        observer=observer,
        invariant_id=InvariantId.PREDICTION_RETRIEVABILITY,
    ):
        post_ctx = default_check_context(
            scope=scope,
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            just_written_prediction=just_written_prediction,
        )
        post_write = (_run_invariant(InvariantId.PREDICTION_RETRIEVABILITY, ctx=post_ctx),)
        gate_checks.append(
            GateInvariantCheck(gate_point="post_write", output=normalize_outcome(post_write[0]))
        )

    halt_outcome: Optional[InvariantOutcome] = None
    halt_stage: Optional[str] = None
    if pre_outcome is not None and pre_outcome.flow == InvariantFlow.STOP:
        halt_outcome = pre_outcome
        halt_stage = "pre_consume"
    elif post_write and post_write[0].flow == InvariantFlow.STOP:
        halt_outcome = post_write[0]
        halt_stage = "post_write"

    halt_record: Optional[HaltRecord] = None
    if halt_outcome is not None and halt_stage is not None:
        halt_record = _halt_record_from_outcome(stage=halt_stage, outcome=halt_outcome)
        gate_checks.append(
            GateInvariantCheck(
                gate_point="halt_validation",
                output=normalize_outcome(
                    REGISTRY[InvariantId.EXPLAINABLE_HALT_COMPLETENESS](
                        default_check_context(
                            scope=scope,
                            prediction_key=prediction_key,
                            current_predictions=current_predictions,
                            prediction_log_available=prediction_log_available,
                            just_written_prediction=just_written_prediction,
                            halt_candidate=halt_outcome,
                        )
                    )
                ),
            )
        )

    result_kind: str
    if halt_record is None:
        result = GateSuccessOutcome(artifact=PredictionOutcome(pre_consume=pre_consume, post_write=post_write))
        result_kind = "prediction"
    else:
        result = GateHaltOutcome(artifact=halt_record)
        result_kind = "halt"

    halt_evidence_ref: Optional[Dict[str, str]] = None
    stable_ids = _episode_stable_ids(ep) if ep is not None else {}
    if isinstance(result, GateHaltOutcome):
        halt_evidence_ref = append_halt_record(
            result.artifact,
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
                "prediction": _to_dict(result.artifact) if isinstance(result, GateSuccessOutcome) else None,
                "halt": _to_dict(result.artifact) if isinstance(result, GateHaltOutcome) else None,
                "halt_evidence_ref": halt_evidence_ref,
            },
        )

        if isinstance(result, GateHaltOutcome):
            halt = result.artifact
            halt_observation = Observation(
                observation_id=_new_id("obs:"),
                t_observed_iso=_now_iso(),
                type=ObservationType.HALT,
                text=halt.reason,
                source=f"invariant:{halt.violated_invariant_id}",
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
                    "violated_invariant_id": halt.violated_invariant_id,
                    "reason": halt.reason,
                    "retryable": halt.retryable,
                    "evidence_refs": [_to_dict(e) for e in halt.evidence_refs],
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
    payload: Any = halt.model_dump(mode="json")
    if stable_ids:
        payload = {**dict(stable_ids), **halt.model_dump(mode="json")}
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

        err = observed_value - pred.expectation
        compared += 1
        error_total += abs(err)
        compared_at = _now_iso()
        updated_pred = pred.model_copy(
            update={
                "observed_value": observed_value,
                "prediction_error": err,
                "absolute_error": abs(err),
                "observed_at_iso": compared_at,
                "compared_at_iso": compared_at,
                "was_corrected": True,
                "corrected_at_iso": compared_at,
            }
        )
        current_predictions[scope_key] = updated_pred
        append_prediction_record(updated_pred, prediction_log_path=prediction_log_path, stable_ids=_episode_stable_ids(ep), episode=ep)

        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "prediction_comparison",
                "prediction_id": updated_pred.prediction_id,
                "scope_key": scope_key,
                "expected": pred.expectation,
                "observed": observed_value,
                "error": err,
                "absolute_error": abs(err),
                "compared_at_iso": compared_at,
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

        gate = evaluate_invariant_gates(
            ep=ep,
            scope=pred.scope_key,
            prediction_key=pred.scope_key,
            projection_state=updated_projection,
            prediction_log_available=True,
            just_written_prediction={"key": pred.scope_key, "evidence_refs": [evidence_ref]},
        )
        if isinstance(gate, GateHaltOutcome):
            return ep, belief, updated_projection


    active_scope = next(iter(updated_projection.current_predictions), "decision_stage")
    pre_decision_gate = evaluate_invariant_gates(
        ep=ep,
        scope=active_scope,
        prediction_key=None,
        projection_state=updated_projection,
        prediction_log_available=True,
    )
    if isinstance(pre_decision_gate, GateHaltOutcome):
        return ep, belief, updated_projection

    ep = ingest_observation(ep)
    updated_projection = _reconcile_predictions(ep, updated_projection, prediction_log_path=prediction_log_path)
    ep, belief = apply_utterance_interpretation(ep, belief)
    ep, belief = apply_schema_bubbling(ep, belief)
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
            "observer": _to_dict(ep.observer),
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
            "observer": _to_dict(ep.observer),
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
