from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl, iter_projection_lineage_records
from state_renormalization.contracts import HaltRecord


def _canonical_halt_payload(halt_id: str, *, timestamp: str) -> dict[str, object]:
    return HaltRecord(
        halt_id=halt_id,
        stage="gate:pre_consume",
        invariant_id="prediction_availability.v1",
        reason="missing prediction",
        details={"scope": "turn:1"},
        evidence=[{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        retryability=True,
        timestamp=timestamp,
    ).to_canonical_payload()


def test_iter_projection_lineage_records_filters_mixed_jsonl_rows(tmp_path: Path) -> None:
    path = tmp_path / "mixed.jsonl"

    prediction_row = {"event_kind": "prediction", "prediction_id": "pred:1", "scope_key": "turn:1"}
    canonical_halt = _canonical_halt_payload("halt:1", timestamp="2026-02-14T00:00:00+00:00")
    unknown_event = {"event_kind": "turn_summary", "turn_index": 1}
    malformed_halt_like = {
        "halt_id": "halt:bad",
        "stage": "gate:pre_consume",
        "reason": "missing invariant + payload fields",
    }
    prediction_record_row = {
        "event_kind": "prediction_record",
        "prediction_id": "pred:2",
        "scope_key": "turn:2",
    }

    for row in (
        prediction_row,
        canonical_halt,
        unknown_event,
        malformed_halt_like,
        prediction_record_row,
    ):
        append_jsonl(path, row)

    lineage = list(iter_projection_lineage_records(path))

    assert lineage == [prediction_row, canonical_halt, prediction_record_row]


def test_iter_projection_lineage_records_preserves_append_only_order(tmp_path: Path) -> None:
    path = tmp_path / "ordered.jsonl"

    rows = [
        {"event_kind": "prediction", "prediction_id": "pred:1"},
        {"event_kind": "prediction_record", "prediction_id": "pred:2"},
        _canonical_halt_payload("halt:1", timestamp="2026-02-14T00:00:00+00:00"),
        {"event_kind": "prediction", "prediction_id": "pred:3"},
        _canonical_halt_payload("halt:2", timestamp="2026-02-14T00:00:01+00:00"),
    ]

    for row in rows:
        append_jsonl(path, row)

    lineage = list(iter_projection_lineage_records(path))

    ids_in_order = [row.get("prediction_id", row.get("halt_id")) for row in lineage]
    assert ids_in_order == ["pred:1", "pred:2", "halt:1", "pred:3", "halt:2"]


def test_iter_projection_lineage_records_includes_only_rehydratable_halts(tmp_path: Path) -> None:
    path = tmp_path / "rehydration.jsonl"

    valid_canonical_halt = _canonical_halt_payload(
        "halt:valid", timestamp="2026-02-14T00:00:00+00:00"
    )
    invalid_halt_like = {
        "halt_id": "halt:invalid",
        "stage": "gate:pre_consume",
        "invariant_id": "prediction_availability.v1",
        "reason": "missing details/evidence/retryability/timestamp",
    }

    append_jsonl(path, invalid_halt_like)
    append_jsonl(path, valid_canonical_halt)

    lineage = list(iter_projection_lineage_records(path))

    assert lineage == [valid_canonical_halt]
    assert HaltRecord.from_payload(lineage[0]).to_canonical_payload() == valid_canonical_halt


def test_iter_projection_lineage_records_skips_malformed_json_lines_and_non_object_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "malformed.jsonl"
    canonical_halt = _canonical_halt_payload("halt:ok", timestamp="2026-02-14T00:00:00+00:00")
    path.write_text(
        "\n".join(
            [
                '{"event_kind":"prediction_record","prediction_id":"pred:ok","scope_key":"turn:1"}',
                '{"event_kind":"prediction_record",',  # malformed JSON
                "[]",
                '"string"',
                json.dumps(canonical_halt),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    lineage = list(iter_projection_lineage_records(path))
    assert [row.get("prediction_id", row.get("halt_id")) for row in lineage] == [
        "pred:ok",
        "halt:ok",
    ]


def test_iter_projection_lineage_records_includes_ask_outbox_events_for_replay(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ask-outbox.jsonl"

    request = {
        "event_kind": "ask_outbox_request",
        "request_id": "ask:1",
        "scope": "mission_loop:start",
        "reason": "human recruitment requested by intervention lifecycle",
        "evidence_refs": [{"kind": "intervention_request", "ref": "hitl:1"}],
        "created_at_iso": "2026-02-14T00:00:00+00:00",
    }
    response = {
        "event_kind": "ask_outbox_response",
        "request_id": "ask:1",
        "scope": "mission_loop:start",
        "reason": "operator timeout",
        "evidence_refs": [{"kind": "intervention_request", "ref": "hitl:1"}],
        "created_at_iso": "2026-02-14T00:00:00+00:00",
        "responded_at_iso": "2026-02-14T00:00:05+00:00",
        "status": "timeout",
        "escalation": False,
    }

    append_jsonl(path, request)
    append_jsonl(path, response)

    lineage_once = list(iter_projection_lineage_records(path))
    lineage_twice = list(iter_projection_lineage_records(path))

    assert lineage_once == lineage_twice == [request, response]
