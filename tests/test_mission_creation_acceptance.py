from __future__ import annotations

import json
from pathlib import Path

from state_renormalization.contracts import AskResult, AskStatus, BeliefState, Observation, ObservationType, ProjectionState
from state_renormalization.engine import replay_projection_analytics, run_mission_loop


def _episode(make_episode, *, turn_index: int, text: str, slots: dict[str, str]):
    return make_episode(
        turn_index=turn_index,
        ask=AskResult(status=AskStatus.OK, sentence=text, slots=slots),
        observations=[
            Observation(
                observation_id=f"obs:{turn_index}",
                t_observed_iso="2026-03-01T00:00:00+00:00",
                type=ObservationType.USER_UTTERANCE,
                text=text,
            )
        ],
    )


def test_mission_creation_acceptance_ambiguous_then_clarified_then_replay_idempotent(
    tmp_path: Path,
    make_episode,
) -> None:
    log = tmp_path / "prediction-log.jsonl"
    belief = BeliefState()
    projection = ProjectionState(current_predictions={}, updated_at_iso="1970-01-01T00:00:00+00:00")

    ep0 = _episode(make_episode, turn_index=0, text="remind me to check the report", slots={})
    _, belief_after_ambiguous, projection = run_mission_loop(
        ep0,
        belief,
        projection,
        prediction_log_path=log,
    )

    assert belief_after_ambiguous.pending_about is not None
    assert projection.active_missions == {}

    clarification_slots = {
        "reminder.schedule": "tomorrow at 9",
        "reminder.completion_condition": "manual",
        "reminder.target_entity": "check the report",
    }
    ep1 = _episode(
        make_episode,
        turn_index=1,
        text="remind me tomorrow morning to check the report",
        slots=clarification_slots,
    )
    _, belief_after_clarification, projection_after_create = run_mission_loop(
        ep1,
        belief_after_ambiguous,
        projection,
        prediction_log_path=log,
    )

    assert "intent.mission_create" in belief_after_clarification.active_schemas
    mission_draft = belief_after_clarification.bindings.get("mission.draft")
    assert isinstance(mission_draft, dict)
    assert mission_draft["schedule"] == "tomorrow at 9"
    assert len(projection_after_create.active_missions) == 1

    _, _, projection_after_replay = run_mission_loop(
        ep1,
        belief_after_clarification,
        projection_after_create,
        prediction_log_path=log,
    )
    assert len(projection_after_replay.active_missions) == 1

    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    mission_created_rows = [r for r in rows if r.get("event_kind") == "mission_created"]
    mission_link_rows = [r for r in rows if r.get("event_kind") == "ask_response_mission_link"]
    assert len(mission_created_rows) == 1
    assert len(mission_link_rows) == 1
    assert mission_created_rows[0]["mission"]["lineage_refs"][0]["relation"] == "resolved_by"

    replay_a = replay_projection_analytics(log)
    replay_b = replay_projection_analytics(log)
    assert replay_a.model_dump(mode="json") == replay_b.model_dump(mode="json")
    assert len(replay_a.projection_state.active_missions) == 1
