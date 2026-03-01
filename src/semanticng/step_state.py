from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResourceStepState:
    meta: dict[str, Any] = field(default_factory=dict)
    payload: Any = None
    extensions: dict[str, Any] | None = None
    resource: dict[str, Any] | None = None
    bad_extension: dict[str, Any] | None = None


@dataclass
class IndexStepState:
    pending_dc: dict[str, Any] = field(default_factory=dict)
    pending_payload_text: str | None = None
    last_persisted_resource: Any = None
    last_ingested_resource: Any = None
    last_artifact_resource: Any = None
    last_proposal: dict[str, Any] | None = None
    last_validation: dict[str, Any] | None = None


@dataclass
class OntologyStepState:
    onto: Any = None


def get_resource_step_state(context: Any) -> ResourceStepState:
    state = getattr(context, "_resource_step_state", None)
    if not isinstance(state, ResourceStepState):
        state = ResourceStepState()
        setattr(context, "_resource_step_state", state)
    return state


def get_index_step_state(context: Any) -> IndexStepState:
    state = getattr(context, "_index_step_state", None)
    if not isinstance(state, IndexStepState):
        state = IndexStepState()
        setattr(context, "_index_step_state", state)
    return state


def get_ontology_step_state(context: Any) -> OntologyStepState:
    state = getattr(context, "_ontology_step_state", None)
    if not isinstance(state, OntologyStepState):
        state = OntologyStepState()
        setattr(context, "_ontology_step_state", state)
    return state
