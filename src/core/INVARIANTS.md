# INVARIANTS

Let `M_core` be the `src/core` module boundary.

## Symbolic constraints
- **I1 (Surface minimality):** `Exports(M_core) = {__version__}`.
- **I2 (Version provenance):** `__version__` in `core` must be imported from `semanticng._version`.
- **I3 (No orchestration):** `core` defines no feature workflow semantics; only foundational boundary contract.

## Failure semantics
- Violation of **I1** or **I2** is a **contract break** (reject release/build).
- Violation of **I3** is a **layering breach** (must be refactored before merge).

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
