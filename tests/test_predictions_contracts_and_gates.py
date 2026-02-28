from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from state_renormalization.contracts import HaltRecord, PredictionRecord, ProjectionState
from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.engine import (
    GateDecision,
    Success,
    append_prediction_record,
    evaluate_invariant_gates,
    project_current,
)
from state_renormalization.invariants import (
    Flow,
    InvariantId,
    InvariantOutcome,
    REGISTRY,
    Validity,
    default_check_context,
    normalize_outcome,
)


FIXED_PREDICTION = {
    "prediction_id": "pred:test",
    "prediction_key": "room:kitchen:light",
    "scope_key": "room:kitchen:light",
    "filtration_ref": "filt:1",
    "variable": "light_on",
    "horizon_iso": "2026-02-13T00:05:00+00:00",
    "distribution_kind": "bernoulli",
    "distribution_params": {"p": 0.7},
    "confidence": 0.88,
    "uncertainty": 0.12,
    "issued_at_iso": "2026-02-13T00:00:00+00:00",
    "valid_from_iso": "2026-02-13T00:00:00+00:00",
    "valid_until_iso": "2026-02-13T00:10:00+00:00",
    "stopping_time_iso": None,
    "invariants_assumed": ["prediction_availability.v1"],
    "evidence_links": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
    "conditional_expectation": None,
    "conditional_variance": None,
}

REGISTERED_INVARIANTS = tuple(REGISTRY.keys())


@dataclass(frozen=True)
class InvariantScenario:
    name: str
    build_context: Callable[[], Any]
    expected_passed: bool
    expected_flow: Flow
    gate_inputs: dict[str, Any] | None = None


@dataclass(frozen=True)
class InvariantCoverage:
    supports_stop: bool
    scenarios: tuple[InvariantScenario, ...]


def _build_allow_context_for_prediction_availability() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
    )


def _build_stop_context_for_prediction_availability() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={},
        prediction_log_available=True,
    )


def _build_allow_context_for_evidence_link_completeness() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        just_written_prediction={"key": "scope:test", "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}]},
    )


def _build_stop_context_for_evidence_link_completeness() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        just_written_prediction={"key": "scope:test", "evidence_refs": []},
    )


def _build_allow_context_for_prediction_outcome_binding() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        prediction_outcome={"prediction_id": "pred:test", "error_metric": 0.12},
    )


def _build_stop_context_for_prediction_outcome_binding() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        prediction_outcome={"prediction_id": "", "error_metric": 0.12},
    )


def _build_allow_context_for_explainable_halt_payload() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        halt_candidate=InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_AVAILABILITY,
            passed=False,
            reason="Action selection requires at least one projected current prediction.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_predictions_projected",
            details={"message": "Action selection requires at least one projected current prediction."},
            evidence=({"kind": "scope", "value": "scope:test"},),
            action_hints=({"kind": "rebuild_view", "scope": "scope:test"},),
        ),
    )


def _build_stop_context_for_explainable_halt_payload() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        halt_candidate=InvariantOutcome(
            invariant_id=InvariantId.PREDICTION_AVAILABILITY,
            passed=False,
            reason="Action selection requires at least one projected current prediction.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_predictions_projected",
            details=None,  # type: ignore[arg-type]
            evidence=None,  # type: ignore[arg-type]
            action_hints=({"kind": "rebuild_view", "scope": "scope:test"},),
        ),
    )


INVARIANT_RELEASE_GATE_MATRIX: dict[InvariantId, InvariantCoverage] = {
    InvariantId.PREDICTION_AVAILABILITY: InvariantCoverage(
        supports_stop=True,
        scenarios=(
            InvariantScenario(
                name="pass",
                build_context=_build_allow_context_for_prediction_availability,
                expected_passed=True,
                expected_flow=Flow.CONTINUE,
                gate_inputs={"just_written_prediction": None, "has_projected_prediction": True},
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_prediction_availability,
                expected_passed=False,
                expected_flow=Flow.STOP,
                gate_inputs={"just_written_prediction": None, "has_projected_prediction": False},
            ),
        ),
    ),
    InvariantId.EVIDENCE_LINK_COMPLETENESS: InvariantCoverage(
        supports_stop=True,
        scenarios=(
            InvariantScenario(
                name="pass",
                build_context=_build_allow_context_for_evidence_link_completeness,
                expected_passed=True,
                expected_flow=Flow.CONTINUE,
                gate_inputs={
                    "just_written_prediction": {"key": "scope:test", "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}]},
                    "has_projected_prediction": True,
                },
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_evidence_link_completeness,
                expected_passed=False,
                expected_flow=Flow.STOP,
                gate_inputs={"just_written_prediction": {"key": "scope:test", "evidence_refs": []}, "has_projected_prediction": True},
            ),
        ),
    ),
    InvariantId.PREDICTION_OUTCOME_BINDING: InvariantCoverage(
        supports_stop=True,
        scenarios=(
            InvariantScenario(
                name="pass",
                build_context=_build_allow_context_for_prediction_outcome_binding,
                expected_passed=True,
                expected_flow=Flow.CONTINUE,
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_prediction_outcome_binding,
                expected_passed=False,
                expected_flow=Flow.STOP,
            ),
        ),
    ),
    InvariantId.EXPLAINABLE_HALT_PAYLOAD: InvariantCoverage(
        supports_stop=True,
        scenarios=(
            InvariantScenario(
                name="pass",
                build_context=_build_allow_context_for_explainable_halt_payload,
                expected_passed=True,
                expected_flow=Flow.CONTINUE,
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_explainable_halt_payload,
                expected_passed=False,
                expected_flow=Flow.STOP,
            ),
        ),
    ),
}


MATRIX_CASES = [
    pytest.param(invariant_id, scenario, id=f"{invariant_id.value}:{scenario.name}")
    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
    for scenario in coverage.scenarios
]


def _assert_result_contract(result: GateDecision) -> None:
    if isinstance(result, Success):
        assert all(out.flow == Flow.CONTINUE for out in result.artifact.combined)
    else:
        assert isinstance(result, HaltRecord)
        assert result.halt_id.startswith("halt:")
        assert result.invariant_id
        assert result.reason


def test_halt_payload_schema_is_canonical_for_stop_emitters() -> None:
    expected_schema = {
        "halt_id": "str",
        "stage": "str",
        "invariant_id": "str",
        "reason": "str",
        "details": "dict",
        "evidence": "list",
        "retryability": "bool",
        "timestamp": "str",
    }

    assert HaltRecord.required_payload_fields() == tuple(expected_schema)
    assert HaltRecord.canonical_payload_schema() == expected_schema

def test_gate_flow_contract_parity_for_continue_and_stop(tmp_path: Path) -> None:
    scope = FIXED_PREDICTION["scope_key"]
    projected = project_current(
        PredictionRecord.model_validate(FIXED_PREDICTION),
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    continue_gate = evaluate_invariant_gates(
        ep=None,
        scope=scope,
        prediction_key=scope,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": scope, "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}]},
        halt_log_path=tmp_path / "continue_halts.jsonl",
    )
    stop_gate = evaluate_invariant_gates(
        ep=None,
        scope=scope,
        prediction_key=scope,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": scope, "evidence_refs": []},
        halt_log_path=tmp_path / "stop_halts.jsonl",
    )

    assert isinstance(continue_gate, Success)
    assert all(out.flow == Flow.CONTINUE for out in continue_gate.artifact.pre_consume)
    assert all(out.flow == Flow.CONTINUE for out in continue_gate.artifact.post_write)
    assert all(out.flow == Flow.CONTINUE for out in continue_gate.artifact.combined)

    assert isinstance(stop_gate, HaltRecord)
    assert stop_gate.stage == "pre-decision:post_write"
    assert stop_gate.invariant_id == InvariantId.EVIDENCE_LINK_COMPLETENESS.value


def test_prediction_record_json_round_trip() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    dumped = pred.model_dump(mode="json")
    reloaded = PredictionRecord.model_validate(dumped)

    assert reloaded == pred


def test_registered_invariant_parameterization_matches_registry() -> None:
    assert set(REGISTERED_INVARIANTS) == set(INVARIANT_RELEASE_GATE_MATRIX)


def test_invariant_identifiers_are_enumerated_and_registered() -> None:
    enumerated_identifiers = tuple(invariant.value for invariant in InvariantId)
    assert enumerated_identifiers == (
        "prediction_availability.v1",
        "evidence_link_completeness.v1",
        "prediction_outcome_binding.v1",
        "explainable_halt_payload.v1",
    )
    assert tuple(InvariantId(identifier) for identifier in enumerated_identifiers) == REGISTERED_INVARIANTS


def test_invariant_matrix_release_gate_has_required_coverage() -> None:
    assert set(InvariantId) == set(REGISTERED_INVARIANTS) == set(INVARIANT_RELEASE_GATE_MATRIX)

    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items():
        assert any(s.expected_passed for s in coverage.scenarios), f"{invariant_id.value} has no pass scenario"
        if coverage.supports_stop:
            assert any(not s.expected_passed for s in coverage.scenarios), f"{invariant_id.value} has no stop scenario"


@pytest.mark.parametrize("invariant_id,scenario", MATRIX_CASES)
def test_invariant_outcomes_are_deterministic_and_contract_compliant(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
) -> None:
    checker = REGISTRY[invariant_id]
    ctx = scenario.build_context()

    first = checker(ctx)
    second = checker(ctx)
    assert first == second
    assert first.invariant_id == invariant_id
    assert first.passed is scenario.expected_passed
    assert first.flow == scenario.expected_flow

    normalized = normalize_outcome(first, gate=f"test:{scenario.name}")
    assert normalized.invariant_id == invariant_id.value
    assert normalized.gate == f"test:{scenario.name}"
    assert normalized.passed is scenario.expected_passed
    assert isinstance(normalized.reason, str)
    assert isinstance(normalized.evidence, tuple)


@pytest.mark.parametrize("invariant_id,scenario", MATRIX_CASES)
def test_gate_decisions_and_artifacts_are_deterministic_by_invariant(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
    tmp_path: Path,
) -> None:
    if scenario.gate_inputs is None:
        pytest.skip(f"{invariant_id.value} is not directly evaluated by evaluate_invariant_gates")

    just_written_prediction = scenario.gate_inputs["just_written_prediction"]
    has_projected_prediction = scenario.gate_inputs["has_projected_prediction"]
    expect_halt = scenario.expected_flow == Flow.STOP

    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = []

    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")
    scope_key = FIXED_PREDICTION["scope_key"]
    if has_projected_prediction:
        pred = PredictionRecord.model_validate(FIXED_PREDICTION)
        projection = project_current(pred, projection)

    first_ep = DummyEpisode()
    second_ep = DummyEpisode()
    gate_write = None
    if just_written_prediction is not None:
        gate_write = dict(just_written_prediction)
        gate_write["key"] = scope_key

    first = evaluate_invariant_gates(
        ep=first_ep,
        scope=scope_key,
        prediction_key=scope_key,
        projection_state=projection,
        prediction_log_available=True,
        just_written_prediction=gate_write,
        halt_log_path=tmp_path / f"halts_{invariant_id.value.replace('.', '_')}_1.jsonl",
    )
    second = evaluate_invariant_gates(
        ep=second_ep,
        scope=scope_key,
        prediction_key=scope_key,
        projection_state=projection,
        prediction_log_available=True,
        just_written_prediction=gate_write,
        halt_log_path=tmp_path / f"halts_{invariant_id.value.replace('.', '_')}_2.jsonl",
    )

    _assert_result_contract(first)
    _assert_result_contract(second)

    first_artifact = first_ep.artifacts[0]
    second_artifact = second_ep.artifacts[0]
    assert first_artifact["artifact_kind"] == "invariant_outcomes"
    assert second_artifact["artifact_kind"] == "invariant_outcomes"
    assert first_artifact["invariant_checks"] == second_artifact["invariant_checks"]

    if expect_halt:
        assert isinstance(first, HaltRecord)
        assert isinstance(second, HaltRecord)
        assert first.invariant_id == invariant_id.value
        assert second.invariant_id == invariant_id.value
        assert first.halt_id == second.halt_id
        assert first_artifact["kind"] == "halt"
        assert any(check["invariant_id"] == InvariantId.EXPLAINABLE_HALT_PAYLOAD.value for check in first_artifact["invariant_checks"])
    else:
        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert [out.code for out in first.artifact.combined] == [out.code for out in second.artifact.combined]
        assert first_artifact["kind"] == "prediction"
        assert any(check["invariant_id"] == invariant_id.value for check in first_artifact["invariant_checks"])


@pytest.mark.parametrize(
    "invariant_id,scenario_name",
    [
        pytest.param(invariant_id, scenario.name, id=f"{invariant_id.value}:{scenario.name}")
        for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
        for scenario in coverage.scenarios
        if scenario.gate_inputs is not None
    ],
)
def test_gate_matrix_covers_all_gate_evaluated_invariants(invariant_id: InvariantId, scenario_name: str) -> None:
    assert invariant_id in {
        InvariantId.PREDICTION_AVAILABILITY,
        InvariantId.EVIDENCE_LINK_COMPLETENESS,
    }
    assert scenario_name in {"pass", "stop"}


def test_post_write_gate_passes_when_evidence_and_projection_current() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )

    assert isinstance(gate, Success)
    assert gate.artifact.post_write
    assert gate.artifact.post_write[0].code == "evidence_links_complete"


def test_post_write_gate_halts_when_append_evidence_missing(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    halt = gate
    assert halt.stage == "pre-decision:post_write"
    assert halt.invariant_id == "evidence_link_completeness.v1"
    assert halt.reason == "Prediction append did not produce linked evidence."
    assert [e.model_dump(mode="json") for e in halt.evidence] == [{"kind": "scope", "ref": pred.scope_key}]
    assert halt.retryability is True


def test_halt_artifact_includes_halt_evidence_ref_and_invariant_context(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = []

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )
    ep = DummyEpisode()

    gate = evaluate_invariant_gates(
        ep=ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    assert len(ep.artifacts) == 2
    artifact = ep.artifacts[0]
    assert artifact["artifact_kind"] == "invariant_outcomes"
    assert artifact["kind"] == "halt"
    assert artifact["halt"]["halt_id"].startswith("halt:")
    assert set(artifact["halt"].keys()) == set(HaltRecord.required_payload_fields())
    assert artifact["halt_evidence_ref"] == {"kind": "jsonl", "ref": "halts.jsonl@1"}
    assert artifact["invariant_context"]["prediction_log_available"] is True
    assert artifact["invariant_context"]["has_current_predictions"] is True
    assert artifact["invariant_context"]["just_written_prediction"] == {
        "key": pred.scope_key,
        "evidence_refs": [],
    }
    assert artifact["invariant_checks"] == [
        {
            "gate_point": "pre-decision:pre_consume",
            "invariant_id": "prediction_availability.v1",
            "passed": True,
            "evidence": [],
            "reason": "current_prediction_available",
        },
        {
            "gate_point": "pre-decision:post_write",
            "invariant_id": "evidence_link_completeness.v1",
            "passed": False,
            "evidence": [{"kind": "scope", "ref": pred.scope_key}],
            "reason": "Prediction append did not produce linked evidence.",
        },
        {
            "gate_point": "halt_validation",
            "invariant_id": "explainable_halt_payload.v1",
            "passed": True,
            "evidence": [],
            "reason": "halt_payload_explainable",
        },
    ]

    halt_observation = ep.artifacts[1]
    assert halt_observation["artifact_kind"] == "halt_observation"
    assert halt_observation["observation_type"] == "halt"
    assert halt_observation["halt_id"].startswith("halt:")
    assert set(halt_observation.keys()) >= set(HaltRecord.required_payload_fields())
    assert halt_observation["invariant_id"] == "evidence_link_completeness.v1"


def test_append_prediction_and_projection_support_post_write_gate(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    evidence = append_prediction_record(pred, prediction_log_path=tmp_path / "predictions.jsonl")

    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    gate = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": [evidence]},
    )

    assert evidence["ref"].startswith("predictions.jsonl@")
    assert projected.current_predictions[pred.scope_key] == pred
    assert isinstance(gate, Success)
    assert gate.artifact.post_write[0].code == "evidence_links_complete"


def test_pre_consume_gate_halts_without_any_projected_predictions(tmp_path: Path) -> None:
    gate = evaluate_invariant_gates(
        ep=None,
        scope="scope:test",
        prediction_key="scope:test",
        projection_state=ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    halt = gate
    assert halt.invariant_id == "prediction_availability.v1"
    assert halt.reason == "Action selection requires at least one projected current prediction."


def test_append_prediction_record_persists_supplied_stable_ids(tmp_path: Path) -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    prediction_path = tmp_path / "predictions.jsonl"

    append_prediction_record(
        pred,
        prediction_log_path=prediction_path,
        stable_ids={"feature_id": "feat_1", "scenario_id": "scn_1", "step_id": "stp_1"},
    )

    (_, rec), = list(read_jsonl(prediction_path))
    assert rec["feature_id"] == "feat_1"
    assert rec["scenario_id"] == "scn_1"
    assert rec["step_id"] == "stp_1"


def test_evaluate_invariant_gates_persists_halt_with_episode_stable_ids(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = [{"kind": "stable_ids", "feature_id": "feat_1", "scenario_id": "scn_1", "step_id": "stp_1"}]

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    evaluate_invariant_gates(
        ep=DummyEpisode(),
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    (_, rec), = list(read_jsonl(tmp_path / "halts.jsonl"))
    assert rec["feature_id"] == "feat_1"
    assert rec["scenario_id"] == "scn_1"
    assert rec["step_id"] == "stp_1"


def test_gate_branch_parity_and_deterministic_halt_selection(tmp_path: Path) -> None:
    projected = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")

    gate = evaluate_invariant_gates(
        ep=None,
        scope="scope:test",
        prediction_key="scope:test",
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": "scope:test", "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    assert gate.stage == "pre-decision:pre_consume"
    assert gate.invariant_id == "prediction_availability.v1"


def test_gate_deterministic_continue_outcome_has_stable_branches() -> None:
    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    first = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )
    second = evaluate_invariant_gates(
        ep=None,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert [out.flow.value for out in first.artifact.combined] == ["continue", "continue"]
    assert [out.code for out in first.artifact.combined] == [out.code for out in second.artifact.combined]


def test_gate_flow_parity_continue_and_stop_payloads(tmp_path: Path) -> None:
    class DummyEpisode:
        def __init__(self) -> None:
            self.artifacts = []

    pred = PredictionRecord.model_validate(FIXED_PREDICTION)
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    continue_ep = DummyEpisode()
    continue_gate = evaluate_invariant_gates(
        ep=continue_ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )
    assert isinstance(continue_gate, Success)
    assert [out.flow for out in continue_gate.artifact.pre_consume] == [Flow.CONTINUE]
    assert [out.flow for out in continue_gate.artifact.post_write] == [Flow.CONTINUE]
    assert [out.flow for out in continue_gate.artifact.combined] == [Flow.CONTINUE, Flow.CONTINUE]

    stop_ep = DummyEpisode()
    stop_gate = evaluate_invariant_gates(
        ep=stop_ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )
    assert isinstance(stop_gate, HaltRecord)
    stop_checks = stop_ep.artifacts[0]["invariant_checks"]
    assert [check["passed"] for check in stop_checks[:2]] == [True, False]
    assert [check["invariant_id"] for check in stop_checks[:2]] == [
        InvariantId.PREDICTION_AVAILABILITY.value,
        InvariantId.EVIDENCE_LINK_COMPLETENESS.value,
    ]
    assert stop_gate.stage == "pre-decision:post_write"
    assert stop_gate.invariant_id == InvariantId.EVIDENCE_LINK_COMPLETENESS.value
