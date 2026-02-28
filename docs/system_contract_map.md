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
| Capability invocation policy gate contract | `src/state_renormalization/contracts.py` (`CapabilityAdapterGate`) + `src/state_renormalization/engine.py` policy denial flow | `capability.invocation.policy.v1` | capability adapter invocation path (`append_prediction_record`, Ask outbox emission paths) | persistence adapters + mission-loop halt/audit consumers | `tests/test_capability_invocation_governance.py`, `tests/test_capability_adapter_policy_guards.py`, `tests/test_capability_adapter_surface_policy_guards.py` | operational |
| Ask outbox capability contract | `src/state_renormalization/contracts.py` (`AskOutboxRequestArtifact`, `AskOutboxResponseArtifact`) + `src/state_renormalization/adapters/persistence.py` outbox appenders | _none currently registered_ | ask request/response emission (`maybe_request_intervention`, freshness-triggered ask flow) | replay projection + intervention audit consumers | `tests/test_ask_outbox_contracts.py`, `tests/test_replay_projection_analytics.py`, `tests/test_predictions_contracts_and_gates.py` | operational |
| Observation staleness policy contract | `src/state_renormalization/contracts.py` (`ObservationFreshnessPolicyContract`, `ObservationFreshnessDecision`) + `src/state_renormalization/engine.py` (`evaluate_observation_freshness`) | _none currently registered_ | observation freshness evaluation + staleness-trigger decisioning | Ask outbox request path + policy artifact consumers | `tests/test_predictions_contracts_and_gates.py`, `tests/test_ask_outbox_contracts.py` | operational |
| Replay projection analytics contract | `src/state_renormalization/contracts.py` (`ProjectionState`, `PredictionRecord`, `ProjectionReplayResult`) | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | replay-grade projection/correction pipeline | analytics, correction metrics, and historical audit consumers | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/replay_projection_analytics/test_append_only_replay.py` | operational |
| Observer authorization contract | `src/state_renormalization/contracts.py` (`ObserverFrame`) | `authorization.scope.v1` (engine-issued authorization gate), optional restriction of `prediction_availability.v1`/`evidence_link_completeness.v1` | `build_episode` (default or provided observer) | `evaluate_invariant_gates` authorization and invariant allowlist enforcement | `tests/test_observer_frame.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py` | operational |

## Milestone: Next

_No contracts currently staged in `Next`; Observer authorization is fully promoted in Milestone `Now` and tracked as a completed dependency for downstream governance capabilities._

## Maturity update protocol (apply each milestone review)

Reference convention:
- Each capability entry in `docs/dod_manifest.json` should include a `contract_map_refs` list.
- `contract_map_refs` values must exactly match canonical names from the `Contract name` column in this file.
- Every active contract listed in Milestone `Next` or `Later` must be referenced by at least one capability.

1. Validate contract behavior against milestone pytest commands from `docs/dod_manifest.json`.
2. Promote `prototype` → `operational` once default-path runtime + gate behavior are covered in CI.
3. Promote `operational` → `proven` once replay and halt/audit paths are repeatedly validated across milestone regressions.
4. Keep a changelog entry in this file whenever a maturity value changes, using `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale. https://<evidence-link>` (must include at least one `https://` URL).

### Changelog format

- Required entry style: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale. https://<evidence-link>`

### Changelog

- 2026-02-28 (Now): Observation staleness policy contract prototype -> operational; freshness-policy decisioning and Ask-request handoff now run in default mission-loop policy paths with deterministic artifact emission. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): Ask outbox capability contract prototype -> operational; canonical Ask request/response artifact shapes are validated and replay consumers ingest outbox events as first-class persisted artifacts. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): Capability invocation policy gate contract prototype -> operational; adapter-level policy gates enforce deny-by-default side-effect blocking with explainable halt persistence on policy violations. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201

- 2026-02-28 (Now): Replay projection analytics contract in_progress -> operational; replay reconstruction/determinism/restart and append-only replay suites now serve as the baseline evidence set, aligned with manifest transition to `done`. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): Observer authorization contract prototype -> operational; authorization scope gating and invariant allowlist behavior are validated in default runtime contract and gate suites, and milestone posture is locked to `Now` as completed dependency coverage. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): Halt normalization contract operational -> proven; merged gate + halt hardening enforces canonical halt payloads end-to-end across mission-loop, persistence, and replay/restart validation. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): Prediction append contract operational -> proven; deterministic persistence and gate-consumption behavior is repeatedly validated in baseline and invariant/gate regressions. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Next): Halt normalization contract prototype -> operational; deterministic invariant-matrix coverage added explicit non-applicable markers and registry guard assertions. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
