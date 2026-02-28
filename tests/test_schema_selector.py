# tests/test_schema_selector.py
from __future__ import annotations

import inspect

import pytest

from state_renormalization.adapters.schema_selector import (
    BaseRule,
    SelectorContext,
    _legacy_naive_schema_selector,
    build_selector_context,
    naive_schema_selector,
    register_rule,
    RULE_REGISTRY,
    RULE_PHASES,
)
from state_renormalization.contracts import CaptureOutcome, CaptureStatus, SchemaHit, SchemaSelection


SELECTOR_FIXTURES: list[tuple[str | None, CaptureOutcome | None]] = [
    (None, CaptureOutcome(status=CaptureStatus.NO_RESPONSE)),
    ("", None),
    ("quit", None),
    ("they are coming", None),
    ("https://example.com", None),
    ("set timer for ten", None),
    ("maybe", None),
    ("turn on the lights", None),
    ("maybe https://example.com", None),
    ("they are coming maybe", None),
    ("set timer for ten maybe", None),
]


def test_no_response_yields_capture_clarification_ambiguity() -> None:
    sel = naive_schema_selector(text=None, error=CaptureOutcome(status=CaptureStatus.NO_RESPONSE))

    assert sel.schemas, "Expected schema hits"
    assert any(h.name.startswith("clarify.") for h in sel.schemas)

    assert sel.ambiguities, "Expected an ambiguity"
    a0 = sel.ambiguities[0]
    assert a0.status.value == "unresolved"
    assert a0.about.key == "channel.capture"


def test_schema_selector_signature_is_channel_agnostic() -> None:
    sig = inspect.signature(naive_schema_selector)
    assert "ha_error" not in sig.parameters, "selector must not depend on Home Assistant naming"
    # choose one canonical name and enforce it:
    assert "error" in sig.parameters, "expected keyword 'error' parameter"


@pytest.mark.parametrize(
    ("text", "error", "expected_schemas", "expected_about_key"),
    [
        ("", None, ["clarify.empty_input"], "cli.input.empty"),
        ("quit", None, ["exit_intent"], "user.intent.exit"),
        ("they are coming", None, ["clarify.actor", "clarification_needed"], "event.actor"),
        ("https://example.com", None, ["clarify.link_intent", "clarification_needed"], "task.intent.link"),
        ("set timer for ten", None, ["clarify.duration_unit", "clarification_needed"], "timer.duration"),
        ("maybe", None, ["clarify.goal", "clarification_needed"], "user.goal"),
        ("turn on the lights", None, ["actionable_intent"], "user.intent"),
    ],
)
def test_schema_selector_regression_snapshots(
    text: str,
    error: CaptureOutcome | None,
    expected_schemas: list[str],
    expected_about_key: str,
) -> None:
    sel = naive_schema_selector(text=text, error=error)

    assert [hit.name for hit in sel.schemas] == expected_schemas
    assert all(hit.about is not None for hit in sel.schemas)
    assert sel.schemas[0].about is not None
    assert sel.schemas[0].about.key == expected_about_key


@pytest.mark.parametrize(("text", "error"), SELECTOR_FIXTURES)
def test_refactored_selector_matches_legacy_snapshots(text: str | None, error: CaptureOutcome | None) -> None:
    legacy = _legacy_naive_schema_selector(text=text, error=error)
    refactored = naive_schema_selector(text=text, error=error)

    assert refactored.model_dump(mode="json") == legacy.model_dump(mode="json")


def test_build_selector_context_normalizes_once_and_exposes_signals() -> None:
    ctx = build_selector_context("They're coming in ten", error=None)

    assert ctx.raw == "They're coming in ten"
    assert ctx.normalized == "they are coming in ten"
    assert "they" in ctx.tokens
    assert ctx.metadata["has_numberish"] is True
    assert ctx.metadata["mentions_timerish"] is True


def test_rule_phases_and_rule_units_are_structured_for_extension() -> None:
    assert RULE_PHASES == ("hard-stop", "ambiguity-disambiguation", "fallback")

    for phase in RULE_PHASES:
        phase_rules = RULE_REGISTRY.phase_rules(phase=phase)
        assert phase_rules, f"Expected rules for phase {phase}"
        for rule in phase_rules:
            assert isinstance(rule.name, str) and rule.name
            assert callable(rule.applies)
            assert callable(rule.emit)


def test_variant_addition_can_be_localized_to_a_single_phase_rule() -> None:
    class KitchenLightsRule(BaseRule):
        name: str = "kitchen_lights"

        def applies(self, ctx: SelectorContext) -> bool:
            return "kitchen" in ctx.tokens and "lights" in ctx.tokens

        def emit(self, ctx: SelectorContext) -> SchemaSelection:
            return SchemaSelection(
                schemas=[SchemaHit(name="lights.kitchen", score=0.99, about=None)],
                ambiguities=[],
            )

    fallback = RULE_REGISTRY._rules_by_domain["home-assistant"]["fallback"]
    original = list(fallback)
    try:
        register_rule(
            phase="fallback",
            rule=KitchenLightsRule(name="kitchen_lights"),
            domain="home-assistant",
            prepend=True,
        )

        localized = naive_schema_selector("turn on kitchen lights", error=None, domain="home-assistant")
        baseline = naive_schema_selector("turn on bedroom lights", error=None, domain="home-assistant")
        default_domain = naive_schema_selector("turn on kitchen lights", error=None)

        assert [hit.name for hit in localized.schemas] == ["lights.kitchen"]
        assert [hit.name for hit in baseline.schemas] == ["actionable_intent"]
        assert [hit.name for hit in default_domain.schemas] == ["actionable_intent"]
    finally:
        fallback[:] = original


def test_regression_stays_stable_as_non_matching_rules_grow() -> None:
    class NeverAppliesRule(BaseRule):
        name: str = "never"

        def applies(self, ctx: SelectorContext) -> bool:
            return False

        def emit(self, ctx: SelectorContext) -> SchemaSelection:
            raise AssertionError("should never emit")

    snapshot_before = [
        naive_schema_selector(text=text, error=error).model_dump(mode="json")
        for text, error in SELECTOR_FIXTURES
    ]

    fallback = RULE_REGISTRY._rules_by_domain["default"]["fallback"]
    original = list(fallback)
    try:
        for i in range(25):
            register_rule(phase="fallback", rule=NeverAppliesRule(name=f"never-{i}"))

        snapshot_after = [
            naive_schema_selector(text=text, error=error).model_dump(mode="json")
            for text, error in SELECTOR_FIXTURES
        ]
    finally:
        fallback[:] = original

    assert snapshot_after == snapshot_before
