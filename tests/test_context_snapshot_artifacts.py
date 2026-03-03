from __future__ import annotations

from pathlib import Path

from state_renormalization.adapters.persistence import (
    append_context_snapshot_event,
    append_jsonl,
    iter_projection_lineage_records,
)
from state_renormalization.contracts import CapabilityAdapterGate
from state_renormalization.engine import build_context_snapshot_artifact


def test_context_snapshot_hash_is_stable_for_same_as_of_and_records() -> None:
    records = [
        {
            "event_kind": "prior_interaction",
            "created_at_iso": "2026-02-13T00:00:00+00:00",
            "interaction_id": "int:1",
        },
        {
            "event_kind": "external_knowledge_digest",
            "created_at_iso": "2026-02-13T00:01:00+00:00",
            "digest_id": "dig:1",
        },
        {
            "event_kind": "external_knowledge_retrieval_output",
            "created_at_iso": "2026-02-13T00:02:00+00:00",
            "retrieval_id": "ret:1",
        },
    ]

    first = build_context_snapshot_artifact(records, as_of_iso="2026-02-13T00:02:00+00:00")
    second = build_context_snapshot_artifact(records, as_of_iso="2026-02-13T00:02:00+00:00")

    assert first.snapshot_hash == second.snapshot_hash
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_context_snapshot_selector_is_deterministic_at_fixed_as_of() -> None:
    records = [
        {
            "event_kind": "prior_interaction",
            "created_at_iso": "2026-02-13T00:00:00+00:00",
            "interaction_id": "int:1",
        },
        {
            "event_kind": "external_knowledge_digest",
            "created_at_iso": "2026-02-13T00:01:00+00:00",
            "digest_id": "dig:1",
        },
        {
            "event_kind": "external_knowledge_retrieval_output",
            "created_at_iso": "2026-02-13T00:02:00+00:00",
            "retrieval_id": "ret:1",
        },
        {
            "event_kind": "external_knowledge_digest",
            "created_at_iso": "2026-02-13T00:03:00+00:00",
            "digest_id": "dig:2",
        },
    ]

    snap = build_context_snapshot_artifact(records, as_of_iso="2026-02-13T00:02:00+00:00")

    assert [ref.artifact_kind for ref in snap.selected_artifact_refs] == [
        "prior_interaction",
        "external_knowledge_digest",
        "external_knowledge_retrieval_output",
    ]
    assert [ref.artifact_ref for ref in snap.selected_artifact_refs] == [
        "predictions.jsonl@1",
        "predictions.jsonl@2",
        "predictions.jsonl@3",
    ]


def test_context_snapshot_artifact_persists_append_only_for_replay(tmp_path: Path) -> None:
    log_path = tmp_path / "predictions.jsonl"
    records = [
        {
            "event_kind": "prior_interaction",
            "created_at_iso": "2026-02-13T00:00:00+00:00",
            "interaction_id": "int:1",
        },
        {
            "event_kind": "external_knowledge_digest",
            "created_at_iso": "2026-02-13T00:01:00+00:00",
            "digest_id": "dig:1",
        },
    ]
    for row in records:
        append_jsonl(log_path, row)

    snapshot = build_context_snapshot_artifact(records, as_of_iso="2026-02-13T00:01:00+00:00")
    append_context_snapshot_event(
        snapshot,
        adapter_gate=CapabilityAdapterGate(invocation_id="gate:context-snapshot", allowed=True),
        path=log_path,
    )

    replay_rows = list(iter_projection_lineage_records(log_path))
    persisted_snapshot = replay_rows[-1]

    assert persisted_snapshot["event_kind"] == "context_snapshot"
    assert persisted_snapshot["snapshot_hash"] == snapshot.snapshot_hash
    assert persisted_snapshot["selected_artifact_refs"] == [
        {
            "artifact_ref": "predictions.jsonl@1",
            "artifact_kind": "prior_interaction",
            "event_time": "2026-02-13T00:00:00+00:00",
        },
        {
            "artifact_ref": "predictions.jsonl@2",
            "artifact_kind": "external_knowledge_digest",
            "event_time": "2026-02-13T00:01:00+00:00",
        },
    ]
