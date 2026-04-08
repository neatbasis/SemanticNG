from __future__ import annotations

from typing import Any

import pytest

from state_renormalization.adapters.halt_boundary import (
    materialize_halt_record_from_invariant_outcome,
)
from state_renormalization.contracts import EvidenceRef, HaltPayloadValidationError, HaltRecord
from state_renormalization.invariants import Flow, InvariantId, InvariantOutcome, Validity


def _stop_outcome(*, details: dict[str, Any] | None = None) -> InvariantOutcome:
    return InvariantOutcome(
        invariant_id=InvariantId.PREDICTION_AVAILABILITY,
        passed=False,
        reason="missing prediction",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="no_current_prediction",
        evidence=(EvidenceRef(kind="scope", ref="test"),),
        details={} if details is None else details,
        action_hints=({"kind": "rebuild_view", "scope": "test"},),
    )


def test_halt_boundary_materializes_canonical_halt_record_from_invariant_outcome() -> None:
    outcome = _stop_outcome(details={"message": "missing prediction"})

    halt = materialize_halt_record_from_invariant_outcome(
        stage="pre-decision:pre_consume",
        outcome=outcome,
        halt_id="halt:test",
        timestamp_iso="2026-04-08T10:00:00+00:00",
    )

    assert isinstance(halt, HaltRecord)
    assert isinstance(outcome, InvariantOutcome)
    assert not isinstance(outcome, HaltRecord)
    assert set(halt.to_canonical_payload().keys()) == set(HaltRecord.required_payload_fields())


def test_halt_boundary_rejects_incomplete_invariant_outcome_payload() -> None:
    outcome = _stop_outcome(details={"message": "missing prediction"})
    object.__setattr__(outcome, "details", None)

    with pytest.raises(HaltPayloadValidationError, match="malformed or incomplete"):
        materialize_halt_record_from_invariant_outcome(
            stage="pre-decision:pre_consume",
            outcome=outcome,
            halt_id="halt:test",
            timestamp_iso="2026-04-08T10:00:00+00:00",
        )
