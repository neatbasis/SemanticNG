# Mypy Debt List

Policy boundary:

- **Tier 1 (strict, required pre-commit):** `src/state_renormalization`, `src/core`.
- **Tier 2 (extended, optional local / CI):** `src`, `tests`.

Canonical tier source is `[tool.semanticng.mypy_tiers]` in `pyproject.toml`.

Temporary suppressions are tracked against a specific tier below.

- **Tier:** Tier 2 only (BDD integration surface, outside Tier 1 strict gate)
  **Modules:** `steps`, `index_steps`, `ontology_steps`
  **Suppressed:** `import-not-found`, `arg-type`, `misc`, `type-arg`, `typeddict-unknown-key`, and untyped-def/decorator strictness.
  **Why:** Legacy/high-churn Behave BDD glue code uses dynamic `context` mutation and optional runtime deps (`behave`, `deeponto`) not always present in CI type-check envs.
  **Owner:** BDD/Acceptance Test Maintainers.

- **Tier:** Tier 2 only (optional dependency import surface)
  **Imports:** `behave`, `deeponto`, `deeponto.*`
  **Suppressed:** `ignore_missing_imports = true` in targeted mypy override.
  **Why:** Optional dependency group (`bdd`) is not required for core runtime/type-checking pipeline.
  **Owner:** Build & Tooling Maintainers.
