from __future__ import annotations

import pytest

from state_renormalization.contracts import HaltRecord


def test_halt_record_required_payload_fields_declared() -> None:
    assert HaltRecord.required_payload_fields() == (
        "halt_id",
        "stage",
        "invariant_id",
        "reason",
        "details",
        "evidence",
        "retryability",
        "timestamp",
    )


def test_halt_record_rejects_missing_required_field() -> None:
    with pytest.raises(Exception):
        HaltRecord.model_validate(
            {
                "halt_id": "halt:1",
                "stage": "pre-decision:pre_consume",
                "invariant_id": "prediction_availability.v1",
                "reason": "missing timestamp",
                "details": {"message": "missing timestamp"},
                "evidence": [{"kind": "scope", "ref": "scope:test"}],
                "retryability": True,
            }
        )


def test_halt_record_rejects_conflicting_alias_values() -> None:
    with pytest.raises(Exception):
        HaltRecord.model_validate(
            {
                "halt_id": "halt:canonical",
                "stable_halt_id": "halt:other",
                "stage": "pre-decision:pre_consume",
                "invariant_id": "prediction_availability.v1",
                "reason": "alias mismatch",
                "details": {"message": "alias mismatch"},
                "evidence": [{"kind": "scope", "ref": "scope:test"}],
                "retryability": True,
                "timestamp": "2026-02-13T00:00:00+00:00",
            }
        )


def test_halt_record_rejects_incomplete_evidence_item() -> None:
    with pytest.raises(Exception):
        HaltRecord.model_validate(
            {
                "halt_id": "halt:1",
                "stage": "pre-decision:pre_consume",
                "invariant_id": "prediction_availability.v1",
                "reason": "bad evidence",
                "details": {"message": "bad evidence"},
                "evidence": [{"kind": "scope", "ref": ""}],
                "retryability": True,
                "timestamp": "2026-02-13T00:00:00+00:00",
            }
        )


def test_halt_record_rejects_missing_details_field() -> None:
    with pytest.raises(Exception):
        HaltRecord.model_validate(
            {
                "halt_id": "halt:1",
                "stage": "pre-decision:pre_consume",
                "invariant_id": "prediction_availability.v1",
                "reason": "details missing",
                "evidence": [{"kind": "scope", "ref": "scope:test"}],
                "retryability": True,
                "timestamp": "2026-02-13T00:00:00+00:00",
            }
        )
