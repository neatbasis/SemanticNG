# SemanticNG Core (Clean Staging)

This folder defines the **clean core boundary** for SemanticNG: foundational module identity plus its canonical constraint stack.

This README is a **projection artifact**. Normative constraints live in:

1. [AXIOMS.md](./AXIOMS.md)
2. [INVARIANTS.md](./INVARIANTS.md)
3. [STATE_SPACE.md](./STATE_SPACE.md)
4. [CANONICALIZATION.md](./CANONICALIZATION.md)
5. [MAPPINGS.md](./MAPPINGS.md)
6. [CAPABILITY_LEVELS.md](./CAPABILITY_LEVELS.md)
7. [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Active implementation directive

`src/core/REFACTORING_METAPLAN.md` is the active implementation directive for this module.

All work in `src/core/` must satisfy:

- deterministic domain logic only,
- explicit contracts and ports,
- zero direct infrastructure coupling or I/O,
- inward dependency flow.

If a proposed change needs framework, persistence, network, filesystem, or runtime-environment coupling, place it in an adapter layer and keep only the contract in core.

## What Core *Is*

Core is the minimal, deterministic boundary contract for foundational package identity:

- a constrained state space for module-surface correctness,
- canonicalization and equivalence rules for boundary states,
- invariant-preserving evolution rules,
- explicit mapping constraints between implementation and formal model.

Core exists to keep future implementation choices inside an admissible region.

## What Core *Is Not*

Core is not an integration layer, runtime orchestrator, adapter host, or side-effect surface.

In `src/core` specifically:

- no workflow/policy orchestration,
- no external I/O behaviors,
- no expansion of the public surface beyond governed boundary contracts.

---

## Boundary Rules (Hard Constraints)

- `src/core` is a **constraint boundary module**, not a behavior engine.
- Public API surface remains intentionally minimal and explicitly governed.
- Changes that alter boundary semantics must first update local canonical docs (starting with `AXIOMS.md`, then `INVARIANTS.md`).

If a change cannot be justified in the local constraint stack, it does not belong in this module.

---

## Universal Constraint Schema

`src/core` uses the common structural model:

`S = (X, ~, C, ∂, Ω)`

Where:

- `X` is module boundary state,
- `~` is equivalence over observable boundary behavior,
- `C` is the canonical constraint set,
- `∂` is boundary transition surface,
- `Ω` is invariant structure governing admissibility.

See local docs for formal definitions and admissibility criteria.

---

## Capability Levels (Guarantee → Artifacts → Tests)

Levels are formally defined in [CAPABILITY_LEVELS.md](./CAPABILITY_LEVELS.md). Summary:

- **L0 — Declared:** constraint docs exist and are ordered.
- **L1 — Enforced surface:** boundary export/import semantics are constrained.
- **L2 — Governed evolution:** edits preserve invariants and canonical commutation.
- **L3 — Audit-ready:** violations are classifiable and release-blocking.

### Level Coverage (Current)

| Module / Surface | L0 | L1 | L2 | L3 | Notes |
|---|---|---|---|---|---|
| `src/core/__init__.py` | ✅ | ✅ | ✅ | ✅ | Enforces minimal export and version provenance contract. |
| Constraint stack docs | ✅ | ✅ | ✅ | ⏳ | Classification is explicit; automated release gating can keep expanding. |

---

## Determinism Contract

`src/core` must remain deterministic at the boundary level:

- canonicalization is idempotent,
- equivalent states canonicalize to the same representative,
- admissible transitions preserve boundary invariants.

Non-deterministic or representation-accidental drift is out of policy.

---

## Migration Strategy (Legacy to Constrained Core)

Adopt vertical slices:

1. define/adjust target constraint in local docs,
2. apply minimal implementation change,
3. verify parity and invariant preservation,
4. proceed incrementally.

No big-bang mutation of core semantics.

---

## Contribution Rules (Core)

- Update tests/checks for any changed invariant or level claim.
- Keep the module-scope boundary narrow.
- Update local canonical docs before changing behavior.
- Preserve compatibility with the architecture mapping in [ARCHITECTURE.md](./ARCHITECTURE.md).
