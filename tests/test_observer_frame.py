from __future__ import annotations

from pathlib import Path

from state_renormalization.adapters.persistence import append_jsonl, read_jsonl
from state_renormalization.contracts import (
    AskMetrics,
    BeliefState,
    Channel,
    EpisodeOutputs,
    ObserverFrame,
    OutputRenderingArtifact,
    ProjectionState,
    VerbosityLevel,
)
from state_renormalization.engine import (
    GateSuccessOutcome,
    apply_schema_bubbling,
    apply_utterance_interpretation,
    attach_decision_effect,
    build_episode,
    evaluate_invariant_gates,
    ingest_observation,
    to_jsonable_episode,
)


def _outputs() -> EpisodeOutputs:
    return EpisodeOutputs(
        assistant_text_full="full",
        assistant_text_channel="channel",
        rendering=OutputRenderingArtifact(
            kind="text",
            channel=Channel.SATELLITE,
            verbosity_level=VerbosityLevel.V3_CONCISE,
            method="template",
        ),
    )


def test_build_episode_uses_default_observer(make_policy_decision) -> None:
    ep = build_episode(
        conversation_id="conv:test",
        turn_index=1,
        assistant_prompt_asked="prompt",
        policy_decision=make_policy_decision(),
        payload={"sentence": "hi", "metrics": AskMetrics().model_dump(mode="json")},
        outputs=_outputs(),
    )

    assert ep.observer is not None
    assert ep.observer.role == "assistant"
    assert "baseline.dialog" in ep.observer.capabilities


def test_observer_preserved_in_persisted_episode_json(tmp_path: Path, make_episode) -> None:
    ep = make_episode(
        observer=ObserverFrame(
            role="assistant",
            capabilities=["baseline.dialog"],
            authorization_level="baseline",
            evaluation_invariants=["prediction_availability.v1"],
        )
    )
    serialized = to_jsonable_episode(ep)

    out = tmp_path / "episodes.jsonl"
    append_jsonl(out, serialized)

    (_, rec), = list(read_jsonl(out))
    assert rec["observer"]["role"] == "assistant"
    assert rec["observer"]["capabilities"] == ["baseline.dialog"]
    assert rec["observer"]["evaluation_invariants"] == ["prediction_availability.v1"]


def test_observer_passed_through_decision_and_evaluation_artifacts(make_episode, make_ask_result) -> None:
    prev_ep = make_episode()
    curr_ep = make_episode(ask=make_ask_result(sentence="hello"))

    curr_ep = attach_decision_effect(prev_ep, curr_ep)
    assert curr_ep.effects[0].notes["observer"]["role"] == "assistant"

    evaluate_invariant_gates(
        ep=curr_ep,
        scope="scope:test",
        prediction_key=None,
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=False,
    )
    invariant_artifact = next(a for a in curr_ep.artifacts if a.get("artifact_kind") == "invariant_outcomes")
    assert invariant_artifact["observer"]["role"] == "assistant"

    halt_observation = next(a for a in curr_ep.artifacts if a.get("artifact_kind") == "halt_observation")
    assert halt_observation["observation_type"] == "halt"


def test_episode_serialization_supports_null_observer(tmp_path: Path, make_episode) -> None:
    ep = make_episode(with_default_observer=False)
    serialized = to_jsonable_episode(ep)

    assert serialized["observer"] is None

    out = tmp_path / "episodes.jsonl"
    append_jsonl(out, serialized)
    (_, rec), = list(read_jsonl(out))
    assert rec["observer"] is None


def test_observer_enforcement_hooks_limit_invariant_evaluation(make_episode, make_observer) -> None:
    ep = make_episode(
        observer=make_observer(evaluation_invariants=["prediction_retrievability.v1"]),
    )

    gate = evaluate_invariant_gates(
        ep=ep,
        scope="scope:test",
        prediction_key="scope:test",
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=True,
    )

    assert isinstance(gate, GateSuccessOutcome)
    assert gate.artifact.pre_consume == ()

    invariant_artifact = next(a for a in ep.artifacts if a.get("artifact_kind") == "invariant_outcomes")
    assert invariant_artifact["observer_enforcement"]["enforced"] is True
    assert invariant_artifact["observer_enforcement"]["requested_evaluation_invariants"] == [
        "prediction_retrievability.v1"
    ]

def test_build_episode_attaches_stable_ids_from_feature_doc(tmp_path: Path, make_policy_decision) -> None:
    feature = tmp_path / "sample.feature"
    feature.write_text(
        """
Feature: Stable IDs
  Scenario: keyed scenario
    Given a concrete step
""".strip()
        + "\n",
        encoding="utf-8",
    )

    ep = build_episode(
        conversation_id="conv:test",
        turn_index=1,
        assistant_prompt_asked="prompt",
        policy_decision=make_policy_decision(),
        payload={
            "sentence": "hi",
            "metrics": AskMetrics().model_dump(mode="json"),
            "feature_uri": str(feature),
            "scenario_name": "keyed scenario",
            "step_text": "a concrete step",
        },
        outputs=_outputs(),
    )

    policy_artifact = ep.artifacts[0]
    assert policy_artifact["feature_id"].startswith("feat_")
    assert policy_artifact["scenario_id"].startswith("scn_")
    assert policy_artifact["step_id"].startswith("stp_")


def test_observer_included_in_schema_and_utterance_artifacts(make_episode, make_ask_result) -> None:
    ep = make_episode(ask=make_ask_result(sentence="hello there"))
    ep = ingest_observation(ep)

    ep, belief = apply_schema_bubbling(ep, BeliefState())
    ep, _ = apply_utterance_interpretation(ep, belief)

    schema_artifact = next(a for a in ep.artifacts if a.get("kind") == "schema_selection")
    utterance_artifact = next(a for a in ep.artifacts if a.get("kind") == "utterance_interpretation")
    assert schema_artifact["observer"]["role"] == "assistant"
    assert utterance_artifact["observer"]["role"] == "assistant"
