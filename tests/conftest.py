# tests/conftest.py
from __future__ import annotations

import pytest
from state_renormalization.contracts import BeliefState


@pytest.fixture
def belief() -> BeliefState:
    return BeliefState()
