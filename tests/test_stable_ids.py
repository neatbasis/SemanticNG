# tests/test_stable_ids.py
from __future__ import annotations

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from state_renormalization.stable_ids import derive_stable_ids


FEATURE_TEXT = """
Feature: Addition
  Scenario: add
    Given a is 1
    When I add 2
    Then result is 3
"""


def _parse(feature_text: str, uri: str):
    parser = Parser()
    doc = parser.parse(TokenScanner(feature_text))
    doc["uri"] = uri
    return doc


def test_stable_ids_are_deterministic_across_runs():
    uri = "./features/core/compiler.feature"

    doc1 = _parse(FEATURE_TEXT, uri)
    doc2 = _parse(FEATURE_TEXT, uri)

    ids1 = derive_stable_ids(doc1)
    ids2 = derive_stable_ids(doc2)

    assert ids1.feature_id == ids2.feature_id
    assert ids1.scenario_ids == ids2.scenario_ids
    assert ids1.step_ids == ids2.step_ids


def test_stable_ids_change_if_uri_changes():
    doc_a = _parse(FEATURE_TEXT, "./features/A.feature")
    doc_b = _parse(FEATURE_TEXT, "./features/B.feature")

    ids_a = derive_stable_ids(doc_a)
    ids_b = derive_stable_ids(doc_b)

    assert ids_a.feature_id != ids_b.feature_id
