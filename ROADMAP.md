# ROADMAP

This roadmap tracks the state-renormalization work as executable behavior. Every item is tied to concrete modules and explicit test-based done conditions so progress is measurable.

## 1. Shipped (verified by tests)

### 1.1 Schema selection and ambiguity bubbling baseline
- **Modules/files:** `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/schema_selector.py`, `src/state_renormalization/contracts.py`.
- **Primary tests:** `tests/test_schema_selector.py`, `tests/test_schema_bubbling_option_a.py`, `tests/test_capture_outcome_states.py`, `tests/test_engine_calls_selector_with_generic_error.py`.
- **Done condition (test terms):**
  - `pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py` passes, proving selector interface stability (`error` kwarg), unresolved ambiguity handling, and artifact emission.

### 1.2 Core contract normalization (channel-agnostic naming)
- **Modules/files:** `src/state_renormalization/contracts.py`, `src/state_renormalization/engine.py`.
- **Primary tests:** `tests/test_contracts_belief_state.py`, `tests/test_contracts_decision_effect_shape.py`, `tests/test_engine_pending_obligation.py`, `tests/test_engine_pending_obligation_minimal.py`.
- **Done condition (test terms):**
  - `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py` passes, confirming generic field names and pending-obligation behavior remain stable.

### 1.3 Deterministic identity and persistence foundation
- **Modules/files:** `src/state_renormalization/stable_ids.py`, `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/engine.py`.
- **Primary tests:** `tests/test_stable_ids.py`, `tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py`.
- **Done condition (test terms):**
  - `pytest tests/test_stable_ids.py tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py` passes, verifying deterministic IDs, JSONL append/read semantics, and prediction write/projection contract behavior.

## 2. In progress

### 2.1 Engine gates refactor hardening
- **Refactor target files:** `src/state_renormalization/engine.py`, `src/state_renormalization/invariants.py`.
- **Scope:** Continue isolating gate evaluation flow and stop semantics so pre-consume/post-write checks are easier to evolve without changing episode behavior.
- **Done condition (test terms):**
  - `pytest tests/test_predictions_contracts_and_gates.py` passes with explicit coverage of both pass and halt branches (`prediction_write_materialized`, `prediction_append_unverified`).
  - New/updated tests (same file or adjacent gate-focused test file) must assert explainable STOP behavior linked to `InvariantId.H0_EXPLAINABLE_HALT`.

### 2.2 Invariant flow tightening
- **Refactor target files:** `src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`.
- **Scope:** Make invariant outcomes consistently evidence-rich and action-oriented so degraded/invalid flows are debuggable and composable.
- **Done condition (test terms):**
  - Gate/invariant tests assert STOP outcomes include both `details` and `evidence`, and that missing explainability is surfaced by `halt_not_explainable`.
  - Existing invariant-related assertions in `tests/test_predictions_contracts_and_gates.py` remain green after refactor.

### 2.3 Persistence artifact guarantees
- **Refactor target files:** `src/state_renormalization/adapters/persistence.py`, `src/state_renormalization/engine.py`.
- **Scope:** Harden append metadata and retrievability conventions for prediction evidence references used by gates.
- **Done condition (test terms):**
  - `pytest tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py` passes with assertions that evidence refs are emitted in stable `file@offset` form and remain consumable through JSONL readers.

## 3. Planned

### P0 — Formal invariant test matrix
- **Priority:** Highest.
- **Files to extend:** `tests/test_predictions_contracts_and_gates.py`, `tests/test_persistence_jsonl.py`, `src/state_renormalization/invariants.py`.
- **Acceptance criteria (test terms):**
  - Add parameterized tests for every invariant code path in `InvariantId` registry.
  - A single command `pytest tests/test_predictions_contracts_and_gates.py` must cover all `Flow.STOP` and `Flow.CONTINUE` outcomes with explicit code assertions.

### P1 — Projection/persistence integration scenarios
- **Priority:** High.
- **Files to extend:** `src/state_renormalization/engine.py`, `src/state_renormalization/adapters/persistence.py`, `tests/test_predictions_contracts_and_gates.py`.
- **Acceptance criteria (test terms):**
  - Add multi-write integration tests asserting monotonic offsets and consistent `ProjectionState.current_predictions` updates over successive predictions.
  - `pytest tests/test_predictions_contracts_and_gates.py` must pass with at least one multi-turn append/projection case.

### P2 — Schema-selection contract robustness
- **Priority:** Medium.
- **Files to extend:** `src/state_renormalization/adapters/schema_selector.py`, `src/state_renormalization/engine.py`, `tests/test_capture_outcome_states.py`, `tests/test_schema_selector.py`.
- **Acceptance criteria (test terms):**
  - Add negative tests for malformed selector responses and broaden ambiguity shape assertions.
  - `pytest tests/test_capture_outcome_states.py tests/test_schema_selector.py` passes while preserving the current channel-agnostic selector signature.

### P3 — End-to-end executable documentation alignment
- **Priority:** Medium.
- **Files to align:** `README.md`, `tests/README.md`, selected tests under `tests/`.
- **Acceptance criteria (test terms):**
  - Document canonical smoke-test command groups used in this roadmap.
  - CI/readme smoke set (`pytest tests/test_contracts_belief_state.py tests/test_schema_selector.py tests/test_predictions_contracts_and_gates.py`) passes and is documented in both README files.

## 4. Out of scope for now

These boundaries prevent accidental scope creep while refactors above are active.

- Replacing JSONL persistence with external databases or streaming infrastructure (`src/state_renormalization/adapters/persistence.py`).
  - **Re-entry done condition:** only reconsider when current JSONL contract tests (`tests/test_persistence_jsonl.py`, `tests/test_predictions_contracts_and_gates.py`) are fully green and invariant matrix milestone P0 is complete.

- Building a production-grade schema-ranking ML pipeline beyond current naive selector (`src/state_renormalization/adapters/schema_selector.py`).
  - **Re-entry done condition:** only after schema contract suites (`tests/test_schema_selector.py`, `tests/test_capture_outcome_states.py`, `tests/test_schema_bubbling_option_a.py`) are stable and expanded.

- Broad CLI/app UX expansion unrelated to state-renormalization invariants (`src/features/**`, `src/features/steps/**`).
  - **Re-entry done condition:** only after engine/invariant/persistence milestones above are accepted by passing targeted pytest sets.

- Non-essential ontology/modeling experiments outside the tested runtime path (`ideas/`, exploratory `.feature` additions without tests).
  - **Re-entry done condition:** new experiments must first propose test coverage under `tests/` that captures runtime impact.
