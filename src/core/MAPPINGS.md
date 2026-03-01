# MAPPINGS

Define correspondence `Φ_core : Implementation -> Constraint Model`.

Required conditions:
1. **Boundary mapping:** each concrete export/import at module boundary maps to a declared state-space element.
2. **Invariant preservation:** if implementation step `t` is accepted, then `Φ_core(t(x)) ⊨ C`.
3. **Commutation:** `Φ_core ∘ κ = κ ∘ Φ_core` on admissible states.

If any condition fails, mapping is unsound and change is non-admissible.
