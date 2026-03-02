from __future__ import annotations

from pathlib import Path

from state_renormalization.engine import replay_projection_analytics


def test_replay_accepts_legacy_prediction_and_repair_decision_event_kind(tmp_path: Path) -> None:
    prediction_log = tmp_path / "legacy-lineage.jsonl"
    prediction_log.write_text(
        "\n".join(
            [
                '{"event_kind":"prediction","prediction_id":"pred:1","scope_key":"turn:1","filtration_id":"conversation:c1","target_variable":"user_response_present","target_horizon_iso":"2026-02-13T00:00:00+00:00","expectation":0.2,"issued_at_iso":"2026-02-13T00:00:00+00:00"}',
                '{"event_kind":"repair_decision","repair_id":"repair:1","proposal_kind":"repair_proposal","decision":"accepted","resolved_at":"2026-02-13T00:00:01+00:00","lineage_ref":{"scope_key":"turn:1","prediction_id":"pred:1","correction_root_prediction_id":"pred:1"},"accepted_payload":{"prediction_id":"pred:1","scope_key":"turn:1","filtration_id":"conversation:c1","target_variable":"user_response_present","target_horizon_iso":"2026-02-13T00:00:00+00:00","expectation":0.2,"observed_value":1.0,"prediction_error":0.8,"absolute_error":0.8,"was_corrected":true,"correction_parent_prediction_id":"pred:1","correction_root_prediction_id":"pred:1","correction_revision":1,"issued_at_iso":"2026-02-13T00:00:00+00:00","compared_at_iso":"2026-02-13T00:00:01+00:00","corrected_at_iso":"2026-02-13T00:00:01+00:00"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    replay = replay_projection_analytics(prediction_log)

    assert replay.records_processed == 2
    assert replay.analytics_snapshot.correction_count == 1
    corrected = replay.projection_state.current_predictions["turn:1"]
    assert corrected.was_corrected is True
    assert corrected.correction_revision == 1
