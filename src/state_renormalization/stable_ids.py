# state_renormalization/stable_ids.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .gherkin_document import GherkinDocument


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj: Any) -> str:
    """
    Canonical JSON string (stable across runs) for hashing.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class StableIds:
    uri: str
    feature_id: str
    scenario_ids: Dict[str, str]          # key: scenario_key -> scenario_id
    step_ids: Dict[str, str]              # key: step_key -> step_id


def derive_stable_ids(gherkin_document: GherkinDocument, *, uri: Optional[str] = None) -> StableIds:
    """
    Compute stable IDs for feature/scenarios/steps using deterministic hashing.
    Does NOT rely on gherkin-official's internal incremental IDs.
    """
    doc_uri = uri or gherkin_document.uri
    feature = gherkin_document.feature
    feature_name = feature.name
    f_line = feature.location.line
    f_col = feature.location.column

    # Feature ID: uri + feature name (+ location as tie-breaker)
    feature_key_obj = {
        "uri": doc_uri,
        "feature": feature_name,
        "line": f_line,
        "col": f_col,
    }
    feature_id = "feat_" + _sha256_hex(_canon(feature_key_obj))

    scenario_ids: Dict[str, str] = {}
    step_ids: Dict[str, str] = {}

    for scenario in feature.scenarios:
        s_name = scenario.name
        s_keyword = scenario.keyword
        s_line = scenario.location.line
        s_col = scenario.location.column

        scenario_key_obj = {
            "feature_id": feature_id,
            "keyword": s_keyword,
            "name": s_name,
            "line": s_line,
            "col": s_col,
        }
        scenario_id = "scn_" + _sha256_hex(_canon(scenario_key_obj))

        # Scenario "key" is a deterministic string you can use in logs/debugging
        scenario_key = f"{s_keyword}:{s_name}@{s_line}:{s_col}"
        scenario_ids[scenario_key] = scenario_id

        for step in scenario.steps:
            st_text = step.text
            st_type = step.keyword_type
            st_keyword = step.keyword
            st_line = step.location.line
            st_col = step.location.column

            step_key_obj = {
                "scenario_id": scenario_id,
                "keywordType": st_type,
                "keyword": st_keyword,
                "text": st_text,
                "line": st_line,
                "col": st_col,
            }
            step_id = "stp_" + _sha256_hex(_canon(step_key_obj))

            step_key = f"{scenario_key}::{st_type}:{st_text}@{st_line}:{st_col}"
            step_ids[step_key] = step_id

    return StableIds(
        uri=doc_uri,
        feature_id=feature_id,
        scenario_ids=scenario_ids,
        step_ids=step_ids,
    )


def derive_prediction_id(
    *,
    scope_key: str,
    horizon_iso: str,
    issued_at_iso: str,
    filtration_id: str,
    distribution_kind: str,
    distribution_params: Dict[str, Any],
) -> str:
    key_obj = {
        "scope_key": scope_key,
        "horizon_iso": horizon_iso,
        "issued_at_iso": issued_at_iso,
        "filtration_id": filtration_id,
        "distribution_kind": distribution_kind,
        "distribution_params": distribution_params,
    }
    return "pred_" + _sha256_hex(_canon(key_obj))
