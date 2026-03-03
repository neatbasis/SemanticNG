from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from state_renormalization.adapters.persistence import append_jsonl, read_jsonl
from state_renormalization.contracts import AskResult, BeliefState, Episode, ProjectionState, VerbosityDecision
from state_renormalization.engine import replay_projection_analytics, run_mission_loop


@dataclass
class _AskOutboxStub:
    requests: list[dict[str, Any]] = field(default_factory=list)

    def create_request(self, title: str, question: str, context: Mapping[str, object]) -> str:
        request_id = f"ask:{len(self.requests) + 1}"
        self.requests.append(
            {
                "request_id": request_id,
                "title": title,
                "question": question,
                "context": dict(context),
            }
        )
        return request_id


def _seed_active_due_mission(path: Path, *, mission_id: str = "mission:1") -> None:
    append_jsonl(
        path,
        {
            "event_kind": "mission_created",
            "mission": {
                "mission_id": mission_id,
                "mission_identity": "reminder:plants",
                "kind": "follow_up",
                "entity_ref": {"kind": "reminder_target", "ref": "plants"},
                "schedule_policy": {"min_prompt_interval_s": 300},
                "completion_mode": "manual",
                "status": "active",
                "next_prompt_at": "2026-02-13T09:00:00+02:00",
                "lineage_refs": [],
                "created_at_iso": "2026-02-13T06:55:00+00:00",
                "updated_at_iso": "2026-02-13T06:55:00+00:00",
            },
        },
    )


def test_scheduler_emits_due_prompt_once_and_respects_single_open_request_invariant(
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "predictions.jsonl"
    _seed_active_due_mission(log_path)

    projection = replay_projection_analytics(log_path).projection_state
    outbox = _AskOutboxStub()
    episode = make_episode(
        turn_index=1,
        t_asked_iso="2026-02-13T07:10:00+00:00",
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="status?"),
    )

    _, _, updated_projection = run_mission_loop(
        episode,
        BeliefState(),
        projection,
        prediction_log_path=log_path,
        ask_outbox_adapter=outbox,
    )

    assert len(outbox.requests) == 1
    assert outbox.requests[0]["context"]["overdue"] is True
    assert outbox.requests[0]["context"]["timezone"] == "UTC"

    first_next_prompt = updated_projection.active_missions["mission:1"].next_prompt_at
    assert first_next_prompt == "2026-02-13T07:15:00+00:00"

    second_episode = make_episode(
        turn_index=2,
        t_asked_iso="2026-02-13T07:16:00+00:00",
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="again"),
    )
    _, _, second_projection = run_mission_loop(
        second_episode,
        BeliefState(),
        updated_projection,
        prediction_log_path=log_path,
        ask_outbox_adapter=outbox,
    )

    assert len(outbox.requests) == 1
    assert second_projection.active_missions["mission:1"].next_prompt_at == first_next_prompt


def test_restart_replay_emits_identical_prompt_events_without_duplicates(
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
    tmp_path: Path,
) -> None:
    seed_log = tmp_path / "seed.jsonl"
    _seed_active_due_mission(seed_log, mission_id="mission:restart")

    log_a = tmp_path / "restart-a.jsonl"
    log_b = tmp_path / "restart-b.jsonl"
    payload = seed_log.read_text(encoding="utf-8")
    log_a.write_text(payload, encoding="utf-8")
    log_b.write_text(payload, encoding="utf-8")

    projection_a = replay_projection_analytics(log_a).projection_state
    projection_b = replay_projection_analytics(log_b).projection_state

    ep = make_episode(
        turn_index=3,
        t_asked_iso="2026-02-13T07:10:00+00:00",
        decision=make_policy_decision(),
        ask=make_ask_result(sentence="check"),
    )

    run_mission_loop(
        ep,
        BeliefState(),
        projection_a,
        prediction_log_path=log_a,
        ask_outbox_adapter=_AskOutboxStub(),
    )
    run_mission_loop(
        ep,
        BeliefState(),
        projection_b,
        prediction_log_path=log_b,
        ask_outbox_adapter=_AskOutboxStub(),
    )

    rows_a = [row for _, row in read_jsonl(log_a)]
    rows_b = [row for _, row in read_jsonl(log_b)]
    prompt_rows_a = [r for r in rows_a if r.get("event_kind") in {"ask_outbox_request", "mission_prompted"}]
    prompt_rows_b = [r for r in rows_b if r.get("event_kind") in {"ask_outbox_request", "mission_prompted"}]

    assert prompt_rows_a == prompt_rows_b
    assert len([r for r in rows_a if r.get("event_kind") == "mission_prompted"]) == 1
    assert len([r for r in rows_a if r.get("event_kind") == "ask_outbox_request"]) == 1
