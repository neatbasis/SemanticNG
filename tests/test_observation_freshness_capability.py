from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from _pytest.monkeypatch import MonkeyPatch

from state_renormalization.contracts import (
    AskResult,
    BeliefState,
    Episode,
    Observation,
    ObservationFreshnessDecisionOutcome,
    ObservationFreshnessPolicyContract,
    ObservationType,
    ProjectionState,
    VerbosityDecision,
)
from state_renormalization.engine import evaluate_observation_freshness


@dataclass
class _FreshnessPolicyAdapter:
    contract: ObservationFreshnessPolicyContract
    outstanding_request_id: str | None = None

    def get_contract(self, **_: Any) -> ObservationFreshnessPolicyContract:
        return self.contract

    def has_outstanding_request(self, *, scope: str) -> str | None:
        if scope == self.contract.scope:
            return self.outstanding_request_id
        return None


@dataclass
class _AskOutboxStub:
    requests: list[dict[str, Any]] = field(default_factory=list)

    def create_request(self, title: str, question: str, context: Mapping[str, object]) -> str:
        request_id = f"req:{len(self.requests) + 1}"
        self.requests.append(
            {
                "request_id": request_id,
                "title": title,
                "question": question,
                "context": dict(context),
            }
        )
        return request_id


def _projection_state() -> ProjectionState:
    return ProjectionState(updated_at_iso="2026-02-13T00:05:00+00:00")


def test_no_observation_emits_request(
    monkeypatch: MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> None:
    monkeypatch.setattr(
        "state_renormalization.engine._now_iso", lambda: "2026-02-13T00:05:00+00:00"
    )
    ep = make_episode(decision=make_policy_decision(), ask=make_ask_result(), observations=[])
    outbox = _AskOutboxStub()

    decision = evaluate_observation_freshness(
        ep=ep,
        belief=BeliefState(),
        projection_state=_projection_state(),
        policy_adapter=_FreshnessPolicyAdapter(
            contract=ObservationFreshnessPolicyContract(
                scope=ObservationType.USER_UTTERANCE.value, observed_at_iso=None, stale_after_seconds=30
            ),
        ),
        ask_outbox_adapter=outbox,
    )

    assert decision.outcome == ObservationFreshnessDecisionOutcome.ASK_REQUEST
    assert outbox.requests


def test_stale_observation_emits_request_with_rationale(
    monkeypatch: MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
    make_observation: Callable[..., Observation],
) -> None:
    monkeypatch.setattr(
        "state_renormalization.engine._now_iso", lambda: "2026-02-13T00:05:00+00:00"
    )
    old_obs = make_observation(
        t_observed_iso="2026-02-13T00:00:00+00:00",
        observation_type=ObservationType.USER_UTTERANCE,
        text="last known reading",
    )
    ep = make_episode(
        decision=make_policy_decision(), ask=make_ask_result(), observations=[old_obs]
    )

    decision = evaluate_observation_freshness(
        ep=ep,
        belief=BeliefState(),
        projection_state=_projection_state(),
        policy_adapter=_FreshnessPolicyAdapter(
            contract=ObservationFreshnessPolicyContract(
                scope=ObservationType.USER_UTTERANCE.value, stale_after_seconds=120
            ),
        ),
        ask_outbox_adapter=_AskOutboxStub(),
    )

    assert decision.outcome == ObservationFreshnessDecisionOutcome.ASK_REQUEST
    ask_artifact = next(
        a for a in ep.artifacts if a.get("artifact_kind") == "observation_freshness_ask_request"
    )
    assert ask_artifact["reason"] == "observation is stale for freshness policy"
    assert ask_artifact["last_observed_at"] == "2026-02-13T00:00:00+00:00"
    assert ask_artifact["last_observed_value"] == "last known reading"
    assert ask_artifact["policy_threshold_seconds"] == 120


def test_fresh_observation_continues_without_request(
    monkeypatch: MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
    make_observation: Callable[..., Observation],
) -> None:
    monkeypatch.setattr(
        "state_renormalization.engine._now_iso", lambda: "2026-02-13T00:05:00+00:00"
    )
    fresh_obs = make_observation(
        t_observed_iso="2026-02-13T00:04:40+00:00",
        observation_type=ObservationType.USER_UTTERANCE,
        text="recent reading",
    )
    ep = make_episode(
        decision=make_policy_decision(), ask=make_ask_result(), observations=[fresh_obs]
    )
    outbox = _AskOutboxStub()

    decision = evaluate_observation_freshness(
        ep=ep,
        belief=BeliefState(),
        projection_state=_projection_state(),
        policy_adapter=_FreshnessPolicyAdapter(
            contract=ObservationFreshnessPolicyContract(
                scope=ObservationType.USER_UTTERANCE.value, stale_after_seconds=60
            ),
        ),
        ask_outbox_adapter=outbox,
    )

    assert decision.outcome == ObservationFreshnessDecisionOutcome.CONTINUE
    assert outbox.requests == []


def test_duplicate_outstanding_request_holds_instead_of_reissuing(
    monkeypatch: MonkeyPatch,
    make_episode: Callable[..., Episode],
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
    make_observation: Callable[..., Observation],
) -> None:
    monkeypatch.setattr(
        "state_renormalization.engine._now_iso", lambda: "2026-02-13T00:05:00+00:00"
    )
    stale_obs = make_observation(
        t_observed_iso="2026-02-13T00:00:00+00:00",
        observation_type=ObservationType.USER_UTTERANCE,
    )
    ep = make_episode(
        decision=make_policy_decision(), ask=make_ask_result(), observations=[stale_obs]
    )
    outbox = _AskOutboxStub()

    decision = evaluate_observation_freshness(
        ep=ep,
        belief=BeliefState(),
        projection_state=_projection_state(),
        policy_adapter=_FreshnessPolicyAdapter(
            contract=ObservationFreshnessPolicyContract(
                scope=ObservationType.USER_UTTERANCE.value, stale_after_seconds=10
            ),
            outstanding_request_id="req:existing",
        ),
        ask_outbox_adapter=outbox,
    )

    assert decision.outcome == ObservationFreshnessDecisionOutcome.HOLD
    assert decision.evidence["outstanding_request_id"] == "req:existing"
    assert outbox.requests == []
