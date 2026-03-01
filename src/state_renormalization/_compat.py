from __future__ import annotations

from datetime import timezone
from enum import Enum

from typing_extensions import Self

UTC = timezone.utc


class StrEnum(str, Enum):  # noqa: UP042
    """Python 3.10-compatible StrEnum."""

    pass


__all__ = ["Self", "UTC", "StrEnum"]
