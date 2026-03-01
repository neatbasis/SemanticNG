# SemanticNG Axioms

This document defines application-layer axioms for `src/semanticng` that refine the core axioms in `src/core/AXIOMS.md` for `PredictionRecord` and state transitions.

## S1 — PredictionRecord-scoped state-space

SemanticNG state is the tuple of persisted `PredictionRecord` lineage plus its derived projection.

- Every consequential transition must be representable as an admissible transition over that tuple.
- A transition with no representable `PredictionRecord` lineage effect is outside SemanticNG scope.

## S2 — Transition equivalence via PredictionRecord semantics

Two SemanticNG states are equivalent when they yield the same contract-valid projection for the same authorized observer scope.

- Byte-level or ordering artifacts that do not change projection semantics are non-semantic.
- Gate and policy decisions must depend on semantic equivalence, not incidental serialization details.

## S3 — Canonical PredictionRecord normalization

`PredictionRecord` normalization is canonical, unique by semantic equivalence class, and idempotent.

- Re-normalizing an already normalized record is a no-op.
- Equivalent records collapse to the same canonical representation used for comparison, gating, and replay.

## S4 — Boundary invariants for transition safety

SemanticNG invariants are boundary-defined at append, projection, and gate-decision boundaries.

- Prediction availability, evidence-link completeness, and explainable-halt structure are enforced as boundary contracts.
- Transition admission or continuation is invalid when required boundary invariants fail.

## S5 — Deterministic lineage replay for PredictionRecord transitions

For equivalent canonical append-only `PredictionRecord` lineage, replay must yield the same projection state and decision outcomes.

- Restart or reprocessing cannot change outcomes unless lineage input changes.
- Any variability source must be captured as explicit lineage evidence so deterministic replay is preserved.
