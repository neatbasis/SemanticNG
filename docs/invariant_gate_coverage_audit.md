# Invariant Coverage Audit (contracts + gates)

## 1) REGISTRY invariant IDs

From `src/state_renormalization/invariants.py::InvariantId` and `src/state_renormalization/invariants.py::REGISTRY`:

1. `authorization.scope.v1`
2. `prediction_availability.v1`
3. `evidence_link_completeness.v1`
4. `prediction_outcome_binding.v1`
5. `explainable_halt_payload.v1`

## 2) Mapping: invariant ID -> relevant tests

| Invariant ID | Relevant test evidence anchors |
|---|---|
| `authorization.scope.v1` | `tests/test_invariants.py::test_authorization_scope_invariant_pass_and_fail_have_deterministic_shape` (direct checker pass/stop for `authorization_scope_allowed` and `authorization_scope_denied`), plus matrix and gate anchors in `tests/test_predictions_contracts_and_gates.py` via `INVARIANT_RELEASE_GATE_MATRIX`, `test_invariant_outcomes_are_deterministic_and_contract_compliant`, `test_invariant_admissible_branch_is_deterministic`, `test_invariant_stop_branch_is_deterministic_when_supported`, and halt-artifact evidence anchoring in `test_authorization_halt_evidence_ref_matches_persisted_halt_row`. |
| `prediction_availability.v1` | `INVARIANT_RELEASE_GATE_MATRIX` defines `pass` (`current_prediction_available`) and `stop` (`no_predictions_projected`), then exercised by `test_invariant_outcomes_are_deterministic_and_contract_compliant`, `test_invariant_admissible_branch_is_deterministic`, `test_invariant_stop_branch_is_deterministic_when_supported`, and other `MATRIX_CASES`-driven tests in `tests/test_predictions_contracts_and_gates.py`. Additional branch audit coverage includes `availability_not_keyed` and `no_current_prediction` via `test_invariant_audit_missing_branch_codes_are_explicitly_covered`. |
| `evidence_link_completeness.v1` | Matrix defines `pass` (`evidence_links_complete`) and `stop` (`missing_evidence_links`), exercised by matrix-parametrized tests in `tests/test_predictions_contracts_and_gates.py`. Additional branch audit coverage includes `evidence_check_not_applicable`, `prediction_log_unavailable`, and `write_before_use_violation` via `test_invariant_audit_missing_branch_codes_are_explicitly_covered`. Direct gate execution anchors include `test_post_write_gate_passes_when_evidence_and_projection_current`, `test_post_write_gate_halts_when_append_evidence_missing`, and `test_append_prediction_and_projection_support_post_write_gate`. |
| `prediction_outcome_binding.v1` | Matrix defines `pass` (`prediction_outcome_bound`) and `stop` (`missing_prediction_id`), exercised by matrix-parametrized invariant tests in `tests/test_predictions_contracts_and_gates.py`. Additional branch audit coverage includes `outcome_binding_not_applicable` and `non_numeric_error_metric` via `test_invariant_audit_missing_branch_codes_are_explicitly_covered`. |
| `explainable_halt_payload.v1` | Matrix defines `pass` (`halt_payload_explainable`) and `stop` (`halt_payload_incomplete`), exercised by matrix-parametrized invariant tests in `tests/test_predictions_contracts_and_gates.py`. Additional branch audit coverage includes `halt_check_not_applicable` via `test_invariant_audit_missing_branch_codes_are_explicitly_covered`. Indirect gate-level anchor: `test_evaluate_invariant_gates_rejects_malformed_halt_outcome_payload`. |

## 3) Pass/stop status per invariant (full/partial/missing)

Status criterion: **full** = all checker pass/stop branches (all branch codes) are covered in listed tests; **partial** = at least one branch covered but not all; **missing** = no branch for that pass/stop side.

| Invariant ID | Pass status | Stop status | Covered branch codes | Missing branch codes |
|---|---|---|---|---|
| `authorization.scope.v1` | **partial** | **full** | pass: `authorization_scope_allowed`; stop: `authorization_scope_denied` | pass: `authorization_not_applicable` |
| `prediction_availability.v1` | **full** | **full** | pass: `current_prediction_available`, `availability_not_keyed`; stop: `no_predictions_projected`, `no_current_prediction` | _none_ |
| `evidence_link_completeness.v1` | **full** | **full** | pass: `evidence_links_complete`, `evidence_check_not_applicable`; stop: `missing_evidence_links`, `prediction_log_unavailable`, `write_before_use_violation` | _none_ |
| `prediction_outcome_binding.v1` | **full** | **full** | pass: `prediction_outcome_bound`, `outcome_binding_not_applicable`; stop: `missing_prediction_id`, `non_numeric_error_metric` | _none_ |
| `explainable_halt_payload.v1` | **full** | **full** | pass: `halt_payload_explainable`, `halt_check_not_applicable`; stop: `halt_payload_incomplete` | _none_ |

## 4) Immediate priorities

1. Add explicit audit coverage for authorization non-applicable pass branch (`authorization_not_applicable`) in `tests/test_predictions_contracts_and_gates.py::test_invariant_audit_missing_branch_codes_are_explicitly_covered` (or an equivalent targeted checker test).
2. Keep this document synchronized whenever `InvariantId`, `REGISTRY`, or checker branch codes change in `src/state_renormalization/invariants.py`.
