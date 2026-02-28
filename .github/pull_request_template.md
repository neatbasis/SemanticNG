## Summary

- Describe the change.

## Testing

- List tests/checks run for this PR.

## Milestone pytest commands + adjacent evidence URLs (mandatory)

For every status-transition capability in this PR, include the exact `pytest` command lines from `docs/dod_manifest.json` (verbatim) and place one adjacent `https://...` evidence URL directly below each command line.

<!-- AUTOGEN SECTION: milestone evidence pairs; source=docs/dod_manifest.json; generator=.github/scripts/render_transition_evidence.py -->

<!-- BEGIN AUTOGEN: milestone-evidence -->
### Capability command/evidence blocks (generated from `docs/dod_manifest.json`)

#### Capability: `capability_invocation_governance` (status: `planned`)
```text
pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `channel_agnostic_pending_obligation` (status: `done`)
```text
pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `gate_halt_unification` (status: `done`)
```text
pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `invariant_matrix_coverage` (status: `done`)
```text
pytest tests/test_predictions_contracts_and_gates.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `observer_authorization_contract` (status: `planned`)
```text
pytest tests/test_observer_frame.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `prediction_persistence_baseline` (status: `done`)
```text
pytest tests/test_stable_ids.py tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `repair_aware_projection_evolution` (status: `planned`)
```text
pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_predictions_contracts_and_gates.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `replay_projection_analytics` (status: `done`)
```text
pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

pytest tests/replay_projection_analytics/test_append_only_replay.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```

#### Capability: `schema_selection_ambiguity_baseline` (status: `done`)
```text
pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py
Evidence URL: https://github.com/<org>/<repo>/actions/runs/<run_id>

```
<!-- END AUTOGEN: milestone-evidence -->
