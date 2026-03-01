This README is a projection artifact; normative constraints live in AXIOMS/INVARIANTS/STATE_SPACE/CANONICALIZATION/MAPPINGS.

## Purpose
`src/semanticng` defines the SemanticNG module surface and its module-level composition responsibilities.

## Scope-in (allowed to define)
- SemanticNG module entry points and explicit public surface.
- Composition glue that wires core capabilities into the SemanticNG boundary.
- Module-level contracts that describe externally consumed SemanticNG behavior.

## Scope-out (must not define)
- Fundamental primitives that should live in `src/core`.
- Infrastructure adapter details or persistence/integration mechanics.
- Unscoped cross-module policy that is not specific to SemanticNG boundaries.

## Canonical governing docs
- [AXIOMS.md](./AXIOMS.md)
- [INVARIANTS.md](./INVARIANTS.md)

## Change policy
Before changing behavior in this module, update local governing docs first (especially `AXIOMS.md` and `INVARIANTS.md`) to reflect intended semantics. Behavior changes without corresponding doc updates violate module policy.
