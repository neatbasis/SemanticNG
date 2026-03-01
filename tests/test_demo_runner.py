from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from state_renormalization.contracts import (
    AskResult,
    AskStatus,
    BeliefState,
    Episode,
    ProjectionState,
)
from state_renormalization.engine import run_mission_loop


def _blank_projection() -> ProjectionState:
    return ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")


def test_demo_runner_substrate_smoke_executes_mission_loop_and_persists_prediction_log(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    prediction_log = tmp_path / "predictions.jsonl"
    episode = make_episode(
        conversation_id="conv:demo-smoke",
        turn_index=1,
        ask=make_ask_result(status=AskStatus.OK, sentence="hello"),
    )

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
        prediction_log_path=prediction_log,
    )

    assert prediction_log.exists()
    assert prediction_log.read_text(encoding="utf-8").strip()
    assert any(a.get("artifact_kind") == "turn_summary" for a in episode.artifacts)


def test_demo_runner_substrate_non_blocking_with_no_response_capture(
    make_episode: Callable[..., Episode],
    make_ask_result: Callable[..., AskResult],
) -> None:
    episode = make_episode(
        conversation_id="conv:demo-no-response",
        turn_index=2,
        ask=make_ask_result(status=AskStatus.NO_RESPONSE, sentence=None),
    )

    run_mission_loop(
        episode,
        BeliefState(),
        _blank_projection(),
    )

    assert any(a.get("artifact_kind") == "turn_summary" for a in episode.artifacts)
