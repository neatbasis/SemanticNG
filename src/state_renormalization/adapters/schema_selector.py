# state_renormalization/adapters/schema_selector.py
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol

from state_renormalization.contracts import (
    AboutKind,
    Ambiguity,
    AmbiguityAbout,
    AmbiguityStatus,
    AmbiguityType,
    AskFormat,
    CaptureOutcome,
    CaptureStatus,
    Candidate,
    ClarifyingQuestion,
    ResolutionPolicy,
    SchemaHit,
    SchemaSelection,
    TextSpan,
)

_WORD = re.compile(r"[a-zA-Z0-9']+")


def norm_tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD.finditer(text or "")]


def normalize_text(s: str) -> str:
    """
    Minimal normalization so downstream token rules behave.
    Key: make "they're" observable as "they" + "are".
    """
    t = (s or "").strip().replace("’", "'")
    t = t.lower()
    t = t.replace("they're", "they are")
    t = t.replace("dont", "don't")
    return t


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


def is_exit_intent(t: str) -> bool:
    t = (t or "").strip().lower()
    if t in EXIT_EXACT:
        return True
    return any(p in t for p in EXIT_PHRASES)


UNCERTAIN_PHRASES = {"not sure", "don't know", "dont know", "idk", "maybe", "perhaps", "unsure"}
ARRIVAL_WORDS = {"coming", "arriving", "here", "outside", "near"}
VAGUE_PRONOUNS = {"they", "them"}  # keep narrow to avoid he/she/it false positives


def has_any_phrase(t: str, phrases: set[str]) -> bool:
    return any(p in t for p in phrases)


def has_url(t: str) -> bool:
    return "http://" in t or "https://" in t


def sort_schema_hits(hits: list[SchemaHit]) -> list[SchemaHit]:
    return sorted(
        hits,
        key=lambda h: (
            -float(h.score),
            0 if h.about is not None else 1,
            h.name,
        ),
    )


@dataclass(frozen=True)
class SelectorContext:
    raw: str
    normalized: str
    tokens: set[str]
    error: Optional[CaptureOutcome]
    metadata: dict[str, object] = field(default_factory=dict)


class Rule(Protocol):
    @property
    def name(self) -> str: ...

    def applies(self, ctx: SelectorContext) -> bool: ...

    def emit(self, ctx: SelectorContext) -> SchemaSelection: ...


class SelectorDecisionStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    HALT = "halt"


@dataclass(frozen=True)
class HeuristicCandidate:
    phase: str
    rule_name: str
    phase_index: int
    order_in_phase: int
    rule: Rule
    score: float


@dataclass(frozen=True)
class InvariantViolation:
    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyFinding:
    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SelectorDecisionOutcome:
    status: SelectorDecisionStatus
    chosen: Optional[HeuristicCandidate]
    violations: list[InvariantViolation]
    policy_findings: list[PolicyFinding]
    heuristic_candidates: list[HeuristicCandidate]


@dataclass(frozen=True)
class BaseRule:
    name: str

    def applies(self, ctx: SelectorContext) -> bool:
        raise NotImplementedError

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        raise NotImplementedError


def _about(kind: AboutKind, key: str, *, span_text: Optional[str] = None) -> AmbiguityAbout:
    if span_text is None:
        return AmbiguityAbout(kind=kind, key=key)
    return AmbiguityAbout(kind=kind, key=key, span=TextSpan(text=span_text))


def _amb(
    *,
    about: AmbiguityAbout,
    type_: AmbiguityType,
    ask: list[ClarifyingQuestion],
    evidence: dict[str, object],
    resolution_policy: ResolutionPolicy = ResolutionPolicy.ASK_USER,
    candidates: Optional[list[Candidate]] = None,
    notes: Optional[str] = None,
) -> Ambiguity:
    return Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=type_,
        candidates=candidates or [],
        resolution_policy=resolution_policy,
        ask=ask,
        evidence=evidence,
        notes=notes,
    )


def _selection(*, schemas: list[SchemaHit], ambiguities: list[Ambiguity], notes: Optional[str] = None) -> SchemaSelection:
    return SchemaSelection(
        schemas=sort_schema_hits(schemas),
        ambiguities=ambiguities,
        notes=notes,
    )


@dataclass(frozen=True)
class NoResponseRule(BaseRule):
    name: str = "no_response"

    def applies(self, ctx: SelectorContext) -> bool:
        return ctx.error is not None and ctx.error.status == CaptureStatus.NO_RESPONSE

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _no_response_emit(ctx)


@dataclass(frozen=True)
class EmptyInputRule(BaseRule):
    name: str = "empty_input"

    def applies(self, ctx: SelectorContext) -> bool:
        return ctx.error is None and not ctx.normalized.strip()

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _empty_input_emit(ctx)


@dataclass(frozen=True)
class ExitIntentRule(BaseRule):
    name: str = "exit_intent"

    def applies(self, ctx: SelectorContext) -> bool:
        return ctx.error is None and is_exit_intent(ctx.normalized)

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _exit_emit(ctx)


@dataclass(frozen=True)
class VagueActorRule(BaseRule):
    name: str = "vague_actor"

    def applies(self, ctx: SelectorContext) -> bool:
        return bool((ctx.tokens & VAGUE_PRONOUNS) and any(w in ctx.tokens for w in ARRIVAL_WORDS))

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _vague_actor_emit(ctx)


@dataclass(frozen=True)
class UrlIntentRule(BaseRule):
    name: str = "url_intent"

    def applies(self, ctx: SelectorContext) -> bool:
        return bool(ctx.metadata.get("has_url"))

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _url_emit(ctx)


@dataclass(frozen=True)
class TimerUnitRule(BaseRule):
    name: str = "timer_unit"

    def applies(self, ctx: SelectorContext) -> bool:
        return (
            bool(ctx.metadata.get("mentions_timerish"))
            and bool(ctx.metadata.get("has_numberish"))
            and not bool(ctx.metadata.get("has_unit"))
        )

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _timer_unit_emit(ctx)


@dataclass(frozen=True)
class UncertaintyRule(BaseRule):
    name: str = "uncertainty"

    def applies(self, ctx: SelectorContext) -> bool:
        return has_any_phrase(ctx.normalized, UNCERTAIN_PHRASES)

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _uncertainty_emit(ctx)


@dataclass(frozen=True)
class ActionableIntentRule(BaseRule):
    name: str = "actionable_intent"

    def applies(self, ctx: SelectorContext) -> bool:
        return True

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return _actionable_emit(ctx)


def _no_response_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.SCHEMA, "channel.capture")
    amb = _amb(
        about=about,
        type_=AmbiguityType.MISSING_CONTEXT,
        ask=[
            ClarifyingQuestion(
                q="I didn’t catch that. Please repeat?",
                format=AskFormat.FREEFORM,
            )
        ],
        evidence={"signals": ["no_response"]},
        notes="No response captured (transport/ASR timeout).",
    )
    return _selection(
        schemas=[SchemaHit(name="clarify.capture", score=0.95, about=about)],
        ambiguities=[amb],
        notes="no_response",
    )


def _empty_input_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.SCHEMA, "cli.input.empty")
    amb = _amb(
        about=about,
        type_=AmbiguityType.MISSING_CONTEXT,
        ask=[ClarifyingQuestion(q="I didn't catch anything. What do you want to do?", format=AskFormat.FREEFORM)],
        evidence={"signals": ["empty_text"]},
    )
    return _selection(
        schemas=[SchemaHit(name="clarify.empty_input", score=0.95, about=about)],
        ambiguities=[amb],
    )


def _exit_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.INTENT, "user.intent.exit", span_text=ctx.raw)
    return _selection(
        schemas=[SchemaHit(name="exit_intent", score=0.99, about=about)],
        ambiguities=[],
    )


def _vague_actor_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.ENTITY, "event.actor", span_text=ctx.raw)
    amb = _amb(
        about=about,
        type_=AmbiguityType.UNDERSPECIFIED,
        ask=[
            ClarifyingQuestion(
                q="Who is 'they'?",
                format=AskFormat.FREEFORM,
            )
        ],
        evidence={"signals": ["vague_pronoun", "arrival_event"], "tokens": sorted(ctx.tokens)},
        notes="Vague actor in arrival statement.",
    )
    return _selection(
        schemas=[
            SchemaHit(name="clarify.actor", score=0.92, about=about),
            SchemaHit(name="clarification_needed", score=0.75, about=about),
        ],
        ambiguities=[amb],
    )


def _url_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.INTENT, "task.intent.link", span_text=ctx.raw)
    amb = _amb(
        about=about,
        type_=AmbiguityType.UNDERSPECIFIED,
        ask=[
            ClarifyingQuestion(
                q="What should I do with that link?",
                format=AskFormat.MULTICHOICE,
                options=["summarize", "extract key claims", "relate to our system", "just open it"],
            )
        ],
        evidence={"signals": ["url_present"]},
    )
    return _selection(
        schemas=[
            SchemaHit(name="clarify.link_intent", score=0.9, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _timer_unit_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.PARAMETER, "timer.duration", span_text=ctx.raw)
    amb = _amb(
        about=about,
        type_=AmbiguityType.UNDERSPECIFIED,
        candidates=[
            Candidate(value="minutes", score=0.65),
            Candidate(value="seconds", score=0.25),
            Candidate(value="hours", score=0.10),
        ],
        ask=[
            ClarifyingQuestion(
                q="Ten what — minutes or seconds?",
                format=AskFormat.MULTICHOICE,
                options=["minutes", "seconds"],
            )
        ],
        evidence={"signals": ["timerish", "number_without_unit"], "tokens": sorted(ctx.tokens)},
        notes="Duration unit missing.",
    )
    return _selection(
        schemas=[
            SchemaHit(name="clarify.duration_unit", score=0.9, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _uncertainty_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.GOAL, "user.goal", span_text=ctx.raw)
    amb = _amb(
        about=about,
        type_=AmbiguityType.UNDERSPECIFIED,
        ask=[
            ClarifyingQuestion(
                q="What are you trying to achieve right now?",
                format=AskFormat.MULTICHOICE,
                options=["find something", "understand something", "plan next step", "something else"],
            )
        ],
        evidence={"signals": ["uncertainty_phrase"]},
    )
    return _selection(
        schemas=[
            SchemaHit(name="clarify.goal", score=0.86, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _actionable_emit(ctx: SelectorContext) -> SchemaSelection:
    about = _about(AboutKind.INTENT, "user.intent", span_text=ctx.raw)
    return _selection(
        schemas=[SchemaHit(name="actionable_intent", score=0.7, about=about)],
        ambiguities=[],
    )


def build_selector_context(text: Optional[str], *, error: Optional[CaptureOutcome]) -> SelectorContext:
    raw = text or ""
    normalized = normalize_text(raw)
    tokens = set(norm_tokens(normalized))
    return SelectorContext(
        raw=raw,
        normalized=normalized,
        tokens=tokens,
        error=error,
        metadata={
            "has_url": has_url(normalized),
            "has_numberish": any(tok.isdigit() for tok in tokens) or any(tok in {"ten", "five"} for tok in tokens),
            "has_unit": any(
                u in tokens
                for u in {"s", "sec", "second", "seconds", "m", "min", "minute", "minutes", "h", "hour", "hours"}
            ),
            "mentions_timerish": any(w in normalized for w in ["timer", "remind", "reminder", "in "]),
        },
    )


RULE_PHASES: tuple[str, ...] = ("hard-stop", "ambiguity-disambiguation", "fallback")


@dataclass
class RuleRegistry:
    """
    Registry-based phase pipeline.

    `domain` allows adding domain/context specific rules without modifying selector flow.
    """

    phases: tuple[str, ...] = RULE_PHASES
    _rules_by_domain: dict[str, dict[str, list[Rule]]] = field(
        default_factory=lambda: defaultdict(lambda: {phase: [] for phase in RULE_PHASES})
    )

    def register(self, *, phase: str, rule: Rule, domain: str = "default", prepend: bool = False) -> None:
        if phase not in self.phases:
            raise ValueError(f"Unknown rule phase '{phase}'. Expected one of: {', '.join(self.phases)}")
        bucket = self._rules_by_domain[domain][phase]
        if prepend:
            bucket.insert(0, rule)
            return
        bucket.append(rule)

    def phase_rules(self, *, phase: str, domain: str = "default") -> list[Rule]:
        if phase not in self.phases:
            raise ValueError(f"Unknown rule phase '{phase}'. Expected one of: {', '.join(self.phases)}")
        domain_rules = self._rules_by_domain.get(domain, {}).get(phase, [])
        if domain == "default":
            return list(domain_rules)
        default_rules = self._rules_by_domain.get("default", {}).get(phase, [])
        return [*domain_rules, *default_rules]

    def clone_domain(self, *, domain: str = "default") -> dict[str, list[Rule]]:
        return {phase: list(self.phase_rules(phase=phase, domain=domain)) for phase in self.phases}


RULE_REGISTRY = RuleRegistry()


def register_rule(*, phase: str, rule: Rule, domain: str = "default", prepend: bool = False) -> Rule:
    RULE_REGISTRY.register(phase=phase, rule=rule, domain=domain, prepend=prepend)
    return rule


register_rule(phase="hard-stop", rule=NoResponseRule())
register_rule(phase="hard-stop", rule=EmptyInputRule())
register_rule(phase="hard-stop", rule=ExitIntentRule())

register_rule(phase="ambiguity-disambiguation", rule=VagueActorRule())
register_rule(phase="ambiguity-disambiguation", rule=UrlIntentRule())
register_rule(phase="ambiguity-disambiguation", rule=TimerUnitRule())
register_rule(phase="ambiguity-disambiguation", rule=UncertaintyRule())

register_rule(phase="fallback", rule=ActionableIntentRule())


RULES_BY_PHASE: dict[str, list[Rule]] = RULE_REGISTRY.clone_domain(domain="default")


def _propose_candidates(ctx: SelectorContext, *, domain: str) -> list[HeuristicCandidate]:
    candidates: list[HeuristicCandidate] = []
    for phase_index, phase in enumerate(RULE_PHASES):
        phase_rules = RULE_REGISTRY.phase_rules(phase=phase, domain=domain)
        for order_in_phase, rule in enumerate(phase_rules):
            if not rule.applies(ctx):
                continue
            candidates.append(
                HeuristicCandidate(
                    phase=phase,
                    rule_name=rule.name,
                    phase_index=phase_index,
                    order_in_phase=order_in_phase,
                    rule=rule,
                    score=float(-(phase_index * 1000 + order_in_phase)),
                )
            )
    return candidates


def _validate_selector_invariants(candidates: list[HeuristicCandidate]) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    if not candidates:
        violations.append(
            InvariantViolation(
                code="selector.empty_candidate_set.v1",
                message="Schema selector must always produce at least one applicable rule candidate.",
            )
        )
    return violations


def _decide_selection_policy(
    candidates: list[HeuristicCandidate],
    *,
    violations: list[InvariantViolation],
) -> SelectorDecisionOutcome:
    if violations:
        return SelectorDecisionOutcome(
            status=SelectorDecisionStatus.HALT,
            chosen=None,
            violations=violations,
            policy_findings=[],
            heuristic_candidates=candidates,
        )

    ranked = sorted(candidates, key=lambda c: (c.phase_index, c.order_in_phase))
    chosen = ranked[0]
    findings: list[PolicyFinding] = []
    if chosen.phase == "ambiguity-disambiguation":
        findings.append(
            PolicyFinding(
                code="selector.prefer_clarification_on_ambiguity.v1",
                message="Prefer clarification when ambiguity-specific rules are applicable.",
            )
        )
    return SelectorDecisionOutcome(
        status=SelectorDecisionStatus.OK,
        chosen=chosen,
        violations=violations,
        policy_findings=findings,
        heuristic_candidates=ranked,
    )


def _legacy_naive_schema_selector(text: Optional[str], *, error: Optional[CaptureOutcome]) -> SchemaSelection:
    """
    Frozen baseline implementation used by tests to verify refactors preserve behavior.
    """
    raw = text or ""
    t = normalize_text(raw)
    tokens = set(norm_tokens(t))

    if error is not None and error.status == CaptureStatus.NO_RESPONSE:
        return _no_response_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    if not t.strip():
        return _empty_input_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    if is_exit_intent(t):
        return _exit_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    if (tokens & VAGUE_PRONOUNS) and any(w in tokens for w in ARRIVAL_WORDS):
        return _vague_actor_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    if has_url(t):
        return _url_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    numberish = any(tok.isdigit() for tok in tokens) or any(tok in {"ten", "five"} for tok in tokens)
    has_unit_token = any(
        u in tokens for u in {"s", "sec", "second", "seconds", "m", "min", "minute", "minutes", "h", "hour", "hours"}
    )
    mentions_timerish = any(w in t for w in ["timer", "remind", "reminder", "in "])
    if mentions_timerish and numberish and not has_unit_token:
        return _timer_unit_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    if has_any_phrase(t, UNCERTAIN_PHRASES):
        return _uncertainty_emit(
            SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
        )

    return _actionable_emit(
        SelectorContext(raw=raw, normalized=t, tokens=tokens, error=error)
    )

def naive_schema_selector(
    text: Optional[str], *, error: Optional[CaptureOutcome], domain: str = "default"
) -> SchemaSelection:
    ctx = build_selector_context(text, error=error)

    candidates = _propose_candidates(ctx, domain=domain)
    violations = _validate_selector_invariants(candidates)
    decision = _decide_selection_policy(candidates, violations=violations)
    if decision.chosen is not None:
        return decision.chosen.rule.emit(ctx)

    return SchemaSelection(schemas=[], ambiguities=[])
