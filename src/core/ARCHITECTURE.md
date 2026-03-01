# ARCHITECTURE

Constraint-to-code map for `src/core`:

- `src/core/__init__.py`
  - Enforces **I1** via `__all__ = ["__version__"]`.
  - Enforces **I2** via `from semanticng._version import __version__`.
  - Serves as the concrete boundary state in `S = (X, ~, C, ∂, Ω)`.

No other module in `src/core` may introduce higher-level orchestration (**I3**).
