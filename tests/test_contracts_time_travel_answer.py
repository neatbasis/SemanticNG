from __future__ import annotations

import pytest
from pydantic import ValidationError

from state_renormalization.contracts import TimeTravelAnswer


def test_time_travel_answer_strict_replay_requires_historical_output_ref() -> None:
    with pytest.raises(ValidationError):
        TimeTravelAnswer.model_validate(
            {
                "mode": "strict_replay",
                "temporal_invariant": {
                    "invariant_id": "time_travel_answering.as_of.v1",
                    "query_mode": "latest",
                    "as_of_iso": None,
                    "satisfied": True,
                },
            }
        )


def test_time_travel_answer_reconstructed_requires_snapshot_and_reconstruction_identifiers() -> None:
    with pytest.raises(ValidationError):
        TimeTravelAnswer.model_validate(
            {
                "mode": "reconstructed",
                "temporal_invariant": {
                    "invariant_id": "time_travel_answering.as_of.v1",
                    "query_mode": "as_of",
                    "as_of_iso": "2026-01-01T00:00:00+00:00",
                    "satisfied": True,
                },
                "context_snapshot_ref": "predictions.jsonl@1",
            }
        )
