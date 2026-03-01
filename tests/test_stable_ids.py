# tests/test_stable_ids.py
from __future__ import annotations

from typing import Any

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from state_renormalization.gherkin_document import GherkinDocument
from state_renormalization.stable_ids import derive_prediction_id, derive_stable_ids

FEATURE_TEXT = """
Feature: Addition
  Scenario: add
    Given a is 1
    When I add 2
    Then result is 3
"""


def _parse(feature_text: str, uri: str) -> GherkinDocument:
    parser = Parser()
    raw_doc = parser.parse(TokenScanner(feature_text))
    doc = GherkinDocument.from_raw(raw_doc, uri=uri)
    assert doc is not None
    return doc


def test_stable_ids_are_deterministic_across_runs() -> None:
    uri = "./features/core/compiler.feature"

    doc1 = _parse(FEATURE_TEXT, uri)
    doc2 = _parse(FEATURE_TEXT, uri)

    ids1 = derive_stable_ids(doc1)
    ids2 = derive_stable_ids(doc2)

    assert ids1.feature_id == ids2.feature_id
    assert ids1.scenario_ids == ids2.scenario_ids
    assert ids1.step_ids == ids2.step_ids


def test_stable_ids_change_if_uri_changes() -> None:
    doc_a = _parse(FEATURE_TEXT, "./features/A.feature")
    doc_b = _parse(FEATURE_TEXT, "./features/B.feature")

    ids_a = derive_stable_ids(doc_a)
    ids_b = derive_stable_ids(doc_b)

    assert ids_a.feature_id != ids_b.feature_id


def test_prediction_ids_are_deterministic() -> None:
    kwargs: dict[str, Any] = {
        "scope_key": "room:kitchen:light",
        "horizon_iso": "2026-02-13T00:05:00+00:00",
        "issued_at_iso": "2026-02-13T00:00:00+00:00",
        "filtration_id": "filt:1",
        "distribution_kind": "bernoulli",
        "distribution_params": {"p": 0.7},
    }

    first = derive_prediction_id(**kwargs)
    second = derive_prediction_id(**kwargs)

    assert first == second


def test_prediction_ids_change_when_scope_changes() -> None:
    base = derive_prediction_id(
        scope_key="room:kitchen:light",
        horizon_iso="2026-02-13T00:05:00+00:00",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        filtration_id="filt:1",
        distribution_kind="bernoulli",
        distribution_params={"p": 0.7},
    )
    changed = derive_prediction_id(
        scope_key="room:bedroom:light",
        horizon_iso="2026-02-13T00:05:00+00:00",
        issued_at_iso="2026-02-13T00:00:00+00:00",
        filtration_id="filt:1",
        distribution_kind="bernoulli",
        distribution_params={"p": 0.7},
    )

    assert base != changed
