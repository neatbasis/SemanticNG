# STATE_SPACE

Define:

`S = (X, ~, C, ∂, Ω)`

- `X`: possible public-surface states of `src/core` (`__all__`, imports, doc contract).
- `~`: equivalence relation where states are equal if they expose the same public API contract.
- `C`: constraints from `INVARIANTS.md` (`I1..I3`).
- `∂`: allowed transitions (edits) that preserve `C`.
- `Ω`: invalid/error states (extra exports, wrong version source, orchestration leakage).

Admissible subspace:

`A = { x ∈ X | x ⊨ C }`.

Only transitions `x -> x'` with `x, x' ∈ A` are admissible.

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
