# Mypy Debt List

Temporary suppressions added while keeping core `state_renormalization` modules strict.

- **Modules:** `steps`, `index_steps`, `ontology_steps`
  **Suppressed:** `import-not-found`, `arg-type`, `misc`, `type-arg`, `typeddict-unknown-key`, and untyped-def/decorator strictness.
  **Why:** Legacy/high-churn Behave BDD glue code uses dynamic `context` mutation and optional runtime deps (`behave`, `deeponto`) not always present in CI type-check envs.
  **Owner:** BDD/Acceptance Test Maintainers.

- **Imports:** `behave`, `deeponto`, `deeponto.*`
  **Suppressed:** `ignore_missing_imports = true` in targeted mypy override.
  **Why:** Optional dependency group (`bdd`) is not required for core runtime/type-checking pipeline.
  **Owner:** Build & Tooling Maintainers.
