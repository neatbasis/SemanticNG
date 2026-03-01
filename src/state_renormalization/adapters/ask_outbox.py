from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class AskOutboxAdapter(Protocol):
    """Adapter interface for dispatching human-recruitment requests."""

    def create_request(self, title: str, question: str, context: Mapping[str, object]) -> str:
        """Create an outbox request and return request_id."""
        ...
