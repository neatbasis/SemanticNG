# ROADMAP

This roadmap translates the architecture in `ARCHITECTURE.md` into an execution plan organized by horizon and validated by tests. It is intentionally future-leaning while preserving the fail-closed principles already implemented: prediction-first gating, explainable halts, and deterministic projection/replay.

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

### 4) Unified gate pipeline and halt persistence (`status: done`)
- **Owner area/module:** Engine + Invariants + Contracts + Persistence (`src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py` passes.
  - Outcomes verify unified gate behavior (`Flow.CONTINUE`/`Flow.STOP`) and durable explainable halt records.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py`, `tests/test_persistence_jsonl.py`, `tests/test_contracts_halt_record.py`

### 5) Invariant matrix coverage (`status: done`)
- **Owner area/module:** Invariants + Test harness (`src/state_renormalization/invariants.py`, `tests/test_predictions_contracts_and_gates.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py` passes with parameterized coverage across all registered `InvariantId` branches.
  - Outcomes show deterministic explainable-stop behavior and non-applicable markers for each invariant path.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `tests/test_predictions_contracts_and_gates.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`

## Next (planned capabilities)

### 1) Observer authorization contract (`status: planned`)
- **Owner area/module:** Contracts + Engine + Invariants (`src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_observer_frame.py` passes, validating `ObserverFrame` authorization shape and defaults.
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` passes with authorization gate and invariant allowlist behavior enforced in the runtime pipeline.
- **Related files/tests:**
  - Files: `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`
  - Tests: `tests/test_observer_frame.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py`

## Capability status alignment (manifest source-of-truth sync)

- `done`: `prediction_persistence_baseline`, `channel_agnostic_pending_obligation`, `schema_selection_ambiguity_baseline`, `gate_halt_unification`, `invariant_matrix_coverage`.
- `in_progress`: `replay_projection_analytics`.
- `planned`: `observer_authorization_contract`, `capability_invocation_governance`, `repair_aware_projection_evolution`.

## Later (larger architecture goals)

### 1) Replay projection analytics contract (replay-grade projection engine and longitudinal correction analytics; `status: in_progress`)
- **Owner area/module:** Engine + Persistence + Correction artifacts (`src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`)
- **Success criteria (test outcomes):**
  - New replay tests pass, proving `ProjectionState` reconstructed from append-only logs is deterministic across repeated runs and independent process restarts.
  - Multi-episode tests pass, demonstrating correction/cost attribution can be computed from persisted lineage without side channels.
  - Phase scope remains read-only: analytics are derived from persisted prediction/halt/correction lineage only (no side effects, no external integrations).
  - Non-goal for this phase: no policy changes to gating behavior and no online cost accounting mutations during mission execution.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`
  - Tests: extend `tests/test_predictions_contracts_and_gates.py`; add replay/correction-focused tests under `tests/`.

### 2) Capability-invocation governance (policy-aware external actions; `status: planned`)
- **Owner area/module:** Engine + Contracts + Capability adapters (`src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, adapter modules under `src/state_renormalization/adapters/`)
- **Success criteria (test outcomes):**
  - New capability-gating tests pass, showing no externally consequential action executes without a current valid prediction and explicit gate pass.
  - Failure-path tests pass, proving policy violations produce persisted explainable halts and zero side-effect invocation.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, capability adapter files (as added)
  - Tests: add capability governance suites under `tests/` (prediction + halt + side-effect guards).

### 3) Evolution path toward repair-aware projection (without silent mutation; `status: planned`)
- **Owner area/module:** Invariants + Engine (`src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`)
- **Success criteria (test outcomes):**
  - Prototype repair-mode tests pass where repair proposals are emitted as explicit auditable events (never implicit state mutation).
  - Regression tests continue to pass in strict halt-only mode, proving backward compatibility of fail-closed execution.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`
  - Tests: existing `tests/test_predictions_contracts_and_gates.py` plus new repair-mode tests.

## Sequencing gate (enforced branch merge policy)

- No `Later` feature branch merges are allowed until all `Next` capability tests are green in CI.
- Green means every test command listed in the `Next` section completes successfully with no skipped required assertions for gate/halt behavior.
- Any emergency exception must be documented in planning cadence notes with explicit rationale, owner, and rollback/follow-up date.

## Backlog dependency tags

- `Later` item 1 (Replay projection analytics contract): `in_progress` with no `Next` dependency blocker currently recorded in manifest governance files.
- `Later` item 2 (Capability-invocation governance): `planned`; sequence after observer authorization contract to keep authorization semantics stable before external side-effect policy gating.
- `Later` item 3 (Repair-aware projection evolution): `planned`; sequence after replay analytics baselines are stable to preserve auditable repair-event lineage.

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
| `observer_authorization_contract` | `observer_not_authorized` | 6 | 1 | `Next` | contracts/engine | land authorization gating + explainable halt persistence follow-up |
| `replay_projection_analytics` | `prediction_missing_for_effect` | 2 | 4 | `Later` | engine/persistence | keep design prep only until sequencing gate dependencies are met |

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
| `replay_projection_analytics` | met (`status=in_progress`) | partial | partial | 3/5 | Continue focused in-progress replay PRs while preserving append-only and explainable-halt contracts. |
| `observer_authorization_contract` | met (`status=planned`) | partial | partial | 4/5 | Prioritize the next PR to land runtime authorization gating + persisted explainable halt coverage. |
| `capability_invocation_governance` | blocked (sequence after observer authorization) | blocked | missing | 5/5 | Keep design/doc prep only; defer merge work until observer authorization is done. |
| `repair_aware_projection_evolution` | blocked (sequence after replay analytics hardening) | blocked | missing | 3/5 | Draft explicit auditable repair-event contract tests while keeping strict halt-only behavior as default. |

## Guardrails (unchanged until Next milestones are complete)

- Keep JSONL append-only persistence as the reference storage contract until gate/halt unification and invariant matrix completion are green in CI.
- Defer production ML ranking complexity for schema selection until selector contract tests are expanded and stable.
- Avoid broad UX/CLI expansion outside invariant-critical paths until the Next section is complete.
