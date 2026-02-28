## Summary

- Describe the change.

## Testing

- List tests/checks run for this PR.

## Milestone pytest commands + CI evidence (mandatory)

For every status-transition capability in this PR, keep the exact command/evidence adjacency shown below: one `Evidence: https://...` line immediately under each command line.

```text
# Capability: prediction_persistence_baseline
pytest tests/test_stable_ids.py tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: channel_agnostic_pending_obligation
pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: schema_selection_ambiguity_baseline
pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: gate_halt_unification
pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: observer_authorization_contract
pytest tests/test_observer_frame.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: replay_projection_analytics
pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/replay_projection_analytics/test_append_only_replay.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: invariant_matrix_coverage
pytest tests/test_predictions_contracts_and_gates.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: capability_invocation_governance
pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

# Capability: repair_aware_projection_evolution
pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py
Evidence: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

- [ ] I confirmed adjacency formatting was preserved (each command line is immediately followed by its own `Evidence: https://...` evidence line).
