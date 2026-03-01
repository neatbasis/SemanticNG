from __future__ import annotations

from pathlib import Path

import pytest

from state_renormalization.adapters.persistence import append_prediction_record_event, read_jsonl
from state_renormalization.contracts import CapabilityAdapterGate


def test_adapter_guard_requires_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction-records.jsonl"

    with pytest.raises(TypeError):
        append_prediction_record_event({"prediction_id": "pred:1"}, path=path)  # type: ignore[call-arg]

    assert not path.exists()


def test_adapter_guard_rejects_denied_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction-records.jsonl"

    with pytest.raises(PermissionError):
        append_prediction_record_event(
            {"prediction_id": "pred:1"},
            adapter_gate=CapabilityAdapterGate(invocation_id="invoke:1", allowed=False),
            path=path,
        )

    assert not path.exists()


def test_adapter_guard_allows_with_granted_policy_gate(tmp_path: Path) -> None:
    path = tmp_path / "prediction-records.jsonl"

    append_prediction_record_event(
        {"prediction_id": "pred:1", "scope_key": "scope:1"},
        adapter_gate=CapabilityAdapterGate(invocation_id="invoke:1", allowed=True),
        path=path,
    )

    rows = [row for _, row in read_jsonl(path)]
    assert len(rows) == 1
    assert rows[0]["event_kind"] == "prediction_record"
