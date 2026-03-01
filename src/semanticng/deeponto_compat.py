from __future__ import annotations

import importlib
import importlib.util
from typing import Protocol, cast


class OntologyLike(Protocol):
    owl_classes: dict[str, object]

    def get_annotations(self, owl_obj: object, annotation_property_iri: str) -> list[str]: ...


_HAS_DEEPONTO = importlib.util.find_spec("deeponto.onto") is not None


def create_ontology(path: str) -> OntologyLike:
    if not _HAS_DEEPONTO:
        raise ModuleNotFoundError("deeponto is required for ontology BDD steps")
    onto_mod = importlib.import_module("deeponto.onto")
    ontology_cls = getattr(onto_mod, "Ontology")
    return cast(OntologyLike, ontology_cls(path))
