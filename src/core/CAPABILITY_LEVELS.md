# CAPABILITY_LEVELS

Staged maturity guarantees for `src/core`:

- **L0 (Declared):** constraints documented (`INVARIANTS`, `STATE_SPACE`, `CANONICALIZATION`, `MAPPINGS`).
- **L1 (Enforced surface):** public API constrained to `__version__` and verified in review/tests.
- **L2 (Governed evolution):** edits validated against commutation + invariant preservation rules.
- **L3 (Audit-ready):** violations are detectable, classified, and release-blocking.
