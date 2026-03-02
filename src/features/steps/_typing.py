from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypeVar


class BehaveNode(Protocol):
    name: str


class BehaveFeature(BehaveNode, Protocol):
    filename: str


class BehaveContext(Protocol):
    feature: BehaveFeature
    scenario: BehaveNode
    step: BehaveNode
    table: Any
    text: str

    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...


StepFunc = TypeVar("StepFunc", bound=Callable[..., Any])
StepDecorator = Callable[[str], Callable[[StepFunc], StepFunc]]
