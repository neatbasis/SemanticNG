# Mypy Debt List

Policy boundary:

- **Tier 1 (strict, required pre-commit):** `src/state_renormalization`, `src/core`.
- **Tier 2a (focused contract-sensitive tests):** `tests/test_engine_*.py`, `tests/test_contracts_*.py`, `tests/test_capability_adapter_*.py`, `tests/test_ask_outbox_contracts.py`, `tests/test_predictions_contracts_and_gates.py`.
- **Tier 2b (extended, optional local / CI):** `src`, `tests`.

Canonical tier source is `[tool.semanticng.mypy_tiers]` in `pyproject.toml`.

Temporary suppressions are tracked against a specific tier below.

## Current suppression inventory (authoritative)

| File/module | Suppression/error code | Owner | Created date | Target removal sprint | Blocker |
| --- | --- | --- | --- | --- | --- |
| `src.features.steps.*` | `disallow_untyped_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `src.features.steps.*` | `disallow_incomplete_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `src.features.steps.*` | `disallow_untyped_decorators = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Behave decorators are runtime-driven and currently untyped. |
| `src.features.steps.*` | `warn_return_any = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Step glue returns transitively depend on untyped Behave objects. |
| `steps` | `disallow_untyped_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `steps` | `disallow_incomplete_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `steps` | `disallow_untyped_decorators = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Behave decorators are runtime-driven and currently untyped. |
| `steps` | `warn_return_any = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Step glue returns transitively depend on untyped Behave objects. |
| `index_steps` | `disallow_untyped_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `index_steps` | `disallow_incomplete_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `index_steps` | `disallow_untyped_decorators = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Behave decorators are runtime-driven and currently untyped. |
| `index_steps` | `warn_return_any = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Step glue returns transitively depend on untyped Behave objects. |
| `ontology_steps` | `disallow_untyped_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `ontology_steps` | `disallow_incomplete_defs = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Missing typed Behave context protocol and decorator stubs for step signatures. |
| `ontology_steps` | `disallow_untyped_decorators = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Behave decorators are runtime-driven and currently untyped. |
| `ontology_steps` | `warn_return_any = false` | BDD/Acceptance Test Maintainers | 2026-03-01 | Sprint 7 | Step glue returns transitively depend on untyped Behave objects. |
| `semanticng.bdd_compat` | `warn_return_any = false` | Build & Tooling Maintainers | 2026-03-01 | Sprint 8 | Runtime importlib boundaries for optional dependencies are not typed yet. |
| `semanticng.deeponto_compat` | `warn_return_any = false` | Build & Tooling Maintainers | 2026-03-01 | Sprint 8 | Runtime importlib boundaries for optional dependencies are not typed yet. |
| `tests` / `tests.*` | `strict = false` | Testing Infrastructure Maintainers | 2026-03-01 | Sprint 10 | Contract-sensitive tranche is strict-ready, but full test tree still has legacy fixture/fake typing gaps. |
| `tests` / `tests.*` | `disallow_any_generics = false` | Testing Infrastructure Maintainers | 2026-03-01 | Sprint 10 | Tests still use generic runtime fixtures/fakes that require progressive annotation cleanup. |
| `tests` / `tests.*` | `check_untyped_defs = false` | Testing Infrastructure Maintainers | 2026-03-01 | Sprint 10 | Test modules remain readability-first while helper/fake protocols are being formalized. |
| `tests` / `tests.*` | `disallow_untyped_defs = false` | Testing Infrastructure Maintainers | 2026-03-01 | Sprint 10 | Test fixtures and helper factories need explicit signatures before strict re-enable. |
| `tests` / `tests.*` | `warn_return_any = false` | Testing Infrastructure Maintainers | 2026-03-01 | Sprint 10 | Test factories currently expose transitional `Any` payloads in non-contract test modules. |

Use the suppression inventory script to regenerate/review this table before release:

```bash
python .github/scripts/mypy_override_inventory.py --format markdown
```

## Sprint-level KPIs

| KPI | Baseline (Sprint 5) | Sprint 6 target | Sprint 7 target | Sprint 8 target | Sprint 9 target | Sprint 10 target |
| --- | --- | --- | --- | --- | --- | --- |
| Remove suppression entries from `tool.mypy.overrides` | 0 removed | Remove >=2 | Remove >=8 | Remove >=10 cumulative | Remove >=14 cumulative | Remove all planned-to-remove suppressions (>=18 cumulative) |
| Reduce `Any` count in engine/adapters paths (`src/state_renormalization`) | 100% baseline from Sprint 5 audit | -10% | -25% | -40% | -55% | -70% |
| Shrink disabled error-code/rule set across overrides | 11 disabled rules | <=10 | <=8 | <=6 | <=4 | <=2 |
| Keep suppression inventory visibility current in CI | Manual snapshots only | Add inventory script | Enforce script in release evidence | Weekly inventory trend artifact | Delta report in sprint handoff | Release checklist gate with debt-delta sign-off |

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
