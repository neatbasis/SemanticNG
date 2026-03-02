from __future__ import annotations

from state_renormalization.contracts import RepairProposalEvent, RepairResolutionEvent, RepairResolution


def test_repair_proposal_accepts_legacy_field_aliases() -> None:
    proposal = RepairProposalEvent.model_validate(
        {
            "event_kind": "repair_proposal",
            "repair_id": "repair:legacy:1",
            "proposed_at": "2026-02-13T00:00:01+00:00",
            "reason": "legacy payload",
            "invariant_id": "prediction_outcome_binding.v1",
            "lineage_ref": {
                "scope_key": "turn:1",
                "prediction_id": "pred:1",
                "correction_root_prediction_id": "pred:1",
            },
            "candidate_prediction": {
                "prediction_id": "pred:1",
                "scope_key": "turn:1",
                "filtration_id": "conversation:c1",
                "target_variable": "user_response_present",
                "target_horizon_iso": "2026-02-13T00:00:00+00:00",
                "expectation": 0.2,
                "issued_at_iso": "2026-02-13T00:00:00+00:00",
            },
            "outcome": {
                "prediction_id": "pred:1",
                "observed_outcome": 1.0,
                "error_metric": 0.8,
                "absolute_error": 0.8,
                "recorded_at": "2026-02-13T00:00:01+00:00",
            },
        }
    )

    assert proposal.proposed_at_iso == "2026-02-13T00:00:01+00:00"
    assert proposal.proposed_prediction.prediction_id == "pred:1"


def test_repair_resolution_accepts_legacy_field_aliases() -> None:
    resolution = RepairResolutionEvent.model_validate(
        {
            "event_kind": "repair_resolution",
            "repair_id": "repair:legacy:1",
            "proposal_kind": "repair_proposal",
            "decision": RepairResolution.ACCEPTED,
            "resolved_at": "2026-02-13T00:00:01+00:00",
            "lineage_ref": {
                "scope_key": "turn:1",
                "prediction_id": "pred:1",
                "correction_root_prediction_id": "pred:1",
            },
            "accepted_payload": {
                "prediction_id": "pred:1",
                "scope_key": "turn:1",
                "filtration_id": "conversation:c1",
                "target_variable": "user_response_present",
                "target_horizon_iso": "2026-02-13T00:00:00+00:00",
                "expectation": 0.2,
                "issued_at_iso": "2026-02-13T00:00:00+00:00",
            },
        }
    )

    assert resolution.proposal_event_kind == "repair_proposal"
    assert resolution.resolved_at_iso == "2026-02-13T00:00:01+00:00"
    assert resolution.accepted_prediction is not None


def test_repair_resolution_accepts_extended_legacy_aliases() -> None:
    resolution = RepairResolutionEvent.model_validate(
        {
            "event_kind": "repair_resolution",
            "repair_id": "repair:legacy:2",
            "resolution": "accepted",
            "resolved_at": "2026-02-13T00:00:02+00:00",
            "lineage_ref": {
                "scope_key": "turn:2",
                "prediction_id": "pred:2",
                "correction_root_prediction_id": "pred:2",
            },
            "accepted_prediction_record": {
                "prediction_id": "pred:2",
                "scope_key": "turn:2",
                "filtration_id": "conversation:c1",
                "target_variable": "user_response_present",
                "target_horizon_iso": "2026-02-13T00:00:00+00:00",
                "expectation": 0.9,
                "issued_at_iso": "2026-02-13T00:00:00+00:00",
            },
        }
    )

    assert resolution.decision == RepairResolution.ACCEPTED
    assert resolution.accepted_prediction is not None
    assert resolution.accepted_prediction.prediction_id == "pred:2"
