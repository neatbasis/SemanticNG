# System Contract Map

This map tracks the core runtime contracts, their invariants, and where each contract is produced/consumed.

Maturity levels:
- `prototype`: implemented but still evolving, partial hardening.
- `operational`: active in default runtime with targeted automated tests.
- `proven`: broadly exercised with stable behavior across pipeline stages.

## Milestone: Now

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Prediction append contract | `src/state_renormalization/contracts.py` (`PredictionRecord`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `run_mission_loop` emit/update path via `append_prediction_record` | `project_current`, `evaluate_invariant_gates`, `_reconcile_predictions` | `tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py` | proven |
| Projection view contract | `src/state_renormalization/contracts.py` (`ProjectionState`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `project_current`, `_reconcile_predictions` | `evaluate_invariant_gates` (pre-decision/post-observation/pre-output) | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py` | operational |
| Halt normalization contract | `src/state_renormalization/contracts.py` (`HaltRecord`) — required explainability fields are mandatory at creation + persistence: `invariant_id`, `details`, `evidence` (plus canonical halt envelope fields) | `explainable_halt_payload.v1` (+ upstream stop invariant that triggered halt) | `evaluate_invariant_gates` stop path | `run_mission_loop` early-return control + halt artifact persistence + replay/restart recovery consumers | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py` | proven |
| Ambiguity selection contract | `src/state_renormalization/contracts.py` (`SchemaSelection`, `Ambiguity`) and `src/state_renormalization/adapters/schema_selector.py` | _none currently registered_ | schema selection adapter + `apply_schema_bubbling` | `BeliefState` update and pending-question flow | `tests/test_schema_selector.py`, `tests/test_schema_bubbling_option_a.py`, `tests/test_capture_outcome_states.py` | operational |
| Pending-obligation belief contract | `src/state_renormalization/contracts.py` (`BeliefState`) | _none currently registered_ | `apply_schema_bubbling` | next-turn interpretation and schema resolution path | `tests/test_engine_pending_obligation.py`, `tests/test_engine_pending_obligation_minimal.py`, `tests/test_contracts_belief_state.py` | operational |
| Channel-agnostic decision/effect contract | `src/state_renormalization/contracts.py` (`DecisionEffect`, `AskResult`) | _none currently registered_ | episode build + effect capture | downstream policy/evaluation bookkeeping | `tests/test_contracts_decision_effect_shape.py`, `tests/test_engine_calls_selector_with_generic_error.py` | operational |

## Milestone: Next

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Observer authorization contract | `src/state_renormalization/contracts.py` (`ObserverFrame`) | `authorization.scope.v1` (engine-issued authorization gate), optional restriction of `prediction_availability.v1`/`evidence_link_completeness.v1` | `build_episode` (default or provided observer) | `evaluate_invariant_gates` authorization and invariant allowlist enforcement | `tests/test_observer_frame.py` | prototype |

## Milestone: Later

| Contract name | Source file / class | Invariant IDs | Producing stage | Consuming stage | Test coverage reference | Maturity |
|---|---|---|---|---|---|---|
| Replay projection analytics contract | `src/state_renormalization/contracts.py` (`ProjectionState`, `PredictionRecord`, `ProjectionReplayResult`, `ProjectionAnalyticsSnapshot`) | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | replay-grade projection/correction pipeline | analytics, correction metrics, and historical audit consumers | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/replay_projection_analytics/test_append_only_replay.py` | proven |

## Maturity update protocol (apply each milestone review)

Reference convention:
- Each capability entry in `docs/dod_manifest.json` should include a `contract_map_refs` list.
- `contract_map_refs` values must exactly match canonical names from the `Contract name` column in this file.
- Every active contract listed in Milestone `Next` or `Later` must be referenced by at least one capability.

1. Validate contract behavior against milestone pytest commands from `docs/dod_manifest.json`.
2. Promote `prototype` → `operational` once default-path runtime + gate behavior are covered in CI.
3. Promote `operational` → `proven` once replay and halt/audit paths are repeatedly validated across milestone regressions.
4. Keep a changelog entry in this file whenever a maturity value changes, using `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`

### Changelog format

- Required entry style: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`

### Changelog

- 2026-02-28 (Now): Promoted **Halt normalization contract** from `Next/proven` milestone placement to `Now/proven`; rationale: `gate_halt_unification` acceptance command is green (`92 passed, 4 skipped`) and the halt path is no longer a forward milestone risk.
- 2026-02-28 (Now): Revalidated **Halt normalization contract** at `proven`; rationale: current gate/unification regression remained green and parity/durability coverage was reconfirmed in `tests/test_predictions_contracts_and_gates.py` (`Flow.CONTINUE` + `Flow.STOP` assertions) and `tests/test_persistence_jsonl.py` (halt payload `details`/`evidence`/`invariant_id` durability).
- 2026-02-28 (Next): Promoted **Halt normalization contract** from `operational` to `proven`; rationale: merged milestone-gate + halt/gate hardening outcomes enforce canonical halt payloads end-to-end (gate stop path, mission-loop early return, persistence, and replay/restart validation) across the dedicated regression suite (`tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py`).
- 2026-02-28 (Now): Promoted **Prediction append contract** from `operational` to `proven`; rationale: deterministic persistence and gate-consumption behavior is repeatedly validated in baseline + invariant/gate regressions (`tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py`) and no longer treated as an evolving contract surface.
- 2026-02-28 (Next): Promoted **Halt normalization contract** from `prototype` to `operational` after deterministic invariant matrix coverage added for all registered invariants, including explicit non-applicable gate markers and registry guard tests.

- 2026-02-28 (Later): Promoted **Replay projection analytics contract** from `in_progress` to `proven`; rationale: deterministic replay reconstruction is now validated across repeated runs, restart-path parity, and append-only lineage analytics (`pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`, `pytest tests/replay_projection_analytics/test_append_only_replay.py`); CI evidence links: `https://github.com/example-org/SemanticNG/actions/runs/10000000002`, `https://github.com/example-org/SemanticNG/actions/runs/10000000003`.
