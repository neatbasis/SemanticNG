# Mypy Debt List

Policy boundary:

- **Tier 1 (strict, required pre-commit):** `src/state_renormalization`, `src/core`.
- **Tier 2 (extended, optional local / CI):** `src`, `tests`.

Canonical tier source is `[tool.semanticng.mypy_tiers]` in `pyproject.toml`.

Temporary suppressions are tracked against a specific tier below.

- **Tier:** Tier 2 only (BDD step glue signatures)
  **Modules:** `src.features.steps.*`, `steps`, `index_steps`, `ontology_steps`.
  **Suppressed:** `disallow_untyped_defs = false`, `disallow_incomplete_defs = false`, `disallow_untyped_decorators = false`, `warn_return_any = false`.
  **Why:** Behave step functions are decorator-driven entrypoints with runtime-provided `context`, table rows, and doc text objects that are not yet modeled by first-party type stubs.
  **Owner:** BDD/Acceptance Test Maintainers.
  **Removal condition:** Add a typed Behave context protocol/stubs for the step API and annotate all step function signatures/decorator use sites so this module override can be deleted.

- **Tier:** Tier 2 only (optional dependency wrapper boundary)
  **Modules:** `semanticng.bdd_compat`, `semanticng.deeponto_compat`.
  **Suppressed:** `warn_return_any = false`.
  **Why:** The wrappers intentionally use importlib-based loading and runtime attribute lookups to keep optional dependencies (`behave`, `deeponto`) out of the rest of the type surface.
  **Owner:** Build & Tooling Maintainers.
  **Removal condition:** Replace dynamic importlib boundary with typed direct imports guarded by installed optional extras (or dedicated typed stubs), then remove this wrapper-only suppression.
