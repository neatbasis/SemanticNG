# System Contract Map

This map tracks the core runtime contracts, their invariants, and where each contract is produced/consumed.

Maturity levels:
- `prototype`: implemented but still evolving, partial hardening.
- `operational`: active in default runtime with targeted automated tests.
- `proven`: broadly exercised with stable behavior across pipeline stages.

## Milestone: Now

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Prediction append contract | `src/state_renormalization/contracts.py` (`PredictionRecord`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `run_mission_loop` emit/update path via `append_prediction_record` | `project_current`, `evaluate_invariant_gates`, `_reconcile_predictions` | `tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py` | operational |
| Projection view contract | `src/state_renormalization/contracts.py` (`ProjectionState`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `project_current`, `_reconcile_predictions` | `evaluate_invariant_gates` (pre-decision/post-observation/pre-output) | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py` | operational |
| Ambiguity selection contract | `src/state_renormalization/contracts.py` (`SchemaSelection`, `Ambiguity`) and `src/state_renormalization/adapters/schema_selector.py` | _none currently registered_ | schema selection adapter + `apply_schema_bubbling` | `BeliefState` update and pending-question flow | `tests/test_schema_selector.py`, `tests/test_schema_bubbling_option_a.py`, `tests/test_capture_outcome_states.py` | operational |
| Pending-obligation belief contract | `src/state_renormalization/contracts.py` (`BeliefState`) | _none currently registered_ | `apply_schema_bubbling` | next-turn interpretation and schema resolution path | `tests/test_engine_pending_obligation.py`, `tests/test_engine_pending_obligation_minimal.py`, `tests/test_contracts_belief_state.py` | operational |
| Channel-agnostic decision/effect contract | `src/state_renormalization/contracts.py` (`DecisionEffect`, `AskResult`) | _none currently registered_ | episode build + effect capture | downstream policy/evaluation bookkeeping | `tests/test_contracts_decision_effect_shape.py`, `tests/test_engine_calls_selector_with_generic_error.py` | operational |

## Milestone: Next

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Halt normalization contract | `src/state_renormalization/contracts.py` (`HaltRecord`) — required explainability fields are mandatory at creation + persistence: `invariant_id`, `details`, `evidence` (plus canonical halt envelope fields) | `explainable_halt_payload.v1` (+ upstream stop invariant that triggered halt) | `evaluate_invariant_gates` stop path | `run_mission_loop` early-return control + halt artifact persistence | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py` | operational |
| Observer authorization contract | `src/state_renormalization/contracts.py` (`ObserverFrame`) | `authorization.scope.v1` (engine-issued authorization gate), optional restriction of `prediction_availability.v1`/`evidence_link_completeness.v1` | `build_episode` (default or provided observer) | `evaluate_invariant_gates` authorization and invariant allowlist enforcement | `tests/test_observer_frame.py` | prototype |

## Milestone: Later

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Replay projection analytics contract | `src/state_renormalization/contracts.py` (`ProjectionState`, `PredictionRecord`, `ProjectionReplayResult`) | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | replay-grade projection/correction pipeline | analytics, correction metrics, and historical audit consumers | `tests/test_replay_projection_analytics.py` | in_progress |

## Maturity update protocol (apply each milestone review)

1. Validate contract behavior against milestone pytest commands from `docs/dod_manifest.json`.
2. Promote `prototype` → `operational` once default-path runtime + gate behavior are covered in CI.
3. Promote `operational` → `proven` once replay and halt/audit paths are repeatedly validated across milestone regressions.
4. Keep a changelog entry in this file whenever a maturity value changes, using `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`

### Changelog format

- Required entry style: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`

### Changelog

- 2026-02-28 (Next): Promoted **Halt normalization contract** from `prototype` to `operational` after deterministic invariant matrix coverage added for all registered invariants, including explicit non-applicable gate markers and registry guard tests.
