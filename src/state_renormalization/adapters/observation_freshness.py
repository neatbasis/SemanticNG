from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol

from state_renormalization.contracts import BeliefState, Episode, ObservationFreshnessPolicyContract, ProjectionState


class ObservationFreshnessPolicyAdapter(Protocol):
    """Adapter interface for supplying freshness policy contracts and dedupe checks."""

    def get_contract(
        self,
        *,
        episode: Episode,
        belief: BeliefState,
        projection_state: ProjectionState,
    ) -> ObservationFreshnessPolicyContract | Mapping[str, Any] | None:
        """Return the freshness policy contract for the current turn, or None to skip checks."""
        ...

    def has_outstanding_request(self, *, scope: str) -> Optional[str]:
        """Return an existing outstanding request id for the same scope (if any)."""
        ...
