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

## Next (active refactors: gate/halt unification + halt persistence)

### 1) Unified gate pipeline (pre-consume + post-write invariants)
- **Owner area/module:** Engine + Invariants (`src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py` passes with explicit assertions for both `Flow.CONTINUE` and `Flow.STOP` branches.
  - Tests validate parity of behavior before/after refactor for core gate scenarios (`prediction_write_materialized`, `prediction_append_unverified`).
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`

### 2) Explainable halt contract unification and durable halt records
- **Owner area/module:** Invariants + Contracts + Persistence (`src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/engine.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py` passes with assertions that every STOP includes machine-readable `details`, `evidence`, and invariant identity.
  - New/updated tests assert halt artifacts are persisted and replayable without loss of explainability fields.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `src/state_renormalization/contracts.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/engine.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`, `tests/test_persistence_jsonl.py`

### 3) Invariant matrix completion (all registered invariants exhaustively tested)
- **Owner area/module:** Invariants + Test harness (`src/state_renormalization/invariants.py`, `tests/test_predictions_contracts_and_gates.py`)
- **Success criteria (test outcomes):**
  - `pytest tests/test_predictions_contracts_and_gates.py` passes with parameterized coverage across all `InvariantId` branches.
  - Test suite proves each invariant can deterministically emit either admissible continuation or explainable stop.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`
  - Tests: `tests/test_predictions_contracts_and_gates.py`

## Later (larger architecture goals)

### 1) Replay-grade projection engine and longitudinal correction analytics
- **Owner area/module:** Engine + Persistence + Correction artifacts (`src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`)
- **Success criteria (test outcomes):**
  - New replay tests pass, proving `ProjectionState` reconstructed from append-only logs is deterministic across repeated runs and independent process restarts.
  - Multi-episode tests pass, demonstrating correction/cost attribution can be computed from persisted lineage without side channels.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/contracts.py`
  - Tests: extend `tests/test_predictions_contracts_and_gates.py`; add replay/correction-focused tests under `tests/`.

### 2) Capability-invocation governance (policy-aware external actions)
- **Owner area/module:** Engine + Contracts + Capability adapters (`src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, adapter modules under `src/state_renormalization/adapters/`)
- **Success criteria (test outcomes):**
  - New capability-gating tests pass, showing no externally consequential action executes without a current valid prediction and explicit gate pass.
  - Failure-path tests pass, proving policy violations produce persisted explainable halts and zero side-effect invocation.
- **Related files/tests:**
  - Files: `src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, capability adapter files (as added)
  - Tests: add capability governance suites under `tests/` (prediction + halt + side-effect guards).

### 3) Evolution path toward repair-aware projection (without silent mutation)
- **Owner area/module:** Invariants + Engine (`src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`)
- **Success criteria (test outcomes):**
  - Prototype repair-mode tests pass where repair proposals are emitted as explicit auditable events (never implicit state mutation).
  - Regression tests continue to pass in strict halt-only mode, proving backward compatibility of fail-closed execution.
- **Related files/tests:**
  - Files: `src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`
  - Tests: existing `tests/test_predictions_contracts_and_gates.py` plus new repair-mode tests.

## Guardrails (unchanged until Next milestones are complete)

- Keep JSONL append-only persistence as the reference storage contract until gate/halt unification and invariant matrix completion are green in CI.
- Defer production ML ranking complexity for schema selection until selector contract tests are expanded and stable.
- Avoid broad UX/CLI expansion outside invariant-critical paths until the Next section is complete.
