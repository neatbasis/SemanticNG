# ARCHITECTURE

Constraint-to-code map for `src/core`:

- `src/core/__init__.py`
  - Enforces **I1** at the package public surface via `__all__ = ["__version__"]`.
  - Enforces **I2** via `from semanticng._version import __version__`.
  - Serves as the concrete boundary state in `S = (X, ~, C, ∂, Ω)`.

Permitted internal modules under `src/core` (not re-exported as package API) include:

- contract/type definitions,
- pure deterministic state-transition logic,
- pure policy evaluators.

All `src/core` modules must remain deterministic and side-effect free at runtime:

- no filesystem/network/process/environment I/O,
- no imports from `src/state_renormalization` adapters/integration modules.

Feature orchestration, adapter invocation, and integration flows remain owned by `src/state_renormalization`.

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
