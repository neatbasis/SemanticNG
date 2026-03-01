This README is a projection artifact; normative constraints live in AXIOMS/INVARIANTS/STATE_SPACE/CANONICALIZATION/MAPPINGS.

## Purpose
`src/core` defines foundational, cross-cutting primitives and contracts used by higher-level modules.

## Scope-in (allowed to define)
- Stable, low-level domain primitives shared across the codebase.
- Core interfaces/protocols that other modules depend on.
- Minimal utilities that enforce global invariants without embedding product workflows.

## Scope-out (must not define)
- Feature-specific orchestration or policy logic belonging to application-level modules.
- SemanticNG composition/assembly behavior that belongs in `src/semanticng`.
- Adapter/integration behavior tied to external systems.

## Canonical governing docs
- [AXIOMS.md](./AXIOMS.md)
- [INVARIANTS.md](./INVARIANTS.md)

## Change policy
Before changing behavior in this module, update local governing docs first (especially `AXIOMS.md` and `INVARIANTS.md`) to reflect the new intended rules. Code changes that alter behavior without corresponding invariant/axiom updates are out of policy.
