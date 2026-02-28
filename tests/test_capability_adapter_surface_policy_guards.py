from __future__ import annotations

from pathlib import Path

import pytest

from state_renormalization.adapters.persistence import (
    append_halt,
    append_prediction,
    append_prediction_event,
    read_jsonl,
)
from state_renormalization.contracts import CapabilityAdapterGate, HaltRecord


def test_append_prediction_requires_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction.jsonl"
    with pytest.raises(TypeError):
        append_prediction(path=path, record={"prediction_id": "pred:1"})  # type: ignore[call-arg]


def test_append_prediction_event_rejects_denied_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction-event.jsonl"
    with pytest.raises(PermissionError):
        append_prediction_event(
            {"prediction_id": "pred:1"},
            adapter_gate=CapabilityAdapterGate(invocation_id="invoke:1", allowed=False),
            path=path,
        )

    assert not path.exists()


def test_append_prediction_event_allows_with_granted_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction-event.jsonl"
    append_prediction_event(
        {"prediction_id": "pred:1", "scope_key": "scope:1"},
        adapter_gate=CapabilityAdapterGate(invocation_id="invoke:1", allowed=True),
        path=path,
    )

    rows = [row for _, row in read_jsonl(path)]
    assert rows[0]["event_kind"] == "prediction"


def test_append_halt_rejects_denied_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "halts.jsonl"
    halt = HaltRecord(
        halt_id="halt:1",
        stage="pre-decision",
        invariant_id="prediction_availability.v1",
        reason="denied",
        details={"message": "denied"},
        evidence=[{"kind": "scope", "ref": "scope:test"}],
        retryability=True,
        timestamp="2026-02-13T00:00:00+00:00",
    )
    with pytest.raises(PermissionError):
        append_halt(
            path,
            halt,
            adapter_gate=CapabilityAdapterGate(invocation_id="invoke:1", allowed=False),
        )

    assert not path.exists()
