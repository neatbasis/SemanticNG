"""
SemanticNG distribution import namespace.

This package currently re-exports the core `state_renormalization` package
for convenience and backwards-compatible imports.
"""

# src/semanticng/__init__.py
from state_renormalization import *  # noqa: F401,F403

from ._version import __version__  # canonical

__all__ = ["__version__"]
