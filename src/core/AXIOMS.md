# Core Axioms

This document defines irreducible, domain-agnostic axioms for `src/core`.

## C1 — State-space existence

A runtime system is modeled as a non-empty state space `S` with admissible transitions `T`.

- Every valid operation maps one admissible state to another admissible state.
- Undefined state representations are outside the model and must be rejected at boundaries.

## C2 — Equivalence-class structure

There exists an equivalence relation `~` over states in `S` such that observationally indistinguishable states are members of the same equivalence class.

- Core behavior may depend on equivalence class membership, not representation accidents.
- Refinements must preserve equivalence-class membership semantics.

## C3 — Canonicalization idempotency and uniqueness

A canonicalization function `canon: S -> S` exists such that:

1. **Idempotency:** `canon(canon(s)) = canon(s)` for all admissible `s`.
2. **Uniqueness by class:** if `s1 ~ s2`, then `canon(s1) = canon(s2)`.
3. **Class preservation:** `canon(s) ~ s`.

These properties make canonical form the stable representative of an equivalence class.

## C4 — Boundary-defined invariant structure

Invariants are defined and evaluated at explicit boundaries (state admission, transition application, and projection/exposure boundaries).

- Invariant semantics are attached to boundary contracts, not hidden implementation details.
- Crossing a boundary without satisfying required invariants is invalid.

## C5 — Deterministic lineage and replay constraints

Given equivalent canonicalized lineage input, replay/projection outcomes are deterministic.

- Re-executing the same admissible lineage yields the same canonical state and same invariant verdicts.
- Non-determinism must be represented as explicit lineage data to remain replay-safe.
