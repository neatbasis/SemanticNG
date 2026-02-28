from __future__ import annotations

from state_renormalization.contracts import AskOutboxRequestArtifact, AskOutboxResponseArtifact


def test_ask_outbox_request_contract_has_canonical_fields() -> None:
    request = AskOutboxRequestArtifact(
        request_id="ask:1",
        scope="mission_loop:start",
        reason="needs human check",
        evidence_refs=[{"kind": "intervention_request", "ref": "hitl:1"}],
        created_at_iso="2026-02-13T00:00:00+00:00",
    )

    payload = request.model_dump(mode="json")
    assert payload["event_kind"] == "ask_outbox_request"
    assert payload["request_id"] == "ask:1"
    assert payload["scope"] == "mission_loop:start"


def test_ask_outbox_response_contract_has_canonical_fields() -> None:
    response = AskOutboxResponseArtifact(
        request_id="ask:1",
        scope="mission_loop:start",
        reason="operator escalation",
        evidence_refs=[{"kind": "intervention_request", "ref": "hitl:1"}],
        created_at_iso="2026-02-13T00:00:00+00:00",
        responded_at_iso="2026-02-13T00:00:05+00:00",
        status="escalate",
        escalation=True,
    )

    payload = response.model_dump(mode="json")
    assert payload["event_kind"] == "ask_outbox_response"
    assert payload["status"] == "escalate"
    assert payload["escalation"] is True
