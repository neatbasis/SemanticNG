# ARCHITECTURE

Constraint-to-code map for `src/semanticng`:

- `src/semanticng/__init__.py`
  - Implements bridge behavior via `from state_renormalization import *` (**I2/I3**).
  - Binds canonical version export via `from ._version import __version__` (**I1**).
  - Defines observable boundary state for `S = (X, ~, C, ∂, Ω)`.

Related module `_version.py` supplies canonical version source used by **I1**.

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
