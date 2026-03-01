# SemanticNG Namespace Boundary (Clean Staging)

This folder defines the `semanticng` package boundary as a constrained bridge over implementation modules.

This README is a **projection artifact**. Normative constraints live in:

1. [AXIOMS.md](./AXIOMS.md)
2. [INVARIANTS.md](./INVARIANTS.md)
3. [STATE_SPACE.md](./STATE_SPACE.md)
4. [CANONICALIZATION.md](./CANONICALIZATION.md)
5. [MAPPINGS.md](./MAPPINGS.md)
6. [CAPABILITY_LEVELS.md](./CAPABILITY_LEVELS.md)
7. [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## What `semanticng` *Is*

`src/semanticng` is the canonical namespace boundary for consumers:

- it exposes stable package identity and version provenance,
- it bridges to implementation surface while preserving boundary invariants,
- it constrains external semantics through canonical docs.

## What `semanticng` *Is Not*

`src/semanticng` is not where domain semantics are redefined.

Specifically it must not:

- introduce hidden behavioral drift versus the mapped implementation,
- bypass local invariants/canonicalization constraints,
- blur package-boundary responsibilities.

---

## Boundary Rules (Hard Constraints)

- Boundary semantics must remain explicit and auditable.
- Any export/re-export changes must preserve local invariants.
- Canonicalization and mapping commutation requirements are non-optional.
- Constraint updates must precede behavior updates.

---

## Universal Constraint Schema

`src/semanticng` uses the same abstract structure:

`S = (X, ~, C, ∂, Ω)`

Where `X` is namespace boundary state and admissibility is defined by local invariants and canonicalization constraints.

See local docs for formal definitions and failure semantics.

---

## Capability Levels (Guarantee → Artifacts → Tests)

Levels are defined in [CAPABILITY_LEVELS.md](./CAPABILITY_LEVELS.md). Summary:

- **L0 — Declared:** boundary constraints are explicitly documented.
- **L1 — Stable boundary:** version/export bridge is stable.
- **L2 — Controlled evolution:** edits preserve invariants and canonical form.
- **L3 — Auditable semantics:** incompatible boundary drift is classifiable and blocking.

### Level Coverage (Current)

| Module / Surface | L0 | L1 | L2 | L3 | Notes |
|---|---|---|---|---|---|
| `src/semanticng/__init__.py` | ✅ | ✅ | ✅ | ✅ | Defines bridge + canonical version binding for namespace contract. |
| Constraint stack docs | ✅ | ✅ | ✅ | ⏳ | Explicit semantic boundary model with room for broader automated policy checks. |

---

## Determinism Contract

The package boundary must be replay-stable at semantic level:

- equivalent boundary states remain equivalent across revisions,
- canonicalization remains idempotent,
- accepted edits preserve mapping soundness.

---

## Migration Strategy

For boundary changes:

1. update local constraints,
2. implement minimal boundary edit,
3. validate invariant preservation,
4. expand incrementally.

This keeps compatibility measurable and drift bounded.

---

## Contribution Rules (`semanticng` boundary)

- Treat this package as a constrained semantic boundary, not a dumping ground.
- Keep changes aligned with [ARCHITECTURE.md](./ARCHITECTURE.md).
- Pair behavior changes with constraint and test/check updates.
