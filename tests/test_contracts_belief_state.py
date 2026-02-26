# tests/test_contracts_belief_state.py
from __future__ import annotations

from state_renormalization.contracts import AmbiguityStatus, BeliefState


def test_belief_state_defaults() -> None:
    b = BeliefState()
    assert b.belief_version == 0
    assert b.ambiguity_state == AmbiguityStatus.NONE
    assert b.pending_about is None
    assert b.pending_question is None
    assert b.pending_attempts == 0
    assert b.bindings == {}
    assert b.active_schemas == []
    assert b.schema_confidence == {}

def test_belief_state_uses_last_status_not_last_ha_status() -> None:
    b = BeliefState()
    assert hasattr(b, "last_status"), "BeliefState should track channel-agnostic last_status"
    assert not hasattr(b, "last_ha_status"), "Do not keep HA-named fields in core BeliefState"
