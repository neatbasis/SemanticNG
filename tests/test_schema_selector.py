# tests/test_schema_selector.py
from __future__ import annotations

import inspect
from state_renormalization.adapters.schema_selector import naive_schema_selector
from state_renormalization.contracts import CaptureOutcome, CaptureStatus

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

