# Invariant Coverage Audit (contracts + gates)

## 1) REGISTRY invariant IDs

From `src/state_renormalization/invariants.py::REGISTRY`:

1. `prediction_availability.v1`
2. `evidence_link_completeness.v1`
3. `prediction_outcome_binding.v1`
4. `explainable_halt_payload.v1`

## 2) Mapping: invariant ID -> test cases in `tests/test_predictions_contracts_and_gates.py`

| Invariant ID | Matrix scenarios | Direct/targeted gate tests |
|---|---|---|
| `prediction_availability.v1` | `INVARIANT_RELEASE_GATE_MATRIX` defines `pass` (`current_prediction_available`) and `stop` (`no_predictions_projected`), then exercised by `test_invariant_outcomes_are_deterministic_and_contract_compliant`, `test_invariant_admissible_branch_is_deterministic`, `test_invariant_stop_branch_is_deterministic_when_supported`, and other `MATRIX_CASES`-driven tests. | `test_pre_consume_gate_halts_without_any_projected_predictions`, `test_gate_branch_parity_and_deterministic_halt_selection` |
| `evidence_link_completeness.v1` | Matrix defines `pass` (`evidence_links_complete`) and `stop` (`missing_evidence_links`), exercised by matrix-parametrized tests. | `test_post_write_gate_passes_when_evidence_and_projection_current`, `test_post_write_gate_halts_when_append_evidence_missing`, `test_append_prediction_and_projection_support_post_write_gate`, `test_halt_artifact_includes_halt_evidence_ref_and_invariant_context` |
| `prediction_outcome_binding.v1` | Matrix defines `pass` (`prediction_outcome_bound`) and `stop` (`missing_prediction_id`), exercised by matrix-parametrized invariant tests. Marked gate-non-applicable in this file. | No dedicated `evaluate_invariant_gates` test in this file (explicitly marked non-applicable for gate execution). |
| `explainable_halt_payload.v1` | Matrix defines `pass` (`halt_payload_explainable`) and `stop` (`halt_payload_incomplete`), exercised by matrix-parametrized invariant tests. Marked gate-non-applicable in this file. | Indirect halt validation coverage in `test_evaluate_invariant_gates_rejects_malformed_halt_outcome_payload` |

## 3) Pass/stop status per invariant (full/partial/missing)

Status criterion: **full** = all checker pass/stop branches (all branch codes) are covered in this test file; **partial** = at least one branch covered but not all; **missing** = no branch for that pass/stop side.

| Invariant ID | Pass status | Stop status | Covered branch codes | Missing branch codes |
|---|---|---|---|---|
| `prediction_availability.v1` | **partial** | **partial** | pass: `current_prediction_available`; stop: `no_predictions_projected` | pass: `availability_not_keyed`; stop: `no_current_prediction` |
| `evidence_link_completeness.v1` | **partial** | **partial** | pass: `evidence_links_complete`; stop: `missing_evidence_links` | pass: `evidence_check_not_applicable`; stop: `prediction_log_unavailable`, `write_before_use_violation` |
| `prediction_outcome_binding.v1` | **partial** | **partial** | pass: `prediction_outcome_bound`; stop: `missing_prediction_id` | pass: `outcome_binding_not_applicable`; stop: `non_numeric_error_metric` |
| `explainable_halt_payload.v1` | **partial** | **full** | pass: `halt_payload_explainable`; stop: `halt_payload_incomplete` | pass: `halt_check_not_applicable`; stop: _none_ |

## 4) Immediate priorities for missing branch tests

Ordered by risk to correctness + branch fan-out:

1. **`evidence_link_completeness.v1` stop branches**
   - Add tests for `prediction_log_unavailable` and `write_before_use_violation`.
   - Why first: these are high-impact gate-halting conditions in post-write flow and currently untested in this file.

2. **`prediction_availability.v1` missing stop branch**
   - Add `no_current_prediction` (non-empty projection with mismatched `prediction_key`).
   - Why second: direct pre-consume safety gate, easy to regress when key-selection logic changes.

3. **`prediction_outcome_binding.v1` stop branch**
   - Add `non_numeric_error_metric`.
   - Why third: contract integrity for outcome ingestion; currently only missing-id is covered.

4. **Non-applicable pass branches**
   - Add explicit non-applicable pass checks for:
     - `prediction_availability.v1`: `availability_not_keyed`
     - `evidence_link_completeness.v1`: `evidence_check_not_applicable`
     - `prediction_outcome_binding.v1`: `outcome_binding_not_applicable`
     - `explainable_halt_payload.v1`: `halt_check_not_applicable`
   - Why fourth: lower operational risk than stop branches, but improves completeness and documents intended no-op behavior.
