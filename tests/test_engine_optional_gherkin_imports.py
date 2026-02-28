from __future__ import annotations

import importlib
from pathlib import Path
from typing import NoReturn

from _pytest.monkeypatch import MonkeyPatch
from state_renormalization.engine import _find_stable_ids_from_payload, _parse_feature_doc


def test_parse_feature_doc_returns_none_when_gherkin_is_unavailable(monkeypatch: MonkeyPatch) -> None:
    def _missing_import(name: str) -> NoReturn:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", _missing_import)

    assert _parse_feature_doc("Feature: demo") is None


def test_find_stable_ids_returns_empty_when_gherkin_is_unavailable(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    feature_path = tmp_path / "demo.feature"
    feature_path.write_text("Feature: Demo\n  Scenario: one\n    Given hello\n", encoding="utf-8")

    def _missing_import(name: str) -> NoReturn:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", _missing_import)

    assert _find_stable_ids_from_payload({"feature_path": str(feature_path)}) == {}
