# INVARIANTS

Let `M_core` be the `src/core` module boundary.

## Symbolic constraints
- **I1 (Public surface minimality):** `PublicExports(M_core) = {__version__}` while internal core modules for deterministic domain contracts/transitions/policies are permitted.
- **I2 (Version provenance):** `__version__` in `core` must be imported from `semanticng._version`.
- **I3 (No integration coupling):** `core` may define deterministic domain state-transition and policy evaluation logic, but must not perform I/O or import adapter/integration modules.

## Failure semantics
- Violation of **I1** or **I2** is a **contract break** (reject release/build).
- Violation of **I3** is a **layering breach** (must be refactored before merge).

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
