from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from semanticng.interfaces import StepDecorator


class BehaveNode(Protocol):
    name: str


class BehaveFeature(BehaveNode, Protocol):
    filename: str


class BehaveRow(Protocol):
    cells: list[str]

    def __getitem__(self, key: str | int) -> str: ...

    def __contains__(self, key: object) -> bool: ...


class BehaveTable(Protocol):
    def __iter__(self) -> Iterator[BehaveRow]: ...


class BehaveContext(Protocol):
    feature: BehaveFeature
    scenario: BehaveNode
    step: BehaveNode
    table: BehaveTable
    text: str

    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...


__all__ = ["BehaveContext", "StepDecorator"]
