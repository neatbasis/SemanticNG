# state_renormalization/contracts.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# ------------------------------------------------------------------------------
# Shared BaseModel config helpers
# ------------------------------------------------------------------------------

_CONTRACT_CONFIG = ConfigDict(
    extra="forbid",
    validate_assignment=True,
    use_enum_values=False,  # keep enums as enums in Python
)

# ------------------------------------------------------------------------------
# Ask / satellite
# ------------------------------------------------------------------------------

class AskStatus(str, Enum):
    OK = "ok"
    NO_RESPONSE = "no_response"
    ERROR = "error"


class CaptureStatus(str, Enum):
    NO_RESPONSE = "no_response"
    ERROR = "error"


class CaptureOutcome(BaseModel):
    model_config = _CONTRACT_CONFIG
    status: CaptureStatus
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AskMetrics(BaseModel):
    model_config = _CONTRACT_CONFIG
    elapsed_s: float = 0.0
    question_chars: int = 0
    question_words: int = 0


class AskResult(BaseModel):
    model_config = _CONTRACT_CONFIG
    status: AskStatus
    sentence: Optional[str] = None
    slots: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[CaptureOutcome] = None
    metrics: AskMetrics = Field(default_factory=AskMetrics)

# ------------------------------------------------------------------------------
# Ambiguity core
# ------------------------------------------------------------------------------

class AmbiguityStatus(str, Enum):
    NONE = "none"
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


class ResolutionPolicy(str, Enum):
    ASK_USER = "ask_user"
    USE_DEFAULT = "use_default"
    DEFER = "defer"
    LOOKUP = "lookup"


class AmbiguityType(str, Enum):
    UNDERSPECIFIED = "underspecified"
    POLYSEMY = "polysemy"
    CONFLICT = "conflict"
    MISSING_CONTEXT = "missing_context"
    UNCERTAIN_MAPPING = "uncertain_mapping"


class AboutKind(str, Enum):
    INTENT = "intent"
    ENTITY = "entity"
    TIME = "time"
    PLACE = "place"
    PARAMETER = "parameter"
    SCHEMA = "schema"
    GOAL = "goal"
    CHANNEL = "channel"


class TextSpan(BaseModel):
    """Optional span info for anchoring the referent in text."""
    model_config = _CONTRACT_CONFIG
    text: str
    start: Optional[int] = None
    end: Optional[int] = None


class AmbiguityAbout(BaseModel):
    """
    'Ambiguity is always about something' -> stable referent.
    """
    model_config = _CONTRACT_CONFIG
    kind: AboutKind
    key: str
    span: Optional[TextSpan] = None


class Candidate(BaseModel):
    model_config = _CONTRACT_CONFIG
    value: str
    score: float


class AskFormat(str, Enum):
    """
    Minimal and descriptive set.
    We'll use FREEFORM as the default instead of SHORT_TEXT.
    """
    FREEFORM = "freeform"
    BINARY = "binary"
    MULTICHOICE = "multichoice"


class BindSpec(BaseModel):
    """
    Where the clarification should land in belief.bindings / pending_about.
    Keep minimal to avoid schema drift while you iterate.
    """
    model_config = _CONTRACT_CONFIG
    key: str
    kind: Optional[AboutKind] = None
    expected_type: Optional[str] = None
    hints: Dict[str, Any] = Field(default_factory=dict)


class ClarifyingQuestion(BaseModel):
    model_config = _CONTRACT_CONFIG
    q: str
    format: AskFormat = AskFormat.FREEFORM
    options: Optional[List[str]] = None
    bind: Optional[BindSpec] = None
    artifact: Dict[str, Any] = Field(default_factory=dict)


class Ambiguity(BaseModel):
    model_config = _CONTRACT_CONFIG
    status: AmbiguityStatus
    about: AmbiguityAbout
    type: AmbiguityType
    candidates: List[Candidate] = Field(default_factory=list)
    resolution_policy: ResolutionPolicy = ResolutionPolicy.ASK_USER
    ask: List[ClarifyingQuestion] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

# ------------------------------------------------------------------------------
# Schema selection outputs (normalized)
# ------------------------------------------------------------------------------

class SchemaHit(BaseModel):
    model_config = _CONTRACT_CONFIG

    name: str
    score: float
    about: Optional[AmbiguityAbout] = None
    # TODO: add these when it's time
    #schema_id: Optional[str] = None
    #source: Optional[str] = None

class SchemaSelection(BaseModel):
    """
    Output of schema selector: ranked schema hits + extracted ambiguities (if any).
    """
    model_config = _CONTRACT_CONFIG

    schemas: List[SchemaHit] = Field(default_factory=list)
    ambiguities: List[Ambiguity] = Field(default_factory=list)
    notes: Optional[str] = None

def project_ambiguity_state(ambiguities: List[Ambiguity]) -> AmbiguityStatus:
    if not ambiguities:
        return AmbiguityStatus.NONE
    if any(a.status == AmbiguityStatus.UNRESOLVED for a in ambiguities):
        return AmbiguityStatus.UNRESOLVED
    return AmbiguityStatus.RESOLVED

# ------------------------------------------------------------------------------
# Policy / output / episode logging
# ------------------------------------------------------------------------------

class VerbosityLevel(str, Enum):
    V1_BINARY = "v1_binary"
    V2_MVQ = "v2_mvq"
    V3_CONCISE = "v3_concise"
    V4_OPEN = "v4_open"


class Channel(str, Enum):
    CLI = "cli"
    DISCORD = "discord"
    HOMEASSISTANT = "homeassistant"
    SATELLITE = "satellite"
    OTHER = "other"


class HypothesisEvaluation(BaseModel):
    model_config = _CONTRACT_CONFIG
    hypothesis: Optional[str]
    held: bool


class VerbosityDecision(BaseModel):
    model_config = _CONTRACT_CONFIG
    decision_id: str
    t_decided_iso: str
    action_type: str
    verbosity_level: VerbosityLevel
    channel: Channel
    reason_codes: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    hypothesis: Optional[str] = None
    policy_version: str = "0"
    source: str = "policy"


class ObservationType(str, Enum):
    USER_UTTERANCE = "user_utterance"
    SILENCE = "silence"
    HALT = "halt"

class UtteranceType(str, Enum):
    NONE = "none"
    LOW_SIGNAL = "low_signal"
    NORMAL = "normal"
    EXIT_INTENT = "exit_intent"


class Observation(BaseModel):
    model_config = _CONTRACT_CONFIG
    observation_id: str
    t_observed_iso: str
    type: ObservationType
    text: Optional[str] = None
    source: str = "unknown"


class OutputRenderingArtifact(BaseModel):
    model_config = _CONTRACT_CONFIG
    kind: str
    channel: Channel
    verbosity_level: VerbosityLevel
    method: str
    dropped_elements: List[str] = Field(default_factory=list)


class EpisodeOutputs(BaseModel):
    model_config = _CONTRACT_CONFIG
    assistant_text_full: str
    assistant_text_channel: str
    rendering: OutputRenderingArtifact


class DecisionEffect(BaseModel):
    model_config = _CONTRACT_CONFIG
    evaluates_decision_id: str
    decision_episode_id: str
    evaluated_in_episode_id: str
    response_captured: bool
    status: AskStatus
    had_user_utterance: bool
    user_utterance_chars: int
    elapsed_s: float
    notes: Dict[str, Any] = Field(default_factory=dict)
    hypothesis_eval: Optional[HypothesisEvaluation] = None


class ObserverFrame(BaseModel):
    model_config = _CONTRACT_CONFIG
    role: str
    capabilities: List[str] = Field(default_factory=list)
    authorization_level: str
    evaluation_invariants: List[str] = Field(default_factory=list)


def default_observer_frame() -> ObserverFrame:
    return ObserverFrame(
        role="assistant",
        capabilities=[
            "baseline.dialog",
            "baseline.schema_selection",
            "baseline.invariant_evaluation",
            "baseline.evaluation",
        ],
        authorization_level="baseline",
        evaluation_invariants=[],
    )


class Episode(BaseModel):
    model_config = _CONTRACT_CONFIG
    episode_id: str
    conversation_id: str
    turn_index: int
    t_asked_iso: str
    assistant_prompt_asked: str
    observer: Optional[ObserverFrame] = None
    policy_decision: VerbosityDecision
    ask: AskResult
    observations: List[Observation] = Field(default_factory=list)
    outputs: Optional[EpisodeOutputs] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    effects: List[DecisionEffect] = Field(default_factory=list)


class EvidenceRef(BaseModel):
    model_config = _CONTRACT_CONFIG
    kind: str
    ref: str


class HaltRecord(BaseModel):
    model_config = _CONTRACT_CONFIG

    halt_id: str = Field(validation_alias=AliasChoices("halt_id", "stable_halt_id"))
    stage: str
    invariant_id: str = Field(validation_alias=AliasChoices("invariant_id", "violated_invariant_id"))
    reason: str
    evidence: List[EvidenceRef] = Field(default_factory=list, validation_alias=AliasChoices("evidence", "evidence_refs"))
    retryability: bool = Field(validation_alias=AliasChoices("retryability", "retryable"))
    timestamp: str = Field(validation_alias=AliasChoices("timestamp", "timestamp_iso"))

    @property
    def stable_halt_id(self) -> str:
        return self.halt_id

    @property
    def violated_invariant_id(self) -> str:
        return self.invariant_id

    @property
    def evidence_refs(self) -> List[EvidenceRef]:
        return self.evidence

    @property
    def retryable(self) -> bool:
        return self.retryability

    @property
    def timestamp_iso(self) -> str:
        return self.timestamp

    def to_persistence_dict(self) -> Dict[str, Any]:
        payload = self.model_dump(mode="json")
        return {
            **payload,
            "stable_halt_id": payload["halt_id"],
            "violated_invariant_id": payload["invariant_id"],
            "evidence_refs": payload["evidence"],
            "retryable": payload["retryability"],
            "timestamp_iso": payload["timestamp"],
        }


class PredictionRecord(BaseModel):
    model_config = _CONTRACT_CONFIG

    prediction_id: str
    scope_key: str
    prediction_key: Optional[str] = None
    prediction_target: Optional[str] = Field(default=None, validation_alias=AliasChoices("prediction_target", "target"))
    filtration_id: str = Field(validation_alias=AliasChoices("filtration_id", "filtration_ref", "filtration_reference"))
    target_variable: str = Field(validation_alias=AliasChoices("target_variable", "variable"))
    target_horizon_iso: str = Field(validation_alias=AliasChoices("target_horizon_iso", "horizon_iso", "horizon"))
    target_horizon_turns: Optional[int] = Field(default=None, validation_alias=AliasChoices("target_horizon_turns", "horizon_turns"))

    # Backward-compatible optional distribution metadata.
    distribution_kind: Optional[str] = None
    distribution_params: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    uncertainty: Optional[float] = None

    expectation: Optional[float] = Field(default=None, validation_alias=AliasChoices("expectation", "conditional_expectation"))
    variance: Optional[float] = Field(default=None, validation_alias=AliasChoices("variance", "conditional_variance"))
    observed_value: Optional[float] = None
    prediction_error: Optional[float] = None
    absolute_error: Optional[float] = None
    was_corrected: bool = False

    issued_at_iso: str
    observed_at_iso: Optional[str] = None
    compared_at_iso: Optional[str] = None
    corrected_at_iso: Optional[str] = None
    valid_from_iso: Optional[str] = None
    valid_until_iso: Optional[str] = None
    stopping_time_iso: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list, validation_alias=AliasChoices("assumptions", "invariants_assumed"))
    evidence_refs: List[EvidenceRef] = Field(default_factory=list, validation_alias=AliasChoices("evidence_refs", "evidence_links"))

    @property
    def variable(self) -> str:
        return self.target_variable

    @property
    def horizon_iso(self) -> str:
        return self.target_horizon_iso

    @property
    def filtration_ref(self) -> str:
        return self.filtration_id

    @property
    def invariants_assumed(self) -> List[str]:
        return self.assumptions

    @property
    def evidence_links(self) -> List[EvidenceRef]:
        return self.evidence_refs

    @property
    def conditional_expectation(self) -> Optional[float]:
        return self.expectation

    @property
    def conditional_variance(self) -> Optional[float]:
        return self.variance


class ProjectionState(BaseModel):
    model_config = _CONTRACT_CONFIG

    current_predictions: Dict[str, PredictionRecord] = Field(default_factory=dict)
    prediction_history: List[PredictionRecord] = Field(default_factory=list)
    correction_metrics: Dict[str, float] = Field(default_factory=dict)
    last_comparison_at_iso: Optional[str] = None
    updated_at_iso: str

    @property
    def has_current_predictions(self) -> bool:
        return bool(self.current_predictions)


class PredictionOutcome(BaseModel):
    model_config = _CONTRACT_CONFIG

    prediction_id: str
    observed_outcome: Any
    error_metric: float
    absolute_error: float
    recorded_at_iso: str = Field(validation_alias=AliasChoices("recorded_at_iso", "recorded_at"))
    prediction_scope_key: Optional[str] = None
    target_variable: Optional[str] = None

    @property
    def recorded_at(self) -> str:
        return self.recorded_at_iso

# ------------------------------------------------------------------------------
# Demo-only statuses + BeliefState (Option A)
# ------------------------------------------------------------------------------

class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    VAGUE = "vague"
    NO_SIGNAL = "no_signal"


@dataclass
class BeliefState:
    belief_version: int = 0

    ambiguity_state: AmbiguityStatus = AmbiguityStatus.NONE
    pending_about: Optional[Dict[str, Any]] = None
    pending_question: Optional[str] = None
    pending_attempts: int = 0

    bindings: Dict[str, Any] = field(default_factory=dict)

    active_schemas: List[str] = field(default_factory=list)
    schema_confidence: Dict[str, float] = field(default_factory=dict)

    ambiguities_active: List[Any] = field(default_factory=list)
    updated_at_iso: Optional[str] = None

    last_utterance_type: Optional[UtteranceType] = None
    last_status: Optional[AskStatus] = None
    consecutive_no_response: int = 0
