# ROADMAP

This roadmap translates the architecture in `ARCHITECTURE.md` into an execution plan organized by horizon and validated by tests. It is intentionally future-leaning while preserving the fail-closed principles already implemented: prediction-first gating, explainable halts, and deterministic projection/replay.

Canonical completion gates and enablement dependencies are defined in `docs/definition_of_complete.md`.

Cross-sprint execution sequencing, capability dependency leverage, and maturity-path exit criteria are tracked in `docs/sprint_plan_5x.md`.

Governance artifacts are updated only after passing evidence exists (CI artifact/report links first, then roadmap/manifest/contract-map synchronization).

## Five-sprint objective alignment (execution brief)

1. **Sprint 1:** one high-impact `capability_invocation_governance` boundary slice with halt semantics + evidence reference.
2. **Sprint 2:** same governance path hardened for allow/deny/failure edge cases + normalized audit payload.
3. **Sprint 3:** minimal usable `repair_aware_projection_evolution` live flow with lineage/replay scenario.
4. **Sprint 4:** finalize deferred contract fields (`schema_id`, `source`) + deterministic/back-compat coverage.
5. **Sprint 5:** promote based on evidence, then refresh manifest/contract-map/roadmap in lockstep.

## Now (already implemented + verified tests)

### 1) Prediction-first contracts and deterministic persistence baseline
- **Owner area/module:** Contracts + Engine + Persistence (`src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/stable_ids.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_stable_ids.py tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py` passes.
  - Outcomes verify deterministic IDs, append/read JSONL stability, and prediction write/projection behavior.
- **Related files/tests:**
  - Files: `src/state_renormalization/stable_ids.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/engine.py`
  - Tests: `tests/test_stable_ids.py`, `tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py`

### 2) Channel-agnostic contract normalization and pending-obligation behavior
- **Owner area/module:** Contracts + Engine (`src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py` passes.
  - Outcomes verify generic artifact shapes and stable pending-obligation semantics.
- **Related files/tests:**
  - Files: `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`
  - Tests: `tests/test_contracts_belief_state.py`, `tests/test_contracts_decision_effect_shape.py`, `tests/test_engine_pending_obligation.py`, `tests/test_engine_pending_obligation_minimal.py`

### 3) Schema selection + ambiguity bubbling contract baseline
- **Owner area/module:** Selector Adapter + Engine (`src/state_renormalization/adapters/schema_selector.py`, `src/state_renormalization/engine.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py` passes.
  - Outcomes verify selector interface compatibility (`error` kwarg), unresolved ambiguity capture, and consistent artifact emission.
- **Related files/tests:**
  - Files: `src/state_renormalization/adapters/schema_selector.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`
  - Tests: `tests/test_schema_selector.py`, `tests/test_schema_bubbling_option_a.py`, `tests/test_capture_outcome_states.py`, `tests/test_engine_calls_selector_with_generic_error.py`

### 4) Unified gate pipeline and halt persistence (manifest: `gate_halt_unification`)
- **Owner area/module:** Engine + Invariants + Contracts + Persistence (`src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py` passes.
  - Outcomes verify unified gate behavior (`Flow.CONTINUE`/`Flow.STOP`) and durable explainable halt records.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py`

### 5) Invariant matrix coverage (manifest: `invariant_matrix_coverage`)
- **Owner area/module:** Invariants + Test harness (`src/state_renormalization/invariants.py`, `tests/test_predictions_contracts_and_gates.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py` passes with parameterized coverage across all registered `InvariantId` branches.
  - Outcomes show deterministic explainable-stop behavior and non-applicable markers for each invariant path.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `tests/test_predictions_contracts_and_gates.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`

### 6) Replay projection analytics contract (replay-grade projection engine and longitudinal correction analytics; manifest: `replay_projection_analytics`)
- **Owner area/module:** Engine + Persistence + Correction artifacts (`src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`)
- **Success criteria (test outcomes):**
  - Replay tests pass, proving `ProjectionState` reconstructed from append-only logs is deterministic across repeated runs and independent process restarts.
  - Multi-episode replay tests pass, demonstrating correction/cost attribution can be computed from persisted lineage without side channels.
  - Scope remains read-only: analytics are derived from persisted prediction/halt/correction lineage only (no side effects, no external integrations).
  - No policy changes to gating behavior and no online cost accounting mutations during mission execution in this completed phase.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`, `tests/test_persistence_jsonl.py`, `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/test_prediction_outcome_binding.py`, `tests/replay_projection_analytics/test_append_only_replay.py`

### 7) Observer authorization contract (manifest: `observer_authorization_contract`)
- **Owner area/module:** Contracts + Engine + Invariants (`src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_observer_frame.py` passes, validating `ObserverFrame` authorization shape and defaults.
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` passes with authorization gate and invariant allowlist behavior enforced in the runtime pipeline.
- **Related files/tests:**
  - Files: `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`
  - Tests: `tests/test_observer_frame.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py`

## Next (promotion checkpoint)

`capability_invocation_governance` has advanced to `in_progress` in the manifest because its acceptance command pack is now actively used as a promotion gate in CI. `repair_aware_projection_evolution` remains `planned`, but its baseline repair-event behavior is already shipped and test-backed; remaining scope is explicitly tracked as missing acceptance gates plus dependency closure (`capability_invocation_governance` = `done`).

## Capability status alignment (manifest source-of-truth sync)

- `done`: `prediction_persistence_baseline`, `channel_agnostic_pending_obligation`, `schema_selection_ambiguity_baseline`, `gate_halt_unification`, `invariant_matrix_coverage`, `replay_projection_analytics`, `observer_authorization_contract`.
- `in_progress`: `capability_invocation_governance` (promotion started; policy-aware side-effect gate coverage is active, but completion criteria for done are not yet closed).
- `planned`: `repair_aware_projection_evolution` (baseline shipped and test-backed; full completion still blocked by dependency closure and missing acceptance gates documented in `docs/dod_manifest.json`).

## Later (larger architecture goals)

### 1) Capability-invocation governance (policy-aware external actions; manifest: `capability_invocation_governance`, currently `in_progress`)
- **Owner area/module:** Engine + Contracts + Capability adapters (`src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, adapter modules under `src/state_renormalization/adapters/`)
- **Success criteria (test outcomes):**
  - Sprint 1 boundary-slice tests pass with explicit halt semantics and linked evidence reference before doc promotion updates.
  - Sprint 2 edge-case tests pass for allow/deny/failure outcomes with normalized audit payload assertions.
  - New capability-gating tests pass, showing no externally consequential action executes without a current valid prediction and explicit gate pass.
  - Failure-path tests pass, proving policy violations produce persisted explainable halts and zero side-effect invocation.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, capability adapter files (as added)
  - Tests: `tests/test_capability_invocation_governance.py`, `tests/test_capability_adapter_policy_guards.py`, `tests/test_predictions_contracts_and_gates.py`.

### 2) Evolution path toward repair-aware projection (without silent mutation; manifest: `repair_aware_projection_evolution`, currently `planned`)
- **Owner area/module:** Invariants + Engine (`src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`)
- **Baseline shipped behavior (already present + test-backed):**
  - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py` passes, validating repair proposal/resolution emission, lineage traceability, immutable repair-event contracts, and explicit no-mutation guarantees for prediction records.
  - Related replay suites (`pytest tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/replay_projection_analytics/test_append_only_replay.py`) pass, validating deterministic reconstruction across restart branches with repair-compatible analytics behavior.
- **Remaining scope for full completion (status still `planned`):**
  - Missing acceptance gate pack A (contract evolution/back-compat): `pytest tests/test_schema_contract_evolution.py tests/test_replay_backward_compatibility.py` (not yet implemented in-repo).
  - Missing acceptance gate pack B (multi-turn and acceptance-policy hardening): `pytest tests/test_repair_mode_projection_multiturn.py tests/test_repair_acceptance_policy.py` (not yet implemented in-repo).
  - Dependency gate remains open: `capability_invocation_governance` must reach `done` before promotion from `planned`.
- **Evidence policy:**
  - Do not promote status until both missing acceptance packs exist, pass in CI, and are linked in `docs/dod_manifest.json` evidence entries; baseline tests alone are treated as shipped behavior evidence, not full-completion evidence.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`
  - Tests: `tests/test_repair_mode_projection.py`, `tests/test_repair_events_auditability.py`, `tests/test_replay_projection_determinism.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/replay_projection_analytics/test_append_only_replay.py`, `tests/test_predictions_contracts_and_gates.py`.

## Sequencing gate (enforced branch merge policy)

- No `Later` feature branch merges are allowed until all `Next` capability tests are green in CI.
- Green means every test command listed in the `Next` section completes successfully with no skipped required assertions for gate/halt behavior.
- Any emergency exception must be documented in planning cadence notes with explicit rationale, owner, and rollback/follow-up date.

## Backlog dependency tags

- `Later` item 1 (`replay_projection_analytics`): see `docs/dod_manifest.json` for canonical status; maintain replay analytics suites as non-regression gates while sequencing `Next` governance contracts.
- `Next`/promotion item (`capability_invocation_governance`): dependency on `observer_authorization_contract` is met per `docs/dod_manifest.json`; promotion is currently `in_progress` and gated by policy-side CI command-pack evidence.
- `Later` item 3 (`repair_aware_projection_evolution`): sequence after `replay_projection_analytics` and `capability_invocation_governance` per canonical dependency map in `docs/sprint_plan_5x.md`.


## Canonical dependency statements (capability-ID only)

- `capability_invocation_governance` depends on: `observer_authorization_contract`, `invariant_matrix_coverage`, `channel_agnostic_pending_obligation`.
- `repair_aware_projection_evolution` depends on: `capability_invocation_governance`, `replay_projection_analytics`.

## Planning cadence

- Reserve majority sprint/iteration capacity for `Next` milestones until all `Next` items are complete and green in CI.
- Track any allocation exception explicitly in cadence logs (date, scope, reason, approver, and timeboxed re-entry to `Next`).
- Reconfirm dependency tags and sequencing gate status at each planning checkpoint before accepting `Later` scope.

### Weekly CI failure review (lightweight evidence loop)

- Run a weekly 30-minute review that groups CI failures by both `capability_id` and `invariant_id` (from halt details/test metadata).
- Produce a compact rollup table with: failure count, first-seen date, latest-seen date, and owning roadmap horizon (`Next` or `Later`).
- Treat this rollup as the default planning input; feature requests can add context but cannot override unresolved high-frequency failures without documented rationale.

#### Weekly review output template

| capability_id | invariant_id | failures (7d) | recurrence rank | mapped roadmap section | owner | action |
| --- | --- | --- | --- | --- | --- | --- |
| `observer_authorization_contract` | `observer_not_authorized` | 6 | 1 | `Now` | contracts/engine | keep authorization gating + explainable halt persistence coverage green as a non-regression signal |
| `replay_projection_analytics` | `prediction_missing_for_effect` | 2 | 4 | `Later` | engine/persistence | maintain deterministic replay analytics regressions as a stability baseline while `Next` items are prioritized |

#### Recurring-cause tracking and roadmap mapping

- Maintain a running "Top recurring causes" list sourced from the weekly rollup and sorted by 4-week failure concentration.
- Map each recurring cause directly to one roadmap section:
  - `Next`: causes tied to active gate/halt, invariant, or authorization milestones.
  - `Later`: causes tied to blocked capabilities that remain dependency-gated.
- Re-map causes during each checkpoint if dependency status changes (for example, a `Later` cause can move to `Next` once sequencing prerequisites are met).

#### Priority update rule (failure concentration first)

- Planning priority is determined by failure concentration, not by breadth of incoming feature requests.
- Default ordering rule:
  1. Highest 4-week recurring failure cause mapped to `Next`.
  2. Next highest `Next` cause with unresolved invariant/test gaps.
  3. Only after top `Next` causes are actively addressed, consider `Later` discovery/design work.
- Any override requires a roadmap note capturing evidence, approver, and expiry date.

#### Roadmap decision notes (required record)

- At each planning checkpoint, add a short decision note with:
  - Date/checkpoint identifier.
  - Top 3 recurring failure causes (with counts and `capability_id`/`invariant_id`).
  - Chosen priority changes (`Next` vs `Later`) and explicit rationale.
  - Deferred items and re-evaluation date.
- Keep these notes in this roadmap file so prioritization remains auditable and evidence-driven over time.

##### Decision notes log (append-only)

| Date | Evidence snapshot (top recurring causes) | Priority decision | Notes/owner |
| --- | --- | --- | --- |
| _TBD_ | _Populate from weekly review rollup_ | _Set `Next` focus by highest failure concentration_ | _Record approver + recheck date_ |

### Planning checkpoint capability table

Use this short table at each planning checkpoint to pick exactly one next PR scope.

| Capability ID | Dependency status (met/blocked) | Governance readiness (manifest+roadmap+contract-map aligned) | Test evidence completeness | Risk-reduction score | Recommended next action |
| --- | --- | --- | --- | --- | --- |
| `replay_projection_analytics` | met (`status=done`) | aligned | complete | 2/5 | Keep replay analytics tests green as non-regression guardrails while sequencing capability invocation governance. |
| `observer_authorization_contract` | met (`status=done`) | aligned | complete | 4/5 | Maintain authorization gate/invariant allowlist tests as non-regression guardrails. |
| `capability_invocation_governance` | met (observer authorization dependency complete) | partial (promotion in progress) | partial | 5/5 | Continue in-progress promotion: keep policy-aware side-effect gate suites green and close remaining `done` criteria. |
| `repair_aware_projection_evolution` | blocked (requires `capability_invocation_governance` = `done`) | partial (baseline shipped; full gate pack missing) | baseline complete / completion gates missing | 3/5 | Keep status at `planned`; retain shipped repair-event tests as baseline evidence and add missing acceptance command packs before promotion. |

## Guardrails (unchanged until Next milestones are complete)

- Keep JSONL append-only persistence as the reference storage contract until gate/halt unification and invariant matrix completion are green in CI.
- Defer production ML ranking complexity for schema selection until selector contract tests are expanded and stable.
- Avoid broad UX/CLI expansion outside invariant-critical paths until the Next section is complete.

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._
