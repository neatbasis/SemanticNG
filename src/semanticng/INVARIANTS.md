# INVARIANTS

Let `M_sem` be the `src/semanticng` boundary.

## Symbolic constraints
- **I1 (Canonical version export):** `__version__` is part of the public surface and sourced from `semanticng._version`.
- **I2 (Bridge role):** module composes/re-exports implementation surface without redefining core semantics.
- **I3 (Boundary clarity):** semantic boundary policy is documented and remains compatible with `state_renormalization` re-export behavior.

## Failure semantics
- Violation of **I1** is a **release integrity failure**.
- Violation of **I2** is a **semantic drift failure**.
- Violation of **I3** is a **boundary contract failure**.
