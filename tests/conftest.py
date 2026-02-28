from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

import pytest
from typing_extensions import Unpack

from state_renormalization.contracts import (
    Ambiguity,
    AskMetrics,
    AskResult,
    AskStatus,
    BeliefState,
    CaptureOutcome,
    Channel,
    Episode,
    Observation,
    ObservationType,
    ObserverFrame,
    SchemaHit,
    SchemaSelection,
    VerbosityDecision,
    VerbosityLevel,
    default_observer_frame,
)


@pytest.fixture
def belief() -> BeliefState:
    return BeliefState()


@pytest.fixture
def make_policy_decision() -> Callable[..., VerbosityDecision]:
    def _make_policy_decision(
        *,
        decision_id: str = "dec:test",
        t_decided_iso: str = "2026-02-11T00:00:00Z",
        action_type: str = "prompt_user",
        verbosity_level: VerbosityLevel = VerbosityLevel.V3_CONCISE,
        channel: Channel = Channel.SATELLITE,
        policy_version: str = "test",
        source: str = "test",
    ) -> VerbosityDecision:
        return VerbosityDecision(
            decision_id=decision_id,
            t_decided_iso=t_decided_iso,
            action_type=action_type,
            verbosity_level=verbosity_level,
            channel=channel,
            reason_codes=[],
            signals={},
            hypothesis=None,
            policy_version=policy_version,
            source=source,
        )

    return _make_policy_decision


@pytest.fixture
def make_ask_result() -> Callable[..., AskResult]:
    def _make_ask_result(
        *,
        status: AskStatus = AskStatus.OK,
        sentence: str | None = None,
        error: CaptureOutcome | None = None,
        metrics: AskMetrics | None = None,
    ) -> AskResult:
        return AskResult(
            status=status,
            sentence=sentence,
            slots={},
            error=error,
            metrics=metrics or AskMetrics(),
        )

    return _make_ask_result


@pytest.fixture
def make_episode(
    make_policy_decision: Callable[..., VerbosityDecision],
    make_ask_result: Callable[..., AskResult],
) -> Callable[..., Episode]:
    def _make_episode(
        *,
        episode_id: str = "ep:test",
        conversation_id: str = "conv:test",
        turn_index: int = 0,
        t_asked_iso: str = "2026-02-11T00:00:00Z",
        assistant_prompt_asked: str = "(test prompt)",
        decision: VerbosityDecision | None = None,
        ask: AskResult | None = None,
        observations: list[Observation] | None = None,
        observer: ObserverFrame | None = None,
        with_default_observer: bool = True,
    ) -> Episode:
        episode_observer = observer
        if episode_observer is None and with_default_observer:
            episode_observer = default_observer_frame()

        return Episode(
            episode_id=episode_id,
            conversation_id=conversation_id,
            turn_index=turn_index,
            t_asked_iso=t_asked_iso,
            assistant_prompt_asked=assistant_prompt_asked,
            observer=episode_observer,
            policy_decision=decision or make_policy_decision(),
            ask=ask or make_ask_result(),
            observations=observations or [],
            outputs=None,
            artifacts=[],
            effects=[],
        )

    return _make_episode


@pytest.fixture
def make_observer() -> Callable[..., ObserverFrame]:
    def _make_observer(
        *,
        role: str = "assistant",
        capabilities: list[str] | None = None,
        authorization_level: str = "baseline",
        evaluation_invariants: list[str] | None = None,
    ) -> ObserverFrame:
        return ObserverFrame(
            role=role,
            capabilities=capabilities or ["baseline.dialog", "baseline.schema_selection", "baseline.invariant_evaluation", "baseline.evaluation"],
            authorization_level=authorization_level,
            evaluation_invariants=evaluation_invariants or [],
        )

    return _make_observer


@pytest.fixture
def make_observation() -> Callable[..., Observation]:
    def _make_observation(
        *,
        observation_id: str = "obs:test:0",
        t_observed_iso: str = "2026-02-11T00:00:00Z",
        observation_type: ObservationType = ObservationType.USER_UTTERANCE,
        text: str | None = "Hello",
        source: str = "channel:satellite",
    ) -> Observation:
        return Observation(
            observation_id=observation_id,
            t_observed_iso=t_observed_iso,
            type=observation_type,
            text=text,
            source=source,
        )

    return _make_observation


@pytest.fixture
def make_schema_selection() -> Callable[..., SchemaSelection]:
    class _SchemaSelectionKwargs(TypedDict, total=False):
        schemas: list[SchemaHit]
        ambiguities: list[Ambiguity]
        notes: str | None

    def _make_schema_selection(**kwargs: Unpack[_SchemaSelectionKwargs]) -> SchemaSelection:
        return SchemaSelection(**kwargs)

    return _make_schema_selection
