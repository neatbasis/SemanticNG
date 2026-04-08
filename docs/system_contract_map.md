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
| Prediction append contract | `src/state_renormalization/contracts.py` (`PredictionRecord`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `run_mission_loop` emit/update path via `append_prediction_record` (policy handoff boundary: `_prediction_append_policy_handoff`) | `project_current`, `evaluate_invariant_gates`, `_reconcile_predictions` | `tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py` | proven |
| Projection view contract | `src/state_renormalization/contracts.py` (`ProjectionState`) | `prediction_availability.v1`, `evidence_link_completeness.v1` | `project_current`, `_reconcile_predictions` | `evaluate_invariant_gates` (pre-decision/post-observation/pre-output) | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py` | operational |
| Halt normalization contract | `src/state_renormalization/contracts.py` (`HaltRecord`) — required explainability fields are mandatory at creation + persistence: `invariant_id`, `details`, `evidence` (plus canonical halt envelope fields) | `explainable_halt_payload.v1` (+ upstream stop invariant that triggered halt) | `evaluate_invariant_gates` stop path | `run_mission_loop` early-return control + halt artifact persistence + replay/restart recovery consumers | `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py` | proven |
| Ambiguity selection contract | `src/state_renormalization/contracts.py` (`SchemaSelection`, `Ambiguity`) and `src/state_renormalization/adapters/schema_selector.py` | _none currently registered_ | schema selection adapter + `apply_schema_bubbling` | `BeliefState` update and pending-question flow | `tests/test_schema_selector.py`, `tests/test_schema_bubbling_option_a.py`, `tests/test_capture_outcome_states.py` | operational |
| Pending-obligation belief contract | `src/state_renormalization/contracts.py` (`BeliefState`) | _none currently registered_ | `apply_schema_bubbling` | next-turn interpretation and schema resolution path | `tests/test_engine_pending_obligation.py`, `tests/test_engine_pending_obligation_minimal.py`, `tests/test_contracts_belief_state.py` | operational |
| Channel-agnostic decision/effect contract | `src/state_renormalization/contracts.py` (`DecisionEffect`, `AskResult`) | _none currently registered_ | episode build + effect capture | downstream policy/evaluation bookkeeping | `tests/test_contracts_decision_effect_shape.py`, `tests/test_engine_calls_selector_with_generic_error.py` | proven |
| Replay projection analytics contract | `src/state_renormalization/contracts.py` (`ProjectionState`, `PredictionRecord`, `ProjectionReplayResult`) | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | replay-grade projection/correction pipeline | analytics, correction metrics, and historical audit consumers | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/replay_projection_analytics/test_append_only_replay.py` | proven |
| Observer authorization contract | `src/state_renormalization/contracts.py` (`ObserverFrame`) | `authorization.scope.v1` (engine-issued authorization gate), optional restriction of `prediction_availability.v1`/`evidence_link_completeness.v1` | `build_episode` (default or provided observer) | `evaluate_invariant_gates` authorization and invariant allowlist enforcement | `tests/test_observer_frame.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py` | operational |

## Milestone: Next

`capability_invocation_governance` is tracked as `done` in `docs/dod_manifest.json` with the canonical acceptance command pack (`pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`).

`repair_aware_projection_evolution` is tracked as `done` with repair-event and replay suites remaining active as non-regression coverage: `tests/test_repair_mode_projection.py`, `tests/test_repair_events_auditability.py`, `tests/test_replay_projection_determinism.py`, and `tests/test_replay_projection_restart_contracts.py`.

Capability statuses are synchronized to manifest `done` states with CI evidence links attached; contract maturity remains unchanged in this update.

## Runtime Concept Taxonomy (State and Decision Contracts)

This section is the runtime-facing authority for concept roles used by `src/state_renormalization/*` and related behavioral contract tests. Ontology alignment is recorded as runtime mapping status, not equivalence.

### Concept role classification

| Concept | Runtime role | Runtime authority anchors | Alignment status | Non-equivalence note |
|---|---|---|---|---|
| `MissionContract` | Mission execution contract and scheduling envelope for mission-loop decisions | `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py` (`run_mission_loop`) | mapped, not equivalent | Governance capability IDs do not define mission runtime semantics. |
| `BeliefState` | Turn-local interpretation and ambiguity state for pending obligations | `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py` (`apply_schema_bubbling`) | mapped, not equivalent | `BeliefState` is not `ProjectionState`. |
| `ProjectionState` | Projection/replay-facing prediction and mission status view | `src/state_renormalization/contracts.py`, `src/state_renormalization/read_model.py`, replay tests | mapped, not equivalent | `ProjectionState` is not `BeliefState`. |
| `Observation` | Normalized observed input envelope used by mission-loop processing | `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py` (`ingest_observation`) | mapped, not equivalent | Observation normalization is runtime-scoped, not ontology identity authority. |
| `DecisionEffect` | Emitted decision outcome/effect record for downstream evaluation and persistence | `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py` (`attach_decision_effect`) | mapped, not equivalent | Effect envelope is execution-local; not a canonical ontology decision class. |
| `InvariantOutcome` | Invariant evaluation result used to continue/defer/halt loop progression | `src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py` (`evaluate_invariant_gates`; `_evaluate_gate_invariant_phase`, `_select_gate_outcome_phase`) | local validation artifact | `InvariantOutcome` does not equal persisted halt artifact. |
| `HaltRecord` | Persisted explainable stop artifact for replay/audit lineage | `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py` | ontology-mappable only with qualifiers | `HaltRecord` does not equal `InvariantOutcome`. |
| `EvidenceRef` | Evidence lineage reference attached to runtime/persisted artifacts | `src/state_renormalization/contracts.py`, persistence and replay tests | ontology-mappable only with qualifiers | Evidence linkage is contract-governed execution metadata. |
| `SchemaSelection` / `Ambiguity` | Runtime schema disambiguation output for state shaping | `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/schema_selector.py`, `src/state_renormalization/engine.py` (`_resolve_schema_selection`, `SchemaSelectorPort`) | mapped, not equivalent | Ambiguity handling is runtime selection behavior, not ontology identity resolution authority. |

### Field-level stabilization status

Status categories: `stabilize now`, `local only`, `mapped, not equivalent`, `defer`.

#### `BeliefState` field notes

- `updated_at_iso`: `stabilize now` (canonical runtime timestamp qualifier).
- `ambiguity_state`, `active_schemas`, `schema_confidence`, `ambiguities_active`: `mapped, not equivalent` (ontology-influenced but runtime interpretation-specific).
- `belief_version`, `pending_about`, `pending_question`, `pending_attempts`, `last_utterance_type`, `last_status`, `consecutive_no_response`: `local only` (execution control/retry/session artifacts).
- `bindings`: `defer` (typing not yet stable; runtime read/write boundary anchors are `_write_belief_bindings` for writes and `_binding_reminder_slot_values`/`_binding_mission_draft` for reads in `src/state_renormalization/engine.py`).

#### `ProjectionState` field notes

- `updated_at_iso`: `stabilize now` (canonical runtime timestamp qualifier).
- `current_predictions`, `prediction_history`, `active_missions`, `deferred_missions`, `completed_missions`, `last_comparison_at_iso`: `mapped, not equivalent` (projection/replay application view, not ontology identity model).
- `correction_metrics`: `local only` (runtime correction instrumentation artifact).

#### `MissionContract` field notes

- `kind`, `lineage_refs`, `created_at_iso`, `updated_at_iso`: `stabilize now` (core mission contract and lineage/time qualifiers).
- `mission_identity`, `entity_ref`, `schedule_policy`, `completion_mode`, `status`, `next_prompt_at`: `mapped, not equivalent` (runtime mission semantics with ontology/project qualifiers).
- `mission_id`, `idempotency_key`: `local only` (non-ontology execution identifiers for control/idempotency).

#### `Observation` field notes

- `t_observed_iso`: `stabilize now` (canonical observation-time qualifier).
- `type`, `text`, `source`: `mapped, not equivalent` (runtime observation envelope semantics).
- `observation_id`: `local only` (execution-local identifier).

## Purpose-Stack Linkage

Runtime linkage is defined as an execution chain, not ontology equivalence:

1. Mission principle intent is declared in capability/governance artifacts (`docs/dod_manifest.json`, `docs/definition_of_complete.md`).
2. Runtime capability execution is implemented via mission-loop/state-renormalization contracts and engine paths (`src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`).
3. Invariant sets are evaluated in runtime policy code (`src/state_renormalization/invariants.py`) and surfaced as `InvariantOutcome`.
4. Artifact obligations are enforced through runtime contract shapes and persistence envelopes (for example `HaltRecord` explainability fields in `src/state_renormalization/contracts.py` and persistence adapter behavior).
5. Governance checks validate required coupling and promotion conditions (`scripts/ci/*`, `docs/process/quality_stage_commands.json`, promotion tests).

Linkage constraints:
- Governance capability IDs are governance/control identifiers and are not interchangeable with runtime capability strings.
- Runtime contract artifacts (`InvariantOutcome`, `HaltRecord`, `DecisionEffect`) are linked but non-equivalent types with separate authority roles.
- Step-layer execution success is evidence of behavior coverage, not runtime authority ownership.

## Capability-Plane Mapping (Initial Instantiated Subset)

This table instantiates a minimal active subset of cross-plane mappings. It is a mapping artifact, not an ontology-equivalence claim.

| Ontology capability concept (project label) | Governance capability ID (`docs/dod_manifest.json`) | Runtime capability string anchor(s) | Relation type | Non-equivalence note |
|---|---|---|---|---|
| Intent disambiguation and schema-grounded mission extraction | `schema_selection_ambiguity_baseline` | `clarify.reminder`; `intent.mission_create` | many runtime schema strings map into one governance capability | Runtime schema strings are execution-local selectors and do not define ontology capability identity. |
| Observer-scoped authorization gating | `observer_authorization_contract` | `authorization.scope.v1` | runtime invariant/policy string anchors governance capability checks | Invariant ID strings are runtime policy anchors, not ontology capability identifiers. |
| Explainable halt envelope governance | `gate_halt_unification` | `explainable_halt_payload.v1` | runtime invariant string maps to halt-governance capability intent | Runtime halt invariant string does not unify with governance capability ID semantics. |
| Prediction persistence and evidence-link substrate | `prediction_persistence_baseline` | `prediction_availability.v1`; `evidence_link_completeness.v1` | one governance capability maps to a paired runtime invariant anchor set | Runtime invariant IDs are execution policy anchors and do not by themselves define ontology capability identity. |
| Replay/projection lineage analytics | `replay_projection_analytics` | `prediction_availability.v1`; `evidence_link_completeness.v1`; `explainable_halt_payload.v1` | one governance capability maps to a multi-anchor runtime replay invariant set | Replay invariant anchors constrain runtime projection correctness, not ontology-equivalent capability identity. |
| Invariant matrix branch coverage governance | `invariant_matrix_coverage` | `prediction_availability.v1`; `evidence_link_completeness.v1`; `explainable_halt_payload.v1`; `authorization.scope.v1` | governance coverage capability maps to runtime invariant ID coverage set | Coverage-governance capability ID is not interchangeable with any single runtime invariant string. |

## Step-Layer Authority Boundary

`src/features/steps/*` and `src/semanticng/step_state.py` are executable test/harness adapters. They may orchestrate scenarios and fixtures, but canonical runtime authority remains in `src/state_renormalization/*`.

Boundary rules:
- Step-layer logic may express scenario intent and setup policy for behavioral verification.
- Step-layer code must not be treated as the canonical owner of runtime decision/state contracts.
- Canonical contract and invariant authority resides in runtime modules and their contract tests (`tests/test_*contracts*`, `tests/test_*invariants*`, mission-loop contract suites).
- Non-equivalence: step-layer executable behavior does not imply canonical runtime authority.

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

- 2026-03-02 (Next): capability_id=capability_invocation_governance; Channel-agnostic decision/effect contract operational -> proven; capability status synchronized to `done` with policy-guard command-pack CI evidence. https://github.com/neatbasis/SemanticNG/actions/runs/19027411847
- 2026-03-02 (Later): capability_id=repair_aware_projection_evolution; Replay projection analytics contract operational -> proven; capability status synchronized to `done` with acceptance command-pack CI evidence linked in the manifest. https://github.com/neatbasis/SemanticNG/actions/runs/19041234567

- 2026-02-28 (Now): capability_id=replay_projection_analytics; Replay projection analytics contract in_progress -> operational; replay reconstruction/determinism/restart and append-only replay suites now serve as the baseline evidence set, aligned with manifest transition to `done`. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=observer_authorization_contract; Observer authorization contract prototype -> operational; authorization scope gating and invariant allowlist behavior are validated in default runtime contract and gate suites, and milestone posture is locked to `Now` as completed dependency coverage. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=gate_halt_unification; Halt normalization contract operational -> proven; merged gate + halt hardening enforces canonical halt payloads end-to-end across mission-loop, persistence, and replay/restart validation. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=prediction_persistence_baseline; Prediction append contract operational -> proven; deterministic persistence and gate-consumption behavior is repeatedly validated in baseline and invariant/gate regressions. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201
- 2026-02-28 (Now): capability_id=invariant_matrix_coverage; Projection view contract prototype -> operational; deterministic invariant-matrix coverage now validates all registered InvariantId branches with explicit non-applicable markers, matching manifest `done`/ROADMAP `Now` canonical status. https://github.com/neatbasis/SemanticNG/actions/runs/18994531201

_Last regenerated from manifest: 2026-04-08T16:13:25Z (UTC)._
