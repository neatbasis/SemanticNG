# state_renormalization/adapters/schema_selector.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

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
    name: str

    def applies(self, ctx: SelectorContext) -> bool: ...

    def emit(self, ctx: SelectorContext) -> SchemaSelection: ...


@dataclass(frozen=True)
class FunctionRule:
    name: str
    _applies: Callable[[SelectorContext], bool]
    _emit: Callable[[SelectorContext], SchemaSelection]

    def applies(self, ctx: SelectorContext) -> bool:
        return self._applies(ctx)

    def emit(self, ctx: SelectorContext) -> SchemaSelection:
        return self._emit(ctx)


def _no_response_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.SCHEMA, key="channel.capture")
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.MISSING_CONTEXT,
        candidates=[],
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[
            ClarifyingQuestion(
                q="I didn’t catch that. Please repeat?",
                format=AskFormat.FREEFORM,
            )
        ],
        evidence={"signals": ["no_response"]},
        notes="No response captured (transport/ASR timeout).",
    )
    return SchemaSelection(
        schemas=[SchemaHit(name="clarify.capture", score=0.95, about=about)],
        ambiguities=[amb],
        notes="no_response",
    )


def _empty_input_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.SCHEMA, key="cli.input.empty")
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.MISSING_CONTEXT,
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[ClarifyingQuestion(q="I didn't catch anything. What do you want to do?", format=AskFormat.FREEFORM)],
        evidence={"signals": ["empty_text"]},
    )
    return SchemaSelection(
        schemas=[SchemaHit(name="clarify.empty_input", score=0.95, about=about)],
        ambiguities=[amb],
    )


def _exit_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.INTENT, key="user.intent.exit", span=TextSpan(text=ctx.raw))
    return SchemaSelection(
        schemas=[SchemaHit(name="exit_intent", score=0.99, about=about)],
        ambiguities=[],
    )


def _vague_actor_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.ENTITY, key="event.actor", span=TextSpan(text=ctx.raw))
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.UNDERSPECIFIED,
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[
            ClarifyingQuestion(
                q="Who is 'they'?",
                format=AskFormat.FREEFORM,
            )
        ],
        evidence={"signals": ["vague_pronoun", "arrival_event"], "tokens": sorted(ctx.tokens)},
        notes="Vague actor in arrival statement.",
    )
    return SchemaSelection(
        schemas=[
            SchemaHit(name="clarify.actor", score=0.92, about=about),
            SchemaHit(name="clarification_needed", score=0.75, about=about),
        ],
        ambiguities=[amb],
    )


def _url_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.INTENT, key="task.intent.link", span=TextSpan(text=ctx.raw))
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.UNDERSPECIFIED,
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[
            ClarifyingQuestion(
                q="What should I do with that link?",
                format=AskFormat.MULTICHOICE,
                options=["summarize", "extract key claims", "relate to our system", "just open it"],
            )
        ],
        evidence={"signals": ["url_present"]},
    )
    return SchemaSelection(
        schemas=[
            SchemaHit(name="clarify.link_intent", score=0.9, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _timer_unit_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.PARAMETER, key="timer.duration", span=TextSpan(text=ctx.raw))
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.UNDERSPECIFIED,
        candidates=[
            Candidate(value="minutes", score=0.65),
            Candidate(value="seconds", score=0.25),
            Candidate(value="hours", score=0.10),
        ],
        resolution_policy=ResolutionPolicy.ASK_USER,
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
    return SchemaSelection(
        schemas=[
            SchemaHit(name="clarify.duration_unit", score=0.9, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _uncertainty_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.GOAL, key="user.goal", span=TextSpan(text=ctx.raw))
    amb = Ambiguity(
        status=AmbiguityStatus.UNRESOLVED,
        about=about,
        type=AmbiguityType.UNDERSPECIFIED,
        resolution_policy=ResolutionPolicy.ASK_USER,
        ask=[
            ClarifyingQuestion(
                q="What are you trying to achieve right now?",
                format=AskFormat.MULTICHOICE,
                options=["find something", "understand something", "plan next step", "something else"],
            )
        ],
        evidence={"signals": ["uncertainty_phrase"]},
    )
    return SchemaSelection(
        schemas=[
            SchemaHit(name="clarify.goal", score=0.86, about=about),
            SchemaHit(name="clarification_needed", score=0.7, about=about),
        ],
        ambiguities=[amb],
    )


def _actionable_emit(ctx: SelectorContext) -> SchemaSelection:
    about = AmbiguityAbout(kind=AboutKind.INTENT, key="user.intent", span=TextSpan(text=ctx.raw))
    return SchemaSelection(
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


RULE_PHASES: tuple[str, ...] = ("hard-stop", "disambiguation", "fallback")
RULES_BY_PHASE: dict[str, list[Rule]] = {
    "hard-stop": [
        FunctionRule(
            name="no_response",
            _applies=lambda ctx: ctx.error is not None and ctx.error.status == CaptureStatus.NO_RESPONSE,
            _emit=_no_response_emit,
        ),
        FunctionRule(
            name="empty_input",
            _applies=lambda ctx: ctx.error is None and not ctx.normalized.strip(),
            _emit=_empty_input_emit,
        ),
        FunctionRule(
            name="exit_intent",
            _applies=lambda ctx: ctx.error is None and is_exit_intent(ctx.normalized),
            _emit=_exit_emit,
        ),
    ],
    "disambiguation": [
        FunctionRule(
            name="vague_actor",
            _applies=lambda ctx: (ctx.tokens & VAGUE_PRONOUNS) and any(w in ctx.tokens for w in ARRIVAL_WORDS),
            _emit=_vague_actor_emit,
        ),
        FunctionRule(
            name="url_intent",
            _applies=lambda ctx: bool(ctx.metadata.get("has_url")),
            _emit=_url_emit,
        ),
        FunctionRule(
            name="timer_unit",
            _applies=lambda ctx: bool(ctx.metadata.get("mentions_timerish"))
            and bool(ctx.metadata.get("has_numberish"))
            and not bool(ctx.metadata.get("has_unit")),
            _emit=_timer_unit_emit,
        ),
        FunctionRule(
            name="uncertainty",
            _applies=lambda ctx: has_any_phrase(ctx.normalized, UNCERTAIN_PHRASES),
            _emit=_uncertainty_emit,
        ),
    ],
    "fallback": [
        FunctionRule(
            name="actionable_intent",
            _applies=lambda _ctx: True,
            _emit=_actionable_emit,
        )
    ],
}


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

def naive_schema_selector(text: Optional[str], *, error: Optional[CaptureOutcome]) -> SchemaSelection:
    ctx = build_selector_context(text, error=error)

    for phase in RULE_PHASES:
        for rule in RULES_BY_PHASE[phase]:
            if rule.applies(ctx):
                return rule.emit(ctx)

    return SchemaSelection(schemas=[], ambiguities=[])
