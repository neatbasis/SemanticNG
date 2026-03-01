# features/steps/ontology_steps.py

import os

from behave import given, then
from deeponto.onto import Ontology

RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@given('an ontology file "{path}"')
def step_load_ontology(context, path):
    basename = os.path.basename(path)
    print(basename)
    context.onto = Ontology(path)


def _resolve_class_iri(onto: Ontology, cls: str) -> str | None:
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
    iri = _resolve_class_iri(context.onto, cls)
    assert iri is not None, f'Class "{cls}" not found (tried: full IRI, localname, rdfs:label)'
