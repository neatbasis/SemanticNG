from __future__ import annotations

from state_renormalization.contracts import HaltPayloadValidationError, HaltRecord
from state_renormalization.invariants import InvariantOutcome


def materialize_halt_record_from_invariant_outcome(
    *,
    stage: str,
    outcome: InvariantOutcome,
    halt_id: str,
    timestamp_iso: str,
) -> HaltRecord:
    """Convert a STOP invariant evaluation result into a canonical HaltRecord envelope."""
    if outcome.details is None or outcome.evidence is None:
        raise HaltPayloadValidationError("halt payload is malformed or incomplete")

    return HaltRecord.from_payload(
        HaltRecord.build_canonical_payload(
            halt_id=halt_id,
            stage=stage,
            invariant_id=outcome.invariant_id.value,
            reason=outcome.reason,
            details=dict(outcome.details),
            evidence=list(outcome.evidence),
            timestamp=timestamp_iso,
            retryability=bool(outcome.action_hints),
        )
    )
