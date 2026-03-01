# features/steps/ontology_steps.py

import os

from semanticng.bdd_compat import given, then
from semanticng.deeponto_compat import OntologyLike, create_ontology
from semanticng.step_state import get_ontology_step_state

RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@given('an ontology file "{path}"')
def step_load_ontology(context, path):
    basename = os.path.basename(path)
    print(basename)
    state = get_ontology_step_state(context)
    state.onto = create_ontology(path)


def _resolve_class_iri(onto: OntologyLike, cls: str) -> str | None:
    # 1) Full IRI given
    if cls.startswith("http://") or cls.startswith("https://"):
        return cls if cls in onto.owl_classes else None

    # 2) Match by local name in IRI (…#MargheritaPizza or …/MargheritaPizza)
    for iri in onto.owl_classes.keys():
        if iri.endswith(f"#{cls}") or iri.endswith(f"/{cls}"):
            return iri

    # 3) Match by rdfs:label (slower but robust)
    #    (Docs show get_annotations takes either OWLObject or its IRI) :contentReference[oaicite:1]{index=1}
    for iri, owl_cls in onto.owl_classes.items():
        labels = onto.get_annotations(owl_cls, annotation_property_iri=RDFS_LABEL)
        if cls in labels:
            return iri

    return None


@then('class "{cls}" should exist')
def step_check_class(context, cls):
    state = get_ontology_step_state(context)
    assert state.onto is not None, "Ontology must be loaded before lookup"
    iri = _resolve_class_iri(state.onto, cls)
    assert iri is not None, f'Class "{cls}" not found (tried: full IRI, localname, rdfs:label)'
