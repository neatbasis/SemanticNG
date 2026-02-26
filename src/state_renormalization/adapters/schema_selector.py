# state_renormalization/adapters/schema_selector.py
from __future__ import annotations

import re
from typing import Optional

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
    
# TODO: When we have implemented the feature for delivering multiple schemas
#return SchemaSelection(
#    schemas=sort_schema_hits([
#        SchemaHit(...),
#        SchemaHit(...),
#    ]),
#    ambiguities=[...],
#    notes="...",
#)

def naive_schema_selector(text: Optional[str], *, error: Optional[CaptureOutcome]) -> SchemaSelection:
    # --------------------------------------------------------------------------
    # 0) Transport-level failure
    # --------------------------------------------------------------------------
    if error is not None and error.status == CaptureStatus.NO_RESPONSE:
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

    # --------------------------------------------------------------------------
    # 1) Normalize + guard empty
    # --------------------------------------------------------------------------
    raw = text or ""
    t = normalize_text(raw)

    if not t.strip():
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

    # --------------------------------------------------------------------------
    # 2) Exit intent early
    # --------------------------------------------------------------------------
    if is_exit_intent(t):
        about = AmbiguityAbout(kind=AboutKind.INTENT, key="user.intent.exit", span=TextSpan(text=raw))
        return SchemaSelection(
            schemas=[SchemaHit(name="exit_intent", score=0.99, about=about)],
            ambiguities=[],
        )

    tokens = set(norm_tokens(t))

    # --------------------------------------------------------------------------
    # 3) Specific ambiguity: vague actor ("they ... coming")
    #    IMPORTANT: this must run before "uncertainty" so "I don't know" doesn't steal it.
    # --------------------------------------------------------------------------
    if (tokens & VAGUE_PRONOUNS) and any(w in tokens for w in ARRIVAL_WORDS):
        about = AmbiguityAbout(kind=AboutKind.ENTITY, key="event.actor", span=TextSpan(text=raw))
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
            evidence={"signals": ["vague_pronoun", "arrival_event"], "tokens": sorted(tokens)},
            notes="Vague actor in arrival statement.",
        )
        return SchemaSelection(
            schemas=[
                SchemaHit(name="clarify.actor", score=0.92, about=about),
                SchemaHit(name="clarification_needed", score=0.75, about=about),
            ],
            ambiguities=[amb],
        )

    # --------------------------------------------------------------------------
    # 4) URL task intent
    # --------------------------------------------------------------------------
    if has_url(t):
        about = AmbiguityAbout(kind=AboutKind.INTENT, key="task.intent.link", span=TextSpan(text=raw))
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

    # --------------------------------------------------------------------------
    # 5) Timer duration unit underspecification
    # --------------------------------------------------------------------------
    has_numberish = any(tok.isdigit() for tok in tokens) or any(tok in {"ten", "five"} for tok in tokens)
    has_unit = any(u in tokens for u in {"s", "sec", "second", "seconds", "m", "min", "minute", "minutes", "h", "hour", "hours"})
    mentions_timerish = any(w in t for w in ["timer", "remind", "reminder", "in "])

    if mentions_timerish and has_numberish and not has_unit:
        about = AmbiguityAbout(kind=AboutKind.PARAMETER, key="timer.duration", span=TextSpan(text=raw))
        amb = Ambiguity(
            status=AmbiguityStatus.UNRESOLVED,
            about=about,
            type=AmbiguityType.UNDERSPECIFIED,
            candidates=[
                Candidate("minutes", 0.65),
                Candidate("seconds", 0.25),
                Candidate("hours", 0.10),
            ],
            resolution_policy=ResolutionPolicy.ASK_USER,
            ask=[
                ClarifyingQuestion(
                    q="Ten what — minutes or seconds?",
                    format=AskFormat.MULTICHOICE,
                    options=["minutes", "seconds"],
                )
            ],
            evidence={"signals": ["timerish", "number_without_unit"], "tokens": sorted(tokens)},
            notes="Duration unit missing.",
        )
        return SchemaSelection(
            schemas=[
                SchemaHit(name="clarify.duration_unit", score=0.9, about=about),
                SchemaHit(name="clarification_needed", score=0.7, about=about),
            ],
            ambiguities=[amb],
        )

    # --------------------------------------------------------------------------
    # 6) Broad uncertainty (goal/intent) — LAST among ambiguity rules
    # --------------------------------------------------------------------------
    if has_any_phrase(t, UNCERTAIN_PHRASES):
        about = AmbiguityAbout(kind=AboutKind.GOAL, key="user.goal", span=TextSpan(text=raw))
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

    # --------------------------------------------------------------------------
    # 7) Default
    # --------------------------------------------------------------------------
    about = AmbiguityAbout(kind=AboutKind.INTENT, key="user.intent", span=TextSpan(text=raw))
    return SchemaSelection(
        schemas=[SchemaHit(name="actionable_intent", score=0.7, about=about)],
        ambiguities=[],
    )

