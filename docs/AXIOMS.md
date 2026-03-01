# Repository Governance Axioms

This document defines **repository governance axioms**: project-level, cross-module constraints used to steer architecture, planning, and verification decisions.

> Scope note: this file intentionally avoids restating module-local semantic axioms.
> - Core irreducible/domain-agnostic axioms live in [`src/core/AXIOMS.md`](../src/core/AXIOMS.md).
> - SemanticNG application-layer axioms for `PredictionRecord`/state transitions live in [`src/semanticng/AXIOMS.md`](../src/semanticng/AXIOMS.md).

## Axiom list

- **A1 — Append-only lineage determinism.** For equivalent append-only event lineage, `project_current`/replay must produce equivalent projection and gate outcomes.
- **A2 — Prediction-before-consequence.** Any consequential effect requires a prior durable prediction artifact bound to the same scope.
- **A3 — Explainable halt completeness.** Every stop path MUST emit halt payloads containing `invariant_id`, `details`, and `evidence` with contract-valid structure.
- **A4 — Authorization-scoped invariant evaluation.** Invariant checks execute only within observer-authorized scope and allowlisted invariant IDs.
- **A5 — Contract-shape-before-interpretation.** Contract schema validity is a precondition for interpretation, policy selection, and execution.
- **A6 — No silent repair mutation.** Repair flows may propose/record corrections but must not silently mutate runtime truth outside explicit lineage artifacts.
- **A7 — Replay-grade auditability.** Runtime decisions must remain reconstructible from persisted contracts, halts, and invariant-check evidence.
- **A8 — Deterministic gate semantics.** Invariant gate evaluation must resolve deterministically to continue/stop with machine-readable evidence.
- **A9 — Evidence-carrying claims.** Assertions in durable records must include evidence references or explicit unknown/pending markers.
- **A10 — Executable-governance supremacy.** Mission/governance claims are binding only when encoded in contracts/invariants and enforced by automated tests.

## Mapping: governance axiom → mission principle → invariants → contract map → enforcing tests

| axiom_id | Mission principle(s) | Invariant IDs | Contract-map row(s) | Enforcing tests |
|---|---|---|---|---|
| A1 | Decisions replayable/auditable | `prediction_availability.v1`, `evidence_link_completeness.v1` | Prediction append contract; Projection view contract; Replay projection analytics contract | `tests/test_replay_projection_determinism.py`, `tests/replay_projection_analytics/test_append_only_replay.py`, `tests/test_engine_projection_mission_loop.py` |
| A2 | Prediction precedes action | `prediction_availability.v1` | Prediction append contract; Projection view contract | `tests/test_predictions_contracts_and_gates.py`, `tests/test_persistence_jsonl.py` |
| A3 | Decisions explainable post-hoc | `explainable_halt_payload.v1` (+ triggering stop invariant) | Halt normalization contract | `tests/test_contracts_halt_record.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_engine_projection_mission_loop.py` |
| A4 | Contract-bounded, safe behavior | `authorization.scope.v1` (+ allowlisted gate invariants) | Observer authorization contract | `tests/test_observer_frame.py`, `tests/test_invariants.py`, `tests/test_predictions_contracts_and_gates.py` |
| A5 | Contracts define capability boundaries | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | Prediction append contract; Projection view contract; Halt normalization contract | `tests/test_contracts_halt_record.py`, `tests/test_predictions_contracts_and_gates.py`, `tests/test_contracts_decision_effect_shape.py` |
| A6 | Evidence-grounded, no opaque mutation | `prediction_outcome_binding.v1` | Replay projection analytics contract | `tests/test_repair_mode_projection.py`, `tests/test_replay_projection_restart_contracts.py` |
| A7 | Replayable + auditable over time | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1` | Replay projection analytics contract; Halt normalization contract | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_restart_contracts.py`, `tests/test_persistence_projection_lineage_iterator.py` |
| A8 | Predict-first guardrail correctness | `prediction_availability.v1`, `evidence_link_completeness.v1`, `explainable_halt_payload.v1`, `authorization.scope.v1` | Projection view contract; Halt normalization contract; Observer authorization contract | `tests/test_predictions_contracts_and_gates.py`, `tests/test_invariants.py` |
| A9 | Evidence anchors every claim | `evidence_link_completeness.v1` | Prediction append contract; Projection view contract | `tests/test_invariants.py`, `tests/test_predictions_contracts_and_gates.py` |
| A10 | Behavior defined by executable specification | _all registered invariants_ | _all active contract rows with milestone coverage_ | `pytest` baseline + milestone manifest commands (`tests/test_dod_manifest.py`) |

## Design boundary decisions (governance scope)

Until a governance axiom in this document is revised in the same PR, the following are out of bounds:

- Introducing non-deterministic projection/replay behavior for identical lineage input (violates A1/A8).
- Executing consequential effects without durable pre-effect prediction artifacts (violates A2).
- Returning/recording stop outcomes without a contract-valid explainability triple (`invariant_id`, `details`, `evidence`) (violates A3).
- Evaluating gated invariants outside observer authorization scope/allowlist (violates A4).
- Interpreting capability payloads before contract-shape validation (violates A5).
- Applying repair updates as hidden in-memory mutations that bypass append-only lineage artifacts (violates A6/A7).
- Replacing invariant/policy decisions with opaque heuristics where contract or invariant checks are available (violates A5/A10).

## How to use this doc in PRs

For any PR that changes behavior under `src/state_renormalization/`:

1. Include an **Impacted axioms** subsection in the PR description listing affected IDs (for example: `A2`, `A3`, `A8`).
2. Cite at least one enforcing test per impacted axiom (existing or newly added).
3. If behavior would violate an existing axiom, update this file in the same PR and describe the revision rationale.
4. Keep `docs/system_contract_map.md` contract rows and maturity/testing references aligned with impacted axioms.

Template snippet:

```md
### Impacted axioms
- A3 (Explainable halt completeness): reinforced stop-path normalization in gate exit branch.
  - Evidence: tests/test_contracts_halt_record.py::test_halt_record_requires_normalized_explainability_fields
- A4 (Authorization-scoped invariant evaluation): restricted gate evaluation to observer allowlist.
  - Evidence: tests/test_observer_frame.py::test_evaluate_invariant_gates_respects_observer_invariant_allowlist
```
