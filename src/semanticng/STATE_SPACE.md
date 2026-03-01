# STATE_SPACE

Define:

`S = (X, ~, C, ∂, Ω)`

- `X`: boundary states of `src/semanticng` (exports, re-exports, version binding, namespace contract).
- `~`: equivalence by externally observable module behavior.
- `C`: constraints in `INVARIANTS.md` (`I1..I3`).
- `∂`: admissible edits preserving `C`.
- `Ω`: invalid states (version mismatch, broken bridge behavior, undocumented boundary drift).

Admissible subspace:

`A = { x ∈ X | x ⊨ C }`.

Only transitions closed over `A` are accepted.
