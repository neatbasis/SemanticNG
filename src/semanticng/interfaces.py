from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

StepDecorator = Callable[[str], Callable[..., Any]]


class BehaveModuleLike(Protocol):
    given: StepDecorator
    when: StepDecorator
    then: StepDecorator


class OntologyLike(Protocol):
    owl_classes: dict[str, object]

    def get_annotations(self, owl_obj: object, annotation_property_iri: str) -> list[str]: ...


class DeepOntoModuleLike(Protocol):
    Ontology: Callable[[str], OntologyLike]
