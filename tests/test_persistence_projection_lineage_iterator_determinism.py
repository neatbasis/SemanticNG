from __future__ import annotations

from pathlib import Path

import pytest

from state_renormalization.adapters.persistence import append_jsonl, iter_projection_lineage_records
from state_renormalization.contracts import HaltRecord


@pytest.fixture
def mixed_projection_rows() -> list[dict[str, object]]:
    valid_halt_payload = HaltRecord(
        halt_id="halt:canonical:accepted",
        stage="gate:pre_consume",
        invariant_id="prediction_availability.v1",
        reason="missing prediction",
        details={"scope": "turn:7"},
        evidence=[{"kind": "jsonl", "ref": "predictions.jsonl@4"}],
        retryability=True,
        timestamp="2026-02-14T00:00:00+00:00",
    ).to_canonical_payload()

    malformed_halt_like = {
        "halt_id": "halt:canonical:malformed",
        "stage": "gate:pre_consume",
        "reason": "looks-like-halt-but-missing-required-fields",
    }

    return [
        {"event_kind": "prediction_record", "prediction_id": "pred:r-01", "scope_key": "turn:1"},
        {"event_kind": "system_trace", "trace_id": "trace:drop-01"},
        valid_halt_payload,
        {"event_kind": "prediction", "prediction_id": "pred:p-02", "scope_key": "turn:2"},
        malformed_halt_like,
        {"event_kind": "user_message", "message_id": "msg:drop-02"},
        {"event_kind": "prediction_record", "prediction_id": "pred:r-03", "scope_key": "turn:3"},
        {"event_kind": "prediction", "prediction_id": "pred:p-04", "scope_key": "turn:4"},
    ]


def test_iter_projection_lineage_records_deterministic_filtering_and_stability(
    tmp_path: Path,
    mixed_projection_rows: list[dict[str, object]],
) -> None:
    path = tmp_path / "projection_lineage_mixed.jsonl"

    for row in mixed_projection_rows:
        append_jsonl(path, row)

    first_read = list(iter_projection_lineage_records(path))
    second_read = list(iter_projection_lineage_records(path))

    expected = [
        mixed_projection_rows[0],
        mixed_projection_rows[2],
        mixed_projection_rows[3],
        mixed_projection_rows[6],
        mixed_projection_rows[7],
    ]

    # 1) Append-only order is preserved for all included lineage rows.
    assert first_read == expected

    # 2) Rows tagged with lineage event kinds are always included.
    assert all(
        row in first_read
        for row in mixed_projection_rows
        if row.get("event_kind") in {"prediction_record", "prediction"}
    )

    # 3) Canonical halt payload rows are included only when HaltRecord validates.
    assert mixed_projection_rows[2] in first_read
    assert (
        HaltRecord.from_payload(mixed_projection_rows[2]).to_canonical_payload()
        == mixed_projection_rows[2]
    )

    # 4) Non-lineage and malformed halt-like rows are excluded deterministically.
    assert mixed_projection_rows[1] not in first_read
    assert mixed_projection_rows[4] not in first_read
    assert mixed_projection_rows[5] not in first_read

    # 5) Result set is stable across repeated reads.
    assert second_read == first_read
