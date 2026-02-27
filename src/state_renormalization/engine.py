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
from state_renormalization.adapters.persistence import append_halt, append_prediction
from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.invariants import (
    Flow as InvariantFlow,
    InvariantId,
    InvariantOutcome,
    REGISTRY,
    default_check_context,
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
class Prediction:
    pre_consume: Sequence[InvariantOutcome] = field(default_factory=tuple)
    post_write: Sequence[InvariantOutcome] = field(default_factory=tuple)


    @property
    def combined(self) -> Sequence[InvariantOutcome]:
        return tuple(self.pre_consume) + tuple(self.post_write)


GateDecision = Prediction | HaltRecord


def _as_evidence_ref(item: Mapping[str, Any]) -> EvidenceRef:
    kind = str(item.get("kind") or "unknown")
    ref = item.get("ref")
    if ref is None and "value" in item:
        ref = item["value"]
    return EvidenceRef(kind=kind, ref=str(ref) if ref is not None else "")


def _halt_record_from_outcome(*, stage: str, outcome: InvariantOutcome) -> HaltRecord:
    reason = str(outcome.details.get("message") or outcome.code)
    return HaltRecord(
        halt_id=_new_id("halt:"),
        stage=stage,
        invariant_id=outcome.invariant_id.value,
        reason=reason,
        evidence_refs=[_as_evidence_ref(_to_dict(item)) for item in outcome.evidence],
        timestamp=_now_iso(),
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
    explicit = {
        "feature_id": payload.get("feature_id"),
        "scenario_id": payload.get("scenario_id"),
        "step_id": payload.get("step_id"),
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

    scenario_name = payload.get("scenario_name")
    step_text = payload.get("step_text")

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
    explainable_halt = REGISTRY[InvariantId.H0_EXPLAINABLE_HALT](h0_ctx)
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
    current_predictions = {
        key: pred.prediction_id
        for key, pred in projection_state.current_predictions.items()
    }

    pre_ctx = default_check_context(
        scope=scope,
        prediction_key=prediction_key,
        current_predictions=current_predictions,
        prediction_log_available=prediction_log_available,
    )
    pre_outcome = _run_invariant(InvariantId.P0_NO_CURRENT_PREDICTION, ctx=pre_ctx)
    pre_consume = (pre_outcome,)

    post_write: Sequence[InvariantOutcome] = tuple()
    if just_written_prediction is not None:
        post_ctx = default_check_context(
            scope=scope,
            prediction_key=prediction_key,
            current_predictions=current_predictions,
            prediction_log_available=prediction_log_available,
            just_written_prediction=just_written_prediction,
        )
        post_write = (_run_invariant(InvariantId.P1_WRITE_BEFORE_USE, ctx=post_ctx),)

    halt_outcome: Optional[InvariantOutcome] = None
    halt_stage: Optional[str] = None
    if pre_outcome.flow == InvariantFlow.STOP:
        halt_outcome = pre_outcome
        halt_stage = "pre_consume"
    elif post_write and post_write[0].flow == InvariantFlow.STOP:
        halt_outcome = post_write[0]
        halt_stage = "post_write"

    halt_record: Optional[HaltRecord] = None
    if halt_outcome is not None and halt_stage is not None:
        halt_record = _halt_record_from_outcome(stage=halt_stage, outcome=halt_outcome)

    result: GateDecision
    result_kind: str
    if halt_record is None:
        result = Prediction(pre_consume=pre_consume, post_write=post_write)
        result_kind = "prediction"
    else:
        result = halt_record
        result_kind = "halt"

    halt_evidence_ref: Optional[Dict[str, str]] = None
    if isinstance(result, HaltRecord):
        halt_evidence_ref = append_halt(halt_log_path, result)

    if ep is not None:
        _append_episode_artifact(
            ep,
            {
                "artifact_kind": "invariant_outcomes",
                "observer": _to_dict(getattr(ep, "observer", None)),
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
                "kind": result_kind,
                "prediction": _to_dict(result) if isinstance(result, Prediction) else None,
                "halt": _to_dict(result) if isinstance(result, HaltRecord) else None,
                "halt_evidence_ref": halt_evidence_ref,
            },
        )

        if isinstance(result, HaltRecord):
            _append_episode_artifact(
                ep,
                {
                    "artifact_kind": "halt_observation",
                    "observation_type": "halt",
                    "halt_id": result.halt_id,
                    "stage": result.stage,
                    "invariant_id": result.invariant_id,
                    "reason": result.reason,
                    "retryable": result.retryable,
                    "evidence_refs": [_to_dict(e) for e in result.evidence_refs],
                    "halt_evidence_ref": halt_evidence_ref,
                },
            )

    return result




def append_prediction_record(
    pred: PredictionRecord,
    *,
    prediction_log_path: str | Path = "artifacts/predictions.jsonl",
) -> dict[str, str]:
    return append_prediction(prediction_log_path, pred)


def append_halt_record(
    halt: HaltRecord,
    *,
    halt_log_path: str | Path = "halts.jsonl",
) -> dict[str, str]:
    return append_halt(halt_log_path, halt)


def project_current(pred: PredictionRecord, projection_state: ProjectionState) -> ProjectionState:
    current = dict(projection_state.current_predictions)
    current[pred.scope_key] = pred
    return ProjectionState(current_predictions=current, updated_at_iso=_now_iso())

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
