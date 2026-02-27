NOTE: This file is exploratory. It is not normative and should be treated as draft material unless and until it is promoted into roadmap or architecture documentation.

Below is a **project-aligned “north-star” model set** (contracts + ports) and the **design choices** they encode. I’m keeping it tight and composable so you can drop these into `src/state_renormalization/contracts.py` (and `invariants.py`) with minimal churn.

---

## Design choices that matter in SemanticNG

### 1) One outcome algebra everywhere

Every capability returns the same envelope:

* **Flow:** continue vs stop (controlled early return)
* **Validity:** valid vs degraded vs invalid (epistemic quality)
* **Rationale:** code + invariant id + evidence + details
* **Action hints:** what the observation layer should do next
* **Issues:** durable obligations (orthogonal to flow)

This avoids “mixed status/error channels.”

### 2) Event-sourced truth + materialized view

* **PredictionLog** is append-only (JSONL fine).
* **CurrentView** is a rebuildable projection (derived from log).
  This keeps “current predictions highly available while current” testable.

### 3) Confidence + calibration are first-class

Predictions carry:

* raw distribution (model-native)
* calibrated distribution
* confidence/uncertainty scalars
* calibration meta-confidence (optional output of calibrator)

### 4) Invariants are pure checkers with uniform signature

Each invariant checker:

* takes `CheckContext` (Protocol/dataclass)
* returns `Result[None]` (or `InvariantOutcome`, same shape)

No check should need to import `engine.py`.

### 5) Stable IDs from Gherkin are part of every event

Every JSONL event includes:

* `feature_id`, `scenario_id`, `step_id`
  This makes downstream indexing and learning deterministic.

---

## Core models

### Result envelope and supporting types (`contracts.py`)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Mapping, Optional, Sequence, TypeVar


class Flow(str, Enum):
    CONTINUE = "continue"
    STOP = "stop"


class Validity(str, Enum):
    VALID = "valid"
    DEGRADED = "degraded"
    INVALID = "invalid"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Code(str, Enum):
    # invariants / gating
    NO_CURRENT_PREDICTION = "no_current_prediction"
    WRITE_BEFORE_USE_VIOLATION = "write_before_use_violation"
    STORE_UNAVAILABLE = "store_unavailable"
    INVARIANT_VIOLATION = "invariant_violation"

    # observation / staleness
    STALE_OBSERVATION = "stale_observation"
    FRESH_OBSERVATION = "fresh_observation"

    # prompting/experiments
    PROMPT_ALLOWED = "prompt_allowed"
    PROMPT_SUPPRESSED = "prompt_suppressed"
    LOW_EXPECTED_VALUE = "low_expected_value"


@dataclass(frozen=True)
class EvidenceRef:
    kind: str          # e.g. "sensor_event", "jsonl_offset", "user_reply", "ha_state"
    ref: str           # stable pointer/ID


@dataclass(frozen=True)
class ActionHint:
    kind: str          # e.g. "probe", "prompt_user", "retry", "fallback", "rebuild_view"
    params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IssueRef:
    issue_id: str
    issue_type: str
    severity: Severity
    owner: str
    acceptance_criteria: str


@dataclass(frozen=True)
class Rationale:
    code: Code
    invariant_id: Optional[str]   # e.g. "P0_NO_PREDICTION"
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)
    evidence: Sequence[EvidenceRef] = field(default_factory=tuple)


T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    flow: Flow
    validity: Validity
    value: Optional[T]
    rationale: Rationale
    action_hints: Sequence[ActionHint] = field(default_factory=tuple)
    issues: Sequence[IssueRef] = field(default_factory=tuple)

    @property
    def is_halt(self) -> bool:
        return self.flow == Flow.STOP

    @property
    def is_ok(self) -> bool:
        return self.flow == Flow.CONTINUE and self.validity == Validity.VALID
```

---

### Scope, observer frame, and stable IDs

```python
@dataclass(frozen=True)
class Scope:
    mission: str
    entity: str
    variable: str

    def key(self) -> str:
        return f"{self.mission}:{self.entity}:{self.variable}"


@dataclass(frozen=True)
class ObserverFrame:
    role: str                       # "assistant", "living_being_in_room", "auditor"
    capabilities: Sequence[str]      # ["prompt_user", "probe_sensor", ...]
    authorization_level: str         # "baseline", "elevated"
    evaluation_invariants: Sequence[str]


@dataclass(frozen=True)
class StableGherkinIds:
    feature_id: str
    scenario_id: str
    step_id: str
```

---

### Prediction + resolution + calibration-friendly distribution

This supports lights, meters, categorical states, numeric series—without locking you into expectation/variance only.

```python
@dataclass(frozen=True)
class Distribution:
    kind: str                       # "bernoulli", "categorical", "normal", ...
    params: Mapping[str, Any]       # e.g. {"p": 0.87}, {"mean": 3.2, "var": 1.1}, {"probs": {...}}

    # normalized, model-agnostic accessors (required)
    confidence: float               # in (0,1]
    uncertainty: float              # >= 0, e.g. entropy, var, CI width


@dataclass(frozen=True)
class PredictionRecord:
    prediction_id: str
    scope: Scope

    issued_at: datetime
    valid_from: datetime
    valid_until: datetime

    filtration_id: str
    evidence_refs: Sequence[EvidenceRef] = field(default_factory=tuple)
    invariants_assumed: Sequence[str] = field(default_factory=tuple)
    supersedes: Sequence[str] = field(default_factory=tuple)

    distribution_raw: Distribution = field(default_factory=lambda: Distribution("unknown", {}, 0.5, 1.0))
    distribution_calibrated: Distribution = field(default_factory=lambda: Distribution("unknown", {}, 0.5, 1.0))

    decision_intent: str = ""


@dataclass(frozen=True)
class ResolutionRecord:
    prediction_id: str
    resolved_at: datetime
    observed_value: Any
    evidence_refs: Sequence[EvidenceRef] = field(default_factory=tuple)
```

**Design choice:** `Distribution` carries `confidence` and `uncertainty` directly so you can compute policies and “85% rule” without knowing distribution internals.

---

### Current projection state (materialized view)

Keyed by scope key (not a list), to enforce “one current prediction per scope”.

```python
@dataclass(frozen=True)
class ProjectionState:
    updated_at: datetime
    current_predictions: Mapping[str, str]  # scope_key -> prediction_id
```

---

### Observation staleness (water meter scenario)

```python
@dataclass(frozen=True)
class ObservationRecord:
    scope: Scope
    observed_at: datetime
    value: Any
    evidence_refs: Sequence[EvidenceRef] = field(default_factory=tuple)


@dataclass(frozen=True)
class ObservationSchedule:
    period_seconds: int              # expected update period
    stale_after_seconds: int         # staleness threshold
```

---

### Prompting experiments + Ask request integration

Keep prompting as a *decision artifact* and Ask request as an *outbox action*.

```python
@dataclass(frozen=True)
class ExperimentAssignment:
    experiment_id: str
    variant: str
    seed: str                        # stable hashing seed for reproducibility


@dataclass(frozen=True)
class PromptDecision:
    decision_id: str
    scope: Scope
    made_at: datetime

    agent_id: str
    observer: ObserverFrame
    policy_id: str
    policy_version: str
    experiment: Optional[ExperimentAssignment]

    decision_kind: str               # "prompt_user" | "do_not_prompt" | "probe_sensor" | ...
    prompt_text: Optional[str]

    expected_value: float            # EIG*P(response)*P(resolve) - cost
    alternatives: Sequence[Mapping[str, Any]] = field(default_factory=tuple)

    evidence_refs: Sequence[EvidenceRef] = field(default_factory=tuple)
    rationale: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptOutcome:
    decision_id: str
    observed_at: datetime
    responded: bool
    response_text: Optional[str]
    resolved: bool
    resolved_value: Optional[Any]
    latency_seconds: Optional[float]
```

**Design choice:** Decisions and outcomes are linked by `decision_id`. This makes experiments analyzable without guesswork.

---

### Event envelope for JSONL streams (predictions, halts, invariants, decisions)

One envelope simplifies your downstream indexing.

```python
@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str                  # "prediction", "resolution", "invariant_check", "halt", "decision", ...
    occurred_at: datetime

    episode_id: str
    scope: Optional[Scope]
    gherkin: Optional[StableGherkinIds]
    observer: Optional[ObserverFrame]

    payload: Mapping[str, Any]       # serialized model
```

---

## Invariants layer (`invariants.py`) models and design

### InvariantId + CheckContext + Registry

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence

from state_renormalization.contracts import (
    ActionHint, Code, EvidenceRef, Flow, Rationale, Result, Scope, Validity
)

class InvariantId(str, Enum):
    P0_NO_CURRENT_PREDICTION = "P0_NO_CURRENT_PREDICTION"
    P1_WRITE_BEFORE_USE = "P1_WRITE_BEFORE_USE"
    H0_EXPLAINABLE_HALT = "H0_EXPLAINABLE_HALT"


class CurrentViewPort(Protocol):
    def get_current_prediction_id(self, scope: Scope, *, now_iso: str) -> Optional[str]: ...


class PredictionLogPort(Protocol):
    def is_available(self) -> bool: ...
    def has_prediction(self, prediction_id: str) -> bool: ...


@dataclass(frozen=True)
class CheckContext:
    scope: Scope
    now_iso: str
    current_view: CurrentViewPort
    prediction_log: PredictionLogPort
    evidence_refs: Sequence[EvidenceRef] = ()


Checker = Callable[[CheckContext], Result[None]]

REGISTRY: Mapping[InvariantId, Checker] = {}
```

**Design choice:** invariants depend on *ports*, not engine internals. This prevents circular imports and keeps checkers pure.

---

## Ports (interfaces) that make this architecture real

```python
from typing import Protocol, Optional, Sequence
from state_renormalization.contracts import PredictionRecord, ResolutionRecord, Scope

class PredictionLog(Protocol):
    def append(self, record: PredictionRecord) -> None: ...
    def append_resolution(self, record: ResolutionRecord) -> None: ...
    def get(self, prediction_id: str) -> PredictionRecord: ...
    def is_available(self) -> bool: ...

class CurrentView(Protocol):
    def get_current(self, scope: Scope, *, now: datetime) -> Optional[PredictionRecord]: ...
    def project_from_log(self, log: PredictionLog, *, now: datetime) -> None: ...

class Calibrator(Protocol):
    def calibrate(self, raw: Distribution, scope: Scope) -> Distribution: ...
    def update(self, pred: PredictionRecord, res: ResolutionRecord) -> None: ...
    def meta_confidence(self, scope: Scope) -> float: ...

class AskOutbox(Protocol):
    def create_request(self, *, title: str, question: str, context: Mapping[str, Any]) -> str: ...
```

---

## How these pieces map to your current work

* **State renormalization**: `ResolutionRecord` + `ObservationRecord` become evidence that updates filtration + calibration.
* **Schema selection**: rules can emit `Result[SchemaHit]` with `ActionHint`s and `IssueRef`s; stable IDs make it traceable.
* **BDD scenarios**: `StableGherkinIds` + `EventEnvelope` makes every decision/prediction attributable to a specific step.
* **Experiments**: `PromptDecision/Outcome` + `ExperimentAssignment` lets you run A/B or bandits safely and audibly.

---

I can now show a small `engine.py` spine that threads exactly these models through:

1. staleness check → (warn + ask request) or continue
2. ensure current prediction → (prediction or halt)
3. action selection gated on `Result.flow/validity`
   …and emits `EventEnvelope`s for each step with stable Gherkin IDs.


```python
# src/state_renormalization/engine.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from state_renormalization.contracts import (
    ActionHint,
    Calibrator,  # Protocol (if you placed ports in contracts; otherwise import from ports.py)
    Code,
    EventEnvelope,
    EvidenceRef,
    ExperimentAssignment,
    Flow,
    ObserverFrame,
    ObservationRecord,
    ObservationSchedule,
    PromptDecision,
    PromptOutcome,
    ProjectionState,
    Rationale,
    ResolutionRecord,
    Result,
    Scope,
    StableGherkinIds,
    Validity,
    Distribution,
    PredictionRecord,
    IssueRef,
)

from state_renormalization.invariants import InvariantId, REGISTRY, CheckContext


# -----------------------------------------------------------------------------
# Ports (if you keep them in a separate module, import from there instead)
# -----------------------------------------------------------------------------
class PredictionLog:
    def append(self, record: PredictionRecord) -> None: ...
    def append_resolution(self, record: ResolutionRecord) -> None: ...
    def get(self, prediction_id: str) -> PredictionRecord: ...
    def is_available(self) -> bool: ...


class CurrentView:
    def get_current(self, scope: Scope, *, now: datetime) -> Optional[PredictionRecord]: ...
    def project_from_log(self, log: PredictionLog, *, now: datetime) -> None: ...


class AskOutbox:
    def create_request(self, *, title: str, question: str, context: Mapping[str, Any]) -> str: ...


class EventSink:
    """Append-only event sink (JSONL, etc.)."""
    def emit(self, event: EventEnvelope) -> None: ...


class Predictor:
    def predict(self, scope: Scope, evidence: Sequence[EvidenceRef], *, now: datetime) -> Distribution: ...


# -----------------------------------------------------------------------------
# Minimal helpers (stable)
# -----------------------------------------------------------------------------
def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _event_id(prefix: str, *, episode_id: str, now: datetime, extra: str = "") -> str:
    # North-star: stable-enough + collision resistant for local use; replace with hash/uuidv7 later.
    base = f"{prefix}::{episode_id}::{int(now.timestamp()*1000)}"
    return f"{base}::{extra}" if extra else base


def _prediction_id(scope: Scope, now: datetime) -> str:
    # North-star placeholder; replace with content-addressed hash later.
    return f"pred::{scope.key()}::{int(now.timestamp())}"


def _decision_id(scope: Scope, now: datetime) -> str:
    return f"dec::{scope.key()}::{int(now.timestamp()*1000)}"


def _merge_results(results: Sequence[Result[None]]) -> Result[None]:
    """
    Compose invariant outcomes:
    - STOP dominates CONTINUE
    - INVALID dominates DEGRADED dominates VALID
    - merge action_hints/issues; keep first failing rationale as primary
    """
    if not results:
        return Result(
            flow=Flow.CONTINUE,
            validity=Validity.VALID,
            value=None,
            rationale=Rationale(code=Code.INVARIANT_VIOLATION, invariant_id=None, message="No invariants executed."),
        )

    flow = Flow.CONTINUE
    validity = Validity.VALID
    action_hints: list[ActionHint] = []
    issues: list[IssueRef] = []
    primary: Optional[Result[None]] = None

    def worse_validity(a: Validity, b: Validity) -> Validity:
        order = {Validity.VALID: 0, Validity.DEGRADED: 1, Validity.INVALID: 2}
        return a if order[a] >= order[b] else b

    for r in results:
        action_hints.extend(list(r.action_hints))
        issues.extend(list(r.issues))
        validity = worse_validity(validity, r.validity)
        if r.flow == Flow.STOP:
            flow = Flow.STOP
        if primary is None and (r.flow == Flow.STOP or r.validity != Validity.VALID):
            primary = r

    if primary is None:
        primary = results[0]

    return Result(
        flow=flow,
        validity=validity,
        value=None,
        rationale=primary.rationale,
        action_hints=tuple(action_hints),
        issues=tuple(issues),
    )


def _ok(message: str, *, code: Code, details: Mapping[str, Any] | None = None) -> Result[Any]:
    return Result(
        flow=Flow.CONTINUE,
        validity=Validity.VALID,
        value=None,
        rationale=Rationale(code=code, invariant_id=None, message=message, details=details or {}),
    )


def _warn(message: str, *, code: Code, details: Mapping[str, Any] | None = None,
          evidence: Sequence[EvidenceRef] = (), hints: Sequence[ActionHint] = ()) -> Result[Any]:
    return Result(
        flow=Flow.CONTINUE,
        validity=Validity.DEGRADED,
        value=None,
        rationale=Rationale(code=code, invariant_id=None, message=message, details=details or {}, evidence=tuple(evidence)),
        action_hints=tuple(hints),
    )


def _halt(message: str, *, code: Code, invariant_id: str, details: Mapping[str, Any] | None = None,
          evidence: Sequence[EvidenceRef] = (), hints: Sequence[ActionHint] = (),
          issues: Sequence[IssueRef] = ()) -> Result[Any]:
    return Result(
        flow=Flow.STOP,
        validity=Validity.INVALID,
        value=None,
        rationale=Rationale(code=code, invariant_id=invariant_id, message=message,
                            details=details or {}, evidence=tuple(evidence)),
        action_hints=tuple(hints),
        issues=tuple(issues),
    )


# -----------------------------------------------------------------------------
# Engine Context
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class EpisodeContext:
    episode_id: str
    observer: ObserverFrame
    gherkin: Optional[StableGherkinIds] = None
    experiment: Optional[ExperimentAssignment] = None


# -----------------------------------------------------------------------------
# The Engine Spine
# -----------------------------------------------------------------------------
class Engine:
    """
    Minimal north-star spine:
    1) staleness check -> (warn + Ask request) or continue
    2) ensure current prediction -> (prediction or halt)
    3) action selection gated on Result.flow/validity (placeholder action)
    4) emit EventEnvelope for everything with stable IDs
    """

    def __init__(
        self,
        *,
        prediction_log: PredictionLog,
        current_view: CurrentView,
        predictor: Predictor,
        calibrator: Calibrator,
        ask_outbox: AskOutbox,
        event_sink: EventSink,
        default_prediction_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        self._log = prediction_log
        self._view = current_view
        self._predictor = predictor
        self._cal = calibrator
        self._ask = ask_outbox
        self._events = event_sink
        self._ttl = default_prediction_ttl

    # ---------------------------
    # Event emission
    # ---------------------------
    def _emit(self, *, ctx: EpisodeContext, now: datetime, event_type: str,
              scope: Optional[Scope], payload: Mapping[str, Any]) -> None:
        env = EventEnvelope(
            event_id=_event_id(event_type, episode_id=ctx.episode_id, now=now, extra=scope.key() if scope else ""),
            event_type=event_type,
            occurred_at=now,
            episode_id=ctx.episode_id,
            scope=scope,
            gherkin=ctx.gherkin,
            observer=ctx.observer,
            payload=payload,
        )
        self._events.emit(env)

    # ---------------------------
    # (1) Observation freshness
    # ---------------------------
    def evaluate_observation_freshness(
        self,
        *,
        ctx: EpisodeContext,
        scope: Scope,
        schedule: ObservationSchedule,
        last_observation: Optional[ObservationRecord],
        now: datetime,
    ) -> Result[None]:
        if last_observation is None:
            r = _warn(
                "No observation exists yet; request initial measurement.",
                code=Code.STALE_OBSERVATION,
                details={"scope": scope.key()},
                hints=(ActionHint(kind="prompt_user", params={"reason": "no_observation"}),),
            )
            self._emit(ctx=ctx, now=now, event_type="observation_freshness", scope=scope, payload=asdict(r.rationale))
            return Result(flow=r.flow, validity=r.validity, value=None, rationale=r.rationale, action_hints=r.action_hints)

        age_s = (now - last_observation.observed_at).total_seconds()
        details = {
            "last_observed_at": _iso(last_observation.observed_at),
            "age_seconds": int(age_s),
            "stale_after_seconds": schedule.stale_after_seconds,
        }

        if age_s > schedule.stale_after_seconds:
            r = _warn(
                "Observation is stale; request human measurement via Ask.",
                code=Code.STALE_OBSERVATION,
                details=details,
                evidence=last_observation.evidence_refs,
                hints=(ActionHint(kind="prompt_user", params={"channel": "ask", "title": "Check water meter"}),),
            )
        else:
            r = _ok("Observation is fresh.", code=Code.FRESH_OBSERVATION, details=details)

        self._emit(ctx=ctx, now=now, event_type="observation_freshness", scope=scope, payload={
            "flow": r.flow.value,
            "validity": r.validity.value,
            "rationale": asdict(r.rationale),
            "action_hints": [asdict(h) for h in r.action_hints],
        })
        return Result(flow=r.flow, validity=r.validity, value=None, rationale=r.rationale, action_hints=r.action_hints)

    # ---------------------------
    # Ask request creation (human probe)
    # ---------------------------
    def request_user_observation_via_ask(
        self,
        *,
        ctx: EpisodeContext,
        scope: Scope,
        question: str,
        last_observation: Optional[ObservationRecord],
        now: datetime,
    ) -> PromptDecision:
        decision = PromptDecision(
            decision_id=_decision_id(scope, now),
            scope=scope,
            made_at=now,
            agent_id="engine",
            observer=ctx.observer,
            policy_id="staleness_policy",
            policy_version="v0",
            experiment=ctx.experiment,
            decision_kind="prompt_user",
            prompt_text=question,
            expected_value=0.0,  # fill in later with EIG*P*P - cost
            evidence_refs=tuple(last_observation.evidence_refs if last_observation else ()),
            rationale={"reason": "stale_observation", "scope": scope.key()},
        )

        ask_context = {
            "scope": scope.key(),
            "last_seen": _iso(last_observation.observed_at) if last_observation else None,
            "last_value": last_observation.value if last_observation else None,
            "now": _iso(now),
        }
        request_id = self._ask.create_request(title="Check water meter", question=question, context=ask_context)

        self._emit(ctx=ctx, now=now, event_type="prompt_decision", scope=scope, payload={
            **asdict(decision),
            "request_id": request_id,
        })
        return decision

    # ---------------------------
    # (2) Ensure current prediction (with invariant gates)
    # ---------------------------
    def ensure_current_prediction(
        self,
        *,
        ctx: EpisodeContext,
        scope: Scope,
        evidence: Sequence[EvidenceRef],
        now: datetime,
    ) -> Result[PredictionRecord]:
        # Pre-consume invariants (P0)
        inv_results: list[Result[None]] = []
        check_ctx = CheckContext(
            scope=scope,
            now_iso=_iso(now),
            current_view=self._view,      # If your CheckContext expects ports, wrap with adapters
            prediction_log=self._log,     # same as above
            evidence_refs=tuple(evidence),
        )
        for inv_id, checker in REGISTRY.items():
            # In minimal spine, run all and merge. Later you can phase/prioritize.
            inv_results.append(checker(check_ctx))

        merged = _merge_results(inv_results)
        self._emit(ctx=ctx, now=now, event_type="invariant_checks_pre", scope=scope, payload={
            "merged": {
                "flow": merged.flow.value,
                "validity": merged.validity.value,
                "rationale": asdict(merged.rationale),
                "action_hints": [asdict(h) for h in merged.action_hints],
            },
            "all": [
                {
                    "flow": r.flow.value,
                    "validity": r.validity.value,
                    "rationale": asdict(r.rationale),
                    "action_hints": [asdict(h) for h in r.action_hints],
                } for r in inv_results
            ],
        })

        if merged.flow == Flow.STOP:
            # Return controlled halt, as per contract (no exceptions)
            return Result(flow=Flow.STOP, validity=Validity.INVALID, value=None,
                          rationale=merged.rationale, action_hints=merged.action_hints, issues=merged.issues)

        # Fast path: view already has current
        current = self._view.get_current(scope, now=now)
        if current is not None:
            self._emit(ctx=ctx, now=now, event_type="prediction_current", scope=scope, payload=asdict(current))
            return Result(
                flow=Flow.CONTINUE,
                validity=Validity.VALID,
                value=current,
                rationale=Rationale(code=Code.NO_CURRENT_PREDICTION, invariant_id=None, message="Current prediction available.",
                                    details={"prediction_id": current.prediction_id}),
            )

        # Produce raw + calibrated
        raw = self._predictor.predict(scope, evidence, now=now)
        calibrated = self._cal.calibrate(raw, scope)

        pred = PredictionRecord(
            prediction_id=_prediction_id(scope, now),
            scope=scope,
            issued_at=now,
            valid_from=now,
            valid_until=now + self._ttl,
            filtration_id=f"F::{int(now.timestamp())}::{len(evidence)}",
            evidence_refs=tuple(evidence),
            invariants_assumed=(InvariantId.P0_NO_CURRENT_PREDICTION.value, InvariantId.P1_WRITE_BEFORE_USE.value),
            distribution_raw=raw,
            distribution_calibrated=calibrated,
        )

        # Write-before-use
        if not self._log.is_available():
            r = _halt(
                "Prediction store unavailable; cannot record prediction.",
                code=Code.STORE_UNAVAILABLE,
                invariant_id=InvariantId.P1_WRITE_BEFORE_USE.value,
                details={"scope": scope.key()},
                hints=(ActionHint(kind="retry", params={"after_seconds": 30}),),
                evidence=evidence,
            )
            self._emit(ctx=ctx, now=now, event_type="halt", scope=scope, payload=asdict(r.rationale))
            return Result(flow=r.flow, validity=r.validity, value=None, rationale=r.rationale, action_hints=r.action_hints)

        self._log.append(pred)
        self._emit(ctx=ctx, now=now, event_type="prediction_appended", scope=scope, payload=asdict(pred))

        # Project current view from log
        self._view.project_from_log(self._log, now=now)
        current_after = self._view.get_current(scope, now=now)

        # Post-write gate: ensure retrievable/current
        if current_after is None or current_after.prediction_id != pred.prediction_id:
            r = _halt(
                "Prediction not retrievable as current after write; refusing to proceed.",
                code=Code.WRITE_BEFORE_USE_VIOLATION,
                invariant_id=InvariantId.P1_WRITE_BEFORE_USE.value,
                details={"expected_prediction_id": pred.prediction_id, "scope": scope.key()},
                hints=(ActionHint(kind="rebuild_view", params={"source": "prediction_log"}),),
                evidence=evidence,
            )
            self._emit(ctx=ctx, now=now, event_type="halt", scope=scope, payload=asdict(r.rationale))
            return Result(flow=r.flow, validity=r.validity, value=None, rationale=r.rationale, action_hints=r.action_hints)

        # Return prediction
        return Result(
            flow=Flow.CONTINUE,
            validity=Validity.VALID,
            value=current_after,
            rationale=Rationale(code=Code.NO_CURRENT_PREDICTION, invariant_id=None, message="New prediction recorded and current.",
                                details={"prediction_id": current_after.prediction_id}),
        )

    # ---------------------------
    # (3) Decision/action selection (placeholder)
    # ---------------------------
    def decide_next_action(
        self,
        *,
        ctx: EpisodeContext,
        scope: Scope,
        evidence: Sequence[EvidenceRef],
        now: datetime,
    ) -> Result[Mapping[str, Any]]:
        pred_res = self.ensure_current_prediction(ctx=ctx, scope=scope, evidence=evidence, now=now)
        self._emit(ctx=ctx, now=now, event_type="ensure_prediction_result", scope=scope, payload={
            "flow": pred_res.flow.value,
            "validity": pred_res.validity.value,
            "rationale": asdict(pred_res.rationale),
            "action_hints": [asdict(h) for h in pred_res.action_hints],
            "prediction_id": pred_res.value.prediction_id if pred_res.value else None,
        })

        if pred_res.flow == Flow.STOP or pred_res.value is None:
            # Controlled halt/invalid: return as-is, let observation layer respond
            return Result(flow=pred_res.flow, validity=pred_res.validity, value=None,
                          rationale=pred_res.rationale, action_hints=pred_res.action_hints, issues=pred_res.issues)

        # Example policy: if calibrated confidence < 0.6, warn + suggest probe (but continue)
        conf = float(pred_res.value.distribution_calibrated.confidence)
        if conf < 0.6:
            r = Result(
                flow=Flow.CONTINUE,
                validity=Validity.DEGRADED,
                value={"action": "probe_more", "scope": scope.key()},
                rationale=Rationale(code=Code.LOW_EXPECTED_VALUE, invariant_id=None,
                                    message="Low confidence; recommend more evidence before acting.",
                                    details={"confidence": conf}),
                action_hints=(ActionHint(kind="probe", params={"scope": scope.key()}),),
            )
            self._emit(ctx=ctx, now=now, event_type="decision", scope=scope, payload={
                "flow": r.flow.value,
                "validity": r.validity.value,
                "rationale": asdict(r.rationale),
                "action_hints": [asdict(h) for h in r.action_hints],
                "value": r.value,
            })
            return r

        # Otherwise "act"
        r = Result(
            flow=Flow.CONTINUE,
            validity=Validity.VALID,
            value={"action": "act", "scope": scope.key(), "prediction_id": pred_res.value.prediction_id},
            rationale=Rationale(code=Code.PROMPT_ALLOWED, invariant_id=None,
                                message="Sufficient confidence to act.",
                                details={"confidence": conf}),
        )
        self._emit(ctx=ctx, now=now, event_type="decision", scope=scope, payload={
            "flow": r.flow.value,
            "validity": r.validity.value,
            "rationale": asdict(r.rationale),
            "value": r.value,
        })
        return r

    # ---------------------------
    # (4) Resolution updates calibration (closed loop)
    # ---------------------------
    def resolve_prediction(
        self,
        *,
        ctx: EpisodeContext,
        prediction_id: str,
        observed_value: Any,
        evidence: Sequence[EvidenceRef],
        now: datetime,
    ) -> None:
        pred = self._log.get(prediction_id)
        res = ResolutionRecord(
            prediction_id=prediction_id,
            resolved_at=now,
            observed_value=observed_value,
            evidence_refs=tuple(evidence),
        )
        self._log.append_resolution(res)
        self._cal.update(pred, res)
        self._emit(ctx=ctx, now=now, event_type="prediction_resolution", scope=pred.scope, payload=asdict(res))


# -----------------------------------------------------------------------------
# Example usage sequence (how the spine is intended to be called)
# -----------------------------------------------------------------------------
def run_water_meter_cycle(
    engine: Engine,
    *,
    episode_id: str,
    now: Optional[datetime] = None,
    gherkin: Optional[StableGherkinIds] = None,
) -> Result[Mapping[str, Any]]:
    now = now or _now_utc()
    ctx = EpisodeContext(
        episode_id=episode_id,
        observer=ObserverFrame(
            role="assistant",
            capabilities=("prompt_user", "probe_sensor"),
            authorization_level="baseline",
            evaluation_invariants=(InvariantId.P0_NO_CURRENT_PREDICTION.value, InvariantId.P1_WRITE_BEFORE_USE.value),
        ),
        gherkin=gherkin,
        experiment=ExperimentAssignment(experiment_id="water_meter_tracking", variant="A", seed="stable"),
    )

    scope = Scope(mission="utilities_monitoring", entity="Home", variable="water_meter_level")
    schedule = ObservationSchedule(period_seconds=3600, stale_after_seconds=7200)

    # In real code, this comes from an ObservationLog adapter:
    last_obs: Optional[ObservationRecord] = None

    freshness = engine.evaluate_observation_freshness(
        ctx=ctx, scope=scope, schedule=schedule, last_observation=last_obs, now=now
    )
    if freshness.validity == Validity.DEGRADED:
        # Create Ask request (human measurement)
        engine.request_user_observation_via_ask(
            ctx=ctx,
            scope=scope,
            question="What is the current water meter reading?",
            last_observation=last_obs,
            now=now,
        )
        # We can still proceed to prediction/decision, but policy may choose to wait.

    evidence: list[EvidenceRef] = []
    return engine.decide_next_action(ctx=ctx, scope=scope, evidence=evidence, now=now)
```


A few things in what I delivered are **above-and-beyond** (extra complexity or “nice-to-have” that’s not minimal), and a few places could be **cleaner / more aligned** with your north-star invariants.

## What’s above-and-beyond in my delivery

### 1) I mixed *engine spine* with *example usage*

`run_water_meter_cycle()` is useful as a demo, but it’s not part of the “spine.” It adds cognitive load and makes it look like the engine owns scenario orchestration.

**Better:** keep the spine as a class + methods only; put demo wiring in `examples/` or tests.

---

### 2) I ran **all** invariants in `ensure_current_prediction`

I looped through `REGISTRY` and merged results, which is more general than needed for a minimal first iteration.

**Better minimal:** for the “ensure prediction” capability, explicitly call just the invariants you need at that gate (P0 pre-consume, P1 post-write). Registry iteration becomes useful later for policy-defined invariant sets.

---

### 3) I emitted “halt” as a special event type *and* used Result

This duplicates semantics (halt is already a Result with STOP/INVALID). Emitting `event_type="halt"` is fine as an index convenience, but it risks divergence if you later enrich Result and forget Halt-specific emission.

**Better:** always emit `event_type="result"` (or `capability_result`) with `flow/validity`, and optionally tag/route it as “halt” downstream based on `flow==STOP`.

---

### 4) I included a placeholder `_merge_results` composer

It’s useful, but arguably above-minimal because you can avoid composition entirely by calling only two invariants in deterministic order.

**Better minimal:** remove merging until you actually need multiple invariants per gate.

---

### 5) I did ad-hoc ID generation in-line

`_prediction_id`, `_decision_id`, `_event_id` are placeholders. Having them in the spine is okay, but it’s extra surface area early.

**Better:** centralize as one `IdProvider` port or utility module so you don’t spread “ID semantics” into the engine.

---

## What could be done better (real improvements)

### A) Fix a type/port mismatch in CheckContext usage

In the spine I passed `self._view` and `self._log` into `CheckContext` assuming they match `CurrentViewPort`/`PredictionLogPort`. But I also used methods (`get_current`) that don’t match the port signature I sketched earlier (`get_current_prediction_id(scope, now_iso)`).

**Better:** either:

* align the port protocols to the real methods (`get_current(scope, now)`), **or**
* wrap adapters into “port views” that exactly match the invariant checker needs.

This matters because invariants are supposed to be stable and low-level.

---

### B) Make “staleness → Ask request” a *capability* returning Result, not two separate calls

Right now:

* `evaluate_observation_freshness()` returns Result with a hint
* then a separate method creates the Ask request

That separation is fine, but it’s easy to forget to perform the hint, and it blurs “decision vs emission.”

**Better (cleanest):** one capability:

* `request_observation_if_stale(...) -> Result[PromptDecision]`
  that:
* evaluates staleness
* records decision
* emits Ask request (via outbox)
* returns STOP/CONTINUE with appropriate validity

This matches your “prompting is a first-class decision artifact.”

---

### C) Ensure “write-before-emit” invariant for prompts too

I did write-before-use for predictions, but for prompting I didn’t explicitly enforce:

* “decision must be recorded before prompt emission”

I created `PromptDecision` and then called Ask outbox, but it’s not gated as a formal invariant and not persisted to a log before emission.

**Better:** treat prompt decisions like prediction decisions:

* append `PromptDecision` to a log first
* then call `AskOutbox.create_request`
* then emit event referencing the logged decision id

This makes experimentation auditable and reproducible.

---

### D) Don’t hardcode policy inside the engine method

In `decide_next_action()` I inserted a threshold (`confidence < 0.6`) and used `LOW_EXPECTED_VALUE` in a way that doesn’t quite match the earlier “expected value” objective.

**Better:** `Engine` should orchestrate; a `Policy` port should decide actions based on:

* calibrated confidence
* meta-confidence (calibration quality)
* nuisance budgets / quiet hours / authorization
* expected value computation

So the spine stays invariant, policy evolves.

---

### E) “85% rule” / calibration loop isn’t actually threaded

I included `calibrator.update` on resolution, which is good, but I didn’t show:

* how calibration meta-confidence influences prompting/asking
* how miscalibration triggers ISSUE creation or adjusts mapping
* how results carry calibration diagnostics

**Better:** return a small `CalibrationSnapshot` from `calibrate()` or `meta_confidence(scope)` and include it in prediction records / decision rationale.

---

### F) EventEnvelope payload serialization is too hand-wavy

I used `asdict()` on dataclasses and stuffed them into `payload`. That’s okay for a sketch, but in a real system you’ll want:

* stable JSON shape
* versioning (`schema_version`)
* guaranteed ISO timestamps
* stable keys

**Better:** use Pydantic models for envelopes + payloads, or a single `to_json()` per model, and include `schema_version`.

---

## The “most minimal” engine spine (what I’d tighten)

If I were to tighten it to exactly what you promised and nothing extra, I’d do:

1. **One** method for staleness + Ask:

* returns `Result[PromptDecision|None]`
* always emits an event

2. **One** method ensure prediction:

* runs only P0 then P1
* returns `Result[PredictionRecord]`
* emits one “capability_result” event with stable IDs

3. **Action selection** delegated to a `Policy` port:

* `policy.decide(prediction, ctx) -> Result[ActionPlan]`

4. **All events** are `EventEnvelope(event_type="capability_result")`

* with tags in payload if needed

No demo runner, no registry iteration, no merge function yet.

---

## Net summary

**Above-and-beyond:** registry-wide invariant execution, merge composer, demo runner, halt-special events, scattered ID helpers.

**Better:** make ports match, fold staleness→Ask into one capability, enforce write-before-emit for prompts, move policy out of engine, make envelope serialization/versioning explicit, and simplify invariant execution to exactly P0/P1 at two gate points.

We could rewrite the spine in that tighter form (same models, fewer moving parts), so it’s closer to an invariant “complete” north-star implementation.

