from __future__ import annotations

import importlib
import importlib.util
from typing import cast

from semanticng.interfaces import DeepOntoModuleLike, OntologyLike as OntologyLike

_HAS_DEEPONTO = importlib.util.find_spec("deeponto.onto") is not None

__all__ = ["OntologyLike", "create_ontology"]


def create_ontology(path: str) -> OntologyLike:
    if not _HAS_DEEPONTO:
        raise ModuleNotFoundError("deeponto is required for ontology BDD steps")
    onto_mod = cast(DeepOntoModuleLike, importlib.import_module("deeponto.onto"))
    return onto_mod.Ontology(path)
