# tests/test_schema_selector.py
from __future__ import annotations

import inspect

import pytest

from state_renormalization.adapters.schema_selector import _legacy_naive_schema_selector, naive_schema_selector
from state_renormalization.contracts import CaptureOutcome, CaptureStatus


SELECTOR_FIXTURES: list[tuple[str | None, CaptureOutcome | None]] = [
    (None, CaptureOutcome(status=CaptureStatus.NO_RESPONSE)),
    ("", None),
    ("quit", None),
    ("they are coming", None),
    ("https://example.com", None),
    ("set timer for ten", None),
    ("maybe", None),
    ("turn on the lights", None),
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
