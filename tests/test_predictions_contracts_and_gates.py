from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from state_renormalization.adapters.persistence import read_jsonl
from state_renormalization.contracts import (
    Episode,
    EvidenceRef,
    HaltRecord,
    PredictionRecord,
    ProjectionState,
)
from state_renormalization.engine import (
    GateDecision,
    Success,
    append_prediction_record,
    evaluate_invariant_gates,
    project_current,
)
from state_renormalization.invariants import (
    REGISTERED_INVARIANT_BRANCH_BEHAVIORS,
    REGISTERED_INVARIANT_IDS,
    REGISTRY,
    Flow,
    InvariantId,
    InvariantOutcome,
    Validity,
    default_check_context,
    normalize_outcome,
)

FIXED_PREDICTION_PAYLOAD: dict[str, Any] = {
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


def _fixed_prediction_record() -> PredictionRecord:
    return PredictionRecord.model_validate(FIXED_PREDICTION_PAYLOAD)


def _make_episode_with_artifacts() -> Episode:
    return Episode(
        episode_id="ep:test",
        conversation_id="conv:test",
        turn_index=0,
        t_asked_iso="2026-02-13T00:00:00+00:00",
        assistant_prompt_asked="(test prompt)",
        observer=None,
        policy_decision=None,
        ask=None,
        observations=[],
        outputs=None,
        artifacts=[],
        effects=[],
    )

REGISTERED_INVARIANTS = tuple(REGISTRY.keys())
REGISTERED_INVARIANT_IDS_FROM_REGISTRY = tuple(
    invariant_id.value for invariant_id in REGISTERED_INVARIANTS
)
REPLAY_ANALYTICS_SCOPE_REQUIRES_COMPLETE_MATRIX = True


@dataclass(frozen=True)
class InvariantScenario:
    name: str
    build_context: Callable[[], Any]
    expected_passed: bool
    expected_flow: Flow
    expected_code: str
    rationale: str
    gate_inputs: dict[str, Any] | None = None


@dataclass(frozen=True)
class NonApplicableGateCoverage:
    rationale: str


@dataclass(frozen=True)
class InvariantCoverage:
    supports_stop: bool
    scenarios: tuple[InvariantScenario, ...]
    gate_non_applicable: NonApplicableGateCoverage | None = None


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
        just_written_prediction={
            "key": "scope:test",
            "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        },
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
            details={
                "message": "Action selection requires at least one projected current prediction."
            },
            evidence=(EvidenceRef(kind="scope", ref="scope:test"),),
            action_hints=({"kind": "rebuild_view", "scope": "scope:test"},),
        ),
    )


def _build_stop_context_for_explainable_halt_payload() -> Any:
    return default_check_context(
        scope="scope:test",
        prediction_key="scope:test",
        current_predictions={"scope:test": "pred:test"},
        prediction_log_available=True,
        halt_candidate=InvariantOutcome.model_construct(
            invariant_id=InvariantId.PREDICTION_AVAILABILITY,
            passed=False,
            reason="Action selection requires at least one projected current prediction.",
            flow=Flow.STOP,
            validity=Validity.INVALID,
            code="no_predictions_projected",
            details=None,
            evidence=None,
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
                expected_code="current_prediction_available",
                rationale="Projected prediction exists for the selected prediction_key.",
                gate_inputs={"just_written_prediction": None, "has_projected_prediction": True},
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_prediction_availability,
                expected_passed=False,
                expected_flow=Flow.STOP,
                expected_code="no_predictions_projected",
                rationale="No projected predictions exist, so pre-consume must halt.",
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
                expected_code="evidence_links_complete",
                rationale="Post-write append has evidence links and projection is current.",
                gate_inputs={
                    "just_written_prediction": {
                        "key": "scope:test",
                        "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
                    },
                    "has_projected_prediction": True,
                },
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_evidence_link_completeness,
                expected_passed=False,
                expected_flow=Flow.STOP,
                expected_code="missing_evidence_links",
                rationale="Prediction append without evidence links must halt.",
                gate_inputs={
                    "just_written_prediction": {"key": "scope:test", "evidence_refs": []},
                    "has_projected_prediction": True,
                },
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
                expected_code="prediction_outcome_bound",
                rationale="Outcome is bound with prediction_id and numeric error_metric.",
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_prediction_outcome_binding,
                expected_passed=False,
                expected_flow=Flow.STOP,
                expected_code="missing_prediction_id",
                rationale="Outcome without prediction_id is invalid and must halt.",
            ),
        ),
        gate_non_applicable=NonApplicableGateCoverage(
            rationale="This invariant is validated independently and currently not executed by evaluate_invariant_gates.",
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
                expected_code="halt_payload_explainable",
                rationale="STOP candidate provides explainable payload fields.",
            ),
            InvariantScenario(
                name="stop",
                build_context=_build_stop_context_for_explainable_halt_payload,
                expected_passed=False,
                expected_flow=Flow.STOP,
                expected_code="halt_payload_incomplete",
                rationale="STOP candidate missing details/evidence must halt as degraded payload.",
            ),
        ),
        gate_non_applicable=NonApplicableGateCoverage(
            rationale="This invariant runs only during halt validation and is not a direct gate input scenario.",
        ),
    ),
}


MATRIX_CASES = [
    pytest.param(invariant_id, scenario, id=f"{invariant_id.value}:{scenario.name}")
    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
    for scenario in coverage.scenarios
]

INVARIANT_MATRIX_CASES_BY_ID = [
    pytest.param(invariant_id, id=invariant_id.value) for invariant_id in REGISTERED_INVARIANTS
]

MATRIX_SCENARIO_NAMES_BY_INVARIANT = {
    invariant_id: tuple(sorted(scenario.name for scenario in coverage.scenarios))
    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
}

ADMISSIBLE_CASES = [
    pytest.param(invariant_id, scenario, id=f"{invariant_id.value}:{scenario.name}")
    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
    for scenario in coverage.scenarios
    if scenario.expected_flow == Flow.CONTINUE
]

STOP_CASES = [
    pytest.param(invariant_id, scenario, id=f"{invariant_id.value}:{scenario.name}")
    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
    for scenario in coverage.scenarios
    if scenario.expected_flow == Flow.STOP
]


def _assert_result_contract(result: GateDecision) -> None:
    if isinstance(result, Success):
        assert all(out.flow == Flow.CONTINUE for out in result.artifact.pre_consume)
        assert all(out.flow == Flow.CONTINUE for out in result.artifact.post_write)
        assert all(out.flow == Flow.CONTINUE for out in result.artifact.combined)
    else:
        assert isinstance(result, HaltRecord)
        assert result.halt_id.startswith("halt:")
        assert result.invariant_id
        assert result.reason
        assert set(result.to_canonical_payload().keys()) == set(
            HaltRecord.required_payload_fields()
        )


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
    scope = _fixed_prediction_record().scope_key
    projected = project_current(
        _fixed_prediction_record(),
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    continue_gate = evaluate_invariant_gates(
        ep=None,
        scope=scope,
        prediction_key=scope,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": scope,
            "evidence_refs": [{"kind": "jsonl", "ref": "predictions.jsonl@1"}],
        },
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
    assert [out.flow for out in continue_gate.artifact.pre_consume] == [Flow.CONTINUE]
    assert [out.flow for out in continue_gate.artifact.post_write] == [Flow.CONTINUE]
    assert [out.flow for out in continue_gate.artifact.combined] == [Flow.CONTINUE, Flow.CONTINUE]

    assert isinstance(stop_gate, HaltRecord)
    assert stop_gate.stage == "pre-decision:post_write"
    assert stop_gate.invariant_id == InvariantId.EVIDENCE_LINK_COMPLETENESS.value
    assert set(stop_gate.to_canonical_payload().keys()) == set(HaltRecord.required_payload_fields())


def test_prediction_record_json_round_trip() -> None:
    pred = _fixed_prediction_record()
    dumped = pred.model_dump(mode="json")
    reloaded = PredictionRecord.model_validate(dumped)

    assert reloaded == pred


def test_registered_invariant_parameterization_matches_registry() -> None:
    assert set(REGISTERED_INVARIANTS) == set(INVARIANT_RELEASE_GATE_MATRIX)


def test_invariant_identifiers_are_enumerated_and_registered() -> None:
    assert REGISTERED_INVARIANT_IDS == REGISTERED_INVARIANT_IDS_FROM_REGISTRY
    enumerated_identifiers = tuple(invariant.value for invariant in InvariantId)
    assert (
        tuple(InvariantId(identifier) for identifier in enumerated_identifiers)
        == REGISTERED_INVARIANTS
    )


def test_invariant_matrix_release_gate_has_required_coverage() -> None:
    assert set(InvariantId) == set(REGISTERED_INVARIANTS) == set(INVARIANT_RELEASE_GATE_MATRIX)
    assert set(REGISTERED_INVARIANTS) == set(REGISTERED_INVARIANT_BRANCH_BEHAVIORS)

    for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items():
        assert any(s.expected_passed for s in coverage.scenarios), (
            f"{invariant_id.value} has no pass scenario"
        )
        if coverage.supports_stop:
            assert any(not s.expected_passed for s in coverage.scenarios), (
                f"{invariant_id.value} has no stop scenario"
            )


@pytest.mark.parametrize("invariant_id", INVARIANT_MATRIX_CASES_BY_ID)
def test_invariant_matrix_has_explicit_pass_stop_scenarios_per_invariant(
    invariant_id: InvariantId,
) -> None:
    scenario_names = MATRIX_SCENARIO_NAMES_BY_INVARIANT[invariant_id]
    assert scenario_names == ("pass", "stop"), (
        f"{invariant_id.value} must define deterministic pass/stop scenarios; got {scenario_names}"
    )


def test_invariant_matrix_guard_fails_when_registry_gains_uncovered_invariant() -> None:
    missing_in_matrix = set(REGISTERED_INVARIANTS) - set(INVARIANT_RELEASE_GATE_MATRIX)
    stale_matrix_entries = set(INVARIANT_RELEASE_GATE_MATRIX) - set(REGISTERED_INVARIANTS)

    assert not missing_in_matrix, (
        "INVARIANT_RELEASE_GATE_MATRIX is missing registered invariants: "
        + ", ".join(sorted(invariant.value for invariant in missing_in_matrix))
    )
    assert not stale_matrix_entries, (
        "INVARIANT_RELEASE_GATE_MATRIX contains non-registered invariants: "
        + ", ".join(sorted(invariant.value for invariant in stale_matrix_entries))
    )

    uncovered_branch_contracts = set(REGISTERED_INVARIANTS) - set(
        REGISTERED_INVARIANT_BRANCH_BEHAVIORS
    )
    stale_branch_contracts = set(REGISTERED_INVARIANT_BRANCH_BEHAVIORS) - set(REGISTERED_INVARIANTS)
    assert not uncovered_branch_contracts, (
        "REGISTERED_INVARIANT_BRANCH_BEHAVIORS is missing registered invariants: "
        + ", ".join(sorted(invariant.value for invariant in uncovered_branch_contracts))
    )
    assert not stale_branch_contracts, (
        "REGISTERED_INVARIANT_BRANCH_BEHAVIORS contains non-registered invariants: "
        + ", ".join(sorted(invariant.value for invariant in stale_branch_contracts))
    )


def test_replay_analytics_scope_requires_complete_invariant_matrix() -> None:
    missing_coverage = set(REGISTERED_INVARIANTS) - set(INVARIANT_RELEASE_GATE_MATRIX)
    assert REPLAY_ANALYTICS_SCOPE_REQUIRES_COMPLETE_MATRIX is True
    assert not missing_coverage, (
        "Replay analytics scope expansion is blocked until invariant matrix coverage is complete for: "
        + ", ".join(sorted(invariant.value for invariant in missing_coverage))
    )


@pytest.mark.parametrize("invariant_id,scenario", ADMISSIBLE_CASES)
def test_invariant_admissible_branch_is_deterministic(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
) -> None:
    checker = REGISTRY[invariant_id]
    first = checker(scenario.build_context())
    second = checker(scenario.build_context())

    assert first == second
    assert first.passed is True
    assert first.flow == Flow.CONTINUE


@pytest.mark.parametrize("invariant_id,scenario", STOP_CASES)
def test_invariant_stop_branch_is_deterministic_when_supported(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
) -> None:
    checker = REGISTRY[invariant_id]
    first = checker(scenario.build_context())
    second = checker(scenario.build_context())

    assert first == second
    assert first.passed is False
    assert first.flow == Flow.STOP


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
    assert first.code == scenario.expected_code

    normalized = normalize_outcome(first, gate=f"test:{scenario.name}")
    assert normalized.invariant_id == invariant_id.value
    assert normalized.gate == f"test:{scenario.name}"
    assert normalized.passed is scenario.expected_passed
    assert isinstance(normalized.reason, str)
    assert isinstance(normalized.evidence, tuple)


@pytest.mark.parametrize("invariant_id,scenario", MATRIX_CASES)
def test_invariant_matrix_emits_deterministic_artifact_per_branch(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
) -> None:
    checker = REGISTRY[invariant_id]
    first = checker(scenario.build_context())
    second = checker(scenario.build_context())

    first_artifact = {
        "invariant_id": invariant_id.value,
        "scenario": scenario.name,
        "branch": "stop" if first.flow == Flow.STOP else "continue",
        "passed": first.passed,
        "flow": first.flow.value,
        "code": first.code,
        "normalized": normalize_outcome(first, gate=f"matrix:{scenario.name}").__dict__,
    }
    second_artifact = {
        "invariant_id": invariant_id.value,
        "scenario": scenario.name,
        "branch": "stop" if second.flow == Flow.STOP else "continue",
        "passed": second.passed,
        "flow": second.flow.value,
        "code": second.code,
        "normalized": normalize_outcome(second, gate=f"matrix:{scenario.name}").__dict__,
    }

    assert first_artifact == second_artifact
    assert first_artifact["flow"] == scenario.expected_flow.value
    assert first_artifact["passed"] is scenario.expected_passed
    assert first_artifact["code"] == scenario.expected_code


@pytest.mark.parametrize("invariant_id,scenario", MATRIX_CASES)
def test_gate_decisions_and_artifacts_are_deterministic_by_invariant(
    invariant_id: InvariantId,
    scenario: InvariantScenario,
    tmp_path: Path,
) -> None:
    if scenario.gate_inputs is None:
        non_applicable = INVARIANT_RELEASE_GATE_MATRIX[invariant_id].gate_non_applicable
        assert non_applicable is not None
        assert non_applicable.rationale
        pytest.skip(
            f"{invariant_id.value} is not directly evaluated by evaluate_invariant_gates: {non_applicable.rationale}"
        )

    just_written_prediction = scenario.gate_inputs["just_written_prediction"]
    has_projected_prediction = scenario.gate_inputs["has_projected_prediction"]
    expect_halt = scenario.expected_flow == Flow.STOP

    projection = ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00")
    scope_key = _fixed_prediction_record().scope_key
    if has_projected_prediction:
        pred = _fixed_prediction_record()
        projection = project_current(pred, projection)

    first_ep = _make_episode_with_artifacts()
    second_ep = _make_episode_with_artifacts()
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
    assert first_artifact["invariant_context"] == second_artifact["invariant_context"]

    flow_decisions = [check["passed"] for check in first_artifact["invariant_checks"]]
    if just_written_prediction is None:
        assert flow_decisions == ([False, True] if expect_halt else [True])
    elif expect_halt:
        assert flow_decisions == [True, False, True]
    else:
        assert flow_decisions == [True, True]

    if expect_halt:
        assert isinstance(first, HaltRecord)
        assert isinstance(second, HaltRecord)
        assert first.invariant_id == invariant_id.value
        assert second.invariant_id == invariant_id.value
        assert first.halt_id == second.halt_id
        assert first_artifact["kind"] == "halt"
        assert set(first_artifact["halt"]) == set(HaltRecord.required_payload_fields())
        if just_written_prediction is None:
            assert [check["passed"] for check in first_artifact["invariant_checks"]] == [
                False,
                True,
            ]
            assert [check["invariant_id"] for check in first_artifact["invariant_checks"]] == [
                InvariantId.PREDICTION_AVAILABILITY.value,
                InvariantId.EXPLAINABLE_HALT_PAYLOAD.value,
            ]
        else:
            assert [check["passed"] for check in first_artifact["invariant_checks"]] == [
                True,
                False,
                True,
            ]
            assert [check["invariant_id"] for check in first_artifact["invariant_checks"]] == [
                InvariantId.PREDICTION_AVAILABILITY.value,
                InvariantId.EVIDENCE_LINK_COMPLETENESS.value,
                InvariantId.EXPLAINABLE_HALT_PAYLOAD.value,
            ]
    else:
        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert [out.code for out in first.artifact.combined] == [
            out.code for out in second.artifact.combined
        ]
        assert first_artifact["kind"] == "prediction"
        if just_written_prediction is None:
            assert [out.flow for out in first.artifact.combined] == [Flow.CONTINUE]
            assert [check["invariant_id"] for check in first_artifact["invariant_checks"]] == [
                InvariantId.PREDICTION_AVAILABILITY.value,
            ]
        else:
            assert [out.flow for out in first.artifact.combined] == [Flow.CONTINUE, Flow.CONTINUE]
            assert [check["passed"] for check in first_artifact["invariant_checks"]] == [True, True]
            assert [check["invariant_id"] for check in first_artifact["invariant_checks"]] == [
                InvariantId.PREDICTION_AVAILABILITY.value,
                InvariantId.EVIDENCE_LINK_COMPLETENESS.value,
            ]


@pytest.mark.parametrize(
    "invariant_id,scenario_name",
    [
        pytest.param(invariant_id, scenario.name, id=f"{invariant_id.value}:{scenario.name}")
        for invariant_id, coverage in INVARIANT_RELEASE_GATE_MATRIX.items()
        for scenario in coverage.scenarios
        if scenario.gate_inputs is not None
    ],
)
def test_gate_matrix_covers_all_gate_evaluated_invariants(
    invariant_id: InvariantId, scenario_name: str
) -> None:
    assert invariant_id in {
        InvariantId.PREDICTION_AVAILABILITY,
        InvariantId.EVIDENCE_LINK_COMPLETENESS,
    }
    assert scenario_name in {"pass", "stop"}


@pytest.mark.parametrize("invariant_id", INVARIANT_MATRIX_CASES_BY_ID)
def test_gate_matrix_explicitly_marks_non_applicable_gate_coverage(
    invariant_id: InvariantId,
) -> None:
    coverage = INVARIANT_RELEASE_GATE_MATRIX[invariant_id]
    has_gate_scenarios = any(scenario.gate_inputs is not None for scenario in coverage.scenarios)
    if has_gate_scenarios:
        assert coverage.gate_non_applicable is None, (
            f"{invariant_id.value} unexpectedly marked non-applicable"
        )
    else:
        assert coverage.gate_non_applicable is not None, (
            f"{invariant_id.value} must declare non-applicable gate rationale"
        )
        assert coverage.gate_non_applicable.rationale


@pytest.mark.parametrize("invariant_id", INVARIANT_MATRIX_CASES_BY_ID)
def test_each_registered_invariant_is_exercised_by_matrix_parameterization(
    invariant_id: InvariantId,
) -> None:
    coverage = INVARIANT_RELEASE_GATE_MATRIX[invariant_id]
    assert tuple(sorted(s.name for s in coverage.scenarios)) == ("pass", "stop")


@pytest.mark.parametrize("invariant_id", INVARIANT_MATRIX_CASES_BY_ID)
def test_registry_guard_requires_matrix_coverage_for_each_invariant(
    invariant_id: InvariantId,
) -> None:
    assert invariant_id in INVARIANT_RELEASE_GATE_MATRIX, (
        "INVARIANT_RELEASE_GATE_MATRIX must add deterministic pass/stop (or explicit non-applicable gate rationale) "
        f"for new registry invariant: {invariant_id.value}"
    )


def test_post_write_gate_passes_when_evidence_and_projection_current() -> None:
    pred = _fixed_prediction_record()
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
    pred = _fixed_prediction_record()
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
    assert [e.model_dump(mode="json") for e in halt.evidence] == [
        {"kind": "scope", "ref": pred.scope_key}
    ]
    assert halt.retryability is True


def test_halt_artifact_includes_halt_evidence_ref_and_invariant_context(tmp_path: Path) -> None:
    pred = _fixed_prediction_record()
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )
    ep = _make_episode_with_artifacts()

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
    checks = artifact["invariant_checks"]
    assert len(checks) == 3
    assert [check["invariant_id"] for check in checks] == [
        "prediction_availability.v1",
        "evidence_link_completeness.v1",
        "explainable_halt_payload.v1",
    ]
    assert [check["passed"] for check in checks] == [True, False, True]
    assert [check["gate_point"] for check in checks] == [
        "pre-decision:pre_consume",
        "pre-decision:post_write",
        "halt_validation",
    ]
    for check in checks:
        assert set(check.keys()) >= {"gate_point", "invariant_id", "passed", "evidence", "reason"}

    assert checks[1]["evidence"] == [{"kind": "scope", "ref": pred.scope_key}]

    halt_observation = ep.artifacts[1]
    assert halt_observation["artifact_kind"] == "halt_observation"
    assert halt_observation["observation_type"] == "halt"
    assert halt_observation["halt_id"].startswith("halt:")
    assert set(halt_observation.keys()) >= set(HaltRecord.required_payload_fields())
    assert halt_observation["invariant_id"] == "evidence_link_completeness.v1"


def test_append_prediction_and_projection_support_post_write_gate(tmp_path: Path) -> None:
    pred = _fixed_prediction_record()
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
        projection_state=ProjectionState(
            current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"
        ),
        prediction_log_available=True,
        halt_log_path=tmp_path / "halts.jsonl",
    )

    assert isinstance(gate, HaltRecord)
    halt = gate
    assert halt.invariant_id == "prediction_availability.v1"
    assert halt.reason == "Action selection requires at least one projected current prediction."


def test_append_prediction_record_persists_supplied_stable_ids(tmp_path: Path) -> None:
    pred = _fixed_prediction_record()
    prediction_path = tmp_path / "predictions.jsonl"

    append_prediction_record(
        pred,
        prediction_log_path=prediction_path,
        stable_ids={"feature_id": "feat_1", "scenario_id": "scn_1", "step_id": "stp_1"},
    )

    records = [rec for _, rec in read_jsonl(prediction_path)]
    assert records
    for rec in records:
        assert rec["feature_id"] == "feat_1"
        assert rec["scenario_id"] == "scn_1"
        assert rec["step_id"] == "stp_1"


def test_gate_invariants_remain_stable_when_capability_policy_denies_side_effect(
    tmp_path: Path,
) -> None:
    pred = _fixed_prediction_record()
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

    denied = append_prediction_record(
        pred,
        prediction_log_path=tmp_path / "predictions.jsonl",
        halt_log_path=tmp_path / "halts.jsonl",
        projection_state=projected,
        explicit_gate_pass_present=False,
    )
    assert isinstance(denied, HaltRecord)
    assert denied.invariant_id == "capability.invocation.policy.v1"

    halt_rows = [row for _, row in read_jsonl(tmp_path / "halts.jsonl")]
    assert halt_rows[0]["details"]["policy_code"] == "explicit_gate_pass_required"
    assert not (tmp_path / "predictions.jsonl").exists()


def test_evaluate_invariant_gates_persists_halt_with_episode_stable_ids(tmp_path: Path) -> None:
    pred = _fixed_prediction_record()
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    ep = _make_episode_with_artifacts()
    ep.artifacts.append(
        {
            "kind": "stable_ids",
            "feature_id": "feat_1",
            "scenario_id": "scn_1",
            "step_id": "stp_1",
        }
    )

    evaluate_invariant_gates(
        ep=ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={"key": pred.scope_key, "evidence_refs": []},
        halt_log_path=tmp_path / "halts.jsonl",
    )

    ((_, rec),) = list(read_jsonl(tmp_path / "halts.jsonl"))
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
    pred = _fixed_prediction_record()
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
    assert [out.code for out in first.artifact.combined] == [
        out.code for out in second.artifact.combined
    ]


def test_gate_flow_parity_continue_and_stop_payloads(tmp_path: Path) -> None:
    pred = _fixed_prediction_record()
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    continue_ep = _make_episode_with_artifacts()
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

    stop_ep = _make_episode_with_artifacts()
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


def test_evaluate_invariant_gates_rejects_malformed_halt_outcome_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    malformed = InvariantOutcome.model_construct(
        invariant_id=InvariantId.PREDICTION_AVAILABILITY,
        passed=False,
        reason="malformed",
        flow=Flow.STOP,
        validity=Validity.INVALID,
        code="malformed",
        details=None,
        evidence=None,
        action_hints=(),
    )

    monkeypatch.setattr(
        "state_renormalization.engine._run_invariant",
        lambda invariant_id, *, ctx: malformed,
    )

    with pytest.raises(Exception, match="malformed or incomplete"):
        evaluate_invariant_gates(
            ep=None,
            scope="scope:test",
            prediction_key="scope:test",
            projection_state=ProjectionState(
                current_predictions={
                    "scope:test": _fixed_prediction_record()
                },
                updated_at_iso="2026-02-13T00:00:00+00:00",
            ),
            prediction_log_available=True,
        )


def test_evaluate_invariant_gates_emits_invariant_audit_records() -> None:
    pred = _fixed_prediction_record()
    projected = project_current(
        pred,
        ProjectionState(current_predictions={}, updated_at_iso="2026-02-13T00:00:00+00:00"),
    )

    ep = _make_episode_with_artifacts()
    _ = evaluate_invariant_gates(
        ep=ep,
        scope=pred.scope_key,
        prediction_key=pred.scope_key,
        projection_state=projected,
        prediction_log_available=True,
        just_written_prediction={
            "key": pred.scope_key,
            "evidence_refs": [e.model_dump(mode="json") for e in pred.evidence_links],
        },
    )

    outcomes_artifact = ep.artifacts[0]
    assert "invariant_audit" in outcomes_artifact
    assert outcomes_artifact["invariant_audit"][0]["gate_point"].startswith("pre-decision:")
