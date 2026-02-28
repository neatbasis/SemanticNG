# tests/test_persistence_jsonl.py
from __future__ import annotations

import json

import pytest
from pathlib import Path

from state_renormalization.adapters.persistence import append_halt, append_jsonl, read_halt_record, read_jsonl
from state_renormalization.contracts import CapabilityAdapterGate, HaltRecord
from state_renormalization.engine import to_jsonable_episode


TEST_GATE = CapabilityAdapterGate(invocation_id="invoke:test", allowed=True)


def test_append_and_read_jsonl_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"

    append_jsonl(p, {"kind": "x", "n": 1})
    append_jsonl(p, {"kind": "x", "n": 2})

    rows = [rec for _, rec in read_jsonl(p)]
    assert rows == [{"kind": "x", "n": 1}, {"kind": "x", "n": 2}]

    # sanity: file is valid json-per-line
    raw_lines = p.read_text(encoding="utf-8").splitlines()
    for ln in raw_lines:
        json.loads(ln)


def test_append_halt_jsonl_roundtrip_and_evidence_ref_format(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    halt = HaltRecord(
        halt_id="halt:1",
        stage="post_write",
        invariant_id="evidence_link_completeness.v1",
        reason="x",
        details={"message": "x", "context": {"gate": "post_write"}},
        evidence=[{"kind": "scope", "ref": "scope:test"}],
        retryability=True,
        timestamp="2026-02-13T00:00:00+00:00",
    )

    ref = append_halt(p, halt, adapter_gate=TEST_GATE)

    (meta, rec), = list(read_jsonl(p))
    assert rec["halt_id"] == "halt:1"
    assert rec["invariant_id"] == "evidence_link_completeness.v1"
    assert rec["details"] == {"message": "x", "context": {"gate": "post_write"}}
    assert rec["evidence"] == [{"kind": "scope", "ref": "scope:test"}]
    assert rec["retryability"] is True
    assert rec["timestamp"] == "2026-02-13T00:00:00+00:00"
    assert rec["stage"] == "post_write"
    assert set(rec.keys()) == set(HaltRecord.required_payload_fields())
    assert meta["lineno"] == 1
    assert ref == {"kind": "jsonl", "ref": "halts.jsonl@1"}
    assert "@" in ref["ref"]
    file_name, line_no = ref["ref"].split("@", 1)
    assert file_name == "halts.jsonl"
    assert line_no == "1"


def test_append_jsonl_propagates_stable_ids_to_nested_events(tmp_path: Path) -> None:
    p = tmp_path / "events.jsonl"

    append_jsonl(
        p,
        {
            "kind": "episode",
            "stable_ids": {
                "feature_id": "feat_1",
                "scenario_id": "scn_1",
                "step_id": "stp_1",
            },
            "events": [
                {"kind": "step", "name": "Given x"},
                {"kind": "decision", "name": "choose y"},
            ],
        },
    )

    (_, rec), = list(read_jsonl(p))
    assert rec["feature_id"] == "feat_1"
    assert rec["events"][0]["feature_id"] == "feat_1"
    assert rec["events"][0]["scenario_id"] == "scn_1"
    assert rec["events"][0]["step_id"] == "stp_1"
    assert rec["events"][1]["feature_id"] == "feat_1"


def test_append_jsonl_persists_episode_observer(make_episode, tmp_path: Path) -> None:
    p = tmp_path / "episodes.jsonl"
    ep = make_episode()

    append_jsonl(p, to_jsonable_episode(ep))

    (_, rec), = list(read_jsonl(p))
    assert rec["observer"]["role"] == "assistant"
    assert "baseline.dialog" in rec["observer"]["capabilities"]


def test_append_jsonl_propagates_stable_ids_to_embedding_and_ontology_records(tmp_path: Path) -> None:
    p = tmp_path / "records.jsonl"

    append_jsonl(
        p,
        {
            "kind": "episode",
            "stable_ids": {
                "feature_id": "feat_1",
                "scenario_id": "scn_1",
                "step_id": "stp_1",
            },
            "embedding": {"model": "text-embedding-3"},
            "ontology_alignment": {"concept": "Event"},
            "elasticsearch_documents": [
                {"index": "semanticng-events"},
            ],
        },
    )

    (_, rec), = list(read_jsonl(p))
    assert rec["embedding"]["feature_id"] == "feat_1"
    assert rec["ontology_alignment"]["scenario_id"] == "scn_1"
    assert rec["elasticsearch_documents"][0]["step_id"] == "stp_1"


def test_append_halt_reprojects_alias_payload_to_canonical_shape(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    payload = {
        "halt_id": "halt:exact",
        "stable_halt_id": "halt:exact",
        "stage": "pre-decision:post_write",
        "invariant_id": "evidence_link_completeness.v1",
        "violated_invariant_id": "evidence_link_completeness.v1",
        "reason": "missing evidence",
        "details": {"message": "missing evidence", "contract": "halt"},
        "evidence": [{"kind": "scope", "ref": "scope:test"}],
        "evidence_refs": [{"kind": "scope", "ref": "scope:test"}],
        "retryability": True,
        "retryable": True,
        "timestamp": "2026-02-13T00:00:00+00:00",
        "timestamp_iso": "2026-02-13T00:00:00+00:00",
    }

    append_halt(p, payload, adapter_gate=TEST_GATE)

    (_, rec), = list(read_jsonl(p))
    assert set(rec.keys()) == set(HaltRecord.required_payload_fields())
    assert rec["halt_id"] == payload["halt_id"]
    assert rec["invariant_id"] == payload["invariant_id"]
    assert rec["evidence"] == payload["evidence"]
    assert rec["retryability"] is True


def test_append_halt_rejects_missing_explainability_fields(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    with pytest.raises(Exception):
        append_halt(
            p,
            {
                "halt_id": "halt:missing-evidence",
                "stage": "pre-decision",
                "invariant_id": "prediction_availability.v1",
                "reason": "missing evidence",
                "details": {"message": "missing evidence"},
                "retryability": True,
                "timestamp": "2026-02-13T00:00:00+00:00",
            },
            adapter_gate=TEST_GATE,
        )


def test_append_halt_rejects_incomplete_payloads(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    with pytest.raises(Exception):
        append_halt(
            p,
            {
                "halt_id": "halt:incomplete",
                "stage": "pre-decision",
                "invariant_id": "prediction_availability.v1",
                "reason": "missing timestamp",
                "details": {"message": "missing timestamp"},
                "evidence": [{"kind": "scope", "ref": "scope:test"}],
                "retryability": True,
            },
            adapter_gate=TEST_GATE,
        )


def test_append_halt_rejects_conflicting_alias_fields(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    with pytest.raises(Exception):
        append_halt(
            p,
            {
                "halt_id": "halt:canonical",
                "stable_halt_id": "halt:alias-mismatch",
                "stage": "pre-decision",
                "invariant_id": "prediction_availability.v1",
                "reason": "mismatch",
                "details": {"message": "mismatch"},
                "evidence": [{"kind": "scope", "ref": "scope:test"}],
                "retryability": True,
                "timestamp": "2026-02-13T00:00:00+00:00",
            },
            adapter_gate=TEST_GATE,
        )


def test_append_halt_flow_parity_across_stop_and_continue_artifacts(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    stop_payload = {
        "halt_id": "halt:stop",
        "stage": "pre-decision:post_write",
        "invariant_id": "evidence_link_completeness.v1",
        "reason": "stop branch",
        "details": {"message": "stop branch", "flow": "stop"},
        "evidence": [{"kind": "scope", "ref": "scope:test"}],
        "retryability": True,
        "timestamp": "2026-02-13T00:00:00+00:00",
    }
    continue_payload = {
        "halt_id": "halt:continue",
        "stable_halt_id": "halt:continue",
        "stage": "pre-decision:pre_consume",
        "invariant_id": "prediction_availability.v1",
        "violated_invariant_id": "prediction_availability.v1",
        "reason": "continue parity",
        "details": {"message": "continue parity", "flow": "continue"},
        "evidence": [{"kind": "scope", "ref": "scope:test"}],
        "evidence_refs": [{"kind": "scope", "ref": "scope:test"}],
        "retryability": False,
        "retryable": False,
        "timestamp": "2026-02-13T00:00:01+00:00",
        "timestamp_iso": "2026-02-13T00:00:01+00:00",
    }

    append_halt(p, stop_payload, adapter_gate=TEST_GATE)
    append_halt(p, continue_payload, adapter_gate=TEST_GATE)

    rows = [rec for _, rec in read_jsonl(p)]
    stop_rec, continue_rec = rows

    for rec in (stop_rec, continue_rec):
        assert set(rec.keys()) == set(HaltRecord.required_payload_fields())
        assert isinstance(rec["details"], dict)
        assert isinstance(rec["retryability"], bool)
        assert isinstance(rec["timestamp"], str)


def test_append_halt_roundtrip_reprojects_required_fields_without_mutation(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    payload = {
        "halt_id": "halt:roundtrip",
        "stage": "pre-decision:pre_consume",
        "invariant_id": "prediction_availability.v1",
        "reason": "roundtrip",
        "details": {"message": "roundtrip", "attempt": 1},
        "evidence": [{"kind": "scope", "ref": "scope:test"}],
        "retryability": False,
        "timestamp": "2026-02-13T00:00:00+00:00",
    }

    append_halt(p, payload, adapter_gate=TEST_GATE)
    (_, persisted), = list(read_jsonl(p))
    reprojected = HaltRecord.from_payload(persisted).to_canonical_payload()

    assert set(reprojected.keys()) == set(HaltRecord.required_payload_fields())
    assert reprojected["invariant_id"] == payload["invariant_id"]
    assert reprojected["details"] == payload["details"]
    assert reprojected["evidence"] == payload["evidence"]


def test_append_halt_round_trip_preserves_halt_payload_field_integrity(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    payload = {
        "stable_halt_id": "halt:integrity",
        "stage": "pre-decision:post_write",
        "violated_invariant_id": "evidence_link_completeness.v1",
        "reason": "integrity",
        "details": {"message": "integrity", "attempt": 2},
        "evidence_refs": [{"kind": "scope", "ref": "scope:test"}],
        "retryable": True,
        "timestamp_iso": "2026-02-13T00:00:02+00:00",
    }

    append_halt(p, payload, adapter_gate=TEST_GATE)
    (_, persisted), = list(read_jsonl(p))
    roundtrip = HaltRecord.from_payload(persisted).to_canonical_payload()

    assert persisted == roundtrip
    assert roundtrip == {
        "halt_id": "halt:integrity",
        "stage": "pre-decision:post_write",
        "invariant_id": "evidence_link_completeness.v1",
        "reason": "integrity",
        "details": {"message": "integrity", "attempt": 2},
        "evidence": [{"kind": "scope", "ref": "scope:test"}],
        "retryability": True,
        "timestamp": "2026-02-13T00:00:02+00:00",
    }


def test_halt_reprojection_fails_closed_for_malformed_payload(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    append_jsonl(
        p,
        {
            "halt_id": "halt:bad",
            "stage": "pre-decision:pre_consume",
            "reason": "missing invariant and details",
            "evidence": [{"kind": "scope", "ref": "scope:test"}],
            "retryability": True,
            "timestamp": "2026-02-13T00:00:00+00:00",
        },
    )

    (_, malformed), = list(read_jsonl(p))
    with pytest.raises(Exception):
        HaltRecord.from_payload(malformed)




def test_append_halt_round_trip_reload_preserves_explainability_payload(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    payload = {
        "halt_id": "halt:explainability",
        "stage": "pre-decision:post_write",
        "invariant_id": "evidence_link_completeness.v1",
        "reason": "explainability fields",
        "details": {
            "message": "explainability fields",
            "debug": {"scope": "scope:test", "attempt": 4},
        },
        "evidence": [
            {"kind": "scope", "ref": "scope:test"},
            {"kind": "prediction_key", "ref": "scope:test"},
        ],
        "retryability": True,
        "timestamp": "2026-02-13T00:00:04+00:00",
    }

    append_halt(p, payload, adapter_gate=TEST_GATE)
    (_, persisted), = list(read_jsonl(p))
    reloaded = read_halt_record(persisted)

    assert reloaded.to_canonical_payload() == payload
    assert reloaded.details == payload["details"]
    assert [item.model_dump(mode="json") for item in reloaded.evidence] == payload["evidence"]

def test_append_halt_round_trip_preserves_all_canonical_and_stable_id_fields(tmp_path: Path) -> None:
    p = tmp_path / "halts.jsonl"

    payload = {
        "feature_id": "feat_1",
        "scenario_id": "scn_1",
        "step_id": "stp_1",
        "stable_halt_id": "halt:stable",
        "stage": "pre-decision:post_write",
        "violated_invariant_id": "evidence_link_completeness.v1",
        "reason": "stable roundtrip",
        "details": {"message": "stable roundtrip", "attempt": 3},
        "evidence_refs": [{"kind": "scope", "ref": "scope:test"}],
        "retryable": False,
        "timestamp_iso": "2026-02-13T00:00:03+00:00",
    }

    append_halt(p, payload, adapter_gate=TEST_GATE)

    (_, rec), = list(read_jsonl(p))
    canonical = HaltRecord.from_payload(payload).to_canonical_payload()

    assert rec == {
        "feature_id": "feat_1",
        "scenario_id": "scn_1",
        "step_id": "stp_1",
        **canonical,
    }
