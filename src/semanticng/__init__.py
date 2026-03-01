"""
SemanticNG distribution import namespace.

This package currently re-exports the core `state_renormalization` package
for convenience and backwards-compatible imports.
"""

from importlib.metadata import PackageNotFoundError, version

# src/semanticng/__init__.py
from state_renormalization import *  # noqa: F401,F403

try:
    from ._version import __version__  # canonical
except ImportError:  # pragma: no cover - fallback for editable/local non-built environments
    try:
        __version__ = version("semanticng")
    except PackageNotFoundError:
        __version__ = "0+unknown"

__all__ = ["__version__"]
