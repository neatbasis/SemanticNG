from __future__ import annotations

"""
Typed boundary for Gherkin parser output.

The gherkin parser returns untyped JSON-like dictionaries. This module is the
only boundary where we inspect that untyped structure and convert it into typed
wrapper models. Downstream code should use `GherkinDocument` accessors rather
than traversing raw `dict[str, Any]` payloads.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class GherkinLocation:
    line: Optional[int]
    column: Optional[int]


@dataclass(frozen=True)
class GherkinStep:
    text: str
    keyword_type: str
    keyword: str
    location: GherkinLocation


@dataclass(frozen=True)
class GherkinScenario:
    name: str
    keyword: str
    location: GherkinLocation
    steps: tuple[GherkinStep, ...]


@dataclass(frozen=True)
class GherkinFeature:
    name: str
    location: GherkinLocation
    scenarios: tuple[GherkinScenario, ...]


@dataclass(frozen=True)
class GherkinDocument:
    uri: str
    feature: GherkinFeature

    @classmethod
    def from_raw(cls, raw: object, *, uri: str = "") -> Optional[GherkinDocument]:
        if not isinstance(raw, dict):
            return None

        feature_raw = raw.get("feature")
        if not isinstance(feature_raw, dict):
            return None

        feature_location = _location_from_raw(feature_raw.get("location"))

        scenarios: list[GherkinScenario] = []
        children = feature_raw.get("children")
        if isinstance(children, list):
            for child in children:
                if not isinstance(child, dict):
                    continue
                scenario_raw = child.get("scenario")
                scenario = _scenario_from_raw(scenario_raw)
                if scenario is not None:
                    scenarios.append(scenario)

        feature = GherkinFeature(
            name=_as_str(feature_raw.get("name")),
            location=feature_location,
            scenarios=tuple(scenarios),
        )

        raw_uri = _as_str(raw.get("uri"))
        return cls(uri=uri or raw_uri, feature=feature)


def _scenario_from_raw(raw: object) -> Optional[GherkinScenario]:
    if not isinstance(raw, dict):
        return None

    steps: list[GherkinStep] = []
    steps_raw = raw.get("steps")
    if isinstance(steps_raw, list):
        for step_raw in steps_raw:
            step = _step_from_raw(step_raw)
            if step is not None:
                steps.append(step)

    return GherkinScenario(
        name=_as_str(raw.get("name")),
        keyword=_as_str(raw.get("keyword")),
        location=_location_from_raw(raw.get("location")),
        steps=tuple(steps),
    )


def _step_from_raw(raw: object) -> Optional[GherkinStep]:
    if not isinstance(raw, dict):
        return None

    return GherkinStep(
        text=_as_str(raw.get("text")),
        keyword_type=_as_str(raw.get("keywordType")),
        keyword=_as_str(raw.get("keyword")),
        location=_location_from_raw(raw.get("location")),
    )


def _location_from_raw(raw: object) -> GherkinLocation:
    if not isinstance(raw, dict):
        return GherkinLocation(line=None, column=None)
    return GherkinLocation(line=_as_int(raw.get("line")), column=_as_int(raw.get("column")))


def _as_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _as_int(value: object) -> Optional[int]:
    return value if isinstance(value, int) else None

