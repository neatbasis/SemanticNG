# MAPPINGS

Define correspondence `Φ_sem : Implementation -> Semantic Constraint Model`.

Required conditions:
1. **Boundary mapping:** concrete namespace/re-export decisions map to declared boundary states.
2. **Invariant preservation:** accepted edits preserve `C` under `Φ_sem`.
3. **Commutation:** `Φ_sem ∘ κ = κ ∘ Φ_sem` for admissible states.

If any condition fails, the implementation no longer soundly realizes the semantic boundary model.
