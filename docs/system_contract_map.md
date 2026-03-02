# System Contract Map

This map tracks the core runtime contracts, their invariants, and where each contract is produced/consumed.

For canonical completion-layer criteria and capability enablement dependencies, see `docs/definition_of_complete.md`.

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
| Replay projection analytics contract | `src/state_renormalization/contracts.py` (`ProjectionState`, `PredictionRecord`, `ProjectionReplayResult`) | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | replay-grade projection/correction pipeline | analytics, correction metrics, and historical audit consumers | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/replay_projection_analytics/test_append_only_replay.py` | operational |
| Observer authorization contract | `src/state_renormalization/contracts.py` (`ObserverFrame`) | `authorization.scope.v1` (engine-issued authorization gate), optional restriction of `prediction_availability.v1`/`evidence_link_completeness.v1` | `build_episode` (default or provided observer) | `evaluate_invariant_gates` authorization and invariant allowlist enforcement | `tests/test_observer_frame.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py` | operational |

## Milestone: Next

`capability_invocation_governance` is tracked as `in_progress` in `docs/dod_manifest.json` with the canonical acceptance command pack (`pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`).

`repair_aware_projection_evolution` remains `planned` but with a shipped baseline already covered by tests: `tests/test_repair_mode_projection.py`, `tests/test_repair_events_auditability.py`, `tests/test_replay_projection_determinism.py`, and `tests/test_replay_projection_restart_contracts.py` demonstrate repair proposal/resolution auditability, deterministic replay, and no silent prediction-record mutation.

No new contract rows are promoted in this milestone yet; active maturity remains anchored to Milestone `Now` until capability completion criteria are met. Missing acceptance gates for repair-aware projection completion are explicitly tracked in `docs/dod_manifest.json` (`status_semantics.missing_acceptance_gates`) and must be backed by CI evidence before any status promotion.

## Maturity update protocol (apply each milestone review)

Reference convention:
- Each capability entry in `docs/dod_manifest.json` should include a `contract_map_refs` list.
- `contract_map_refs` values must exactly match canonical names from the `Contract name` column in this file.
- Every active contract listed in Milestone `Next` or `Later` must be referenced by at least one capability.

1. Validate contract behavior against milestone pytest commands from `docs/dod_manifest.json`.
2. Promote `prototype` → `operational` once default-path runtime + gate behavior are covered in CI.
3. Promote `operational` → `proven` only when the transition is tied to explicit manifest capability IDs and replay/halt/audit paths are repeatedly validated.
4. Keep a changelog entry in this file whenever a maturity value changes, using `- YYYY-MM-DD (Milestone): capability_id=<id>; <contract> <from> -> <to>; rationale. https://<evidence-link>` (must include at least one `https://` URL).

### Changelog format

- Required entry style: `- YYYY-MM-DD (Milestone): capability_id=<id>; <contract> <from> -> <to>; rationale. https://<evidence-link>`

### Changelog

- 2026-03-02 (Next): capability_id=capability_invocation_governance; Channel-agnostic decision/effect contract operational -> operational; capability promoted to `in_progress` with policy-guard command-pack evidence, while maturity remains unchanged until `done` criteria are met. https://github.com/neatbasis/SemanticNG/actions/runs/19027411847
- 2026-03-02 (Later): capability_id=repair_aware_projection_evolution; Replay projection analytics contract operational -> operational; baseline repair-event behavior is test-backed and shipped, but completion remains `planned` pending additional acceptance gates and dependency closure. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201

- 2026-02-28 (Now): capability_id=replay_projection_analytics; Replay projection analytics contract in_progress -> operational; replay reconstruction/determinism/restart and append-only replay suites now serve as the baseline evidence set, aligned with manifest transition to `done`. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=observer_authorization_contract; Observer authorization contract prototype -> operational; authorization scope gating and invariant allowlist behavior are validated in default runtime contract and gate suites, and milestone posture is locked to `Now` as completed dependency coverage. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=gate_halt_unification; Halt normalization contract operational -> proven; merged gate + halt hardening enforces canonical halt payloads end-to-end across mission-loop, persistence, and replay/restart validation. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=prediction_persistence_baseline; Prediction append contract operational -> proven; deterministic persistence and gate-consumption behavior is repeatedly validated in baseline and invariant/gate regressions. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=invariant_matrix_coverage; Projection view contract prototype -> operational; deterministic invariant-matrix coverage now validates all registered InvariantId branches with explicit non-applicable markers, matching manifest `done`/ROADMAP `Now` canonical status. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._
