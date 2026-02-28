# state_renormalization/contracts.py
from __future__ import annotations

# Temporary integration merge-freeze marker:
# during stabilization of integration/pr-conflict-resolution, merge changes to this
# module only via the ordered integration stack documented in docs/integration_notes.md.

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, Iterable, List, Literal, Mapping, Optional, Protocol, cast

from typing_extensions import Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class HaltPayloadValidationError(ValueError):
    """Raised when a halt payload cannot be normalized into canonical halt fields."""


class EvidenceRefLike(Protocol):
    kind: str
    ref: str

# ------------------------------------------------------------------------------
# Shared BaseModel config helpers
# ------------------------------------------------------------------------------

_CONTRACT_CONFIG = ConfigDict(
    extra="forbid",
    validate_assignment=True,
    use_enum_values=False,  # keep enums as enums in Python
)

_IMMUTABLE_CONTRACT_CONFIG = ConfigDict(
    extra="forbid",
    use_enum_values=False,
    frozen=True,
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


class ObservationFreshnessPolicyContract(BaseModel):
    model_config = _CONTRACT_CONFIG

    scope: str
    observed_at_iso: Optional[str] = Field(default=None, validation_alias=AliasChoices("observed_at_iso", "observed_at"))
    stale_after_seconds: float = Field(ge=0)

    @property
    def observed_at(self) -> Optional[str]:
        return self.observed_at_iso


class ObservationFreshnessDecisionOutcome(str, Enum):
    CONTINUE = "continue"
    ASK_REQUEST = "ask_request"
    HOLD = "hold"


class ObservationFreshnessDecision(BaseModel):
    model_config = _CONTRACT_CONFIG

    scope: str
    outcome: ObservationFreshnessDecisionOutcome
    reason: str
    stale_after_seconds: float = Field(ge=0)
    observed_at_iso: Optional[str] = Field(default=None, validation_alias=AliasChoices("observed_at_iso", "observed_at"))
    last_observed_at_iso: Optional[str] = None
    last_observed_value: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)

    @property
    def observed_at(self) -> Optional[str]:
        return self.observed_at_iso


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


class InvariantAuditResult(BaseModel):
    """Normalized gate-check outcome suitable for deterministic audit trails."""

    model_config = _CONTRACT_CONFIG

    gate_point: str
    invariant_id: str
    passed: bool
    reason: str = ""
    flow: str = "continue"
    validity: str = "valid"
    code: str = ""
    evidence: List[EvidenceRef] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    action_hints: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("evidence", mode="before")
    @classmethod
    def _normalize_evidence(cls, value: object) -> List[EvidenceRef]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("evidence must be a list")
        return EvidenceRef.parse_many(value)


class GateInvariantOutcomeBundle(BaseModel):
    """Per-gate normalized invariant outcomes split by execution phase."""

    model_config = _CONTRACT_CONFIG

    pre_consume: List[Dict[str, Any]] = Field(default_factory=list)
    post_write: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def combined(self) -> List[Dict[str, Any]]:
        return [*self.pre_consume, *self.post_write]


class InterventionAction(str, Enum):
    NONE = "none"
    PAUSE = "pause"
    RESUME = "resume"
    TIMEOUT = "timeout"
    ESCALATE = "escalate"


class InterventionOverrideSource(str, Enum):
    OPERATOR = "operator"
    POLICY = "policy"
    SYSTEM = "system"


class InterventionRequest(BaseModel):
    """Engine-emitted lifecycle request for HITL processing."""

    model_config = _CONTRACT_CONFIG

    request_id: str
    phase: str
    episode_id: str
    conversation_id: str
    turn_index: int
    projection_updated_at_iso: str
    created_at_iso: str
    timeout_s: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AskOutboxRequestArtifact(BaseModel):
    """Canonical append-only human-recruitment request artifact."""

    model_config = _CONTRACT_CONFIG

    event_kind: Literal["ask_outbox_request"] = "ask_outbox_request"
    request_id: str
    scope: str
    reason: str
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    created_at_iso: str
    timeout_at_iso: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _normalize_evidence_refs(cls, value: object) -> List[EvidenceRef]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("evidence_refs must be a list")
        return EvidenceRef.parse_many(value)


class AskOutboxResponseArtifact(BaseModel):
    """Canonical append-only human-recruitment response artifact."""

    model_config = _CONTRACT_CONFIG

    event_kind: Literal["ask_outbox_response"] = "ask_outbox_response"
    request_id: str
    scope: str
    reason: str
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    created_at_iso: str
    responded_at_iso: str
    status: str
    escalation: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _normalize_evidence_refs(cls, value: object) -> List[EvidenceRef]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("evidence_refs must be a list")
        return EvidenceRef.parse_many(value)


class InterventionDecision(BaseModel):
    """HITL intervention signal emitted at lifecycle hooks in mission loop."""

    model_config = _CONTRACT_CONFIG

    action: InterventionAction = InterventionAction.NONE
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    responded_at_iso: Optional[str] = None
    override_provenance: Optional[str] = None
    override_source: Optional[InterventionOverrideSource] = None

    @model_validator(mode="after")
    def _validate_override_provenance(self) -> Self:
        if self.action != InterventionAction.RESUME:
            return self

        if self.override_source is None or not self.override_provenance:
            raise ValueError(
                "resume intervention requires explicit override_source and override_provenance"
            )
        return self


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
    kind: str = Field(min_length=1)
    ref: str = Field(min_length=1)

    @classmethod
    def from_raw(cls, payload: object) -> "EvidenceRef":
        """Normalize a raw evidence payload into a canonical typed reference."""
        if isinstance(payload, cls):
            return payload

        if isinstance(payload, Mapping):
            raw_kind = payload.get("kind")
            raw_ref = payload.get("ref", payload.get("value"))
            return cast(
                "EvidenceRef",
                cls.model_validate({"kind": str(raw_kind or "unknown"), "ref": "" if raw_ref is None else str(raw_ref)}),
            )

        maybe_kind = getattr(payload, "kind", None)
        maybe_ref = getattr(payload, "ref", None)
        if isinstance(maybe_kind, str) and isinstance(maybe_ref, str):
            return cast("EvidenceRef", cls.model_validate({"kind": maybe_kind, "ref": maybe_ref}))

        raise TypeError("evidence payload must be a mapping or an object with string kind/ref")

    @classmethod
    def parse_many(cls, payloads: Iterable[object]) -> List["EvidenceRef"]:
        return [cls.from_raw(payload) for payload in payloads]


class HaltRecord(BaseModel):
    model_config = _CONTRACT_CONFIG

    REQUIRED_EXPLAINABILITY_FIELDS: ClassVar[tuple[str, ...]] = (
        "invariant_id",
        "details",
        "evidence",
    )

    REQUIRED_PAYLOAD_FIELDS: ClassVar[tuple[str, ...]] = (
        "halt_id",
        "stage",
        "invariant_id",
        "reason",
        "details",
        "evidence",
        "retryability",
        "timestamp",
    )

    halt_id: str = Field(min_length=1, validation_alias=AliasChoices("halt_id", "stable_halt_id"))
    stage: str = Field(min_length=1)
    invariant_id: str = Field(min_length=1, validation_alias=AliasChoices("invariant_id", "violated_invariant_id"))
    reason: str = Field(min_length=1)
    details: Dict[str, Any]
    evidence: List[EvidenceRef] = Field(validation_alias=AliasChoices("evidence", "evidence_refs"))
    retryability: bool = Field(validation_alias=AliasChoices("retryability", "retryable"))
    timestamp: str = Field(min_length=1, validation_alias=AliasChoices("timestamp", "timestamp_iso"))

    @field_validator("evidence", mode="before")
    @classmethod
    def _normalize_evidence(cls, value: object) -> List[EvidenceRef]:
        if not isinstance(value, list):
            raise TypeError("evidence must be a list")
        return EvidenceRef.parse_many(value)

    @staticmethod
    def _enforce_alias_consistency(data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        alias_pairs = (
            ("halt_id", "stable_halt_id"),
            ("invariant_id", "violated_invariant_id"),
            ("evidence", "evidence_refs"),
            ("retryability", "retryable"),
            ("timestamp", "timestamp_iso"),
        )
        for canonical, alias in alias_pairs:
            if canonical in data and alias in data and data[canonical] != data[alias]:
                raise ValueError(f"halt payload field mismatch: {canonical} != {alias}")
        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_alias_consistency(cls, data: Any) -> Any:
        return cls._enforce_alias_consistency(data)

    @classmethod
    def required_payload_fields(cls) -> tuple[str, ...]:
        return cls.REQUIRED_PAYLOAD_FIELDS

    @classmethod
    def required_explainability_fields(cls) -> tuple[str, ...]:
        return cls.REQUIRED_EXPLAINABILITY_FIELDS

    @classmethod
    def canonical_payload_schema(cls) -> Dict[str, str]:
        """Field map for the canonical halt payload used by STOP emitters."""
        return {
            "halt_id": "str",
            "stage": "str",
            "invariant_id": "str",
            "reason": "str",
            "details": "dict",
            "evidence": "list",
            "retryability": "bool",
            "timestamp": "str",
        }

    @classmethod
    def build_canonical_payload(
        cls,
        *,
        halt_id: str,
        stage: str,
        invariant_id: str,
        reason: str,
        details: Mapping[str, Any],
        evidence: list[EvidenceRef | EvidenceRefLike],
        retryability: bool,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Build and validate a canonical STOP payload shape used by all emitters."""
        validated = cast("HaltRecord", cls.model_validate(
            {
                "halt_id": halt_id,
                "stage": stage,
                "invariant_id": invariant_id,
                "reason": reason,
                "details": dict(details),
                "evidence": [EvidenceRef.from_raw(item) for item in evidence],
                "retryability": retryability,
                "timestamp": timestamp,
            }
        ))
        return validated.to_canonical_payload()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "HaltRecord":
        raw = dict(payload)
        try:
            cls._enforce_alias_consistency(raw)
        except ValueError as exc:
            raise HaltPayloadValidationError(str(exc)) from exc
        canonical_candidate = {
            "halt_id": raw.get("halt_id", raw.get("stable_halt_id")),
            "stage": raw.get("stage"),
            "invariant_id": raw.get("invariant_id", raw.get("violated_invariant_id")),
            "reason": raw.get("reason"),
            "details": raw.get("details"),
            "evidence": raw.get("evidence", raw.get("evidence_refs")),
            "retryability": raw.get("retryability", raw.get("retryable")),
            "timestamp": raw.get("timestamp", raw.get("timestamp_iso")),
        }
        try:
            return cast("HaltRecord", cls.model_validate(canonical_candidate))
        except Exception as exc:
            raise HaltPayloadValidationError("halt payload is malformed or incomplete") from exc

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

    def to_canonical_payload(self) -> Dict[str, Any]:
        """Canonical halt payload used by all STOP branches and persistence paths."""
        payload = self.model_dump(mode="json")
        return {field: payload[field] for field in self.required_payload_fields()}


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
    correction_parent_prediction_id: Optional[str] = None
    correction_root_prediction_id: Optional[str] = None
    correction_revision: int = 0

    issued_at_iso: str
    observed_at_iso: Optional[str] = None
    compared_at_iso: Optional[str] = None
    corrected_at_iso: Optional[str] = None
    valid_from_iso: Optional[str] = None
    valid_until_iso: Optional[str] = None
    stopping_time_iso: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list, validation_alias=AliasChoices("assumptions", "invariants_assumed"))
    evidence_refs: List[EvidenceRef] = Field(default_factory=list, validation_alias=AliasChoices("evidence_refs", "evidence_links"))

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _normalize_evidence_refs(cls, value: object) -> List[EvidenceRef]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("evidence_refs must be a list")
        return EvidenceRef.parse_many(value)

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


class CapabilityInvocationPolicyCode(str, Enum):
    CURRENT_PREDICTION_REQUIRED = "current_prediction_required"
    EXPLICIT_GATE_PASS_REQUIRED = "explicit_gate_pass_required"
    OBSERVER_SCOPE_DENIED = "observer_scope_denied"


class CapabilityInvocationAttempt(BaseModel):
    model_config = _CONTRACT_CONFIG

    invocation_id: str
    capability: str
    action: str
    stage: str
    scope_key: str
    prediction_key: Optional[str] = None
    required_capability: str
    explicit_gate_pass_present: bool
    current_prediction_available: bool
    observer_role: Optional[str] = None
    observer_authorization_level: Optional[str] = None
    observer_capabilities: List[str] = Field(default_factory=list)


class CapabilityPolicyHaltPayload(BaseModel):
    model_config = _CONTRACT_CONFIG

    halt_id: str
    stage: str
    invariant_id: str
    reason: str
    details: Dict[str, Any]
    evidence: List[EvidenceRef]

    @field_validator("evidence", mode="before")
    @classmethod
    def _normalize_evidence(cls, value: object) -> List[EvidenceRef]:
        if not isinstance(value, list):
            raise TypeError("evidence must be a list")
        return EvidenceRef.parse_many(value)
    retryability: bool
    timestamp: str


class CapabilityInvocationPolicyDecision(BaseModel):
    model_config = _CONTRACT_CONFIG

    attempt: CapabilityInvocationAttempt
    allowed: bool
    denial_code: Optional[CapabilityInvocationPolicyCode] = None
    denial_reason: Optional[str] = None
    halt_payload: Optional[CapabilityPolicyHaltPayload] = None


class CapabilityAdapterGate(BaseModel):
    model_config = _CONTRACT_CONFIG

    invocation_id: str
    allowed: bool = True


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


class ProjectionReplayResult(BaseModel):
    model_config = _CONTRACT_CONFIG

    projection_state: ProjectionState
    analytics_snapshot: ProjectionAnalyticsSnapshot = Field(default_factory=lambda: ProjectionAnalyticsSnapshot())
    records_processed: int = 0


class RepairResolution(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RepairLineageRef(BaseModel):
    model_config = _IMMUTABLE_CONTRACT_CONFIG

    conversation_id: Optional[str] = None
    episode_id: Optional[str] = None
    turn_index: Optional[int] = None
    scope_key: str
    prediction_id: str
    correction_root_prediction_id: str


class RepairProposalEvent(BaseModel):
    """Immutable append-only proposal describing a candidate prediction repair."""

    model_config = _IMMUTABLE_CONTRACT_CONFIG

    event_kind: Literal["repair_proposal"] = "repair_proposal"
    repair_id: str
    proposed_at_iso: str
    reason: str
    invariant_id: str
    lineage_ref: RepairLineageRef
    proposed_prediction: PredictionRecord
    prediction_outcome: PredictionOutcome


class RepairResolutionEvent(BaseModel):
    """Immutable append-only decision record for a previously proposed repair."""

    model_config = _IMMUTABLE_CONTRACT_CONFIG

    event_kind: Literal["repair_resolution"] = "repair_resolution"
    repair_id: str
    proposal_event_kind: Literal["repair_proposal"] = "repair_proposal"
    decision: RepairResolution
    resolved_at_iso: str
    lineage_ref: RepairLineageRef
    accepted_prediction: Optional[PredictionRecord] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def _validate_decision_payload(self) -> Self:
        if self.decision == RepairResolution.ACCEPTED and self.accepted_prediction is None:
            raise ValueError("accepted repair resolution requires accepted_prediction")
        if self.decision == RepairResolution.REJECTED and not self.rejection_reason:
            raise ValueError("rejected repair resolution requires rejection_reason")
        return self


class CorrectionCostAttribution(BaseModel):
    """Minimal lineage-derived correction analytics per root prediction."""

    model_config = _CONTRACT_CONFIG

    root_prediction_id: str
    correction_count: int = 0
    correction_cost_total: float = 0.0


class ProjectionAnalyticsSnapshot(BaseModel):
    """Deterministic analytics derivable from persisted prediction/halt lineage only."""

    model_config = _CONTRACT_CONFIG

    correction_count: int = 0
    halt_count: int = 0
    correction_cost_total: float = 0.0
    correction_cost_attribution: Dict[str, CorrectionCostAttribution] = Field(default_factory=dict)
    outstanding_human_requests: Dict[str, AskOutboxRequestArtifact] = Field(default_factory=dict)
    resolved_human_requests: Dict[str, AskOutboxResponseArtifact] = Field(default_factory=dict)
    request_outcome_linkage: Dict[str, str] = Field(default_factory=dict)

    @property
    def correction_cost_mean(self) -> float:
        if self.correction_count <= 0:
            return 0.0
        return self.correction_cost_total / float(self.correction_count)


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
