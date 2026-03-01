# CANONICALIZATION

Let `κ` canonicalize module surface state.

- **Idempotency:** `κ(κ(x)) = κ(x)`.
- **Unique representative:** each equivalence class `[x]_~` has exactly one canonical representative `x*` with only `__version__` exported.
- **Commutation requirement:** for any admissible transition `τ`, `κ(τ(x)) = τ(κ(x))`.

Non-commuting or non-idempotent canonicalization is a governance failure.
