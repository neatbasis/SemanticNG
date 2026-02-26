# state_renormalization/engine.py
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel
from enum import Enum

from state_renormalization.contracts import (
    Ambiguity,
    AmbiguityAbout,
    AmbiguityStatus,
    AmbiguityType,
    AskFormat,
    CaptureOutcome,
    CaptureStatus,
    ClarifyingQuestion,
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    AboutKind,
    HypothesisEvaluation,
    DecisionEffect,
    Episode,
    EpisodeOutputs,
    Observation,
    ObservationType,
    OutputRenderingArtifact,
    ResolutionPolicy,
    SchemaSelection,
    SchemaHit,
    UtteranceType,
    project_ambiguity_state,
)
from state_renormalization.adapters.schema_selector import naive_schema_selector


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


def build_episode(
    *,
    conversation_id: str,
    turn_index: int,
    assistant_prompt_asked: str,
    policy_decision,
    payload: Dict[str, Any],
    outputs: EpisodeOutputs,
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
        policy_decision=policy_decision,
        ask=ask,
        observations=[],
        outputs=outputs,
        artifacts=[],
        effects=[],
    )
    ep.artifacts.append({
        "kind": "policy_hypothesis",
        "decision_id": policy_decision.decision_id,
        "hypothesis": policy_decision.hypothesis,
        "reason_codes": policy_decision.reason_codes,
    })
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
        },
        hypothesis_eval=HypothesisEvaluation(hypothesis=hyp, held=held),
    )

    curr_ep.effects.append(eff)
    return curr_ep




def _invalid_selection_fallback() -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.SCHEMA, key="engine.selection.invalid")
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.MISSING_CONTEXT,
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[ClarifyingQuestion(q="I couldn't parse that response. Could you rephrase?", format=AskFormat.FREEFORM)],
        evidence={"signals": ["malformed_selection"]},
        notes="Schema selector returned malformed selection.",
    )
    return SchemaSelection(
        schemas=[SchemaHit(name="clarify.selection_malformed", score=0.99, about=about)],
        ambiguities=[amb],
        notes="malformed_selection",
    )


def _validated_selection(raw_selection: Any) -> SchemaSelection:
    try:
        return SchemaSelection.model_validate(raw_selection)
    except Exception:
        return _invalid_selection_fallback()


def apply_schema_bubbling(ep: Episode, belief: BeliefState) -> tuple[Episode, BeliefState]:
    """
    Single-writer: updates belief state based on the latest observation.

    Option A: pending obligation is represented via:
      - belief.pending_about (dict)
      - belief.pending_question (str)
      - belief.pending_attempts (int)
    """
    user_text = extract_user_utterance(ep)
    raw_selection = naive_schema_selector(user_text, error=ep.ask.error)
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
                about_dict = _to_dict(chosen.about)
                if isinstance(about_dict, dict):
                    belief.pending_about = about_dict
                else:
                    belief.pending_about = {"value": about_dict}

                # Prefer the first ClarifyingQuestion.q if present
                q: Optional[str] = None
                ask_list = chosen.ask
                if isinstance(ask_list, list) and ask_list:
                    first = ask_list[0]
                    q_val = first.q
                    if isinstance(q_val, str) and q_val.strip():
                        q = q_val.strip()

                # Fallback: synthesize
                if not q:
                    span = None
                    if isinstance(belief.pending_about, dict):
                        span = belief.pending_about.get("span") or belief.pending_about.get("text")
                        # support schema_selector.py which uses TextSpan {text: ...}
                        if isinstance(span, dict):
                            span = span.get("text")
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

    ep.artifacts.append(
        {
            "kind": "schema_selection",
            "schemas": [{"name": h.name, "score": h.score, "about": _to_dict(h.about)} for h in sel.schemas],
            "ambiguities": [_to_dict(a) for a in belief.ambiguities_active],
            "ambiguity_state": belief.ambiguity_state.value,
            "notes": sel.notes,
            "pending_about": _to_dict(belief.pending_about),
            "pending_question": belief.pending_question,
            "pending_attempts": belief.pending_attempts,
        }
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

    ep.artifacts.append(
        {
            "kind": "utterance_interpretation",
            "utterance_type": utype.value,
            "text_preview": (user_text[:80] if isinstance(user_text, str) else None),
            "consecutive_no_response": belief.consecutive_no_response,
        }
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
