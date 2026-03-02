from __future__ import annotations

import importlib
import importlib.util
from collections.abc import Callable
from typing import Any, cast

from semanticng.interfaces import BehaveModuleLike


def _identity_step_decorator(_: str) -> Callable[[Any], Any]:
    def _decorator(func: Any) -> Any:
        return func

    return _decorator


if importlib.util.find_spec("behave") is not None:
    _behave = cast(BehaveModuleLike, importlib.import_module("behave"))
    given = _behave.given
    when = _behave.when
    then = _behave.then
else:
    given = _identity_step_decorator
    when = _identity_step_decorator
    then = _identity_step_decorator
