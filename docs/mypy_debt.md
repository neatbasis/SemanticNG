# Mypy Debt List

Policy boundary:

- **Tier 1 (strict, required pre-commit):** `src/state_renormalization`, `src/core`.
- **Tier 2a (focused contract-sensitive tests):** `tests/test_engine_*.py`, `tests/test_contracts_*.py`, `tests/test_capability_adapter_*.py`, `tests/test_ask_outbox_contracts.py`, `tests/test_predictions_contracts_and_gates.py`.
- **Tier 2b (extended, optional local / CI):** `src`, `tests`.

Canonical tier source is `[tool.semanticng.mypy_tiers]` in `pyproject.toml`.

Temporary suppressions are tracked against a specific tier below.

- **Tier:** Tier 2 only (BDD step glue signatures)
  **Modules:** `src.features.steps.*`, `steps`, `index_steps`, `ontology_steps`.
  **Suppressed:** `disallow_untyped_defs = false`, `disallow_incomplete_defs = false`, `disallow_untyped_decorators = false`, `warn_return_any = false`.
  **Why:** Behave step functions are decorator-driven entrypoints with runtime-provided `context`, table rows, and doc text objects that are not yet modeled by first-party type stubs.
  **Owner:** BDD/Acceptance Test Maintainers.
  **Removal condition:** Add a typed Behave context protocol/stubs for the step API and annotate all step function signatures/decorator use sites so this module override can be deleted.

- **Tier:** Tier 2 only (optional dependency wrapper boundary)
  **Modules:** `semanticng.bdd_compat`, `semanticng.deeponto_compat`.
  **Suppressed:** `warn_return_any = false`.
  **Why:** The wrappers intentionally use importlib-based loading and runtime attribute lookups to keep optional dependencies (`behave`, `deeponto`) out of the rest of the type surface.
  **Owner:** Build & Tooling Maintainers.
  **Removal condition:** Replace dynamic importlib boundary with typed direct imports guarded by installed optional extras (or dedicated typed stubs), then remove this wrapper-only suppression.

## 2026-03 Engine canonical payload typing pass (incremental)

Completed in `src/state_renormalization/engine.py` (core loop boundary):

- Replaced `Mapping[str, Any]` payload wiring in gate/invariant flow with `CanonicalPredictionPayload` alias.
- Added validated payload models for high-traffic canonical payload paths:
  - `WrittenPredictionPayload` (mission-loop `last_written_prediction` contract)
  - `CanonicalHaltPayload` (typed canonical halt payload normalization)
- Refactored payload transformation helpers used by persistence handoff:
  - `_prediction_payload_with_stable_ids`
  - `_prediction_record_event_payload`
  - `_halt_payload_with_stable_ids`
- Replaced cast-based pre-output gate key extraction with typed model access (`last_written_prediction.key`).
- Extended schema selector validation boundary so `_validated_selection` accepts either `SchemaSelection` or a mapping validated via `SchemaSelection.model_validate`.

High-traffic function inventory addressed in this pass:

- `evaluate_invariant_gates(..., just_written_prediction=...)`
- `_evaluate_gate_phase(..., just_written_prediction=...)`
- `_evaluate_invariant_gate_pipeline(..., just_written_prediction=...)`
- `append_prediction_record(...)`
- `append_halt_record(...)`
- `_halt_payload(...)`
- `_validated_selection(...)`

Remaining `Any` hotspots (next module boundary: adapters):

- `src/state_renormalization/adapters/persistence.py`
  - `JsonObj = dict[str, Any]`
  - `_to_jsonable`, `append_jsonl`, `append_prediction*`, `append_ask_outbox_*`, `_canonicalize_halt_payload`, `append_halt`
  - follow-up plan: replace `Any` entrypoints with typed JSON aliases + validated event payload wrappers.


## 2026-03 Graduated test typing rollout

Status updates for the contract-sensitive tranche:

- ✅ Added automatic pytest classification (`contract_sensitive` vs `general_behavior`) in `tests/conftest.py`.
- ✅ Introduced focused Tier 2a mypy command/profile for contract-sensitive tests.
- ✅ Removed targeted `type: ignore` call-arg suppressions in adapter policy-guard tests by annotating callable fakes.
- ✅ Replaced cast-based episode fakes in invariant contract tests with typed `Episode` factory helpers.
- ✅ Replaced malformed-outcome `type: ignore[arg-type]` usage with explicit `InvariantOutcome.model_construct(...)` fixtures where invalid payloads are intentional.
- ⏳ Remaining work: extend fixture/fake annotations to additional high-noise modules outside current contract-sensitive tranche before tightening Tier 2b defaults.
