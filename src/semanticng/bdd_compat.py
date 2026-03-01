from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Callable, TypeVar, cast

StepFunc = TypeVar("StepFunc", bound=Callable[..., Any])


def _identity_step_decorator(_: str) -> Callable[[StepFunc], StepFunc]:
    def _decorator(func: StepFunc) -> StepFunc:
        return func

    return _decorator


if importlib.util.find_spec("behave") is not None:
    _behave = importlib.import_module("behave")
    given = cast(Callable[[str], Callable[[StepFunc], StepFunc]], _behave.given)
    when = cast(Callable[[str], Callable[[StepFunc], StepFunc]], _behave.when)
    then = cast(Callable[[str], Callable[[StepFunc], StepFunc]], _behave.then)
else:
    given = _identity_step_decorator
    when = _identity_step_decorator
    then = _identity_step_decorator
